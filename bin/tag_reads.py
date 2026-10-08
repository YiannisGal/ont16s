#!/usr/bin/env python3
"""Concatenate FASTQ files, prefixing read IDs with '<sample>__<n>__' (unique per read).

Usage: tag_reads.py --out pooled.fastq[.gz] --counts counts.tsv [--max-reads N] SAMPLE=FILE ...
Writes the number of reads taken per sample to --counts. Standard library only.
"""

import argparse
import gzip


def opener(path, mode):
    return gzip.open(path, mode + "t") if path.endswith(".gz") else open(path, mode)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--counts", required=True)
    ap.add_argument("--max-reads", type=int, default=0, help="0 = all reads")
    ap.add_argument("pairs", nargs="+", help="SAMPLE=FILE")
    args = ap.parse_args()

    counts = []
    with opener(args.out, "w") as out:
        for pair in args.pairs:
            sample, path = pair.split("=", 1)
            if "__" in sample:
                raise SystemExit(f"Sample name must not contain '__': {sample}")
            n = 0
            with opener(path, "r") as fh:
                for i, line in enumerate(fh):
                    if i % 4 == 0:
                        if args.max_reads and n >= args.max_reads:
                            break
                        n += 1
                        # running number keeps IDs unique even if a read occurs twice in a sample
                        line = f"@{sample}__{n}__{line[1:]}"
                    out.write(line)
            counts.append((sample, n))
    with open(args.counts, "w") as fh:
        fh.write("sample\tn_reads\n")
        for sample, n in counts:
            fh.write(f"{sample}\t{n}\n")


if __name__ == "__main__":
    main()
