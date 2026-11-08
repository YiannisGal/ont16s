#!/usr/bin/env python3
"""Consensus sequences for clusters of novel reads, classified against the database.

Steps (all reads pooled across samples, IDs '<sample>__<read id>'):
  1. vsearch --cluster_fast at --cluster-id (raw-read identity; two reads at 98 % accuracy from
     the same organism are ~96 % identical, so the default 0.90 groups reads of one genus-level
     lineage while keeping lineages > ~10 % apart separate).
  2. Clusters with >= --min-size reads: the centroid is polished --rounds times with racon using
     up to --max-reads members (minimap2 map-ont overlaps).
  3. Each consensus is aligned to the database (minimap2 -c); identity of a consensus is no
     longer dominated by read errors, so the Yarza thresholds apply directly.

Outputs: novel_otus.fasta, novel_otus.tsv (one row per OTU: size, per-sample reads, best hit,
identity, supported rank, lineage truncated to that rank).
"""

import argparse
import csv
import os
import subprocess
from collections import Counter, defaultdict

RANKS = ["phylum", "class", "order", "family", "genus", "species"]
THRESHOLDS = {"species": 0.987, "genus": 0.945, "family": 0.865, "order": 0.82, "class": 0.785, "phylum": 0.75}


def run(cmd, stdout=None):
    subprocess.run(cmd, check=True, stdout=stdout)


def read_fastq(path):
    recs = {}
    with open(path) as fh:
        while True:
            h = fh.readline()
            if not h:
                break
            s, _, q = fh.readline().rstrip(), fh.readline(), fh.readline().rstrip()
            recs[h[1:].split()[0]] = (s, q)
    return recs


def read_fasta(path):
    seqs, name = {}, None
    with open(path) as fh:
        for line in fh:
            line = line.rstrip()
            if line.startswith(">"):
                name = line[1:].split()[0]
                seqs[name] = []
            elif name:
                seqs[name].append(line)
    return {k: "".join(v) for k, v in seqs.items()}


def supported_rank(ident):
    deepest = "unclassified"
    for r in RANKS:
        if ident >= THRESHOLDS[r]:
            deepest = r
    return deepest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reads", required=True)
    ap.add_argument("--db", required=True, help="Emu database directory")
    ap.add_argument("--cluster-id", type=float, default=0.90)
    ap.add_argument("--min-size", type=int, default=10)
    ap.add_argument("--max-reads", type=int, default=200)
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--threads", type=int, default=1)
    args = ap.parse_args()

    reads = read_fastq(args.reads)
    header = ["otu", "size"]
    samples = sorted({rid.split("__", 1)[0] for rid in reads})
    cols = header + samples + ["best_taxid", "identity", "supported_rank"] + RANKS
    if not reads:
        open("novel_otus.fasta", "w").close()
        with open("novel_otus.tsv", "w", newline="") as fh:
            csv.writer(fh, delimiter="\t", lineterminator="\n").writerow(cols)
        return

    with open("all.fasta", "w") as fh:
        for rid, (s, _) in reads.items():
            fh.write(f">{rid}\n{s}\n")
    run(["vsearch", "--cluster_fast", "all.fasta", "--id", str(args.cluster_id), "--strand", "both",
         "--uc", "clusters.uc", "--threads", str(args.threads), "--quiet"])

    members = defaultdict(list)
    with open("clusters.uc") as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if f[0] == "S":
                members[f[8]].insert(0, f[8])
            elif f[0] == "H":
                members[f[9]].append(f[8])

    big = sorted((m for m in members.values() if len(m) >= args.min_size), key=len, reverse=True)
    consensus = {}
    os.makedirs("work_otu", exist_ok=True)
    for i, mem in enumerate(big, 1):
        otu = f"novel_otu_{i:04d}"
        d = f"work_otu/{otu}"
        os.makedirs(d, exist_ok=True)
        with open(f"{d}/reads.fastq", "w") as fh:
            for rid in mem[: args.max_reads]:
                s, q = reads[rid]
                fh.write(f"@{rid}\n{s}\n+\n{q}\n")
        draft = reads[mem[0]][0]
        for r in range(args.rounds):
            with open(f"{d}/draft.fasta", "w") as fh:
                fh.write(f">{otu}\n{draft}\n")
            with open(f"{d}/ovl.paf", "w") as fh:
                run(["minimap2", "-x", "map-ont", "-t", str(args.threads), f"{d}/draft.fasta", f"{d}/reads.fastq"], stdout=fh)
            if os.path.getsize(f"{d}/ovl.paf") == 0:
                break
            with open(f"{d}/polished.fasta", "w") as fh:
                run(["racon", "-t", str(args.threads), f"{d}/reads.fastq", f"{d}/ovl.paf", f"{d}/draft.fasta"], stdout=fh)
            polished = list(read_fasta(f"{d}/polished.fasta").values())
            if not polished or not polished[0]:
                break
            draft = polished[0]
        consensus[otu] = (draft, mem)

    with open("novel_otus.fasta", "w") as fh:
        for otu, (seq, mem) in consensus.items():
            fh.write(f">{otu};size={len(mem)}\n{seq}\n")

    hits = {}
    if consensus:
        with open("otu_hits.paf", "w") as fh:
            run(["minimap2", "-c", "-x", "map-ont", "--secondary=no", "-t", str(args.threads),
                 os.path.join(args.db, "species_taxid.fasta"), "novel_otus.fasta"], stdout=fh)
        with open("otu_hits.paf") as fh:
            for line in fh:
                f = line.split("\t")
                otu = f[0].split(";")[0]
                m, b = int(f[9]), int(f[10])
                if b and (otu not in hits or m > hits[otu][0]):
                    hits[otu] = (m, m / b, f[5].split(":")[0])

    tax = {}
    with open(os.path.join(args.db, "taxonomy.tsv")) as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            tax[row["tax_id"]] = [(row.get(k) or "").strip() for k in RANKS]

    with open("novel_otus.tsv", "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(cols)
        for otu, (seq, mem) in consensus.items():
            per = Counter(rid.split("__", 1)[0] for rid in mem)
            if otu in hits:
                _, ident, taxid = hits[otu]
                rank = supported_rank(ident)
                lin = tax.get(taxid, [""] * len(RANKS))
                depth = RANKS.index(rank) + 1 if rank in RANKS else 0
                lin = lin[:depth] + [""] * (len(RANKS) - depth)
                w.writerow([otu, len(mem)] + [per.get(s, 0) for s in samples] + [taxid, f"{ident:.4f}", rank] + lin)
            else:
                w.writerow([otu, len(mem)] + [per.get(s, 0) for s in samples] + ["", "", "no_hit"] + [""] * len(RANKS))


if __name__ == "__main__":
    main()
