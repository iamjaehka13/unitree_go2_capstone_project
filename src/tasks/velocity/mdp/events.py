from __future__ import annotations

from typing import TYPE_CHECKING

import torch

from mjlab.entity import Entity
from mjlab.managers.scene_entity_config import SceneEntityCfg
from mjlab.utils.lab_api.math import sample_uniform

if TYPE_CHECKING:
  from mjlab.envs import ManagerBasedRlEnv


_DEFAULT_ASSET_CFG = SceneEntityCfg("robot")


def reset_joints_by_pose_curriculum(
  env: ManagerBasedRlEnv,
  env_ids: torch.Tensor | None,
  default_joint_pos: tuple[float, ...],
  tripod_joint_pos: tuple[float, ...],
  alpha_start: float = 1.0,
  alpha_end: float = 0.0,
  decay_steps: int = 80_000,
  alpha_noise: float = 0.1,
  joint_noise_range: tuple[float, float] = (-0.03, 0.03),
  velocity_range: tuple[float, float] = (-0.02, 0.02),
  asset_cfg: SceneEntityCfg = _DEFAULT_ASSET_CFG,
) -> None:
  """Reset joints from a tripod-to-default curriculum distribution.

  ``alpha=1`` means tripod pose, and ``alpha=0`` means default pose.
  The schedule moves alpha from ``alpha_start`` to ``alpha_end`` over
  ``decay_steps`` environment steps, with optional per-reset alpha noise.
  """
  if env_ids is None:
    env_ids = torch.arange(env.num_envs, device=env.device, dtype=torch.int)

  asset: Entity = env.scene[asset_cfg.name]
  soft_joint_pos_limits = asset.data.soft_joint_pos_limits
  assert soft_joint_pos_limits is not None

  default = torch.tensor(default_joint_pos, device=env.device, dtype=torch.float32)
  tripod = torch.tensor(tripod_joint_pos, device=env.device, dtype=torch.float32)
  if default.shape != tripod.shape:
    raise ValueError(
      f"default_joint_pos shape {default.shape} != tripod_joint_pos shape {tripod.shape}"
    )

  progress = min(max(env.common_step_counter / max(decay_steps, 1), 0.0), 1.0)
  alpha_center = alpha_start + (alpha_end - alpha_start) * progress
  alpha = torch.full((len(env_ids), 1), alpha_center, device=env.device)
  if alpha_noise > 0.0:
    alpha += sample_uniform(
      -alpha_noise, alpha_noise, alpha.shape, device=env.device
    )
  alpha = torch.clamp(alpha, min=min(alpha_start, alpha_end), max=max(alpha_start, alpha_end))

  joint_pos = (1.0 - alpha) * default + alpha * tripod
  joint_pos += sample_uniform(*joint_noise_range, joint_pos.shape, device=env.device)

  joint_pos_limits = soft_joint_pos_limits[env_ids][:, asset_cfg.joint_ids]
  joint_pos = joint_pos.clamp_(joint_pos_limits[..., 0], joint_pos_limits[..., 1])

  joint_vel = sample_uniform(
    *velocity_range, joint_pos.shape, device=env.device
  )

  joint_ids = asset_cfg.joint_ids
  if isinstance(joint_ids, list):
    joint_ids = torch.tensor(joint_ids, device=env.device)

  asset.write_joint_state_to_sim(
    joint_pos.view(len(env_ids), -1),
    joint_vel.view(len(env_ids), -1),
    env_ids=env_ids,
    joint_ids=joint_ids,
  )

  if hasattr(env, "extras"):
    env.extras.setdefault("log", {})
    env.extras["log"]["Metrics/init_pose_alpha_mean"] = torch.mean(alpha)
