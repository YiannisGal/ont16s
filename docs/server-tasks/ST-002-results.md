# ST-002 results — Emu speed test

**Status: Executed (2026-10-08, server). Not validated.** Single replicate per setting;
timings are indicative only.

Data and logs: `/mnt/Ubuntu_HD5/yiannis/ont16s_data/ST-002/` (not in git).
Script: `run_st002.sh`; comparison: `compare.py` → `logs/compare.txt`.

## Question

ST-001 showed Emu takes ~50 min per 53 k-read chunk at 8 threads. Where does the time go,
does it scale with threads, and does minimap2 preset `--type lr:hq` (intended for
high-accuracy long reads, e.g. R10.4.1 SUP) help?

## Setup

- Input: ST-001 20 k subsample (`ST-001/reads/sub20k.fastq`, seed 42).
- Emu 3.6.2 (`quay.io/biocontainers/emu:3.6.2--hdfd78af_0`), ST-001 default DB.
- Flags as ST-001 minus `--keep-read-assignments`: `--keep-counts --output-unclassified`.
- Measurements inside the container: `memory.peak` and `cpu.stat usage_usec` (cgroup v2);
  wall time from `date` around `docker run`; minimap2's own `[M::main] Real time / CPU`.
- Server load average < 1 during runs.

## Results

| Run | Preset | Threads | Wall | Container CPU | minimap2 real / CPU | Peak mem | Unmapped |
|---|---|---|---|---|---|---|---|
| A (ST-001) | map-ont (default) | 8 | 1,221 s | not measured | not logged | 2.62 GB | 7 |
| B | lr:hq | 8 | 81 s | 420 s | 51 s / 388 s | 0.94 GB | 376 (1.9 %) |
| C | map-ont (default) | 16 | 608 s | 9,187 s | 575 s / 9,151 s | 4.04 GB | 7 |

Emu calls `minimap2 -ax <preset> -t <threads> -N 50 -p .9 -K 500000000`.

Abundance (%) for taxa > 0.01 %:

| Taxon | A map-ont t8 | B lr:hq t8 | C map-ont t16 |
|---|---|---|---|
| Bacillus subtilis | 16.485 | 14.630 | 16.485 |
| Listeria monocytogenes | 14.354 | 14.894 | 14.354 |
| Staphylococcus aureus | 14.575 | 14.328 | 14.575 |
| Limosilactobacillus fermentum | 13.198 | 13.647 | 13.198 |
| Enterococcus faecalis | 9.578 | 9.905 | 9.578 |
| Gardnerella vaginalis | 8.200 | 8.393 | 8.200 |
| Bifidobacterium adolescentis | 5.995 | 6.113 | 5.995 |
| Salmonella enterica | 5.527 | 5.193 | 5.527 |
| Escherichia coli | 4.928 | 4.695 | 4.928 |
| Borreliella burgdorferi | 2.594 | 2.670 | 2.594 |
| Pseudomonas aeruginosa | 2.508 | 2.588 | 2.508 |
| Chlamydia trachomatis | 1.757 | 1.795 | 1.757 |
| Bacillus halotolerans | 0.161 | 0.519 | 0.161 |
| Bacillus mojavensis | 0.051 | 0.411 | 0.051 |
| Borreliella americana | 0.090 | 0.076 | 0.090 |
| Bacillus amyloliquefaciens | 0 | 0.083 | 0 |
| Bacillus velezensis | 0 | 0.060 | 0 |

A vs C: identical (max difference 0.0).

## Interpretation

1. **minimap2 is the bottleneck**, not Emu's EM: 9,151 of 9,187 CPU-seconds (run C).
   The non-alignment part is ~30 s.
2. **Thread scaling is ~linear** (8 → 16 threads: 1,221 → 608 s) with identical results.
   Cost ≈ 9,200 CPU-s per 20 k reads with map-ont (≈ 0.46 CPU-s/read).
3. **`lr:hq` is ~15× faster in wall time (~22× less CPU)**, but leaves 1.9 % of reads
   unmapped (vs 0.04 %) and spreads *Bacillus* reads more across congeners
   (*B. subtilis* −1.9 percentage points). All 12 expected taxa still detected.
4. No preset decision now. `--type` becomes a pipeline parameter (default `map-ont`, as
   Emu); the choice is deferred to mock-community validation (Milestone 8).

## Consequences for the pipeline

- Emu process: CPU-heavy, memory-light. Initial resource label ~8–16 CPUs, 8 GB memory;
  time should scale with read count (~0.5 CPU-s/read with map-ont).
- Expose `--emu_type` (map-ont / lr:hq / sr) as a parameter.
- Open: effect of `-N 50` (fixed inside Emu; not exposed by the CLI).
