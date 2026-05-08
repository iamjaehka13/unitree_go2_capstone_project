# Experiment Scope v1

이 문서는 프로젝트 범위를 줄이고 실험 정의를 엄격하게 고정하기 위한 v1 기준이다.

## 1. v1에서 답할 질문

v1의 질문은 하나만 둔다.

> 한 다리의 토크가 0인 Unitree Go2가 정적 3족 지지를 학습할 때, 기구학적 tripod init 또는 init-pose curriculum은 기본 standing init보다 학습 효율과 균형 안정성을 개선하는가?

즉 v1은 "3족 정적 균형" 프로젝트다. 걷기 성능, 모든 고장 다리 조합, 마찰/질량/COM 일반화는 v2로 넘긴다.

## 2. v1 비교군

| ID | 조건 | 용도 |
| --- | --- | --- |
| E0 | 4-leg baseline + 기본 standing init | 정상 4족 reference. 메인 결론의 중심은 아님 |
| E1 | 3-leg failure + 기본 standing init | main comparison A |
| E2 | 3-leg failure + tripod init | main comparison B |
| E3 | 3-leg failure + tripod-to-default init curriculum | assisted exploration analysis |

v1의 메인 비교는 E1 vs E2다. E0는 "정상 상태라면 어느 정도까지 가능한가"를 보여주는 기준선으로 사용한다. E3는 E1이 실패한 이유가 policy capacity 부족인지, 너무 짧은 초기 생존 시간 때문에 PPO가 유효한 탐색을 못 한 것인지 분리하기 위한 추가 분석 실험이다.

최종 결과 해석에서는 E1/E2만으로 끝내지 않고 E3를 함께 사용한다.

- E1: 아무 도움 없이 default init에서 PPO가 학습 가능한지 확인
- E2: 기구학적 tripod posture prior가 학습을 쉽게 만드는지 확인
- E3: tripod에서 default로 이동하는 reset curriculum이 default-init policy 학습을 가능하게 하는지 확인

영상 확인 후 v2 성공 기준이 사람이 기대한 "깨끗한 3족 지지"를 충분히 강제하지 못한다는 문제가 확인되었다. 따라서 v3 strict comparison을 추가한다.

| ID | 조건 | 용도 |
| --- | --- | --- |
| E1S | FR failure + default init + strict support geometry reward | strict 기준에서도 default init이 실패하는지 확인 |
| E2S | FR failure + tripod init + strict support geometry reward | 기구학적 tripod stance를 실제로 학습 가능한지 확인 |
| E3S | FR failure + init curriculum + strict support geometry reward | curriculum이 strict tripod 기준에서도 default-init 회복을 만드는지 확인 |

v2 결과는 버리지 않고, 약한 contact/posture 기준에서 PPO가 찾은 local optimum 분석으로 둔다. v3는 기구학적으로 방어 가능한 tripod stance를 목표로 하는 재학습 실험이다.

추가 영상 확인 결과 calf로 버티는 듯한 자세가 관찰되면 v4 foot-only strict를 사용한다. v4는 v3의 support geometry 기준에 더해 calf/thigh/body 지면 접촉을 명시적으로 금지한다.

| ID | 조건 | 용도 |
| --- | --- | --- |
| E1F | FR failure + default init + foot-only strict reward | default init에서 foot-only 3족 지지 학습 가능성 확인 |
| E2F | FR failure + tripod init + foot-only strict reward | 기구학적 tripod init이 foot-only 자세를 만드는지 확인 |
| E3F | FR failure + init curriculum + foot-only strict reward | curriculum이 foot-only default-init 회복으로 이어지는지 확인 |

v4 실행 전 점검에서 Go2 foot contact sensor의 실제 순서가 `FL, FR, RL, RR`임을 확인했다. 따라서 기존처럼 `FR, FL, RR, RL`로 indexing하면 고장 발과 지지 발 판정이 뒤섞인다. 이 문제를 수정하고, 발표 영상에서 "누가 봐도 3발로 깨끗하게 서는" 결과를 목표로 v5 clean tripod comparison을 추가한다.

