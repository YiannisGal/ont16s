#!/usr/bin/env python3
"""Split a pooled Emu run back into per-sample Emu abundance tables.

Read IDs in the pooled run are '<sample>__<read id>'. Per-sample estimated counts are the sums
of Emu's per-read assignment probabilities; unclassified/unmapped reads are counted from Emu's
unclassified outputs. Output tables have the same columns as 'emu abundance' output.
Standard library only.
"""

import argparse
import csv
import gzip
import os

SEP = "__"
NON_TAXA = ("unmapped", "mapped_filtered", "mapped_unclassified")


def opener(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def read_ids(path):
    """Yield read IDs from a FASTA or FASTQ file (Emu writes either)."""
    with opener(path) as fh:
        first = fh.read(1)
        if not first:
            return
        fh.seek(0)
        if first == "@":
            for i, line in enumerate(fh):
                if i % 4 == 0:
                    yield line[1:].split()[0]
        else:
            for line in fh:
                if line.startswith(">"):
                    yield line[1:].split()[0]


def sample_of(read_id):
    if SEP not in read_id:
        raise SystemExit(f"Read ID without sample tag '{SEP}': {read_id}")
    return read_id.split(SEP, 1)[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pooled", required=True, help="pooled *_rel-abundance.tsv (taxonomy columns)")
    ap.add_argument("--assignments", required=True, help="pooled *_read-assignment-distributions.tsv")
    ap.add_argument("--unclassified", nargs="*", default=[], help="pooled *_unclassified_mapped.* files")
    ap.add_argument("--unmapped", nargs="*", default=[], help="pooled *_unmapped.* files")
    ap.add_argument("--counts", required=True, help="TSV sample<TAB>n_reads (reads given to Emu)")
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()

    n_in = {}
    with open(args.counts) as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if row and row[0] != "sample":
                n_in[row[0]] = int(row[1])

    with open(args.pooled) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        columns = reader.fieldnames
        lineage = {r["tax_id"]: r for r in reader if r["tax_id"] not in NON_TAXA}

    counts = {s: {} for s in n_in}
    with opener(args.assignments) as fh:
        reader = csv.reader(fh, delimiter="\t")
        taxa = next(reader)[1:]
        for row in reader:
            s = sample_of(row[0])
            per = counts.setdefault(s, {})
            for tax, value in zip(taxa, row[1:]):
                if value:
                    per[tax] = per.get(tax, 0.0) + float(value)

    unclassified = {s: 0 for s in n_in}
    for path in args.unclassified:
        for rid in read_ids(path):
            unclassified[sample_of(rid)] = unclassified.get(sample_of(rid), 0) + 1
    unmapped = {s: 0 for s in n_in}
    for path in args.unmapped:
        for rid in read_ids(path):
            unmapped[sample_of(rid)] = unmapped.get(sample_of(rid), 0) + 1

    count_col = "estimated counts"
    for s in sorted(n_in):
        per = counts.get(s, {})
        classified = sum(per.values())
        filtered = max(0, round(n_in[s] - classified - unclassified.get(s, 0) - unmapped.get(s, 0)))
        with open(os.path.join(args.outdir, f"{s}_rel-abundance.tsv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=columns, delimiter="\t", lineterminator="\n")
            w.writeheader()
            for tax, n in sorted(per.items(), key=lambda kv: -kv[1]):
                row = dict(lineage.get(tax, {"tax_id": tax}))
                row["abundance"] = n / classified if classified else 0
                row[count_col] = n
                w.writerow({c: row.get(c, "") for c in columns})
            for name, n in (("unmapped", unmapped.get(s, 0)), ("mapped_filtered", filtered),
                            ("mapped_unclassified", unclassified.get(s, 0))):
                row = {c: "" for c in columns}
                row.update({"tax_id": name, "abundance": 0, count_col: n})
                w.writerow(row)


if __name__ == "__main__":
    main()
