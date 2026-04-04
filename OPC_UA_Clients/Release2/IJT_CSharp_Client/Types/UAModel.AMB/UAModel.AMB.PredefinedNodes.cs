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

#pragma warning disable CS1591 // Missing XML comment for publicly visible type or member
#pragma warning disable CA1515 // Consider making public types internal
#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1028 // Enum Storage should be Int32

namespace UAModel.AMB
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
               "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8hAAAABGAAUEAAAAABABUA" +
               "AABNYWludGVuYW5jZU1ldGhvZEVudW0BAbwLAB0AewGFAAAAAgAAAAAAAAAAAAAAAgUAAABMb2NhbAIe" +
               "AAAATWFpbnRlbmFuY2UgY2xvc2UgdG8gdGhlIGFzc2V0BQAAAExvY2FsAQAAAAAAAAACBgAAAFJlbW90" +
               "ZQIhAAAATWFpbnRlbmFuY2UgZnJvbSBhbm90aGVyIGxvY2F0aW9uBgAAAFJlbW90Zf////8BAAAAF2Cp" +
               "CgIAAAAAAAoAAABFbnVtVmFsdWVzAQGNFwAuAESNFwAAlgIAAAABADsgATUAAAAAAAAAAAAAAAIFAAAA" +
               "TG9jYWwCHgAAAE1haW50ZW5hbmNlIGNsb3NlIHRvIHRoZSBhc3NldAEAOyABOQAAAAEAAAAAAAAAAgYA" +
               "AABSZW1vdGUCIQAAAE1haW50ZW5hbmNlIGZyb20gYW5vdGhlciBsb2NhdGlvbgEAqh0BAAAAAQAAAAIA" +
               "AAABAf////8AAAAAJGAAUEAAAAABABIAAABOYW1lTm9kZUlkRGF0YVR5cGUBAbsLAwAAAAB2AAAAQSBo" +
               "dW1hbi1yZWFkYWJsZSBuYW1lIG9mIHNvbWV0aGluZyBwbHVzIG9wdGlvbmFsbHkgdGhlIE5vZGVJZCBp" +
               "biBjYXNlIHRoZSBzb21ldGhpbmcgaXMgcmVwcmVzZW50ZWQgaW4gdGhlIEFkZHJlc3NTcGFjZQAWAHoB" +
               "DwEAAAAAABYAAAAAAgAAAAQAAABOYW1lAmUAAABUaGUgaHVtYW4tcmVhZGFibGUgbmFtZS4gU2hhbGwg" +
               "YmUgdGhlIERpc3BsYXlOYW1lIG9mIHRoZSBOb2RlSWQgZmllbGQsIGluIGNhc2UgdGhlIE5vZGVJZCBp" +
               "cyBwcm92aWRlZAAV/////wAAAAAAAAAAAAYAAABOb2RlSWQCZAAAAE9wdGlvbmFsbHkgcHJvdmlkZWQg" +
               "Tm9kZUlkLCBpbiBjYXNlIHRoZSByZWZlcmVuY2VkIHRoaW5nIGlzIHJlcHJlc2VudGVkIGFzIE5vZGUg" +
               "aW4gdGhlIEFkZHJlc3NTcGFjZS4AEf////8AAAAAAAAAAAACAAAAACYAAQGUEwAmAAEBlRMAAAAAJGAA" +
               "UEAAAAABABEAAABSb290Q2F1c2VEYXRhVHlwZQEBugsDAAAAABYAAABSb290IGNhdXNlIG9mIGFuIGFs" +
               "YXJtABYAegHZAgAAAAAAFgAAAAACAAAACwAAAFJvb3RDYXVzZUlkArMBAABUaGUgTm9kZUlkIG9mIHRo" +
               "ZSByb290IGNhdXNlIG9mIGFuIGFsYXJtLiBUaGlzIGNhbiBwb2ludCB0byBhbm90aGVyIE5vZGUgaW4g" +
               "dGhlIEFkZHJlc3NTcGFjZSBvciBhIENvbmRpdGlvbklkLCB0aGF0IGlzIG5vdCBuZWNlc3NhcmlseSBy" +
               "ZXByZXNlbnQgYXMgT2JqZWN0IGluIHRoZSBBZGRyZXNzU3BhY2UuIElkZWFsbHksIHRoaXMgcG9pbnRz" +
               "IGRpcmVjdGx5IHRvIHRoZSByb290IGNhdXNlLiBQb3RlbnRpYWxseSwgaXQgcG9pbnRzIHRvIGFuIGFs" +
               "YXJtIHRoYXQgaGFzIGFuIGFkZGl0aW9uYWwgcm9vdCBjYXVzZS4gQ2xpZW50cyBzaGFsbCBleHBlY3Qs" +
               "IHRoYXQgdGhleSBuZWVkIHRvIGZvbGxvdyBhIHBhdGggdG8gZmluZCB0aGUgcm9vdCBjYXVzZS4gSWYg" +
               "dGhlIHJvb3QgY2F1c2UgaXMgdW5rbm93biwgdGhlIE5vZGVJZCBzaGFsbCBiZSBzZXQgdG8gTlVMTC4A" +
               "Ef////8AAAAAAAAAAAAJAAAAUm9vdENhdXNlAtYAAABMb2NhbGl6ZWQgZGVzY3JpcHRpb24gb2YgdGhl" +
               "IHJvb3QgY2F1c2Ugb2YgYW4gYWxhcm0uIFRoaXMgY2FuIGJlIHRoZSBEaXNwbGF5TmFtZSBvZiB0aGUg" +
               "Tm9kZSByZWZlcmVuY2VkIGJ5IFJvb3RDYXVzZUlkIG9yIGEgbW9yZSBkZXNjcmlwdGl2ZSB0ZXh0LiBJ" +
               "ZiB0aGUgcm9vdCBjYXVzZSBpcyB1bmtub3duLCB0aGlzIHNob3VsZCBiZSBkZXNjcmliZWQgaW4gdGhl" +
               "IHRleHQuABX/////AAAAAAAAAAAAAgAAAAAmAAEBiRMAJgABAY0TAAAAACRsABAgAAAAAQAIAAAAQ29u" +
               "dGFpbnMBAaIPAwAAAABkAAAATGlua3MgYW4gT2JqZWN0IHJlcHJlc2VudGluZyBzb21lIHR5cGUgb2Yg" +
               "bG9jYXRpb24gdG8gT2JqZWN0cyAobGlrZSBhc3NldHMpIGxvY2F0ZWQgaW4gdGhhdCBsb2NhdGlvbgAh" +
               "AQMAAAAACQAAAExvY2F0ZWRJbv////8AAAAAJGQAECAAAAABABQAAABIaWVyYXJjaGljYWxDb250YWlu" +
               "cwEBow8DAAAAAHsAAABMaW5rcyBhbiBPYmplY3QgcmVwcmVzZW50aW5nIHBhcnQgaW4gYSBoaWVyYXJj" +
               "aGljYWwgbG9jYXRpb24gdG8gT2JqZWN0cyAobGlrZSBhc3NldHMpIGxvY2F0ZWQgaW4gdGhhdCBoaWVy" +
               "YXJjaGljYWwgbG9jYXRpb24BAaIPAwAAAAAVAAAASGllcmFyY2hpY2FsTG9jYXRlZElu/////wAAAAAk" +
               "ZAAQIAAAAAEAEwAAAE9wZXJhdGlvbmFsQ29udGFpbnMBAaQPAwAAAAByAAAATGlua3MgYW4gT2JqZWN0" +
               "IHJlcHJlc2VudGluZyBhbiBvcGVyYXRpb25hbCBsb2NhdGlvbiB0byBPYmplY3RzIChsaWtlIGFzc2V0" +
               "cykgbG9jYXRlZCBpbiB0aGF0IG9wZXJhdGlvbmFsIGxvY2F0aW9uAQGiDwMAAAAAFAAAAE9wZXJhdGlv" +
               "bmFsTG9jYXRlZElu/////wAAAAAkaAAQCAAAAAEAIAAAAENhbGlicmF0aW9uRHVlQ29uZGl0aW9uQ2xh" +
               "c3NUeXBlAQHtAwMAAAAAEgAAAENhbGlicmF0aW9uIGlzIGR1ZQEAnSsB/////wAAAAAkaAAQCAAAAAEA" +
               "HwAAAEV4dGVybmFsQ2hlY2tDb25kaXRpb25DbGFzc1R5cGUBAfcDAwAAAAAmAAAAQW4gZXh0ZXJuYWwg" +
               "Y2hlY2sgbWFpbnRlbmFuY2UgYWN0aXZpdHkBAJ0rAf////8AAAAAJGgAEAgAAAABACcAAABGbGFzaFVw" +
               "ZGF0ZUluUHJvZ3Jlc3NDb25kaXRpb25DbGFzc1R5cGUBAe8DAwAAAAAYAAAARmxhc2ggdXBkYXRlIGlu" +
               "IHByb2dyZXNzAQCdKwH/////AAAAACRoABAIAAAAAQAdAAAASW1wcm92ZW1lbnRDb25kaXRpb25DbGFz" +
               "c1R5cGUBAfoDAwAAAAAjAAAAQW4gaW1wcm92ZW1lbnQgbWFpbnRlbmFuY2UgYWN0aXZpdHkBAJ0rAf//" +
               "//8AAAAAJGgAEAgAAAABABwAAABJbnNwZWN0aW9uQ29uZGl0aW9uQ2xhc3NUeXBlAQH2AwMAAAAAIgAA" +
               "AEFuIGluc3BlY3Rpb24gbWFpbnRlbmFuY2UgYWN0aXZpdHkBAJ0rAf////8AAAAAJGgAEAgAAAABABgA" +
               "AABSZXBhaXJDb25kaXRpb25DbGFzc1R5cGUBAfkDAwAAAAAdAAAAQSByZXBhaXIgbWFpbnRlbmFuY2Ug" +
               "YWN0aXZpdHkBAJ0rAf////8AAAAAJGgAEAgAAAABABsAAABTZXJ2aWNpbmdDb25kaXRpb25DbGFzc1R5" +
               "cGUBAfgDAwAAAAAgAAAAQSBzZXJ2aWNpbmcgbWFpbnRlbmFuY2UgYWN0aXZpdHkBAJ0rAf////8AAAAA" +
               "JGgAEAgAAAABACIAAABCYWRDb25maWd1cmF0aW9uQ29uZGl0aW9uQ2xhc3NUeXBlAQHwAwMAAAAAFAAA" +
               "AENvbmZpZ3VyYXRpb24gaXMgYmFkAQCeKwH/////AAAAACRoABAIAAAAAQAjAAAAQ29ubmVjdGlvbkZh" +
               "aWx1cmVDb25kaXRpb25DbGFzc1R5cGUBAesDAwAAAAAjAAAAT25lIG9yIG1vcmUgY29ubmVjdGlvbnMg" +
               "aGF2ZSBmYWlsZWQBAJ4rAf////8AAAAAJGgAEAgAAAABACMAAABGbGFzaFVwZGF0ZUZhaWxlZENvbmRp" +
               "dGlvbkNsYXNzVHlwZQEB+wMDAAAAABcAAABGbGFzaCB1cGRhdGUgaGFzIGZhaWxlZAEAnisB/////wAA" +
               "AAAkaAAQCAAAAAEAIAAAAE91dE9mUmVzb3VyY2VzQ29uZGl0aW9uQ2xhc3NUeXBlAQHxAwMAAAAAFwAA" +
               "AE91dCBvZiByZXNvdXJjZXMgaXNzdWVzAQCeKwH/////AAAAACRoABAIAAAAAQAdAAAAT3V0T2ZNZW1v" +
               "cnlDb25kaXRpb25DbGFzc1R5cGUBAfIDAwAAAAAUAAAAT3V0IG9mIG1lbW9yeSBpc3N1ZXMBAfEDAf//" +
               "//8AAAAAJGgAEAgAAAABACEAAABPdmVyVGVtcGVyYXR1cmVDb25kaXRpb25DbGFzc1R5cGUBAewDAwAA" +
               "AAAQAAAAT3ZlciB0ZW1wZXJhdHVyZQEAnisB/////wAAAAAkaAAQCAAAAAEAIQAAAFNlbGZUZXN0RmFp" +
               "bHVyZUNvbmRpdGlvbkNsYXNzVHlwZQEB7gMDAAAAABEAAABTZWxmLVRlc3QgZmFpbHVyZQEAnisB////" +
               "/wAAAAAkaAAQCAAAAAEAFQAAAElNYWludGVuYW5jZUV2ZW50VHlwZQEB9AMDAAAAAGIAAABJbmZvcm1h" +
               "dGlvbiBvbiBtYWludGVuYW5jZSBhY3Rpdml0aWVzLCBzaG91bGQgYnkgYXBwbGllZCB0byBjb25kaXRp" +
               "b25zIChDb25kaXRpb25UeXBlIG9yIHN1YnR5cGVzKQEAwkQB/////wkAAAA1YIkLAgAAAAEAFAAAAENv" +
               "bmZpZ3VyYXRpb25DaGFuZ2VkAQGaFwMAAAAAfwEAAEluZm9ybWF0aW9uIGlmIHRoZSBjb25maWd1cmF0" +
               "aW9uIG9mIHRoZSBhc3NldCBpcyBwbGFubmVkIHRvIGJlIGNoYW5nZWQgb3IgaGFzIGNoYW5nZWQgZHVy" +
               "aW5nIHRoZSBtYWludGVuYW5jZSBhY3Rpdml0eS4gRkFMU0UgaW5kaWNhdGVzIG5vIGNoYW5nZSwgYW5k" +
               "IFRSVUUgaW5kaWNhdGVzIGEgY2hhbmdlLiBUaGUgY29udGVudCBtYXkgY2hhbmdlIGR1cmluZyB0aGUg" +
               "ZGlmZmVyZW50IE1haW50ZW5hbmNlU3RhdGVzLiBCeSBhY2Nlc3NpbmcgdGhlIGhpc3Rvcnkgb2YgRXZl" +
               "bnRzIGEgQ2xpZW50IGNhbiBkaXN0aW5ndWlzaCBiZXR3ZWVuIHRoZSBwbGFubmVkIGFuZCBhY3R1YWwg" +
               "Y29uZmlndXJhdGlvbiBjaGFuZ2VzIGR1cmluZyB0aGUgbWFpbnRlbmFuY2UgYWN0aXZpdHkuAC4ARABQ" +
               "mhcAAAAB/////wMD/////wAAAAA1YIkLAgAAAAEAEQAAAEVzdGltYXRlZERvd250aW1lAQGUFwMAAAAA" +
               "0AEAAFRoZSBlc3RpbWF0ZWQgdGltZSB0aGUgZXhlY3V0aW9uIG9mIHRoZSBtYWludGVuYW5jZSBhY3Rp" +
               "dml0eSB3aWxsIHRha2UuIEluIGNhc2Ugb2YgcmVwbGFubmluZywgaXQgaXMgYWxsb3dlZCB0byBjaGFu" +
               "Z2UgdGhlIEVzdGltYXRlZERvd250aW1lLiBJZiBkdXJpbmcgdGhlIGV4ZWN1dGlvbiBvZiB0aGUgbWFp" +
               "bnRlbmFuY2UgYWN0aXZpdHkgdGhlIEVzdGltYXRlZERvd250aW1lIGNhbiBiZSBhZGp1c3RlZCAoZS5n" +
               "LiwgdGhlIGFzc2V0IG5lZWRzIHRvIGJlIHJlcGFpcmVkIGJlY2F1c2UgYW4gaW5zcGVjdGlvbiBmb3Vu" +
               "ZCBzb21lIGlzc3VlcykgdGhpcyBzaG91bGQgYmUgZG9uZS4gQ2xpZW50cyBjYW4gYWNjZXNzIHRoZSBo" +
               "aXN0b3J5IG9mIEV2ZW50cyB0byByZWNlaXZlIHRoZSBpbmZvcm1hdGlvbiBvbiB0aGUgb3JpZ2luYWwg" +
               "ZXN0aW1hdGVzIHdoZW4gdGhlIG1haW50ZW5hbmNlIGFjdGl2aXR5IHN0YXJ0ZWQuAC4ARABQlBcAAAEA" +
               "IgH/////AwP/////AAAAADVgiQsCAAAAAQARAAAATWFpbnRlbmFuY2VNZXRob2QBAZkXAwAAAAAMAQAA" +
               "SW5mb3JtYXRpb24gYWJvdXQgdGhlIHBsYW5uZWQgb3IgdXNlZCBtYWludGVuYW5jZSBtZXRob2QuIFRo" +
               "ZSBjb250ZW50IG1heSBjaGFuZ2UgZHVyaW5nIHRoZSBkaWZmZXJlbnQgTWFpbnRlbmFuY2VTdGF0ZXMu" +
               "IEJ5IGFjY2Vzc2luZyB0aGUgaGlzdG9yeSBvZiBFdmVudHMgYSBDbGllbnQgY2FuIGRpc3Rpbmd1aXNo" +
               "IGJldHdlZW4gdGhlIHBsYW5uZWQgYW5kIGFjdHVhbCB1c2VkIG1haW50ZW5hbmNlIG1ldGhvZCBkdXJp" +
               "bmcgdGhlIG1haW50ZW5hbmNlIGFjdGl2aXR5LgAuAEQAUJkXAAABAbwL/////wMD/////wAAAAAkYIAL" +
               "AQAAAAEAEAAAAE1haW50ZW5hbmNlU3RhdGUBAZYTAwAAAABvAAAASW5mb3JtYXRpb24gaWYgdGhlIG1h" +
               "aW50ZW5hbmNlIGFjdGl2aXR5IGlzIHN0aWxsIHBsYW5uZWQsIGN1cnJlbnRseSBpbiBleGVjdXRpb24s" +
               "IG9yIGhhcyBhbHJlYWR5IGJlZW4gZXhlY3V0ZWQuAC8BAfUDAE6WEwAA/////wEAAAAVYIkLAgAAAAAA" +
               "DAAAAEN1cnJlbnRTdGF0ZQEBkRcALwEAyAoATpEXAAAAFf////8BAf////8BAAAAFWCJCwIAAAAAAAIA" +
               "AABJZAEBkhcALgBEAE6SFwAAABH/////AQH/////AAAAADVgiQsCAAAAAQATAAAATWFpbnRlbmFuY2VT" +
               "dXBwbGllcgEBlRcDAAAAANABAABJbmZvcm1hdGlvbiBvbiB0aGUgc3VwcGxpZXIgdGhhdCBpcyBwbGFu" +
               "bmVkIHRvIGV4ZWN1dGUsIGN1cnJlbnRseSBleGVjdXRpbmcgb3IgaGFzIGV4ZWN1dGVkIHRoZSBtYWlu" +
               "dGVuYW5jZSBhY3Rpdml0eS4gVGhlIGNvbnRlbnQgbWF5IGNoYW5nZSBkdXJpbmcgdGhlIGRpZmZlcmVu" +
               "dCBNYWludGVuYW5jZVN0YXRlcy4gQnkgYWNjZXNzaW5nIHRoZSBoaXN0b3J5IG9mIEV2ZW50cyBhIENs" +
               "aWVudCBjYW4gZGlzdGluZ3Vpc2ggYmV0d2VlbiB0aGUgcGxhbm5lZCBhbmQgYWN0dWFsIHN1cHBsaWVy" +
               "IHRoYXQgZXhlY3V0ZWQgdGhlIG1haW50ZW5hbmNlIGFjdGl2aXR5LiBUaGUgdmFsdWUgY29udGFpbnMg" +
               "YWx3YXlzIGEgaHVtYW4tcmVhZGFibGUgbmFtZSBvZiB0aGUgc3VwcGxpZXIgYW5kIG9wdGlvbmFsbHkg" +
               "cmVmZXJlbmNlcyBhIE5vZGUgcmVwcmVzZW50aW5nIHRoZSBzdXBwbGllciBpbiB0aGUgQWRkcmVzc1Nw" +
               "YWNlLgAuAEQAUJUXAAABAbsL/////wMD/////wAAAAA3YIkLAgAAAAEAFAAAAFBhcnRzT2ZBc3NldFJl" +
               "cGxhY2VkAQGXFwMAAAAAagIAAEluZm9ybWF0aW9uIG9uIHRoZSBwYXJ0cyBvZiB0aGUgYXNzZXRzIHRo" +
               "YXQgYXJlIHBsYW5uZWQgdG8gYmUgc2VydmljZWQgZHVyaW5nIHRoZSBtYWludGVuYW5jZSBhY3Rpdml0" +
               "eSwgY3VycmVudGx5IHNlcnZpY2VkIG9yIGhhdmUgYmVlbiBzZXJ2aWNlZCwgZGVwZW5kaW5nIG9uIHRo" +
               "ZSBkaWZmZXJlbnQgTWFpbnRlbmFuY2VTdGF0ZXMuIFRoZSBjb250ZW50IG1heSBjaGFuZ2UgZHVyaW5n" +
               "IHRoZSBkaWZmZXJlbnQgTWFpbnRlbmFuY2VTdGF0ZXMuIEJ5IGFjY2Vzc2luZyB0aGUgaGlzdG9yeSBv" +
               "ZiBFdmVudHMgYSBDbGllbnQgY2FuIGRpc3Rpbmd1aXNoIGJldHdlZW4gdGhlIHBsYW5uZWQgYW5kIGFj" +
               "dHVhbCBwYXJ0cyBvZiB0aGUgYXNzZXRzIHNlcnZpY2VkIGR1cmluZyB0aGUgbWFpbnRlbmFuY2UgYWN0" +
               "aXZpdHkuIFRoZSB2YWx1ZSBjb250YWlucyBhbHdheXMgYW4gYXJyYXkgb2YgYSBodW1hbi1yZWFkYWJs" +
               "ZSBuYW1lIG9mIHRoZSBxdWFsaWZpY2F0aW9uIG9mIHRoZSBwYXJ0cyBvZiB0aGUgYXNzZXQgdG8gYmUg" +
               "c2VydmljZWQgYW5kIG9wdGlvbmFsbHkgcmVmZXJlbmNlcyBhIE5vZGUgcmVwcmVzZW50aW5nIHRoZSBw" +
               "YXJ0IG9mIHRoZSBhc3NldCBpbiB0aGUgQWRkcmVzc1NwYWNlLgAuAEQAUJcXAAABAbsLAQAAAAEAAAAA" +
               "AAAAAwP/////AAAAADdgiQsCAAAAAQAUAAAAUGFydHNPZkFzc2V0U2VydmljZWQBAZgXAwAAAABqAgAA" +
               "SW5mb3JtYXRpb24gb24gdGhlIHBhcnRzIG9mIHRoZSBhc3NldHMgdGhhdCBhcmUgcGxhbm5lZCB0byBi" +
               "ZSBzZXJ2aWNlZCBkdXJpbmcgdGhlIG1haW50ZW5hbmNlIGFjdGl2aXR5LCBjdXJyZW50bHkgc2Vydmlj" +
               "ZWQgb3IgaGF2ZSBiZWVuIHNlcnZpY2VkLCBkZXBlbmRpbmcgb24gdGhlIGRpZmZlcmVudCBNYWludGVu" +
               "YW5jZVN0YXRlcy4gVGhlIGNvbnRlbnQgbWF5IGNoYW5nZSBkdXJpbmcgdGhlIGRpZmZlcmVudCBNYWlu" +
               "dGVuYW5jZVN0YXRlcy4gQnkgYWNjZXNzaW5nIHRoZSBoaXN0b3J5IG9mIEV2ZW50cyBhIENsaWVudCBj" +
               "YW4gZGlzdGluZ3Vpc2ggYmV0d2VlbiB0aGUgcGxhbm5lZCBhbmQgYWN0dWFsIHBhcnRzIG9mIHRoZSBh" +
               "c3NldHMgc2VydmljZWQgZHVyaW5nIHRoZSBtYWludGVuYW5jZSBhY3Rpdml0eS4gVGhlIHZhbHVlIGNv" +
               "bnRhaW5zIGFsd2F5cyBhbiBhcnJheSBvZiBhIGh1bWFuLXJlYWRhYmxlIG5hbWUgb2YgdGhlIHF1YWxp" +
               "ZmljYXRpb24gb2YgdGhlIHBhcnRzIG9mIHRoZSBhc3NldCB0byBiZSBzZXJ2aWNlZCBhbmQgb3B0aW9u" +
               "YWxseSByZWZlcmVuY2VzIGEgTm9kZSByZXByZXNlbnRpbmcgdGhlIHBhcnQgb2YgdGhlIGFzc2V0IGlu" +
               "IHRoZSBBZGRyZXNzU3BhY2UuAC4ARABQmBcAAAEBuwsBAAAAAQAAAAAAAAADA/////8AAAAANWCJCwIA" +
               "AAABAAsAAABQbGFubmVkRGF0ZQEBkxcDAAAAAIABAABEYXRlIGZvciB3aGljaCB0aGUgbWFpbnRlbmFu" +
               "Y2UgYWN0aXZpdHkgaGFzIGJlZW4gc2NoZWR1bGVkLiBJbiBjYXNlIG9mIHJlcGxhbm5pbmcsIGl0IGlz" +
               "IGFsbG93ZWQgdG8gY2hhbmdlIHRoZSBQbGFubmVkRGF0ZS4gSG93ZXZlciwgaXQgaXMgbm90IHRoZSBp" +
               "bnRlbnRpb24gdGhhdCB0aGUgUGxhbm5lZERhdGUgaXMgbW9kaWZpZWQgYmVjYXVzZSB0aGUgbWFpbnRl" +
               "bmFuY2UgYWN0aXZpdHkgc3RhcnRzIHRvIGdldCBleGVjdXRlZC4gSWYgdGhlIFBsYW5uZWREYXRlIGRl" +
               "cGVuZHMgZm9yIGV4YW1wbGUgb24gdGhlIG9wZXJhdGlvbiBob3VycyBvZiB0aGUgYXNzZXQsIGl0IG1p" +
               "Z2h0IGdldCBhZGFwdGVkIGRlcGVuZGluZyBvbiB0aGUgcGFzc2VkIG9wZXJhdGlvbiBob3Vycy4ALgBE" +
               "AFCTFwAAAQAmAf////8DA/////8AAAAANWCJCwIAAAABABgAAABRdWFsaWZpY2F0aW9uT2ZQZXJzb25u" +
               "ZWwBAZYXAwAAAAAoAgAASW5mb3JtYXRpb24gb24gdGhlIHF1YWxpZmljYXRpb24gb2YgdGhlIHBlcnNv" +
               "bm5lbCB0aGF0IGlzIHBsYW5uZWQgdG8gZXhlY3V0ZSwgY3VycmVudGx5IGV4ZWN1dGluZyBvciBoYXMg" +
               "ZXhlY3V0ZWQgdGhlIG1haW50ZW5hbmNlIGFjdGl2aXR5LiBUaGUgY29udGVudCBtYXkgY2hhbmdlIGR1" +
               "cmluZyB0aGUgZGlmZmVyZW50IE1haW50ZW5hbmNlU3RhdGVzLiBCeSBhY2Nlc3NpbmcgdGhlIGhpc3Rv" +
               "cnkgb2YgRXZlbnRzIGEgQ2xpZW50IGNhbiBkaXN0aW5ndWlzaCBiZXR3ZWVuIHRoZSBwbGFubmVkIGFu" +
               "ZCBhY3R1YWwgcXVhbGlmaWNhdGlvbiBvZiB0aGUgcGVyc29ubmVsIHRoYXQgZXhlY3V0ZWQgdGhlIG1h" +
               "aW50ZW5hbmNlIGFjdGl2aXR5LiBUaGUgdmFsdWUgY29udGFpbnMgYWx3YXlzIGEgaHVtYW4tcmVhZGFi" +
               "bGUgbmFtZSBvZiB0aGUgcXVhbGlmaWNhdGlvbiBvZiB0aGUgcGVyc29ubmVsIGFuZCBvcHRpb25hbGx5" +
               "IHJlZmVyZW5jZXMgYSBOb2RlIHJlcHJlc2VudGluZyB0aGUgcXVhbGlmaWNhdGlvbiBvZiB0aGUgcGVy" +
               "c29ubmVsIGluIHRoZSBBZGRyZXNzU3BhY2UuAC4ARABQlhcAAAEBuwv/////AwP/////AAAAACRoABAI" +
               "AAAAAQAYAAAASVJvb3RDYXVzZUluZGljYXRpb25UeXBlAQHqAwMAAAAAYAAAAEluZm9ybWF0aW9uIG9u" +
               "IHRoZSByb290IGNhdXNlIG9mIGNvbmRpdGlvbnMsIHNob3VsZCBiZSBhcHBsaWVkIHRvIGFsYXJtcyAo" +
               "QWxhcm1UeXBlIG9yIHN1YnR5cGVzKQEAwkQB/////wEAAAA3YIkLAgAAAAEAEwAAAFBvdGVudGlhbFJv" +
               "b3RDYXVzZXMBAX8XAwAAAADuAQAAQW4gYXJyYXkgb2YgcG90ZW50aWFsIHJvb3QgY2F1c2VzIG9mIHRo" +
               "ZSBhbGFybS4gVGhpcyBpcyBpbnRlbmRlZCB0byBiZSBhIGhpbnQgdG8gdGhlIGNsaWVudCBhbmQgbWln" +
               "aHQgYmUgYSBsb2NhbCB2aWV3IG9uIHRoZSBwb3RlbnRpYWwgcm9vdCBjYXVzZXMgb2YgdGhlIGFsYXJt" +
               "LiBUaGUgbGlzdCBtaWdodCBub3QgY29udGFpbiBhbGwgcG90ZW50aWFsIHJvb3QgY2F1c2VzLCB0aGF0" +
               "IGlzLCBvdGhlciBwb3RlbnRpYWwgcm9vdCBjYXVzZXMgbWlnaHQgZXhpc3QgYXMgd2VsbC4gSWYgdGhl" +
               "IGFsYXJtIGl0c2VsZiBpcyBjb25zaWRlcmVkIHRvIGJlIHRoZSByb290IGNhdXNlLCB0aGUgYXJyYXkg" +
               "c2hhbGwgYmUgZW1wdHkuIElmIG5vIHBvdGVudGlhbCByb290IGNhdXNlcyBoYXZlIGJlZW4gaWRlbnRp" +
               "ZmllZCwgdGhlcmUgc2hhbGwgYmUgYXQgbGVhc3Qgb25lIGVudHJ5IGluIHRoZSBhcnJheSBpbmRpY2F0" +
               "aW5nIHRoYXQgdGhlIHJvb3QgY2F1c2UgaXMgdW5rbm93bi4ALgBEAE5/FwAAAQG6CwEAAAABAAAAAAAA" +
               "AAMD/////wAAAAAkYAAQCAAAAAEAFgAAAERvY3VtZW50YXRpb25MaW5rc1R5cGUBAfMDAwAAAABLAAAA" +
               "QWRkSW4gdG8gbGluayBkb2N1bWVudGF0aW9uIHByb3ZpZGVkIGJ5IHRoZSBtYW51ZmFjdHVyZXIgYW5k" +
               "IC8gb3IgZW5kLXVzZXIuADr/////BAAAADVgyQsCAAAAEAAAAExpbmtfUGxhY2Vob2xkZXIBAAYAAAA8" +
               "TGluaz4BAYEXAwAAAABFAAAAUmVwcmVzZW50cyBsaW5rcyB0byBleHRlcm5hbGx5IG1hbmFnZWQgZG9j" +
               "dW1lbnRhdGlvbiwgdHlwaWNhbGx5IFVSTHMuAC8APwEA9CyBFwAAAQDHXP////8DA/////8AAAAAJGGC" +
               "CwQAAAABAAcAAABBZGRMaW5rAQFcGwMAAAAAUgAAAE1ldGhvZCB0byBhZGQgYW4gZW5kLXVzZXIgc3Bl" +
               "Y2lmaWMgbGluayB0aGF0IGlzIHN0b3JlZCBwZXJzaXN0ZW50bHkgaW4gdGhlIHNlcnZlci4ALwEBXBsA" +
               "UFwbAAABAf////8CAAAAF2CpCwIAAAAAAA4AAABJbnB1dEFyZ3VtZW50cwEBghcALgBEAE6CFwAAlgQA" +
               "AAABACoBAawAAAAUAAAATGlua1RvRXh0ZXJuYWxTb3VyY2UBAMdc/////wAAAAACgwAAAExpbmsgdG8g" +
               "YW4gZXh0ZXJuYWwgc291cmNlLiBUaGUgc2VydmVyIG1pZ2h0IG9yIG1pZ2h0IG5vdCBjaGVjayBpZiBh" +
               "IGNvcnJlY3QgVVJJIGlzIHByb3ZpZGVkLCBvciBpZiB0aGUgVVJJIGlzIGF2YWlsYWJsZS9yZWFjaGFi" +
               "bGUuAQAqAQGIAAAACgAAAEJyb3dzZU5hbWUAFP////8AAAAAAmsAAABUaGUgQnJvd3NlTmFtZSBvZiB0" +
               "aGUgbmV3IGNyZWF0ZWQgTm9kZS4gTWV0aG9kIGZhaWxzIGlmIGEgVmFyaWFibGUgd2l0aCB0aGUgc2Ft" +
               "ZSBCcm93c2VOYW1lIGFscmVhZHkgZXhpc3RzLgEAKgEB2AAAAAsAAABEaXNwbGF5TmFtZQAV/////wAA" +
               "AAACugAAAFRoZSBEaXNwbGF5TmFtZSBvZiB0aGUgbmV3IGNyZWF0ZWQgTm9kZS4gSWYgdGhlIHNlcnZl" +
               "ciBzdXBwb3J0cyBtdWx0aXBsZSBsb2NhbGVzLCBhbmQgdGhlIENsaWVudCB3YW50cyB0byBwcm92aWRl" +
               "IG1vcmUgdGhhbiBvbmUgbG9jYWxlLCB0aGUgV3JpdGUgb3BlcmF0aW9uIG9uIHRoZSBWYXJpYWJsZSBz" +
               "aGFsbCBiZSB1c2VkLgEAKgEB2AAAAAsAAABEZXNjcmlwdGlvbgAV/////wAAAAACugAAAFRoZSBEZXNj" +
               "cmlwdGlvbiBvZiB0aGUgbmV3IGNyZWF0ZWQgTm9kZS4gSWYgdGhlIHNlcnZlciBzdXBwb3J0cyBtdWx0" +
               "aXBsZSBsb2NhbGVzLCBhbmQgdGhlIENsaWVudCB3YW50cyB0byBwcm92aWRlIG1vcmUgdGhhbiBvbmUg" +
               "bG9jYWxlLCB0aGUgV3JpdGUgb3BlcmF0aW9uIG9uIHRoZSBWYXJpYWJsZSBzaGFsbCBiZSB1c2VkLgEA" +
               "KAEBAAAAAQAAAAQAAAABAf////8AAAAAF2CpCwIAAAAAAA8AAABPdXRwdXRBcmd1bWVudHMBAYMXAC4A" +
               "RABOgxcAAJYBAAAAAQAqAQFIAAAADAAAAExpbmtWYXJpYWJsZQAR/////wAAAAACKQAAAFRoZSBOb2Rl" +
               "SWQgb2YgdGhlIG5ld2x5IGNyZWF0ZWQgVmFyaWFibGUuAQAoAQEAAAABAAAAAQAAAAEB/////wAAAAAV" +
               "YKkKAgAAAAAAGQAAAERlZmF1bHRJbnN0YW5jZUJyb3dzZU5hbWUBAYAXAC4ARIAXAAAUAQASAAAARG9j" +
               "dW1lbnRhdGlvbkxpbmtzABT/////AwP/////AAAAACRhggsEAAAAAQAKAAAAUmVtb3ZlTGluawEBXRsD" +
               "AAAAAEkAAABNZXRob2QgdG8gcmVtb3ZlIGFuIGVuZC11c2VyIHNwZWNpZmljIGxpbmsgdGhhdCBpcyBt" +
               "YW5hZ2VkIGluIHRoZSBzZXJ2ZXIuAC8BAV0bAFBdGwAAAQH/////AQAAABdgqQsCAAAAAAAOAAAASW5w" +
               "dXRBcmd1bWVudHMBAYQXAC4ARABOhBcAAJYBAAAAAQAqAQHRAAAAEwAAAFZhcmlhYmxlVG9CZURlbGV0" +
               "ZWQAEf////8AAAAAAqsAAABOb2RlSWQgb2YgdGhlIFZhcmlhYmxlIGNvbnRhaW5pbmcgYSBsaW5rLCB0" +
               "aGF0IHNob3VsZCBiZSBkZWxldGVkLiBWYXJpYWJsZSBzaGFsbCBiZSByZWZlcmVuY2VkIGZyb20gdGhl" +
               "IE9iamVjdCB3aXRoIGEgSGFzQ29tcG9uZW50IFJlZmVyZW5jZSB3aGVyZSB0aGUgTWV0aG9kIGlzIGNh" +
               "bGxlZCBvbi4BACgBAQAAAAEAAAABAAAAAQH/////AAAAACRgABAIAAAAAQAgAAAATWFpbnRlbmFuY2VF" +
               "dmVudFN0YXRlTWFjaGluZVR5cGUBAfUDAwAAAABkAAAASW5mb3JtYXRpb24sIHdoZXRoZXIgYSBtYWlu" +
               "dGVuYW5jZSBhY3Rpdml0eSBpcyBwbGFubmVkLCBjdXJyZW50bHkgaW4gZXhlY3V0aW9uLCBvciBoYXMg" +
               "YmVlbiBleGVjdXRlZAEA0wr/////BgAAAARggAoBAAAAAQAJAAAARXhlY3V0aW5nAQGPEwAvAQADCY8T" +
               "AAACAAAAADMBAQGSEwA0AQEBkRMBAAAAFWCpCwIAAAAAAAsAAABTdGF0ZU51bWJlcgEBhhcALgBEAE6G" +
               "FwAABwIAAAAAB/////8BAf////8AAAAABGCACgEAAAABAAgAAABGaW5pc2hlZAEBkBMALwEAAwmQEwAA" +
               "AgAAAAA0AQEBkhMAMwEBAZMTAQAAABVgqQsCAAAAAAALAAAAU3RhdGVOdW1iZXIBAYcXAC4ARABOhxcA" +
               "AAcDAAAAAAf/////AQH/////AAAAAARggAoBAAAAAQAXAAAARnJvbUV4ZWN1dGluZ1RvRmluaXNoZWQB" +
               "AZITAC8BAAYJkhMAAAIAAAAAMwABAY8TADQAAQGQEwEAAAAVYKkLAgAAAAAAEAAAAFRyYW5zaXRpb25O" +
               "dW1iZXIBAYkXAC4ARABOiRcAAAcCAAAAAAf/////AQH/////AAAAAARggAoBAAAAAQAVAAAARnJvbUZp" +
               "bmlzaGVkVG9QbGFubmVkAQGTEwAvAQAGCZMTAAACAAAAADMAAQGQEwA0AAEBjhMBAAAAFWCpCwIAAAAA" +
               "ABAAAABUcmFuc2l0aW9uTnVtYmVyAQGKFwAuAEQATooXAAAHAwAAAAAH/////wEB/////wAAAAAEYIAK" +
               "AQAAAAEAFgAAAEZyb21QbGFubmVkVG9FeGVjdXRpbmcBAZETAC8BAAYJkRMAAAIAAAAANAABAY8TADMA" +
               "AQGOEwEAAAAVYKkLAgAAAAAAEAAAAFRyYW5zaXRpb25OdW1iZXIBAYgXAC4ARABOiBcAAAcBAAAAAAf/" +
               "////AQH/////AAAAAARggAoBAAAAAQAHAAAAUGxhbm5lZAEBjhMALwEABQmOEwAAAgAAAAA0AQEBkxMA" +
               "MwEBAZETAQAAABVgqQsCAAAAAAALAAAAU3RhdGVOdW1iZXIBAYUXAC4ARABOhRcAAAcBAAAAAAf/////" +
               "AQH/////AAAAACRggAIBAAAAAQAGAAAAQXNzZXRzAQGKEwMAAAAAHgAAAEVudHJ5IHBvaW50IHRvIGRp" +
               "c2NvdmVyIGFzc2V0cwEAoFuKEwAAAQAAAAAjAQEArlsBAAAABGGCCgQAAAAAAAkAAABGaW5kQWxpYXMB" +
               "AVkbAC8BAKZbWRsAAAEB/////wIAAAAXYKkKAgAAAAAADgAAAElucHV0QXJndW1lbnRzAQFxFwAuAERx" +
               "FwAAlgIAAAABACoBASUAAAAWAAAAQWxpYXNOYW1lU2VhcmNoUGF0dGVybgAM/////wAAAAAAAQAqAQEi" +
               "AAAAEwAAAFJlZmVyZW5jZVR5cGVGaWx0ZXIAEf////8AAAAAAAEAKAEBAAAAAQAAAAIAAAABAf////8A" +
               "AAAAF2CpCgIAAAAAAA8AAABPdXRwdXRBcmd1bWVudHMBAXIXAC4ARHIXAACWAQAAAAEAKgEBIgAAAA0A" +
               "AABBbGlhc05vZGVMaXN0AQCsWwEAAAABAAAAAAAAAAABACgBAQAAAAEAAAABAAAAAQH/////AAAAACRg" +
               "gAIBAAAAAQAPAAAAQXNzZXRzQnlBc3NldElkAQGMEwMAAAAAKQAAAEVudHJ5IHBvaW50IHRvIGRpc2Nv" +
               "dmVyIGFzc2V0cyBieSBBc3NldElkAQCgW4wTAAABAAAAACMBAQGKEwIAAAAEYYIKBAAAAAAACQAAAEZp" +
               "bmRBbGlhcwEBWxsALwEApltbGwAAAQH/////AgAAABdgqQoCAAAAAAAOAAAASW5wdXRBcmd1bWVudHMB" +
               "AXYXAC4ARHYXAACWAgAAAAEAKgEBJQAAABYAAABBbGlhc05hbWVTZWFyY2hQYXR0ZXJuAAz/////AAAA" +
               "AAABACoBASIAAAATAAAAUmVmZXJlbmNlVHlwZUZpbHRlcgAR/////wAAAAAAAQAoAQEAAAABAAAAAgAA" +
               "AAEB/////wAAAAAXYKkKAgAAAAAADwAAAE91dHB1dEFyZ3VtZW50cwEBdxcALgBEdxcAAJYBAAAAAQAq" +
               "AQEiAAAADQAAAEFsaWFzTm9kZUxpc3QBAKxbAQAAAAEAAAAAAAAAAAEAKAEBAAAAAQAAAAEAAAABAf//" +
               "//8AAAAAFWCJCgIAAAAAAAsAAABOb2RlVmVyc2lvbgEBeBcALgBEeBcAAAAM/////wEB/////wAAAAAk" +
               "YIACAQAAAAEAGgAAAEFzc2V0c0J5UHJvZHVjdEluc3RhbmNlVXJpAQGLEwMAAAAANAAAAEVudHJ5IHBv" +
               "aW50IHRvIGRpc2NvdmVyIGFzc2V0cyBieSBQcm9kdWN0SW5zdGFuY2VVcmkBAKBbixMAAAEAAAAAIwEB" +
               "AYoTAgAAAARhggoEAAAAAAAJAAAARmluZEFsaWFzAQFaGwAvAQCmW1obAAABAf////8CAAAAF2CpCgIA" +
               "AAAAAA4AAABJbnB1dEFyZ3VtZW50cwEBcxcALgBEcxcAAJYCAAAAAQAqAQElAAAAFgAAAEFsaWFzTmFt" +
               "ZVNlYXJjaFBhdHRlcm4ADP////8AAAAAAAEAKgEBIgAAABMAAABSZWZlcmVuY2VUeXBlRmlsdGVyABH/" +
               "////AAAAAAABACgBAQAAAAEAAAACAAAAAQH/////AAAAABdgqQoCAAAAAAAPAAAAT3V0cHV0QXJndW1l" +
               "bnRzAQF0FwAuAER0FwAAlgEAAAABACoBASIAAAANAAAAQWxpYXNOb2RlTGlzdAEArFsBAAAAAQAAAAAA" +
               "AAAAAQAoAQEAAAABAAAAAQAAAAEB/////wAAAAAVYIkKAgAAAAAACwAAAE5vZGVWZXJzaW9uAQF1FwAu" +
               "AER1FwAAAAz/////AQH/////AAAAACRggAIBAAAAAQAVAAAASGllcmFyY2hpY2FsTG9jYXRpb25zAQGd" +
               "EwMAAAAARQAAAEVudHJ5IHBvaW50IGZvciBvYmplY3RzIHJlcHJlc2VudGluZyB0aGUgcm9vdCBvZiBh" +
               "IGxvY2F0aW9uIGhpZXJhcmNoeQA9nRMAAAEAAAAAIwEBAKt8AAAAACRggAIBAAAAAQAUAAAAT3BlcmF0" +
               "aW9uYWxMb2NhdGlvbnMBAZ4TAwAAAABVAAAARW50cnkgcG9pbnQgZm9yIG9iamVjdHMgcmVwcmVzZW50" +
               "aW5nIHRoZSByb290IG9mIGEgaGllcmFyY2h5IG9mIG9wZXJhdGlvbmFsIGxvY2F0aW9ucwA9nhMAAAEA" +
               "AAAAIwEBAKt8AAAAAARgwAIBAAAADQAAAERlZmF1bHRCaW5hcnkAAA4AAABEZWZhdWx0IEJpbmFyeQEB" +
               "iRMATIkTAAACAAAAACYBAQG6CwAnAAEBfRcAAAAABGDAAgEAAAAKAAAARGVmYXVsdFhtbAAACwAAAERl" +
               "ZmF1bHQgWE1MAQGNEwBMjRMAAAIAAAAAJgEBAboLACcAAQF+FwAAAAAEYMACAQAAAA0AAABEZWZhdWx0" +
               "QmluYXJ5AAAOAAAARGVmYXVsdCBCaW5hcnkBAZQTAEyUEwAAAgAAAAAmAQEBuwsAJwABAYsXAAAAAARg" +
               "wAIBAAAACgAAAERlZmF1bHRYbWwAAAsAAABEZWZhdWx0IFhNTAEBlRMATJUTAAACAAAAACYBAQG7CwAn" +
               "AAEBjBcAAAAA"
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