| ID | 조건 | 용도 |
| --- | --- | --- |
| E1C | FR failure + default init + clean tripod reward | default init에서 깨끗한 foot-only tripod가 가능한지 확인 |
| E2C | FR failure + tripod init + clean tripod reward | tripod init이 발표 가능한 3족 지지 자세를 만드는지 확인 |
| E3C | FR failure + init curriculum + clean tripod reward | curriculum이 clean tripod 기준에서도 default-init 회복을 만드는지 확인 |

v5 clean 기준은 v4 foot-only에 더해 `FR` foot clearance, 세 support foot의 실제 하중 분담, 더 강한 base height/upright reward를 포함한다.

FR torque-zero passive leg가 영상에서 관성에 의해 흔들리는 현상을 분리하기 위해 v6 locked/tucked extension을 추가한다. 이 조건은 메인 비교를 대체하지 않고 발표용/분석용 보조 실험으로 둔다.

| ID | 조건 | 용도 |
| --- | --- | --- |
| E4L | FR failure + locked/tucked FR joints + clean tripod reward | 고장 다리 swing을 제거했을 때 clean tripod 자세와 시각화가 얼마나 개선되는지 확인 |

E4L은 FR actuator torque는 계속 0으로 두지만, `FR_hip_joint`, `FR_thigh_joint`, `FR_calf_joint`의 joint range를 tuck pose 주변 `+-0.001 rad`로 제한한다. 따라서 E4L은 "순수 passive torque-zero leg"가 아니라 "mechanically locked/tucked failure" 조건으로 해석한다.

## 3. v1에서 고정할 조건

실험의 결론이 흐려지지 않도록 아래 조건은 고정한다.

| 항목 | v1 기준 |
| --- | --- |
| robot | Unitree Go2 |
| terrain | flat plane |
| failed leg | v1 main experiment는 `FR`로 고정 |
| failed joint | `FR_hip_joint`, `FR_thigh_joint`, `FR_calf_joint` |
| failure model | FR 다리 3개 joint의 actuator torque output을 모두 0으로 설정 |
| locked/tucked extension | E4L에서만 FR 세 joint range를 tuck pose 주변 `+-0.001 rad`로 제한 |
| fall height threshold | base height가 `0.23 m` 미만이면 fall |
| command | 정적 standing 목표. evaluation에서는 목표 속도 0 |
| policy algorithm | PPO |
| PPO hyperparameters | E1/E2/E3 동일 |
| reward weights | E1/E2/E3 동일 |
| simulation dt/decimation | E1/E2/E3 동일 |
| train scale | 본 실험은 `4096` parallel env, `5000` PPO iterations 기준 |
| train seeds | 최소 3개 권장. v1 본 실험은 seed 0부터 수행 |
| eval initial state | no-push main eval은 각 task의 init 기준. policy 자체 비교는 fixed default/tripod cross-eval 사용 |

고장 다리는 v1 main experiment에서 `FR`로 확정한다. 이유는 코드와 문서에서 다리 순서를 설명하기 쉽고, 이후 좌우/전후 대칭 확장도 명확하기 때문이다.

`RR` 고장은 v1.5 extension으로 둔다. 즉, FR 조건으로 학습/평가/시각화 파이프라인을 먼저 완성한 뒤, 시간이 허용되면 RR 조건에서 축소 실험을 수행한다.

FR 고장은 hip actuator만 끄는 실험이 아니다. `FR_hip_joint`, `FR_thigh_joint`, `FR_calf_joint` 3개의 actuator torque output을 모두 0으로 만드는 한 다리 전체 actuator failure로 정의한다. action을 0으로 두는 것은 PD controller가 여전히 torque를 만들 수 있으므로 v1 failure model로 사용하지 않는다.

현재 구현에서는 MuJoCo가 `forcerange=[0, 0]` actuator를 거부하므로, FR 세 actuator의 position-control `stiffness`와 `damping`을 0으로 만들어 torque output이 0이 되게 한다. action space에는 FR actuator가 남아 있으므로 policy가 고장난 다리에 어떤 action을 내는지도 분석할 수 있다.

