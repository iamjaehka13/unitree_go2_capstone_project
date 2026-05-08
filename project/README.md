# Unitree Go2 3-Leg Failure Robustness Project

이 폴더는 Unitree Go2의 한 다리 고장 상황에서 초기 자세가 PPO 학습 효율과 외란 강건성에 미치는 영향을 분석하기 위한 프로젝트 작업 공간이다.

원본 학습/시뮬레이션 코드는 최대한 유지하고, 이 폴더에는 실험 설정, 실행 스크립트, 평가 결과, 발표용 시각화 자료를 분리해서 관리한다.

범위를 줄인 실제 실행 기준은 `docs/experiment_scope_v1.md`를 따른다. 이 README는 전체 청사진이고, v1 문서는 첫 번째로 완성할 최소 실험 프로토콜이다. 현재 seed 0 본 실험은 E0/E1/E2/E3 모두 `4096` parallel env, `5000` PPO iterations로 완료했다.

## 팀원이 먼저 보면 좋은 순서

처음 보는 사람은 아래 순서로 읽으면 된다.

| 순서 | 파일 | 목적 |
| --- | --- | --- |
| 1 | `docs/project_handoff_for_teammate.md` | 현재 프로젝트 상태, 실험군, 영상/결과 위치를 한 번에 파악 |
| 2 | `docs/full_project_explanation_ko.md` | 연구 배경, 제어 구조, 실험 설계, 결과 해석을 자세히 확인 |
| 3 | `docs/presentation_outline_ko.md` | PPT 흐름과 슬라이드별 말할 내용 확인 |
| 4 | `docs/experiment_scope_v1.md` | 왜 E0/E1/E2/E3, strict, clean, locked/tucked 조건이 생겼는지 확인 |
| 5 | `docs/current_v1_results_seed0.md` | seed 0 결과와 보고서에서 사용할 해석 확인 |
| 6 | `docs/training_env_reward_plan.md` | reward, termination, clean tripod 기준 확인 |
| 7 | `docs/push_visualization_plan.md` | 외란 영상과 공/화살표 시각화 기준 확인 |

영상과 그림도 Git에 포함되어 있다. 발표용으로 먼저 볼 파일은 아래다.

| 용도 | 우선 확인 파일 |
| --- | --- |
| clean 3족 지지 no-push 영상 | `project/videos/clean_tripod/E2C_tripod_clean_no_push_final.mp4` |
| locked/tucked 보조 영상 | `project/videos/clean_tripod/E4L_locked_tucked_clean_no_push.mp4` |
| push side-by-side 영상 | `project/videos/push/FR_E1_E2_E3_medium_right_calibrated_side_by_side.mp4` |
| E2 push 성공 예시 | `project/videos/push/E2_tripod_medium_right_calibrated_success.mp4` |
| E2 push 실패 예시 | `project/videos/push/E2_tripod_medium_front_calibrated_fail.mp4` |
| clean no-push 평가 CSV | `project/results/no_push_eval/no_push_eval_v5_clean_presentation_4096_5000_seed0.csv` |
| locked/tucked 평가 CSV | `project/results/no_push_eval/no_push_eval_v6_locked_tucked_presentation_4096_5000_seed0.csv` |
| calibrated push 평가 CSV | `project/results/push_eval/push_eval_v2_calibrated_final_seed0.csv` |

주의할 점은 v2 push 영상과 v5 clean standing 영상의 목적이 다르다는 것이다. v2 push 영상은 외란 시각화와 초기 robustness 분석용이고, v5 clean 영상은 "발바닥 세 개로 깔끔하게 서는가"를 보여주는 발표용 standing 결과다. E4L은 순수 passive torque-zero 조건이 아니라, 고장 다리를 접힌 상태로 기계적으로 lock한 보조 실험이다.

세부 정의:

