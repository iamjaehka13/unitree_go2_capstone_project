"""Unitree Go2 velocity environment configurations."""

import math
from typing import Literal

from src.assets.robots import (
  get_go2_fr_failure_robot_cfg,
  get_go2_fr_locked_tucked_robot_cfg,
  get_go2_robot_cfg,
)
from src.assets.robots.unitree_go2.go2_constants import (
  GO2_DEFAULT_JOINT_POS_TUPLE,
  GO2_FR_TRIPOD_JOINT_POS_TUPLE,
  GO2_JOINT_NAMES,
)
from mjlab.envs import ManagerBasedRlEnvCfg
from mjlab.envs import mdp as envs_mdp
from mjlab.envs.mdp.actions import JointPositionActionCfg
from mjlab.managers import RewardTermCfg, SceneEntityCfg, TerminationTermCfg
from mjlab.managers.event_manager import EventTermCfg
from mjlab.sensor import ContactMatch, ContactSensorCfg, RayCastSensorCfg
from mjlab.tasks.velocity.mdp import UniformVelocityCommandCfg
from src.tasks.velocity import mdp

from src.tasks.velocity.velocity_env_cfg import make_velocity_env_cfg

TerrainType = Literal["rough", "obstacles"]
# ContactSensor resolves Go2 foot collision geoms in MuJoCo model order, not in
# the tuple order passed to ContactSensorCfg.
GO2_FOOT_SENSOR_ORDER = ("FL", "FR", "RL", "RR")
GO2_STAND_MIN_BASE_HEIGHT_M = 0.23
GO2_STAND_TARGET_BASE_HEIGHT_M = 0.28


