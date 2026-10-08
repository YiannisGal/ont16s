# ST-001 results — Manual Emu run on one Zymo MSPlus chunk

**Status: Executed (2026-10-06, server). Not validated.** Learning/feasibility run only;
numbers below are from one ~53 k-read chunk and must not be over-interpreted.

Data and logs: `/mnt/Ubuntu_HD5/yiannis/ont16s_data/ST-001/` (not in git).

---

## 1. Commands run and deviations

All commands from `ST-001-emu-manual-run.md` were run verbatim, steps 0–8, via a
wrapper script `ont16s_data/ST-001/run_st001.sh` (`set -euo pipefail`, detached with
`setsid nohup`, log in `logs/run.log`). Start 16:43:13, end 17:56:40 (+03:00).

Deviations:
- Added `docker pull` + `docker image inspect` of each image in step 0 to confirm digests.
  All three biocontainer digests match the pinned ones in the task.
- `python:3.12-slim` was not pinned by digest (as in the task).
- Post-run analysis (not part of the task commands): one extra `samtools view` to count
  reads per read group, and `logs/analyse.py` (run in `python:3.12-slim`) to produce the
  tables below (`logs/analysis.txt`).
- No parameters were changed.

## 2. BAM header facts

| Field | Value |
|---|---|
| Basecaller | dorado 1.1.1+e72f1492 (`dorado basecaller sup@v5.2.0 --kit-name SQK-MAB114-24 --no-trim`) |
| Model | `dna_r10.4.1_e8.2_400bps_sup@v5.2.0` |
| Kit | SQK-MAB114-24 |
| Run ID | `15aa3986-cabb-4454-b73a-f7003128bb27` |
| Flow cell / device | FBB32095 / GXB03865 |
| Run date | 2025-07-16 |
| Source pod5 (`fn` tag) | `pod5_subset_FBB32095_Zymo_plus_spike.pod5` |

The header declares 25 `@RG` lines (barcode01–24 plus unbarcoded); this is dorado
boilerplate. **All 53,011 reads carry `barcode04`**, so the chunk is a single sample.
Note `--no-trim`: barcodes/adapters were not trimmed by dorado.

## 3. Read stats (`seqkit stats -a`)

| | full | 20k |
|---|---|---|
| Reads | 53,011 | 20,000 |
| Total bases | 79,671,458 | 30,173,069 |
| Mean length | 1,502.9 | 1,508.7 |
| N50 | 1,579 | 1,579 |
| Q1 / median / Q3 | 1,560 / 1,577 / 1,589 | 1,561 / 1,578 / 1,589 |
| Min / max | 77 / 56,321 | 139 / 3,204 |
| Q20 / Q30 bases | 86 % / 77 % | 86 % / 77 % |
| AvgQual (seqkit) | 15.68 | 15.81 |

Tight length distribution around full-length 16S (~1.5–1.6 kb). One 56 kb read in the
full chunk is likely a chimera/concatemer; a length filter will be needed in the pipeline.

## 4. Emu database provenance

Source: OSF project `56uf7`, `osfstorage/emu-prebuilt/emu.tar` (via osfclient).

| File | Size (bytes) | sha256 |
|---|---|---|
| emu.tar | 89,407,488 | 75e93064bcbb8fdcb58165e7b09eda7cc8a1abba28839c9dce286c395bbc1738 |
| species_taxid.fasta | 87,131,687 | 75637fdb0b8782d26fdeab1162f2e0e9c364ba6f4ee1832fed5a328eb56e7818 |
| taxonomy.tsv | 2,269,111 | d34945f8485c7cf68ecf9a9494c7374ecc8ec86f1e136f82db94044a35109622 |

- Sequences in fasta: **49,243** (Emu README says 49,301; small discrepancy, unexplained).
- Rows in taxonomy.tsv: **17,556** (README: 17,555 species).
- Tar also contains macOS `._*` resource-fork files (ignorable; checksums in `logs/checksums.txt`).
- File mtimes: 2022-02-11.
- Raw BAM sha256: `470db4e562116077c7c7dddda7d27c21b610eac0ebc2ece9a36ad97044b2d1b1`.

## 5. Emu output files

Per run (`emu_20k/`, `emu_full/`, prefix = input basename):

| File | Content |
|---|---|
| `*_rel-abundance.tsv` | Per-taxon abundance table (main result) |
| `*_read-assignment-distributions.tsv` | Per-read probability over taxa (`--keep-read-assignments`), 3.9 MB for full |
| `*_unmapped.fastq` | Reads with no alignment (`--output-unclassified`) |
| `*_unclassified_mapped.fastq` | Mapped reads assigned to no taxon kept after EM |
| `*_filtered_mapped.fastq` | Reads whose alignments were filtered out |

