# Full Project Explanation

이 문서는 프로젝트 전체를 처음 보는 사람이 읽어도 연구 질문, 코드 구조, 실험군, 결과 해석, 발표 방향을 따라올 수 있도록 자세히 정리한 문서다.

## 1. 최종 연구 질문

우리 프로젝트의 핵심 질문은 하나다.

> Unitree Go2의 FR 다리 전체 actuator torque가 0인 고장 상황에서, 기구학적으로 안정한 tripod 자세 prior를 주는 것이 PPO의 학습 효율과 3족 지지 안정성을 얼마나 개선하는가?

여기서 중요한 단어는 세 개다.

| 단어 | 의미 |
| --- | --- |
| FR 다리 고장 | front-right 다리의 hip, thigh, calf actuator torque가 모두 0인 상황 |
| tripod 자세 prior | 남은 세 발인 FL, RL, RR이 지면을 지지하고 FR 다리는 들거나 접는 초기 자세 정보 |
| PPO 학습 효율 | 초기 실패율, learning curve, 수렴속도, 최종 성공률로 본 학습 난이도 |

단순히 "tripod pose가 예쁜가"를 보는 실험이 아니다. 더 정확히는 한 다리 고장으로 인해 초기 상태가 불안정해졌을 때, PPO가 의미 있는 탐색을 시작할 수 있도록 기구학적 prior가 도와주는지를 분석하는 실험이다.

## 2. 연구 배경

4족 로봇은 각 다리에 보통 3개의 관절을 가진다.

| 관절 | 역할 |
| --- | --- |
| hip | 다리를 좌우로 벌리거나 모으는 방향 제어 |
| thigh | 다리의 앞뒤/위아래 큰 움직임 제어 |
| calf | 발 끝 높이와 지지 자세 제어 |

Unitree Go2는 총 4개 다리, 12개 관절을 가진다. 정상 상태에서는 네 발을 모두 사용할 수 있으므로 standing이나 locomotion이 비교적 쉽다. 하지만 한 다리의 actuator torque가 완전히 사라지면 그 다리는 더 이상 능동적으로 몸을 지탱하지 못한다. 그러면 로봇은 남은 세 다리로 몸통의 roll, pitch, height를 유지해야 한다.

이때 단순히 기존 4족 standing pose에서 시작하면 문제가 생긴다.

- 고장난 FR 다리가 원래처럼 지지할 것이라고 가정한 자세일 수 있다.
- 실제로는 FR actuator torque가 없으므로 그 다리가 몸을 밀어 올릴 수 없다.
- 몸의 무게중심이 남은 세 발 지지 삼각형 안에 들어오지 않을 수 있다.
- episode 초반에 바로 넘어지면 PPO가 균형 전략을 탐색할 시간이 없다.

그래서 비교하고 싶은 것은 다음이다.

| 방법 | 질문 |
| --- | --- |
| default init | 아무 기구학적 도움 없이 PPO가 스스로 3족 지지 전략을 찾을 수 있는가? |
| tripod init | 처음부터 안정한 3족 지지 자세를 주면 더 빨리 배우는가? |
| init curriculum | 초반에는 tripod 근처에서 시작하고 점점 default init으로 옮기면 default 상태에서도 서는 policy가 만들어지는가? |

## 3. 제어 구조

이 프로젝트에서 PPO policy는 torque를 직접 출력하지 않는다.

실제 구조는 다음과 같다.

```text
robot observation
-> PPO policy
-> joint position target
-> MuJoCo position actuator
-> actuator torque
-> robot motion
```

즉 policy output은 12개 관절에 대한 목표 위치 또는 목표 위치 offset이다. MuJoCo의 position actuator가 현재 joint position과 목표 joint position의 차이를 보고 내부적으로 torque를 만든다.

이 구분이 중요하다.

| 오해 | 실제 |
| --- | --- |
| policy가 torque를 직접 출력한다 | policy는 joint position target을 출력한다 |
| action을 0으로 만들면 torque도 0이다 | position actuator가 살아 있으면 목표 자세를 따라가려고 torque가 생긴다 |
| 고장 다리는 action만 막으면 된다 | actuator gain/damping을 꺼서 실제 torque output이 0이 되게 해야 한다 |

