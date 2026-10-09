# ST-004 results — Real environmental samples (PRJNA925180, R10.4.1)

**Status: Executed (2026-10-08, server). Not validated.** Demonstrates that the pipeline runs on
real (non-mock) samples; there is no ground truth, so only plausibility can be judged.

Data and logs: `/mnt/Ubuntu_HD5/yiannis/ont16s_data/ST-004/` (not in git): `runs.tsv`,
`samplesheet.csv`, `server.config`, `analyse.py`, `logs/` (run log, md5 checks, read stats,
Nextflow report/timeline, `analysis.txt`), `results/`.

## Setup

- ENA PRJNA925180, the 9 ONT **R10.4.1** environmental runs (sample alias `*_ontR10.4.1_*`):
  soil (HS), lake water (NW), freshwater (YW), 3 replicates each. Downloaded from ENA, all
  9 MD5 checksums OK (526 MB).
- Samplesheet with **empty `mock` column** (as a user with real samples would write it).
- Pipeline commit `5559f18` (`dev`), `-profile docker`, `--emu_db` = Emu default `emu.tar`
  (OSF `56uf7`), default filters (1,000–2,000 bp, no Q filter).
- Local executor capped at 16 CPUs (`server.config`) to leave capacity for other users.

## Run

40 tasks, 0 failed, ~1 h 42 min wall time.

| Step                   | Per sample                                  |
| ---------------------- | ------------------------------------------- |
| NanoPlot raw           | ~8 s, 0.33 GB                               |
| chopper                | ~13 s, 0.16 GB                              |
| Emu (8 CPUs requested) | 19–26 min, ~7.3 cores used, 1.8–2.5 GB peak |

Emu was ~2.5× faster per read than on the Zymo chunk (ST-001: 50 min / 53 k reads).
Hypothesis (not tested): fewer near-identical database relatives per read → fewer
minimap2 alignments.

## Reads

| Sample             | ENA run     | Raw    | Kept by filter | Classified | Unclassified (mapped) | Species |
| ------------------ | ----------- | ------ | -------------- | ---------- | --------------------- | ------- |
| freshwater_YW_rep1 | SRR23176505 | 55,588 | 100 %          | 53,505     | 2,082                 | 692     |
| freshwater_YW_rep2 | SRR23176504 | 56,032 | 100 %          | 53,413     | 2,619                 | 766     |
| freshwater_YW_rep3 | SRR23176503 | 54,658 | 100 %          | 52,142     | 2,516                 | 759     |
| lake_NW_rep1       | SRR23176501 | 55,660 | 100 %          | 54,350     | 1,309                 | 415     |
| lake_NW_rep2       | SRR23176500 | 56,214 | 100 %          | 55,023     | 1,190                 | 367     |
| lake_NW_rep3       | SRR23176499 | 56,055 | 100 %          | 54,706     | 1,348                 | 424     |
| soil_HS_rep1       | SRR23176498 | 57,610 | 100 %          | 55,458     | 2,152                 | 563     |
| soil_HS_rep2       | SRR23176497 | 58,783 | 100 %          | 56,678     | 2,105                 | 570     |
| soil_HS_rep3       | SRR23176496 | 56,464 | 100 %          | 54,382     | 2,082                 | 552     |

Median read length 1,442–1,453 bp, max ≤ 1,646 bp (Zymo: 1,578 bp, long tail): different
primers/trimming; reads appear pre-filtered by the submitters, so the length filter removed
nothing. Unmapped reads: 0–1 per sample.

## Replicates and habitats

Bray-Curtis dissimilarity on species abundances: within soil 0.08–0.09, within lake
0.11–0.22, within freshwater 0.19–0.27; between habitats 0.62–0.92. Replicates agree and
habitats separate clearly.

Top genera (mean of 3 replicates):

| Soil            | %    | Lake           | %    | Freshwater        | %   |
| --------------- | ---- | -------------- | ---- | ----------------- | --- |
| Pseudoduganella | 18.7 | Hydrogenophaga | 11.5 | (unknown genus)   | 5.4 |
| Massilia        | 13.1 | Curvibacter    | 6.8  | Curvibacter       | 4.8 |
| Vicinamibacter  | 4.4  | Microcystis    | 5.8  | Hydrogenophaga    | 4.6 |
| (unknown genus) | 3.3  | Acidovorax     | 5.1  | Ca. Nanopelagicus | 4.2 |
| Lysobacter      | 3.0  | Roseomonas     | 5.0  | Ilumatobacter     | 3.1 |
| Ramlibacter     | 2.3  | Pseudobacter   | 4.3  | Ca. Fonsibacter   | 2.5 |
| Gemmatirosa     | 2.1  | Rhodobacter    | 4.1  | Synechococcus     | 2.2 |
| Cupriavidus     | 1.8  | Ramlibacter    | 3.2  | Acidovorax        | 2.0 |

Plausible for the habitats (soil Oxalobacteraceae/Acidobacteria; lake bloom-forming
_Microcystis_; typical freshwater lineages _Ca._ Nanopelagicus, _Ca._ Fonsibacter,
_Synechococcus_). Not verified against the original study.

## Caveats

- Emu assigns each read to the closest species **in the database** (2020 rrnDB + RefSeq,
  mostly cultured taxa). High classification rates (96–98 %) do not mean correct species;
  uncultured environmental lineages are forced onto the nearest reference. Genus-level
  summaries are safer for environmental samples.
- Species counts per sample (367–766) include many taxa near Emu's detection floor.

## Issues found

- Empty `results/mock_validation/` folder for runs without mock samples (`collectFile`
  `storeDir`). Fixed on branch `st004-real-samples`.

## Open questions

- Compare with the original study's results (publication still unidentified).
- Test an environmental database (e.g. SILVA- or GTDB-based Emu DB) via `--emu_db`.
- Same habitats were also sequenced on R9.4.1, PacBio and Illumina: cross-platform check.
