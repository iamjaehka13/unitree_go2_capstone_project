# Project Handoff for Teammate

이 문서는 팀원이 저장소를 처음 봤을 때 현재 프로젝트가 어디까지 왔는지, 어떤 파일을 보면 되는지, 발표에서 무엇을 주장해야 하는지 빠르게 파악하기 위한 안내서다.

## 1. 프로젝트 한 줄 요약

핵심 질문은 다음이다.

> Unitree Go2의 FR 다리 전체 actuator torque가 0인 고장 상황에서, 기구학적으로 안정한 tripod 자세 prior가 PPO의 학습 효율과 3족 지지 안정성을 얼마나 개선하는가?

처음에는 단순히 `default init`과 `tripod init`을 비교했다. 이후 영상 확인 과정에서 "성공으로 찍혔지만 실제로는 calf/body에 기대거나, 고장 다리가 흔들리는" 문제가 보여서 평가 기준과 reward를 더 엄격하게 만들었다. 그래서 현재 문서에는 v2, v3, v4, v5, v6라는 단계가 함께 남아 있다.

이건 실험이 망가졌다는 뜻이 아니라, 평가 기준을 사람이 납득 가능한 clean tripod stance로 계속 강화해 온 과정이다.

더 자세한 설명은 아래 두 문서를 보면 된다.

| 문서 | 내용 |
| --- | --- |
| `full_project_explanation_ko.md` | 연구 배경, 제어 구조, 실험 설계, reward/eval 변화, 결과 해석, 남은 일 |
| `presentation_outline_ko.md` | PPT 슬라이드 순서, 각 슬라이드에서 보여줄 파일, 발표 멘트 |

## 2. 실험 조건 이름

기본 비교군은 아래 네 개다.

| ID | 의미 | 해석 |
| --- | --- | --- |
| E0 | 4-leg baseline | 정상 4족 reference |
| E1 | FR failure + default init | 기구학 prior 없이 시작 |
| E2 | FR failure + tripod init | 기구학적 tripod 자세 prior 사용 |
| E3 | FR failure + tripod-to-default init curriculum | 처음에는 tripod 근처에서 시작하고 점점 default init으로 이동 |

이후 clean stance를 만들기 위해 추가된 조건은 아래다.

| ID | 의미 | 주의 |
| --- | --- | --- |
| E1C | FR failure + default init + clean tripod reward | clean reward로 재학습한 default-init 조건 |
| E2C | FR failure + tripod init + clean tripod reward | 발표용 clean tripod stance의 메인 후보 |
| E3C | FR failure + init curriculum + clean tripod reward | clean 기준에서 curriculum 효과 확인용 |
| E4L | FR failure + locked/tucked FR joints + clean tripod reward | 고장 다리를 접힌 상태로 lock한 보조 실험 |

E4L은 FR actuator torque를 0으로 두지만, FR hip/thigh/calf joint range를 tuck pose 주변으로 거의 고정한다. 따라서 "순수한 passive torque-zero 다리"가 아니라 "기계적으로 접힌 고장 다리" 조건이다. 발표에서는 메인 비교군이 아니라 supplementary result로 쓰는 게 안전하다.

## 3. 왜 실험 버전이 여러 개인가

처음 v2 결과에서는 E1은 실패하고, E2와 E3는 성공했다. 이 결과만 보면 "tripod init 또는 curriculum이 PPO의 초기 exploration bottleneck을 풀어준다"는 주장을 만들 수 있다.

하지만 영상으로 확인하니, 성공 기준이 사람이 기대한 "세 발바닥으로 깔끔하게 서기"를 충분히 보장하지 못했다. 특히 다음 문제가 있었다.

- base height 기준이 약하면 낮게 접힌 자세도 성공으로 찍힐 수 있음
- calf/thigh/body가 닿아도 foot contact 기준만 보면 성공처럼 보일 수 있음
- foot contact sensor order를 잘못 가정하면 FR disabled foot과 support foot 판정이 뒤섞임
- torque-zero passive FR 다리가 관성 때문에 흔들려 발표 영상이 지저분해 보일 수 있음

그래서 프로젝트 흐름은 이렇게 정리한다.

| 단계 | 목적 |
| --- | --- |
| v2 | 초기 자세 prior와 PPO exploration 차이를 확인 |
| v3 | support polygon, COM margin 같은 기구학 기준 강화 |
| v4 | calf/thigh/body contact를 금지하는 foot-only 기준 추가 |
| v5 | foot sensor order 수정, FR clearance와 support load를 포함한 clean tripod 기준 추가 |
| v6 | FR passive leg 흔들림을 분리하기 위한 locked/tucked 보조 실험 |

발표에서는 이 과정을 "평가 기준을 강화하면서 local optimum을 걸러낸 과정"으로 설명하면 된다.

## 4. 현재 가장 중요한 결과

### v2 main result

파일:

```text
project/results/no_push_eval/no_push_eval_v2_4096_5000_seed0.csv
project/results/no_push_eval/cross_eval_v2_final_seed0.csv
project/results/push_eval/push_eval_v2_calibrated_final_seed0.csv
```

