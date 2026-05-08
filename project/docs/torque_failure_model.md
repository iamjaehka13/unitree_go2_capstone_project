# Torque Failure Model

이 문서는 v1 실험에서 사용할 한 다리 고장 정의와 구현 후보 위치를 정리한다.

## 1. 실험 정의

v1 main experiment의 고장 다리는 `FR`이다.

고장 joint:

```text
FR_hip_joint
FR_thigh_joint
FR_calf_joint
```

고장 조건:

```text
FR_hip_joint actuator torque output   = 0
FR_thigh_joint actuator torque output = 0
FR_calf_joint actuator torque output  = 0
```

즉 hip만 끄는 고장이 아니라, FR 한 다리 전체 actuator failure로 정의한다.

## 2. Action 0과 Torque 0의 차이

이 실험에서는 action을 0으로 만드는 방식은 사용하지 않는다.

이유:

- 현재 task는 `JointPositionActionCfg` 기반 position target action을 사용한다.
- action이 0이어도 `use_default_offset=True`이면 target position은 default joint pose가 될 수 있다.
- position actuator 또는 PD controller가 살아 있으면 default pose를 추종하려고 torque를 계속 만들 수 있다.

따라서 v1의 고장 모델은 action mask가 아니라 actuator가 실제 torque를 만들지 못하게 하는 방식이어야 한다.

## 3. 현재 repo에서 확인한 위치

Go2 actuator config는 다음 파일에 있다.

```text
src/assets/robots/unitree_go2/go2_constants.py
```

현재 Go2 actuator는 joint type별 regex로 묶여 있다.

```python
GO2_ACTUATOR_HIP = BuiltinPositionActuatorCfg(
  target_names_expr=(".*hip_.*",),
  effort_limit=23.5,
)

GO2_ACTUATOR_THIGH = BuiltinPositionActuatorCfg(
  target_names_expr=(".*thigh_.*",),
  effort_limit=23.5,
)

GO2_ACTUATOR_CALF = BuiltinPositionActuatorCfg(
  target_names_expr=(".*calf_.*",),
  effort_limit=45,
)
```

Action config는 다음 파일에 있다.

```text
src/tasks/velocity/velocity_env_cfg.py
```

현재 action은 모든 actuator를 대상으로 한다.

```python
JointPositionActionCfg(
  entity_name="robot",
  actuator_names=(".*",),
  scale=0.25,
  use_default_offset=True,
)
```

## 4. 구현 후보

### Option A: Actuator config를 joint별로 분리하고 FR actuator 출력을 0으로 설정

v1의 권장 구현 방식이다.

아이디어:

- Go2의 12개 actuated joint를 각각 `BuiltinPositionActuatorCfg`로 분리한다.
- 정상 joint는 기존 gain과 effort limit을 유지한다.
- `FR_hip_joint`, `FR_thigh_joint`, `FR_calf_joint`만 position actuator의 `stiffness=0.0`, `damping=0.0`, `effort_limit=None`으로 둔다.

장점:

- 실험 정의와 가장 직접적으로 맞는다.
- policy action은 그대로 출력하지만, 고장 joint는 실제 torque를 만들지 못한다.
- 기존 actuator action order를 유지하기 쉽다.

검증 결과:

- `effort_limit=0.0`은 MuJoCo position actuator의 `forcerange=[-0.0, 0.0]`을 만들지만, MuJoCo compile 단계에서 `invalid force range`로 거부된다.
- 그래서 실제 구현은 FR actuator의 `stiffness`와 `damping`을 0으로 만들어 PD actuator가 torque를 생성하지 못하게 한다.
- FR actuator는 action space에는 남아 있지만, MuJoCo actuator gain/bias가 0이라 output force/torque가 0이 된다.
- 12개 joint별 actuator config를 쓰면 기존 Go2 actuator order가 유지된다.

검증된 actuator order:

```text
FL_hip_joint
FR_hip_joint
RL_hip_joint
RR_hip_joint
FL_thigh_joint
FR_thigh_joint
RL_thigh_joint
RR_thigh_joint
FL_calf_joint
FR_calf_joint
RL_calf_joint
RR_calf_joint
```

검증된 FR actuator gain/bias:

```text
FR_hip_joint   gain = 0.0, bias1 = -0.0, bias2 = -0.0
FR_thigh_joint gain = 0.0, bias1 = -0.0, bias2 = -0.0
FR_calf_joint  gain = 0.0, bias1 = -0.0, bias2 = -0.0
```

- actuator torque는 0이지만 joint armature나 passive joint dynamics는 모델에 남을 수 있다. 이것은 실제 actuator power-off leg의 passive 링크 특성으로 보고 문서화한다.

### Option B: Torque output 단계에서 FR joint torque를 0으로 mask

`mjlab` 내부 torque 계산부에 접근할 수 있다면 가장 명확한 방식이다.

아이디어:

```python
computed_torque[:, fr_joint_ids] = 0.0
```

장점:

- 최종 torque output을 직접 0으로 만들 수 있다.
- actuator config가 복잡해지지 않는다.

확인할 점:

- 현재 repo에는 `mjlab` 소스가 포함되어 있지 않다.
- `mjlab==1.2.0` 설치 환경에서 actuator 계산부를 찾아야 한다.

### Option C: JointPositionActionCfg에서 FR actuator 제외

이 방식만으로는 v1 고장 정의에 부족할 수 있다.

이유:

- action 대상에서 제외해도 actuator 또는 default target이 남아 있으면 torque가 생성될 수 있다.
- 따라서 단독 사용은 피하고, Option A 또는 B와 함께 검증용으로만 고려한다.

## 5. 현재 조사 상태

`project/.venv` 로컬 venv를 만들고 `mjlab==1.2.0` source를 확인했다.

확인한 사실:

- repo의 `setup.py`는 `mjlab==1.2.0`을 외부 의존성으로 선언한다.
- Go2 actuator 설정은 `src/assets/robots/unitree_go2/go2_constants.py`에 있다.
- action은 `JointPositionActionCfg`로 모든 actuator를 대상으로 한다.
- `mjlab.utils.spec.create_position_actuator()`는 `effort_limit`을 MuJoCo actuator `forcerange`에 넣는다.
- `effort_limit=0.0`은 torque clamp로는 의미가 맞지만 MuJoCo compile이 실패한다.
- 현재 구현은 `src/assets/robots/unitree_go2/go2_constants.py`에서 FR 세 actuator의 `stiffness=0.0`, `damping=0.0`, `effort_limit=None`을 사용한다.

확인한 핵심 소스:

```text
project/.venv/lib/python3.11/site-packages/mjlab/utils/spec.py
project/.venv/lib/python3.11/site-packages/mjlab/envs/mdp/actions/actions.py
```

주의:

- `JointPositionActionCfg(use_default_offset=True)`는 default joint position을 action offset으로 사용한다.
- 그러므로 action을 0으로 만드는 것은 torque 0이 아니다.
- failure model 구현은 actuator가 실제 torque를 만들지 못하는지 또는 최종 torque output 기준으로 검증해야 한다.

## 6. RR Extension

RR extension에서는 같은 정의를 `RR`에 적용한다.

```text
RR_hip_joint actuator torque output   = 0
RR_thigh_joint actuator torque output = 0
RR_calf_joint actuator torque output  = 0
```
