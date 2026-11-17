# Depth Anything V2 inference code

Unmodified inference files from:
https://github.com/DepthAnything/Depth-Anything-V2

Pinned upstream commit: `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf`.
Downloaded only `depth_anything_v2/**/*.py` and the upstream Apache 2.0
license (`DEPTH_ANYTHING_LICENSE`). Per-file DINOv2 notices are preserved.
Only the Small checkpoint is used (Apache 2.0).

Model: https://huggingface.co/depth-anything/Depth-Anything-V2-Small
Revision: `03876f8651c73a60fe4c2c48294e09fcb6838fcf`
SHA256: `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378`

The model is downloaded explicitly using `scripts/download_depth_model.py`.
Server startup and inference do not download code or weights.
