# Presentation Outline

이 문서는 졸업프로젝트 발표용 PPT 흐름과 슬라이드별로 말할 내용을 정리한 초안이다. 실제 PPT를 만들 때는 이 문서에서 필요한 표, 영상, 문장을 골라 쓰면 된다.

## 발표 전체 메시지

발표에서 끝까지 가져갈 메시지는 하나다.

> 한 다리 actuator torque가 0인 상황에서는 초기 자세가 PPO의 탐색 가능성을 크게 바꾼다. 기구학적 tripod 자세 prior와 init curriculum은 초기 실패율을 줄이고, policy가 3족 지지 전략을 학습하도록 돕는다. 단, no-push standing 성공과 외란 강건성은 구분해야 한다.

## Slide 1. 제목

제목 예시:

```text
Effect of Kinematic Tripod Pose Prior on PPO-Based 3-Leg Standing of Unitree Go2 under Single-Leg Actuator Failure
```

한국어 제목:

```text
한 다리 actuator 고장 상황에서 기구학적 Tripod 초기 자세가 Unitree Go2 PPO 학습에 미치는 영향
```

넣을 내용:

- 팀원 이름
- 지도교수님
- 사용 로봇: Unitree Go2
- 사용 시뮬레이터: MuJoCo 기반 unitree_rl_mjlab

## Slide 2. 문제 정의

핵심 그림:

- 정상 4족 standing 이미지
- FR 다리가 고장난 3족 지지 이미지

말할 내용:

```text
본 프로젝트는 Unitree Go2에서 FR 다리 actuator가 모두 고장난 상황을 가정한다.
FR hip, thigh, calf actuator torque가 모두 0이면 로봇은 더 이상 네 발 전체로 몸을 지탱할 수 없고, 남은 세 발인 FL, RL, RR로 균형을 유지해야 한다.
이때 기본 standing pose에서 바로 PPO를 학습시키는 것이 좋은지, 아니면 기구학적으로 안정한 tripod pose를 초기 prior로 주는 것이 좋은지를 비교한다.
```

강조할 점:

- 한 관절 고장이 아니라 한 다리 전체 고장이다.
- action을 0으로 하는 것이 아니라 actuator torque output을 0으로 만드는 고장이다.

## Slide 3. 제어 구조

넣을 그림:

```text
Observation
-> PPO Policy
-> Joint Position Target
-> MuJoCo Position Actuator
-> Joint Torque
-> Robot Motion
```

말할 내용:

```text
우리 policy는 torque를 직접 출력하지 않는다.
PPO policy는 관절 목표 위치를 출력하고, MuJoCo position actuator가 현재 관절 위치와 목표 위치의 오차를 바탕으로 torque를 생성한다.
따라서 고장 다리의 action을 0으로 두는 것만으로는 실제 torque가 0이 되지 않을 수 있다.
본 연구에서는 FR 세 actuator의 stiffness와 damping을 0으로 만들어 실제 actuator torque output이 발생하지 않도록 했다.
```

교수님 질문 대비:

| 질문 | 답 |
| --- | --- |
| 주제어기와 보조제어기는 무엇인가? | PPO policy가 상위 주제어기이고, MuJoCo position actuator가 목표 위치를 torque로 바꾸는 저수준 actuator model이다. 별도 보조 토크 제어기나 actuator network는 사용하지 않았다. |
| torque를 policy가 직접 넣는가? | 아니다. policy는 joint position target을 출력한다. |

## Slide 4. 연구 가설

넣을 표:

| 조건 | 예상 |
| --- | --- |
| default init | FR torque가 없어서 초반에 바로 넘어질 가능성이 큼 |
| tripod init | 초기부터 3족 지지에 가까워 PPO 탐색이 쉬움 |
| init curriculum | tripod에서 시작해 default로 이동하면 default init 회복 전략을 배울 수 있음 |

말할 내용:

```text
가설은 기구학적으로 안정한 초기 자세가 PPO의 초기 실패율을 낮추고, 수렴속도를 높인다는 것이다.
default init은 로봇이 너무 빨리 넘어져서 PPO가 유효한 균형 전략을 탐색하기 어렵다.
tripod init은 초기 생존 시간을 확보해 학습 가능한 상태 분포를 제공한다.
```

## Slide 5. 실험군

넣을 표:

| ID | 조건 | 목적 |
| --- | --- | --- |
| E0 | 4-leg baseline | 정상 reference |
| E1 | FR failure + default init | prior 없는 실패 기준 |
| E2 | FR failure + tripod init | kinematic prior 효과 |
| E3 | FR failure + init curriculum | assisted exploration 효과 |

