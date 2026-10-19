# Confirmed optimization results

Median microseconds. Queries append and consume all IDs from 64 windows. Complete mode medians select NTS list/visitor and Rust direct/interop; all individual modes remain in raw results. NTS visitor does not materialize IDs.

Packed wins 9/12 against the seven external libraries and 9/12 when the existing mutable tree is also a choice. An explicitly best-of-Tedd portfolio wins 9/12 external cells; it is not an automatically dispatched object.

| Entries | Distribution | Operation | Packed (us) | Closest external | External (us) | External / packed |
|---:|---|---|---:|---|---:|---:|
| 1,000 | uniform | build | 21.890 | static_aabb2d_index (Rust) | 16.737 | 0.765 |
| 1,000 | uniform | queries | 15.595 | static_aabb2d_index (Rust) | 11.603 | 0.744 |
| 1,000 | clustered | build | 21.303 | static_aabb2d_index (Rust) | 20.219 | 0.949 |
| 1,000 | clustered | queries | 9.066 | static_aabb2d_index (Rust) | 10.499 | 1.158 |
| 10,000 | uniform | build | 357.801 | geo-index STR (Rust) | 619.097 | 1.730 |
| 10,000 | uniform | queries | 69.821 | static_aabb2d_index (Rust) | 78.310 | 1.122 |
| 10,000 | clustered | build | 443.869 | static_aabb2d_index (Rust) | 555.250 | 1.251 |
| 10,000 | clustered | queries | 38.365 | static_aabb2d_index (Rust) | 67.822 | 1.768 |
| 100,000 | uniform | build | 3037.431 | geo-index STR (Rust) | 7449.569 | 2.453 |
| 100,000 | uniform | queries | 627.865 | geo-index Hilbert (Rust) | 1300.754 | 2.072 |
| 100,000 | clustered | build | 3160.056 | geo-index STR (Rust) | 7083.087 | 2.241 |
| 100,000 | clustered | queries | 473.917 | static_aabb2d_index (Rust) | 1303.571 | 2.751 |

## confirmation-3

| Entries | Distribution | Mode | Build (us) | Queries (us) |
|---:|---|---|---:|---:|
| 1,000 | clustered | control | 26.646 | 8.920 |
| 1,000 | clustered | packed | 21.137 | 8.969 |
| 1,000 | clustered | rust | 20.186 | 10.569 |
| 1,000 | uniform | control | 26.841 | 15.194 |
| 1,000 | uniform | packed | 21.432 | 15.259 |
| 1,000 | uniform | rust | 16.760 | 11.555 |
| 10,000 | clustered | control | 530.060 | 37.873 |
| 10,000 | clustered | packed | 438.581 | 37.910 |
| 10,000 | clustered | rust | 563.254 | 67.065 |
| 10,000 | uniform | control | 478.707 | 69.150 |
| 10,000 | uniform | packed | 378.609 | 69.052 |
| 10,000 | uniform | rust | 632.682 | 79.410 |
| 100,000 | clustered | control | 3663.991 | 475.420 |
| 100,000 | clustered | packed | 3053.694 | 474.122 |
| 100,000 | clustered | rust | 6746.100 | 1283.584 |
| 100,000 | uniform | control | 3817.594 | 610.325 |
| 100,000 | uniform | packed | 3298.022 | 615.042 |
| 100,000 | uniform | rust | 7754.462 | 1214.460 |

## tiered-3

| Entries | Distribution | Mode | Build (us) | Queries (us) |
|---:|---|---|---:|---:|
| 1,000 | clustered | control | 29.263 | 9.832 |
| 1,000 | clustered | mutable | 40.413 | 9.950 |
| 1,000 | clustered | packed | 22.155 | 9.253 |
| 1,000 | clustered | rust | 20.197 | 10.598 |
| 1,000 | uniform | control | 31.113 | 19.292 |
| 1,000 | uniform | mutable | 41.204 | 17.452 |
| 1,000 | uniform | packed | 22.418 | 15.715 |
| 1,000 | uniform | rust | 16.750 | 11.566 |
| 10,000 | clustered | control | 594.448 | 42.876 |
| 10,000 | clustered | mutable | 488.312 | 54.579 |
| 10,000 | clustered | packed | 413.561 | 40.870 |
| 10,000 | clustered | rust | 559.623 | 68.058 |
| 10,000 | uniform | control | 653.296 | 331.773 |
| 10,000 | uniform | mutable | 426.519 | 86.787 |
| 10,000 | uniform | packed | 356.539 | 74.237 |
| 10,000 | uniform | rust | 634.150 | 78.826 |
| 100,000 | clustered | control | 4302.738 | 549.570 |
| 100,000 | clustered | mutable | 6706.731 | 819.550 |
| 100,000 | clustered | packed | 3507.266 | 531.623 |
| 100,000 | clustered | rust | 6710.900 | 1275.547 |
| 100,000 | uniform | control | 4182.947 | 719.469 |
| 100,000 | uniform | mutable | 6939.350 | 922.499 |
| 100,000 | uniform | packed | 3834.088 | 642.604 |
| 100,000 | uniform | rust | 7770.200 | 1212.528 |

## fallback-3

| Entries | Distribution | Mode | Build (us) | Queries (us) |
|---:|---|---|---:|---:|
| 1,000 | clustered | control | 44.939 | 9.211 |
| 1,000 | clustered | packed | 41.240 | 9.139 |
| 1,000 | uniform | control | 44.777 | 16.513 |
| 1,000 | uniform | packed | 41.709 | 15.611 |
| 10,000 | clustered | control | 602.354 | 38.149 |
| 10,000 | clustered | packed | 603.913 | 38.061 |
| 10,000 | uniform | control | 594.608 | 75.826 |
| 10,000 | uniform | packed | 619.479 | 73.467 |
| 100,000 | clustered | control | 5739.059 | 473.514 |
| 100,000 | clustered | packed | 5349.309 | 475.813 |
| 100,000 | uniform | control | 5881.809 | 636.971 |
| 100,000 | uniform | packed | 5429.681 | 623.750 |

All original failures, outliers, regime guards and prototype results remain in REPORT.md and raw epoch directories. Process repetitions do not establish independence, significance, p99, or universal dominance. Source integration does not publish NuGet packages or the website.