- `docs/project_handoff_for_teammate.md`: 팀원이 바로 볼 수 있는 현재 상태 요약과 실행/자료 위치
- `docs/full_project_explanation_ko.md`: 프로젝트 전체 설명, 실험 설계, 결과 해석, 한계와 다음 작업
- `docs/presentation_outline_ko.md`: 졸업프로젝트 발표용 슬라이드 구성과 발표 멘트 초안
- `docs/torque_failure_model.md`: FR/RR 한 다리 전체 torque 0 고장 모델
- `docs/tripod_init_pose_fr.md`: FR 고장 조건의 tripod init pose 후보
- `docs/push_visualization_plan.md`: 외란 평가 발표용 영상/그래프 산출물 계획
- `docs/training_env_reward_plan.md`: v1 standing 학습 환경과 reward 세팅 기준
- `docs/current_v1_results_seed0.md`: 현재 seed 0 본 실험 결과와 해석 메모
- `docs/paper_reward_notes_2403_00398.md`: joint impairment 논문의 reward 반영 메모

현재 구현된 v1 task:

| Task ID | 의미 |
| --- | --- |
| `Unitree-Go2-Stand` | 4-leg baseline standing |
| `Unitree-Go2-FR-Failure-Default-Stand` | FR 전체 다리 torque 0 + 기본 standing init |
| `Unitree-Go2-FR-Failure-Tripod-Stand` | FR 전체 다리 torque 0 + tripod init |
| `Unitree-Go2-FR-Failure-Init-Curriculum-Stand` | FR 전체 다리 torque 0 + tripod-to-default init curriculum |
| `Unitree-Go2-FR-Failure-Default-Strict-Stand` | FR failure + default init + strict support geometry reward |
| `Unitree-Go2-FR-Failure-Tripod-Strict-Stand` | FR failure + tripod init + strict support geometry reward |
| `Unitree-Go2-FR-Failure-Init-Curriculum-Strict-Stand` | FR failure + init curriculum + strict support geometry reward |
| `Unitree-Go2-FR-Failure-Default-Clean-Stand` | FR failure + default init + clean foot-only tripod reward |
| `Unitree-Go2-FR-Failure-Tripod-Clean-Stand` | FR failure + tripod init + clean foot-only tripod reward |
| `Unitree-Go2-FR-Failure-Locked-Tucked-Clean-Stand` | FR torque-zero + mechanically locked/tucked FR leg + clean foot-only tripod reward |
| `Unitree-Go2-FR-Failure-Init-Curriculum-Clean-Stand` | FR failure + init curriculum + clean foot-only tripod reward |

기본 smoke test는 주요 standing task의 reset/step 및 1-iteration PPO 학습까지 통과했다.

```bash
project/.venv/bin/python scripts/train.py Unitree-Go2-Stand --env.scene.num-envs 2 --agent.max-iterations 1 --agent.save-interval 1 --gpu-ids None
project/.venv/bin/python scripts/train.py Unitree-Go2-FR-Failure-Default-Stand --env.scene.num-envs 2 --agent.max-iterations 1 --agent.save-interval 1 --gpu-ids None
project/.venv/bin/python scripts/train.py Unitree-Go2-FR-Failure-Tripod-Stand --env.scene.num-envs 2 --agent.max-iterations 1 --agent.save-interval 1 --gpu-ids None
project/.venv/bin/python scripts/train.py Unitree-Go2-FR-Failure-Init-Curriculum-Stand --env.scene.num-envs 2 --agent.max-iterations 1 --agent.save-interval 1 --gpu-ids None
```

학습 후 로그 추출과 no-push checkpoint 평가는 아래 스크립트로 시작한다.

