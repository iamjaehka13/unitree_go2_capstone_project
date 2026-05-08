"""Render a FR-failure policy with clean tripod presentation overlay."""

from __future__ import annotations

import argparse
import contextlib
import io
import math
import os
import sys
from dataclasses import asdict
from pathlib import Path

import cv2
import imageio.v2 as imageio
import numpy as np
import torch

from tripod_eval_utils import support_geometry_ok, support_triangle_metrics


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUTPUT_DIR = REPO_ROOT / "project" / "videos" / "clean_tripod"
FOOT_NAMES = ("FL", "FR", "RL", "RR")
SUPPORT_FEET = ("FL", "RR", "RL")
DISABLED_FOOT = "FR"


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--task", required=True)
  parser.add_argument("--checkpoint", type=Path, required=True)
  parser.add_argument("--policy-id", required=True)
  parser.add_argument("--eval-init", required=True)
  parser.add_argument("--output", type=Path)
  parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
  parser.add_argument("--name-prefix", default="clean_tripod")
  parser.add_argument("--duration-s", type=float, default=8.0)
  parser.add_argument("--seed", type=int, default=0)
  parser.add_argument("--device", default="cpu")
  parser.add_argument("--width", type=int, default=1280)
  parser.add_argument("--height", type=int, default=720)
  parser.add_argument("--camera-distance", type=float, default=1.55)
  parser.add_argument("--camera-elevation", type=float, default=-18.0)
  parser.add_argument("--camera-azimuth", type=float, default=135.0)
  parser.add_argument("--max-roll-pitch-deg", type=float, default=10.0)
  parser.add_argument("--min-base-height-m", type=float, default=0.23)
  parser.add_argument("--max-base-height-m", type=float, default=0.45)
  parser.add_argument("--min-disabled-foot-height-m", type=float, default=0.045)
  parser.add_argument("--min-support-foot-force-n", type=float, default=15.0)
  parser.add_argument("--min-support-area-m2", type=float, default=0.04)
  parser.add_argument("--min-support-foot-distance-m", type=float, default=0.22)
  parser.add_argument("--min-com-support-margin-m", type=float, default=0.0)
  parser.add_argument("--quiet", action="store_true")
  return parser.parse_args()


def foot_index(name: str) -> int:
  return FOOT_NAMES.index(name)