따라서 본 연구에서 한 다리 고장은 action masking이 아니라 actuator torque output을 제거하는 방식으로 구현한다.

## 4. 고장 모델

메인 고장 모델은 FR whole-leg actuator failure다.

고장 관절:

```text
FR_hip_joint
FR_thigh_joint
FR_calf_joint
```

의미:

```text
FR_hip_joint torque  = 0
FR_thigh_joint torque = 0
FR_calf_joint torque  = 0
```

현재 구현에서는 MuJoCo가 `forcerange=[0, 0]` actuator를 거부하므로, FR 세 actuator의 position-control `stiffness`와 `damping`을 0으로 만들어 실제 torque output이 0이 되도록 했다.

중요한 점:

- action space에는 FR actuator action이 남아 있다.
- 하지만 FR actuator gain이 0이므로 실제 torque는 발생하지 않는다.
- 그래서 policy가 고장난 다리에 어떤 action을 내는지도 분석할 수 있다.

E4L locked/tucked 조건은 별도로 해석해야 한다.

| 조건 | 의미 |
| --- | --- |
| E1/E2/E3/E1C/E2C/E3C | FR 다리가 passive torque-zero 상태로 남아 있음 |
| E4L | FR torque는 0이지만 FR joint range를 tuck pose 근처로 거의 고정 |

E4L은 "고장난 다리가 수동으로 흔들리는 문제"를 분리하기 위한 보조 실험이다. 메인 과학적 결론과 섞으면 안 된다.

## 5. 실험군

### 5.1 기본 v2 실험군

| ID | 조건 | 목적 |
| --- | --- | --- |
| E0 | 4-leg baseline + default init | 정상 4족 reference |
| E1 | FR failure + default init | 아무 자세 prior 없이 PPO가 버티는지 확인 |
| E2 | FR failure + tripod init | tripod posture prior가 학습 효율을 높이는지 확인 |
| E3 | FR failure + tripod-to-default init curriculum | default init exploration bottleneck을 완화하는지 확인 |

v2의 핵심 비교는 E1 vs E2다. E3는 추가 분석이다. E1이 실패하고 E3가 성공하면, E1 실패가 policy capacity 부족이라기보다 초기 탐색이 너무 어려웠기 때문이라는 해석을 보강할 수 있다.

### 5.2 strict/clean 실험군이 추가된 이유

초기 결과는 수치상 성공처럼 보였지만, 영상을 보니 사람이 기대한 "세 발바닥으로 깔끔하게 서는 자세"와 다를 수 있었다. 그래서 단계별로 평가 기준을 강화했다.

| 단계 | 추가 이유 |
| --- | --- |
| v3 strict | support triangle, foot spacing, COM margin 등 기구학 기준 추가 |
| v4 foot-only | calf/thigh/body로 버티는 자세를 막기 위해 non-foot contact 벌점 강화 |
| v5 clean | foot contact sensor order 수정, FR clearance, support load, clean overlay 추가 |
| v6 locked/tucked | passive FR leg 흔들림을 제거한 보조 발표용 조건 |

현재 발표용 clean standing 결과는 v5와 v6을 우선 사용한다.

### 5.3 clean 실험군

| ID | 조건 | 목적 |
| --- | --- | --- |
| E1C | FR failure + default init + clean reward | clean 기준에서도 default init이 가능한지 확인 |
| E2C | FR failure + tripod init + clean reward | 발표용 clean tripod stance 메인 후보 |
| E3C | FR failure + init curriculum + clean reward | clean 기준에서 curriculum 효과 확인 |
| E4L | FR locked/tucked + clean reward | failed leg swing을 제거한 보조 영상 |

## 6. PPO 탐색 분석을 어떻게 할 것인가

"PPO hidden layer가 어떤 최적해를 찾았는지"를 직접 분석한다고 말하면 위험하다. 신경망 내부 hidden unit이 물리적으로 어떤 의미를 갖는지 증명하기 어렵기 때문이다.

대신 다음처럼 표현한다.

> PPO policy가 학습 과정에서 어떤 물리적 자세 안정화 전략으로 수렴하는지 분석한다.

실제로 분석 가능한 항목은 아래다.

