#nullable enable

using System;
using System.Security.Cryptography.X509Certificates;
using System.Threading;
using System.Threading.Tasks;
using Opc.Ua;
using Opc.Ua.Security.Certificates;

namespace IJT_CSharp_Client.Helpers;

/// <summary>
/// A factory-backed implementation of <see cref="ICertificateProvider"/> used by
/// <see cref="X509IdentityTokenHandler"/> to sign authentication nonces when establishing
/// a session over secure OPC UA channels in SDK 2.0.
/// </summary>
internal sealed class X509CertificateProvider : ICertificateProvider
{
    private readonly string _thumbprint;
    private readonly Func<X509Certificate2> _certificateFactory;

    public X509CertificateProvider(string thumbprint, Func<X509Certificate2> certificateFactory)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(thumbprint);
        ArgumentNullException.ThrowIfNull(certificateFactory);
        _thumbprint = thumbprint;
        _certificateFactory = certificateFactory;
    }

    public Certificate? TryGetPrivateKeyCertificate(string thumbprint)
    {
        if (string.Equals(_thumbprint, thumbprint, StringComparison.OrdinalIgnoreCase))
            return Certificate.From(_certificateFactory());

        return null;
    }

    public ValueTask<Certificate?> GetPrivateKeyCertificateAsync(
        CertificateIdentifier identifier,
        ICertificatePasswordProvider? passwordProvider = null,
        string? applicationUri = null,
        CancellationToken ct = default)
    {
        return ValueTask.FromResult<Certificate?>(Certificate.From(_certificateFactory()));
    }

    public void Dispose()
    {
        // Ephemeral certificate instances are owned and disposed by callers.
    }
}