def unitree_go2_rough_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create Unitree Go2 rough terrain velocity configuration."""
  cfg = make_velocity_env_cfg()

  cfg.sim.mujoco.ccd_iterations = 500
  cfg.sim.contact_sensor_maxmatch = 500

  cfg.scene.entities = {"robot": get_go2_robot_cfg()}

  # Set raycast sensor frame to Go2 base_link.
  for sensor in cfg.scene.sensors or ():
    if sensor.name == "terrain_scan":
      assert isinstance(sensor, RayCastSensorCfg)
      sensor.frame.name = "base_link"

  foot_names = ("FR", "FL", "RR", "RL")
  site_names = ("FR", "FL", "RR", "RL")
  geom_names = tuple(f"{name}_foot_collision" for name in foot_names)

  feet_ground_cfg = ContactSensorCfg(
    name="feet_ground_contact",
    primary=ContactMatch(mode="geom", pattern=geom_names, entity="robot"),
    secondary=ContactMatch(mode="body", pattern="terrain"),
    fields=("found", "force"),
    reduce="netforce",
    num_slots=1,
    track_air_time=True,
  )
  nonfoot_ground_cfg = ContactSensorCfg(
    name="nonfoot_ground_touch",
    primary=ContactMatch(
      mode="geom",
      entity="robot",
      # Grab all collision geoms...
      pattern=r".*_collision\d*$",
      # Except for the foot geoms.
      exclude=tuple(geom_names),
    ),
    secondary=ContactMatch(mode="body", pattern="terrain"),
    fields=("found", "force"),
    reduce="none",
    num_slots=1,
    history_length=4,
  )
  cfg.scene.sensors = (cfg.scene.sensors or ()) + (
    feet_ground_cfg,
    nonfoot_ground_cfg,
  )

  if cfg.scene.terrain is not None and cfg.scene.terrain.terrain_generator is not None:
    cfg.scene.terrain.terrain_generator.curriculum = True

  joint_pos_action = cfg.actions["joint_pos"]
  assert isinstance(joint_pos_action, JointPositionActionCfg)

  cfg.viewer.body_name = "base_link"
  cfg.viewer.distance = 1.5
  cfg.viewer.elevation = -10.0

  cfg.observations["critic"].terms["foot_height"].params["asset_cfg"].site_names = site_names

  cfg.events["foot_friction"].params["asset_cfg"].geom_names = geom_names
  cfg.events["base_com"].params["asset_cfg"].body_names = ("base_link",)

  cfg.rewards["pose"].params["std_standing"] = {
    r".*(FR|FL|RR|RL)_hip_joint.*": 0.05,
    r".*(FR|FL|RR|RL)_thigh_joint.*": 0.1,
    r".*(FR|FL|RR|RL)_calf_joint.*": 0.15,
  }
  cfg.rewards["pose"].params["std_walking"] = {
    r".*(FR|FL|RR|RL)_hip_joint.*": 0.15,
    r".*(FR|FL|RR|RL)_thigh_joint.*": 0.35,
    r".*(FR|FL|RR|RL)_calf_joint.*": 0.5,
  }
  cfg.rewards["pose"].params["std_running"] = {
    r".*(FR|FL|RR|RL)_hip_joint.*": 0.15,
    r".*(FR|FL|RR|RL)_thigh_joint.*": 0.35,
    r".*(FR|FL|RR|RL)_calf_joint.*": 0.5,
  }

  cfg.rewards["foot_gait"].params["offset"] = [0.0, 0.5, 0.5, 0.0]
  cfg.rewards["body_orientation_l2"].params["asset_cfg"].body_names = ("base_link",)
  cfg.rewards["body_ang_vel"].params["asset_cfg"].body_names = ("base_link",)
  cfg.rewards["foot_clearance"].params["asset_cfg"].site_names = site_names
  cfg.rewards["foot_slip"].params["asset_cfg"].site_names = site_names

  cfg.terminations["illegal_contact"] = TerminationTermCfg(
    func=mdp.illegal_contact,
    params={"sensor_name": nonfoot_ground_cfg.name, "force_threshold": 10.0},
  )

  # Apply play mode overrides.
  if play:
    # Effectively infinite episode length.
    cfg.episode_length_s = int(1e9)

    cfg.observations["actor"].enable_corruption = False
    cfg.events.pop("push_robot", None)
    cfg.curriculum = {}
    cfg.events["randomize_terrain"] = EventTermCfg(
      func=envs_mdp.randomize_terrain,
      mode="reset",
      params={},
    )

    if cfg.scene.terrain is not None:
      if cfg.scene.terrain.terrain_generator is not None:
        cfg.scene.terrain.terrain_generator.curriculum = False
        cfg.scene.terrain.terrain_generator.num_cols = 5
        cfg.scene.terrain.terrain_generator.num_rows = 5
        cfg.scene.terrain.terrain_generator.border_width = 10.0

  return cfg


def unitree_go2_flat_env_cfg(play: bool = False) -> ManagerBasedRlEnvCfg:
  """Create Unitree Go2 flat terrain velocity configuration."""
  cfg = unitree_go2_rough_env_cfg(play=play)

  cfg.sim.njmax = 300
  cfg.sim.mujoco.ccd_iterations = 50
  cfg.sim.contact_sensor_maxmatch = 64
  cfg.sim.nconmax = None

  # Switch to flat terrain.
  assert cfg.scene.terrain is not None
  cfg.scene.terrain.terrain_type = "plane"
  cfg.scene.terrain.terrain_generator = None

  # Remove raycast sensor and height scan (no terrain to scan).
  cfg.scene.sensors = tuple(
    s for s in (cfg.scene.sensors or ()) if s.name != "terrain_scan"
  )
  del cfg.observations["actor"].terms["height_scan"]
  del cfg.observations["critic"].terms["height_scan"]

  # Disable terrain curriculum (not present in play mode since rough clears all).
  cfg.curriculum.pop("terrain_levels", None)

  if play:
    twist_cmd = cfg.commands["twist"]
    assert isinstance(twist_cmd, UniformVelocityCommandCfg)
    twist_cmd.ranges.lin_vel_x = (-0.5, 1.0)
    twist_cmd.ranges.lin_vel_y = (-0.5, 0.5)
    twist_cmd.ranges.ang_vel_z = (-0.5, 0.5)

  return cfg


def _configure_standing_env(cfg: ManagerBasedRlEnvCfg, play: bool) -> ManagerBasedRlEnvCfg:
  """Convert the Go2 flat velocity task into a static standing task."""
  cfg.episode_length_s = int(1e9) if play else 10.0

  cfg.observations["actor"].enable_corruption = False

  twist_cmd = cfg.commands["twist"]
  assert isinstance(twist_cmd, UniformVelocityCommandCfg)
  twist_cmd.resampling_time_range = (10.0, 10.0)
  twist_cmd.rel_standing_envs = 1.0
  twist_cmd.heading_command = False
  twist_cmd.debug_vis = False
  twist_cmd.ranges.lin_vel_x = (0.0, 0.0)
  twist_cmd.ranges.lin_vel_y = (0.0, 0.0)
  twist_cmd.ranges.ang_vel_z = (0.0, 0.0)
  twist_cmd.ranges.heading = None

  cfg.events.pop("push_robot", None)
  cfg.events.pop("foot_friction", None)
  cfg.events.pop("encoder_bias", None)
  cfg.events.pop("base_com", None)
  cfg.events["reset_base"].params = {
    "pose_range": {
      "x": (0.0, 0.0),
      "y": (0.0, 0.0),
      "z": (0.0, 0.0),
      "roll": (0.0, 0.0),
      "pitch": (0.0, 0.0),
      "yaw": (0.0, 0.0),
    },
    "velocity_range": {},
  }
  cfg.events["reset_robot_joints"].params["position_range"] = (0.0, 0.0)
  cfg.events["reset_robot_joints"].params["velocity_range"] = (0.0, 0.0)

  cfg.curriculum = {}

  cfg.rewards = {
    "is_alive": RewardTermCfg(func=envs_mdp.is_alive, weight=1.0),
    "track_linear_velocity": cfg.rewards["track_linear_velocity"],
    "track_angular_velocity": cfg.rewards["track_angular_velocity"],
    "body_orientation_l2": cfg.rewards["body_orientation_l2"],
    "base_height_l2": RewardTermCfg(
      func=mdp.base_height_l2,
      weight=-1.0,
      params={
        "target_height": GO2_STAND_TARGET_BASE_HEIGHT_M,
        "std": 0.05,
        "asset_cfg": SceneEntityCfg("robot"),
      },
    ),
    "pose": cfg.rewards["pose"],
    "body_ang_vel": cfg.rewards["body_ang_vel"],
    "is_terminated": cfg.rewards["is_terminated"],
    "joint_vel_l2": RewardTermCfg(
      func=envs_mdp.joint_vel_l2,
      weight=-1.0e-3,
      params={"asset_cfg": SceneEntityCfg("robot", joint_names=".*")},
    ),
    "joint_acc_l2": cfg.rewards["joint_acc_l2"],
    "joint_torques_l2": RewardTermCfg(
      func=envs_mdp.joint_torques_l2,
      weight=-2.0e-5,
      params={"asset_cfg": SceneEntityCfg("robot", actuator_names=".*")},
    ),
    "joint_pos_limits": cfg.rewards["joint_pos_limits"],
    "action_rate_l2": cfg.rewards["action_rate_l2"],
    "foot_slip": cfg.rewards["foot_slip"],
    "soft_landing": cfg.rewards["soft_landing"],
    "stand_still": cfg.rewards["stand_still"],
  }

  cfg.rewards["body_orientation_l2"].weight = -5.0
  cfg.rewards["body_ang_vel"].weight = -0.1
  cfg.rewards["foot_slip"].weight = -0.5
  cfg.rewards["foot_slip"].params["command_threshold"] = -1.0
  cfg.rewards["soft_landing"].params["command_threshold"] = -1.0
  cfg.rewards["stand_still"].weight = -0.5

  cfg.terminations["fell_over"].params["limit_angle"] = math.radians(60.0)
  cfg.terminations["base_height"] = TerminationTermCfg(
    func=envs_mdp.root_height_below_minimum,
    params={"minimum_height": GO2_STAND_MIN_BASE_HEIGHT_M},
  )

  return cfg


def _add_fr_tripod_contact_rewards(
  cfg: ManagerBasedRlEnvCfg,
  strict_geometry: bool = False,
  clean_tripod: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Discourage using the passive FR foot as a support foot."""
  support_foot_indices = (
    GO2_FOOT_SENSOR_ORDER.index("FL"),
    GO2_FOOT_SENSOR_ORDER.index("RR"),
    GO2_FOOT_SENSOR_ORDER.index("RL"),
  )
  cfg.rewards["fr_disabled_foot_contact"] = RewardTermCfg(
    func=mdp.disabled_foot_contact_penalty,
    weight=-8.0 if clean_tripod else (-4.0 if strict_geometry else -2.0),
    params={
      "sensor_name": "feet_ground_contact",
      "foot_index": GO2_FOOT_SENSOR_ORDER.index("FR"),
      "force_scale": 50.0,
    },
  )
  if clean_tripod:
    cfg.rewards["fr_disabled_foot_clearance"] = RewardTermCfg(
      func=mdp.disabled_foot_clearance_reward,
      weight=3.0,
      params={
        "foot_index": GO2_FOOT_SENSOR_ORDER.index("FR"),
        "min_height": 0.045,
        "max_height": 0.09,
        "asset_cfg": SceneEntityCfg(
          "robot", site_names=GO2_FOOT_SENSOR_ORDER, preserve_order=True
        ),
      },
    )
  cfg.rewards["fr_support_feet_contact"] = RewardTermCfg(
    func=mdp.required_feet_contact_reward,
    weight=3.0 if clean_tripod else (2.0 if strict_geometry else 1.0),
    params={
      "sensor_name": "feet_ground_contact",
      "foot_indices": support_foot_indices,
    },
  )
  if clean_tripod:
    cfg.rewards["fr_support_feet_load"] = RewardTermCfg(
      func=mdp.required_feet_load_reward,
      weight=3.0,
      params={
        "sensor_name": "feet_ground_contact",
        "foot_indices": support_foot_indices,
        "min_force": 20.0,
        "balance_scale": 0.45,
      },
    )
  cfg.rewards["fr_support_feet_stance_tracking"] = RewardTermCfg(
    func=mdp.required_feet_stance_tracking,
    weight=8.0 if clean_tripod else (6.0 if strict_geometry else 4.0),
    params={
      "sensor_name": "feet_ground_contact",
      "foot_indices": support_foot_indices,
      "velocity_scale": 0.25,
      "asset_cfg": SceneEntityCfg(
        "robot", site_names=GO2_FOOT_SENSOR_ORDER, preserve_order=True
      ),
    },
  )
  if strict_geometry:
    cfg.terminations["illegal_contact"].params["force_threshold"] = 1.0
    cfg.rewards["nonfoot_ground_contact"] = RewardTermCfg(
      func=mdp.nonfoot_ground_contact_penalty,
      weight=-35.0 if clean_tripod else -20.0,
      params={
        "sensor_name": "nonfoot_ground_touch",
        "force_scale": 10.0,
      },
    )
    if clean_tripod:
      cfg.rewards["pose"].weight = 0.0
      cfg.rewards["stand_still"].weight = -0.1
      cfg.rewards["base_height_l2"].weight = -4.0
      cfg.rewards["base_height_l2"].params["std"] = 0.035
      cfg.rewards["body_orientation_l2"].weight = -8.0
      cfg.rewards["body_ang_vel"].weight = -0.2
    cfg.rewards["fr_support_geometry"] = RewardTermCfg(
      func=mdp.required_feet_support_geometry,
      weight=8.0 if clean_tripod else 5.0,
      params={
        "foot_indices": support_foot_indices,
        "min_area": 0.05 if clean_tripod else 0.025,
        "min_foot_distance": 0.30 if clean_tripod else 0.16,
        "com_margin_scale": 0.015 if clean_tripod else 0.02,
        "asset_cfg": SceneEntityCfg(
          "robot", site_names=GO2_FOOT_SENSOR_ORDER, preserve_order=True
        ),
      },
    )
  return cfg


