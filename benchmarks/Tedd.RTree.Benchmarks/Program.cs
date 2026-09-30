using BenchmarkDotNet.Running;
using BenchmarkDotNet.Configs;

if (args is ["--probe-sharptrees"])
{
    var (bounds, queries) = PackageComparisonData.Create(1_000, "Uniform");
    PackageValidation.Check(PackageIndexes.Prepare("SharpTrees", bounds, queries), bounds, queries, "SharpTrees/1000/Uniform");
    return;
}

if (args is ["--validate-packages"])
{
    PackageValidation.Run();
    return;
}

if (args is ["--validate-hypotheses"])
{
    HypothesisValidation.Run();
    return;
}

if (args is ["--probe-concurrency"])
{
    ConcurrencyProbe.Run();
    return;
}

// Enyim's published NuGet binary has optimizations disabled. Measure that binary as
// distributed rather than replacing it with a locally rebuilt competitor.
BenchmarkSwitcher.FromAssembly(typeof(Program).Assembly).Run(args,
    DefaultConfig.Instance.WithOptions(ConfigOptions.DisableOptimizationsValidator));
