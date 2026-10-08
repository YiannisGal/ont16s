# SERVER TASK ST-001 — Run Emu manually on one Zymo chunk

Status: **Executed 2026-10-06.** Results: `ST-001-results.md`. Written 2026-10-06.

This prompt is self-contained. Claude Code on the server can execute it without the
conversation that created it. Read `CLAUDE.md` section 0 first.

---

You are working on the **ont16s** project (Nextflow pipeline for ONT full-length 16S,
Emu-based, see `docs/project-landscape.md`).

## Objective

Before writing any Nextflow, run Emu **by hand** on real data to learn:

1. what the input reads look like (BAM header, read count, length distribution);
2. what Emu needs (inputs, database files) and produces (output files, columns);
3. how many resources it uses (wall time, peak memory);
4. whether results are biologically plausible for a known mock community;
5. how sequencing depth changes what Emu reports (20 k reads vs full chunk).

This is a learning/feasibility run, **not validation**. Do not over-interpret numbers.

## Environment (verified 2026-10-06)

- Lab server: Ubuntu 24.04, x86_64, 28 CPU, 125 GB RAM, Docker 29.8 (user in `docker` group), no SLURM.
- Repo: `/mnt/Ubuntu_HD5/yiannis/ont16s`
- Root partition `/` is 87 % full → **all data under `/mnt/Ubuntu_HD5`**, never in `~` or `/tmp`.
- Data **must not** be committed to git (`.gitignore` already excludes BAM/FASTQ).

## Inputs

| Item                                       | Source                                                                                                                               | Notes                                                                                                   |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| Reads                                      | `https://ont-open-data.s3.amazonaws.com/zymo_16s_2025.09/basecalls/MSPlus/MAB114/sup/rep1/FBB32095_bam_pass_15aa3986_bbffde72_0.bam` | 67.6 MB, unaligned BAM, SUP v5.2.0, SQK-MAB114.24, R10.4.1                                              |
| Emu default DB                             | OSF project `56uf7`, file `osfstorage/emu-prebuilt/emu.tar`                                                                          | rrnDB v5.6 + NCBI 16S RefSeq, 2020-09-17; 49,301 seqs, 17,555 species (per Emu README)                  |
| ONT's own Emu result (for comparison only) | `https://ont-open-data.s3.amazonaws.com/zymo_16s_2025.09/analysis/emu/MSPlus/MAB114/rep1/reads.fastq_rel-abundance.tsv`              | ONT used an **undocumented** Emu DB (`analysis/databases/emu/`, 369 MB fasta). Not directly comparable. |

## Containers (pinned by tag + digest)

```
quay.io/biocontainers/emu:3.6.2--hdfd78af_0       sha256:61ea3336f12d41930d73e57ce1b041bce48d66b4011a165bf1f0efce9d684777
quay.io/biocontainers/samtools:1.24--h9dcdb79_1   sha256:a130447589651ed09252aa95a5e4f4132942cdb54d835d81a04a9a930d656561
quay.io/biocontainers/seqkit:2.14.0--hb192632_0   sha256:45fb535880be37dfed5be5517111fb8bfdd6234ef36e725b126a6131b1af2ef0
python:3.12-slim                                   (only to run osfclient for the DB download)
```

## Commands

Run step by step. After each step, check the output before continuing.

