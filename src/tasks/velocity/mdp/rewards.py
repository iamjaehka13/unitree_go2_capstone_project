from __future__ import annotations

from typing import TYPE_CHECKING

import torch

from mjlab.entity import Entity
from mjlab.managers.reward_manager import RewardTermCfg
from mjlab.managers.scene_entity_config import SceneEntityCfg
from mjlab.sensor import BuiltinSensor, ContactSensor
from mjlab.utils.lab_api.math import quat_apply_inverse
from mjlab.utils.lab_api.string import (
  resolve_matching_names_values,
)

if TYPE_CHECKING:
  from mjlab.envs import ManagerBasedRlEnv


_DEFAULT_ASSET_CFG = SceneEntityCfg("robot")


def _contact_found(sensor: ContactSensor) -> torch.Tensor:
  assert sensor.data.found is not None
  found = sensor.data.found
  if found.dim() == 3 and found.shape[-1] == 1:
    found = found.squeeze(-1)
  return found > 0


def _contact_force_norm(sensor: ContactSensor) -> torch.Tensor:
  assert sensor.data.force is not None
  force = sensor.data.force
  if force.dim() == 4 and force.shape[-2] == 1:
    force = force.squeeze(-2)
  return torch.linalg.norm(force, dim=-1)


def _cross2(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
  return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _support_triangle_metrics(
  support_xy: torch.Tensor,
  com_xy: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
  """Return area, minimum pairwise foot distance, and signed COM margin."""
  a = support_xy[:, 0, :]
  b = support_xy[:, 1, :]
  c = support_xy[:, 2, :]
  ab = b - a
  bc = c - b
  ca = a - c
  signed_area2 = _cross2(ab, c - a)
  area = 0.5 * torch.abs(signed_area2)

  ab_len = torch.linalg.norm(ab, dim=1)
  bc_len = torch.linalg.norm(bc, dim=1)
  ca_len = torch.linalg.norm(ca, dim=1)
  min_foot_distance = torch.minimum(torch.minimum(ab_len, bc_len), ca_len)

  orientation = torch.where(signed_area2 >= 0.0, 1.0, -1.0)
  eps = 1.0e-6
  dist_ab = orientation * _cross2(ab, com_xy - a) / torch.clamp(ab_len, min=eps)
  dist_bc = orientation * _cross2(bc, com_xy - b) / torch.clamp(bc_len, min=eps)
  dist_ca = orientation * _cross2(ca, com_xy - c) / torch.clamp(ca_len, min=eps)
  com_margin = torch.minimum(torch.minimum(dist_ab, dist_bc), dist_ca)
  return area, min_foot_distance, com_margin


def track_linear_velocity(
  env: ManagerBasedRlEnv,
  std: float,
  command_name: str,
  asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
  """Reward for tracking the commanded base linear velocity.

  The commanded z velocity is assumed to be zero.
  """
  asset: Entity = env.scene[asset_cfg.name]
  command = env.command_manager.get_command(command_name)
  assert command is not None, f"Command '{command_name}' not found."
  actual = asset.data.root_link_lin_vel_b
  xy_error = torch.sum(torch.square(command[:, :2] - actual[:, :2]), dim=1)
  z_error = torch.square(actual[:, 2])
  lin_vel_error = xy_error + (2 * z_error)
  return torch.exp(-lin_vel_error / std**2)


def track_angular_velocity(
  env: ManagerBasedRlEnv,
  std: float,
  command_name: str,
  asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
  """Reward heading error for heading-controlled envs, angular velocity for others.

  The commanded xy angular velocities are assumed to be zero.
  """
  asset: Entity = env.scene[asset_cfg.name]
  command = env.command_manager.get_command(command_name)
  assert command is not None, f"Command '{command_name}' not found."
  actual = asset.data.root_link_ang_vel_b
  z_error = torch.square(command[:, 2] - actual[:, 2])
  xy_error = torch.sum(torch.square(actual[:, :2]), dim=1)
  ang_vel_error = z_error + (0.05 * xy_error)
  return torch.exp(-ang_vel_error / std**2)


def body_orientation_l2(
  env: ManagerBasedRlEnv,
  asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
  """Reward flat base orientation (robot being upright).

  If asset_cfg has body_ids specified, computes the projected gravity
  for that specific body. Otherwise, uses the root link projected gravity.
  """
  asset: Entity = env.scene[asset_cfg.name]

  # If body_ids are specified, compute projected gravity for that body.
  if asset_cfg.body_ids:
    body_quat_w = asset.data.body_link_quat_w[:, asset_cfg.body_ids, :]  # [B, N, 4]
    body_quat_w = body_quat_w.squeeze(1)  # [B, 4]
    gravity_w = asset.data.gravity_vec_w  # [3]
    projected_gravity_b = quat_apply_inverse(body_quat_w, gravity_w)  # [B, 3]
    xy_squared = torch.sum(torch.square(projected_gravity_b[:, :2]), dim=1)
  else:
    # Use root link projected gravity.
    xy_squared = torch.sum(torch.square(asset.data.projected_gravity_b[:, :2]), dim=1)
  return xy_squared


def base_height_l2(
  env: ManagerBasedRlEnv,
  target_height: float,
  std: float,
  asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
  """Penalize root height deviation from a standing target."""
  asset: Entity = env.scene[asset_cfg.name]
  height = asset.data.root_link_pos_w[:, 2]
  env.extras["log"]["Metrics/base_height_mean"] = torch.mean(height)
  return torch.square((height - target_height) / std)


def self_collision_cost(
  env: ManagerBasedRlEnv,
  sensor_name: str,
  force_threshold: float = 10.0,
) -> torch.Tensor:
  """Penalize self-collisions.

  When the sensor provides force history (from ``history_length > 0``),
  counts substeps where any contact force exceeds *force_threshold*.
  Falls back to the instantaneous ``found`` count otherwise.
  """
  sensor: ContactSensor = env.scene[sensor_name]
  data = sensor.data
  if data.force_history is not None:
    # force_history: [B, N, H, 3]
    force_mag = torch.norm(data.force_history, dim=-1)  # [B, N, H]
    hit = (force_mag > force_threshold).any(dim=1)  # [B, H]
    return hit.sum(dim=-1).float()  # [B]
  assert data.found is not None
  return data.found.squeeze(-1)


def nonfoot_ground_contact_penalty(
  env: ManagerBasedRlEnv,
  sensor_name: str,
  force_scale: float = 10.0,
) -> torch.Tensor:
  """Penalize any non-foot ground support, including calf/thigh/body contact."""
  sensor: ContactSensor = env.scene[sensor_name]
  found = _contact_found(sensor).reshape(env.num_envs, -1)
  contact_any = torch.any(found, dim=1).float()
  if sensor.data.force is not None:
    force_norm = _contact_force_norm(sensor).reshape(env.num_envs, -1)
    force_sum = torch.sum(force_norm, dim=1)
  else:
    force_sum = torch.zeros(env.num_envs, device=env.device, dtype=torch.float32)

  env.extras["log"]["Metrics/nonfoot_ground_contact_mean"] = torch.mean(contact_any)
  env.extras["log"]["Metrics/nonfoot_ground_force_mean"] = torch.mean(force_sum)
  return contact_any + (force_sum / force_scale)


def body_angular_velocity_penalty(
  env: ManagerBasedRlEnv,
  asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
  """Penalize excessive body angular velocities."""
  asset: Entity = env.scene[asset_cfg.name]
  ang_vel = asset.data.body_link_ang_vel_w[:, asset_cfg.body_ids, :]
  ang_vel = ang_vel.squeeze(1)
  ang_vel_xy = ang_vel[:, :2]  # Don't penalize z-angular velocity.
  return torch.sum(torch.square(ang_vel_xy), dim=1)


def angular_momentum_penalty(
  env: ManagerBasedRlEnv,
  sensor_name: str,
) -> torch.Tensor:
  """Penalize whole-body angular momentum to encourage natural arm swing."""
  angmom_sensor: BuiltinSensor = env.scene[sensor_name]
  angmom = angmom_sensor.data
  angmom_magnitude_sq = torch.sum(torch.square(angmom), dim=-1)
  angmom_magnitude = torch.sqrt(angmom_magnitude_sq)
  env.extras["log"]["Metrics/angular_momentum_mean"] = torch.mean(angmom_magnitude)
  return angmom_magnitude_sq


def feet_air_time(
  env: ManagerBasedRlEnv,
  sensor_name: str,
  threshold: float = 0.4,
  command_name: str | None = None,
  command_threshold: float = 0.1,
) -> torch.Tensor:
  """Reward feet air time."""
  sensor: ContactSensor = env.scene[sensor_name]
  sensor_data = sensor.data
  air_time = sensor_data.current_air_time
  contact_time = sensor_data.current_contact_time
  in_contact = contact_time > 0.0
  in_mode_time = torch.where(in_contact, contact_time, air_time)
  single_stance = torch.mean(in_contact.float(), dim=1) == 0.5
  mode_time = torch.min(torch.where(single_stance.unsqueeze(-1), in_mode_time, 0.0), dim=1)[0]
  error = torch.abs(mode_time - threshold)
  reward = torch.clamp(threshold - error, min=0.0)
  if command_name is not None:
    command = env.command_manager.get_command(command_name)
    if command is not None:
      linear_norm = torch.norm(command[:, :2], dim=1)
      angular_norm = torch.abs(command[:, 2])
      total_command = linear_norm + angular_norm
      scale = (total_command > command_threshold).float()
      reward *= scale
  return reward


def feet_clearance(
  env: ManagerBasedRlEnv,
  target_height: float,
  command_name: str | None = None,
  command_threshold: float = 0.1,
  asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
  """Penalize deviation from target clearance height, weighted by foot velocity."""
  asset: Entity = env.scene[asset_cfg.name]
  foot_z = asset.data.site_pos_w[:, asset_cfg.site_ids, 2]  # [B, N]
  foot_vel_xy = asset.data.site_lin_vel_w[:, asset_cfg.site_ids, :2]  # [B, N, 2]
  vel_norm = torch.norm(foot_vel_xy, dim=-1)  # [B, N]
  delta = torch.abs(foot_z - target_height)  # [B, N]
  cost = torch.sum(delta * vel_norm, dim=1)  # [B]
  if command_name is not None:
    command = env.command_manager.get_command(command_name)
    if command is not None:
      linear_norm = torch.norm(command[:, :2], dim=1)
      angular_norm = torch.abs(command[:, 2])
      total_command = linear_norm + angular_norm
      active = (total_command > command_threshold).float()
      cost = cost * active
  return cost


def feet_gait(
        env: ManagerBasedRlEnv,
        period: float,
        offset: list[float],
        threshold: float,
        command_threshold: float,
        command_name: str,
        sensor_name: str,
) -> torch.Tensor:
    sensor: ContactSensor = env.scene[sensor_name]
    is_contact = sensor.data.current_contact_time > 0
    global_phase = ((env.episode_length_buf * env.step_dt) / period).unsqueeze(1)
    offsets = torch.as_tensor(offset, device=env.device, dtype=global_phase.dtype).view(1, -1)
    leg_phase = (global_phase + offsets) % 1.0
    is_stance = (leg_phase < threshold)
    reward = (is_stance == is_contact).float().mean(dim=1)
    if command_name is not None:
        command = env.command_manager.get_command(command_name)
        if command is not None:
            linear_norm = torch.norm(command[:, :2], dim=1)
            angular_norm = torch.abs(command[:, 2])
            total_command = linear_norm + angular_norm
            scale = (total_command > command_threshold).float()
            reward *= scale
    return reward


class feet_swing_height:
  """Penalize deviation from target swing height, evaluated at landing."""

  def __init__(self, cfg: RewardTermCfg, env: ManagerBasedRlEnv):
    self.sensor_name = cfg.params["sensor_name"]
    self.site_names = cfg.params["asset_cfg"].site_names
    self.peak_heights = torch.zeros(
      (env.num_envs, len(self.site_names)), device=env.device, dtype=torch.float32
    )
    self.step_dt = env.step_dt

  def __call__(
    self,
    env: ManagerBasedRlEnv,
    sensor_name: str,
    target_height: float,
    command_name: str,
    command_threshold: float,
    asset_cfg: SceneEntityCfg,
  ) -> torch.Tensor:
    asset: Entity = env.scene[asset_cfg.name]
    contact_sensor: ContactSensor = env.scene[sensor_name]
    command = env.command_manager.get_command(command_name)
    assert command is not None
    foot_heights = asset.data.site_pos_w[:, asset_cfg.site_ids, 2]
    in_air = contact_sensor.data.found == 0
    self.peak_heights = torch.where(
      in_air,
      torch.maximum(self.peak_heights, foot_heights),
      self.peak_heights,
    )
    first_contact = contact_sensor.compute_first_contact(dt=self.step_dt)
    linear_norm = torch.norm(command[:, :2], dim=1)
    angular_norm = torch.abs(command[:, 2])
    total_command = linear_norm + angular_norm
    active = (total_command > command_threshold).float()
    error = self.peak_heights / target_height - 1.0
    cost = torch.sum(torch.square(error) * first_contact.float(), dim=1) * active
    num_landings = torch.sum(first_contact.float())
    peak_heights_at_landing = self.peak_heights * first_contact.float()
    mean_peak_height = torch.sum(peak_heights_at_landing) / torch.clamp(
      num_landings, min=1
    )
    env.extras["log"]["Metrics/peak_height_mean"] = mean_peak_height
    self.peak_heights = torch.where(
      first_contact,
      torch.zeros_like(self.peak_heights),
      self.peak_heights,
    )
    return cost


def feet_slip(
  env: ManagerBasedRlEnv,
  sensor_name: str,
  command_name: str,
  command_threshold: float = 0.01,
  asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
  """Penalize foot sliding (xy velocity while in contact)."""
  asset: Entity = env.scene[asset_cfg.name]
  contact_sensor: ContactSensor = env.scene[sensor_name]
  command = env.command_manager.get_command(command_name)
  assert command is not None
  linear_norm = torch.norm(command[:, :2], dim=1)
  angular_norm = torch.abs(command[:, 2])
  total_command = linear_norm + angular_norm
  active = (total_command > command_threshold).float()
  assert contact_sensor.data.found is not None
  in_contact = (contact_sensor.data.found > 0).float()  # [B, N]
  foot_vel_xy = asset.data.site_lin_vel_w[:, asset_cfg.site_ids, :2]  # [B, N, 2]
  vel_xy_norm = torch.norm(foot_vel_xy, dim=-1)  # [B, N]
  vel_xy_norm_sq = torch.square(vel_xy_norm)  # [B, N]
  cost = torch.sum(vel_xy_norm_sq * in_contact, dim=1) * active
  num_in_contact = torch.sum(in_contact)
  mean_slip_vel = torch.sum(vel_xy_norm * in_contact) / torch.clamp(
    num_in_contact, min=1
  )
  env.extras["log"]["Metrics/slip_velocity_mean"] = mean_slip_vel
  return cost


def disabled_foot_contact_penalty(
  env: ManagerBasedRlEnv,
  sensor_name: str,
  foot_index: int,
  force_scale: float = 50.0,
) -> torch.Tensor:
  """Penalize contact and support force on a failed/passive foot."""
  contact_sensor: ContactSensor = env.scene[sensor_name]
  in_contact = _contact_found(contact_sensor)[:, foot_index].float()
  force_norm = _contact_force_norm(contact_sensor)[:, foot_index]
  env.extras["log"]["Metrics/disabled_foot_contact_mean"] = torch.mean(in_contact)
  env.extras["log"]["Metrics/disabled_foot_force_mean"] = torch.mean(force_norm)
  return in_contact + (force_norm / force_scale)


def disabled_foot_clearance_reward(
  env: ManagerBasedRlEnv,
  foot_index: int,
  min_height: float,
  max_height: float,
  asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
  """Reward keeping the failed foot visibly off the ground."""
  asset: Entity = env.scene[asset_cfg.name]
  foot_z = asset.data.site_pos_w[:, asset_cfg.site_ids[foot_index], 2]
  clearance = torch.clamp(
    (foot_z - min_height) / max(max_height - min_height, 1.0e-6),
    min=0.0,
    max=1.0,
  )
  env.extras["log"]["Metrics/disabled_foot_height_mean"] = torch.mean(foot_z)
  env.extras["log"]["Metrics/disabled_foot_clearance_reward_mean"] = torch.mean(
    clearance
  )
  return clearance


def required_feet_contact_reward(
  env: ManagerBasedRlEnv,
  sensor_name: str,
  foot_indices: tuple[int, ...],
) -> torch.Tensor:
  """Reward all required support feet being in contact with the ground."""
  contact_sensor: ContactSensor = env.scene[sensor_name]
  in_contact = _contact_found(contact_sensor)[:, list(foot_indices)]
  all_support_feet = torch.all(in_contact, dim=1).float()
  env.extras["log"]["Metrics/support_feet_contact_mean"] = torch.mean(all_support_feet)
  return all_support_feet


def required_feet_load_reward(
  env: ManagerBasedRlEnv,
  sensor_name: str,
  foot_indices: tuple[int, ...],
  min_force: float,
  balance_scale: float = 0.35,
) -> torch.Tensor:
  """Reward all support feet carrying meaningful, not wildly uneven, load."""
  contact_sensor: ContactSensor = env.scene[sensor_name]
  force_norm = _contact_force_norm(contact_sensor)[:, list(foot_indices)]
  min_support_force = torch.min(force_norm, dim=1)[0]
  mean_support_force = torch.mean(force_norm, dim=1)
  force_std = torch.std(force_norm, dim=1, unbiased=False)
  load_score = torch.clamp(min_support_force / min_force, min=0.0, max=1.0)
  balance_error = force_std / torch.clamp(mean_support_force, min=1.0)
  balance_score = torch.exp(-torch.square(balance_error / balance_scale))
  reward = 0.7 * load_score + 0.3 * balance_score

  env.extras["log"]["Metrics/support_min_force_mean"] = torch.mean(min_support_force)
  env.extras["log"]["Metrics/support_mean_force_mean"] = torch.mean(mean_support_force)
  env.extras["log"]["Metrics/support_load_reward_mean"] = torch.mean(reward)
  return reward


def required_feet_stance_tracking(
  env: ManagerBasedRlEnv,
  sensor_name: str,
  foot_indices: tuple[int, ...],
  velocity_scale: float = 0.25,
  asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
  """Dense tripod stance reward adapted from stance-phase gait tracking."""
  contact_sensor: ContactSensor = env.scene[sensor_name]
  asset: Entity = env.scene[asset_cfg.name]
  in_contact = _contact_found(contact_sensor)[:, list(foot_indices)].float()
  foot_vel_xy = asset.data.site_lin_vel_w[:, asset_cfg.site_ids, :2]
  support_vel_xy = foot_vel_xy[:, list(foot_indices), :]
  slip_speed_sq = torch.sum(torch.square(support_vel_xy), dim=-1)
  stance_quality = in_contact * torch.exp(-slip_speed_sq / velocity_scale)
  all_support_feet = torch.all(in_contact.bool(), dim=1).float()

  env.extras["log"]["Metrics/support_feet_contact_mean"] = torch.mean(all_support_feet)
  env.extras["log"]["Metrics/support_feet_contact_fraction"] = torch.mean(in_contact)
  env.extras["log"]["Metrics/support_feet_stance_quality_mean"] = torch.mean(
    stance_quality
  )
  return torch.mean(stance_quality, dim=1)


def required_feet_support_geometry(
  env: ManagerBasedRlEnv,
  foot_indices: tuple[int, ...],
  min_area: float,
  min_foot_distance: float,
  com_margin_scale: float = 0.02,
  asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> torch.Tensor:
  """Reward a wide tripod support polygon with the base projection inside it."""
  asset: Entity = env.scene[asset_cfg.name]
  foot_xy = asset.data.site_pos_w[:, asset_cfg.site_ids, :2]
  support_xy = foot_xy[:, list(foot_indices), :]
  com_xy = asset.data.root_link_pos_w[:, :2]
  area, min_distance, com_margin = _support_triangle_metrics(support_xy, com_xy)

  area_score = torch.clamp(area / min_area, min=0.0, max=1.0)
  distance_score = torch.clamp(min_distance / min_foot_distance, min=0.0, max=1.0)
  margin_score = torch.sigmoid(com_margin / com_margin_scale)
  reward = (area_score + distance_score + margin_score) / 3.0

  env.extras["log"]["Metrics/support_triangle_area_mean"] = torch.mean(area)
  env.extras["log"]["Metrics/support_min_foot_distance_mean"] = torch.mean(min_distance)
  env.extras["log"]["Metrics/support_com_margin_mean"] = torch.mean(com_margin)
  env.extras["log"]["Metrics/support_geometry_reward_mean"] = torch.mean(reward)
  return reward


def soft_landing(
  env: ManagerBasedRlEnv,
  sensor_name: str,
  command_name: str | None = None,
  command_threshold: float = 0.05,
) -> torch.Tensor:
  """Penalize high impact forces at landing to encourage soft footfalls."""
  contact_sensor: ContactSensor = env.scene[sensor_name]
  sensor_data = contact_sensor.data
  assert sensor_data.force is not None
  forces = sensor_data.force  # [B, N, 3]
  force_magnitude = torch.norm(forces, dim=-1)  # [B, N]
  first_contact = contact_sensor.compute_first_contact(dt=env.step_dt)  # [B, N]
  landing_impact = force_magnitude * first_contact.float()  # [B, N]
  cost = torch.sum(landing_impact, dim=1)  # [B]
  num_landings = torch.sum(first_contact.float())
  mean_landing_force = torch.sum(landing_impact) / torch.clamp(num_landings, min=1)
  env.extras["log"]["Metrics/landing_force_mean"] = mean_landing_force
  if command_name is not None:
    command = env.command_manager.get_command(command_name)
    if command is not None:
      linear_norm = torch.norm(command[:, :2], dim=1)
      angular_norm = torch.abs(command[:, 2])
      total_command = linear_norm + angular_norm
      active = (total_command > command_threshold).float()
      cost = cost * active
  return cost


class variable_posture:
  """Penalize deviation from default pose with speed-dependent tolerance.

  Uses per-joint standard deviations to control how much each joint can deviate
  from default pose. Smaller std = stricter (less deviation allowed), larger
  std = more forgiving. The reward is: exp(-mean(error² / std²))

  Three speed regimes (based on linear + angular command velocity):
    - std_standing (speed < walking_threshold): Tight tolerance for holding pose.
    - std_walking (walking_threshold <= speed < running_threshold): Moderate.
    - std_running (speed >= running_threshold): Loose tolerance for large motion.

  Tune std values per joint based on how much motion that joint needs at each
  speed. Map joint name patterns to std values, e.g. {".*knee.*": 0.35}.
  """

  def __init__(self, cfg: RewardTermCfg, env: ManagerBasedRlEnv):
    asset: Entity = env.scene[cfg.params["asset_cfg"].name]
    default_joint_pos = asset.data.default_joint_pos
    assert default_joint_pos is not None
    self.default_joint_pos = default_joint_pos

    _, joint_names = asset.find_joints(cfg.params["asset_cfg"].joint_names)

    _, _, std_standing = resolve_matching_names_values(
      data=cfg.params["std_standing"],
      list_of_strings=joint_names,
    )
    self.std_standing = torch.tensor(
      std_standing, device=env.device, dtype=torch.float32
    )

    _, _, std_walking = resolve_matching_names_values(
      data=cfg.params["std_walking"],
      list_of_strings=joint_names,
    )
    self.std_walking = torch.tensor(std_walking, device=env.device, dtype=torch.float32)

    _, _, std_running = resolve_matching_names_values(
      data=cfg.params["std_running"],
      list_of_strings=joint_names,
    )
    self.std_running = torch.tensor(std_running, device=env.device, dtype=torch.float32)

  def __call__(
    self,
    env: ManagerBasedRlEnv,
    std_standing,
    std_walking,
    std_running,
    asset_cfg: SceneEntityCfg,
    command_name: str,
    walking_threshold: float = 0.5,
    running_threshold: float = 1.5,
  ) -> torch.Tensor:
    del std_standing, std_walking, std_running  # Unused.

    asset: Entity = env.scene[asset_cfg.name]
    command = env.command_manager.get_command(command_name)
    assert command is not None

    linear_speed = torch.norm(command[:, :2], dim=1)
    angular_speed = torch.abs(command[:, 2])
    total_speed = linear_speed + angular_speed

    standing_mask = (total_speed < walking_threshold).float()
    walking_mask = (
      (total_speed >= walking_threshold) & (total_speed < running_threshold)
    ).float()
    running_mask = (total_speed >= running_threshold).float()

    std = (
      self.std_standing * standing_mask.unsqueeze(1)
      + self.std_walking * walking_mask.unsqueeze(1)
      + self.std_running * running_mask.unsqueeze(1)
    )

    current_joint_pos = asset.data.joint_pos[:, asset_cfg.joint_ids]
    desired_joint_pos = self.default_joint_pos[:, asset_cfg.joint_ids]
    error_squared = torch.square(current_joint_pos - desired_joint_pos)

    return torch.exp(-torch.mean(error_squared / (std**2), dim=1))


def stand_still(
        env: ManagerBasedRlEnv,
        command_name: str,
        command_threshold: float = 0.1,
        asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG
) -> torch.Tensor:
    asset: Entity = env.scene[asset_cfg.name]
    diff_angle = asset.data.joint_pos[:, asset_cfg.joint_ids] - asset.data.default_joint_pos[:, asset_cfg.joint_ids]
    reward = torch.sum(torch.square(diff_angle), dim=1)
    if command_name is not None:
        command = env.command_manager.get_command(command_name)
        if command is not None:
            linear_norm = torch.norm(command[:, :2], dim=1)
            angular_norm = torch.abs(command[:, 2])
            total_command = linear_norm + angular_norm
            scale = (total_command <= command_threshold).float()
            reward *= scale
    return reward