세부 구현 메모는 `torque_failure_model.md`를 따른다. FR tripod init 후보값은 `tripod_init_pose_fr.md`에 기록한다.

학습 환경과 reward 세팅은 `training_env_reward_plan.md`를 따른다.

## 4. 독립변수와 추가 분석 변수

v1의 핵심 독립변수는 다음 하나다.

> 3-leg failure 조건에서 학습 시작 자세가 기본 standing init인가, 기구학적 tripod init인가?

E3는 이 독립변수에 대한 보조 분석 변수다. E3는 고정 tripod init과 고정 default init을 직접 비교하는 조건이 아니라, reset pose를 tripod에서 default로 점진적으로 이동시키는 curriculum을 사용한다. 따라서 E3 결과는 "초기 자세 prior 자체"라기보다 "초기 탐색을 살리는 reset curriculum이 default-init policy 학습을 가능하게 하는가"로 해석한다.

주의할 점:

- 만약 `init_state`를 바꾸는 순간 action offset이나 posture reward target도 같이 바뀐다면, 이것은 순수한 "초기 자세"가 아니라 "posture prior" 실험이 된다.
- 순수하게 초기 자세의 영향만 보려면 reset pose만 바꾸고, reward target과 action offset은 동일하게 유지해야 한다.
- 구현 난이도 때문에 reset pose, action offset, posture target이 함께 바뀐다면 발표에서는 "초기 자세 prior" 또는 "kinematic posture prior"라고 표현한다.

이 구분은 중요하다. 나중에 코드 구현 전에 반드시 확인한다.

## 5. v1에서 제외할 것

아래 항목은 v1 결론을 흐릴 수 있으므로 제외한다.

| 제외 항목 | 이유 |
| --- | --- |
| 모든 고장 다리 조합 | 실험 수가 4배 증가함. v1에서는 FR만 수행하고 RR은 extension으로 둠 |
| rough terrain | 초기 자세 효과와 지형 적응 효과가 섞임 |
| 마찰/질량/COM 일반화 | main result 이후 보조 실험으로 충분함 |
| 지속 force push | v1에서는 impulse push만 먼저 완성 |
| velocity tracking 성능 | 정적 3족 지지 질문과 섞이면 해석이 어려움 |
| hidden layer 해석 | 방어하기 어렵고 핵심 결론에 필수 아님 |

## 5.1 E3 Assisted Exploration

E3는 E1과 같은 `FR` whole-leg torque-zero failure를 사용하지만, reset joint pose를 학습 단계에 따라 다음 분포에서 샘플링한다.

```text
q_reset = (1 - alpha) * q_default + alpha * q_tripod + noise
alpha: 1.0 -> 0.0
```

해석:

- `alpha=1.0`: 기구학적 tripod pose 근처에서 시작하여 초기 탐색 가능성을 확보
- `alpha=0.0`: default standing pose에서 시작
- `noise`: 작은 joint-position DR로 주변 자세 분포를 탐색

E3가 default 평가에서 성공하면 E1 실패의 주원인이 policy capacity 부족이 아니라 초기 exploration bottleneck이었음을 보강한다. E3도 실패하면 단순한 curriculum보다 명시적인 tripod posture prior 자체가 더 중요하다는 해석이 가능하다.

현재 구현값:

| 항목 | 값 |
| --- | --- |
| reset schedule | `alpha: 1.0 -> 0.0` |
| decay steps | `80,000` env steps |
| alpha noise | `0.10` |
| joint noise | `[-0.03, 0.03] rad` |
| action offset/posture target | default-init robot config 기준 |

E3 policy 평가는 반드시 cross-eval을 포함한다.

| Cross-eval | 해석 |
| --- | --- |
| E3 policy on E1 default-init env | curriculum 학습이 default init에서도 서는 policy를 만들었는지 확인 |
| E3 policy on E2 tripod-init env | E3 policy가 tripod pose에도 일반화되는지 확인 |
| E2 policy on E1 default-init env | E2가 tripod posture prior에 특화됐는지 확인 |

