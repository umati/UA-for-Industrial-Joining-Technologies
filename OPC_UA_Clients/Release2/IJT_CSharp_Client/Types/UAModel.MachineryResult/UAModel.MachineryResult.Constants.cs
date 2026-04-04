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
using System.Reflection;
using System.Xml;
using System.Runtime.Serialization;
using Opc.Ua;

#pragma warning disable CS1591 // Missing XML comment for publicly visible type or member
#pragma warning disable CA1707 // Identifiers should not contain underscores

namespace UAModel.MachineryResult
{
    #region DataType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class DataTypes
    {
        public const uint ResultEvaluationEnum = 3002;

        public const uint BaseResultTransferOptionsDataType = 3005;

        public const uint ResultTransferOptionsDataType = 3004;

        public const uint ProcessingTimesDataType = 3006;

        public const uint ResultDataType = 3008;

        public const uint ResultMetaDataType = 3007;
    }
    #endregion

    #region Method Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Methods
    {
        public const uint ResultManagementType_AcknowledgeResults = 7009;

        public const uint ResultManagementType_GetLatestResult = 7008;

        public const uint ResultManagementType_GetResultById = 7005;

        public const uint ResultManagementType_GetResultIdListFiltered = 7006;

        public const uint ResultManagementType_ReleaseResultHandle = 7007;

        public const uint ResultManagementType_ResultTransfer_GenerateFileForRead = 7002;

        public const uint ResultManagementType_ResultTransfer_GenerateFileForWrite = 7004;

        public const uint ResultManagementType_ResultTransfer_CloseAndCommit = 7003;

        public const uint ResultTransferType_GenerateFileForRead = 7001;
    }
    #endregion

    #region Object Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Objects
    {
        public const uint ResultManagementType_Results = 5011;

        public const uint ResultManagementType_ResultTransfer = 5010;

        public const uint ResultTransferOptionsDataType_Encoding_DefaultBinary = 5001;

        public const uint ResultTransferOptionsDataType_Encoding_DefaultXml = 5002;

        public const uint ProcessingTimesDataType_Encoding_DefaultBinary = 5003;

        public const uint ProcessingTimesDataType_Encoding_DefaultXml = 5004;

        public const uint ResultMetaDataType_Encoding_DefaultBinary = 5005;

        public const uint ResultMetaDataType_Encoding_DefaultXml = 5006;

        public const uint ResultDataType_Encoding_DefaultBinary = 5008;

        public const uint ResultDataType_Encoding_DefaultXml = 5009;

        public const uint ResultTransferOptionsDataType_Encoding_DefaultJson = 5012;

        public const uint ProcessingTimesDataType_Encoding_DefaultJson = 5013;

        public const uint ResultDataType_Encoding_DefaultJson = 5014;

        public const uint ResultMetaDataType_Encoding_DefaultJson = 5015;
    }
    #endregion

    #region ObjectType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectTypes
    {
        public const uint ResultReadyEventType = 1002;

        public const uint ResultManagementType = 1004;

        public const uint ResultTransferType = 1003;
    }
    #endregion

