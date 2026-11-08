process NOVELTY {
    tag "${meta.id}"
    label 'process_medium'

    conda "bioconda::emu=3.6.2"
    container "community.wave.seqera.io/library/emu:3.6.2--0adcfa4809f061f6"

    input:
    tuple val(meta), path(reads)
    path db

    output:
    tuple val(meta), path("*_novelty_summary.tsv"), emit: summary
    tuple val(meta), path("*_novelty_profile.tsv"), emit: profile
    tuple val(meta), path("*_novelty_reads.tsv.gz"), emit: reads
    tuple val("${task.process}"), val('minimap2'), eval('minimap2 --version'), topic: versions, emit: versions_minimap2

    when:
    task.ext.when == null || task.ext.when

    script:
    // Best hit of every read against the database; rank supported by error-corrected identity
    def args   = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    minimap2 -c -x map-ont --secondary=no -t ${task.cpus} ${db}/species_taxid.fasta ${reads} > hits.paf
    novelty.py \\
        --reads ${reads} \\
        --paf hits.paf \\
        --taxonomy ${db}/taxonomy.tsv \\
        --sample ${meta.id} \\
        --prefix ${prefix} \\
        ${args}
    rm hits.paf
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}_novelty_summary.tsv ${prefix}_novelty_profile.tsv
    echo | gzip > ${prefix}_novelty_reads.tsv.gz
    """
}
