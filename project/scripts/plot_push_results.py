"""Plot push evaluation summaries and heatmaps."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "project" / "results" / "push_eval" / "push_eval.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "project" / "results" / "figures" / "push_eval"
DIRECTION_ORDER = ["front", "back", "left", "right"]
LEVEL_ORDER = ["weak", "medium", "strong"]
POLICY_COLORS = {
  "E1": "#D97706",
  "E2": "#0F766E",
  "E3": "#2563EB",
}


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
  parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
  parser.add_argument("--dpi", type=int, default=180)
  return parser.parse_args()


def numeric(df: pd.DataFrame, column: str) -> pd.Series:
  return pd.to_numeric(df[column], errors="coerce")


def prepare(df: pd.DataFrame) -> pd.DataFrame:
  df = df.copy()
  for column in [
    "success",
    "push_success",
    "survival_success",
    "strict_success",
    "tripod_success",
    "recovered",
    "recovery_time_s",
    "survival_time_s",
    "max_tilt_after_push_deg",
    "max_base_displacement_after_push_m",
    "mean_torque_norm",
    "force_n",
    "impulse_ns",
  ]:
    if column in df.columns:
      df[column] = numeric(df, column)
  return df


def aggregate(df: pd.DataFrame) -> pd.DataFrame:
  group_cols = [
    "policy_id",
    "eval_init",
    "push_direction",
    "push_level",
    "force_n",
    "impulse_ns",
  ]
  summary = (
    df.groupby(group_cols, as_index=False)
    .agg(
      episodes=("episode", "count"),
      push_success_rate=("push_success", "mean"),
      survival_success_rate=("survival_success", "mean"),
      strict_success_rate=("strict_success", "mean"),
      tripod_success_rate=("tripod_success", "mean"),
      recovery_rate=("recovered", "mean"),
      recovery_time_mean_s=("recovery_time_s", "mean"),
      survival_time_mean_s=("survival_time_s", "mean"),
      max_tilt_after_push_mean_deg=("max_tilt_after_push_deg", "mean"),
      max_base_displacement_after_push_mean_m=("max_base_displacement_after_push_m", "mean"),
      mean_torque_norm=("mean_torque_norm", "mean"),
    )
    .fillna(0.0)
  )
  summary["push_direction"] = pd.Categorical(
    summary["push_direction"], categories=DIRECTION_ORDER, ordered=True
  )
  summary["push_level"] = pd.Categorical(
    summary["push_level"], categories=LEVEL_ORDER, ordered=True
  )
  return summary.sort_values(["policy_id", "eval_init", "push_direction", "push_level"])


def plot_heatmap(
  part: pd.DataFrame,
  policy_label: str,
  metric: str,
  title: str,
  output_path: Path,
  dpi: int,
  vmin: float | None = None,
  vmax: float | None = None,
  cmap: str = "viridis",
) -> None:
  table = (
    part.pivot_table(
      index="push_direction",
      columns="push_level",
      values=metric,
      observed=False,
    )
    .reindex(index=DIRECTION_ORDER, columns=LEVEL_ORDER)
    .fillna(0.0)
  )
  fig, ax = plt.subplots(figsize=(5.6, 4.2))
  im = ax.imshow(table.to_numpy(), vmin=vmin, vmax=vmax, cmap=cmap)
  ax.set_xticks(range(len(LEVEL_ORDER)), LEVEL_ORDER)
  ax.set_yticks(range(len(DIRECTION_ORDER)), DIRECTION_ORDER)
  ax.set_title(f"{policy_label}: {title}")
  for row_idx, direction in enumerate(DIRECTION_ORDER):
    for col_idx, level in enumerate(LEVEL_ORDER):
      value = table.loc[direction, level]
      ax.text(col_idx, row_idx, f"{value:.2f}", ha="center", va="center", color="white")
  fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
  fig.tight_layout()
  fig.savefig(output_path, dpi=dpi)
  plt.close(fig)


def plot_policy_bars(summary: pd.DataFrame, output_dir: Path, dpi: int) -> None:
  collapsed = (
    summary.groupby(["policy_id", "eval_init"], as_index=False)
    .agg(
      push_success_rate=("push_success_rate", "mean"),
      survival_success_rate=("survival_success_rate", "mean"),
      recovery_rate=("recovery_rate", "mean"),
      max_tilt_after_push_mean_deg=("max_tilt_after_push_mean_deg", "mean"),
    )
  )
  labels = [f"{row.policy_id}\n{row.eval_init}" for row in collapsed.itertuples()]
  x = range(len(collapsed))
  fig, ax = plt.subplots(figsize=(7.0, 4.0))
  colors = [POLICY_COLORS.get(str(row.policy_id), "#6B7280") for row in collapsed.itertuples()]
  ax.bar(x, collapsed["push_success_rate"], color=colors)
  ax.set_xticks(list(x), labels)
  ax.set_ylim(0.0, 1.02)
  ax.set_ylabel("Mean Push Success Rate")
  ax.set_title("Push Robustness Summary")
  ax.grid(axis="y", color="#E5E7EB")
  ax.spines["top"].set_visible(False)
  ax.spines["right"].set_visible(False)
  fig.tight_layout()
  fig.savefig(output_dir / "push_success_policy_summary.png", dpi=dpi)
  plt.close(fig)


def main() -> None:
  args = parse_args()
  if not args.input.exists():
    raise FileNotFoundError(f"Push eval CSV not found: {args.input}")
  df = prepare(pd.read_csv(args.input))
  if df.empty:
    raise ValueError("Push eval CSV is empty.")

  args.output_dir.mkdir(parents=True, exist_ok=True)
  summary = aggregate(df)
  summary.to_csv(args.output_dir / "push_eval_summary.csv", index=False)

  plot_policy_bars(summary, args.output_dir, args.dpi)
  for (policy_id, eval_init), part in summary.groupby(["policy_id", "eval_init"]):
    label = f"{policy_id} {eval_init}"
    suffix = f"{policy_id}_{eval_init}".replace("/", "_")
    plot_heatmap(
      part,
      label,
      "push_success_rate",
      "Push Success Rate",
      args.output_dir / f"push_success_heatmap_{suffix}.png",
      args.dpi,
      vmin=0.0,
      vmax=1.0,
      cmap="YlGn",
    )
    plot_heatmap(
      part,
      label,
      "survival_success_rate",
      "Survival Success Rate",
      args.output_dir / f"survival_success_heatmap_{suffix}.png",
      args.dpi,
      vmin=0.0,
      vmax=1.0,
      cmap="YlGn",
    )
    plot_heatmap(
      part,
      label,
      "max_tilt_after_push_mean_deg",
      "Mean Max Tilt After Push (deg)",
      args.output_dir / f"max_tilt_heatmap_{suffix}.png",
      args.dpi,
      cmap="magma",
    )

  print(f"[INFO] Wrote push summary and figures to {args.output_dir}")


if __name__ == "__main__":
  main()