```bash
project/.venv/bin/python project/scripts/extract_training_logs.py
project/.venv/bin/python project/scripts/plot_learning_curves.py

project/.venv/bin/python project/scripts/eval_no_push.py \
  --task Unitree-Go2-FR-Failure-Tripod-Stand \
  --checkpoint logs/rsl_rl/go2_fr_failure_tripod_stand/<run>/model_0.pt \
  --episodes 20 \
  --num-envs 20 \
  --seed 0 \
  --device cpu

E0_RUN=logs/rsl_rl/go2_stand/<run> \
E1_RUN=logs/rsl_rl/go2_fr_failure_default_stand/<run> \
E2_RUN=logs/rsl_rl/go2_fr_failure_tripod_stand/<run> \
E3_RUN=logs/rsl_rl/go2_fr_failure_init_curriculum_stand/<run> \
bash project/scripts/run_v2_no_push_eval_seed0_4096_5000.sh

project/.venv/bin/python project/scripts/plot_no_push_eval.py
```

분석 산출물 기본 위치:

| 산출물 | 위치 |
| --- | --- |
| 학습 scalar CSV | `project/results/training_logs/training_logs.csv` |
| 학습 curve 그림 | `project/results/figures/learning_curves/` |
| no-push 평가 CSV | `project/results/no_push_eval/no_push_eval_v2_4096_5000_seed0.csv` |
| no-push 평가 그림 | `project/results/figures/no_push_eval_v2_4096_5000_seed0/` |
| final cross-eval CSV | `project/results/no_push_eval/cross_eval_v2_final_seed0.csv` |
| calibrated push 평가 CSV | `project/results/push_eval/push_eval_v2_calibrated_final_seed0.csv` |
| calibrated push 평가 그림 | `project/results/figures/push_eval_v2_calibrated_final_seed0/` |
| push 발표용 영상 | `project/videos/push/` |

현재 seed 0 본 실험 결과는 아래 위치에 정리되어 있다.

```text
project/docs/current_v1_results_seed0.md
project/results/no_push_eval/no_push_eval_v2_4096_5000_seed0.csv
project/results/figures/no_push_eval_v2_4096_5000_seed0/
project/results/no_push_eval/cross_eval_v2_final_seed0.csv
```

이전 contact-penalty pilot은 낮게 접힌 자세로 foot contact를 유지하는 문제가 있었다. 현재 본 실험은 base height `< 0.23 m`를 fall로 처리하고, height/upright 및 FR tripod contact reward를 적용한 기준으로 진행한다.

```bash
project/scripts/run_v2_training_5000_seed0_4096.sh
```

현재 seed 0 핵심 결과:

| ID | 조건 | 최종 no-push strict success | 해석 |
| --- | --- | ---: | --- |
| E0 | 4-leg baseline | 1.00 | 정상 기준선 성공 |
| E1 | FR failure + default init | 0.00 | default init에서는 5000 iter 후에도 초기 실패 |
| E2 | FR failure + tripod init | 1.00 | tripod prior로 안정 3족 지지 성공 |
| E3 | FR failure + init curriculum | 1.00 | curriculum으로 default-init 성공 policy 형성 |

Final policy cross-eval:

| Policy | default-init eval | tripod-init eval | 해석 |
| --- | ---: | ---: | --- |
| E1 | 실패 | 실패 | 안정화 전략 학습 실패 |
| E2 | 실패 | 성공 | tripod pose에 특화 |
| E3 | 성공 | 실패 | default init에서 서는 별도 전략 학습 |

Strict tripod recheck:

| Policy | old strict | kinematic tripod | new tripod success | 해석 |
| --- | ---: | ---: | ---: | --- |
| E2 | 1.00 | 0.00 | 0.00 | 기존 기준은 통과하지만 COM support polygon 기준 실패 |
| E3 | 1.00 | 0.00 | 0.00 | 기존 기준은 통과하지만 support area/COM 기준 실패 |

따라서 v2 결과는 폐기하지 않고 "약한 기준에서 PPO가 찾은 local optimum"으로 보존한다. 기구학적으로 방어 가능한 3족 지지는 E1S/E2S/E3S strict task에서 다시 학습한다.

```bash
bash project/scripts/run_v3_strict_training_5000_seed0_4096.sh
```

Foot-only strict update:

Calf/thigh/body로 버티는 자세를 막기 위해 v4 foot-only 기준을 추가했다. v4는 support geometry에 더해 non-foot ground contact를 직접 벌점화하고, illegal contact threshold를 `1 N`으로 낮춘다. 또한 reset 직후 발이 지면에 더 가깝도록 Go2 init base height를 `0.295 m`로 조정했다.

```bash
bash project/scripts/run_v4_footonly_training_5000_seed0_4096.sh
```

Clean tripod update:

영상 확인 중 contact sensor의 실제 foot order가 `FL, FR, RL, RR`임을 확인했다. 기존 reward/eval에서 `FR, FL, RR, RL`로 가정하던 부분을 수정했고, v5 clean task를 추가했다. v5는 진짜 `FR` disabled foot을 벌점화하고, `FL/RL/RR` 세 발바닥 지지, support load, FR foot clearance, base height/upright를 함께 강제한다.

```bash
bash project/scripts/run_v5_clean_tripod_training_5000_seed0_4096.sh
bash project/scripts/run_v5_clean_no_push_eval_seed0_4096_5000.sh
```

Clean tripod 발표 영상은 아래 스크립트로 생성한다. 영상에는 `FR` foot clearance, `FL/RL/RR` support foot contact/load, non-foot contact 여부, support triangle/COM margin 판정이 함께 overlay된다.

```bash
bash project/scripts/render_v5_clean_tripod_videos_seed0.sh
```

`render_push_video.py`도 같은 clean-tripod overlay를 사용하므로, 공/화살표 push 시각화와 foot-only tripod 판정을 한 영상에서 함께 보여줄 수 있다.

v5 clean 평가는 두 기준을 분리한다. Strict metric은 roll/pitch `10 deg`, last-window fraction `0.95`이고, 발표용 presentation-clean metric은 roll/pitch `12 deg`, last-window fraction `0.90`이다. 기본 v5 eval runner는 presentation-clean CSV를 생성한다.

Locked/tucked extension:

FR torque-zero passive leg가 영상에서 흔들리는 현상을 분리하기 위해 E4L locked/tucked failure를 추가했다. E4L은 FR actuator torque는 계속 0으로 두되, FR hip/thigh/calf joint range를 tuck pose 주변 `+-0.001 rad`로 제한해 기계적으로 접힌 고장 다리처럼 모델링한다. 따라서 E4L은 E1C/E2C/E3C의 torque-zero passive-leg 메인 실험을 대체하지 않고, "failed leg swing을 제거했을 때 발표용 tripod stance가 얼마나 깔끔해지는가"를 확인하는 보조 실험으로 사용한다.

```bash
bash project/scripts/run_v6_locked_tucked_training_5000_seed0_4096.sh
bash project/scripts/run_v6_locked_tucked_no_push_eval_seed0_4096_5000.sh
bash project/scripts/render_v6_locked_tucked_video_seed0.sh
```

E4L seed 0 final no-push presentation-clean 평가는 20/20 episode에서 `tripod_success=1.00`이다. 발표용 영상은 `project/videos/clean_tripod/E4L_locked_tucked_clean_no_push.mp4`에 저장된다.

Calibrated push 결과:

| Policy | Eval init | push success | survival success | 해석 |
| --- | --- | ---: | ---: | --- |
| E1 | default | 0.00 | 0.00 | push 전에 이미 무너지는 실패 reference |
| E2 | tripod | 0.33 | 0.33 | 방향 의존적으로 weak/medium push 일부 성공 |
| E3 | default | 0.00 | 0.08 | default standing은 가능하지만 strict tripod push 성공은 아직 없음 |

발표용 push 영상은 아래 파일을 우선 생성했다.

```text
project/videos/push/E1_default_medium_right_calibrated_fail.mp4
project/videos/push/E2_tripod_medium_back_calibrated_success.mp4
project/videos/push/E2_tripod_medium_front_calibrated_fail.mp4
project/videos/push/E2_tripod_medium_right_calibrated_success.mp4
project/videos/push/E3_default_medium_right_calibrated_survive_not_strict.mp4
project/videos/push/FR_E1_E2_E3_medium_right_calibrated_side_by_side.mp4
```

