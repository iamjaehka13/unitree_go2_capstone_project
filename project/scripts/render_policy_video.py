"""Render a trained policy rollout to an MP4 video."""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUTPUT_DIR = REPO_ROOT / "project" / "videos" / "no_push"


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--task", required=True, help="Registered mjlab task id.")
  parser.add_argument("--checkpoint", type=Path, required=True)
  parser.add_argument("--output", type=Path)
  parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
  parser.add_argument("--name-prefix", default="policy")
  parser.add_argument("--duration-s", type=float, default=10.0)
  parser.add_argument("--num-envs", type=int, default=1)
  parser.add_argument("--seed", type=int, default=0)
  parser.add_argument("--device", default="cpu")
  parser.add_argument("--width", type=int, default=1280)
  parser.add_argument("--height", type=int, default=720)
  parser.add_argument("--camera-distance", type=float, default=1.8)
  parser.add_argument("--camera-elevation", type=float, default=-12.0)
  parser.add_argument("--camera-azimuth", type=float, default=135.0)
  parser.add_argument("--quiet", action="store_true")
  return parser.parse_args()


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
  from mjlab.utils.wrappers import VideoRecorder

  env_cfg = load_env_cfg(args.task)
  env_cfg.scene.num_envs = args.num_envs
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
    steps = max(1, round(args.duration_s / base_env.step_dt))
    video_env = VideoRecorder(
      base_env,
      video_folder=args.output_dir,
      step_trigger=lambda step: step == 0,
      video_length=steps,
      name_prefix=args.name_prefix,
      disable_logger=args.quiet,
    )
    env = RslRlVecEnvWrapper(video_env, clip_actions=agent_cfg.clip_actions)
    runner_cls = load_runner_cls(args.task) or MjlabOnPolicyRunner
    runner = runner_cls(env, asdict(agent_cfg), log_dir=None, device=args.device)
    runner.load(
      str(checkpoint),
      load_cfg={"actor": True},
      strict=True,
      map_location=args.device,
    )
    policy = runner.get_inference_policy(device=args.device)
    obs = env.get_observations().to(args.device)

    for _ in range(steps):
      with torch.inference_mode():
        action = policy(obs)
      obs, _reward, _dones, _extras = env.step(action)
      obs = obs.to(args.device)

    env.close()

  recorded_path = args.output_dir / f"{args.name_prefix}-step-0.mp4"
  final_path = args.output if args.output is not None else recorded_path
  if args.output is not None:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    if recorded_path.resolve() != final_path.resolve():
      shutil.move(str(recorded_path), str(final_path))
  if not final_path.exists():
    raise FileNotFoundError(f"Video was not created: {final_path}")

  print(f"[INFO] Saved video: {final_path}")


if __name__ == "__main__":
  main()
