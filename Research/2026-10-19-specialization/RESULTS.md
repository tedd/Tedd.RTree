# Confirmed specialization results

## confirmation

Median microseconds; queries materialize and consume all IDs from 64 windows. Ratios below 1 favor packed.

| Entries | Distribution | Operation | Mutable | Packed | Packed / mutable |
|---:|---|---|---:|---:|---:|
| 1,000 | uniform | build | 37.431 | 28.465 | 0.760 |
| 1,000 | uniform | queries | 15.027 | 15.636 | 1.041 |
| 1,000 | clustered | build | 36.847 | 27.732 | 0.753 |
| 1,000 | clustered | queries | 9.837 | 8.871 | 0.902 |
| 10,000 | uniform | build | 421.901 | 531.115 | 1.259 |
| 10,000 | uniform | queries | 80.168 | 70.292 | 0.877 |
| 10,000 | clustered | build | 448.214 | 641.763 | 1.432 |
| 10,000 | clustered | queries | 53.018 | 38.369 | 0.724 |
| 100,000 | uniform | build | 7007.259 | 3865.756 | 0.552 |
| 100,000 | uniform | queries | 880.518 | 619.577 | 0.704 |
| 100,000 | clustered | build | 6877.528 | 3839.981 | 0.558 |
| 100,000 | clustered | queries | 819.121 | 477.360 | 0.583 |
## tiered

Median microseconds; queries materialize and consume all IDs from 64 windows. Ratios below 1 favor packed.

| Entries | Distribution | Operation | Mutable | Packed | Packed / mutable |
|---:|---|---|---:|---:|---:|
| 1,000 | uniform | build | 41.591 | 28.867 | 0.694 |
| 1,000 | uniform | queries | 17.882 | 18.546 | 1.037 |
| 1,000 | clustered | build | 41.290 | 33.996 | 0.823 |
| 1,000 | clustered | queries | 10.248 | 9.805 | 0.957 |
| 10,000 | uniform | build | 452.695 | 395.818 | 0.874 |
| 10,000 | uniform | queries | 86.445 | 81.831 | 0.947 |
| 10,000 | clustered | build | 474.870 | 489.104 | 1.030 |
| 10,000 | clustered | queries | 52.396 | 60.506 | 1.155 |
| 100,000 | uniform | build | 6228.300 | 4721.816 | 0.758 |
| 100,000 | uniform | queries | 923.659 | 719.504 | 0.779 |
| 100,000 | clustered | build | 6785.425 | 4791.209 | 0.706 |
| 100,000 | clustered | queries | 837.271 | 525.684 | 0.628 |
## Fresh complete comparison

Lower whole-operation median selects NTS list/visitor or Rust direct/interop; all individual modes remain in raw summaries. Ratios above 1 favor packed. This finite matrix does not establish universal dominance.

| Entries | Distribution | Operation | Packed (us) | Fastest other | Other (us) | Other / packed |
|---:|---|---|---:|---|---:|---:|
| 1,000 | uniform | build | 28.438 | static_aabb2d_index (Rust) | 16.846 | 0.592 |
| 1,000 | uniform | queries | 15.821 | static_aabb2d_index (Rust) | 11.819 | 0.747 |
| 1,000 | clustered | build | 27.875 | static_aabb2d_index (Rust) | 20.238 | 0.726 |
| 1,000 | clustered | queries | 9.045 | Tedd.RTree (C#) | 10.069 | 1.113 |
| 10,000 | uniform | build | 660.821 | Tedd.RTree (C#) | 434.654 | 0.658 |
| 10,000 | uniform | queries | 69.955 | static_aabb2d_index (Rust) | 79.271 | 1.133 |
| 10,000 | clustered | build | 615.065 | Tedd.RTree (C#) | 470.247 | 0.765 |
| 10,000 | clustered | queries | 38.420 | Tedd.RTree (C#) | 52.737 | 1.373 |
| 100,000 | uniform | build | 4094.803 | geo-index Hilbert (Rust) | 7044.938 | 1.720 |
| 100,000 | uniform | queries | 619.337 | Tedd.RTree (C#) | 884.041 | 1.427 |
| 100,000 | clustered | build | 3886.922 | static_aabb2d_index (Rust) | 6819.137 | 1.754 |
| 100,000 | clustered | queries | 479.609 | Tedd.RTree (C#) | 816.524 | 1.702 |

Packed wins 7/12 against the seven external competitors, or 7/12 when the existing mutable tree is also a competing choice. The mutable tree wins both 10k construction cells. This is not an automatically dispatched implementation.


All medians and ranges are descriptive. Desktop load, thermals and frequency are uncontrolled; fresh processes and repetitions do not establish independence, significance or tail latency. Native allocation is unavailable. NTS visitor visits every ID; other selected query APIs materialize IDs. Build/reclamation contracts differ as declared in REPORT.md. Mutation capability is not a zero-cost timing entry. SharpTrees remains unranked after its retained correctness failure.
