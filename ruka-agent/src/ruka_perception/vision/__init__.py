"""Vision processing module for Ruka Perception.

Exposes image tensor operations and convolution primitives.
"""

from .image_tensor import (
    add_batch,
    estimate_image_tokens,
    laplacian_variance,
    normalize_01,
    normalize_imagenet,
    to_chw,
    to_grayscale,
    to_hwc,
)
from .convolution import (
    BOX_BLUR,
    SHARPEN,
    SOBEL_X,
    SOBEL_Y,
    avgpool2d,
    conv2d,
    maxpool2d,
    receptive_field,
)

__all__ = [
    "to_chw",
    "to_hwc",
    "add_batch",
    "normalize_01",
    "normalize_imagenet",
    "to_grayscale",
    "estimate_image_tokens",
    "laplacian_variance",
    "conv2d",
    "maxpool2d",
    "avgpool2d",
    "receptive_field",
    "SOBEL_X",
    "SOBEL_Y",
    "BOX_BLUR",
    "SHARPEN",
]
