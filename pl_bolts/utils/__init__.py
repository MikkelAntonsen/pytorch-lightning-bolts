import torch
from pytorch_lightning.utilities import _module_available

_NATIVE_AMP_AVAILABLE: bool = _module_available("torch.cuda.amp") and hasattr(torch.cuda.amp, "autocast")

_TORCHVISION_AVAILABLE: bool = _module_available("torchvision")
_GYM_AVAILABLE: bool = _module_available("gym")
_SKLEARN_AVAILABLE: bool = _module_available("sklearn")
_PIL_AVAILABLE: bool = _module_available("PIL")
_OPENCV_AVAILABLE: bool = _module_available("cv2")
