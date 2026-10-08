process EMU_SPLIT_POOLED {
    tag "pooled"
    label 'process_single'

    conda "bioconda::emu=3.6.2"
    container "community.wave.seqera.io/library/emu:3.6.2--0adcfa4809f061f6"

    input:
    path report
    path assignments
    path unclassified
    path unmapped
    path counts

    output:
    path "split/*_rel-abundance.tsv", emit: reports
    tuple val("${task.process}"), val('python'), eval('python3 --version | sed "s/Python //"'), topic: versions, emit: versions_python

    when:
    task.ext.when == null || task.ext.when

    script:
    """
    mkdir split
    emu_split_pooled.py \\
        --pooled ${report} \\
        --assignments ${assignments} \\
        --unclassified ${unclassified} \\
        --unmapped ${unmapped} \\
        --counts ${counts} \\
        --outdir split
    """

    stub:
    """
    mkdir split
    """
}
