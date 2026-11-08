# Etoliko sediment core: ont16s vs the published NanoCLUST/SILVA workflow

This document compares the workflow used for the published Etoliko lake-sediment analysis
(`NB_NanoClust_SILVA.sh`, results in `Results_new/`, taxonomy `taxonomy_blast_138_2_95`) with the
ont16s pipeline, run on the **same input reads**. It covers how the two methods differ, how
similar their results are, and which is better for which purpose.

Detailed evidence: `docs/server-tasks/ST-005-results.md` (first comparison),
`ST-006-results.md` (pooled Emu), `ST-008-009-results.md` (final pipeline runs).
All numbers below were measured on the server (2026-10-08/09); none are from the literature.

## 1. Data

- 70 barcoded samples from one sediment core, 14 depth intervals (0–70 cm).
- ONT R10.4.1, basecalled with the **fast** model `dna_r10.4.1_e8.2_400bps_fast@v3` (2023-04-10);
  mean read quality ≈ 9.2. 2.0 million reads in `input_fq2/`.
- Both analyses used `input_fq2/` (verified via read counts and read IDs).

## 2. How the methods work

| Step                | Published workflow                                                                                                            | ont16s                                                                                                                                       |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Read preparation    | porechop (adapter trimming), NanoFilt 1,000–1,800 bp and `-q minQc`                                                           | BAM or FASTQ input; chopper 1,000–2,000 bp (no quality filter by default); exact duplicate reads removed                                     |
| Unit of analysis    | **Clusters**: k-mer profiles of all reads pooled, UMAP + HDBSCAN (min. 50 reads per cluster)                                  | **Individual reads**                                                                                                                         |
| Sequence per unit   | Consensus per cluster: canu correction → racon → medaka (`r941_min_high_g303`)                                                | none (reads are classified directly)                                                                                                         |
| Taxonomy            | BLAST of each consensus vs SILVA 138.2 (99 %), ≥ 95 % identity, QIIME 2 consensus                                             | Emu: alignment of every read to the database + expectation-maximisation of abundances                                                        |
| Rare-taxon handling | clusters below 0.1 % removed                                                                                                  | Emu abundance floor `10/n`; samples pooled automatically when many are shallow (`--emu_mode auto`)                                           |
| Database            | SILVA 138.2                                                                                                                   | any Emu database; here the Emu default (NCBI 2020) and SILVA 138.2 grouped by genus                                                          |
| Output              | cluster × sample count table, taxonomy, consensus sequences                                                                   | per-sample and combined tables (species/genus, abundance/counts), QC reports, warnings, database provenance, mock validation, MultiQC report |
| Execution           | bash script; tools from conda environments in another user's home directory; samples and clusters processed one after another | Nextflow + pinned containers; parallel; resumable; tested in CI                                                                              |

## 3. How similar are the results?

ont16s **with the genus-level SILVA database** (ST-009) compared with the published results:

| Measure                                                           | Value                                                                                                        | Meaning                                                                      |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Between-sample pattern (Mantel r, Bray-Curtis)                    | 0.96 phylum, 0.95 genus                                                                                      | both methods order samples the same way                                      |
| Sample-to-sample difference between methods (Bray-Curtis, median) | 0.13 (range 0.02–0.26)                                                                                       | phylum profiles of the same sample are close                                 |
| Depth structure (dissimilarity vs depth difference)               | r = 0.21 published, 0.24 ont16s                                                                              | same depth signal                                                            |
| Published phyla > 0.1 % missed by ont16s                          | none                                                                                                         | all lineages recovered, incl. Atribacterota, Zixibacteria, WS1, Acetothermia |
| Published resolved-genus abundance in genera also found by ont16s | 99.5 % (median per sample)                                                                                   | genus-level agreement                                                        |
| Depth trends of main phyla (Spearman ρ, published / ont16s)       | Cyanobacteria −0.40 / −0.43; Acetothermia 0.39 / 0.44; Acidobacteriota 0.27 / 0.32; Bacteroidota 0.32 / 0.29 | same ecological trends                                                       |

**The ecological conclusions of the published study are reproduced by an independent method.**

Differences that remain:

- Mean phylum shares differ by a few percentage points (e.g. Bacillota 35.8 % vs 30.1 %,
  Patescibacteria 0.4 % vs 2.7 %).
- With Emu's default database (NCBI 2020) instead of SILVA, ~7 % of the community (sediment
  candidate phyla) cannot be detected and reads are forced onto cultured genera; community
  patterns still agree (Mantel 0.96 / 0.92), but names are less reliable.

