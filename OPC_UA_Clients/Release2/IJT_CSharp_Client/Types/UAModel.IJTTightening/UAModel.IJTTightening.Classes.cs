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
using UAModel.DI;
using UAModel.AMB;
using UAModel.IA;
using UAModel.Machinery;
using UAModel.MachineryResult;
using UAModel.IJTBase;

#pragma warning disable CS1591 // Missing XML comment for publicly visible type or member
#pragma warning disable CA1515 // Consider making public types internal
#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1028 // Enum Storage should be Int32

namespace UAModel.IJTTightening
{
    #region ITighteningToolParametersTypeState Class
    #if (!OPCUA_EXCLUDE_ITighteningToolParametersTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class ITighteningToolParametersTypeState : BaseInterfaceState
    {
        #region Constructors
        public ITighteningToolParametersTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IJTTightening.ObjectTypes.ITighteningToolParametersType, UAModel.IJTTightening.Namespaces.IJTTightening, namespaceUris);
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

            if (MaxSpeed != null)
            {
                MaxSpeed.Initialize(context, MaxSpeed_InitializationString);
            }

            if (MaxTorque != null)
            {
                MaxTorque.Initialize(context, MaxTorque_InitializationString);
            }

            if (MinTorque != null)
            {
                MinTorque.Initialize(context, MinTorque_InitializationString);
            }

            if (MotorType != null)
            {
                MotorType.Initialize(context, MotorType_InitializationString);
            }

