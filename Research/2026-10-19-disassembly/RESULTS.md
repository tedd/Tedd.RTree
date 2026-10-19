# Disassembly intervention results

Median microseconds for all 64 materialized-and-consumed query windows. All construction times, individual query groups, ranges, allocations and raw observations remain in the JSON/raw files. These are descriptive exploratory results, not a new complete competitor ranking. SIMD consumer changes affect caller work, not library work.

## First intervention

| Entries | Distribution | List | SIMD consumer | AVX leaf + list | AVX leaf + SIMD | Rust |
|---:|---|---:|---:|---:|---:|---:|
| 1,000 | uniform | 15.680 | 13.319 | 14.681 | 12.358 | 11.840 |
| 1,000 | clustered | 9.050 | 6.157 | 9.001 | 6.092 | 10.620 |
| 10,000 | uniform | 70.512 | 51.863 | 66.496 | 48.356 | 79.115 |
| 10,000 | clustered | 38.549 | 19.904 | 37.953 | 18.662 | 67.647 |
| 100,000 | uniform | 613.436 | 357.746 | 603.187 | 339.495 | 1246.113 |
| 100,000 | clustered | 526.166 | 199.790 | 472.473 | 188.947 | 1290.114 |

Library primary ratio: 0.936298; guard failures: 1.

## Refinement

| Entries | Distribution | List | SIMD consumer | AVX leaf + list | AVX leaf + SIMD | Rust |
|---:|---|---:|---:|---:|---:|---:|
| 1,000 | uniform | 15.457 | 13.205 | 14.563 | 12.356 | 11.836 |
| 1,000 | clustered | 9.074 | 6.149 | 8.994 | 5.996 | 10.538 |
| 10,000 | uniform | 70.223 | 51.687 | 63.168 | 44.607 | 79.717 |
| 10,000 | clustered | 38.382 | 19.764 | 37.229 | 18.309 | 66.618 |
| 100,000 | uniform | 613.834 | 359.783 | 580.074 | 311.242 | 1231.706 |
| 100,000 | clustered | 476.511 | 197.938 | 465.567 | 185.211 | 1282.063 |

Library primary ratio: 0.942187; guard failures: 0.
