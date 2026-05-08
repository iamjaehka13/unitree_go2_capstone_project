# Push Visualization Plan

이 문서는 외란 평가 결과를 발표용 영상과 그림으로 만들기 위한 기준이다.

## 1. 목적

외란 평가는 수치만으로는 직관성이 약하다. PPT 발표에서는 같은 조건에서 `E1 default-init policy`, `E2 tripod-init policy`, `E3 init-curriculum policy`가 어떻게 다르게 반응하는지 영상으로 보여준다.

핵심 메시지:

> 같은 FR 다리 고장, 같은 시작 상태, 같은 외란을 받았을 때 tripod prior와 init-pose curriculum이 default-init PPO 실패를 어떻게 보완하는지 시각적으로 보여준다.

## 2. 반드시 구분할 표현

외란 구현 방식에 따라 발표 표현을 다르게 한다.

| 구현 방식 | 발표 표현 |
| --- | --- |
| `base_link` 또는 base COM에 실제 external force 적용 | force push, impulse push |
| base velocity를 순간적으로 바꿈 | velocity perturbation |

PPT에서는 구현과 다른 표현을 쓰지 않는다. v1의 목표는 실제 external force 기반 impulse push다.

## 3. 발표용 영상 구성

### 3.1 Main Side-by-Side Video

동일한 push 조건에서 세 policy를 비교한다.

```text
left   = E1 default-init policy
center = E2 tripod-init policy
right  = E3 init-curriculum policy
```

영상 조건:

- 같은 camera pose
- 같은 reset pose
- 같은 push timing
- 같은 push direction
- 같은 push magnitude
- 같은 playback speed
- 같은 episode horizon

오버레이:

- push 방향 화살표
- push magnitude
- push type
- push start time
- current time
- success/fail
- recovery time

### 3.2 Push Magnitude Demo

발표용 최소 영상 세트:

| 영상 | 조건 |
| --- | --- |
| weak push | 한 방향 weak impulse |
| medium push | 한 방향 medium impulse |
| strong push | 한 방향 strong impulse |

방향은 FR 고장 조건에서 차이가 가장 잘 보이는 방향을 최종 결과를 보고 선택한다. pilot 단계에서는 `left`, `right`, `front`, `back` 모두 짧게 렌더링한다.

### 3.3 Robustness Grid Video

시간이 있으면 다음 grid 영상을 만든다.

```text
rows    = push direction: front, back, left, right
columns = policy: E1 default-init, E2 tripod-init, E3 init-curriculum
```

각 row는 medium push 기준으로 만든다.

## 4. 화살표 시각화 규칙

외란 화살표는 base 근처에 표시한다.

| Push Level | Arrow Color | 의미 |
| --- | --- | --- |
| weak | green | 작은 외란 |
| medium | yellow | 중간 외란 |
| strong | red | 큰 외란 |

화살표 길이는 force 또는 impulse 크기에 비례시킨다.

```text
arrow_length = k * force_magnitude
```

또는 impulse 기준:

```text
arrow_length = k * force_magnitude * duration
```

실제 overlay에는 다음 텍스트를 짧게 넣는다.

```text
Push: right, medium, 0.35 BW, 0.1 s
```

## 4.1 공 기반 외란 시각화

PPT 발표에서는 force 방향과 크기를 더 직관적으로 보여주기 위해 공이 로봇을 때리는 것처럼 시각화한다.

중요한 원칙:

> 공은 실제 충돌로 force를 만드는 물체가 아니라, external force impulse를 설명하기 위한 ghost visual object다.

즉 실제 물리는 `base_link` 또는 base COM에 정량적인 external force를 넣고, 화면에는 같은 타이밍에 공이 날아와 맞는 것처럼 보여준다.

발표 표현:

> 영상의 공은 외란 방향과 크기를 직관적으로 보여주기 위한 시각화 요소이며, 실제 외란은 base에 정량적으로 인가한 external force입니다.

공 metaphor:

| Push Level | Visual Object | Visual Meaning | Physics Meaning |
| --- | --- | --- | --- |
| weak | tennis ball | 작은 충격 | `0.25 BW`, `0.1 s` |
| medium | soccer ball | 중간 충격 | `0.35 BW`, `0.1 s` |
| strong | bowling ball | 큰 충격 | `0.45 BW`, `0.1 s` |

`0.5 / 1.0 / 1.5 BW` 기준은 stress-test로 남긴다. 현재 seed 0 no-push standing policy에서는 이 기준이 너무 강해서 E1/E2/E3 모두 실패했으므로, PPT용 main visualization은 policy 간 차이가 드러나는 calibrated 기준을 사용한다.

