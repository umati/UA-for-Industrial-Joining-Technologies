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

namespace UAModel.AMB
{
    #region DataType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class DataTypes
    {
        public const uint MaintenanceMethodEnum = 3004;

        public const uint NameNodeIdDataType = 3003;

        public const uint RootCauseDataType = 3002;
    }
    #endregion

    #region Method Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Methods
    {
        public const uint DocumentationLinksType_AddLink = 7004;

        public const uint DocumentationLinksType_RemoveLink = 7005;

        public const uint Assets_FindAlias = 7001;

        public const uint AssetsByAssetId_FindAlias = 7003;

        public const uint AssetsByProductInstanceUri_FindAlias = 7002;
    }
    #endregion

    #region Object Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Objects
    {
        public const uint IMaintenanceEventType_MaintenanceState = 5014;

        public const uint MaintenanceEventStateMachineType_Executing = 5007;

        public const uint MaintenanceEventStateMachineType_Finished = 5008;

        public const uint MaintenanceEventStateMachineType_FromExecutingToFinished = 5010;

        public const uint MaintenanceEventStateMachineType_FromFinishedToPlanned = 5011;

        public const uint MaintenanceEventStateMachineType_FromPlannedToExecuting = 5009;

        public const uint MaintenanceEventStateMachineType_Planned = 5006;

        public const uint Assets = 5002;

        public const uint AssetsByAssetId = 5004;

        public const uint AssetsByProductInstanceUri = 5003;

        public const uint HierarchicalLocations = 5021;

        public const uint OperationalLocations = 5022;

        public const uint RootCauseDataType_Encoding_DefaultBinary = 5001;

        public const uint RootCauseDataType_Encoding_DefaultXml = 5005;

        public const uint NameNodeIdDataType_Encoding_DefaultBinary = 5012;

        public const uint NameNodeIdDataType_Encoding_DefaultXml = 5013;
    }
    #endregion

    #region ObjectType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectTypes
    {
        public const uint CalibrationDueConditionClassType = 1005;

        public const uint ExternalCheckConditionClassType = 1015;

        public const uint FlashUpdateInProgressConditionClassType = 1007;

        public const uint ImprovementConditionClassType = 1018;

        public const uint InspectionConditionClassType = 1014;

        public const uint RepairConditionClassType = 1017;

        public const uint ServicingConditionClassType = 1016;

        public const uint BadConfigurationConditionClassType = 1008;

        public const uint ConnectionFailureConditionClassType = 1003;

        public const uint FlashUpdateFailedConditionClassType = 1019;

        public const uint OutOfResourcesConditionClassType = 1009;

        public const uint OutOfMemoryConditionClassType = 1010;

        public const uint OverTemperatureConditionClassType = 1004;

        public const uint SelfTestFailureConditionClassType = 1006;

        public const uint IMaintenanceEventType = 1012;

        public const uint IRootCauseIndicationType = 1002;

        public const uint DocumentationLinksType = 1011;

        public const uint MaintenanceEventStateMachineType = 1013;
    }
    #endregion

    #region ReferenceType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ReferenceTypes
    {
        public const uint Contains = 4002;

        public const uint HierarchicalContains = 4003;

        public const uint OperationalContains = 4004;
    }
    #endregion

