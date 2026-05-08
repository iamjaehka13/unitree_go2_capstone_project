"""Evaluate a trained checkpoint on the no-push standing task."""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import math
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import torch

from tripod_eval_utils import support_geometry_ok, support_triangle_metrics


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUTPUT = REPO_ROOT / "project" / "results" / "no_push_eval" / "no_push_eval.csv"
# ContactSensor resolves Go2 foot geoms in MuJoCo model order.
FOOT_NAMES = ("FL", "FR", "RL", "RR")


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--task", required=True, help="Registered mjlab task id.")
  parser.add_argument("--checkpoint", type=Path, required=True)
  parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
  parser.add_argument("--episodes", type=int, default=20)
  parser.add_argument("--num-envs", type=int, default=20)
  parser.add_argument("--seed", type=int, default=0)
  parser.add_argument("--device", default="cpu")
  parser.add_argument("--episode-length-s", type=float, default=10.0)
  parser.add_argument("--initial-failure-s", type=float, default=2.0)
  parser.add_argument("--strict-window-s", type=float, default=2.0)
  parser.add_argument("--max-stable-roll-pitch-deg", type=float, default=10.0)
  parser.add_argument("--min-stable-base-height-m", type=float, default=0.23)
  parser.add_argument("--max-stable-base-height-m", type=float, default=0.45)
  parser.add_argument("--max-stable-ang-vel-rad-s", type=float, default=1.0)
  parser.add_argument("--min-contact-fraction", type=float, default=0.95)
  parser.add_argument("--max-disabled-foot-contact-fraction", type=float, default=0.20)
  parser.add_argument("--max-nonfoot-contact-fraction", type=float, default=0.0)
  parser.add_argument("--min-disabled-foot-height-m", type=float, default=0.045)
  parser.add_argument("--min-support-foot-force-n", type=float, default=15.0)
  parser.add_argument("--min-support-area-m2", type=float, default=0.04)
  parser.add_argument("--min-support-foot-distance-m", type=float, default=0.22)
  parser.add_argument("--min-com-support-margin-m", type=float, default=0.0)
  parser.add_argument("--append", action="store_true")
  parser.add_argument("--quiet", action="store_true")
  return parser.parse_args()


