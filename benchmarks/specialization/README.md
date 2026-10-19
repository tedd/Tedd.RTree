# Packed-index specialization research

[Research protocol](../../Research/2026-10-19-specialization/REPORT.md), [design and remaining hypotheses](../../Research/2026-10-19-specialization/DESIGN.md), and [results](../../Research/2026-10-19-specialization/RESULTS.md).

The proposal patch is reviewable research; the production library is unchanged. No script publishes or deploys the website. `comparison-ready.json` is an experimental chart input, not a released implementation's score.

`contracts-only.patch` contains just the additive interfaces and declarations on the nine existing classes. `packed-index.patch` adds the experimental packed implementation and vector helper after those contracts. `specialization.patch` combines both. The contracts-only build independently passes the full existing suite and the interface checks, with intrinsics enabled/disabled. None of these patches is applied. The ordinary-tiering failure prevents an unrestricted performance-adoption claim for the packed implementation.

All temporary sources, builds, fixtures, logs, IPC and the local DotNetLab catalog use `D:\Workspaces\AI\rtree-specialization-20261019`. Scripts refuse to overwrite an existing timing epoch. Performance prerequisites, worker processes and diagnostics hold `Global\Tedd.RTree.PerformanceHost`; the coordinator assigns affinity mask 4. Measurement requires the retained matching runtime (CoreCLR 10.0.13), SDK 10.0.402, and Windows x64. The measured host is a Ryzen 9 5950X; performance on other CPUs is unestablished.

The reproduction archive and SHA-256 manifest preserve the actual measured sources, callers, libraries, fixtures, native binaries and build/diagnostic evidence. Verify the archive and every entry before extracting only relative, contained paths into a dedicated task directory. The earlier SIMD archive supplies the retained pinned native source archives; its identity is recorded in the reproduction manifest. Do not restore policy/signing files or reuse expired grants.

The staged exploratory sequence was:

```powershell
python benchmarks/specialization/research.py prepare
python benchmarks/specialization/research.py exploration
python benchmarks/specialization/research.py prepare-columns
python benchmarks/specialization/research.py columns
python benchmarks/specialization/research.py keys
python benchmarks/specialization/research.py prepare-guards
python benchmarks/specialization/research.py guards
python benchmarks/specialization/research.py leaf-columns
python benchmarks/specialization/research.py prepare-capacities
python benchmarks/specialization/research.py capacities
python benchmarks/specialization/research.py prepare-radix
python benchmarks/specialization/research.py small-radix
```

Initial setup creates the designated directory, restores and verifies the earlier archive under `retained`, and copies its pinned `global.json` to the task root. `prepare` then copies current library source into isolation. The archive records exact historical identities; changed checkout/compiler dependencies define a new experiment, not a replacement for historical observations. Existing setup failures are retained separately.

The frozen selected-source sequence is:

```powershell
python benchmarks/specialization/finalize.py KeyPackedRTree
python benchmarks/specialization/confirm.py confirmation
python benchmarks/specialization/confirm.py tiered
python benchmarks/specialization/confirm.py prepare-comparison
python benchmarks/specialization/confirm.py comparison
python benchmarks/specialization/summarize.py
```

The subsequent targeted `boundary.py` experiment tests a NoInlining remedy on the failed ordinary-tiering fixture. Its 18 processes and source/binaries are separate; it fails its primary gate and is not substituted into the selected source or comparison. `diagnose.py` retains the byte-identical fresh rebuild and actual ordinary-tiering code. `audit.py` verifies all 798 scheduled processes, every build/query group, the frozen binaries, unchanged production sources and four completed capture/analysis pairs.

Comparators reference the four exact distributed package DLLs copied from the pinned installed cache into task storage; package archive/DLL hashes are retained. The three Rust modes reuse verified executables/native DLLs from the prior source-bound archive. Their paths read explicit fixtures and operate in memory. Enyim's distributed optimization-disabled binary is preserved. SharpTrees is not ranked because retained exact-result validation fails.

`profile.py <task-root> <durable-destination> mutable|packed` starts an owned persistent DotNetLab MCP controller and one prepared target at a time. It initializes only task-local SQLite, issues scoped observe grants through the CLI, discovers identities/capabilities, requests captures once and retains terminal failures. Normal timing remains an external harness comparison of a dependency library; it is not a qualified ReJIT/promotion operation.

The full comparison retains all 13 API/execution modes. Summary selection uses the lower *whole-operation median*, as prospectively declared, rather than minimum samples or per-window mixing. The chart-ready artifact includes all nine compared implementations (two Tedd variants plus seven competitors). Independent five-process confirmation and three-process ordinary-tiering checks remain separate datasets. Queries consume every returned ID and compare exact IDs against a brute-force oracle before timing.

No test connects to a server or application database. Fixture generation, builds and profiling are local research operations. Applying `specialization.patch` to the production library requires the outstanding authorization described in the report; `git apply --check` is nonmutating.