## 1. 핵심 연구 질문

한 다리의 토크를 0으로 둔 3-leg failure 조건에서, 학습 초기 자세를 기본 4족 standing pose로 두는 경우, 기구학적으로 안정한 tripod pose로 두는 경우, 그리고 tripod-to-default init curriculum을 주는 경우는 어떤 차이를 만드는가?

분석할 핵심은 다음과 같다.

- 초기 자세가 학습 초반 실패율을 줄이는가?
- 초기 자세가 PPO의 수렴속도와 learning curve를 개선하는가?
- 최종 policy의 자세, 토크 분포, 접촉력, 에너지 사용이 달라지는가?
- 같은 외란 조건에서 tripod init으로 학습한 policy가 더 강건한가?
- 기구학적으로 설계한 tripod pose와 policy가 최종적으로 찾은 pose가 얼마나 유사한가?
- E3 curriculum이 default-init exploration bottleneck을 완화하는가?

## 2. 비교 조건

### 2.1 Main Comparison

| 조건 | 로봇 상태 | 학습 초기 자세 | 목적 |
| --- | --- | --- | --- |
| 4-leg baseline | 모든 다리 정상 | 기본 standing init | 정상 4족 성능 상한선 |
| 3-leg default init | 한 다리 torque 0 | 기본 standing init | 고장 상황에서 일반 초기 자세의 한계 분석 |
| 3-leg tripod init | 한 다리 torque 0 | 기구학적 tripod init | 안정 초기 자세가 학습과 강건성에 주는 효과 분석 |
| 3-leg init curriculum | 한 다리 torque 0 | tripod-to-default reset curriculum | 초기 탐색 보조가 default-init policy 학습을 가능하게 하는지 분석 |

고장 다리는 main experiment에서 `FR`로 고정한다. `RR`은 FR 파이프라인을 완성한 뒤 결론의 일반성을 확인하는 extension으로 둔다.

### 2.2 Optional Extension

필요하면 고장 다리를 바꾼 추가 실험을 수행한다.

| 추가 조건 | 목적 |
| --- | --- |
| front leg failure | 앞다리 고장에 대한 안정성 분석 |
| rear leg failure | 뒷다리 고장에 대한 안정성 분석 |
| left/right failure | 좌우 방향 외란과 지지 삼각형의 관계 분석 |

단, 졸업프로젝트 범위에서는 먼저 하나의 고장 다리로 실험 프로토콜을 완성한 뒤 확장한다.

## 3. 학습 단계 평가

학습 단계에서는 PPO가 얼마나 빠르고 안정적으로 정책을 형성하는지 본다.

### 3.1 주요 지표

| 지표 | 의미 |
| --- | --- |
| 초기 실패율 | 학습 초반 episode에서 일정 시간 안에 넘어지는 비율 |
| survival time | episode가 종료되기 전까지 버틴 시간 |
| learning curve | iteration별 return, episode length, fall rate 변화 |
| 수렴속도 | 목표 성능 threshold에 도달하는 데 필요한 iteration 또는 sample 수 |
| seed variance | seed별 성능 편차 |

### 3.2 예상 가설

3-leg default init은 한 다리 torque가 사라졌는데도 기본 4족 자세에서 시작하므로, 초기 COM과 지지 상태가 불안정할 가능성이 높다. 따라서 PPO가 초반에 "넘어지지 않는 자세"를 찾는 데 많은 sample을 사용할 수 있다.

3-leg tripod init은 시작 시점부터 3족 지지에 가까우므로 초기 실패율이 낮고, PPO가 자세 회복보다 균형 유지와 외란 대응 전략을 더 빨리 학습할 가능성이 있다.

