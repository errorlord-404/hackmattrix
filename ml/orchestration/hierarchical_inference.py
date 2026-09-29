"""Local two-stage crop-health inference, independent of the web/backend layer.

The first checkpoint routes a crop image. A farmer can confirm/correct that
crop before a crop-specific checkpoint is run. Missing or unapproved
specialists fail closed instead of returning a generic disease label.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from PIL import Image
from torchvision import transforms

from orchestration.crop_router import CropCandidate, select_specialist
from training.models import build_classifier


def _checkpoint_candidates(checkpoint: Path, image_path: Path, top_k: int = 3) -> list[dict[str, float | str]]:
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    model = build_classifier(payload["architecture"], len(payload["classes"]), pretrained=False)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    normalization = payload["normalization"]
    transform = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(payload["image_size"]), transforms.ToTensor(),
        transforms.Normalize(mean=normalization["mean"], std=normalization["std"]),
    ])
    with torch.no_grad():
        probabilities = torch.softmax(model(transform(Image.open(image_path).convert("RGB")).unsqueeze(0))[0], dim=0)
    values, indices = torch.topk(probabilities, min(top_k, len(payload["classes"])))
    return [{"label": payload["classes"][int(index)], "score": float(score)} for score, index in zip(values, indices)]


def run_hierarchical_inference(
    image_path: Path,
    router_checkpoint: Path,
    specialist_checkpoints: dict[str, Path],
    *,
    confirmed_crop: str | None = None,
) -> dict[str, Any]:
    """Return a transparent router decision plus specialist result if available."""
    crop_candidates = _checkpoint_candidates(router_checkpoint, image_path)
    route = select_specialist(
        [CropCandidate(str(item["label"]), float(item["score"])) for item in crop_candidates],
        {crop: crop for crop, path in specialist_checkpoints.items() if path.exists()},
        confirmed_crop=confirmed_crop,
    )
    result: dict[str, Any] = {
        "router_candidates": crop_candidates,
        "route_status": route.status,
        "crop": route.crop,
        "requires_farmer_confirmation": route.requires_farmer_confirmation,
        "reason": route.reason,
    }
    specialist_path = specialist_checkpoints.get(route.crop or "")
    if route.status != "routed" or not specialist_path or not specialist_path.exists():
        result["status"] = "needs_expert_review" if route.status == "needs_crop_confirmation" else route.status
        result["disease_candidates"] = []
        return result
    result["status"] = "completed"
    result["specialist_model"] = specialist_path.name
    result["disease_candidates"] = _checkpoint_candidates(specialist_path, image_path)
    return result