```bash
# 0. Setup
export D=/mnt/Ubuntu_HD5/yiannis/ont16s_data/ST-001
mkdir -p $D/{raw,reads,db,emu_20k,emu_full,ont_ref,logs}
cd $D
DR="docker run --rm -u $(id -u):$(id -g) -v $D:$D -w $D"
EMU=quay.io/biocontainers/emu:3.6.2--hdfd78af_0
SAM=quay.io/biocontainers/samtools:1.24--h9dcdb79_1
SK=quay.io/biocontainers/seqkit:2.14.0--hb192632_0

# 1. Download one BAM chunk and record checksum
curl -fL -o raw/MSPlus_MAB114_sup_rep1_0.bam \
  https://ont-open-data.s3.amazonaws.com/zymo_16s_2025.09/basecalls/MSPlus/MAB114/sup/rep1/FBB32095_bam_pass_15aa3986_bbffde72_0.bam
sha256sum raw/*.bam | tee logs/checksums.txt

# 2. Inspect BAM header: basecaller model, kit, read groups
$DR $SAM samtools view -H raw/MSPlus_MAB114_sup_rep1_0.bam | grep -E '^@(RG|PG)' | cut -c1-300 | tee logs/bam_header.txt

# 3. BAM -> FASTQ, then read stats
$DR $SAM sh -c "samtools fastq raw/MSPlus_MAB114_sup_rep1_0.bam > reads/full.fastq"
$DR $SK seqkit stats -a -T reads/full.fastq | tee logs/stats_full.tsv

# 4. Reproducible 20k subsample (fixed seed, two-pass for exact count)
$DR $SK seqkit sample -2 -s 42 -n 20000 reads/full.fastq -o reads/sub20k.fastq
$DR $SK seqkit stats -a -T reads/sub20k.fastq | tee logs/stats_20k.tsv

# 5. Emu default database + provenance
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -v $D/db:/db -w /db python:3.12-slim \
  sh -c "pip install -q --user osfclient && /tmp/.local/bin/osf -p 56uf7 fetch osfstorage/emu-prebuilt/emu.tar"
tar -xf db/emu.tar -C db && ls -la db
find db -type f \( -name '*.tar' -o -name '*.fasta' -o -name '*.tsv' \) -exec sha256sum {} + | tee -a logs/checksums.txt
#   -> locate the directory containing species_taxid.fasta + taxonomy.tsv; set:
export EMUDB=$(dirname $(find $D/db -name species_taxid.fasta | head -1))

# 6. Emu on 20k subsample (wall time + peak container memory via cgroup v2)
/usr/bin/time -v $DR $EMU sh -c "emu --version; emu abundance reads/sub20k.fastq --db $EMUDB \
   --threads 8 --keep-counts --keep-read-assignments --output-unclassified \
   --output-dir emu_20k; echo PEAK_MEM_BYTES=\$(cat /sys/fs/cgroup/memory.peak 2>/dev/null)" \
   2> logs/time_20k.txt | tee logs/emu_20k.log

# 7. Same on the full chunk
/usr/bin/time -v $DR $EMU sh -c "emu abundance reads/full.fastq --db $EMUDB \
   --threads 8 --keep-counts --keep-read-assignments --output-unclassified \
   --output-dir emu_full; echo PEAK_MEM_BYTES=\$(cat /sys/fs/cgroup/memory.peak 2>/dev/null)" \
   2> logs/time_full.txt | tee logs/emu_full.log

# 8. ONT's own Emu result (reference only)
curl -fL -o ont_ref/rel-abundance.tsv \
  https://ont-open-data.s3.amazonaws.com/zymo_16s_2025.09/analysis/emu/MSPlus/MAB114/rep1/reads.fastq_rel-abundance.tsv
```

If a command fails, diagnose it. Do not silently change parameters. Record any deviation.
If `/usr/bin/time` is missing (package `time` not installed), use the shell builtin
`time` for wall time instead and note it. If `memory.peak` is empty, note it and use `docker stats` sampling or report "not measured".

## Resources

Expected small (minutes, a few GB RAM), but **not yet measured**, which is the point of
this task. Use `--threads 8`. Leave the remaining cores for other server users.

## Expected biology (for a plausibility check only)

MSPlus = ZymoBIOMICS Microbial Community DNA Standard + gDNA from _Bifidobacterium
adolescentis_, _Borrelia burgdorferi_, _Chlamydia trachomatis_, _Gardnerella vaginalis_
(per ONT dataset page). The standard's bacteria: _Pseudomonas aeruginosa_,
_Escherichia coli_, _Salmonella enterica_, _Limosilactobacillus fermentum_,
_Enterococcus faecalis_, _Staphylococcus aureus_, _Listeria monocytogenes_,
_Bacillus subtilis_. (Its two yeasts have no 16S and should not appear.)

Expected **proportions are not published by ONT** for the spiked mix, so use this as a
**presence/absence** check only. Note naming differences (e.g. _Lactobacillus fermentum_
vs _Limosilactobacillus fermentum_) caused by the database being from 2020.

## Outputs to produce

Write **`docs/server-tasks/ST-001-results.md`** in the repo (small text only), containing:

1. Exact commands run + any deviations.
2. BAM header facts: basecall model, kit, run ID (from `@RG`/`@PG`).
3. Read stats table (full vs 20k): count, mean/N50/min/max length, mean Q if available.
4. Emu DB provenance: source, file sizes, sha256, number of sequences/species.
5. Emu output files produced and the column meanings of `*_rel-abundance.tsv`.
6. Resource table: wall time, peak memory, for 20k and full.
7. Top 20 species (full and 20k), with abundance and estimated counts.
8. Presence/absence of the 12 expected bacteria in full and 20k; list unexpected taxa
   above 0.1 %.
9. Emu's mapped / unmapped / filtered / unclassified-mapped read counts (from log).
10. Taxa present in full but missing from 20k (relates to Emu's `10/n_reads` detection floor).
11. Qualitative comparison with ONT's own Emu result (same species? DB differs!).
12. Problems encountered and how they were fixed.
13. Clear status labels: Executed / not validated.

Also append a short entry to `docs/development-log.md` and update `CLAUDE.md` section 0
("Completed" / "Current task") only if something important changed.

## Save results

- Large data stays in `/mnt/Ubuntu_HD5/yiannis/ont16s_data/ST-001/`.
- Commit only the markdown files:
  `git add docs/ && git commit -m "docs: add ST-001 manual Emu run results"` then `git push`.

## Return

A short summary for the user: did everything run, resource usage, whether the 12 expected
bacteria were detected, anything surprising, and open questions for the next step
(Milestone 1 scaffold).