def quat_to_roll_pitch(q: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
  w, x, y, z = q.unbind(dim=-1)
  roll = torch.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
  sin_pitch = torch.clamp(2.0 * (w * y - z * x), -1.0, 1.0)
  pitch = torch.asin(sin_pitch)
  return roll, pitch


def draw_text(
  frame: np.ndarray,
  text: str,
  org: tuple[int, int],
  scale: float = 0.62,
  color: tuple[int, int, int] = (255, 255, 255),
) -> None:
  cv2.putText(frame, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 4, cv2.LINE_AA)
  cv2.putText(frame, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2, cv2.LINE_AA)


def draw_chip(
  frame: np.ndarray,
  label: str,
  value: str,
  ok: bool,
  x: int,
  y: int,
  width: int,
) -> None:
  color = (48, 190, 105) if ok else (225, 80, 70)
  cv2.rectangle(frame, (x, y), (x + width, y + 32), (24, 28, 34), -1, cv2.LINE_AA)
  cv2.rectangle(frame, (x, y), (x + 6, y + 32), color, -1, cv2.LINE_AA)
  draw_text(frame, f"{label}: {value}", (x + 14, y + 23), 0.48, color)


def metrics_snapshot(
  env,
  foot_site_ids: list[int],
  support_indices: torch.Tensor,
  max_tilt_rad: float,
  args: argparse.Namespace,
) -> dict[str, float | bool]:
  unwrapped = env.unwrapped
  robot = unwrapped.scene["robot"]
  roll, pitch = quat_to_roll_pitch(robot.data.root_link_quat_w)
  foot_pos_w = robot.data.site_pos_w[:, foot_site_ids, :]
  support_area, min_support_foot_distance, com_margin = support_triangle_metrics(
    foot_pos_w,
    robot.data.root_link_pos_w[:, :2],
    support_indices,
  )

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

  try:
    nonfoot_sensor = unwrapped.scene["nonfoot_ground_touch"]
  except KeyError:
    nonfoot_contact = torch.zeros(1, dtype=torch.bool, device=unwrapped.device)
  else:
    if nonfoot_sensor.data.found is None:
      nonfoot_contact = torch.zeros(1, dtype=torch.bool, device=unwrapped.device)
    else:
      nonfoot_found = nonfoot_sensor.data.found > 0
      nonfoot_contact = torch.any(nonfoot_found.reshape(1, -1), dim=1)

  disabled_idx = foot_index(DISABLED_FOOT)
  disabled_height = foot_pos_w[:, disabled_idx, 2]
  support_contact_ok = torch.all(foot_contact[:, support_indices], dim=1)
  support_min_force = torch.min(foot_force_norm[:, support_indices], dim=1)[0]
  support_load_ok = support_min_force >= args.min_support_foot_force_n
  disabled_clearance_ok = disabled_height >= args.min_disabled_foot_height_m
  posture_ok = (
    (torch.abs(roll) <= max_tilt_rad)
    & (torch.abs(pitch) <= max_tilt_rad)
    & (robot.data.root_link_pos_w[:, 2] >= args.min_base_height_m)
    & (robot.data.root_link_pos_w[:, 2] <= args.max_base_height_m)
  )
  geometry_ok = support_geometry_ok(
    support_area,
    min_support_foot_distance,
    com_margin,
    min_area=args.min_support_area_m2,
    min_distance=args.min_support_foot_distance_m,
    min_com_margin=args.min_com_support_margin_m,
  )
  clean_ok = (
    posture_ok
    & support_contact_ok
    & support_load_ok
    & disabled_clearance_ok
    & geometry_ok
    & (~nonfoot_contact)
  )

  return {
    "clean_ok": bool(clean_ok[0].item()),
    "posture_ok": bool(posture_ok[0].item()),
    "support_contact_ok": bool(support_contact_ok[0].item()),
    "support_load_ok": bool(support_load_ok[0].item()),
    "disabled_clearance_ok": bool(disabled_clearance_ok[0].item()),
    "nonfoot_ok": not bool(nonfoot_contact[0].item()),
    "geometry_ok": bool(geometry_ok[0].item()),
    "base_height": float(robot.data.root_link_pos_w[0, 2].item()),
    "roll_deg": math.degrees(float(roll[0].item())),
    "pitch_deg": math.degrees(float(pitch[0].item())),
    "disabled_height": float(disabled_height[0].item()),
    "support_min_force": float(support_min_force[0].item()),
    "support_area": float(support_area[0].item()),
    "min_support_foot_distance": float(min_support_foot_distance[0].item()),
    "com_margin": float(com_margin[0].item()),
    "fr_force": float(foot_force_norm[0, foot_index("FR")].item()),
    "fl_force": float(foot_force_norm[0, foot_index("FL")].item()),
    "rr_force": float(foot_force_norm[0, foot_index("RR")].item()),
    "rl_force": float(foot_force_norm[0, foot_index("RL")].item()),
  }


def draw_overlay(
  frame_rgb: np.ndarray,
  policy_id: str,
  eval_init: str,
  time_s: float,
  metrics: dict[str, float | bool],
) -> np.ndarray:
  frame = np.ascontiguousarray(frame_rgb.copy())
  height, width = frame.shape[:2]
  clean_ok = bool(metrics["clean_ok"])
  status_color = (48, 210, 115) if clean_ok else (235, 95, 85)
  status_text = "CLEAN TRIPOD" if clean_ok else "NOT CLEAN"

  draw_text(frame, f"{policy_id} policy | eval init: {eval_init}", (26, 38), 0.72)
  draw_text(frame, f"t = {time_s:0.2f}s", (26, 70), 0.62)
  status_org = (width - 300, 46) if width >= 900 else (26, 106)
  draw_text(frame, status_text, status_org, 0.82, status_color)

  draw_chip(
    frame,
    "FR foot raised",
    f"{metrics['disabled_height']:.3f} m",
    bool(metrics["disabled_clearance_ok"]),
    26,
    height - 188,
    260,
  )
  draw_chip(
    frame,
    "FL/RL/RR foot contact",
    "all three feet",
    bool(metrics["support_contact_ok"]),
    26,
    height - 150,
    260,
  )
  draw_chip(
    frame,
    "support load",
    f"min {metrics['support_min_force']:.1f} N",
    bool(metrics["support_load_ok"]),
    26,
    height - 112,
    260,
  )
  draw_chip(
    frame,
    "calf/body contact",
    "none" if bool(metrics["nonfoot_ok"]) else "detected",
    bool(metrics["nonfoot_ok"]),
    26,
    height - 74,
    260,
  )

  right_x = width - 336
  draw_chip(
    frame,
    "support triangle",
    f"{metrics['support_area']:.3f} m2",
    bool(metrics["geometry_ok"]),
    right_x,
    height - 150,
    310,
  )
  draw_chip(
    frame,
    "COM margin",
    f"{metrics['com_margin']:.3f} m",
    bool(metrics["geometry_ok"]),
    right_x,
    height - 112,
    310,
  )
  draw_chip(
    frame,
    "body posture",
    f"roll {metrics['roll_deg']:.1f}, pitch {metrics['pitch_deg']:.1f}",
    bool(metrics["posture_ok"]),
    right_x,
    height - 74,
    310,
  )

  draw_text(
    frame,
    f"foot forces  FL {metrics['fl_force']:.0f}N | RL {metrics['rl_force']:.0f}N | RR {metrics['rr_force']:.0f}N | FR {metrics['fr_force']:.0f}N",
    (26, height - 24),
    0.52,
  )
  return frame


def main() -> None:
  args = parse_args()
  checkpoint = args.checkpoint.resolve()
  if not checkpoint.exists():
    raise FileNotFoundError(f"Checkpoint not found: {checkpoint}")

  if "MUJOCO_GL" not in os.environ and not (
    os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
  ):
    os.environ["MUJOCO_GL"] = "egl"

  import mjlab.tasks  # noqa: F401
  import src.tasks  # noqa: F401
  from mjlab.envs import ManagerBasedRlEnv
  from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
  from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls

  env_cfg = load_env_cfg(args.task)
  env_cfg.scene.num_envs = 1
  env_cfg.seed = args.seed
  env_cfg.episode_length_s = max(args.duration_s, 1.0)
  env_cfg.viewer.width = args.width
  env_cfg.viewer.height = args.height
  env_cfg.viewer.distance = args.camera_distance
  env_cfg.viewer.elevation = args.camera_elevation
  env_cfg.viewer.azimuth = args.camera_azimuth

  agent_cfg = load_rl_cfg(args.task)
  stdout_ctx = contextlib.redirect_stdout(io.StringIO()) if args.quiet else contextlib.nullcontext()
  with stdout_ctx:
    base_env = ManagerBasedRlEnv(cfg=env_cfg, device=args.device, render_mode="rgb_array")
    env = RslRlVecEnvWrapper(base_env, clip_actions=agent_cfg.clip_actions)
    runner_cls = load_runner_cls(args.task) or MjlabOnPolicyRunner
    runner = runner_cls(env, asdict(agent_cfg), log_dir=None, device=args.device)
    runner.load(
      str(checkpoint),
      load_cfg={"actor": True},
      strict=True,
      map_location=args.device,
    )
    policy = runner.get_inference_policy(device=args.device)

  unwrapped = env.unwrapped
  robot = unwrapped.scene["robot"]
  foot_site_ids, foot_site_names = robot.find_sites(FOOT_NAMES, preserve_order=True)
  if tuple(foot_site_names) != FOOT_NAMES:
    raise RuntimeError(f"Unexpected foot site order: {foot_site_names}")
  support_indices = torch.tensor(
    [foot_index(name) for name in SUPPORT_FEET],
    dtype=torch.long,
    device=args.device,
  )
  max_tilt_rad = math.radians(args.max_roll_pitch_deg)
  obs = env.get_observations().to(args.device)
  step_dt = unwrapped.step_dt
  steps = max(1, round(args.duration_s / step_dt))
  frames: list[np.ndarray] = []

  eval_stdout_ctx = contextlib.redirect_stdout(io.StringIO()) if args.quiet else contextlib.nullcontext()
  with eval_stdout_ctx:
    for step in range(steps):
      with torch.inference_mode():
        action = policy(obs)
      obs, _reward, _dones, _extras = env.step(action)
      obs = obs.to(args.device)
      frame = base_env.render()
      if frame is None:
        continue
      if frame.ndim == 4:
        frame = frame[0]
      if frame.dtype != np.uint8:
        frame = (np.clip(frame, 0.0, 1.0) * 255).astype(np.uint8)
      metrics = metrics_snapshot(env, foot_site_ids, support_indices, max_tilt_rad, args)
      frames.append(draw_overlay(frame, args.policy_id, args.eval_init, step * step_dt, metrics))

    env.close()

  if not frames:
    raise RuntimeError("No video frames were rendered.")

  output = args.output
  if output is None:
    output = args.output_dir / f"{args.name_prefix}_{args.policy_id}_{args.eval_init}.mp4"
  output.parent.mkdir(parents=True, exist_ok=True)
  fps = round(1.0 / step_dt)
  imageio.mimwrite(output, frames, fps=fps)
  print(f"[INFO] Saved clean tripod video: {output} | policy={args.policy_id}")


if __name__ == "__main__":
  main()
