# YiannisGal/ont16s: Usage

> _Documentation of pipeline parameters is generated automatically from the pipeline schema and can no longer be found in markdown files._

## Introduction

<!-- TODO nf-core: Add documentation about anything specific to running your pipeline. For general topics, please point to (and add to) the main nf-core website. -->

## Samplesheet input

You will need to create a samplesheet with information about the samples you would like to analyse before running the pipeline. Use this parameter to specify its location. It has to be a comma-separated file with a header row and the columns described below.

```bash
--input '[path to samplesheet file]'
```

Each row is **one reads file**. Reads can be unaligned ONT BAM files (as written by dorado) or FASTQ files (plain or gzipped).

For real (non-mock) samples leave `mock` empty; every step except mock validation runs:

```csv title="samplesheet.csv"
sample,reads,mock
soil_rep1,/data/soil_rep1.fastq.gz,
lake_rep1,/data/lake_rep1.fastq.gz,
```

### Multiple files of the same sample

ONT output is often split into chunks (`..._0.bam`, `..._1.bam`, ...). Give every chunk its own row with the **same** `sample` name; the pipeline groups them into one sample. All files of a sample must be the same format (all BAM or all FASTQ) and have the same `mock` value.

```csv title="samplesheet.csv"
sample,reads,mock
zymo_msplus_rep1,FBB32095_bam_pass_15aa3986_bbffde72_0.bam,zymo_msplus
zymo_msplus_rep1,FBB32095_bam_pass_15aa3986_bbffde72_1.bam,zymo_msplus
soil_A,soil_A.fastq.gz,
```

| Column   | Required | Description                                                                                                                             |
| -------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `sample` | yes      | Sample name, no spaces. Identical for all files of the same sample.                                                                     |
| `reads`  | yes      | Path or URL to a reads file with extension `.bam`, `.fastq`, `.fq`, `.fastq.gz` or `.fq.gz`. No spaces.                                 |
| `mock`   | no       | Name of the mock community this sample contains (e.g. `zymo_msplus`), used for mock-community validation. Leave empty for real samples. |

Basecalling model and kit are not samplesheet columns: they will be read from the BAM header (planned).

An [example samplesheet](../assets/samplesheet.csv) has been provided with the pipeline.

## Running the pipeline

The typical command for running the pipeline is as follows:

```bash
nextflow run YiannisGal/ont16s --input ./samplesheet.csv --emu_db /path/to/emu_db --outdir ./results  -profile docker
```

## Read filtering