## 6. 학습 평가 정의

### 6.1 초기 실패율

초기 실패율은 다음 둘 중 구현 가능한 방식으로 측정한다.

| 방식 | 정의 |
| --- | --- |
| training log 방식 | 학습 초반 `N` iteration 동안 종료된 episode 중 `2.0 s` 이전에 fall한 비율 |
| checkpoint eval 방식 | early checkpoint를 고정 평가하고, `2.0 s` 이전 fall 비율을 계산 |

v1 기본값:

- checkpoint: `0`, `100`, `500`, `1000`, `2000`, `3000`, `4000`, `4999`
- episode horizon: `10.0 s`
- initial failure: reset 후 `2.0 s` 안에 fall

fall 조건:

- termination이 timeout이 아닌 경우
- 또는 base height가 기준값 이하로 내려간 경우
- 또는 roll/pitch가 termination threshold를 초과한 경우

### 6.2 수렴속도

수렴속도는 wall-clock 시간이 아니라 environment step 또는 PPO iteration 기준으로 비교한다.

v1 기준:

> no-push standing 평가에서 success rate가 90% 이상인 상태가 2개 연속 checkpoint에서 유지되는 가장 빠른 iteration.

success 조건:

- `10.0 s` 동안 fall하지 않음
- 마지막 `2.0 s` 동안 base height가 `0.23 m` 이상 안정 범위에 있음
- 마지막 `2.0 s` 동안 roll/pitch가 각각 10도 이내
- FR failure 조건에서는 마지막 `2.0 s` 동안 `FL`, `RR`, `RL` 지지발 접촉이 유지되고, 고장난 `FR` 발 접촉률이 낮아야 함
- 마지막 `2.0 s` 동안 thigh/calf/body 등 non-foot 지면 접촉이 없어야 함

발표용 clean-tripod 판정은 별도로 둔다. 영상에서 foot-only tripod가 명확하지만 strict metric이 짧은 settling까지 실패로 잡는 경우를 분리하기 위해, presentation-clean metric은 roll/pitch `12 deg`, last-window fraction `0.90`을 사용한다. strict metric 결과도 함께 보존한다.

## 7. Robustness 평가 정의

### 7.1 기본 조건

| 항목 | v1 기준 |
| --- | --- |
| evaluation mode | deterministic policy |
| episode horizon | `10.0 s` |
| push timing | reset 후 `2.0 s` |
| push target | `base_link` 또는 base COM |
| push direction | front, back, left, right |
| push type | impulse push |
| push duration | `0.1 s` |
| push magnitude | weak, medium, strong |

push는 가능하면 실제 external force로 구현한다. 만약 기존 framework의 `push_by_setting_velocity`를 사용한다면, 발표와 문서에서는 "force"가 아니라 "velocity perturbation"이라고 정확히 표현한다.

### 7.2 Push magnitude

크기는 로봇 무게 기준으로 정규화한다.

본래 stress-test 기준은 다음과 같다.

```text
weak   = 0.5 * body_weight
medium = 1.0 * body_weight
strong = 1.5 * body_weight
```

다만 seed 0 최종 policy에서는 위 기준이 standing policy에 너무 강해서 E1/E2/E3 모두 실패했다. 따라서 발표용 main robustness heatmap은 policy 간 차이가 드러나는 calibrated push 기준을 사용한다.

```text
weak   = 0.25 * body_weight
medium = 0.35 * body_weight
strong = 0.45 * body_weight
```

```text
body_weight = robot_mass * gravity
impulse = force * duration
```

seed 0 calibrated push에서 계산된 실제 수치는 약 `37.3 N`, `52.2 N`, `67.1 N`이고, `0.1 s` impulse 기준으로는 약 `3.7 Ns`, `5.2 Ns`, `6.7 Ns`다.

### 7.3 반복 수

최종 평가 권장값:

- train seed: 3개
- eval episode: push 조건당 seed별 20회
- push 조건: 4 directions x 3 magnitudes = 12개

