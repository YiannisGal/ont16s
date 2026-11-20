#!/usr/bin/env python3
"""Compare an Emu abundance table with a mock-community definition.

Writes a per-taxon table and a one-row summary. Uses only the Python standard library.

Each expected taxon gets a status that separates profiler errors from limits of the data:
  detected               reported under an accepted name
  genus_only             species not reported, but another species of the same genus is
                         (16S-identical relatives, e.g. Veillonella rogosae / parvula)
  below_detection_limit  expected reads (abundance x classified reads) < --min-expected-reads
  not_amplified          (with --novelty-reads) almost no read has its closest reference in the
                         taxon's genus: the organism is missing from the sequenced amplicons
  missed                 none of the above
Metrics are reported at species and at genus rank.
"""

import argparse
import csv
import gzip
import math
import sys
from collections import Counter

NON_TAXA = {"unmapped", "mapped_filtered", "mapped_unclassified"}


def read_tsv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def load_mock(path):
    """Return list of (species, set of accepted names, expected abundance or None)."""
    expected = []
    for row in read_tsv(path):
        names = {row["species"].strip()}
        names |= {a.strip() for a in (row.get("aliases") or "").split(";") if a.strip()}
        value = (row.get("expected_abundance") or "").strip()
        exp = None if value in ("", "NA") else float(value)
        expected.append((row["species"].strip(), names, exp))
    if not expected:
        sys.exit(f"Mock definition has no taxa: {path}")
    return expected


def load_emu(path):
    """Return ({species name: relative abundance}, {genus: abundance}, classified read count)."""
    abundance, by_genus, n_reads = {}, Counter(), 0.0
    for row in read_tsv(path):
        if row["tax_id"] in NON_TAXA:
            continue
        name = row.get("species") or f"tax_id:{row['tax_id']}"
        ab = float(row["abundance"])
        abundance[name] = abundance.get(name, 0.0) + ab
        by_genus[genus(name) or name] += ab
        n_reads += float(row.get("estimated counts") or 0)
    return abundance, by_genus, n_reads


def load_novelty_genera(path):
    """Return (Counter of closest-reference genus per read, number of reads) from novelty.py."""
    opener = gzip.open if path.endswith(".gz") else open
    counts, n = Counter(), 0
    with opener(path, "rt") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            n += 1
            g = (row.get("best_genus") or "").strip()
            if g:
                counts[g] += 1
    return counts, n


def bray_curtis(obs, exp):
    keys = set(obs) | set(exp)
    tot = sum(obs.get(k, 0) + exp.get(k, 0) for k in keys)
    return 1 - 2 * sum(min(obs.get(k, 0), exp.get(k, 0)) for k in keys) / tot if tot else float("nan")


