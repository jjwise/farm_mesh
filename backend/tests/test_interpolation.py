"""Tests for pod interpolation service."""

from app.services.interpolation import interpolate_pods


def test_interpolate_pods_with_valid_segment() -> None:
    points, compressed = interpolate_pods(
        lat_a=-33.0,
        long_a=151.0,
        lat_b=-33.0005,
        long_b=151.0005,
        pod_count=4,
        pod_spacing_m=20.0,
    )

    assert len(points) == 4
    assert compressed is False
    assert points[0]["pod_index"] == 0
    assert points[-1]["pod_index"] == 3


def test_interpolate_pods_handles_zero_distance() -> None:
    points, compressed = interpolate_pods(
        lat_a=-33.0,
        long_a=151.0,
        lat_b=-33.0,
        long_b=151.0,
        pod_count=3,
        pod_spacing_m=20.0,
    )

    assert len(points) == 3
    assert compressed is True
    assert all(point["lat"] == -33.0 for point in points)