def quat_to_roll_pitch(q: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
  """Convert wxyz quaternions to roll and pitch in radians."""
  w, x, y, z = q.unbind(dim=-1)
  roll = torch.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
  sin_pitch = torch.clamp(2.0 * (w * y - z * x), -1.0, 1.0)
  pitch = torch.asin(sin_pitch)
  return roll, pitch


def checkpoint_iteration(path: Path) -> str:
  stem = path.stem
  if stem.startswith("model_"):
    return stem.removeprefix("model_")
  return stem


def termination_reason(env: Any, env_idx: int, timeout: bool, terminated: bool) -> str:
  if timeout and not terminated:
    return "time_out"
  for name in env.termination_manager.active_terms:
    if bool(env.termination_manager.get_term(name)[env_idx].item()):
      return name
  if terminated:
    return "terminated"
  if timeout:
    return "time_out"
  return "unknown"


def required_contact_feet(task: str) -> tuple[tuple[str, ...], str | None]:
  if "FR-Failure" in task:
    return ("FL", "RR", "RL"), "FR"
  return FOOT_NAMES, None


def foot_index(name: str) -> int:
  return FOOT_NAMES.index(name)


def fraction_pass(value: float, threshold: float) -> bool:
  return value + 1.0e-6 >= threshold


def write_rows(path: Path, rows: list[dict[str, Any]], append: bool) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  fieldnames = [
    "task",
    "checkpoint",
    "checkpoint_iteration",
    "seed",
    "episode",
    "success",
    "survival_success",
    "strict_success",
    "tripod_success",
    "tripod_contact_success",
    "kinematic_tripod_success",
    "posture_success",
    "support_contact_success",
    "support_load_success",
    "support_geometry_success",
    "disabled_clearance_success",
    "nonfoot_contact_success",
    "initial_failure",
    "survival_time_s",
    "termination_reason",
    "final_base_height_m",
    "final_roll_deg",
    "final_pitch_deg",
    "final_base_ang_vel_norm_rad_s",
    "max_roll_deg",
    "max_pitch_deg",
    "last_window_posture_fraction",
    "last_window_support_contact_fraction",
    "last_window_support_load_fraction",
    "last_window_support_geometry_fraction",
    "last_window_disabled_contact_fraction",
    "last_window_disabled_clearance_fraction",
    "last_window_disabled_foot_height_mean_m",
    "last_window_nonfoot_contact_fraction",
    "last_window_support_min_force_mean_n",
    "last_window_support_area_mean_m2",
    "last_window_min_support_foot_distance_mean_m",
    "last_window_com_margin_mean_m",
    "fr_contact_fraction",
    "fl_contact_fraction",
    "rr_contact_fraction",
    "rl_contact_fraction",
    "fr_force_mean_n",
    "fl_force_mean_n",
    "rr_force_mean_n",
    "rl_force_mean_n",
    "mean_torque_norm",
    "mean_action_norm",
  ]
  mode = "a" if append and path.exists() else "w"
  with path.open(mode, newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    if mode == "w":
      writer.writeheader()
    writer.writerows(rows)


def main() -> None:
  args = parse_args()
  checkpoint = args.checkpoint.resolve()
  if not checkpoint.exists():
    raise FileNotFoundError(f"Checkpoint not found: {checkpoint}")

  import mjlab.tasks  # noqa: F401
  import src.tasks  # noqa: F401
  from mjlab.envs import ManagerBasedRlEnv
  from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
  from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls

  env_cfg = load_env_cfg(args.task)
  env_cfg.scene.num_envs = args.num_envs
  env_cfg.seed = args.seed
  env_cfg.episode_length_s = args.episode_length_s

  agent_cfg = load_rl_cfg(args.task)
  device = args.device
  max_stable_tilt_rad = math.radians(args.max_stable_roll_pitch_deg)
  required_feet, disabled_foot = required_contact_feet(args.task)
  required_foot_indices = torch.tensor(
    [foot_index(name) for name in required_feet], dtype=torch.long, device=device
  )
  disabled_foot_index = foot_index(disabled_foot) if disabled_foot is not None else None

  stdout_ctx = contextlib.redirect_stdout(io.StringIO()) if args.quiet else contextlib.nullcontext()
  with stdout_ctx:
    base_env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
    env = RslRlVecEnvWrapper(base_env, clip_actions=agent_cfg.clip_actions)
    runner_cls = load_runner_cls(args.task) or MjlabOnPolicyRunner
    runner = runner_cls(env, asdict(agent_cfg), log_dir=None, device=device)
    runner.load(
      str(checkpoint),
      load_cfg={"actor": True},
      strict=True,
      map_location=device,
    )
    policy = runner.get_inference_policy(device=device)

  unwrapped = env.unwrapped
  robot = unwrapped.scene["robot"]
  foot_site_ids, foot_site_names = robot.find_sites(FOOT_NAMES, preserve_order=True)
  if tuple(foot_site_names) != FOOT_NAMES:
    raise RuntimeError(f"Unexpected foot site order: {foot_site_names}")
  obs = env.get_observations().to(device)
  num_envs = env.num_envs
  step_dt = unwrapped.step_dt
  steps_since_reset = torch.zeros(num_envs, dtype=torch.long, device=unwrapped.device)
  max_roll = torch.zeros(num_envs, dtype=torch.float32, device=unwrapped.device)
  max_pitch = torch.zeros_like(max_roll)
  torque_norm_sum = torch.zeros_like(max_roll)
  action_norm_sum = torch.zeros_like(max_roll)
  sample_count = torch.zeros(num_envs, dtype=torch.long, device=unwrapped.device)
  last_base_height = torch.zeros_like(max_roll)
  last_roll = torch.zeros_like(max_roll)
  last_pitch = torch.zeros_like(max_roll)
  last_base_ang_vel_norm = torch.zeros_like(max_roll)
  window_sample_count = torch.zeros(num_envs, dtype=torch.long, device=unwrapped.device)
  window_posture_ok_count = torch.zeros_like(window_sample_count)
  window_support_contact_ok_count = torch.zeros_like(window_sample_count)
  window_support_load_ok_count = torch.zeros_like(window_sample_count)
  window_support_geometry_ok_count = torch.zeros_like(window_sample_count)
  window_disabled_contact_count = torch.zeros_like(window_sample_count)
  window_disabled_clearance_ok_count = torch.zeros_like(window_sample_count)
  window_nonfoot_contact_count = torch.zeros_like(window_sample_count)
  window_disabled_foot_height_sum = torch.zeros(num_envs, dtype=torch.float32, device=unwrapped.device)
  window_support_min_force_sum = torch.zeros(num_envs, dtype=torch.float32, device=unwrapped.device)
  window_support_area_sum = torch.zeros(num_envs, dtype=torch.float32, device=unwrapped.device)
  window_min_support_foot_distance_sum = torch.zeros_like(window_support_area_sum)
  window_com_margin_sum = torch.zeros_like(window_support_area_sum)
  foot_contact_count = torch.zeros((num_envs, len(FOOT_NAMES)), dtype=torch.long, device=unwrapped.device)
  foot_force_sum = torch.zeros((num_envs, len(FOOT_NAMES)), dtype=torch.float32, device=unwrapped.device)
  try:
    nonfoot_sensor = unwrapped.scene["nonfoot_ground_touch"]
  except KeyError:
    nonfoot_sensor = None

  rows: list[dict[str, Any]] = []
  episode_id = 0
  eval_stdout_ctx = contextlib.redirect_stdout(io.StringIO()) if args.quiet else contextlib.nullcontext()
  with eval_stdout_ctx:
    while len(rows) < args.episodes:
      robot = unwrapped.scene["robot"]
      roll, pitch = quat_to_roll_pitch(robot.data.root_link_quat_w)
      foot_pos_w = robot.data.site_pos_w[:, foot_site_ids, :]
      support_area, min_support_foot_distance, com_margin = support_triangle_metrics(
        foot_pos_w,
        robot.data.root_link_pos_w[:, :2],
        required_foot_indices,
      )
      base_height = robot.data.root_link_pos_w[:, 2].clone()
      base_ang_vel_norm = torch.linalg.norm(robot.data.root_link_ang_vel_b, dim=1)
      contact_sensor = unwrapped.scene["feet_ground_contact"]
      assert contact_sensor.data.found is not None
      foot_contact = contact_sensor.data.found > 0
      if foot_contact.dim() == 3:
        foot_contact = foot_contact.squeeze(-1)
      foot_contact = foot_contact[:, : len(FOOT_NAMES)]
      if contact_sensor.data.force is not None:
        foot_force = contact_sensor.data.force
        if foot_force.dim() == 4:
          foot_force = foot_force.squeeze(2)
        foot_force_norm = torch.linalg.norm(foot_force[:, : len(FOOT_NAMES)], dim=-1)
      else:
        foot_force_norm = torch.zeros_like(foot_contact, dtype=torch.float32)
      nonfoot_contact = torch.zeros(num_envs, dtype=torch.bool, device=unwrapped.device)
      if nonfoot_sensor is not None and nonfoot_sensor.data.found is not None:
        nonfoot_found = nonfoot_sensor.data.found > 0
        nonfoot_contact = torch.any(nonfoot_found.reshape(num_envs, -1), dim=1)

      max_roll = torch.maximum(max_roll, torch.abs(roll))
      max_pitch = torch.maximum(max_pitch, torch.abs(pitch))
      last_base_height = base_height
      last_roll = roll
      last_pitch = pitch
      last_base_ang_vel_norm = base_ang_vel_norm
      torque_norm_sum += torch.linalg.norm(robot.data.actuator_force, dim=1)
      foot_contact_count += foot_contact.long()
      foot_force_sum += foot_force_norm
      sample_count += 1

      elapsed_time = steps_since_reset.float() * step_dt
      in_strict_window = elapsed_time >= max(args.episode_length_s - args.strict_window_s, 0.0)
      posture_ok = (
        (torch.abs(roll) <= max_stable_tilt_rad)
        & (torch.abs(pitch) <= max_stable_tilt_rad)
        & (base_height >= args.min_stable_base_height_m)
        & (base_height <= args.max_stable_base_height_m)
        & (base_ang_vel_norm <= args.max_stable_ang_vel_rad_s)
      )
      support_contact_ok = torch.all(foot_contact[:, required_foot_indices], dim=1)
      support_min_force = torch.min(foot_force_norm[:, required_foot_indices], dim=1)[0]
      support_load_ok = support_min_force >= args.min_support_foot_force_n
      disabled_foot_height = torch.zeros(num_envs, dtype=torch.float32, device=unwrapped.device)
      disabled_clearance_ok = torch.ones(num_envs, dtype=torch.bool, device=unwrapped.device)
      if disabled_foot_index is not None:
        disabled_foot_height = foot_pos_w[:, disabled_foot_index, 2]
        disabled_clearance_ok = disabled_foot_height >= args.min_disabled_foot_height_m
      support_geometry_is_ok = support_geometry_ok(
        support_area,
        min_support_foot_distance,
        com_margin,
        min_area=args.min_support_area_m2,
        min_distance=args.min_support_foot_distance_m,
        min_com_margin=args.min_com_support_margin_m,
      )
      if torch.any(in_strict_window):
        window_sample_count[in_strict_window] += 1
        window_posture_ok_count[in_strict_window] += posture_ok[in_strict_window].long()
        window_support_contact_ok_count[in_strict_window] += support_contact_ok[in_strict_window].long()
        window_support_load_ok_count[in_strict_window] += support_load_ok[in_strict_window].long()
        window_support_geometry_ok_count[in_strict_window] += support_geometry_is_ok[
          in_strict_window
        ].long()
        window_disabled_clearance_ok_count[in_strict_window] += disabled_clearance_ok[
          in_strict_window
        ].long()
        window_nonfoot_contact_count[in_strict_window] += nonfoot_contact[in_strict_window].long()
        window_disabled_foot_height_sum[in_strict_window] += disabled_foot_height[
          in_strict_window
        ]
        window_support_min_force_sum[in_strict_window] += support_min_force[
          in_strict_window
        ]
        window_support_area_sum[in_strict_window] += support_area[in_strict_window]
        window_min_support_foot_distance_sum[in_strict_window] += min_support_foot_distance[
          in_strict_window
        ]
        window_com_margin_sum[in_strict_window] += com_margin[in_strict_window]
        if disabled_foot_index is not None:
          disabled_contact = foot_contact[:, disabled_foot_index]
          window_disabled_contact_count[in_strict_window] += disabled_contact[in_strict_window].long()

      with torch.inference_mode():
        action = policy(obs)
      action_norm_sum += torch.linalg.norm(action.to(unwrapped.device), dim=1)

      obs, _reward, dones, _extras = env.step(action)
      obs = obs.to(device)
      steps_since_reset += 1

      done_ids = dones.nonzero(as_tuple=False).flatten()
      if len(done_ids) == 0:
        continue

      for done_id_tensor in done_ids:
        env_idx = int(done_id_tensor.item())
        if len(rows) >= args.episodes:
          break
        timeout = bool(unwrapped.reset_time_outs[env_idx].item())
        terminated = bool(unwrapped.reset_terminated[env_idx].item())
        survival_success = timeout and not terminated
        survival_time = float(steps_since_reset[env_idx].item() * step_dt)
        reason = termination_reason(unwrapped, env_idx, timeout, terminated)
        final_height = float(last_base_height[env_idx].item())
        denom = max(int(sample_count[env_idx].item()), 1)
        window_denom = max(int(window_sample_count[env_idx].item()), 1)
        posture_fraction = float((window_posture_ok_count[env_idx] / window_denom).item())
        support_contact_fraction = float((window_support_contact_ok_count[env_idx] / window_denom).item())
        support_load_fraction = float((window_support_load_ok_count[env_idx] / window_denom).item())
        support_geometry_fraction = float(
          (window_support_geometry_ok_count[env_idx] / window_denom).item()
        )
        disabled_clearance_fraction = float(
          (window_disabled_clearance_ok_count[env_idx] / window_denom).item()
        )
        disabled_contact_fraction = (
          float((window_disabled_contact_count[env_idx] / window_denom).item())
          if disabled_foot_index is not None
          else 0.0
        )
        nonfoot_contact_fraction = float((window_nonfoot_contact_count[env_idx] / window_denom).item())
        disabled_foot_height_mean = float(
          (window_disabled_foot_height_sum[env_idx] / window_denom).item()
        )
        support_min_force_mean = float(
          (window_support_min_force_sum[env_idx] / window_denom).item()
        )
        support_area_mean = float((window_support_area_sum[env_idx] / window_denom).item())
        min_support_foot_distance_mean = float(
          (window_min_support_foot_distance_sum[env_idx] / window_denom).item()
        )
        com_margin_mean = float((window_com_margin_sum[env_idx] / window_denom).item())
        posture_success = fraction_pass(posture_fraction, args.min_contact_fraction)
        support_contact_success = fraction_pass(support_contact_fraction, args.min_contact_fraction)
        support_load_success = fraction_pass(support_load_fraction, args.min_contact_fraction)
        support_geometry_success = fraction_pass(
          support_geometry_fraction, args.min_contact_fraction
        )
        disabled_clearance_success = (
          disabled_foot_index is None
          or fraction_pass(disabled_clearance_fraction, args.min_contact_fraction)
        )
        disabled_contact_ok = disabled_foot_index is None or (
          disabled_contact_fraction <= args.max_disabled_foot_contact_fraction + 1.0e-6
        )
        nonfoot_contact_success = (
          nonfoot_contact_fraction <= args.max_nonfoot_contact_fraction + 1.0e-6
        )
        tripod_contact_success = (
          survival_success
          and support_contact_success
          and support_load_success
          and disabled_contact_ok
          and disabled_clearance_success
          and nonfoot_contact_success
        )
        strict_success = (
          survival_success
          and posture_success
          and support_contact_success
          and nonfoot_contact_success
        )
        kinematic_tripod_success = survival_success and support_geometry_success
        tripod_success = strict_success and disabled_contact_ok and support_geometry_success
        tripod_success = (
          tripod_success and support_load_success and disabled_clearance_success
        )
        foot_contact_fraction = foot_contact_count[env_idx].float() / denom
        foot_force_mean = foot_force_sum[env_idx] / denom
        rows.append(
          {
            "task": args.task,
            "checkpoint": str(checkpoint.relative_to(REPO_ROOT)),
            "checkpoint_iteration": checkpoint_iteration(checkpoint),
            "seed": args.seed,
            "episode": episode_id,
            "success": int(survival_success),
            "survival_success": int(survival_success),
            "strict_success": int(strict_success),
            "tripod_success": int(tripod_success),
            "tripod_contact_success": int(tripod_contact_success),
            "kinematic_tripod_success": int(kinematic_tripod_success),
            "posture_success": int(posture_success),
            "support_contact_success": int(support_contact_success),
            "support_load_success": int(support_load_success),
            "support_geometry_success": int(support_geometry_success),
            "disabled_clearance_success": int(disabled_clearance_success),
            "nonfoot_contact_success": int(nonfoot_contact_success),
            "initial_failure": int((not survival_success) and survival_time <= args.initial_failure_s),
            "survival_time_s": survival_time,
            "termination_reason": reason,
            "final_base_height_m": final_height,
            "final_roll_deg": math.degrees(float(last_roll[env_idx].item())),
            "final_pitch_deg": math.degrees(float(last_pitch[env_idx].item())),
            "final_base_ang_vel_norm_rad_s": float(last_base_ang_vel_norm[env_idx].item()),
            "max_roll_deg": math.degrees(float(max_roll[env_idx].item())),
            "max_pitch_deg": math.degrees(float(max_pitch[env_idx].item())),
            "last_window_posture_fraction": posture_fraction,
            "last_window_support_contact_fraction": support_contact_fraction,
            "last_window_support_load_fraction": support_load_fraction,
            "last_window_support_geometry_fraction": support_geometry_fraction,
            "last_window_disabled_contact_fraction": disabled_contact_fraction,
            "last_window_disabled_clearance_fraction": disabled_clearance_fraction,
            "last_window_disabled_foot_height_mean_m": disabled_foot_height_mean,
            "last_window_nonfoot_contact_fraction": nonfoot_contact_fraction,
            "last_window_support_min_force_mean_n": support_min_force_mean,
            "last_window_support_area_mean_m2": support_area_mean,
            "last_window_min_support_foot_distance_mean_m": min_support_foot_distance_mean,
            "last_window_com_margin_mean_m": com_margin_mean,
            "fr_contact_fraction": float(foot_contact_fraction[foot_index("FR")].item()),
            "fl_contact_fraction": float(foot_contact_fraction[foot_index("FL")].item()),
            "rr_contact_fraction": float(foot_contact_fraction[foot_index("RR")].item()),
            "rl_contact_fraction": float(foot_contact_fraction[foot_index("RL")].item()),
            "fr_force_mean_n": float(foot_force_mean[foot_index("FR")].item()),
            "fl_force_mean_n": float(foot_force_mean[foot_index("FL")].item()),
            "rr_force_mean_n": float(foot_force_mean[foot_index("RR")].item()),
            "rl_force_mean_n": float(foot_force_mean[foot_index("RL")].item()),
            "mean_torque_norm": float((torque_norm_sum[env_idx] / denom).item()),
            "mean_action_norm": float((action_norm_sum[env_idx] / denom).item()),
          }
        )
        episode_id += 1

      for env_idx in done_ids:
        max_roll[env_idx] = 0.0
        max_pitch[env_idx] = 0.0
        torque_norm_sum[env_idx] = 0.0
        action_norm_sum[env_idx] = 0.0
        sample_count[env_idx] = 0
        window_sample_count[env_idx] = 0
        window_posture_ok_count[env_idx] = 0
        window_support_contact_ok_count[env_idx] = 0
        window_support_load_ok_count[env_idx] = 0
        window_support_geometry_ok_count[env_idx] = 0
        window_disabled_contact_count[env_idx] = 0
        window_disabled_clearance_ok_count[env_idx] = 0
        window_nonfoot_contact_count[env_idx] = 0
        window_disabled_foot_height_sum[env_idx] = 0.0
        window_support_min_force_sum[env_idx] = 0.0
        window_support_area_sum[env_idx] = 0.0
        window_min_support_foot_distance_sum[env_idx] = 0.0
        window_com_margin_sum[env_idx] = 0.0
        foot_contact_count[env_idx] = 0
        foot_force_sum[env_idx] = 0.0
        steps_since_reset[env_idx] = 0

  env.close()
  write_rows(args.output, rows, append=args.append)
  successes = sum(row["survival_success"] for row in rows)
  strict_successes = sum(row["strict_success"] for row in rows)
  tripod_successes = sum(row["tripod_success"] for row in rows)
  tripod_contact_successes = sum(row["tripod_contact_success"] for row in rows)
  kinematic_tripod_successes = sum(row["kinematic_tripod_success"] for row in rows)
  initial_failures = sum(row["initial_failure"] for row in rows)
  print(
    f"[INFO] Wrote {len(rows)} rows to {args.output} | "
    f"survival_success_rate={successes / len(rows):.3f}, "
    f"tripod_contact_success_rate={tripod_contact_successes / len(rows):.3f}, "
    f"kinematic_tripod_success_rate={kinematic_tripod_successes / len(rows):.3f}, "
    f"strict_success_rate={strict_successes / len(rows):.3f}, "
    f"tripod_success_rate={tripod_successes / len(rows):.3f}, "
    f"initial_failure_rate={initial_failures / len(rows):.3f}"
  )


if __name__ == "__main__":
  main()