| 항목 | 의미 |
| --- | --- |
| learning curve | return, episode length, termination이 어떻게 바뀌는지 |
| 초기 실패율 | 초반 episode가 2초 안에 넘어지는 비율 |
| checkpoint별 성공률 | 몇 iteration부터 안정적으로 서는지 |
| final joint angle | 최종 policy가 어떤 자세로 서는지 |
| contact force | 세 지지 발에 하중이 어떻게 분배되는지 |
| FR foot contact/clearance | 고장난 다리를 지지점으로 쓰는 꼼수를 쓰는지 |
| support geometry | 세 지지 발의 support triangle이 충분한지 |
| COM margin | 몸 중심 projection이 support polygon 안에 있는지 |
| torque/action norm | 안정 자세를 유지하는 데 필요한 제어량 |

즉 "내부 레이어 해석"이 아니라 "행동 결과와 물리량 해석"으로 가져간다. 이게 졸업프로젝트 발표에서 훨씬 방어 가능하다.

## 7. 평가 지표

### 7.1 학습 단계 지표

| 지표 | 정의 |
| --- | --- |
| 초기 실패율 | reset 후 2초 안에 fall 또는 termination이 발생한 episode 비율 |
| survival time | episode가 종료되기 전까지 버틴 시간 |
| learning curve | PPO iteration별 return, episode length, fall rate 변화 |
| 수렴속도 | success rate가 일정 threshold를 넘는 데 필요한 iteration |
| seed variance | 서로 다른 random seed에서 결과가 얼마나 흔들리는지 |

현재 seed 0 결과는 확보되어 있다. 최종 보고서에서 더 강하게 방어하려면 seed를 추가하는 것이 좋다.

### 7.2 no-push standing 지표

| 지표 | 의미 |
| --- | --- |
| survival_success | episode 끝까지 넘어지지 않고 생존 |
| posture_success | 마지막 안정 구간에서 roll/pitch, base height가 기준을 만족 |
| support_contact_success | FL/RL/RR 지지 발 접촉 유지 |
| support_load_success | 세 지지 발이 실제 하중을 받음 |
| support_geometry_success | support triangle area, foot spacing, COM margin 기준 만족 |
| disabled_clearance_success | FR foot이 지면에 끌리지 않고 충분히 떠 있음 |
| nonfoot_contact_success | calf/thigh/body가 지면에 닿지 않음 |
| tripod_success | 위 조건들을 종합한 clean 3족 지지 성공 |

단순히 안 넘어졌다고 성공으로 보지 않는다. 자세, 접촉, 하중, 기구학, non-foot contact를 함께 본다.

### 7.3 push robustness 지표

push 평가는 reset 후 일정 시간 뒤 `base_link`에 external force impulse를 넣는다.

기본 설정:

| 항목 | 값 |
| --- | --- |
| push start | `2.0 s` |
| push duration | `0.1 s` |
| directions | front, back, left, right |
| magnitudes | weak, medium, strong |
| calibrated force | `0.25 BW`, `0.35 BW`, `0.45 BW` |

현재 seed 0 기준 힘:

| level | force | impulse |
| --- | ---: | ---: |
| weak | 약 `37 N` | 약 `3.7 Ns` |
| medium | 약 `52 N` | 약 `5.2 Ns` |
| strong | 약 `67 N` | 약 `6.7 Ns` |

처음 생각한 `0.5 BW`, `1.0 BW`, `1.5 BW`는 현재 standing policy에 너무 강해서 모두 실패했다. 그래서 발표용 heatmap은 policy 간 차이가 보이는 calibrated 기준을 사용한다.

## 8. 현재 결과 요약

### 8.1 v2 main no-push 결과

학습 조건:

```text
4096 parallel env
5000 PPO iterations
seed 0
```

| ID | 조건 | 최종 no-push 결과 | 해석 |
| --- | --- | ---: | --- |
| E0 | 4-leg baseline | 성공 | 정상 기준선 |
| E1 | FR failure + default init | 실패 | default init은 초기 탐색이 막힘 |
| E2 | FR failure + tripod init | 성공 | tripod prior가 학습 가능성을 크게 높임 |
| E3 | FR failure + init curriculum | 성공 | curriculum이 default-init 회복 전략을 만들 수 있음 |

