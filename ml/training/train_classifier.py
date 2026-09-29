"""Train either the crop-router CNN or one crop-specific disease CNN.

The command intentionally uses ImageFolder. This makes labels reviewable in Git
via a dataset manifest while keeping farmer images outside source control.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch
from torch import nn
from torch.optim import AdamW
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from models import SUPPORTED_ARCHITECTURES, build_classifier


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--dataset", type=Path, required=True, help="Directory with train/<label>/ and val/<label>/ images")
    result.add_argument("--output", type=Path, required=True, help="Output .pt checkpoint")
    result.add_argument("--architecture", choices=SUPPORTED_ARCHITECTURES, default="mobilenet_v3_small")
    result.add_argument("--epochs", type=int, default=12)
    result.add_argument("--batch-size", type=int, default=24)
    result.add_argument("--learning-rate", type=float, default=3e-4)
    result.add_argument("--seed", type=int, default=42)
    result.add_argument("--no-pretrained", action="store_true", help="Do not initialize from ImageNet weights")
    return result


def main() -> None:
    args = parser().parse_args()
    if args.epochs < 1 or args.batch_size < 1:
        raise SystemExit("epochs and batch-size must be positive")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    normalize = transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225))
    train_transform = transforms.Compose([
        transforms.Resize(256), transforms.RandomResizedCrop(224, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(), transforms.ColorJitter(brightness=0.18, contrast=0.18, saturation=0.10),
        transforms.ToTensor(), normalize,
    ])
    val_transform = transforms.Compose([transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(), normalize])
    train = datasets.ImageFolder(args.dataset / "train", transform=train_transform)
    validation = datasets.ImageFolder(args.dataset / "val", transform=val_transform)
    if train.classes != validation.classes:
        raise SystemExit("train and val must contain the same label directories")
    if len(train.classes) < 2:
        raise SystemExit("at least two reviewed label directories are required")
    train_loader = DataLoader(train, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(validation, batch_size=args.batch_size, shuffle=False, num_workers=0)
    model = build_classifier(args.architecture, len(train.classes), pretrained=not args.no_pretrained).to(device)
    optimizer = AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    loss_function = nn.CrossEntropyLoss()
    best_accuracy = -1.0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        for images, targets in train_loader:
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(model(images.to(device)), targets.to(device))
            loss.backward()
            optimizer.step()
        model.eval()
        correct = total = 0
        with torch.no_grad():
            for images, targets in val_loader:
                predicted = model(images.to(device)).argmax(dim=1).cpu()
                correct += int((predicted == targets).sum())
                total += len(targets)
        accuracy = correct / total if total else 0.0
        print(json.dumps({"epoch": epoch, "validation_accuracy": accuracy, "device": str(device)}))
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            torch.save({
                "architecture": args.architecture, "classes": train.classes, "image_size": 224,
                "normalization": {"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
                "validation_accuracy": accuracy, "state_dict": model.state_dict(),
            }, args.output)
    print(json.dumps({"checkpoint": str(args.output), "best_validation_accuracy": best_accuracy, "classes": train.classes}))


if __name__ == "__main__":
    main()
