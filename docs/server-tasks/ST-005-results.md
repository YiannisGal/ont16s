# ST-005 results — Etoliko lake sediment core: ont16s vs published NanoCLUST/SILVA analysis

**Status: Executed (2026-10-08, server). Not validated** (no ground truth; method comparison only).

Data and scripts: `/mnt/Ubuntu_HD5/yiannis/ont16s_data/ST-005/` (not in git): `samplesheet.csv`,
`server.config` (24 CPUs), `phylum_map.tsv`, `compare.py`, `extra.py`, `compare_out/`, `logs/`.
Input data stay in the user's directory (`~/Documents/Etoliko_new/`, unpublished; not copied).

## Data

- 70 samples (barcodes) from a sediment core, 14 depth intervals (0–70 cm); metadata
  `Metadata_minion.tsv`.
- R10.4.1, basecalled with **fast** model `dna_r10.4.1_e8.2_400bps_fast@v3` (run 2023-04-10);
  mean read quality ~9.2.
- Input `input_fq2/` (2.0 M reads). Checks:
  - The published run used `input_fq2` (porechop output = input_fq2 × 1.00–1.06 for all
    discordant samples; read IDs match). `input_fq/` is an older version that differs in 9
    samples (up to 900×) and was not used.
  - barcode20 and barcode21 share 11,174 of 22,306 reads: **technical replicates** (user).
  - Several deep-sequenced samples are mostly short fragments (barcode16, barcode18: median
    ~330 bp; ~5 % reads ≥ 1 kb).

## Methods compared

|             | Published (Results_new, taxonomy_blast_138_2_95)                                                                                                         | ont16s (commit 5559f18, defaults)                         |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Trim/filter | porechop; NanoFilt 1,000–1,800 bp, -q minQc                                                                                                              | chopper 1,000–2,000 bp, no Q filter                       |
| Unit        | UMAP+HDBSCAN clusters of **pooled** reads (min 50), canu/racon/medaka consensus (medaka model `r941_min_high_g303` — R9.4.1 model on R10.4.1 fast reads) | each read, per sample                                     |
| Taxonomy    | BLAST vs SILVA 138.2 (99 %), 95 % identity, QIIME 2 consensus                                                                                            | Emu 3.6.2, Emu default DB (rrnDB + NCBI 16S RefSeq, 2020) |
| Reads used  | 490,635 (in clusters)                                                                                                                                    | 575,406 (after filter)                                    |

Phylum names harmonised with an explicit map (`phylum_map.tsv`, 36 entries, e.g.
Bacillota→Firmicutes, Thermodesulfobacteriota/Myxococcota/Campylobacterota→Proteobacteria
s.l., Acetothermia↔Candidatus Bipolaricaulota). Genera compared by exact name; placeholders
(Incertae_Sedis, uncultured, names with digits/lineage/clade) count as unresolved.

## Results

**Run:** 354 tasks, 0 failed, ~2 h 15 min on 24 CPUs.

**1. Unassigned reads:** published 19.8 %, ont16s 15.8 % overall — but ont16s depends strongly
on per-sample depth (r = −0.63 with log10 reads), published does not:

| ont16s reads after filter | n   | ont16s unassigned (median) | published unassigned (median) |
| ------------------------- | --- | -------------------------- | ----------------------------- |
| < 3,000                   | 20  | 44.2 %                     | 21.8 %                        |
| 3,000–6,000               | 19  | 30.1 %                     | 21.6 %                        |
| 6,000–10,000              | 11  | 20.1 %                     | 18.5 %                        |
| ≥ 10,000                  | 20  | 11.3 %                     | 23.6 %                        |

Cause (Emu 3.6.2 source): per-sample abundance floor `10/n_reads` (n > 1,000) — taxa below it
are removed and their reads become `mapped_unclassified`. Diverse sediments with few reads lose
most rare taxa. The published method pools all samples before clustering, avoiding this.
Filtered reads per sample: min 127, median 5,368, max 49,111.

**2. Phylum composition** (mean of samples, assigned reads):

| Phylum (harmonised)            | Published | ont16s |
| ------------------------------ | --------- | ------ |
| Firmicutes                     | 35.8 %    | 36.2 % |
| Proteobacteria s.l.            | 17.4 %    | 20.3 % |
| Chloroflexi                    | 11.3 %    | 14.3 % |
| Planctomycetes                 | 7.7 %     | 10.9 % |
| Acidobacteria                  | 4.8 %     | 3.1 %  |
| Bacteroidetes                  | 3.9 %     | 2.8 %  |
| Bipolaricaulota (Acetothermia) | 3.1 %     | 1.6 %  |
| Spirochaetes                   | 1.8 %     | 2.5 %  |
| Cyanobacteria                  | 2.1 %     | 1.5 %  |
| Actinobacteria                 | 2.1 %     | 1.4 %  |

Only in published (absent from Emu DB): Atribacterota 2.1 %, Zixibacteria 1.4 %, WS1 1.0 %,
Sva0485 0.9 %, Dependentiae 0.5 %, Aerophobota 0.4 % and smaller candidate phyla.
Only in ont16s: no phylum in DB 2.5 % (e.g. Candidatus Babela), Kiritimatiellaeota 0.5 %.
Per-sample Bray-Curtis published vs ont16s: median 0.19 (0.02–0.47).

Depth trends (Spearman ρ with depth) agree, e.g. Cyanobacteria −0.40 / −0.40,
Bipolaricaulota 0.39 / 0.39, Acidobacteria 0.27 / 0.27, Planctomycetes 0.18 / 0.17.

**3. Genus level:** reads without a resolved genus: published 53.0 % (SILVA placeholders),
ont16s 19.0 % (Emu forces reads onto named cultured genera). Overlap of resolved-genus
abundance with genera found by the other method (same sample): published 60.5 %, ont16s
41.5 % (medians). Top genera shared: Mesobacillus (16.8 / 14.5 %), Desulfatiglans
(11.9 / 7.9 %); differing: Aminicenans (published 9.7 %, not in Emu DB) vs Dehalococcoides,
Anaerohalosphaera, Dehalogenimonas (ont16s; likely nearest cultured relatives of uncultured
Chloroflexi/Planctomycetes).

**4. Ecological pattern:** Mantel (Bray-Curtis, 999 permutations) published vs ont16s:
phylum r = 0.93, genus r = 0.89 (p = 0.001). Dissimilarity vs depth difference: published
r = 0.21, ont16s r = 0.20 (p = 0.001).

**5. Technical replicates** barcode20 vs barcode21 (ont16s): Bray-Curtis phylum 0.015,
genus 0.057, species 0.075.

## Interpretation

- Community-level conclusions (between-sample pattern, depth structure, dominant phyla) are
  reproduced by ont16s with a completely different method and database.
- Problems for this kind of data (diverse sediment, fast basecalling, uneven shallow depth):
  1. Emu's per-sample floor discards up to ~44 % of reads in shallow samples (depth-dependent bias).
  2. The 2020 NCBI-based Emu DB lacks candidate phyla common in sediments; their reads are
     missing or forced onto cultured relatives (species/genus names unreliable).
- Proposed adjustments: pooled Emu mode (shared floor across samples), environmental Emu DB
  (SILVA/GTDB), unassigned fraction reported prominently.
