# Development log

Chronological record of what was done, tested, failed, and decided.
Status vocabulary: Written · Reasoned about · Executed · Tested · Validated.

---

## 2026-10-06 — Milestone 0: landscape and feasibility

**Done (Reasoned about — no code executed):**

- Surveyed nf-core/ampliseq (2.18.0 release; ONT/Savont in dev 3.0.0), Savont, Emu
  (v3.6.2), TRANA (v1.1.0), EPI2ME wf-16s (v1.6.x).
- Queried ENA run metadata for PRJEB82315 and PRJNA925180 (counts in
  `docs/project-landscape.md`).
- Repositioned project (D-001), chose Emu primary (D-002), set dataset roles (D-003).
- Initialised git repository (`main`), added docs.

**Discoveries:**

- TRANA is an existing, maintained Emu Nextflow pipeline — not in original brief.
- PRJEB82315 contains Zymo D6306/D6331 + chicken samples, not independent mocks.
- PRJNA925180 is cross-platform (Illumina/PacBio/ONT R9+R10) with a synthetic mock.

**Open questions:**

- Chemistry / software versions used in Ota et al. comparison.
- Publication linked to PRJNA925180.
- Which Emu container images exist for arm64.
- Rare-taxon loss: Emu source (`emu` L441–470) drops taxa below `10/n_mapped_reads`
  after EM convergence and re-runs EM, redistributing their reads (possible absorption
  into abundant relatives). Plan: validation module reports limit of detection via
  depth subsampling, using low-abundance members of Zymo D6331 (verify Zymo sheet).

**Environment check:**

- MacBook: arm64, 8 GB RAM, ~12 GB free disk, Java 8 (too old for Nextflow), Docker installed.
- Lab server: Ubuntu 24.04 x86_64, 28 CPU, 125 GB RAM, Docker 29.8, Java 17,
  Nextflow present (version TBC), conda present, no SLURM. Data disk ~1.7 TB free;
  root partition 87 % full.
- Decision D-004: server is primary execution environment.
- Zymo 2025.09 BAMs are split into ~70–120 MB chunks per replicate
  (`basecalls/{GutMock,MSPlus}/MAB114/{hac,sup}/repN/`).
- GitHub remote added: `YiannisGal/ont16s` (private).

**Server setup (executed by user):** GitHub SSH key on server, repo cloned to
`/mnt/Ubuntu_HD5/yiannis/ont16s`, Nextflow 26.04.2, Docker works without sudo.

**Zymo 2025.09 dataset details (from S3 listing + ONT page):**

- `basecalls/` only contains SQK-MAB114 BAMs (MSPlus ×6 reps, GutMock ×4, HAC + SUP).
  `analysis/` also has SQK-16S114 results, but no 16S114 BAMs are published.
- MSPlus = Zymo DNA standard + gDNA of _B. adolescentis_, _B. burgdorferi_,
  _C. trachomatis_, _G. vaginalis_. **Expected proportions not published.** Must be sourced
  before quantitative validation.
- ONT ran Emu, wf-16s (Kraken2) and wf-16s (minimap2) on all samples (`analysis/`).
  Useful comparators. ONT's Emu DB (369 MB fasta) is **undocumented**.
- Emu default DB = rrnDB v5.6 + NCBI 16S RefSeq of **2020-09-17** (6 years old).
- Emu v3.6.2 supports `--type lr:hq` (minimap2 preset for high-accuracy reads):
  candidate comparison for R10.4.1 SUP data later.

**Written:** `docs/server-tasks/ST-001-emu-manual-run.md` (not yet executed).

**Next:** execute ST-001 on the server with Claude Code.

## 2026-10-08 — ST-001 executed (manual Emu run)

Ran ST-001 on the server (2026-10-06, Docker, detached script). Full write-up:
`docs/server-tasks/ST-001-results.md`. **Executed, not validated.**

- One MSPlus SUP chunk: 53,011 reads (all barcode04), median 1,577 bp, AvgQual 15.7.
- Emu 3.6.2 + default DB (49,243 seqs): **12/12 expected bacteria detected** in full and
  20k subsample (_Borrelia_ reported as _Borreliella_); they make up ~99.4 % of abundance.
