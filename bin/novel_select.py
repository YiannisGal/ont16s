#!/usr/bin/env python3
"""Collect reads too distant from the database for a genus name, from all samples.

Inputs: pairs of <sample>=<novelty_reads.tsv.gz>:<reads.fastq.gz>.
A read is selected when its supported rank (novelty.py) is family, order, class, phylum or
unclassified. Read IDs are rewritten as '<sample>__<read id>' so that cluster membership can be
counted per sample later. Writes novel_reads.fastq and novel_reads_per_sample.tsv.
"""

import argparse
import csv
import gzip

NOVEL = {"family", "order", "class", "phylum", "unclassified"}


def opener(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pairs", nargs="+")
    ap.add_argument("--out", default="novel_reads.fastq")
    ap.add_argument("--counts", default="novel_reads_per_sample.tsv")
    args = ap.parse_args()

    stats = []
    with open(args.out, "w") as out:
        for pair in args.pairs:
            sample, files = pair.split("=", 1)
            table, fastq = files.split(":", 1)
            keep = set()
            total = 0
            with opener(table) as fh:
                for row in csv.DictReader(fh, delimiter="\t"):
                    total += 1
                    if row["supported_rank"] in NOVEL:
                        keep.add(row["read_id"])
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

    with open(args.counts, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["sample", "reads", "novel_reads"])
        w.writerows(stats)


if __name__ == "__main__":
    main()
