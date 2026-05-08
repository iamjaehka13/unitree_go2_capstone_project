"""Render a policy rollout with an external-force push and PPT overlay."""

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

from render_clean_tripod_video import (
  FOOT_NAMES,
  SUPPORT_FEET,
  draw_chip as draw_clean_chip,
  foot_index,
  metrics_snapshot,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUTPUT_DIR = REPO_ROOT / "project" / "videos" / "push"
PUSH_DIRECTIONS = {
  "front": (1.0, 0.0, 0.0),
  "back": (-1.0, 0.0, 0.0),
  "left": (0.0, 1.0, 0.0),
  "right": (0.0, -1.0, 0.0),
}
SCREEN_DIRECTIONS = {
  "front": (0, -1),
  "back": (0, 1),
  "left": (-1, 0),
  "right": (1, 0),
}
PUSH_LEVELS = {
  "weak": 0.5,
  "medium": 1.0,
  "strong": 1.5,
}
BALL_STYLES = {
  "weak": ("tennis ball", (60, 220, 90), 22),
  "medium": ("soccer ball", (245, 245, 245), 28),
  "strong": ("bowling ball", (80, 80, 120), 34),
}


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--task", required=True)
  parser.add_argument("--checkpoint", type=Path, required=True)
  parser.add_argument("--policy-id", required=True)
  parser.add_argument("--eval-init", required=True)
  parser.add_argument("--output", type=Path)
  parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
  parser.add_argument("--name-prefix", default="push_policy")
  parser.add_argument("--duration-s", type=float, default=6.0)
  parser.add_argument("--seed", type=int, default=0)
  parser.add_argument("--device", default="cpu")
  parser.add_argument("--push-start-s", type=float, default=2.0)
  parser.add_argument("--push-duration-s", type=float, default=0.1)
  parser.add_argument("--push-direction", choices=sorted(PUSH_DIRECTIONS), required=True)
  parser.add_argument("--push-level", choices=sorted(PUSH_LEVELS), required=True)
  parser.add_argument("--force-multiplier-bw", type=float)
  parser.add_argument("--width", type=int, default=1280)
  parser.add_argument("--height", type=int, default=720)
  parser.add_argument("--camera-distance", type=float, default=1.8)
  parser.add_argument("--camera-elevation", type=float, default=-12.0)
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


def draw_text(
  frame: np.ndarray,
  text: str,
  org: tuple[int, int],
  scale: float = 0.65,
  color: tuple[int, int, int] = (255, 255, 255),
) -> None:
  cv2.putText(frame, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 4, cv2.LINE_AA)
  cv2.putText(frame, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2, cv2.LINE_AA)


def ball_position(
  width: int,
  height: int,
  direction: str,
  time_s: float,
  push_start_s: float,
  push_duration_s: float,
) -> tuple[int, int] | None:
  screen_dx, screen_dy = SCREEN_DIRECTIONS[direction]
  center = np.array([width * 0.52, height * 0.54], dtype=np.float32)
  start = center - np.array([screen_dx, screen_dy], dtype=np.float32) * width * 0.42
  if time_s < push_start_s - 0.8:
    return None
  if time_s <= push_start_s:
    alpha = (time_s - (push_start_s - 0.8)) / 0.8
    alpha = float(np.clip(alpha, 0.0, 1.0))
    pos = start * (1.0 - alpha) + center * alpha
    return int(pos[0]), int(pos[1])
  if time_s <= push_start_s + push_duration_s + 0.15:
    return int(center[0]), int(center[1])
  return None


def draw_overlay(
  frame_rgb: np.ndarray,
  policy_id: str,
  eval_init: str,
  direction: str,
  level: str,
  force_n: float,
  duration_s: float,
  time_s: float,
  push_start_s: float,
  push_duration_s: float,
  metrics: dict[str, float | bool] | None = None,
) -> np.ndarray:
  frame = np.ascontiguousarray(frame_rgb.copy())
  height, width = frame.shape[:2]
  active = push_start_s <= time_s < push_start_s + push_duration_s
  ball_name, color, radius = BALL_STYLES[level]

  draw_text(frame, f"{policy_id} policy | eval init: {eval_init}", (26, 38), 0.72)
  draw_text(frame, f"t = {time_s:0.2f}s", (26, 70), 0.66)
  draw_text(
    frame,
    f"{ball_name}: {direction}, {level}, {force_n:.0f} N, {duration_s:.2f}s",
    (26, 102),
    0.62,
  )
  draw_text(frame, "external force visualized as ghost ball", (26, height - 28), 0.55)

  screen_dx, screen_dy = SCREEN_DIRECTIONS[direction]
  center = (int(width * 0.52), int(height * 0.54))
  arrow_end = (center[0] + int(screen_dx * 120), center[1] + int(screen_dy * 120))
  arrow_color = (30, 220, 255) if active else (120, 120, 120)
  cv2.arrowedLine(frame, center, arrow_end, arrow_color, 8, cv2.LINE_AA, tipLength=0.28)
  if active:
    draw_text(frame, "PUSH ACTIVE", (width - 230, 44), 0.78)

  if metrics is not None:
    clean_ok = bool(metrics["clean_ok"])
    status_color = (48, 210, 115) if clean_ok else (235, 95, 85)
    status_text = "CLEAN TRIPOD" if clean_ok else "NOT CLEAN"
    draw_text(frame, status_text, (width - 300, 82), 0.68, status_color)
    draw_clean_chip(
      frame,
      "FR foot raised",
      f"{metrics['disabled_height']:.3f} m",
      bool(metrics["disabled_clearance_ok"]),
      26,
      height - 174,
      260,
    )
    draw_clean_chip(
      frame,
      "support load",
      f"min {metrics['support_min_force']:.1f} N",
      bool(metrics["support_load_ok"]),
      26,
      height - 136,
      260,
    )
    draw_clean_chip(
      frame,
      "calf/body contact",
      "none" if bool(metrics["nonfoot_ok"]) else "detected",
      bool(metrics["nonfoot_ok"]),
      26,
      height - 98,
      260,
    )
    draw_clean_chip(
      frame,
      "body posture",
      f"roll {metrics['roll_deg']:.1f}, pitch {metrics['pitch_deg']:.1f}",
      bool(metrics["posture_ok"]),
      26,
      height - 60,
      260,
    )

  pos = ball_position(width, height, direction, time_s, push_start_s, push_duration_s)
  if pos is not None:
    cv2.circle(frame, pos, radius + 3, (0, 0, 0), -1, cv2.LINE_AA)
    cv2.circle(frame, pos, radius, color, -1, cv2.LINE_AA)
    if level == "medium":
      cv2.circle(frame, pos, radius, (20, 20, 20), 2, cv2.LINE_AA)
      cv2.line(frame, (pos[0] - radius, pos[1]), (pos[0] + radius, pos[1]), (20, 20, 20), 2)
      cv2.line(frame, (pos[0], pos[1] - radius), (pos[0], pos[1] + radius), (20, 20, 20), 2)
    if level == "strong":
      cv2.circle(frame, (pos[0] - radius // 3, pos[1] - radius // 3), 4, (20, 20, 40), -1)
      cv2.circle(frame, (pos[0], pos[1] - radius // 4), 4, (20, 20, 40), -1)
      cv2.circle(frame, (pos[0] - radius // 5, pos[1]), 4, (20, 20, 40), -1)

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
  base_body_id = robot.body_names.index("base_link")
  total_mass = float(robot.data.model.body_mass[0, robot.data.indexing.body_ids].sum().item())
  body_weight_n = total_mass * 9.81
  force_multiplier = args.force_multiplier_bw
  if force_multiplier is None:
    force_multiplier = PUSH_LEVELS[args.push_level]
  force_n = body_weight_n * force_multiplier
  direction = torch.tensor(PUSH_DIRECTIONS[args.push_direction], device=args.device, dtype=torch.float32)
  force_vector = direction * force_n

  obs = env.get_observations().to(args.device)
  step_dt = unwrapped.step_dt
  steps = max(1, round(args.duration_s / step_dt))
  frames: list[np.ndarray] = []

  with contextlib.redirect_stdout(io.StringIO()) if args.quiet else contextlib.nullcontext():
    for step in range(steps):
      time_s = step * step_dt
      active = args.push_start_s <= time_s < args.push_start_s + args.push_duration_s
      forces = torch.zeros((1, 1, 3), device=unwrapped.device)
      torques = torch.zeros_like(forces)
      if active:
        forces[0, 0, :] = force_vector
      robot.write_external_wrench_to_sim(
        forces,
        torques,
        env_ids=torch.tensor([0], device=unwrapped.device),
        body_ids=[base_body_id],
      )
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
      frames.append(
        draw_overlay(
          frame,
          args.policy_id,
          args.eval_init,
          args.push_direction,
          args.push_level,
          force_n,
          args.push_duration_s,
          time_s,
          args.push_start_s,
          args.push_duration_s,
          metrics,
        )
      )

    zeros = torch.zeros((1, 1, 3), device=unwrapped.device)
    robot.write_external_wrench_to_sim(
      zeros,
      zeros,
      env_ids=torch.tensor([0], device=unwrapped.device),
      body_ids=[base_body_id],
    )
    env.close()

  if not frames:
    raise RuntimeError("No video frames were rendered.")

  output = args.output
  if output is None:
    output = args.output_dir / (
      f"{args.name_prefix}_{args.policy_id}_{args.eval_init}_{args.push_level}_{args.push_direction}.mp4"
    )
  output.parent.mkdir(parents=True, exist_ok=True)
  fps = round(1.0 / step_dt)
  imageio.mimwrite(output, frames, fps=fps)
  print(
    f"[INFO] Saved push video: {output} | policy={args.policy_id}, "
    f"direction={args.push_direction}, level={args.push_level}, force={force_n:.1f} N"
  )


if __name__ == "__main__":
  main()
