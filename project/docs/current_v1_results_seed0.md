# Current v1 Seed 0 Results

이 문서는 현재 seed 0 기준으로 완료한 본 실험 결과를 발표/보고서에서 어떻게 해석할지 정리한 메모다.

## 1. 실행된 학습 조건

본 실험은 모든 조건을 `4096` parallel env, `5000` PPO iterations로 학습했다.

| ID | 조건 | Run |
| --- | --- | --- |
| E0 | 4-leg baseline standing | `logs/rsl_rl/go2_stand/2026-05-06_19-16-09_v2_4096_5000_seed0_e0_four_leg` |
| E1 | FR failure + default init | `logs/rsl_rl/go2_fr_failure_default_stand/2026-05-06_20-24-01_v2_4096_5000_seed0_e1_fr_default` |
| E2 | FR failure + tripod init | `logs/rsl_rl/go2_fr_failure_tripod_stand/2026-05-06_21-37-52_v2_4096_5000_seed0_e2_fr_tripod` |
| E3 | FR failure + tripod-to-default init curriculum | `logs/rsl_rl/go2_fr_failure_init_curriculum_stand/2026-05-06_22-50-24_v2_4096_5000_seed0_e3_fr_init_curriculum` |

학습 로그:

```text
project/results/training_runs/v2_4096_5000_seed0_20260506_191650.log
```

No-push checkpoint 평가:

```text
project/results/no_push_eval/no_push_eval_v2_4096_5000_seed0.csv
project/results/figures/no_push_eval_v2_4096_5000_seed0/
```

Final policy cross-eval:

```text
project/results/no_push_eval/cross_eval_v2_final_seed0.csv
```

## 2. No-Push 최종 결과

최종 checkpoint `model_4999.pt` 기준 결과다. episode horizon은 `10.0 s`, initial failure는 reset 후 `2.0 s` 이내 실패로 계산했다.

| ID | survival success | strict success | tripod success | initial failure | mean survival time |
| --- | ---: | ---: | ---: | ---: | ---: |
| E0 | 1.00 | 1.00 | 1.00 | 0.00 | 10.00 s |
| E1 | 0.00 | 0.00 | 0.00 | 1.00 | 0.24 s |
| E2 | 1.00 | 1.00 | 1.00 | 0.00 | 10.00 s |
| E3 | 1.00 | 1.00 | 1.00 | 0.00 | 10.00 s |

핵심 관찰:

- E0는 정상 4족 기준선으로 쉽게 성공했다.
- E1은 `5000` iterations까지 학습해도 default init에서 계속 초기 실패했다.
- E2는 tripod init을 주면 안정적인 3족 지지를 학습했다.
- E3는 tripod-to-default reset curriculum을 사용했을 때 default init에서도 서는 policy를 학습했다.

따라서 현재 seed 0 결과는 "default init은 단순히 더 오래 학습하면 해결된다"가 아니라, "초기 탐색이 막혀 PPO가 안정 자세를 찾기 어렵다"는 해석을 지지한다.

## 3. Checkpoint별 학습 효율

No-push checkpoint 평가 요약:

| ID | 0 | 100 | 500 | 1000 | 2000 | 3000 | 4000 | 4999 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| E0 strict | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| E1 strict | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| E2 strict | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| E3 strict | 0.00 | 0.95 | 1.00 | 0.55 | 0.45 | 1.00 | 0.30 | 1.00 |

해석:

- E2는 `500` iteration부터 안정 성공률이 1.0으로 올라가며, tripod init이 sample efficiency를 크게 개선했다.
- E1은 모든 checkpoint에서 초기 실패율 1.0으로 남아, 순수 default init은 현재 reward/failure 조건에서 탐색이 불가능한 수준이다.
- E3는 중간 checkpoint에서 성능이 흔들리지만, 최종적으로 default init 성공 policy에 도달했다. 이는 curriculum 중 reset 분포가 계속 이동하기 때문에 학습 목표가 비정상적으로 변하는 구간이 있었던 것으로 해석한다.

## 4. Final Policy Cross-Eval

E3 task 자체 평가에는 reset curriculum 분포가 섞일 수 있으므로, final policy를 고정 default-init task와 고정 tripod-init task에서 다시 평가했다.

