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
include { NANOPLOT as NANOPLOT_FILTERED } from '../modules/nf-core/nanoplot/main'
include { UNTAR as UNTAR_EMU_DB  } from '../modules/nf-core/untar/main'
include { EMU_ABUNDANCE          } from '../modules/nf-core/emu/abundance/main'
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
    NANOPLOT_FILTERED ( CHOPPER.out.fastq )

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
    // MODULE: Emu taxonomic abundance
    //
    EMU_ABUNDANCE ( CHOPPER.out.fastq, ch_emu_db )

    //
    // MODULE: Record which Emu database was used (checksums, size)
    //
    EMU_DB_INFO ( ch_emu_db, params.emu_db )

    //
    // MODULE: Mock-community validation for samples with a 'mock' value
    //
    MOCK_VALIDATION (
        EMU_ABUNDANCE.out.report
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
        EMU_ABUNDANCE.out.report
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
    reads          = CHOPPER.out.fastq           // channel: [ val(meta), path(fastq.gz) ] filtered reads
    emu_abundance  = EMU_ABUNDANCE.out.report    // channel: [ val(meta), path(rel-abundance.tsv) ]
    emu_combined   = EMU_COMBINE.out.tables      // channel: [ path(emu-combined-*.tsv) ]
    multiqc_report = MULTIQC.out.report.map { _meta, report -> [report] }.toList() // channel: /path/to/multiqc_report.html
    versions       = ch_versions                 // channel: [ path(versions.yml) ]
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
