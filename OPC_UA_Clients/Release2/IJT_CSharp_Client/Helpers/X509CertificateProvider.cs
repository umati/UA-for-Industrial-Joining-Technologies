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
        if (!string.Equals(_thumbprint, thumbprint, StringComparison.OrdinalIgnoreCase))
            return null;

        return Certificate.From(CreateValidatedCertificate());
    }

    /// <summary>
    /// Invokes the factory and verifies the produced certificate is the configured identity.
    /// The identity file or factory result may change after construction; a different certificate
    /// is never served (it is disposed and an <see cref="InvalidOperationException"/> is thrown).
    /// </summary>
    private X509Certificate2 CreateValidatedCertificate()
    {
        var certificate = _certificateFactory()
            ?? throw new InvalidOperationException("X509 identity certificate factory returned null.");
        if (!string.Equals(certificate.Thumbprint, _thumbprint, StringComparison.OrdinalIgnoreCase))
        {
            var actual = certificate.Thumbprint;
            certificate.Dispose();
            throw new InvalidOperationException(
                $"X509 identity certificate changed: expected thumbprint '{_thumbprint}' but the factory produced '{actual}'.");
        }

        return certificate;
    }

    public ValueTask<Certificate?> GetPrivateKeyCertificateAsync(
        CertificateIdentifier identifier,
        ICertificatePasswordProvider? passwordProvider = null,
        string? applicationUri = null,
        CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(identifier);
        ct.ThrowIfCancellationRequested();

        // Only serve the identity this provider was created for; never hand out a different certificate.
        return ValueTask.FromResult(TryGetPrivateKeyCertificate(identifier.Thumbprint ?? string.Empty));
    }

    public void Dispose()
    {
        // Ephemeral certificate instances are owned and disposed by callers.
    }
}
