# Installing and running ont16s, step by step

This guide goes from an empty Linux machine to a finished analysis. Every command can be copied as
it is; replace only the paths in `/path/to/...`. If you have run Nextflow pipelines before, the
[Quick start](../README.md#quick-start) in the README is enough.

**You need:** a Linux computer or server (x86_64), at least 4 CPUs and 16 GB RAM (8 CPUs and 32 GB
for large runs), ~10 GB free disk for containers and the database, plus about 3× the size of your
reads for the work directory. macOS works with Docker Desktop but is not tested. Windows: use WSL2.

---

## Part 1 — Install (once per computer)

### Step 1. Java 17 or newer

Nextflow runs on Java. Check whether you have it:

```bash
java -version
```

If the version is 17 or higher, go to step 2. Otherwise install it. The simplest way, without
administrator rights, is SDKMAN:

```bash
curl -s https://get.sdkman.io | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install java 17.0.10-tem
java -version
```

(With administrator rights on Ubuntu/Debian: `sudo apt install openjdk-17-jre`.)

### Step 2. Nextflow (≥ 25.10.4)

```bash
cd ~
curl -s https://get.nextflow.io | bash
mkdir -p ~/bin && mv nextflow ~/bin/
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
nextflow -version
```

You should see `nextflow version 25.10.4` or newer. To update later: `nextflow self-update`.

### Step 3. A container engine (the software of the pipeline)

The pipeline does not install Emu, minimap2 etc. on your system; it downloads ready-made
containers. Choose **one**:

| Option                      | When to use                                                | Profile                |
| --------------------------- | ---------------------------------------------------------- | ---------------------- |
| **Docker**                  | your own computer or a server where you have Docker        | `-profile docker`      |
| **Singularity / Apptainer** | HPC clusters (no root needed)                              | `-profile singularity` |
| **Conda**                   | no containers available at all (slower, less reproducible) | `-profile conda`       |

**Docker** (Ubuntu; needs administrator rights once):

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER     # lets you run docker without sudo
# log out and in again, then check:
docker run --rm hello-world
```

If `docker run hello-world` prints "Hello from Docker!", Docker is ready.

**Singularity/Apptainer:** usually installed on clusters already; check with `singularity --version`
or `apptainer --version`. Otherwise ask your administrator.

**Conda:** install [Miniforge](https://github.com/conda-forge/miniforge), then
`conda config --set channel_priority strict`.

### Step 4. Test that everything works

```bash
nextflow run YiannisGal/ont16s -r v0.3.1 -profile test,docker --outdir results_test
```

(Replace `docker` with `singularity` or `conda` if you chose those.)

- The first run downloads the pipeline and the containers (a few minutes); later runs reuse them.
- The test itself takes about 2–3 minutes and analyses 546 reads of a Zymo mock community.
- At the end you must see `Pipeline completed successfully`.
- Check the result: `column -t results_test/mock_validation/mock_validation_summary.tsv` should
  show the expected species of the mock as detected.

If this works, the installation is complete.

### Step 5. Download an Emu database

The database is the list of reference 16S sequences reads are compared with. Choose with this rule:

- **Mock communities, human/animal gut, well-studied environments** → Emu default database
  (species names).
- **Lakes, sediments, soils, extreme environments** → SILVA grouped by genus (many uncultured
  lineages; genus names).

**Emu default database (86 MB download):**

```bash
pip install osfclient
mkdir -p /path/to/databases && cd /path/to/databases
osf -p 56uf7 fetch osfstorage/emu-prebuilt/emu.tar
mkdir emu_default && tar -xf emu.tar -C emu_default
ls emu_default        # must contain species_taxid.fasta and taxonomy.tsv
```

(If `pip` is missing: `python3 -m pip install --user osfclient`.)

**SILVA 138.2 grouped by genus:** see
[usage: choosing a database](usage.md#choosing-a-database) (one download and one command).

You can also pass the `.tar` file directly to `--emu_db`; unpacking once is faster for repeated runs.

---

## Part 2 — Run your data

### Step 6. Collect your reads

ont16s accepts what the ONT basecaller (dorado / MinKNOW) writes:

- unaligned **BAM** files (`*.bam`), or
- **FASTQ** files (`*.fastq`, `*.fq`, optionally `.gz`).

Reads must already be **demultiplexed** (one barcode = one sample) and should be full-length 16S
amplicons (~1,500 bp). MinKNOW usually writes one folder per barcode with many chunk files, e.g.:

```
fastq_pass/
├── barcode01/  FBB32095_pass_barcode01_..._0.fastq.gz, ..._1.fastq.gz, ...
├── barcode02/  ...
```

You do **not** need to merge the chunks; list them all in the samplesheet (next step).

### Step 7. Write the samplesheet

A samplesheet is a CSV file with three columns: `sample`, `reads`, `mock`.

```csv
sample,reads,mock
lake_A,/data/run1/fastq_pass/barcode01/FBB32095_pass_barcode01_0.fastq.gz,
lake_A,/data/run1/fastq_pass/barcode01/FBB32095_pass_barcode01_1.fastq.gz,
lake_B,/data/run1/fastq_pass/barcode02/FBB32095_pass_barcode02_0.fastq.gz,
zymo_ctrl,/data/run1/fastq_pass/barcode12/FBB32095_pass_barcode12_0.fastq.gz,zymo_d6306
```

Rules:

- One row per file. Rows with the same `sample` name are merged into one sample.
- Sample names: letters, numbers, `_` or `-`; no spaces.
- Use full (absolute) paths.
- `mock`: empty for real samples. For a mock community control, write its name: `zymo_msplus`,
  `zymo_d6306` (ZymoBIOMICS even) or `zymo_d6331` (ZymoBIOMICS gut). The pipeline then checks
  the result against the known composition.

**Make the samplesheet automatically** from a MinKNOW folder (one sample per barcode folder):

```bash
cd /data/run1/fastq_pass
echo "sample,reads,mock" > ~/samplesheet.csv
for d in barcode*/; do
  for f in "$PWD/$d"*.fastq.gz; do echo "${d%/},$f," >> ~/samplesheet.csv; done
done
head ~/samplesheet.csv
```

Then edit `~/samplesheet.csv` to rename samples (e.g. `barcode01` → `lake_A`) or to add the mock name.

### Step 8. Tell Nextflow how much of the computer it may use

Create a file `server.config` with the CPUs and memory you can give the pipeline:

```groovy
process {
    resourceLimits = [ cpus: 16, memory: 64.GB, time: 48.h ]
}
```

On a shared server, use less than the total so others can work. Emu is the slowest step;
more CPUs make it faster.

### Step 9. Run

```bash
nextflow run YiannisGal/ont16s -r v0.3.1 \
    -profile docker \
    -c server.config \
    --input ~/samplesheet.csv \
    --emu_db /path/to/databases/emu_default \
    --outdir results \
    -resume
```

| Part               | Meaning                                                                         |
| ------------------ | ------------------------------------------------------------------------------- |
| `-r v0.3.1`        | the exact pipeline version (write it in your methods)                           |
| `-profile docker`  | software from containers (`singularity` / `conda` if you chose those)           |
| `-c server.config` | your CPU/memory limits                                                          |
| `--input`          | the samplesheet                                                                 |
| `--emu_db`         | the database folder                                                             |
| `--outdir`         | where results are written                                                       |
| `-resume`          | if the run stops, rerunning the same command continues instead of starting over |

Note: options of Nextflow itself have **one** dash (`-profile`, `-resume`); options of the
pipeline have **two** (`--input`).

**Long runs:** run in the background so closing the terminal does not stop it:

```bash
nohup nextflow run YiannisGal/ont16s -r v0.3.1 -profile docker -c server.config \
    --input ~/samplesheet.csv --emu_db /path/to/databases/emu_default \
    --outdir results -resume > run.log 2>&1 &
tail -f run.log          # watch progress; Ctrl+C stops watching, not the run
```

(`screen` or `tmux` work too.)

**How long?** Emu dominates. Measured on a shared 28-CPU server with the default database:
15 samples × 50,000 reads took ~6.5 h, and 10 samples × 300,000 reads ~9 h. The 546-read test
takes 2–3 minutes.

### Step 10. Useful options

| Option                                    | Example                    | When                                                              |
| ----------------------------------------- | -------------------------- | ----------------------------------------------------------------- |
| `--exclude_taxa`                          | `chloroplast,mitochondria` | remove organelle reads (needs a database that labels them, SILVA) |
| `--min_read_length` / `--max_read_length` | `1200` / `1800`            | different amplicon length (default 1000–2000 bp)                  |
| `--min_read_qual`                         | `10`                       | drop low-quality reads (default: off)                             |
| `--emu_mode`                              | `pooled`                   | force pooling of shallow samples (default `auto` decides)         |
| `--skip_novelty`                          |                            | skip the novel-organism analysis (faster)                         |
| `--skip_novel_otus`                       |                            | keep the novelty table but skip consensus OTUs                    |

All options: `nextflow run YiannisGal/ont16s -r v0.3.1 --help --show_hidden`, and
[usage.md](usage.md) for the reasoning behind each threshold.

---

## Part 3 — Read the results

Open these in this order:

1. **`results/multiqc/multiqc_report.html`** (open in a browser): read numbers and quality per
   sample, warnings, mock validation and novelty in one page.
2. **`results/ont16s_report/ont16s_warnings.tsv`**: every warning and why. Common ones:
   - `low_read_accuracy`: reads are < 90 % accurate (older chemistry or fast basecalling);
     trust genus more than species names.
   - low read numbers: few reads after filtering; abundances of rare taxa are uncertain.
3. **`results/emu/emu-combined-species.tsv`** and **`emu-combined-genus.tsv`**: the main result,
   taxa × samples, relative abundance (0–1). The `-counts` versions contain estimated read counts
   (use these for diversity statistics, e.g. in R with phyloseq or vegan).
4. **`results/mock_validation/mock_validation_summary.tsv`** (only with mock samples): did the
   control come out right? Look at `recall_detectable` (should be close to 1) and
   `bray_curtis_genus` (0 = perfect). Each missed taxon has a `status` explaining why
   (`below_detection_limit`, `not_amplified`, `genus_only`, `missed`).
5. **`results/novelty/`**: organisms not in the database.
   - `<sample>_novelty_summary.tsv`: `frac_novel_genus` = fraction of reads too distant for a
     genus name. Up to ~3–4 % is normal noise; more means real unknown organisms.
   - `novel_otus/novel_otus.tsv` and `.fasta`: consensus sequences of unknown lineages with the
     rank they can be named to (e.g. `family`) and reads per sample. Use the FASTA for BLAST or a
     phylogenetic tree.

All files are described in [output.md](output.md).

**Load the table in R:**

```r
ab <- read.delim("results/emu/emu-combined-genus.tsv", check.names = FALSE)
head(ab)
```

**Load it in Python:**

```python
import pandas as pd
ab = pd.read_csv("results/emu/emu-combined-genus.tsv", sep="\t")
print(ab.head())
```

---

## Part 4 — Problems and solutions

| Problem                                  | Solution                                                                                                     |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `nextflow: command not found`            | `source ~/.bashrc`, or check that `~/bin` is on your `PATH`                                                  |
| `permission denied ... docker.sock`      | `sudo usermod -aG docker $USER`, then log out and in                                                         |
| `Missing required parameter(s): input`   | add `--input samplesheet.csv` (two dashes), or use `-profile test,docker` for the test                       |
| Samplesheet error at start               | check the header `sample,reads,mock`, no spaces in names or paths, files exist, extensions as listed         |
| Mock definition missing                  | the `mock` value must be `zymo_msplus`, `zymo_d6306`, `zymo_d6331`, or your own via `--mock_definitions`     |
| Process killed / `exit status 137`       | out of memory: raise `memory` in `server.config` or run fewer samples at once                                |
| Run stopped (power cut, closed terminal) | run the same command again with `-resume`                                                                    |
| Disk full                                | the `work/` folder holds intermediate files; delete it after a successful run (`results/` is separate)       |
| Very few reads after filtering           | check the amplicon length in NanoPlot (`qc/nanoplot/raw`) and adjust `--min_read_length`/`--max_read_length` |

Still stuck: open an issue at <https://github.com/YiannisGal/ont16s/issues> with the command you
ran and the end of `.nextflow.log`.

---

## Part 5 — Cite and report

In your methods, write the version and database, e.g.:

> Reads were profiled with ont16s v0.3.1 (Galiatsatos, doi:10.5281/zenodo.24419883) using Emu
> 3.6.2 and the Emu default database, with Nextflow 25.10 and Docker.

The exact software versions are in `results/pipeline_info/` and the database checksums in
`results/pipeline_info/emu_db_provenance.tsv`. Also cite the tools listed in
[CITATIONS.md](../CITATIONS.md).