따라서 FR failure 조건 E1/E2/E3 각각 `3 seeds x 12 conditions x 20 episodes = 720 episodes`가 된다. 세 조건을 모두 수행하면 총 `2160` episodes다.

시간이 부족하면 pilot은 다음으로 줄인다.

- train seed: 1개
- eval episode: 조건당 10회
- push 조건: left/right/front/back x medium만 먼저

## 8. Robustness 지표

v1에서 메인 지표는 4개만 사용한다.

| 지표 | 정의 |
| --- | --- |
| success rate | push 후 episode 끝까지 fall하지 않은 비율 |
| survival time | push 이후 fall까지 걸린 시간. fall하지 않으면 horizon까지 |
| recovery time | push 이후 안정 조건으로 복귀하는 데 걸린 시간 |
| max body tilt | push 이후 최대 `abs(roll)` 또는 `abs(pitch)` |

평가 성공률은 세 단계로 분리해서 기록한다.

| 지표 | 정의 |
| --- | --- |
| `survival_success` | timeout까지 fall/termination 없이 생존 |
| `tripod_contact_success` | 생존 + `FL`, `RR`, `RL` 지지발 접촉 유지 + 고장난 `FR` 발 접촉률 낮음 + non-foot 접촉 없음 |
| `strict_success` | 생존 + 마지막 안정 구간에서 자세/높이/각속도/지지발 접촉/non-foot 접촉 조건 만족 |
| `kinematic_tripod_success` | 생존 + support triangle area/foot spacing/COM margin 기준 만족 |
| `tripod_success` | `strict_success` + 고장난 `FR` 발 접촉률 낮음 + `FR` foot clearance + support foot load + `kinematic_tripod_success` |

`tripod_contact_success`는 "진짜 3족 지지 패턴을 만들었는가"를 보기 위한 접촉 기준이다. `strict_success`와 `tripod_success`는 여기에 자세/높이 기준까지 포함하므로, learned tripod pose가 낮거나 기울어진 경우에는 접촉 성공과 자세 성공을 분리해서 해석한다. 단, base height가 `0.23 m`보다 낮으면 foot contact가 있더라도 fall로 본다.

recovery 조건:

- push 이후 roll/pitch가 각각 10도 이내
- base angular velocity가 작은 범위로 복귀
- base height가 안정 범위 안에 있음
- 위 조건이 `0.5 s` 이상 연속 유지

보조 지표:

- torque norm
- energy consumption
- foot slip
- contact force distribution
- COM displacement
- support triangle area
- minimum support foot distance
- COM support margin

보조 지표는 메인 결론이 아니라 해석용으로 사용한다.

Strict tripod geometry 기준:

| 항목 | 값 |
| --- | ---: |
| minimum support triangle area | `0.025 m^2` |
| minimum support foot distance | `0.16 m` |
| minimum COM support margin | `0.0 m` |

기준 발은 FR failure에서 `FL`, `RR`, `RL`이다. COM은 현재 구현에서는 base projection을 proxy로 사용한다.

Foot-only strict 기준:

| 항목 | 값 |
| --- | ---: |
| non-foot illegal contact force threshold | `1.0 N` |
| non-foot contact penalty | calf/thigh/body contact + force penalty |
| init base height | `0.295 m` |

non-foot contact에는 hip/thigh/calf/body collision geom과 지면의 접촉이 포함된다. Foot-only 성공 영상에서는 `FL`, `RR`, `RL` foot contact marker가 켜지고 non-foot contact marker가 꺼진 상태를 보여준다.

Clean tripod 기준:

| 항목 | 값 |
| --- | ---: |
| contact sensor order | `FL`, `FR`, `RL`, `RR` |
| support feet | `FL`, `RL`, `RR` |
| disabled foot | `FR` |
| minimum support triangle area | `0.04 m^2` |
| minimum support foot distance | `0.22 m` |
| minimum support foot force | `15 N` |
| minimum disabled foot height | `0.045 m` |

