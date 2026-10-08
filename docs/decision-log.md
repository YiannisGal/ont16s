# Decision log

Significant architectural and scientific decisions. Newest last.
Format: date · decision · alternatives · reason · consequences.

---

## D-001 — Project positioning

- **Date:** 2026-10-06
- **Decision:** ont16s is a validation- and database-aware Emu profiling pipeline for
  environmental ONT full-length 16S, not a generic ONT 16S pipeline.
- **Alternatives:**
  1. Generic Emu Nextflow pipeline (as originally scoped).
  2. Contribute an Emu route to nf-core/ampliseq instead of a standalone pipeline.
  3. Use TRANA or EPI2ME wf-16s as-is.
- **Reason:** TRANA (v1.1.0, Sept 2026) already provides an Emu-centred Nextflow
  pipeline; nf-core/ampliseq dev covers ONT via Savont. Neither provides built-in mock
  validation, database provenance, or environmental database support.
  See `docs/project-landscape.md`.
- **Consequences:** Validation and database modules are core scope, not stretch goals.
  Upstream contribution remains a stretch goal. Landscape must be re-checked before release.

## D-002 — Emu as primary profiler; Savont deferred

- **Date:** 2026-10-06
- **Decision:** Emu (pinned version) is the primary profiling route. Savont / ASV route
  is not implemented until Emu is validated, and only if a comparison justifies it.
- **Alternatives:** Savont ASVs + classifier; minimap2 best-hit; Kraken2 + Bracken.
- **Reason:** Emu is designed for error-prone full-length ONT reads and has an nf-core
  module. Savont is already integrated in nf-core/ampliseq dev, so ont16s adds little by
  re-wrapping it.
- **Consequences:** Results depend heavily on the Emu reference database → see future
  database decisions. Emu cannot report taxa absent from its database.

## D-003 — Dataset roles and no re-tuning

- **Date:** 2026-10-06
- **Decision:** Zymo 2025.09 = development / testing / primary validation;
  PRJNA925180 synthetic mock + PRJEB82315 Zymo runs = independent validation;
  PRJNA925180 environmental samples = demonstration. Parameters are fixed on Zymo
  development data and not re-tuned on later datasets.
- **Alternatives:** Treat NaMeco as fully independent; tune per dataset.
- **Reason:** PRJEB82315 uses the same Zymo standards (D6306, D6331), so it tests
  lab/protocol independence, not biological independence. Re-tuning would overfit.
- **Consequences:** Independent validation may show worse performance — that is a
  valid result and will be reported.

## D-004 — Lab server is the primary execution environment

- **Date:** 2026-10-06
- **Decision:** All pipeline runs, data downloads and container work happen on the lab
  server (Ubuntu 24.04, x86_64, 28 CPU, 125 GB RAM, Docker 29.8, Java 17, no SLURM).
  The MacBook (M1, 8 GB RAM, ~12 GB free disk) is used for documentation, review and
  Claude Desktop discussion only. GitHub (`YiannisGal/ont16s`) synchronises the two.
- **Alternatives:** Develop locally on the MacBook with subsets; copy project to server manually.
- **Reason:** 8 GB RAM and ~12 GB free disk are too tight for Docker + Nextflow + Emu,
  and the full Zymo set is 5.1 GB. Server is x86_64, avoiding arm64 container issues.
  Manual copying would create diverging copies; git keeps one source of truth.
- **Consequences:**
  - Default container engine: Docker (`-profile docker`) on the server.
  - Large data and Nextflow `work/` must live on the large data disk, not the
    nearly-full root partition.
  - The server has **no SLURM**: the HPC milestone (M11) needs another cluster, or a
    local test SLURM setup. Unresolved.
  - ARM compatibility is no longer blocking but should still be documented for users.

## D-005 — nf-core branching model (`dev` → `main`)

- **Date:** 2026-10-08
- **Decision:** Feature branches merge into `dev` through pull requests. `main` only
  receives merges from `dev` (or `patch`) at releases. A `TEMPLATE` branch holds the
  untouched nf-core template output for future template syncs.
- **Alternatives:** Merge feature branches directly into `main` and delete the template's
  `branch.yml` check.
- **Reason:** It is the nf-core convention (and `branch.yml` from the template enforces
  it); `main` always reflects the latest release; learning value for nf-core work.
- **Consequences:** Default branch for development is `dev`. Releases are explicit
  `dev` → `main` PRs plus a tag. `nf-core pipelines lint` currently reports
  `files_unchanged: .github/workflows/branch.yml`: caused by a one-space whitespace
  difference (nf-core/tools 4.1.0 template with skipped features); fixed 2026-10-08.