핵심은 E2와 E3가 둘 다 성공했지만 같은 policy가 아니라는 점이다. cross-eval 결과 E2는 tripod init에 특화되고, E3는 default init에서 서는 다른 전략을 학습했다.

### 8.2 v5 clean no-push 결과

파일:

```text
project/results/no_push_eval/no_push_eval_v5_clean_presentation_4096_5000_seed0.csv
```

presentation-clean 기준 요약:

| 조건 | survival | tripod success | FR contact | support min force | support area | COM margin | non-foot contact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| E1C | 1.00 | 1.00 | 0.029 | 45.0 N | 0.089 m2 | 0.100 m | 0.00 |
| E2C | 1.00 | 1.00 | 0.026 | 45.1 N | 0.084 m2 | 0.100 m | 0.00 |

이 결과는 clean reward/eval 기준을 적용하면 foot-only tripod stance가 가능하다는 것을 보여준다. 다만 v2와 reward 기준이 다르므로, v2의 초기 자세 효과 분석과 v5의 clean stance 결과는 구분해서 말해야 한다.

### 8.3 v6 locked/tucked 결과

파일:

```text
project/results/no_push_eval/no_push_eval_v6_locked_tucked_presentation_4096_5000_seed0.csv
project/videos/clean_tripod/E4L_locked_tucked_clean_no_push.mp4
```

| 조건 | survival | tripod success | FR contact | FR foot height | support area | COM margin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E4L | 1.00 | 1.00 | 0.00 | 0.092 m | 0.066 m2 | 0.101 m |

E4L 영상은 매우 깔끔하다. 하지만 메인 결론으로 섞으면 안 된다. "실제 고장 다리가 기계적으로 접혀 있거나 lock된 경우"의 보조 결과로 보여준다.

### 8.4 push 결과

파일:

```text
project/results/push_eval/push_eval_v2_calibrated_final_seed0.csv
project/videos/push/FR_E1_E2_E3_medium_right_calibrated_side_by_side.mp4
```

요약:

| Policy | Eval init | push success | survival success | 해석 |
| --- | --- | ---: | ---: | --- |
| E1 | default | 0.00 | 0.00 | push 전에 이미 무너짐 |
| E2 | tripod | 0.33 | 0.33 | back/right weak/medium 일부 성공 |
| E3 | default | 0.00 | 0.08 | no-push는 가능하지만 push에는 취약 |

따라서 현재 결과로 "tripod prior가 외란 강건성까지 완성했다"고 말하면 안 된다. 안전한 해석은 다음이다.

> tripod prior와 curriculum은 no-push standing 학습을 가능하게 만들었지만, 외란 강건성은 별도의 push-aware training 또는 push randomization이 필요하다.

## 9. 발표용 파일 위치

### 9.1 먼저 볼 영상

| 용도 | 파일 |
| --- | --- |
| E2C clean tripod standing | `project/videos/clean_tripod/E2C_tripod_clean_no_push_final.mp4` |
| E4L locked/tucked clean standing | `project/videos/clean_tripod/E4L_locked_tucked_clean_no_push.mp4` |
| v2 push side-by-side | `project/videos/push/FR_E1_E2_E3_medium_right_calibrated_side_by_side.mp4` |
| E2 push success | `project/videos/push/E2_tripod_medium_right_calibrated_success.mp4` |
| E2 push fail | `project/videos/push/E2_tripod_medium_front_calibrated_fail.mp4` |

### 9.2 먼저 볼 그래프/CSV

| 용도 | 파일 |
| --- | --- |
| learning curves | `project/results/figures/learning_curves/` |
| v2 no-push summary | `project/results/figures/no_push_eval_v2_4096_5000_seed0/` |
| v2 push heatmap | `project/results/figures/push_eval_v2_calibrated_final_seed0/` |
| v5 clean CSV | `project/results/no_push_eval/no_push_eval_v5_clean_presentation_4096_5000_seed0.csv` |
| v6 locked/tucked CSV | `project/results/no_push_eval/no_push_eval_v6_locked_tucked_presentation_4096_5000_seed0.csv` |

## 10. 실행 방법

### 10.1 학습 실행

학습은 오래 걸린다. 이미 seed 0 결과는 생성되어 있다.

