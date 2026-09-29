"""Small, reproducible CNN classifiers used by the crop router and specialists.

Weights are ImageNet-initialized only when requested. They do not contain crop
or disease knowledge until fine-tuned on an approved dataset.
"""

from __future__ import annotations

from torch import nn
from torchvision.models import (
    EfficientNet_B0_Weights,
    MobileNet_V3_Large_Weights,
    MobileNet_V3_Small_Weights,
    efficientnet_b0,
    mobilenet_v3_large,
    mobilenet_v3_small,
)


SUPPORTED_ARCHITECTURES = ("mobilenet_v3_small", "mobilenet_v3_large", "efficientnet_b0")


def build_classifier(architecture: str, class_count: int, *, pretrained: bool = True) -> nn.Module:
    """Return a transfer-learning classifier with a new, task-specific head."""
    if class_count < 2:
        raise ValueError("class_count must be at least 2 (including healthy/unknown where applicable)")
    if architecture == "mobilenet_v3_small":
        model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT if pretrained else None)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, class_count)
    elif architecture == "mobilenet_v3_large":
        model = mobilenet_v3_large(weights=MobileNet_V3_Large_Weights.DEFAULT if pretrained else None)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, class_count)
    elif architecture == "efficientnet_b0":
        model = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT if pretrained else None)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, class_count)
    else:
        raise ValueError(f"Unsupported architecture '{architecture}'. Choose one of: {', '.join(SUPPORTED_ARCHITECTURES)}")
    return model