- Resources (8 threads): 20k = 20 min / 2.6 GB; full = 50 min / 3.4 GB. Emu is slow,
  not memory-hungry. `/usr/bin/time` around `docker run` does not measure the container.
- 9 trace taxa (≤0.055 %) present in full but absent at 20k (detection floor `10/n_reads`).
- ONT's own Emu result uses a GTDB-like DB: different species names/splits for several
  mock members. Confirms DB choice matters (D-001).

**Next:** Milestone 1 scaffold; investigate Emu speed (`--type lr:hq`, thread scaling);
add read-length filter.

## 2026-10-08 — ST-002 Emu speed test; Milestone 1 scaffold started

**ST-002** (`docs/server-tasks/ST-002-results.md`, executed, not validated): on the 20 k
subsample, minimap2 is the bottleneck (99.6 % of CPU); 8 → 16 threads halves wall time
(1,221 → 608 s) with identical results. `--type lr:hq` is ~15× faster but leaves 1.9 %
reads unmapped and shifts _Bacillus_ assignments. Keep `map-ont` default; expose `--type`
as a parameter; decide in Milestone 8.

**Milestone 1** (branch `m1-scaffold`):

- Tools in `ont16s_data/tools/`: nf-core/tools 4.1.0 (venv), nf-test 0.9.5
  (sha256 `b7679eb9…fc1641` of the release tarball).
- `nf-core pipelines create` (org `YiannisGal`; skipped igenomes, fastqc, gpu, codespaces,
  seqera_platform, email). Merged via a `TEMPLATE` branch with
  `--allow-unrelated-histories`; `.gitignore` conflict resolved by combining rules.
- `nextflow run . -profile test,docker` → success (MULTIQC only). Warnings:
  `validation.defaultIgnoreParams` / `validation.monochromeLogs` unrecognised.
  Test profile still points at nf-core viralrecon Illumina samplesheet (placeholder).
- `nf-core pipelines lint`: 192 passed, 36 warnings, 1 failed (`branch.yml`, see D-005).
- D-005: nf-core branching model (`dev` → `main`).

**Next:** walk through scaffold files together (step 1c); replace test data with an ONT
Zymo subset; Milestone 2 modules.

## 2026-10-08 — ONT samplesheet (branch `m3-samplesheet`)

- PR #2 (`m1-scaffold` → `dev`) merged by user. CI check results not visible from the
  server (no `gh`/token).
- New samplesheet: `sample,reads,mock`. One row per file (BAM or FASTQ), chunks grouped by
  `sample`. Channel item: `[ [id, mock, format, n_files], [files] ]`.
- Tested locally: valid (BAM + 2-chunk FASTQ + no-mock), mixed BAM/FASTQ (error),
  bad extension (schema error) — all behave as intended.
- Test profiles now use `assets/test/samplesheet_test.csv` → public ONT S3 BAM chunk
  (53 k reads). **Open:** need a small public test subset before Emu goes into CI.
- Lint: 192 passed, 33 warnings, 1 failed (`branch.yml`, D-005).

## 2026-10-08 — Test data repo; branch.yml lint fix; read preparation (M2)

- Lint `branch.yml` failure explained and fixed (one-space whitespace difference).
  Lint: 0 failures.
- D-006: universal pipeline; Zymo only for tests and validation.
- Public test data repo `YiannisGal/ont16s-test-datasets`: 546-read subset (seed 42, 1 %)
  of the ST-001 BAM, 0.7 MB, CC BY-NC 4.0 (ONT). Emu default DB detects 12/12 in 52 s on
  4 threads. Test profiles use it via raw.githubusercontent.com.
- Branch `m2-bam2fastq`: nf-core modules `samtools/cat`, `samtools/fastq`, `cat/fastq`.
  Samples are branched by format/file count; unpaired ONT reads come out of
  `samtools fastq` as `*_other.fastq.gz` (verified: 546/546 reads, flag 4).
  Tested with BAM×1, BAM×2, FASTQ×1, FASTQ×2.gz: read counts exact (546, 53,557, 546,
  1,092). Mixed gz/plain FASTQ rejected. Intermediates not published.
- nf-test pipeline snapshot created and reproduced (2 runs, ~19 s).
- Planned exercise was done by Claude at the user's request.

**Next:** Emu module (`--emu_db`, `--emu_type`) — Milestone 2/5.

