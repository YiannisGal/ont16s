# ST-012 / ST-013 results — novel OTUs on low-accuracy reads; D6331 at full depth

**Executed:** 2026-11-20/21, lab server, `-profile docker`, Emu default database.
ST-013 was first run with v0.2.0 (86 tasks), then resumed with the v0.3.0 code (`feat/v0.3.0`).

## ST-013 — NaMeco D6331 gut mock, full depth (PRJEB82315, 10 replicates)

263 000–359 000 classified reads per sample (mean 300 000), instead of the 50 000-read subsample of ST-010.

| Metric                           | 50 k reads (ST-010) | Full depth (ST-013)     |
| -------------------------------- | ------------------- | ----------------------- |
| Species recall (all 15)          | 0.65                | 0.75 (0.73–0.80)        |
| Recall of detectable taxa        | –                   | 0.85 (0.85–0.86)        |
| Bray-Curtis, species             | 0.48                | 0.48 (0.43–0.51)        |
| Bray-Curtis, genus               | –                   | **0.32 (0.27–0.35)**    |
| Novel consensus OTUs (all false) | 0                   | 94 → **0** after filter |

Status of the expected taxa that are not detected:

- _Bifidobacterium adolescentis_ (8.8 %) and _Methanobrevibacter smithii_: `not_amplified`. In the raw
  reads there are almost no reads near these genera (zymogut04: 1 and 0 reads). The organisms are
  absent from the amplicon, so no profiler can report them.
- _Clostridium perfringens_ (0.0002 %): `below_detection_limit` (< 1 read expected at 300 k reads).
- _Enterococcus faecalis_ (0.0009 %): `below_detection_limit` (≈ 2.7 expected reads) in 8 replicates; detected in 2 (zymogut02, zymogut09).
- 0 taxa are `missed`, i.e. not explained by the amplicon or by depth.

_Veillonella rogosae_ is reported as _V. parvula_ (16S-identical), which explains most of the
species-rank Bray-Curtis gap; at genus rank it is correct.

**Conclusion:** the remaining D6331 difference comes from the sample, not the pipeline: two taxa
were not amplified, two are below any realistic depth, and species-rank proportions are
limited by 16S-identical species and PCR bias. At genus rank the error is a third smaller.

### Chimera filter (new in v0.3.0)

The accuracy-aware consensus (cluster threshold 0.842 at measured accuracy 0.929) built 94
candidate novel OTUs from the 6 532 novel-looking mock reads. Their best hits were the mock members
themselves (_E. coli_, _Veillonella_, _Roseburia_, _Faecalibacterium_, _Limosilactobacillus_) at
88–94 % identity, i.e. chimeras that PCR reproduces many times. vsearch `--uchime_ref` against the
Emu database flags all 94; they are now removed (`chimeric_consensus_removed` in
`novel_otus_params.tsv`).

## ST-012 — Etoliko lagoon, 70 samples (consensus OTUs on 88 % accurate reads)

- Measured read accuracy 0.885; Q-score accuracy 0.881 (calibrated). The report's
  `low_read_accuracy` warning fires.
- v0.2.0 consensus (fixed 0.90 threshold): 233 484 clusters, almost all singletons → **0 OTUs**.
  At 88 % accuracy, two reads of one organism are only ~78 % identical, so 0.90 cannot cluster them.
- v0.3.0: automatic threshold 0.764, 280 091 novel reads in 564 lineage groups →
  2 643 consensus OTUs, of which 73 chimeric → **2 566 OTUs**, holding ~94 % of the novel reads.
- Median identity of the consensus sequences to their best reference: 85.5 %. Supported rank:
  order 1 154, family 1 031, class 401, phylum 41, unclassified 16 (before chimera removal).
- Main lineages: Dehalococcoidia, Deltaproteobacteria, Clostridia, Phycisphaerae,
  Planctomycetia, Bacteroidia and Anaerolineae, all typical of an anoxic, sulfidic, meromictic lagoon.

Caveat: at a 0.764 threshold, one organism may still split into more than one OTU, so 2 566 is an
upper bound for the number of distinct novel lineages. The same settings gave 0 OTUs on the gut
mock, so the OTUs are not produced by read errors or chimeras.

## Resources

ST-013 at full depth: about 9 h (Emu dominates); the v0.3.0 resume took minutes. Etoliko consensus
with `--max-group-reads 5000`: about 1 h.