| Policy | default-init eval | tripod-init eval | mean survival time | 해석 |
| --- | ---: | ---: | ---: | --- |
| E1 policy | 0.00 | 0.00 | 0.24 s / 0.28 s | 안정화 전략 학습 실패 |
| E2 policy | 0.00 | 1.00 | 0.20 s / 10.00 s | tripod pose에 특화 |
| E3 policy | 1.00 | 0.00 | 10.00 s / 0.14 s | default init에서 서는 다른 전략 학습 |

이 결과가 가장 중요하다.

> E2는 안정적인 tripod init을 주면 잘 서지만, default init으로 바꾸면 실패한다.
> E3는 curriculum 덕분에 default init에서 서는 policy를 학습했지만, E2의 tripod 자세에 그대로 일반화되지는 않는다.

즉 E3는 E2를 단순히 복사한 policy가 아니라, default init에서 살아남기 위한 다른 자세 안정화 전략을 찾은 것으로 해석할 수 있다.

## 5. 최종 자세 전략 분석

성공한 두 조건을 비교했다.

- E2: E2 policy를 tripod-init env에서 평가
- E3: E3 policy를 default-init env에서 평가

값은 마지막 `2.0 s` 평균 실제 joint position이다.

| Leg | Joint | E2 | E3 | E3 - E2 |
| --- | --- | ---: | ---: | ---: |
| FL | hip | 0.148 | -0.090 | -0.239 |
| FL | thigh | 0.897 | 0.768 | -0.129 |
| FL | calf | -2.066 | -1.908 | 0.158 |
| FR disabled | hip | 1.048 | 0.774 | -0.273 |
| FR disabled | thigh | 1.104 | 0.415 | -0.689 |
| FR disabled | calf | -1.463 | -1.142 | 0.320 |
| RL | hip | -0.021 | -0.439 | -0.418 |
| RL | thigh | 0.849 | 0.136 | -0.713 |
| RL | calf | -1.791 | -1.522 | 0.269 |
| RR | hip | 0.578 | -0.078 | -0.655 |
| RR | thigh | -0.109 | 0.413 | 0.521 |
| RR | calf | -1.468 | -1.774 | -0.306 |

해석:

- E2는 tripod init pose에 가까운 특화 전략을 만든다.
- E3는 default init에서 살아남기 위해 E2와 다른 joint configuration을 찾는다.
- 특히 `FR_thigh`, `RL_thigh`, `RR_hip`, `RR_thigh` 차이가 커서, 두 policy가 같은 안정 자세로 수렴했다고 보기 어렵다.

발표에서는 다음 문장을 사용할 수 있다.

> E2와 E3는 모두 최종 no-push standing에는 성공했지만, cross-eval과 joint angle 분석에서 서로 다른 자세 전략을 사용한다. E2는 tripod prior에 특화된 안정 자세를 학습하고, E3는 init-pose curriculum을 통해 default-init 상태에서 균형을 회복하는 별도의 전략을 학습한다.

## 6. Push Robustness 평가

최종 policy에 대해 `base_link`에 실제 external force를 인가하는 impulse push 평가를 수행했다.

공통 설정:

- push start: `2.0 s`
- push duration: `0.1 s`
- directions: `front`, `back`, `left`, `right`
- episodes: 조건당 `20`
- success 기준: 단순 생존이 아니라 `tripod_success`와 `recovered`를 함께 만족해야 하는 `push_success`

결과 파일:

```text
project/results/push_eval/push_eval_v2_final_seed0.csv
project/results/push_eval/push_eval_v2_calibrated_final_seed0.csv
project/results/figures/push_eval_v2_calibrated_final_seed0/
```

처음 설정한 `0.5 / 1.0 / 1.5 BW` push는 현재 no-push standing policy에는 너무 강해서 E1/E2/E3 모두 실패했다. 따라서 발표용 robustness heatmap은 standing policy의 차이가 드러나는 보정 구간을 사용한다.

| Level | Multiplier | Force | Impulse |
| --- | ---: | ---: | ---: |
| weak | `0.25 BW` | `37.3 N` | `3.7 Ns` |
| medium | `0.35 BW` | `52.2 N` | `5.2 Ns` |
| strong | `0.45 BW` | `67.1 N` | `6.7 Ns` |

보정 구간 전체 평균:

