# Reward Notes from arXiv:2403.00398v1

참고 논문:

```text
Learning Quadrupedal Locomotion with Impaired Joints Using Random Joint Masking
arXiv:2403.00398v1
Local file: /home/iamjaehka13/Downloads/2403.00398v1.pdf
```

## 1. 논문에서 직접 가져올 핵심

논문은 joint impairment 상황에서 정상 보행 gait를 강제하는 일부 reward가 비효율적이라고 보고, impaired joint scenario에서는 Table I의 세 reward를 제외한다.

| Reward | 논문 처리 | 우리 프로젝트 처리 |
| --- | --- | --- |
| Swing phase tracking | impaired scenario에서 제외 | 정적 standing 실험이므로 제외 |
| Stance phase tracking | impaired scenario에서 제외 | 보행 phase 대신 `FL/RR/RL` support contact reward로 대체 |
| Foot swing tracking | impaired scenario에서 제외 | 정적 standing 실험이므로 제외 |

따라서 이 논문을 "카피"한다는 의미는 gait reward를 넣는 것이 아니라, 고장 조건에서는 정상 gait prior를 약하게 하거나 제거하고 고장 상태에 맞는 contact/height/upright reward를 쓰는 것이다.

## 2. 우리 v1 reward에 반영한 방향

우리 목표는 보행이 아니라 `FR` actuator failure에서 3발 정적 지지를 만드는 것이다. 따라서 다음 항목을 강화한다.

| 항목 | 목적 |
| --- | --- |
| `fr_support_feet_contact` | `FL`, `RR`, `RL` 세 발 지지 유지 |
| `fr_support_feet_stance_tracking` | 논문 stance phase tracking을 정적 tripod 지지용 dense reward로 변형 |
| `fr_disabled_foot_contact` | 고장난 `FR` 발을 수동 지지점으로 쓰는 것 방지 |
| `base_height_l2` | 몸통이 낮게 접힌 자세로 버티는 것 방지 |
| `body_orientation_l2` | 몸통 roll/pitch가 과하게 기울어지는 것 방지 |
| `foot_slip` | 지지 발 미끄러짐 감소 |
| `base_height` termination | base height `< 0.23 m`이면 fall |

현재 height/upright 기준:

```text
base height fall threshold = 0.23 m
base height reward target  = 0.28 m
base height reward std     = 0.05 m
body orientation penalty   = 기존보다 강화
```

논문 Table I의 stance phase tracking은 stance foot이 지면에 닿아 있고 xy 속도가 작을수록 보상을 주는 형태다. 우리 v1은 보행 phase가 없으므로 `FL`, `RR`, `RL`을 항상 stance foot으로 보고 다음과 같이 변형한다.

```text
fr_support_feet_stance_tracking
= mean_i(contact_i * exp(-|v_xy,i|^2 / 0.25)), i in {FL, RR, RL}
weight = +4.0
```

기존 `fr_support_feet_contact`는 세 발이 동시에 닿았는지 보는 sparse reward 및 로그용 신호로 낮춰서 유지한다.

## 3. 논문과 다른 점

논문은 다양한 joint failure를 하나의 policy가 다루도록 random joint masking, teacher-student joint status estimator, progressive curriculum을 사용한다. 우리 v1은 졸업프로젝트 범위를 줄이기 위해 `FR` 전체 다리 actuator failure 하나에 고정한다.

또한 논문은 action과 torque를 함께 masking하지만, 우리 구현은 `FR` actuator torque output을 실제로 0으로 만들고 action output은 유지한다. 이유는 고장난 다리에 대해 policy가 어떤 action을 내는지 분석하기 위해서다. 단, 실제 torque는 stiffness/damping 0으로 인해 발생하지 않는다.

## 4. 발표에서 쓸 수 있는 표현

> 선행연구는 고장 joint 상황에서 정상 보행 gait reward가 오히려 학습을 방해할 수 있다고 보고, impaired scenario에서는 gait phase tracking reward를 제외했다. 본 연구도 보행이 아니라 3족 정적 지지가 목표이므로 gait reward를 사용하지 않고, 세 지지발 접촉, 고장발 비사용, base height, 몸통 자세 안정성을 중심으로 reward를 재구성했다.
