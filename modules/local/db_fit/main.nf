process DB_FIT {
    tag "${ids.size()} samples"
    label 'process_medium'

    conda "bioconda::emu=3.6.2"
    container "community.wave.seqera.io/library/emu:3.6.2--0adcfa4809f061f6"

    input:
    tuple val(ids), path(reads, stageAs: 'reads/?/*')
    path db
    val n_reads

    output:
    path "db_fit.tsv", emit: tsv
    tuple val("${task.process}"), val('minimap2'), eval('minimap2 --version'), topic: versions, emit: versions_minimap2

    when:
    task.ext.when == null || task.ext.when

    script:
    // Best hit of the first n_reads reads per sample against the database (informational)
    def files = reads instanceof List ? reads : [reads]
    def pairs = [ids, files].transpose().collect { id, f -> "${id}=${f}" }.join(' ')
    """
    tag_reads.py --out subsample.fastq --counts counts.tsv --max-reads ${n_reads} ${pairs}
    minimap2 -c -x map-ont --secondary=no -t ${task.cpus} ${db}/species_taxid.fasta subsample.fastq > hits.paf
    db_fit.py --paf hits.paf --counts counts.tsv --out db_fit.tsv
    """

    stub:
    """
    printf 'sample\\treads_tested\\tfrac_with_hit\\tmedian_identity\\tfrac_ge_0.97\\tfrac_lt_0.90\\n' > db_fit.tsv
    """
}