| Policy | Eval init | push success | survival success | strict success | recovered | mean survival |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| E1 | default | 0.00 | 0.00 | 0.00 | 0.00 | 0.24 s |
| E2 | tripod | 0.33 | 0.33 | 0.33 | 0.33 | 4.97 s |
| E3 | default | 0.00 | 0.08 | 0.00 | 0.09 | 3.20 s |

E2 policy의 방향별 결과:

| Direction | weak | medium | strong |
| --- | ---: | ---: | ---: |
| front | 0.00 | 0.00 | 0.00 |
| back | 1.00 | 1.00 | 0.00 |
| left | 0.00 | 0.00 | 0.00 |
| right | 1.00 | 1.00 | 0.00 |

E3 policy는 no-push default-init standing에는 성공했지만, push 평가에서는 대부분 `illegal_contact` 또는 자세 기준 위반으로 실패했다. `right medium` 조건에서는 timeout까지 생존하고 recovery도 만족했지만, strict tripod 기준을 만족하지 못해 `push_success=0`으로 처리했다.

해석:

- E1은 push가 들어가기 전에 이미 무너지므로 robustness 비교 대상이 아니라 실패 reference다.
- E2는 tripod init 기반 policy답게 특정 방향(`back`, `right`)의 weak/medium push에는 버티지만, `front`, `left`, strong push에는 취약하다.
- E3는 default init에서 서는 별도 전략을 찾았지만, 그 전략이 외란 강건성으로 바로 이어지지는 않았다.
- 따라서 현재 결과는 "기구학적 prior가 no-push standing 학습을 가능하게 한다"는 결론은 강하게 지지하지만, "외란에도 강건하다"까지 주장하려면 push-aware training 또는 push randomization 추가가 필요하다.

발표용 영상:

```text
project/videos/push/E1_default_medium_right_calibrated_fail.mp4
project/videos/push/E2_tripod_medium_back_calibrated_success.mp4
project/videos/push/E2_tripod_medium_front_calibrated_fail.mp4
project/videos/push/E2_tripod_medium_right_calibrated_success.mp4
project/videos/push/E3_default_medium_right_calibrated_survive_not_strict.mp4
project/videos/push/FR_E1_E2_E3_medium_right_calibrated_side_by_side.mp4
```

## 7. Strict Tripod Recheck

영상 확인 결과 E2/E3 policy가 사람이 기대한 "깨끗한 3족 지지"와 다르게 보였다. 따라서 기존 결과를 폐기하지 않고, 다음처럼 해석을 분리한다.

> v2 결과는 PPO가 약한 contact/posture 기준을 만족하는 local optimum을 찾은 사례다.
> v3에서는 support polygon 기반 성공 기준과 reward를 추가하여 진짜 3족 지지 자세를 다시 학습한다.

새로 추가한 strict 기준:

| 항목 | 기준 |
| --- | --- |
| support triangle area | `FL`, `RR`, `RL` 지지 삼각형 면적이 `0.025 m^2` 이상 |
| support foot spacing | 세 지지발 pairwise distance 최솟값이 `0.16 m` 이상 |
| COM support margin | base projection이 support triangle 내부에 위치. margin `>= 0.0 m` |
| disabled foot | `FR` foot contact fraction 제한 유지 |
| non-foot contact | thigh/calf/body contact 금지 유지 |

기존 E2/E3 final policy를 strict 기준으로 다시 평가한 결과:

```text
project/results/no_push_eval/strict_recheck_v2_final_seed0.csv
```

| Policy | survival | old strict | old tripod contact | kinematic tripod | new tripod success | area | min foot distance | COM margin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| E2 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0.0344 | 0.2593 | -0.0055 |
| E3 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0.0206 | 0.1989 | -0.0070 |

즉 E2/E3는 기존 기준으로는 성공이지만, COM support polygon 기준을 만족하지 못해 새 `tripod_success`는 0이다. E3는 support triangle area도 기준보다 작다.

새 strict 학습 task:

| ID | Task |
| --- | --- |
| E1S | `Unitree-Go2-FR-Failure-Default-Strict-Stand` |
| E2S | `Unitree-Go2-FR-Failure-Tripod-Strict-Stand` |
| E3S | `Unitree-Go2-FR-Failure-Init-Curriculum-Strict-Stand` |

추가 reward:

- `fr_support_geometry`: support triangle area, support foot spacing, COM margin을 함께 보상
- `fr_disabled_foot_contact`: strict task에서는 penalty weight 강화
- `fr_support_feet_contact`, `fr_support_feet_stance_tracking`: strict task에서는 support feet reward weight 강화

## 7.1 Foot-Only Strict Update

영상 확인에서 calf로 버티는 듯한 자세가 관찰되었으므로, strict 기준을 한 번 더 강화한다.

추가된 foot-only 조건:

| 항목 | 변경 |
| --- | --- |
| non-foot contact termination | calf/thigh/body ground contact force threshold를 `10 N`에서 `1 N`으로 낮춤 |
| non-foot contact reward | `nonfoot_ground_contact` penalty 추가. calf/thigh/body contact와 force를 직접 벌점화 |
| init base height | `0.32 m`에서 `0.295 m`로 낮춰 reset 직후 foot sphere가 지면에 더 가깝게 위치하도록 조정 |
| visual 기준 | 발표 영상에서는 foot contact marker와 non-foot contact fail 표시를 함께 사용 예정 |

이후 실험 이름은 v4 foot-only strict로 분리한다.

```text
project/scripts/run_v4_footonly_training_5000_seed0_4096.sh
```

해석:

> v3는 support geometry를 강화한 실험이고, v4는 calf/thigh/body 접촉을 명시적으로 금지한 foot-only tripod 실험이다.
> 발표에서 최종적으로 보여줄 영상은 v4 결과를 우선 사용한다.

학습 실행 스크립트:

```text
project/scripts/run_v4_footonly_training_5000_seed0_4096.sh
```

## 7.2 Clean Tripod Update

v4 초반 로그와 영상 해석을 다시 확인하면서 더 근본적인 문제를 찾았다. Go2 `feet_ground_contact` sensor의 실제 foot order는 코드에서 가정한 `FR, FL, RR, RL`이 아니라 MuJoCo model order인 `FL, FR, RL, RR`이다.

이 순서가 틀리면 `FR` disabled foot penalty와 `FL/RL/RR` support foot reward가 서로 다른 발을 보고 학습한다. 따라서 이전 v2/v3/v4 결과는 "약한 기준과 잘못된 foot index 가정에서 나온 local optimum/실패 사례"로 보존하고, 최종 발표용 실험은 v5 clean tripod로 분리한다.

v5에서 수정한 핵심:

| 항목 | 수정 |
| --- | --- |
| foot contact order | `FL`, `FR`, `RL`, `RR`로 통일 |
| disabled foot | 진짜 `FR` foot 접촉/하중을 penalty |
| support feet | `FL`, `RL`, `RR` 세 발바닥 접촉과 하중 분담 reward |
| clean visual stance | base height/upright 강화, support geometry 강화, `FR` foot clearance reward |
| eval 기준 | `FR` foot height, support foot load를 `tripod_success`에 포함 |

새 clean 학습 task:

| ID | Task |
| --- | --- |
| E1C | `Unitree-Go2-FR-Failure-Default-Clean-Stand` |
| E2C | `Unitree-Go2-FR-Failure-Tripod-Clean-Stand` |
| E3C | `Unitree-Go2-FR-Failure-Init-Curriculum-Clean-Stand` |
| E4L | `Unitree-Go2-FR-Failure-Locked-Tucked-Clean-Stand` |

학습 실행 스크립트:

```text
project/scripts/run_v5_clean_tripod_training_5000_seed0_4096.sh
project/scripts/run_v5_clean_no_push_eval_seed0_4096_5000.sh
project/scripts/run_v6_locked_tucked_training_5000_seed0_4096.sh
project/scripts/run_v6_locked_tucked_no_push_eval_seed0_4096_5000.sh
```

발표용 clean tripod 영상 스크립트:

```text
project/scripts/render_clean_tripod_video.py
project/scripts/render_v5_clean_tripod_videos_seed0.sh
project/scripts/render_v6_locked_tucked_video_seed0.sh
```

이 영상은 단순 생존이 아니라 `FR` foot clearance, `FL/RL/RR` support foot contact/load, calf/body non-foot contact 여부, support triangle/COM margin을 함께 표시한다. 따라서 사람이 보기에도 "세 발바닥으로 버티는지"를 확인하는 용도로 사용한다.

