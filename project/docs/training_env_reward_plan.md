# Training Environment and Reward Plan

이 문서는 v1 학습 환경과 reward 세팅 기준을 정리한다.

## 1. v1 학습 목표

v1 학습 목표는 velocity tracking이 아니라 정적 3족 균형이다.

> FR 한 다리 전체 actuator torque가 0인 상태에서, 남은 세 다리로 넘어지지 않고 안정적으로 서 있는 policy를 학습한다.

따라서 기존 `Unitree-Go2-Flat` velocity task를 그대로 쓰기보다, Go2 flat task를 기반으로 standing 중심 task를 새로 구성한다.

## 2. 비교 task

| ID | Task 의미 | Failed Leg | Init Pose |
| --- | --- | --- | --- |
| E0 | 4-leg baseline standing | 없음 | 기본 standing |
| E1 | FR failure default-init standing | FR | 기본 standing |
| E2 | FR failure tripod-init standing | FR | FR tripod candidate |
| E3 | FR failure init-pose curriculum standing | FR | tripod-to-default reset curriculum |

v1의 메인 비교는 E1 vs E2다. E3는 E1이 실패했을 때 그 원인이 policy capacity 부족인지, 또는 default init에서 episode가 너무 빨리 끝나 PPO가 의미 있는 탐색을 못 했기 때문인지 분리하기 위한 assisted exploration 조건이다.

## 3. 중요한 해석 기준

`init_state.joint_pos`를 바꾸면 이 repo 구조에서는 다음 값들도 함께 달라질 수 있다.

- reset pose
- `default_joint_pos`
- `JointPositionActionCfg(use_default_offset=True)`의 action offset
- posture reward가 참조하는 default pose

따라서 단순히 `init_state`를 tripod pose로 바꾸는 실험은 순수한 "초기 상태만 변경"이 아니라 다음처럼 해석하는 것이 안전하다.

> 기구학적으로 안정한 tripod posture prior가 PPO 학습 효율과 외란 회복 성능에 미치는 영향

만약 "초기 상태만 변경"을 엄격하게 보고 싶다면 reset pose만 별도 event로 바꾸고, action offset과 posture reward target은 동일하게 유지해야 한다. E3는 이 목적에 맞춰, robot config와 action offset은 default-init 조건과 동일하게 두고 reset joint pose만 tripod에서 default로 점진적으로 이동시키는 curriculum으로 구현한다.

## 4. 환경 설정

| 항목 | v1 기준 |
| --- | --- |
| terrain | flat plane |
| command | zero velocity standing |
| episode length | 10 s 또는 20 s |
| failed leg | E1/E2/E3는 FR |
| failed actuator | `FR_hip_joint`, `FR_thigh_joint`, `FR_calf_joint` torque output 0 |
| reset root randomization | off |
| push during training | v1 pilot에서는 off, robust policy가 필요하면 later curriculum으로 on |
| domain randomization | E1/E2는 off. E3만 init-pose curriculum의 작은 joint noise 사용 |
| termination | fall, illegal contact, timeout |
| base height fall threshold | base height `< 0.23 m`이면 fall |

학습 초기에는 push와 일반 domain randomization을 끄고, 각 policy가 no-push 조건에서 안정적으로 서는지 먼저 확인한다. E3의 joint noise는 외란 강건성용 DR이 아니라 초기 탐색을 살리기 위한 reset 분포 확장으로 해석한다. 이후 외란 강건성을 학습 중에도 키우고 싶다면 push curriculum을 별도 실험으로 추가한다.

## 5. Observation 기준

Actor observation은 너무 복잡하게 늘리지 않는다.

권장 actor observation:

- base angular velocity
- projected gravity
- zero command 또는 command placeholder
- joint position relative to default
- joint velocity
- previous action

권장 critic-only observation:

- base linear velocity
- foot contact state
- foot contact force
- foot air time 또는 foot height

flat standing task에서는 height scan은 제거한다.

## 6. Action 기준

v1은 기존 구조와 맞춰 joint position action을 사용한다.

```python
JointPositionActionCfg(
  entity_name="robot",
  actuator_names=(".*",),
  scale=0.25,
  use_default_offset=True,
)
```

FR 고장 joint에도 policy는 action을 출력할 수 있다. 하지만 해당 actuator의 position-control gain과 damping이 0이므로 실제 torque output은 0이 된다.

고장난 다리 action을 action space에서 제거하지 않는다. 이유는 다음과 같다.

- 4-leg baseline, E1, E2, E3의 action dimension을 동일하게 유지할 수 있다.
- policy가 고장난 다리에 어떤 action을 내는지 분석할 수 있다.
- 실제 torque는 actuator gain/damping 제거로 0이 되므로 failure model과 충돌하지 않는다.