`*_rel-abundance.tsv` columns: `tax_id`; `abundance` (relative abundance, fraction
of classified reads, sums to 1); taxonomy ranks `species … superkingdom` and
`subspecies / species subgroup / species group` (from `taxonomy.tsv`, often empty);
`estimated counts` (abundance × reads, from `--keep-counts`). With
`--output-unclassified`, extra rows `unmapped`, `mapped_filtered`, `mapped_unclassified`
appear with counts and abundance 0.

## 6. Resources (`--threads 8`, server otherwise lightly loaded)

| Run | Reads | Wall time | Peak container memory (`memory.peak`) |
|---|---|---|---|
| 20k | 20,000 | 20:21 | 2.62 GB (2,615,889,920 B) |
| full | 53,011 | 50:18 | 3.40 GB (3,400,679,424 B) |

- `/usr/bin/time -v` measures the `docker` client, not the container: its max RSS
  (~31 MB) and CPU time (~0.1 s) are **not** Emu's and are not reported. CPU usage of Emu
  was therefore **not measured**.
- Emu is much slower than expected (~16 reads/s at 20k; ~18 reads/s at full; i.e. roughly linear in read count).
  Cause not investigated (minimap2 vs EM vs single-threaded parts). Open question.

## 7. Top species

| Species | full % | full counts | 20k % | 20k counts |
|---|---|---|---|---|
| Bacillus subtilis | 16.394 | 8,679.1 | 16.485 | 3,292.5 |
| Staphylococcus aureus | 14.429 | 7,639.0 | 14.575 | 2,911.0 |
| Listeria monocytogenes | 14.116 | 7,473.2 | 14.354 | 2,867.0 |
| Limosilactobacillus fermentum | 13.190 | 6,983.3 | 13.198 | 2,635.9 |
| Enterococcus faecalis | 9.320 | 4,934.0 | 9.578 | 1,913.0 |
| Gardnerella vaginalis | 8.391 | 4,442.5 | 8.200 | 1,637.8 |
| Bifidobacterium adolescentis | 6.279 | 3,324.0 | 5.995 | 1,197.3 |
| Salmonella enterica | 5.340 | 2,827.0 | 5.527 | 1,103.8 |
| Escherichia coli | 4.963 | 2,627.7 | 4.928 | 984.2 |
| Borreliella burgdorferi | 2.584 | 1,368.0 | 2.594 | 518.1 |
| Pseudomonas aeruginosa | 2.495 | 1,321.0 | 2.508 | 501.0 |
| Chlamydia trachomatis | 1.898 | 1,005.0 | 1.757 | 351.0 |
| Bacillus halotolerans | 0.157 | 82.9 | 0.161 | 32.3 |
| Borreliella americana | 0.060 | 31.9 | 0.090 | 17.9 |
| Laceyella sacchari | 0.055 | 29.0 | — | — |
| Bifidobacterium ruminantium | 0.051 | 27.1 | — | — |
| Bacillus mojavensis | 0.049 | 25.7 | 0.051 | 10.2 |
| Borreliella bissettii | 0.042 | 22.0 | — | — |
| Listeria ivanovii | 0.039 | 20.9 | — | — |
| Bacteroides fragilis | 0.036 | 19.0 | — | — |

Taxa detected: 27 rows full, 18 rows 20k (including the 3 unclassified/unmapped rows).
The 20k profile is within ~0.3 percentage points of the full profile for all 12 main taxa.

## 8. Expected bacteria: presence/absence

| Expected | full | 20k |
|---|---|---|
| Pseudomonas aeruginosa | ✅ | ✅ |
| Escherichia coli | ✅ | ✅ |
| Salmonella enterica | ✅ | ✅ |
| Limosilactobacillus fermentum | ✅ | ✅ |
| Enterococcus faecalis | ✅ | ✅ |
| Staphylococcus aureus | ✅ | ✅ |
| Listeria monocytogenes | ✅ | ✅ |
| Bacillus subtilis | ✅ | ✅ |
| Bifidobacterium adolescentis | ✅ | ✅ |
| Borrelia burgdorferi | ✅ as *Borreliella burgdorferi* (genus renamed) | ✅ |
| Chlamydia trachomatis | ✅ | ✅ |
| Gardnerella vaginalis | ✅ | ✅ |

**12/12 detected in both.** The 12 account for ~99.4 % of abundance.
Unexpected taxa > 0.1 %: only *Bacillus halotolerans* (0.16 %), a close relative of
*B. subtilis* (likely cross-assignment, not contamination). All other off-target taxa are
< 0.1 % and are mostly congeners of mock members (*Borreliella americana/bissettii*,
*Listeria ivanovii*, *Bacillus mojavensis/vallismortis/velezensis*, *Shigella flexneri*,
*Bifidobacterium ruminantium*) — consistent with species-level ambiguity of 16S.
*Bacteroides fragilis*, *Veillonella parvula*, *Laceyella sacchari* (~0.03–0.05 %) are not
mock relatives: possible low-level contamination, barcode bleed, or misassignment.

