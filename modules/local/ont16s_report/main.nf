process ONT16S_REPORT {
    label 'process_single'

    conda "bioconda::emu=3.6.2"
    container "community.wave.seqera.io/library/emu:3.6.2--0adcfa4809f061f6"

    input:
    path metrics , stageAs: 'metrics/*'
    path raw     , stageAs: 'raw/*'
    path filtered, stageAs: 'filtered/*'
    path decision
    path db_fit

    output:
    path "ont16s_run_summary.tsv", emit: summary
    path "ont16s_warnings.tsv"   , emit: warnings
    tuple val("${task.process}"), val('python'), eval('python3 --version | sed "s/Python //"'), topic: versions, emit: versions_python

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def fit  = db_fit ? "--db-fit ${db_fit}" : ''
    """
    ont16s_report.py \\
        --metrics-dir metrics \\
        --raw-dir raw \\
        --filtered-dir filtered \\
        --decision ${decision} \\
        ${fit} \\
        ${args}
    """

    stub:
    """
    touch ont16s_run_summary.tsv ont16s_warnings.tsv
    """
}