            if (ShutOffMethod != null)
            {
                ShutOffMethod.Initialize(context, ShutOffMethod_InitializationString);
            }
        }

        #region Initialization String
        private const string MaxSpeed_InitializationString =
           "BwAAACsAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUpUL1RpZ2h0ZW5pbmcvJQAAAGh0dHA6" +
           "Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9JSlQvQmFzZS8mAAAAaHR0cDovL29wY2ZvdW5kYXRpb24ub3Jn" +
           "L1VBL01hY2hpbmVyeS8fAAAAaHR0cDovL29wY2ZvdW5kYXRpb24ub3JnL1VBL0lBLx8AAABodHRwOi8v" +
           "b3BjZm91bmRhdGlvbi5vcmcvVUEvREkvIAAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9BTUIv" +
           "LQAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9NYWNoaW5lcnkvUmVzdWx0L/////81YKkKAgAA" +
           "AAEACAAAAE1heFNwZWVkAQGGFwMAAAAAPAAAAE1heFNwZWVkIGlzIHRoZSBtYXhpbXVtIHJvdGF0aW9u" +
           "IHNwZWVkIG9mIHRoZSBkcml2aW5nIHNoYWZ0LgAvAQLbB4YXAAALAAAAAAAAAAAAC/////8BAf////8C" +
           "AAAANWCpCgIAAAACABAAAABFbmdpbmVlcmluZ1VuaXRzAQGUFwMAAAAAPgAAADA6RW5naW5lZXJpbmdV" +
           "bml0cyBkZWZpbmVzIHRoZSBlbmdpbmVlcmluZyB1bml0IG9mIHRoZSB2YWx1ZXMuAC4ARJQXAAAWAQB5" +
           "AwEKAAAAAAAAAP////8AAAEAdwP/////AQH/////AAAAADVgqQoCAAAAAgAQAAAAUGh5c2ljYWxRdWFu" +
           "dGl0eQEBihcDAAAAAGIAAABQaHlzaWNhbFF1YW50aXR5IGlzIHRvIGRldGVybWluZSB0aGUgdHlwZSBv" +
           "ZiB0aGUgcGh5c2ljYWwgcXVhbnRpdHkgYXNzb2NpYXRlZCB0byBhIGdpdmVuIHZhbHVlKHMpLgAvAQBI" +
           "CYoXAAADAAAD/////wEB/////wEAAAAXYKkKAgAAAAAACwAAAEVudW1TdHJpbmdzAQGLFwAuAESLFwAA" +
           "lR0AAAACBQAAAE9USEVSAgQAAABUSU1FAgYAAABUT1JRVUUCBQAAAEFOR0xFAgcAAABJTVBVTFNFAggA" +
           "AABESVNUQU5DRQIEAAAAQVJFQQIGAAAAVk9MVU1FAgUAAABGT1JDRQIIAAAAUFJFU1NVUkUCBwAAAFZP" +
           "TFRBR0UCBwAAAENVUlJFTlQCCgAAAFJFU0lTVEFOQ0UCBQAAAFBPV0VSAgYAAABFTkVSR1kCBAAAAE1B" +
           "U1MCCwAAAFRFTVBFUkFUVVJFAgkAAABGUkVRVUVOQ1kCBAAAAEpPTFQCCQAAAFZJQlJBVElPTgIGAAAA" +
           "TlVNQkVSAgwAAABMSU5FQVJfU1BFRUQCDQAAAEFOR1VMQVJfU1BFRUQCEwAAAExJTkVBUl9BQ0NFTEVS" +
           "QVRJT04CFAAAAEFOR1VMQVJfQUNDRUxFUkFUSU9OAgwAAABUT1JRVUVfU1BFRUQCEwAAAFRPUlFVRV9B" +
           "Q0NFTEVSQVRJT04CGQAAAFRPUlFVRV9QRVJfQU5HTEVfR1JBRElFTlQCGgAAAFRPUlFVRV9QRVJfQU5H" +
           "TEVfR1JBRElFTlQyABUBAAAAAQAAAAAAAAABAf////8AAAAA";

        private const string MaxTorque_InitializationString =
           "BwAAACsAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUpUL1RpZ2h0ZW5pbmcvJQAAAGh0dHA6" +
           "Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9JSlQvQmFzZS8mAAAAaHR0cDovL29wY2ZvdW5kYXRpb24ub3Jn" +
           "L1VBL01hY2hpbmVyeS8fAAAAaHR0cDovL29wY2ZvdW5kYXRpb24ub3JnL1VBL0lBLx8AAABodHRwOi8v" +
           "b3BjZm91bmRhdGlvbi5vcmcvVUEvREkvIAAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9BTUIv" +
           "LQAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9NYWNoaW5lcnkvUmVzdWx0L/////81YKkKAgAA" +
           "AAEACQAAAE1heFRvcnF1ZQEBhBcDAAAAAI0AAABNYXhUb3JxdWUgaXMgdGhlIG1heGltdW0gYWxsb3dl" +
           "ZCB0b3JxdWUgZm9yIHdoaWNoIHRoZSB0b29sIG1heSBiZSB1c2VkIGZvciB0aWdodGVuaW5nIHByb2Nl" +
           "c3Nlcy4gRm9yIENsaWNrIFdyZW5jaGVzLCBpdCBtYXkgbm90IGJlIGF2YWlsYWJsZS4ALwEC2weEFwAA" +
           "CwAAAAAAAAAAAAv/////AQH/////AgAAADVgqQoCAAAAAgAQAAAARW5naW5lZXJpbmdVbml0cwEBjBcD" +
           "AAAAAD4AAAAwOkVuZ2luZWVyaW5nVW5pdHMgZGVmaW5lcyB0aGUgZW5naW5lZXJpbmcgdW5pdCBvZiB0" +
           "aGUgdmFsdWVzLgAuAESMFwAAFgEAeQMBCgAAAAAAAAD/////AAABAHcD/////wEB/////wAAAAA1YKkK" +
           "AgAAAAIAEAAAAFBoeXNpY2FsUXVhbnRpdHkBAY0XAwAAAABiAAAAUGh5c2ljYWxRdWFudGl0eSBpcyB0" +
           "byBkZXRlcm1pbmUgdGhlIHR5cGUgb2YgdGhlIHBoeXNpY2FsIHF1YW50aXR5IGFzc29jaWF0ZWQgdG8g" +
           "YSBnaXZlbiB2YWx1ZShzKS4ALwEASAmNFwAAAwAAA/////8BAf////8BAAAAF2CpCgIAAAAAAAsAAABF" +
           "bnVtU3RyaW5ncwEBkBcALgBEkBcAAJUdAAAAAgUAAABPVEhFUgIEAAAAVElNRQIGAAAAVE9SUVVFAgUA" +
           "AABBTkdMRQIHAAAASU1QVUxTRQIIAAAARElTVEFOQ0UCBAAAAEFSRUECBgAAAFZPTFVNRQIFAAAARk9S" +
           "Q0UCCAAAAFBSRVNTVVJFAgcAAABWT0xUQUdFAgcAAABDVVJSRU5UAgoAAABSRVNJU1RBTkNFAgUAAABQ" +
           "T1dFUgIGAAAARU5FUkdZAgQAAABNQVNTAgsAAABURU1QRVJBVFVSRQIJAAAARlJFUVVFTkNZAgQAAABK" +
           "T0xUAgkAAABWSUJSQVRJT04CBgAAAE5VTUJFUgIMAAAATElORUFSX1NQRUVEAg0AAABBTkdVTEFSX1NQ" +
           "RUVEAhMAAABMSU5FQVJfQUNDRUxFUkFUSU9OAhQAAABBTkdVTEFSX0FDQ0VMRVJBVElPTgIMAAAAVE9S" +
           "UVVFX1NQRUVEAhMAAABUT1JRVUVfQUNDRUxFUkFUSU9OAhkAAABUT1JRVUVfUEVSX0FOR0xFX0dSQURJ" +
           "RU5UAhoAAABUT1JRVUVfUEVSX0FOR0xFX0dSQURJRU5UMgAVAQAAAAEAAAAAAAAAAQH/////AAAAAA==";

        private const string MinTorque_InitializationString =
           "BwAAACsAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUpUL1RpZ2h0ZW5pbmcvJQAAAGh0dHA6" +
           "Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9JSlQvQmFzZS8mAAAAaHR0cDovL29wY2ZvdW5kYXRpb24ub3Jn" +
           "L1VBL01hY2hpbmVyeS8fAAAAaHR0cDovL29wY2ZvdW5kYXRpb24ub3JnL1VBL0lBLx8AAABodHRwOi8v" +
           "b3BjZm91bmRhdGlvbi5vcmcvVUEvREkvIAAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9BTUIv" +
           "LQAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9NYWNoaW5lcnkvUmVzdWx0L/////81YKkKAgAA" +
           "AAEACQAAAE1pblRvcnF1ZQEBhRcDAAAAAGAAAABNaW5Ub3JxdWUgaXMgdGhlIG1pbmltdW0gYWxsb3dl" +
           "ZCB0b3JxdWUgZm9yIHdoaWNoIHRoZSB0b29sIG1heSBiZSB1c2VkIGZvciB0aWdodGVuaW5nIHByb2Nl" +
           "c3Nlcy4ALwEC2weFFwAACwAAAAAAAAAAAAv/////AQH/////AgAAADVgqQoCAAAAAgAQAAAARW5naW5l" +
           "ZXJpbmdVbml0cwEBiBcDAAAAAD4AAAAwOkVuZ2luZWVyaW5nVW5pdHMgZGVmaW5lcyB0aGUgZW5naW5l" +
           "ZXJpbmcgdW5pdCBvZiB0aGUgdmFsdWVzLgAuAESIFwAAFgEAeQMBCgAAAAAAAAD/////AAABAHcD////" +
           "/wEB/////wAAAAA1YKkKAgAAAAIAEAAAAFBoeXNpY2FsUXVhbnRpdHkBAYkXAwAAAABiAAAAUGh5c2lj" +
           "YWxRdWFudGl0eSBpcyB0byBkZXRlcm1pbmUgdGhlIHR5cGUgb2YgdGhlIHBoeXNpY2FsIHF1YW50aXR5" +
           "IGFzc29jaWF0ZWQgdG8gYSBnaXZlbiB2YWx1ZShzKS4ALwEASAmJFwAAAwAAA/////8BAf////8BAAAA" +
           "F2CpCgIAAAAAAAsAAABFbnVtU3RyaW5ncwEBkRcALgBEkRcAAJUdAAAAAgUAAABPVEhFUgIEAAAAVElN" +
           "RQIGAAAAVE9SUVVFAgUAAABBTkdMRQIHAAAASU1QVUxTRQIIAAAARElTVEFOQ0UCBAAAAEFSRUECBgAA" +
           "AFZPTFVNRQIFAAAARk9SQ0UCCAAAAFBSRVNTVVJFAgcAAABWT0xUQUdFAgcAAABDVVJSRU5UAgoAAABS" +
           "RVNJU1RBTkNFAgUAAABQT1dFUgIGAAAARU5FUkdZAgQAAABNQVNTAgsAAABURU1QRVJBVFVSRQIJAAAA" +
           "RlJFUVVFTkNZAgQAAABKT0xUAgkAAABWSUJSQVRJT04CBgAAAE5VTUJFUgIMAAAATElORUFSX1NQRUVE" +
           "Ag0AAABBTkdVTEFSX1NQRUVEAhMAAABMSU5FQVJfQUNDRUxFUkFUSU9OAhQAAABBTkdVTEFSX0FDQ0VM" +
           "RVJBVElPTgIMAAAAVE9SUVVFX1NQRUVEAhMAAABUT1JRVUVfQUNDRUxFUkFUSU9OAhkAAABUT1JRVUVf" +
           "UEVSX0FOR0xFX0dSQURJRU5UAhoAAABUT1JRVUVfUEVSX0FOR0xFX0dSQURJRU5UMgAVAQAAAAEAAAAA" +
           "AAAAAQH/////AAAAAA==";

        private const string MotorType_InitializationString =
           "BwAAACsAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUpUL1RpZ2h0ZW5pbmcvJQAAAGh0dHA6" +
           "Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9JSlQvQmFzZS8mAAAAaHR0cDovL29wY2ZvdW5kYXRpb24ub3Jn" +
           "L1VBL01hY2hpbmVyeS8fAAAAaHR0cDovL29wY2ZvdW5kYXRpb24ub3JnL1VBL0lBLx8AAABodHRwOi8v" +
           "b3BjZm91bmRhdGlvbi5vcmcvVUEvREkvIAAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9BTUIv" +
           "LQAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9NYWNoaW5lcnkvUmVzdWx0L/////81YKkKAgAA" +
           "AAEACQAAAE1vdG9yVHlwZQEBhxcDAAAAACsAAABNb3RvclR5cGUgaXMgdGhlIHR5cGUgb2YgbW90b3Ig" +
           "aW4gdGhlIHRvb2wuAC8AP4cXAAAMAAAAAAAM/////wEB/////wAAAAA=";

        private const string ShutOffMethod_InitializationString =
           "BwAAACsAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUpUL1RpZ2h0ZW5pbmcvJQAAAGh0dHA6" +
           "Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9JSlQvQmFzZS8mAAAAaHR0cDovL29wY2ZvdW5kYXRpb24ub3Jn" +
           "L1VBL01hY2hpbmVyeS8fAAAAaHR0cDovL29wY2ZvdW5kYXRpb24ub3JnL1VBL0lBLx8AAABodHRwOi8v" +
           "b3BjZm91bmRhdGlvbi5vcmcvVUEvREkvIAAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9BTUIv" +
           "LQAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9NYWNoaW5lcnkvUmVzdWx0L/////81YKkKAgAA" +
           "AAEADQAAAFNodXRPZmZNZXRob2QBAYIXAwAAAABFAAAAU2h1dE9mZk1ldGhvZCBwcm92aWRlcyBpbmZv" +
           "cm1hdGlvbiBvbiB0aGUgc2h1dG9mZiBtZXRob2Qgb2YgdGhlIHRvb2wuAC8BAEgJghcAAAMAAAP/////" +
           "AQH/////AQAAABdgqQoCAAAAAAALAAAARW51bVN0cmluZ3MBAYMXAC4ARIMXAACVBAAAAAIFAAAAT1RI" +
           "RVICCgAAAE1FQ0hBTklDQUwCBwAAAENVUlJFTlQCCgAAAFRSQU5TRFVDRVIAFQEAAAABAAAAAAAAAAEB" +
           "/////wAAAAA=";

        private const string InitializationString =
           "BwAAACsAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUpUL1RpZ2h0ZW5pbmcvJQAAAGh0dHA6" +
           "Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9JSlQvQmFzZS8mAAAAaHR0cDovL29wY2ZvdW5kYXRpb24ub3Jn" +
           "L1VBL01hY2hpbmVyeS8fAAAAaHR0cDovL29wY2ZvdW5kYXRpb24ub3JnL1VBL0lBLx8AAABodHRwOi8v" +
           "b3BjZm91bmRhdGlvbi5vcmcvVUEvREkvIAAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9BTUIv" +
           "LQAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9NYWNoaW5lcnkvUmVzdWx0L/////8EYIACAQAA" +
           "AAEAJQAAAElUaWdodGVuaW5nVG9vbFBhcmFtZXRlcnNUeXBlSW5zdGFuY2UBAesDAQHrA+sDAAD/////" +
           "CAAAADVgqQoCAAAAAQAKAAAARGVzaWduVHlwZQEBdRcDAAAAADoAAABEZXNpZ25UeXBlIHByb3ZpZGVz" +
           "IGluZm9ybWF0aW9uIG9uIHRoZSBkZXNpZ24gb2YgdGhlIFRvb2wuAC8BAEgJdRcAAAMAAAP/////AQH/" +
           "////AQAAABdgqQoCAAAAAAALAAAARW51bVN0cmluZ3MBAXYXAC4ARHYXAACVBgAAAAIFAAAAT1RIRVIC" +
           "BgAAAFBJU1RPTAIFAAAAQU5HTEUCCAAAAFNUUkFJR0hUAgYAAABPRkZTRVQCDgAAAFJFVkVSU0VfT0ZG" +
           "U0VUABUBAAAAAQAAAAAAAAABAf////8AAAAANWCpCgIAAAABAAsAAABEcml2ZU1ldGhvZAEBfhcDAAAA" +
           "AE4AAABEcml2ZU1ldGhvZCBwcm92aWRlcyBpbmZvcm1hdGlvbiBvbiB0aGUgZHJpdmUgbWV0aG9kIG9m" +
           "IHRoZSBtb3RvciBvZiB0aGUgVG9vbC4ALwEASAl+FwAAAwAAA/////8BAf////8BAAAAF2CpCgIAAAAA" +
           "AAsAAABFbnVtU3RyaW5ncwEBfxcALgBEfxcAAJUIAAAAAgUAAABPVEhFUgIKAAAAQ09OVElOVU9VUwIF" +
           "AAAAUFVMU0UCCgAAAFJBVENIRVRJTkcCCgAAAFRFTlNJT05JTkcCBgAAAE1BTlVBTAIHAAAASU5FUlRJ" +
           "QQIGAAAASFlCUklEABUBAAAAAQAAAAAAAAABAf////8AAAAANWCpCgIAAAABAAkAAABEcml2ZVR5cGUB" +
           "AYAXAwAAAAA9AAAARHJpdmVUeXBlIHByb3ZpZGVzIGluZm9ybWF0aW9uIG9uIHRoZSBkcml2ZSB0eXBl" +
           "IG9mIHRoZSBUb29sLgAvAQBICYAXAAADAAAD/////wEB/////wEAAAAXYKkKAgAAAAAACwAAAEVudW1T" +
           "dHJpbmdzAQGBFwAuAESBFwAAlQUAAAACBQAAAE9USEVSAggAAABFTEVDVFJJQwIJAAAASFlEUkFVTElD" +
           "AgkAAABQTkVVTUFUSUMCBgAAAE1BTlVBTAAVAQAAAAEAAAAAAAAAAQH/////AAAAADVgqQoCAAAAAQAI" +
           "AAAATWF4U3BlZWQBAYYXAwAAAAA8AAAATWF4U3BlZWQgaXMgdGhlIG1heGltdW0gcm90YXRpb24gc3Bl" +
           "ZWQgb2YgdGhlIGRyaXZpbmcgc2hhZnQuAC8BAtsHhhcAAAsAAAAAAAAAAAAL/////wEB/////wIAAAA1" +
           "YKkKAgAAAAIAEAAAAEVuZ2luZWVyaW5nVW5pdHMBAZQXAwAAAAA+AAAAMDpFbmdpbmVlcmluZ1VuaXRz" +
           "IGRlZmluZXMgdGhlIGVuZ2luZWVyaW5nIHVuaXQgb2YgdGhlIHZhbHVlcy4ALgBElBcAABYBAHkDAQoA" +
           "AAAAAAAA/////wAAAQB3A/////8BAf////8AAAAANWCpCgIAAAACABAAAABQaHlzaWNhbFF1YW50aXR5" +
           "AQGKFwMAAAAAYgAAAFBoeXNpY2FsUXVhbnRpdHkgaXMgdG8gZGV0ZXJtaW5lIHRoZSB0eXBlIG9mIHRo" +
           "ZSBwaHlzaWNhbCBxdWFudGl0eSBhc3NvY2lhdGVkIHRvIGEgZ2l2ZW4gdmFsdWUocykuAC8BAEgJihcA" +
           "AAMAAAP/////AQH/////AQAAABdgqQoCAAAAAAALAAAARW51bVN0cmluZ3MBAYsXAC4ARIsXAACVHQAA" +
           "AAIFAAAAT1RIRVICBAAAAFRJTUUCBgAAAFRPUlFVRQIFAAAAQU5HTEUCBwAAAElNUFVMU0UCCAAAAERJ" +
           "U1RBTkNFAgQAAABBUkVBAgYAAABWT0xVTUUCBQAAAEZPUkNFAggAAABQUkVTU1VSRQIHAAAAVk9MVEFH" +
           "RQIHAAAAQ1VSUkVOVAIKAAAAUkVTSVNUQU5DRQIFAAAAUE9XRVICBgAAAEVORVJHWQIEAAAATUFTUwIL" +
           "AAAAVEVNUEVSQVRVUkUCCQAAAEZSRVFVRU5DWQIEAAAASk9MVAIJAAAAVklCUkFUSU9OAgYAAABOVU1C" +
           "RVICDAAAAExJTkVBUl9TUEVFRAINAAAAQU5HVUxBUl9TUEVFRAITAAAATElORUFSX0FDQ0VMRVJBVElP" +
           "TgIUAAAAQU5HVUxBUl9BQ0NFTEVSQVRJT04CDAAAAFRPUlFVRV9TUEVFRAITAAAAVE9SUVVFX0FDQ0VM" +
           "RVJBVElPTgIZAAAAVE9SUVVFX1BFUl9BTkdMRV9HUkFESUVOVAIaAAAAVE9SUVVFX1BFUl9BTkdMRV9H" +
           "UkFESUVOVDIAFQEAAAABAAAAAAAAAAEB/////wAAAAA1YKkKAgAAAAEACQAAAE1heFRvcnF1ZQEBhBcD" +
           "AAAAAI0AAABNYXhUb3JxdWUgaXMgdGhlIG1heGltdW0gYWxsb3dlZCB0b3JxdWUgZm9yIHdoaWNoIHRo" +
           "ZSB0b29sIG1heSBiZSB1c2VkIGZvciB0aWdodGVuaW5nIHByb2Nlc3Nlcy4gRm9yIENsaWNrIFdyZW5j" +
           "aGVzLCBpdCBtYXkgbm90IGJlIGF2YWlsYWJsZS4ALwEC2weEFwAACwAAAAAAAAAAAAv/////AQH/////" +
           "AgAAADVgqQoCAAAAAgAQAAAARW5naW5lZXJpbmdVbml0cwEBjBcDAAAAAD4AAAAwOkVuZ2luZWVyaW5n" +
           "VW5pdHMgZGVmaW5lcyB0aGUgZW5naW5lZXJpbmcgdW5pdCBvZiB0aGUgdmFsdWVzLgAuAESMFwAAFgEA" +
           "eQMBCgAAAAAAAAD/////AAABAHcD/////wEB/////wAAAAA1YKkKAgAAAAIAEAAAAFBoeXNpY2FsUXVh" +
           "bnRpdHkBAY0XAwAAAABiAAAAUGh5c2ljYWxRdWFudGl0eSBpcyB0byBkZXRlcm1pbmUgdGhlIHR5cGUg" +
           "b2YgdGhlIHBoeXNpY2FsIHF1YW50aXR5IGFzc29jaWF0ZWQgdG8gYSBnaXZlbiB2YWx1ZShzKS4ALwEA" +
           "SAmNFwAAAwAAA/////8BAf////8BAAAAF2CpCgIAAAAAAAsAAABFbnVtU3RyaW5ncwEBkBcALgBEkBcA" +
           "AJUdAAAAAgUAAABPVEhFUgIEAAAAVElNRQIGAAAAVE9SUVVFAgUAAABBTkdMRQIHAAAASU1QVUxTRQII" +
           "AAAARElTVEFOQ0UCBAAAAEFSRUECBgAAAFZPTFVNRQIFAAAARk9SQ0UCCAAAAFBSRVNTVVJFAgcAAABW" +
           "T0xUQUdFAgcAAABDVVJSRU5UAgoAAABSRVNJU1RBTkNFAgUAAABQT1dFUgIGAAAARU5FUkdZAgQAAABN" +
           "QVNTAgsAAABURU1QRVJBVFVSRQIJAAAARlJFUVVFTkNZAgQAAABKT0xUAgkAAABWSUJSQVRJT04CBgAA" +
           "AE5VTUJFUgIMAAAATElORUFSX1NQRUVEAg0AAABBTkdVTEFSX1NQRUVEAhMAAABMSU5FQVJfQUNDRUxF" +
           "UkFUSU9OAhQAAABBTkdVTEFSX0FDQ0VMRVJBVElPTgIMAAAAVE9SUVVFX1NQRUVEAhMAAABUT1JRVUVf" +
           "QUNDRUxFUkFUSU9OAhkAAABUT1JRVUVfUEVSX0FOR0xFX0dSQURJRU5UAhoAAABUT1JRVUVfUEVSX0FO" +
           "R0xFX0dSQURJRU5UMgAVAQAAAAEAAAAAAAAAAQH/////AAAAADVgqQoCAAAAAQAJAAAATWluVG9ycXVl" +
           "AQGFFwMAAAAAYAAAAE1pblRvcnF1ZSBpcyB0aGUgbWluaW11bSBhbGxvd2VkIHRvcnF1ZSBmb3Igd2hp" +
           "Y2ggdGhlIHRvb2wgbWF5IGJlIHVzZWQgZm9yIHRpZ2h0ZW5pbmcgcHJvY2Vzc2VzLgAvAQLbB4UXAAAL" +
           "AAAAAAAAAAAAC/////8BAf////8CAAAANWCpCgIAAAACABAAAABFbmdpbmVlcmluZ1VuaXRzAQGIFwMA" +
           "AAAAPgAAADA6RW5naW5lZXJpbmdVbml0cyBkZWZpbmVzIHRoZSBlbmdpbmVlcmluZyB1bml0IG9mIHRo" +
           "ZSB2YWx1ZXMuAC4ARIgXAAAWAQB5AwEKAAAAAAAAAP////8AAAEAdwP/////AQH/////AAAAADVgqQoC" +
           "AAAAAgAQAAAAUGh5c2ljYWxRdWFudGl0eQEBiRcDAAAAAGIAAABQaHlzaWNhbFF1YW50aXR5IGlzIHRv" +
           "IGRldGVybWluZSB0aGUgdHlwZSBvZiB0aGUgcGh5c2ljYWwgcXVhbnRpdHkgYXNzb2NpYXRlZCB0byBh" +
           "IGdpdmVuIHZhbHVlKHMpLgAvAQBICYkXAAADAAAD/////wEB/////wEAAAAXYKkKAgAAAAAACwAAAEVu" +
           "dW1TdHJpbmdzAQGRFwAuAESRFwAAlR0AAAACBQAAAE9USEVSAgQAAABUSU1FAgYAAABUT1JRVUUCBQAA" +
           "AEFOR0xFAgcAAABJTVBVTFNFAggAAABESVNUQU5DRQIEAAAAQVJFQQIGAAAAVk9MVU1FAgUAAABGT1JD" +
           "RQIIAAAAUFJFU1NVUkUCBwAAAFZPTFRBR0UCBwAAAENVUlJFTlQCCgAAAFJFU0lTVEFOQ0UCBQAAAFBP" +
           "V0VSAgYAAABFTkVSR1kCBAAAAE1BU1MCCwAAAFRFTVBFUkFUVVJFAgkAAABGUkVRVUVOQ1kCBAAAAEpP" +
           "TFQCCQAAAFZJQlJBVElPTgIGAAAATlVNQkVSAgwAAABMSU5FQVJfU1BFRUQCDQAAAEFOR1VMQVJfU1BF" +
           "RUQCEwAAAExJTkVBUl9BQ0NFTEVSQVRJT04CFAAAAEFOR1VMQVJfQUNDRUxFUkFUSU9OAgwAAABUT1JR" +
           "VUVfU1BFRUQCEwAAAFRPUlFVRV9BQ0NFTEVSQVRJT04CGQAAAFRPUlFVRV9QRVJfQU5HTEVfR1JBRElF" +
           "TlQCGgAAAFRPUlFVRV9QRVJfQU5HTEVfR1JBRElFTlQyABUBAAAAAQAAAAAAAAABAf////8AAAAANWCp" +
           "CgIAAAABAAkAAABNb3RvclR5cGUBAYcXAwAAAAArAAAATW90b3JUeXBlIGlzIHRoZSB0eXBlIG9mIG1v" +
           "dG9yIGluIHRoZSB0b29sLgAvAD+HFwAADAAAAAAADP////8BAf////8AAAAANWCpCgIAAAABAA0AAABT" +
           "aHV0T2ZmTWV0aG9kAQGCFwMAAAAARQAAAFNodXRPZmZNZXRob2QgcHJvdmlkZXMgaW5mb3JtYXRpb24g" +
           "b24gdGhlIHNodXRvZmYgbWV0aG9kIG9mIHRoZSB0b29sLgAvAQBICYIXAAADAAAD/////wEB/////wEA" +
           "AAAXYKkKAgAAAAAACwAAAEVudW1TdHJpbmdzAQGDFwAuAESDFwAAlQQAAAACBQAAAE9USEVSAgoAAABN" +
           "RUNIQU5JQ0FMAgcAAABDVVJSRU5UAgoAAABUUkFOU0RVQ0VSABUBAAAAAQAAAAAAAAABAf////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public MultiStateDiscreteState<byte> DesignType
        {
            get => m_designType;

            set
            {
                if (!Object.ReferenceEquals(m_designType, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_designType = value;
            }
        }

        public MultiStateDiscreteState<byte> DriveMethod
        {
            get => m_driveMethod;

            set
            {
                if (!Object.ReferenceEquals(m_driveMethod, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_driveMethod = value;
            }
        }

        public MultiStateDiscreteState<byte> DriveType
        {
            get => m_driveType;

            set
            {
                if (!Object.ReferenceEquals(m_driveType, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_driveType = value;
            }
        }

        public JoiningDataVariableTypeState<double> MaxSpeed
        {
            get => m_maxSpeed;

            set
            {
                if (!Object.ReferenceEquals(m_maxSpeed, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_maxSpeed = value;
            }
        }

        public JoiningDataVariableTypeState<double> MaxTorque
        {
            get => m_maxTorque;

            set
            {
                if (!Object.ReferenceEquals(m_maxTorque, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_maxTorque = value;
            }
        }

        public JoiningDataVariableTypeState<double> MinTorque
        {
            get => m_minTorque;

            set
            {
                if (!Object.ReferenceEquals(m_minTorque, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_minTorque = value;
            }
        }

        public BaseDataVariableState<string> MotorType
        {
            get => m_motorType;

            set
            {
                if (!Object.ReferenceEquals(m_motorType, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_motorType = value;
            }
        }

        public MultiStateDiscreteState<byte> ShutOffMethod
        {
            get => m_shutOffMethod;

            set
            {
                if (!Object.ReferenceEquals(m_shutOffMethod, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_shutOffMethod = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_designType != null)
            {
                children.Add(m_designType);
            }

            if (m_driveMethod != null)
            {
                children.Add(m_driveMethod);
            }

            if (m_driveType != null)
            {
                children.Add(m_driveType);
            }

            if (m_maxSpeed != null)
            {
                children.Add(m_maxSpeed);
            }

            if (m_maxTorque != null)
            {
                children.Add(m_maxTorque);
            }

            if (m_minTorque != null)
            {
                children.Add(m_minTorque);
            }

            if (m_motorType != null)
            {
                children.Add(m_motorType);
            }

            if (m_shutOffMethod != null)
            {
                children.Add(m_shutOffMethod);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_designType, child))
            {
                m_designType = null;
                return;
            }

            if (Object.ReferenceEquals(m_driveMethod, child))
            {
                m_driveMethod = null;
                return;
            }

            if (Object.ReferenceEquals(m_driveType, child))
            {
                m_driveType = null;
                return;
            }

            if (Object.ReferenceEquals(m_maxSpeed, child))
            {
                m_maxSpeed = null;
                return;
            }

            if (Object.ReferenceEquals(m_maxTorque, child))
            {
                m_maxTorque = null;
                return;
            }

            if (Object.ReferenceEquals(m_minTorque, child))
            {
                m_minTorque = null;
                return;
            }

            if (Object.ReferenceEquals(m_motorType, child))
            {
                m_motorType = null;
                return;
            }

            if (Object.ReferenceEquals(m_shutOffMethod, child))
            {
                m_shutOffMethod = null;
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
                case UAModel.IJTTightening.BrowseNames.DesignType:
                {
                    if (createOrReplace)
                    {
                        if (DesignType == null)
                        {
                            if (replacement == null)
                            {
                                DesignType = new MultiStateDiscreteState<byte>(this);
                            }
                            else
                            {
                                DesignType = (MultiStateDiscreteState<byte>)replacement;
                            }
                        }
                    }

                    instance = DesignType;
                    break;
                }

                case UAModel.IJTTightening.BrowseNames.DriveMethod:
                {
                    if (createOrReplace)
                    {
                        if (DriveMethod == null)
                        {
                            if (replacement == null)
                            {
                                DriveMethod = new MultiStateDiscreteState<byte>(this);
                            }
                            else
                            {
                                DriveMethod = (MultiStateDiscreteState<byte>)replacement;
                            }
                        }
                    }

                    instance = DriveMethod;
                    break;
                }

                case UAModel.IJTTightening.BrowseNames.DriveType:
                {
                    if (createOrReplace)
                    {
                        if (DriveType == null)
                        {
                            if (replacement == null)
                            {
                                DriveType = new MultiStateDiscreteState<byte>(this);
                            }
                            else
                            {
                                DriveType = (MultiStateDiscreteState<byte>)replacement;
                            }
                        }
                    }

                    instance = DriveType;
                    break;
                }

                case UAModel.IJTTightening.BrowseNames.MaxSpeed:
                {
                    if (createOrReplace)
                    {
                        if (MaxSpeed == null)
                        {
                            if (replacement == null)
                            {
                                MaxSpeed = new JoiningDataVariableTypeState<double>(this);
                            }
                            else
                            {
                                MaxSpeed = (JoiningDataVariableTypeState<double>)replacement;
                            }
                        }
                    }

                    instance = MaxSpeed;
                    break;
                }

                case UAModel.IJTTightening.BrowseNames.MaxTorque:
                {
                    if (createOrReplace)
                    {
                        if (MaxTorque == null)
                        {
                            if (replacement == null)
                            {
                                MaxTorque = new JoiningDataVariableTypeState<double>(this);
                            }
                            else
                            {
                                MaxTorque = (JoiningDataVariableTypeState<double>)replacement;
                            }
                        }
                    }

                    instance = MaxTorque;
                    break;
                }

                case UAModel.IJTTightening.BrowseNames.MinTorque:
                {
                    if (createOrReplace)
                    {
                        if (MinTorque == null)
                        {
                            if (replacement == null)
                            {
                                MinTorque = new JoiningDataVariableTypeState<double>(this);
                            }
                            else
                            {
                                MinTorque = (JoiningDataVariableTypeState<double>)replacement;
                            }
                        }
                    }

                    instance = MinTorque;
                    break;
                }

                case UAModel.IJTTightening.BrowseNames.MotorType:
                {
                    if (createOrReplace)
                    {
                        if (MotorType == null)
                        {
                            if (replacement == null)
                            {
                                MotorType = new BaseDataVariableState<string>(this);
                            }
                            else
                            {
                                MotorType = (BaseDataVariableState<string>)replacement;
                            }
                        }
                    }

                    instance = MotorType;
                    break;
                }

                case UAModel.IJTTightening.BrowseNames.ShutOffMethod:
                {
                    if (createOrReplace)
                    {
                        if (ShutOffMethod == null)
                        {
                            if (replacement == null)
                            {
                                ShutOffMethod = new MultiStateDiscreteState<byte>(this);
                            }
                            else
                            {
                                ShutOffMethod = (MultiStateDiscreteState<byte>)replacement;
                            }
                        }
                    }

                    instance = ShutOffMethod;
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
        private MultiStateDiscreteState<byte> m_designType;
        private MultiStateDiscreteState<byte> m_driveMethod;
        private MultiStateDiscreteState<byte> m_driveType;
        private JoiningDataVariableTypeState<double> m_maxSpeed;
        private JoiningDataVariableTypeState<double> m_maxTorque;
        private JoiningDataVariableTypeState<double> m_minTorque;
        private BaseDataVariableState<string> m_motorType;
        private MultiStateDiscreteState<byte> m_shutOffMethod;
        #endregion
    }
    #endif
    #endregion
}