이 기준은 "버티긴 하지만 낮게 웅크리거나 calf/body를 쓰는 자세"를 성공으로 세지 않기 위한 발표용 최종 기준이다.

외란 평가는 발표용 시각화를 함께 생성한다. 영상/그래프 산출물 기준은 `push_visualization_plan.md`를 따른다.

## 9. 자세 전략 분석

v1에서는 "PPO hidden layer가 최적해를 찾는 방식"을 분석하지 않는다.

대신 다음을 분석한다.

> PPO 학습 과정에서 policy가 어떤 물리적 자세 안정화 전략으로 수렴하는가?

측정 항목:

- checkpoint별 평균 joint angle
- checkpoint별 base height, roll, pitch
- 최종 policy의 torque RMS
- 정상 3다리의 contact force 분포
- 고장난 다리의 action 출력
- designed tripod pose와 learned final pose의 차이

분석 checkpoint:

- `0`
- `100`
- `500`
- `1000`
- `final`

실제 저장된 checkpoint 간격에 맞춰 조정한다.

## 10. 최종 결과물

v1이 성공했다고 판단하는 최소 결과물은 다음이다.

- E0/E1/E2/E3 학습 curve 비교
- E1/E2/E3 초기 실패율 비교
- E1/E2/E3 수렴속도 비교
- E1/E2/E3 fixed-init cross-eval table
- E1/E2/E3 impulse push robustness table
- push direction x magnitude 성공률 heatmap
- weak/medium/strong push side-by-side 영상
- push 방향/크기 화살표 overlay가 포함된 PPT용 comparison video
- final pose, torque, contact force 비교
- 4-leg baseline reference 결과

## 10.1 RR Extension

FR main experiment가 끝난 뒤 시간이 허용되면 RR 고장 조건을 추가한다. RR은 v1의 핵심 결론을 보강하는 일반성 확인 실험이며, FR만큼 모든 결과물을 만들 필요는 없다.

RR extension의 최소 결과물:

- E1/E2 학습 curve 비교. 시간이 허용되면 E3도 추가
- E1/E2 초기 실패율 비교. 시간이 허용되면 E3도 추가
- medium impulse push 4방향 성공률
- final pose, torque, contact force 비교

발표에서는 다음처럼 표현한다.

> 주 실험은 FR 고장 조건에서 수행하고, 결론의 일반성을 확인하기 위해 RR 고장 조건을 추가 실험으로 검토한다.

## 11. 발표에서 방어 가능한 결론 형태

결과가 어떻게 나오든 아래 네 방향 중 하나로 해석할 수 있어야 한다.

### Case A: tripod init이 학습과 robustness 모두 개선

기구학적 tripod init이 초기 실패율을 낮추고, PPO가 더 빠르게 안정화 전략을 형성했으며, 최종 외란 회복 성능도 개선했다.

### Case B: tripod init이 학습은 빠르게 하지만 최종 robustness는 비슷함

초기 자세는 sample efficiency에는 영향을 주지만, 충분한 학습 후 PPO가 비슷한 안정화 전략에 수렴했다.

### Case C: 차이가 거의 없음

현재 reward/action/failure model에서는 초기 자세보다 PPO의 reward 구조 또는 policy capacity가 더 지배적이었다. 이 경우에도 초기 자세 영향이 제한적이라는 의미 있는 결론이 된다.

### Case D: default init은 실패하지만 E3 curriculum은 성공

기본 standing init에서는 episode가 너무 빨리 끝나 PPO가 유효한 탐색을 하지 못한다. 그러나 tripod-to-default reset curriculum을 주면 default init에서도 서는 policy가 만들어진다. 이 경우 핵심 결론은 "tripod init이 단순히 좋은 자세를 제공한다"가 아니라, "기구학적 prior가 PPO의 초기 exploration bottleneck을 완화한다"가 된다.

## 11.1 현재 seed 0 본 실험 결과

`4096` parallel env, `5000` PPO iterations, seed 0 기준으로 E0/E1/E2/E3 학습은 모두 완료됐다.