## 2026-10-08 — Emu module (branch `m5-emu`)

- PRs #3 (samplesheet) and #4 (read preparation) merged into `dev` by user.
- Test data repo: `emu_db_zymo_genera/` (+ `.tar.gz`, 1.5 MB): all 955 species / 10,170
  sequences of the 15 mock genera from the Emu default DB. Emu detects 12/12 on the
  546-read subset. Citations in the test repo README.
- nf-core modules `emu/abundance` (Emu 3.6.2, Wave container) and `untar`.
- Params `--emu_db` (required; directory or .tar/.tar.gz/.tgz, local or URL) and
  `--emu_type` (default `map-ont`). Emu args: `--type <emu_type> --keep-counts --output-unclassified`.
- Emu resources overridden from `process_high` (12 CPU / 72 GB) to 8 CPU / 8 GB / 8 h
  (× attempt), from ST-001/ST-002 measurements.
- Tests: `-profile test` end-to-end (BAM → FASTQ → Emu) 144 s, result identical to manual
  run; local DB directory works; missing `--emu_db` gives a clear schema error.
  nf-test snapshot updated; Emu output md5 identical across 2 runs.
- Lint: 217 passed, 0 failed.

**Next:** Emu outputs in MultiQC / summary table; read QC + length filter (M4); DB provenance in report.

## 2026-10-08 — CI fixed; read QC and filtering (branch `m4-read-qc`)

- CI failures diagnosed via read-only GitHub token (`~/.config/ont16s/github_token`):
  test profile requested 12 GB on 7.8 GB private-repo runners; template-version job had no
  checkout permission. Fixed in PR #6; all checks green (latest-everything verified in log).
- ST-003 (`docs/server-tasks/ST-003-results.md`): length 1,000–2,000 removes 8.3 %; short
  reads are truncated amplicons with similar composition; > 2 kb reads carry spurious taxa.
- nf-core modules `chopper` (0.12.0) and `nanoplot` (1.47.0). NanoPlot before/after filter,
  stats in MultiQC. Plain single FASTQ now routed through CAT_FASTQ (gzip) because
  chopper/NanoPlot modules need `.gz`. Emu runs on filtered reads.
- Params `--min_read_length 1000`, `--max_read_length 2000`, `--min_read_qual 0`.
- Tested: BAM×1, BAM×2, plain FASTQ, gz FASTQ, FASTQ×2: 546→507 and 1,092→1,014 reads.
- nf-test snapshot updated (NanoPlot html/png and nanostat tables ignored for content);
  stable over 2 runs.

## 2026-10-08 — Combined tables and DB provenance (branch `m6-outputs`)

- PR #7 (read QC) was merged while CI was running; nf-test passed, linting failed because
  the new ST-003 doc was untracked when pre-commit ran locally (pre-commit only checks
  tracked files). Fixed on `fix/prettier-st003`. Lesson: stage new files before pre-commit.
- First local modules: `EMU_COMBINE` (`emu combine-outputs`, species + genus, abundance +
  counts) and `EMU_DB_INFO` (source, sha256, size, n sequences, n species).
- Tested: 5-sample run; provenance checksums match the test-data README; DB missing
  `taxonomy.tsv` fails with a clear message. nf-test snapshot includes combined tables and
  provenance file (stable over 2 runs).
- Open: sample column order in combined tables follows Emu's file listing (not sorted).

## 2026-10-08 — Mock-community validation (branch `m8-mock-validation`)

- PRs #8 and #9 merged after all checks were green.
- `assets/mocks/zymo_msplus.tsv`: 12 expected species with aliases; proportions `NA`
  (not published — data gap).
- `bin/mock_validation.py` (stdlib only) + local module `MOCK_VALIDATION` (Emu container).
  Recall, missing taxa, near-neighbour vs off-target unexpected taxa, false positives
  ≥ `--mock_min_abundance` (0.001), L1 distance if all proportions known.
- Checked against ST-001 manual analysis: 12/12, 1 FP (_B. halotolerans_), unexpected
  0.6 %. Fake mock: recall 2/3 and L1 = 0.4 as computed by hand.
- Bugs found and fixed while testing: `collectFile` cannot combine `keepHeader` and `seed`
  (MultiQC section moved to `assets/multiqc_config.yml`); Python csv `\r\n` line endings
  broke the joined summary; missing-definition check moved to samplesheet validation so
  it fails before any task runs.