    #region Variable Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Variables
    {
        public const uint ResultEvaluationEnum_EnumValues = 6001;

        public const uint ResultType_ReducedResultContent = 6011;

        public const uint ResultType_ResultContent = 6010;

        public const uint ResultType_ResultMetaData = 6009;

        public const uint ResultType_ResultMetaData_CreationTime = 6025;

        public const uint ResultType_ResultMetaData_ExternalConfigurationId = 6022;

        public const uint ResultType_ResultMetaData_ExternalRecipeId = 6019;

        public const uint ResultType_ResultMetaData_FileFormat = 6031;

        public const uint ResultType_ResultMetaData_HasTransferableDataOnFile = 6013;

        public const uint ResultType_ResultMetaData_InternalConfigurationId = 6023;

        public const uint ResultType_ResultMetaData_InternalRecipeId = 6020;

        public const uint ResultType_ResultMetaData_IsPartial = 6014;

        public const uint ResultType_ResultMetaData_IsSimulated = 6015;

        public const uint ResultType_ResultMetaData_JobId = 6024;

        public const uint ResultType_ResultMetaData_PartId = 6018;

        public const uint ResultType_ResultMetaData_ProcessingTimes = 6026;

        public const uint ResultType_ResultMetaData_ProductId = 6021;

        public const uint ResultType_ResultMetaData_ResultEvaluation = 6028;

        public const uint ResultType_ResultMetaData_ResultEvaluationCode = 6030;

        public const uint ResultType_ResultMetaData_ResultEvaluationDetails = 6029;

        public const uint ResultType_ResultMetaData_ResultId = 6012;

        public const uint ResultType_ResultMetaData_ResultState = 6016;

        public const uint ResultType_ResultMetaData_ResultUri = 6027;

        public const uint ResultType_ResultMetaData_StepId = 6017;

        public const uint ResultReadyEventType_Result = 6032;

        public const uint ResultReadyEventType_Result_ResultMetaData = 6033;

        public const uint ResultReadyEventType_Result_ResultMetaData_CreationTime = 6056;

        public const uint ResultReadyEventType_Result_ResultMetaData_ExternalConfigurationId = 6057;

        public const uint ResultReadyEventType_Result_ResultMetaData_ExternalRecipeId = 6058;

        public const uint ResultReadyEventType_Result_ResultMetaData_FileFormat = 6059;

        public const uint ResultReadyEventType_Result_ResultMetaData_HasTransferableDataOnFile = 6060;

        public const uint ResultReadyEventType_Result_ResultMetaData_InternalConfigurationId = 6061;

        public const uint ResultReadyEventType_Result_ResultMetaData_InternalRecipeId = 6062;

        public const uint ResultReadyEventType_Result_ResultMetaData_IsPartial = 6063;

        public const uint ResultReadyEventType_Result_ResultMetaData_IsSimulated = 6064;

        public const uint ResultReadyEventType_Result_ResultMetaData_JobId = 6065;

        public const uint ResultReadyEventType_Result_ResultMetaData_PartId = 6066;

        public const uint ResultReadyEventType_Result_ResultMetaData_ProcessingTimes = 6067;

        public const uint ResultReadyEventType_Result_ResultMetaData_ProductId = 6068;

        public const uint ResultReadyEventType_Result_ResultMetaData_ResultEvaluation = 6069;

        public const uint ResultReadyEventType_Result_ResultMetaData_ResultEvaluationCode = 6070;

        public const uint ResultReadyEventType_Result_ResultMetaData_ResultEvaluationDetails = 6071;

        public const uint ResultReadyEventType_Result_ResultMetaData_ResultId = 6034;

        public const uint ResultReadyEventType_Result_ResultMetaData_ResultState = 6072;

        public const uint ResultReadyEventType_Result_ResultMetaData_ResultUri = 6073;

        public const uint ResultReadyEventType_Result_ResultMetaData_StepId = 6074;

        public const uint ResultManagementType_AcknowledgeResults_InputArguments = 6089;

        public const uint ResultManagementType_AcknowledgeResults_OutputArguments = 6090;

        public const uint ResultManagementType_DefaultInstanceBrowseName = 6037;

        public const uint ResultManagementType_GetLatestResult_InputArguments = 6054;

        public const uint ResultManagementType_GetLatestResult_OutputArguments = 6055;

        public const uint ResultManagementType_GetResultById_InputArguments = 6048;

        public const uint ResultManagementType_GetResultById_OutputArguments = 6049;

        public const uint ResultManagementType_GetResultIdListFiltered_InputArguments = 6050;

        public const uint ResultManagementType_GetResultIdListFiltered_OutputArguments = 6051;

        public const uint ResultManagementType_ReleaseResultHandle_InputArguments = 6052;

        public const uint ResultManagementType_ReleaseResultHandle_OutputArguments = 6053;

        public const uint ResultManagementType_Results_ResultVariable_Placeholder = 6045;

        public const uint ResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData = 6046;

        public const uint ResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData_ResultId = 6047;

        public const uint ResultManagementType_ResultTransfer_ClientProcessingTimeout = 6040;

        public const uint ResultManagementType_ResultTransfer_GenerateFileForRead_InputArguments = 6038;

        public const uint ResultManagementType_ResultTransfer_GenerateFileForRead_OutputArguments = 6039;

        public const uint ResultManagementType_ResultTransfer_GenerateFileForWrite_InputArguments = 6043;

        public const uint ResultManagementType_ResultTransfer_GenerateFileForWrite_OutputArguments = 6044;

        public const uint ResultManagementType_ResultTransfer_CloseAndCommit_InputArguments = 6041;

        public const uint ResultManagementType_ResultTransfer_CloseAndCommit_OutputArguments = 6042;

        public const uint ResultTransferType_GenerateFileForRead_InputArguments = 6035;

        public const uint ResultTransferType_GenerateFileForRead_OutputArguments = 6036;
    }
    #endregion

