process NOVELTY {
    tag "${meta.id}"
    label 'process_medium'

    conda "bioconda::emu=3.6.2 bioconda::minimap2=2.30 conda-forge::python=3.13.12"
    container "community.wave.seqera.io/library/emu:3.6.2--0adcfa4809f061f6"

    input:
    tuple val(meta), path(reads)
    path db
    val max_reads

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
    # Systematic subsample (every k-th read) when the sample has more than max_reads reads (0 = all)
    n=\$(zcat -f ${reads} | awk 'END { print int(NR / 4) }')
    k=1
    if [ ${max_reads} -gt 0 ] && [ \$n -gt ${max_reads} ]; then k=\$(( (n + ${max_reads} - 1) / ${max_reads} )); fi
    zcat -f ${reads} | awk -v k=\$k '{ r = int((NR - 1) / 4) } r % k == 0' > novelty_input.fastq
    minimap2 -c -x map-ont --secondary=no -t ${task.cpus} ${db}/species_taxid.fasta novelty_input.fastq > hits.paf
    novelty.py \\
        --reads novelty_input.fastq \\
        --paf hits.paf \\
        --taxonomy ${db}/taxonomy.tsv \\
        --sample ${meta.id} \\
        --prefix ${prefix} \\
        ${args}
    rm hits.paf novelty_input.fastq
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}_novelty_summary.tsv ${prefix}_novelty_profile.tsv
    echo | gzip > ${prefix}_novelty_reads.tsv.gz
    """
}
