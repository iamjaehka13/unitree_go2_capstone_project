#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-project/.venv/bin/python}"
DEVICE="${DEVICE:-cpu}"
SEED="${SEED:-0}"
DURATION_S="${DURATION_S:-8.0}"
WIDTH="${WIDTH:-1280}"
HEIGHT="${HEIGHT:-720}"
OUTPUT_DIR="${OUTPUT_DIR:-project/videos/clean_tripod}"

latest_run() {
  local root="$1"
  local pattern="$2"
  local run
  run="$(find "$root" -maxdepth 1 -type d -name "$pattern" | sort | tail -n 1)"
  if [[ -z "$run" ]]; then
    echo "Could not find run matching $root/$pattern" >&2
    exit 1
  fi
  echo "$run"
}

checkpoint() {
  local run="$1"
  local ckpt="$run/model_4999.pt"
  if [[ ! -f "$ckpt" ]]; then
    echo "Missing checkpoint: $ckpt" >&2
    exit 1
  fi
  echo "$ckpt"
}

E1C_RUN="$(latest_run logs/rsl_rl/go2_fr_failure_default_clean_stand '*v5_clean_4096_5000_seed0_e1c_fr_default')"
E2C_RUN="$(latest_run logs/rsl_rl/go2_fr_failure_tripod_clean_stand '*v5_clean_4096_5000_seed0_e2c_fr_tripod')"
E3C_RUN="$(latest_run logs/rsl_rl/go2_fr_failure_init_curriculum_clean_stand '*v5_clean_4096_5000_seed0_e3c_fr_init_curriculum')"

mkdir -p "$OUTPUT_DIR"

"$PYTHON" project/scripts/render_clean_tripod_video.py \
  --task Unitree-Go2-FR-Failure-Default-Clean-Stand \
  --checkpoint "$(checkpoint "$E1C_RUN")" \
  --policy-id E1C \
  --eval-init default_clean \
  --duration-s "$DURATION_S" \
  --width "$WIDTH" \
  --height "$HEIGHT" \
  --seed "$SEED" \
  --device "$DEVICE" \
  --quiet \
  --output "$OUTPUT_DIR/E1C_default_clean_no_push.mp4"

"$PYTHON" project/scripts/render_clean_tripod_video.py \
  --task Unitree-Go2-FR-Failure-Tripod-Clean-Stand \
  --checkpoint "$(checkpoint "$E2C_RUN")" \
  --policy-id E2C \
  --eval-init tripod_clean \
  --duration-s "$DURATION_S" \
  --width "$WIDTH" \
  --height "$HEIGHT" \
  --seed "$SEED" \
  --device "$DEVICE" \
  --quiet \
  --output "$OUTPUT_DIR/E2C_tripod_clean_no_push.mp4"

"$PYTHON" project/scripts/render_clean_tripod_video.py \
  --task Unitree-Go2-FR-Failure-Default-Clean-Stand \
  --checkpoint "$(checkpoint "$E3C_RUN")" \
  --policy-id E3C \
  --eval-init default_clean \
  --duration-s "$DURATION_S" \
  --width "$WIDTH" \
  --height "$HEIGHT" \
  --seed "$SEED" \
  --device "$DEVICE" \
  --quiet \
  --output "$OUTPUT_DIR/E3C_default_clean_no_push.mp4"

echo "[INFO] Saved clean tripod videos under $OUTPUT_DIR"
