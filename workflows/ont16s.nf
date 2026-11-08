/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT MODULES / SUBWORKFLOWS / FUNCTIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
include { SAMTOOLS_CAT           } from '../modules/nf-core/samtools/cat/main'
include { SAMTOOLS_FASTQ         } from '../modules/nf-core/samtools/fastq/main'
include { CAT_FASTQ              } from '../modules/nf-core/cat/fastq/main'
include { NANOPLOT as NANOPLOT_RAW      } from '../modules/nf-core/nanoplot/main'
include { CHOPPER                       } from '../modules/nf-core/chopper/main'
include { SEQKIT_RMDUP                  } from '../modules/nf-core/seqkit/rmdup/main'
include { NANOPLOT as NANOPLOT_FILTERED } from '../modules/nf-core/nanoplot/main'
include { UNTAR as UNTAR_EMU_DB  } from '../modules/nf-core/untar/main'
include { EMU_ABUNDANCE          } from '../modules/nf-core/emu/abundance/main'
include { EMU_ABUNDANCE as EMU_ABUNDANCE_POOLED } from '../modules/nf-core/emu/abundance/main'
include { EMU_POOL_READS         } from '../modules/local/emu_pool_reads/main'
include { EMU_SPLIT_POOLED       } from '../modules/local/emu_split_pooled/main'
include { EMU_POSTPROCESS        } from '../modules/local/emu_postprocess/main'
include { DB_FIT                 } from '../modules/local/db_fit/main'
include { NOVELTY                } from '../modules/local/novelty/main'
include { ONT16S_REPORT          } from '../modules/local/ont16s_report/main'
include { EMU_COMBINE            } from '../modules/local/emu_combine/main'
include { EMU_DB_INFO            } from '../modules/local/emu_db_info/main'
include { MOCK_VALIDATION        } from '../modules/local/mock_validation/main'
include { MULTIQC                } from '../modules/nf-core/multiqc/main'
include { paramsSummaryMap       } from 'plugin/nf-schema'
include { paramsSummaryMultiqc   } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { softwareVersionsToYAML } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { methodsDescriptionText } from '../subworkflows/local/utils_nfcore_ont16s_pipeline'

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    RUN MAIN WORKFLOW
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow ONT16S {

    take:
    ch_samplesheet // channel: samplesheet read in from --input
    multiqc_config
    multiqc_logo
    multiqc_methods_description
    outdir

    main:

    def ch_versions = channel.empty()
    def ch_multiqc_files = channel.empty()

    //
    // Prepare reads: one FASTQ per sample, whatever the input format.
    // ONT reads are never paired, so every sample is single-end.
    //
    def ch_input = ch_samplesheet
        .map { meta, reads -> [ meta + [ single_end: true ], reads ] }
        .branch { meta, reads ->
            bam_multi: meta.format == 'bam' && meta.n_files > 1
            bam:       meta.format == 'bam'
            // CAT_FASTQ merges chunks and gzips plain FASTQ (downstream tools need .gz)
            fastq_multi: meta.n_files > 1 || !reads[0].name.endsWith('.gz')
            fastq:     true
        }

    //
    // MODULE: Merge BAM chunks of the same sample
    //
    SAMTOOLS_CAT ( ch_input.bam_multi )

    //
    // MODULE: Unaligned BAM -> FASTQ. Unpaired ONT reads go to the `other` output.
    //
    SAMTOOLS_FASTQ (
        ch_input.bam
            .map { meta, reads -> [ meta, reads[0] ] }
            .mix ( SAMTOOLS_CAT.out.bam ),
        false
    )

    //
    // MODULE: Merge FASTQ chunks of the same sample
    //
    CAT_FASTQ ( ch_input.fastq_multi )

    def ch_reads = SAMTOOLS_FASTQ.out.other
        .mix ( CAT_FASTQ.out.reads )
        .mix ( ch_input.fastq.map { meta, reads -> [ meta, reads[0] ] } )

    //
    // MODULES: Read QC before and after length/quality filtering
    //
    NANOPLOT_RAW ( ch_reads )
    CHOPPER ( ch_reads, [] )

    //
    // MODULE: Remove duplicate reads (same read ID written twice, e.g. overlapping chunks)
    //
    SEQKIT_RMDUP ( CHOPPER.out.fastq )
    def ch_filtered = SEQKIT_RMDUP.out.fastx
    NANOPLOT_FILTERED ( ch_filtered )

    ch_multiqc_files = ch_multiqc_files
        .mix ( NANOPLOT_RAW.out.txt.map { _meta, txt -> txt } )
        .mix ( NANOPLOT_FILTERED.out.txt.map { _meta, txt -> txt } )

    //
    // Emu database: a directory, or an archive that is unpacked first
    //
    def ch_emu_db
    if (params.emu_db ==~ /.*\.(tar\.gz|tgz|tar)$/) {
        UNTAR_EMU_DB ( channel.value([ [ id: 'emu_db' ], file(params.emu_db, checkIfExists: true) ]) )
        ch_emu_db = UNTAR_EMU_DB.out.untar.map { _meta, db -> db }
    } else {
        ch_emu_db = channel.value(file(params.emu_db, checkIfExists: true))
    }

    //
    // Emu mode: per sample, or pooled across samples (one shared abundance floor).
    // 'auto' pools when many samples are shallow (see decideEmuMode below).
    //
    def ch_filtered_counts = NANOPLOT_FILTERED.out.txt
        .map { meta, txt -> [ meta.id, nanostatReads(txt) ] }
    def ch_mode = ch_filtered_counts.toList().map { counts -> decideEmuMode(counts) }
    def ch_for_emu = ch_filtered.combine(ch_mode)

    //
    // MODULE: Emu per sample
    //
    EMU_ABUNDANCE (
        ch_for_emu
            .filter { _meta, _reads, decision -> decision.emu_mode == 'per_sample' }
            .map { meta, reads, _decision -> [ meta, reads ] },
        ch_emu_db
    )

    //
    // MODULES: Emu pooled: tag reads with their sample, run Emu once, split per sample
    //
    EMU_POOL_READS (
        ch_for_emu
            .filter { _meta, _reads, decision -> decision.emu_mode == 'pooled' }
            .map { meta, reads, _decision -> [ meta.id, reads ] }
            .toList()
            .filter { pairs -> pairs }
            .map { pairs -> [ pairs.collect { pair -> pair[0] }, pairs.collect { pair -> pair[1] } ] }
    )
    EMU_ABUNDANCE_POOLED (
        EMU_POOL_READS.out.fastq.map { reads -> [ [ id: 'pooled', single_end: true ], reads ] },
        ch_emu_db
    )
    EMU_SPLIT_POOLED (
        EMU_ABUNDANCE_POOLED.out.report.map { _meta, report -> report },
        EMU_ABUNDANCE_POOLED.out.assignment_report.map { _meta, tsv -> tsv },
        EMU_ABUNDANCE_POOLED.out.unclassified.map { _meta, files -> files }.ifEmpty([]),
        EMU_ABUNDANCE_POOLED.out.unmapped.map { _meta, files -> files }.ifEmpty([]),
        EMU_POOL_READS.out.counts
    )
    def ch_meta_by_id = ch_filtered.map { meta, _reads -> [ meta.id, meta ] }
    def ch_split = EMU_SPLIT_POOLED.out.reports
        .flatten()
        .map { report -> [ report.name - '_rel-abundance.tsv', report ] }
        .join(ch_meta_by_id)
        .map { _id, report, meta -> [ meta, report ] }

    //
    // MODULE: Per-sample post-processing (taxon exclusion, metrics) for both modes
    //
    EMU_POSTPROCESS (
        EMU_ABUNDANCE.out.report
            .mix(ch_split)
            .combine(ch_mode)
            .map { meta, report, decision -> [ meta, report, decision.emu_mode ] }
    )
    def ch_emu_report = EMU_POSTPROCESS.out.report

    //
    // MODULE: How well do reads match the database (informational)
    //
    def ch_db_fit = channel.value([])
    if (!params.skip_db_fit) {
        DB_FIT (
            ch_filtered
                .map { meta, reads -> [ meta.id, reads ] }
                .toList()
                .map { pairs -> [ pairs.collect { pair -> pair[0] }, pairs.collect { pair -> pair[1] } ] },
            ch_emu_db,
            params.db_fit_reads
        )
        ch_db_fit = DB_FIT.out.tsv
    }

    //
    // MODULE: Novelty — which rank does each read's similarity to the database support
    //
    if (!params.skip_novelty) {
        NOVELTY ( ch_filtered, ch_emu_db )
        def ch_novelty_summary = NOVELTY.out.summary
            .map { _meta, tsv -> tsv }
            .collectFile(name: 'novelty_summary.tsv', keepHeader: true, sort: true, storeDir: "${params.outdir}/novelty")
        ch_multiqc_files = ch_multiqc_files.mix(ch_novelty_summary)
    }

    //
    // MODULE: Run summary and warnings
    //
    def ch_decision = ch_mode
        .map { d -> "emu_mode\trule\treason\n${d.emu_mode}\t${d.rule}\t${d.reason}\n" }
        .collectFile(name: 'emu_mode_decision.tsv')
    ONT16S_REPORT (
        EMU_POSTPROCESS.out.metrics.map { _meta, tsv -> tsv }.collect(),
        NANOPLOT_RAW.out.txt.map { _meta, txt -> txt }.collect(),
        NANOPLOT_FILTERED.out.txt.map { _meta, txt -> txt }.collect(),
        SEQKIT_RMDUP.out.log.map { _meta, log -> log }.collect(),
        ch_decision,
        ch_db_fit
    )
    ch_multiqc_files = ch_multiqc_files
        .mix(ONT16S_REPORT.out.summary)
        .mix(ONT16S_REPORT.out.warnings)

    //
    // MODULE: Record which Emu database was used (checksums, size)
    //
    EMU_DB_INFO ( ch_emu_db, params.emu_db )

    //
    // MODULE: Mock-community validation for samples with a 'mock' value
    //
    MOCK_VALIDATION (
        ch_emu_report
            .filter { meta, _report -> meta.mock }
            // Definition file existence is checked during samplesheet validation
            .map { meta, report -> [ meta, report, file("${params.mock_definitions ?: "${projectDir}/assets/mocks"}/${meta.mock}.tsv") ] }
    )

    def ch_mock_summary = MOCK_VALIDATION.out.summary
        .map { _meta, summary -> summary }
        .collectFile(
            name: 'mock_validation_summary.tsv',
            keepHeader: true,
            sort: true
        )
        // Publish only if there is a summary (storeDir would create an empty folder for runs without mocks)
        .map { summary ->
            def mock_dir = file("${outdir}/mock_validation")
            mock_dir.mkdirs()
            summary.copyTo(mock_dir.resolve(summary.name))
            summary
        }
    ch_multiqc_files = ch_multiqc_files.mix(ch_mock_summary)

    //
    // MODULE: Combine per-sample Emu tables into one table per rank
    //
    EMU_COMBINE (
        ch_emu_report
            .map { _meta, report -> report }
            .collect()
    )

    //
    // Collate and save software versions
    //
    def topic_versions = channel.topic("versions")
        .distinct()
        .branch { entry ->
            versions_file: entry instanceof Path
            versions_tuple: true
        }

    def topic_versions_string = topic_versions.versions_tuple
        .map { process, tool, version ->
            [ process[process.lastIndexOf(':')+1..-1], "  ${tool}: ${version}" ]
        }
        .groupTuple(by:0)
        .map { process, tool_versions ->
            tool_versions.unique().sort()
            "${process}:\n${tool_versions.join('\n')}"
        }

    def ch_collated_versions = softwareVersionsToYAML(ch_versions.mix(topic_versions.versions_file))
        .mix(topic_versions_string)
        .collectFile(
            storeDir: "${outdir}/pipeline_info",
            name:  'ont16s_software_'  + 'mqc_'  + 'versions.yml',
            sort: true,
            newLine: true
        )

    //
    // MODULE: MultiQC
    //
    ch_multiqc_files = ch_multiqc_files.mix(ch_collated_versions)
    def ch_summary_params = paramsSummaryMap(workflow, parameters_schema: "nextflow_schema.json")
    def ch_workflow_summary = channel.value(paramsSummaryMultiqc(ch_summary_params))
    ch_multiqc_files = ch_multiqc_files.mix(ch_workflow_summary.collectFile(name: 'workflow_summary_mqc.yaml'))
    def ch_multiqc_custom_methods_description = multiqc_methods_description
        ? file(multiqc_methods_description, checkIfExists: true)
        : file("${projectDir}/assets/methods_description_template.yml", checkIfExists: true)
    def ch_methods_description = channel.value(methodsDescriptionText(ch_multiqc_custom_methods_description))
    ch_multiqc_files = ch_multiqc_files.mix(ch_methods_description.collectFile(name: 'methods_description_mqc.yaml', sort: true))
    MULTIQC(
        ch_multiqc_files.flatten().collect().map { files ->
            [
                [id: 'ont16s'],
                files,
                multiqc_config
                    ? file(multiqc_config, checkIfExists: true)
                    : file("${projectDir}/assets/multiqc_config.yml", checkIfExists: true),
                multiqc_logo ? file(multiqc_logo, checkIfExists: true) : [],
                [],
                [],
            ]
        }
    )
    emit:
    reads          = ch_filtered           // channel: [ val(meta), path(fastq.gz) ] filtered reads
    emu_abundance  = ch_emu_report               // channel: [ val(meta), path(rel-abundance.tsv) ]
    emu_combined   = EMU_COMBINE.out.tables      // channel: [ path(emu-combined-*.tsv) ]
    multiqc_report = MULTIQC.out.report.map { _meta, report -> [report] }.toList() // channel: /path/to/multiqc_report.html
    versions       = ch_versions                 // channel: [ path(versions.yml) ]
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    FUNCTIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

// Number of reads from a NanoPlot NanoStats file
def nanostatReads(txt) {
    def line = txt.readLines().find { l -> l.startsWith('number_of_reads') }
    return line ? (line.split(/\s+/)[1] as double) as long : 0L
}

// Choose 'per_sample' or 'pooled' Emu. In 'auto', pool when at least --pool_min_fraction of
// samples have fewer than --pool_min_reads filtered reads: Emu's per-sample abundance floor
// (10/n reads) then discards many reads of shallow, diverse samples (ST-005).
def decideEmuMode(counts) {
    def rule = "pooled if >= ${params.pool_min_fraction} of samples have < ${params.pool_min_reads} filtered reads"
    if (params.emu_mode != 'auto') {
        return [ emu_mode: params.emu_mode, rule: 'set by --emu_mode', reason: "--emu_mode ${params.emu_mode}" ]
    }
    def low = counts.count { pair -> pair[1] < params.pool_min_reads }
    def frac = counts ? low / counts.size() : 0
    def pool = counts.size() > 1 && frac >= params.pool_min_fraction
    def reason = "auto: ${low} of ${counts.size()} samples have < ${params.pool_min_reads} filtered reads (fraction ${String.format('%.2f', frac as double)})"
    return [ emu_mode: pool ? 'pooled' : 'per_sample', rule: rule, reason: reason ]
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
