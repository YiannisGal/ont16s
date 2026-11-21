process ONT16S_REPORT {
    label 'process_single'

    conda "bioconda::emu=3.6.2 bioconda::minimap2=2.30 conda-forge::python=3.13.12"
    container "community.wave.seqera.io/library/emu:3.6.2--0adcfa4809f061f6"

    input:
    path metrics , stageAs: 'metrics/*'
    path raw     , stageAs: 'raw/*'
    path filtered, stageAs: 'filtered/*'
    path dedup   , stageAs: 'dedup/*'
    path decision
    path db_fit
    path novelty

    output:
    path "ont16s_run_summary.tsv", emit: summary
    path "ont16s_warnings.tsv"   , emit: warnings
    tuple val("${task.process}"), val('python'), eval('python3 --version | sed "s/Python //"'), topic: versions, emit: versions_python

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def fit  = db_fit ? "--db-fit ${db_fit}" : ''
    def nov  = novelty ? "--novelty ${novelty}" : ''
    """
    ont16s_report.py \\
        --metrics-dir metrics \\
        --raw-dir raw \\
        --filtered-dir filtered \\
        --dedup-dir dedup \\
        --decision ${decision} \\
        ${fit} \\
        ${nov} \\
        ${args}
    """

    stub:
    """
    touch ont16s_run_summary.tsv ont16s_warnings.tsv
    """
}
