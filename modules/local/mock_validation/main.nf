process MOCK_VALIDATION {
    tag "${meta.id}"
    label 'process_single'

    // Standard-library Python only; reuses the Emu container (Python 3)
    conda "bioconda::emu=3.6.2 bioconda::minimap2=2.30 conda-forge::python=3.13.12"
    container "community.wave.seqera.io/library/emu:3.6.2--0adcfa4809f061f6"

    input:
    tuple val(meta), path(report), path(mock_definition), path(novelty_reads)

    output:
    tuple val(meta), path("*_mock_validation.tsv"), emit: taxa
    tuple val(meta), path("*_mock_summary.tsv")   , emit: summary
    tuple val("${task.process}"), val('python'), eval('python3 --version | sed "s/Python //"'), topic: versions, emit: versions_python

    when:
    task.ext.when == null || task.ext.when

    script:
    def args   = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    def novelty = novelty_reads ? "--novelty-reads ${novelty_reads}" : ''
    """
    mock_validation.py \\
        --sample ${meta.id} \\
        --mock-name ${meta.mock} \\
        --emu ${report} \\
        --mock ${mock_definition} \\
        --prefix ${prefix} \\
        ${novelty} \\
        ${args}
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}_mock_validation.tsv ${prefix}_mock_summary.tsv
    """
}
