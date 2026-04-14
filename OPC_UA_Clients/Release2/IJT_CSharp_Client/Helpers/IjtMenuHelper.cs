#nullable enable

namespace IJT_CSharp_Client.Helpers;

public static class IjtMenuHelper
{
    public static void PrintUsage(
        string title,
        string description,
        IEnumerable<string> inputs,
        IEnumerable<string> outputs,
        string? tip = null)
    {
        var lines = new List<string>
        {
            $"USAGE: {title}",
            $"Description: {description}",
            "Inputs:",
        };
        lines.AddRange(inputs.Select(i => $"  - {i}"));
        lines.Add("Outputs:");
        lines.AddRange(outputs.Select(o => $"  - {o}"));
        if (!string.IsNullOrWhiteSpace(tip))
            lines.Add($"Tip: {tip}");

        int width = Math.Max(64, lines.Max(l => l.Length) + 4);
        var bar = new string('─', width - 2);
        Console.WriteLine();
        Console.WriteLine($"┌{bar}┐");
        foreach (var line in lines)
            Console.WriteLine($"│ {line.PadRight(width - 4)} │");
        Console.WriteLine($"└{bar}┘");
    }
}
