# YiannisGal/ont16s: Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v0.3.1 - 2026-11-21

### Fixed

- `CITATION.cff`: removed the v0.2.0 version DOI and updated the version, so the Zenodo archive of the release succeeds (v0.3.0 failed to archive). Same code as v0.3.0.

## v0.3.0 - 2026-11-21

### Added

- Mock validation: per-taxon `status` (`detected`, `genus_only`, `below_detection_limit`,
  `not_amplified`, `missed`), expected reads, `recall_detectable`, `recall_genus` and
  `bray_curtis_genus`.
- Report warnings `low_read_accuracy` (measured accuracy < `--min_read_accuracy`, 0.90) and
  `q_score_overestimate` (Q scores promise more accuracy than measured).
- Novelty: measured read accuracy (median identity of species-rank reads) and best genus/species
  per read.
- `novel_otus_params.tsv`.
- Validation at full depth on the D6331 gut mock (ST-013) and novel-lineage test on Etoliko (ST-012).

### Changed

- Consensus OTUs: reads grouped by closest-reference lineage; clustering threshold `auto` from
  measured read accuracy (`--novel_cluster_id auto`); OTU size counted by mapping all novel reads
  back; chimeric consensus sequences removed (vsearch `--uchime_ref`). Old method: 0 OTUs on
  Etoliko (88 % accurate reads); new: 2 566. Gut mock: 0 false OTUs.
- Release DOI added (v0.2.0: 10.5281/zenodo.24406558).

## v0.2.0 - 2026-11-20

### Added

- Novelty analysis (`novelty/`): per read, how deep a name the identity to the closest reference
  supports (Yarza et al. 2014 thresholds, corrected for read accuracy); summary in MultiQC.
  `--skip_novelty`, `--novelty_min_coverage`, `--novelty_max_reads`.
- Consensus OTUs of novel lineages (`novelty/novel_otus/`): VSEARCH clustering + Racon polishing,
  classified against the database. `--skip_novel_otus`, `--novel_cluster_id`, `--novel_min_size`.
- Mock validation reports Bray-Curtis and per-taxon log2(observed/expected).
- NaMeco independent-laboratory validation (ST-010): D6306 8/8 species, Bray-Curtis 0.09.
- `CITATION.cff`.

### Changed

- nf-core template updated to 4.2.1 (nf-schema 2.7.3: no more `validation.*` config warnings).
- NanoPlot conda environment pins `plotly<7` (conda CI failed with plotly 7).
- Docker, Singularity and conda profiles tested in CI.

## v0.1.0 - 2026-11-08

First release.

### Added

- Input: samplesheet `sample,reads,mock`; unaligned BAM or FASTQ (plain/gzipped), multiple files per sample merged.
- Read QC (NanoPlot, raw and filtered), length/quality filter (chopper, default 1,000–2,000 bp), duplicate-read removal (seqkit rmdup).
- Taxonomic profiling with Emu 3.6.2; `--emu_db` accepts a directory or archive (local or URL); database provenance (checksums) recorded.
- `--emu_mode auto|per_sample|pooled`: pooled Emu with per-sample split for many shallow samples.
- Combined tables (species/genus, abundance/counts), `--exclude_taxa`, organelle reporting.
- Run summary and warnings (low depth, filter loss, duplicates, unassigned reads, organelles) and database-fit check, shown in MultiQC.
- Mock-community validation (`assets/mocks/`: Zymo MSPlus, D6306, D6331 with expected 16S proportions).
- `bin/build_silva_genus_db.py`: genus-level SILVA 138.2 Emu database.
- Test profile with public test data (YiannisGal/ont16s-test-datasets); nf-test pipeline tests (per-sample and pooled).
- Documentation: README, usage, output, validation reports (`docs/server-tasks/`), Etoliko method comparison, logo.

### Changed

- `manifest.defaultBranch` set to `main`.
