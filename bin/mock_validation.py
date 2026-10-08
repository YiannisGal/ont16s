#!/usr/bin/env python3
"""Compare an Emu abundance table with a mock-community definition.

Writes a per-taxon table and a one-row summary. Uses only the Python standard library.
"""

import argparse
import csv
import sys

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
    """Return {species name: relative abundance} for classified taxa."""
    abundance = {}
    for row in read_tsv(path):
        if row["tax_id"] in NON_TAXA:
            continue
        name = row.get("species") or f"tax_id:{row['tax_id']}"
        abundance[name] = abundance.get(name, 0.0) + float(row["abundance"])
    return abundance


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
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()

    expected = load_mock(args.mock)
    observed = load_emu(args.emu)

    rows = []
    matched = set()
    for species, names, exp in expected:
        hits = [n for n in observed if n in names]
        matched.update(hits)
        obs = sum(observed[n] for n in hits)
        rows.append({
            "taxon": species,
            "category": "expected",
            "detected": "yes" if obs > 0 else "no",
            "observed_abundance": f"{obs:.6f}",
            "expected_abundance": "NA" if exp is None else f"{exp:.6f}",
            "reported_as": ";".join(sorted(hits)),
        })

    expected_genera = {genus(n) for _, names, _ in expected for n in names}
    for name, obs in sorted(observed.items(), key=lambda kv: -kv[1]):
        if name in matched:
            continue
        rows.append({
            "taxon": name,
            "category": "near_neighbour" if genus(name) in expected_genera else "off_target",
            "detected": "yes",
            "observed_abundance": f"{obs:.6f}",
            "expected_abundance": "0",
            "reported_as": name,
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
    else:
        l1 = "NA"

    summary = {
        "sample": args.sample,
        "mock": args.mock_name,
        "n_expected": len(exp_rows),
        "n_detected": n_detected,
        "recall": f"{n_detected / len(exp_rows):.4f}",
        "missing": ";".join(r["taxon"] for r in exp_rows if r["detected"] == "no") or "none",
        "unexpected_abundance": f"{sum(float(r['observed_abundance']) for r in unexp):.6f}",
        "n_false_pos": len(fp),
        "n_false_pos_near_neighbour": sum(r["category"] == "near_neighbour" for r in fp),
        "n_false_pos_off_target": sum(r["category"] == "off_target" for r in fp),
        "false_pos_min_abundance": args.min_abundance,
        "l1_distance": l1,
    }
    with open(f"{args.prefix}_mock_summary.tsv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary.keys()), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow(summary)


if __name__ == "__main__":
    main()