    #region Variable Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Variables
    {
        public const uint MaintenanceMethodEnum_EnumValues = 6029;

        public const uint IMaintenanceEventType_ConfigurationChanged = 6042;

        public const uint IMaintenanceEventType_EstimatedDowntime = 6036;

        public const uint IMaintenanceEventType_MaintenanceMethod = 6041;

        public const uint IMaintenanceEventType_MaintenanceState_CurrentState = 6033;

        public const uint IMaintenanceEventType_MaintenanceState_CurrentState_Id = 6034;

        public const uint IMaintenanceEventType_MaintenanceSupplier = 6037;

        public const uint IMaintenanceEventType_PartsOfAssetReplaced = 6039;

        public const uint IMaintenanceEventType_PartsOfAssetServiced = 6040;

        public const uint IMaintenanceEventType_PlannedDate = 6035;

        public const uint IMaintenanceEventType_QualificationOfPersonnel = 6038;

        public const uint IRootCauseIndicationType_PotentialRootCauses = 6015;

        public const uint DocumentationLinksType_Link_Placeholder = 6017;

        public const uint DocumentationLinksType_AddLink_InputArguments = 6018;

        public const uint DocumentationLinksType_AddLink_OutputArguments = 6019;

        public const uint DocumentationLinksType_DefaultInstanceBrowseName = 6016;

        public const uint DocumentationLinksType_RemoveLink_InputArguments = 6020;

        public const uint MaintenanceEventStateMachineType_Executing_StateNumber = 6022;

        public const uint MaintenanceEventStateMachineType_Finished_StateNumber = 6023;

        public const uint MaintenanceEventStateMachineType_FromExecutingToFinished_TransitionNumber = 6025;

        public const uint MaintenanceEventStateMachineType_FromFinishedToPlanned_TransitionNumber = 6026;

        public const uint MaintenanceEventStateMachineType_FromPlannedToExecuting_TransitionNumber = 6024;

        public const uint MaintenanceEventStateMachineType_Planned_StateNumber = 6021;

        public const uint Assets_FindAlias_InputArguments = 6001;

        public const uint Assets_FindAlias_OutputArguments = 6002;

        public const uint AssetsByAssetId_FindAlias_InputArguments = 6006;

        public const uint AssetsByAssetId_FindAlias_OutputArguments = 6007;

        public const uint AssetsByProductInstanceUri_FindAlias_InputArguments = 6003;

        public const uint AssetsByProductInstanceUri_FindAlias_OutputArguments = 6004;
    }
    #endregion

