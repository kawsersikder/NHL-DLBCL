"""Phase 2 recovery QC using the successful E-001 LyNSeC H&E U-Net.

Why this exists
---------------
The released HoLy-Net ``he.tar`` checkpoint loads with complete key coverage in
current TIAToolbox, but its source-data smoke test produces Dice ~= 0.28. Direct
forward and the public TIAToolbox inference API agree exactly, and RGB/BGR plus
threshold diagnostics do not rescue it. It is therefore not a defensible
segmenter for downstream morphology extraction in this project.

This script keeps the project in Phase 2 while removing that checkpoint from
the critical path. It:

1. loads the E-001 SmallUNet checkpoint (LyNSeC H&E validation Dice 0.8779),
2. evaluates semantic masks and watershed-derived instances on the validation
   tiles recorded by E-001's tile manifest,
3. creates instance overlays for a patient-diverse sample of DLBCL-Morph H&E
   patches, and
4. writes a blank review sheet for human/pathologist QC.

The LyNSeC split is tile-level because the release lacks patient identifiers.
Its metrics are an engineering gate, not a publication result. DLBCL-Morph has
no manual nucleus ground truth in this workflow, so its overlays require human
review before feature extraction.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import random
import time
import zipfile
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import torch
import torch.nn.functional as functional
from matplotlib import pyplot as plt
from PIL import Image
from scipy import ndimage as ndi
from scipy.optimize import linear_sum_assignment
from skimage.feature import peak_local_max
from skimage.measure import label, regionprops
from skimage.morphology import remove_small_objects
from skimage.segmentation import find_boundaries, watershed
from torch import Tensor, nn


# ---------------------------------------------------------------------------
# Run settings. Keep True until the smoke output and overlays look correct.
# ---------------------------------------------------------------------------
SMOKE_TEST = True
SEED = 20260828
PROBABILITY_THRESHOLD = 0.50
MIN_NUCLEUS_AREA_PX = 20
WATERSHED_MIN_DISTANCE_PX = 5
CENTROID_MATCH_RADIUS_PX = 12.0

LYNSEC_TILES = 1 if SMOKE_TEST else 50
DLBCL_PATCHES = 2 if SMOKE_TEST else 20

if Path("/kaggle/working").exists():
    OUTPUT_DIR = Path("/kaggle/working/phase_02_unet_recovery_qc")
    SEARCH_ROOT = Path("/kaggle/input")
else:
    OUTPUT_DIR = Path("phase_02_unet_recovery_qc_output")
    SEARCH_ROOT = Path.cwd()

LYNSEC_OVERLAY_DIR = OUTPUT_DIR / "lynsec_overlays"
DLBCL_OVERLAY_DIR = OUTPUT_DIR / "dlbcl_morph_overlays"


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def md5sum(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


class ConvBlock(nn.Module):
    """Exact E-001 convolutional block."""

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
    """Exact architecture used by the successful E-001 run."""

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
        return functional.interpolate(
            features,
            size=skip.shape[-2:],
            mode="bilinear",
            align_corners=False,
        )

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


def find_e001_checkpoint() -> Path:
    candidates = list(SEARCH_ROOT.rglob("best_model.pt"))
    candidates.sort(
        key=lambda path: (
            "phase_01_lynsec" not in str(path).lower(),
            "output_final" not in str(path).lower(),
            len(str(path)),
        )
    )
    if not candidates:
        raise FileNotFoundError(
            "No best_model.pt found. Attach the dlbcl-kaggle-code dataset "
            "containing the E-001 output_final directory."
        )
    return candidates[0]


def load_e001_model(device: torch.device) -> tuple[SmallUNet, Path, dict]:
    checkpoint_path = find_e001_checkpoint()
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    if not isinstance(checkpoint, dict) or "model_state_dict" not in checkpoint:
        raise RuntimeError(f"Unexpected checkpoint structure: {checkpoint_path}")
    model = SmallUNet()
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.eval().to(device)
    return model, checkpoint_path, checkpoint


def find_validation_manifest(checkpoint_path: Path) -> Path:
    nearby = checkpoint_path.parent / "tile_manifest.csv"
    if nearby.exists():
        return nearby
    candidates = list(SEARCH_ROOT.rglob("tile_manifest.csv"))
    candidates.sort(key=lambda path: ("phase_01_lynsec" not in str(path).lower(), len(str(path))))
    if not candidates:
        raise FileNotFoundError(
            "E-001 tile_manifest.csv was not found. Refusing to score arbitrary "
            "tiles because training tiles could be mislabeled as validation."
        )
    return candidates[0]


def validation_tile_names(manifest_path: Path) -> set[str]:
    names: set[str] = set()
    with manifest_path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("split", "").startswith("validation"):
                names.add(Path(row["path"]).name)
    if not names:
        raise RuntimeError(f"No validation rows found in {manifest_path}")
    return names


def find_lynsec_validation_tiles(valid_names: set[str]) -> list[Path]:
    by_name: dict[str, Path] = {}
    for path in SEARCH_ROOT.rglob("*.npy"):
        lower = path.stem.lower()
        if lower.endswith(("_l2", "_l3")) and path.name in valid_names:
            by_name.setdefault(path.name, path)
    missing = sorted(valid_names - set(by_name))
    if missing:
        raise FileNotFoundError(
            f"Only {len(by_name)}/{len(valid_names)} E-001 validation tiles were found; "
            f"examples missing: {missing[:5]}"
        )
    return [by_name[name] for name in sorted(by_name)]


def load_lynsec_tile(path: Path) -> tuple[np.ndarray, np.ndarray]:
    array = np.load(path, allow_pickle=True)
    if isinstance(array, np.ndarray) and array.shape == ():
        array = array.item()
    if isinstance(array, dict):
        image_key = next((key for key in ("image", "img", "rgb") if key in array), None)
        mask_key = next((key for key in ("mask", "instance", "inst", "label") if key in array), None)
        if image_key is None or mask_key is None:
            raise ValueError(f"Unsupported dictionary tile keys in {path}: {list(array)[:10]}")
        image = np.asarray(array[image_key])
        instances = np.asarray(array[mask_key])
    else:
        array = np.asarray(array)
        if array.ndim != 3 or array.shape[-1] < 4:
            raise ValueError(f"Expected HxWx4+ LyNSeC array, got {array.shape} in {path}")
        image = array[..., :3]
        instances = array[..., 3]
    return np.clip(image, 0, 255).astype(np.uint8), instances.astype(np.int32)


def predict_probability(model: nn.Module, image: np.ndarray, device: torch.device) -> np.ndarray:
    height, width = image.shape[:2]
    pad_height = (-height) % 16
    pad_width = (-width) % 16
    tensor = torch.from_numpy(
        np.ascontiguousarray(image.astype(np.float32).transpose(2, 0, 1)[None] / 255.0)
    ).to(device)
    if pad_height or pad_width:
        tensor = functional.pad(tensor, (0, pad_width, 0, pad_height), mode="reflect")
    with torch.inference_mode():
        probability = torch.sigmoid(model(tensor))[0, 0]
    return probability[:height, :width].cpu().numpy()


def probability_to_instances(probability: np.ndarray) -> np.ndarray:
    binary = probability >= PROBABILITY_THRESHOLD
    binary = remove_small_objects(binary, min_size=MIN_NUCLEUS_AREA_PX)
    binary = ndi.binary_fill_holes(binary)
    if not binary.any():
        return np.zeros(binary.shape, dtype=np.int32)

    distance = ndi.distance_transform_edt(binary)
    peaks = peak_local_max(
        distance,
        labels=binary,
        min_distance=WATERSHED_MIN_DISTANCE_PX,
        threshold_abs=1.0,
        exclude_border=False,
    )
    if len(peaks) == 0:
        return label(binary, connectivity=1).astype(np.int32)

    markers = np.zeros(binary.shape, dtype=np.int32)
    markers[tuple(peaks.T)] = np.arange(1, len(peaks) + 1, dtype=np.int32)
    return watershed(-distance, markers=markers, mask=binary).astype(np.int32)


def semantic_dice(pred_instances: np.ndarray, gt_instances: np.ndarray) -> float:
    predicted = pred_instances > 0
    target = gt_instances > 0
    intersection = np.logical_and(predicted, target).sum()
    return float((2 * intersection + 1) / (predicted.sum() + target.sum() + 1))


def centroid_detection_scores(
    pred_instances: np.ndarray,
    gt_instances: np.ndarray,
) -> dict[str, float | int]:
    pred_centroids = np.asarray([region.centroid for region in regionprops(pred_instances)])
    gt_centroids = np.asarray([region.centroid for region in regionprops(gt_instances)])
    pred_count = int(len(pred_centroids))
    gt_count = int(len(gt_centroids))

    if pred_count == 0 or gt_count == 0:
        true_positive = 0
    else:
        distances = np.linalg.norm(
            gt_centroids[:, None, :] - pred_centroids[None, :, :],
            axis=2,
        )
        rows, columns = linear_sum_assignment(distances)
        true_positive = int((distances[rows, columns] <= CENTROID_MATCH_RADIUS_PX).sum())

    false_positive = pred_count - true_positive
    false_negative = gt_count - true_positive
    precision = true_positive / max(1, true_positive + false_positive)
    recall = true_positive / max(1, true_positive + false_negative)
    f1 = 2 * precision * recall / max(1e-12, precision + recall)
    count_error = abs(pred_count - gt_count) / max(1, gt_count)
    return {
        "gt_count": gt_count,
        "pred_count": pred_count,
        "detection_tp": true_positive,
        "detection_precision": float(precision),
        "detection_recall": float(recall),
        "detection_f1": float(f1),
        "absolute_count_error_fraction": float(count_error),
    }


def dense_relabel(instances: np.ndarray) -> np.ndarray:
    """Map arbitrary positive instance IDs to consecutive 1..N labels."""
    positive_ids = np.unique(instances)
    positive_ids = positive_ids[positive_ids > 0]
    output = np.zeros(instances.shape, dtype=np.int32)
    foreground = instances > 0
    if len(positive_ids):
        output[foreground] = np.searchsorted(positive_ids, instances[foreground]) + 1
    return output


def panoptic_quality(pred_instances: np.ndarray, gt_instances: np.ndarray) -> dict[str, float]:
    pred_instances = dense_relabel(pred_instances)
    gt_instances = dense_relabel(gt_instances)
    gt_count = int(gt_instances.max())
    pred_count = int(pred_instances.max())
    if gt_count == 0 and pred_count == 0:
        return {"pq": 1.0, "dq": 1.0, "sq": 1.0}
    if gt_count == 0 or pred_count == 0:
        return {"pq": 0.0, "dq": 0.0, "sq": 0.0}

    intersections = np.zeros((gt_count + 1, pred_count + 1), dtype=np.int64)
    np.add.at(intersections, (gt_instances.ravel(), pred_instances.ravel()), 1)
    gt_areas = np.bincount(gt_instances.ravel(), minlength=gt_count + 1)
    pred_areas = np.bincount(pred_instances.ravel(), minlength=pred_count + 1)
    intersection = intersections[1:, 1:]
    union = gt_areas[1:, None] + pred_areas[None, 1:] - intersection
    iou = np.divide(
        intersection,
        union,
        out=np.zeros_like(intersection, dtype=np.float64),
        where=union > 0,
    )
    rows, columns = linear_sum_assignment(1.0 - iou)
    matched_ious = iou[rows, columns]
    matched_ious = matched_ious[matched_ious > 0.5]
    true_positive = len(matched_ious)
    false_positive = pred_count - true_positive
    false_negative = gt_count - true_positive
    denominator = true_positive + 0.5 * false_positive + 0.5 * false_negative
    detection_quality = true_positive / denominator if denominator else 0.0
    segmentation_quality = float(matched_ious.mean()) if true_positive else 0.0
    return {
        "pq": float(detection_quality * segmentation_quality),
        "dq": float(detection_quality),
        "sq": segmentation_quality,
    }


def save_lynsec_overlay(
    image: np.ndarray,
    gt_instances: np.ndarray,
    pred_instances: np.ndarray,
    metrics: dict,
    output_path: Path,
) -> None:
    gt_boundaries = find_boundaries(gt_instances, mode="outer")
    pred_boundaries = find_boundaries(pred_instances, mode="outer")
    gt_overlay = image.copy()
    pred_overlay = image.copy()
    gt_overlay[gt_boundaries] = [0, 255, 0]
    pred_overlay[pred_boundaries] = [255, 0, 0]

    error_overlay = image.copy()
    gt_binary = gt_instances > 0
    pred_binary = pred_instances > 0
    error_overlay[pred_binary & ~gt_binary] = [255, 0, 0]
    error_overlay[gt_binary & ~pred_binary] = [0, 180, 255]

    figure, axes = plt.subplots(1, 4, figsize=(18, 5))
    axes[0].imshow(image)
    axes[0].set_title("H&E")
    axes[1].imshow(gt_overlay)
    axes[1].set_title(f"GT instances: {metrics['gt_count']}")
    axes[2].imshow(pred_overlay)
    axes[2].set_title(f"U-Net + watershed: {metrics['pred_count']}")
    axes[3].imshow(error_overlay)
    axes[3].set_title(
        f"FP red / FN blue\nDice={metrics['semantic_dice']:.3f}, "
        f"det-F1={metrics['detection_f1']:.3f}"
    )
    for axis in axes:
        axis.axis("off")
    figure.tight_layout()
    figure.savefig(output_path, dpi=130)
    plt.close(figure)


def find_dlbcl_patches_zip() -> Path | None:
    candidates = list(SEARCH_ROOT.rglob("dlbcl_morph_patches.zip"))
    if not candidates:
        return None
    candidates.sort(key=lambda path: len(str(path)))
    return candidates[0]


def find_dlbcl_he_directory(max_depth: int = 6) -> Path | None:
    """Find Kaggle's extracted ``HE/<patient>/<patch>.png`` layout.

    Kaggle may expose an uploaded ZIP as unpacked dataset folders.  Use a
    breadth-first directory search so finding the shallow ``HE`` root does not
    require recursively walking all ~152,000 patch files.
    """

    current_level = [SEARCH_ROOT]
    for _ in range(max_depth + 1):
        next_level: list[Path] = []
        current_level.sort(
            key=lambda path: ("dlbcl-morph-patches" not in str(path).lower(), str(path))
        )
        for directory in current_level:
            candidate = directory / "HE"
            if candidate.is_dir():
                patient_directory = next(
                    (path for path in candidate.iterdir() if path.is_dir()),
                    None,
                )
                if patient_directory is not None and next(
                    patient_directory.glob("*.png"), None
                ) is not None:
                    return candidate

        for directory in current_level:
            try:
                next_level.extend(path for path in directory.iterdir() if path.is_dir())
            except OSError:
                continue
        current_level = next_level
        if not current_level:
            break
    return None


def choose_dlbcl_he_members(archive: zipfile.ZipFile, count: int) -> list[tuple[str, str, str]]:
    by_patient: dict[str, list[str]] = defaultdict(list)
    for member in archive.namelist():
        if member.endswith("/"):
            continue
        parts = Path(member).parts
        if len(parts) >= 3 and parts[-3].upper() == "HE" and parts[-1].lower().endswith(".png"):
            by_patient[parts[-2]].append(member)
    if not by_patient:
        raise RuntimeError("No HE/<patient_id>/<patch_id>.png members found in patches zip")

    generator = random.Random(SEED)
    patients = sorted(by_patient)
    generator.shuffle(patients)
    selected: list[tuple[str, str, str]] = []
    for patient in patients[: min(count, len(patients))]:
        members = sorted(by_patient[patient])
        member = members[generator.randrange(len(members))]
        selected.append((patient, Path(member).stem, member))
    return selected


def choose_dlbcl_he_paths(he_directory: Path, count: int) -> list[tuple[str, str, Path]]:
    patient_directories = sorted(path for path in he_directory.iterdir() if path.is_dir())
    if not patient_directories:
        raise RuntimeError(f"No patient directories found under {he_directory}")

    generator = random.Random(SEED)
    generator.shuffle(patient_directories)
    selected: list[tuple[str, str, Path]] = []
    for patient_directory in patient_directories[: min(count, len(patient_directories))]:
        patches = sorted(
            path
            for path in patient_directory.iterdir()
            if path.is_file() and path.suffix.lower() == ".png"
        )
        if not patches:
            continue
        patch_path = patches[generator.randrange(len(patches))]
        selected.append((patient_directory.name, patch_path.stem, patch_path))
    if not selected:
        raise RuntimeError(f"No HE/<patient_id>/<patch_id>.png files found under {he_directory}")
    return selected


def save_dlbcl_overlay(
    image: np.ndarray,
    probability: np.ndarray,
    pred_instances: np.ndarray,
    title: str,
    output_path: Path,
) -> None:
    boundaries = find_boundaries(pred_instances, mode="outer")
    overlay = image.copy()
    overlay[boundaries] = [255, 40, 40]
    figure, axes = plt.subplots(1, 3, figsize=(12, 4))
    axes[0].imshow(image)
    axes[0].set_title("DLBCL-Morph H&E")
    axes[1].imshow(probability, cmap="magma", vmin=0, vmax=1)
    axes[1].set_title("Nucleus probability")
    axes[2].imshow(overlay)
    axes[2].set_title(f"Predicted instances: {int(pred_instances.max())}")
    figure.suptitle(title)
    for axis in axes:
        axis.axis("off")
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def aggregate_lynsec_metrics(rows: list[dict]) -> dict:
    numeric_fields = (
        "semantic_dice",
        "detection_precision",
        "detection_recall",
        "detection_f1",
        "absolute_count_error_fraction",
        "pq",
        "dq",
        "sq",
    )
    aggregate: dict[str, float] = {}
    for field in numeric_fields:
        values = np.asarray([row[field] for row in rows], dtype=float)
        aggregate[f"mean_{field}"] = float(values.mean())
        aggregate[f"median_{field}"] = float(np.median(values))
    aggregate["tile_count"] = len(rows)
    return aggregate


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    if not rows and fieldnames is None:
        return
    columns = fieldnames or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LYNSEC_OVERLAY_DIR.mkdir(exist_ok=True)
    DLBCL_OVERLAY_DIR.mkdir(exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log(f"mode: {'SMOKE' if SMOKE_TEST else 'PILOT'} | device: {device}")

    log("STEP 1: loading E-001 SmallUNet checkpoint")
    model, checkpoint_path, checkpoint = load_e001_model(device)
    checkpoint_md5 = md5sum(checkpoint_path)
    validation_metrics = checkpoint.get("validation_metrics", {})
    log(
        f"checkpoint: {checkpoint_path} | md5={checkpoint_md5} | "
        f"recorded Dice={validation_metrics.get('dice')}"
    )

    log("STEP 2: locating the exact E-001 validation tiles")
    manifest_path = find_validation_manifest(checkpoint_path)
    valid_names = validation_tile_names(manifest_path)
    validation_tiles = find_lynsec_validation_tiles(valid_names)
    selected_tiles = validation_tiles[: min(LYNSEC_TILES, len(validation_tiles))]
    log(f"validation tiles found: {len(validation_tiles)} | scoring: {len(selected_tiles)}")

    log("STEP 3: LyNSeC semantic + instance QC")
    lynsec_rows: list[dict] = []
    first_overlay: Path | None = None
    for index, tile_path in enumerate(selected_tiles):
        image, gt_instances = load_lynsec_tile(tile_path)
        probability = predict_probability(model, image, device)
        pred_instances = probability_to_instances(probability)
        row: dict = {
            "tile": tile_path.name,
            "semantic_dice": semantic_dice(pred_instances, gt_instances),
        }
        row.update(centroid_detection_scores(pred_instances, gt_instances))
        row.update(panoptic_quality(pred_instances, gt_instances))
        lynsec_rows.append(row)
        overlay_path = LYNSEC_OVERLAY_DIR / f"{tile_path.stem}_recovery_qc.png"
        save_lynsec_overlay(image, gt_instances, pred_instances, row, overlay_path)
        first_overlay = first_overlay or overlay_path
        log(
            f"  {tile_path.name}: Dice={row['semantic_dice']:.4f} "
            f"det-F1={row['detection_f1']:.4f} PQ={row['pq']:.4f} "
            f"count={row['pred_count']}/{row['gt_count']}"
        )

    write_csv(OUTPUT_DIR / "lynsec_metrics.csv", lynsec_rows)
    aggregate = aggregate_lynsec_metrics(lynsec_rows)
    automatic_gate = (
        aggregate["mean_semantic_dice"] >= 0.80
        and aggregate["mean_detection_f1"] >= 0.70
        and aggregate["median_absolute_count_error_fraction"] <= 0.20
    )
    gate_status = "not_evaluated_smoke" if SMOKE_TEST else ("pass" if automatic_gate else "fail")
    log(
        f"LyNSeC aggregate: Dice={aggregate['mean_semantic_dice']:.4f} | "
        f"det-F1={aggregate['mean_detection_f1']:.4f} | "
        f"median count error={aggregate['median_absolute_count_error_fraction']:.3f} | "
        f"automatic gate={gate_status.upper()}"
    )

    log("STEP 4: DLBCL-Morph patient-diverse overlay sample")
    review_rows: list[dict] = []
    # Kaggle normally exposes uploaded archives as extracted folders.  Check
    # that shallow layout first to avoid walking all patch files looking for a
    # ZIP which no longer exists in the mounted dataset.
    he_directory = find_dlbcl_he_directory()
    patches_zip = None if he_directory is not None else find_dlbcl_patches_zip()
    patch_source: Path | None = patches_zip or he_directory
    patch_records: list[tuple[str, str, np.ndarray]] = []
    if he_directory is not None:
        log(f"extracted patch directory: {he_directory}")
        for patient_id, patch_id, patch_path in choose_dlbcl_he_paths(
            he_directory, DLBCL_PATCHES
        ):
            image = np.asarray(Image.open(patch_path).convert("RGB"))
            patch_records.append((patient_id, patch_id, image))
    elif patches_zip is not None:
        log(f"patch archive: {patches_zip}")
        with zipfile.ZipFile(patches_zip) as archive:
            members = choose_dlbcl_he_members(archive, DLBCL_PATCHES)
            for patient_id, patch_id, member in members:
                with archive.open(member) as handle:
                    image = np.asarray(Image.open(io.BytesIO(handle.read())).convert("RGB"))
                patch_records.append((patient_id, patch_id, image))
    else:
        log(
            "  WARNING: neither dlbcl_morph_patches.zip nor an extracted "
            "HE/<patient>/<patch>.png tree was found; DLBCL overlay step skipped"
        )

    for patient_id, patch_id, image in patch_records:
        probability = predict_probability(model, image, device)
        pred_instances = probability_to_instances(probability)
        output_name = f"patient_{patient_id}_patch_{patch_id}_qc.png"
        save_dlbcl_overlay(
            image,
            probability,
            pred_instances,
            f"patient {patient_id} | patch {patch_id}",
            DLBCL_OVERLAY_DIR / output_name,
        )
        review_rows.append(
            {
                "patient_id": patient_id,
                "patch_id": patch_id,
                "overlay_file": output_name,
                "predicted_nuclei": int(pred_instances.max()),
                "usable_0_no_1_yes": "",
                "overall_quality_1_to_3": "",
                "merged_nuclei_0_to_3": "",
                "split_nuclei_0_to_3": "",
                "missed_nuclei_0_to_3": "",
                "spurious_nuclei_0_to_3": "",
                "notes": "",
            }
        )
        log(f"  patient {patient_id} patch {patch_id}: {int(pred_instances.max())} nuclei")

    review_fields = [
        "patient_id",
        "patch_id",
        "overlay_file",
        "predicted_nuclei",
        "usable_0_no_1_yes",
        "overall_quality_1_to_3",
        "merged_nuclei_0_to_3",
        "split_nuclei_0_to_3",
        "missed_nuclei_0_to_3",
        "spurious_nuclei_0_to_3",
        "notes",
    ]
    write_csv(OUTPUT_DIR / "dlbcl_morph_review_sheet.csv", review_rows, review_fields)

    summary = {
        "status": "smoke_complete" if SMOKE_TEST else "pilot_complete_pending_human_review",
        "mode": "smoke" if SMOKE_TEST else "pilot",
        "seed": SEED,
        "device": str(device),
        "checkpoint": {
            "path": str(checkpoint_path),
            "md5": checkpoint_md5,
            "e001_recorded_validation_metrics": validation_metrics,
        },
        "postprocessing": {
            "probability_threshold": PROBABILITY_THRESHOLD,
            "minimum_nucleus_area_px": MIN_NUCLEUS_AREA_PX,
            "watershed_min_distance_px": WATERSHED_MIN_DISTANCE_PX,
            "centroid_match_radius_px": CENTROID_MATCH_RADIUS_PX,
        },
        "lynsec": {
            "manifest": str(manifest_path),
            "split_limitation": "E-001 validation is tile-level; LyNSeC has no public patient IDs.",
            "aggregate": aggregate,
            "automatic_engineering_gate": gate_status,
            "gate_definition": {
                "mean_semantic_dice_min": 0.80,
                "mean_detection_f1_min": 0.70,
                "median_absolute_count_error_fraction_max": 0.20,
            },
        },
        "dlbcl_morph": {
            "patch_source": str(patch_source) if patch_source else None,
            "patch_source_mode": (
                "extracted_directory" if he_directory else "zip" if patches_zip is not None else None
            ),
            "patch_archive": str(patches_zip) if patches_zip else None,
            "overlay_count": len(review_rows),
            "gate": "pending human/pathologist review; require >=80% usable patches",
        },
        "scientific_scope": (
            "Binary all-nuclei segmentation plus instance postprocessing. It does not "
            "provide validated tumour/non-tumour phenotypes; downstream features must "
            "remain type-free unless a separate classifier is validated."
        ),
    }
    (OUTPUT_DIR / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n" + "=" * 76)
    print(
        f"PHASE 2 RECOVERY {'SMOKE' if SMOKE_TEST else 'PILOT'} COMPLETE | "
        f"LyNSeC gate={gate_status.upper()} | "
        f"DLBCL overlays={len(review_rows)}"
    )
    print("=" * 76)
    for path in sorted(OUTPUT_DIR.rglob("*")):
        if path.is_file():
            print(f"  {str(path.relative_to(OUTPUT_DIR))[:56]:56s} {path.stat().st_size:>12,d} bytes")

    # Kaggle saves figures to disk; display the first LyNSeC panel interactively too.
    if first_overlay is not None:
        try:
            from IPython.display import display

            display(Image.open(first_overlay))
        except Exception:
            pass


if __name__ == "__main__":
    main()
