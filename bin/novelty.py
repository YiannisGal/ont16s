#!/usr/bin/env python3
"""Novelty-aware classification of full-length 16S reads.

Emu assigns every read to its closest reference, so an organism missing from the database is
reported under a related name. This script asks, per read, how deep a name the similarity to the
closest reference actually supports.

Per read:
  identity      = matching bases / alignment block length of the best minimap2 hit (PAF, -c)
  read_accuracy = 1 - mean per-base error probability from the read's own quality scores
  adj_identity  = min(1, identity / read_accuracy)   (removes the read's own sequencing errors)
  supported rank = deepest rank whose threshold adj_identity reaches (Yarza et al. 2014,
                   full-length 16S: species 98.7, genus 94.5, family 86.5, order 82.0,
                   class 78.5, phylum 75.0 %)
Reads whose best hit covers < --min-coverage of the read are 'unaligned' (chimeras, off-target).

Outputs (prefix = sample):
  <prefix>_novelty_summary.tsv  one row: fractions of reads per deepest supported rank
  <prefix>_novelty_profile.tsv  lineage of the best hit truncated to the supported rank, counts
  <prefix>_novelty_reads.tsv.gz per read details
"""

import argparse
import csv
import gzip
import statistics
from collections import Counter

RANKS = ["phylum", "class", "order", "family", "genus", "species"]
THRESHOLDS = {"species": 0.987, "genus": 0.945, "family": 0.865, "order": 0.82, "class": 0.785, "phylum": 0.75}


def opener(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def read_accuracy(fastq):
    acc = {}
    with opener(fastq) as fh:
        while True:
            h = fh.readline()
            if not h:
                break
            fh.readline()
            fh.readline()
            q = fh.readline().rstrip("\n")
            rid = h[1:].split()[0]
            if q:
                acc[rid] = 1.0 - sum(10 ** (-(ord(c) - 33) / 10) for c in q) / len(q)
            else:
                acc[rid] = float("nan")
    return acc


def best_hits(paf):
    best = {}
    with opener(paf) as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 12 or int(f[10]) == 0:
                continue
            matches, block = int(f[9]), int(f[10])
            if f[0] not in best or matches > best[f[0]][0]:
                cov = (int(f[3]) - int(f[2])) / int(f[1])
                best[f[0]] = (matches, matches / block, cov, f[5].split(":")[0])
    return best


def load_taxonomy(path):
    tax = {}
    with open(path) as fh:
        r = csv.DictReader(fh, delimiter="\t")
        for row in r:
            tax[row["tax_id"]] = [(row.get(k) or "").strip() for k in RANKS]
    return tax


def supported_rank(adj):
    deepest = "unclassified"
    for rank in RANKS:
        if adj >= THRESHOLDS[rank]:
            deepest = rank
    return deepest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reads", required=True)
    ap.add_argument("--paf", required=True)
    ap.add_argument("--taxonomy", required=True)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--min-coverage", type=float, default=0.8)
    ap.add_argument("--no-error-correction", action="store_true", help="use raw identity")
    args = ap.parse_args()

    acc = read_accuracy(args.reads)
    best = best_hits(args.paf)
    tax = load_taxonomy(args.taxonomy)

    counts = Counter()
    profile = Counter()
    raw_ids, adj_ids, accs = [], [], []
    with gzip.open(f"{args.prefix}_novelty_reads.tsv.gz", "wt") as out:
        w = csv.writer(out, delimiter="\t", lineterminator="\n")
        w.writerow(["read_id", "read_accuracy", "identity", "adj_identity", "coverage", "best_taxid", "supported_rank"])
        for rid, a in acc.items():
            if a == a:
                accs.append(a)
            hit = best.get(rid)
            if hit is None or hit[2] < args.min_coverage:
                counts["unaligned"] += 1
                profile[("unaligned",) + ("",) * len(RANKS)] += 1
                w.writerow([rid, f"{a:.4f}", "", "", f"{hit[2]:.3f}" if hit else "", hit[3] if hit else "", "unaligned"])
                continue
            _, ident, cov, taxid = hit
            adj = ident if args.no_error_correction or a != a or a <= 0 else min(1.0, ident / a)
            rank = supported_rank(adj)
            raw_ids.append(ident)
            adj_ids.append(adj)
            counts[rank] += 1
            lineage = tax.get(taxid, [""] * len(RANKS))
            depth = RANKS.index(rank) + 1 if rank in RANKS else 0
            profile[(rank,) + tuple(lineage[:depth]) + ("",) * (len(RANKS) - depth)] += 1
            w.writerow([rid, f"{a:.4f}", f"{ident:.4f}", f"{adj:.4f}", f"{cov:.3f}", taxid, rank])

    total = sum(counts.values())
    order = ["species", "genus", "family", "order", "class", "phylum", "unclassified", "unaligned"]
    below_genus = sum(counts[k] for k in ["family", "order", "class", "phylum", "unclassified"])
    aligned = total - counts["unaligned"]

    def frac(x, n):
        return f"{x / n:.4f}" if n else "NA"

    def med(v):
        return f"{statistics.median(v):.4f}" if v else "NA"

    with open(f"{args.prefix}_novelty_summary.tsv", "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(
            ["sample", "reads", "median_read_accuracy", "median_identity", "median_adj_identity"]
            + [f"frac_{k}" for k in order]
            + ["frac_novel_genus"]
        )
        w.writerow(
            [args.sample, total, med(accs), med(raw_ids), med(adj_ids)]
            + [frac(counts[k], total) for k in order]
            + [frac(below_genus, aligned)]
        )

    with open(f"{args.prefix}_novelty_profile.tsv", "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["supported_rank"] + RANKS + ["reads", "abundance"])
        for key, n in sorted(profile.items(), key=lambda kv: -kv[1]):
            w.writerow(list(key) + [n, f"{n / total:.6f}" if total else "NA"])


if __name__ == "__main__":
    main()
