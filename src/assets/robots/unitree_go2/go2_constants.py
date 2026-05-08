"""Unitree Go2 constants."""

from pathlib import Path
from typing import Literal

import mujoco

from src import SRC_PATH
from mjlab.actuator import BuiltinPositionActuatorCfg
from mjlab.entity import EntityArticulationInfoCfg, EntityCfg
from mjlab.utils.actuator import ElectricActuator, reflected_inertia
from mjlab.utils.os import update_assets
from mjlab.utils.spec_config import CollisionCfg

##
# MJCF and assets.
##

GO2_XML: Path = (
  SRC_PATH / "assets" / "robots" / "unitree_go2" / "xmls" / "go2.xml"
)
assert GO2_XML.exists()


def get_assets(meshdir: str) -> dict[str, bytes]:
  assets: dict[str, bytes] = {}
  update_assets(assets, GO2_XML.parent / "assets", meshdir)
  return assets


def get_spec() -> mujoco.MjSpec:
  spec = mujoco.MjSpec.from_file(str(GO2_XML))
  spec.assets = get_assets(spec.meshdir)
  return spec


##
# Actuator config.
##

GO2_ACTUATOR_HIP = BuiltinPositionActuatorCfg(
  target_names_expr=(
    ".*hip_.*",
  ),
  stiffness=20.0,
  damping=1.0,
  effort_limit=23.5,
  armature=0.01,
)
GO2_ACTUATOR_THIGH = BuiltinPositionActuatorCfg(
  target_names_expr=(
    ".*thigh_.*",
  ),
  stiffness=20.0,
  damping=1.0,
  effort_limit=23.5,
  armature=0.01,
)
GO2_ACTUATOR_CALF = BuiltinPositionActuatorCfg(
  target_names_expr=(
    ".*calf_.*",
  ),
  stiffness=40.0,
  damping=2.0,
  effort_limit=45,
  armature=0.02,
)

GO2_JOINT_NAMES = (
  "FL_hip_joint",
  "FR_hip_joint",
  "RL_hip_joint",
  "RR_hip_joint",
  "FL_thigh_joint",
  "FR_thigh_joint",
  "RL_thigh_joint",
  "RR_thigh_joint",
  "FL_calf_joint",
  "FR_calf_joint",
  "RL_calf_joint",
  "RR_calf_joint",
)

GO2_FR_FAILED_JOINT_NAMES = (
  "FR_hip_joint",
  "FR_thigh_joint",
  "FR_calf_joint",
)
GO2_FR_LOCK_HALF_RANGE_RAD = 0.001

GO2_DEFAULT_JOINT_POS = {
  "FL_hip_joint": -0.1,
  "FR_hip_joint": 0.1,
  "RL_hip_joint": -0.1,
  "RR_hip_joint": 0.1,
  "FL_thigh_joint": 0.9,
  "FR_thigh_joint": 0.9,
  "RL_thigh_joint": 0.9,
  "RR_thigh_joint": 0.9,
  "FL_calf_joint": -1.8,
  "FR_calf_joint": -1.8,
  "RL_calf_joint": -1.8,
  "RR_calf_joint": -1.8,
}

GO2_FR_TRIPOD_JOINT_POS = {
  "FL_hip_joint": -0.245,
  "FL_thigh_joint": 0.559,
  "FL_calf_joint": -1.760,
  "FR_hip_joint": 0.155,
  "FR_thigh_joint": 1.167,
  "FR_calf_joint": -2.334,
  "RL_hip_joint": -0.245,
  "RL_thigh_joint": 0.559,
  "RL_calf_joint": -1.760,
  "RR_hip_joint": -0.042,
  "RR_thigh_joint": 0.522,
  "RR_calf_joint": -1.643,
}
GO2_FR_TUCKED_JOINT_POS = {
  "FR_hip_joint": GO2_FR_TRIPOD_JOINT_POS["FR_hip_joint"],
  "FR_thigh_joint": GO2_FR_TRIPOD_JOINT_POS["FR_thigh_joint"],
  "FR_calf_joint": GO2_FR_TRIPOD_JOINT_POS["FR_calf_joint"],
}

GO2_DEFAULT_JOINT_POS_TUPLE = tuple(
  GO2_DEFAULT_JOINT_POS[name] for name in GO2_JOINT_NAMES
)
GO2_FR_TRIPOD_JOINT_POS_TUPLE = tuple(
  GO2_FR_TRIPOD_JOINT_POS[name] for name in GO2_JOINT_NAMES
)


