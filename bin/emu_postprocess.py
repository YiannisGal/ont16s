#!/usr/bin/env python3
"""Per-sample Emu post-processing: optional taxon exclusion and summary metrics.

- Taxa whose lineage contains any --exclude term (case-insensitive, any rank) are removed and
  the remaining abundances renormalised. Their reads are reported, not hidden.
- Organelle reads (lineage contains 'chloroplast' or 'mitochondri') are always reported.
Writes '<prefix>_rel-abundance.tsv' (same columns as Emu) and '<prefix>_emu_metrics.tsv'.
Standard library only.
"""

import argparse
import csv

NON_TAXA = ("unmapped", "mapped_filtered", "mapped_unclassified")
ORGANELLE = ("chloroplast", "mitochondri")
RANKS = ("superkingdom", "domain", "phylum", "class", "order", "family", "genus", "species")


def lineage_text(row):
    return " ".join(row.get(r) or "" for r in RANKS).lower()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--mode", required=True, help="per_sample or pooled (reported only)")
    ap.add_argument("--exclude", default="", help="comma-separated lineage terms to remove")
    args = ap.parse_args()
    exclude = [t.strip().lower() for t in args.exclude.split(",") if t.strip()]

    with open(args.input) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        columns = reader.fieldnames
        rows = list(reader)
    count_col = "estimated counts"

    taxa = [r for r in rows if r["tax_id"] not in NON_TAXA]
    other = {r["tax_id"]: float(r[count_col] or 0) for r in rows if r["tax_id"] in NON_TAXA}
    classified = sum(float(r[count_col]) for r in taxa)
    organelle = sum(float(r[count_col]) for r in taxa if any(o in lineage_text(r) for o in ORGANELLE))
    removed_rows = [r for r in taxa if exclude and any(t in lineage_text(r) for t in exclude)]
    kept = [r for r in taxa if r not in removed_rows]
    removed = sum(float(r[count_col]) for r in removed_rows)
    kept_total = classified - removed

    with open(f"{args.prefix}_rel-abundance.tsv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in kept:
            r = dict(r)
            r["abundance"] = float(r[count_col]) / kept_total if kept_total else 0
            w.writerow(r)
        for r in rows:
            if r["tax_id"] in NON_TAXA:
                w.writerow(r)

    total = classified + sum(other.values())
    def frac(x):
        return f"{x / total:.4f}" if total else "NA"
    metrics = {
        "sample": args.sample,
        "emu_mode": args.mode,
        "reads_to_emu": f"{total:.0f}",
        "classified": f"{classified:.0f}",
        "classified_frac": frac(classified),
        "mapped_unclassified_frac": frac(other.get("mapped_unclassified", 0)),
        "unmapped_frac": frac(other.get("unmapped", 0)),
        "mapped_filtered_frac": frac(other.get("mapped_filtered", 0)),
        "organelle_frac": frac(organelle),
        "excluded_frac": frac(removed),
        "excluded_terms": ",".join(exclude) or "none",
        "n_taxa": len(kept),
    }
    with open(f"{args.prefix}_emu_metrics.tsv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(metrics), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerow(metrics)


if __name__ == "__main__":
    main()
