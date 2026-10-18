# Capability scope for the comparison charts

Reviewed 18 October 2026 against the versions measured on the website. This table compares particular indexes, not entire geometry frameworks or every available query operation. Tedd.RTree's row includes its native 2D/3D family; the speed charts measure the original 2D double API. No 3D competitor speed claim follows from those timings.

| Index | Changes after construction | Dimensions | Coordinates | Construction |
|---|---|---|---|---|
| Tedd.RTree 1.0.14 | Insert, remove, move | Native 2D and 3D | int, long, float, double | Bulk or incremental |
| RBush 4.0.0 | Insert, delete | 2D | double | Bulk or incremental |
| NTS STRtree 2.6.0 | Remove only; no new inserts | 2D | double | Packed bulk build |
| RTree 1.1.0 | Add, delete | 3D; exact 2D embedding at z=0 | float | Incremental insertion |
| Enyim.Collections.RTree 1.0.5 | Insert, remove | 2D | int | Bulk or incremental |
| static_aabb2d_index 2.1.0 | Rebuild for changes | 2D | Generic numeric types, including integers/custom types | Packed bulk build |
| geo-index 0.4.0, Hilbert/STR | Rebuild for changes | 2D | i8/u8/i16/u16/i32/u32/f32/f64 | Packed bulk build |

Tedd offers Update/Move entry points. Other mutable indexes can move entries by removing and reinserting them; absence of a move entry point is not an inability to move data. NTS STRtree supports concurrent read-only queries and removals. It must not be described as fully immutable or lacking concurrency. Static Rust indexes can likewise serve concurrent read-only workloads; Tedd's concurrent-update and snapshot-publication APIs describe distinct update contracts, not exclusive support for concurrent reading.

## Source evidence

- [Tedd.RTree source corresponding to NuGet 1.0.14](https://github.com/tedd/Tedd.RTree/tree/af521dbfc18c00747ea4870e1fa8de2f8ae6e10d/src/Tedd.RTree): RTree/RTree2D/RTree3D expose BulkLoad, Insert, Remove, Update and SearchBatch. Typed geometry is retained for search; int/long split metrics are exact. Concurrent variants use reader/writer locking; snapshot variants build separately and publish complete trees with lock-free reads. Tests cover adjacent long coordinates above 2^53. These API capabilities do not imply all numeric types are equally fast.
- [RBush 4.0.0 source](https://github.com/viceroypenguin/RBush/tree/b8690322abac35d835baa2fdca4a3918ed77a910/RBush): RBush.cs provides Insert, Delete and BulkLoad; Envelope.cs has four double coordinates. The package metadata identifies this exact source revision.
- [NTS 2.6.0 STRtree](https://github.com/NetTopologySuite/NetTopologySuite/blob/97d26b92586448b52d5a4f0c060217f94f882c75/src/NetTopologySuite/Index/Strtree/STRtree.cs): versioned remarks specify two dimensions, no inserts after build, removals and thread-safe queries. [Envelope](https://github.com/NetTopologySuite/NetTopologySuite/blob/97d26b92586448b52d5a4f0c060217f94f882c75/src/NetTopologySuite/Geometries/Envelope.cs) uses double bounds. NTS offers other data structures/query features outside this comparison.
- [RTree repository API](https://github.com/drorgl/cspatialindexrt/tree/41e45bd56c55362cc1c5726063530a99c720838c/RTree): RTree.cs provides Add/Delete and the Rectangle type fixes DIMENSIONS=3 with float arrays. Its 1.1.0 published API/benchmark adapter uses incremental Add. Its package metadata does not pin an exact source commit; the repository review is supporting evidence, not proof of binary/source identity.
- [Enyim repository API](https://github.com/marchello2000/RTree/tree/5667d313a786f61eb5a977219c893947958f4630/src/RTree): Load, Insert and Remove; Envelope stores four int coordinates. The published 1.0.5 package lacks an exact source-build identity, as recorded in the existing package provenance review.
- [static_aabb2d_index pinned implementation](https://github.com/jbuckmccready/static_aabb2d_index/blob/a511a6327e14a0f0418cea01c401bf147e0e835c/src/static_aabb2d_index.rs): add belongs to the builder; the completed index exposes read-only queries/accessors and no insertion/removal path. [README](https://github.com/jbuckmccready/static_aabb2d_index/blob/a511a6327e14a0f0418cea01c401bf147e0e835c/README.md) identifies a static 2D index and numeric generic/custom-type support. No claim that Tedd alone supports integer coordinates is justified.
- [geo-index pinned README](https://github.com/georust/geo-index/blob/e6efbb01d3c298e8963c8b7d1aab40c1bd540715/README.md): immutable, bulk-only, two-dimensional indexes; enumerates supported coordinate types. Hilbert/STR are construction layouts of the same R-tree API. Its binary formats and other query features are outside the capability table.

## Speed claim policy

The callout uses the selected fixture's actual chart medians. It names competitors that block new inserts after construction only when Tedd has a lower measured 64-query median. It claims lower construction **and** query medians only for the subset where both comparisons hold; otherwise it states query medians alone. A lower descriptive median is not a significance test or a universal fastest claim. In particular, the 100k clustered construction results do not support the stronger combined claim against the Rust indexes; the combined claim in that fixture names NTS alone. No measurements are rerun, rescaled or discarded for this copy change.

The capability data are maintained in [index-capabilities.json](../site/assets/index-capabilities.json); [the generator](csharp-charts/capabilities.py) renders the static fallback, and app.js applies the same rule when the fixture changes. The capability table and source references remain usable without JavaScript. The existing Rust scoring still gives each competitor the better whole-workload median of direct Rust and optimized interop.