3-leg init curriculum은 학습 초반에는 tripod 근처에서 시작해 초기 생존 시간을 확보하고, 학습 후반에는 default init 근처로 reset 분포를 이동시킨다. 따라서 E1이 실패하고 E3가 성공하면, default init의 문제가 policy capacity 부족이 아니라 초기 exploration bottleneck이었다고 해석할 수 있다.

## 4. PPO 학습 과정 분석

신경망 내부 hidden layer가 정확히 어떤 의미의 최적해를 찾았다고 단정하지 않는다. 대신 policy의 행동과 로봇 물리 상태가 학습 중 어떻게 변화하는지를 분석한다.

### 4.1 분석할 항목

| 항목 | 해석 |
| --- | --- |
| entropy | 탐색 정도가 학습 중 어떻게 줄어드는지 |
| action std | policy의 행동 분포가 얼마나 안정화되는지 |
| KL divergence | PPO update가 얼마나 크게 일어나는지 |
| policy/value loss | 최적화 과정의 안정성 |
| reward term별 변화 | 어떤 reward가 성능 개선에 기여했는지 |
| checkpoint별 자세 변화 | 학습 중 policy가 어떤 standing strategy로 수렴하는지 |

### 4.2 Checkpoint Pose Analysis

동일 조건에서 여러 checkpoint를 평가한다.

- 초기 checkpoint
- 중간 checkpoint
- 수렴 직전 checkpoint
- final checkpoint

각 checkpoint에서 기록할 값:

- base height
- base roll/pitch/yaw
- joint position
- action target
- joint torque
- foot contact state
- foot contact force
- foot slip
- COM 위치
- support polygon과 COM 관계

이 분석의 표현은 다음처럼 가져간다.

> PPO가 학습 과정에서 어떤 자세 안정화 전략을 형성했는지 분석한다.

"hidden layer가 최적해를 직접 찾는 과정"이라고 표현하지 않는다.

## 5. 외란 강건성 평가

외란 평가는 E1/E2/E3 policy를 같은 정적 3족 지지 상태 또는 같은 default-init 상태에서 시작시켜 비교한다. E3는 curriculum task 자체 평가와 fixed-init cross-eval을 분리한다.

### 5.1 기본 외란 조건

| 항목 | 조건 |
| --- | --- |
| 시작 상태 | 정적 3족 지지 상태 |
| 방향 | 앞, 뒤, 좌, 우 |
| 형태 | 순간적 타격, 일정 시간 지속 force |
| 크기 | 약, 중, 강 |

외란 크기는 가능하면 단순 force보다 impulse 기준으로 정리한다.

```text
impulse = force * duration
```

또는 로봇 무게 기준으로 정규화한다.

```text
weak   = 0.5 * body_weight
medium = 1.0 * body_weight
strong = 1.5 * body_weight
```

### 5.2 외란 평가 지표

| 지표 | 의미 |
| --- | --- |
| 목표 도달률 | 외란 후 지정된 안정 조건을 만족한 비율 |
| 생존 시간 | 외란 후 넘어지지 않고 버틴 시간 |
| 자세 회복 시간 | roll/pitch/base height가 정상 범위로 돌아오는 데 걸린 시간 |
| 최대 자세 흔들림 | 외란 후 최대 roll/pitch 변화 |
| COM displacement | 외란 후 COM 이동량 |
| foot slip | 발 미끄러짐 정도 |
| energy | torque 기반 에너지 소모량 |

## 6. 일반화 평가

학습 조건과 다른 환경에서 policy가 얼마나 유지되는지 본다.

| 일반화 조건 | 예시 |
| --- | --- |
| 마찰 계수 변화 | 낮음, 기본, 높음 |
| 질량 변화 | base mass 증가 또는 감소 |
| COM 변화 | 앞/뒤/좌/우 방향 offset |

일반화 평가는 main result가 아니라 보조 결과로 둔다. 기본 실험이 완성된 뒤 추가한다.

## 7. 최종 자세와 토크 비교

최종 policy가 실제로 어떤 안정화 해를 찾았는지 비교한다.