## 7. Reward 설계 원칙

v1 reward는 걷기보다 "넘어지지 않고 조용히 서기"에 맞춘다.

선행 논문 `Learning Quadrupedal Locomotion with Impaired Joints Using Random Joint Masking`은 impaired joint scenario에서 정상 gait를 강제하는 swing/stance/foot swing tracking reward를 제외한다. 본 프로젝트도 이 방향을 따른다. 즉, 고장 조건에서 정상 보행 gait reward를 복사해 넣지 않고, 3족 정적 지지에 맞는 contact/height/upright reward로 대체한다. 세부 메모는 `paper_reward_notes_2403_00398.md`를 따른다.

### 7.1 Main Reward Terms

| Reward | 목적 | 방향 |
| --- | --- | --- |
| alive/survival | 오래 버티기 | positive |
| base orientation | roll/pitch 작게 유지 | penalty |
| base angular velocity | 몸통 흔들림 감소 | penalty |
| base linear velocity | 정적 상태 유지 | penalty |
| base height | 몸통이 낮게 접히지 않고 서 있도록 유지 | penalty 또는 tracking |
| posture | 과도한 joint deviation 억제 | penalty 또는 tracking |
| action rate | action 튐 감소 | penalty |
| joint velocity | 떨림 감소 | penalty |
| torque/energy | 불필요한 힘 사용 감소 | penalty |
| foot slip | 지지 발 미끄러짐 감소 | penalty |
| illegal contact | body/calf/thigh 접촉 방지 | termination/penalty |

### 7.2 Optional Reward Terms

| Reward | 목적 | 주의 |
| --- | --- | --- |
| support contact reward | FL/RL/RR 접촉 유지 | 너무 강하면 발을 움직이는 recovery가 어려워질 수 있음 |
| failed foot no-load | FR 접촉력 또는 하중 감소 | FR foot이 살짝 닿는 것까지 과하게 벌하면 불안정할 수 있음 |
| COM inside support triangle | 기구학적 안정성 직접 유도 | 구현 난이도 있음. v1에서는 분석 지표로 먼저 사용 |

현재 E1/E2/E3 구현에는 `FR` 고장발을 수동 지지점으로 쓰는 꼼수를 줄이기 위해 두 reward를 추가한다.

| Reward | 구현 의미 | Weight |
| --- | --- | --- |
| `fr_disabled_foot_contact` | `FR` foot contact와 contact force를 penalty로 부여 | `-2.0` |
| `fr_support_feet_contact` | `FL`, `RR`, `RL` 세 지지발이 동시에 지면 접촉하면 sparse reward 부여 | `+1.0` |
| `fr_support_feet_stance_tracking` | 논문 stance phase tracking을 정적 tripod에 맞게 변형. 세 지지발이 접촉 중이고 xy 미끄러짐이 작을수록 dense reward 부여 | `+4.0` |

이 reward는 4-leg baseline E0에는 적용하지 않고, FR failure 조건인 E1/E2/E3에만 적용한다. 평가에서는 단순 생존 성공률(`survival_success`)과 별개로, 3족 접촉 패턴만 보는 `tripod_contact_success`, 자세와 발 접촉 조건을 함께 만족하는 `strict_success`, 고장난 `FR` 발 접촉률까지 낮은 `tripod_success`를 따로 기록한다.

`fr_support_feet_stance_tracking`은 arXiv:2403.00398v1의 Table I 중 stance phase tracking 구조를 그대로 보행 phase에 묶지 않고, 정적 3족 지지 조건에 맞게 다음 형태로 사용한다.

```text
reward = mean_i(contact_i * exp(-|v_xy,i|^2 / 0.25)), i in {FL, RR, RL}
```

논문은 impaired scenario에서 정상 gait reward를 제외하지만, stance foot의 미끄러짐을 줄이는 구조 자체는 고장 보행/지지 안정화에 유용하다. 우리 v1에서는 gait phase 대신 항상 `FL`, `RR`, `RL`이 stance foot이라고 보고 이 항목을 사용한다.

또한 낮게 접힌 자세가 foot contact만 유지하며 성공으로 찍히는 것을 막기 위해 standing task 공통 reward/termination을 강화한다.

| 항목 | 값 |
| --- | --- |
| base height fall threshold | `0.23 m` |
| base height target reward | target `0.28 m`, std `0.05 m` |
| body orientation penalty | 기존보다 강화 |

해석 기준:

| 지표 | 의미 |
| --- | --- |
| `survival_success` | 넘어지지 않고 episode horizon까지 생존 |
| `tripod_contact_success` | 생존하면서 `FL`, `RR`, `RL` 세 발로 지지하고 `FR` 접촉률은 낮으며 non-foot 접촉 없음 |
| `strict_success` | 생존 + 자세/높이/각속도 + 지지발 접촉 + non-foot 접촉 기준 통과 |
| `tripod_success` | `strict_success` + `FR` 접촉률 낮음 |

따라서 policy가 실제 3족 지지를 만들었지만 몸통이 낮거나 기울어진 경우에는 `tripod_contact_success`는 높고 `strict_success`는 낮을 수 있다. 이 경우는 접촉 전략은 성공했지만 자세 품질은 추가 reward 또는 평가 threshold로 따로 판단한다.

### 7.3 E3 Init Pose Curriculum

E3는 reward를 바꾸지 않고 reset 초기 자세 분포만 바꾼다.

```text
q_reset = (1 - alpha) * q_default + alpha * q_tripod + joint_noise
alpha: 1.0 -> 0.0 over 80,000 env steps
joint_noise: [-0.03, 0.03] rad
```

의도는 default init에서 episode가 너무 빨리 끝나 PPO가 의미 있는 탐색을 못 하는 문제를 완화하는 것이다. E3는 E2처럼 고정된 tripod prior를 끝까지 주는 실험이 아니라, 학습 후반에는 default init에 가까운 reset 상태에서 3족 지지 자세로 전환할 수 있는지 확인하는 assisted exploration 실험이다.

E3 평가를 해석할 때는 두 가지를 분리한다.

| 평가 | 목적 |
| --- | --- |
| E3 task no-push eval | curriculum 환경에서 학습이 정상적으로 진행됐는지 확인 |
| E3 policy cross-eval on E1/E2 task | 학습된 policy가 고정 default init 또는 고정 tripod init에서 실제로 버티는지 확인 |

따라서 최종 발표에서는 E3의 성능을 말할 때 반드시 fixed-init cross-eval 결과를 함께 제시한다. E3 task 자체로만 평가하면 reset curriculum 분포 효과가 평가에도 섞일 수 있다.

## 8. 기존 velocity reward에서 제거/약화할 것

기존 Go2 velocity task에는 걷기/속도 추종을 위한 reward가 포함되어 있다. standing v1에서는 다음 항목을 제거하거나 약화한다.

| 기존 성격 | v1 처리 |
| --- | --- |
| track linear velocity | zero command 기준으로 약하게 유지하거나 base velocity penalty로 대체 |
| track angular velocity | zero yaw 기준으로 약하게 유지하거나 base angular velocity penalty로 대체 |
| foot gait | 제거 |
| foot clearance | 제거 또는 매우 약화 |
| soft landing | 필요 시 유지 |
| velocity curriculum | 제거 |
| terrain curriculum | 제거 |
| random push during training | pilot에서는 제거 |

## 9. Termination 기준

v1 termination:

- timeout
- bad orientation
- base height below `0.23 m`
- non-foot illegal contact

기존 `bad_orientation` 70도는 너무 늦을 수 있다. standing task에서는 pilot 후 45도에서 60도 사이로 조정한다. base height threshold는 낮게 접힌 자세가 foot contact만 유지하며 성공으로 찍히는 것을 막기 위해 `0.23 m`로 둔다.

초기 실패율 분석에서는 reset 후 2초 이내 termination 또는 fall 조건을 initial failure로 기록한다.

## 10. 추천 구현 순서

1. 기존 `Unitree-Go2-Flat`을 기반으로 `Go2-Stand` config 생성
2. flat terrain, height scan 제거, zero command 설정
3. velocity/gait 관련 reward 제거
4. standing reward와 termination 정리
5. E0 4-leg baseline task 생성
6. E1 FR failure default-init task 생성
7. E2 FR failure tripod-init task 생성
8. E3 FR failure init-pose curriculum task 생성
9. 각 task를 `agent=zero` 또는 random policy로 reset/play smoke test
10. short PPO pilot 학습
11. 초기 실패율과 no-push standing success 확인
12. final checkpoint에 대해 fixed-init cross-eval 수행

## 11. Pilot 성공 기준

pilot에서 아래가 확인되면 full training으로 넘어간다.

- E0가 쉽게 서 있음
- E1은 학습 가능하면 좋지만, 계속 초기 실패하면 exploration bottleneck 결과로 기록하고 E3로 보완함
- E2는 reset 직후 tripod 자세가 무너지지 않음
- E3는 `Metrics/init_pose_alpha_mean`이 1.0에서 0.0 방향으로 감소하고, 학습 후반 default init 근처에서도 episode가 유지됨
- FR actuator gain/damping이 0이고 실제 actuator torque가 0임
- reward가 발산하지 않음
- episode length가 학습 중 증가함