Reads are filtered with [chopper](https://github.com/wdecoster/chopper) before profiling, and
summarised with [NanoPlot](https://github.com/wdecoster/NanoPlot) before and after filtering
(`qc/nanoplot/raw`, `qc/nanoplot/filtered`, and the MultiQC report).

| Parameter           | Default | Meaning                                    |
| ------------------- | ------- | ------------------------------------------ |
| `--min_read_length` | 1000    | Minimum read length (bp)                   |
| `--max_read_length` | 2000    | Maximum read length (bp)                   |
| `--min_read_qual`   | 0       | Minimum mean read quality (Phred); 0 = off |

The defaults come from one Zymo R10.4.1 SUP run (`docs/server-tasks/ST-003-results.md`): the
length window removed ~8 % of reads, mostly truncated amplicons and reads > 2 kb that were
enriched for spurious taxa. They are provisional; adjust them for other primers or chemistries.

## Choosing a database

The database decides which taxa can be reported and how they are named. Measured on 2,000 reads
from a lake-sediment core (R10.4.1 fast basecalling, per-sample Emu, ST-007):

| Database                                       | Size       | Time  | Peak memory | Mapped reads unclassified | Notes                                                                                           |
| ---------------------------------------------- | ---------- | ----- | ----------- | ------------------------- | ----------------------------------------------------------------------------------------------- |
| Emu default (rrnDB + NCBI RefSeq, 2020)        | 49 k seqs  | 17 s  | 1.2 GB      | 46 %                      | species level; few environmental lineages                                                       |
| Emu prebuilt SILVA 138.2                       | 2.2 M seqs | 104 s | 16.9 GB     | 73 %                      | one taxon per sequence: support is split, most reads fall below Emu's floor                     |
| **SILVA 138.2 grouped by genus** (built below) | 79 k seqs  | 14 s  | 0.9 GB      | 32 %                      | genus level, SILVA names; detects sediment phyla (Zixibacteria, Atribacterota, Acetothermia, …) |

For environmental samples rich in uncultured lineages, the genus-level SILVA database is the
better choice; for well-characterised communities (mocks, host-associated) the default
database gives species-level names. It also labels organelles, which `--exclude_taxa` needs.

Build the genus-level SILVA database (once):

```bash
# Emu prebuilt SILVA 138.2 (OSF project 56uf7, file emu-prebuilt/silva-138.2.tar, ~680 MB)
pip install osfclient && osf -p 56uf7 fetch osfstorage/emu-prebuilt/silva-138.2.tar
mkdir emu_silva && tar -xf silva-138.2.tar -C emu_silva --exclude='./._*'
mkdir emu_silva_genus20 && cd emu_silva_genus20
python3 /path/to/ont16s/bin/build_silva_genus_db.py ../emu_silva 20
```

Then run with `--emu_db /path/to/emu_silva_genus20`. SILVA is licensed CC BY 4.0; cite SILVA
(Quast et al. 2013) and Emu (Curry et al. 2022).

## Emu mode: per sample or pooled (`--emu_mode`)

Emu removes taxa below an abundance floor of `10 / n` reads (n > 1,000) **per run**. Run per
sample, shallow and diverse samples lose many reads: in a lake-sediment core (ST-005), samples
with fewer than 3,000 reads had a median of 44 % reads unassigned, versus 11 % for samples with
more than 10,000 reads.

| `--emu_mode`     | What happens                                                                                                                               | Use for                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------- |
| `auto` (default) | `pooled` if at least `--pool_min_fraction` (0.25) of samples have fewer than `--pool_min_reads` (10,000) filtered reads, else `per_sample` | most runs                       |
| `per_sample`     | Emu once per sample                                                                                                                        | few, deeply sequenced samples   |
| `pooled`         | reads of all samples are tagged with their sample, Emu runs once (one shared floor), the result is split back into per-sample tables       | many shallow or diverse samples |

The decision and its reason are written to `ont16s_report/ont16s_warnings.tsv` and the MultiQC
report. In pooled mode a single Emu task processes all reads, so it needs more memory and time
(`EMU_ABUNDANCE_POOLED`: 16 CPUs, 32 GB by default). Pooling shares the abundance floor across
samples: a taxon well supported in some samples can be reported in others with few reads.

## Taxon exclusion (`--exclude_taxa`)

Taxa whose lineage contains any of the comma-separated terms are removed and abundances
renormalised, e.g. `--exclude_taxa chloroplast,mitochondria` for plant- or host-associated
samples. The removed fraction is reported per sample. Organelle reads are always reported
(`organelle_frac`), but only databases that label organelles (such as SILVA) can detect them;
Emu's default database does not.

## Run checks and warnings

`ont16s_report/ont16s_run_summary.tsv` (one row per sample) and `ont16s_warnings.tsv` (one row per
warning, with its reason) are also shown in MultiQC:

| Check                                                      | Default threshold | Parameter            |
| ---------------------------------------------------------- | ----------------- | -------------------- |
| Few reads after filtering                                  | < 1,000           | `--min_sample_reads` |
| Most reads removed by the filter (e.g. degraded libraries) | > 50 %            | `--warn_filter_loss` |
| Many reads not assigned to a taxon                         | > 20 %            | `--warn_unassigned`  |
| Many organelle reads                                       | > 5 %             | `--warn_organelle`   |

**Database fit** (`qc/db_fit/db_fit.tsv`): the best-hit identity of the first `--db_fit_reads`
(500) reads per sample against the database (minimap2). It is informational: read errors lower
identity too, so compare samples or databases with the same chemistry and basecalling, not
absolute values. On Zymo R10.4.1 SUP reads against a database containing the mock species, the
median identity was 0.99. Skip with `--skip_db_fit`.

## Mock-community validation

Samples with a `mock` value in the samplesheet are compared with a mock definition
`<mock_definitions>/<mock>.tsv` (default directory: `assets/mocks/`). The run stops at the
start if a definition is missing. To use your own mock, create a TSV like
`assets/mocks/zymo_msplus.tsv` and pass its directory with `--mock_definitions`:

| Column               | Meaning                                                                                                            |
| -------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `species`            | Expected species name                                                                                              |
| `aliases`            | Other names it may have in your database, `;`-separated (e.g. `Borrelia burgdorferi` vs `Borreliella burgdorferi`) |
| `expected_abundance` | Expected fraction of 16S reads, or `NA` if unknown                                                                 |
| `source`             | Where the expectation comes from                                                                                   |

Reported per mock sample: expected taxa detected (recall), unexpected taxa split into
near-neighbours (same genus as an expected taxon) and off-target taxa, false positives at or
above `--mock_min_abundance` (default 0.001 = 0.1 %), and the L1 distance to the expected
proportions when all expected abundances are given.

Limits: false positives depend on depth (with < 1,000 reads a single read exceeds 0.1 %); the
genus rule cannot see that e.g. _Shigella_ is nested within _E. coli_; proportions are not
assessed when expected abundances are `NA` (as for the shipped `zymo_msplus` definition).

## Emu database (`--emu_db`, required)

Emu assigns reads by aligning them to a reference database, and the database choice strongly
affects species names and assignments. `--emu_db` accepts:

- a directory containing `species_taxid.fasta` and `taxonomy.tsv`, or
- a `.tar`, `.tar.gz` or `.tgz` archive of such a directory (local path or URL); it is unpacked automatically.

Emu's prebuilt default database (rrnDB v5.6 + NCBI 16S RefSeq, 2020-09-17) can be downloaded from
OSF project `56uf7` (`emu-prebuilt/emu.tar`) and passed directly as `--emu_db emu.tar`.
Any other Emu-format database (e.g. SILVA, GTDB or a custom environmental database) works the same way.

`--emu_type` sets the minimap2 preset used by Emu (default `map-ont`). In our tests `lr:hq` was
about 15x faster on R10.4.1 SUP reads, but left more reads unmapped; it is not yet validated.

This will launch the pipeline with the `docker` configuration profile. See below for more information about profiles.

Note that the pipeline will create the following files in your working directory:

```bash
work                # Directory containing the nextflow working files
<OUTDIR>            # Finished results in specified location (defined with --outdir)
.nextflow_log       # Log file from Nextflow
# Other nextflow hidden files, eg. history of pipeline runs and old logs.
```

If you wish to repeatedly use the same parameters for multiple runs, rather than specifying each flag in the command, you can specify these in a params file.

Pipeline settings can be provided in a `yaml` or `json` file via `-params-file <file>`.

> [!WARNING]
> Do not use `-c <file>` to specify parameters as this will result in errors. Custom config files specified with `-c` must only be used for [tuning process resource specifications](https://nf-co.re/docs/running/run-pipelines#configuring-pipelines), other infrastructural tweaks (such as output directories), or module arguments (args).

The above pipeline run specified with a params file in yaml format:

```bash
nextflow run YiannisGal/ont16s -profile docker -params-file params.yaml
```

with:

```yaml title="params.yaml"
input: './samplesheet.csv'
outdir: './results/'
<...>
```

You can also generate such `YAML`/`JSON` files via [nf-core/launch](https://nf-co.re/launch).

### Updating the pipeline

When you run the above command, Nextflow automatically pulls the pipeline code from GitHub and stores it as a cached version. When running the pipeline after this, it will always use the cached version if available - even if the pipeline has been updated since. To make sure that you're running the latest version of the pipeline, make sure that you regularly update the cached version of the pipeline:

```bash
nextflow pull YiannisGal/ont16s
```

### Reproducibility

It is a good idea to specify the pipeline version when running the pipeline on your data. This ensures that a specific version of the pipeline code and software are used when you run your pipeline. If you keep using the same tag, you'll be running the same version of the pipeline, even if there have been changes to the code since.

First, go to the [YiannisGal/ont16s releases page](https://github.com/YiannisGal/ont16s/releases) and find the latest pipeline version - numeric only (eg. `1.3.1`). Then specify this when running the pipeline with `-r` (one hyphen) - eg. `-r 1.3.1`. Of course, you can switch to another version by changing the number after the `-r` flag.

This version number will be logged in reports when you run the pipeline, so that you'll know what you used when you look back in the future. For example, at the bottom of the MultiQC reports.

To further assist in reproducibility, you can use share and reuse [parameter files](#running-the-pipeline) to repeat pipeline runs with the same settings without having to write out a command with every single parameter.

> [!TIP]
> If you wish to share such profile (such as upload as supplementary material for academic publications), make sure to NOT include cluster specific paths to files, nor institutional specific profiles.

## Core Nextflow arguments

> [!NOTE]
> These options are part of Nextflow and use a _single_ hyphen (pipeline parameters use a double-hyphen)

### `-profile`

Use this parameter to choose a configuration profile. Profiles can give configuration presets for different compute environments.

Several generic profiles are bundled with the pipeline which instruct the pipeline to use software packaged using different methods (Docker, Singularity, Podman, Shifter, Charliecloud, Apptainer, Conda) - see below.

> [!IMPORTANT]
> We highly recommend the use of Docker or Singularity containers for full pipeline reproducibility, however when this is not possible, Conda is also supported.

The pipeline also dynamically loads configurations from [https://github.com/nf-core/configs](https://github.com/nf-core/configs) when it runs, making multiple config profiles for various institutional clusters available at run time. For more information and to check if your system is supported, please see the [nf-core/configs documentation](https://github.com/nf-core/configs#documentation).

Note that multiple profiles can be loaded, for example: `-profile test,docker` - the order of arguments is important!
They are loaded in sequence, so later profiles can overwrite earlier profiles.

If `-profile` is not specified, the pipeline will run locally and expect all software to be installed and available on the `PATH`. This is _not_ recommended, since it can lead to different results on different machines dependent on the computer environment.

- `test`
  - A profile with a complete configuration for automated testing
  - Includes links to test data so needs no other parameters
- `docker`
  - A generic configuration profile to be used with [Docker](https://docker.com/)
- `singularity`
  - A generic configuration profile to be used with [Singularity](https://sylabs.io/docs/)
- `podman`
  - A generic configuration profile to be used with [Podman](https://podman.io/)
- `shifter`
  - A generic configuration profile to be used with [Shifter](https://nersc.gitlab.io/development/shifter/how-to-use/)
- `charliecloud`
  - A generic configuration profile to be used with [Charliecloud](https://charliecloud.io/)
- `apptainer`
  - A generic configuration profile to be used with [Apptainer](https://apptainer.org/)
- `wave`
  - A generic configuration profile to enable [Wave](https://seqera.io/wave/) containers. Use together with one of the above (requires Nextflow `24.03.0-edge` or later).
- `conda`
  - A generic configuration profile to be used with [Conda](https://conda.io/docs/). Please only use Conda as a last resort i.e. when it's not possible to run the pipeline with Docker, Singularity, Podman, Shifter, Charliecloud, or Apptainer.

### `-resume`

Specify this when restarting a pipeline. Nextflow will use cached results from any pipeline steps where the inputs are the same, continuing from where it got to previously. For input to be considered the same, not only the names must be identical but the files' contents as well. For more info about this parameter, see [this blog post](https://www.nextflow.io/blog/2019/demystifying-nextflow-resume.html).

You can also supply a run name to resume a specific run: `-resume [run-name]`. Use the `nextflow log` command to show previous run names.

### `-c`

Specify the path to a specific config file (this is a core Nextflow command). See the [nf-core website documentation](https://nf-co.re/usage/configuration) for more information.

## Custom configuration

### Resource requests

Whilst the default requirements set within the pipeline will hopefully work for most people and with most input data, you may find that you want to customise the compute resources that the pipeline requests. Each step in the pipeline has a default set of requirements for number of CPUs, memory and time. For most of the pipeline steps, if the job exits with any of the error codes specified [here](https://github.com/nf-core/rnaseq/blob/4c27ef5610c87db00c3c5a3eed10b1d161abf575/conf/base.config#L18) it will automatically be resubmitted with higher resources request (2 x original, then 3 x original). If it still fails after the third attempt then the pipeline execution is stopped.

To change the resource requests, please see the [max resources](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources) and [customise process resources](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#customize-process-resources) section of the nf-core website.

### Custom Containers

In some cases, you may wish to change the container or conda environment used by a pipeline steps for a particular tool. By default, nf-core pipelines use containers and software from the [biocontainers](https://biocontainers.pro/) or [bioconda](https://bioconda.github.io/) projects. However, in some cases the pipeline specified version maybe out of date.

To use a different container from the default container or conda environment specified in a pipeline, please see the [updating tool versions](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#update-tool-versions) section of the nf-core website.

### Custom Tool Arguments

A pipeline might not always support every possible argument or option of a particular tool used in pipeline. Fortunately, nf-core pipelines provide some freedom to users to insert additional parameters that the pipeline does not include by default.

To learn how to provide additional arguments to a particular tool of the pipeline, please see the [customising tool arguments](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#modifying-tool-arguments) section of the nf-core website.

### nf-core/configs

In most cases, you will only need to create a custom config as a one-off but if you and others within your organisation are likely to be running nf-core pipelines regularly and need to use the same settings regularly it may be a good idea to request that your custom config file is uploaded to the `nf-core/configs` git repository. Before you do this please can you test that the config file works with your pipeline of choice using the `-c` parameter. You can then create a pull request to the `nf-core/configs` repository with the addition of your config file, associated documentation file (see examples in [`nf-core/configs/docs`](https://github.com/nf-core/configs/tree/master/docs)), and amending [`nfcore_custom.config`](https://github.com/nf-core/configs/blob/master/nfcore_custom.config) to include your custom profile.

See the main [Nextflow documentation](https://www.nextflow.io/docs/latest/config.html) for more information about creating your own configuration files.

If you have any questions or issues please send us a message on [Slack](https://nf-co.re/join/slack) on the [`#configs` channel](https://nfcore.slack.com/channels/configs).

## Running in the background

Nextflow handles job submissions and supervises the running jobs. The Nextflow process must run until the pipeline is finished.

The Nextflow `-bg` flag launches Nextflow in the background, detached from your terminal so that the workflow does not stop if you log out of your session. The logs are saved to a file.

Alternatively, you can use `screen` / `tmux` or similar tool to create a detached session which you can log back into at a later time.
Some HPC setups also allow you to run nextflow within a cluster job submitted your job scheduler (from where it submits more jobs).

## Nextflow memory requirements

In some cases, the Nextflow Java virtual machines can start to request a large amount of memory.
We recommend adding the following line to your environment to limit this (typically in `~/.bashrc` or `~./bash_profile`):

```bash
NXF_OPTS='-Xms1g -Xmx4g'
```