def get_fr_locked_tucked_spec() -> mujoco.MjSpec:
  """Get Go2 MJCF with the failed FR leg mechanically locked in a tucked pose."""
  spec = get_spec()
  for joint in spec.joints:
    if joint.name in GO2_FR_TUCKED_JOINT_POS:
      target = GO2_FR_TUCKED_JOINT_POS[joint.name]
      joint.range = (
        target - GO2_FR_LOCK_HALF_RANGE_RAD,
        target + GO2_FR_LOCK_HALF_RANGE_RAD,
      )
  return spec


def _go2_joint_actuator_cfg(joint_name: str) -> BuiltinPositionActuatorCfg:
  if "calf" in joint_name:
    stiffness = 40.0
    damping = 2.0
    effort_limit = 45.0
    armature = 0.02
  else:
    stiffness = 20.0
    damping = 1.0
    effort_limit = 23.5
    armature = 0.01

  if joint_name in GO2_FR_FAILED_JOINT_NAMES:
    stiffness = 0.0
    damping = 0.0
    effort_limit = None

  return BuiltinPositionActuatorCfg(
    target_names_expr=(joint_name,),
    stiffness=stiffness,
    damping=damping,
    effort_limit=effort_limit,
    armature=armature,
  )


GO2_FR_FAILURE_ARTICULATION = EntityArticulationInfoCfg(
  actuators=tuple(_go2_joint_actuator_cfg(name) for name in GO2_JOINT_NAMES),
  soft_joint_pos_limit_factor=0.9,
)

##
# Keyframes.
##


INIT_STATE = EntityCfg.InitialStateCfg(
  pos=(0.0, 0.0, 0.295),
  joint_pos=GO2_DEFAULT_JOINT_POS,
  joint_vel={".*": 0.0},
)

FR_TRIPOD_INIT_STATE = EntityCfg.InitialStateCfg(
  pos=(0.0, 0.0, 0.295),
  joint_pos=GO2_FR_TRIPOD_JOINT_POS,
  joint_vel={".*": 0.0},
)

##
# Collision config.
##

_foot_regex = "^[FR][LR]_foot_collision$"

# This disables all collisions except the feet.
# Furthermore, feet self collisions are disabled.
FEET_ONLY_COLLISION = CollisionCfg(
  geom_names_expr=(_foot_regex,),
  contype=0,
  conaffinity=1,
  condim=3,
  priority=1,
  friction=(0.6,),
  solimp=(0.9, 0.95, 0.023),
)

# This enables all collisions, excluding self collisions.
# Foot collisions are given custom condim, friction and solimp.
FULL_COLLISION = CollisionCfg(
  geom_names_expr=(".*_collision",),
  condim={_foot_regex: 3, ".*_collision": 1},
  priority={_foot_regex: 1},
  friction={_foot_regex: (0.6,)},
  solimp={_foot_regex: (0.9, 0.95, 0.023)},
  contype=1,
  conaffinity=0,
)

##
# Final config.
##

GO2_ARTICULATION = EntityArticulationInfoCfg(
  actuators=(
    GO2_ACTUATOR_HIP,
    GO2_ACTUATOR_THIGH,
    GO2_ACTUATOR_CALF,
  ),
  soft_joint_pos_limit_factor=0.9,
)


def get_go2_robot_cfg() -> EntityCfg:
  """Get a fresh Go2 robot configuration instance.

  Returns a new EntityCfg instance each time to avoid mutation issues when
  the config is shared across multiple places.
  """
  return EntityCfg(
    init_state=INIT_STATE,
    collisions=(FULL_COLLISION,),
    spec_fn=get_spec,
    articulation=GO2_ARTICULATION,
  )


def get_go2_fr_failure_robot_cfg(
  init_pose: Literal["default", "tripod"] = "default",
) -> EntityCfg:
  """Get a Go2 robot config with the entire FR leg torque-limited to zero."""
  init_state = FR_TRIPOD_INIT_STATE if init_pose == "tripod" else INIT_STATE
  return EntityCfg(
    init_state=init_state,
    collisions=(FULL_COLLISION,),
    spec_fn=get_spec,
    articulation=GO2_FR_FAILURE_ARTICULATION,
  )


def get_go2_fr_locked_tucked_robot_cfg() -> EntityCfg:
  """Get Go2 with zero FR actuator torque and mechanically locked FR joints."""
  return EntityCfg(
    init_state=FR_TRIPOD_INIT_STATE,
    collisions=(FULL_COLLISION,),
    spec_fn=get_fr_locked_tucked_spec,
    articulation=GO2_FR_FAILURE_ARTICULATION,
  )

if __name__ == "__main__":
  import mujoco.viewer as viewer

  from mjlab.entity.entity import Entity

  robot = Entity(get_go2_robot_cfg())

  viewer.launch(robot.spec.compile())
