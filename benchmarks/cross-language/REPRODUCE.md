# Cross-language rectangle-index benchmark

This harness compares in-memory 2D rectangle intersection queries and index construction. Exact source identities and tool versions are in [sources.lock.json](sources.lock.json); Rust's transitive dependencies are pinned in [Cargo.lock](rust/Cargo.lock). These are source snapshots, including development branches, rather than a claim that every version label is a published release.

The published measurements use the Tedd source revision recorded as `teddCommit` in the lock file. Use that library revision when reproducing the published comparison. The build script compiles the current checkout; update provenance when measuring a different revision.

On the measurement host, use a dedicated disposable workspace:

```powershell
.\benchmarks\cross-language\fetch.ps1 -Workspace D:\Workspaces\AI\rtree-comparison-reproduction
# Inspect downloaded sources and dependency build scripts before compiling them.
.\benchmarks\cross-language\build.ps1 -Workspace D:\Workspaces\AI\rtree-comparison-reproduction
python .\benchmarks\cross-language\run.py D:\Workspaces\AI\rtree-comparison-reproduction D:\Workspaces\AI\rtree-comparison-reproduction\results
python .\benchmarks\cross-language\run.py D:\Workspaces\AI\rtree-comparison-reproduction D:\Workspaces\AI\rtree-comparison-reproduction\results-supplementary supplementary
```

`fetch.ps1` downloads sources and a SHA-256-verified portable Go toolchain. It fetches Cargo dependencies without compiling them. `build.ps1` invokes the installed .NET SDK, Clang, Rust compiler, and portable Go compiler directly. It runs no upstream benchmark, installation, npm, or CMake scripts. Rust dependency build scripts do run during Cargo compilation; inspect those first. Adjust explicit compiler/SDK paths when reproducing on another host. Compiler and linker temporary files, package caches, and build outputs belong in the disposable workspace.

The Rust manifest is staged into `WORKSPACE/rust/`, alongside `WORKSPACE/rstar/` and `WORKSPACE/geo-index/`. Its local dependency paths deliberately refer to that staged layout. The .NET project can be built directly from this repository with `--artifacts-path` pointing into the workspace.

The runner uses five separate processes per library and fixture, in a fixed shuffled order. All children inherit Windows affinity mask `4` (logical CPU 2). Each operation doubles its repetition count until a discarded calibration block reaches 100 ms, then measures one block of the same length. Consequently the raw sample is a process/block average, not an individual-operation latency. The report uses the median and observed range of the five process averages. The runner keeps serial execution, disables .NET tiered compilation, and sets `GOMAXPROCS=1`. Background applications and power policy are uncontrolled.

Fixtures contain 1,000, 10,000, or 100,000 entries, with uniform or eight-cluster placement in approximately a 1,000-by-1,000 coordinate domain. A specified 32-bit LCG generates integer-valued geometry, exact in every library's double-precision representation. Each fixture has 64 queries, in interleaved width groups of 0, 20, 200, and 1,000 units. Each timed query operation executes the 16 queries of one width and sums every returned ID plus one. These fixtures use a different PRNG from the existing .NET package comparison and their timings must not be combined.

Before timing, each process sorts returned IDs and compares them with a brute-force scan for every query. An additional four-entry fixture verifies duplicate bounds, zero-area rectangles, negative coordinates, boundary contact, complete coverage, and no matches. Every worker materializes IDs. Tedd, C, C++, Go, and `rstar` have reused result buffers; Tedd's allocating API is measured separately. `geo-index` and Flatbush use their allocating search APIs. Buffer reuse does not imply allocation-free traversal.

Construction uses prepared geometry/entries outside timing. The operation creates a new index and releases the previous index through the language's normal lifetime mechanism. Native/Rust destruction occurs within the operation; .NET/Go/JavaScript reclamation follows their garbage collectors. Go and JavaScript retain the latest constructed index; the .NET worker also retains it. These are amortized construction/lifecycle measurements, not isolated allocator-independent construction timings. `rstar` clones its consumed input vector inside timing; other input copies required by a library also belong inside timing. Tedd has bulk and incremental construction variants. C, Go, and Superliminal use incremental insertion; Boost, `rstar`, `geo-index`, and Flatbush use packed/bulk construction. Node capacities are 16 except Tidwall C/Go (upstream default 64) and `rstar` (upstream default 6). There is no capacity-tuning sweep.

`samples.json` preserves every timed process result; `summary.csv` contains medians and ranges. `fixtures.json` preserves fixture hashes and per-query hit counts. `protocol.json` records commands and timing controls. No database, application server, external service, or network client is exercised by the worker paths.

The supplementary cohort contains Boost's `rtree.query` with an output iterator that writes only IDs, plus Rust's `static_aabb2d_index` with reused result and traversal buffers. Geometry, correctness checks, timing policy, process count, and affinity match the primary run. It runs afterward as a separate cohort; the primary run's Boost measurements use `qbegin`. Both Boost APIs materialize the same IDs into a reused vector. `static_aabb2d_index` uses node capacity 16 and its default safe configuration, without the `unsafe_optimizations` feature.

Preserve results in their intended permanent destination before removing the reproduction workspace. Verify the resolved target is the specific task-owned subdirectory of `D:\Workspaces\AI\` before recursive deletion.
