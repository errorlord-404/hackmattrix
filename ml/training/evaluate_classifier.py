"""Evaluate a saved classifier on an ImageFolder split with per-class metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from models import build_classifier


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True, help="ImageFolder directory, normally val")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    payload = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    model = build_classifier(payload["architecture"], len(payload["classes"]), pretrained=False)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    normalize = payload["normalization"]
    transform = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(payload["image_size"]), transforms.ToTensor(),
        transforms.Normalize(mean=normalize["mean"], std=normalize["std"]),
    ])
    dataset = datasets.ImageFolder(args.dataset, transform=transform)
    if dataset.classes != payload["classes"]:
        raise SystemExit(f"Dataset classes {dataset.classes} do not match checkpoint classes {payload['classes']}")
    confusion = [[0 for _ in dataset.classes] for _ in dataset.classes]
    with torch.no_grad():
        for images, targets in DataLoader(dataset, batch_size=args.batch_size, shuffle=False, num_workers=0):
            predictions = model(images).argmax(dim=1)
            for target, predicted in zip(targets.tolist(), predictions.tolist()):
                confusion[target][predicted] += 1
    total = sum(sum(row) for row in confusion)
    per_class = {}
    f1_scores = []
    for index, label in enumerate(dataset.classes):
        true_positive = confusion[index][index]
        false_negative = sum(confusion[index]) - true_positive
        false_positive = sum(row[index] for row in confusion) - true_positive
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1_scores.append(f1)
        per_class[label] = {"precision": round(precision, 6), "recall": round(recall, 6), "f1": round(f1, 6), "support": sum(confusion[index])}
    print(json.dumps({
        "checkpoint": args.checkpoint.name,
        "samples": total,
        "accuracy": round(sum(confusion[index][index] for index in range(len(confusion))) / total if total else 0.0, 6),
        "macro_f1": round(sum(f1_scores) / len(f1_scores) if f1_scores else 0.0, 6),
        "classes": per_class,
        "confusion_matrix": confusion,
    }, indent=2))


if __name__ == "__main__":
    main()
