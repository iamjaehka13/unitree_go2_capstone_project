#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-project/.venv/bin/python}"
DEVICE="${DEVICE:-cuda:0}"
EPISODES="${EPISODES:-20}"
NUM_ENVS="${NUM_ENVS:-20}"
SEED="${SEED:-0}"
MAX_ROLL_PITCH_DEG="${MAX_ROLL_PITCH_DEG:-12}"
MIN_CONTACT_FRACTION="${MIN_CONTACT_FRACTION:-0.90}"
OUTPUT="${OUTPUT:-project/results/no_push_eval/no_push_eval_v5_clean_presentation_4096_5000_seed0.csv}"
CROSS_OUTPUT="${CROSS_OUTPUT:-project/results/no_push_eval/cross_eval_v5_clean_presentation_final_seed0.csv}"

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

E1C_CKPT="$(checkpoint "$E1C_RUN")"
E2C_CKPT="$(checkpoint "$E2C_RUN")"
E3C_CKPT="$(checkpoint "$E3C_RUN")"

rm -f "$OUTPUT" "$CROSS_OUTPUT"

echo "[INFO] Main clean no-push eval -> $OUTPUT"
"$PYTHON" project/scripts/eval_no_push.py \
  --task Unitree-Go2-FR-Failure-Default-Clean-Stand \
  --checkpoint "$E1C_CKPT" \
  --output "$OUTPUT" \
  --episodes "$EPISODES" \
  --num-envs "$NUM_ENVS" \
  --seed "$SEED" \
  --device "$DEVICE" \
  --max-stable-roll-pitch-deg "$MAX_ROLL_PITCH_DEG" \
  --min-contact-fraction "$MIN_CONTACT_FRACTION" \
  --append \
  --quiet

"$PYTHON" project/scripts/eval_no_push.py \
  --task Unitree-Go2-FR-Failure-Tripod-Clean-Stand \
  --checkpoint "$E2C_CKPT" \
  --output "$OUTPUT" \
  --episodes "$EPISODES" \
  --num-envs "$NUM_ENVS" \
  --seed "$SEED" \
  --device "$DEVICE" \
  --max-stable-roll-pitch-deg "$MAX_ROLL_PITCH_DEG" \
  --min-contact-fraction "$MIN_CONTACT_FRACTION" \
  --append \
  --quiet

"$PYTHON" project/scripts/eval_no_push.py \
  --task Unitree-Go2-FR-Failure-Default-Clean-Stand \
  --checkpoint "$E3C_CKPT" \
  --output "$OUTPUT" \
  --episodes "$EPISODES" \
  --num-envs "$NUM_ENVS" \
  --seed "$SEED" \
  --device "$DEVICE" \
  --max-stable-roll-pitch-deg "$MAX_ROLL_PITCH_DEG" \
  --min-contact-fraction "$MIN_CONTACT_FRACTION" \
  --append \
  --quiet

echo "[INFO] Clean cross-eval -> $CROSS_OUTPUT"
"$PYTHON" project/scripts/eval_no_push.py \
  --task Unitree-Go2-FR-Failure-Tripod-Clean-Stand \
  --checkpoint "$E1C_CKPT" \
  --output "$CROSS_OUTPUT" \
  --episodes "$EPISODES" \
  --num-envs "$NUM_ENVS" \
  --seed "$SEED" \
  --device "$DEVICE" \
  --max-stable-roll-pitch-deg "$MAX_ROLL_PITCH_DEG" \
  --min-contact-fraction "$MIN_CONTACT_FRACTION" \
  --append \
  --quiet

"$PYTHON" project/scripts/eval_no_push.py \
  --task Unitree-Go2-FR-Failure-Default-Clean-Stand \
  --checkpoint "$E2C_CKPT" \
  --output "$CROSS_OUTPUT" \
  --episodes "$EPISODES" \
  --num-envs "$NUM_ENVS" \
  --seed "$SEED" \
  --device "$DEVICE" \
  --max-stable-roll-pitch-deg "$MAX_ROLL_PITCH_DEG" \
  --min-contact-fraction "$MIN_CONTACT_FRACTION" \
  --append \
  --quiet

"$PYTHON" project/scripts/eval_no_push.py \
  --task Unitree-Go2-FR-Failure-Tripod-Clean-Stand \
  --checkpoint "$E3C_CKPT" \
  --output "$CROSS_OUTPUT" \
  --episodes "$EPISODES" \
  --num-envs "$NUM_ENVS" \
  --seed "$SEED" \
  --device "$DEVICE" \
  --max-stable-roll-pitch-deg "$MAX_ROLL_PITCH_DEG" \
  --min-contact-fraction "$MIN_CONTACT_FRACTION" \
  --append \
  --quiet

echo "[INFO] Done"
