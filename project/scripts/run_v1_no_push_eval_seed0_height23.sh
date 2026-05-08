#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/home/iamjaehka13/unitree_rl_mjlab"
PYTHON="${REPO_ROOT}/project/.venv/bin/python"
EVAL="${REPO_ROOT}/project/scripts/eval_no_push.py"
OUTPUT="${REPO_ROOT}/project/results/no_push_eval/no_push_eval_v1_height23_paperstance_2000_seed0.csv"
EPISODES=20
NUM_ENVS=20
SEED=0
DEVICE="cuda:0"
CHECKPOINTS=(0 50 100 200 500 1000 1999)

E0_RUN="${E0_RUN:-}"
E1_RUN="${E1_RUN:-}"
E2_RUN="${E2_RUN:-}"

cd "${REPO_ROOT}"
mkdir -p "$(dirname "${OUTPUT}")"
rm -f "${OUTPUT}"

if [[ -z "${E0_RUN}" || -z "${E1_RUN}" || -z "${E2_RUN}" ]]; then
  echo "[ERROR] Set E0_RUN, E1_RUN, and E2_RUN to the height23 paper-stance training run directories." >&2
  echo "Example:" >&2
  echo "  E0_RUN=${REPO_ROOT}/logs/rsl_rl/go2_stand/<height23-paperstance-e0-run> \\" >&2
  echo "  E1_RUN=${REPO_ROOT}/logs/rsl_rl/go2_fr_failure_default_stand/<height23-paperstance-e1-run> \\" >&2
  echo "  E2_RUN=${REPO_ROOT}/logs/rsl_rl/go2_fr_failure_tripod_stand/<height23-paperstance-e2-run> \\" >&2
  echo "  ${0}" >&2
  exit 2
fi

echo "[INFO] v1 height23 paper-stance no-push eval started at $(date --iso-8601=seconds)"
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

run_condition "Unitree-Go2-Stand" "${E0_RUN}"
run_condition "Unitree-Go2-FR-Failure-Default-Stand" "${E1_RUN}"
run_condition "Unitree-Go2-FR-Failure-Tripod-Stand" "${E2_RUN}"

echo
echo "[INFO] v1 height23 paper-stance no-push eval finished at $(date --iso-8601=seconds)"
