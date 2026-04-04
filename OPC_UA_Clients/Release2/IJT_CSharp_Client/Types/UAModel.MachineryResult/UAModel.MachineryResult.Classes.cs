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
using System.Collections.Generic;
using System.Text;
using System.Xml;
using System.Linq;
using System.Runtime.Serialization;
using System.Threading.Tasks;
using System.Threading;
using Opc.Ua;

#pragma warning disable CS1591 // Missing XML comment for publicly visible type or member
#pragma warning disable CA1515 // Consider making public types internal
#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1028 // Enum Storage should be Int32

namespace UAModel.MachineryResult
{
    #region ResultTypeState Class
    #if (!OPCUA_EXCLUDE_ResultTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class ResultTypeState : BaseDataVariableState<UAModel.MachineryResult.ResultDataType>
    {
        #region Constructors
        public ResultTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.MachineryResult.VariableTypes.ResultType, UAModel.MachineryResult.Namespaces.MachineryResult, namespaceUris);
        }

        protected override NodeId GetDefaultDataTypeId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.MachineryResult.DataTypes.ResultDataType, UAModel.MachineryResult.Namespaces.MachineryResult, namespaceUris);
        }

        protected override int GetDefaultValueRank()
        {
            return ValueRanks.Scalar;
        }

        #if (!OPCUA_EXCLUDE_InitializationStrings)
        protected override void Initialize(ISystemContext context)
        {
            base.Initialize(context);
            Initialize(context, InitializationString);
            InitializeOptionalChildren(context);
        }

        protected override void Initialize(ISystemContext context, NodeState source)
        {
            InitializeOptionalChildren(context);
            base.Initialize(context, source);
        }

        protected override void InitializeOptionalChildren(ISystemContext context)
        {
            base.InitializeOptionalChildren(context);

            if (ReducedResultContent != null)
            {
                ReducedResultContent.Initialize(context, ReducedResultContent_InitializationString);
            }

            if (ResultContent != null)
            {
                ResultContent.Initialize(context, ResultContent_InitializationString);
            }
        }

        #region Initialization String
        private const string ReducedResultContent_InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////F2CJ" +
           "CgIAAAABABQAAABSZWR1Y2VkUmVzdWx0Q29udGVudAEBexcALwA/excAAAAYAQAAAAEAAAAAAAAAAwP/" +
           "////AAAAAA==";

        private const string ResultContent_InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////F2CJ" +
           "CgIAAAABAA0AAABSZXN1bHRDb250ZW50AQF6FwEASF4AP3oXAAAAGAEAAAABAAAAAAAAAAEB/////wAA" +
           "AAA=";

        private const string InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////FWCp" +
           "AgIAAAABABIAAABSZXN1bHRUeXBlSW5zdGFuY2UBAdEHAQHRB9EHAAAWAQGREwLbAQAAPFJlc3VsdERh" +
           "dGFUeXBlIHhtbG5zPSJodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC9U" +
           "eXBlcy54c2QiPjxSZXN1bHRNZXRhRGF0YT48VHlwZUlkIHhtbG5zPSJodHRwOi8vb3BjZm91bmRhdGlv" +
           "bi5vcmcvVUEvMjAwOC8wMi9UeXBlcy54c2QiPjxJZGVudGlmaWVyPm5zPTE7aT01MDA2PC9JZGVudGlm" +
           "aWVyPjwvVHlwZUlkPjxCb2R5IHhtbG5zPSJodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvMjAwOC8w" +
           "Mi9UeXBlcy54c2QiPjxSZXN1bHRNZXRhRGF0YVR5cGUgeG1sbnM9Imh0dHA6Ly9vcGNmb3VuZGF0aW9u" +
           "Lm9yZy9VQS9NYWNoaW5lcnkvUmVzdWx0L1R5cGVzLnhzZCI+PEVuY29kaW5nTWFzaz4wPC9FbmNvZGlu" +
           "Z01hc2s+PFJlc3VsdElkPjwvUmVzdWx0SWQ+PC9SZXN1bHRNZXRhRGF0YVR5cGU+PC9Cb2R5PjwvUmVz" +
           "dWx0TWV0YURhdGE+PFJlc3VsdENvbnRlbnQgLz48L1Jlc3VsdERhdGFUeXBlPgEBwAv/////AQH/////" +
           "AwAAABdgiQoCAAAAAQAUAAAAUmVkdWNlZFJlc3VsdENvbnRlbnQBAXsXAC8AP3sXAAAAGAEAAAABAAAA" +
           "AAAAAAMD/////wAAAAAXYIkKAgAAAAEADQAAAFJlc3VsdENvbnRlbnQBAXoXAQBIXgA/ehcAAAAYAQAA" +
           "AAEAAAAAAAAAAQH/////AAAAABVgiQoCAAAAAQAOAAAAUmVzdWx0TWV0YURhdGEBAXkXAQBIXgA/eRcA" +
           "AAEBvwv/////AQH/////FAAAADVgiQoCAAAAAQAMAAAAQ3JlYXRpb25UaW1lAQGJFwMAAAAAwAAAAENy" +
           "ZWF0aW9uVGltZSBpbmRpY2F0ZXMgdGhlIHRpbWUgd2hlbiB0aGUgcmVzdWx0IHdhcyBjcmVhdGVkLiBD" +
           "cmVhdGlvbiB0aW1lIG9uIHRoZSBtZWFzdXJlbWVudCBzeXN0ZW0gKG5vdCB0aGUgcmVjZWl2ZSB0aW1l" +
           "IG9mIHRoZSBzZXJ2ZXIpLgpJdCBpcyByZWNvbW1lbmRlZCB0byBhbHdheXMgcHJvdmlkZSB0aGUgY3Jl" +
           "YXRpb25UaW1lLgEASF4AP4kXAAABACYB/////wMD/////wAAAAAVYKkKAgAAAAEAFwAAAEV4dGVybmFs" +
           "Q29uZmlndXJhdGlvbklkAQGGFwEASF4AP4YXAAAM8gAAAEV4dGVybmFsIElEIG9mIHRoZSBDb25maWd1" +
           "cmF0aW9uIGluIHVzZSB3aGlsZSB0aGUgcmVzdWx0IHdhcyBwcm9kdWNlZC4KSXQgaXMgbWFuYWdlZCBi" +
           "eSB0aGUgRW52aXJvbm1lbnQuClRoaXMgc3BlY2lmaWNhdGlvbiBkb2VzIG5vdCBkZWZpbmUgaG93IHRo" +
           "ZSBleHRlcm5hbENvbmZpZ3VyYXRpb25JZCBpcyB0cmFuc21pdHRlZCB0byB0aGUgc3lzdGVtLiBUeXBp" +
           "Y2FsbHksIGl0IGlzIHByb3ZpZGVkIGJ5IHRoZSBjbGllbnQuAQCufP////8DA/////8AAAAANWCJCgIA" +
           "AAABABAAAABFeHRlcm5hbFJlY2lwZUlkAQGDFwMAAAAA7QAAAEV4dGVybmFsIElEIG9mIHRoZSByZWNp" +
           "cGUgaW4gdXNlIHdoaWNoIHByb2R1Y2VkIHRoZSByZXN1bHQuIFRoZSBFeHRlcm5hbCBJRCBpcyBtYW5h" +
           "Z2VkIGJ5IHRoZSBlbnZpcm9ubWVudC4KVGhpcyBzcGVjaWZpY2F0aW9uIGRvZXMgbm90IGRlZmluZSBo" +
           "b3cgdGhlIGV4dGVybmFsUmVjaXBlSWQgaXMgdHJhbnNtaXR0ZWQgdG8gdGhlIHN5c3RlbS4gVHlwaWNh" +
           "bGx5LCBpdCBpcyBwcm92aWRlZCBieSB0aGUgY2xpZW50LgEASF4AP4MXAAABAK58/////wMD/////wAA" +
           "AAA3YIkKAgAAAAEACgAAAEZpbGVGb3JtYXQBAY8XAwAAAABEAQAAVGhlIGZvcm1hdCBpbiB3aGljaCB0" +
           "aGUgbWVhc3VyZW1lbnQgcmVzdWx0cyBhcmUgYXZhaWxhYmxlIChlLmcuIFFEQVMsIENTViwg4oCmKSB1" +
           "c2luZyB0aGUgUmVzdWx0VHJhbnNmZXIgT2JqZWN0LiBJZiBtdWx0aXBsZSBmaWxlIGZvcm1hdHMgYXJl" +
           "IHByb3ZpZGVkLCB0aGUgR2VuZXJhdGVGaWxlRm9yUmVhZCBvZiBSZXN1bHRUcmFuc2ZlciBzaG91bGQg" +
           "Y29udGFpbiBjb3JyZXNwb25kaW5nIHRyYW5zZmVyT3B0aW9ucywgdG8gc2VsZWN0IHRoZSBmaWxlIGZv" +
           "cm1hdC4gVGhpcyBzcGVjaWZpY2F0aW9uIGRvZXMgbm90IGRlZmluZSB0aG9zZSB0cmFuc2Zlck9wdGlv" +
           "bnMuAQBIXgA/jxcAAAAMAQAAAAEAAAAAAAAAAwP/////AAAAADVgiQoCAAAAAQAZAAAASGFzVHJhbnNm" +
           "ZXJhYmxlRGF0YU9uRmlsZQEBfRcDAAAAAJUAAABJbmRpY2F0ZXMgdGhhdCBhZGRpdGlvbmFsIGRhdGEg" +
           "Zm9yIHRoaXMgcmVzdWx0IGNhbiBiZSByZXRyaWV2ZWQgYnkgdGVtcG9yYXJ5IGZpbGUgdHJhbnNmZXIu" +
           "CklmIG5vdCBwcm92aWRlZCwgaXQgaXMgYXNzdW1lZCB0aGF0IG5vIGZpbGUgaXMgYXZhaWxhYmxlLgEA" +
           "SF4AP30XAAAAAf////8DA/////8AAAAANWCJCgIAAAABABcAAABJbnRlcm5hbENvbmZpZ3VyYXRpb25J" +
           "ZAEBhxcDAAAAAIYAAABJbnRlcm5hbCBJRCBvZiB0aGUgQ29uZmlndXJhdGlvbiBpbiB1c2Ugd2hpbGUg" +
           "dGhlIHJlc3VsdCB3YXMgcHJvZHVjZWQuIFRoaXMgSUQgaXMgc3lzdGVtLXdpZGUgdW5pcXVlIGFuZCBp" +
           "dCBpcyBhc3NpZ25lZCBieSB0aGUgc3lzdGVtLgEASF4AP4cXAAABAK58/////wMD/////wAAAAA1YIkK" +
           "AgAAAAEAEAAAAEludGVybmFsUmVjaXBlSWQBAYQXAwAAAAB7AAAASW50ZXJuYWwgSUQgb2YgdGhlIHJl" +
           "Y2lwZSBpbiB1c2Ugd2hpY2ggcHJvZHVjZWQgdGhlIHJlc3VsdC4gVGhpcyBJRCBpcyBzeXN0ZW0td2lk" +
           "ZSB1bmlxdWUgYW5kIGl0IGlzIGFzc2lnbmVkIGJ5IHRoZSBzeXN0ZW0uAQBIXgA/hBcAAAEArnz/////" +
           "AwP/////AAAAADVgiQoCAAAAAQAJAAAASXNQYXJ0aWFsAQF+FwMAAAAAuQAAAEluZGljYXRlcyB3aGV0" +
           "aGVyIHRoZSByZXN1bHQgaXMgdGhlIHBhcnRpYWwgcmVzdWx0IG9mIGEgdG90YWwgcmVzdWx0LiBXaGVu" +
           "IG5vdCBhbGwgc2FtcGxlcyBhcmUgZmluaXNoZWQgeWV0IHRoZSByZXN1bHQgaXMgJ3BhcnRpYWwnLgpJ" +
           "ZiBub3QgcHJvdmlkZWQsIGl0IGlzIGFzc3VtZWQgdG8gYmUgYSB0b3RhbCByZXN1bHQuAQBIXgA/fhcA" +
           "AAAB/////wMD/////wAAAAA1YIkKAgAAAAEACwAAAElzU2ltdWxhdGVkAQF/FwMAAAAA5gAAAEluZGlj" +
           "YXRlcyB3aGV0aGVyIHRoZSByZXN1bHQgd2FzIGNyZWF0ZWQgaW4gc2ltdWxhdGlvbiBtb2RlLgpTaW11" +
           "bGF0aW9uIG1vZGUgaW1wbGllcyB0aGF0IHRoZSByZXN1bHQgaXMgb25seSBnZW5lcmF0ZWQgZm9yIHRl" +
           "c3RpbmcgcHVycG9zZXMgYW5kIG5vdCBiYXNlZCBvbiByZWFsIHByb2R1Y3Rpb24gZGF0YS4KSWYgbm90" +
           "IHByb3ZpZGVkLCBpdCBpcyBhc3N1bWVkIHRvIG5vdCBiZSBzaW11bGF0ZWQuAQBIXgA/fxcAAAAB////" +
           "/wMD/////wAAAAA1YIkKAgAAAAEABQAAAEpvYklkAQGIFwMAAAAAbQAAAElkZW50aWZpZXMgdGhlIGpv" +
           "YiB3aGljaCBwcm9kdWNlZCB0aGUgcmVzdWx0LgpUaGlzIElEIGlzIHN5c3RlbS13aWRlIHVuaXF1ZSBh" +
           "bmQgaXQgaXMgYXNzaWduZWQgYnkgdGhlIHN5c3RlbS4BAEheAD+IFwAAAQCufP////8DA/////8AAAAA" +
           "NWCJCgIAAAABAAYAAABQYXJ0SWQBAYIXAwAAAABqAQAASWRlbnRpZmllcyB0aGUgcGFydCB1c2VkIHRv" +
           "IHByb2R1Y2UgdGhlIHJlc3VsdC4KQWx0aG91Z2ggdGhlIHN5c3RlbS13aWRlIHVuaXF1ZSBKb2JJZCB3" +
           "b3VsZCBiZSBzdWZmaWNpZW50IHRvIGlkZW50aWZ5IHRoZSBqb2Igd2hpY2ggdGhlIHJlc3VsdCBiZWxv" +
           "bmdzIHRvLCB0aGlzIG1ha2VzIGZvciBlYXNpZXIgZmlsdGVyaW5nIHdpdGhvdXQga2VlcGluZyB0cmFj" +
           "ayBvZiBKb2JJZHMuClRoaXMgc3BlY2lmaWNhdGlvbiBkb2VzIG5vdCBkZWZpbmUgaG93IHRoZSBwYXJ0" +
           "SWQgaXMgdHJhbnNtaXR0ZWQgdG8gdGhlIHN5c3RlbS4gVHlwaWNhbGx5LCBpdCBpcyBwcm92aWRlZCBi" +
           "eSB0aGUgY2xpZW50IHdoZW4gc3RhcnRpbmcgdGhlIGpvYi4BAEheAD+CFwAAAQCufP////8DA/////8A" +
           "AAAANWCpCgIAAAABAA8AAABQcm9jZXNzaW5nVGltZXMBAYoXAwAAAABPAAAAQ29sbGVjdGlvbiBvZiBk" +
           "aWZmZXJlbnQgcHJvY2Vzc2luZyB0aW1lcyB0aGF0IHdlcmUgbmVlZGVkIHRvIGNyZWF0ZSB0aGUgcmVz" +
           "dWx0LgEASF4AP4oXAAAWAQGMEwLiAAAAPFByb2Nlc3NpbmdUaW1lc0RhdGFUeXBlIHhtbG5zPSJodHRw" +
           "Oi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC9UeXBlcy54c2QiPjxFbmNvZGlu" +
           "Z01hc2s+MDwvRW5jb2RpbmdNYXNrPjxTdGFydFRpbWU+MTkwMC0wMS0wMVQwMDowMDowMFo8L1N0YXJ0" +
           "VGltZT48RW5kVGltZT4xOTAwLTAxLTAxVDAwOjAwOjAwWjwvRW5kVGltZT48L1Byb2Nlc3NpbmdUaW1l" +
           "c0RhdGFUeXBlPgEBvgv/////AwP/////AAAAABVgqQoCAAAAAQAJAAAAUHJvZHVjdElkAQGFFwEASF4A" +
           "P4UXAAAMtQAAAElkZW50aWZpZXMgdGhlIHByb2R1Y3QgdXNlZCB0byBwcm9kdWNlIHRoZSByZXN1bHQu" +
           "ClRoaXMgc3BlY2lmaWNhdGlvbiBkb2VzIG5vdCBkZWZpbmUgaG93IHRoZSBleHRlcm5hbFJlY2lwZUlk" +
           "IGlzIHRyYW5zbWl0dGVkIHRvIHRoZSBzeXN0ZW0uIFR5cGljYWxseSwgaXQgaXMgcHJvdmlkZWQgYnkg" +
           "dGhlIGNsaWVudC4BAK58/////wMD/////wAAAAA1YIkKAgAAAAEAEAAAAFJlc3VsdEV2YWx1YXRpb24B" +
           "AYwXAwAAAABDAAAAVGhlIFJlc3VsdEV2YWx1YXRpb24gaW5kaWNhdGVzIHdoZXRoZXIgdGhlIHJlc3Vs" +
           "dCB3YXMgaW4gdG9sZXJhbmNlLgEASF4AP4wXAAABAboL/////wMD/////wAAAAA1YKkKAgAAAAEAFAAA" +
           "AFJlc3VsdEV2YWx1YXRpb25Db2RlAQGOFwMAAAAAQQAAAFZlbmRvci1zcGVjaWZpYyBjb2RlIGRlc2Ny" +
           "aWJpbmcgbW9yZSBkZXRhaWxzIG9uIHJlc3VsdEV2YWx1YXRpb24uAQBIXgA/jhcAAAgAAAAAAAAAAAAI" +
           "/////wMD/////wAAAAA1YIkKAgAAAAEAFwAAAFJlc3VsdEV2YWx1YXRpb25EZXRhaWxzAQGNFwMAAAAA" +
           "kAAAAFRoZSBvcHRpb25hbCBFdmFsdWF0aW9uRGV0YWlscyBwcm92aWRlcyBoaWdoIGxldmVsIHN0YXR1" +
           "cyBpbmZvcm1hdGlvbiBpbiBhIHVzZXItZnJpZW5kbHkgdGV4dC4gVGhpcyBjYW4gYmUgbGVmdCBlbXB0" +
           "eSBmb3Igc3VjY2Vzc2Z1bCBvcGVyYXRpb25zLgEASF4AP40XAAAAFf////8DA/////8AAAAANWCJCgIA" +
           "AAABAAgAAABSZXN1bHRJZAEBfBcDAAAAACIBAABTeXN0ZW0td2lkZSB1bmlxdWUgaWRlbnRpZmllciwg" +
           "d2hpY2ggaXMgYXNzaWduZWQgYnkgdGhlIHN5c3RlbS4gVGhpcyBJRCBjYW4gYmUgdXNlZCBmb3IgZmV0" +
           "Y2hpbmcgZXhhY3RseSB0aGlzIHJlc3VsdCB1c2luZyB0aGUgbWV0aG9kIEdldFJlc3VsdEJ5SWQgYW5k" +
           "IGl0IGlzIGlkZW50aWNhbCB0byB0aGUgUmVzdWx0SWQgb2YgdGhlIFJlc3VsdFJlYWR5RXZlbnRUeXBl" +
           "LgpJZiB0aGUgc3lzdGVtIGRvZXMgbm90IG1hbmFnZSByZXN1bHRJZHMsIGl0IHNob3VsZCBhbHdheXMg" +
           "YmUgc2V0IHRvIOKAnE5B4oCdLgEASF4AP3wXAAABAK58/////wMD/////wAAAAA1YIkKAgAAAAEACwAA" +
           "AFJlc3VsdFN0YXRlAQGAFwMAAAAA7wEAAFJlc3VsdFN0YXRlIHByb3ZpZGVzIGluZm9ybWF0aW9uIGFi" +
           "b3V0IHRoZSBjdXJyZW50IHN0YXRlIG9mIHRoZSBwcm9jZXNzIG9yIG1lYXN1cmVtZW50IGNyZWF0aW5n" +
           "IGEgcmVzdWx0LgpBcHBsaWNhdGlvbnMgbWF5IHVzZSBuZWdhdGl2ZSB2YWx1ZXMgZm9yIGFwcGxpY2F0" +
           "aW9uLXNwZWNpZmljIHN0YXRlcy4gQWxsIG90aGVyIHZhbHVlcyBzaGFsbCBvbmx5IGJlIHVzZWQgYXMg" +
           "ZGVmaW5lZCBpbiB0aGUgZm9sbG93aW5nOgowIOKAkyBVbmRlZmluZWQgaW5pdGlhbCB2YWx1ZQoxIOKA" +
           "kyBDb21wbGV0ZWQ6IFByb2Nlc3Npbmcgd2FzIGNhcnJpZWQgb3V0IGNvbXBsZXRlbHkKMiDigJMgUHJv" +
           "Y2Vzc2luZzogUHJvY2Vzc2luZyBoYXMgbm90IGJlZW4gZmluaXNoZWQgeWV0CjMg4oCTIEFib3J0ZWQ6" +
           "IFByb2Nlc3Npbmcgd2FzIHN0b3BwZWQgYXQgc29tZSBwb2ludCBiZWZvcmUgY29tcGxldGlvbgo0IOKA" +
           "kyBGYWlsZWQ6IFByb2Nlc3NpbmcgZmFpbGVkIGluIHNvbWUgd2F5LgEASF4AP4AXAAAABv////8DA///" +
           "//8AAAAAN2CJCgIAAAABAAkAAABSZXN1bHRVcmkBAYsXAwAAAABDAAAAUGF0aCB0byB0aGUgYWN0dWFs" +
           "IG1lYXN1cmVkIHJlc3VsdCwgbWFuYWdlZCBleHRlcm5hbCB0byB0aGUgc2VydmVyLgEASF4AP4sXAAAB" +
           "AMdcAQAAAAEAAAAAAAAAAwP/////AAAAADVgiQoCAAAAAQAGAAAAU3RlcElkAQGBFwMAAAAAbgEAAElk" +
           "ZW50aWZpZXMgdGhlIHN0ZXAgd2hpY2ggcHJvZHVjZWQgdGhlIHJlc3VsdC4KQWx0aG91Z2ggdGhlIHN5" +
           "c3RlbS13aWRlIHVuaXF1ZSBKb2JJZCB3b3VsZCBiZSBzdWZmaWNpZW50IHRvIGlkZW50aWZ5IHRoZSBq" +
           "b2Igd2hpY2ggdGhlIHJlc3VsdCBiZWxvbmdzIHRvLCB0aGlzIG1ha2VzIGZvciBlYXNpZXIgZmlsdGVy" +
           "aW5nIHdpdGhvdXQga2VlcGluZyB0cmFjayBvZiBKb2JJZHMuClRoaXMgc3BlY2lmaWNhdGlvbiBkb2Vz" +
           "IG5vdCBkZWZpbmUgaG93IHRoZSBzdGVwSWQgaXMgdHJhbnNtaXR0ZWQgdG8gdGhlIHN5c3RlbS4gVHlw" +
           "aWNhbGx5LCBpdCBpcyBwcm92aWRlZCBieSB0aGUgY2xpZW50IHdoZW4gc3RhcnRpbmcgYW4gZXhlY3V0" +
           "aW9uLgEASF4AP4EXAAABAK58/////wMD/////wAAAAA=";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public BaseDataVariableState<object[]> ReducedResultContent
        {
            get => m_reducedResultContent;

            set
            {
                if (!Object.ReferenceEquals(m_reducedResultContent, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_reducedResultContent = value;
            }
        }

        public BaseDataVariableState<object[]> ResultContent
        {
            get => m_resultContent;

            set
            {
                if (!Object.ReferenceEquals(m_resultContent, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_resultContent = value;
            }
        }

        public BaseDataVariableState<ResultMetaDataType> ResultMetaData
        {
            get => m_resultMetaData;

            set
            {
                if (!Object.ReferenceEquals(m_resultMetaData, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_resultMetaData = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_reducedResultContent != null)
            {
                children.Add(m_reducedResultContent);
            }

            if (m_resultContent != null)
            {
                children.Add(m_resultContent);
            }

            if (m_resultMetaData != null)
            {
                children.Add(m_resultMetaData);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_reducedResultContent, child))
            {
                m_reducedResultContent = null;
                return;
            }

            if (Object.ReferenceEquals(m_resultContent, child))
            {
                m_resultContent = null;
                return;
            }

            if (Object.ReferenceEquals(m_resultMetaData, child))
            {
                m_resultMetaData = null;
                return;
            }

            base.RemoveExplicitlyDefinedChild(child);
        }

        protected override BaseInstanceState FindChild(
            ISystemContext context,
            QualifiedName browseName,
            bool createOrReplace,
            BaseInstanceState replacement)
        {
            if (QualifiedName.IsNull(browseName))
            {
                return null;
            }

            BaseInstanceState instance = null;

            switch (browseName.Name)
            {
                case UAModel.MachineryResult.BrowseNames.ReducedResultContent:
                {
                    if (createOrReplace)
                    {
                        if (ReducedResultContent == null)
                        {
                            if (replacement == null)
                            {
                                ReducedResultContent = new BaseDataVariableState<object[]>(this);
                            }
                            else
                            {
                                ReducedResultContent = (BaseDataVariableState<object[]>)replacement;
                            }
                        }
                    }

                    instance = ReducedResultContent;
                    break;
                }

                case UAModel.MachineryResult.BrowseNames.ResultContent:
                {
                    if (createOrReplace)
                    {
                        if (ResultContent == null)
                        {
                            if (replacement == null)
                            {
                                ResultContent = new BaseDataVariableState<object[]>(this);
                            }
                            else
                            {
                                ResultContent = (BaseDataVariableState<object[]>)replacement;
                            }
                        }
                    }

                    instance = ResultContent;
                    break;
                }

                case UAModel.MachineryResult.BrowseNames.ResultMetaData:
                {
                    if (createOrReplace)
                    {
                        if (ResultMetaData == null)
                        {
                            if (replacement == null)
                            {
                                ResultMetaData = new BaseDataVariableState<ResultMetaDataType>(this);
                            }
                            else
                            {
                                ResultMetaData = (BaseDataVariableState<ResultMetaDataType>)replacement;
                            }
                        }
                    }

                    instance = ResultMetaData;
                    break;
                }
            }

            if (instance != null)
            {
                return instance;
            }

            return base.FindChild(context, browseName, createOrReplace, replacement);
        }
        #endregion

        #region Private Fields
        private BaseDataVariableState<object[]> m_reducedResultContent;
        private BaseDataVariableState<object[]> m_resultContent;
        private BaseDataVariableState<ResultMetaDataType> m_resultMetaData;
        #endregion
    }

    #region ResultTypeValue Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public class ResultTypeValue : BaseVariableValue
    {
        #region Constructors
        public ResultTypeValue(ResultTypeState variable, ResultDataType value, object dataLock) : base(dataLock)
        {
            m_value = value;

            if (m_value == null)
            {
                m_value = new ResultDataType();
            }

            Initialize(variable);
        }
        #endregion

        #region Public Members
        public ResultTypeState Variable
        {
            get { return m_variable; }
        }

        public ResultDataType Value
        {
            get { return m_value; }
            set { m_value = value; }
        }
        #endregion

        #region Private Methods
        private void Initialize(ResultTypeState variable)
        {
            lock (Lock)
            {
                m_variable = variable;

                variable.Value = m_value;

                variable.OnReadValue = OnReadValue;
                variable.OnWriteValue = OnWriteValue;

                BaseVariableState instance = null;
                List<BaseInstanceState> updateList = new List<BaseInstanceState>();
                updateList.Add(variable);

                instance = m_variable.ResultMetaData;
                if (instance != null)
                {
                    instance.OnReadValue = OnRead_ResultMetaData;
                    instance.OnWriteValue = OnWrite_ResultMetaData;
                    updateList.Add(instance);
                }
                instance = m_variable.ResultContent;
                if (instance != null)
                {
                    instance.OnReadValue = OnRead_ResultContent;
                    instance.OnWriteValue = OnWrite_ResultContent;
                    updateList.Add(instance);
                }

                SetUpdateList(updateList);
            }
        }

        protected ServiceResult OnReadValue(
            ISystemContext context,
            NodeState node,
            NumericRange indexRange,
            QualifiedName dataEncoding,
            ref object value,
            ref StatusCode statusCode,
            ref DateTime timestamp)
        {
            lock (Lock)
            {
                DoBeforeReadProcessing(context, node);

                if (m_value != null)
                {
                    value = m_value;
                }

                return Read(context, node, indexRange, dataEncoding, ref value, ref statusCode, ref timestamp);
            }
        }

        private ServiceResult OnWriteValue(
            ISystemContext context,
            NodeState node,
            NumericRange indexRange,
            QualifiedName dataEncoding,
            ref object value,
            ref StatusCode statusCode,
            ref DateTime timestamp)
        {
            lock (Lock)
            {
                ResultDataType newValue;
                if (value is ExtensionObject extensionObject)
                {
                    newValue = (ResultDataType)extensionObject.Body;
                }
                else
                {
                    newValue = (ResultDataType)value;
                }

                if (!Utils.IsEqual(m_value, newValue))
                {
                    UpdateChildrenChangeMasks(context, ref newValue, ref statusCode, ref timestamp);
                    Timestamp = timestamp;
                    m_value = (ResultDataType)Write(newValue);
                    m_variable.UpdateChangeMasks(NodeStateChangeMasks.Value);
                }
            }

            return ServiceResult.Good;
        }

        private void UpdateChildrenChangeMasks(ISystemContext context, ref ResultDataType newValue, ref StatusCode statusCode, ref DateTime timestamp)
        {
            if (!Utils.IsEqual(m_value.ResultMetaData, newValue.ResultMetaData)) UpdateChildVariableStatus(m_variable.ResultMetaData, ref statusCode, ref timestamp);
            if (!Utils.IsEqual(m_value.ResultContent, newValue.ResultContent)) UpdateChildVariableStatus(m_variable.ResultContent, ref statusCode, ref timestamp);
        }

        private void UpdateParent(ISystemContext context, ref StatusCode statusCode, ref DateTime timestamp)
        {
            Timestamp = timestamp;
            m_variable.UpdateChangeMasks(NodeStateChangeMasks.Value);
            m_variable.ClearChangeMasks(context, false);
        }

        private void UpdateChildVariableStatus(BaseVariableState child, ref StatusCode statusCode, ref DateTime timestamp)
        {
            if (child == null) return;
            child.StatusCode = statusCode;
            if (timestamp == DateTime.MinValue)
            {
                timestamp = DateTime.UtcNow;
            }
            child.Timestamp = timestamp;
        }

        #region ResultMetaData Access Methods
        private ServiceResult OnRead_ResultMetaData(
            ISystemContext context,
            NodeState node,
            NumericRange indexRange,
            QualifiedName dataEncoding,
            ref object value,
            ref StatusCode statusCode,
            ref DateTime timestamp)
        {
            lock (Lock)
            {
                DoBeforeReadProcessing(context, node);

                var childVariable = m_variable?.ResultMetaData;
                if (childVariable != null && StatusCode.IsBad(childVariable.StatusCode))
                {
                    value = null;
                    statusCode = childVariable.StatusCode;
                    return new ServiceResult(statusCode);
                }

                if (m_value != null)
                {
                    value = m_value.ResultMetaData;
                }

                var result = Read(context, node, indexRange, dataEncoding, ref value, ref statusCode, ref timestamp);

                if (childVariable != null && ServiceResult.IsNotBad(result))
                {
                    timestamp = childVariable.Timestamp;
                    if (statusCode != childVariable.StatusCode)
                    {
                        statusCode = childVariable.StatusCode;
                        result = new ServiceResult(statusCode);
                    }
                }

                return result;
            }
        }

        private ServiceResult OnWrite_ResultMetaData(
            ISystemContext context,
            NodeState node,
            NumericRange indexRange,
            QualifiedName dataEncoding,
            ref object value,
            ref StatusCode statusCode,
            ref DateTime timestamp)
        {
            lock (Lock)
            {
                UpdateChildVariableStatus(m_variable.ResultMetaData, ref statusCode, ref timestamp);
                m_value.ResultMetaData = (ResultMetaDataType)Write(value);
                UpdateParent(context, ref statusCode, ref timestamp);
            }

            return ServiceResult.Good;
        }
        #endregion

        #region ResultContent Access Methods
        private ServiceResult OnRead_ResultContent(
            ISystemContext context,
            NodeState node,
            NumericRange indexRange,
            QualifiedName dataEncoding,
            ref object value,
            ref StatusCode statusCode,
            ref DateTime timestamp)
        {
            lock (Lock)
            {
                DoBeforeReadProcessing(context, node);

                var childVariable = m_variable?.ResultContent;
                if (childVariable != null && StatusCode.IsBad(childVariable.StatusCode))
                {
                    value = null;
                    statusCode = childVariable.StatusCode;
                    return new ServiceResult(statusCode);
                }

                if (m_value != null)
                {
                    value = m_value.ResultContent;
                }

                var result = Read(context, node, indexRange, dataEncoding, ref value, ref statusCode, ref timestamp);

                if (childVariable != null && ServiceResult.IsNotBad(result))
                {
                    timestamp = childVariable.Timestamp;
                    if (statusCode != childVariable.StatusCode)
                    {
                        statusCode = childVariable.StatusCode;
                        result = new ServiceResult(statusCode);
                    }
                }

                return result;
            }
        }

        private ServiceResult OnWrite_ResultContent(
            ISystemContext context,
            NodeState node,
            NumericRange indexRange,
            QualifiedName dataEncoding,
            ref object value,
            ref StatusCode statusCode,
            ref DateTime timestamp)
        {
            lock (Lock)
            {
                UpdateChildVariableStatus(m_variable.ResultContent, ref statusCode, ref timestamp);
                m_value.ResultContent = (VariantCollection)Write(value);
                UpdateParent(context, ref statusCode, ref timestamp);
            }

            return ServiceResult.Good;
        }
        #endregion
        #endregion

        #region Private Fields
        private ResultDataType m_value;
        private ResultTypeState m_variable;
        #endregion
    }
    #endregion
    #endif
    #endregion

    #region ResultReadyEventTypeState Class
    #if (!OPCUA_EXCLUDE_ResultReadyEventTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class ResultReadyEventTypeState : BaseEventState
    {
        #region Constructors
        public ResultReadyEventTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.MachineryResult.ObjectTypes.ResultReadyEventType, UAModel.MachineryResult.Namespaces.MachineryResult, namespaceUris);
        }

        #if (!OPCUA_EXCLUDE_InitializationStrings)
        protected override void Initialize(ISystemContext context)
        {
            base.Initialize(context);
            Initialize(context, InitializationString);
            InitializeOptionalChildren(context);
        }

        protected override void Initialize(ISystemContext context, NodeState source)
        {
            InitializeOptionalChildren(context);
            base.Initialize(context, source);
        }

        protected override void InitializeOptionalChildren(ISystemContext context)
        {
            base.InitializeOptionalChildren(context);
        }

        #region Initialization String
        private const string InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGCA" +
           "AgEAAAABABwAAABSZXN1bHRSZWFkeUV2ZW50VHlwZUluc3RhbmNlAQHqAwEB6gPqAwAAAQAAAAApAQEB" +
           "7AMJAAAAFWCJCAIAAAAAAAcAAABFdmVudElkAQEAAAAuAEQAD/////8BAf////8AAAAAFWCJCAIAAAAA" +
           "AAkAAABFdmVudFR5cGUBAQAAAC4ARAAR/////wEB/////wAAAAAVYIkIAgAAAAAACgAAAFNvdXJjZU5v" +
           "ZGUBAQAAAC4ARAAR/////wEB/////wAAAAAVYIkIAgAAAAAACgAAAFNvdXJjZU5hbWUBAQAAAC4ARAAM" +
           "/////wEB/////wAAAAAVYIkIAgAAAAAABAAAAFRpbWUBAQAAAC4ARAEAJgH/////AQH/////AAAAABVg" +
           "iQgCAAAAAAALAAAAUmVjZWl2ZVRpbWUBAQAAAC4ARAEAJgH/////AQH/////AAAAABVgiQgCAAAAAAAH" +
           "AAAATWVzc2FnZQEBAAAALgBEABX/////AQH/////AAAAABVgiQgCAAAAAAAIAAAAU2V2ZXJpdHkBAQAA" +
           "AC4ARAAF/////wEB/////wAAAAAVYKkKAgAAAAEABgAAAFJlc3VsdAEBkBcALwEB0QeQFwAAFgEBkRMC" +
           "2wEAADxSZXN1bHREYXRhVHlwZSB4bWxucz0iaHR0cDovL29wY2ZvdW5kYXRpb24ub3JnL1VBL01hY2hp" +
           "bmVyeS9SZXN1bHQvVHlwZXMueHNkIj48UmVzdWx0TWV0YURhdGE+PFR5cGVJZCB4bWxucz0iaHR0cDov" +
           "L29wY2ZvdW5kYXRpb24ub3JnL1VBLzIwMDgvMDIvVHlwZXMueHNkIj48SWRlbnRpZmllcj5ucz0xO2k9" +
           "NTAwNjwvSWRlbnRpZmllcj48L1R5cGVJZD48Qm9keSB4bWxucz0iaHR0cDovL29wY2ZvdW5kYXRpb24u" +
           "b3JnL1VBLzIwMDgvMDIvVHlwZXMueHNkIj48UmVzdWx0TWV0YURhdGFUeXBlIHhtbG5zPSJodHRwOi8v" +
           "b3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC9UeXBlcy54c2QiPjxFbmNvZGluZ01h" +
           "c2s+MDwvRW5jb2RpbmdNYXNrPjxSZXN1bHRJZD48L1Jlc3VsdElkPjwvUmVzdWx0TWV0YURhdGFUeXBl" +
           "PjwvQm9keT48L1Jlc3VsdE1ldGFEYXRhPjxSZXN1bHRDb250ZW50IC8+PC9SZXN1bHREYXRhVHlwZT4B" +
           "AcAL/////wMD/////wEAAAAVYIkKAgAAAAEADgAAAFJlc3VsdE1ldGFEYXRhAQGRFwEASF4AP5EXAAAB" +
           "Ab8L/////wEB/////xQAAAA1YIkKAgAAAAEADAAAAENyZWF0aW9uVGltZQEBqBcDAAAAAMAAAABDcmVh" +
           "dGlvblRpbWUgaW5kaWNhdGVzIHRoZSB0aW1lIHdoZW4gdGhlIHJlc3VsdCB3YXMgY3JlYXRlZC4gQ3Jl" +
           "YXRpb24gdGltZSBvbiB0aGUgbWVhc3VyZW1lbnQgc3lzdGVtIChub3QgdGhlIHJlY2VpdmUgdGltZSBv" +
           "ZiB0aGUgc2VydmVyKS4KSXQgaXMgcmVjb21tZW5kZWQgdG8gYWx3YXlzIHByb3ZpZGUgdGhlIGNyZWF0" +
           "aW9uVGltZS4BAEheAD+oFwAAAQAmAf////8DA/////8AAAAAFWCpCgIAAAABABcAAABFeHRlcm5hbENv" +
           "bmZpZ3VyYXRpb25JZAEBqRcBAEheAD+pFwAADPIAAABFeHRlcm5hbCBJRCBvZiB0aGUgQ29uZmlndXJh" +
           "dGlvbiBpbiB1c2Ugd2hpbGUgdGhlIHJlc3VsdCB3YXMgcHJvZHVjZWQuCkl0IGlzIG1hbmFnZWQgYnkg" +
           "dGhlIEVudmlyb25tZW50LgpUaGlzIHNwZWNpZmljYXRpb24gZG9lcyBub3QgZGVmaW5lIGhvdyB0aGUg" +
           "ZXh0ZXJuYWxDb25maWd1cmF0aW9uSWQgaXMgdHJhbnNtaXR0ZWQgdG8gdGhlIHN5c3RlbS4gVHlwaWNh" +
           "bGx5LCBpdCBpcyBwcm92aWRlZCBieSB0aGUgY2xpZW50LgEArnz/////AwP/////AAAAADVgiQoCAAAA" +
           "AQAQAAAARXh0ZXJuYWxSZWNpcGVJZAEBqhcDAAAAAO0AAABFeHRlcm5hbCBJRCBvZiB0aGUgcmVjaXBl" +
           "IGluIHVzZSB3aGljaCBwcm9kdWNlZCB0aGUgcmVzdWx0LiBUaGUgRXh0ZXJuYWwgSUQgaXMgbWFuYWdl" +
           "ZCBieSB0aGUgZW52aXJvbm1lbnQuClRoaXMgc3BlY2lmaWNhdGlvbiBkb2VzIG5vdCBkZWZpbmUgaG93" +
           "IHRoZSBleHRlcm5hbFJlY2lwZUlkIGlzIHRyYW5zbWl0dGVkIHRvIHRoZSBzeXN0ZW0uIFR5cGljYWxs" +
           "eSwgaXQgaXMgcHJvdmlkZWQgYnkgdGhlIGNsaWVudC4BAEheAD+qFwAAAQCufP////8DA/////8AAAAA" +
           "N2CJCgIAAAABAAoAAABGaWxlRm9ybWF0AQGrFwMAAAAARAEAAFRoZSBmb3JtYXQgaW4gd2hpY2ggdGhl" +
           "IG1lYXN1cmVtZW50IHJlc3VsdHMgYXJlIGF2YWlsYWJsZSAoZS5nLiBRREFTLCBDU1YsIOKApikgdXNp" +
           "bmcgdGhlIFJlc3VsdFRyYW5zZmVyIE9iamVjdC4gSWYgbXVsdGlwbGUgZmlsZSBmb3JtYXRzIGFyZSBw" +
           "cm92aWRlZCwgdGhlIEdlbmVyYXRlRmlsZUZvclJlYWQgb2YgUmVzdWx0VHJhbnNmZXIgc2hvdWxkIGNv" +
           "bnRhaW4gY29ycmVzcG9uZGluZyB0cmFuc2Zlck9wdGlvbnMsIHRvIHNlbGVjdCB0aGUgZmlsZSBmb3Jt" +
           "YXQuIFRoaXMgc3BlY2lmaWNhdGlvbiBkb2VzIG5vdCBkZWZpbmUgdGhvc2UgdHJhbnNmZXJPcHRpb25z" +
           "LgEASF4AP6sXAAAADAEAAAABAAAAAAAAAAMD/////wAAAAA1YIkKAgAAAAEAGQAAAEhhc1RyYW5zZmVy" +
           "YWJsZURhdGFPbkZpbGUBAawXAwAAAACVAAAASW5kaWNhdGVzIHRoYXQgYWRkaXRpb25hbCBkYXRhIGZv" +
           "ciB0aGlzIHJlc3VsdCBjYW4gYmUgcmV0cmlldmVkIGJ5IHRlbXBvcmFyeSBmaWxlIHRyYW5zZmVyLgpJ" +
           "ZiBub3QgcHJvdmlkZWQsIGl0IGlzIGFzc3VtZWQgdGhhdCBubyBmaWxlIGlzIGF2YWlsYWJsZS4BAEhe" +
           "AD+sFwAAAAH/////AwP/////AAAAADVgiQoCAAAAAQAXAAAASW50ZXJuYWxDb25maWd1cmF0aW9uSWQB" +
           "Aa0XAwAAAACGAAAASW50ZXJuYWwgSUQgb2YgdGhlIENvbmZpZ3VyYXRpb24gaW4gdXNlIHdoaWxlIHRo" +
           "ZSByZXN1bHQgd2FzIHByb2R1Y2VkLiBUaGlzIElEIGlzIHN5c3RlbS13aWRlIHVuaXF1ZSBhbmQgaXQg" +
           "aXMgYXNzaWduZWQgYnkgdGhlIHN5c3RlbS4BAEheAD+tFwAAAQCufP////8DA/////8AAAAANWCJCgIA" +
           "AAABABAAAABJbnRlcm5hbFJlY2lwZUlkAQGuFwMAAAAAewAAAEludGVybmFsIElEIG9mIHRoZSByZWNp" +
           "cGUgaW4gdXNlIHdoaWNoIHByb2R1Y2VkIHRoZSByZXN1bHQuIFRoaXMgSUQgaXMgc3lzdGVtLXdpZGUg" +
           "dW5pcXVlIGFuZCBpdCBpcyBhc3NpZ25lZCBieSB0aGUgc3lzdGVtLgEASF4AP64XAAABAK58/////wMD" +
           "/////wAAAAA1YIkKAgAAAAEACQAAAElzUGFydGlhbAEBrxcDAAAAALkAAABJbmRpY2F0ZXMgd2hldGhl" +
           "ciB0aGUgcmVzdWx0IGlzIHRoZSBwYXJ0aWFsIHJlc3VsdCBvZiBhIHRvdGFsIHJlc3VsdC4gV2hlbiBu" +
           "b3QgYWxsIHNhbXBsZXMgYXJlIGZpbmlzaGVkIHlldCB0aGUgcmVzdWx0IGlzICdwYXJ0aWFsJy4KSWYg" +
           "bm90IHByb3ZpZGVkLCBpdCBpcyBhc3N1bWVkIHRvIGJlIGEgdG90YWwgcmVzdWx0LgEASF4AP68XAAAA" +
           "Af////8DA/////8AAAAANWCJCgIAAAABAAsAAABJc1NpbXVsYXRlZAEBsBcDAAAAAOYAAABJbmRpY2F0" +
           "ZXMgd2hldGhlciB0aGUgcmVzdWx0IHdhcyBjcmVhdGVkIGluIHNpbXVsYXRpb24gbW9kZS4KU2ltdWxh" +
           "dGlvbiBtb2RlIGltcGxpZXMgdGhhdCB0aGUgcmVzdWx0IGlzIG9ubHkgZ2VuZXJhdGVkIGZvciB0ZXN0" +
           "aW5nIHB1cnBvc2VzIGFuZCBub3QgYmFzZWQgb24gcmVhbCBwcm9kdWN0aW9uIGRhdGEuCklmIG5vdCBw" +
           "cm92aWRlZCwgaXQgaXMgYXNzdW1lZCB0byBub3QgYmUgc2ltdWxhdGVkLgEASF4AP7AXAAAAAf////8D" +
           "A/////8AAAAANWCJCgIAAAABAAUAAABKb2JJZAEBsRcDAAAAAG0AAABJZGVudGlmaWVzIHRoZSBqb2Ig" +
           "d2hpY2ggcHJvZHVjZWQgdGhlIHJlc3VsdC4KVGhpcyBJRCBpcyBzeXN0ZW0td2lkZSB1bmlxdWUgYW5k" +
           "IGl0IGlzIGFzc2lnbmVkIGJ5IHRoZSBzeXN0ZW0uAQBIXgA/sRcAAAEArnz/////AwP/////AAAAADVg" +
           "iQoCAAAAAQAGAAAAUGFydElkAQGyFwMAAAAAagEAAElkZW50aWZpZXMgdGhlIHBhcnQgdXNlZCB0byBw" +
           "cm9kdWNlIHRoZSByZXN1bHQuCkFsdGhvdWdoIHRoZSBzeXN0ZW0td2lkZSB1bmlxdWUgSm9iSWQgd291" +
           "bGQgYmUgc3VmZmljaWVudCB0byBpZGVudGlmeSB0aGUgam9iIHdoaWNoIHRoZSByZXN1bHQgYmVsb25n" +
           "cyB0bywgdGhpcyBtYWtlcyBmb3IgZWFzaWVyIGZpbHRlcmluZyB3aXRob3V0IGtlZXBpbmcgdHJhY2sg" +
           "b2YgSm9iSWRzLgpUaGlzIHNwZWNpZmljYXRpb24gZG9lcyBub3QgZGVmaW5lIGhvdyB0aGUgcGFydElk" +
           "IGlzIHRyYW5zbWl0dGVkIHRvIHRoZSBzeXN0ZW0uIFR5cGljYWxseSwgaXQgaXMgcHJvdmlkZWQgYnkg" +
           "dGhlIGNsaWVudCB3aGVuIHN0YXJ0aW5nIHRoZSBqb2IuAQBIXgA/shcAAAEArnz/////AwP/////AAAA" +
           "ADVgqQoCAAAAAQAPAAAAUHJvY2Vzc2luZ1RpbWVzAQGzFwMAAAAATwAAAENvbGxlY3Rpb24gb2YgZGlm" +
           "ZmVyZW50IHByb2Nlc3NpbmcgdGltZXMgdGhhdCB3ZXJlIG5lZWRlZCB0byBjcmVhdGUgdGhlIHJlc3Vs" +
           "dC4BAEheAD+zFwAAFgEBjBMC4gAAADxQcm9jZXNzaW5nVGltZXNEYXRhVHlwZSB4bWxucz0iaHR0cDov" +
           "L29wY2ZvdW5kYXRpb24ub3JnL1VBL01hY2hpbmVyeS9SZXN1bHQvVHlwZXMueHNkIj48RW5jb2RpbmdN" +
           "YXNrPjA8L0VuY29kaW5nTWFzaz48U3RhcnRUaW1lPjE5MDAtMDEtMDFUMDA6MDA6MDBaPC9TdGFydFRp" +
           "bWU+PEVuZFRpbWU+MTkwMC0wMS0wMVQwMDowMDowMFo8L0VuZFRpbWU+PC9Qcm9jZXNzaW5nVGltZXNE" +
           "YXRhVHlwZT4BAb4L/////wMD/////wAAAAAVYKkKAgAAAAEACQAAAFByb2R1Y3RJZAEBtBcBAEheAD+0" +
           "FwAADLUAAABJZGVudGlmaWVzIHRoZSBwcm9kdWN0IHVzZWQgdG8gcHJvZHVjZSB0aGUgcmVzdWx0LgpU" +
           "aGlzIHNwZWNpZmljYXRpb24gZG9lcyBub3QgZGVmaW5lIGhvdyB0aGUgZXh0ZXJuYWxSZWNpcGVJZCBp" +
           "cyB0cmFuc21pdHRlZCB0byB0aGUgc3lzdGVtLiBUeXBpY2FsbHksIGl0IGlzIHByb3ZpZGVkIGJ5IHRo" +
           "ZSBjbGllbnQuAQCufP////8DA/////8AAAAANWCJCgIAAAABABAAAABSZXN1bHRFdmFsdWF0aW9uAQG1" +
           "FwMAAAAAQwAAAFRoZSBSZXN1bHRFdmFsdWF0aW9uIGluZGljYXRlcyB3aGV0aGVyIHRoZSByZXN1bHQg" +
           "d2FzIGluIHRvbGVyYW5jZS4BAEheAD+1FwAAAQG6C/////8DA/////8AAAAANWCpCgIAAAABABQAAABS" +
           "ZXN1bHRFdmFsdWF0aW9uQ29kZQEBthcDAAAAAEEAAABWZW5kb3Itc3BlY2lmaWMgY29kZSBkZXNjcmli" +
           "aW5nIG1vcmUgZGV0YWlscyBvbiByZXN1bHRFdmFsdWF0aW9uLgEASF4AP7YXAAAIAAAAAAAAAAAACP//" +
           "//8DA/////8AAAAANWCJCgIAAAABABcAAABSZXN1bHRFdmFsdWF0aW9uRGV0YWlscwEBtxcDAAAAAJAA" +
           "AABUaGUgb3B0aW9uYWwgRXZhbHVhdGlvbkRldGFpbHMgcHJvdmlkZXMgaGlnaCBsZXZlbCBzdGF0dXMg" +
           "aW5mb3JtYXRpb24gaW4gYSB1c2VyLWZyaWVuZGx5IHRleHQuIFRoaXMgY2FuIGJlIGxlZnQgZW1wdHkg" +
           "Zm9yIHN1Y2Nlc3NmdWwgb3BlcmF0aW9ucy4BAEheAD+3FwAAABX/////AwP/////AAAAADVgiQoCAAAA" +
           "AQAIAAAAUmVzdWx0SWQBAZIXAwAAAAAiAQAAU3lzdGVtLXdpZGUgdW5pcXVlIGlkZW50aWZpZXIsIHdo" +
           "aWNoIGlzIGFzc2lnbmVkIGJ5IHRoZSBzeXN0ZW0uIFRoaXMgSUQgY2FuIGJlIHVzZWQgZm9yIGZldGNo" +
           "aW5nIGV4YWN0bHkgdGhpcyByZXN1bHQgdXNpbmcgdGhlIG1ldGhvZCBHZXRSZXN1bHRCeUlkIGFuZCBp" +
           "dCBpcyBpZGVudGljYWwgdG8gdGhlIFJlc3VsdElkIG9mIHRoZSBSZXN1bHRSZWFkeUV2ZW50VHlwZS4K" +
           "SWYgdGhlIHN5c3RlbSBkb2VzIG5vdCBtYW5hZ2UgcmVzdWx0SWRzLCBpdCBzaG91bGQgYWx3YXlzIGJl" +
           "IHNldCB0byDigJxOQeKAnS4BAEheAD+SFwAAAQCufP////8DA/////8AAAAANWCJCgIAAAABAAsAAABS" +
           "ZXN1bHRTdGF0ZQEBuBcDAAAAAO8BAABSZXN1bHRTdGF0ZSBwcm92aWRlcyBpbmZvcm1hdGlvbiBhYm91" +
           "dCB0aGUgY3VycmVudCBzdGF0ZSBvZiB0aGUgcHJvY2VzcyBvciBtZWFzdXJlbWVudCBjcmVhdGluZyBh" +
           "IHJlc3VsdC4KQXBwbGljYXRpb25zIG1heSB1c2UgbmVnYXRpdmUgdmFsdWVzIGZvciBhcHBsaWNhdGlv" +
           "bi1zcGVjaWZpYyBzdGF0ZXMuIEFsbCBvdGhlciB2YWx1ZXMgc2hhbGwgb25seSBiZSB1c2VkIGFzIGRl" +
           "ZmluZWQgaW4gdGhlIGZvbGxvd2luZzoKMCDigJMgVW5kZWZpbmVkIGluaXRpYWwgdmFsdWUKMSDigJMg" +
           "Q29tcGxldGVkOiBQcm9jZXNzaW5nIHdhcyBjYXJyaWVkIG91dCBjb21wbGV0ZWx5CjIg4oCTIFByb2Nl" +
           "c3Npbmc6IFByb2Nlc3NpbmcgaGFzIG5vdCBiZWVuIGZpbmlzaGVkIHlldAozIOKAkyBBYm9ydGVkOiBQ" +
           "cm9jZXNzaW5nIHdhcyBzdG9wcGVkIGF0IHNvbWUgcG9pbnQgYmVmb3JlIGNvbXBsZXRpb24KNCDigJMg" +
           "RmFpbGVkOiBQcm9jZXNzaW5nIGZhaWxlZCBpbiBzb21lIHdheS4BAEheAD+4FwAAAAb/////AwP/////" +
           "AAAAADdgiQoCAAAAAQAJAAAAUmVzdWx0VXJpAQG5FwMAAAAAQwAAAFBhdGggdG8gdGhlIGFjdHVhbCBt" +
           "ZWFzdXJlZCByZXN1bHQsIG1hbmFnZWQgZXh0ZXJuYWwgdG8gdGhlIHNlcnZlci4BAEheAD+5FwAAAQDH" +
           "XAEAAAABAAAAAAAAAAMD/////wAAAAA1YIkKAgAAAAEABgAAAFN0ZXBJZAEBuhcDAAAAAG4BAABJZGVu" +
           "dGlmaWVzIHRoZSBzdGVwIHdoaWNoIHByb2R1Y2VkIHRoZSByZXN1bHQuCkFsdGhvdWdoIHRoZSBzeXN0" +
           "ZW0td2lkZSB1bmlxdWUgSm9iSWQgd291bGQgYmUgc3VmZmljaWVudCB0byBpZGVudGlmeSB0aGUgam9i" +
           "IHdoaWNoIHRoZSByZXN1bHQgYmVsb25ncyB0bywgdGhpcyBtYWtlcyBmb3IgZWFzaWVyIGZpbHRlcmlu" +
           "ZyB3aXRob3V0IGtlZXBpbmcgdHJhY2sgb2YgSm9iSWRzLgpUaGlzIHNwZWNpZmljYXRpb24gZG9lcyBu" +
           "b3QgZGVmaW5lIGhvdyB0aGUgc3RlcElkIGlzIHRyYW5zbWl0dGVkIHRvIHRoZSBzeXN0ZW0uIFR5cGlj" +
           "YWxseSwgaXQgaXMgcHJvdmlkZWQgYnkgdGhlIGNsaWVudCB3aGVuIHN0YXJ0aW5nIGFuIGV4ZWN1dGlv" +
           "bi4BAEheAD+6FwAAAQCufP////8DA/////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public ResultTypeState Result
        {
            get => m_result;

            set
            {
                if (!Object.ReferenceEquals(m_result, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_result = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_result != null)
            {
                children.Add(m_result);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_result, child))
            {
                m_result = null;
                return;
            }

            base.RemoveExplicitlyDefinedChild(child);
        }

        protected override BaseInstanceState FindChild(
            ISystemContext context,
            QualifiedName browseName,
            bool createOrReplace,
            BaseInstanceState replacement)
        {
            if (QualifiedName.IsNull(browseName))
            {
                return null;
            }

            BaseInstanceState instance = null;

            switch (browseName.Name)
            {
                case UAModel.MachineryResult.BrowseNames.Result:
                {
                    if (createOrReplace)
                    {
                        if (Result == null)
                        {
                            if (replacement == null)
                            {
                                Result = new ResultTypeState(this);
                            }
                            else
                            {
                                Result = (ResultTypeState)replacement;
                            }
                        }
                    }

                    instance = Result;
                    break;
                }
            }

            if (instance != null)
            {
                return instance;
            }

            return base.FindChild(context, browseName, createOrReplace, replacement);
        }
        #endregion

        #region Private Fields
        private ResultTypeState m_result;
        #endregion
    }
    #endif
    #endregion

    #region ResultManagementTypeState Class
    #if (!OPCUA_EXCLUDE_ResultManagementTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class ResultManagementTypeState : BaseObjectState
    {
        #region Constructors
        public ResultManagementTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.MachineryResult.ObjectTypes.ResultManagementType, UAModel.MachineryResult.Namespaces.MachineryResult, namespaceUris);
        }

        #if (!OPCUA_EXCLUDE_InitializationStrings)
        protected override void Initialize(ISystemContext context)
        {
            base.Initialize(context);
            Initialize(context, InitializationString);
            InitializeOptionalChildren(context);
        }

        protected override void Initialize(ISystemContext context, NodeState source)
        {
            InitializeOptionalChildren(context);
            base.Initialize(context, source);
        }

        protected override void InitializeOptionalChildren(ISystemContext context)
        {
            base.InitializeOptionalChildren(context);

            if (AcknowledgeResults != null)
            {
                AcknowledgeResults.Initialize(context, AcknowledgeResults_InitializationString);
            }

            if (GetLatestResult != null)
            {
                GetLatestResult.Initialize(context, GetLatestResult_InitializationString);
            }

            if (GetResultById != null)
            {
                GetResultById.Initialize(context, GetResultById_InitializationString);
            }

            if (GetResultIdListFiltered != null)
            {
                GetResultIdListFiltered.Initialize(context, GetResultIdListFiltered_InitializationString);
            }

            if (ReleaseResultHandle != null)
            {
                ReleaseResultHandle.Initialize(context, ReleaseResultHandle_InitializationString);
            }

            if (Results != null)
            {
                Results.Initialize(context, Results_InitializationString);
            }

            if (ResultTransfer != null)
            {
                ResultTransfer.Initialize(context, ResultTransfer_InitializationString);
            }
        }

        #region Initialization String
        private const string AcknowledgeResults_InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGGC" +
           "CgQAAAABABIAAABBY2tub3dsZWRnZVJlc3VsdHMBAWEbAC8BAWEbYRsAAAEB/////wIAAAAXYKkKAgAA" +
           "AAAADgAAAElucHV0QXJndW1lbnRzAQHJFwAuAETJFwAAlgEAAAABACoBAVAAAAAJAAAAUmVzdWx0SWRz" +
           "AQCufAEAAAABAAAAAAAAAAIuAAAATGlzdCBvZiByZXN1bHQgaWRlbnRpZmllcnMgdG8gYmUgYWNrbm93" +
           "bGVkZ2VkLgEAKAEBAAAAAQAAAAEAAAABAf////8AAAAAF2CpCgIAAAAAAA8AAABPdXRwdXRBcmd1bWVu" +
           "dHMBAcoXAC4ARMoXAACWAgAAAAEAKgEBdQEAABAAAABFcnJvclBlclJlc3VsdElkAAYBAAAAAQAAAAAA" +
           "AAACTgEAAFNoYWxsIGJlIG51bGwgb3IgZW1wdHkgaWYgZXJyb3IgZXF1YWxzIDAuIFNoYWxsIGhhdmUg" +
           "dGhlIHNhbWUgbGVuZ3RoIGFzIHJlc3VsdElkcyBpZiBlcnJvciBpcyBub3QgZXF1YWwgMC4gSW5kaWNh" +
           "dGVzIGZvciBlYWNoIHJlc3VsdElkIGluIHJlc3VsdElkcywgaWYgdGhlIGFja25vd2xlZGdlIHdhcyBz" +
           "dWNjZXNzZnVsLgpQZXIgZW50cnk6CjAg4oCTIE9LClZhbHVlcyA+IDAgYXJlIHJlc2VydmVkIGZvciBl" +
           "cnJvcnMgZGVmaW5lZCBieSB0aGlzIGFuZCBmdXR1cmUgc3RhbmRhcmRzLgpWYWx1ZXMgPCAwIHNoYWxs" +
           "IGJlIHVzZWQgZm9yIGFwcGxpY2F0aW9uLXNwZWNpZmljIGVycm9ycy4BACoBATMBAAAFAAAARXJyb3IA" +
           "Bv////8AAAAAAhsBAAAwIOKAkyBPSwpWYWx1ZXMgPiAwIGFyZSByZXNlcnZlZCBmb3IgZXJyb3JzIGRl" +
           "ZmluZWQgYnkgdGhpcyBhbmQgZnV0dXJlIHN0YW5kYXJkcy4KVmFsdWVzIDwgMCBzaGFsbCBiZSB1c2Vk" +
           "IGZvciBhcHBsaWNhdGlvbi1zcGVjaWZpYyBlcnJvcnMuClNoYWxsIGJlIG5vdCBlcXVhbCAwIGlmIGFu" +
           "eSByZXN1bHRJZCBvZiByZXN1bHRJZHMgd2FzIG5vdCBzdWNjZXNzZnVsbHkgYWNrbm93bGVkZ2VkLiBT" +
           "aGFsbCBiZSAwIGlmIGFsbCByZXN1bHRJZHMgd2hlcmUgYWNrbm93bGVkZ2VkIHN1Y2Nlc3NmdWwuAQAo" +
           "AQEAAAABAAAAAgAAAAEB/////wAAAAA=";

        private const string GetLatestResult_InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGGC" +
           "CgQAAAABAA8AAABHZXRMYXRlc3RSZXN1bHQBAWAbAC8BAWAbYBsAAAEB/////wIAAAAXYKkKAgAAAAAA" +
           "DgAAAElucHV0QXJndW1lbnRzAQGmFwAuAESmFwAAlgEAAAABACoBATYCAAAHAAAAVGltZW91dAAG////" +
           "/wAAAAACHAIAAFdpdGggdGhpcyBhcmd1bWVudCB0aGUgY2xpZW50IGNhbiBnaXZlIGEgaGludCB0byB0" +
           "aGUgc2VydmVyIGhvdyBsb25nIGl0IHdpbGwgbmVlZCBhY2Nlc3MgdG8gdGhlIHJlc3VsdCBkYXRhLgpB" +
           "IHZhbHVlID4gMCBpbmRpY2F0ZXMgYW4gZXN0aW1hdGVkIG1heGltdW0gdGltZSBmb3IgcHJvY2Vzc2lu" +
           "ZyB0aGUgZGF0YSBpbiBtaWxsaXNlY29uZHMuIApBIHZhbHVlID0gMCBpbmRpY2F0ZXMgdGhhdCB0aGUg" +
           "Y2xpZW50IHdpbGwgbm90IG5lZWQgYW55dGhpbmcgYmVzaWRlcyB0aGUgZGF0YSByZXR1cm5lZCBieSB0" +
           "aGUgbWV0aG9kIGNhbGwuCkEgdmFsdWUgPCAwIGluZGljYXRlcyB0aGF0IHRoZSBjbGllbnQgY2Fubm90" +
           "IGdpdmUgYW4gZXN0aW1hdGUuClRoZSBjbGllbnQgY2Fubm90IHJlbHkgb24gdGhlIGRhdGEgYmVpbmcg" +
           "YXZhaWxhYmxlIGR1cmluZyB0aGUgaW5kaWNhdGVkIHRpbWUgcGVyaW9kLiBUaGUgYXJndW1lbnQgaXMg" +
           "bWVyZWx5IGEgaGludCBhbGxvd2luZyB0aGUgc2VydmVyIHRvIG9wdGltaXplIGl0cyByZXNvdXJjZSBt" +
           "YW5hZ2VtZW50LgEAKAEBAAAAAQAAAAEAAAABAf////8AAAAAF2CpCgIAAAAAAA8AAABPdXRwdXRBcmd1" +
           "bWVudHMBAacXAC4ARKcXAACWAwAAAAEAKgEBIwIAAAwAAABSZXN1bHRIYW5kbGUBAK18/////wAAAAAC" +
           "AgIAAFRoZSBzZXJ2ZXIgc2hhbGwgcmV0dXJuIHRvIGVhY2ggY2xpZW50IHJlcXVlc3RpbmcgcmVzdWx0" +
           "IGRhdGEgYSBzeXN0ZW0td2lkZSB1bmlxdWUgaGFuZGxlIGlkZW50aWZ5aW5nIHRoZSByZXN1bHQgc2V0" +
           "IC8gY2xpZW50IGNvbWJpbmF0aW9uLiBUaGlzIGhhbmRsZSBzaG91bGQgYmUgdXNlZCBieSB0aGUgY2xp" +
           "ZW50IHRvIGluZGljYXRlIHRvIHRoZSBzZXJ2ZXIgdGhhdCB0aGUgcmVzdWx0IGRhdGEgaXMgbm8gbG9u" +
           "Z2VyIG5lZWRlZCwgYWxsb3dpbmcgdGhlIHNlcnZlciB0byBvcHRpbWl6ZSBpdHMgcmVzb3VyY2UgaGFu" +
           "ZGxpbmcuCklmIHRoZSBpbnN0YW5jZSBvZiBSZXN1bHRNYW5hZ2VtZW50VHlwZSBkb2VzIG5vdCBzdXBw" +
           "b3J0IHRoZSBSZWxlYXNlUmVzdWx0SGFuZGxlIE1ldGhvZCwgdGhlIHJlc3VsdEhhbmRsZSBzaG91bGQg" +
           "YWx3YXlzIGJlIHNldCB0byAwLgpJZiB0aGUgZXJyb3IgaXMgc2V0IHRvIGEgdmFsdWUgb3RoZXIgdGhh" +
           "biAwLCB0aGUgcmVzdWx0SGFuZGxlIG1heSBiZSBzZXQgdG8gMC4BACoBATkAAAAGAAAAUmVzdWx0AQHA" +
           "C/////8AAAAAAh4AAABUaGUgcmVzdWx0IGluY2x1ZGluZyBtZXRhZGF0YS4BACoBAaMAAAAFAAAARXJy" +
           "b3IABv////8AAAAAAosAAAAwIOKAkyBPSwpWYWx1ZXMgPiAwIGFyZSByZXNlcnZlZCBmb3IgZXJyb3Jz" +
           "IGRlZmluZWQgYnkgdGhpcyBhbmQgZnV0dXJlIHN0YW5kYXJkcy4KVmFsdWVzIDwgMCBzaGFsbCBiZSB1" +
           "c2VkIGZvciBhcHBsaWNhdGlvbi1zcGVjaWZpYyBlcnJvcnMuAQAoAQEAAAABAAAAAwAAAAEB/////wAA" +
           "AAA=";

        private const string GetResultById_InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////JGGC" +
           "CgQAAAABAA0AAABHZXRSZXN1bHRCeUlkAQFdGwMAAAAAAgIAAFRoZSBzZXJ2ZXIgc2hhbGwgcmV0dXJu" +
           "IHRvIGVhY2ggY2xpZW50IHJlcXVlc3RpbmcgcmVzdWx0IGRhdGEgYSBzeXN0ZW0td2lkZSB1bmlxdWUg" +
           "aGFuZGxlIGlkZW50aWZ5aW5nIHRoZSByZXN1bHQgc2V0IC8gY2xpZW50IGNvbWJpbmF0aW9uLiBUaGlz" +
           "IGhhbmRsZSBzaG91bGQgYmUgdXNlZCBieSB0aGUgY2xpZW50IHRvIGluZGljYXRlIHRvIHRoZSBzZXJ2" +
           "ZXIgdGhhdCB0aGUgcmVzdWx0IGRhdGEgaXMgbm8gbG9uZ2VyIG5lZWRlZCwgYWxsb3dpbmcgdGhlIHNl" +
           "cnZlciB0byBvcHRpbWl6ZSBpdHMgcmVzb3VyY2UgaGFuZGxpbmcuCklmIHRoZSBpbnN0YW5jZSBvZiBS" +
           "ZXN1bHRNYW5hZ2VtZW50VHlwZSBkb2VzIG5vdCBzdXBwb3J0IHRoZSBSZWxlYXNlUmVzdWx0SGFuZGxl" +
           "IE1ldGhvZCwgdGhlIHJlc3VsdEhhbmRsZSBzaG91bGQgYWx3YXlzIGJlIHNldCB0byAwLgpJZiB0aGUg" +
           "ZXJyb3IgaXMgc2V0IHRvIGEgdmFsdWUgb3RoZXIgdGhhbiAwLCB0aGUgcmVzdWx0SGFuZGxlIG1heSBi" +
           "ZSBzZXQgdG8gMC4ALwEBXRtdGwAAAQH/////AgAAABdgqQoCAAAAAAAOAAAASW5wdXRBcmd1bWVudHMB" +
           "AaAXAC4ARKAXAACWAgAAAAEAKgEBSgAAAAgAAABSZXN1bHRJZAEArnz/////AAAAAAItAAAAU3lzdGVt" +
           "LXdpZGUgdW5pcXVlIGlkZW50aWZpZXIgZm9yIHRoZSByZXN1bHQuAQAqAQE2AgAABwAAAFRpbWVvdXQA" +
           "Bv////8AAAAAAhwCAABXaXRoIHRoaXMgYXJndW1lbnQgdGhlIGNsaWVudCBjYW4gZ2l2ZSBhIGhpbnQg" +
           "dG8gdGhlIHNlcnZlciBob3cgbG9uZyBpdCB3aWxsIG5lZWQgYWNjZXNzIHRvIHRoZSByZXN1bHQgZGF0" +
           "YS4KQSB2YWx1ZSA+IDAgaW5kaWNhdGVzIGFuIGVzdGltYXRlZCBtYXhpbXVtIHRpbWUgZm9yIHByb2Nl" +
           "c3NpbmcgdGhlIGRhdGEgaW4gbWlsbGlzZWNvbmRzLiAKQSB2YWx1ZSA9IDAgaW5kaWNhdGVzIHRoYXQg" +
           "dGhlIGNsaWVudCB3aWxsIG5vdCBuZWVkIGFueXRoaW5nIGJlc2lkZXMgdGhlIGRhdGEgcmV0dXJuZWQg" +
           "YnkgdGhlIG1ldGhvZCBjYWxsLgpBIHZhbHVlIDwgMCBpbmRpY2F0ZXMgdGhhdCB0aGUgY2xpZW50IGNh" +
           "bm5vdCBnaXZlIGFuIGVzdGltYXRlLgpUaGUgY2xpZW50IGNhbm5vdCByZWx5IG9uIHRoZSBkYXRhIGJl" +
           "aW5nIGF2YWlsYWJsZSBkdXJpbmcgdGhlIGluZGljYXRlZCB0aW1lIHBlcmlvZC4gVGhlIGFyZ3VtZW50" +
           "IGlzIG1lcmVseSBhIGhpbnQgYWxsb3dpbmcgdGhlIHNlcnZlciB0byBvcHRpbWl6ZSBpdHMgcmVzb3Vy" +
           "Y2UgbWFuYWdlbWVudC4BACgBAQAAAAEAAAACAAAAAQH/////AAAAABdgqQoCAAAAAAAPAAAAT3V0cHV0" +
           "QXJndW1lbnRzAQGhFwAuAEShFwAAlgMAAAABACoBASMCAAAMAAAAUmVzdWx0SGFuZGxlAQCtfP////8A" +
           "AAAAAgICAABUaGUgc2VydmVyIHNoYWxsIHJldHVybiB0byBlYWNoIGNsaWVudCByZXF1ZXN0aW5nIHJl" +
           "c3VsdCBkYXRhIGEgc3lzdGVtLXdpZGUgdW5pcXVlIGhhbmRsZSBpZGVudGlmeWluZyB0aGUgcmVzdWx0" +
           "IHNldCAvIGNsaWVudCBjb21iaW5hdGlvbi4gVGhpcyBoYW5kbGUgc2hvdWxkIGJlIHVzZWQgYnkgdGhl" +
           "IGNsaWVudCB0byBpbmRpY2F0ZSB0byB0aGUgc2VydmVyIHRoYXQgdGhlIHJlc3VsdCBkYXRhIGlzIG5v" +
           "IGxvbmdlciBuZWVkZWQsIGFsbG93aW5nIHRoZSBzZXJ2ZXIgdG8gb3B0aW1pemUgaXRzIHJlc291cmNl" +
           "IGhhbmRsaW5nLgpJZiB0aGUgaW5zdGFuY2Ugb2YgUmVzdWx0TWFuYWdlbWVudFR5cGUgZG9lcyBub3Qg" +
           "c3VwcG9ydCB0aGUgUmVsZWFzZVJlc3VsdEhhbmRsZSBNZXRob2QsIHRoZSByZXN1bHRIYW5kbGUgc2hv" +
           "dWxkIGFsd2F5cyBiZSBzZXQgdG8gMC4KSWYgdGhlIGVycm9yIGlzIHNldCB0byBhIHZhbHVlIG90aGVy" +
           "IHRoYW4gMCwgdGhlIHJlc3VsdEhhbmRsZSBtYXkgYmUgc2V0IHRvIDAuAQAqAQF2AAAABgAAAFJlc3Vs" +
           "dAEBwAv/////AAAAAAJbAAAAVGhlIHJlc3VsdCBpbmNsdWRpbmcgbWV0YWRhdGEuIE1heSBiZSBzZXQg" +
           "dG8gTnVsbCwgaWYgZXJyb3IgaXMgc2V0IHRvIGEgdmFsdWUgb3RoZXIgdGhhbiAwLgEAKgEBowAAAAUA" +
           "AABFcnJvcgAG/////wAAAAACiwAAADAg4oCTIE9LClZhbHVlcyA+IDAgYXJlIHJlc2VydmVkIGZvciBl" +
           "cnJvcnMgZGVmaW5lZCBieSB0aGlzIGFuZCBmdXR1cmUgc3RhbmRhcmRzLgpWYWx1ZXMgPCAwIHNoYWxs" +
           "IGJlIHVzZWQgZm9yIGFwcGxpY2F0aW9uLXNwZWNpZmljIGVycm9ycy4BACgBAQAAAAEAAAADAAAAAQH/" +
           "////AAAAAA==";

        private const string GetResultIdListFiltered_InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGGC" +
           "CgQAAAABABcAAABHZXRSZXN1bHRJZExpc3RGaWx0ZXJlZAEBXhsALwEBXhteGwAAAQH/////AgAAABdg" +
           "qQoCAAAAAAAOAAAASW5wdXRBcmd1bWVudHMBAaIXAC4ARKIXAACWBAAAAAEAKgEBGAEAAAYAAABGaWx0" +
           "ZXIBAEoC/////wAAAAAC/QAAAEZpbHRlciB1c2VkIHRvIGZpbHRlciBmb3Igc3BlY2lmaWMgcmVzdWx0" +
           "cyBiYXNlZCBvbiB0aGUgbWV0YSBkYXRhIG9mIHRoZSByZXN1bHRzLiBWYWxpZCBCcm93c2VQYXRocyB1" +
           "c2VkIGluIHRoZSBmaWx0ZXIgY2FuIGJlIGJ1aWx0IGZyb20gdGhlIGZpZWxkcyBvZiB0aGUgUmVzdWx0" +
           "UmVhZHlFdmVudFR5cGUsIHRoZSBSZXN1bHRUeXBlIFZhcmlhYmxlVHlwZSBvciB0aGUgUmVzdWx0RGF0" +
           "YVR5cGUgb3IgY29ycmVzcG9uZGluZyBzdWJ0eXBlcy4BACoBASsBAAAJAAAAT3JkZXJlZEJ5AQAcAgEA" +
           "AAABAAAAAAAAAAIJAQAAQW4gYXJyYXkgb2YgQnJvd3NlUGF0aHMgKGFzIGFycmF5IG9mIFF1YWxpZmll" +
           "ZE5hbWUpIGlkZW50aWZ5aW5nIHRoZSBvcmRlcmluZyBjcml0ZXJpYSBmb3IgdGhlIHJlc3VsdHMuIElm" +
           "IHRoZSBhcnJheSBpcyBudWxsIG9yIGVtcHR5LCBubyBvcmRlcmluZyBpcyBleGVjdXRlZC4KSWYgc2V2" +
           "ZXJhbCBCcm93c2VQYXRocyBhcmUgcHJvdmlkZWQsIHRoZSBmaXJzdCBlbnRyeSBpbiB0aGUgYXJyYXkg" +
           "aXMgdXNlZCBhcyBmaXJzdCBvcmRlcmluZyBjcml0ZXJpYSwgZXRjLgEAKgEBjgAAAAoAAABNYXhSZXN1" +
           "bHRzAAf/////AAAAAAJxAAAARGVmaW5lcyBob3cgbWFueSByZXN1bHRJZHMgdGhlIENsaWVudCB3YW50" +
           "cyB0byByZWNlaXZlIGF0IG1vc3QuIElmIG5vIG1heGltdW0gc2hvdWxkIGJlIHByb3ZpZGVkLCBpdCBp" +
           "cyBzZXQgdG8gMC4BACoBATYCAAAHAAAAVGltZW91dAAG/////wAAAAACHAIAAFdpdGggdGhpcyBhcmd1" +
           "bWVudCB0aGUgY2xpZW50IGNhbiBnaXZlIGEgaGludCB0byB0aGUgc2VydmVyIGhvdyBsb25nIGl0IHdp" +
           "bGwgbmVlZCBhY2Nlc3MgdG8gdGhlIHJlc3VsdCBkYXRhLgpBIHZhbHVlID4gMCBpbmRpY2F0ZXMgYW4g" +
           "ZXN0aW1hdGVkIG1heGltdW0gdGltZSBmb3IgcHJvY2Vzc2luZyB0aGUgZGF0YSBpbiBtaWxsaXNlY29u" +
           "ZHMuIApBIHZhbHVlID0gMCBpbmRpY2F0ZXMgdGhhdCB0aGUgY2xpZW50IHdpbGwgbm90IG5lZWQgYW55" +
           "dGhpbmcgYmVzaWRlcyB0aGUgZGF0YSByZXR1cm5lZCBieSB0aGUgbWV0aG9kIGNhbGwuCkEgdmFsdWUg" +
           "PCAwIGluZGljYXRlcyB0aGF0IHRoZSBjbGllbnQgY2Fubm90IGdpdmUgYW4gZXN0aW1hdGUuClRoZSBj" +
           "bGllbnQgY2Fubm90IHJlbHkgb24gdGhlIGRhdGEgYmVpbmcgYXZhaWxhYmxlIGR1cmluZyB0aGUgaW5k" +
           "aWNhdGVkIHRpbWUgcGVyaW9kLiBUaGUgYXJndW1lbnQgaXMgbWVyZWx5IGEgaGludCBhbGxvd2luZyB0" +
           "aGUgc2VydmVyIHRvIG9wdGltaXplIGl0cyByZXNvdXJjZSBtYW5hZ2VtZW50LgEAKAEBAAAAAQAAAAQA" +
           "AAABAf////8AAAAAF2CpCgIAAAAAAA8AAABPdXRwdXRBcmd1bWVudHMBAaMXAC4ARKMXAACWAwAAAAEA" +
           "KgEBwwEAAAwAAABSZXN1bHRIYW5kbGUBAK18/////wAAAAACogEAAFRoZSBzZXJ2ZXIgc2hhbGwgcmV0" +
           "dXJuIHRvIGVhY2ggY2xpZW50IHJlcXVlc3RpbmcgcmVzdWx0IGRhdGEgYSBzeXN0ZW0td2lkZSB1bmlx" +
           "dWUgaGFuZGxlIGlkZW50aWZ5aW5nIHRoZSByZXN1bHQgc2V0IC8gY2xpZW50IGNvbWJpbmF0aW9uLiBU" +
           "aGlzIGhhbmRsZSBoYXMgdG8gYmUgdXNlZCBieSB0aGUgY2xpZW50IHRvIHJlbGVhc2UgdGhlIHJlc3Vs" +
           "dCBzZXQuCklmIHRoZSBpbnN0YW5jZSBvZiBSZXN1bHRNYW5hZ2VtZW50VHlwZSBkb2VzIG5vdCBzdXBw" +
           "b3J0IHRoZSBSZWxlYXNlUmVzdWx0SGFuZGxlIE1ldGhvZCwgdGhlIHJlc3VsdEhhbmRsZSBzaG91bGQg" +
           "YWx3YXlzIGJlIHNldCB0byAwLgpJZiB0aGUgZXJyb3IgaXMgc2V0IHRvIGEgdmFsdWUgb3RoZXIgdGhh" +
           "biAwLCB0aGUgcmVzdWx0SGFuZGxlIG1heSBiZSBzZXQgdG8gMC4BACoBAVYAAAAMAAAAUmVzdWx0SWRM" +
           "aXN0AQCufAEAAAABAAAAAAAAAAIxAAAATGlzdCBvZiByZXN1bHRJZHMgb2YgcmVzdWx0cyBtYXRjaGlu" +
           "ZyB0aGUgRmlsdGVyLgEAKgEBowAAAAUAAABFcnJvcgAG/////wAAAAACiwAAADAg4oCTIE9LClZhbHVl" +
           "cyA+IDAgYXJlIHJlc2VydmVkIGZvciBlcnJvcnMgZGVmaW5lZCBieSB0aGlzIGFuZCBmdXR1cmUgc3Rh" +
           "bmRhcmRzLgpWYWx1ZXMgPCAwIHNoYWxsIGJlIHVzZWQgZm9yIGFwcGxpY2F0aW9uLXNwZWNpZmljIGVy" +
           "cm9ycy4BACgBAQAAAAEAAAADAAAAAQH/////AAAAAA==";

        private const string ReleaseResultHandle_InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGGC" +
           "CgQAAAABABMAAABSZWxlYXNlUmVzdWx0SGFuZGxlAQFfGwAvAQFfG18bAAABAf////8CAAAAF2CpCgIA" +
           "AAAAAA4AAABJbnB1dEFyZ3VtZW50cwEBpBcALgBEpBcAAJYBAAAAAQAqAQGMAAAADAAAAFJlc3VsdEhh" +
           "bmRsZQEArXz/////AAAAAAJrAAAASGFuZGxlIHJldHVybmVkIGJ5IEdldFJlc3VsdEJ5SWQgb3IgR2V0" +
           "UmVzdWx0SWRMaXN0RmlsdGVyZWQsIGlkZW50aWZ5aW5nIHRoZSByZXN1bHQgc2V0L2NsaWVudCBjb21i" +
           "aW5hdGlvbi4BACgBAQAAAAEAAAABAAAAAQH/////AAAAABdgqQoCAAAAAAAPAAAAT3V0cHV0QXJndW1l" +
           "bnRzAQGlFwAuAESlFwAAlgEAAAABACoBAaMAAAAFAAAARXJyb3IABv////8AAAAAAosAAAAwIOKAkyBP" +
           "SwpWYWx1ZXMgPiAwIGFyZSByZXNlcnZlZCBmb3IgZXJyb3JzIGRlZmluZWQgYnkgdGhpcyBhbmQgZnV0" +
           "dXJlIHN0YW5kYXJkcy4KVmFsdWVzIDwgMCBzaGFsbCBiZSB1c2VkIGZvciBhcHBsaWNhdGlvbi1zcGVj" +
           "aWZpYyBlcnJvcnMuAQAoAQEAAAABAAAAAQAAAAEB/////wAAAAA=";

        private const string Results_InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGCA" +
           "CgEAAAABAAcAAABSZXN1bHRzAQGTEwAvAD2TEwAA/////wEAAAAVYOkKAgAAABoAAABSZXN1bHRWYXJp" +
           "YWJsZV9QbGFjZWhvbGRlcgEAEAAAADxSZXN1bHRWYXJpYWJsZT4BAZ0XAC8BAdEHnRcAABYBAZETAtsB" +
           "AAA8UmVzdWx0RGF0YVR5cGUgeG1sbnM9Imh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9NYWNoaW5l" +
           "cnkvUmVzdWx0L1R5cGVzLnhzZCI+PFJlc3VsdE1ldGFEYXRhPjxUeXBlSWQgeG1sbnM9Imh0dHA6Ly9v" +
           "cGNmb3VuZGF0aW9uLm9yZy9VQS8yMDA4LzAyL1R5cGVzLnhzZCI+PElkZW50aWZpZXI+bnM9MTtpPTUw" +
           "MDY8L0lkZW50aWZpZXI+PC9UeXBlSWQ+PEJvZHkgeG1sbnM9Imh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9y" +
           "Zy9VQS8yMDA4LzAyL1R5cGVzLnhzZCI+PFJlc3VsdE1ldGFEYXRhVHlwZSB4bWxucz0iaHR0cDovL29w" +
           "Y2ZvdW5kYXRpb24ub3JnL1VBL01hY2hpbmVyeS9SZXN1bHQvVHlwZXMueHNkIj48RW5jb2RpbmdNYXNr" +
           "PjA8L0VuY29kaW5nTWFzaz48UmVzdWx0SWQ+PC9SZXN1bHRJZD48L1Jlc3VsdE1ldGFEYXRhVHlwZT48" +
           "L0JvZHk+PC9SZXN1bHRNZXRhRGF0YT48UmVzdWx0Q29udGVudCAvPjwvUmVzdWx0RGF0YVR5cGU+AQHA" +
           "C/////8DA/////8BAAAAFWCJCgIAAAABAA4AAABSZXN1bHRNZXRhRGF0YQEBnhcBAEheAD+eFwAAAQG/" +
           "C/////8BAf////8BAAAANWCJCgIAAAABAAgAAABSZXN1bHRJZAEBnxcDAAAAACIBAABTeXN0ZW0td2lk" +
           "ZSB1bmlxdWUgaWRlbnRpZmllciwgd2hpY2ggaXMgYXNzaWduZWQgYnkgdGhlIHN5c3RlbS4gVGhpcyBJ" +
           "RCBjYW4gYmUgdXNlZCBmb3IgZmV0Y2hpbmcgZXhhY3RseSB0aGlzIHJlc3VsdCB1c2luZyB0aGUgbWV0" +
           "aG9kIEdldFJlc3VsdEJ5SWQgYW5kIGl0IGlzIGlkZW50aWNhbCB0byB0aGUgUmVzdWx0SWQgb2YgdGhl" +
           "IFJlc3VsdFJlYWR5RXZlbnRUeXBlLgpJZiB0aGUgc3lzdGVtIGRvZXMgbm90IG1hbmFnZSByZXN1bHRJ" +
           "ZHMsIGl0IHNob3VsZCBhbHdheXMgYmUgc2V0IHRvIOKAnE5B4oCdLgEASF4AP58XAAABAK58/////wMD" +
           "/////wAAAAA=";

        private const string ResultTransfer_InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGCA" +
           "CgEAAAABAA4AAABSZXN1bHRUcmFuc2ZlcgEBkhMALwEB6wOSEwAA/////wQAAAAVYIkKAgAAAAAAFwAA" +
           "AENsaWVudFByb2Nlc3NpbmdUaW1lb3V0AQGYFwAuAESYFwAAAQAiAf////8BAf////8AAAAABGGCCgQA" +
           "AAAAABMAAABHZW5lcmF0ZUZpbGVGb3JSZWFkAQFaGwAvAQCCPVobAAABAf////8CAAAAF2CpCgIAAAAA" +
           "AA4AAABJbnB1dEFyZ3VtZW50cwEBlhcALgBElhcAAJYBAAAAAQAqAQF/AAAADwAAAEdlbmVyYXRlT3B0" +
           "aW9ucwEBvQv/////AAAAAAJbAAAAT3B0aW9ucyBob3cgdG8gZ2VuZXJhdGUgdGhlIGZpbGUsIGluY2x1" +
           "ZGluZyB0aGUgcmVzdWx0SWQgb2YgdGhlIHJlc3VsdCB0aGUgZmlsZSBiZWxvbmdzIHRvLgEAKAEBAAAA" +
           "AQAAAAEAAAABAf////8AAAAAF2CpCgIAAAAAAA8AAABPdXRwdXRBcmd1bWVudHMBAZcXAC4ARJcXAACW" +
           "AwAAAAEAKgEBOgAAAAoAAABGaWxlTm9kZUlkABH/////AAAAAAIdAAAATm9kZUlkIG9mIHRoZSB0ZW1w" +
           "b3JhcnkgZmlsZS4BACoBAZUAAAAKAAAARmlsZUhhbmRsZQAH/////wAAAAACeAAAAFRoZSBGaWxlSGFu" +
           "ZGxlIG9mIHRoZSBvcGVuZWQgVHJhbnNmZXJGaWxlLgpUaGUgRmlsZUhhbmRsZSBjYW4gYmUgdXNlZCB0" +
           "byBhY2Nlc3MgdGhlIFRyYW5zZmVyRmlsZSBtZXRob2RzIFJlYWQgYW5kIENsb3NlLgEAKgEBlQEAABYA" +
           "AABDb21wbGV0aW9uU3RhdGVNYWNoaW5lABH/////AAAAAAJsAQAASWYgdGhlIGNyZWF0aW9uIG9mIHRo" +
           "ZSBmaWxlIGlzIGNvbXBsZXRlZCBhc3luY2hyb25vdXNseSwgdGhlIHBhcmFtZXRlciByZXR1cm5zIHRo" +
           "ZSBOb2RlSWQgb2YgdGhlIGNvcnJlc3BvbmRpbmcgRmlsZVRyYW5zZmVyU3RhdGVNYWNoaW5lVHlwZSBP" +
           "YmplY3QuCklmIHRoZSBjcmVhdGlvbiBvZiB0aGUgZmlsZSBpcyBhbHJlYWR5IGNvbXBsZXRlZCwgdGhl" +
           "IHBhcmFtZXRlciBpcyBudWxsLgpJZiBhIEZpbGVUcmFuc2ZlclN0YXRlTWFjaGluZVR5cGUgb2JqZWN0" +
           "IE5vZGVJZCBpcyByZXR1cm5lZCwgdGhlIFJlYWQgTWV0aG9kIG9mIHRoZSBmaWxlIGZhaWxzIHVudGls" +
           "IHRoZSBUcmFuc2ZlclN0YXRlIGNoYW5nZWQgdG8gUmVhZFRyYW5zZmVyLgEAKAEBAAAAAQAAAAMAAAAB" +
           "Af////8AAAAABGGCCgQAAAAAABQAAABHZW5lcmF0ZUZpbGVGb3JXcml0ZQEBXBsALwEAhT1cGwAAAQH/" +
           "////AgAAABdgqQoCAAAAAAAOAAAASW5wdXRBcmd1bWVudHMBAZsXAC4ARJsXAACWAQAAAAEAKgEBHgAA" +
           "AA8AAABHZW5lcmF0ZU9wdGlvbnMAGP////8AAAAAAAEAKAEBAAAAAQAAAAEAAAABAf////8AAAAAF2Cp" +
           "CgIAAAAAAA8AAABPdXRwdXRBcmd1bWVudHMBAZwXAC4ARJwXAACWAgAAAAEAKgEBGQAAAAoAAABGaWxl" +
           "Tm9kZUlkABH/////AAAAAAABACoBARkAAAAKAAAARmlsZUhhbmRsZQAH/////wAAAAAAAQAoAQEAAAAB" +
           "AAAAAgAAAAEB/////wAAAAAEYYIKBAAAAAAADgAAAENsb3NlQW5kQ29tbWl0AQFbGwAvAQCHPVsbAAAB" +
           "Af////8CAAAAF2CpCgIAAAAAAA4AAABJbnB1dEFyZ3VtZW50cwEBmRcALgBEmRcAAJYBAAAAAQAqAQEZ" +
           "AAAACgAAAEZpbGVIYW5kbGUAB/////8AAAAAAAEAKAEBAAAAAQAAAAEAAAABAf////8AAAAAF2CpCgIA" +
           "AAAAAA8AAABPdXRwdXRBcmd1bWVudHMBAZoXAC4ARJoXAACWAQAAAAEAKgEBJQAAABYAAABDb21wbGV0" +
           "aW9uU3RhdGVNYWNoaW5lABH/////AAAAAAABACgBAQAAAAEAAAABAAAAAQH/////AAAAAA==";

        private const string InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGCA" +
           "AgEAAAABABwAAABSZXN1bHRNYW5hZ2VtZW50VHlwZUluc3RhbmNlAQHsAwEB7APsAwAAAQAAAAApAAEB" +
           "6gMIAAAABGGCCgQAAAABABIAAABBY2tub3dsZWRnZVJlc3VsdHMBAWEbAC8BAWEbYRsAAAEB/////wIA" +
           "AAAXYKkKAgAAAAAADgAAAElucHV0QXJndW1lbnRzAQHJFwAuAETJFwAAlgEAAAABACoBAVAAAAAJAAAA" +
           "UmVzdWx0SWRzAQCufAEAAAABAAAAAAAAAAIuAAAATGlzdCBvZiByZXN1bHQgaWRlbnRpZmllcnMgdG8g" +
           "YmUgYWNrbm93bGVkZ2VkLgEAKAEBAAAAAQAAAAEAAAABAf////8AAAAAF2CpCgIAAAAAAA8AAABPdXRw" +
           "dXRBcmd1bWVudHMBAcoXAC4ARMoXAACWAgAAAAEAKgEBdQEAABAAAABFcnJvclBlclJlc3VsdElkAAYB" +
           "AAAAAQAAAAAAAAACTgEAAFNoYWxsIGJlIG51bGwgb3IgZW1wdHkgaWYgZXJyb3IgZXF1YWxzIDAuIFNo" +
           "YWxsIGhhdmUgdGhlIHNhbWUgbGVuZ3RoIGFzIHJlc3VsdElkcyBpZiBlcnJvciBpcyBub3QgZXF1YWwg" +
           "MC4gSW5kaWNhdGVzIGZvciBlYWNoIHJlc3VsdElkIGluIHJlc3VsdElkcywgaWYgdGhlIGFja25vd2xl" +
           "ZGdlIHdhcyBzdWNjZXNzZnVsLgpQZXIgZW50cnk6CjAg4oCTIE9LClZhbHVlcyA+IDAgYXJlIHJlc2Vy" +
           "dmVkIGZvciBlcnJvcnMgZGVmaW5lZCBieSB0aGlzIGFuZCBmdXR1cmUgc3RhbmRhcmRzLgpWYWx1ZXMg" +
           "PCAwIHNoYWxsIGJlIHVzZWQgZm9yIGFwcGxpY2F0aW9uLXNwZWNpZmljIGVycm9ycy4BACoBATMBAAAF" +
           "AAAARXJyb3IABv////8AAAAAAhsBAAAwIOKAkyBPSwpWYWx1ZXMgPiAwIGFyZSByZXNlcnZlZCBmb3Ig" +
           "ZXJyb3JzIGRlZmluZWQgYnkgdGhpcyBhbmQgZnV0dXJlIHN0YW5kYXJkcy4KVmFsdWVzIDwgMCBzaGFs" +
           "bCBiZSB1c2VkIGZvciBhcHBsaWNhdGlvbi1zcGVjaWZpYyBlcnJvcnMuClNoYWxsIGJlIG5vdCBlcXVh" +
           "bCAwIGlmIGFueSByZXN1bHRJZCBvZiByZXN1bHRJZHMgd2FzIG5vdCBzdWNjZXNzZnVsbHkgYWNrbm93" +
           "bGVkZ2VkLiBTaGFsbCBiZSAwIGlmIGFsbCByZXN1bHRJZHMgd2hlcmUgYWNrbm93bGVkZ2VkIHN1Y2Nl" +
           "c3NmdWwuAQAoAQEAAAABAAAAAgAAAAEB/////wAAAAA1YKkKAgAAAAAAGQAAAERlZmF1bHRJbnN0YW5j" +
           "ZUJyb3dzZU5hbWUBAZUXAwAAAAAxAAAAVGhlIGRlZmF1bHQgQnJvd3NlTmFtZSBmb3IgaW5zdGFuY2Vz" +
           "IG9mIHRoZSB0eXBlLgAuAESVFwAAFAEAEAAAAFJlc3VsdE1hbmFnZW1lbnQAFP////8DA/////8AAAAA" +
           "BGGCCgQAAAABAA8AAABHZXRMYXRlc3RSZXN1bHQBAWAbAC8BAWAbYBsAAAEB/////wIAAAAXYKkKAgAA" +
           "AAAADgAAAElucHV0QXJndW1lbnRzAQGmFwAuAESmFwAAlgEAAAABACoBATYCAAAHAAAAVGltZW91dAAG" +
           "/////wAAAAACHAIAAFdpdGggdGhpcyBhcmd1bWVudCB0aGUgY2xpZW50IGNhbiBnaXZlIGEgaGludCB0" +
           "byB0aGUgc2VydmVyIGhvdyBsb25nIGl0IHdpbGwgbmVlZCBhY2Nlc3MgdG8gdGhlIHJlc3VsdCBkYXRh" +
           "LgpBIHZhbHVlID4gMCBpbmRpY2F0ZXMgYW4gZXN0aW1hdGVkIG1heGltdW0gdGltZSBmb3IgcHJvY2Vz" +
           "c2luZyB0aGUgZGF0YSBpbiBtaWxsaXNlY29uZHMuIApBIHZhbHVlID0gMCBpbmRpY2F0ZXMgdGhhdCB0" +
           "aGUgY2xpZW50IHdpbGwgbm90IG5lZWQgYW55dGhpbmcgYmVzaWRlcyB0aGUgZGF0YSByZXR1cm5lZCBi" +
           "eSB0aGUgbWV0aG9kIGNhbGwuCkEgdmFsdWUgPCAwIGluZGljYXRlcyB0aGF0IHRoZSBjbGllbnQgY2Fu" +
           "bm90IGdpdmUgYW4gZXN0aW1hdGUuClRoZSBjbGllbnQgY2Fubm90IHJlbHkgb24gdGhlIGRhdGEgYmVp" +
           "bmcgYXZhaWxhYmxlIGR1cmluZyB0aGUgaW5kaWNhdGVkIHRpbWUgcGVyaW9kLiBUaGUgYXJndW1lbnQg" +
           "aXMgbWVyZWx5IGEgaGludCBhbGxvd2luZyB0aGUgc2VydmVyIHRvIG9wdGltaXplIGl0cyByZXNvdXJj" +
           "ZSBtYW5hZ2VtZW50LgEAKAEBAAAAAQAAAAEAAAABAf////8AAAAAF2CpCgIAAAAAAA8AAABPdXRwdXRB" +
           "cmd1bWVudHMBAacXAC4ARKcXAACWAwAAAAEAKgEBIwIAAAwAAABSZXN1bHRIYW5kbGUBAK18/////wAA" +
           "AAACAgIAAFRoZSBzZXJ2ZXIgc2hhbGwgcmV0dXJuIHRvIGVhY2ggY2xpZW50IHJlcXVlc3RpbmcgcmVz" +
           "dWx0IGRhdGEgYSBzeXN0ZW0td2lkZSB1bmlxdWUgaGFuZGxlIGlkZW50aWZ5aW5nIHRoZSByZXN1bHQg" +
           "c2V0IC8gY2xpZW50IGNvbWJpbmF0aW9uLiBUaGlzIGhhbmRsZSBzaG91bGQgYmUgdXNlZCBieSB0aGUg" +
           "Y2xpZW50IHRvIGluZGljYXRlIHRvIHRoZSBzZXJ2ZXIgdGhhdCB0aGUgcmVzdWx0IGRhdGEgaXMgbm8g" +
           "bG9uZ2VyIG5lZWRlZCwgYWxsb3dpbmcgdGhlIHNlcnZlciB0byBvcHRpbWl6ZSBpdHMgcmVzb3VyY2Ug" +
           "aGFuZGxpbmcuCklmIHRoZSBpbnN0YW5jZSBvZiBSZXN1bHRNYW5hZ2VtZW50VHlwZSBkb2VzIG5vdCBz" +
           "dXBwb3J0IHRoZSBSZWxlYXNlUmVzdWx0SGFuZGxlIE1ldGhvZCwgdGhlIHJlc3VsdEhhbmRsZSBzaG91" +
           "bGQgYWx3YXlzIGJlIHNldCB0byAwLgpJZiB0aGUgZXJyb3IgaXMgc2V0IHRvIGEgdmFsdWUgb3RoZXIg" +
           "dGhhbiAwLCB0aGUgcmVzdWx0SGFuZGxlIG1heSBiZSBzZXQgdG8gMC4BACoBATkAAAAGAAAAUmVzdWx0" +
           "AQHAC/////8AAAAAAh4AAABUaGUgcmVzdWx0IGluY2x1ZGluZyBtZXRhZGF0YS4BACoBAaMAAAAFAAAA" +
           "RXJyb3IABv////8AAAAAAosAAAAwIOKAkyBPSwpWYWx1ZXMgPiAwIGFyZSByZXNlcnZlZCBmb3IgZXJy" +
           "b3JzIGRlZmluZWQgYnkgdGhpcyBhbmQgZnV0dXJlIHN0YW5kYXJkcy4KVmFsdWVzIDwgMCBzaGFsbCBi" +
           "ZSB1c2VkIGZvciBhcHBsaWNhdGlvbi1zcGVjaWZpYyBlcnJvcnMuAQAoAQEAAAABAAAAAwAAAAEB////" +
           "/wAAAAAkYYIKBAAAAAEADQAAAEdldFJlc3VsdEJ5SWQBAV0bAwAAAAACAgAAVGhlIHNlcnZlciBzaGFs" +
           "bCByZXR1cm4gdG8gZWFjaCBjbGllbnQgcmVxdWVzdGluZyByZXN1bHQgZGF0YSBhIHN5c3RlbS13aWRl" +
           "IHVuaXF1ZSBoYW5kbGUgaWRlbnRpZnlpbmcgdGhlIHJlc3VsdCBzZXQgLyBjbGllbnQgY29tYmluYXRp" +
           "b24uIFRoaXMgaGFuZGxlIHNob3VsZCBiZSB1c2VkIGJ5IHRoZSBjbGllbnQgdG8gaW5kaWNhdGUgdG8g" +
           "dGhlIHNlcnZlciB0aGF0IHRoZSByZXN1bHQgZGF0YSBpcyBubyBsb25nZXIgbmVlZGVkLCBhbGxvd2lu" +
           "ZyB0aGUgc2VydmVyIHRvIG9wdGltaXplIGl0cyByZXNvdXJjZSBoYW5kbGluZy4KSWYgdGhlIGluc3Rh" +
           "bmNlIG9mIFJlc3VsdE1hbmFnZW1lbnRUeXBlIGRvZXMgbm90IHN1cHBvcnQgdGhlIFJlbGVhc2VSZXN1" +
           "bHRIYW5kbGUgTWV0aG9kLCB0aGUgcmVzdWx0SGFuZGxlIHNob3VsZCBhbHdheXMgYmUgc2V0IHRvIDAu" +
           "CklmIHRoZSBlcnJvciBpcyBzZXQgdG8gYSB2YWx1ZSBvdGhlciB0aGFuIDAsIHRoZSByZXN1bHRIYW5k" +
           "bGUgbWF5IGJlIHNldCB0byAwLgAvAQFdG10bAAABAf////8CAAAAF2CpCgIAAAAAAA4AAABJbnB1dEFy" +
           "Z3VtZW50cwEBoBcALgBEoBcAAJYCAAAAAQAqAQFKAAAACAAAAFJlc3VsdElkAQCufP////8AAAAAAi0A" +
           "AABTeXN0ZW0td2lkZSB1bmlxdWUgaWRlbnRpZmllciBmb3IgdGhlIHJlc3VsdC4BACoBATYCAAAHAAAA" +
           "VGltZW91dAAG/////wAAAAACHAIAAFdpdGggdGhpcyBhcmd1bWVudCB0aGUgY2xpZW50IGNhbiBnaXZl" +
           "IGEgaGludCB0byB0aGUgc2VydmVyIGhvdyBsb25nIGl0IHdpbGwgbmVlZCBhY2Nlc3MgdG8gdGhlIHJl" +
           "c3VsdCBkYXRhLgpBIHZhbHVlID4gMCBpbmRpY2F0ZXMgYW4gZXN0aW1hdGVkIG1heGltdW0gdGltZSBm" +
           "b3IgcHJvY2Vzc2luZyB0aGUgZGF0YSBpbiBtaWxsaXNlY29uZHMuIApBIHZhbHVlID0gMCBpbmRpY2F0" +
           "ZXMgdGhhdCB0aGUgY2xpZW50IHdpbGwgbm90IG5lZWQgYW55dGhpbmcgYmVzaWRlcyB0aGUgZGF0YSBy" +
           "ZXR1cm5lZCBieSB0aGUgbWV0aG9kIGNhbGwuCkEgdmFsdWUgPCAwIGluZGljYXRlcyB0aGF0IHRoZSBj" +
           "bGllbnQgY2Fubm90IGdpdmUgYW4gZXN0aW1hdGUuClRoZSBjbGllbnQgY2Fubm90IHJlbHkgb24gdGhl" +
           "IGRhdGEgYmVpbmcgYXZhaWxhYmxlIGR1cmluZyB0aGUgaW5kaWNhdGVkIHRpbWUgcGVyaW9kLiBUaGUg" +
           "YXJndW1lbnQgaXMgbWVyZWx5IGEgaGludCBhbGxvd2luZyB0aGUgc2VydmVyIHRvIG9wdGltaXplIGl0" +
           "cyByZXNvdXJjZSBtYW5hZ2VtZW50LgEAKAEBAAAAAQAAAAIAAAABAf////8AAAAAF2CpCgIAAAAAAA8A" +
           "AABPdXRwdXRBcmd1bWVudHMBAaEXAC4ARKEXAACWAwAAAAEAKgEBIwIAAAwAAABSZXN1bHRIYW5kbGUB" +
           "AK18/////wAAAAACAgIAAFRoZSBzZXJ2ZXIgc2hhbGwgcmV0dXJuIHRvIGVhY2ggY2xpZW50IHJlcXVl" +
           "c3RpbmcgcmVzdWx0IGRhdGEgYSBzeXN0ZW0td2lkZSB1bmlxdWUgaGFuZGxlIGlkZW50aWZ5aW5nIHRo" +
           "ZSByZXN1bHQgc2V0IC8gY2xpZW50IGNvbWJpbmF0aW9uLiBUaGlzIGhhbmRsZSBzaG91bGQgYmUgdXNl" +
           "ZCBieSB0aGUgY2xpZW50IHRvIGluZGljYXRlIHRvIHRoZSBzZXJ2ZXIgdGhhdCB0aGUgcmVzdWx0IGRh" +
           "dGEgaXMgbm8gbG9uZ2VyIG5lZWRlZCwgYWxsb3dpbmcgdGhlIHNlcnZlciB0byBvcHRpbWl6ZSBpdHMg" +
           "cmVzb3VyY2UgaGFuZGxpbmcuCklmIHRoZSBpbnN0YW5jZSBvZiBSZXN1bHRNYW5hZ2VtZW50VHlwZSBk" +
           "b2VzIG5vdCBzdXBwb3J0IHRoZSBSZWxlYXNlUmVzdWx0SGFuZGxlIE1ldGhvZCwgdGhlIHJlc3VsdEhh" +
           "bmRsZSBzaG91bGQgYWx3YXlzIGJlIHNldCB0byAwLgpJZiB0aGUgZXJyb3IgaXMgc2V0IHRvIGEgdmFs" +
           "dWUgb3RoZXIgdGhhbiAwLCB0aGUgcmVzdWx0SGFuZGxlIG1heSBiZSBzZXQgdG8gMC4BACoBAXYAAAAG" +
           "AAAAUmVzdWx0AQHAC/////8AAAAAAlsAAABUaGUgcmVzdWx0IGluY2x1ZGluZyBtZXRhZGF0YS4gTWF5" +
           "IGJlIHNldCB0byBOdWxsLCBpZiBlcnJvciBpcyBzZXQgdG8gYSB2YWx1ZSBvdGhlciB0aGFuIDAuAQAq" +
           "AQGjAAAABQAAAEVycm9yAAb/////AAAAAAKLAAAAMCDigJMgT0sKVmFsdWVzID4gMCBhcmUgcmVzZXJ2" +
           "ZWQgZm9yIGVycm9ycyBkZWZpbmVkIGJ5IHRoaXMgYW5kIGZ1dHVyZSBzdGFuZGFyZHMuClZhbHVlcyA8" +
           "IDAgc2hhbGwgYmUgdXNlZCBmb3IgYXBwbGljYXRpb24tc3BlY2lmaWMgZXJyb3JzLgEAKAEBAAAAAQAA" +
           "AAMAAAABAf////8AAAAABGGCCgQAAAABABcAAABHZXRSZXN1bHRJZExpc3RGaWx0ZXJlZAEBXhsALwEB" +
           "XhteGwAAAQH/////AgAAABdgqQoCAAAAAAAOAAAASW5wdXRBcmd1bWVudHMBAaIXAC4ARKIXAACWBAAA" +
           "AAEAKgEBGAEAAAYAAABGaWx0ZXIBAEoC/////wAAAAAC/QAAAEZpbHRlciB1c2VkIHRvIGZpbHRlciBm" +
           "b3Igc3BlY2lmaWMgcmVzdWx0cyBiYXNlZCBvbiB0aGUgbWV0YSBkYXRhIG9mIHRoZSByZXN1bHRzLiBW" +
           "YWxpZCBCcm93c2VQYXRocyB1c2VkIGluIHRoZSBmaWx0ZXIgY2FuIGJlIGJ1aWx0IGZyb20gdGhlIGZp" +
           "ZWxkcyBvZiB0aGUgUmVzdWx0UmVhZHlFdmVudFR5cGUsIHRoZSBSZXN1bHRUeXBlIFZhcmlhYmxlVHlw" +
           "ZSBvciB0aGUgUmVzdWx0RGF0YVR5cGUgb3IgY29ycmVzcG9uZGluZyBzdWJ0eXBlcy4BACoBASsBAAAJ" +
           "AAAAT3JkZXJlZEJ5AQAcAgEAAAABAAAAAAAAAAIJAQAAQW4gYXJyYXkgb2YgQnJvd3NlUGF0aHMgKGFz" +
           "IGFycmF5IG9mIFF1YWxpZmllZE5hbWUpIGlkZW50aWZ5aW5nIHRoZSBvcmRlcmluZyBjcml0ZXJpYSBm" +
           "b3IgdGhlIHJlc3VsdHMuIElmIHRoZSBhcnJheSBpcyBudWxsIG9yIGVtcHR5LCBubyBvcmRlcmluZyBp" +
           "cyBleGVjdXRlZC4KSWYgc2V2ZXJhbCBCcm93c2VQYXRocyBhcmUgcHJvdmlkZWQsIHRoZSBmaXJzdCBl" +
           "bnRyeSBpbiB0aGUgYXJyYXkgaXMgdXNlZCBhcyBmaXJzdCBvcmRlcmluZyBjcml0ZXJpYSwgZXRjLgEA" +
           "KgEBjgAAAAoAAABNYXhSZXN1bHRzAAf/////AAAAAAJxAAAARGVmaW5lcyBob3cgbWFueSByZXN1bHRJ" +
           "ZHMgdGhlIENsaWVudCB3YW50cyB0byByZWNlaXZlIGF0IG1vc3QuIElmIG5vIG1heGltdW0gc2hvdWxk" +
           "IGJlIHByb3ZpZGVkLCBpdCBpcyBzZXQgdG8gMC4BACoBATYCAAAHAAAAVGltZW91dAAG/////wAAAAAC" +
           "HAIAAFdpdGggdGhpcyBhcmd1bWVudCB0aGUgY2xpZW50IGNhbiBnaXZlIGEgaGludCB0byB0aGUgc2Vy" +
           "dmVyIGhvdyBsb25nIGl0IHdpbGwgbmVlZCBhY2Nlc3MgdG8gdGhlIHJlc3VsdCBkYXRhLgpBIHZhbHVl" +
           "ID4gMCBpbmRpY2F0ZXMgYW4gZXN0aW1hdGVkIG1heGltdW0gdGltZSBmb3IgcHJvY2Vzc2luZyB0aGUg" +
           "ZGF0YSBpbiBtaWxsaXNlY29uZHMuIApBIHZhbHVlID0gMCBpbmRpY2F0ZXMgdGhhdCB0aGUgY2xpZW50" +
           "IHdpbGwgbm90IG5lZWQgYW55dGhpbmcgYmVzaWRlcyB0aGUgZGF0YSByZXR1cm5lZCBieSB0aGUgbWV0" +
           "aG9kIGNhbGwuCkEgdmFsdWUgPCAwIGluZGljYXRlcyB0aGF0IHRoZSBjbGllbnQgY2Fubm90IGdpdmUg" +
           "YW4gZXN0aW1hdGUuClRoZSBjbGllbnQgY2Fubm90IHJlbHkgb24gdGhlIGRhdGEgYmVpbmcgYXZhaWxh" +
           "YmxlIGR1cmluZyB0aGUgaW5kaWNhdGVkIHRpbWUgcGVyaW9kLiBUaGUgYXJndW1lbnQgaXMgbWVyZWx5" +
           "IGEgaGludCBhbGxvd2luZyB0aGUgc2VydmVyIHRvIG9wdGltaXplIGl0cyByZXNvdXJjZSBtYW5hZ2Vt" +
           "ZW50LgEAKAEBAAAAAQAAAAQAAAABAf////8AAAAAF2CpCgIAAAAAAA8AAABPdXRwdXRBcmd1bWVudHMB" +
           "AaMXAC4ARKMXAACWAwAAAAEAKgEBwwEAAAwAAABSZXN1bHRIYW5kbGUBAK18/////wAAAAACogEAAFRo" +
           "ZSBzZXJ2ZXIgc2hhbGwgcmV0dXJuIHRvIGVhY2ggY2xpZW50IHJlcXVlc3RpbmcgcmVzdWx0IGRhdGEg" +
           "YSBzeXN0ZW0td2lkZSB1bmlxdWUgaGFuZGxlIGlkZW50aWZ5aW5nIHRoZSByZXN1bHQgc2V0IC8gY2xp" +
           "ZW50IGNvbWJpbmF0aW9uLiBUaGlzIGhhbmRsZSBoYXMgdG8gYmUgdXNlZCBieSB0aGUgY2xpZW50IHRv" +
           "IHJlbGVhc2UgdGhlIHJlc3VsdCBzZXQuCklmIHRoZSBpbnN0YW5jZSBvZiBSZXN1bHRNYW5hZ2VtZW50" +
           "VHlwZSBkb2VzIG5vdCBzdXBwb3J0IHRoZSBSZWxlYXNlUmVzdWx0SGFuZGxlIE1ldGhvZCwgdGhlIHJl" +
           "c3VsdEhhbmRsZSBzaG91bGQgYWx3YXlzIGJlIHNldCB0byAwLgpJZiB0aGUgZXJyb3IgaXMgc2V0IHRv" +
           "IGEgdmFsdWUgb3RoZXIgdGhhbiAwLCB0aGUgcmVzdWx0SGFuZGxlIG1heSBiZSBzZXQgdG8gMC4BACoB" +
           "AVYAAAAMAAAAUmVzdWx0SWRMaXN0AQCufAEAAAABAAAAAAAAAAIxAAAATGlzdCBvZiByZXN1bHRJZHMg" +
           "b2YgcmVzdWx0cyBtYXRjaGluZyB0aGUgRmlsdGVyLgEAKgEBowAAAAUAAABFcnJvcgAG/////wAAAAAC" +
           "iwAAADAg4oCTIE9LClZhbHVlcyA+IDAgYXJlIHJlc2VydmVkIGZvciBlcnJvcnMgZGVmaW5lZCBieSB0" +
           "aGlzIGFuZCBmdXR1cmUgc3RhbmRhcmRzLgpWYWx1ZXMgPCAwIHNoYWxsIGJlIHVzZWQgZm9yIGFwcGxp" +
           "Y2F0aW9uLXNwZWNpZmljIGVycm9ycy4BACgBAQAAAAEAAAADAAAAAQH/////AAAAAARhggoEAAAAAQAT" +
           "AAAAUmVsZWFzZVJlc3VsdEhhbmRsZQEBXxsALwEBXxtfGwAAAQH/////AgAAABdgqQoCAAAAAAAOAAAA" +
           "SW5wdXRBcmd1bWVudHMBAaQXAC4ARKQXAACWAQAAAAEAKgEBjAAAAAwAAABSZXN1bHRIYW5kbGUBAK18" +
           "/////wAAAAACawAAAEhhbmRsZSByZXR1cm5lZCBieSBHZXRSZXN1bHRCeUlkIG9yIEdldFJlc3VsdElk" +
           "TGlzdEZpbHRlcmVkLCBpZGVudGlmeWluZyB0aGUgcmVzdWx0IHNldC9jbGllbnQgY29tYmluYXRpb24u" +
           "AQAoAQEAAAABAAAAAQAAAAEB/////wAAAAAXYKkKAgAAAAAADwAAAE91dHB1dEFyZ3VtZW50cwEBpRcA" +
           "LgBEpRcAAJYBAAAAAQAqAQGjAAAABQAAAEVycm9yAAb/////AAAAAAKLAAAAMCDigJMgT0sKVmFsdWVz" +
           "ID4gMCBhcmUgcmVzZXJ2ZWQgZm9yIGVycm9ycyBkZWZpbmVkIGJ5IHRoaXMgYW5kIGZ1dHVyZSBzdGFu" +
           "ZGFyZHMuClZhbHVlcyA8IDAgc2hhbGwgYmUgdXNlZCBmb3IgYXBwbGljYXRpb24tc3BlY2lmaWMgZXJy" +
           "b3JzLgEAKAEBAAAAAQAAAAEAAAABAf////8AAAAABGCACgEAAAABAAcAAABSZXN1bHRzAQGTEwAvAD2T" +
           "EwAA/////wEAAAAVYOkKAgAAABoAAABSZXN1bHRWYXJpYWJsZV9QbGFjZWhvbGRlcgEAEAAAADxSZXN1" +
           "bHRWYXJpYWJsZT4BAZ0XAC8BAdEHnRcAABYBAZETAtsBAAA8UmVzdWx0RGF0YVR5cGUgeG1sbnM9Imh0" +
           "dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9NYWNoaW5lcnkvUmVzdWx0L1R5cGVzLnhzZCI+PFJlc3Vs" +
           "dE1ldGFEYXRhPjxUeXBlSWQgeG1sbnM9Imh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS8yMDA4LzAy" +
           "L1R5cGVzLnhzZCI+PElkZW50aWZpZXI+bnM9MTtpPTUwMDY8L0lkZW50aWZpZXI+PC9UeXBlSWQ+PEJv" +
           "ZHkgeG1sbnM9Imh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS8yMDA4LzAyL1R5cGVzLnhzZCI+PFJl" +
           "c3VsdE1ldGFEYXRhVHlwZSB4bWxucz0iaHR0cDovL29wY2ZvdW5kYXRpb24ub3JnL1VBL01hY2hpbmVy" +
           "eS9SZXN1bHQvVHlwZXMueHNkIj48RW5jb2RpbmdNYXNrPjA8L0VuY29kaW5nTWFzaz48UmVzdWx0SWQ+" +
           "PC9SZXN1bHRJZD48L1Jlc3VsdE1ldGFEYXRhVHlwZT48L0JvZHk+PC9SZXN1bHRNZXRhRGF0YT48UmVz" +
           "dWx0Q29udGVudCAvPjwvUmVzdWx0RGF0YVR5cGU+AQHAC/////8DA/////8BAAAAFWCJCgIAAAABAA4A" +
           "AABSZXN1bHRNZXRhRGF0YQEBnhcBAEheAD+eFwAAAQG/C/////8BAf////8BAAAANWCJCgIAAAABAAgA" +
           "AABSZXN1bHRJZAEBnxcDAAAAACIBAABTeXN0ZW0td2lkZSB1bmlxdWUgaWRlbnRpZmllciwgd2hpY2gg" +
           "aXMgYXNzaWduZWQgYnkgdGhlIHN5c3RlbS4gVGhpcyBJRCBjYW4gYmUgdXNlZCBmb3IgZmV0Y2hpbmcg" +
           "ZXhhY3RseSB0aGlzIHJlc3VsdCB1c2luZyB0aGUgbWV0aG9kIEdldFJlc3VsdEJ5SWQgYW5kIGl0IGlz" +
           "IGlkZW50aWNhbCB0byB0aGUgUmVzdWx0SWQgb2YgdGhlIFJlc3VsdFJlYWR5RXZlbnRUeXBlLgpJZiB0" +
           "aGUgc3lzdGVtIGRvZXMgbm90IG1hbmFnZSByZXN1bHRJZHMsIGl0IHNob3VsZCBhbHdheXMgYmUgc2V0" +
           "IHRvIOKAnE5B4oCdLgEASF4AP58XAAABAK58/////wMD/////wAAAAAEYIAKAQAAAAEADgAAAFJlc3Vs" +
           "dFRyYW5zZmVyAQGSEwAvAQHrA5ITAAD/////BAAAABVgiQoCAAAAAAAXAAAAQ2xpZW50UHJvY2Vzc2lu" +
           "Z1RpbWVvdXQBAZgXAC4ARJgXAAABACIB/////wEB/////wAAAAAEYYIKBAAAAAAAEwAAAEdlbmVyYXRl" +
           "RmlsZUZvclJlYWQBAVobAC8BAII9WhsAAAEB/////wIAAAAXYKkKAgAAAAAADgAAAElucHV0QXJndW1l" +
           "bnRzAQGWFwAuAESWFwAAlgEAAAABACoBAX8AAAAPAAAAR2VuZXJhdGVPcHRpb25zAQG9C/////8AAAAA" +
           "AlsAAABPcHRpb25zIGhvdyB0byBnZW5lcmF0ZSB0aGUgZmlsZSwgaW5jbHVkaW5nIHRoZSByZXN1bHRJ" +
           "ZCBvZiB0aGUgcmVzdWx0IHRoZSBmaWxlIGJlbG9uZ3MgdG8uAQAoAQEAAAABAAAAAQAAAAEB/////wAA" +
           "AAAXYKkKAgAAAAAADwAAAE91dHB1dEFyZ3VtZW50cwEBlxcALgBElxcAAJYDAAAAAQAqAQE6AAAACgAA" +
           "AEZpbGVOb2RlSWQAEf////8AAAAAAh0AAABOb2RlSWQgb2YgdGhlIHRlbXBvcmFyeSBmaWxlLgEAKgEB" +
           "lQAAAAoAAABGaWxlSGFuZGxlAAf/////AAAAAAJ4AAAAVGhlIEZpbGVIYW5kbGUgb2YgdGhlIG9wZW5l" +
           "ZCBUcmFuc2ZlckZpbGUuClRoZSBGaWxlSGFuZGxlIGNhbiBiZSB1c2VkIHRvIGFjY2VzcyB0aGUgVHJh" +
           "bnNmZXJGaWxlIG1ldGhvZHMgUmVhZCBhbmQgQ2xvc2UuAQAqAQGVAQAAFgAAAENvbXBsZXRpb25TdGF0" +
           "ZU1hY2hpbmUAEf////8AAAAAAmwBAABJZiB0aGUgY3JlYXRpb24gb2YgdGhlIGZpbGUgaXMgY29tcGxl" +
           "dGVkIGFzeW5jaHJvbm91c2x5LCB0aGUgcGFyYW1ldGVyIHJldHVybnMgdGhlIE5vZGVJZCBvZiB0aGUg" +
           "Y29ycmVzcG9uZGluZyBGaWxlVHJhbnNmZXJTdGF0ZU1hY2hpbmVUeXBlIE9iamVjdC4KSWYgdGhlIGNy" +
           "ZWF0aW9uIG9mIHRoZSBmaWxlIGlzIGFscmVhZHkgY29tcGxldGVkLCB0aGUgcGFyYW1ldGVyIGlzIG51" +
           "bGwuCklmIGEgRmlsZVRyYW5zZmVyU3RhdGVNYWNoaW5lVHlwZSBvYmplY3QgTm9kZUlkIGlzIHJldHVy" +
           "bmVkLCB0aGUgUmVhZCBNZXRob2Qgb2YgdGhlIGZpbGUgZmFpbHMgdW50aWwgdGhlIFRyYW5zZmVyU3Rh" +
           "dGUgY2hhbmdlZCB0byBSZWFkVHJhbnNmZXIuAQAoAQEAAAABAAAAAwAAAAEB/////wAAAAAEYYIKBAAA" +
           "AAAAFAAAAEdlbmVyYXRlRmlsZUZvcldyaXRlAQFcGwAvAQCFPVwbAAABAf////8CAAAAF2CpCgIAAAAA" +
           "AA4AAABJbnB1dEFyZ3VtZW50cwEBmxcALgBEmxcAAJYBAAAAAQAqAQEeAAAADwAAAEdlbmVyYXRlT3B0" +
           "aW9ucwAY/////wAAAAAAAQAoAQEAAAABAAAAAQAAAAEB/////wAAAAAXYKkKAgAAAAAADwAAAE91dHB1" +
           "dEFyZ3VtZW50cwEBnBcALgBEnBcAAJYCAAAAAQAqAQEZAAAACgAAAEZpbGVOb2RlSWQAEf////8AAAAA" +
           "AAEAKgEBGQAAAAoAAABGaWxlSGFuZGxlAAf/////AAAAAAABACgBAQAAAAEAAAACAAAAAQH/////AAAA" +
           "AARhggoEAAAAAAAOAAAAQ2xvc2VBbmRDb21taXQBAVsbAC8BAIc9WxsAAAEB/////wIAAAAXYKkKAgAA" +
           "AAAADgAAAElucHV0QXJndW1lbnRzAQGZFwAuAESZFwAAlgEAAAABACoBARkAAAAKAAAARmlsZUhhbmRs" +
           "ZQAH/////wAAAAAAAQAoAQEAAAABAAAAAQAAAAEB/////wAAAAAXYKkKAgAAAAAADwAAAE91dHB1dEFy" +
           "Z3VtZW50cwEBmhcALgBEmhcAAJYBAAAAAQAqAQElAAAAFgAAAENvbXBsZXRpb25TdGF0ZU1hY2hpbmUA" +
           "Ef////8AAAAAAAEAKAEBAAAAAQAAAAEAAAABAf////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public AcknowledgeResultsMethodState AcknowledgeResults
        {
            get => m_acknowledgeResultsMethod;

            set
            {
                if (!Object.ReferenceEquals(m_acknowledgeResultsMethod, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_acknowledgeResultsMethod = value;
            }
        }

        public GetLatestResultMethodState GetLatestResult
        {
            get => m_getLatestResultMethod;

            set
            {
                if (!Object.ReferenceEquals(m_getLatestResultMethod, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_getLatestResultMethod = value;
            }
        }

        public GetResultByIdMethodState GetResultById
        {
            get => m_getResultByIdMethod;

            set
            {
                if (!Object.ReferenceEquals(m_getResultByIdMethod, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_getResultByIdMethod = value;
            }
        }

        public GetResultIdListFilteredMethodState GetResultIdListFiltered
        {
            get => m_getResultIdListFilteredMethod;

            set
            {
                if (!Object.ReferenceEquals(m_getResultIdListFilteredMethod, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_getResultIdListFilteredMethod = value;
            }
        }

        public ReleaseResultHandleMethodState ReleaseResultHandle
        {
            get => m_releaseResultHandleMethod;

            set
            {
                if (!Object.ReferenceEquals(m_releaseResultHandleMethod, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_releaseResultHandleMethod = value;
            }
        }

        public FolderState Results
        {
            get => m_results;

            set
            {
                if (!Object.ReferenceEquals(m_results, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_results = value;
            }
        }

        public ResultTransferTypeState ResultTransfer
        {
            get => m_resultTransfer;

            set
            {
                if (!Object.ReferenceEquals(m_resultTransfer, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_resultTransfer = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_acknowledgeResultsMethod != null)
            {
                children.Add(m_acknowledgeResultsMethod);
            }

            if (m_getLatestResultMethod != null)
            {
                children.Add(m_getLatestResultMethod);
            }

            if (m_getResultByIdMethod != null)
            {
                children.Add(m_getResultByIdMethod);
            }

            if (m_getResultIdListFilteredMethod != null)
            {
                children.Add(m_getResultIdListFilteredMethod);
            }

            if (m_releaseResultHandleMethod != null)
            {
                children.Add(m_releaseResultHandleMethod);
            }

            if (m_results != null)
            {
                children.Add(m_results);
            }

            if (m_resultTransfer != null)
            {
                children.Add(m_resultTransfer);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_acknowledgeResultsMethod, child))
            {
                m_acknowledgeResultsMethod = null;
                return;
            }

            if (Object.ReferenceEquals(m_getLatestResultMethod, child))
            {
                m_getLatestResultMethod = null;
                return;
            }

            if (Object.ReferenceEquals(m_getResultByIdMethod, child))
            {
                m_getResultByIdMethod = null;
                return;
            }

            if (Object.ReferenceEquals(m_getResultIdListFilteredMethod, child))
            {
                m_getResultIdListFilteredMethod = null;
                return;
            }

            if (Object.ReferenceEquals(m_releaseResultHandleMethod, child))
            {
                m_releaseResultHandleMethod = null;
                return;
            }

            if (Object.ReferenceEquals(m_results, child))
            {
                m_results = null;
                return;
            }

            if (Object.ReferenceEquals(m_resultTransfer, child))
            {
                m_resultTransfer = null;
                return;
            }

            base.RemoveExplicitlyDefinedChild(child);
        }

        protected override BaseInstanceState FindChild(
            ISystemContext context,
            QualifiedName browseName,
            bool createOrReplace,
            BaseInstanceState replacement)
        {
            if (QualifiedName.IsNull(browseName))
            {
                return null;
            }

            BaseInstanceState instance = null;

            switch (browseName.Name)
            {
                case UAModel.MachineryResult.BrowseNames.AcknowledgeResults:
                {
                    if (createOrReplace)
                    {
                        if (AcknowledgeResults == null)
                        {
                            if (replacement == null)
                            {
                                AcknowledgeResults = new AcknowledgeResultsMethodState(this);
                            }
                            else
                            {
                                AcknowledgeResults = (AcknowledgeResultsMethodState)replacement;
                            }
                        }
                    }

                    instance = AcknowledgeResults;
                    break;
                }

                case UAModel.MachineryResult.BrowseNames.GetLatestResult:
                {
                    if (createOrReplace)
                    {
                        if (GetLatestResult == null)
                        {
                            if (replacement == null)
                            {
                                GetLatestResult = new GetLatestResultMethodState(this);
                            }
                            else
                            {
                                GetLatestResult = (GetLatestResultMethodState)replacement;
                            }
                        }
                    }

                    instance = GetLatestResult;
                    break;
                }

                case UAModel.MachineryResult.BrowseNames.GetResultById:
                {
                    if (createOrReplace)
                    {
                        if (GetResultById == null)
                        {
                            if (replacement == null)
                            {
                                GetResultById = new GetResultByIdMethodState(this);
                            }
                            else
                            {
                                GetResultById = (GetResultByIdMethodState)replacement;
                            }
                        }
                    }

                    instance = GetResultById;
                    break;
                }

                case UAModel.MachineryResult.BrowseNames.GetResultIdListFiltered:
                {
                    if (createOrReplace)
                    {
                        if (GetResultIdListFiltered == null)
                        {
                            if (replacement == null)
                            {
                                GetResultIdListFiltered = new GetResultIdListFilteredMethodState(this);
                            }
                            else
                            {
                                GetResultIdListFiltered = (GetResultIdListFilteredMethodState)replacement;
                            }
                        }
                    }

                    instance = GetResultIdListFiltered;
                    break;
                }

                case UAModel.MachineryResult.BrowseNames.ReleaseResultHandle:
                {
                    if (createOrReplace)
                    {
                        if (ReleaseResultHandle == null)
                        {
                            if (replacement == null)
                            {
                                ReleaseResultHandle = new ReleaseResultHandleMethodState(this);
                            }
                            else
                            {
                                ReleaseResultHandle = (ReleaseResultHandleMethodState)replacement;
                            }
                        }
                    }

                    instance = ReleaseResultHandle;
                    break;
                }

                case UAModel.MachineryResult.BrowseNames.Results:
                {
                    if (createOrReplace)
                    {
                        if (Results == null)
                        {
                            if (replacement == null)
                            {
                                Results = new FolderState(this);
                            }
                            else
                            {
                                Results = (FolderState)replacement;
                            }
                        }
                    }

                    instance = Results;
                    break;
                }

                case UAModel.MachineryResult.BrowseNames.ResultTransfer:
                {
                    if (createOrReplace)
                    {
                        if (ResultTransfer == null)
                        {
                            if (replacement == null)
                            {
                                ResultTransfer = new ResultTransferTypeState(this);
                            }
                            else
                            {
                                ResultTransfer = (ResultTransferTypeState)replacement;
                            }
                        }
                    }

                    instance = ResultTransfer;
                    break;
                }
            }

            if (instance != null)
            {
                return instance;
            }

            return base.FindChild(context, browseName, createOrReplace, replacement);
        }
        #endregion

        #region Private Fields
        private AcknowledgeResultsMethodState m_acknowledgeResultsMethod;
        private GetLatestResultMethodState m_getLatestResultMethod;
        private GetResultByIdMethodState m_getResultByIdMethod;
        private GetResultIdListFilteredMethodState m_getResultIdListFilteredMethod;
        private ReleaseResultHandleMethodState m_releaseResultHandleMethod;
        private FolderState m_results;
        private ResultTransferTypeState m_resultTransfer;
        #endregion
    }
    #endif
    #endregion

    #region ResultTransferTypeState Class
    #if (!OPCUA_EXCLUDE_ResultTransferTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class ResultTransferTypeState : TemporaryFileTransferState
    {
        #region Constructors
        public ResultTransferTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.MachineryResult.ObjectTypes.ResultTransferType, UAModel.MachineryResult.Namespaces.MachineryResult, namespaceUris);
        }

        #if (!OPCUA_EXCLUDE_InitializationStrings)
        protected override void Initialize(ISystemContext context)
        {
            base.Initialize(context);
            Initialize(context, InitializationString);
            InitializeOptionalChildren(context);
        }

        protected override void Initialize(ISystemContext context, NodeState source)
        {
            InitializeOptionalChildren(context);
            base.Initialize(context, source);
        }

        protected override void InitializeOptionalChildren(ISystemContext context)
        {
            base.InitializeOptionalChildren(context);
        }

        #region Initialization String
        private const string InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGCA" +
           "AgEAAAABABoAAABSZXN1bHRUcmFuc2ZlclR5cGVJbnN0YW5jZQEB6wMBAesD6wMAAP////8EAAAAFWCJ" +
           "CAIAAAAAABcAAABDbGllbnRQcm9jZXNzaW5nVGltZW91dAEBAAAALgBEAQAiAf////8BAf////8AAAAA" +
           "BGGCCgQAAAAAABMAAABHZW5lcmF0ZUZpbGVGb3JSZWFkAQFZGwAvAQCCPVkbAAABAf////8CAAAAF2Cp" +
           "CgIAAAAAAA4AAABJbnB1dEFyZ3VtZW50cwEBkxcALgBEkxcAAJYBAAAAAQAqAQF/AAAADwAAAEdlbmVy" +
           "YXRlT3B0aW9ucwEBvQv/////AAAAAAJbAAAAT3B0aW9ucyBob3cgdG8gZ2VuZXJhdGUgdGhlIGZpbGUs" +
           "IGluY2x1ZGluZyB0aGUgcmVzdWx0SWQgb2YgdGhlIHJlc3VsdCB0aGUgZmlsZSBiZWxvbmdzIHRvLgEA" +
           "KAEBAAAAAQAAAAEAAAABAf////8AAAAAF2CpCgIAAAAAAA8AAABPdXRwdXRBcmd1bWVudHMBAZQXAC4A" +
           "RJQXAACWAwAAAAEAKgEBOgAAAAoAAABGaWxlTm9kZUlkABH/////AAAAAAIdAAAATm9kZUlkIG9mIHRo" +
           "ZSB0ZW1wb3JhcnkgZmlsZS4BACoBAZUAAAAKAAAARmlsZUhhbmRsZQAH/////wAAAAACeAAAAFRoZSBG" +
           "aWxlSGFuZGxlIG9mIHRoZSBvcGVuZWQgVHJhbnNmZXJGaWxlLgpUaGUgRmlsZUhhbmRsZSBjYW4gYmUg" +
           "dXNlZCB0byBhY2Nlc3MgdGhlIFRyYW5zZmVyRmlsZSBtZXRob2RzIFJlYWQgYW5kIENsb3NlLgEAKgEB" +
           "lQEAABYAAABDb21wbGV0aW9uU3RhdGVNYWNoaW5lABH/////AAAAAAJsAQAASWYgdGhlIGNyZWF0aW9u" +
           "IG9mIHRoZSBmaWxlIGlzIGNvbXBsZXRlZCBhc3luY2hyb25vdXNseSwgdGhlIHBhcmFtZXRlciByZXR1" +
           "cm5zIHRoZSBOb2RlSWQgb2YgdGhlIGNvcnJlc3BvbmRpbmcgRmlsZVRyYW5zZmVyU3RhdGVNYWNoaW5l" +
           "VHlwZSBPYmplY3QuCklmIHRoZSBjcmVhdGlvbiBvZiB0aGUgZmlsZSBpcyBhbHJlYWR5IGNvbXBsZXRl" +
           "ZCwgdGhlIHBhcmFtZXRlciBpcyBudWxsLgpJZiBhIEZpbGVUcmFuc2ZlclN0YXRlTWFjaGluZVR5cGUg" +
           "b2JqZWN0IE5vZGVJZCBpcyByZXR1cm5lZCwgdGhlIFJlYWQgTWV0aG9kIG9mIHRoZSBmaWxlIGZhaWxz" +
           "IHVudGlsIHRoZSBUcmFuc2ZlclN0YXRlIGNoYW5nZWQgdG8gUmVhZFRyYW5zZmVyLgEAKAEBAAAAAQAA" +
           "AAMAAAABAf////8AAAAABGGCCAQAAAAAABQAAABHZW5lcmF0ZUZpbGVGb3JXcml0ZQEBAAAALwEAhT0B" +
           "Af////8CAAAAF2CpCAIAAAAAAA4AAABJbnB1dEFyZ3VtZW50cwEBAAAALgBElgEAAAABACoBAR4AAAAP" +
           "AAAAR2VuZXJhdGVPcHRpb25zABj/////AAAAAAABACgBAQAAAAEAAAABAAAAAQH/////AAAAABdgqQgC" +
           "AAAAAAAPAAAAT3V0cHV0QXJndW1lbnRzAQEAAAAuAESWAgAAAAEAKgEBGQAAAAoAAABGaWxlTm9kZUlk" +
           "ABH/////AAAAAAABACoBARkAAAAKAAAARmlsZUhhbmRsZQAH/////wAAAAAAAQAoAQEAAAABAAAAAgAA" +
           "AAEB/////wAAAAAEYYIIBAAAAAAADgAAAENsb3NlQW5kQ29tbWl0AQEAAAAvAQCHPQEB/////wIAAAAX" +
           "YKkIAgAAAAAADgAAAElucHV0QXJndW1lbnRzAQEAAAAuAESWAQAAAAEAKgEBGQAAAAoAAABGaWxlSGFu" +
           "ZGxlAAf/////AAAAAAABACgBAQAAAAEAAAABAAAAAQH/////AAAAABdgqQgCAAAAAAAPAAAAT3V0cHV0" +
           "QXJndW1lbnRzAQEAAAAuAESWAQAAAAEAKgEBJQAAABYAAABDb21wbGV0aW9uU3RhdGVNYWNoaW5lABH/" +
           "////AAAAAAABACgBAQAAAAEAAAABAAAAAQH/////AAAAAA==";
        #endregion
        #endif
        #endregion

        #region Public Properties
        #endregion

        #region Overridden Methods
        #endregion

        #region Private Fields
        #endregion
    }
    #endif
    #endregion

    #region AcknowledgeResultsMethodState Class
    #if (!OPCUA_EXCLUDE_AcknowledgeResultsMethodState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class AcknowledgeResultsMethodState : MethodState
    {
        #region Constructors
        public AcknowledgeResultsMethodState(NodeState parent) : base(parent)
        {
        }

        public new static NodeState Construct(NodeState parent)
        {
            return new AcknowledgeResultsMethodState(parent);
        }

        #if (!OPCUA_EXCLUDE_InitializationStrings)
        protected override void Initialize(ISystemContext context)
        {
            base.Initialize(context);
            Initialize(context, InitializationString);
            InitializeOptionalChildren(context);
        }

        protected override void InitializeOptionalChildren(ISystemContext context)
        {
            base.InitializeOptionalChildren(context);
        }

        #region Initialization String
        private const string InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGGC" +
           "AAQAAAABABwAAABBY2tub3dsZWRnZVJlc3VsdHNNZXRob2RUeXBlAQEAAAEBAAABAf////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Event Callbacks
        public AcknowledgeResultsMethodStateMethodCallHandler OnCall;

        public AcknowledgeResultsMethodStateMethodAsyncCallHandler OnCallAsync;
        #endregion

        #region Public Properties
        #endregion

        #region Overridden Methods
        protected override ServiceResult Call(
            ISystemContext _context,
            NodeId _objectId,
            IList<object> _inputArguments,
            IList<object> _outputArguments)
        {
            if (OnCall == null)
            {
                return base.Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            ServiceResult _result = null;

            string[] resultIds = (string[])_inputArguments[0];

            int[] errorPerResultId = (int[])_outputArguments[0];
            int error = (int)_outputArguments[1];

            if (OnCall != null)
            {
                _result = OnCall(
                    _context,
                    this,
                    _objectId,
                    resultIds,
                    ref errorPerResultId,
                    ref error);
            }

            _outputArguments[0] = errorPerResultId;
            _outputArguments[1] = error;

            return _result;
        }

        #if (OPCUA_INCLUDE_ASYNC)
        protected override async ValueTask<ServiceResult> CallAsync(
            ISystemContext _context,
            NodeId _objectId,
            IList<object> _inputArguments,
            IList<object> _outputArguments,
            CancellationToken cancellationToken = default)
        {
            if (OnCall == null && OnCallAsync == null)
            {
                return await base.CallAsync(_context, _objectId, _inputArguments, _outputArguments, cancellationToken).ConfigureAwait(false);
            }

            AcknowledgeResultsMethodStateResult _result = null;

            string[] resultIds = (string[])_inputArguments[0];

            if (OnCallAsync != null)
            {
                _result = await OnCallAsync(
                    _context,
                    this,
                    _objectId,
                    resultIds,
                    cancellationToken).ConfigureAwait(false);
            }
            else if (OnCall != null)
            {
                return Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            _outputArguments[0] = _result.ErrorPerResultId;
            _outputArguments[1] = _result.Error;

            return _result.ServiceResult;
        }
        #endif

        #endregion

        #region Private Fields
        #endregion
    }

    /// <exclude />
    public delegate ServiceResult AcknowledgeResultsMethodStateMethodCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        string[] resultIds,
        ref int[] errorPerResultId,
        ref int error);

    /// <exclude />
    public partial class AcknowledgeResultsMethodStateResult
    {
        public ServiceResult ServiceResult { get; set; }
        public int[] ErrorPerResultId { get; set; }
        public int Error { get; set; }
    }

    /// <exclude />
    public delegate ValueTask<AcknowledgeResultsMethodStateResult> AcknowledgeResultsMethodStateMethodAsyncCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        string[] resultIds,
        CancellationToken cancellationToken);
    #endif
    #endregion

    #region GetLatestResultMethodState Class
    #if (!OPCUA_EXCLUDE_GetLatestResultMethodState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class GetLatestResultMethodState : MethodState
    {
        #region Constructors
        public GetLatestResultMethodState(NodeState parent) : base(parent)
        {
        }

        public new static NodeState Construct(NodeState parent)
        {
            return new GetLatestResultMethodState(parent);
        }

        #if (!OPCUA_EXCLUDE_InitializationStrings)
        protected override void Initialize(ISystemContext context)
        {
            base.Initialize(context);
            Initialize(context, InitializationString);
            InitializeOptionalChildren(context);
        }

        protected override void InitializeOptionalChildren(ISystemContext context)
        {
            base.InitializeOptionalChildren(context);
        }

        #region Initialization String
        private const string InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGGC" +
           "AAQAAAABABkAAABHZXRMYXRlc3RSZXN1bHRNZXRob2RUeXBlAQEAAAEBAAABAf////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Event Callbacks
        public GetLatestResultMethodStateMethodCallHandler OnCall;

        public GetLatestResultMethodStateMethodAsyncCallHandler OnCallAsync;
        #endregion

        #region Public Properties
        #endregion

        #region Overridden Methods
        protected override ServiceResult Call(
            ISystemContext _context,
            NodeId _objectId,
            IList<object> _inputArguments,
            IList<object> _outputArguments)
        {
            if (OnCall == null)
            {
                return base.Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            ServiceResult _result = null;

            int timeout = (int)_inputArguments[0];

            uint resultHandle = (uint)_outputArguments[0];
            ResultDataType result = (ResultDataType)_outputArguments[1];
            int error = (int)_outputArguments[2];

            if (OnCall != null)
            {
                _result = OnCall(
                    _context,
                    this,
                    _objectId,
                    timeout,
                    ref resultHandle,
                    ref result,
                    ref error);
            }

            _outputArguments[0] = resultHandle;
            _outputArguments[1] = result;
            _outputArguments[2] = error;

            return _result;
        }

        #if (OPCUA_INCLUDE_ASYNC)
        protected override async ValueTask<ServiceResult> CallAsync(
            ISystemContext _context,
            NodeId _objectId,
            IList<object> _inputArguments,
            IList<object> _outputArguments,
            CancellationToken cancellationToken = default)
        {
            if (OnCall == null && OnCallAsync == null)
            {
                return await base.CallAsync(_context, _objectId, _inputArguments, _outputArguments, cancellationToken).ConfigureAwait(false);
            }

            GetLatestResultMethodStateResult _result = null;

            int timeout = (int)_inputArguments[0];

            if (OnCallAsync != null)
            {
                _result = await OnCallAsync(
                    _context,
                    this,
                    _objectId,
                    timeout,
                    cancellationToken).ConfigureAwait(false);
            }
            else if (OnCall != null)
            {
                return Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            _outputArguments[0] = _result.ResultHandle;
            _outputArguments[1] = _result.Result;
            _outputArguments[2] = _result.Error;

            return _result.ServiceResult;
        }
        #endif

        #endregion

        #region Private Fields
        #endregion
    }

    /// <exclude />
    public delegate ServiceResult GetLatestResultMethodStateMethodCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        int timeout,
        ref uint resultHandle,
        ref ResultDataType result,
        ref int error);

    /// <exclude />
    public partial class GetLatestResultMethodStateResult
    {
        public ServiceResult ServiceResult { get; set; }
        public uint ResultHandle { get; set; }
        public ResultDataType Result { get; set; }
        public int Error { get; set; }
    }

    /// <exclude />
    public delegate ValueTask<GetLatestResultMethodStateResult> GetLatestResultMethodStateMethodAsyncCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        int timeout,
        CancellationToken cancellationToken);
    #endif
    #endregion

    #region GetResultByIdMethodState Class
    #if (!OPCUA_EXCLUDE_GetResultByIdMethodState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class GetResultByIdMethodState : MethodState
    {
        #region Constructors
        public GetResultByIdMethodState(NodeState parent) : base(parent)
        {
        }

        public new static NodeState Construct(NodeState parent)
        {
            return new GetResultByIdMethodState(parent);
        }

        #if (!OPCUA_EXCLUDE_InitializationStrings)
        protected override void Initialize(ISystemContext context)
        {
            base.Initialize(context);
            Initialize(context, InitializationString);
            InitializeOptionalChildren(context);
        }

        protected override void InitializeOptionalChildren(ISystemContext context)
        {
            base.InitializeOptionalChildren(context);
        }

        #region Initialization String
        private const string InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGGC" +
           "AAQAAAABABcAAABHZXRSZXN1bHRCeUlkTWV0aG9kVHlwZQEBAAABAQAAAQH/////AAAAAA==";
        #endregion
        #endif
        #endregion

        #region Event Callbacks
        public GetResultByIdMethodStateMethodCallHandler OnCall;

        public GetResultByIdMethodStateMethodAsyncCallHandler OnCallAsync;
        #endregion

        #region Public Properties
        #endregion

        #region Overridden Methods
        protected override ServiceResult Call(
            ISystemContext _context,
            NodeId _objectId,
            IList<object> _inputArguments,
            IList<object> _outputArguments)
        {
            if (OnCall == null)
            {
                return base.Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            ServiceResult _result = null;

            string resultId = (string)_inputArguments[0];
            int timeout = (int)_inputArguments[1];

            uint resultHandle = (uint)_outputArguments[0];
            ResultDataType result = (ResultDataType)_outputArguments[1];
            int error = (int)_outputArguments[2];

            if (OnCall != null)
            {
                _result = OnCall(
                    _context,
                    this,
                    _objectId,
                    resultId,
                    timeout,
                    ref resultHandle,
                    ref result,
                    ref error);
            }

            _outputArguments[0] = resultHandle;
            _outputArguments[1] = result;
            _outputArguments[2] = error;

            return _result;
        }

        #if (OPCUA_INCLUDE_ASYNC)
        protected override async ValueTask<ServiceResult> CallAsync(
            ISystemContext _context,
            NodeId _objectId,
            IList<object> _inputArguments,
            IList<object> _outputArguments,
            CancellationToken cancellationToken = default)
        {
            if (OnCall == null && OnCallAsync == null)
            {
                return await base.CallAsync(_context, _objectId, _inputArguments, _outputArguments, cancellationToken).ConfigureAwait(false);
            }

            GetResultByIdMethodStateResult _result = null;

            string resultId = (string)_inputArguments[0];
            int timeout = (int)_inputArguments[1];

            if (OnCallAsync != null)
            {
                _result = await OnCallAsync(
                    _context,
                    this,
                    _objectId,
                    resultId,
                    timeout,
                    cancellationToken).ConfigureAwait(false);
            }
            else if (OnCall != null)
            {
                return Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            _outputArguments[0] = _result.ResultHandle;
            _outputArguments[1] = _result.Result;
            _outputArguments[2] = _result.Error;

            return _result.ServiceResult;
        }
        #endif

        #endregion

        #region Private Fields
        #endregion
    }

    /// <exclude />
    public delegate ServiceResult GetResultByIdMethodStateMethodCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        string resultId,
        int timeout,
        ref uint resultHandle,
        ref ResultDataType result,
        ref int error);

    /// <exclude />
    public partial class GetResultByIdMethodStateResult
    {
        public ServiceResult ServiceResult { get; set; }
        public uint ResultHandle { get; set; }
        public ResultDataType Result { get; set; }
        public int Error { get; set; }
    }

    /// <exclude />
    public delegate ValueTask<GetResultByIdMethodStateResult> GetResultByIdMethodStateMethodAsyncCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        string resultId,
        int timeout,
        CancellationToken cancellationToken);
    #endif
    #endregion

    #region GetResultIdListFilteredMethodState Class
    #if (!OPCUA_EXCLUDE_GetResultIdListFilteredMethodState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class GetResultIdListFilteredMethodState : MethodState
    {
        #region Constructors
        public GetResultIdListFilteredMethodState(NodeState parent) : base(parent)
        {
        }

        public new static NodeState Construct(NodeState parent)
        {
            return new GetResultIdListFilteredMethodState(parent);
        }

        #if (!OPCUA_EXCLUDE_InitializationStrings)
        protected override void Initialize(ISystemContext context)
        {
            base.Initialize(context);
            Initialize(context, InitializationString);
            InitializeOptionalChildren(context);
        }

        protected override void InitializeOptionalChildren(ISystemContext context)
        {
            base.InitializeOptionalChildren(context);
        }

        #region Initialization String
        private const string InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGGC" +
           "AAQAAAABACEAAABHZXRSZXN1bHRJZExpc3RGaWx0ZXJlZE1ldGhvZFR5cGUBAQAAAQEAAAEB/////wAA" +
           "AAA=";
        #endregion
        #endif
        #endregion

        #region Event Callbacks
        public GetResultIdListFilteredMethodStateMethodCallHandler OnCall;

        public GetResultIdListFilteredMethodStateMethodAsyncCallHandler OnCallAsync;
        #endregion

        #region Public Properties
        #endregion

        #region Overridden Methods
        protected override ServiceResult Call(
            ISystemContext _context,
            NodeId _objectId,
            IList<object> _inputArguments,
            IList<object> _outputArguments)
        {
            if (OnCall == null)
            {
                return base.Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            ServiceResult _result = null;

            Opc.Ua.ContentFilter filter = (Opc.Ua.ContentFilter)ExtensionObject.ToEncodeable((ExtensionObject)_inputArguments[0]);
            Opc.Ua.RelativePath[] orderedBy = (Opc.Ua.RelativePath[])ExtensionObject.ToArray(_inputArguments[1], typeof(Opc.Ua.RelativePath));
            uint maxResults = (uint)_inputArguments[2];
            int timeout = (int)_inputArguments[3];

            uint resultHandle = (uint)_outputArguments[0];
            string[] resultIdList = (string[])_outputArguments[1];
            int error = (int)_outputArguments[2];

            if (OnCall != null)
            {
                _result = OnCall(
                    _context,
                    this,
                    _objectId,
                    filter,
                    orderedBy,
                    maxResults,
                    timeout,
                    ref resultHandle,
                    ref resultIdList,
                    ref error);
            }

            _outputArguments[0] = resultHandle;
            _outputArguments[1] = resultIdList;
            _outputArguments[2] = error;

            return _result;
        }

        #if (OPCUA_INCLUDE_ASYNC)
        protected override async ValueTask<ServiceResult> CallAsync(
            ISystemContext _context,
            NodeId _objectId,
            IList<object> _inputArguments,
            IList<object> _outputArguments,
            CancellationToken cancellationToken = default)
        {
            if (OnCall == null && OnCallAsync == null)
            {
                return await base.CallAsync(_context, _objectId, _inputArguments, _outputArguments, cancellationToken).ConfigureAwait(false);
            }

            GetResultIdListFilteredMethodStateResult _result = null;

            Opc.Ua.ContentFilter filter = (Opc.Ua.ContentFilter)ExtensionObject.ToEncodeable((ExtensionObject)_inputArguments[0]);
            Opc.Ua.RelativePath[] orderedBy = (Opc.Ua.RelativePath[])ExtensionObject.ToArray(_inputArguments[1], typeof(Opc.Ua.RelativePath));
            uint maxResults = (uint)_inputArguments[2];
            int timeout = (int)_inputArguments[3];

            if (OnCallAsync != null)
            {
                _result = await OnCallAsync(
                    _context,
                    this,
                    _objectId,
                    filter,
                    orderedBy,
                    maxResults,
                    timeout,
                    cancellationToken).ConfigureAwait(false);
            }
            else if (OnCall != null)
            {
                return Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            _outputArguments[0] = _result.ResultHandle;
            _outputArguments[1] = _result.ResultIdList;
            _outputArguments[2] = _result.Error;

            return _result.ServiceResult;
        }
        #endif

        #endregion

        #region Private Fields
        #endregion
    }

    /// <exclude />
    public delegate ServiceResult GetResultIdListFilteredMethodStateMethodCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        Opc.Ua.ContentFilter filter,
        Opc.Ua.RelativePath[] orderedBy,
        uint maxResults,
        int timeout,
        ref uint resultHandle,
        ref string[] resultIdList,
        ref int error);

    /// <exclude />
    public partial class GetResultIdListFilteredMethodStateResult
    {
        public ServiceResult ServiceResult { get; set; }
        public uint ResultHandle { get; set; }
        public string[] ResultIdList { get; set; }
        public int Error { get; set; }
    }

    /// <exclude />
    public delegate ValueTask<GetResultIdListFilteredMethodStateResult> GetResultIdListFilteredMethodStateMethodAsyncCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        Opc.Ua.ContentFilter filter,
        Opc.Ua.RelativePath[] orderedBy,
        uint maxResults,
        int timeout,
        CancellationToken cancellationToken);
    #endif
    #endregion

    #region ReleaseResultHandleMethodState Class
    #if (!OPCUA_EXCLUDE_ReleaseResultHandleMethodState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class ReleaseResultHandleMethodState : MethodState
    {
        #region Constructors
        public ReleaseResultHandleMethodState(NodeState parent) : base(parent)
        {
        }

        public new static NodeState Construct(NodeState parent)
        {
            return new ReleaseResultHandleMethodState(parent);
        }

        #if (!OPCUA_EXCLUDE_InitializationStrings)
        protected override void Initialize(ISystemContext context)
        {
            base.Initialize(context);
            Initialize(context, InitializationString);
            InitializeOptionalChildren(context);
        }

        protected override void InitializeOptionalChildren(ISystemContext context)
        {
            base.InitializeOptionalChildren(context);
        }

        #region Initialization String
        private const string InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGGC" +
           "AAQAAAABAB0AAABSZWxlYXNlUmVzdWx0SGFuZGxlTWV0aG9kVHlwZQEBAAABAQAAAQH/////AAAAAA==";
        #endregion
        #endif
        #endregion

        #region Event Callbacks
        public ReleaseResultHandleMethodStateMethodCallHandler OnCall;

        public ReleaseResultHandleMethodStateMethodAsyncCallHandler OnCallAsync;
        #endregion

        #region Public Properties
        #endregion

        #region Overridden Methods
        protected override ServiceResult Call(
            ISystemContext _context,
            NodeId _objectId,
            IList<object> _inputArguments,
            IList<object> _outputArguments)
        {
            if (OnCall == null)
            {
                return base.Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            ServiceResult _result = null;

            uint resultHandle = (uint)_inputArguments[0];

            int error = (int)_outputArguments[0];

            if (OnCall != null)
            {
                _result = OnCall(
                    _context,
                    this,
                    _objectId,
                    resultHandle,
                    ref error);
            }

            _outputArguments[0] = error;

            return _result;
        }

        #if (OPCUA_INCLUDE_ASYNC)
        protected override async ValueTask<ServiceResult> CallAsync(
            ISystemContext _context,
            NodeId _objectId,
            IList<object> _inputArguments,
            IList<object> _outputArguments,
            CancellationToken cancellationToken = default)
        {
            if (OnCall == null && OnCallAsync == null)
            {
                return await base.CallAsync(_context, _objectId, _inputArguments, _outputArguments, cancellationToken).ConfigureAwait(false);
            }

            ReleaseResultHandleMethodStateResult _result = null;

            uint resultHandle = (uint)_inputArguments[0];

            if (OnCallAsync != null)
            {
                _result = await OnCallAsync(
                    _context,
                    this,
                    _objectId,
                    resultHandle,
                    cancellationToken).ConfigureAwait(false);
            }
            else if (OnCall != null)
            {
                return Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            _outputArguments[0] = _result.Error;

            return _result.ServiceResult;
        }
        #endif

        #endregion

        #region Private Fields
        #endregion
    }

    /// <exclude />
    public delegate ServiceResult ReleaseResultHandleMethodStateMethodCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        uint resultHandle,
        ref int error);

    /// <exclude />
    public partial class ReleaseResultHandleMethodStateResult
    {
        public ServiceResult ServiceResult { get; set; }
        public int Error { get; set; }
    }

    /// <exclude />
    public delegate ValueTask<ReleaseResultHandleMethodStateResult> ReleaseResultHandleMethodStateMethodAsyncCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        uint resultHandle,
        CancellationToken cancellationToken);
    #endif
    #endregion

    #region GenerateFileForReadMethodState Class
    #if (!OPCUA_EXCLUDE_GenerateFileForReadMethodState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class GenerateFileForReadMethodState : MethodState
    {
        #region Constructors
        public GenerateFileForReadMethodState(NodeState parent) : base(parent)
        {
        }

        public new static NodeState Construct(NodeState parent)
        {
            return new GenerateFileForReadMethodState(parent);
        }

        #if (!OPCUA_EXCLUDE_InitializationStrings)
        protected override void Initialize(ISystemContext context)
        {
            base.Initialize(context);
            Initialize(context, InitializationString);
            InitializeOptionalChildren(context);
        }

        protected override void InitializeOptionalChildren(ISystemContext context)
        {
            base.InitializeOptionalChildren(context);
        }

        #region Initialization String
        private const string InitializationString =
           "AQAAAC0AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5L1Jlc3VsdC//////BGGC" +
           "AAQAAAABAB0AAABHZW5lcmF0ZUZpbGVGb3JSZWFkTWV0aG9kVHlwZQEBAAABAQAAAQH/////AAAAAA==";
        #endregion
        #endif
        #endregion

        #region Event Callbacks
        public GenerateFileForReadMethodStateMethodCallHandler OnCall;

        public GenerateFileForReadMethodStateMethodAsyncCallHandler OnCallAsync;
        #endregion

        #region Public Properties
        #endregion

        #region Overridden Methods
        protected override ServiceResult Call(
            ISystemContext _context,
            NodeId _objectId,
            IList<object> _inputArguments,
            IList<object> _outputArguments)
        {
            if (OnCall == null)
            {
                return base.Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            ServiceResult _result = null;

            BaseResultTransferOptionsDataType generateOptions = (BaseResultTransferOptionsDataType)ExtensionObject.ToEncodeable((ExtensionObject)_inputArguments[0]);

            NodeId fileNodeId = (NodeId)_outputArguments[0];
            uint fileHandle = (uint)_outputArguments[1];
            NodeId completionStateMachine = (NodeId)_outputArguments[2];

            if (OnCall != null)
            {
                _result = OnCall(
                    _context,
                    this,
                    _objectId,
                    generateOptions,
                    ref fileNodeId,
                    ref fileHandle,
                    ref completionStateMachine);
            }

            _outputArguments[0] = fileNodeId;
            _outputArguments[1] = fileHandle;
            _outputArguments[2] = completionStateMachine;

            return _result;
        }

        #if (OPCUA_INCLUDE_ASYNC)
        protected override async ValueTask<ServiceResult> CallAsync(
            ISystemContext _context,
            NodeId _objectId,
            IList<object> _inputArguments,
            IList<object> _outputArguments,
            CancellationToken cancellationToken = default)
        {
            if (OnCall == null && OnCallAsync == null)
            {
                return await base.CallAsync(_context, _objectId, _inputArguments, _outputArguments, cancellationToken).ConfigureAwait(false);
            }

            GenerateFileForReadMethodStateResult _result = null;

            BaseResultTransferOptionsDataType generateOptions = (BaseResultTransferOptionsDataType)ExtensionObject.ToEncodeable((ExtensionObject)_inputArguments[0]);

            if (OnCallAsync != null)
            {
                _result = await OnCallAsync(
                    _context,
                    this,
                    _objectId,
                    generateOptions,
                    cancellationToken).ConfigureAwait(false);
            }
            else if (OnCall != null)
            {
                return Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            _outputArguments[0] = _result.FileNodeId;
            _outputArguments[1] = _result.FileHandle;
            _outputArguments[2] = _result.CompletionStateMachine;

            return _result.ServiceResult;
        }
        #endif

        #endregion

        #region Private Fields
        #endregion
    }

    /// <exclude />
    public delegate ServiceResult GenerateFileForReadMethodStateMethodCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        BaseResultTransferOptionsDataType generateOptions,
        ref NodeId fileNodeId,
        ref uint fileHandle,
        ref NodeId completionStateMachine);

    /// <exclude />
    public partial class GenerateFileForReadMethodStateResult
    {
        public ServiceResult ServiceResult { get; set; }
        public NodeId FileNodeId { get; set; }
        public uint FileHandle { get; set; }
        public NodeId CompletionStateMachine { get; set; }
    }

    /// <exclude />
    public delegate ValueTask<GenerateFileForReadMethodStateResult> GenerateFileForReadMethodStateMethodAsyncCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        BaseResultTransferOptionsDataType generateOptions,
        CancellationToken cancellationToken);
    #endif
    #endregion
}