말할 내용:

```text
E1과 E2가 메인 비교다.
E0는 정상 기준선이고, E3는 E1 실패의 원인이 policy capacity 부족인지 초기 탐색 문제인지 분리하기 위한 보조 실험이다.
E3는 초반에는 tripod pose 근처에서 reset하고, 학습이 진행될수록 default pose 쪽으로 reset 분포를 이동시킨다.
```

## Slide 6. 평가 지표

넣을 표:

| 종류 | 지표 |
| --- | --- |
| 학습 효율 | 초기 실패율, learning curve, 수렴속도 |
| standing 안정성 | survival, base height, roll/pitch, angular velocity |
| 3족 지지 품질 | support foot contact, support load, FR clearance, support geometry |
| 외란 강건성 | push success, survival time, recovery, max tilt |

말할 내용:

```text
단순히 episode가 끝까지 살아남았는지만 보지 않는다.
몸통 높이와 자세가 안정적인지, 세 지지 발바닥이 실제로 하중을 받는지, 고장난 FR 발이 지면에 끌리지 않는지, calf나 body가 땅에 닿지 않는지를 함께 본다.
```

## Slide 7. v2 학습 결과

넣을 그림:

- `project/results/figures/learning_curves/Train_mean_reward.png`
- `project/results/figures/no_push_eval_v2_4096_5000_seed0/success_rate.png`
- `project/results/figures/no_push_eval_v2_4096_5000_seed0/initial_failure_rate.png`

넣을 표:

| ID | final no-push | initial failure | 해석 |
| --- | ---: | ---: | --- |
| E0 | 성공 | 낮음 | 정상 reference |
| E1 | 실패 | 높음 | default init exploration 실패 |
| E2 | 성공 | 낮음 | tripod prior 효과 |
| E3 | 성공 | 낮음 | curriculum 효과 |

말할 내용:

```text
E1은 5000 iteration까지 학습해도 default init에서 계속 초기 실패했다.
반면 E2는 tripod init을 사용했을 때 안정적으로 서는 policy를 학습했다.
E3는 curriculum을 사용하여 default init에서도 서는 policy를 만들었다.
이는 E1 실패가 단순히 policy capacity 부족이 아니라, 초반 episode가 너무 빨리 끝나 탐색이 막힌 문제였음을 시사한다.
```

## Slide 8. Cross-Eval과 자세 전략

넣을 표:

| Policy | default-init eval | tripod-init eval | 해석 |
| --- | ---: | ---: | --- |
| E1 | 실패 | 실패 | 안정화 전략 학습 실패 |
| E2 | 실패 | 성공 | tripod pose 특화 |
| E3 | 성공 | 실패 | default init용 별도 전략 |

말할 내용:

```text
E2와 E3는 둘 다 no-push standing에 성공했지만 같은 전략을 학습한 것은 아니다.
E2는 tripod init에서만 성공하고 default init에서는 실패했다.
E3는 반대로 default init에서 성공하지만 tripod init에는 일반화되지 않았다.
따라서 두 policy는 서로 다른 자세 안정화 전략으로 수렴했다고 해석할 수 있다.
```

강조:

- 이게 "초기 자세 덕분에만 서는지", "policy 자체가 다른 전략을 배웠는지"를 분리하는 포인트다.

## Slide 9. 왜 clean 기준이 필요했는가

넣을 내용:

- v2 성공 기준만으로는 사람이 보기 좋은 3족 지지를 보장하지 못했다.
- 낮게 웅크리거나 calf/body로 버티는 local optimum이 생길 수 있었다.
- foot contact sensor order도 재확인해야 했다.

말할 내용:

```text
초기 결과는 수치상 성공이었지만, 영상을 보면 사람이 기대하는 "세 발바닥으로 깔끔하게 서기"와 차이가 있었다.
그래서 support polygon, COM margin, non-foot contact, FR foot clearance, support foot load를 포함한 clean tripod 기준을 추가했다.
이 과정을 통해 단순 생존이 아니라 발표에서 납득 가능한 3족 지지 자세를 목표로 다시 정리했다.
```

## Slide 10. v5 Clean Tripod Result

넣을 영상:

```text
project/videos/clean_tripod/E2C_tripod_clean_no_push_final.mp4
```

넣을 표:

| 조건 | tripod success | FR contact | support load | non-foot contact |
| --- | ---: | ---: | ---: | ---: |
| E2C | 1.00 | 0.026 | 45.1 N | 0.00 |

