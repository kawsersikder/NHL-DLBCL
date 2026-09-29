"""Kaggle-friendly Phase 1a baseline: binary nucleus segmentation on LyNSeC H&E.

This is an engineering run, not a patient-level or publication-ready evaluation.
LyNSeC's public release does not provide patient identifiers for grouped splitting.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import torch
from torch import Tensor, nn
from torch.nn import functional as functional
from torch.utils.data import DataLoader, Dataset


@dataclass(frozen=True)
class TileRef:
    path: str
    index: int | None
    partition: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    parser.add_argument("--patience", type=int, default=35)
    parser.add_argument("--seed", type=int, default=20260821)
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = False
    torch.backends.cudnn.benchmark = True


def partition_from_path(path: Path) -> str | None:
    text = path.as_posix().lower()
    if "l2" in text:
        return "lynsec2_he"
    if "l3" in text:
        return "lynsec3_he_expert"
    return None


def discover_tiles(data_dir: Path) -> list[TileRef]:
    """Support either individual per-tile arrays or stacked arrays in the archive."""
    tiles: list[TileRef] = []
    for path in sorted(data_dir.rglob("*.npy")):
        partition = partition_from_path(path)
        if partition is None:
            continue  # Ignore IHC LyNSeC 1 for this H&E-only run.
        array = np.load(path, mmap_mode="r")
        if array.ndim == 3 and array.shape[-1] in (4, 5):
            tiles.append(TileRef(str(path), None, partition))
        elif array.ndim == 4 and array.shape[-1] in (4, 5):
            tiles.extend(TileRef(str(path), index, partition) for index in range(array.shape[0]))
        else:
            print(f"Skipping non-image array: {path} with shape {array.shape}")
    if not tiles:
        raise RuntimeError(
            "No LyNSeC H&E arrays were found. Check extraction and confirm relevant paths include l2/l3."
        )
    return tiles


@lru_cache(maxsize=16)
def load_memmap(path: str) -> np.ndarray:
    return np.load(path, mmap_mode="r")


class LyNSeCHEDataset(Dataset[tuple[Tensor, Tensor]]):
    def __init__(self, tiles: list[TileRef], augment: bool) -> None:
        self.tiles = tiles
        self.augment = augment

    def __len__(self) -> int:
        return len(self.tiles)

    def __getitem__(self, item: int) -> tuple[Tensor, Tensor]:
        reference = self.tiles[item]
        array = load_memmap(reference.path)
        tile = array if reference.index is None else array[reference.index]
        image = np.asarray(tile[..., :3], dtype=np.float32) / 255.0
        mask = (np.asarray(tile[..., 3]) > 0).astype(np.float32)
        image_tensor = torch.from_numpy(np.ascontiguousarray(image.transpose(2, 0, 1)))
        mask_tensor = torch.from_numpy(np.ascontiguousarray(mask[None, ...]))

        if self.augment:
            if torch.rand(()) < 0.5:
                image_tensor, mask_tensor = image_tensor.flip(-1), mask_tensor.flip(-1)
            if torch.rand(()) < 0.5:
                image_tensor, mask_tensor = image_tensor.flip(-2), mask_tensor.flip(-2)
            rotations = int(torch.randint(0, 4, (1,)).item())
            image_tensor = torch.rot90(image_tensor, rotations, dims=(-2, -1))
            mask_tensor = torch.rot90(mask_tensor, rotations, dims=(-2, -1))
            gain = 0.85 + 0.30 * torch.rand(())
            bias = -0.08 + 0.16 * torch.rand(())
            image_tensor = (image_tensor * gain + bias).clamp(0.0, 1.0)
        return image_tensor, mask_tensor


class ConvBlock(nn.Module):
    def __init__(self, channels_in: int, channels_out: int) -> None:
        super().__init__()
        groups = min(8, channels_out)
        self.layers = nn.Sequential(
            nn.Conv2d(channels_in, channels_out, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(groups, channels_out),
            nn.GELU(),
            nn.Conv2d(channels_out, channels_out, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(groups, channels_out),
            nn.GELU(),
        )

    def forward(self, features: Tensor) -> Tensor:
        return self.layers(features)


class SmallUNet(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.enc1 = ConvBlock(3, 32)
        self.enc2 = ConvBlock(32, 64)
        self.enc3 = ConvBlock(64, 128)
        self.enc4 = ConvBlock(128, 256)
        self.bottleneck = ConvBlock(256, 384)
        self.pool = nn.MaxPool2d(2)
        self.dec4 = ConvBlock(384 + 256, 256)
        self.dec3 = ConvBlock(256 + 128, 128)
        self.dec2 = ConvBlock(128 + 64, 64)
        self.dec1 = ConvBlock(64 + 32, 32)
        self.head = nn.Conv2d(32, 1, kernel_size=1)

    @staticmethod
    def upsample(features: Tensor, skip: Tensor) -> Tensor:
        return functional.interpolate(features, size=skip.shape[-2:], mode="bilinear", align_corners=False)

    def forward(self, image: Tensor) -> Tensor:
        enc1 = self.enc1(image)
        enc2 = self.enc2(self.pool(enc1))
        enc3 = self.enc3(self.pool(enc2))
        enc4 = self.enc4(self.pool(enc3))
        current = self.bottleneck(self.pool(enc4))
        current = self.dec4(torch.cat([self.upsample(current, enc4), enc4], dim=1))
        current = self.dec3(torch.cat([self.upsample(current, enc3), enc3], dim=1))
        current = self.dec2(torch.cat([self.upsample(current, enc2), enc2], dim=1))
        current = self.dec1(torch.cat([self.upsample(current, enc1), enc1], dim=1))
        return self.head(current)


def dice_score(logits: Tensor, targets: Tensor, epsilon: float = 1e-6) -> Tensor:
    predicted = (torch.sigmoid(logits) >= 0.5).float()
    intersection = (predicted * targets).sum(dim=(1, 2, 3))
    denominator = predicted.sum(dim=(1, 2, 3)) + targets.sum(dim=(1, 2, 3))
    return ((2 * intersection + epsilon) / (denominator + epsilon)).mean()


def iou_score(logits: Tensor, targets: Tensor, epsilon: float = 1e-6) -> Tensor:
    predicted = (torch.sigmoid(logits) >= 0.5).float()
    intersection = (predicted * targets).sum(dim=(1, 2, 3))
    union = ((predicted + targets) > 0).float().sum(dim=(1, 2, 3))
    return ((intersection + epsilon) / (union + epsilon)).mean()


def combined_loss(logits: Tensor, targets: Tensor) -> Tensor:
    bce = functional.binary_cross_entropy_with_logits(logits, targets)
    probabilities = torch.sigmoid(logits)
    intersection = (probabilities * targets).sum(dim=(1, 2, 3))
    denominator = probabilities.sum(dim=(1, 2, 3)) + targets.sum(dim=(1, 2, 3))
    soft_dice_loss = 1 - ((2 * intersection + 1e-6) / (denominator + 1e-6)).mean()
    return bce + soft_dice_loss


def make_split(tiles: list[TileRef], fraction: float, seed: int) -> tuple[list[TileRef], list[TileRef]]:
    if not 0 < fraction < 0.5:
        raise ValueError("validation fraction must be between 0 and 0.5")
    generator = torch.Generator().manual_seed(seed)
    order = torch.randperm(len(tiles), generator=generator).tolist()
    valid_count = max(1, round(len(tiles) * fraction))
    validation = [tiles[index] for index in order[:valid_count]]
    training = [tiles[index] for index in order[valid_count:]]
    return training, validation


def make_loader(dataset: Dataset, batch_size: int, shuffle: bool, workers: int, device: torch.device) -> DataLoader:
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=workers,
        pin_memory=device.type == "cuda",
        persistent_workers=workers > 0,
    )


def evaluate(model: nn.Module, batches: Iterable[tuple[Tensor, Tensor]], device: torch.device) -> dict[str, float]:
    model.eval()
    losses: list[float] = []
    dices: list[float] = []
    ious: list[float] = []
    with torch.no_grad():
        for image, target in batches:
            image, target = image.to(device, non_blocking=True), target.to(device, non_blocking=True)
            logits = model(image)
            losses.append(combined_loss(logits, target).item())
            dices.append(dice_score(logits, target).item())
            ious.append(iou_score(logits, target).item())
    return {"loss": float(np.mean(losses)), "dice": float(np.mean(dices)), "iou": float(np.mean(ious))}


def save_preview(model: nn.Module, dataset: Dataset, device: torch.device, path: Path) -> None:
    model.eval()
    figure, axes = plt.subplots(3, 3, figsize=(12, 12))
    with torch.no_grad():
        for column in range(3):
            image, target = dataset[column % len(dataset)]
            prediction = torch.sigmoid(model(image.unsqueeze(0).to(device))).squeeze().cpu().numpy()
            axes[0, column].imshow(image.permute(1, 2, 0).numpy())
            axes[1, column].imshow(target.squeeze().numpy(), cmap="gray", vmin=0, vmax=1)
            axes[2, column].imshow(prediction >= 0.5, cmap="gray", vmin=0, vmax=1)
            for row in range(3):
                axes[row, column].axis("off")
    axes[0, 0].set_ylabel("H&E", fontsize=12)
    axes[1, 0].set_ylabel("Mask", fontsize=12)
    axes[2, 0].set_ylabel("Prediction", fontsize=12)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def write_tile_manifest(path: Path, training: list[TileRef], validation: list[TileRef]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["split", "path", "array_index", "partition"])
        writer.writeheader()
        for split_name, values in (("train", training), ("validation_tile_only", validation)):
            for tile in values:
                writer.writerow(
                    {"split": split_name, "path": tile.path, "array_index": tile.index, "partition": tile.partition}
                )


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    data_dir = args.data_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        print("WARNING: CUDA is unavailable. This configuration is intended for a Kaggle GPU session.")

    tiles = discover_tiles(data_dir)
    training_tiles, validation_tiles = make_split(tiles, args.validation_fraction, args.seed)
    write_tile_manifest(output_dir / "tile_manifest.csv", training_tiles, validation_tiles)
    train_loader = make_loader(LyNSeCHEDataset(training_tiles, augment=True), args.batch_size, True, args.num_workers, device)
    validation_dataset = LyNSeCHEDataset(validation_tiles, augment=False)
    validation_loader = make_loader(validation_dataset, args.batch_size, False, args.num_workers, device)

    model = SmallUNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=10)
    scaler = torch.cuda.amp.GradScaler(enabled=device.type == "cuda")
    run_config = {
        "arguments": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
        "device": str(device),
        "cuda_device": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "torch_version": torch.__version__,
        "tile_count": len(tiles),
        "training_tile_count": len(training_tiles),
        "validation_tile_count": len(validation_tiles),
        "scientific_limitation": "Validation is tile-level only; LyNSeC public release lacks patient IDs for grouped splitting.",
    }
    (output_dir / "run_config.json").write_text(json.dumps(run_config, indent=2), encoding="utf-8")

    best_dice, best_epoch, epochs_without_improvement = -1.0, -1, 0
    history_path = output_dir / "history.csv"
    with history_path.open("w", newline="", encoding="utf-8") as history_file:
        fields = ["epoch", "train_loss", "validation_loss", "validation_dice", "validation_iou", "learning_rate"]
        writer = csv.DictWriter(history_file, fieldnames=fields)
        writer.writeheader()
        for epoch in range(1, args.epochs + 1):
            model.train()
            training_losses: list[float] = []
            for image, target in train_loader:
                image, target = image.to(device, non_blocking=True), target.to(device, non_blocking=True)
                optimizer.zero_grad(set_to_none=True)
                with torch.cuda.amp.autocast(enabled=device.type == "cuda"):
                    logits = model(image)
                    loss = combined_loss(logits, target)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
                training_losses.append(loss.item())

            metrics = evaluate(model, validation_loader, device)
            scheduler.step(metrics["dice"])
            row = {
                "epoch": epoch,
                "train_loss": float(np.mean(training_losses)),
                "validation_loss": metrics["loss"],
                "validation_dice": metrics["dice"],
                "validation_iou": metrics["iou"],
                "learning_rate": optimizer.param_groups[0]["lr"],
            }
            writer.writerow(row)
            history_file.flush()
            print(
                f"epoch={epoch:03d} train_loss={row['train_loss']:.4f} "
                f"valid_dice={row['validation_dice']:.4f} valid_iou={row['validation_iou']:.4f}"
            )
            if metrics["dice"] > best_dice:
                best_dice, best_epoch, epochs_without_improvement = metrics["dice"], epoch, 0
                torch.save(
                    {
                        "model_state_dict": model.state_dict(),
                        "epoch": epoch,
                        "validation_metrics": metrics,
                        "run_config": run_config,
                    },
                    output_dir / "best_model.pt",
                )
                (output_dir / "run_summary.json").write_text(json.dumps({
                    "best_epoch": epoch, "best_validation_metrics": metrics,
                    "status": "training_in_progress",
                    "interpretation": "Engineering-only tile-level LyNSeC segmentation baseline; not patient-level validation.",
                }, indent=2), encoding="utf-8")
            else:
                epochs_without_improvement += 1
                if epochs_without_improvement >= args.patience:
                    print(f"Early stopping after {epoch} epochs; best validation Dice was at epoch {best_epoch}.")
                    break

    checkpoint = torch.load(output_dir / "best_model.pt", map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    save_preview(model, validation_dataset, device, output_dir / "prediction_preview.png")
    summary = {
        "best_epoch": best_epoch,
        "best_validation_metrics": checkpoint["validation_metrics"],
        "interpretation": "Engineering-only tile-level LyNSeC segmentation baseline; not patient-level validation.",
    }
    (output_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