- Limits documented: depth-dependent false positives; genus rule misses _Shigella_/_E. coli_.

## 2026-10-08 — ST-004: real environmental samples

- User asked whether the pipeline handles real samples, not only mocks. ST-004 ran the
  pipeline on 9 R10.4.1 environmental runs (PRJNA925180: soil, lake, freshwater ×3) with an
  empty `mock` column and the Emu default DB: 40/40 tasks, ~1 h 42 min, Emu ≤ 2.5 GB.
  96–98 % reads classified; replicates agree (Bray-Curtis ≤ 0.27), habitats separate
  (0.62–0.92); plausible genera. Results: `docs/server-tasks/ST-004-results.md`.
- Fix: no empty `mock_validation/` folder when there are no mock samples (branch
  `st004-real-samples`).
- PR #10 merged before CI finished; CI later passed (latest-everything verified).

## 2026-10-08/09 — ST-005 to ST-009: Etoliko sediment core; adaptive pipeline (branch `m10-adaptive`)

- ST-005: ont16s (per-sample Emu, default DB) vs published NanoCLUST/SILVA results: same
  community pattern (Mantel 0.93) but depth-dependent read loss (Emu floor 10/n; 44 % unassigned
  in shallow samples) and missing sediment phyla (DB). Input issues: duplicated reads (5 samples),
  barcode20/21 technical replicates sharing reads, R9.4.1 medaka model used on R10.4.1 fast reads.
- ST-006: pooled Emu removes most of the depth bias (unassigned 15.8 % → 3.5 %).
- ST-007: Emu prebuilt SILVA 138.2 is unusable as distributed (one taxon per sequence; 73 %
  unclassified, 16.9 GB); genus-grouped build: 32 % unclassified, 0.9 GB, detects sediment phyla.
- Implemented: `--emu_mode auto|per_sample|pooled`, duplicate-read removal (seqkit rmdup),
  `--exclude_taxa` and organelle reporting, database-fit check, run summary + warnings in
  MultiQC, genus-level SILVA builder. Bugs found by real data: Emu `*_threshold-*` outputs
  double-counting, pooled memory (34 GB), duplicate IDs.
- ST-008/009: full pipeline with defaults chose pooled automatically; with the SILVA genus DB:
  all published phyla detected, Bray-Curtis vs published median 0.13, Mantel genus 0.95, 36 min.
- User question on AI/LLM for parameter choice: answered with data-driven, logged rules inside
  the pipeline (reproducible); an LLM could explain reports outside the pipeline.

## 2026-11-08 — v0.1.0 release preparation (branch `release-v0.1.0`)

- Server cleanup (2026-11-07) archived the old repo copy and `ont16s_data` (ST-001–ST-011) to
  `gdrive:server/09_ont16s_pipeline/` and removed them from the server. Fresh clone at
  `/mnt/Ubuntu_HD5/Users/yiannis/ont16s`; tools reinstalled in `.../ont16s_tools/`.
- Merged the three commits left on `m10-adaptive` after PR #11 (pooled-mode nf-test, Zymo D6306/
  D6331 mock definitions, Etoliko method comparison).
- Fixes: `manifest.defaultBranch` 'master' → 'main' (remote runs would fail); nf-schema kept at
  2.5.1 (2.8.0 needs Nextflow >=26.04; CI tests 25.10.4, so the harmless 'validation.*' warnings stay); version 0.1.0 in manifest and
  `.nf-core.yml`; `included_configs` lint check disabled (no nf-core/configs file for ont16s).
- New: logo (`docs/images/`), README (install, test data, samplesheet, databases, parameters,
  outputs, validation, limitations), CITATIONS (all PubMed references verified), CHANGELOG v0.1.0.
- Verified from the fresh clone: `-profile test,docker` 14/14 tasks, 12/12 mock taxa; nf-test 2/2
  (per-sample and pooled) twice; lint with nf-core 4.1.0 (as CI) 0 failures, also `--release`;
  pre-commit 7/7.
- Pending: NaMeco (ST-010, download had stopped at 3/15 runs), novelty Phase A (ST-011; best-hit
  alignments in the archive) and Phase B.