def unitree_go2_stand_env_cfg(play: bool = False) -> ManagerBasedRlEnvCfg:
  """Create Unitree Go2 four-leg static standing configuration."""
  cfg = unitree_go2_flat_env_cfg(play=play)
  return _configure_standing_env(cfg, play=play)


def unitree_go2_fr_failure_default_stand_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create Go2 static standing config with the whole FR leg torque set to zero."""
  cfg = unitree_go2_flat_env_cfg(play=play)
  cfg.scene.entities = {
    "robot": get_go2_fr_failure_robot_cfg(init_pose="default"),
  }
  cfg = _configure_standing_env(cfg, play=play)
  return _add_fr_tripod_contact_rewards(cfg)


def unitree_go2_fr_failure_tripod_stand_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create Go2 static standing config with FR torque-zero and tripod init pose."""
  cfg = unitree_go2_flat_env_cfg(play=play)
  cfg.scene.entities = {
    "robot": get_go2_fr_failure_robot_cfg(init_pose="tripod"),
  }
  cfg = _configure_standing_env(cfg, play=play)
  return _add_fr_tripod_contact_rewards(cfg)


def unitree_go2_fr_failure_init_curriculum_stand_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create FR failure standing config with tripod-to-default reset curriculum."""
  cfg = unitree_go2_flat_env_cfg(play=play)
  cfg.scene.entities = {
    "robot": get_go2_fr_failure_robot_cfg(init_pose="default"),
  }
  cfg = _configure_standing_env(cfg, play=play)
  cfg.events["reset_robot_joints"] = EventTermCfg(
    func=mdp.reset_joints_by_pose_curriculum,
    mode="reset",
    params={
      "default_joint_pos": GO2_DEFAULT_JOINT_POS_TUPLE,
      "tripod_joint_pos": GO2_FR_TRIPOD_JOINT_POS_TUPLE,
      "alpha_start": 1.0,
      "alpha_end": 0.0,
      "decay_steps": 80_000,
      "alpha_noise": 0.10,
      "joint_noise_range": (-0.03, 0.03),
      "velocity_range": (-0.02, 0.02),
      "asset_cfg": SceneEntityCfg(
        "robot", joint_names=GO2_JOINT_NAMES, preserve_order=True
      ),
    },
  )
  return _add_fr_tripod_contact_rewards(cfg)


def unitree_go2_fr_failure_default_strict_stand_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create FR-failure default-init standing config with strict tripod geometry reward."""
  cfg = unitree_go2_flat_env_cfg(play=play)
  cfg.scene.entities = {
    "robot": get_go2_fr_failure_robot_cfg(init_pose="default"),
  }
  cfg = _configure_standing_env(cfg, play=play)
  return _add_fr_tripod_contact_rewards(cfg, strict_geometry=True)


