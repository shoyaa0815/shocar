"""Experimental obstacles from relative inverse depth, never from floor colour."""
from dataclasses import dataclass, field

import cv2
import numpy as np

from server.ai_brain.range import CameraGeometry

WATCH_ZONE = (0.0, 0.50, 1.0, 0.95)


@dataclass
class Detection:
    depth: np.ndarray
    mask: np.ndarray
    boxes: list[list[int]]
    blocked: bool | None
    reason: str
    floor_support: float = 0.0
    objects: list[dict] = field(default_factory=list)
    farthest_floor: dict | None = None

    @property
    def obstacle_scores(self):
        """Image occupancy, not clearance or distance in metres."""
        h, w = self.mask.shape
        return {side: float(np.mean(self.mask[y1:y2, x1:x2] > 0))
                for side, (x1, y1, x2, y2) in side_bounds(w, h).items()}

    @property
    def sides(self):
        h, w = self.mask.shape
        can_confirm_clear = self.blocked is False or self.floor_support > 0
        return {side: True if np.any(self.mask[y1:y2, x1:x2]) else
                False if can_confirm_clear else None
                for side, (x1, y1, x2, y2) in side_bounds(w, h).items()}


def zone_bounds(width: int, height: int):
    return tuple(round(value * (width if i % 2 == 0 else height))
                 for i, value in enumerate(WATCH_ZONE))


def side_bounds(width: int, height: int):
    x1, y1, x2, y2 = zone_bounds(width, height)
    middle = (x1 + x2) // 2
    return {'left': (x1, y1, middle, y2), 'right': (middle, y1, x2, y2)}


def floor_plane(depth: np.ndarray):
    """Fit an increasing inverse-depth plane with spatially spread floor support.

    This is a fixed-camera/pitched-down floor heuristic, not semantic floor
    segmentation. If evidence is weak, callers must report unknown, not clear.
    """
    h, w = depth.shape
    ys, xs = np.mgrid[round(h * .45):round(h * .98):4, round(w * .05):round(w * .95):4]
    if xs.size < 30:
        return None, 0.0
    x, y = xs.ravel() / w, ys.ravel() / h
    design = np.column_stack((x, y, np.ones_like(x)))
    z = depth[ys, xs].ravel()
    rng = np.random.default_rng(7)
    best, best_count = None, 0
    for _ in range(96):
        indices = rng.choice(len(z), 3, replace=False)
        sample = design[indices]
        if abs(np.linalg.det(sample)) < .003:
            continue
        coefficients = np.linalg.solve(sample, z[indices])
        if not (.12 < coefficients[1] < 3.5 and abs(coefficients[0]) < 1):
            continue
        inliers = np.abs(design @ coefficients - z) < .045
        count = int(inliers.sum())
        if count > best_count:
            best, best_count = inliers, count
    if best is None or best_count / len(z) < .35:
        return None, 0.0
    coefficients = np.linalg.lstsq(design[best], z[best], rcond=None)[0]
    if not (.12 < coefficients[1] < 3.5 and abs(coefficients[0]) < 1):
        return None, 0.0
    if np.ptp(y[best]) < .32 or np.ptp(x[best]) < .65:
        return None, 0.0
    bottom = y > .85
    if not bottom.any() or float(np.mean(best[bottom])) < .25:
        return None, 0.0
    grid_y, grid_x = np.mgrid[:h, :w]
    plane = coefficients[0] * grid_x / w + coefficients[1] * grid_y / h + coefficients[2]
    return plane.astype(np.float32), best_count / len(z)


def near_foreground(depth: np.ndarray):
    """Find a near component with a local depth jump, without requiring floor.

    A smooth near/far gradient (e.g. visible floor or wall) is not sufficient.
    Compare its immediate inner boundary with a surrounding farther ring.
    This can flag foreground but cannot establish that an unseen area is clear.
    """
    near = (depth > .65).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(near)
    mask = np.zeros(depth.shape, np.uint8)
    boxes = []
    for index in range(1, count):
        x, y, w, h, area = stats[index]
        if area < max(20, depth.size * .0007) or h < 5 or w < 3:
            continue
        component = (labels == index).astype(np.uint8)
        inner = (component > 0) & (cv2.erode(component, np.ones((5, 5), np.uint8)) == 0)
        outer = (cv2.dilate(component, np.ones((15, 15), np.uint8)) > 0) & (near == 0)
        farther = outer & (depth < .60)
        if np.count_nonzero(inner) < 8 or np.count_nonzero(farther) < 20:
            continue
        if np.median(depth[inner]) - np.median(depth[farther]) < .16:
            continue
        if np.count_nonzero(farther) / max(1, np.count_nonzero(outer)) < .3:
            continue
        mask[component > 0] = 255
        boxes.append([int(x), int(y), int(w), int(h)])
    return mask, boxes


