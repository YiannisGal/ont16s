process EMU_COMBINE {
    tag "${reports.size()} samples"
    label 'process_single'

    conda "bioconda::emu=3.6.2"
    container "community.wave.seqera.io/library/emu:3.6.2--0adcfa4809f061f6"

    input:
    path reports, stageAs: 'reports/*'

    output:
    path "emu-combined-*.tsv", emit: tables
    tuple val("${task.process}"), val('emu'), eval('emu --version 2>&1 | sed "s/^.*emu //; s/Using.*$//"'), topic: versions, emit: versions_emu

    when:
    task.ext.when == null || task.ext.when

    script:
    def ranks = task.ext.ranks ?: ['species', 'genus']
    """
    for rank in ${ranks.join(' ')}; do
        emu combine-outputs reports \$rank
        emu combine-outputs --counts reports \$rank
    done
    mv reports/emu-combined-*.tsv .
    """

    stub:
    """
    touch emu-combined-species.tsv emu-combined-species-counts.tsv
    """
}
