"""Run no-push evaluation across saved checkpoints for v1 conditions."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "project" / "configs" / "experiment_v1.yaml"
DEFAULT_LOGS_ROOT = REPO_ROOT / "logs" / "rsl_rl"
DEFAULT_OUTPUT = REPO_ROOT / "project" / "results" / "no_push_eval" / "no_push_eval.csv"
DEFAULT_CHECKPOINTS = [0, 50, 100, 200, 500]


@dataclass(frozen=True)
class Condition:
  condition_id: str
  label: str
  task: str
  experiment_name: str


@dataclass(frozen=True)
class EvalJob:
  condition: Condition
  checkpoint: Path
  iteration: int


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  parser.add_argument("--logs-root", type=Path, default=DEFAULT_LOGS_ROOT)
  parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
  parser.add_argument(
    "--condition",
    action="append",
    help="Condition id to evaluate, e.g. E1. Defaults to all config conditions.",
  )
  parser.add_argument(
    "--checkpoint",
    type=int,
    action="append",
    help="Checkpoint iteration to evaluate. Defaults to 0, 50, 100, 200, 500.",
  )
  parser.add_argument("--episodes", type=int, default=20)
  parser.add_argument("--num-envs", type=int, default=20)
  parser.add_argument("--seed", type=int, default=0, help="Evaluation seed.")
  parser.add_argument("--device", default="cpu")
  parser.add_argument("--episode-length-s", type=float, default=10.0)
  parser.add_argument("--initial-failure-s", type=float, default=2.0)
  parser.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
  parser.add_argument("--quiet", action="store_true")
  return parser.parse_args()


def load_conditions(config_path: Path) -> list[Condition]:
  data = yaml.safe_load(config_path.read_text()) or {}
  conditions: list[Condition] = []
  for condition in data.get("conditions", []):
    conditions.append(
      Condition(
        condition_id=str(condition["id"]),
        label=str(condition["label"]),
        task=str(condition["task"]),
        experiment_name=str(condition["experiment_name"]),
      )
    )
  return conditions


def checkpoint_iteration(path: Path) -> int | None:
  stem = path.stem
  if not stem.startswith("model_"):
    return None
  try:
    return int(stem.removeprefix("model_"))
  except ValueError:
    return None


def discover_jobs(
  conditions: list[Condition],
  logs_root: Path,
  checkpoint_filter: set[int],
) -> list[EvalJob]:
  jobs: list[EvalJob] = []
  for condition in conditions:
    experiment_dir = logs_root / condition.experiment_name
    if not experiment_dir.exists():
      print(f"[WARN] Missing log dir for {condition.condition_id}: {experiment_dir}")
      continue
    for checkpoint in sorted(experiment_dir.glob("*/model_*.pt")):
      iteration = checkpoint_iteration(checkpoint)
      if iteration is None or iteration not in checkpoint_filter:
        continue
      jobs.append(EvalJob(condition=condition, checkpoint=checkpoint, iteration=iteration))
  return sorted(
    jobs,
    key=lambda job: (
      job.condition.condition_id,
      str(job.checkpoint.parent),
      job.iteration,
    ),
  )


def command_for_job(args: argparse.Namespace, job: EvalJob, append: bool) -> list[str]:
  cmd = [
    sys.executable,
    str(REPO_ROOT / "project" / "scripts" / "eval_no_push.py"),
    "--task",
    job.condition.task,
    "--checkpoint",
    str(job.checkpoint),
    "--output",
    str(args.output),
    "--episodes",
    str(args.episodes),
    "--num-envs",
    str(args.num_envs),
    "--seed",
    str(args.seed),
    "--device",
    str(args.device),
    "--episode-length-s",
    str(args.episode_length_s),
    "--initial-failure-s",
    str(args.initial_failure_s),
  ]
  if append:
    cmd.append("--append")
  if args.quiet:
    cmd.append("--quiet")
  return cmd


def shell_quote(parts: list[str]) -> str:
  return " ".join("'" + part.replace("'", "'\\''") + "'" if any(ch.isspace() for ch in part) else part for part in parts)


def main() -> None:
  args = parse_args()
  selected_conditions = set(args.condition or [])
  checkpoint_filter = set(args.checkpoint or DEFAULT_CHECKPOINTS)

  conditions = load_conditions(args.config)
  if selected_conditions:
    conditions = [condition for condition in conditions if condition.condition_id in selected_conditions]
  if not conditions:
    raise ValueError("No conditions selected.")

  jobs = discover_jobs(conditions, args.logs_root, checkpoint_filter)
  if not jobs:
    print("[WARN] No checkpoint jobs found.")
    return

  if not args.dry_run:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
      args.output.unlink()

  for index, job in enumerate(jobs):
    append = index > 0
    cmd = command_for_job(args, job, append)
    print(
      f"[INFO] {job.condition.condition_id} {job.condition.label} "
      f"iter={job.iteration} checkpoint={job.checkpoint.relative_to(REPO_ROOT)}"
    )
    if args.dry_run:
      print(shell_quote(cmd))
      continue
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)

  print(f"[INFO] Processed {len(jobs)} checkpoint evaluation jobs.")


if __name__ == "__main__":
  main()
