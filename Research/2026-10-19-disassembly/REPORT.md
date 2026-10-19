# Small-index generated-code investigation

Integration branch: `main`; starting commit `f3c72ca`. The checkout was clean.
The user explicitly requested pushing the prepared implementation to main, then
continuing with disassembly. The prior 17-file patch is now applied with all
postimage SHA-256 values verified against its retained integration plan.

## Scope and prospective protocol

Use the DotNetLab guided gates with an inspected external rig. The retained
benchmark runtime is CoreCLR 10.0.13; static Rust PE disassembly is outside the
tool's qualified live managed replacement path. Do not attach to unrelated
targets or change the shared catalog. Hold `Global\Tedd.RTree.PerformanceHost`
across builds and dependent diagnostic/measurement processes. Temporary files
belong only in `D:\Workspaces\AI\rtree-disassembly-20261019`.

First build the applied library and repository tests with the repository SDK;
run all checks with hardware intrinsics enabled and disabled. Commit and push
the implementation before proceeding with the disassembly investigation.

Inspect the exact hash-bound Rust executable and DLL from the prior archive,
alongside the exact managed comparison caller. New compilation is diagnostic
and must not be substituted for the recorded Rust baseline. Focus on 1,000
uniform construction and materialized queries, with clustered input as the
contrast. Inspect exported native construction/query routines, actual managed
constructor/traversal/caller code, scalar versus vector checksum consumption,
range checks, divisions, copies, allocation calls, and branch structure.

Competing hypotheses: S1 partial ordering/ownership construction work; S2 scalar
versus vector output consumption; S3 traversal code and result appends; S4
compiler/codegen differences. Static instruction counts do not establish dynamic
frequency, cache/branch misses, or a causal share of total elapsed time.

If generated code supports a specific intervention, freeze a separate bounded
paired protocol before timing. Preserve exact-ID correctness, equal result
materialization/consumption, both small distributions, and large-input guards.
No universal-win or statistical-significance claim follows from descriptive
medians. Diagnostic runs are not quiet timing observations. No database,
application service, deployment, package publication, or website write is used.

## First generated-code findings and frozen intervention study

Implementation commit `da4883e887797fc52af1aac7b9856e3b779e3b06` was pushed to
`origin/main` and verified against `ls-remote`. Library/tests build with zero
warnings/errors; the complete repository checks pass with intrinsics on/off.

The exact native DLL exports `index_query` and `index_query_leaf` at the same
RVA 0xac50, jumping to Context query at RVA 0x4200. Its static-index leaf loop
at RVA 0x438f loads one complete rectangle and uses `vinsertf128`,
`vperm2f128`, `vcmpnltpd`, and `vtestpd` for four inclusive comparisons. Its
internal-node loop remains scalar. This is SIMD across coordinates of one box,
not across four independent boxes. The managed SearchLevel emits scalar
coordinate predicates and separate result append/capacity checks (809 bytes).

The exact direct Rust worker contains a post-query checksum at RVA 0x163b0:
four `vpmovzxdq`/`vpaddq` accumulators, increment adjustment, horizontal
reduction, and scalar tails. The managed caller's actual consume lambda must
be inspected separately from LINQ oracle code; the former is a List<int>
enumeration. These are concrete code differences, not causal elapsed-time
fractions. No native program is recompiled in this study.

Before intervention timing, freeze six modes: unchanged managed list caller,
span-only checksum caller, vector checksum caller, leaf-only AVX predicate
with original list caller, leaf AVX plus vector checksum, exact direct Rust.
The checksum variants are benchmark-caller changes, not library speedups.
The leaf intervention retains the original AoS bounds, recursion, internal
predicates, subtree copies, construction and public API; unlike the earlier
rejected normalized representation, it only replaces the leaf predicate.
AVX loads are exactly one valid 32-byte rectangle; unsupported hosts use the
scalar predicate. Checksum vectorization is restricted to fixture IDs in
0..N-1 and consumes all materialized IDs, preserving the original sum.

Budget: three shuffled process blocks, six fixtures (1k/10k/100k,
uniform/clustered), six modes = 108 scheduled quiet processes; seed 191079.
CoreCLR 10.0.13, repository-pinned SDK, affinity mask 4, Release,
tiering/PGO off, no observer, calibration at least 100 ms per operation.
Every process performs exact result-ID and timed-checksum validation before
timing. Keep every observation; stop on failures, no favorable reruns.
Primary library hypothesis: at least 10% lower complete 1k uniform queries
for leaf-only versus unchanged list control, with every six-fixture build/query
median no more than 10% worse. Caller hypotheses report their matched contrasts
separately; no old/new ranking splice or automatic adoption. Full public tests
with intrinsics on/off and actual emitted predicate/checksum code are required
before quiet execution. A positive library result still needs independent
ordinary-tiering and fresh-build confirmation in a subsequent protocol.

## First study disposition and prospective refinement

All 108 quiet processes completed and validated every query. On 1k uniform,
list/span/SIMD/leaf/combined/Rust median totals are
15.680/15.207/13.319/14.681/12.358/11.840 us. Leaf-only improves 6.4%, below
the frozen 10% primary; reject this source for adoption. A faster consumer
reduces the same index's caller time, not the index's work. The measured
2.361-us consumer contrast is substantial relative to the 3.840-us same-epoch
list/Rust gap, but do not treat this ratio as a general causal wall-time share.
Preserve the native 1k uniform outlier (26.236 us), all managed outliers, and
every construction observation even though construction source is unchanged.

