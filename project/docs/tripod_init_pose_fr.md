# FR Tripod Init Pose Candidate

이 문서는 FR 고장 조건에서 사용할 기구학적 tripod init pose 후보를 기록한다.

주의: 아래 값은 MJCF 기하를 기준으로 계산한 초기 후보이며, MuJoCo에서 정적 안정성, 발 접촉, base height, collision 상태를 확인한 뒤 최종값으로 확정한다.

## 1. 목표

FR 다리 전체 actuator torque가 0인 조건에서, 남은 세 발 `FL`, `RL`, `RR`이 지지 삼각형을 만들도록 초기 자세를 설정한다.

기본 standing pose에서 FR을 고장 다리로 제거하면 base COM 투영점이 `FL-RL-RR` support triangle 밖으로 살짝 벗어난다. 따라서 tripod init은 단순히 FR 발만 드는 것이 아니라, 남은 세 발 기준으로 base COM이 support triangle 내부에 들어오도록 정상 3다리의 발 위치를 조정한다.

## 2. 사용한 MJCF 기하

Go2 XML에서 확인한 값:

```text
hip x offset      = +/-0.1934 m
hip y offset      = +/-0.0465 m
hip lateral link  = 0.0955 m
thigh length      = 0.213 m
calf length       = 0.213 m
base COM xy       = (0.021112, 0.0) in base frame
```

기본 standing pose:

```python
{
  ".*thigh_joint": 0.9,
  ".*calf_joint": -1.8,
  ".*R_hip_joint": 0.1,
  ".*L_hip_joint": -0.1,
}
```

## 3. 기본 pose의 FR-failure support check

기본 standing pose의 발 위치 후보:

```text
FL = ( 0.1934,  0.115086, -0.273017)
FR = ( 0.1934, -0.115086, -0.273017)
RL = (-0.1934,  0.115086, -0.273017)
RR = (-0.1934, -0.115086, -0.273017)
```

FR 고장 시 지지 발은 `FL`, `RL`, `RR`이다.

base COM의 barycentric coordinate with `FL-RL-RR`:

```text
(0.554581, -0.054581, 0.500000)
```

두 번째 값이 음수이므로, 기본 standing pose에서는 base COM 투영점이 support triangle 밖에 있다.

## 4. FR Tripod Init Candidate

후보 joint position:

```python
FR_TRIPOD_INIT_JOINT_POS = {
  "FL_hip_joint": -0.245,
  "FL_thigh_joint": 0.559,
  "FL_calf_joint": -1.760,

  "FR_hip_joint": 0.155,
  "FR_thigh_joint": 1.167,
  "FR_calf_joint": -2.334,

  "RL_hip_joint": -0.245,
  "RL_thigh_joint": 0.559,
  "RL_calf_joint": -1.760,

  "RR_hip_joint": -0.042,
  "RR_thigh_joint": 0.522,
  "RR_calf_joint": -1.643,
}
```

권장 base init height 후보:

```python
pos = (0.0, 0.0, 0.273)
```

기존 Go2 default init height는 `0.32`이지만, 위 후보는 발 z 위치가 대략 `-0.273 m`가 되도록 계산했다. 실제 환경에서는 foot sphere radius, contact settling, collision 상태를 고려해 `0.273`부터 `0.32` 사이를 검증한다.

## 5. Candidate Foot Positions

정상 3다리 목표 발 위치:

```text
FL = ( 0.2790,  0.0767, -0.2730)
RL = (-0.1078,  0.0767, -0.2730)
RR = (-0.1078, -0.1535, -0.2730)
```

이때 base COM의 barycentric coordinate with `FL-RL-RR`:

```text
(0.3333, 0.3336, 0.3332)
```

즉 COM 투영점이 세 발 지지 삼각형 중심 부근에 오도록 설계한 후보이다.

FR 고장 다리의 목표 발 위치는 접지하지 않도록 들어올린 후보를 사용했다.

```text
FR = (0.1934, -0.1151, -0.1800)
```

## 6. 관절 제한 확인

후보값은 XML에 명시된 관절 제한 안에 들어온다.

```text
hip range         = [-1.0472, 1.0472]
front thigh range = [-1.5708, 3.4907]
rear thigh range  = [-0.5236, 4.5379]
calf range        = [-2.7227, -0.83776]
```

## 7. 실험 해석상 주의점

현재 task는 `JointPositionActionCfg(..., use_default_offset=True)`를 사용한다. 따라서 robot config의 `init_state.joint_pos`를 바꾸면 reset pose뿐 아니라 default joint pose, action offset, posture reward 기준에도 영향을 줄 수 있다.

이 경우 실험은 순수한 "초기 상태만 변경"이 아니라 "기구학적 tripod posture prior 제공"으로 해석하는 것이 더 정확하다.

발표 표현:

> 기구학적으로 안정한 3족 초기 자세 prior가 PPO 학습 효율과 외란 회복 성능에 미치는 영향을 분석한다.

## 8. 다음 검증

MuJoCo 실행 환경에서 아래 항목을 확인한 뒤 최종 pose로 고정한다.

- reset 직후 `FL`, `RL`, `RR` 세 발이 안정적으로 접촉하는지
- `FR` 발이 접촉하지 않거나, 최소한 하중을 받지 않는지
- base height가 너무 낮아 body collision이 생기지 않는지
- roll/pitch가 초기부터 크게 기울지 않는지
- torque zero 적용 후에도 초기 2초 이상 넘어지지 않는지