요약:

| 조건 | no-push 결과 | 해석 |
| --- | --- | --- |
| E1 default init | 실패 | default init에서는 episode가 너무 빨리 끝나 PPO가 안정 전략을 못 찾음 |
| E2 tripod init | 성공 | tripod prior가 초기 탐색을 살려 sample efficiency를 개선 |
| E3 init curriculum | 성공 | curriculum이 default-init exploration bottleneck을 완화 |

cross-eval에서 E2는 tripod init에서는 성공하지만 default init에서는 실패했고, E3는 default init에서는 성공하지만 tripod init에는 일반화되지 않았다. 따라서 E2와 E3는 같은 자세를 배운 것이 아니라 서로 다른 안정화 전략으로 해석한다.

### v5 clean standing result

파일:

```text
project/results/no_push_eval/no_push_eval_v5_clean_presentation_4096_5000_seed0.csv
project/videos/clean_tripod/E1C_default_clean_no_push.mp4
project/videos/clean_tripod/E2C_tripod_clean_no_push_final.mp4
project/videos/clean_tripod/E3C_default_clean_no_push.mp4
```

presentation-clean 기준에서 E1C와 E2C는 모두 no-push 3족 지지에 성공했다. 평균적으로 `FR` foot contact fraction은 약 `0.03` 이하이고, non-foot contact fraction은 `0.00`이다. support foot load도 약 `45 N` 수준으로 세 지지 발바닥이 실제로 하중을 받는다.

중요한 해석:

> v5 clean 결과는 v2와 reward/eval 기준이 달라진 재학습 결과다. 따라서 v2 결론을 대체한다기보다, 발표용으로 "진짜 발바닥 3개로 서는 clean stance"를 만들기 위해 기준을 강화한 결과로 설명한다.

### v6 locked/tucked result

파일:

```text
project/results/no_push_eval/no_push_eval_v6_locked_tucked_presentation_4096_5000_seed0.csv
project/videos/clean_tripod/E4L_locked_tucked_clean_no_push.mp4
```

E4L은 20/20 episode에서 presentation-clean `tripod_success=1.00`이다.

대표 평균값:

| 지표 | 값 |
| --- | ---: |
| survival success | `1.00` |
| tripod success | `1.00` |
| final base height | 약 `0.284 m` |
| final roll/pitch | 약 `0.79 deg` / `2.92 deg` |
| FR contact fraction | `0.00` |
| FR foot height | 약 `0.092 m` |
| support min force | 약 `47.4 N` |
| support area | 약 `0.066 m2` |
| COM margin | 약 `0.101 m` |
| non-foot contact fraction | `0.00` |

해석:

> E4L은 발표 영상으로 가장 깔끔하다. 다만 순수 passive torque-zero failure가 아니므로, 메인 과학적 결론은 E1/E2/E3 또는 E1C/E2C/E3C를 중심으로 말하고, E4L은 "failed leg swing을 제거한 보조 조건"으로 보여준다.

## 5. Push 결과와 영상

push 평가는 `base_link`에 실제 external force impulse를 인가한다. 발표용 calibrated 기준은 다음이다.

| Level | Force multiplier | Force |
| --- | ---: | ---: |
| weak | `0.25 BW` | 약 `37 N` |
| medium | `0.35 BW` | 약 `52 N` |
| strong | `0.45 BW` | 약 `67 N` |

파일:

```text
project/results/push_eval/push_eval_v2_calibrated_final_seed0.csv
project/results/figures/push_eval_v2_calibrated_final_seed0/
project/videos/push/FR_E1_E2_E3_medium_right_calibrated_side_by_side.mp4
```

요약:

| Policy | Eval init | push success | survival success | 해석 |
| --- | --- | ---: | ---: | --- |
| E1 | default | `0.00` | `0.00` | push 전에 이미 무너지는 실패 reference |
| E2 | tripod | `0.33` | `0.33` | back/right weak/medium에는 일부 성공 |
| E3 | default | `0.00` | `0.08` | no-push standing은 가능하지만 strict tripod push 성공은 부족 |

발표에서 조심할 점:

- 이 push 결과는 v2 final policy 기준이다.
- clean tripod overlay가 들어간 push 렌더러는 준비되어 있지만, 최종 clean policy push 전체 평가는 아직 보강 여지가 있다.
- 현재 결과로는 "tripod prior가 외란까지 완전히 강건하게 만든다"가 아니라, "no-push standing 학습은 개선되지만 외란 강건성은 별도 push-aware training이 필요하다"라고 말해야 한다.

발표용 영상:

```text
project/videos/push/E1_default_medium_right_calibrated_fail.mp4
project/videos/push/E2_tripod_medium_back_calibrated_success.mp4
project/videos/push/E2_tripod_medium_front_calibrated_fail.mp4
project/videos/push/E2_tripod_medium_right_calibrated_success.mp4
project/videos/push/E3_default_medium_right_calibrated_survive_not_strict.mp4
project/videos/push/FR_E1_E2_E3_medium_right_calibrated_side_by_side.mp4
```

