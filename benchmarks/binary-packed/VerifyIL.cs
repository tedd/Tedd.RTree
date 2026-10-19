using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;

static Dictionary<string, string> Methods(string path)
{
    using var stream = File.OpenRead(path);
    using var pe = new PEReader(stream);
    var md = pe.GetMetadataReader();
    string TypeName(TypeDefinitionHandle handle)
    {
        var type = md.GetTypeDefinition(handle);
        var parent = type.GetDeclaringType();
        return parent.IsNil ? md.GetString(type.Namespace) + "." + md.GetString(type.Name)
            : TypeName(parent) + "+" + md.GetString(type.Name);
    }
    var result = new Dictionary<string, string>();
    foreach (var typeHandle in md.TypeDefinitions)
    foreach (var methodHandle in md.GetTypeDefinition(typeHandle).GetMethods())
    {
        var method = md.GetMethodDefinition(methodHandle);
        if (method.RelativeVirtualAddress == 0) continue;
        var body = pe.GetMethodBody(method.RelativeVirtualAddress);
        string signature = Convert.ToHexString(md.GetBlobBytes(method.Signature));
        string locals = body.LocalSignature.IsNil ? "" : Convert.ToHexString(md.GetBlobBytes(md.GetStandaloneSignature(body.LocalSignature).Signature));
        string regions = string.Join(";", body.ExceptionRegions.Select(region =>
            $"{region.Kind},{region.TryOffset},{region.TryLength},{region.HandlerOffset},{region.HandlerLength},{region.FilterOffset},{System.Reflection.Metadata.Ecma335.MetadataTokens.GetToken(region.CatchType)}"));
        string identity = $"{(int)method.ImplAttributes}|{body.MaxStack}|{body.LocalVariablesInitialized}|{locals}|{regions}|{Convert.ToHexString(body.GetILBytes()!)}";
        result.Add(TypeName(typeHandle) + ":" + md.GetString(method.Name) + ":" + signature,
            Convert.ToHexString(SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(identity))));
    }
    return result;
}

var actual = Methods(args[0]);
var frozen = Methods(args[1]);
var differences = actual.Keys.Union(frozen.Keys).Where(key => !actual.TryGetValue(key, out var a) || !frozen.TryGetValue(key, out var b) || a != b).ToArray();
if (differences.Length > 0)
{
    foreach (string method in differences) Console.WriteLine(method);
    throw new Exception($"{differences.Length} method/signature/implementation differences from frozen source.");
}
Console.WriteLine($"All {actual.Count} method bodies, local signatures, exception regions and implementation flags match the frozen build.");