| 분석 항목 | 비교 내용 |
| --- | --- |
| final standing pose | default-init policy, tripod-init policy, init-curriculum policy의 평균 joint angle 비교 |
| designed tripod pose vs learned pose | 사람이 설계한 tripod init과 policy가 수렴한 자세의 차이 |
| torque distribution | 정상 3다리에 토크가 어떻게 분산되는지 |
| disabled leg action | 고장난 다리에 대해 policy가 어떤 action을 내는지 |
| contact force | 세 지지 발에 하중이 어떻게 분산되는지 |
| energy consumption | 안정 유지에 필요한 에너지 차이 |

## 8. 시각화 계획

### 8.1 발표용 영상

동일한 push 조건에서 policy를 side-by-side로 보여준다.

| Push Level | E1 default policy | E2 tripod policy | E3 curriculum policy |
| --- | --- | --- | --- |
| weak | video | video | video |
| medium | video | video | video |
| strong | video | video | video |

영상에는 다음 정보를 오버레이한다.

- push 방향 화살표
- push 크기
- 현재 시간
- fall 여부
- recovery time

### 8.2 발표용 그래프

- learning curve 비교
- 초기 실패율 막대그래프
- 수렴속도 비교
- push direction x push magnitude 성공률 heatmap
- base roll/pitch 회복 곡선
- torque norm 비교
- foot slip 비교
- COM trajectory 비교

## 9. 폴더 구조

```text
project/
  README.md
  configs/    # 실험 조건 yaml/json
  docs/       # 설계 메모, 발표용 분석 문서
  scripts/    # 학습 실행, 평가, 로그 추출, 영상 생성 스크립트
  results/    # 평가 csv/json, 그래프 결과
  videos/     # push 시각화 영상
```

## 10. 구현 로드맵

### Phase 1: 실험 조건 확정

- 고장 다리 하나 선택
- 기본 standing init 확인
- tripod init pose 설계
- torque zero 적용 방식 결정
- 4-leg baseline 포함 범위 확정

### Phase 2: 학습 환경 구성

- 4-leg baseline task
- 3-leg default init task
- 3-leg tripod init task
- 3-leg init curriculum task
- 각 task의 log 이름과 seed 관리 방식 정리

### Phase 3: 학습 실행 및 로그 수집

- 최소 3개 seed로 학습
- 초기 실패율, return, episode length, fall rate 저장
- checkpoint별 policy 저장

### Phase 4: 정적 3족 외란 평가

- push direction: front/back/left/right
- push type: impulse/sustained
- push magnitude: weak/medium/strong
- 각 조건 반복 평가
- 성공률, 회복 시간, 흔들림, 에너지 저장

### Phase 5: 자세 전략 분석

- checkpoint별 pose/torque/contact force 추출
- designed tripod pose와 learned pose 비교
- default-init policy, tripod-init policy, init-curriculum policy의 최종 전략 비교

### Phase 6: 발표 자료 생성

- side-by-side push 영상
- learning curve
- robustness heatmap
- final pose/torque 비교표
- 핵심 결론 정리

## 11. 최종 발표에서 말할 핵심 구조

1. 한 다리 고장 상황에서는 초기 자세가 PPO의 탐색 공간과 초기 실패율에 영향을 준다.
2. 기구학적 tripod init은 학습 초반 실패를 줄이고, policy가 안정화 전략을 더 빨리 형성하도록 도울 수 있다.
3. E3 init-pose curriculum은 default init에서의 PPO exploration bottleneck을 완화할 수 있다.
4. 최종 policy의 강건성은 같은 정적 3족 지지 상태와 fixed-init cross-eval에서 동일 외란을 넣어 비교한다.
5. 외란 방향과 크기별 성공률, 회복 시간, 자세 흔들림, 에너지 사용량으로 robust policy인지 판단한다.
6. policy가 찾은 최종 자세와 사람이 설계한 tripod pose를 비교해, 강화학습이 어떤 안정화 전략으로 수렴했는지 해석한다.
