/* ========================================================================
 * Copyright (c) 2005-2024 The OPC Foundation, Inc. All rights reserved.
 *
 * OPC Foundation MIT License 1.00
 *
 * Permission is hereby granted, free of charge, to any person
 * obtaining a copy of this software and associated documentation
 * files (the "Software"), to deal in the Software without
 * restriction, including without limitation the rights to use,
 * copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following
 * conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 * OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
 * WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 *
 * The complete license agreement can be found here:
 * http://opcfoundation.org/License/MIT/1.00/
 * ======================================================================*/

using System;
using System.Text;
using System.IO;
using Opc.Ua;
using UAModel.DI;

#pragma warning disable CS1591 // Missing XML comment for publicly visible type or member
#pragma warning disable CA1515 // Consider making public types internal
#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1028 // Enum Storage should be Int32

namespace UAModel.IA
{
    #region _ClassName_ Declarations
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class PredefinedNodes
    {
        #region PredefinedNodes Declarations
        // <summary/>
        public static NodeStateCollection Load(ISystemContext context)
        {
            byte[] initializationBuffer = Convert.FromBase64String(
               "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
               "aW9uLm9yZy9VQS9ESS//////HQAAACRgAFBAAAAAAQAQAAAATGV2ZWxEaXNwbGF5TW9kZQEBuwsDAAAA" +
               "AHkAAABDb250YWlucyB0aGUgdmFsdWVzIHVzZWQgdG8gaW5kaWNhdGUgaG93IGEgcGVyY2VudHVhbCB2" +
               "YWx1ZSBpcyBkaXNwbGF5ZWQgaWYgdGhlIHN0YWNrbGlnaHQgdW5pdCB3b3JrcyBpbiBMZXZlbG1ldGVy" +
               "IG1vZGUuAB0AewH9AAAAAwAAAAAAAAAAAAAAAgYAAABEaW1tZWQCIgAAAFVzZXMgZGltbWluZyB0byBk" +
               "aXNwbGF5IGZyYWN0aW9ucy4GAAAARGltbWVkAQAAAAAAAAACCAAAAEJsaW5raW5nAiMAAABVc2VzIGJs" +
               "aW5raW5nIHRvIGRpc3BsYXkgZnJhY3Rpb25zLggAAABCbGlua2luZwIAAAAAAAAAAgUAAABPdGhlcgJM" +
               "AAAARGlzcGxheSBmcmFjdGlvbnMgaW4gYSB3YXkgbm90IGRlZmluZWQgaW4gdGhpcyB2ZXJzaW9uIG9m" +
               "IHRoZSBzcGVjaWZpY2F0aW9uLgUAAABPdGhlcv////8BAAAAF2CpCgIAAAAAAAoAAABFbnVtVmFsdWVz" +
               "AQFxFwAuAERxFwAAlgMAAAABADsgAUAAAAAAAAAAAAAAAAIGAAAARGltbWVkAwIAAABlbiIAAABVc2Vz" +
               "IGRpbW1pbmcgdG8gZGlzcGxheSBmcmFjdGlvbnMuAQA7IAFDAAAAAQAAAAAAAAACCAAAAEJsaW5raW5n" +
               "AwIAAABlbiMAAABVc2VzIGJsaW5raW5nIHRvIGRpc3BsYXkgZnJhY3Rpb25zLgEAOyABaQAAAAIAAAAA" +
               "AAAAAgUAAABPdGhlcgMCAAAAZW5MAAAARGlzcGxheSBmcmFjdGlvbnMgaW4gYSB3YXkgbm90IGRlZmlu" +
               "ZWQgaW4gdGhpcyB2ZXJzaW9uIG9mIHRoZSBzcGVjaWZpY2F0aW9uLgEAqh0BAAAAAQAAAAMAAAABAf//" +
               "//8AAAAAJGAAUEAAAAABAAsAAABTaWduYWxDb2xvcgEBvAsDAAAAADYAAABIb2xkcyB0aGUgcG9zc2li" +
               "bGUgY29sb3VyIHZhbHVlcyBmb3Igc3RhY2tsaWdodCBsYW1wcy4AHQB7AUcCAAAIAAAAAAAAAAAAAAAC" +
               "AwAAAE9mZgIUAAAARWxlbWVudCBpcyBkaXNhYmxlZC4DAAAAT2ZmAQAAAAAAAAACAwAAAFJlZAInAAAA" +
               "VGhpcyB2YWx1ZSBpbmRpY2F0ZXMgYSByZWQgbGFtcCBjb2xvdXIuAwAAAFJlZAIAAAAAAAAAAgUAAABH" +
               "cmVlbgIpAAAAVGhpcyB2YWx1ZSBpbmRpY2F0ZXMgYSBncmVlbiBsYW1wIGNvbG91ci4FAAAAR3JlZW4D" +
               "AAAAAAAAAAIEAAAAQmx1ZQIoAAAAVGhpcyB2YWx1ZSBpbmRpY2F0ZXMgYSBibHVlIGxhbXAgY29sb3Vy" +
               "LgQAAABCbHVlBAAAAAAAAAACBgAAAFllbGxvdwIwAAAAVGhpcyB2YWx1ZSBpbmRpY2F0ZXMgYSB5ZWxs" +
               "b3cgbGFtcCBjb2xvdXIgKFIrRykuBgAAAFllbGxvdwUAAAAAAAAAAgYAAABQdXJwbGUCMAAAAFRoaXMg" +
               "dmFsdWUgaW5kaWNhdGVzIGEgcHVycGxlIGxhbXAgY29sb3VyIChSK0IpLgYAAABQdXJwbGUGAAAAAAAA" +
               "AAIEAAAAQ3lhbgIuAAAAVGhpcyB2YWx1ZSBpbmRpY2F0ZXMgYSBjeWFuIGxhbXAgY29sb3VyIChHK0Ip" +
               "LgQAAABDeWFuBwAAAAAAAAACBQAAAFdoaXRlAjEAAABUaGlzIHZhbHVlIGluZGljYXRlcyBhIHdoaXRl" +
               "IGxhbXAgY29sb3VyIChSK0crQikuBQAAAFdoaXRl/////wEAAAAXYKkKAgAAAAAACgAAAEVudW1WYWx1" +
               "ZXMBAXcXAC4ARHcXAACWCAAAAAEAOyABLwAAAAAAAAAAAAAAAgMAAABPZmYDAgAAAGVuFAAAAEVsZW1l" +
               "bnQgaXMgZGlzYWJsZWQuAQA7IAFCAAAAAQAAAAAAAAACAwAAAFJlZAMCAAAAZW4nAAAAVGhpcyB2YWx1" +
               "ZSBpbmRpY2F0ZXMgYSByZWQgbGFtcCBjb2xvdXIuAQA7IAFGAAAAAgAAAAAAAAACBQAAAEdyZWVuAwIA" +
               "AABlbikAAABUaGlzIHZhbHVlIGluZGljYXRlcyBhIGdyZWVuIGxhbXAgY29sb3VyLgEAOyABRAAAAAMA" +
               "AAAAAAAAAgQAAABCbHVlAwIAAABlbigAAABUaGlzIHZhbHVlIGluZGljYXRlcyBhIGJsdWUgbGFtcCBj" +
               "b2xvdXIuAQA7IAFOAAAABAAAAAAAAAACBgAAAFllbGxvdwMCAAAAZW4wAAAAVGhpcyB2YWx1ZSBpbmRp" +
               "Y2F0ZXMgYSB5ZWxsb3cgbGFtcCBjb2xvdXIgKFIrRykuAQA7IAFOAAAABQAAAAAAAAACBgAAAFB1cnBs" +
               "ZQMCAAAAZW4wAAAAVGhpcyB2YWx1ZSBpbmRpY2F0ZXMgYSBwdXJwbGUgbGFtcCBjb2xvdXIgKFIrQiku" +
               "AQA7IAFKAAAABgAAAAAAAAACBAAAAEN5YW4DAgAAAGVuLgAAAFRoaXMgdmFsdWUgaW5kaWNhdGVzIGEg" +
               "Y3lhbiBsYW1wIGNvbG91ciAoRytCKS4BADsgAU4AAAAHAAAAAAAAAAIFAAAAV2hpdGUDAgAAAGVuMQAA" +
               "AFRoaXMgdmFsdWUgaW5kaWNhdGVzIGEgd2hpdGUgbGFtcCBjb2xvdXIgKFIrRytCKS4BAKodAQAAAAEA" +
               "AAAIAAAAAQH/////AAAAACRgAFBAAAAAAQAPAAAAU2lnbmFsTW9kZUxpZ2h0AQG9CwMAAAAAUQAAAENv" +
               "bnRhaW5zIHRoZSB2YWx1ZXMgdXNlZCB0byBpbmRpY2F0ZSBpbiB3aGF0IHdheSBhIGxhbXAgYmVoYXZl" +
               "cyB3aGVuIHN3aXRjaGVkIG9uLgAdAHsBCQIAAAQAAAAAAAAAAAAAAAIKAAAAQ29udGludW91cwIoAAAA" +
               "VGhpcyB2YWx1ZSBpbmRpY2F0ZXMgYSBjb250aW51b3VzIGxpZ2h0LgoAAABDb250aW51b3VzAQAAAAAA" +
               "AAACCAAAAEJsaW5raW5nAmkAAABUaGlzIHZhbHVlIGluZGljYXRlcyBhIGJsaW5raW5nIGxpZ2h0IChi" +
               "bGlua2luZyBpbiByZWd1bGFyIGludGVydmFscyB3aXRoIGVxdWFsbHkgbG9uZyBvbiBhbmQgb2ZmIHRp" +
               "bWVzKS4IAAAAQmxpbmtpbmcCAAAAAAAAAAIIAAAARmxhc2hpbmcCjwAAAFRoaXMgdmFsdWUgaW5kaWNh" +
               "dGVzIGEgZmxhc2hpbmcgbGlnaHQgKGJsaW5raW5nIGluIGludGVydmFscyB3aXRoIGxvbmdlciBvZmYg" +
               "dGltZXMgdGhhbiBvbiB0aW1lcywgcGVyIGludGVydmFsIG11bHRpcGxlIG9uIHRpbWVzIGFyZSBwb3Nz" +
               "aWJsZSkuCAAAAEZsYXNoaW5nAwAAAAAAAAACBQAAAE90aGVyAk8AAABUaGUgbGlnaHQgaXMgaGFuZGxl" +
               "ZCBpbiBhIHdheSBub3QgZGVmaW5lZCBpbiB0aGlzIHZlcnNpb24gb2YgdGhlIHNwZWNpZmljYXRpb24u" +
               "BQAAAE90aGVy/////wEAAAAXYKkKAgAAAAAACgAAAEVudW1WYWx1ZXMBAXgXAC4ARHgXAACWBAAAAAEA" +
               "OyABSgAAAAAAAAAAAAAAAgoAAABDb250aW51b3VzAwIAAABlbigAAABUaGlzIHZhbHVlIGluZGljYXRl" +
               "cyBhIGNvbnRpbnVvdXMgbGlnaHQuAQA7IAGJAAAAAQAAAAAAAAACCAAAAEJsaW5raW5nAwIAAABlbmkA" +
               "AABUaGlzIHZhbHVlIGluZGljYXRlcyBhIGJsaW5raW5nIGxpZ2h0IChibGlua2luZyBpbiByZWd1bGFy" +
               "IGludGVydmFscyB3aXRoIGVxdWFsbHkgbG9uZyBvbiBhbmQgb2ZmIHRpbWVzKS4BADsgAa8AAAACAAAA" +
               "AAAAAAIIAAAARmxhc2hpbmcDAgAAAGVujwAAAFRoaXMgdmFsdWUgaW5kaWNhdGVzIGEgZmxhc2hpbmcg" +
               "bGlnaHQgKGJsaW5raW5nIGluIGludGVydmFscyB3aXRoIGxvbmdlciBvZmYgdGltZXMgdGhhbiBvbiB0" +
               "aW1lcywgcGVyIGludGVydmFsIG11bHRpcGxlIG9uIHRpbWVzIGFyZSBwb3NzaWJsZSkuAQA7IAFsAAAA" +
               "AwAAAAAAAAACBQAAAE90aGVyAwIAAABlbk8AAABUaGUgbGlnaHQgaXMgaGFuZGxlZCBpbiBhIHdheSBu" +
               "b3QgZGVmaW5lZCBpbiB0aGlzIHZlcnNpb24gb2YgdGhlIHNwZWNpZmljYXRpb24uAQCqHQEAAAABAAAA" +
               "BAAAAAEB/////wAAAAAkYABQQAAAAAEAFwAAAFN0YWNrbGlnaHRPcGVyYXRpb25Nb2RlAQG6CwMAAAAA" +
               "UAAAAENvbnRhaW5zIHRoZSB2YWx1ZXMgdXNlZCB0byBpbmRpY2F0ZSBob3cgYSBzdGFja2xpZ2h0IChh" +
               "cyBhIHdob2xlIHVuaXQpIGlzIHVzZWQuAB0AewFqAQAABAAAAAAAAAAAAAAAAgkAAABTZWdtZW50ZWQC" +
               "MAAAAFN0YWNrbGlnaHQgaXMgdXNlZCBhcyBzdGFjayBvZiBpbmRpdmlkdWFsIGxpZ2h0cwkAAABTZWdt" +
               "ZW50ZWQBAAAAAAAAAAIKAAAATGV2ZWxtZXRlcgIhAAAAU3RhY2tsaWdodCBpcyB1c2VkIGFzIGxldmVs" +
               "IG1ldGVyCgAAAExldmVsbWV0ZXICAAAAAAAAAAINAAAAUnVubmluZ19MaWdodAInAAAAVGhlIHdob2xl" +
               "IHN0YWNrIGFjdHMgYXMgYSBydW5uaW5nIGxpZ2h0DQAAAFJ1bm5pbmdfTGlnaHQDAAAAAAAAAAIFAAAA" +
               "T3RoZXICTAAAAFN0YWNrbGlnaHQgaXMgdXNlZCBpbiBhIHdheSBub3QgZGVmaW5lZCBpbiB0aGlzIHZl" +
               "cnNpb24gb2YgdGhlIHNwZWNpZmljYXRpb24FAAAAT3RoZXL/////AQAAABdgqQoCAAAAAAAKAAAARW51" +
               "bVZhbHVlcwEBdhcALgBEdhcAAJYEAAAAAQA7IAFRAAAAAAAAAAAAAAACCQAAAFNlZ21lbnRlZAMCAAAA" +
               "ZW4wAAAAU3RhY2tsaWdodCBpcyB1c2VkIGFzIHN0YWNrIG9mIGluZGl2aWR1YWwgbGlnaHRzAQA7IAFD" +
               "AAAAAQAAAAAAAAACCgAAAExldmVsbWV0ZXIDAgAAAGVuIQAAAFN0YWNrbGlnaHQgaXMgdXNlZCBhcyBs" +
               "ZXZlbCBtZXRlcgEAOyABTAAAAAIAAAAAAAAAAg0AAABSdW5uaW5nX0xpZ2h0AwIAAABlbicAAABUaGUg" +
               "d2hvbGUgc3RhY2sgYWN0cyBhcyBhIHJ1bm5pbmcgbGlnaHQBADsgAWkAAAADAAAAAAAAAAIFAAAAT3Ro" +
               "ZXIDAgAAAGVuTAAAAFN0YWNrbGlnaHQgaXMgdXNlZCBpbiBhIHdheSBub3QgZGVmaW5lZCBpbiB0aGlz" +
               "IHZlcnNpb24gb2YgdGhlIHNwZWNpZmljYXRpb24BAKodAQAAAAEAAAAEAAAAAQH/////AAAAAARgAFBA" +
               "AAAAAQAMAAAAUkdCV0RhdGFUeXBlAQG/CwAWAHoBUgEAAAAAABYBAAAABAAAAAMAAABSZWQCJwAAAERl" +
               "ZmluZXMgdGhlIGludGVuc2l0eSBvZiB0aGUgY29sb3VyIHJlZAAD/////wAAAAAAAAAAAAUAAABHcmVl" +
               "bgIpAAAARGVmaW5lcyB0aGUgaW50ZW5zaXR5IG9mIHRoZSBjb2xvdXIgZ3JlZW4AA/////8AAAAAAAAA" +
               "AAAEAAAAQmx1ZQIoAAAARGVmaW5lcyB0aGUgaW50ZW5zaXR5IG9mIHRoZSBjb2xvdXIgYmx1ZQAD////" +
               "/wAAAAAAAAAAAAUAAABXaGl0ZQJdAAAARGVmaW5lcyB0aGUgaW50ZW5zaXR5IG9mIGFuIGFkZGl0aW9u" +
               "YWwgd2hpdGUgY29tcG9uZW50LiBTaGFsbCBiZSBub3QgcHJvdmlkZWQgd2hlbiB1c2luZyBSR0IuAAP/" +
               "////AAAAAAAAAAABAgAAAAAmAAEBkRMAJgABAZYTAAAAACRkABAgAAAAAQAVAAAASGFzU3RhdGlzdGlj" +
               "Q29tcG9uZW50AQGiDwMAAAAApQAAAFJlZmVyZW5jZXMgb2YgdGhpcyB0eXBlIGxpbmsgVmFyaWFibGVz" +
               "IG1hbmFnaW5nIHN0YXRpc3RpY2FsIGRhdGEgZWl0aGVyIGRpcmVjdGx5IG9yIGluZGlyZWN0bHkgdG8g" +
               "YW4gT2JqZWN0IG9yIE9iamVjdFR5cGUgaW1wbGVtZW50aW5nIHRoZSBJU3RhdGlzdGljc1R5cGUgaW50" +
               "ZXJmYWNlLgAvAwAAAAAUAAAAU3RhdGlzdGljQ29tcG9uZW50T2b/////AAAAACRkABAgAAAAAQAhAAAA" +
               "SGFzUmVmZXJlbmNlTWVhc3VyZW1lbnRJbnN0cnVtZW50AQGjDwMAAAAAjgAAAFJlbGF0ZXMgdGhlIHNv" +
               "dXJjZSBub2RlIHRvIGEgcmVmZXJlbmNlIG1lYXN1cmVtZW50IGluc3RydW1lbnQsIGxpa2UgZm9yIGV4" +
               "YW1wbGUgYSBjYWxpYnJhdGlvbiB0YXJnZXQgdXNpbmcgYSByZWZlcmVuY2UgbWVhc3VyZW1lbnQgaW5z" +
               "dHJ1bWVudC4AIAMAAAAAIAAAAFJlZmVyZW5jZU1lYXN1cmVtZW50SW5zdHJ1bWVudE9m/////wAAAAA0" +
               "YAAQEAAAAAEAFAAAAENhbGlicmF0aW9uVmFsdWVUeXBlAQHSBwMAAAAAgwAAAFJlcHJlc2VudHMgdGhl" +
               "IHNwZWNpZmljIHF1YW50aXR5IGFuZCB2YWx1ZSAod2l0aCBlbmdpbmVlcmluZyB1bml0KSB0aGF0IGEg" +
               "Y2FsaWJyYXRpb24gdGFyZ2V0IHByb3ZpZGVzIGZvciBjYWxpYnJhdGlvbiBvZiBlcXVpcG1lbnQuAQA9" +
               "CQAa/////wEAAAAVYIkLAgAAAAAAEAAAAEVuZ2luZWVyaW5nVW5pdHMBAakXAC4ARABOqRcAAAEAdwP/" +
               "////AwP/////AAAAADRgCBAQAAAAAQARAAAAQ2FwYWNpdHlSYW5nZVR5cGUBAdMHAwAAAACTAAAAUmVw" +
               "cmVzZW50IGEgc2NhbGUgb2YgY2FsaWJyYXRpb24gdmFsdWVzLiBUaGUgdmFsdWUgZGVmaW5lcyB0aGUg" +
               "cmFuZ2UgKGxvd2VzdCBhbmQgaGlnaGVzdCB2YWx1ZSksIGFuZCB0aGUgcmVzb2x1dGlvbiBwcm9wZXJ0" +
               "eSB0aGUgc2l6ZSBvZiBlYWNoIHN0ZXAuAQA9CQEAdAP//////////wIAAAAVYIkLAgAAAAAAEAAAAEVu" +
               "Z2luZWVyaW5nVW5pdHMBAaoXAC4ARABOqhcAAAEAdwP/////AwP/////AAAAABVgiQsCAAAAAQAKAAAA" +
               "UmVzb2x1dGlvbgEBqxcALgBEAE6rFwAAAAv/////AwP/////AAAAACRgABAIAAAAAQASAAAAQWNvdXN0" +
               "aWNTaWduYWxUeXBlAQHxAwMAAAAAHgAAAFJlcHJlc2VudHMgYW4gYWNvdXN0aWMgc2lnbmFsLgA6AQAA" +
               "AAEAw0QAAQDZWwIAAAA1YIkLAgAAAAEACwAAAEF1ZGlvU2FtcGxlAQGNFwMAAAAARAAAAENvbnRhaW5z" +
               "IHRoZSBhdWRpbyBkYXRhLCBlLmcuIGZvciBkZXZpY2VzIGNhcGFibGUgb2YgYXVkaW8gcGxheWJhY2su" +
               "AC8APwBQjRcAAAEAsz//////AwP/////AAAAADVgiQsCAAAAAAAMAAAATnVtYmVySW5MaXN0AQGMFwMA" +
               "AAAAfgAAAEVudW1lcmF0ZSB0aGUgYWNvdXN0aWMgc2lnbmFscy4gSW5zdGFuY2VzIG9mIFN0YWNrRWxl" +
               "bWVudEFjb3VzdGljVHlwZSBpbmRleCBpbnRvIHRoaXMgbnVtYmVyIHVzaW5nIHRoZSBPcGVyYXRpb25N" +
               "b2RlIFByb3BlcnR5LgAuAEQATowXAAAAHP////8DA/////8AAAAAJGgAEAgAAAABACEAAABCYXNlQ2Fs" +
               "aWJyYXRpb25UYXJnZXRDYXRlZ29yeVR5cGUBAfYDAwAAAABhAAAAQWJzdHJhY3QgYmFzZSB0eXBlIGZv" +
               "ciBjYXRlZ29yaXppbmcgY2FsaWJyYXRpb24gdGFyZ2V0cy4gU3VidHlwZXMgZGVmaW5lIHRoZSBjb25j" +
               "cmV0ZSBjYXRlZ29yaWVzLgA6Af////8AAAAAJGAAEAgAAAABACQAAABEeW5hbWljQ2FsaWJyYXRpb25U" +
               "YXJnZXRDYXRlZ29yeVR5cGUBAfoDAwAAAAChAQAAQ2hhcmFjdGVyaXplcyBhIGNhbGlicmF0aW9uIHRh" +
               "cmdldCB0byBiZSB1c2VkIHRvZ2V0aGVyIHdpdGggYSBtZWFzdXJlbWVudCBpbnN0cnVtZW50LCB0aGF0" +
               "IGRldGVybWluZXMgdGhlIHZhbHVlcyB0byBiZSBjYWxpYnJhdGVkLiBJdCBjYW4gYmUgYSBwaWVjZSBj" +
               "cmVhdGVkIGR1cmluZyB0aGUgbm9ybWFsIHByb2R1Y3Rpb24gcHJvY2VzcyBvciBhbiBpdGVtIHNwZWNp" +
               "ZmljYWxseSBjcmVhdGVkIGZvciBjYWxpYnJhdGlvbiBwdXJwb3Nlcy4gVGhlIGNhbGlicmF0aW9uIHRh" +
               "cmdldCByZXByZXNlbnRzIGFuIGluZGl2aWR1YWwgcGllY2Ugb3IgaXRlbSwgdGhhdCBpcywgaWYgYSBu" +
               "ZXcgcGllY2Ugc2hvdWxkIGJlIHVzZWQgb3IgaXRlbSBpcyBjcmVhdGVkLCBhIG5ldyBPYmplY3Qgb2Yg" +
               "dGhpcyBPYmplY3RUeXBlIGlzIGNyZWF0ZWQuAQH2A/////8AAAAAJGAAEAgAAAABACQAAABPbmVUaW1l" +
               "Q2FsaWJyYXRpb25UYXJnZXRDYXRlZ29yeVR5cGUBAfkDAwAAAAALAQAAQ2F0ZWdvcml6ZXMgYSBjYWxp" +
               "YnJhdGlvbiB0YXJnZXQgdG8gYmUgdXNlZCBvbmx5IG9uY2UsIGZvciBleGFtcGxlIGJlY2F1c2UgdGhl" +
               "IGNhbGlicmF0aW9uIGRlc3Ryb3lzIHRoZSB0YXJnZXQuIFR5cGljYWxseSwgT2JqZWN0cyBvZiB0aGlz" +
               "IE9iamVjdFR5cGUgZG8gbm90IHJlcHJlc2VudCBvbmUgaW5kaXZpZHVhbCBjYWxpYnJhdGlvbiB0YXJn" +
               "ZXQsIGJ1dCBhIGJhdGNoIG9mIGNhbGlicmF0aW9uIHRhcmdldHMgd2l0aCB0aGUgc2FtZSBjaGFyYWN0" +
               "ZXJpc3RpY3MuAQH2A/////8AAAAAJGAAEAgAAAABACUAAABSZXVzYWJsZUNhbGlicmF0aW9uVGFyZ2V0" +
               "Q2F0ZWdvcnlUeXBlAQH3AwMAAAAA1gAAAENhdGVnb3JpemVzIGEgY2FsaWJyYXRpb24gdGFyZ2V0IHRv" +
               "IGJlIHJldXNlZCBzZXZlcmFsIHRpbWVzLiBGb3IgZXhhbXBsZSwgYSBjYWxpYnJhdGlvbiB0YXJnZXQg" +
               "bGlrZSBhIG1ldGVyLCB0aGF0IGlzIGJvdWdodCBzcGVjaWZpY2FsbHkgZm9yIGNhbGlicmF0aW9uIGFu" +
               "ZCBub3QgZGVzdHJveWVkIGJ5IGFuIGluZGl2aWR1YWwgdXNhZ2UgaXMgb2YgdGhpcyBjYXRlZ29yeS4B" +
               "AfYD/////wAAAAAkYAAQCAAAAAEAKwAAAFJldXNhYmxlRGV2aWNlQ2FsaWJyYXRpb25UYXJnZXRDYXRl" +
               "Z29yeVR5cGUBAfgDAwAAAACMAAAAQ2F0ZWdvcml6ZXMgYSBjYWxpYnJhdGlvbiB0YXJnZXQgdG8gYmUg" +
               "YSByZXVzYWJsZSBkZXZpY2UgdGhhdCBwcm9kdWNlcyBhIGNlcnRhaW4gZW52aXJvbm1lbnQgbGlrZSBw" +
               "cmVzc3VyZSB0aGF0IGNhbiBiZSB1c2VkIGZvciBjYWxpYnJhdGlvbi4BAfcD/////wAAAAAkaAAQCAAA" +
               "AAEADwAAAElTdGF0aXN0aWNzVHlwZQEB8wMDAAAAAC0AAABCYXNlIGludGVyZmFjZSBmb3IgbWFuYWdp" +
               "bmcgc3RhdGlzdGljYWwgZGF0YS4BAMJEAf////8CAAAAJGGCCwQAAAABAA8AAABSZXNldFN0YXRpc3Rp" +
               "Y3MBAVkbAwAAAABWAAAAUmVzdGFydHMgYWxsIHN0YXRpc3RpY2FsIGRhdGEsIGluY2x1ZGluZyBhIHJl" +
               "c2V0IG9mIHRoZSBTdGFydFRpbWUgdG8gdGhlIGN1cnJlbnQgdGltZS4ALwEBWRsAUFkbAAABAf////8A" +
               "AAAANWCJCwIAAAABAAkAAABTdGFydFRpbWUBAZ4XAwAAAABdAAAASW5kaWNhdGVzIHRoZSBwb2ludCBp" +
               "biB0aW1lIGF0IHdoaWNoIHRoZSBjb2xsZWN0aW9uIG9mIHRoZSBzdGF0aXN0aWNhbCBkYXRhIGhhcyBi" +
               "ZWVuIHN0YXJ0ZWQuAC4ARABQnhcAAAAN/////wMD/////wAAAAAkaAAQCAAAAAEAGAAAAElBZ2dyZWdh" +
               "dGVTdGF0aXN0aWNzVHlwZQEB9AMDAAAAAK0AAABCYXNlIGludGVyZmFjZSBmb3IgbWFuYWdpbmcgc3Rh" +
               "dGlzdGljYWwgZGF0YSB0aGF0IGlzIG5vdCByb2xsZWQgb3Zlci4gQWxsIGRhdGEgZnJvbSB0aGUgc3Rh" +
               "cnQgb2YgdHJhY2tpbmcgdGhlIHN0YXRpc3RpY2FsIGRhdGEgYXJlIGNvbnNpZGVyZWQsIHVudGlsIHRo" +
               "ZSB0cmFja2luZyBnZXRzIHJlc2V0LgEB8wMB/////wEAAAA1YIkLAgAAAAEADgAAAFJlc2V0Q29uZGl0" +
               "aW9uAQGfFwMAAAAA0gEAAFRoZSByZWFzb24gYW5kIGNvbnRleHQgZm9yIHRoZSByZXNldCBvZiB0aGUg" +
               "c3RhdGlzdGljcywgd2hpY2ggaXMgZG9uZSB3aXRob3V0IGEgdHJpZ2dlciBmcm9tIGFuIE9QQyBVQSBD" +
               "bGllbnQsIGxpa2UgY2FsbGluZyB0aGUgUmVzZXRTdGF0aXN0aWNzIE1ldGhvZC4gUmVzZXRDb25kaXRp" +
               "b24gaXMgYSB2ZW5kb3Itc3BlY2lmaWMsIGh1bWFuIHJlYWRhYmxlIHN0cmluZy4gUmVzZXRDb25kaXRp" +
               "b24gaXMgbm9uLWxvY2FsaXplZCBhbmQgbWlnaHQgY29udGFpbiBhbiBleHByZXNzaW9uIHRoYXQgY2Fu" +
               "IGJlIHBhcnNlZCBieSBjZXJ0YWluIGNsaWVudHMuIEV4YW1wbGVzIGFyZTog4oCcQUZURVIgNCBIT1VS" +
               "U+KAnSwg4oCcQUZURVIgMTAwMCBJVEVNU+KAnSwg4oCcT1BFUkFUT1LigJ0uIOKAnE9QRVJBVE9S4oCd" +
               "IG1lYW5zLCB0aGF0IGFuIG9wZXJhdG9yIHJlc2V0cyB0aGUgc3RhdGlzdGljcyBvbiBhIGxvY2FsIEhN" +
               "SS4ALgBEAFCfFwAAAAz/////AwP/////AAAAACRoABAIAAAAAQAWAAAASVJvbGxpbmdTdGF0aXN0aWNz" +
               "VHlwZQEB9QMDAAAAAIgAAABCYXNlIGludGVyZmFjZSBmb3IgbWFuYWdpbmcgc3RhdGlzdGljYWwgZGF0" +
               "YSB0aGF0IGlzIHJvbGxlZCBvdmVyLCBpLmUuIG9ubHkgYSBjZXJ0YWluIGFtb3VudCBvZiBkYXRhIGlz" +
               "IGNvbnNpZGVyZWQgZm9yIHN0YXRpc3RpY2FsIGRhdGEuAQHzAwH/////AgAAADVgiQsCAAAAAQAOAAAA" +
               "V2luZG93RHVyYXRpb24BAaAXAwAAAADnAAAAVGhlIGR1cmF0aW9uIGFmdGVyIHRoZSBzdGF0aXN0aWNh" +
               "bCBkYXRhIGFyZSByb2xsZWQgb3Zlci4gT25seSB0aGUgZGF0YSB0aGF0IHdlcmUgZ2F0aGVyZWQgZHVy" +
               "aW5nIHRoYXQgZHVyYXRpb24gYXJlIGNvbnNpZGVyZWQgZm9yIHRoZSBzdGF0aXN0aWNhbCBkYXRhLCBl" +
               "dmVuIGlmIHRoZSB0aW1lIGludGVydmFsIGJldHdlZW4gdGhlIFN0YXJ0VGltZSBhbmQgdGhlIGN1cnJl" +
               "bnQgdGltZSBpcyBsb25nZXIuAC4ARABQoBcAAAEAIgH/////AwP/////AAAAADVgiQsCAAAAAQAUAAAA" +
               "V2luZG93TnVtYmVyT2ZWYWx1ZXMBAaEXAwAAAADAAAAAVGhlIG51bWJlciBvZiB2YWx1ZXMgYmVmb3Jl" +
               "IHRoZSBkYXRhIGdldHMgcm9sbGVkIG92ZXIuIEZvciB0aGUgc3RhdGlzdGljYWwgZGF0YSwgb25seSB0" +
               "aGUgZGF0YSBmaXR0aW5nIGludG8gdGhlIG51bWJlciBvZiB2YWx1ZXMgaXMgY29uc2lkZXJlZCwgZXZl" +
               "biBpZiBtb3JlIGRhdGEgd2VyZSBnYXRoZXJlZCBzaW5jZSBTdGFydFRpbWUuAC4ARABQoRcAAAAH////" +
               "/wMD/////wAAAAAkYAAQCAAAAAEAFQAAAENhbGlicmF0aW9uVGFyZ2V0VHlwZQEB+wMDAAAAADAAAABQ" +
               "cm92aWRlcyBpbmZvcm1hdGlvbiBhYm91dCBhIGNhbGlicmF0aW9uIHRhcmdldC4AOv////8IAAAAJGCA" +
               "CwEAAAABABkAAABDYWxpYnJhdGlvblRhcmdldENhdGVnb3J5AQGTEwMAAAAAMwAAAERlZmluZXMgd2hh" +
               "dCBjYXRlZ29yeSB0aGUgY2FsaWJyYXRpb24gdGFyZ2V0IGlzIG9mLgAvAQH2AwBOkxMAAP////8AAAAA" +
               "JGCACwEAAAABABkAAABDYWxpYnJhdGlvblRhcmdldEZlYXR1cmVzAQGVEwMAAAAAiAAAAEEgZm9sZGVy" +
               "IGNvbnRhaW5pbmcgaW5mb3JtYXRpb24gYWJvdXQgdGhlIGZlYXR1cmVzIG9mIGEgY2FsaWJyYXRpb24g" +
               "dGFyZ2V0LCB0aGF0IGlzLCB3aGF0IGNhbiBiZSBjYWxpYnJhdGVkIHdpdGggdGhlIGNhbGlicmF0aW9u" +
               "IHRhcmdldC4ALwA9AE6VEwAA/////wIAAAA1YMkLAgAAABwAAABDYWxpYnJhdGlvblZhbHVlX1BsYWNl" +
               "aG9sZGVyAQASAAAAPENhbGlicmF0aW9uVmFsdWU+AQGwFwMAAAAAhwAAAEEgY2FsaWJyYXRpb24gdmFs" +
               "dWUgaW5kaWNhdGVzIHRoZSB2YWx1ZSB0aGUgY2FsaWJyYXRpb24gdGFyZ2V0IHByb3ZpZGVzIGZvciBj" +
               "YWxpYnJhdGlvbiBhbmQgaW5jbHVkZXMgaXRzIHF1YW50aXR5IGFuZCBlbmdpbmVlcmluZyB1bml0LgAv" +
               "AQHSBwEA9CywFwAAABr/////AwP/////AQAAABVgiQsCAAAAAAAQAAAARW5naW5lZXJpbmdVbml0cwEB" +
               "sRcALgBEAE6xFwAAAQB3A/////8DA/////8AAAAANWDJCwIAAAAZAAAAQ2FwYWNpdHlSYW5nZV9QbGFj" +
               "ZWhvbGRlcgEADwAAADxDYXBhY2l0eVJhbmdlPgEBshcDAAAAANQAAABBIGNhcGFjaXR5IHJhbmdlIGlu" +
               "ZGljYXRlcyBhIHJhbmdlIChsb3cgYW5kIGhpZ2ggdmFsdWUpIGFzIHdlbGwgYXMgYSByZXNvbHV0aW9u" +
               "LCBhbmQgdGh1cyBkZWZpbmVzIGEgbnVtYmVyIG9mIHZhbHVlcyB0aGUgY2FsaWJyYXRpb24gdGFyZ2V0" +
               "IHByb3ZpZGVzIGZvciBjYWxpYnJhdGlvbiBhbmQgaW5jbHVkZXMgdGhlIHF1YW50aXR5IGFuZCBlbmdp" +
               "bmVlcmluZyB1bml0LgAvAQHTBwEA9CyyFwAAAQB0A/////8DA/////8CAAAAFWCJCwIAAAAAABAAAABF" +
               "bmdpbmVlcmluZ1VuaXRzAQGzFwAuAEQATrMXAAABAHcD/////wMD/////wAAAAAVYIkLAgAAAAEACgAA" +
               "AFJlc29sdXRpb24BAbQXAC4ARABOtBcAAAAL/////wMD/////wAAAAA1YIkLAgAAAAEADgAAAENlcnRp" +
               "ZmljYXRlVXJpAQGvFwMAAAAAsgAAAENvbnRhaW5zIHRoZSBVcmkgb2YgYSBjZXJ0aWZpY2F0ZSBvZiB0" +
               "aGUgY2FsaWJyYXRpb24gdGFyZ2V0LCBpbiBjYXNlIHRoZSBjYWxpYnJhdGlvbiB0YXJnZXQgaXMgY2Vy" +
               "dGlmaWVkIGFuZCB0aGUgaW5mb3JtYXRpb24gYXZhaWxhYmxlLiBPdGhlcndpc2UsIHRoZSBQcm9wZXJ0" +
               "eSBzaG91bGQgYmUgb21pdHRlZC4ALgBEAFCvFwAAAAz/////AwP/////AAAAACRggAsBAAAAAgAOAAAA" +
               "SWRlbnRpZmljYXRpb24BAZITAwAAAAAkAAAAUHJvdmlkZXMgaWRlbnRpZmljYXRpb24gaW5mb3JtYXRp" +
               "b24uAC8BAu0DAE6SEwAAAgAAAAEAw0QAAQLIOgEAw0QAAQK7Og4AAAAVYIkLAgAAAAIABwAAAEFzc2V0" +
               "SWQBAcAXAC4ARABQwBcAAAAM/////wMD/////wAAAAAVYIkLAgAAAAIADQAAAENvbXBvbmVudE5hbWUB" +
               "AcEXAC4ARABQwRcAAAAV/////wMD/////wAAAAAVYIkLAgAAAAIACwAAAERldmljZUNsYXNzAQG8FwAu" +
               "AEQAULwXAAAADP////8DA/////8AAAAAFWCJCwIAAAACAAwAAABEZXZpY2VNYW51YWwBAcIXAC4ARABQ" +
               "whcAAAAM/////wMD/////wAAAAAVYIkLAgAAAAIADgAAAERldmljZVJldmlzaW9uAQG7FwAuAEQAULsX" +
               "AAAADP////8DA/////8AAAAAFWCJCwIAAAACABAAAABIYXJkd2FyZVJldmlzaW9uAQG5FwAuAEQAULkX" +
               "AAAADP////8DA/////8AAAAAFWCJCwIAAAACAAwAAABNYW51ZmFjdHVyZXIBAbUXAC4ARABQtRcAAAAV" +
               "/////wMD/////wAAAAAVYIkLAgAAAAIADwAAAE1hbnVmYWN0dXJlclVyaQEBthcALgBEAFC2FwAAAAz/" +
               "////AwP/////AAAAABVgiQsCAAAAAgAFAAAATW9kZWwBAbcXAC4ARABQtxcAAAAV/////wMD/////wAA" +
               "AAAVYIkLAgAAAAIACwAAAFByb2R1Y3RDb2RlAQG4FwAuAEQAULgXAAAADP////8DA/////8AAAAAFWCJ" +
               "CwIAAAACABIAAABQcm9kdWN0SW5zdGFuY2VVcmkBAb4XAC4ARABQvhcAAAAM/////wMD/////wAAAAAV" +
               "YIkLAgAAAAIADwAAAFJldmlzaW9uQ291bnRlcgEBvxcALgBEAFC/FwAAAAb/////AwP/////AAAAABVg" +
               "iQsCAAAAAgAMAAAAU2VyaWFsTnVtYmVyAQG9FwAuAEQAUL0XAAAADP////8DA/////8AAAAAFWCJCwIA" +
               "AAACABAAAABTb2Z0d2FyZVJldmlzaW9uAQG6FwAuAEQAULoXAAAADP////8DA/////8AAAAANWCJCwIA" +
               "AAABABIAAABMYXN0VmFsaWRhdGlvbkRhdGUBAawXAwAAAADAAAAAUHJvdmlkZXMgdGhlIGRhdGUsIHRo" +
               "ZSBjYWxpYnJhdGlvbiB0YXJnZXQgd2FzIHZhbGlkYXRlZCB0aGUgbGFzdCB0aW1lLiBJZiB0aGVyZSBp" +
               "cyBubyBzcGVjaWZpYyB2YWxpZGF0aW9uIGRhdGUga25vd24sIHRoZSBkYXRlIHdoZW4gdGhlIGNhbGli" +
               "cmF0aW9uIHRhcmdldCB3YXMgYm91Z2h0IG9yIGNyZWF0ZWQgc2hvdWxkIGJlIHVzZWQuAC4ARABQrBcA" +
               "AAEAJgH/////AwP/////AAAAADVgiQsCAAAAAQASAAAATmV4dFZhbGlkYXRpb25EYXRlAQGtFwMAAAAA" +
               "8gAAAFByb3ZpZGVzIHRoZSBkYXRlLCB3aGVuIHRoZSBjYWxpYnJhdGlvbiB0YXJnZXQgc2hvdWxkIGJl" +
               "IHZhbGlkYXRlZCB0aGUgbmV4dCB0aW1lLiBJZiB0aGlzIGRhdGUgaXMgbm90IGtub3duLCB0aGUgUHJv" +
               "cGVydHkgc2hvdWxkIGJlIG9taXR0ZWQuIE5vdGU6IFBvdGVudGlhbGx5IHRoZSBOZXh0VmFsaWRhdGlv" +
               "bkRhdGUgaXMgaW4gdGhlIHBhc3QsIHdoZW4gdGhlIG5leHQgdmFsaWRhdGlvbiBkaWQgbm90IHRha2Ug" +
               "cGxhY2UuAC4ARABQrRcAAAEAJgH/////AwP/////AAAAACRggAsBAAAAAQAVAAAAT3BlcmF0aW9uYWxD" +
               "b25kaXRpb25zAQGUEwMAAAAAzwEAAEEgZm9sZGVyIGNvbnRhaW5pbmcgaW5mb3JtYXRpb24gYWJvdXQg" +
               "b3BlcmF0aW9uYWwgY29uZGl0aW9ucyBvZiB0aGUgY2FsaWJyYXRpb24gdGFyZ2V0LiBGb3IgZXhhbXBs" +
               "ZSwgaXQgbWlnaHQgcHJvdmlkZSBpbiB3aGF0IHJhbmdlcyBvZiBodW1pZGl0eSB0aGUgY2FsaWJyYXRp" +
               "b24gdGFyZ2V0IGNhbiBiZSBvcGVyYXRlZC4gSXQgbWlnaHQgYWxzbyBwcm92aWRlIGNvcnJlY3Rpb24g" +
               "aW5mb3JtYXRpb24sIGZvciBleGFtcGxlLCBkZXBlbmRpbmcgb24gdGhlIHRlbXBlcmF0dXJlIHRoZSBj" +
               "YWxpYnJhdGlvbiB2YWx1ZXMgbmVlZCB0byBiZSBjb3JyZWN0ZWQgKGluIGNhc2Ugb2YgYSBsZW5ndGgs" +
               "IHRoZSBsZW5ndGggbWlnaHQgaW5jcmVhc2Ugd2l0aCBoaWdoIHRlbXBlcmF0dXJlcykuIElmIG5vIG9w" +
               "ZXJhdGlvbmFsIGNvbmRpdGlvbnMgYXJlIHByb3ZpZGVkLCB0aGlzIGZvbGRlciBzaG91bGQgYmUgb21p" +
               "dHRlZC4ALwA9AFCUEwAA/////wAAAAA1YIkLAgAAAAEABwAAAFF1YWxpdHkBAa4XAwAAAADOAAAAUHJv" +
               "dmlkZXMgdGhlIHF1YWxpdHkgb2YgdGhlIGNhbGlicmF0aW9uIHRhcmdldCBpbiBwZXJjZW50YWdlLCB0" +
               "aGlzIGlzLCB0aGUgdmFsdWUgc2hhbGwgYmUgYmV0d2VlbiAwIGFuZCAxMDAuIDEwMCBtZWFucyB0aGUg" +
               "aGlnaGVzdCBxdWFsaXR5LCAwIHRoZSBsb3dlc3QuIFRoZSBzZW1hbnRpYyBvZiB0aGUgcXVhbGl0eSBp" +
               "cyBhcHBsaWNhdGlvbi1zcGVjaWZpYy4ALgBEAFCuFwAAAAP/////AwP/////AAAAACRgABAIAAAAAQAS" +
               "AAAAQ29udHJvbENoYW5uZWxUeXBlAQHwAwMAAAAAoQAAAFVzZWQgZm9yIGNvbnRyb2wgY2hhbm5lbHMg" +
               "b2Ygc2luZ2xlIGNvbG91ciBlbGVtZW50cyB3aXRoaW4gYSBzdGFjayBlbGVtZW50IChlLmcuIFJHQiBl" +
               "bGVtZW50cyB3b3VsZCB1c2UgdGhyZWUgQ29udHJvbENoYW5uZWxzLCBvbmUgZm9yIGVhY2ggY29udHJv" +
               "bGxhYmxlIGNvbG91cikuADr/////BAAAADVgiQsCAAAAAQAMAAAAQ2hhbm5lbENvbG9yAQGIFwMAAAAA" +
               "YwAAAEluZGljYXRlcyBpbiB3aGF0IG1vZGUgKGNvbnRpbnVvdXNseSBvbiwgYmxpbmtpbmcsIGZsYXNo" +
               "aW5nKSB0aGUgY2hhbm5lbCBvcGVyYXRlcyB3aGVuIHN3aXRjaGVkIG9uLgAvAD8ATogXAAABAbwL////" +
               "/wMD/////wAAAAA1YIkLAgAAAAEACQAAAEludGVuc2l0eQEBihcDAAAAAC0BAABTaG93cyB0aGUgY2hh" +
               "bm5lbOKAmXMgaW50ZW5zaXR5LCB0aHVzIGl0cyBicmlnaHRuZXNzLiBUaGUgbWFuZGF0b3J5IEVVUmFu" +
               "Z2UgUHJvcGVydHkgb2YgdGhlIFZhcmlhYmxlIGluZGljYXRlcyB0aGUgbG93ZXN0IGFuZCBoaWdoZXN0" +
               "IHZhbHVlIGFuZCB0aGVyZWJ5IGFsbG93cyB0byBjYWxjdWxhdGUgdGhlIHBlcmNlbnRhZ2UgcmVwcmVz" +
               "ZW50ZWQgYnkgdGhlIHZhbHVlLiBUaGUgbG93ZXN0IHZhbHVlIGlzIGludGVycHJldGVkIGFzIDAgcGVy" +
               "Y2VudCwgdGhlIGhpZ2hlc3QgaXMgaW50ZXJwcmV0ZWQgYXMgMTAwIHBlcmNlbnQuAC8BAEAJAFCKFwAA" +
               "AAr/////AwP/////AQAAABVgiQsCAAAAAAAHAAAARVVSYW5nZQEBixcALgBEAE6LFwAAAQB0A/////8B" +
               "Af////8AAAAANWCJCwIAAAABAAoAAABTaWduYWxNb2RlAQGJFwMAAAAASgAAAENvbnRhaW5zIGEgbGlz" +
               "dCBvZiBhdWRpbyBzaWduYWxzIHVzZWQgYnkgdGhpcyBhY291c3RpYyBzdGFja2xpZ2h0IGVsZW1lbnQu" +
               "AC8APwBOiRcAAAEBvQv/////AwP/////AAAAADVgiQsCAAAAAQAIAAAAU2lnbmFsT24BAYcXAwAAAAAn" +
               "AAAASW5kaWNhdGVzIGlmIHRoZSBjb2xvdXIgaXMgc3dpdGNoZWQgb24uAC4ARABOhxcAAAAB/////wMD" +
               "/////wAAAAAkYAAQCAAAAAEAEwAAAEJhc2ljU3RhY2tsaWdodFR5cGUBAeoDAwAAAAB9AAAARW50cnkg" +
               "cG9pbnQgdG8gYSBzdGFja2xpZ2h0IGNvbnRhaW5pbmcgZWxlbWVudHMgb2YgdGhlIHN0YWNrbGlnaHQg" +
               "YXMgd2VsbCBhcyBhZGRpdGlvbmFsIGluZm9ybWF0aW9uIHZhbGlkIGZvciB0aGUgd2hvbGUgdW5pdC4B" +
               "AN5b/////wQAAAAkYMALAQAAABkAAABPcmRlcmVkT2JqZWN0X1BsYWNlaG9sZGVyAAAPAAAAPE9yZGVy" +
               "ZWRPYmplY3Q+AQGOEwMAAAAAuQAAAFJlcHJlc2VudCB0aGUgc3RhY2sgZWxlbWVudHMgKGxhbXBzIGFu" +
               "ZCBhY291c3RpYyBlbGVtZW50cykgdGhlIHN0YWNrbGlnaHQgaXMgY29tcG9zZWQgb2YuIFRoZSBIYXNP" +
               "cmRlcmVkQ29tcG9uZW50IFJlZmVyZW5jZSBzaGFsbCByZXByZXNlbnQgdGhlIG9yZGVyaW5nIGZyb20g" +
               "dGhlIGJhc2Ugb2YgdGhlIHN0YWNrbGlnaHQuADEBAe0DAQD0LI4TAAABAAAAAQDDRAABANlbAQAAADVg" +
               "iQsCAAAAAAAMAAAATnVtYmVySW5MaXN0AQGVFwMAAAAAXQAAAEVudW1lcmF0ZSB0aGUgc3RhY2tsaWdo" +
               "dCBlbGVtZW50cyBjb3VudGluZyB1cHdhcmRzIGJlZ2lubmluZyBmcm9tIHRoZSBiYXNlIG9mIHRoZSBz" +
               "dGFja2xpZ2h0LgAuAEQATpUXAAAAHP////8BAf////8AAAAAJGCACwEAAAABAAoAAABTdGFja0xldmVs" +
               "AQGJEwMAAAAA6QAAAFZhbGlkIGlmIHRoZSBzdGFja2xpZ2h0IGlzIHVzZWQgaW4g4oCcTGV2ZWxtZXRl" +
               "cuKAnSBTdGFja2xpZ2h0TW9kZS4gSWYgc28sIHRoZSB3aG9sZSBzdGFjayBpcyBjb250cm9sbGVkIGJ5" +
               "IGEgc2luZ2xlIHBlcmNlbnR1YWwgdmFsdWUuIEluIHRoaXMgY2FzZSwgdGhlIFNpZ25hbE9uIHBhcmFt" +
               "ZXRlciBvZiBhbnkgc3RhY2sgZWxlbWVudCBvZiBTdGFja0VsZW1lbnRMaWdodFR5cGUgaGFzIG5vIG1l" +
               "YW5pbmcuAC8BAesDAFCJEwAA/////wIAAAA1YIkLAgAAAAEACwAAAERpc3BsYXlNb2RlAQGSFwMAAAAA" +
               "TAAAAEluZGljYXRlcyBpbiB3aGF0IHdheSB0aGUgcGVyY2VudHVhbCB2YWx1ZSBpcyBkaXNwbGF5ZWQg" +
               "d2l0aCB0aGUgc3RhY2tsaWdodC4ALwA/AE6SFwAAAQG7C/////8DA/////8AAAAANWCJCwIAAAABAAwA" +
               "AABMZXZlbFBlcmNlbnQBAZMXAwAAAAAyAQAAU2hvd3MgdGhlIHBlcmNlbnR1YWwgdmFsdWUgdGhlIHN0" +
               "YWNrbGlnaHQgaXMgcmVwcmVzZW50aW5nLiBUaGUgbWFuZGF0b3J5IEVVUmFuZ2UgUHJvcGVydHkgb2Yg" +
               "dGhlIFZhcmlhYmxlIGluZGljYXRlcyB0aGUgbG93ZXN0IGFuZCBoaWdoZXN0IHZhbHVlIGFuZCB0aGVy" +
               "ZWJ5IGFsbG93cyB0byBjYWxjdWxhdGUgdGhlIHBlcmNlbnRhZ2UgcmVwcmVzZW50ZWQgYnkgdGhlIHZh" +
               "bHVlLiBUaGUgbG93ZXN0IHZhbHVlIGlzIGludGVycHJldGVkIGFzIDAgcGVyY2VudCwgdGhlIGhpZ2hl" +
               "c3QgaXMgaW50ZXJwcmV0ZWQgYXMgMTAwIHBlcmNlbnQuAC8BAEAJAE6TFwAAAAr/////AwP/////AQAA" +
               "ABVgiQsCAAAAAAAHAAAARVVSYW5nZQEBlBcALgBEAE6UFwAAAQB0A/////8BAf////8AAAAANWCJCwIA" +
               "AAABAA4AAABTdGFja2xpZ2h0TW9kZQEBeRcDAAAAAGcAAABTaG93cyBpbiB3aGF0IHdheSAoc3RhY2sg" +
               "b2YgaW5kaXZpZHVhbCBsaWdodHMsIGxldmVsIG1ldGVyLCBydW5uaW5nIGxpZ2h0KSB0aGUgc3RhY2ts" +
               "aWdodCB1bml0IGlzIHVzZWQuAC4ARABOeRcAAAEBugv/////AwP/////AAAAACRggAsBAAAAAQAMAAAA" +
               "U3RhY2tSdW5uaW5nAQGNEwMAAAAARgAAAFZhbGlkIGlmIHRoZSBzdGFja2xpZ2h0IGlzIHVzZWQgaW4g" +
               "4oCcUnVubmluZ19MaWdodOKAnSBTdGFja2xpZ2h0TW9kZS4ALwEB7AMAUI0TAAD/////AAAAACRgABAI" +
               "AAAAAQAOAAAAU3RhY2tsaWdodFR5cGUBAfIDAwAAAABaAAAARW50cnkgcG9pbnQgdG8gYSBzdGFja2xp" +
               "Z2h0IHdpdGggdGhlIHBvc3NpYmlsaXR5IHRvIHNob3cgdGhlIHN0YWNrbGlnaHTigJlzIGhlYWx0aCBz" +
               "dGF0dXMuAQHqAwEAAAABAMNEAAECyzoCAAAANWCJCwIAAAACAAwAAABEZXZpY2VIZWFsdGgBAZYXAwAA" +
               "AAA5AAAAQ29udGFpbnMgdGhlIGhlYWx0aCBzdGF0dXMgaW5mb3JtYXRpb24gb2YgdGhlIHN0YWNrbGln" +
               "aHQuAC8APwBQlhcAAAECZBj/////AwP/////AAAAACRggAsBAAAAAgASAAAARGV2aWNlSGVhbHRoQWxh" +
               "cm1zAQGPEwMAAAAAZwAAAENvbnRhaW5zIGFsYXJtcyBvZiB0aGUgc3RhY2tsaWdodHMgcHJvdmlkaW5n" +
               "IG1vcmUgZGV0YWlsZWQgaW5mb3JtYXRpb24gb24gdGhlIGhlYWx0aCBvZiB0aGUgc3RhY2tsaWdodC4A" +
               "LwA9AFCPEwAA/////wAAAAAkaAAQCAAAAAEAEAAAAFN0YWNrRWxlbWVudFR5cGUBAe0DAwAAAAAoAAAA" +
               "QmFzZSBjbGFzcyBmb3IgZWxlbWVudHMgaW4gYSBzdGFja2xpZ2h0LgA6AQEAAAABAMNEAAEA2VsDAAAA" +
               "NWCJCwIAAAABAAwAAABJc1BhcnRPZkJhc2UBAX4XAwAAAACzAAAASW5kaWNhdGVzLCBpZiB0aGUgZWxl" +
               "bWVudCBpcyBjb250YWluZWQgaW4gdGhlIG1vdW50aW5nIGJhc2Ugb2YgdGhlIHN0YWNrbGlnaHQuIEFs" +
               "bCBlbGVtZW50cyBjb250YWluZWQgaW4gdGhlIG1vdW50aW5nIGJhc2Ugc2hhbGwgYmUgYXQgdGhlIGJl" +
               "Z2lubmluZyBvZiB0aGUgbGlzdCBvZiBzdGFjayBlbGVtZW50cy4ALgBEAFB+FwAAAAH/////AwP/////" +
               "AAAAADVgiQsCAAAAAAAMAAAATnVtYmVySW5MaXN0AQF/FwMAAAAAXQAAAEVudW1lcmF0ZSB0aGUgc3Rh" +
               "Y2tsaWdodCBlbGVtZW50cyBjb3VudGluZyB1cHdhcmRzIGJlZ2lubmluZyBmcm9tIHRoZSBiYXNlIG9m" +
               "IHRoZSBzdGFja2xpZ2h0LgAuAEQATn8XAAAAHP////8BAf////8AAAAANWCJCwIAAAABAAgAAABTaWdu" +
               "YWxPbgEBfRcDAAAAAFUAAABJbmRpY2F0ZXMgaWYgdGhlIHNpZ25hbCBlbWl0dGVkIGJ5IHRoZSBzdGFj" +
               "ayBlbGVtZW50IGlzIGN1cnJlbnRseSBzd2l0Y2hlZCBvbiBvciBub3QuAC4ARABQfRcAAAAB/////wMD" +
               "/////wAAAAAkYAAQCAAAAAEAGAAAAFN0YWNrRWxlbWVudEFjb3VzdGljVHlwZQEB7wMDAAAAAC8AAABS" +
               "ZXByZXNlbnRzIGFuIGFjb3VzdGljIGVsZW1lbnQgaW4gYSBzdGFja2xpZ2h0LgEB7QP/////AwAAACRg" +
               "gAsBAAAAAQAPAAAAQWNvdXN0aWNTaWduYWxzAQGLEwMAAAAASgAAAENvbnRhaW5zIGEgbGlzdCBvZiBh" +
               "dWRpbyBzaWduYWxzIHVzZWQgYnkgdGhpcyBhY291c3RpYyBzdGFja2xpZ2h0IGVsZW1lbnQuAC8BAN5b" +
               "AE6LEwAAAQAAAAApAAEAVQgBAAAAJGDACwEAAAANAAAAT3JkZXJlZE9iamVjdAAADwAAADxPcmRlcmVk" +
               "T2JqZWN0PgEBjBMDAAAAAB4AAABSZXByZXNlbnRzIGFuIGFjb3VzdGljIHNpZ25hbC4AMQEB8QMBAPYs" +
               "jBMAAAEAAAABAMNEAAEA2VsBAAAANWCJCwIAAAAAAAwAAABOdW1iZXJJbkxpc3QBAY4XAwAAAAB+AAAA" +
               "RW51bWVyYXRlIHRoZSBhY291c3RpYyBzaWduYWxzLiBJbnN0YW5jZXMgb2YgU3RhY2tFbGVtZW50QWNv" +
               "dXN0aWNUeXBlIGluZGV4IGludG8gdGhpcyBudW1iZXIgdXNpbmcgdGhlIE9wZXJhdGlvbk1vZGUgUHJv" +
               "cGVydHkuAC4ARABOjhcAAAAc/////wMD/////wAAAAA1YIkLAgAAAAEACQAAAEludGVuc2l0eQEBhRcD" +
               "AAAAAG8BAABJbmRpY2F0ZXMgdGhlIHNvdW5kIHByZXNzdXJlIGxldmVsIG9mIHRoZSBhY291c3RpYyBz" +
               "aWduYWwgd2hlbiBzd2l0Y2hlZCBvbi4gVGhpcyB2YWx1ZSBzaGFsbCBvbmx5IGhhdmUgcG9zaXRpdmUg" +
               "dmFsdWVzLiBUaGUgbWFuZGF0b3J5IEVVUmFuZ2UgUHJvcGVydHkgb2YgdGhlIFZhcmlhYmxlIGluZGlj" +
               "YXRlcyB0aGUgbG93ZXN0IGFuZCBoaWdoZXN0IHZhbHVlIGFuZCB0aGVyZWJ5IGFsbG93cyB0byBjYWxj" +
               "dWxhdGUgdGhlIHBlcmNlbnRhZ2UgcmVwcmVzZW50ZWQgYnkgdGhlIHZhbHVlLiBUaGUgbG93ZXN0IHZh" +
               "bHVlIGlzIGludGVycHJldGVkIGFzIDAgcGVyY2VudCwgdGhlIGhpZ2hlc3QgaXMgaW50ZXJwcmV0ZWQg" +
               "YXMgMTAwIHBlcmNlbnQuAC8BAEAJAFCFFwAAAAr/////AwP/////AQAAABVgiQsCAAAAAAAHAAAARVVS" +
               "YW5nZQEBhhcALgBEAE6GFwAAAQB0A/////8BAf////8AAAAANWCJCwIAAAABAA0AAABPcGVyYXRpb25N" +
               "b2RlAQGEFwMAAAAA4QAAAEluZGljYXRlcyB3aGF0IHNpZ25hbCBvZiB0aGUgbGlzdCBvZiBBY291c3Rp" +
               "Y1NpZ25hbFR5cGUgbm9kZXMgaXMgcGxheWVkIHdoZW4gdGhlIGFjb3VzdGljIGVsZW1lbnQgaXMgc3dp" +
               "dGNoZWQgb24uIEl0IHNoYWxsIGNvbnRhaW4gYW4gaW5kZXggaW50byB0aGUgTnVtYmVySW5MaXN0IG9m" +
               "IHRoZSByZXNwZWN0aXZlIEFjb3VzdGljU2lnbmFsVHlwZSBPYmplY3Qgb2YgQWNvdXN0aWNTaWduYWxz" +
               "LgAvAD8AToQXAAAAHP////8DA/////8AAAAAJGAAEAgAAAABABUAAABTdGFja0VsZW1lbnRMaWdodFR5" +
               "cGUBAe4DAwAAAAAqAAAAUmVwcmVzZW50cyBhIGxhbXAgZWxlbWVudCBpbiBhIHN0YWNrbGlnaHQuAQHt" +
               "A/////8FAAAAJGDACwEAAAAaAAAAQ29udHJvbENoYW5uZWxfUGxhY2Vob2xkZXIBABAAAAA8Q29udHJv" +
               "bENoYW5uZWw+AQGKEwMAAAAAgAAAAFRoZSBsaXN0IG9mIDxDb250cm9sQ2hhbm5lbD4gaW5zdGFuY2Vz" +
               "IHNob3dzIHRoZSBjb250cm9sIGluZm9ybWF0aW9uIGZvciBlYWNoIGluZGVwZW5kZW50IGNvbG91ciBj" +
               "aGFubmVsIG9mIHRoZSBzdGFja2VkIGVsZW1lbnQuAC8BAfADAQD0LIoTAAD/////AwAAADVgiQsCAAAA" +
               "AQAMAAAAQ2hhbm5lbENvbG9yAQGPFwMAAAAAYwAAAEluZGljYXRlcyBpbiB3aGF0IG1vZGUgKGNvbnRp" +
               "bnVvdXNseSBvbiwgYmxpbmtpbmcsIGZsYXNoaW5nKSB0aGUgY2hhbm5lbCBvcGVyYXRlcyB3aGVuIHN3" +
               "aXRjaGVkIG9uLgAvAD8ATo8XAAABAbwL/////wMD/////wAAAAA1YIkLAgAAAAEACgAAAFNpZ25hbE1v" +
               "ZGUBAZAXAwAAAABKAAAAQ29udGFpbnMgYSBsaXN0IG9mIGF1ZGlvIHNpZ25hbHMgdXNlZCBieSB0aGlz" +
               "IGFjb3VzdGljIHN0YWNrbGlnaHQgZWxlbWVudC4ALwA/AE6QFwAAAQG9C/////8DA/////8AAAAANWCJ" +
               "CwIAAAABAAgAAABTaWduYWxPbgEBkRcDAAAAACcAAABJbmRpY2F0ZXMgaWYgdGhlIGNvbG91ciBpcyBz" +
               "d2l0Y2hlZCBvbi4ALgBEAE6RFwAAAAH/////AwP/////AAAAADVgiQsCAAAAAQAJAAAASW50ZW5zaXR5" +
               "AQGCFwMAAAAAIwEAAEludGVuc2l0eSBvZiB0aGUgbGFtcCwgdGh1cyBpdHMgYnJpZ2h0bmVzcy4gVGhl" +
               "IG1hbmRhdG9yeSBFVVJhbmdlIFByb3BlcnR5IG9mIHRoZSBWYXJpYWJsZSBpbmRpY2F0ZXMgdGhlIGxv" +
               "d2VzdCBhbmQgaGlnaGVzdCB2YWx1ZSBhbmQgdGhlcmVieSBhbGxvd3MgdG8gY2FsY3VsYXRlIHRoZSBw" +
               "ZXJjZW50YWdlIHJlcHJlc2VudGVkIGJ5IHRoZSB2YWx1ZS4gVGhlIGxvd2VzdCB2YWx1ZSBpcyBpbnRl" +
               "cnByZXRlZCBhcyAwIHBlcmNlbnQsIHRoZSBoaWdoZXN0IGlzIGludGVycHJldGVkIGFzIDEwMCBwZXJj" +
               "ZW50LgAvAQBACQBQghcAAAAK/////wMD/////wEAAAAVYIkLAgAAAAAABwAAAEVVUmFuZ2UBAYMXAC4A" +
               "RABOgxcAAAEAdAP/////AQH/////AAAAADVgiQsCAAAAAQALAAAAU2lnbmFsQ29sb3IBAYAXAwAAAAA7" +
               "AAAASW5kaWNhdGVzIHRoZSBjb2xvdXIgdGhlIGxhbXAgZWxlbWVudCBoYXMgd2hlbiBzd2l0Y2hlZCBv" +
               "bi4ALwA/AFCAFwAAAQG8C/////8DA/////8AAAAANWCJCwIAAAABAAoAAABTaWduYWxNb2RlAQGBFwMA" +
               "AAAAWwAAAFNob3dzIGluIHdoYXQgd2F5IHRoZSBsYW1wIGlzIHVzZWQgKGNvbnRpbnVvdXMgbGlnaHQs" +
               "IGZsYXNoaW5nLCBibGlua2luZykgd2hlbiBzd2l0Y2hlZCBvbi4ALwA/AFCBFwAAAQG9C/////8DA///" +
               "//8AAAAAFWCJCwIAAAABAA8AAABTaWduYWxSR0JXVmFsdWUBAaQXAC8APwBQpBcAAAEBvwv/////AwP/" +
               "////AAAAACRgABAIAAAAAQAOAAAAU3RhY2tMZXZlbFR5cGUBAesDAwAAAAB+AAAAQ29udGFpbnMgaW5m" +
               "b3JtYXRpb24gcmVsZXZhbnQgdG8gYSBzdGFja2xpZ2h0IG9wZXJhdGluZyBhcyBhIGxldmVsIG1ldGVy" +
               "LiBUaGUgd2hvbGUgc3RhY2sgaXMgY29udHJvbGxlZCBieSBhIHBlcmNlbnR1YWwgdmFsdWUuADr/////" +
               "AgAAADVgiQsCAAAAAQALAAAARGlzcGxheU1vZGUBAXwXAwAAAABMAAAASW5kaWNhdGVzIGluIHdoYXQg" +
               "d2F5IHRoZSBwZXJjZW50dWFsIHZhbHVlIGlzIGRpc3BsYXllZCB3aXRoIHRoZSBzdGFja2xpZ2h0LgAv" +
               "AD8ATnwXAAABAbsL/////wMD/////wAAAAA1YIkLAgAAAAEADAAAAExldmVsUGVyY2VudAEBehcDAAAA" +
               "ADIBAABTaG93cyB0aGUgcGVyY2VudHVhbCB2YWx1ZSB0aGUgc3RhY2tsaWdodCBpcyByZXByZXNlbnRp" +
               "bmcuIFRoZSBtYW5kYXRvcnkgRVVSYW5nZSBQcm9wZXJ0eSBvZiB0aGUgVmFyaWFibGUgaW5kaWNhdGVz" +
               "IHRoZSBsb3dlc3QgYW5kIGhpZ2hlc3QgdmFsdWUgYW5kIHRoZXJlYnkgYWxsb3dzIHRvIGNhbGN1bGF0" +
               "ZSB0aGUgcGVyY2VudGFnZSByZXByZXNlbnRlZCBieSB0aGUgdmFsdWUuIFRoZSBsb3dlc3QgdmFsdWUg" +
               "aXMgaW50ZXJwcmV0ZWQgYXMgMCBwZXJjZW50LCB0aGUgaGlnaGVzdCBpcyBpbnRlcnByZXRlZCBhcyAx" +
               "MDAgcGVyY2VudC4ALwEAQAkATnoXAAAACv////8DA/////8BAAAAFWCJCwIAAAAAAAcAAABFVVJhbmdl" +
               "AQF7FwAuAEQATnsXAAABAHQD/////wEB/////wAAAAAkYAAQCAAAAAEAEAAAAFN0YWNrUnVubmluZ1R5" +
               "cGUBAewDAwAAAACZAAAAQ29udGFpbnMgaW5mb3JtYXRpb24gcmVsZXZhbnQgdG8gYSBzdGFja2xpZ2h0" +
               "IG9wZXJhdGluZyBhcyBhIHJ1bm5pbmcgbGlnaHQuIFRoaXMgYmFzZSB0eXBlIGRvZXMgbm90IGRlZmlu" +
               "ZSBhbnkgc3BlY2lmaWMgaW5mb3JtYXRpb24sIGJ1dCBjYW4gYmUgZXh0ZW5kZWQuADr/////AAAAAARg" +
               "wAIBAAAADQAAAERlZmF1bHRCaW5hcnkAAA4AAABEZWZhdWx0IEJpbmFyeQEBkRMATJETAAACAAAAACYB" +
               "AQG/CwAnAAEBohcAAAAABGDAAgEAAAAKAAAARGVmYXVsdFhtbAAACwAAAERlZmF1bHQgWE1MAQGWEwBM" +
               "lhMAAAIAAAAAJgEBAb8LACcAAQGjFwAAAAA="
            );
            using (MemoryStream stream = new MemoryStream(initializationBuffer))
            {
                NodeStateCollection predefinedNodes = new NodeStateCollection();
                predefinedNodes.LoadFromBinary(context, stream, true);
                return predefinedNodes;
            }
        }
        #endregion
    }
    #endregion
}