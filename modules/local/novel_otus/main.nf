process NOVEL_OTUS {
    tag "${ids.size()} samples"
    label 'process_medium'

    conda "bioconda::vsearch=2.30.0 bioconda::racon=1.5.0 bioconda::minimap2=2.29 conda-forge::python=3.12"
    container "community.wave.seqera.io/library/vsearch_racon_minimap2_python:a507b673851c3369"

    input:
    tuple val(ids), path(tables, stageAs: 'tables/?/*'), path(reads, stageAs: 'reads/?/*')
    path db

    output:
    path "novel_otus.fasta"           , emit: fasta
    path "novel_otus.tsv"             , emit: tsv
    path "novel_reads_per_sample.tsv" , emit: counts
    tuple val("${task.process}"), val('vsearch'), eval('vsearch --version 2>&1 | head -1 | sed "s/vsearch v//; s/_.*//"'), topic: versions, emit: versions_vsearch
    tuple val("${task.process}"), val('racon'), eval('racon --version | sed "s/v//"'), topic: versions, emit: versions_racon

    when:
    task.ext.when == null || task.ext.when

    script:
    // Pool reads too distant for a genus name, cluster, polish consensus, classify
    def args  = task.ext.args ?: ''
    def t     = tables instanceof List ? tables : [tables]
    def r     = reads instanceof List ? reads : [reads]
    def pairs = [ids, t, r].transpose().collect { id, tab, fq -> "${id}=${tab}:${fq}" }.join(' ')
    """
    novel_select.py ${pairs}
    novel_consensus.py \\
        --reads novel_reads.fastq \\
        --db ${db} \\
        --threads ${task.cpus} \\
        ${args}
    rm -rf work_otu all.fasta novel_reads.fastq
    """

    stub:
    """
    touch novel_otus.fasta novel_otus.tsv novel_reads_per_sample.tsv
    """
}
