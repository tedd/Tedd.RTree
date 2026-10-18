# Generic packed-tree measurements

This harness measures generic 2D/3D plain, snapshot, and concurrent APIs against a preserved pre-change library. All data is generated and validated in memory; no external service or database is used by the indexing workloads. Diagnostic SQLite catalogs, builds, and scratch belong in a dedicated `D:\Workspaces\AI\<task>` directory.

Preserve the baseline library source from `3d2d88f` and build it to `<workspace>\control\Tedd.RTree.dll` before making changes. Build under the same named host mutex used by `locked.ps1`, with Release configuration and `UseSharedCompilation=false`. The control and candidate callers use identical `Worker.cs`; `LibraryPath` selects the external control DLL. Run:

```powershell
.\benchmarks\generic-packed\locked.ps1 -Workspace D:\Workspaces\AI\rtree-generic-packed -Action build -Stage control
.\benchmarks\generic-packed\locked.ps1 -Workspace D:\Workspaces\AI\rtree-generic-packed -Action build -Stage candidate
.\benchmarks\generic-packed\locked.ps1 -Workspace D:\Workspaces\AI\rtree-generic-packed -Action test
.\benchmarks\generic-packed\locked.ps1 -Workspace D:\Workspaces\AI\rtree-generic-packed -Action confirmation
python .\benchmarks\generic-packed\summarize.py
python .\benchmarks\generic-packed\export-site.py
```

The confirmation budget is fixed at 288 fresh-process launches. Each validates exact result IDs, records PID/launch time and binary hashes, calibrates each operation to 100 ms, and reports one block average. Mutation code is warmed on a separate tree before the measured batch. Snapshot APIs replace complete batches and have no individual mutation metric. Harness adapters are prepared outside query timing; construction includes an identical small adapter object in each arm. Native competitors are not included in these 3D measurements.

`ordering`, `transfer`, and `inline` are separate prospective exploration budgets. The [research record](../../Research/2026-10-18-generic-packed/REPORT.md) preserves scope, source stages, candidate selection, tradeoffs, and diagnostic IDs. The unselected Hilbert 3D encoding is retained there as a prototype. `codegen` exits normally to flush full optimized JIT listings. `profile.py` uses the configured installed DotNetLab host with its own local catalog, scoped grants, owned targets/controllers, and the shared host mutex; its diagnostic data is separate from timing.
