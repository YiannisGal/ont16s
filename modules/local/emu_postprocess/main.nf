process EMU_POSTPROCESS {
    tag "${meta.id}"
    label 'process_single'

    conda "bioconda::emu=3.6.2"
    container "community.wave.seqera.io/library/emu:3.6.2--0adcfa4809f061f6"

    input:
    tuple val(meta), path(report, stageAs: 'input/*'), val(mode)

    output:
    tuple val(meta), path("*_rel-abundance.tsv"), emit: report
    tuple val(meta), path("*_emu_metrics.tsv")  , emit: metrics
    tuple val("${task.process}"), val('python'), eval('python3 --version | sed "s/Python //"'), topic: versions, emit: versions_python

    when:
    task.ext.when == null || task.ext.when

    script:
    def args   = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    emu_postprocess.py \\
        --input ${report} \\
        --sample ${meta.id} \\
        --prefix ${prefix} \\
        --mode ${mode} \\
        ${args}
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}_rel-abundance.tsv ${prefix}_emu_metrics.tsv
    """
}
