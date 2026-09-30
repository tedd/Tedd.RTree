using Tedd.RTree;
internal static class VariantRegistration
{
    [System.Runtime.CompilerServices.ModuleInitializer]
    internal static void Initialize()
    {
        Screening.Variants["SpanCollector"] = entries => { var tree = new SpanCollectorRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["ListCount"] = entries => { var tree = new ListCountRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["SpanCollector"] = entries => { var tree = new SpanCollectorRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["ListCount"] = entries => { var tree = new ListCountRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["Contained"] = entries => { var tree = new ContainedRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["InternalContained"] = entries => { var tree = new InternalContainedRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["RootContained"] = entries => { var tree = new RootContainedRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["SpanTraversal"] = entries => { var tree = new SpanTraversalRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["ContainedSpan"] = entries => { var tree = new ContainedSpanRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["MatchedContained"] = entries => { var tree = new MatchedContainedRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["MatchedContainedSpan"] = entries => { var tree = new MatchedContainedSpanRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["InternalContainedSpan"] = entries => { var tree = new InternalContainedSpanRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["MatchedContainedPoint"] = entries => { var tree = new MatchedContainedPointRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["MatchedContainedSpanPoint"] = entries => { var tree = new MatchedContainedSpanPointRTree<int>(); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["Capacity8"] = entries => { var tree = new BaselineRTree<int>(8); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["Capacity32"] = entries => { var tree = new BaselineRTree<int>(32); tree.BulkLoad(entries); return tree.Search; };
        Screening.Variants["Capacity64"] = entries => { var tree = new BaselineRTree<int>(64); tree.BulkLoad(entries); return tree.Search; };
    }
}
