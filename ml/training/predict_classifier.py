"""Run a saved crop-router/specialist checkpoint on a single local image."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms

from models import build_classifier


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    payload = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    model = build_classifier(payload["architecture"], len(payload["classes"]), pretrained=False)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    normalization = payload["normalization"]
    transform = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(payload["image_size"]), transforms.ToTensor(),
        transforms.Normalize(mean=normalization["mean"], std=normalization["std"]),
    ])
    with torch.no_grad():
        logits = model(transform(Image.open(args.image).convert("RGB")).unsqueeze(0))[0]
        probabilities = torch.softmax(logits, dim=0)
    top_k = min(max(args.top_k, 1), len(payload["classes"]))
    values, indices = torch.topk(probabilities, top_k)
    print(json.dumps({
        "model": args.checkpoint.name,
        "candidates": [{"crop": payload["classes"][int(index)], "score": round(float(score), 6)} for score, index in zip(values, indices)],
        "warning": "Controlled-image demo model only; require farmer confirmation and do not use as field validation.",
    }))


if __name__ == "__main__":
    main()
