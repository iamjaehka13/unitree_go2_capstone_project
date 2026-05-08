#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/home/iamjaehka13/unitree_rl_mjlab"
PYTHON="${REPO_ROOT}/project/.venv/bin/python"
TRAIN="${REPO_ROOT}/scripts/train.py"
NUM_ENVS="${NUM_ENVS:-4096}"
MAX_ITERATIONS="${MAX_ITERATIONS:-5000}"
SAVE_INTERVAL="${SAVE_INTERVAL:-100}"
SEED="${SEED:-0}"

cd "${REPO_ROOT}"

echo "[INFO] v6 locked/tucked clean 4096-env 5000-iteration training started at $(date --iso-8601=seconds)"
echo "[INFO] num_envs=${NUM_ENVS}, max_iterations=${MAX_ITERATIONS}, save_interval=${SAVE_INTERVAL}, seed=${SEED}"
echo "[INFO] condition: E4L FR torque-zero + mechanically locked/tucked FR leg + clean tripod reward"

"${PYTHON}" "${TRAIN}" "Unitree-Go2-FR-Failure-Locked-Tucked-Clean-Stand" \
  --env.scene.num-envs "${NUM_ENVS}" \
  --agent.max-iterations "${MAX_ITERATIONS}" \
  --agent.save-interval "${SAVE_INTERVAL}" \
  --agent.run-name "v6_locked_tucked_4096_5000_seed0_e4l_fr_locked_tucked" \
  --env.seed "${SEED}" \
  --agent.seed "${SEED}"

echo "[INFO] v6 locked/tucked clean training finished at $(date --iso-8601=seconds)"
