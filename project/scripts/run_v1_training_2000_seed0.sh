#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/home/iamjaehka13/unitree_rl_mjlab"
PYTHON="${REPO_ROOT}/project/.venv/bin/python"
TRAIN="${REPO_ROOT}/scripts/train.py"
NUM_ENVS=1024
MAX_ITERATIONS=2000
SAVE_INTERVAL=50
SEED=0

cd "${REPO_ROOT}"

echo "[INFO] v1 2000-iteration sequential training started at $(date --iso-8601=seconds)"
echo "[INFO] num_envs=${NUM_ENVS}, max_iterations=${MAX_ITERATIONS}, save_interval=${SAVE_INTERVAL}, seed=${SEED}"

run_train() {
  local task_id="$1"
  local run_name="$2"
  echo
  echo "[INFO] Starting ${task_id} run_name=${run_name} at $(date --iso-8601=seconds)"
  "${PYTHON}" "${TRAIN}" "${task_id}" \
    --env.scene.num-envs "${NUM_ENVS}" \
    --agent.max-iterations "${MAX_ITERATIONS}" \
    --agent.save-interval "${SAVE_INTERVAL}" \
    --agent.run-name "${run_name}" \
    --env.seed "${SEED}" \
    --agent.seed "${SEED}"
  echo "[INFO] Finished ${task_id} run_name=${run_name} at $(date --iso-8601=seconds)"
}

run_train "Unitree-Go2-Stand" "v1_2000_seed0_e0_four_leg"
run_train "Unitree-Go2-FR-Failure-Default-Stand" "v1_2000_seed0_e1_fr_default"
run_train "Unitree-Go2-FR-Failure-Tripod-Stand" "v1_2000_seed0_e2_fr_tripod"

echo
echo "[INFO] v1 2000-iteration sequential training finished at $(date --iso-8601=seconds)"
