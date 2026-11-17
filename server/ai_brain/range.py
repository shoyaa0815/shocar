import math
import os
from dataclasses import dataclass

DEFAULT_HEIGHT_CM = 20.0
DEFAULT_TILT_DEG = 15.0
DEFAULT_HFOV_DEG = 65.0
HEIGHT_RANGE = (5.0, 200.0)
TILT_RANGE = (-45.0, 89.0)
HFOV_RANGE = (20.0, 170.0)
MIN_CM = 10
MAX_CM = 300
STEP_CM = 5


def _setting(name, default, low, high):
    raw = os.environ.get(name, '').strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f'{name} must be a number') from None
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must be between {low:g} and {high:g}')
    return value


@dataclass(frozen=True)
class CameraGeometry:

    height_cm: float = DEFAULT_HEIGHT_CM
    tilt_deg: float = DEFAULT_TILT_DEG
    hfov_deg: float = DEFAULT_HFOV_DEG

    @classmethod
    def from_env(cls):
        return cls(_setting('CAMERA_HEIGHT_CM', DEFAULT_HEIGHT_CM, *HEIGHT_RANGE),
                   _setting('CAMERA_TILT_DEG', DEFAULT_TILT_DEG, *TILT_RANGE),
                   _setting('CAMERA_HFOV_DEG', DEFAULT_HFOV_DEG, *HFOV_RANGE))

    def focal_px(self, width: int) -> float:
        return (width / 2) / math.tan(math.radians(self.hfov_deg) / 2)

    def distance_cm(self, base_v: float, width: int, height: int):
        focal = self.focal_px(width)
        middle = height / 2
        tilt = math.radians(self.tilt_deg)
        if base_v <= middle - focal * math.tan(tilt) or base_v >= height:
            return None
        depression = tilt + math.atan((base_v - middle) / focal)
        distance = self.height_cm / math.tan(depression)
        if not math.isfinite(distance) or not MIN_CM <= distance <= MAX_CM:
            return None
        return int(round(distance / STEP_CM) * STEP_CM)

    def objects(self, boxes, shape, *, estimate=True):
        height, width = shape
        found = []
        for x, y, box_w, box_h in boxes:
            base_u = min(width - 1, max(0, int(x) + int(box_w) // 2))
            base_v = min(height - 1, max(0, int(y) + int(box_h)))
            found.append({'box': [int(x), int(y), int(box_w), int(box_h)],
                          'base': [base_u, base_v],
                          'distance_cm': self.distance_cm(base_v, width, height) if estimate else None})
        found.sort(key=lambda item: (item['distance_cm'] is None, item['distance_cm'] or 0))
        return found
