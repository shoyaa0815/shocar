from pathlib import Path
import os

import numpy as np

CHECKPOINT = Path(__file__).resolve().parents[2] / 'models/yoloe-v8s-seg-pf.pt'

EXCLUDED_NAMES = frozenset({
    'person', 'people', 'human', 'man', 'woman', 'boy', 'girl', 'child', 'baby',
    'floor', 'flooring', 'wall', 'ceiling', 'roof', 'ground', 'sky',
    'door', 'doorway', 'window', 'window frame', 'building', 'house',
    'wallpaper', 'indoor', 'outdoor', 'child actor', 'tv personality',
    'adult', 'pedestrian', 'bride', 'groom',
    'darkness', 'shadow', 'reflection', 'background', 'skyline',
    'scenery', 'landscape', 'interior', 'exterior', 'bedroom', 'bathroom',
    'kitchen', 'hallway',
})


def is_thing(name):
    name = name.strip().lower().replace('_', ' ')
    return name not in EXCLUDED_NAMES and not name.endswith((
        ' floor', ' flooring', ' wall', ' ceiling', ' door', ' window',
        ' woman', ' man', ' boy', ' girl',
        ' scene', ' shot', ' room',
    ))


class ObjectModel:
    def __init__(self, checkpoint=CHECKPOINT):
        self.checkpoint = Path(checkpoint)
        self.model = None
        self.device = None

    def load(self):
        if self.model is not None:
            return
        if not self.checkpoint.is_file():
            raise FileNotFoundError('Object checkpoint is missing')
        os.environ.setdefault('YOLO_AUTOINSTALL', 'false')
        os.environ.setdefault('YOLO_OFFLINE', 'true')
        import torch
        from ultralytics import YOLOE

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if self.device == 'cpu':
            torch.set_num_threads(min(4, torch.get_num_threads()))
        self.model = YOLOE(str(self.checkpoint))

    def predict(self, image):
        self.load()
        result = self.model.predict(
            source=image, imgsz=640, conf=.20, iou=.5, agnostic_nms=True,
            max_det=300, device=self.device, verbose=False, save=False,
        )[0]
        height, width = image.shape[:2]
        boxes = []
        if result.boxes is None:
            return boxes
        for xyxy, class_id in zip(result.boxes.xyxy.cpu().numpy(), result.boxes.cls.cpu().numpy()):
            if not is_thing(result.names[int(class_id)]) or not np.isfinite(xyxy).all():
                continue
            x1, y1, x2, y2 = np.rint(xyxy).astype(int)
            x1, x2 = np.clip([x1, x2], 0, width)
            y1, y2 = np.clip([y1, y2], 0, height)
            if x2 > x1 and y2 > y1:
                boxes.append([int(x1), int(y1), int(x2 - x1), int(y2 - y1)])
        return boxes
