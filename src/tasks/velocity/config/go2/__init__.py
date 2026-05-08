from mjlab.tasks.registry import register_mjlab_task
from src.tasks.velocity.rl import VelocityOnPolicyRunner

from .env_cfgs import (
  unitree_go2_fr_failure_default_clean_stand_env_cfg,
  unitree_go2_fr_failure_default_stand_env_cfg,
  unitree_go2_fr_failure_default_strict_stand_env_cfg,
  unitree_go2_fr_failure_init_curriculum_clean_stand_env_cfg,
  unitree_go2_fr_failure_init_curriculum_stand_env_cfg,
  unitree_go2_fr_failure_init_curriculum_strict_stand_env_cfg,
  unitree_go2_fr_failure_locked_tucked_clean_stand_env_cfg,
  unitree_go2_fr_failure_tripod_clean_stand_env_cfg,
  unitree_go2_fr_failure_tripod_stand_env_cfg,
  unitree_go2_fr_failure_tripod_strict_stand_env_cfg,
  unitree_go2_flat_env_cfg,
  unitree_go2_rough_env_cfg,
  unitree_go2_stand_env_cfg,
)
from .rl_cfg import unitree_go2_ppo_runner_cfg

register_mjlab_task(
  task_id="Unitree-Go2-Rough",
  env_cfg=unitree_go2_rough_env_cfg(),
  play_env_cfg=unitree_go2_rough_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Unitree-Go2-Flat",
  env_cfg=unitree_go2_flat_env_cfg(),
  play_env_cfg=unitree_go2_flat_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Unitree-Go2-Stand",
  env_cfg=unitree_go2_stand_env_cfg(),
  play_env_cfg=unitree_go2_stand_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(experiment_name="go2_stand"),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Unitree-Go2-FR-Failure-Default-Stand",
  env_cfg=unitree_go2_fr_failure_default_stand_env_cfg(),
  play_env_cfg=unitree_go2_fr_failure_default_stand_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(
    experiment_name="go2_fr_failure_default_stand"
  ),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Unitree-Go2-FR-Failure-Tripod-Stand",
  env_cfg=unitree_go2_fr_failure_tripod_stand_env_cfg(),
  play_env_cfg=unitree_go2_fr_failure_tripod_stand_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(
    experiment_name="go2_fr_failure_tripod_stand"
  ),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Unitree-Go2-FR-Failure-Init-Curriculum-Stand",
  env_cfg=unitree_go2_fr_failure_init_curriculum_stand_env_cfg(),
  play_env_cfg=unitree_go2_fr_failure_init_curriculum_stand_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(
    experiment_name="go2_fr_failure_init_curriculum_stand"
  ),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Unitree-Go2-FR-Failure-Default-Strict-Stand",
  env_cfg=unitree_go2_fr_failure_default_strict_stand_env_cfg(),
  play_env_cfg=unitree_go2_fr_failure_default_strict_stand_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(
    experiment_name="go2_fr_failure_default_strict_stand"
  ),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Unitree-Go2-FR-Failure-Tripod-Strict-Stand",
  env_cfg=unitree_go2_fr_failure_tripod_strict_stand_env_cfg(),
  play_env_cfg=unitree_go2_fr_failure_tripod_strict_stand_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(
    experiment_name="go2_fr_failure_tripod_strict_stand"
  ),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Unitree-Go2-FR-Failure-Init-Curriculum-Strict-Stand",
  env_cfg=unitree_go2_fr_failure_init_curriculum_strict_stand_env_cfg(),
  play_env_cfg=unitree_go2_fr_failure_init_curriculum_strict_stand_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(
    experiment_name="go2_fr_failure_init_curriculum_strict_stand"
  ),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Unitree-Go2-FR-Failure-Default-Clean-Stand",
  env_cfg=unitree_go2_fr_failure_default_clean_stand_env_cfg(),
  play_env_cfg=unitree_go2_fr_failure_default_clean_stand_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(
    experiment_name="go2_fr_failure_default_clean_stand"
  ),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Unitree-Go2-FR-Failure-Tripod-Clean-Stand",
  env_cfg=unitree_go2_fr_failure_tripod_clean_stand_env_cfg(),
  play_env_cfg=unitree_go2_fr_failure_tripod_clean_stand_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(
    experiment_name="go2_fr_failure_tripod_clean_stand"
  ),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Unitree-Go2-FR-Failure-Locked-Tucked-Clean-Stand",
  env_cfg=unitree_go2_fr_failure_locked_tucked_clean_stand_env_cfg(),
  play_env_cfg=unitree_go2_fr_failure_locked_tucked_clean_stand_env_cfg(
    play=True
  ),
  rl_cfg=unitree_go2_ppo_runner_cfg(
    experiment_name="go2_fr_failure_locked_tucked_clean_stand"
  ),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Unitree-Go2-FR-Failure-Init-Curriculum-Clean-Stand",
  env_cfg=unitree_go2_fr_failure_init_curriculum_clean_stand_env_cfg(),
  play_env_cfg=unitree_go2_fr_failure_init_curriculum_clean_stand_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(
    experiment_name="go2_fr_failure_init_curriculum_clean_stand"
  ),
  runner_cls=VelocityOnPolicyRunner,
)