The actual managed consume lambda is 107 bytes and scalar. Its inlined
enumeration has no per-item version comparison; a value-array range check
remains. Do not attribute the loss to an imagined virtual MoveNext call or
enumerator version test. The first AVX leaf source reloads the query per box
and emits two extracts/two inserts plus moves before compare/mask extraction.
Rust loads the query outside the loop and emits one insert/one lane permute
followed by compare/test.

R10 (A03/C18/V03/V05): preserve AoS layout and scalar internal-node predicates;
hoist the query vector once per leaf-range invocation and express the exact
one-insert/one-permute AVX predicate with TestC. Finite ordered coordinates
make the native unordered-not-less-than comparison equivalent to inclusive
scalar predicates; hardware-disabled execution uses the original scalar loop.
No constructor, normalization, result container, or output-order change.

Before R10 observations freeze five modes: original list, original SIMD
consumer, refined leaf with list, refined leaf with the identical SIMD
consumer, exact direct Rust. Three shuffled blocks/all six fixtures = 90
quiet processes, seed 191080. Same runtime/affinity/calibration/observer and
exact-ID/checksum rules as the first study. Primary >=10% lower 1k uniform
queries with list versus original list, no >10% build/query median regression
on any six fixtures. This is a distinct generated-code remedy, not more samples
of the rejected first AVX source. Full original API tests with intrinsics on/off
and emitted-code checks precede quiet timing. A passing exploratory result is
not automatic main-source adoption or a new complete competitor ranking.

## Construction and attribution limits

The pinned native source uses `unsafe_optimizations`: uninitialized owned box
storage, unchecked index helpers, and a partial binary MSD radix partition
which stops within leaf groups. Its exact DLL radix routine (RVA 0x49e0,
called from RVA 0x2f26 and recursively at 0x4e27) still emits variable integer
divisions for node-group boundaries and guarded swaps. Its common-prefix scan
also contains SIMD XOR/OR reductions. Do not characterize it as universally
check-free or division-free. The managed constructor's small path uses the
framework paired-key introsort; its emitted constructor also contains metadata,
allocation and gather work. Both implementations scan total bounds.

This disassembly identifies different work/instructions, not the elapsed-time
cause of either construction deficit. The retained earlier attempts at exact
binary partition, owned swaps, smaller radix threshold, packed-64 sorting and
vector bounds reductions failed their adoption gates. Construction is unchanged
in the new query experiments. Do not relabel a checksum-caller improvement as
construction or library-query progress, and do not discard unfavorable build
observations from a query-focused study.

Registry coverage for this follow-up: A03 (hoist invariant query), A06 (partial
ordering, retained rejected ports), C01/V06 (independent reduction accumulators),
C18 (actual caller/inlining), M04/M24 (span view and remaining range guards),
V01/V03/V04/V05/V08/V17/V18 (SIMD comparisons, masks, shuffles, widening,
safe tails and fallback). Memory/branch/port/cache causal claims require evidence
beyond the static/JIT code retained here. No PMU events were collected.

The implementation's remote CI run is successful:
https://github.com/tedd/Tedd.RTree/actions/runs/39253485389 . The workflow's
main branch runs solution build/test, competitor validation and package
generation; publication jobs require the separate deploy branch. No redundant
local package build is required after that successful check.

## Final disposition

All 198 scheduled quiet processes complete (990 raw operation rows), with no
discarded/replaced observations. Both changed libraries build without warnings
or errors and pass the entire original/public API suite with intrinsics on/off.
Every quiet process checks exact result IDs and timed checksums for 64 windows.
The source and diagnostic identities, all construction/query observations,
medians/ranges and allocations are retained, including unfavorable outliers.

R10 actually hoists the query and emits the native-style insert/permute/compare/
test sequence. Its whole SearchLevel is 905 bytes versus the original 809;
extra upper-vector preservation occurs around the result-growth slow path.
The intended hot-loop simplification did not produce the primary gain. Fresh
matched 1k uniform list/tuned/Rust query medians are 15.457/14.563/11.836 us:
5.8% lower than control, below the declared 10% primary. All six-fixture
build/query regression guards pass for R10, but the primary fails. Reject R10
for adoption. The first leaf source also fails its primary and a 10k clustered
build guard (1.1503x), despite unchanged constructor source; no causal explanation
for that build difference is established or required to erase the guard.

The same-epoch SIMD-consumer control is 13.205 us; tuned leaf plus identical
SIMD consumer is 12.356 us, still 4.4% slower than Rust. Reducing checksum work
accounts for a measured caller improvement, not a new library algorithm. Both
studies support investigating consumer code before attributing the complete
caller gap to tree traversal. Neither proves that all the remaining gap is in
the caller, nor that any cache/branch/port effect is dominant.

The two small construction deficits remain unresolved. No new production source
is selected from these studies; main retains the independently validated and
pushed `da4883e` implementation. The prior 9/12 complete external matrix remains
the applicable published-comparison candidate; do not splice the new two-library
caller experiments into it or update a website ranking from these numbers.

Further untested directions are exact-type versus interface caller dispatch,
visitor/span-output contracts, genuinely batched queries, or different small-index
representations. They require their own complete-work/equivalence protocols and
construction/query guards. Repeating either rejected predicate unchanged is
not the next experiment. This follow-up completes the bounded disassembly and
two-intervention investigation; it does not establish universal dominance.

The research is integrated into the original `main` branch. Preserve a verified
reproduction archive before removing the owned scratch directory; `cleanup.json`
records the final resolved target and result. No task worktree was created.
