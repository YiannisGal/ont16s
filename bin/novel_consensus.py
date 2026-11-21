#!/usr/bin/env python3
"""Consensus sequences for clusters of novel reads, classified against the database.

Steps (all reads pooled across samples, IDs '<sample>__<read id>'):
  1. Reads are split into groups by the lineage of their closest reference (novel_groups.tsv), so
     that distant lineages are never clustered together even at a low identity threshold.
  2. vsearch --cluster_fast per group. Identity threshold: --cluster-id, or 'auto' =
     a^2 - 0.02 (bounded 0.70-0.95), where a is the measured read accuracy (median identity of
     species-rank reads to their reference). Two reads of one organism are about a^2 identical:
     0.98 accuracy -> 0.94; 0.88 (fast basecalling) -> 0.75. A fixed 0.90 leaves reads of
     < ~95 % accuracy as singletons.
  3. Clusters with >= --min-size reads: the centroid is polished --rounds times with racon using
     up to --max-reads members (minimap2 map-ont overlaps).
  4. All novel reads are mapped to the consensus set; a read counts for its best consensus when
     identity >= threshold - 0.02 and coverage >= 0.8 (per-sample counts in novel_otus.tsv).
  5. Each consensus is aligned to the database (minimap2 -c); the identity of a consensus is no
     longer dominated by read errors, so the Yarza thresholds apply directly.

Outputs: novel_otus.fasta, novel_otus.tsv (one row per OTU: assigned reads, per-sample reads, best
hit, identity, supported rank, lineage truncated to that rank, group), novel_otus_params.tsv.
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


def map_best(ref, reads_fa, threads):
    """Best hit per read: {read: (ref, identity, coverage)} from minimap2 -c."""
    out = subprocess.run(["minimap2", "-c", "-x", "map-ont", "--secondary=no", "-t", str(threads), ref, reads_fa],
                         check=True, capture_output=True, text=True).stdout
    best = {}
    for line in out.splitlines():
        f = line.split("\t")
        m, b = int(f[9]), int(f[10])
        if not b:
            continue
        cov = (int(f[3]) - int(f[2])) / int(f[1])
        if f[0] not in best or m > best[f[0]][3]:
            best[f[0]] = (f[5], m / b, cov, m)
    return {k: v[:3] for k, v in best.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reads", required=True)
    ap.add_argument("--db", required=True, help="Emu database directory")
    ap.add_argument("--groups", help="novel_groups.tsv (read, group); default: one group")
    ap.add_argument("--accuracy-file", default="read_accuracy.txt")
    ap.add_argument("--cluster-id", default="auto", help="identity threshold or 'auto'")
    ap.add_argument("--min-size", type=int, default=10)
    ap.add_argument("--max-reads", type=int, default=200, help="reads used to polish one consensus")
    ap.add_argument("--max-group-reads", type=int, default=5000, help="reads clustered per group (every k-th)")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--keep-chimeras", action="store_true", help="skip the reference chimera filter")
    args = ap.parse_args()

    reads = read_fastq(args.reads)
    samples = sorted({rid.split("__", 1)[0] for rid in reads})
    cols = ["otu", "size"] + samples + ["best_taxid", "identity", "supported_rank"] + RANKS + ["group"]

    acc = None
    if os.path.exists(args.accuracy_file):
        v = open(args.accuracy_file).read().strip()
        acc = float(v) if v not in ("", "NA") else None
    if args.cluster_id == "auto":
        cid = min(0.95, max(0.70, acc * acc - 0.02)) if acc else 0.90
    else:
        cid = float(args.cluster_id)
    with open("novel_otus_params.tsv", "w") as fh:
        fh.write(f"read_accuracy\t{acc if acc else 'NA'}\ncluster_id\t{cid:.3f}\nnovel_reads\t{len(reads)}\n")

    if not reads:
        open("novel_otus.fasta", "w").close()
        with open("novel_otus.tsv", "w", newline="") as fh:
            csv.writer(fh, delimiter="\t", lineterminator="\n").writerow(cols)
        return

    group_of = {}
    if args.groups and os.path.exists(args.groups):
        with open(args.groups) as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                group_of[row["read"]] = row["group"]
    by_group = defaultdict(list)
    for rid in reads:
        by_group[group_of.get(rid, "all")].append(rid)

    os.makedirs("work_otu", exist_ok=True)
    big = []
    for gi, (grp, rids) in enumerate(sorted(by_group.items(), key=lambda kv: -len(kv[1]))):
        if len(rids) < args.min_size:
            continue
        step = max(1, len(rids) // args.max_group_reads)
        sub = rids[::step]
        fa = f"work_otu/group_{gi}.fasta"
        with open(fa, "w") as fh:
            for rid in sub:
                fh.write(f">{rid}\n{reads[rid][0]}\n")
        uc = f"work_otu/group_{gi}.uc"
        run(["vsearch", "--cluster_fast", fa, "--id", f"{cid:.3f}", "--strand", "both",
             "--uc", uc, "--threads", str(args.threads), "--quiet"])
        members = defaultdict(list)
        with open(uc) as fh:
            for line in fh:
                f = line.rstrip("\n").split("\t")
                if f[0] == "S":
                    members[f[8]].insert(0, f[8])
                elif f[0] == "H":
                    members[f[9]].append(f[8])
        big += [(grp, m) for m in members.values() if len(m) * step >= args.min_size]
    big.sort(key=lambda gm: len(gm[1]), reverse=True)

    consensus = {}
    for i, (grp, mem) in enumerate(big, 1):
        otu = f"novel_otu_{i:04d}"
        d = f"work_otu/{otu}"
        os.makedirs(d, exist_ok=True)
        with open(f"{d}/reads.fastq", "w") as fh:
            for rid in mem[: args.max_reads]:
                s, q = reads[rid]
                fh.write(f"@{rid}\n{s}\n+\n{q}\n")
        draft = reads[mem[0]][0]
        for _ in range(args.rounds):
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
        consensus[otu] = (draft, grp)

    # drop chimeric consensus sequences (reference-based UCHIME against the Emu database);
    # in mock communities every false-novel OTU was a chimera of two mock members
    n_chim = 0
    if consensus and not args.keep_chimeras:
        with open("work_otu/raw_consensus.fasta", "w") as fh:
            for otu, (seq, _) in consensus.items():
                fh.write(f">{otu}\n{seq}\n")
        run(["vsearch", "--uchime_ref", "work_otu/raw_consensus.fasta", "--db",
             os.path.join(args.db, "species_taxid.fasta"), "--nonchimeras", "work_otu/nonchim.fasta",
             "--threads", str(args.threads), "--quiet"])
        ok = set(read_fasta("work_otu/nonchim.fasta"))
        n_chim = len(consensus) - len(ok)
        consensus = {o: v for o, v in consensus.items() if o in ok}
    with open("novel_otus_params.tsv", "a") as fh:
        fh.write(f"chimeric_consensus_removed\t{n_chim}\n")

    # assign every novel read to its best consensus
    assigned = defaultdict(Counter)
    if consensus:
        with open("work_otu/consensus.fasta", "w") as fh:
            for otu, (seq, _) in consensus.items():
                fh.write(f">{otu}\n{seq}\n")
        with open("all.fasta", "w") as fh:
            for rid, (s, _) in reads.items():
                fh.write(f">{rid}\n{s}\n")
        for rid, (otu, ident, cov) in map_best("work_otu/consensus.fasta", "all.fasta", args.threads).items():
            if ident >= cid - 0.02 and cov >= 0.8:
                assigned[otu][rid.split("__", 1)[0]] += 1
    keep = {o: v for o, v in consensus.items() if sum(assigned[o].values()) >= args.min_size}
    order = sorted(keep, key=lambda o: -sum(assigned[o].values()))

    with open("novel_otus.fasta", "w") as fh:
        for otu in order:
            fh.write(f">{otu};size={sum(assigned[otu].values())}\n{keep[otu][0]}\n")

    hits = {}
    if keep:
        for otu, (ref, ident, _) in map_best(os.path.join(args.db, "species_taxid.fasta"), "novel_otus.fasta", args.threads).items():
            hits[otu.split(";")[0]] = (ident, ref.split(":")[0])

    tax = {}
    with open(os.path.join(args.db, "taxonomy.tsv")) as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            tax[row["tax_id"]] = [(row.get(k) or "").strip() for k in RANKS]

    with open("novel_otus.tsv", "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(cols)
        for otu in order:
            per = assigned[otu]
            row = [otu, sum(per.values())] + [per.get(s, 0) for s in samples]
            if otu in hits:
                ident, taxid = hits[otu]
                rank = supported_rank(ident)
                lin = tax.get(taxid, [""] * len(RANKS))
                depth = RANKS.index(rank) + 1 if rank in RANKS else 0
                lin = lin[:depth] + [""] * (len(RANKS) - depth)
                w.writerow(row + [taxid, f"{ident:.4f}", rank] + lin + [keep[otu][1]])
            else:
                w.writerow(row + ["", "", "no_hit"] + [""] * len(RANKS) + [keep[otu][1]])


if __name__ == "__main__":
    main()