    #region DataType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class DataTypeIds
    {
        public static readonly ExpandedNodeId MaintenanceMethodEnum = new ExpandedNodeId(UAModel.AMB.DataTypes.MaintenanceMethodEnum, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId NameNodeIdDataType = new ExpandedNodeId(UAModel.AMB.DataTypes.NameNodeIdDataType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId RootCauseDataType = new ExpandedNodeId(UAModel.AMB.DataTypes.RootCauseDataType, UAModel.AMB.Namespaces.AMB);
    }
    #endregion

    #region Method Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class MethodIds
    {
        public static readonly ExpandedNodeId DocumentationLinksType_AddLink = new ExpandedNodeId(UAModel.AMB.Methods.DocumentationLinksType_AddLink, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId DocumentationLinksType_RemoveLink = new ExpandedNodeId(UAModel.AMB.Methods.DocumentationLinksType_RemoveLink, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId Assets_FindAlias = new ExpandedNodeId(UAModel.AMB.Methods.Assets_FindAlias, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId AssetsByAssetId_FindAlias = new ExpandedNodeId(UAModel.AMB.Methods.AssetsByAssetId_FindAlias, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId AssetsByProductInstanceUri_FindAlias = new ExpandedNodeId(UAModel.AMB.Methods.AssetsByProductInstanceUri_FindAlias, UAModel.AMB.Namespaces.AMB);
    }
    #endregion

    #region Object Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectIds
    {
        public static readonly ExpandedNodeId IMaintenanceEventType_MaintenanceState = new ExpandedNodeId(UAModel.AMB.Objects.IMaintenanceEventType_MaintenanceState, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId MaintenanceEventStateMachineType_Executing = new ExpandedNodeId(UAModel.AMB.Objects.MaintenanceEventStateMachineType_Executing, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId MaintenanceEventStateMachineType_Finished = new ExpandedNodeId(UAModel.AMB.Objects.MaintenanceEventStateMachineType_Finished, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId MaintenanceEventStateMachineType_FromExecutingToFinished = new ExpandedNodeId(UAModel.AMB.Objects.MaintenanceEventStateMachineType_FromExecutingToFinished, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId MaintenanceEventStateMachineType_FromFinishedToPlanned = new ExpandedNodeId(UAModel.AMB.Objects.MaintenanceEventStateMachineType_FromFinishedToPlanned, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId MaintenanceEventStateMachineType_FromPlannedToExecuting = new ExpandedNodeId(UAModel.AMB.Objects.MaintenanceEventStateMachineType_FromPlannedToExecuting, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId MaintenanceEventStateMachineType_Planned = new ExpandedNodeId(UAModel.AMB.Objects.MaintenanceEventStateMachineType_Planned, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId Assets = new ExpandedNodeId(UAModel.AMB.Objects.Assets, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId AssetsByAssetId = new ExpandedNodeId(UAModel.AMB.Objects.AssetsByAssetId, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId AssetsByProductInstanceUri = new ExpandedNodeId(UAModel.AMB.Objects.AssetsByProductInstanceUri, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId HierarchicalLocations = new ExpandedNodeId(UAModel.AMB.Objects.HierarchicalLocations, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId OperationalLocations = new ExpandedNodeId(UAModel.AMB.Objects.OperationalLocations, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId RootCauseDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.AMB.Objects.RootCauseDataType_Encoding_DefaultBinary, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId RootCauseDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.AMB.Objects.RootCauseDataType_Encoding_DefaultXml, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId NameNodeIdDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.AMB.Objects.NameNodeIdDataType_Encoding_DefaultBinary, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId NameNodeIdDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.AMB.Objects.NameNodeIdDataType_Encoding_DefaultXml, UAModel.AMB.Namespaces.AMB);
    }
    #endregion

    #region ObjectType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectTypeIds
    {
        public static readonly ExpandedNodeId CalibrationDueConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.CalibrationDueConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId ExternalCheckConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.ExternalCheckConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId FlashUpdateInProgressConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.FlashUpdateInProgressConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId ImprovementConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.ImprovementConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId InspectionConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.InspectionConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId RepairConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.RepairConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId ServicingConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.ServicingConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId BadConfigurationConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.BadConfigurationConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId ConnectionFailureConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.ConnectionFailureConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId FlashUpdateFailedConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.FlashUpdateFailedConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId OutOfResourcesConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.OutOfResourcesConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId OutOfMemoryConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.OutOfMemoryConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId OverTemperatureConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.OverTemperatureConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId SelfTestFailureConditionClassType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.SelfTestFailureConditionClassType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId IMaintenanceEventType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.IMaintenanceEventType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId IRootCauseIndicationType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.IRootCauseIndicationType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId DocumentationLinksType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.DocumentationLinksType, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId MaintenanceEventStateMachineType = new ExpandedNodeId(UAModel.AMB.ObjectTypes.MaintenanceEventStateMachineType, UAModel.AMB.Namespaces.AMB);
    }
    #endregion

    #region ReferenceType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ReferenceTypeIds
    {
        public static readonly ExpandedNodeId Contains = new ExpandedNodeId(UAModel.AMB.ReferenceTypes.Contains, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId HierarchicalContains = new ExpandedNodeId(UAModel.AMB.ReferenceTypes.HierarchicalContains, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId OperationalContains = new ExpandedNodeId(UAModel.AMB.ReferenceTypes.OperationalContains, UAModel.AMB.Namespaces.AMB);
    }
    #endregion

    #region Variable Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class VariableIds
    {
        public static readonly ExpandedNodeId MaintenanceMethodEnum_EnumValues = new ExpandedNodeId(UAModel.AMB.Variables.MaintenanceMethodEnum_EnumValues, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId IMaintenanceEventType_ConfigurationChanged = new ExpandedNodeId(UAModel.AMB.Variables.IMaintenanceEventType_ConfigurationChanged, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId IMaintenanceEventType_EstimatedDowntime = new ExpandedNodeId(UAModel.AMB.Variables.IMaintenanceEventType_EstimatedDowntime, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId IMaintenanceEventType_MaintenanceMethod = new ExpandedNodeId(UAModel.AMB.Variables.IMaintenanceEventType_MaintenanceMethod, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId IMaintenanceEventType_MaintenanceState_CurrentState = new ExpandedNodeId(UAModel.AMB.Variables.IMaintenanceEventType_MaintenanceState_CurrentState, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId IMaintenanceEventType_MaintenanceState_CurrentState_Id = new ExpandedNodeId(UAModel.AMB.Variables.IMaintenanceEventType_MaintenanceState_CurrentState_Id, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId IMaintenanceEventType_MaintenanceSupplier = new ExpandedNodeId(UAModel.AMB.Variables.IMaintenanceEventType_MaintenanceSupplier, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId IMaintenanceEventType_PartsOfAssetReplaced = new ExpandedNodeId(UAModel.AMB.Variables.IMaintenanceEventType_PartsOfAssetReplaced, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId IMaintenanceEventType_PartsOfAssetServiced = new ExpandedNodeId(UAModel.AMB.Variables.IMaintenanceEventType_PartsOfAssetServiced, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId IMaintenanceEventType_PlannedDate = new ExpandedNodeId(UAModel.AMB.Variables.IMaintenanceEventType_PlannedDate, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId IMaintenanceEventType_QualificationOfPersonnel = new ExpandedNodeId(UAModel.AMB.Variables.IMaintenanceEventType_QualificationOfPersonnel, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId IRootCauseIndicationType_PotentialRootCauses = new ExpandedNodeId(UAModel.AMB.Variables.IRootCauseIndicationType_PotentialRootCauses, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId DocumentationLinksType_Link_Placeholder = new ExpandedNodeId(UAModel.AMB.Variables.DocumentationLinksType_Link_Placeholder, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId DocumentationLinksType_AddLink_InputArguments = new ExpandedNodeId(UAModel.AMB.Variables.DocumentationLinksType_AddLink_InputArguments, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId DocumentationLinksType_AddLink_OutputArguments = new ExpandedNodeId(UAModel.AMB.Variables.DocumentationLinksType_AddLink_OutputArguments, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId DocumentationLinksType_DefaultInstanceBrowseName = new ExpandedNodeId(UAModel.AMB.Variables.DocumentationLinksType_DefaultInstanceBrowseName, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId DocumentationLinksType_RemoveLink_InputArguments = new ExpandedNodeId(UAModel.AMB.Variables.DocumentationLinksType_RemoveLink_InputArguments, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId MaintenanceEventStateMachineType_Executing_StateNumber = new ExpandedNodeId(UAModel.AMB.Variables.MaintenanceEventStateMachineType_Executing_StateNumber, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId MaintenanceEventStateMachineType_Finished_StateNumber = new ExpandedNodeId(UAModel.AMB.Variables.MaintenanceEventStateMachineType_Finished_StateNumber, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId MaintenanceEventStateMachineType_FromExecutingToFinished_TransitionNumber = new ExpandedNodeId(UAModel.AMB.Variables.MaintenanceEventStateMachineType_FromExecutingToFinished_TransitionNumber, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId MaintenanceEventStateMachineType_FromFinishedToPlanned_TransitionNumber = new ExpandedNodeId(UAModel.AMB.Variables.MaintenanceEventStateMachineType_FromFinishedToPlanned_TransitionNumber, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId MaintenanceEventStateMachineType_FromPlannedToExecuting_TransitionNumber = new ExpandedNodeId(UAModel.AMB.Variables.MaintenanceEventStateMachineType_FromPlannedToExecuting_TransitionNumber, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId MaintenanceEventStateMachineType_Planned_StateNumber = new ExpandedNodeId(UAModel.AMB.Variables.MaintenanceEventStateMachineType_Planned_StateNumber, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId Assets_FindAlias_InputArguments = new ExpandedNodeId(UAModel.AMB.Variables.Assets_FindAlias_InputArguments, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId Assets_FindAlias_OutputArguments = new ExpandedNodeId(UAModel.AMB.Variables.Assets_FindAlias_OutputArguments, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId AssetsByAssetId_FindAlias_InputArguments = new ExpandedNodeId(UAModel.AMB.Variables.AssetsByAssetId_FindAlias_InputArguments, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId AssetsByAssetId_FindAlias_OutputArguments = new ExpandedNodeId(UAModel.AMB.Variables.AssetsByAssetId_FindAlias_OutputArguments, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId AssetsByProductInstanceUri_FindAlias_InputArguments = new ExpandedNodeId(UAModel.AMB.Variables.AssetsByProductInstanceUri_FindAlias_InputArguments, UAModel.AMB.Namespaces.AMB);

        public static readonly ExpandedNodeId AssetsByProductInstanceUri_FindAlias_OutputArguments = new ExpandedNodeId(UAModel.AMB.Variables.AssetsByProductInstanceUri_FindAlias_OutputArguments, UAModel.AMB.Namespaces.AMB);
    }
    #endregion

    #region BrowseName Declarations
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class BrowseNames
    {
        public const string AddLink = "AddLink";

        public const string Assets = "Assets";

        public const string AssetsByAssetId = "AssetsByAssetId";

        public const string AssetsByProductInstanceUri = "AssetsByProductInstanceUri";

        public const string BadConfigurationConditionClassType = "BadConfigurationConditionClassType";

        public const string CalibrationDueConditionClassType = "CalibrationDueConditionClassType";

        public const string ConfigurationChanged = "ConfigurationChanged";

        public const string ConnectionFailureConditionClassType = "ConnectionFailureConditionClassType";

        public const string Contains = "Contains";

        public const string DocumentationLinks = "DocumentationLinks";

        public const string DocumentationLinksType = "DocumentationLinksType";

        public const string EstimatedDowntime = "EstimatedDowntime";

        public const string Executing = "Executing";

        public const string ExternalCheckConditionClassType = "ExternalCheckConditionClassType";

        public const string Finished = "Finished";

        public const string FlashUpdateFailedConditionClassType = "FlashUpdateFailedConditionClassType";

        public const string FlashUpdateInProgressConditionClassType = "FlashUpdateInProgressConditionClassType";

        public const string FromExecutingToFinished = "FromExecutingToFinished";

        public const string FromFinishedToPlanned = "FromFinishedToPlanned";

        public const string FromPlannedToExecuting = "FromPlannedToExecuting";

        public const string HierarchicalContains = "HierarchicalContains";

        public const string HierarchicalLocations = "HierarchicalLocations";

        public const string IMaintenanceEventType = "IMaintenanceEventType";

        public const string ImprovementConditionClassType = "ImprovementConditionClassType";

        public const string InspectionConditionClassType = "InspectionConditionClassType";

        public const string IRootCauseIndicationType = "IRootCauseIndicationType";

        public const string Link_Placeholder = "<Link>";

        public const string MaintenanceEventStateMachineType = "MaintenanceEventStateMachineType";

        public const string MaintenanceMethod = "MaintenanceMethod";

        public const string MaintenanceMethodEnum = "MaintenanceMethodEnum";

        public const string MaintenanceState = "MaintenanceState";

        public const string MaintenanceSupplier = "MaintenanceSupplier";

        public const string NameNodeIdDataType = "NameNodeIdDataType";

        public const string OperationalContains = "OperationalContains";

        public const string OperationalLocations = "OperationalLocations";

        public const string OutOfMemoryConditionClassType = "OutOfMemoryConditionClassType";

        public const string OutOfResourcesConditionClassType = "OutOfResourcesConditionClassType";

        public const string OverTemperatureConditionClassType = "OverTemperatureConditionClassType";

        public const string PartsOfAssetReplaced = "PartsOfAssetReplaced";

        public const string PartsOfAssetServiced = "PartsOfAssetServiced";

        public const string Planned = "Planned";

        public const string PlannedDate = "PlannedDate";

        public const string PotentialRootCauses = "PotentialRootCauses";

        public const string QualificationOfPersonnel = "QualificationOfPersonnel";

        public const string RemoveLink = "RemoveLink";

        public const string RepairConditionClassType = "RepairConditionClassType";

        public const string RootCauseDataType = "RootCauseDataType";

        public const string SelfTestFailureConditionClassType = "SelfTestFailureConditionClassType";

        public const string ServicingConditionClassType = "ServicingConditionClassType";
    }
    #endregion

    #region Namespace Declarations
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Namespaces
    {
        /// <summary>
        /// The URI for the AMB namespace (.NET code namespace is 'UAModel.AMB').
        /// </summary>
        public const string AMB = "http://opcfoundation.org/UA/AMB/";

        /// <summary>
        /// The URI for the OpcUa namespace (.NET code namespace is 'Opc.Ua').
        /// </summary>
        public const string OpcUa = "http://opcfoundation.org/UA/";
    }
    #endregion
}