## 9. Emu read accounting (from logs)

| | 20k | full |
|---|---|---|
| Mapped | 19,992 | 52,979 |
| Unmapped | 7 | 30 |
| Filtered (alignment length > 2000) | 1 | 2 |
| Unclassified mapped | 19 | 37 |
| EM iterations | 20 | 20 |

## 10. Taxa in full but missing from 20k

| Taxon | full % | full counts |
|---|---|---|
| Laceyella sacchari | 0.0548 | 29.0 |
| Bifidobacterium ruminantium | 0.0511 | 27.1 |
| Borreliella bissettii | 0.0416 | 22.0 |
| Listeria ivanovii | 0.0394 | 20.9 |
| Bacteroides fragilis | 0.0359 | 19.0 |
| Shigella flexneri | 0.0327 | 17.3 |
| Veillonella parvula | 0.0302 | 16.0 |
| Bacillus vallismortis | 0.0260 | 13.8 |
| Bacillus velezensis | 0.0237 | 12.5 |

Nothing appears in 20k but not in full. Emu drops taxa below a detection floor of about
`10 / n_reads` (20k: 0.05 %; full: ~0.019 %). All of the dropped taxa above sit at
0.02–0.055 %, i.e. near or below the 20k floor (expected 20k counts ≈ 5–11 reads). The
smallest taxa therefore depend on depth; the 12 main taxa don't.

## 11. Comparison with ONT's own Emu result (qualitative)

ONT's table (`ont_ref/rel-abundance.tsv`, 33 rows) uses a **different, undocumented DB**
whose naming looks GTDB-like (e.g. `Bacillus_P_294101`, `Listeria_A monocytogenes_B_319801`,
phylum `Bacillota_I`). ONT's read total (~50.7 k from counts) also differs, so it covers
a different read set than our one chunk.

- **Same at genus level / similar proportions:** *L. fermentum* 13.46 % vs 13.19 %;
  *Bifidobacterium adolescentis* 6.45 vs 6.28; *Chlamydia trachomatis* 1.94 vs 1.90;
  *Enterococcus faecalis* 9.50 vs 9.32; Pseudomonas ~2.50 vs 2.50; Borrelia ~2.68 vs 2.58.
- **Different species names in ONT's DB** for several mock members:
  *Bacillus spizizenii* (vs *B. subtilis*), *Staphylococcus argenteus* (vs *S. aureus*),
  *Bifidobacterium vaginale* (= GTDB name for *Gardnerella vaginalis*),
  *Salmonella bongori* (vs *S. enterica*), *Pseudomonas paraeruginosa*,
  *Escherichia ruysiae* + *Shigella sonnei/boydii* (vs *E. coli*).
- *Listeria monocytogenes* is split across two GTDB sub-species plus *L. marthii* in ONT's
  result (10.46 + 2.71 + 1.81 %); with the default DB it is a single 14.1 % call.

Interpretation: the default 2020 DB gave the cleaner species-level answer on this mock.
ONT's DB shows how strongly the reference choice changes species names and splits.
This supports the project's "database-aware" positioning (D-001). Not a validation.

## 12. Problems encountered

- **No pipeline failures.** All steps exited 0.
- `/usr/bin/time` around `docker run` measures the client only (see §6). For the
  pipeline, rely on Nextflow trace (cgroup-based) or `memory.peak`.
- First attempt at the analysis script piped Python via stdin into `docker run` without
  `-i`, which produced no output. Fixed by writing `logs/analyse.py` and running it from file.
- Emu DB fasta has 58 fewer sequences than the README states (unexplained).
- Initial watcher process in Claude Code was lost when the session ended; the detached
  run itself was unaffected.

## 13. Status and open questions

**Status: Executed. Not validated.**

Open questions for Milestone 1:
1. Why is Emu so slow (50 min / 53 k reads on 8 threads)? Profile minimap2 vs EM; try
   `--type lr:hq` for R10.4.1 SUP reads; check thread scaling.
2. A read-length filter (e.g. 1,000–2,000 bp) is needed: one 56 kb read was present, and
   dorado ran with `--no-trim`.
3. Expected MSPlus proportions are still needed for quantitative validation.
4. Where does ONT's Emu DB come from (GTDB-based?) — needed for any fair comparison.
5. Resource requests for the Emu process: ~4 GB memory per chunk looks enough; time
   is the bottleneck.
