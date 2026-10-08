#nullable enable

using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using IJT_CSharp_Client.Helpers;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.UnitTests;

public sealed class X509CertificateProviderTests
{
    private static X509Certificate2 NewCert()
    {
        using var rsa = RSA.Create(2048);
        var req = new CertificateRequest("CN=ProviderTest", rsa, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        return req.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-1), DateTimeOffset.UtcNow.AddDays(1));
    }

    [Fact]
    public async Task GetPrivateKeyCertificateAsync_MatchingThumbprint_ReturnsFreshCertificateEachCall()
    {
        using var seed = NewCert();
        var calls = 0;
        var sut = new X509CertificateProvider(seed.Thumbprint, () => { calls++; return NewCertCopy(seed); });
        var id = new CertificateIdentifier { Thumbprint = seed.Thumbprint };

        var first = await sut.GetPrivateKeyCertificateAsync(id);
        var second = await sut.GetPrivateKeyCertificateAsync(id);

        Assert.NotNull(first);
        Assert.NotNull(second);
        Assert.NotSame(first, second);
        Assert.Equal(2, calls);
        first!.Dispose();
        second!.Dispose();
    }

    [Fact]
    public async Task GetPrivateKeyCertificateAsync_MismatchedThumbprint_ReturnsNullAndDoesNotInvokeFactory()
    {
        using var seed = NewCert();
        var calls = 0;
        var sut = new X509CertificateProvider(seed.Thumbprint, () => { calls++; return NewCertCopy(seed); });

        var result = await sut.GetPrivateKeyCertificateAsync(new CertificateIdentifier { Thumbprint = "DEADBEEF" });

        Assert.Null(result);
        Assert.Equal(0, calls);
    }

    [Fact]
    public async Task GetPrivateKeyCertificateAsync_EmptyThumbprint_ReturnsNull()
    {
        using var seed = NewCert();
        var sut = new X509CertificateProvider(seed.Thumbprint, () => NewCertCopy(seed));
        Assert.Null(await sut.GetPrivateKeyCertificateAsync(new CertificateIdentifier()));
    }

    [Fact]
    public async Task GetPrivateKeyCertificateAsync_CancelledToken_Throws()
    {
        using var seed = NewCert();
        var calls = 0;
        var sut = new X509CertificateProvider(seed.Thumbprint, () => { calls++; return NewCertCopy(seed); });
        using var cts = new CancellationTokenSource();
        cts.Cancel();

        await Assert.ThrowsAsync<OperationCanceledException>(async () =>
            await sut.GetPrivateKeyCertificateAsync(new CertificateIdentifier { Thumbprint = seed.Thumbprint }, null, null, cts.Token));
        Assert.Equal(0, calls);
    }

    [Fact]
    public async Task GetPrivateKeyCertificateAsync_NullIdentifier_Throws()
    {
        using var seed = NewCert();
        var sut = new X509CertificateProvider(seed.Thumbprint, () => NewCertCopy(seed));
        await Assert.ThrowsAsync<ArgumentNullException>(async () => await sut.GetPrivateKeyCertificateAsync(null!));
    }

    [Fact]
    public void TryGetPrivateKeyCertificate_IsCaseInsensitiveAndRejectsOthers()
    {
        using var seed = NewCert();
        var sut = new X509CertificateProvider(seed.Thumbprint, () => NewCertCopy(seed));
        var hit = sut.TryGetPrivateKeyCertificate(seed.Thumbprint.ToLowerInvariant());
        Assert.NotNull(hit);
        hit!.Dispose();
        Assert.Null(sut.TryGetPrivateKeyCertificate("0000"));
    }

    [Fact]
    public async Task Constructor_RejectsBlankThumbprintAndNullFactory()
    {
        await Assert.ThrowsAsync<ArgumentException>(async () => new X509CertificateProvider(" ", () => NewCert()));
        await Assert.ThrowsAsync<ArgumentNullException>(async () => new X509CertificateProvider("AB", null!));
    }

    private static X509Certificate2 NewCertCopy(X509Certificate2 source)
        => X509CertificateLoader.LoadPkcs12(source.Export(X509ContentType.Pfx), null, X509KeyStorageFlags.EphemeralKeySet);

    [Fact]
    public async Task GetPrivateKeyCertificateAsync_FactoryProducesDifferentCertificate_ThrowsAndDisposesIt()
    {
        using var configured = NewCert();
        var other = NewCert();
        var sut = new X509CertificateProvider(configured.Thumbprint, () => other);

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(async () =>
            await sut.GetPrivateKeyCertificateAsync(new CertificateIdentifier { Thumbprint = configured.Thumbprint }));

        Assert.Contains("changed", ex.Message);
        await Assert.ThrowsAsync<CryptographicException>(async () => other.GetRSAPrivateKey()!.ExportParameters(true).ToString());
    }

    [Fact]
    public async Task TryGetPrivateKeyCertificate_FactoryProducesDifferentCertificate_Throws()
    {
        using var configured = NewCert();
        var sut = new X509CertificateProvider(configured.Thumbprint, () => NewCert());
        await Assert.ThrowsAsync<InvalidOperationException>(async () => sut.TryGetPrivateKeyCertificate(configured.Thumbprint));
    }

    [Fact]
    public async Task TryGetPrivateKeyCertificate_FactoryReturnsNull_Throws()
    {
        var sut = new X509CertificateProvider("AB", () => null!);
        await Assert.ThrowsAsync<InvalidOperationException>(async () => sut.TryGetPrivateKeyCertificate("AB"));
    }
}
