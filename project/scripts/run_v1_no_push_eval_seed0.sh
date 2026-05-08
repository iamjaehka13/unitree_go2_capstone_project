#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/home/iamjaehka13/unitree_rl_mjlab"
PYTHON="${REPO_ROOT}/project/.venv/bin/python"
EVAL="${REPO_ROOT}/project/scripts/eval_no_push.py"
OUTPUT="${REPO_ROOT}/project/results/no_push_eval/no_push_eval_v1_2000_seed0.csv"
EPISODES=20
NUM_ENVS=20
SEED=0
DEVICE="cuda:0"
CHECKPOINTS=(0 50 100 200 500 1000 1999)

cd "${REPO_ROOT}"
mkdir -p "$(dirname "${OUTPUT}")"
rm -f "${OUTPUT}"

echo "[INFO] v1 no-push eval started at $(date --iso-8601=seconds)"
echo "[INFO] output=${OUTPUT}"
echo "[INFO] episodes=${EPISODES}, num_envs=${NUM_ENVS}, seed=${SEED}, device=${DEVICE}"

run_condition() {
  local task_id="$1"
  local run_dir="$2"

  for iteration in "${CHECKPOINTS[@]}"; do
    local checkpoint="${run_dir}/model_${iteration}.pt"
    echo
    echo "[INFO] Evaluating ${task_id} checkpoint=model_${iteration}.pt at $(date --iso-8601=seconds)"
    "${PYTHON}" "${EVAL}" \
      --task "${task_id}" \
      --checkpoint "${checkpoint}" \
      --output "${OUTPUT}" \
      --episodes "${EPISODES}" \
      --num-envs "${NUM_ENVS}" \
      --seed "${SEED}" \
      --device "${DEVICE}" \
      --append \
      --quiet
  done
}

run_condition \
  "Unitree-Go2-Stand" \
  "${REPO_ROOT}/logs/rsl_rl/go2_stand/2026-05-03_23-21-09_v1_2000_seed0_e0_four_leg"

run_condition \
  "Unitree-Go2-FR-Failure-Default-Stand" \
  "${REPO_ROOT}/logs/rsl_rl/go2_fr_failure_default_stand/2026-05-03_23-36-15_v1_2000_seed0_e1_fr_default"

run_condition \
  "Unitree-Go2-FR-Failure-Tripod-Stand" \
  "${REPO_ROOT}/logs/rsl_rl/go2_fr_failure_tripod_stand/2026-05-03_23-51-32_v1_2000_seed0_e2_fr_tripod"

echo
echo "[INFO] v1 no-push eval finished at $(date --iso-8601=seconds)"