## 4. Which is better at what

### Where the published workflow is stronger

| Strength                         | Why                                                                                                                                                                                           |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Representative sequences**     | Each cluster gets a polished consensus sequence (useful for phylogenies, novel lineages, database submission). ont16s reports taxa, not sequences.                                            |
| **Novel organisms stay visible** | A cluster is counted even when BLAST finds no match ("Unassigned", 19.8 % of reads). Emu always assigns a read to its closest reference, so a truly novel lineage appears under a known name. |
| **Conservative naming**          | The 95 % identity threshold refuses weak assignments. Emu has no such threshold.                                                                                                              |
| **Shallow samples by design**    | Pooled clustering shares information across samples. (ont16s now does the same with `--emu_mode pooled`, see below.)                                                                          |

### Where ont16s is stronger

| Strength                                        | Evidence                                                                                                                                                                                                                                                                                               |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Reproducibility**                             | Pinned containers, fixed software versions, Nextflow; any user can rerun it. The published script depends on conda environments and scripts in another user's home directory, and the SILVA reference path in the QIIME 2 step lacks a leading `/` (only works from `/`).                              |
| **Speed and scalability**                       | 70 samples in ~36 min on 24 CPUs (ST-009); parallel and resumable; runs on laptops, servers, HPC or cloud. The published workflow processes clusters one after another (canu, racon, medaka, fastANI per cluster); its run time was not recorded.                                                      |
| **Correct models for the chemistry**            | The published consensus step used a medaka model for R9.4.1 high-accuracy reads (`r941_min_high_g303`) on R10.4.1 fast reads. ont16s has no polishing step that depends on a chemistry model.                                                                                                          |
| **Data-quality checks**                         | ont16s found problems the published run did not report: identical reads duplicated in 5 input files (barcode24 and barcode50 entirely), and 36 samples where most reads were short fragments. These are removed or flagged in a warnings report.                                                       |
| **Read-level abundances**                       | Every read contributes (probabilistically) to the estimate; no 50-read cluster minimum and no 0.1 % cluster filter.                                                                                                                                                                                    |
| **Species resolution when the database allows** | On Zymo mock communities, ont16s with Emu's default database detected all 12 expected species (ST-001, ST-008 test runs). The published workflow was not run on a mock, so its species-level accuracy is unknown; on Etoliko it left 53 % of reads without a resolved genus (ont16s with SILVA: 51 %). |
| **Validation built in**                         | Mock samples are checked automatically against expected composition (presence/absence and, when known, proportions).                                                                                                                                                                                   |
| **Transparency**                                | Every run records software versions, database checksums, the pooling decision and every warning with its reason.                                                                                                                                                                                       |
| **Flexibility**                                 | Database, filters and pooling are parameters; BAM or FASTQ input; organelle removal for host/plant samples.                                                                                                                                                                                            |

### Limitations of ont16s to keep in mind

- Taxonomy depends entirely on the database. For sediments use the genus-level SILVA database;
  Emu's default database lacks most uncultured lineages.
- "Unassigned" fractions are not comparable with the published workflow (1.3 % vs 19.8 %): Emu
  assigns weak matches that BLAST at 95 % would reject.
- With pooling, a taxon well supported in some samples can be reported in a sample where it has
  only a few reads.
- No representative sequences (yet).

## 5. Recommendation

| Goal                                                                                  | Recommended                                                                                                     |
| ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Community composition, depth/treatment patterns, many samples, reproducible reporting | **ont16s** with `--emu_db` = SILVA 138.2 genus database (pooling is chosen automatically)                       |
| Discovering and describing novel lineages, phylogenies, depositing sequences          | the clustering + consensus approach (with a medaka model matching the chemistry), or an amplicon-variant method |
| Both                                                                                  | run ont16s for the community analysis; use clustering only on the lineages of interest                          |

## 6. Issues in the published analysis worth checking

1. **Duplicated reads** in `input_fq2/`: barcode24 and barcode50 contain every read twice;
   barcode16, barcode18 and barcode64 partly (11,345 duplicates after length filtering). This
   doubles their weight in pooled clustering.
2. **barcode20 and barcode21** share 50 % of their reads (technical replicates; noted for analyses
   that assume independent samples).
3. **Medaka model** `r941_min_high_g303` used on R10.4.1 fast-basecalled reads.
4. `input_fq/` and `input_fq2/` differ in 9 samples (up to 900× in read count); only `input_fq2/`
   was used.

None of these changes the main community-level conclusions, which both methods reproduce.
