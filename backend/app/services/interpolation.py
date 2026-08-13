"""Interpolation helpers for pod positions between endpoints."""

from math import atan2, cos, radians, sin, sqrt


def haversine_distance_m(lat_1: float, long_1: float, lat_2: float, long_2: float) -> float:
    """Return approximate geodesic distance in meters."""

    earth_radius_m = 6371000.0
    d_lat = radians(lat_2 - lat_1)
    d_long = radians(long_2 - long_1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat_1)) * cos(radians(lat_2)) * sin(d_long / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_m * c


def interpolate_pods(
    lat_a: float,
    long_a: float,
    lat_b: float,
    long_b: float,
    pod_count: int,
    pod_spacing_m: float,
) -> tuple[list[dict], bool]:
    """Interpolate pods from endpoint A to endpoint B using fixed spacing."""

    if pod_count <= 0:
        return [], False

    if pod_count == 1:
        return [{"pod_index": 0, "lat": lat_a, "long": long_a, "compressed": False}], False

    actual_distance_m = haversine_distance_m(lat_a, long_a, lat_b, long_b)
    required_distance_m = max(0.0, (pod_count - 1) * pod_spacing_m)

    if actual_distance_m < 0.01:
        points = []
        for index in range(pod_count):
            points.append(
                {"pod_index": index, "lat": lat_a, "long": long_a, "compressed": True}
            )
        return points, True

    compression_ratio = 1.0
    if required_distance_m > 0.0 and actual_distance_m < required_distance_m:
        compression_ratio = actual_distance_m / required_distance_m

    points = []
    compressed = compression_ratio < 0.999
    for index in range(pod_count):
        if required_distance_m <= 0.0:
            ratio = index / (pod_count - 1)
        else:
            scaled_distance_m = index * pod_spacing_m * compression_ratio
            ratio = min(1.0, scaled_distance_m / actual_distance_m)

        latitude = lat_a + (lat_b - lat_a) * ratio
        longitude = long_a + (long_b - long_a) * ratio
        points.append(
            {
                "pod_index": index,
                "lat": latitude,
                "long": longitude,
                "compressed": compressed,
            }
        )

    return points, compressed

