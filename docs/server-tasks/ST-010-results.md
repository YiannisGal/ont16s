# ST-010 results — NaMeco independent mock validation (PRJEB82315)

**Executed:** 2026-11-20, lab server, ont16s v0.2.0dev (branch `release-v0.2.0`, commit d9336ce),
`-profile docker`, Emu default database (`ont16s_runs/data/emu_db`).
**Status:** pipeline completed, 126 tasks, 0 failed.

## Input

- ENA PRJEB82315 (NaMeco, an independent laboratory), ONT full-length 16S.
- 5 × ZymoBIOMICS D6306 (C1S–C5S; 8 bacteria, even 16S composition).
- 10 × ZymoBIOMICS D6331 gut standard (zymogut01–10; staggered composition, 0.0002–17.6 %).
- Each run was subsampled to 50 000 reads (`seqkit sample -s 11`). The full depth (~300 k reads per
  sample) was too slow on the shared server. Data are on the data disk, not in git.

## Mock validation (taxa ≥ 0.1 % counted as detected)

| Mock         | n   | Recall           | Bray-Curtis         | mean abs log2 ratio | Abundance on unexpected taxa |
| ------------ | --- | ---------------- | ------------------- | ------------------- | ---------------------------- |
| D6306 (even) | 5   | 1.00 (all 8/8)   | 0.086 (0.072–0.108) | 0.40 (0.34–0.47)    | 0.8 % (0.6–1.5 %)            |
| D6331 (gut)  | 10  | 0.65 (0.53–0.73) | 0.477 (0.428–0.508) | 1.66 (1.21–2.35)    | 24.5 % (17.9–31.2 %)         |

**D6306:** all expected species are found in every replicate. The largest deviation is
_Pseudomonas aeruginosa_, which is under-estimated by 2–5× in each sample. Off-target taxa
amount to 2–3 per sample, together < 1.5 %.

**D6331:** the poor numbers have identifiable causes; they are not random error:

1. _Veillonella rogosae_ (15.9 % expected) is reported as _V. parvula_ (≈17 %). Its 16S gene is
   nearly identical to the database's _V. parvula_, so the genus is right and the species name is
   wrong. This single taxon accounts for most of the "unexpected" abundance.
2. _Bifidobacterium adolescentis_ (8.8 %) and the archaeon _Methanobrevibacter smithii_ (0.07 %)
   get no reads at all. This is consistent with primer bias: the bacterial 27F primer has known
   mismatches to Bifidobacterium, and bacterial primers amplify archaea poorly. This is a
   hypothesis; the primers were not checked against these genomes.
3. _Enterococcus faecalis_ (0.0009 %) and _Clostridium perfringens_ (0.0002 %) are below what
   50 k reads can detect (≥ 1 read in 50 000 = 0.002 %).
4. _Bacteroides fragilis_, _Prevotella corporis_ and _Akkermansia_ are under-estimated
   8–10× (log2 ≈ −3.0 to −4.0), while _E. coli_ and _Limosilactobacillus_ are over-estimated about 2×.
   This is the expected pattern of amplification and 16S copy-number bias in the wet lab.
   Emu cannot correct it.

Conclusion: the pipeline recovers an even mock from an independent laboratory with high
accuracy (BC 0.09). On a staggered gut mock, the error is dominated by the amplicon (primers,
copy number) and by species that are 16S-identical. Neither is fixable by the profiler. Results at
genus rank are more reliable than species names for close relatives (_Veillonella_).

## Novelty analysis (calibration — all taxa in these mocks are in the database)

- Reads scored as below genus rank (false novel): **0.4–3.3 % per sample** (median 1.1 %), all at
  family rank; none at order or deeper. The highest values are in D6331 replicates with more
  chimeras and unaligned reads (up to 3.3 %).
- Median read accuracy from Q scores: 0.89–0.91. Raw identity to the best hit: 0.91–0.93. Raw
  identity exceeds the Q-score accuracy, so the Q scores of these reads are conservative and the
  adjusted identity saturates at 1.0.
- **Consensus OTUs:** 7 476 candidate novel reads were pooled from the 15 samples and gave
  **0 clusters with ≥ 10 reads** at 90 % identity. The reads that look novel in mocks are
  scattered noise (errors, chimeras), not a lineage. The consensus step therefore removes the
  false-novel signal of the read-level analysis completely.

**Practical threshold:** a sample-level `frac_novel_genus` up to ~3–4 % is within what known
organisms produce. Values well above that, or any consensus OTU, indicate real novelty.

## Resources

About 6.5 h wall time (12:49–19:15) for 15 × 50 k reads. The server was shared, so only about 22 of 28 CPUs were
available. Emu dominated the runtime.
