"""Phase 3A E-007 outcome-blind full feature extraction for DLBCL-Morph.

Run order
---------
1. Create/upload ``phase_03_feature_extraction_e007.yaml``.
2. Keep ``SMOKE_TEST = False`` and Save & Run All for all 170 image patients.
3. Preserve the complete Kaggle output even when a gate fails; diagnose before rerun.

This script never reads clinical variables or survival outcomes. The frozen E-006
rule excludes low-tissue patches only from patch-level count/spatial summaries;
valid non-border cells in partial-tissue patches remain in per-cell morphology
distributions. Spatial features remain patch-local and pixel-based until
physical scale and patch-to-ROI coordinates are verified.

E-007 creates a provisional feature cache pending independent pathology review.
It must not be joined to outcomes or used for survival modelling until that review
gate is documented as passed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import scipy
import skimage
import torch
import torch.nn.functional as functional
import yaml
from matplotlib import pyplot as plt
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import Delaunay, QhullError, cKDTree
from skimage.feature import peak_local_max
from skimage.measure import regionprops
from skimage.morphology import remove_small_objects
from skimage.segmentation import find_boundaries, watershed
from torch import Tensor, nn


# False runs the required 170-patient E-007 extraction.
SMOKE_TEST = False
# In Kaggle, create this YAML in /kaggle/working before running this cell.
CONFIG_PATH_OVERRIDE: str | None = (
    "/kaggle/working/phase_03_feature_extraction_e007.yaml"
    if Path("/kaggle/working").exists()
    else None
)

if Path("/kaggle/working").exists():
    SEARCH_ROOT = Path("/kaggle/input")
    OUTPUT_DIR = Path("/kaggle/working/phase_03a_e007_full_extraction")
else:
    SEARCH_ROOT = Path.cwd()
    OUTPUT_DIR = Path("phase_03a_e007_full_extraction_output")

OVERLAY_DIR = OUTPUT_DIR / "qc_overlays"
CONFIG_NAME = "phase_03_feature_extraction_e007.yaml"
EXPECTED_FULL_PATCH_COUNT = 30007


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def md5sum(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def canonical_list_sha256(values: list[str]) -> str:
    """Hash a compact JSON list so Kaggle input identity is reproducible."""
    payload = json.dumps(values, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def discover_input_inventory(he_root: Path) -> tuple[list[str], list[str]]:
    """Return numerically sorted patients and patient/patch.png inventory."""
    patient_directories = sorted(
        (path for path in he_root.iterdir() if path.is_dir() and path.name.isdigit()),
        key=lambda path: int(path.name),
    )
    patients = [path.name for path in patient_directories]
    inventory: list[str] = []
    for patient_directory in patient_directories:
        patch_paths = sorted(
            patient_directory.glob("*.png"), key=lambda path: int(path.stem)
        )
        inventory.extend(
            f"{patient_directory.name}/{patch_path.name}" for patch_path in patch_paths
        )
    return patients, inventory


def breadth_first_directories(root: Path, max_depth: int = 7):
    current = [root]
    for _ in range(max_depth + 1):
        current.sort(
            key=lambda path: (
                "dlbcl-kaggle-code" not in str(path).lower(),
                "dlbcl-e001-unet" not in str(path).lower(),
                "dlbcl-morph-patches" not in str(path).lower(),
                str(path),
            )
        )
        yield from current
        next_level: list[Path] = []
        for directory in current:
            try:
                next_level.extend(path for path in directory.iterdir() if path.is_dir())
            except OSError:
                continue
        if not next_level:
            return
        current = next_level


def find_config() -> Path:
    if CONFIG_PATH_OVERRIDE is not None:
        override = Path(CONFIG_PATH_OVERRIDE)
        if not override.is_file():
            raise FileNotFoundError(f"CONFIG_PATH_OVERRIDE does not exist: {override}")
        return override
    local_candidates = [
        Path("/kaggle/working") / CONFIG_NAME,
        Path.cwd() / CONFIG_NAME,
        Path.cwd() / "configs" / CONFIG_NAME,
    ]
    if "__file__" in globals():
        local_candidates.insert(
            0, Path(__file__).resolve().parents[2] / "configs" / CONFIG_NAME
        )
    for local in local_candidates:
        if local.exists():
            return local
    for directory in breadth_first_directories(SEARCH_ROOT):
        for candidate in (directory / CONFIG_NAME, directory / "configs" / CONFIG_NAME):
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(
        f"{CONFIG_NAME} not found. Attach the updated dlbcl-kaggle-codee dataset "
        "containing configs/, or upload the YAML as a notebook input."
    )


def find_checkpoint() -> Path:
    for directory in breadth_first_directories(SEARCH_ROOT):
        candidate = directory / "best_model.pt"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("best_model.pt not found; attach dlbcl-e001-unet")


def find_he_directory() -> Path:
    for directory in breadth_first_directories(SEARCH_ROOT):
        candidate = directory / "HE"
        if not candidate.is_dir():
            continue
        patient = next((path for path in candidate.iterdir() if path.is_dir()), None)
        if patient is not None and next(patient.glob("*.png"), None) is not None:
            return candidate
    raise FileNotFoundError(
        "Extracted HE/<patient_id>/<patch_id>.png tree not found; "
        "attach kawsersikder/dlbcl-morph-patches"
    )


class ConvBlock(nn.Module):
    def __init__(self, channels_in: int, channels_out: int) -> None:
        super().__init__()
        groups = min(8, channels_out)
        self.layers = nn.Sequential(
            nn.Conv2d(channels_in, channels_out, 3, padding=1, bias=False),
            nn.GroupNorm(groups, channels_out),
            nn.GELU(),
            nn.Conv2d(channels_out, channels_out, 3, padding=1, bias=False),
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
        self.dec4 = ConvBlock(640, 256)
        self.dec3 = ConvBlock(384, 128)
        self.dec2 = ConvBlock(192, 64)
        self.dec1 = ConvBlock(96, 32)
        self.head = nn.Conv2d(32, 1, 1)

    @staticmethod
    def upsample(features: Tensor, skip: Tensor) -> Tensor:
        return functional.interpolate(
            features, size=skip.shape[-2:], mode="bilinear", align_corners=False
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


def load_model(path: Path, expected_md5: str, device: torch.device) -> tuple[nn.Module, str]:
    observed_md5 = md5sum(path)
    if observed_md5.lower() != expected_md5.lower():
        raise RuntimeError(
            f"Checkpoint MD5 mismatch: expected {expected_md5}, observed {observed_md5}"
        )
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(checkpoint, dict) or "model_state_dict" not in checkpoint:
        raise RuntimeError(f"Unexpected checkpoint structure: {path}")
    model = SmallUNet()
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.eval().to(device)
    return model, observed_md5


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


def probability_to_instances(
    probability: np.ndarray, threshold: float, minimum_area: int, minimum_distance: int
) -> np.ndarray:
    binary = remove_small_objects(probability >= threshold, min_size=minimum_area)
    binary = ndi.binary_fill_holes(binary)
    if not binary.any():
        return np.zeros(binary.shape, dtype=np.int32)
    distance = ndi.distance_transform_edt(binary)
    coordinates = peak_local_max(
        distance, labels=binary, min_distance=minimum_distance, exclude_border=False
    )
    markers = np.zeros(binary.shape, dtype=np.int32)
    if len(coordinates):
        markers[tuple(coordinates.T)] = np.arange(1, len(coordinates) + 1)
    else:
        markers, _ = ndi.label(binary)
    return watershed(-distance, markers, mask=binary).astype(np.int32)


def known_failures(config: dict) -> dict[tuple[str, str], dict]:
    result = {}
    for row in config.get("object_qc", {}).get("known_visual_failures", []):
        result[(str(row["patient_id"]), str(row["patch_id"]))] = row
    return result


def object_rows(
    patient_id: str,
    patch_id: str,
    image: np.ndarray,
    instances: np.ndarray,
    excluded_patch: bool,
) -> list[dict]:
    height, width = instances.shape
    rows: list[dict] = []
    for prop in regionprops(instances):
        min_row, min_col, max_row, max_col = prop.bbox
        border = min_row == 0 or min_col == 0 or max_row == height or max_col == width
        coords = prop.coords
        colours = image[coords[:, 0], coords[:, 1]].mean(axis=0)
        perimeter = float(prop.perimeter)
        circularity = 4.0 * math.pi * float(prop.area) / perimeter**2 if perimeter > 0 else np.nan
        rows.append(
            {
                "patient_id": patient_id,
                "patch_id": patch_id,
                "cell_id": int(prop.label),
                "centroid_y_px": float(prop.centroid[0]),
                "centroid_x_px": float(prop.centroid[1]),
                "area_px": float(prop.area),
                "perimeter_px": perimeter,
                "eccentricity": float(prop.eccentricity),
                "solidity": float(prop.solidity),
                "circularity": float(circularity),
                "major_axis_px": float(prop.axis_major_length),
                "minor_axis_px": float(prop.axis_minor_length),
                "rgb_mean_r": float(colours[0]),
                "rgb_mean_g": float(colours[1]),
                "rgb_mean_b": float(colours[2]),
                "border_touching": int(border),
                "patch_excluded_from_primary": int(excluded_patch),
            }
        )
    return rows


def spatial_features(rows: list[dict]) -> dict[str, float]:
    primary = [
        row
        for row in rows
        if not row["border_touching"] and not row["patch_excluded_from_primary"]
    ]
    points = np.asarray(
        [[row["centroid_x_px"], row["centroid_y_px"]] for row in primary], dtype=float
    )
    result = {
        "nearest_neighbour_median_px": np.nan,
        "nearest_neighbour_mean_px": np.nan,
        "delaunay_edge_median_px": np.nan,
        "delaunay_edge_mean_px": np.nan,
    }
    if len(points) >= 2:
        distances, _ = cKDTree(points).query(points, k=2)
        nearest = distances[:, 1]
        result["nearest_neighbour_median_px"] = float(np.median(nearest))
        result["nearest_neighbour_mean_px"] = float(np.mean(nearest))
    if len(points) >= 3:
        try:
            triangles = Delaunay(points).simplices
            edges = set()
            for triangle in triangles:
                for first, second in ((0, 1), (1, 2), (0, 2)):
                    edges.add(tuple(sorted((int(triangle[first]), int(triangle[second])))))
            lengths = np.asarray([np.linalg.norm(points[a] - points[b]) for a, b in edges])
            result["delaunay_edge_median_px"] = float(np.median(lengths))
            result["delaunay_edge_mean_px"] = float(np.mean(lengths))
        except QhullError:
            pass
    return result


def save_overlay(image: np.ndarray, probability: np.ndarray, instances: np.ndarray, path: Path) -> None:
    overlay = image.copy()
    overlay[find_boundaries(instances, mode="outer")] = [255, 40, 40]
    figure, axes = plt.subplots(1, 3, figsize=(12, 4))
    axes[0].imshow(image)
    axes[0].set_title("DLBCL-Morph H&E")
    axes[1].imshow(probability, cmap="magma", vmin=0, vmax=1)
    axes[1].set_title("Nucleus probability")
    axes[2].imshow(overlay)
    axes[2].set_title(f"Instances: {int(instances.max())}")
    for axis in axes:
        axis.axis("off")
    figure.tight_layout()
    figure.savefig(path, dpi=140)
    plt.close(figure)


def describe(values: pd.Series, prefix: str) -> dict[str, float]:
    array = values.to_numpy(dtype=float)
    array = array[np.isfinite(array)]
    if not len(array):
        return {
            f"{prefix}_median": np.nan,
            f"{prefix}_iqr": np.nan,
            f"{prefix}_p10": np.nan,
            f"{prefix}_p90": np.nan,
        }
    return {
        f"{prefix}_median": float(np.median(array)),
        f"{prefix}_iqr": float(np.percentile(array, 75) - np.percentile(array, 25)),
        f"{prefix}_p10": float(np.percentile(array, 10)),
        f"{prefix}_p90": float(np.percentile(array, 90)),
    }


def aggregate_patients(cells: pd.DataFrame, patches: pd.DataFrame, patients: list[str]) -> pd.DataFrame:
    cell_fields = [
        "area_px",
        "perimeter_px",
        "eccentricity",
        "solidity",
        "circularity",
        "major_axis_px",
        "minor_axis_px",
        "rgb_mean_r",
        "rgb_mean_g",
        "rgb_mean_b",
    ]
    patch_fields = [
        "primary_cell_count",
        "nuclear_foreground_fraction",
        "tissue_fraction",
        "nearest_neighbour_median_px",
        "delaunay_edge_median_px",
    ]
    output: list[dict] = []
    for patient_id in patients:
        patient_cells = cells[
            (cells["patient_id"] == patient_id)
            & (cells["border_touching"] == 0)
            & (cells["patch_excluded_from_primary"] == 0)
        ]
        patient_patches = patches[patches["patient_id"] == patient_id]
        accepted_patches = patient_patches[
            patient_patches["eligible_for_patch_summaries"] == 1
        ]
        row: dict[str, float | int | str] = {
            "patient_id": patient_id,
            "patch_count_total": int(len(patient_patches)),
            "patch_count_primary": int(len(accepted_patches)),
            "patch_count_low_tissue": int(
                patient_patches["low_tissue_for_patch_summaries"].sum()
            ),
            "cell_count_total": int((cells["patient_id"] == patient_id).sum()),
            "cell_count_primary": int(len(patient_cells)),
        }
        for field in cell_fields:
            row.update(describe(patient_cells[field], f"cell_{field}"))
        for field in patch_fields:
            row.update(describe(accepted_patches[field], f"patch_{field}"))
        output.append(row)
    return pd.DataFrame(output)


def write_environment(path: Path, device: torch.device) -> None:
    payload = {
        "python": sys.version,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "scikit_image": skimage.__version__,
        "pyyaml": getattr(yaml, "__version__", "unknown"),
        "device": str(device),
        "cuda_available": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    started = time.time()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OVERLAY_DIR.mkdir(exist_ok=True)
    config_path = find_config()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["scope"].get("selection_uses_outcomes") is not False:
        raise RuntimeError("Refusing to run: YAML must declare selection_uses_outcomes: false")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    mode = "smoke" if SMOKE_TEST else "full_extraction"
    log(f"mode: {mode.upper()} | device: {device} | config: {config_path}")

    checkpoint_path = find_checkpoint()
    model, checkpoint_md5 = load_model(
        checkpoint_path, str(config["checkpoint"]["md5"]), device
    )
    he_root = find_he_directory()
    patients, patch_inventory = discover_input_inventory(he_root)
    patient_inventory_sha256 = canonical_list_sha256(patients)
    patch_inventory_sha256 = canonical_list_sha256(patch_inventory)
    expected_patient_count = int(config["scope"]["expected_patient_count"])
    expected_patch_count = int(config["scope"]["expected_patch_count"])
    expected_patient_sha256 = str(config["scope"]["expected_patient_inventory_sha256"])
    expected_patch_sha256 = str(config["scope"]["expected_patch_inventory_sha256"])
    if len(patients) != expected_patient_count:
        raise RuntimeError(
            f"H&E patient count mismatch: expected {expected_patient_count}, "
            f"observed {len(patients)}"
        )
    if len(patch_inventory) != expected_patch_count:
        raise RuntimeError(
            f"H&E patch count mismatch: expected {expected_patch_count}, "
            f"observed {len(patch_inventory)}"
        )
    if patient_inventory_sha256 != expected_patient_sha256:
        raise RuntimeError(
            "H&E patient inventory SHA-256 mismatch: "
            f"expected {expected_patient_sha256}, observed {patient_inventory_sha256}"
        )
    if patch_inventory_sha256 != expected_patch_sha256:
        raise RuntimeError(
            "H&E patch inventory SHA-256 mismatch: "
            f"expected {expected_patch_sha256}, observed {patch_inventory_sha256}"
        )
    selected_patients = patients[:1] if SMOKE_TEST else patients
    log(f"checkpoint: {checkpoint_path} | md5={checkpoint_md5}")
    log(f"H&E root: {he_root}")
    log(
        f"input inventory verified: patients={len(patients)} | "
        f"patches={len(patch_inventory)} | sha256={patch_inventory_sha256[:12]}..."
    )

    post = config["postprocessing"]
    patch_qc = config["patch_qc"]
    tissue_pixel_threshold = float(patch_qc["tissue_pixel_mean_rgb_max"])
    minimum_tissue_fraction = float(
        patch_qc["minimum_tissue_fraction_for_patch_summaries"]
    )
    failures = known_failures(config)
    cell_rows: list[dict] = []
    patch_rows: list[dict] = []
    exclusion_rows: list[dict] = []
    overlay_written: set[str] = set()
    total_discovered = 0

    for patient_id in selected_patients:
        patient_directory = he_root / patient_id
        if not patient_directory.is_dir():
            raise FileNotFoundError(f"Configured patient directory missing: {patient_directory}")
        patch_paths = sorted(patient_directory.glob("*.png"), key=lambda path: int(path.stem))
        if not patch_paths:
            raise RuntimeError(f"No PNG patches found for patient {patient_id}")
        total_discovered += len(patch_paths)
        if SMOKE_TEST:
            patch_paths = patch_paths[:1]
        log(f"patient {patient_id}: processing {len(patch_paths)} / {total_discovered} discovered patches")

        for patch_path in patch_paths:
            patch_id = patch_path.stem
            image = np.asarray(Image.open(patch_path).convert("RGB"))
            probability = predict_probability(model, image, device)
            instances = probability_to_instances(
                probability,
                float(post["probability_threshold"]),
                int(post["minimum_nucleus_area_px"]),
                int(post["watershed_min_distance_px"]),
            )
            tissue_fraction = float(
                np.mean(np.mean(image, axis=2) < tissue_pixel_threshold)
            )
            low_tissue = tissue_fraction < minimum_tissue_fraction
            failure = failures.get((patient_id, patch_id))
            excluded = failure is not None and failure.get("action") == "exclude_from_primary_and_record"
            eligible_for_patch_summaries = not excluded and not low_tissue
            rows = object_rows(patient_id, patch_id, image, instances, excluded)
            cell_rows.extend(rows)
            primary_count = sum(
                not row["border_touching"] and not row["patch_excluded_from_primary"]
                for row in rows
            )
            patch_row = {
                "patient_id": patient_id,
                "patch_id": patch_id,
                "height_px": int(image.shape[0]),
                "width_px": int(image.shape[1]),
                "predicted_cell_count": len(rows),
                "primary_cell_count": int(primary_count),
                "border_cell_count": int(sum(row["border_touching"] for row in rows)),
                "nuclear_foreground_fraction": float(
                    np.mean(probability >= float(post["probability_threshold"]))
                ),
                "tissue_fraction": tissue_fraction,
                "excluded_from_primary": int(excluded),
                "low_tissue_for_patch_summaries": int(low_tissue),
                "eligible_for_patch_summaries": int(eligible_for_patch_summaries),
                "qc_flag": ";".join(
                    flag
                    for flag in [
                        "known_visual_failure" if failure else "",
                        "low_tissue_for_patch_summaries" if low_tissue else "",
                    ]
                    if flag
                ),
            }
            patch_row.update(spatial_features(rows))
            patch_rows.append(patch_row)
            if failure:
                exclusion_rows.append(
                    {
                        "patient_id": patient_id,
                        "patch_id": patch_id,
                        "action": failure["action"],
                        "reason": failure["reason"],
                        "source": "phase_02_preliminary_computational_review",
                        "tissue_fraction": tissue_fraction,
                        "threshold": "",
                    }
                )
            if low_tissue:
                exclusion_rows.append(
                    {
                        "patient_id": patient_id,
                        "patch_id": patch_id,
                        "action": patch_qc["low_tissue_action"],
                        "reason": (
                            "tissue_fraction_below_"
                            f"{minimum_tissue_fraction:.2f}_for_patch_summaries"
                        ),
                        "source": patch_qc["rule_source"],
                        "tissue_fraction": tissue_fraction,
                        "threshold": minimum_tissue_fraction,
                    }
                )
            if patient_id not in overlay_written:
                save_overlay(
                    image,
                    probability,
                    instances,
                    OVERLAY_DIR / f"patient_{patient_id}_patch_{patch_id}_feature_qc.png",
                )
                overlay_written.add(patient_id)

    cells = pd.DataFrame(cell_rows)
    patches = pd.DataFrame(patch_rows)
    patient_features = aggregate_patients(cells, patches, selected_patients)
    cells.to_parquet(OUTPUT_DIR / "cells.parquet", index=False)
    patches.to_csv(OUTPUT_DIR / "patch_qc.csv", index=False)
    patient_features.to_csv(OUTPUT_DIR / "patient_features.csv", index=False)
    exclusion_fields = [
        "patient_id",
        "patch_id",
        "action",
        "reason",
        "source",
        "tissue_fraction",
        "threshold",
    ]
    with (OUTPUT_DIR / "exclusion_log.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=exclusion_fields)
        writer.writeheader()
        writer.writerows(exclusion_rows)
    (OUTPUT_DIR / "resolved_config.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )

    feature_schema = {
        "unit_of_survival_analysis": "patient",
        "cell_coordinates": "patch-local pixels",
        "spatial_scope": "within patch only",
        "physical_units": "disabled pending pixel-spacing verification",
        "phenotype_scope": "all nuclei; no tumour/non-tumour labels",
        "border_rule": config["object_qc"]["border_touching"],
        "patch_summary_tissue_rule": {
            "method": patch_qc["tissue_pixel_definition"],
            "mean_rgb_threshold": tissue_pixel_threshold,
            "minimum_tissue_fraction": minimum_tissue_fraction,
            "scope": "patch-level count/spatial summaries only",
            "partial_patch_cells_retained_for_morphology": bool(
                patch_qc["partial_tissue_cells_in_per_cell_morphology"]
            ),
        },
        "columns": {column: str(dtype) for column, dtype in patient_features.dtypes.items()},
    }
    (OUTPUT_DIR / "feature_schema.json").write_text(
        json.dumps(feature_schema, indent=2), encoding="utf-8"
    )
    write_environment(OUTPUT_DIR / "environment.json", device)

    elapsed = time.time() - started
    processed_patches = len(patches)
    rate = processed_patches / elapsed if elapsed else 0.0
    numeric = patient_features.select_dtypes(include=[np.number]).to_numpy(dtype=float)
    finite_fraction = float(np.isfinite(numeric).mean()) if numeric.size else 0.0
    expected_rows = 1 if SMOKE_TEST else expected_patient_count
    expected_patches = 1 if SMOKE_TEST else int(
        config["promotion_gate"]["expected_processed_patches"]
    )
    low_tissue_count = int(patches["low_tissue_for_patch_summaries"].sum())
    eligible_patch_count = int(patches["eligible_for_patch_summaries"].sum())
    expected_eligibility = (
        (patches["excluded_from_primary"] == 0)
        & (patches["tissue_fraction"] >= minimum_tissue_fraction)
    )
    eligibility_rule_check = bool(
        np.array_equal(
            patches["eligible_for_patch_summaries"].to_numpy(dtype=bool),
            expected_eligibility.to_numpy(dtype=bool),
        )
    )
    low_tissue_pairs = set(
        zip(
            patches.loc[patches["low_tissue_for_patch_summaries"] == 1, "patient_id"],
            patches.loc[patches["low_tissue_for_patch_summaries"] == 1, "patch_id"],
        )
    )
    partial_tissue_primary_cells_retained = sum(
        (row.patient_id, row.patch_id) in low_tissue_pairs
        and not row.border_touching
        and not row.patch_excluded_from_primary
        for row in cells.itertuples(index=False)
    )
    recorded_low_tissue_rows = sum(
        row["action"] == patch_qc["low_tissue_action"] for row in exclusion_rows
    )
    known_failure_expected = not SMOKE_TEST
    known_failure_flagged = any(
        row["patient_id"] == "17649" and row["patch_id"] == "5053"
        for row in exclusion_rows
    )
    patients_with_eligible_patches = int(
        (patches.groupby("patient_id")["eligible_for_patch_summaries"].sum() > 0).sum()
    )
    promotion = {
        "expected_patient_rows": expected_rows,
        "observed_patient_rows": len(patient_features),
        "patient_row_check": len(patient_features) == expected_rows,
        "expected_processed_patches": expected_patches,
        "observed_processed_patches": processed_patches,
        "processed_patch_check": processed_patches == expected_patches,
        "expected_patient_inventory_sha256": expected_patient_sha256,
        "observed_patient_inventory_sha256": patient_inventory_sha256,
        "patient_inventory_check": patient_inventory_sha256 == expected_patient_sha256,
        "expected_patch_inventory_sha256": expected_patch_sha256,
        "observed_patch_inventory_sha256": patch_inventory_sha256,
        "patch_inventory_check": patch_inventory_sha256 == expected_patch_sha256,
        "finite_numeric_feature_fraction": finite_fraction,
        "finite_fraction_check": finite_fraction
        >= float(config["promotion_gate"]["finite_feature_fraction_min"]),
        "known_failure_flagged": known_failure_flagged,
        "known_failure_check": (not known_failure_expected) or known_failure_flagged,
        "minimum_tissue_fraction_for_patch_summaries": minimum_tissue_fraction,
        "observed_low_tissue_patches": low_tissue_count,
        "recorded_low_tissue_rows": recorded_low_tissue_rows,
        "low_tissue_record_check": recorded_low_tissue_rows == low_tissue_count,
        "eligible_patch_count": eligible_patch_count,
        "patients_with_eligible_patches": patients_with_eligible_patches,
        "all_patients_have_eligible_patch_check": (
            patients_with_eligible_patches == len(selected_patients)
        ),
        "eligibility_rule_check": eligibility_rule_check,
        "partial_tissue_primary_cells_retained": int(
            partial_tissue_primary_cells_retained
        ),
        "partial_tissue_cell_morphology_check": (
            True if SMOKE_TEST else partial_tissue_primary_cells_retained > 0
        ),
    }
    promotion["pass"] = all(
        [
            promotion["patient_row_check"],
            promotion["processed_patch_check"],
            promotion["patient_inventory_check"],
            promotion["patch_inventory_check"],
            promotion["finite_fraction_check"],
            promotion["known_failure_check"],
            promotion["low_tissue_record_check"],
            promotion["all_patients_have_eligible_patch_check"],
            promotion["eligibility_rule_check"],
            promotion["partial_tissue_cell_morphology_check"],
        ]
    )
    summary = {
        "status": f"{mode}_complete",
        "experiment_id": config["experiment_id"],
        "mode": mode,
        "config_path": str(config_path),
        "selection_uses_outcomes": False,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_md5": checkpoint_md5,
        "he_root": str(he_root),
        "provisional_pending_pathology_review": True,
        "outcome_join_permitted": False,
        "full_input_patient_inventory_sha256": patient_inventory_sha256,
        "full_input_patch_inventory_sha256": patch_inventory_sha256,
        "patients": selected_patients,
        "discovered_patches_for_selected_patients": total_discovered,
        "processed_patches": processed_patches,
        "detected_cells": len(cells),
        "excluded_from_cell_morphology_patches": int(
            patches["excluded_from_primary"].sum()
        ),
        "low_tissue_patch_summary_exclusions": low_tissue_count,
        "patch_summary_eligible_patches": eligible_patch_count,
        "exclusion_log_rows": len(exclusion_rows),
        "elapsed_seconds": elapsed,
        "patches_per_second": rate,
        "projected_full_30007_patch_hours": (
            EXPECTED_FULL_PATCH_COUNT / rate / 3600.0 if rate else None
        ),
        "promotion_gate": promotion,
        "scientific_scope": feature_schema,
    }
    (OUTPUT_DIR / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print("\n" + "=" * 78)
    print(
        f"PHASE 3A E007 {mode.upper()} COMPLETE | patients={len(patient_features)} | "
        f"patches={processed_patches} | cells={len(cells)} | "
        f"low_tissue={low_tissue_count} | gate={promotion['pass']}"
    )
    print("=" * 78)
    for path in sorted(OUTPUT_DIR.rglob("*")):
        if path.is_file():
            print(f"  {str(path.relative_to(OUTPUT_DIR))[:58]:58s} {path.stat().st_size:>12,d} bytes")

    first_overlay = next(iter(sorted(OVERLAY_DIR.glob("*.png"))), None)
    if first_overlay is not None:
        try:
            from IPython.display import display

            display(Image.open(first_overlay))
        except Exception:
            pass


if __name__ == "__main__":
    main()