## 6. 친구가 바로 실행할 명령

현재 결과를 다시 뽑는 주요 명령은 아래다.

```bash
# v2 learning/no-push/push plots
project/.venv/bin/python project/scripts/extract_training_logs.py
project/.venv/bin/python project/scripts/plot_learning_curves.py
project/.venv/bin/python project/scripts/plot_no_push_eval.py
project/.venv/bin/python project/scripts/plot_push_results.py \
  --input project/results/push_eval/push_eval_v2_calibrated_final_seed0.csv \
  --output-dir project/results/figures/push_eval_v2_calibrated_final_seed0

# v5 clean no-push eval
bash project/scripts/run_v5_clean_no_push_eval_seed0_4096_5000.sh

# v5 clean videos
bash project/scripts/render_v5_clean_tripod_videos_seed0.sh

# v6 locked/tucked eval and video
bash project/scripts/run_v6_locked_tucked_no_push_eval_seed0_4096_5000.sh
bash project/scripts/render_v6_locked_tucked_video_seed0.sh
```

학습을 새로 돌릴 때는 시간이 오래 걸린다.

```bash
bash project/scripts/run_v2_training_5000_seed0_4096.sh
bash project/scripts/run_v5_clean_tripod_training_5000_seed0_4096.sh
bash project/scripts/run_v6_locked_tucked_training_5000_seed0_4096.sh
```

## 7. 발표에서 안전한 주장

가장 방어 가능한 문장은 아래다.

> 한 다리 actuator torque가 0인 상황에서, 기본 standing init만으로 PPO를 학습하면 초반 episode가 너무 빨리 실패하여 안정 전략 탐색이 어렵다. 기구학적 tripod posture prior는 초기 실패율을 낮추고 학습 가능한 상태 공간으로 policy를 유도한다. 또한 tripod-to-default reset curriculum은 default init에서의 exploration bottleneck을 완화할 수 있다.

추가로 말할 수 있는 내용:

- 단순 생존 성공률만으로는 "제대로 선다"고 보기 어렵다.
- 그래서 base height, roll/pitch, support foot contact, FR foot clearance, support load, support triangle/COM margin, non-foot contact를 함께 보았다.
- clean tripod 기준을 추가하니 발표 영상에서 사람이 봐도 납득 가능한 3족 지지 자세를 만들 수 있었다.
- push 강건성은 아직 충분하지 않다. 현재는 calibrated push 일부 조건에서만 성공하므로, 최종 robust policy를 만들려면 push randomization 또는 push-aware curriculum이 필요하다.

## 8. 발표에서 피해야 할 주장

아래 표현은 피하는 게 좋다.

| 피할 표현 | 이유 |
| --- | --- |
| "PPO hidden layer가 어떤 최적해를 찾는지 분석했다" | hidden layer 의미를 직접 증명한 것이 아님 |
| "tripod init이면 외란에도 강건하다" | 현재 push 결과는 방향 의존적이고 성공률이 제한적임 |
| "E4L이 메인 고장 모델이다" | E4L은 locked/tucked extension이고, passive torque-zero와 다름 |
| "v2 성공은 완전히 깨끗한 3족 지지다" | v2는 약한 기준의 local optimum으로 보존하고, clean 주장은 v5/v6에서 함 |

대신 이렇게 말한다.

> PPO policy가 학습 과정에서 어떤 물리적 자세 안정화 전략으로 수렴하는지, joint angle, contact force, support geometry, 영상 overlay를 통해 분석했다.

## 9. 남은 일

졸업프로젝트 발표 완성도 기준으로 남은 우선순위는 아래다.

| 우선순위 | 작업 | 목적 |
| --- | --- | --- |
| 1 | clean policy push 영상 추가 생성 | clean stance와 외란 시각화를 같은 영상에서 보여주기 |
| 2 | E1C/E2C/E3C learning curve 정리 | clean reward 기준에서도 init 효과가 어떻게 달라졌는지 확인 |
| 3 | seed 추가 | PPO 랜덤성 방어 |
| 4 | PPT용 figure 선별 | 결과가 너무 많아서 핵심만 보여주기 |
| 5 | 가능하면 push-aware training pilot | 외란 강건성 한계 보완 |

시간이 부족하면 1, 2, 4만 해도 발표 흐름은 만들 수 있다.

## 10. GitHub에 올라간 것과 안 올라간 것

올라간 것:

- `project/docs/`
- `project/scripts/`
- `project/results/no_push_eval/`
- `project/results/push_eval/`
- `project/results/figures/`
- `project/results/training_logs/`
- `project/videos/`

일부러 제외한 것:

- `.venv/`
- `project/.venv/`
- `logs/`
- `project/results/training_runs/` 대용량 raw 학습 로그

대용량 raw log는 로컬에는 있지만 GitHub에는 올리지 않았다. 발표와 친구 확인에는 CSV, figure, video만으로 충분하다.
