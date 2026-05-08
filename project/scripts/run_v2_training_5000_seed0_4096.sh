#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/home/iamjaehka13/unitree_rl_mjlab"
PYTHON="${REPO_ROOT}/project/.venv/bin/python"
TRAIN="${REPO_ROOT}/scripts/train.py"
NUM_ENVS=4096
MAX_ITERATIONS=5000
SAVE_INTERVAL=100
SEED=0

cd "${REPO_ROOT}"

echo "[INFO] v2 4096-env 5000-iteration training started at $(date --iso-8601=seconds)"
echo "[INFO] num_envs=${NUM_ENVS}, max_iterations=${MAX_ITERATIONS}, save_interval=${SAVE_INTERVAL}, seed=${SEED}"
echo "[INFO] conditions: E0 four-leg, E1 FR default, E2 FR tripod, E3 FR init curriculum"
echo "[INFO] fall condition: base_height < 0.23 m"

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

run_train "Unitree-Go2-Stand" "v2_4096_5000_seed0_e0_four_leg"
run_train "Unitree-Go2-FR-Failure-Default-Stand" "v2_4096_5000_seed0_e1_fr_default"
run_train "Unitree-Go2-FR-Failure-Tripod-Stand" "v2_4096_5000_seed0_e2_fr_tripod"
run_train "Unitree-Go2-FR-Failure-Init-Curriculum-Stand" "v2_4096_5000_seed0_e3_fr_init_curriculum"

echo
echo "[INFO] v2 4096-env 5000-iteration training finished at $(date --iso-8601=seconds)"
