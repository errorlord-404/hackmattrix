"""Approved TensorFlow Hub image backbones for the on-device benchmark."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TfHubBackbone:
    name: str
    handle: str
    image_size: int
    edge_intent: str
    fine_tune_supported: bool


BACKBONES = {
    "mobilenet_v3_small": TfHubBackbone(
        "mobilenet_v3_small",
        "https://tfhub.dev/google/imagenet/mobilenet_v3_small_100_224/feature_vector/5",
        224,
        "fast crop-router candidate",
        True,
    ),
    "mobilenet_v3_large": TfHubBackbone(
        "mobilenet_v3_large",
        "https://tfhub.dev/google/imagenet/mobilenet_v3_large_100_224/feature_vector/5",
        224,
        "accuracy-oriented, fine-tunable TFLite specialist benchmark candidate",
        True,
    ),
    "efficientnet_v2_b0": TfHubBackbone(
        "efficientnet_v2_b0",
        "https://tfhub.dev/google/imagenet/efficientnet_v2_imagenet1k_b0/feature_vector/2",
        224,
        "accuracy-versus-latency specialist benchmark candidate",
        True,
    ),
    "efficientnet_lite0": TfHubBackbone(
        "efficientnet_lite0",
        "https://tfhub.dev/tensorflow/efficientnet/lite0/feature-vector/2",
        224,
        "higher-capacity TFLite specialist candidate",
        False,
    ),
}


def get_backbone(name: str) -> TfHubBackbone:
    try:
        return BACKBONES[name]
    except KeyError as exc:
        raise ValueError(f"Unsupported backbone '{name}'. Choose one of: {', '.join(BACKBONES)}") from exc
