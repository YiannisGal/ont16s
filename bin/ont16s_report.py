#!/usr/bin/env python3
"""Run summary and warnings for ont16s.

Inputs: per-sample Emu metrics, NanoPlot NanoStats (raw and filtered), the Emu mode decision
and (optionally) the database-fit table. Writes 'ont16s_run_summary.tsv' (one row per sample)
and 'ont16s_warnings.tsv' (one row per warning, with the reason). Standard library only.
"""

import argparse
import csv
import glob
import os
import re


def nanostats(path):
    out = {}
    with open(path) as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if len(row) == 2:
                out[row[0]] = row[1]
    return out


def sample_from(path, suffix):
    return re.sub(suffix + r"$", "", os.path.basename(path))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--metrics-dir", required=True)
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--filtered-dir", required=True)
    ap.add_argument("--dedup-dir", default=None, help="seqkit rmdup logs '<sample>*.log'")
    ap.add_argument("--decision", required=True)
    ap.add_argument("--db-fit", default=None)
    ap.add_argument("--min-reads", type=int, default=1000)
    ap.add_argument("--max-filter-loss", type=float, default=0.5)
    ap.add_argument("--max-unassigned", type=float, default=0.2)
    ap.add_argument("--max-organelle", type=float, default=0.05)
    args = ap.parse_args()

    raw = {sample_from(p, "_raw_NanoStats.txt"): nanostats(p)
           for p in glob.glob(os.path.join(args.raw_dir, "*_raw_NanoStats.txt"))}
    flt = {sample_from(p, "_filtered_NanoStats.txt"): nanostats(p)
           for p in glob.glob(os.path.join(args.filtered_dir, "*_filtered_NanoStats.txt"))}
    dups = {}
    if args.dedup_dir:
        for p in glob.glob(os.path.join(args.dedup_dir, "*.log")):
            m = re.search(r"(\d+) duplicated records removed", open(p).read())
            dups[re.sub(r"(\.dedup)?\.log$", "", os.path.basename(p))] = int(m.group(1)) if m else 0
    metrics = {}
    for p in glob.glob(os.path.join(args.metrics_dir, "*_emu_metrics.tsv")):
        with open(p) as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                metrics[row["sample"]] = row
    with open(args.decision) as fh:
        decision = next(csv.DictReader(fh, delimiter="\t"))
    fit = {}
    if args.db_fit and os.path.exists(args.db_fit):
        with open(args.db_fit) as fh:
            fit = {r["sample"]: r for r in csv.DictReader(fh, delimiter="\t")}

    rows, warnings = [], []

    def warn(sample, check, value, threshold, message):
        warnings.append({"id": f"{sample}:{check}", "sample": sample, "check": check, "value": value,
                         "threshold": threshold, "message": message})

    for s in sorted(set(raw) | set(flt) | set(metrics)):
        n_raw = float(raw.get(s, {}).get("number_of_reads", "nan"))
        n_flt = float(flt.get(s, {}).get("number_of_reads", "nan"))
        m = metrics.get(s, {})

        # reads removed by the length/quality filter only (duplicates are reported separately)
        n_dup = dups.get(s, 0) if isinstance(dups.get(s), int) else 0
        loss = 1 - (n_flt + n_dup) / n_raw if n_raw and n_raw == n_raw else float("nan")
        unassigned = 1 - float(m["classified_frac"]) if m.get("classified_frac", "NA") != "NA" else float("nan")
        organelle = float(m.get("organelle_frac", "nan")) if m.get("organelle_frac", "NA") != "NA" else float("nan")
        row = {
            "sample": s,
            "reads_raw": f"{n_raw:.0f}",
            "median_length_raw": raw.get(s, {}).get("median_read_length", "NA"),
            "mean_qual_raw": raw.get(s, {}).get("mean_qual", "NA"),
            "duplicates_removed": dups.get(s, "NA"),
            "reads_filtered": f"{n_flt:.0f}",
            "filter_loss_frac": f"{loss:.4f}",
            "emu_mode": m.get("emu_mode", decision["emu_mode"]),
            "classified_frac": m.get("classified_frac", "NA"),
            "unassigned_frac": f"{unassigned:.4f}",
            "organelle_frac": m.get("organelle_frac", "NA"),
            "excluded_frac": m.get("excluded_frac", "NA"),
            "db_fit_median_identity": fit.get(s, {}).get("median_identity", "NA"),
            "db_fit_frac_ge_0.97": fit.get(s, {}).get("frac_ge_0.97", "NA"),
        }
        rows.append(row)
        if n_flt == n_flt and n_flt < args.min_reads:
            warn(s, "low_depth", f"{n_flt:.0f}", args.min_reads,
                 "Few reads after filtering; abundances are unreliable.")
        if loss == loss and loss > args.max_filter_loss:
            warn(s, "filter_loss", f"{loss:.2f}", args.max_filter_loss,
                 f"Most reads removed by the length/quality filter (raw median length "
                 f"{row['median_length_raw']} bp): check library quality or filter settings.")
        if isinstance(dups.get(s), int) and dups[s] > 0:
            warn(s, "duplicate_reads", dups[s], 0,
                 "Identical reads occurred more than once (same read ID) and were removed; "
                 "check how the input files were assembled (e.g. overlapping chunks).")
        if unassigned == unassigned and unassigned > args.max_unassigned:
            hint = ("in per-sample mode this can be caused by Emu's per-sample abundance floor; "
                    "consider --emu_mode pooled" if row["emu_mode"] == "per_sample"
                    else "the database may cover these taxa poorly; consider another --emu_db")
            warn(s, "unassigned", f"{unassigned:.2f}", args.max_unassigned,
                 f"Many reads were not assigned to a taxon ({hint}).")
        if organelle == organelle and organelle > args.max_organelle:
            warn(s, "organelle", f"{organelle:.2f}", args.max_organelle,
                 "Many reads are chloroplast/mitochondria; consider --exclude_taxa chloroplast,mitochondria.")

    warnings.insert(0, {"id": "all:emu_mode", "sample": "all", "check": "emu_mode", "value": decision["emu_mode"],
                        "threshold": decision.get("rule", ""), "message": decision.get("reason", "")})

    for name, data in (("ont16s_run_summary.tsv", rows), ("ont16s_warnings.tsv", warnings)):
        with open(name, "w", newline="") as fh:
            fields = list(data[0].keys()) if data else ["sample"]
            w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(data)


if __name__ == "__main__":
    main()
