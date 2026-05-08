"""Extract TensorBoard scalar logs into a flat CSV for v1 analysis."""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "project" / "configs" / "experiment_v1.yaml"
DEFAULT_LOGS_ROOT = REPO_ROOT / "logs" / "rsl_rl"
DEFAULT_OUTPUT = REPO_ROOT / "project" / "results" / "training_logs" / "training_logs.csv"


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  parser.add_argument("--logs-root", type=Path, default=DEFAULT_LOGS_ROOT)
  parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
  parser.add_argument(
    "--experiment-name",
    action="append",
    help="Limit extraction to one experiment_name. Can be passed multiple times.",
  )
  parser.add_argument(
    "--include-time-tags",
    action="store_true",
    help="Also include TensorBoard tags ending in '/time'. These use wall-time steps.",
  )
  return parser.parse_args()


def load_conditions(config_path: Path) -> dict[str, dict[str, Any]]:
  if not config_path.exists():
    return {}
  data = yaml.safe_load(config_path.read_text()) or {}
  conditions = data.get("conditions", [])
  return {condition["experiment_name"]: condition for condition in conditions}


def scalar_column(tag: str) -> str:
  return re.sub(r"[^0-9A-Za-z_]+", "_", tag).strip("_")


def read_simple_yaml_value(path: Path, key: str) -> str | None:
  if not path.exists():
    return None
  pattern = re.compile(rf"^{re.escape(key)}:\s*(.+?)\s*$")
  for line in path.read_text(errors="ignore").splitlines():
    match = pattern.match(line)
    if match:
      return match.group(1).strip("'\"")
  return None


def read_first_int_yaml_value(path: Path, key: str) -> int | None:
  if not path.exists():
    return None
  pattern = re.compile(rf"^\s*{re.escape(key)}:\s*([0-9]+)\s*$")
  for line in path.read_text(errors="ignore").splitlines():
    match = pattern.match(line)
    if match:
      return int(match.group(1))
  return None


def extract_run(
  run_dir: Path,
  condition: dict[str, Any] | None,
  include_time_tags: bool,
) -> list[dict[str, Any]]:
  event_files = sorted(run_dir.glob("events.out.tfevents.*"))
  if not event_files:
    return []

  agent_yaml = run_dir / "params" / "agent.yaml"
  env_yaml = run_dir / "params" / "env.yaml"
  seed = read_simple_yaml_value(agent_yaml, "seed")
  cfg_run_name = read_simple_yaml_value(agent_yaml, "run_name")
  num_steps_per_env = read_first_int_yaml_value(agent_yaml, "num_steps_per_env")
  num_envs = read_first_int_yaml_value(env_yaml, "num_envs")

  rows_by_step: dict[int, dict[str, Any]] = defaultdict(dict)
  for event_file in event_files:
    accumulator = EventAccumulator(str(event_file))
    accumulator.Reload()
    for tag in accumulator.Tags().get("scalars", []):
      if tag.endswith("/time") and not include_time_tags:
        continue
      column = scalar_column(tag)
      for scalar in accumulator.Scalars(tag):
        row = rows_by_step[scalar.step]
        row["iteration"] = scalar.step
        row[column] = scalar.value

  rows = []
  experiment_name = run_dir.parent.name
  condition = condition or {}
  for step in sorted(rows_by_step):
    row = {
      "condition_id": condition.get("id", ""),
      "condition_label": condition.get("label", ""),
      "task": condition.get("task", ""),
      "experiment_name": experiment_name,
      "run_dir": str(run_dir.relative_to(REPO_ROOT)),
      "run_name": cfg_run_name or run_dir.name,
      "seed": seed or "",
      "iteration": step,
    }
    if num_envs is not None:
      row["num_envs"] = num_envs
    if num_steps_per_env is not None:
      row["num_steps_per_env"] = num_steps_per_env
    if num_envs is not None and num_steps_per_env is not None:
      row["total_steps_est"] = (step + 1) * num_envs * num_steps_per_env
    row.update(rows_by_step[step])
    rows.append(row)
  return rows


def main() -> None:
  args = parse_args()
  logs_root = args.logs_root.resolve()
  conditions = load_conditions(args.config.resolve())
  selected = set(args.experiment_name or conditions.keys())

  all_rows: list[dict[str, Any]] = []
  for experiment_dir in sorted(logs_root.iterdir() if logs_root.exists() else []):
    if not experiment_dir.is_dir():
      continue
    if selected and experiment_dir.name not in selected:
      continue
    condition = conditions.get(experiment_dir.name)
    for run_dir in sorted(p for p in experiment_dir.iterdir() if p.is_dir()):
      all_rows.extend(extract_run(run_dir, condition, args.include_time_tags))

  args.output.parent.mkdir(parents=True, exist_ok=True)
  if not all_rows:
    print(f"[WARN] No TensorBoard scalar rows found under {logs_root}")
    return

  fieldnames = sorted({key for row in all_rows for key in row})
  preferred = [
    "condition_id",
    "condition_label",
    "task",
    "experiment_name",
    "run_name",
    "seed",
    "iteration",
    "total_steps_est",
    "num_envs",
    "num_steps_per_env",
    "run_dir",
  ]
  fieldnames = preferred + [name for name in fieldnames if name not in preferred]

  with args.output.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)

  print(f"[INFO] Wrote {len(all_rows)} rows to {args.output}")


if __name__ == "__main__":
  main()