시각화 규칙:

- 공은 push 방향 반대편에서 날아와 base 근처에서 impact한다.
- impact 순간부터 정해진 duration 동안 external force를 적용한다.
- 공의 크기와 색을 push level에 맞춰 다르게 한다.
- 공은 collision을 만들지 않거나, collision이 물리 결과에 영향을 주지 않도록 처리한다.
- impact 순간에 화살표와 force label을 함께 표시한다.

예시 overlay:

```text
Tennis Ball Push: 37 N, 0.1 s
Soccer Ball Push: 52 N, 0.1 s
Bowling Ball Push: 67 N, 0.1 s
```

위 숫자는 seed 0 calibrated push evaluation에서 계산된 Go2 모델 기준 force 값이다.

## 5. 저장할 로그

영상과 그래프를 나중에 다시 만들 수 있도록 평가 중 아래 값을 저장한다.

| field | 설명 |
| --- | --- |
| `policy_id` | `e1_default_init`, `e2_tripod_init`, `e3_init_curriculum` |
| `eval_init` | `default`, `tripod`, 또는 `curriculum` |
| `failed_leg` | v1은 `FR` |
| `seed` | 학습 seed |
| `episode_id` | 평가 episode id |
| `time_s` | simulation time |
| `push_active` | push가 적용 중인지 |
| `push_direction` | front/back/left/right |
| `push_force_n` | external force magnitude |
| `push_duration_s` | force duration |
| `base_pos` | base xyz |
| `base_quat` | base quaternion |
| `base_roll_pitch_yaw` | 자세 각도 |
| `base_lin_vel` | base linear velocity |
| `base_ang_vel` | base angular velocity |
| `joint_pos` | 12개 joint position |
| `joint_torque` | 12개 joint torque 또는 actuator force |
| `foot_contact` | FL/FR/RL/RR contact state |
| `foot_contact_force` | foot contact force |
| `success` | episode 성공 여부 |
| `fall_time_s` | 넘어졌다면 fall time |
| `recovery_time_s` | 회복 시간 |

## 6. 그래프 산출물

영상과 함께 PPT에 넣을 그림:

- push direction x magnitude success rate heatmap
- roll/pitch recovery curve
- base height curve
- torque RMS comparison
- contact force distribution
- COM trajectory over support triangle

메인 발표 슬라이드에서는 너무 많은 그래프를 넣지 않는다. 권장 조합:

1. side-by-side video
2. success rate heatmap
3. recovery curve 하나
4. final pose/contact force 비교 그림

## 7. 구현 파이프라인

권장 스크립트 구조:

```text
project/scripts/
  eval_push.py              # policy 평가 및 로그 저장
  render_push_video.py      # 동일 조건 영상 렌더링
  make_push_comparison.py   # side-by-side 영상 + 화살표 overlay
  plot_push_results.py      # heatmap/recovery curve 생성
```

출력 위치:

```text
project/results/push/
  *.csv
  *.json
  *.png

project/videos/push/
  raw/
  comparison/
  ppt/
```

## 8. PPT용 최종 산출물

v1 최소 산출물:

- `project/videos/push/E1_default_medium_right_calibrated_fail.mp4`
- `project/videos/push/E2_tripod_medium_back_calibrated_success.mp4`
- `project/videos/push/E2_tripod_medium_front_calibrated_fail.mp4`
- `project/videos/push/E2_tripod_medium_right_calibrated_success.mp4`
- `project/videos/push/E3_default_medium_right_calibrated_survive_not_strict.mp4`
- `project/videos/push/FR_E1_E2_E3_medium_right_calibrated_side_by_side.mp4`
- `project/results/figures/push_eval_v2_calibrated_final_seed0/push_success_policy_summary.png`
- `project/results/figures/push_eval_v2_calibrated_final_seed0/push_success_heatmap_E2_tripod.png`
- `project/results/figures/push_eval_v2_calibrated_final_seed0/push_success_heatmap_E3_default.png`

`FR_E1_E2_E3_medium_right_calibrated_side_by_side.mp4`는 세 policy를 같은 `right medium` push 조건에서 비교하는 PPT 우선 사용 영상이다.

## 9. 구현 전 확인사항

- 실제 external force를 어디서 넣을지 확인한다.
- external force 적용 시 simulator step마다 force가 초기화되는지 확인한다.
- viewer/render path에서 동일 camera를 고정할 수 있는지 확인한다.
- raw video frame에 화살표를 직접 그릴지, post-process로 overlay할지 결정한다.
- PPT에 넣을 영상은 너무 길지 않게 5초에서 8초 정도로 만든다.
