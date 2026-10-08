# ST-006 results — Pooled Emu on the Etoliko sediment core

**Status: Executed (2026-10-08, server). Not validated** (method comparison, no ground truth).

Data: `/mnt/Ubuntu_HD5/yiannis/ont16s_data/ST-006/` (not in git): `pooled.fastq.gz`,
`run_pooled.sh`, `emu_pooled/`, `split/`, `logs/compare_pooled.txt`.

## Question

ST-005 showed that Emu run per sample leaves many reads unassigned in shallow samples
(median 44 % below 3,000 reads), because of its per-run abundance floor `10/n`. Does running
Emu once on all samples pooled, then splitting per sample, remove this depth dependence?

## Method

- The same filtered reads as ST-005 (chopper output of all 70 samples), read IDs prefixed with
  the sample name, concatenated: 586,751 reads.
- Emu 3.6.2, Emu default DB, `--threads 24 --keep-counts --keep-read-assignments
--output-unclassified`; per-sample tables rebuilt from per-read assignment probabilities
  (`bin/emu_split_pooled.py`).
- Compared with the published NanoCLUST/SILVA results with the same scripts as ST-005.

## Run

1 h 52 min wall time; peak memory **34 GB** (alignment ~65 min on ~19 cores, then a
single-core assignment phase); 8 GB alignment SAM, 1.7 GB read-assignment table.
Emu: 568,196 mapped, 7,210 unmapped, 2,074 mapped but unclassified.

## Results (pooled vs per-sample ST-005 vs published)

| Metric                                            | Per sample  | Pooled      | Published |
| ------------------------------------------------- | ----------- | ----------- | --------- |
| Unassigned, overall                               | 15.8 %      | 3.5 %       | 19.8 %    |
| Unassigned, samples < 3,000 reads (median)        | 44.2 %      | 7.0 %       | 21.9 %    |
| Unassigned, samples ≥ 10,000 reads (median)       | 11.3 %      | 0.7 %       | 23.6 %    |
| r(log10 reads, unassigned)                        | −0.63       | −0.18       | —         |
| Mantel vs published, phylum                       | 0.91        | 0.96        | —         |
| Mantel vs published, genus                        | 0.89        | 0.92        | —         |
| Bray-Curtis vs published per sample, median (max) | 0.19 (0.47) | 0.18 (0.32) | —         |
| Technical replicates barcode20/21, phylum BC      | 0.015       | 0.012       | —         |

Phyla absent from the Emu default DB (Atribacterota, Zixibacteria, WS1, Sva0485, … ≈ 7 % in
published) remain undetected: pooling fixes the depth bias, not database coverage.

## Issues found (fixed in branch `m10-adaptive`)

1. **Duplicate reads in the input:** 11,345 reads occur twice with identical ID and sequence in
   5 samples (barcode50 3,457; barcode18 3,307; barcode64 2,310; barcode24 1,455; barcode16 816
   after length filtering). barcode24 and barcode50 are entirely duplicated. Emu collapses
   duplicate IDs silently; the pipeline now removes them with `seqkit rmdup --by-name` and
   reports them.
2. **Emu threshold outputs:** with > ~100 k reads, Emu also writes `*_threshold-0.0001*` files
   that repeat unclassified reads; the split script now ignores them.
3. **Memory:** 34 GB for 586 k reads; pooled Emu default raised to 48 GB.

## Interpretation

Pooling removes most of the depth-dependent loss of reads and brings the results closer to the
published analysis (which pools reads before clustering). `--emu_mode auto` selects pooling for
data like this (most samples < 10,000 reads).
