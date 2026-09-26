using BenchmarkDotNet.Running;

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

BenchmarkSwitcher.FromAssembly(typeof(Program).Assembly).Run(args);
