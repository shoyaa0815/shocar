from pathlib import Path

import numpy as np

CHECKPOINT = Path(__file__).resolve().parents[2] / 'models/depth_anything_v2_vits.pth'


class DepthModel:
    def __init__(self):
        self.model = None
        self.device = None
        self.input_size = 392

    def load(self):
        if self.model is not None:
            return
        if not CHECKPOINT.is_file():
            raise FileNotFoundError('Depth checkpoint is missing')
        import torch
        from server.ai_brain.vendor.depth_anything_v2.dpt import DepthAnythingV2

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if self.device == 'cpu':
            torch.set_num_threads(min(4, torch.get_num_threads()))
        self.input_size = 518 if self.device == 'cuda' else 392
        model = DepthAnythingV2(encoder='vits', features=64, out_channels=[48, 96, 192, 384])
        model.load_state_dict(torch.load(CHECKPOINT, map_location='cpu', weights_only=True))
        self.model = model.to(self.device).eval()

    def predict(self, image: np.ndarray) -> np.ndarray:
        self.load()
        return self.model.infer_image(image, input_size=self.input_size)
