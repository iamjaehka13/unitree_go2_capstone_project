"""Shared geometry checks for FR-failure tripod evaluation."""

from __future__ import annotations

import torch


def cross2(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
  """2D cross product for batched xy vectors."""
  return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def support_triangle_metrics(
  foot_pos_w: torch.Tensor,
  com_xy_w: torch.Tensor,
  support_indices: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
  """Return support triangle area, minimum foot distance, and signed COM margin.

  ``foot_pos_w`` is expected to match the caller's foot name order. ``support_indices``
  selects the enabled support feet for the failure condition.
  """
  support_xy = foot_pos_w[:, support_indices, :2]
  a = support_xy[:, 0, :]
  b = support_xy[:, 1, :]
  c = support_xy[:, 2, :]

  ab = b - a
  bc = c - b
  ca = a - c
  signed_area2 = cross2(ab, c - a)
  area = 0.5 * torch.abs(signed_area2)

  ab_len = torch.linalg.norm(ab, dim=1)
  bc_len = torch.linalg.norm(bc, dim=1)
  ca_len = torch.linalg.norm(ca, dim=1)
  min_foot_distance = torch.minimum(torch.minimum(ab_len, bc_len), ca_len)

  orientation = torch.where(signed_area2 >= 0.0, 1.0, -1.0)
  eps = 1.0e-6
  dist_ab = orientation * cross2(ab, com_xy_w - a) / torch.clamp(ab_len, min=eps)
  dist_bc = orientation * cross2(bc, com_xy_w - b) / torch.clamp(bc_len, min=eps)
  dist_ca = orientation * cross2(ca, com_xy_w - c) / torch.clamp(ca_len, min=eps)
  com_margin = torch.minimum(torch.minimum(dist_ab, dist_bc), dist_ca)

  return area, min_foot_distance, com_margin


def support_geometry_ok(
  area: torch.Tensor,
  min_foot_distance: torch.Tensor,
  com_margin: torch.Tensor,
  min_area: float,
  min_distance: float,
  min_com_margin: float,
) -> torch.Tensor:
  """Return true when the stance is a usable tripod support polygon."""
  return (
    (area >= min_area)
    & (min_foot_distance >= min_distance)
    & (com_margin >= min_com_margin)
  )
