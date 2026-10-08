# ST-003 results — Read length/quality filter defaults

**Status: Executed (2026-10-08, server). Not validated.** One Zymo MSPlus chunk; used to set
provisional defaults for `--min_read_length`, `--max_read_length`, `--min_read_qual`.

Data: ST-001 full chunk (53,011 reads, R10.4.1 SUP). Files in
`/mnt/Ubuntu_HD5/yiannis/ont16s_data/ST-003/` (`chopper_thresholds.txt`, `length_bins.txt`,
`by_length.py`, `by_length.txt`).

## Reads kept by chopper 0.12.0 (`community.wave.seqera.io/library/chopper:0.12.0b--f39108dd84394289`)

| Filter                      | Reads kept | Removed |
| --------------------------- | ---------- | ------- |
| none                        | 53,011     | 0       |
| length 1,000–2,000          | 48,596     | 8.3 %   |
| length 1,200–1,800          | 46,223     | 12.8 %  |
| mean Q ≥ 10                 | 51,563     | 2.7 %   |
| mean Q ≥ 15                 | 42,346     | 20.1 %  |
| length 1,000–2,000 + Q ≥ 10 | 47,427     | 10.5 %  |

## Length distribution

| Length (bp) | Reads           |
| ----------- | --------------- |
| < 500       | 619             |
| 500–999     | 3,271           |
| 1,000–1,199 | 2,352           |
| 1,200–1,399 | 1,265           |
| 1,400–1,499 | 528             |
| 1,500–1,699 | 44,404 (83.8 %) |
| 1,700–1,999 | 47              |
| 2,000–3,499 | 518             |
| ≥ 3,500     | 7               |

## Species composition by length (from ST-001 Emu per-read assignments, default DB)

Share of each length bin's reads (Emu posterior-weighted), taxa > 0.5 % in any bin:

| Species                       | < 1,000 | 1,000–1,499 | 1,500–2,000 | > 2,000 |
| ----------------------------- | ------- | ----------- | ----------- | ------- |
| (reads)                       | 3,862   | 4,132       | 44,425      | 523     |
| Bacillus subtilis             | 19.31   | 16.72       | 16.06       | 21.05   |
| Staphylococcus aureus         | 13.59   | 17.52       | 14.18       | 17.59   |
| Listeria monocytogenes        | 16.78   | 16.55       | 13.68       | 11.85   |
| Limosilactobacillus fermentum | 12.25   | 12.56       | 13.36       | 11.09   |
| Enterococcus faecalis         | 10.93   | 11.40       | 9.04        | 4.78    |
| Gardnerella vaginalis         | 6.93    | 5.81        | 8.68        | 15.30   |
| Bifidobacterium adolescentis  | 5.86    | 4.93        | 6.36        | 12.81   |
| Salmonella enterica           | 5.19    | 4.09        | 5.52        | 0.76    |
| Escherichia coli              | 3.59    | 4.39        | 5.19        | 0.38    |
| Borreliella burgdorferi       | 1.47    | 1.65        | 2.79        | 0.76    |
| Pseudomonas aeruginosa        | 2.36    | 2.25        | 2.55        | 0.57    |
| Chlamydia trachomatis         | 1.19    | 0.99        | 2.07        | 0.00    |
| Listeria ivanovii             | 0.00    | 0.10        | 0.03        | 0.75    |
| Laceyella sacchari            | 0.13    | 0.17        | 0.02        | 1.72    |

(Read IDs from the unfiltered FASTQ; a few reads without assignment are not counted.)

## Interpretation

- Short reads (< 1,000 bp, 7.3 %) contain all 12 taxa in broadly similar proportions
  (Gram-positives somewhat higher, Gram-negatives lower): truncated amplicons, not a
  different community. Removing them changes overall abundances by roughly ≤ 0.2
  percentage points per taxon.
- Long reads (> 2,000 bp, 1 %) are compositionally distorted and carry most of the
  _Laceyella sacchari_ signal (1.72 % vs 0.02 % in full-length reads): likely
  chimeras/concatemers producing spurious taxa.
- **Defaults chosen:** `--min_read_length 1000`, `--max_read_length 2000`,
  `--min_read_qual 0` (quality filter off: effect on profiles not measured yet).
- To evaluate in Milestone 8: Q filter, tighter windows (e.g. 1,200–1,800), and whether
  length filtering improves mock accuracy (needs expected proportions).
