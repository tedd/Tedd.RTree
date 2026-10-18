# Measured results

Production source remains unchanged pending the mutation-scope decision and independent confirmation of the combined SIMD source. Construction parity is supported exploratorily on this Ryzen 5950X/AVX2 host; it is not a release-wide or cross-platform guarantee.

All times below are microseconds. Query aggregates sum four measured width groups covering 64 fully materialized and consumed queries. Medians are across complete process blocks; they are descriptive, not confidence intervals or individual latency percentiles. Distinct PIDs do not establish independence. Every observation remains in its original epoch.

## Confirmed shared-array layout, scalar key construction

Five blocks per fixture. Build, mutation and post-move changes are relative to the matching control. Mutation is one 1,000-move batch per process.

| Entries | Distribution | Baseline queries | Shared queries | Query change | Build change | Mutation change | Post-move queries |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1,000 | uniform | 14.865 | 13.787 | -7.3% | -1.6% | +1.9% | +0.0% |
| 1,000 | clustered | 9.286 | 7.727 | -16.8% | -2.2% | +0.8% | -0.5% |
| 10,000 | uniform | 85.542 | 72.156 | -15.6% | -1.0% | +4.8% | +7.3% |
| 10,000 | clustered | 75.281 | 51.724 | -31.3% | +0.2% | +0.8% | +5.2% |
| 100,000 | uniform | 785.265 | 561.923 | -28.4% | +12.3% | +4.0% | +3.0% |
| 100,000 | clustered | 755.968 | 442.721 | -41.4% | +7.8% | +8.2% | +0.9% |

Build allocation decreases approximately 2.3–2.4%; mutation allocation increases up to 12.1%. The 12.3% build regression is retained, not erased by later epochs.

## SIMD construction alternatives

Three blocks per fixture in each distinct study. Ordinary vector source adds eight-lane integer Hilbert/Morton transforms with scalar quantization, tails and fallback. It retains the shared-array layout. Inlining is a separate intervention; it removes the call but does not improve build time against the ordinary vector method.

| Study | Distribution | Baseline build | Shared build | Vector build | Inlined build | Vector vs baseline |
|---|---|---:|---:|---:|---:|---:|
| keyvectors | uniform | 5413.406 | 5268.700 | 4820.941 | — | -10.9% |
| keyvectors | clustered | 5038.366 | 5360.147 | 4932.553 | — | -2.1% |
| keyinlines | uniform | 5370.463 | 5297.900 | 4806.609 | 4894.438 | -10.5% |
| keyinlines | clustered | 5023.234 | 5719.622 | 4820.147 | 4861.438 | -4.0% |

The first vector study narrowly fails its post-move guard (+10.04% uniform). The later four-arm study does not replace that failed observation. Forced inlining is rejected as an unsupported isolated optimization. Both sources require an explicit mutation tradeoff decision and fresh confirmation before adoption. Correctness passes include the full typed/reference suite, scalar dispatch, exact fixture order fingerprints, and a 65,536-tuple scalar/vector key oracle.

## Fresh closest-competitor comparison for the scalar shared-array source

Three blocks; pinned `static_aabb2d_index` 2.1.0 with native CPU tuning, thin LTO and its unsafe optimizations enabled. Both direct Rust and zero-copy interop are retained; the lower whole-workload median wins. These shared file fixtures differ from the generic-worker fixtures above. They were not rerun for the combined SIMD source.

| Entries | Distribution | Shared queries | Best Rust queries | Rust/shared ratio |
|---:|---|---:|---:|---:|
| 1,000 | uniform | 14.538 | 11.656 | 0.80× |
| 1,000 | clustered | 8.574 | 10.545 | 1.23× |
| 10,000 | uniform | 69.539 | 74.811 | 1.08× |
| 10,000 | clustered | 38.012 | 65.313 | 1.72× |
| 100,000 | uniform | 631.413 | 1218.237 | 1.93× |
| 100,000 | clustered | 485.606 | 1275.548 | 2.63× |

Rust remains faster for 1k uniform; the 10k uniform lead is small. The large-fixture margin is substantial, but no universal ranking follows.

## Transfer and runtime guardrails

These describe the scalar shared-array source; they are not confirmation of the SIMD combination. Generic/wrapper studies have two blocks and single mutation batches, so large observed changes require cautious interpretation rather than dismissal.

| Regime | Query change range | Build change range | Mutation change range | Post-move query range |
|---|---:|---:|---:|---:|
| generic | -43.3% to -2.9% | -6.8% to +19.8% | -2.6% to +26.7% | -13.9% to +17.0% |
| wrappers | -14.8% to -4.1% | -1.6% to +4.8% | +2.5% to +61.6% | -0.4% to +3.3% |
| tiered | -36.1% to +35.1% | +1.7% to +17.5% | -0.1% to +1.7% | -3.2% to +263.9% |
| final-tiered | -36.8% to -11.0% | -2.7% to -1.3% | -2.4% to -1.2% | -0.7% to +11.9% |

`tiered` enables PGO with short calibration only; it is unstable and includes material regressions. `final-tiered` is the separately declared fixed three-second warmup study. Separate normal-exit listings contain Tier1 Search/CollectValues, without proving every timed process had one identical tier state. No startup/first-request claim is made.

## Dispositions and limits

- Rejected: eager scalar predicates, tested per-rectangle SIMD query predicate, matching-run collection, BMI2 PDEP spreading, fused radix histograms, shared-value chunks, direct leaf fill, count-only span collector, forced vector-helper inlining.
- Shared contiguous values: confirmed original query benefit; documented construction/mutation/transfer tradeoffs, pending adoption decision.
- Eight-lane spatial keys: supported construction remedy, exact code/semantic evidence, pending independent combined-source confirmation and scope decision.
- DotNetLab baseline/shared profiles completed. Latest vector trace completed but stack parsing failed `invalid_path`; the failed operation and unparsed trace are retained. No successful vector reprofile claim.
- No PMU, significance, p99, multicore, Arm/other-CPU performance or hardware-disabled performance claim. Desktop load, frequency/thermal state, short blocks and inter-epoch build variation limit inference.

See [REPORT.md](REPORT.md) for prospective protocols, exact IDs, causal limitations, and the full negative-result ledger. Raw process observations, protocols and executable identities are under [benchmarks/results/simd](../../benchmarks/results/simd).