def farthest_floor(depth, plane, obstacle_mask, geometry):
    """Farthest supported floor patch connected to visible foreground floor.

    This is a floor heuristic, not a claim that the line to it is traversable.
    Erosion rejects isolated pixels and keeps endpoints away from object edges.
    """
    h, w = depth.shape
    floor = ((np.abs(depth - plane) < .045) & (obstacle_mask == 0)).astype(np.uint8)
    floor[:round(h * .15)] = 0
    floor[round(h * .98):] = 0
    floor[:, :round(w * .05)] = 0
    floor[:, round(w * .95):] = 0
    floor = cv2.erode(floor, np.ones((5, 5), np.uint8))
    _, labels, stats, _ = cv2.connectedComponentsWithStats(floor)
    connected = np.unique(labels[round(h * .85):])
    connected = [index for index in connected if index and stats[index, cv2.CC_STAT_AREA] >= max(25, depth.size * .005)]
    if not connected:
        return None
    supported = np.isin(labels, connected)
    for y in np.flatnonzero(supported.any(axis=1)):
        distance = geometry.distance_cm(int(y), w, h)
        if distance is None:
            continue
        xs = np.flatnonzero(supported[y])
        x = int(xs[np.argmin(np.abs(xs - w / 2))])
        return {'point': [x, int(y)], 'distance_cm': distance}
    return None


class Detector:
    def __init__(self, geometry=None):
        self.geometry = geometry if geometry is not None else CameraGeometry()

    def analyze(self, raw_depth: np.ndarray) -> Detection:
        if raw_depth.ndim != 2 or min(raw_depth.shape) < 32 or not np.isfinite(raw_depth).all():
            raise ValueError('Invalid depth image')
        lo, hi = np.percentile(raw_depth, (2, 98))
        if hi - lo < 1e-5:
            return Detection(np.zeros_like(raw_depth, dtype=np.float32),
                             np.zeros(raw_depth.shape, np.uint8), [], None,
                             'ความลึกไม่ชัดเจน · ยังประเมินสิ่งกีดขวางไม่ได้')
        depth = np.clip((raw_depth - lo) / (hi - lo), 0, 1).astype(np.float32)
        plane, support = floor_plane(depth)
        if plane is None:
            mask, boxes = near_foreground(depth)
            h, w = depth.shape
            x1, y1, x2, y2 = zone_bounds(w, h)
            blocked = True if np.any(mask[y1:y2, x1:x2]) else None
            reason = ('พบขอบวัตถุใกล้ในกรอบ · ผลทดลองจากความลึก' if blocked else
                      'พื้นไม่ชัดและยังไม่พบขอบวัตถุใกล้ในกรอบ · ยังประเมินไม่ได้')
            return Detection(depth, mask, boxes, blocked, reason,
                             objects=self.geometry.objects(boxes, depth.shape, estimate=False))
        mask = ((depth - plane > .085) & (depth > .52)).astype(np.uint8) * 255
        h, w = depth.shape
        mask[:round(h * .15)] = 0
        mask[round(h * .98):] = 0
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        filtered = np.zeros_like(mask)
        boxes = []
        for index in range(1, count):
            x, y, bw, bh, area = stats[index]
            if area >= max(20, mask.size * .0007) and bh >= 5:
                filtered[labels == index] = 255
                boxes.append([int(x), int(y), int(bw), int(bh)])
        x1, y1, x2, y2 = zone_bounds(w, h)
        blocked = bool(np.any(filtered[y1:y2, x1:x2]))
        reason = ('พบสิ่งกีดขวางใกล้ในกรอบ' if blocked else 'ยังไม่พบสิ่งกีดขวางใกล้ในกรอบ · ผลทดลอง')
        return Detection(depth, filtered, boxes, blocked, reason, support,
                         self.geometry.objects(boxes, depth.shape),
                         farthest_floor(depth, plane, filtered, self.geometry))


def render(image: np.ndarray, result: Detection):
    original = image.copy()
    heatmap = cv2.applyColorMap((result.depth * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
    h, w = image.shape[:2]
    sides = result.sides
    for view in (original, heatmap):
        for x, y, bw, bh in result.boxes:
            cv2.rectangle(view, (x, y), (x + bw, y + bh), (40, 180, 255), 2)
        for side, (x1, y1, x2, y2) in side_bounds(w, h).items():
            blocked = sides[side]
            color = (40, 60, 245) if blocked else (90, 215, 105)
            if blocked is None:
                color = (30, 185, 245)
            edge = x2 - 1
            cv2.rectangle(view, (x1, y1), (edge, y2), color, 2)
            cv2.rectangle(view, (x1, y1 - 24), (min(edge, x1 + 70), y1 - 2), (15, 15, 15), -1)
            cv2.putText(view, side.upper(), (x1 + 5, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1)
    return original, heatmap
