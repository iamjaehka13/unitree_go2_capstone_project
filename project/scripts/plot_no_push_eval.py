"""Plot checkpoint no-push evaluation metrics."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "project" / "configs" / "experiment_v1.yaml"
DEFAULT_INPUT = REPO_ROOT / "project" / "results" / "no_push_eval" / "no_push_eval.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "project" / "results" / "figures" / "no_push_eval"

CONDITION_COLORS = {
  "E0": "#6B7280",
  "E1": "#D97706",
  "E2": "#0F766E",
  "E3": "#2563EB",
}
DEFAULT_MAX_DISABLED_FOOT_CONTACT_FRACTION = 0.20


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
  parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
  parser.add_argument(
    "--condition",
    action="append",
    help="Condition id to include, e.g. E1. Defaults to all conditions in the CSV.",
  )
  parser.add_argument("--dpi", type=int, default=180)
  return parser.parse_args()


def load_condition_maps(config_path: Path) -> tuple[dict[str, str], dict[str, str]]:
  if not config_path.exists():
    return {}, {}
  data = yaml.safe_load(config_path.read_text()) or {}
  task_to_id: dict[str, str] = {}
  id_to_label: dict[str, str] = {}
  for condition in data.get("conditions", []):
    condition_id = str(condition.get("id", ""))
    task = str(condition.get("task", ""))
    label = str(condition.get("label", condition_id))
    if task and condition_id:
      task_to_id[task] = condition_id
      id_to_label[condition_id] = label
  return task_to_id, id_to_label


def safe_filename(name: str) -> str:
  return re.sub(r"[^0-9A-Za-z._-]+", "_", name).strip("_")


def numeric_column(df: pd.DataFrame, column: str) -> pd.Series:
  return pd.to_numeric(df[column], errors="coerce")


def prepare_data(df: pd.DataFrame, task_to_id: dict[str, str], id_to_label: dict[str, str]) -> pd.DataFrame:
  df = df.copy()
  df["condition_id"] = df["task"].map(task_to_id).fillna(df.get("condition_id", ""))
  df["condition_label"] = df["condition_id"].map(id_to_label).fillna(df["condition_id"])
  df["checkpoint_iteration"] = numeric_column(df, "checkpoint_iteration")
  df["success"] = numeric_column(df, "success").fillna(0.0)
  if "survival_success" in df.columns:
    df["survival_success"] = numeric_column(df, "survival_success").fillna(df["success"])
  else:
    df["survival_success"] = df["success"]
  if "strict_success" in df.columns:
    df["strict_success"] = numeric_column(df, "strict_success").fillna(0.0)
  else:
    df["strict_success"] = df["success"]
  if "tripod_success" in df.columns:
    df["tripod_success"] = numeric_column(df, "tripod_success").fillna(df["strict_success"])
  else:
    df["tripod_success"] = df["strict_success"]
  if "posture_success" in df.columns:
    df["posture_success"] = numeric_column(df, "posture_success").fillna(0.0)
  else:
    df["posture_success"] = df["strict_success"]
  if "support_contact_success" in df.columns:
    df["support_contact_success"] = numeric_column(df, "support_contact_success").fillna(0.0)
  else:
    df["support_contact_success"] = df["strict_success"]
  if "nonfoot_contact_success" in df.columns:
    df["nonfoot_contact_success"] = numeric_column(df, "nonfoot_contact_success").fillna(0.0)
  else:
    df["nonfoot_contact_success"] = df["strict_success"]
  if "last_window_disabled_contact_fraction" in df.columns:
    df["last_window_disabled_contact_fraction"] = numeric_column(
      df, "last_window_disabled_contact_fraction"
    ).fillna(0.0)
  else:
    df["last_window_disabled_contact_fraction"] = 0.0
  if "last_window_nonfoot_contact_fraction" in df.columns:
    df["last_window_nonfoot_contact_fraction"] = numeric_column(
      df, "last_window_nonfoot_contact_fraction"
    ).fillna(0.0)
  else:
    df["last_window_nonfoot_contact_fraction"] = 0.0
  if "tripod_contact_success" in df.columns:
    df["tripod_contact_success"] = numeric_column(df, "tripod_contact_success").fillna(0.0)
  else:
    disabled_contact_ok = (
      df["last_window_disabled_contact_fraction"] <= DEFAULT_MAX_DISABLED_FOOT_CONTACT_FRACTION
    )
    df["tripod_contact_success"] = (
      (df["survival_success"] > 0.0)
      & (df["support_contact_success"] > 0.0)
      & disabled_contact_ok
      & (df["nonfoot_contact_success"] > 0.0)
    ).astype(float)
  df["initial_failure"] = numeric_column(df, "initial_failure").fillna(0.0)
  df["survival_time_s"] = numeric_column(df, "survival_time_s")
  df["max_roll_deg"] = numeric_column(df, "max_roll_deg")
  df["max_pitch_deg"] = numeric_column(df, "max_pitch_deg")
  df["final_base_height_m"] = numeric_column(df, "final_base_height_m")
  df["final_roll_deg"] = numeric_column(df, "final_roll_deg")
  df["final_pitch_deg"] = numeric_column(df, "final_pitch_deg")
  df["mean_torque_norm"] = numeric_column(df, "mean_torque_norm")
  df["mean_action_norm"] = numeric_column(df, "mean_action_norm")
  df["max_tilt_deg"] = df[["max_roll_deg", "max_pitch_deg"]].abs().max(axis=1)
  df["final_tilt_deg"] = df[["final_roll_deg", "final_pitch_deg"]].abs().max(axis=1)
  return df.dropna(subset=["condition_id", "checkpoint_iteration"])


def aggregate(df: pd.DataFrame) -> pd.DataFrame:
  grouped = df.groupby(["condition_id", "condition_label", "checkpoint_iteration"], as_index=False)
  return grouped.agg(
    episodes=("episode", "count"),
    success_rate=("success", "mean"),
    survival_success_rate=("survival_success", "mean"),
    tripod_contact_success_rate=("tripod_contact_success", "mean"),
    strict_success_rate=("strict_success", "mean"),
    tripod_success_rate=("tripod_success", "mean"),
    posture_success_rate=("posture_success", "mean"),
    support_contact_success_rate=("support_contact_success", "mean"),
    nonfoot_contact_success_rate=("nonfoot_contact_success", "mean"),
    initial_failure_rate=("initial_failure", "mean"),
    survival_time_mean_s=("survival_time_s", "mean"),
    survival_time_std_s=("survival_time_s", "std"),
    max_tilt_mean_deg=("max_tilt_deg", "mean"),
    max_tilt_std_deg=("max_tilt_deg", "std"),
    final_tilt_mean_deg=("final_tilt_deg", "mean"),
    final_base_height_mean_m=("final_base_height_m", "mean"),
    mean_torque_norm=("mean_torque_norm", "mean"),
    mean_action_norm=("mean_action_norm", "mean"),
  ).fillna(0.0)


def plot_line(
  summary: pd.DataFrame,
  y_col: str,
  y_label: str,
  output_dir: Path,
  dpi: int,
  y_limit: tuple[float, float] | None = None,
) -> None:
  fig, ax = plt.subplots(figsize=(7.4, 4.4))
  for condition_id in sorted(summary["condition_id"].unique()):
    part = summary[summary["condition_id"] == condition_id].sort_values("checkpoint_iteration")
    label = str(part["condition_label"].dropna().iloc[0] or condition_id)
    ax.plot(
      part["checkpoint_iteration"],
      part[y_col],
      marker="o",
      linewidth=2.2,
      color=CONDITION_COLORS.get(condition_id),
      label=f"{condition_id} {label}",
    )
  ax.set_title(y_label)
  ax.set_xlabel("Checkpoint Iteration")
  ax.set_ylabel(y_label)
  if y_limit is not None:
    ax.set_ylim(*y_limit)
  ax.grid(True, color="#E5E7EB", linewidth=0.9)
  ax.spines["top"].set_visible(False)
  ax.spines["right"].set_visible(False)
  ax.legend(frameon=False, fontsize=9)
  fig.tight_layout()
  output_dir.mkdir(parents=True, exist_ok=True)
  fig.savefig(output_dir / f"{safe_filename(y_col)}.png", dpi=dpi)
  plt.close(fig)


def main() -> None:
  args = parse_args()
  if not args.input.exists():
    raise FileNotFoundError(f"No-push eval CSV not found: {args.input}")

  task_to_id, id_to_label = load_condition_maps(args.config)
  df = prepare_data(pd.read_csv(args.input), task_to_id, id_to_label)
  if args.condition:
    df = df[df["condition_id"].isin(args.condition)]
  if df.empty:
    raise ValueError("No rows left after filtering.")

  summary = aggregate(df)
  args.output_dir.mkdir(parents=True, exist_ok=True)
  summary.to_csv(args.output_dir / "no_push_eval_summary.csv", index=False)

  plot_line(summary, "success_rate", "Success Rate", args.output_dir, args.dpi, (0.0, 1.02))
  plot_line(summary, "survival_success_rate", "Survival Success Rate", args.output_dir, args.dpi, (0.0, 1.02))
  plot_line(
    summary,
    "tripod_contact_success_rate",
    "Tripod Contact Success Rate",
    args.output_dir,
    args.dpi,
    (0.0, 1.02),
  )
  plot_line(summary, "strict_success_rate", "Strict Success Rate", args.output_dir, args.dpi, (0.0, 1.02))
  plot_line(summary, "tripod_success_rate", "Tripod Success Rate", args.output_dir, args.dpi, (0.0, 1.02))
  plot_line(summary, "posture_success_rate", "Posture Success Rate", args.output_dir, args.dpi, (0.0, 1.02))
  plot_line(
    summary,
    "support_contact_success_rate",
    "Support Contact Success Rate",
    args.output_dir,
    args.dpi,
    (0.0, 1.02),
  )
  plot_line(
    summary,
    "nonfoot_contact_success_rate",
    "Non-Foot Contact Success Rate",
    args.output_dir,
    args.dpi,
    (0.0, 1.02),
  )
  plot_line(summary, "initial_failure_rate", "Initial Failure Rate", args.output_dir, args.dpi, (0.0, 1.02))
  plot_line(summary, "survival_time_mean_s", "Mean Survival Time (s)", args.output_dir, args.dpi)
  plot_line(summary, "max_tilt_mean_deg", "Mean Max Body Tilt (deg)", args.output_dir, args.dpi)
  plot_line(summary, "final_tilt_mean_deg", "Mean Final Body Tilt (deg)", args.output_dir, args.dpi)
  plot_line(summary, "final_base_height_mean_m", "Mean Final Base Height (m)", args.output_dir, args.dpi)
  plot_line(summary, "mean_torque_norm", "Mean Torque Norm", args.output_dir, args.dpi)

  print(f"[INFO] Wrote no-push summary and figures to {args.output_dir}")


if __name__ == "__main__":
  main()