def unitree_go2_fr_failure_tripod_strict_stand_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create FR-failure tripod-init standing config with strict support geometry reward."""
  cfg = unitree_go2_flat_env_cfg(play=play)
  cfg.scene.entities = {
    "robot": get_go2_fr_failure_robot_cfg(init_pose="tripod"),
  }
  cfg = _configure_standing_env(cfg, play=play)
  return _add_fr_tripod_contact_rewards(cfg, strict_geometry=True)


def unitree_go2_fr_failure_init_curriculum_strict_stand_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create FR-failure init-curriculum config with strict support geometry reward."""
  cfg = unitree_go2_flat_env_cfg(play=play)
  cfg.scene.entities = {
    "robot": get_go2_fr_failure_robot_cfg(init_pose="default"),
  }
  cfg = _configure_standing_env(cfg, play=play)
  cfg.events["reset_robot_joints"] = EventTermCfg(
    func=mdp.reset_joints_by_pose_curriculum,
    mode="reset",
    params={
      "default_joint_pos": GO2_DEFAULT_JOINT_POS_TUPLE,
      "tripod_joint_pos": GO2_FR_TRIPOD_JOINT_POS_TUPLE,
      "alpha_start": 1.0,
      "alpha_end": 0.0,
      "decay_steps": 80_000,
      "alpha_noise": 0.10,
      "joint_noise_range": (-0.03, 0.03),
      "velocity_range": (-0.02, 0.02),
      "asset_cfg": SceneEntityCfg(
        "robot", joint_names=GO2_JOINT_NAMES, preserve_order=True
      ),
    },
  )
  return _add_fr_tripod_contact_rewards(cfg, strict_geometry=True)