말할 내용:

```text
v5 clean 기준에서는 FR foot clearance, 세 support foot의 하중, support triangle, non-foot contact를 함께 평가한다.
E2C는 presentation-clean 기준에서 20/20 episode 성공했고, FR foot contact는 낮고, 세 지지 발은 실제 하중을 받으며, calf/body 접촉도 없었다.
```

주의:

```text
v5는 v2와 reward/eval 기준이 달라진 재학습 결과이므로, v2의 초기 자세 효과 분석과 clean stance 결과는 구분해서 설명한다.
```

## Slide 11. E4L Locked/Tucked 보조 결과

넣을 영상:

```text
project/videos/clean_tripod/E4L_locked_tucked_clean_no_push.mp4
```

말할 내용:

```text
E4L은 FR torque는 0으로 두되, 고장난 FR 다리를 접힌 상태로 거의 고정한 보조 실험이다.
이 조건에서는 passive leg swing이 제거되어 영상이 훨씬 깔끔하다.
다만 이 조건은 메인 passive torque-zero failure를 대체하지 않고, failed leg가 기계적으로 접혀 있는 경우의 supplementary result로 해석한다.
```

교수님 질문 대비:

| 질문 | 답 |
| --- | --- |
| 왜 lock했는가? | torque-zero passive leg가 관성으로 흔들리는 효과를 분리하고, 고장 다리가 기계적으로 접힌 경우를 보조적으로 확인하기 위해서다. |
| 메인 결과인가? | 아니다. 메인은 passive torque-zero 조건이고, E4L은 발표용/분석용 extension이다. |

## Slide 12. Push Visualization

넣을 영상:

```text
project/videos/push/FR_E1_E2_E3_medium_right_calibrated_side_by_side.mp4
```

넣을 개별 영상:

```text
project/videos/push/E2_tripod_medium_right_calibrated_success.mp4
project/videos/push/E2_tripod_medium_front_calibrated_fail.mp4
```

말할 내용:

```text
외란은 실제 external force impulse로 base_link에 인가했다.
영상의 공은 물리 충돌체가 아니라 push 방향과 크기를 보여주는 ghost visual object다.
calibrated medium push는 약 0.35 body weight, 약 52 N을 0.1초 동안 인가한 조건이다.
```

## Slide 13. Push 결과와 한계

넣을 표:

| Policy | push success | survival success | 해석 |
| --- | ---: | ---: | --- |
| E1 | 0.00 | 0.00 | push 전부터 실패 |
| E2 | 0.33 | 0.33 | 일부 방향/크기에서 성공 |
| E3 | 0.00 | 0.08 | no-push는 되지만 push는 취약 |

말할 내용:

```text
현재 push 결과는 no-push standing 성공이 외란 강건성을 자동으로 보장하지 않는다는 것을 보여준다.
E2는 특정 방향의 weak/medium push에는 버티지만, 전체 방향과 강한 push에 대해서는 충분하지 않다.
따라서 최종 robustness까지 주장하려면 학습 중 push randomization 또는 push-aware curriculum을 추가해야 한다.
```

중요:

- 여기서 솔직하게 한계를 말하면 오히려 발표가 좋아진다.
- "우리는 실패를 숨긴 게 아니라 평가 기준을 강화하고 다음 개선 방향을 찾았다"로 가져간다.

## Slide 14. 결론

결론 문장:

```text
1. FR whole-leg actuator failure에서는 default standing init만으로 PPO가 안정 전략을 찾기 어렵다.
2. 기구학적 tripod posture prior는 초기 실패율을 낮추고 학습 가능한 상태 분포를 제공한다.
3. tripod-to-default init curriculum은 default init에서의 exploration bottleneck을 완화할 수 있다.
4. 단순 생존 성공률만으로는 부족하므로 clean foot-only tripod 기준을 추가해 평가했다.
5. 외란 강건성은 아직 제한적이며, push-aware training이 후속 과제다.
```

마지막 한 문장:

```text
따라서 본 연구는 한 다리 고장 상황에서 기구학적 prior가 강화학습의 초기 탐색과 최종 자세 전략에 미치는 영향을 분석하고, 3족 지지 policy 설계에서 초기 상태와 평가 기준의 중요성을 보였다.
```

## Slide 15. Future Work

넣을 내용:

| 작업 | 목적 |
| --- | --- |
| seed 추가 | PPO 랜덤성 방어 |
| clean policy push 평가 | clean stance 기준의 외란 강건성 확인 |
| push-aware training | 외란 회복 성능 개선 |
| RR failure extension | 고장 다리 위치가 바뀌어도 결론이 유지되는지 확인 |
| real robot 적용 검토 | sim-to-real 가능성 확인 |

말할 내용:

```text
현재 프로젝트는 FR failure seed 0을 중심으로 파이프라인과 분석 기준을 완성했다.
다음 단계는 seed를 늘리고, clean policy에 push-aware training을 적용해 외란 강건성을 개선하는 것이다.
시간이 허용되면 RR failure로 확장하여 고장 다리 위치에 대한 일반성을 확인할 수 있다.
```

## 교수님 질문 대비 Q&A

### Q1. 왜 4발 baseline도 넣었는가?

정상 조건에서 같은 PPO/actuator 구조가 문제 없이 standing을 학습할 수 있다는 reference가 필요하기 때문이다. E0는 메인 비교가 아니라 성능 상한선과 구현 sanity check 역할이다.

### Q2. 왜 FR만 했는가?

모든 다리 조합을 하면 실험 수가 크게 늘어난다. 졸업프로젝트 v1에서는 FR로 고정해 학습, 평가, 시각화 파이프라인을 끝까지 완성하고, RR은 extension으로 둔다.

### Q3. 왜 action을 0으로 하지 않고 actuator gain을 껐는가?

action이 0이어도 position actuator가 살아 있으면 default pose를 따라가려고 torque를 낼 수 있다. 고장 모델의 핵심은 실제 actuator torque output이 0인 것이므로 stiffness/damping을 0으로 만든다.

### Q4. PPO 내부를 분석했다고 할 수 있는가?

hidden layer 자체를 해석한 것은 아니다. 대신 checkpoint별 joint angle, contact force, support geometry, COM margin, torque/action norm을 통해 policy가 어떤 물리적 안정화 전략으로 수렴했는지 분석했다.

### Q5. E4L은 메인 결과인가?

아니다. E4L은 고장 다리가 기계적으로 접힌 경우의 보조 실험이다. passive torque-zero leg의 흔들림을 제거하면 발표용 clean stance가 얼마나 명확해지는지 보여준다.

### Q6. 외란 강건성까지 달성했는가?

완전한 외란 강건성은 아직 아니다. 현재 E2는 일부 방향/크기 push에는 성공하지만 전체적으로는 제한적이다. 결론은 no-push standing 학습 효율과 clean stance 형성까지 강하고, robustness는 push-aware training이 필요한 후속 과제다.

## PPT에 넣을 파일 체크리스트

| 종류 | 파일 |
| --- | --- |
| clean standing video | `project/videos/clean_tripod/E2C_tripod_clean_no_push_final.mp4` |
| locked/tucked video | `project/videos/clean_tripod/E4L_locked_tucked_clean_no_push.mp4` |
| push side-by-side | `project/videos/push/FR_E1_E2_E3_medium_right_calibrated_side_by_side.mp4` |
| push success | `project/videos/push/E2_tripod_medium_right_calibrated_success.mp4` |
| push fail | `project/videos/push/E2_tripod_medium_front_calibrated_fail.mp4` |
| learning curve | `project/results/figures/learning_curves/Train_mean_reward.png` |
| initial failure | `project/results/figures/no_push_eval_v2_4096_5000_seed0/initial_failure_rate.png` |
| push heatmap | `project/results/figures/push_eval_v2_calibrated_final_seed0/push_success_heatmap_E2_tripod.png` |

## 발표 톤

좋은 발표 톤:

```text
우리는 처음부터 완벽한 reward를 만든 것이 아니라, 영상과 수치 평가를 같이 보면서 성공 기준을 점점 강화했다.
그 과정에서 PPO가 약한 기준에서는 local optimum을 찾을 수 있음을 확인했고, 최종적으로는 foot-only clean tripod 기준을 추가했다.
이 프로젝트의 기여는 단순히 "서게 했다"가 아니라, 한 다리 고장 상황에서 초기 자세 prior와 평가 기준이 강화학습 결과 해석에 얼마나 중요한지 보여준 것이다.
```

피해야 할 톤:

```text
무조건 tripod init이 최고다.
PPO 내부 최적화 과정을 완전히 해석했다.
외란도 완벽히 버틴다.
```

정직하게 한계를 말하면서, 그 한계를 어떻게 발견했고 어떻게 다음 실험으로 연결했는지를 보여주는 게 가장 설득력 있다.
