#!/usr/bin/env python3
"""Regroup Emu's prebuilt SILVA 138.2 database by genus (max N sequences per genus).

Usage: build_silva_genus_db.py <emu-silva-dir> <max-seqs-per-genus>   (writes to current dir)
Input: Emu prebuilt SILVA (OSF 56uf7, emu-prebuilt/silva-138.2.tar), extracted.
Why: in the prebuilt database every sequence is its own taxon (2.2 M taxa), so Emu splits each
read's support over many near-identical sequences and most reads fall below its abundance floor
(ST-007: 73 % unclassified). Grouping by genus avoids this and makes the database ~45x smaller.

Each distinct lineage down to genus (superkingdom..genus) becomes one Emu taxon; the 'species'
column holds the genus name. Sequences are taken in file order (deterministic). Eukaryotic nuclear
18S sequences are dropped; organelle sequences (chloroplast, mitochondria) are kept so they can be
reported/excluded.
"""
import csv
import sys

SRC = sys.argv[1]; MAXN = int(sys.argv[2])
RANKS = ['superkingdom', 'phylum', 'class', 'order', 'family', 'genus']
tax = {}
with open(f'{SRC}/taxonomy.tsv') as fh:
    for r in csv.DictReader(fh, delimiter='\t'):
        lin = tuple((r.get(k) or '').strip() for k in RANKS)
        text = ' '.join(lin).lower()
        if lin[0] == 'Eukaryota' and 'chloroplast' not in text and 'mitochondri' not in text:
            continue
        tax[r['tax_id']] = lin
gid, ids, kept = {}, {}, {}
with open(f'{SRC}/species_taxid.fasta') as fi, open('species_taxid.fasta', 'w') as fo:
    keep = False
    for line in fi:
        if line.startswith('>'):
            old = line[1:].split(':', 1)[0]
            lin = tax.get(old)
            keep = False
            if lin is not None:
                if lin not in gid:
                    gid[lin] = str(len(gid) + 1)
                g = gid[lin]
                if kept.get(g, 0) < MAXN:
                    kept[g] = kept.get(g, 0) + 1
                    keep = True
                    fo.write(f'>{g}:silva_genus:{sum(kept.values())}\n')
            continue
        if keep:
            fo.write(line)
with open('taxonomy.tsv', 'w') as fh:
    fh.write('tax_id\t' + '\t'.join(RANKS) + '\tspecies\n')
    for lin, g in gid.items():
        if g in kept:
            fh.write(g + '\t' + '\t'.join(lin) + '\t' + (lin[-1] or 'NA') + '\n')
print(f'taxa: {len(kept)}  sequences: {sum(kept.values())}', file=sys.stderr)