```bash
bash project/scripts/run_v2_training_5000_seed0_4096.sh
bash project/scripts/run_v5_clean_tripod_training_5000_seed0_4096.sh
bash project/scripts/run_v6_locked_tucked_training_5000_seed0_4096.sh
```

### 10.2 평가 실행

```bash
bash project/scripts/run_v2_no_push_eval_seed0_4096_5000.sh
bash project/scripts/run_v2_push_eval_calibrated_final_seed0.sh
bash project/scripts/run_v5_clean_no_push_eval_seed0_4096_5000.sh
bash project/scripts/run_v6_locked_tucked_no_push_eval_seed0_4096_5000.sh
```

### 10.3 영상 렌더링

```bash
bash project/scripts/render_v5_clean_tripod_videos_seed0.sh
bash project/scripts/render_v6_locked_tucked_video_seed0.sh
```

push 영상은 `render_push_video.py`를 사용한다. 현재 렌더러에는 공/화살표 push visual과 clean-tripod overlay가 들어가 있다.

## 11. 발표에서 사용할 결론

가장 안전한 결론은 아래다.

> 한 다리 actuator torque가 0인 상황에서 기본 standing init만으로 PPO를 학습하면 초기 episode가 너무 빨리 실패하여 안정 전략 탐색이 어렵다. 기구학적 tripod posture prior는 초기 실패율을 줄이고 학습 가능한 상태 공간으로 policy를 유도한다. 또한 tripod-to-default init curriculum은 default init에서의 exploration bottleneck을 완화할 수 있다.

추가 결론:

- 단순 생존 성공률만으로는 안정적인 3족 지지를 주장할 수 없다.
- 따라서 foot contact, support load, FR foot clearance, support geometry, COM margin, non-foot contact를 함께 평가했다.
- clean reward/eval 기준을 적용하면 사람이 보기에도 납득 가능한 foot-only tripod stance를 만들 수 있었다.
- 외란 강건성은 현재 제한적이다. robust recovery까지 주장하려면 push-aware training이 필요하다.

## 12. 발표에서 조심할 표현

| 위험한 표현 | 왜 위험한가 | 대체 표현 |
| --- | --- | --- |
| PPO hidden layer가 최적해를 찾는 방식을 분석했다 | 내부 표현을 직접 증명하지 못함 | policy의 물리적 자세 안정화 전략을 분석했다 |
| tripod init이면 외란에도 강건하다 | push 성공률이 제한적임 | no-push standing 학습 효율은 개선되지만 외란 강건성은 추가 학습이 필요하다 |
| E4L이 메인 결과다 | E4L은 locked/tucked extension임 | E4L은 고장 다리 swing을 제거한 보조 조건이다 |
| v2 성공은 깨끗한 tripod stance다 | v2는 약한 기준의 local optimum 문제가 있음 | v2는 exploration 분석, v5는 clean stance 검증으로 분리한다 |

## 13. 남은 우선순위

| 우선순위 | 작업 | 이유 |
| --- | --- | --- |
| 1 | clean policy push 영상 추가 | 발표에서 standing과 외란 시각화를 같은 기준으로 보여주기 |
| 2 | E1C/E2C/E3C learning curve 정리 | clean reward 기준의 init 효과 보강 |
| 3 | PPT figure 선별 | 결과가 많아서 핵심만 보여주기 |
| 4 | seed 추가 | PPO 랜덤성 방어 |
| 5 | push-aware training pilot | robustness 한계 보완 |

시간이 없으면 1, 2, 3만 해도 발표 흐름은 만들 수 있다.

## 14. 친구에게 설명할 때 한 문장 버전

> 이 프로젝트는 한 다리 actuator가 완전히 죽은 Go2가 남은 세 발로 서는 문제에서, 그냥 default pose로 PPO를 시작하면 초반에 너무 빨리 넘어져 탐색이 막히고, tripod 자세 prior나 init curriculum을 주면 학습 가능한 상태가 되어 안정 자세를 찾는다는 것을 보여준다. 이후 영상 기준이 지저분해 보이는 문제를 해결하기 위해 clean foot-only 평가 기준을 추가했고, 외란은 아직 완전 robust하지 않아서 후속으로 push-aware training이 필요하다는 결론이다.
