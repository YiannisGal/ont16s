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
- MSPlus = Zymo DNA standard + gDNA of *B. adolescentis*, *B. burgdorferi*,
  *C. trachomatis*, *G. vaginalis*. **Expected proportions not published.** Must be sourced
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
  20k subsample (*Borrelia* reported as *Borreliella*); they make up ~99.4 % of abundance.
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
reads unmapped and shifts *Bacillus* assignments. Keep `map-ont` default; expose `--type`
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
