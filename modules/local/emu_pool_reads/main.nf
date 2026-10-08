process EMU_POOL_READS {
    tag "${ids.size()} samples"
    label 'process_single'

    conda "bioconda::emu=3.6.2"
    container "community.wave.seqera.io/library/emu:3.6.2--0adcfa4809f061f6"

    input:
    tuple val(ids), path(reads, stageAs: 'reads/?/*')

    output:
    path "pooled.fastq.gz", emit: fastq
    path "pool_counts.tsv", emit: counts
    tuple val("${task.process}"), val('python'), eval('python3 --version | sed "s/Python //"'), topic: versions, emit: versions_python

    when:
    task.ext.when == null || task.ext.when

    script:
    // Read IDs become '<sample>__<read id>' so the pooled Emu result can be split again
    def files = reads instanceof List ? reads : [reads]
    def pairs = [ids, files].transpose().collect { id, f -> "${id}=${f}" }.join(' ')
    """
    tag_reads.py --out pooled.fastq.gz --counts pool_counts.tsv ${pairs}
    """

    stub:
    """
    echo | gzip -c > pooled.fastq.gz
    printf 'sample\\tn_reads\\n' > pool_counts.tsv
    """
}