def unitree_go2_fr_failure_default_clean_stand_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create FR-failure default-init standing config with clean tripod reward."""
  cfg = unitree_go2_flat_env_cfg(play=play)
  cfg.scene.entities = {
    "robot": get_go2_fr_failure_robot_cfg(init_pose="default"),
  }
  cfg = _configure_standing_env(cfg, play=play)
  return _add_fr_tripod_contact_rewards(
    cfg, strict_geometry=True, clean_tripod=True
  )


def unitree_go2_fr_failure_tripod_clean_stand_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create FR-failure tripod-init standing config with clean tripod reward."""
  cfg = unitree_go2_flat_env_cfg(play=play)
  cfg.scene.entities = {
    "robot": get_go2_fr_failure_robot_cfg(init_pose="tripod"),
  }
  cfg = _configure_standing_env(cfg, play=play)
  return _add_fr_tripod_contact_rewards(
    cfg, strict_geometry=True, clean_tripod=True
  )


def unitree_go2_fr_failure_locked_tucked_clean_stand_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create FR-failure clean standing config with the FR leg locked tucked."""
  cfg = unitree_go2_flat_env_cfg(play=play)
  cfg.scene.entities = {
    "robot": get_go2_fr_locked_tucked_robot_cfg(),
  }
  cfg = _configure_standing_env(cfg, play=play)
  return _add_fr_tripod_contact_rewards(
    cfg, strict_geometry=True, clean_tripod=True
  )


def unitree_go2_fr_failure_init_curriculum_clean_stand_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create FR-failure init-curriculum config with clean tripod reward."""
  cfg = unitree_go2_flat_env_cfg(play=play)
  cfg.scene.entities = {
    "robot": get_go2_fr_failure_robot_cfg(init_pose="default"),
  }
  cfg = _configure_standing_env(cfg, play=play)
  cfg.events["reset_robot_joints"] = EventTermCfg(
    func=mdp.reset_joints_by_pose_curriculum,
    mode="reset",
    params={
      "default_joint_pos": GO2_DEFAULT_JOINT_POS_TUPLE,
      "tripod_joint_pos": GO2_FR_TRIPOD_JOINT_POS_TUPLE,
      "alpha_start": 1.0,
      "alpha_end": 0.0,
      "decay_steps": 80_000,
      "alpha_noise": 0.10,
      "joint_noise_range": (-0.03, 0.03),
      "velocity_range": (-0.02, 0.02),
      "asset_cfg": SceneEntityCfg(
        "robot", joint_names=GO2_JOINT_NAMES, preserve_order=True
      ),
    },
  )
  return _add_fr_tripod_contact_rewards(
    cfg, strict_geometry=True, clean_tripod=True
  )