`render_push_video.py`에도 같은 clean-tripod overlay를 추가했다. push 영상에서는 tennis/soccer/bowling ball force visual과 함께 외란 후에도 foot-only tripod 조건이 유지되는지 확인한다.

평가 기준은 두 층으로 분리한다.

| 기준 | 설정 | 용도 |
| --- | --- | --- |
| strict metric | roll/pitch `10 deg`, last-window fraction `0.95` | 매우 엄격한 수치 검증 |
| presentation-clean metric | roll/pitch `12 deg`, last-window fraction `0.90` | 발표 영상과 같은 clean tripod 판정 |

E2C final checkpoint pilot 결과, strict metric에서는 posture/FR-clearance fraction의 짧은 settling 때문에 `tripod_success=0.0`으로 찍혔지만, presentation-clean metric에서는 20/20 episode가 `tripod_success=1.0`이었다. 따라서 발표에서는 두 기준을 명확히 분리해서 보고한다.

E4L locked/tucked extension은 FR torque-zero passive leg가 영상에서 흔들리는 현상을 분리하기 위한 보조 실험이다. E4L은 FR actuator torque를 계속 0으로 두지만, FR hip/thigh/calf joint range를 tuck pose 주변 `+-0.001 rad`로 제한한다. 따라서 E4L 결과는 E1C/E2C/E3C 메인 결론을 대체하지 않고, "mechanically locked/tucked failure에서는 더 깔끔한 발표용 tripod stance가 가능한가"를 보여주는 supplementary comparison으로 사용한다.

E4L seed 0 full training도 `4096` parallel env, `5000` PPO iterations로 완료했다.

```text
logs/rsl_rl/go2_fr_failure_locked_tucked_clean_stand/2026-05-07_23-01-51_v6_locked_tucked_4096_5000_seed0_e4l_fr_locked_tucked/model_4999.pt
project/results/no_push_eval/no_push_eval_v6_locked_tucked_presentation_4096_5000_seed0.csv
project/videos/clean_tripod/E4L_locked_tucked_clean_no_push.mp4
```

E4L final no-push presentation-clean 평가 결과:

| metric | value |
| --- | ---: |
| survival success | 1.00 |
| tripod success | 1.00 |
| posture fraction | 1.00 |
| FR clearance fraction | 1.00 |
| FR foot height mean | `0.092 m` |
| support min force mean | `47.4 N` |
| support triangle area mean | `0.0665 m2` |
| COM margin mean | `0.1009 m` |
| non-foot contact fraction | 0.00 |

해석:

> E4L은 E2C/E3C와 같은 passive torque-zero failure가 아니라 locked/tucked failure extension이다. 따라서 메인 결론의 비교군으로 직접 섞지 않고, "failed leg swing을 제거하면 발표용 clean tripod stance가 얼마나 더 명확해지는가"를 보여주는 보조 결과로 사용한다.

## 8. 현재 결론

현재 seed 0 결과는 실험 단계를 나누어서 해석해야 한다.

v2 E0/E1/E2/E3 결과는 초기 자세 prior와 PPO exploration bottleneck을 보여주는 메인 분석 결과다.

1. FR 전체 다리 actuator failure 상황에서 default standing init만으로는 PPO가 안정 3족 지지 전략을 찾지 못했다.
2. 기구학적 tripod init은 초기 실패율을 낮추고, E2 policy가 빠르게 안정 3족 지지를 학습하게 했다.
3. E3 init-pose curriculum은 E1의 exploration bottleneck을 완화하여 default init에서도 서는 policy를 만들었다.
4. E2와 E3는 같은 결과처럼 보이지만, cross-eval과 joint angle 비교상 서로 다른 자세 전략을 학습했다.
5. no-push standing 성공이 곧 외란 강건성을 의미하지는 않는다. E2는 일부 방향의 약/중 push에만 버티고, E3는 strict tripod push success를 만들지 못했다.
6. 영상과 strict recheck 기준으로 볼 때 v2의 "성공"은 기구학적으로 깨끗한 tripod stance가 아니라, 기존 reward가 허용한 local optimum으로 해석해야 한다.

따라서 보고서의 중심 문장은 다음처럼 잡는다.

