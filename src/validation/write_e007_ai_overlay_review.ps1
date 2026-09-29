param(
    [string]$SourceCsv = "reports/phase_03_e007_overlay_review.csv",
    [string]$OutputCsv = "reports/phase_03_e007_ai_overlay_review.csv",
    [string]$ExpertSubsetCsv = "reports/phase_03_e007_expert_priority_subset.csv"
)

$ErrorActionPreference = "Stop"

$caution = @{
    "13903" = @("fibrous_capture|elongated_objects", "Contours are broadly usable, but several elongated stromal/fibrous structures are represented.")
    "13904" = @("fibrous_capture|elongated_objects", "Fibrous, elongated field; usable nuclear contours coexist with possible stromal capture.")
    "13905" = @("sparse_tissue|fibrous_capture", "Sparse fibrous field with limited representative tumour tissue.")
    "13915" = @("sparse_tissue|merge_split", "Sparse field with large irregular objects and possible merge/split ambiguity.")
    "13926" = @("partial_tissue|fibrous_capture", "Partial/background-rich field with elongated-structure capture risk.")
    "13927" = @("fibrous_capture|elongated_fragmentation", "Dark fibrous streaks and fragmented elongated predictions are present.")
    "13957" = @("partial_tissue", "Priority case: the displayed field is usable, but a large fraction is non-tissue/background.")
    "13959" = @("fibrous_capture|elongated_fragmentation", "Elongated fibrous structures create fragmentation risk.")
    "13961" = @("low_contrast|fibrous_capture", "Pale fibrous field with possible non-nuclear capture.")
    "13962" = @("sparse_tissue|fibrous_capture", "Sparse fibrous tissue limits representativeness.")
    "13966" = @("low_contrast|elongated_objects", "Low-contrast field with several elongated objects.")
    "13976" = @("fibrous_capture|elongated_objects", "Numerous thin elongated predictions in a fibrous field.")
    "13978" = @("fibrous_capture|elongated_objects", "Fibrous field with many elongated predictions.")
    "13981" = @("fibrous_band|elongated_objects", "Central fibrous band produces elongated objects.")
    "17653" = @("sparse_tissue|fibrous_capture", "Sparse fibrous field; some predictions follow dark stromal structures.")
    "17664" = @("partial_tissue|merge_split", "Partial tissue and large irregular objects create merge/split uncertainty.")
    "17669" = @("sparse_tissue|fibrous_capture", "Sparse pale/fibrous field with elongated-structure capture.")
    "18830" = @("fibrous_band|elongated_objects", "Fibrous streak and sparse region with elongated predictions.")
    "18839" = @("elongated_objects|fibrous_capture", "Elongated-cell/fibrous field; contours are usable but not tumour-specific.")
    "18846" = @("elongated_objects|fibrous_capture", "Many elongated objects in a fibrous background.")
    "18847" = @("sparse_tissue|non_nuclear_structure_risk", "Sparse pale field with vessel/debris or non-nuclear-structure risk.")
    "18852" = @("elongated_objects|fibrous_capture", "Usable field with several elongated/fibrous predictions.")
    "19683" = @("sparse_tissue|fibrous_capture", "Sparse elongated/fibrous field; contours broadly track dark structures.")
    "19684" = @("non_nuclear_structure_risk|low_contrast", "Pale field with ring-like structures and possible non-nuclear capture.")
    "19688" = @("sparse_tissue|fibrous_capture", "Low-density elongated/fibrous field.")
    "19694" = @("partial_tissue|non_nuclear_structure_risk", "Irregular partial-tissue field with non-nuclear-structure risk.")
    "26786" = @("partial_tissue|fibrous_capture", "Tissue boundary and elongated/fibrous predictions reduce representativeness.")
    "26792" = @("sparse_tissue|fibrous_capture", "Sparse fibrous field with uneven nuclear representation.")
    "26793" = @("partial_tissue|background_debris|fibrous_capture", "Severe tissue boundary/background and debris with fibrous capture risk.")
    "26796" = @("sparse_tissue|fibrous_capture", "Sparse fibrous field with possible stromal-object capture.")
    "26799" = @("sparse_tissue|fibrous_capture", "Sparse fibrous/low-tissue representative field.")
    "26802" = @("partial_tissue", "Large background area; retained tissue contours are broadly usable.")
    "26812" = @("degraded_or_low_quality_tissue|sparse_tissue", "Degraded/low-quality sparse tissue with irregular contours.")
    "26814" = @("fibrous_capture|elongated_objects", "Fibrous field with elongated predictions.")
    "26818" = @("tissue_tear|elongated_objects", "Tissue tears/white spaces and elongated objects reduce representativeness.")
    "26823" = @("partial_tissue", "Large central non-tissue area; remaining contours are usable.")
    "26830" = @("partial_tissue|merge_split", "Partial tissue with large merged probability regions and contour ambiguity.")
    "26835" = @("sparse_tissue|fibrous_capture", "Sparse low-tissue field with fibrous capture risk.")
    "26849" = @("fibrous_capture|elongated_objects", "Fibrous elongated field with possible stromal capture.")
}

$failed = @{
    "26807" = @("fibrous_dominant_field|off_tumour_or_spindle_tissue|elongated_fragmentation", "Priority case: representative patch 1771 is dominated by fibrous/spindle tissue and elongated fragmented predictions; this panel is not acceptable evidence of tumour-nuclear morphology.")
}

$source = Import-Csv -LiteralPath $SourceCsv
if ($source.Count -ne 170) {
    throw "Expected 170 rows in $SourceCsv; found $($source.Count)."
}

