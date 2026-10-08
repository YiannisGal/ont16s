# Project landscape and feasibility (Milestone 0)

Assessed: 2026-10-06. Status: **research only — nothing executed.**
Re-check this landscape before each release; it changes quickly.

## 1. Existing tools and workflows

| Project                                     | State (as of 2026-10-06)                                                                                                                                                                                                                                                                                     | Relevance                                                                    |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| nf-core/ampliseq                            | Latest release 2.18.0 (2026-06-17), no ONT support. `dev` (future 3.0.0) adds ONT R10.4 via `--sequencing_type nanopore`: Porechop_ABI → Chopper 0.12.0b → Cutadapt → **Savont 0.7.0** ASVs → standard classifiers (DADA2, SINTAX, Kraken2, QIIME2, VSEARCH). No Emu. Emu request (issue #741, 2024) closed. | ONT ASV route will be covered upstream. Do not duplicate Savont.             |
| Savont                                      | Long-read ASV caller for ONT R10.4 (SUP preferred) and PacBio HiFi; ≥98 % read-quality filter; chimera removal. Bioconda.                                                                                                                                                                                    | Optional/deferred comparison route only.                                     |
| Emu                                         | v3.6.2 (2026-02-26). v3.6.0 added identity / alignment-length filters; v3.5.5 validates custom DB tax IDs. nf-core module `emu/abundance` exists.                                                                                                                                                            | Primary profiler. Default DB (rrnDB + NCBI 16S RefSeq) is clinically biased. |
| TRANA (ex gms_16S, Genomic Medicine Sweden) | Nextflow, Emu-centred: FastQC, NanoPlot, Porechop_ABI, Filtlong, Emu, Krona, MultiQC; nf-test; tested on M1. v1.0.0 (2026-05-05), v1.1.0 (2026-09-16).                                                                                                                                                       | **Direct competitor.** A plain "Emu in Nextflow" pipeline is not novel.      |
| EPI2ME wf-16s (ONT)                         | Nextflow, v1.6.x. minimap2 or Kraken2+Bracken; NCBI / SILVA 138.1 / Greengenes2 DBs; BAM or FASTQ input.                                                                                                                                                                                                     | Vendor baseline for comparison.                                              |
| NaMeco, NanoASV, NanoCLUST                  | Clustering/ASV alternatives.                                                                                                                                                                                                                                                                                 | Context only.                                                                |

### Published comparison (to verify, not to trust)

Ota et al., _Comparative evaluation of analytical pipelines for Illumina short- and
Nanopore long-read 16S rRNA gene amplicon sequencing with mock microbial communities_,
reported (via secondary summaries) EPI2ME misclassifying ~39.5 % and leaving ~25.5 %
unclassified at species level, with Emu detecting all mock taxa.
**Not yet verified:** flow-cell chemistry, EPI2ME workflow version, databases used.
If R9.4.1 / legacy EPI2ME, these numbers may not apply to R10.4.1 + current wf-16s.

## 2. Positioning (see decision D-001)

ont16s is **a validation- and database-aware Emu profiling pipeline for environmental
ONT full-length 16S**. Its value over existing tools is:

1. Built-in mock-community validation (expected composition → metrics).
2. Database provenance as a first-class feature (versioned, checksummed, environmental DBs).
3. Same-reads comparison of methods/databases (Emu primary; baselines later).
4. A reproducible public benchmark on current R10.4.1 HAC/SUP data.

If validation and database work are dropped, ont16s duplicates TRANA. Upstream
contribution (Emu route in ampliseq, or validation module to TRANA) remains an option.

## 3. Datasets (verified against ENA / ONT metadata)

| Dataset                               | Content                                                                                                                                                                               | Role                                                                                                                                                  |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `s3://ont-open-data/zymo_16s_2025.09` | R10.4.1, SQK-MAB114.24, Dorado v1.1.1, HAC + SUP v5.2.0. Zymo DNA standard + 4 spiked species (3 bio reps); Zymo Gut Microbiome Standard (2 bio reps); 2 flow cells each. BAM 5.1 GB. | Development (subsampled), CI test data (tiny subset), primary validation, replicate CV, HAC vs SUP.                                                   |
| ENA PRJEB82315 (NaMeco)               | 30 MinION runs: Zymo D6306 ×5, D6331 ×12, chicken feces / crop digesta ×13. ~9.5 M reads, mean ~1.5 kb.                                                                               | Independent lab/protocol validation. **Same Zymo standards — not biologically independent.** Animal, not environmental.                               |
| ENA PRJNA925180                       | Same samples on NovaSeq (18), PacBio Sequel II (18), PromethION (36; R9.4.1 + R10.4.1): Zymo D6305, a synthetic community, soil / freshwater / lake. ~42–59 k reads per ONT run.      | Second (non-Zymo) mock + environmental demonstration + cross-platform reference. **Separate R9 and R10 runs.** Linked publication not yet identified. |
| UniquELT                              | Not available.                                                                                                                                                                        | Not used until verified.                                                                                                                              |

Rule: thresholds are chosen on Zymo development data and **not re-tuned** on later datasets.

## 4. Compute classification (M1 MacBook Air)

- 🟢 Scaffold, lint, nf-test on tiny data, Emu on 10–50 k-read subsets, metric scripts, docs.
- 🟡 Full Zymo download, single full-sample Emu run, PRJNA925180 ONT runs.
- 🔴 Full Zymo × HAC/SUP × databases, custom DB builds (GTDB/SILVA/MiDAS), full NaMeco, repeated benchmarks.
- Containers: assume amd64-only until checked; expect Rosetta or conda fallbacks.

## 5. Risk register

| Risk                                                                        | Impact                              | Mitigation                                               |
| --------------------------------------------------------------------------- | ----------------------------------- | -------------------------------------------------------- |
| Overlap with TRANA                                                          | Project redundant                   | Keep validation + DB provenance central                  |
| ampliseq adds Emu                                                           | Niche shrinks                       | Monitor; consider upstream contribution                  |
| DB effects dominate method effects                                          | Confounded conclusions              | Treat DB as explicit experimental factor                 |
| Mocks are Zymo/gut-like                                                     | Validation ≠ environmental accuracy | State limitation; use PRJNA925180 synthetic mock         |
| Ground truth is genomic/cell-based, not 16S copies                          | Biased abundance error              | Copy-number-aware comparison                             |
| Emu detection floor (~10 reads) + read redistribution to abundant relatives | Rare taxa lost or absorbed          | Report limit of detection via depth subsampling on D6331 |
| ARM64 container gaps                                                        | Local friction                      | Check each image; server for heavy work                  |
| Schedule                                                                    | Rushed validation                   | Validation takes priority over calendar                  |

## Sources

- https://github.com/nf-core/ampliseq/releases
- https://github.com/nf-core/ampliseq/blob/dev/CHANGELOG.md
- https://nf-co.re/ampliseq/dev/docs/usage
- https://github.com/nf-core/ampliseq/issues/741
- https://anaconda.org/bioconda/savont
- https://github.com/treangenlab/emu/releases
- https://github.com/nf-core/modules/tree/master/modules/nf-core/emu
- https://github.com/genomic-medicine-sweden/gms_16S (TRANA)
- https://github.com/epi2me-labs/wf-16s
- https://epi2me.nanoporetech.com/zymo_16s_2025.09/
- https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12817509/ (NaMeco)
- ENA portal API filereports for PRJEB82315 and PRJNA925180
- https://fra.repo.nii.ac.jp/record/2002143/files/Ota%20et%20al%20Comparative%20evaluation%20of%20analytical%20pipelines.pdf
- https://www.biorxiv.org/content/10.1101/2021.05.02.442339v1.full.pdf (Emu)