> 한 다리 고장 상황에서 기구학적 자세 prior는 PPO의 초기 탐색 실패를 줄이고 sample efficiency를 개선한다. 더 나아가 tripod-to-default reset curriculum을 사용하면 단순 tripod 자세 특화가 아니라 default init에서 균형을 회복하는 policy 학습도 가능하다.

v5 clean 결과는 사람이 보기에도 납득 가능한 foot-only 3족 지지를 만들기 위해 reward/eval 기준을 강화한 발표용 standing 결과다. v5에서는 foot contact sensor order를 `FL, FR, RL, RR`로 수정했고, `FR` foot clearance, `FL/RL/RR` support foot load, support geometry, non-foot contact 금지를 함께 본다.

v5 clean presentation 평가:

| 조건 | episodes | survival | tripod success | FR contact fraction | support min force | support area | COM margin | non-foot contact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| E1C default clean | 40 | 1.00 | 1.00 | 0.029 | 45.0 N | 0.089 m2 | 0.100 m | 0.00 |
| E2C tripod clean | 20 | 1.00 | 1.00 | 0.026 | 45.1 N | 0.084 m2 | 0.100 m | 0.00 |

따라서 v5 clean 결과는 "기준을 강화해도 foot-only tripod stance를 만들 수 있다"는 발표용 증거로 사용한다. 다만 v5는 reward와 eval 기준이 v2와 달라진 재학습 결과이므로, v2 E1/E2/E3의 초기 자세 효과 분석을 그대로 대체한다고 말하지 않는다. clean reward 기준에서도 init 효과를 더 엄밀히 말하려면 E1C/E2C/E3C의 learning curve와 checkpoint별 초기 실패율을 별도로 정리해야 한다.

E4L locked/tucked 결과는 발표 영상 품질을 높이기 위한 보조 실험이다. E4L은 FR actuator torque를 0으로 두지만 FR joint range를 tuck pose 주변으로 제한하므로, passive torque-zero 메인 실험과 직접 섞지 않는다.

E4L presentation 평가:

| 조건 | episodes | survival | tripod success | FR contact fraction | FR foot height | support min force | support area | COM margin | non-foot contact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| E4L locked/tucked | 20 | 1.00 | 1.00 | 0.00 | 0.092 m | 47.4 N | 0.066 m2 | 0.101 m | 0.00 |

발표에서는 다음처럼 정리한다.

> v2는 초기 자세 prior와 PPO exploration 차이를 보여주는 분석 실험이고, v5/v6은 영상과 평가 기준을 강화해 foot-only clean tripod stance를 확인한 후속 실험이다. 외란 강건성은 아직 제한적이므로, robust policy까지 주장하려면 push-aware training 또는 push randomization이 필요하다.

## 9. 남은 작업

현재 결과만으로 no-push standing과 clean stance 발표 흐름은 만들 수 있다. 남은 작업은 "논리 보강"과 "외란 시각화 보강"이다.

| 작업 | 목적 |
| --- | --- |
| clean policy push 영상 생성 | foot-only clean stance와 공/화살표 push overlay를 같은 영상에서 보여주기 |
| E1C/E2C/E3C learning curve 정리 | clean reward 기준에서도 init pose가 학습 속도에 주는 영향을 확인 |
| E2C와 E4L 영상/수치 비교 | passive torque-zero와 locked/tucked extension의 차이를 명확히 설명 |
| push-aware training 또는 push DR pilot | 외란 강건성이 부족한 이유를 보완 |
| seed 추가 | PPO 랜덤성 방어. 시간이 부족하면 seed 0 main + 추가 seed pilot로 축소 |
| PPT용 figure 선별 | 결과가 많으므로 핵심 그림과 영상을 좁혀 발표 흐름을 정리 |

현재 GitHub에는 발표 확인에 필요한 CSV, figure, video가 올라가 있다. 대용량 raw training log와 `logs/` checkpoint 폴더는 제외했다.

## 10. 이전 Pilot 결과의 위치

초기 contact-penalty pilot은 낮게 접힌 자세가 foot contact만 유지하는 문제가 있었다. 해당 결과는 현재 본 결론이 아니라 threshold/reward 수정 전의 실패 분석으로만 사용한다.

```text
project/results/no_push_eval/no_push_eval_v1_contactpen_2000_seed0.csv
project/results/figures/no_push_eval_v1_contactpen_2000_seed0/
```
