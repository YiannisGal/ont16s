process EMU_DB_INFO {
    tag "${db.name}"
    label 'process_single'

    conda "bioconda::emu=3.6.2"
    container "community.wave.seqera.io/library/emu:3.6.2--0adcfa4809f061f6"

    input:
    path db
    val source

    output:
    path "emu_db_provenance.tsv", emit: tsv
    tuple val("${task.process}"), val('sha256sum'), eval('sha256sum --version | head -1 | sed "s/.* //"'), topic: versions, emit: versions_sha256sum

    when:
    task.ext.when == null || task.ext.when

    script:
    """
    fasta=${db}/species_taxid.fasta
    tax=${db}/taxonomy.tsv
    for f in \$fasta \$tax; do
        [ -s \$f ] || { echo "Emu database is missing \$(basename \$f): ${db}" >&2; exit 1; }
    done
    {
        printf 'key\\tvalue\\n'
        printf 'source\\t%s\\n' "${source}"
        printf 'species_taxid.fasta_sha256\\t%s\\n' "\$(sha256sum \$fasta | cut -d' ' -f1)"
        printf 'species_taxid.fasta_bytes\\t%s\\n' "\$(wc -c < \$fasta | tr -d ' ')"
        printf 'n_sequences\\t%s\\n' "\$(grep -c '^>' \$fasta)"
        printf 'taxonomy.tsv_sha256\\t%s\\n' "\$(sha256sum \$tax | cut -d' ' -f1)"
        printf 'n_species\\t%s\\n' "\$(tail -n +2 \$tax | wc -l | tr -d ' ')"
    } > emu_db_provenance.tsv
    """

    stub:
    """
    printf 'key\\tvalue\\nsource\\t%s\\n' "${source}" > emu_db_provenance.tsv
    """
}