$knownIds = [System.Collections.Generic.HashSet[string]]::new()
foreach ($row in $source) {
    [void]$knownIds.Add([string]$row.patient_id)
}
foreach ($patientId in @($caution.Keys) + @($failed.Keys)) {
    if (-not $knownIds.Contains([string]$patientId)) {
        throw "Review label refers to patient $patientId, which is absent from $SourceCsv."
    }
}

$review = foreach ($row in $source) {
    $patientId = [string]$row.patient_id
    $label = "PASS"
    $failureModes = "none_observed"
    $notes = "Representative overlay is technically usable; contours broadly follow visible nuclei and no dominant artifact is evident."
    $priority = "routine"
    $action = "retain_primary"

    if ($caution.ContainsKey($patientId)) {
        $label = "CAUTION"
        $failureModes = $caution[$patientId][0]
        $notes = $caution[$patientId][1]
        $priority = "priority"
        $action = "retain_primary_flag_outcome_blind_sensitivity"
    }
    if ($failed.ContainsKey($patientId)) {
        $label = "FAIL"
        $failureModes = $failed[$patientId][0]
        $notes = $failed[$patientId][1]
        $priority = "high"
        $action = "retain_cache_require_patient_level_technical_audit_before_sensitivity_rule"
    }

    if ($patientId -eq "13957") {
        $priority = "high"
    }
    if ($patientId -eq "17649") {
        $priority = "high"
        $notes = "Displayed patch 82 is technically usable. Known linear-artifact patch 5053 was pre-specified and excluded during extraction; verify that exclusion in every derived analysis table."
        $action = "retain_primary_verify_known_patch_exclusion"
    }

    $includedFailOnly = if ($patientId -eq "26807") { "false" } else { "true" }
    $includedStrictQc = if ($patientId -in @("13957", "26807")) { "false" } else { "true" }
    $strictQcReason = "none"
    if ($patientId -eq "13957") {
        $strictQcReason = "patient_low_tissue_patch_fraction_gt_0.20"
    }
    if ($patientId -eq "26807") {
        $strictQcReason = "median_nuclear_foreground_fraction_lt_0.15_and_failed_representative_overlay"
    }

    [pscustomobject][ordered]@{
        patient_id = $patientId
        patch_id = $row.patch_id
        overlay_file = $row.overlay_file
        ai_review = $label
        ai_failure_modes = $failureModes
        ai_notes = $notes
        analysis_action = $action
        included_primary_170 = "true"
        included_sensitivity_fail_only = $includedFailOnly
        included_sensitivity_strict_qc = $includedStrictQc
        strict_qc_reason = $strictQcReason
        expert_review_priority = $priority
        review_scope = "one outcome-blind representative overlay per patient"
        ai_reviewer = "LLM-assisted computational review (not a pathologist)"
        review_date = "2026-08-28"
        outcomes_accessed = "false"
    }
}

$review | Export-Csv -LiteralPath $OutputCsv -NoTypeInformation -Encoding utf8

$priorityRows = @($review | Where-Object { $_.ai_review -ne "PASS" })
$controlRows = @(
    $review |
        Where-Object { $_.ai_review -eq "PASS" -and $_.patient_id -ne "17649" } |
        ForEach-Object {
            $key = "20260828|$($_.patient_id)|$($_.patch_id)"
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($key)
            $hash = [System.Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($bytes))
            [pscustomobject]@{ row = $_; hash = $hash }
        } |
        Sort-Object hash |
        Select-Object -First 9 |
        ForEach-Object { $_.row }
)

$expertSubset = foreach ($row in $priorityRows) {
    [pscustomobject][ordered]@{
        patient_id = $row.patient_id
        patch_id = $row.patch_id
        overlay_file = $row.overlay_file
        selection_reason = "all_AI_$($row.ai_review.ToLowerInvariant())_representative_overlays"
        ai_review = $row.ai_review
        ai_failure_modes = $row.ai_failure_modes
        expert_review = ""
        expert_failure_mode = ""
        reviewer = ""
        review_date = ""
        expert_notes = ""
    }
}

$expertSubset += [pscustomobject][ordered]@{
    patient_id = "17649"
    patch_id = "5053"
    overlay_file = "kaggle/phase_02_segmentation_qc/output_final/dlbcl_morph_overlays/patient_17649_patch_5053_qc.png"
    selection_reason = "known_pre_specified_linear_artifact"
    ai_review = "KNOWN_EXCLUDED_ARTIFACT"
    ai_failure_modes = "linear_artifact"
    expert_review = ""
    expert_failure_mode = ""
    reviewer = ""
    review_date = ""
    expert_notes = ""
}

foreach ($row in $controlRows) {
    $expertSubset += [pscustomobject][ordered]@{
        patient_id = $row.patient_id
        patch_id = $row.patch_id
        overlay_file = $row.overlay_file
        selection_reason = "deterministic_outcome_blind_PASS_control"
        ai_review = $row.ai_review
        ai_failure_modes = $row.ai_failure_modes
        expert_review = ""
        expert_failure_mode = ""
        reviewer = ""
        review_date = ""
        expert_notes = ""
    }
}

if ($expertSubset.Count -ne 50) {
    throw "Expected a 50-panel expert-priority subset; found $($expertSubset.Count)."
}
$expertSubset | Export-Csv -LiteralPath $ExpertSubsetCsv -NoTypeInformation -Encoding utf8

$counts = $review | Group-Object ai_review | Sort-Object Name
Write-Host "Wrote $($review.Count) AI-assisted overlay reviews to $OutputCsv"
foreach ($count in $counts) {
    Write-Host "  $($count.Name): $($count.Count)"
}
Write-Host "Wrote $($expertSubset.Count) targeted expert-review rows to $ExpertSubsetCsv"
