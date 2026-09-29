# Depositor metadata request — DRAFT, NOT SENT

**Status:** ⛔ **DRAFT ONLY. DO NOT SEND.**
The researcher has not authorised sending any external message, and supervisor
rule 10 prohibits it. This file exists so the request is ready if and when
authorisation is given.

**Prepared:** 2026-09-11
**Would be addressed to:** Dr Matthew A. Care — `matthew.care@york.ac.uk`
(contact listed on the GSE181063 series record; Bioscience Technology Facility,
Data Science Hub, Department of Biology, University of York)
**Possible cc:** Dr Sharon L. Barrans (series contributor)

**Scope check before any send:** this asks only for linkage and definitions
among **existing anonymised study records**. It requests no real identities, no
dates of birth, no contact details, and no re-identifiable information. If
authorisation is given, this scope must not be widened.

---

## Draft message

**Subject:** GSE181063 — four metadata questions (sample/patient linkage, OS time origin, QC codes, pred_combine provenance)

Dear Dr Care,

I am carrying out a reanalysis of publicly deposited DLBCL expression cohorts,
using GSE181063 as a development cohort for a prognostic modelling study. The
deposit is unusually well annotated and has made a careful eligibility audit
possible. Four items are not determinable from the released records, and each
materially affects whether the analysis can be specified correctly. I would be
grateful for any guidance you are able to give.

**1. Anonymous sample-to-patient mapping.**
The field `pid_pmid_32187361` is present for 583 of the 1,310 samples, and
those 583 map to 534 distinct identifiers — so repeat samples per patient
clearly occur. For the remaining 727 samples no patient identifier is released,
and `Sample_title` appears to be an array index (`DASLV4_<n>`) rather than a
specimen or patient key.

Would it be possible to release, or to point me to, an **anonymous** mapping
from GEO sample accession to an arbitrary study-patient number covering the
full series? I am asking only for grouping among existing anonymised records —
no identities or dates. Without it I cannot guarantee patient-grouped
cross-validation, and I am currently restricting the analysis to the 301
identifiable eligible patients rather than risk the same patient appearing on
both sides of a split.

**2. Time origin of `os_followup_y`.**
Could you confirm what time zero is for this field — date of diagnosis, date of
registration, date of treatment initiation, or something else — and the
administrative follow-up cut-off? The observed maximum among censored records
is 14.3190 years, which is consistent with a diagnosis origin and a
31 December 2018 cut-off given the 2004–2012 accrual window described in
Lacy et al. (PMID 32187361), but I would rather not infer the estimand.

**3. Definition of `qc_fail`.**
`qc_fail` takes values 0–5. I have been able to establish empirically that
`probe_detection` equals the fraction of probes with detection p < 0.01
(reproduced to six decimal places on several arrays), and that `qc_fail` is
associated with lower `probe_detection`. But the criteria each level counts are
not documented in the deposit. Could you say what checks contribute to the code,
and whether `qc_fail == 0` is the intended "analysis-ready" filter?

**4. Provenance of `pred_combine`.**
Could you confirm which classifier and version produced `pred_combine`
(GCB / ABC / UNC / MHG) and the associated `conf_combine_*` values — and in
particular whether any samples in this series contributed to that classifier's
development or training? I want to avoid presenting a comparator as independent
if it was fitted using overlapping material.

A brief reply to any subset of these would be very helpful, and I am happy to
acknowledge the assistance in any resulting output. If a supplementary file
already covers some of this and I have missed it, a pointer would be equally
welcome.

With thanks for making the dataset available,

[name]
[affiliation]

---

## Notes for the researcher, not part of the message

- **Item 1 is the highest value.** It is the only route that would restore the
  243 excluded samples and raise the analysable population above 301 patients.
- **Item 2 is the current hard gate.** Per the supervisor, survival models are
  not to be fitted until the OS estimand is defensible. A one-line answer here
  unblocks the study; an inference does not.
- **Do not wait on a reply.** Work continues on the identified subcohort and on
  independent documentation. Depositor contact is one possible resolution, not
  proof that no supplementary mapping exists — a further search of the series
  supplementary files and of Lacy/Painter supplements should continue in
  parallel.
- If a mapping arrives **before** outcome modelling, the population is updated
  under the same deterministic rules and the amendment recorded. If it arrives
  **after**, the expanded analysis is reported separately and must never
  quietly replace the frozen primary population.