    #region VariableType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class VariableTypes
    {
        public const uint ResultType = 2001;
    }
    #endregion

    #region DataType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class DataTypeIds
    {
        public static readonly ExpandedNodeId ResultEvaluationEnum = new ExpandedNodeId(UAModel.MachineryResult.DataTypes.ResultEvaluationEnum, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId BaseResultTransferOptionsDataType = new ExpandedNodeId(UAModel.MachineryResult.DataTypes.BaseResultTransferOptionsDataType, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultTransferOptionsDataType = new ExpandedNodeId(UAModel.MachineryResult.DataTypes.ResultTransferOptionsDataType, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ProcessingTimesDataType = new ExpandedNodeId(UAModel.MachineryResult.DataTypes.ProcessingTimesDataType, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultDataType = new ExpandedNodeId(UAModel.MachineryResult.DataTypes.ResultDataType, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultMetaDataType = new ExpandedNodeId(UAModel.MachineryResult.DataTypes.ResultMetaDataType, UAModel.MachineryResult.Namespaces.MachineryResult);
    }
    #endregion

    #region Method Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class MethodIds
    {
        public static readonly ExpandedNodeId ResultManagementType_AcknowledgeResults = new ExpandedNodeId(UAModel.MachineryResult.Methods.ResultManagementType_AcknowledgeResults, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_GetLatestResult = new ExpandedNodeId(UAModel.MachineryResult.Methods.ResultManagementType_GetLatestResult, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_GetResultById = new ExpandedNodeId(UAModel.MachineryResult.Methods.ResultManagementType_GetResultById, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_GetResultIdListFiltered = new ExpandedNodeId(UAModel.MachineryResult.Methods.ResultManagementType_GetResultIdListFiltered, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ReleaseResultHandle = new ExpandedNodeId(UAModel.MachineryResult.Methods.ResultManagementType_ReleaseResultHandle, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ResultTransfer_GenerateFileForRead = new ExpandedNodeId(UAModel.MachineryResult.Methods.ResultManagementType_ResultTransfer_GenerateFileForRead, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ResultTransfer_GenerateFileForWrite = new ExpandedNodeId(UAModel.MachineryResult.Methods.ResultManagementType_ResultTransfer_GenerateFileForWrite, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ResultTransfer_CloseAndCommit = new ExpandedNodeId(UAModel.MachineryResult.Methods.ResultManagementType_ResultTransfer_CloseAndCommit, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultTransferType_GenerateFileForRead = new ExpandedNodeId(UAModel.MachineryResult.Methods.ResultTransferType_GenerateFileForRead, UAModel.MachineryResult.Namespaces.MachineryResult);
    }
    #endregion

    #region Object Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectIds
    {
        public static readonly ExpandedNodeId ResultManagementType_Results = new ExpandedNodeId(UAModel.MachineryResult.Objects.ResultManagementType_Results, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ResultTransfer = new ExpandedNodeId(UAModel.MachineryResult.Objects.ResultManagementType_ResultTransfer, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultTransferOptionsDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.MachineryResult.Objects.ResultTransferOptionsDataType_Encoding_DefaultBinary, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultTransferOptionsDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.MachineryResult.Objects.ResultTransferOptionsDataType_Encoding_DefaultXml, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ProcessingTimesDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.MachineryResult.Objects.ProcessingTimesDataType_Encoding_DefaultBinary, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ProcessingTimesDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.MachineryResult.Objects.ProcessingTimesDataType_Encoding_DefaultXml, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultMetaDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.MachineryResult.Objects.ResultMetaDataType_Encoding_DefaultBinary, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultMetaDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.MachineryResult.Objects.ResultMetaDataType_Encoding_DefaultXml, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.MachineryResult.Objects.ResultDataType_Encoding_DefaultBinary, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.MachineryResult.Objects.ResultDataType_Encoding_DefaultXml, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultTransferOptionsDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.MachineryResult.Objects.ResultTransferOptionsDataType_Encoding_DefaultJson, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ProcessingTimesDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.MachineryResult.Objects.ProcessingTimesDataType_Encoding_DefaultJson, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.MachineryResult.Objects.ResultDataType_Encoding_DefaultJson, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultMetaDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.MachineryResult.Objects.ResultMetaDataType_Encoding_DefaultJson, UAModel.MachineryResult.Namespaces.MachineryResult);
    }
    #endregion

    #region ObjectType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectTypeIds
    {
        public static readonly ExpandedNodeId ResultReadyEventType = new ExpandedNodeId(UAModel.MachineryResult.ObjectTypes.ResultReadyEventType, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType = new ExpandedNodeId(UAModel.MachineryResult.ObjectTypes.ResultManagementType, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultTransferType = new ExpandedNodeId(UAModel.MachineryResult.ObjectTypes.ResultTransferType, UAModel.MachineryResult.Namespaces.MachineryResult);
    }
    #endregion

    #region Variable Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class VariableIds
    {
        public static readonly ExpandedNodeId ResultEvaluationEnum_EnumValues = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultEvaluationEnum_EnumValues, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ReducedResultContent = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ReducedResultContent, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultContent = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultContent, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_CreationTime = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_CreationTime, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_ExternalConfigurationId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_ExternalConfigurationId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_ExternalRecipeId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_ExternalRecipeId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_FileFormat = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_FileFormat, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_HasTransferableDataOnFile = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_HasTransferableDataOnFile, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_InternalConfigurationId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_InternalConfigurationId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_InternalRecipeId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_InternalRecipeId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_IsPartial = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_IsPartial, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_IsSimulated = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_IsSimulated, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_JobId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_JobId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_PartId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_PartId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_ProcessingTimes = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_ProcessingTimes, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_ProductId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_ProductId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_ResultEvaluation = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_ResultEvaluation, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_ResultEvaluationCode = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_ResultEvaluationCode, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_ResultEvaluationDetails = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_ResultEvaluationDetails, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_ResultId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_ResultId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_ResultState = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_ResultState, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_ResultUri = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_ResultUri, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultType_ResultMetaData_StepId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultType_ResultMetaData_StepId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_CreationTime = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_CreationTime, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_ExternalConfigurationId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_ExternalConfigurationId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_ExternalRecipeId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_ExternalRecipeId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_FileFormat = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_FileFormat, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_HasTransferableDataOnFile = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_HasTransferableDataOnFile, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_InternalConfigurationId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_InternalConfigurationId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_InternalRecipeId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_InternalRecipeId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_IsPartial = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_IsPartial, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_IsSimulated = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_IsSimulated, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_JobId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_JobId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_PartId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_PartId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_ProcessingTimes = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_ProcessingTimes, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_ProductId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_ProductId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_ResultEvaluation = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_ResultEvaluation, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_ResultEvaluationCode = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_ResultEvaluationCode, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_ResultEvaluationDetails = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_ResultEvaluationDetails, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_ResultId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_ResultId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_ResultState = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_ResultState, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_ResultUri = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_ResultUri, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultReadyEventType_Result_ResultMetaData_StepId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultReadyEventType_Result_ResultMetaData_StepId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_AcknowledgeResults_InputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_AcknowledgeResults_InputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_AcknowledgeResults_OutputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_AcknowledgeResults_OutputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_DefaultInstanceBrowseName = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_DefaultInstanceBrowseName, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_GetLatestResult_InputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_GetLatestResult_InputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_GetLatestResult_OutputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_GetLatestResult_OutputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_GetResultById_InputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_GetResultById_InputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_GetResultById_OutputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_GetResultById_OutputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_GetResultIdListFiltered_InputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_GetResultIdListFiltered_InputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_GetResultIdListFiltered_OutputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_GetResultIdListFiltered_OutputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ReleaseResultHandle_InputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_ReleaseResultHandle_InputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ReleaseResultHandle_OutputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_ReleaseResultHandle_OutputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_Results_ResultVariable_Placeholder = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_Results_ResultVariable_Placeholder, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData_ResultId = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData_ResultId, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ResultTransfer_ClientProcessingTimeout = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_ResultTransfer_ClientProcessingTimeout, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ResultTransfer_GenerateFileForRead_InputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_ResultTransfer_GenerateFileForRead_InputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ResultTransfer_GenerateFileForRead_OutputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_ResultTransfer_GenerateFileForRead_OutputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ResultTransfer_GenerateFileForWrite_InputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_ResultTransfer_GenerateFileForWrite_InputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ResultTransfer_GenerateFileForWrite_OutputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_ResultTransfer_GenerateFileForWrite_OutputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ResultTransfer_CloseAndCommit_InputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_ResultTransfer_CloseAndCommit_InputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultManagementType_ResultTransfer_CloseAndCommit_OutputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultManagementType_ResultTransfer_CloseAndCommit_OutputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultTransferType_GenerateFileForRead_InputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultTransferType_GenerateFileForRead_InputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);

        public static readonly ExpandedNodeId ResultTransferType_GenerateFileForRead_OutputArguments = new ExpandedNodeId(UAModel.MachineryResult.Variables.ResultTransferType_GenerateFileForRead_OutputArguments, UAModel.MachineryResult.Namespaces.MachineryResult);
    }
    #endregion

    #region VariableType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class VariableTypeIds
    {
        public static readonly ExpandedNodeId ResultType = new ExpandedNodeId(UAModel.MachineryResult.VariableTypes.ResultType, UAModel.MachineryResult.Namespaces.MachineryResult);
    }
    #endregion

    #region BrowseName Declarations
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class BrowseNames
    {
        public const string AcknowledgeResults = "AcknowledgeResults";

        public const string BaseResultTransferOptionsDataType = "BaseResultTransferOptionsDataType";

        public const string CreationTime = "CreationTime";

        public const string ExternalConfigurationId = "ExternalConfigurationId";

        public const string ExternalRecipeId = "ExternalRecipeId";

        public const string FileFormat = "FileFormat";

        public const string GetLatestResult = "GetLatestResult";

        public const string GetResultById = "GetResultById";

        public const string GetResultIdListFiltered = "GetResultIdListFiltered";

        public const string HasTransferableDataOnFile = "HasTransferableDataOnFile";

        public const string InternalConfigurationId = "InternalConfigurationId";

        public const string InternalRecipeId = "InternalRecipeId";

        public const string IsPartial = "IsPartial";

        public const string IsSimulated = "IsSimulated";

        public const string JobId = "JobId";

        public const string PartId = "PartId";

        public const string ProcessingTimes = "ProcessingTimes";

        public const string ProcessingTimesDataType = "ProcessingTimesDataType";

        public const string ProductId = "ProductId";

        public const string ReducedResultContent = "ReducedResultContent";

        public const string ReleaseResultHandle = "ReleaseResultHandle";

        public const string Result = "Result";

        public const string ResultContent = "ResultContent";

        public const string ResultDataType = "ResultDataType";

        public const string ResultEvaluation = "ResultEvaluation";

        public const string ResultEvaluationCode = "ResultEvaluationCode";

        public const string ResultEvaluationDetails = "ResultEvaluationDetails";

        public const string ResultEvaluationEnum = "ResultEvaluationEnum";

        public const string ResultId = "ResultId";

        public const string ResultManagement = "ResultManagement";

        public const string ResultManagementType = "ResultManagementType";

        public const string ResultMetaData = "ResultMetaData";

        public const string ResultMetaDataType = "ResultMetaDataType";

        public const string ResultReadyEventType = "ResultReadyEventType";

        public const string Results = "Results";

        public const string ResultState = "ResultState";

        public const string ResultTransfer = "ResultTransfer";

        public const string ResultTransferOptionsDataType = "ResultTransferOptionsDataType";

        public const string ResultTransferType = "ResultTransferType";

        public const string ResultType = "ResultType";

        public const string ResultUri = "ResultUri";

        public const string ResultVariable_Placeholder = "<ResultVariable>";

        public const string StepId = "StepId";
    }
    #endregion

    #region Namespace Declarations
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Namespaces
    {
        /// <summary>
        /// The URI for the MachineryResult namespace (.NET code namespace is 'UAModel.MachineryResult').
        /// </summary>
        public const string MachineryResult = "http://opcfoundation.org/UA/Machinery/Result/";

        /// <summary>
        /// The URI for the OpcUa namespace (.NET code namespace is 'Opc.Ua').
        /// </summary>
        public const string OpcUa = "http://opcfoundation.org/UA/";
    }
    #endregion
}