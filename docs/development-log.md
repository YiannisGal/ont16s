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

**Next:** clone repo on server; run Emu manually on one Zymo SUP chunk, before any Nextflow.