| ID | 최종 no-push survival | 최종 strict | 초기 실패율 | 해석 |
| --- | ---: | ---: | ---: | --- |
| E0 | 1.00 | 1.00 | 0.00 | 정상 4족 reference 성공 |
| E1 | 0.00 | 0.00 | 1.00 | default init에서는 5000 iter 후에도 실패 |
| E2 | 1.00 | 1.00 | 0.00 | tripod init에서는 안정적인 3족 지지 성공 |
| E3 | 1.00 | 1.00 | 0.00 | init curriculum으로 default-init 성공 policy 형성 |

최종 policy cross-eval 결과:

| Policy | default-init eval | tripod-init eval | 해석 |
| --- | ---: | ---: | --- |
| E1 policy | 실패 | 실패 | 의미 있는 안정화 전략을 학습하지 못함 |
| E2 policy | 실패 | 성공 | tripod pose에 특화된 policy |
| E3 policy | 성공 | 실패 | default init에서 서는 별도 안정화 전략을 학습 |

따라서 현재 seed 0 결과는 Case D에 해당한다. 보고서에서는 E2와 E3를 모두 사용해, tripod prior가 학습 효율을 높이고 E3 curriculum이 default-init exploration bottleneck을 완화한다는 식으로 정리한다.

외란 평가는 calibrated push 기준에서 다음 결과가 나왔다.

| Policy | Eval init | calibrated push success | survival success | 해석 |
| --- | --- | ---: | ---: | --- |
| E1 | default | 0.00 | 0.00 | push 전에 이미 초기 실패 |
| E2 | tripod | 0.33 | 0.33 | `back/right` weak/medium에는 버티지만 방향 민감성이 큼 |
| E3 | default | 0.00 | 0.08 | no-push standing은 성공하지만 strict tripod push success는 실패 |

이 결과는 no-push standing과 외란 강건성을 분리해서 해석해야 함을 보여준다. 현재 v1 결론은 "tripod prior와 init curriculum이 standing 학습을 가능하게 한다"까지는 강하고, "외란 강건성까지 확보한다"는 결론은 push-aware training을 추가해야 방어 가능하다.

## 12. 다음 구현 순서

1. 완료: 고장 다리 확정
2. 완료: 현재 Go2 모델의 joint/actuator 이름 확인
3. 완료: torque zero를 적용할 위치 결정
4. 완료: tripod init pose 설계 및 MuJoCo에서 정적 안정성 확인
5. 완료: E1/E2/E3 task config 생성
6. 완료: seed 0 full 학습 실행
7. 완료: no-push 평가로 초기 실패율/수렴속도 로그 확인
8. 완료: training/no-push CSV를 발표용 그래프로 변환
9. 완료: fixed-init cross-eval로 policy 자체 강건성 확인
10. 완료: impulse push 평가 스크립트 작성 및 calibrated push 평가
11. 완료: 발표용 push 영상 렌더링과 right-medium side-by-side 편집
12. 완료: strict tripod 성공 기준 및 E1S/E2S/E3S task 추가
13. 완료: foot-only strict reward/termination 및 v4 실행 스크립트 추가
14. 완료: contact sensor foot order 수정 및 clean tripod 평가 기준 추가
15. 완료: E1C/E2C/E3C clean tripod full training 실행
16. 완료: clean no-push eval runner 추가. `run_v5_clean_no_push_eval_seed0_4096_5000.sh`
17. 완료: clean final policy 영상 스크립트 작성. `render_clean_tripod_video.py`와 `render_v5_clean_tripod_videos_seed0.sh`는 foot clearance, support load, non-foot contact, support triangle/COM margin overlay를 포함
18. 완료: E4L locked/tucked extension task와 train/eval/render runner 추가
19. 완료: E4L `4096` env, `5000` iteration 학습 및 no-push/영상 생성
20. 다음: E2C와 E4L 영상/수치 비교 자료 정리
21. 다음: clean final policy push 영상 생성 및 side-by-side 편집
22. 다음: push-aware training 또는 push DR pilot으로 외란 강건성 보완
23. 시간이 허용되면 final 3 seeds 실험 실행