def genus(name):
    return name.split()[0] if name and not name.startswith("tax_id:") else ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--mock-name", required=True)
    parser.add_argument("--emu", required=True, help="Emu *_rel-abundance.tsv")
    parser.add_argument("--mock", required=True, help="Mock definition TSV")
    parser.add_argument("--min-abundance", type=float, default=0.001,
                        help="Unexpected taxa at or above this fraction count as false positives")
    parser.add_argument("--min-expected-ratio", type=float, default=0.01,
                        help="Only taxa expected at or above this fraction enter mean_abs_log2_ratio")
    parser.add_argument("--min-expected-reads", type=float, default=3,
                        help="Expected taxa with fewer expected reads are 'below_detection_limit' "
                             "(Poisson: P(0 reads | 3 expected) = 5 %%)")
    parser.add_argument("--novelty-reads", help="novelty.py *_novelty_reads.tsv.gz (enables 'not_amplified')")
    parser.add_argument("--not-amplified-ratio", type=float, default=0.1,
                        help="'not_amplified' when reads with a closest reference in the genus are below "
                             "this fraction of the expected reads")
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()

    expected = load_mock(args.mock)
    observed, observed_genus, n_reads = load_emu(args.emu)
    nov_genera, nov_n = load_novelty_genera(args.novelty_reads) if args.novelty_reads else (None, 0)
    observed_genera = {genus(n) for n in observed}

    rows = []
    matched = set()
    for species, names, exp in expected:
        hits = [n for n in observed if n in names]
        matched.update(hits)
        obs = sum(observed[n] for n in hits)
        g = genus(species)
        if obs > 0:
            status = "detected"
        elif exp is not None and n_reads and exp * n_reads < args.min_expected_reads:
            status = "below_detection_limit"
        elif nov_genera is not None and exp and nov_n and nov_genera.get(g, 0) < args.not_amplified_ratio * exp * nov_n:
            status = "not_amplified"
        elif g in observed_genera:
            status = "genus_only"
        else:
            status = "missed"
        rows.append({
            "taxon": species,
            "category": "expected",
            "detected": "yes" if obs > 0 else "no",
            "status": status,
            "expected_reads": f"{exp * n_reads:.1f}" if exp is not None and n_reads else "NA",
            "observed_abundance": f"{obs:.6f}",
            "expected_abundance": "NA" if exp is None else f"{exp:.6f}",
            "reported_as": ";".join(sorted(hits)),
            "log2_ratio": f"{math.log2(obs / exp):.3f}" if exp and obs > 0 else "NA",
        })

    expected_genera = {genus(n) for _, names, _ in expected for n in names}
    for name, obs in sorted(observed.items(), key=lambda kv: -kv[1]):
        if name in matched:
            continue
        rows.append({
            "taxon": name,
            "category": "near_neighbour" if genus(name) in expected_genera else "off_target",
            "detected": "yes",
            "status": "unexpected",
            "expected_reads": "0",
            "observed_abundance": f"{obs:.6f}",
            "expected_abundance": "0",
            "reported_as": name,
            "log2_ratio": "NA",
        })

    with open(f"{args.prefix}_mock_validation.tsv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    exp_rows = [r for r in rows if r["category"] == "expected"]
    unexp = [r for r in rows if r["category"] != "expected"]
    fp = [r for r in unexp if float(r["observed_abundance"]) >= args.min_abundance]
    n_detected = sum(r["detected"] == "yes" for r in exp_rows)

    # L1 distance only when every expected taxon has a known proportion
    if all(exp is not None for _, _, exp in expected):
        l1 = sum(abs(float(r["observed_abundance"]) - float(r["expected_abundance"])) for r in rows)
        l1 = f"{l1:.6f}"
        tot_o = sum(float(r["observed_abundance"]) for r in rows)
        tot_e = sum(float(r["expected_abundance"]) for r in rows)
        shared = sum(min(float(r["observed_abundance"]), float(r["expected_abundance"])) for r in rows)
        bc = f"{1 - 2 * shared / (tot_o + tot_e):.4f}" if tot_o + tot_e else "NA"
        ratios = [abs(float(r["log2_ratio"])) for r in exp_rows
                  if r["log2_ratio"] != "NA" and float(r["expected_abundance"]) >= args.min_expected_ratio]
        mal = f"{sum(ratios) / len(ratios):.3f}" if ratios else "NA"
        worst = max((r for r in exp_rows if r["log2_ratio"] != "NA" and float(r["expected_abundance"]) >= args.min_expected_ratio),
                    key=lambda r: abs(float(r["log2_ratio"])), default=None)
        worst = f"{worst['taxon']} ({worst['log2_ratio']})" if worst else "NA"
        exp_genus = Counter()
        for species, _, exp in expected:
            exp_genus[genus(species)] += exp
        bc_genus = f"{bray_curtis(observed_genus, exp_genus):.4f}"
    else:
        l1 = bc = mal = worst = bc_genus = "NA"

    def names(status):
        return ";".join(r["taxon"] for r in exp_rows if r["status"] == status) or "none"

    detectable = [r for r in exp_rows if r["status"] != "below_detection_limit"]
    exp_genera = {genus(r["taxon"]) for r in exp_rows}
    det_genera = {g for g in exp_genera if g in observed_genera}

    summary = {
        "sample": args.sample,
        "mock": args.mock_name,
        "n_expected": len(exp_rows),
        "n_detected": n_detected,
        "recall": f"{n_detected / len(exp_rows):.4f}",
        "missing": ";".join(r["taxon"] for r in exp_rows if r["detected"] == "no") or "none",
        "classified_reads": f"{n_reads:.0f}",
        "n_detectable": len(detectable),
        "recall_detectable": f"{sum(r['detected'] == 'yes' for r in detectable) / len(detectable):.4f}" if detectable else "NA",
        "recall_genus": f"{len(det_genera) / len(exp_genera):.4f}",
        "genus_only": names("genus_only"),
        "below_detection_limit": names("below_detection_limit"),
        "not_amplified": names("not_amplified") if nov_genera is not None else "NA",
        "missed": names("missed"),
        "unexpected_abundance": f"{sum(float(r['observed_abundance']) for r in unexp):.6f}",
        "n_false_pos": len(fp),
        "n_false_pos_near_neighbour": sum(r["category"] == "near_neighbour" for r in fp),
        "n_false_pos_off_target": sum(r["category"] == "off_target" for r in fp),
        "false_pos_min_abundance": args.min_abundance,
        "l1_distance": l1,
        "bray_curtis": bc,
        "bray_curtis_genus": bc_genus,
        "mean_abs_log2_ratio": mal,
        "worst_taxon_log2_ratio": worst,
    }
    with open(f"{args.prefix}_mock_summary.tsv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary.keys()), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow(summary)


if __name__ == "__main__":
    main()
