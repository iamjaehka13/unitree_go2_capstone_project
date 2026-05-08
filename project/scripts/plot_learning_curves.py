"""Plot PPO learning curves from the extracted training log CSV."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "project" / "configs" / "experiment_v1.yaml"
DEFAULT_INPUT = REPO_ROOT / "project" / "results" / "training_logs" / "training_logs.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "project" / "results" / "figures" / "learning_curves"
DEFAULT_METRICS = [
  "Train_mean_reward",
  "Train_mean_episode_length",
  "Episode_Termination_illegal_contact",
  "Episode_Termination_base_height",
  "Episode_Termination_fell_over",
  "Policy_mean_std",
  "Loss_entropy",
]

CONDITION_COLORS = {
  "E0": "#6B7280",
  "E1": "#D97706",
  "E2": "#0F766E",
}


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
  parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
  parser.add_argument(
    "--metric",
    action="append",
    help="CSV metric column to plot. Can be passed multiple times.",
  )
  parser.add_argument(
    "--condition",
    action="append",
    help="Condition id to include, e.g. E1. Defaults to all conditions in the CSV.",
  )
  parser.add_argument("--x", choices=["total_steps_est", "iteration"], default="total_steps_est")
  parser.add_argument("--smooth", type=int, default=1, help="Rolling mean window over iterations.")
  parser.add_argument("--dpi", type=int, default=180)
  return parser.parse_args()


def load_condition_labels(config_path: Path) -> dict[str, str]:
  if not config_path.exists():
    return {}
  data = yaml.safe_load(config_path.read_text()) or {}
  labels: dict[str, str] = {}
  for condition in data.get("conditions", []):
    condition_id = str(condition.get("id", ""))
    label = str(condition.get("label", condition_id))
    if condition_id:
      labels[condition_id] = label
  return labels


def pretty_metric_name(metric: str) -> str:
  name = metric
  for prefix in ("Train_", "Episode_", "Reward_", "Termination_", "Loss_", "Policy_", "Metrics_"):
    name = name.replace(prefix, "")
  return name.replace("_", " ").strip().title()


def safe_filename(name: str) -> str:
  return re.sub(r"[^0-9A-Za-z._-]+", "_", name).strip("_")


def numeric_column(df: pd.DataFrame, column: str) -> pd.Series:
  return pd.to_numeric(df[column], errors="coerce")


def available_metrics(df: pd.DataFrame, requested: list[str] | None) -> list[str]:
  if requested:
    missing = [metric for metric in requested if metric not in df.columns]
    if missing:
      raise ValueError(f"Requested metric columns are missing: {', '.join(missing)}")
    return requested
  return [metric for metric in DEFAULT_METRICS if metric in df.columns]


def aggregate_metric(df: pd.DataFrame, x_col: str, metric: str, smooth: int) -> pd.DataFrame:
  work = df[["condition_id", "condition_label", "seed", "run_name", x_col, metric]].copy()
  work[x_col] = numeric_column(work, x_col)
  work[metric] = numeric_column(work, metric)
  work = work.dropna(subset=["condition_id", x_col, metric])
  if work.empty:
    return work

  per_run = (
    work.groupby(["condition_id", "condition_label", "seed", "run_name", x_col], as_index=False)[metric]
    .mean()
    .sort_values(["condition_id", "seed", "run_name", x_col])
  )
  if smooth > 1:
    per_run[metric] = per_run.groupby(["condition_id", "seed", "run_name"])[metric].transform(
      lambda series: series.rolling(window=smooth, min_periods=1).mean()
    )

  summary = per_run.groupby(["condition_id", "condition_label", x_col], as_index=False).agg(
    mean=(metric, "mean"),
    std=(metric, "std"),
    runs=(metric, "count"),
  )
  summary["std"] = summary["std"].fillna(0.0)
  return summary


def plot_metric(
  summary: pd.DataFrame,
  metric: str,
  x_col: str,
  labels: dict[str, str],
  output_dir: Path,
  dpi: int,
) -> None:
  fig, ax = plt.subplots(figsize=(8.0, 4.6))
  for condition_id in sorted(summary["condition_id"].unique()):
    part = summary[summary["condition_id"] == condition_id].sort_values(x_col)
    label = labels.get(condition_id) or str(part["condition_label"].dropna().iloc[0] or condition_id)
    color = CONDITION_COLORS.get(condition_id)
    x = part[x_col].to_numpy(dtype=float)
    y = part["mean"].to_numpy(dtype=float)
    std = part["std"].to_numpy(dtype=float)
    ax.plot(x, y, label=f"{condition_id} {label}", color=color, linewidth=2.2)
    if len(part) > 1:
      ax.fill_between(x, y - std, y + std, color=color, alpha=0.16, linewidth=0)

  x_label = "Estimated Environment Steps" if x_col == "total_steps_est" else "PPO Iteration"
  ax.set_title(pretty_metric_name(metric))
  ax.set_xlabel(x_label)
  ax.set_ylabel(pretty_metric_name(metric))
  ax.grid(True, color="#E5E7EB", linewidth=0.9)
  ax.spines["top"].set_visible(False)
  ax.spines["right"].set_visible(False)
  ax.legend(frameon=False, fontsize=9)
  fig.tight_layout()
  output_dir.mkdir(parents=True, exist_ok=True)
  fig.savefig(output_dir / f"{safe_filename(metric)}.png", dpi=dpi)
  plt.close(fig)


def write_summary(
  summaries: dict[str, pd.DataFrame],
  output_dir: Path,
  x_col: str,
) -> None:
  rows: list[dict[str, Any]] = []
  for metric, summary in summaries.items():
    for row in summary.to_dict("records"):
      rows.append(
        {
          "metric": metric,
          "condition_id": row["condition_id"],
          "condition_label": row["condition_label"],
          x_col: row[x_col],
          "mean": row["mean"],
          "std": row["std"],
          "runs": row["runs"],
        }
      )
  if rows:
    pd.DataFrame(rows).to_csv(output_dir / "learning_curve_summary.csv", index=False)


def main() -> None:
  args = parse_args()
  if not args.input.exists():
    raise FileNotFoundError(f"Training log CSV not found: {args.input}")

  df = pd.read_csv(args.input)
  x_col = args.x if args.x in df.columns else "iteration"
  df[x_col] = numeric_column(df, x_col)
  if args.condition:
    df = df[df["condition_id"].isin(args.condition)]

  metrics = available_metrics(df, args.metric)
  if not metrics:
    raise ValueError("No plottable metric columns found.")

  labels = load_condition_labels(args.config)
  summaries: dict[str, pd.DataFrame] = {}
  for metric in metrics:
    summary = aggregate_metric(df, x_col, metric, max(args.smooth, 1))
    if summary.empty:
      print(f"[WARN] Skipping empty metric: {metric}")
      continue
    summaries[metric] = summary
    plot_metric(summary, metric, x_col, labels, args.output_dir, args.dpi)

  write_summary(summaries, args.output_dir, x_col)
  print(f"[INFO] Wrote {len(summaries)} learning-curve figures to {args.output_dir}")


if __name__ == "__main__":
  main()
