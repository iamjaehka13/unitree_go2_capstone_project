#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/home/iamjaehka13/unitree_rl_mjlab"
PYTHON="${REPO_ROOT}/project/.venv/bin/python"
EVAL="${REPO_ROOT}/project/scripts/eval_push.py"
PLOT="${REPO_ROOT}/project/scripts/plot_push_results.py"
OUTPUT="${REPO_ROOT}/project/results/push_eval/push_eval_v2_calibrated_final_seed0.csv"
FIG_DIR="${REPO_ROOT}/project/results/figures/push_eval_v2_calibrated_final_seed0"
EPISODES="${EPISODES:-20}"
NUM_ENVS="${NUM_ENVS:-20}"
SEED=0
DEVICE="${DEVICE:-cuda:0}"
DIRECTIONS=(front back left right)
LEVELS=(weak medium strong)
MULTIPLIERS=(0.25 0.35 0.45)

E1_CKPT="${E1_CKPT:-${REPO_ROOT}/logs/rsl_rl/go2_fr_failure_default_stand/2026-05-06_20-24-01_v2_4096_5000_seed0_e1_fr_default/model_4999.pt}"
E2_CKPT="${E2_CKPT:-${REPO_ROOT}/logs/rsl_rl/go2_fr_failure_tripod_stand/2026-05-06_21-37-52_v2_4096_5000_seed0_e2_fr_tripod/model_4999.pt}"
E3_CKPT="${E3_CKPT:-${REPO_ROOT}/logs/rsl_rl/go2_fr_failure_init_curriculum_stand/2026-05-06_22-50-24_v2_4096_5000_seed0_e3_fr_init_curriculum/model_4999.pt}"

cd "${REPO_ROOT}"
mkdir -p "$(dirname "${OUTPUT}")" "${FIG_DIR}"
rm -f "${OUTPUT}"

echo "[INFO] v2 calibrated final push eval started at $(date --iso-8601=seconds)"
echo "[INFO] output=${OUTPUT}"
echo "[INFO] calibrated levels: weak=0.25BW, medium=0.35BW, strong=0.45BW"
echo "[INFO] episodes=${EPISODES}, num_envs=${NUM_ENVS}, seed=${SEED}, device=${DEVICE}"

run_policy() {
  local policy_id="$1"
  local eval_init="$2"
  local task="$3"
  local checkpoint="$4"

  for direction in "${DIRECTIONS[@]}"; do
    for idx in "${!LEVELS[@]}"; do
      local level="${LEVELS[$idx]}"
      local multiplier="${MULTIPLIERS[$idx]}"
      echo
      echo "[INFO] Evaluating policy=${policy_id} init=${eval_init} direction=${direction} level=${level} multiplier=${multiplier}BW"
      "${PYTHON}" "${EVAL}" \
        --task "${task}" \
        --checkpoint "${checkpoint}" \
        --policy-id "${policy_id}" \
        --eval-init "${eval_init}" \
        --output "${OUTPUT}" \
        --episodes "${EPISODES}" \
        --num-envs "${NUM_ENVS}" \
        --seed "${SEED}" \
        --device "${DEVICE}" \
        --push-direction "${direction}" \
        --push-level "${level}" \
        --force-multiplier-bw "${multiplier}" \
        --append \
        --quiet
    done
  done
}

# E1 is included as a no-robustness failure reference.
run_policy "E1" "default" "Unitree-Go2-FR-Failure-Default-Stand" "${E1_CKPT}"
run_policy "E2" "tripod" "Unitree-Go2-FR-Failure-Tripod-Stand" "${E2_CKPT}"
run_policy "E3" "default" "Unitree-Go2-FR-Failure-Default-Stand" "${E3_CKPT}"

"${PYTHON}" "${PLOT}" \
  --input "${OUTPUT}" \
  --output-dir "${FIG_DIR}"

echo
echo "[INFO] v2 calibrated final push eval finished at $(date --iso-8601=seconds)"
