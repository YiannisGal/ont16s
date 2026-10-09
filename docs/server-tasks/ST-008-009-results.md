# ST-008 / ST-009 results — Full adaptive pipeline on the Etoliko sediment core

**Status: Executed (2026-10-08/09, server). Not validated** (comparison with the published
NanoCLUST/SILVA analysis; no ground truth).

Data: `/mnt/Ubuntu_HD5/yiannis/ont16s_data/ST-008/`, `ST-009/` (not in git): samplesheet,
`server.config` (24 CPUs), `results/`, `logs/compare.txt`.

## Runs

Pipeline commit `bbe1e03` (branch `m10-adaptive`), **all defaults** except `--emu_db`:

|                                                             | ST-008                                                                 | ST-009                                                                                                   |
| ----------------------------------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `--emu_db`                                                  | Emu default (`emu.tar`)                                                | SILVA 138.2 grouped by genus (`bin/build_silva_genus_db.py`, max 20 seqs/genus; 5,128 taxa, 79,494 seqs) |
| Tasks                                                       | 429, 0 failed                                                          | 428, 0 failed                                                                                            |
| Wall time                                                   | ~2 h                                                                   | ~36 min                                                                                                  |
| Emu mode chosen (`auto`)                                    | pooled: "50 of 70 samples have < 10000 filtered reads (fraction 0.71)" | same                                                                                                     |
| Warnings                                                    | duplicate_reads 5, filter_loss 36, low_depth 2, unassigned 1           | same                                                                                                     |
| Mean unassigned                                             | 3.4 %                                                                  | 2.8 %                                                                                                    |
| Database fit (median best-hit identity, min–max of samples) | 0.80 (0.77–0.88)                                                       | 0.85 (0.84–0.88)                                                                                         |

## Comparison with published results (Results_new, SILVA 138.2, 95 %)

ST-009 phylum and genus names are SILVA on both sides (no name mapping needed); ST-008 uses the
SILVA↔NCBI map from ST-005.

| Metric                                                            | ST-008                                                     | ST-009           |
| ----------------------------------------------------------------- | ---------------------------------------------------------- | ---------------- |
| Phyla > 0.1 % only in published                                   | 15 (Atribacterota 2.1 %, Zixibacteria 1.4 %, WS1 1.0 %, …) | none             |
| Bray-Curtis vs published per sample, median (range)               | 0.18 (0.02–0.32)                                           | 0.13 (0.02–0.26) |
| Mantel vs published, phylum / genus                               | 0.96 / 0.92                                                | 0.96 / 0.95      |
| Published resolved-genus abundance in genera also found (median)  | 79.1 %                                                     | 99.5 %           |
| ont16s resolved-genus abundance in genera also published (median) | 37.4 %                                                     | 80.0 %           |
| Reads without a resolved genus (published 53.0 %)                 | 5.1 %                                                      | 50.9 %           |
| Dissimilarity vs depth difference (published r = 0.21)            | 0.22                                                       | 0.24             |
| Technical replicates barcode20/21, genus BC                       | 0.058                                                      | 0.027            |
| Unassigned, samples < 3,000 reads (median)                        | 6.3 %                                                      | 5.5 %            |

Depth trends (Spearman ρ, published / ST-009): Cyanobacteria −0.40 / −0.43, Bipolaricaulota
0.39 / 0.44, Acidobacteria 0.27 / 0.32, Bacteroidetes 0.32 / 0.29, Firmicutes −0.12 / −0.18.

## Interpretation

- With pooling (chosen automatically) and an environment-appropriate database, ont16s reproduces
  the published community structure closely, detects all published phyla, and runs in ~36 min.
- Unassigned fractions are not comparable between methods: the published BLAST step rejects
  hits below 95 % identity (19.8 % unassigned), Emu assigns every mapped read to its closest
  reference. Genus resolution, however, is similar (≈ 51–53 % without a resolved genus).
- The default Emu database still works for community patterns but misses sediment candidate
  phyla and forces reads onto cultured genera; the database-fit check reflects this (0.80 vs 0.85).
- Open: ST-008 shows a stronger residual depth correlation of unassigned reads than ST-006
  (r = −0.47 vs −0.18, at small absolute values); not yet explained.
