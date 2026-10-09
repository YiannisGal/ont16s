#!/usr/bin/env python3
"""Summarise how well reads match the reference database (informational).

Input: minimap2 PAF (best hit per read, '-c --secondary=no') for a per-sample subsample whose
read IDs are '<sample>__<read id>', plus a TSV of reads per sample in the subsample.
Identity = matching bases / alignment block length. Note that read errors lower identity too,
so compare samples sequenced with the same chemistry/basecalling, not absolute values.
"""

import argparse
import csv
import statistics


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--paf", required=True)
    ap.add_argument("--counts", required=True)
    ap.add_argument("--out", default="db_fit.tsv")
    args = ap.parse_args()

    n = {}
    with open(args.counts) as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if row and row[0] != "sample":
                n[row[0]] = int(row[1])

    best = {}
    with open(args.paf) as fh:
        for line in fh:
            f = line.split("\t")
            if len(f) < 12 or int(f[10]) == 0:
                continue
            ident = int(f[9]) / int(f[10])
            if ident > best.get(f[0], -1):
                best[f[0]] = ident
    per = {s: [] for s in n}
    for rid, ident in best.items():
        per.setdefault(rid.split("__", 1)[0], []).append(ident)

    with open(args.out, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["sample", "reads_tested", "frac_with_hit", "median_identity", "frac_ge_0.97", "frac_lt_0.90"])
        for s in sorted(per):
            ids = per[s]
            tested = n.get(s, len(ids))
            if not ids:
                w.writerow([s, tested, "0.0000", "NA", "NA", "NA"])
                continue
            w.writerow([s, tested, f"{len(ids) / tested:.4f}", f"{statistics.median(ids):.4f}",
                        f"{sum(i >= 0.97 for i in ids) / len(ids):.4f}",
                        f"{sum(i < 0.90 for i in ids) / len(ids):.4f}"])


if __name__ == "__main__":
    main()
