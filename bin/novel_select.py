#!/usr/bin/env python3
"""Collect reads too distant from the database for a genus name, from all samples.

Inputs: pairs of <sample>=<novelty_reads.tsv.gz>:<reads.fastq.gz>.
A read is selected when its supported rank (novelty.py) is family, order, class, phylum or
unclassified. Read IDs are rewritten as '<sample>__<read id>' so that cluster membership can be
counted per sample later. Writes novel_reads.fastq, novel_reads_per_sample.tsv,
novel_groups.tsv (read -> closest-reference lineage at the deepest supported rank, used to cluster
lineages separately) and read_accuracy.txt: the median identity of species-rank reads to their
reference, i.e. the measured accuracy of reads from known organisms (Q scores of fast-basecalled
reads are not calibrated well enough to use instead).
"""

import argparse
import csv
import gzip
import statistics

NOVEL = {"family", "order", "class", "phylum", "unclassified"}
RANKS = ["phylum", "class", "order", "family", "genus", "species"]


def opener(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pairs", nargs="+")
    ap.add_argument("--out", default="novel_reads.fastq")
    ap.add_argument("--counts", default="novel_reads_per_sample.tsv")
    ap.add_argument("--groups", default="novel_groups.tsv")
    ap.add_argument("--taxonomy", help="taxonomy.tsv of the database (lineage of the closest reference)")
    args = ap.parse_args()

    tax = {}
    if args.taxonomy:
        with open(args.taxonomy) as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                tax[row["tax_id"]] = [(row.get(k) or "").strip() for k in RANKS]

    stats, groups, species_ident = [], {}, []
    with open(args.out, "w") as out:
        for pair in args.pairs:
            sample, files = pair.split("=", 1)
            table, fastq = files.split(":", 1)
            keep = set()
            total = 0
            with opener(table) as fh:
                for row in csv.DictReader(fh, delimiter="\t"):
                    total += 1
                    rank = row["supported_rank"]
                    if rank == "species" and row["identity"]:
                        species_ident.append(float(row["identity"]))
                    if rank in NOVEL:
                        keep.add(row["read_id"])
                        lin = tax.get(row["best_taxid"], [])
                        depth = RANKS.index(rank) if rank in RANKS else 0
                        # lineage of the closest reference down to the rank above the supported one
                        key = ";".join(lin[: depth + 1]) if lin else "unknown"
                        groups[f"{sample}__{row['read_id']}"] = key or "unknown"
            n = 0
            with opener(fastq) as fh:
                while True:
                    h = fh.readline()
                    if not h:
                        break
                    seq, plus, qual = fh.readline(), fh.readline(), fh.readline()
                    rid = h[1:].split()[0]
                    if rid in keep:
                        out.write(f"@{sample}__{rid}\n{seq}{plus}{qual}")
                        n += 1
            stats.append((sample, total, n))

    with open(args.groups, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["read", "group"])
        w.writerows(sorted(groups.items()))
    with open("read_accuracy.txt", "w") as fh:
        fh.write(f"{statistics.median(species_ident):.4f}\n" if len(species_ident) >= 100 else "NA\n")

    with open(args.counts, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["sample", "reads", "novel_reads"])
        w.writerows(stats)


if __name__ == "__main__":
    main()
