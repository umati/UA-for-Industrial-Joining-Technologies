namespace IJT_CSharp_Client.Client;

using Microsoft.Extensions.Options;

/// <summary>
/// A lightweight <see cref="IOptionsMonitor{TOptions}"/> adapter for fixed subscription and monitored-item options
/// that avoids requiring a full Dependency Injection service provider.
/// </summary>
/// <typeparam name="T">The options type.</typeparam>
internal sealed class StaticOptionsMonitor<T>(T currentValue) : IOptionsMonitor<T> where T : class
{
    public T CurrentValue { get; } = currentValue ?? throw new ArgumentNullException(nameof(currentValue));

    public T Get(string? name) => CurrentValue;

    public IDisposable OnChange(Action<T, string?> listener) => NullDisposable.Instance;

    private sealed class NullDisposable : IDisposable
    {
        public static readonly NullDisposable Instance = new();
        public void Dispose() { }
    }
}
