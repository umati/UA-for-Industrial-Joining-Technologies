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

namespace UAModel.AMB
{
    #region CalibrationDueConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_CalibrationDueConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class CalibrationDueConditionClassTypeState : MaintenanceConditionClassState
    {
        #region Constructors
        public CalibrationDueConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.CalibrationDueConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAKAAAAENh" +
           "bGlicmF0aW9uRHVlQ29uZGl0aW9uQ2xhc3NUeXBlSW5zdGFuY2UBAe0DAQHtA+0DAAD/////AAAAAA==";
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

    #region ExternalCheckConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_ExternalCheckConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class ExternalCheckConditionClassTypeState : MaintenanceConditionClassState
    {
        #region Constructors
        public ExternalCheckConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.ExternalCheckConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAJwAAAEV4" +
           "dGVybmFsQ2hlY2tDb25kaXRpb25DbGFzc1R5cGVJbnN0YW5jZQEB9wMBAfcD9wMAAP////8AAAAA";
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

    #region FlashUpdateInProgressConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_FlashUpdateInProgressConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class FlashUpdateInProgressConditionClassTypeState : MaintenanceConditionClassState
    {
        #region Constructors
        public FlashUpdateInProgressConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.FlashUpdateInProgressConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEALwAAAEZs" +
           "YXNoVXBkYXRlSW5Qcm9ncmVzc0NvbmRpdGlvbkNsYXNzVHlwZUluc3RhbmNlAQHvAwEB7wPvAwAA////" +
           "/wAAAAA=";
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

    #region ImprovementConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_ImprovementConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class ImprovementConditionClassTypeState : MaintenanceConditionClassState
    {
        #region Constructors
        public ImprovementConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.ImprovementConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAJQAAAElt" +
           "cHJvdmVtZW50Q29uZGl0aW9uQ2xhc3NUeXBlSW5zdGFuY2UBAfoDAQH6A/oDAAD/////AAAAAA==";
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

    #region InspectionConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_InspectionConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class InspectionConditionClassTypeState : MaintenanceConditionClassState
    {
        #region Constructors
        public InspectionConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.InspectionConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAJAAAAElu" +
           "c3BlY3Rpb25Db25kaXRpb25DbGFzc1R5cGVJbnN0YW5jZQEB9gMBAfYD9gMAAP////8AAAAA";
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

    #region RepairConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_RepairConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class RepairConditionClassTypeState : MaintenanceConditionClassState
    {
        #region Constructors
        public RepairConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.RepairConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAIAAAAFJl" +
           "cGFpckNvbmRpdGlvbkNsYXNzVHlwZUluc3RhbmNlAQH5AwEB+QP5AwAA/////wAAAAA=";
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

    #region ServicingConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_ServicingConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class ServicingConditionClassTypeState : MaintenanceConditionClassState
    {
        #region Constructors
        public ServicingConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.ServicingConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAIwAAAFNl" +
           "cnZpY2luZ0NvbmRpdGlvbkNsYXNzVHlwZUluc3RhbmNlAQH4AwEB+AP4AwAA/////wAAAAA=";
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

    #region BadConfigurationConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_BadConfigurationConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class BadConfigurationConditionClassTypeState : SystemConditionClassState
    {
        #region Constructors
        public BadConfigurationConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.BadConfigurationConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAKgAAAEJh" +
           "ZENvbmZpZ3VyYXRpb25Db25kaXRpb25DbGFzc1R5cGVJbnN0YW5jZQEB8AMBAfAD8AMAAP////8AAAAA";
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

    #region ConnectionFailureConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_ConnectionFailureConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class ConnectionFailureConditionClassTypeState : SystemConditionClassState
    {
        #region Constructors
        public ConnectionFailureConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.ConnectionFailureConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAKwAAAENv" +
           "bm5lY3Rpb25GYWlsdXJlQ29uZGl0aW9uQ2xhc3NUeXBlSW5zdGFuY2UBAesDAQHrA+sDAAD/////AAAA" +
           "AA==";
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

    #region FlashUpdateFailedConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_FlashUpdateFailedConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class FlashUpdateFailedConditionClassTypeState : SystemConditionClassState
    {
        #region Constructors
        public FlashUpdateFailedConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.FlashUpdateFailedConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAKwAAAEZs" +
           "YXNoVXBkYXRlRmFpbGVkQ29uZGl0aW9uQ2xhc3NUeXBlSW5zdGFuY2UBAfsDAQH7A/sDAAD/////AAAA" +
           "AA==";
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

    #region OutOfResourcesConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_OutOfResourcesConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class OutOfResourcesConditionClassTypeState : SystemConditionClassState
    {
        #region Constructors
        public OutOfResourcesConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.OutOfResourcesConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAKAAAAE91" +
           "dE9mUmVzb3VyY2VzQ29uZGl0aW9uQ2xhc3NUeXBlSW5zdGFuY2UBAfEDAQHxA/EDAAD/////AAAAAA==";
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

    #region OutOfMemoryConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_OutOfMemoryConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class OutOfMemoryConditionClassTypeState : OutOfResourcesConditionClassTypeState
    {
        #region Constructors
        public OutOfMemoryConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.OutOfMemoryConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAJQAAAE91" +
           "dE9mTWVtb3J5Q29uZGl0aW9uQ2xhc3NUeXBlSW5zdGFuY2UBAfIDAQHyA/IDAAD/////AAAAAA==";
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

    #region OverTemperatureConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_OverTemperatureConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class OverTemperatureConditionClassTypeState : SystemConditionClassState
    {
        #region Constructors
        public OverTemperatureConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.OverTemperatureConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAKQAAAE92" +
           "ZXJUZW1wZXJhdHVyZUNvbmRpdGlvbkNsYXNzVHlwZUluc3RhbmNlAQHsAwEB7APsAwAA/////wAAAAA=";
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

    #region SelfTestFailureConditionClassTypeState Class
    #if (!OPCUA_EXCLUDE_SelfTestFailureConditionClassTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class SelfTestFailureConditionClassTypeState : SystemConditionClassState
    {
        #region Constructors
        public SelfTestFailureConditionClassTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.SelfTestFailureConditionClassType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAKQAAAFNl" +
           "bGZUZXN0RmFpbHVyZUNvbmRpdGlvbkNsYXNzVHlwZUluc3RhbmNlAQHuAwEB7gPuAwAA/////wAAAAA=";
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

    #region IMaintenanceEventTypeState Class
    #if (!OPCUA_EXCLUDE_IMaintenanceEventTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class IMaintenanceEventTypeState : BaseInterfaceState
    {
        #region Constructors
        public IMaintenanceEventTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.IMaintenanceEventType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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

            if (ConfigurationChanged != null)
            {
                ConfigurationChanged.Initialize(context, ConfigurationChanged_InitializationString);
            }

            if (EstimatedDowntime != null)
            {
                EstimatedDowntime.Initialize(context, EstimatedDowntime_InitializationString);
            }

            if (MaintenanceMethod != null)
            {
                MaintenanceMethod.Initialize(context, MaintenanceMethod_InitializationString);
            }

            if (MaintenanceSupplier != null)
            {
                MaintenanceSupplier.Initialize(context, MaintenanceSupplier_InitializationString);
            }

            if (PartsOfAssetReplaced != null)
            {
                PartsOfAssetReplaced.Initialize(context, PartsOfAssetReplaced_InitializationString);
            }

            if (PartsOfAssetServiced != null)
            {
                PartsOfAssetServiced.Initialize(context, PartsOfAssetServiced_InitializationString);
            }

            if (PlannedDate != null)
            {
                PlannedDate.Initialize(context, PlannedDate_InitializationString);
            }

            if (QualificationOfPersonnel != null)
            {
                QualificationOfPersonnel.Initialize(context, QualificationOfPersonnel_InitializationString);
            }
        }

        #region Initialization String
        private const string ConfigurationChanged_InitializationString =
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////81YIkKAgAAAAEAFAAAAENv" +
           "bmZpZ3VyYXRpb25DaGFuZ2VkAQGaFwMAAAAAfwEAAEluZm9ybWF0aW9uIGlmIHRoZSBjb25maWd1cmF0" +
           "aW9uIG9mIHRoZSBhc3NldCBpcyBwbGFubmVkIHRvIGJlIGNoYW5nZWQgb3IgaGFzIGNoYW5nZWQgZHVy" +
           "aW5nIHRoZSBtYWludGVuYW5jZSBhY3Rpdml0eS4gRkFMU0UgaW5kaWNhdGVzIG5vIGNoYW5nZSwgYW5k" +
           "IFRSVUUgaW5kaWNhdGVzIGEgY2hhbmdlLiBUaGUgY29udGVudCBtYXkgY2hhbmdlIGR1cmluZyB0aGUg" +
           "ZGlmZmVyZW50IE1haW50ZW5hbmNlU3RhdGVzLiBCeSBhY2Nlc3NpbmcgdGhlIGhpc3Rvcnkgb2YgRXZl" +
           "bnRzIGEgQ2xpZW50IGNhbiBkaXN0aW5ndWlzaCBiZXR3ZWVuIHRoZSBwbGFubmVkIGFuZCBhY3R1YWwg" +
           "Y29uZmlndXJhdGlvbiBjaGFuZ2VzIGR1cmluZyB0aGUgbWFpbnRlbmFuY2UgYWN0aXZpdHkuAC4ARJoX" +
           "AAAAAf////8DA/////8AAAAA";

        private const string EstimatedDowntime_InitializationString =
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////81YIkKAgAAAAEAEQAAAEVz" +
           "dGltYXRlZERvd250aW1lAQGUFwMAAAAA0AEAAFRoZSBlc3RpbWF0ZWQgdGltZSB0aGUgZXhlY3V0aW9u" +
           "IG9mIHRoZSBtYWludGVuYW5jZSBhY3Rpdml0eSB3aWxsIHRha2UuIEluIGNhc2Ugb2YgcmVwbGFubmlu" +
           "ZywgaXQgaXMgYWxsb3dlZCB0byBjaGFuZ2UgdGhlIEVzdGltYXRlZERvd250aW1lLiBJZiBkdXJpbmcg" +
           "dGhlIGV4ZWN1dGlvbiBvZiB0aGUgbWFpbnRlbmFuY2UgYWN0aXZpdHkgdGhlIEVzdGltYXRlZERvd250" +
           "aW1lIGNhbiBiZSBhZGp1c3RlZCAoZS5nLiwgdGhlIGFzc2V0IG5lZWRzIHRvIGJlIHJlcGFpcmVkIGJl" +
           "Y2F1c2UgYW4gaW5zcGVjdGlvbiBmb3VuZCBzb21lIGlzc3VlcykgdGhpcyBzaG91bGQgYmUgZG9uZS4g" +
           "Q2xpZW50cyBjYW4gYWNjZXNzIHRoZSBoaXN0b3J5IG9mIEV2ZW50cyB0byByZWNlaXZlIHRoZSBpbmZv" +
           "cm1hdGlvbiBvbiB0aGUgb3JpZ2luYWwgZXN0aW1hdGVzIHdoZW4gdGhlIG1haW50ZW5hbmNlIGFjdGl2" +
           "aXR5IHN0YXJ0ZWQuAC4ARJQXAAABACIB/////wMD/////wAAAAA=";

        private const string MaintenanceMethod_InitializationString =
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////81YIkKAgAAAAEAEQAAAE1h" +
           "aW50ZW5hbmNlTWV0aG9kAQGZFwMAAAAADAEAAEluZm9ybWF0aW9uIGFib3V0IHRoZSBwbGFubmVkIG9y" +
           "IHVzZWQgbWFpbnRlbmFuY2UgbWV0aG9kLiBUaGUgY29udGVudCBtYXkgY2hhbmdlIGR1cmluZyB0aGUg" +
           "ZGlmZmVyZW50IE1haW50ZW5hbmNlU3RhdGVzLiBCeSBhY2Nlc3NpbmcgdGhlIGhpc3Rvcnkgb2YgRXZl" +
           "bnRzIGEgQ2xpZW50IGNhbiBkaXN0aW5ndWlzaCBiZXR3ZWVuIHRoZSBwbGFubmVkIGFuZCBhY3R1YWwg" +
           "dXNlZCBtYWludGVuYW5jZSBtZXRob2QgZHVyaW5nIHRoZSBtYWludGVuYW5jZSBhY3Rpdml0eS4ALgBE" +
           "mRcAAAEBvAv/////AwP/////AAAAAA==";

        private const string MaintenanceSupplier_InitializationString =
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////81YIkKAgAAAAEAEwAAAE1h" +
           "aW50ZW5hbmNlU3VwcGxpZXIBAZUXAwAAAADQAQAASW5mb3JtYXRpb24gb24gdGhlIHN1cHBsaWVyIHRo" +
           "YXQgaXMgcGxhbm5lZCB0byBleGVjdXRlLCBjdXJyZW50bHkgZXhlY3V0aW5nIG9yIGhhcyBleGVjdXRl" +
           "ZCB0aGUgbWFpbnRlbmFuY2UgYWN0aXZpdHkuIFRoZSBjb250ZW50IG1heSBjaGFuZ2UgZHVyaW5nIHRo" +
           "ZSBkaWZmZXJlbnQgTWFpbnRlbmFuY2VTdGF0ZXMuIEJ5IGFjY2Vzc2luZyB0aGUgaGlzdG9yeSBvZiBF" +
           "dmVudHMgYSBDbGllbnQgY2FuIGRpc3Rpbmd1aXNoIGJldHdlZW4gdGhlIHBsYW5uZWQgYW5kIGFjdHVh" +
           "bCBzdXBwbGllciB0aGF0IGV4ZWN1dGVkIHRoZSBtYWludGVuYW5jZSBhY3Rpdml0eS4gVGhlIHZhbHVl" +
           "IGNvbnRhaW5zIGFsd2F5cyBhIGh1bWFuLXJlYWRhYmxlIG5hbWUgb2YgdGhlIHN1cHBsaWVyIGFuZCBv" +
           "cHRpb25hbGx5IHJlZmVyZW5jZXMgYSBOb2RlIHJlcHJlc2VudGluZyB0aGUgc3VwcGxpZXIgaW4gdGhl" +
           "IEFkZHJlc3NTcGFjZS4ALgBElRcAAAEBuwv/////AwP/////AAAAAA==";

        private const string PartsOfAssetReplaced_InitializationString =
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////83YIkKAgAAAAEAFAAAAFBh" +
           "cnRzT2ZBc3NldFJlcGxhY2VkAQGXFwMAAAAAagIAAEluZm9ybWF0aW9uIG9uIHRoZSBwYXJ0cyBvZiB0" +
           "aGUgYXNzZXRzIHRoYXQgYXJlIHBsYW5uZWQgdG8gYmUgc2VydmljZWQgZHVyaW5nIHRoZSBtYWludGVu" +
           "YW5jZSBhY3Rpdml0eSwgY3VycmVudGx5IHNlcnZpY2VkIG9yIGhhdmUgYmVlbiBzZXJ2aWNlZCwgZGVw" +
           "ZW5kaW5nIG9uIHRoZSBkaWZmZXJlbnQgTWFpbnRlbmFuY2VTdGF0ZXMuIFRoZSBjb250ZW50IG1heSBj" +
           "aGFuZ2UgZHVyaW5nIHRoZSBkaWZmZXJlbnQgTWFpbnRlbmFuY2VTdGF0ZXMuIEJ5IGFjY2Vzc2luZyB0" +
           "aGUgaGlzdG9yeSBvZiBFdmVudHMgYSBDbGllbnQgY2FuIGRpc3Rpbmd1aXNoIGJldHdlZW4gdGhlIHBs" +
           "YW5uZWQgYW5kIGFjdHVhbCBwYXJ0cyBvZiB0aGUgYXNzZXRzIHNlcnZpY2VkIGR1cmluZyB0aGUgbWFp" +
           "bnRlbmFuY2UgYWN0aXZpdHkuIFRoZSB2YWx1ZSBjb250YWlucyBhbHdheXMgYW4gYXJyYXkgb2YgYSBo" +
           "dW1hbi1yZWFkYWJsZSBuYW1lIG9mIHRoZSBxdWFsaWZpY2F0aW9uIG9mIHRoZSBwYXJ0cyBvZiB0aGUg" +
           "YXNzZXQgdG8gYmUgc2VydmljZWQgYW5kIG9wdGlvbmFsbHkgcmVmZXJlbmNlcyBhIE5vZGUgcmVwcmVz" +
           "ZW50aW5nIHRoZSBwYXJ0IG9mIHRoZSBhc3NldCBpbiB0aGUgQWRkcmVzc1NwYWNlLgAuAESXFwAAAQG7" +
           "CwEAAAABAAAAAAAAAAMD/////wAAAAA=";

        private const string PartsOfAssetServiced_InitializationString =
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////83YIkKAgAAAAEAFAAAAFBh" +
           "cnRzT2ZBc3NldFNlcnZpY2VkAQGYFwMAAAAAagIAAEluZm9ybWF0aW9uIG9uIHRoZSBwYXJ0cyBvZiB0" +
           "aGUgYXNzZXRzIHRoYXQgYXJlIHBsYW5uZWQgdG8gYmUgc2VydmljZWQgZHVyaW5nIHRoZSBtYWludGVu" +
           "YW5jZSBhY3Rpdml0eSwgY3VycmVudGx5IHNlcnZpY2VkIG9yIGhhdmUgYmVlbiBzZXJ2aWNlZCwgZGVw" +
           "ZW5kaW5nIG9uIHRoZSBkaWZmZXJlbnQgTWFpbnRlbmFuY2VTdGF0ZXMuIFRoZSBjb250ZW50IG1heSBj" +
           "aGFuZ2UgZHVyaW5nIHRoZSBkaWZmZXJlbnQgTWFpbnRlbmFuY2VTdGF0ZXMuIEJ5IGFjY2Vzc2luZyB0" +
           "aGUgaGlzdG9yeSBvZiBFdmVudHMgYSBDbGllbnQgY2FuIGRpc3Rpbmd1aXNoIGJldHdlZW4gdGhlIHBs" +
           "YW5uZWQgYW5kIGFjdHVhbCBwYXJ0cyBvZiB0aGUgYXNzZXRzIHNlcnZpY2VkIGR1cmluZyB0aGUgbWFp" +
           "bnRlbmFuY2UgYWN0aXZpdHkuIFRoZSB2YWx1ZSBjb250YWlucyBhbHdheXMgYW4gYXJyYXkgb2YgYSBo" +
           "dW1hbi1yZWFkYWJsZSBuYW1lIG9mIHRoZSBxdWFsaWZpY2F0aW9uIG9mIHRoZSBwYXJ0cyBvZiB0aGUg" +
           "YXNzZXQgdG8gYmUgc2VydmljZWQgYW5kIG9wdGlvbmFsbHkgcmVmZXJlbmNlcyBhIE5vZGUgcmVwcmVz" +
           "ZW50aW5nIHRoZSBwYXJ0IG9mIHRoZSBhc3NldCBpbiB0aGUgQWRkcmVzc1NwYWNlLgAuAESYFwAAAQG7" +
           "CwEAAAABAAAAAAAAAAMD/////wAAAAA=";

        private const string PlannedDate_InitializationString =
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////81YIkKAgAAAAEACwAAAFBs" +
           "YW5uZWREYXRlAQGTFwMAAAAAgAEAAERhdGUgZm9yIHdoaWNoIHRoZSBtYWludGVuYW5jZSBhY3Rpdml0" +
           "eSBoYXMgYmVlbiBzY2hlZHVsZWQuIEluIGNhc2Ugb2YgcmVwbGFubmluZywgaXQgaXMgYWxsb3dlZCB0" +
           "byBjaGFuZ2UgdGhlIFBsYW5uZWREYXRlLiBIb3dldmVyLCBpdCBpcyBub3QgdGhlIGludGVudGlvbiB0" +
           "aGF0IHRoZSBQbGFubmVkRGF0ZSBpcyBtb2RpZmllZCBiZWNhdXNlIHRoZSBtYWludGVuYW5jZSBhY3Rp" +
           "dml0eSBzdGFydHMgdG8gZ2V0IGV4ZWN1dGVkLiBJZiB0aGUgUGxhbm5lZERhdGUgZGVwZW5kcyBmb3Ig" +
           "ZXhhbXBsZSBvbiB0aGUgb3BlcmF0aW9uIGhvdXJzIG9mIHRoZSBhc3NldCwgaXQgbWlnaHQgZ2V0IGFk" +
           "YXB0ZWQgZGVwZW5kaW5nIG9uIHRoZSBwYXNzZWQgb3BlcmF0aW9uIGhvdXJzLgAuAESTFwAAAQAmAf//" +
           "//8DA/////8AAAAA";

        private const string QualificationOfPersonnel_InitializationString =
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////81YIkKAgAAAAEAGAAAAFF1" +
           "YWxpZmljYXRpb25PZlBlcnNvbm5lbAEBlhcDAAAAACgCAABJbmZvcm1hdGlvbiBvbiB0aGUgcXVhbGlm" +
           "aWNhdGlvbiBvZiB0aGUgcGVyc29ubmVsIHRoYXQgaXMgcGxhbm5lZCB0byBleGVjdXRlLCBjdXJyZW50" +
           "bHkgZXhlY3V0aW5nIG9yIGhhcyBleGVjdXRlZCB0aGUgbWFpbnRlbmFuY2UgYWN0aXZpdHkuIFRoZSBj" +
           "b250ZW50IG1heSBjaGFuZ2UgZHVyaW5nIHRoZSBkaWZmZXJlbnQgTWFpbnRlbmFuY2VTdGF0ZXMuIEJ5" +
           "IGFjY2Vzc2luZyB0aGUgaGlzdG9yeSBvZiBFdmVudHMgYSBDbGllbnQgY2FuIGRpc3Rpbmd1aXNoIGJl" +
           "dHdlZW4gdGhlIHBsYW5uZWQgYW5kIGFjdHVhbCBxdWFsaWZpY2F0aW9uIG9mIHRoZSBwZXJzb25uZWwg" +
           "dGhhdCBleGVjdXRlZCB0aGUgbWFpbnRlbmFuY2UgYWN0aXZpdHkuIFRoZSB2YWx1ZSBjb250YWlucyBh" +
           "bHdheXMgYSBodW1hbi1yZWFkYWJsZSBuYW1lIG9mIHRoZSBxdWFsaWZpY2F0aW9uIG9mIHRoZSBwZXJz" +
           "b25uZWwgYW5kIG9wdGlvbmFsbHkgcmVmZXJlbmNlcyBhIE5vZGUgcmVwcmVzZW50aW5nIHRoZSBxdWFs" +
           "aWZpY2F0aW9uIG9mIHRoZSBwZXJzb25uZWwgaW4gdGhlIEFkZHJlc3NTcGFjZS4ALgBElhcAAAEBuwv/" +
           "////AwP/////AAAAAA==";

        private const string InitializationString =
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAHQAAAElN" +
           "YWludGVuYW5jZUV2ZW50VHlwZUluc3RhbmNlAQH0AwEB9AP0AwAA/////wkAAAA1YIkKAgAAAAEAFAAA" +
           "AENvbmZpZ3VyYXRpb25DaGFuZ2VkAQGaFwMAAAAAfwEAAEluZm9ybWF0aW9uIGlmIHRoZSBjb25maWd1" +
           "cmF0aW9uIG9mIHRoZSBhc3NldCBpcyBwbGFubmVkIHRvIGJlIGNoYW5nZWQgb3IgaGFzIGNoYW5nZWQg" +
           "ZHVyaW5nIHRoZSBtYWludGVuYW5jZSBhY3Rpdml0eS4gRkFMU0UgaW5kaWNhdGVzIG5vIGNoYW5nZSwg" +
           "YW5kIFRSVUUgaW5kaWNhdGVzIGEgY2hhbmdlLiBUaGUgY29udGVudCBtYXkgY2hhbmdlIGR1cmluZyB0" +
           "aGUgZGlmZmVyZW50IE1haW50ZW5hbmNlU3RhdGVzLiBCeSBhY2Nlc3NpbmcgdGhlIGhpc3Rvcnkgb2Yg" +
           "RXZlbnRzIGEgQ2xpZW50IGNhbiBkaXN0aW5ndWlzaCBiZXR3ZWVuIHRoZSBwbGFubmVkIGFuZCBhY3R1" +
           "YWwgY29uZmlndXJhdGlvbiBjaGFuZ2VzIGR1cmluZyB0aGUgbWFpbnRlbmFuY2UgYWN0aXZpdHkuAC4A" +
           "RJoXAAAAAf////8DA/////8AAAAANWCJCgIAAAABABEAAABFc3RpbWF0ZWREb3dudGltZQEBlBcDAAAA" +
           "ANABAABUaGUgZXN0aW1hdGVkIHRpbWUgdGhlIGV4ZWN1dGlvbiBvZiB0aGUgbWFpbnRlbmFuY2UgYWN0" +
           "aXZpdHkgd2lsbCB0YWtlLiBJbiBjYXNlIG9mIHJlcGxhbm5pbmcsIGl0IGlzIGFsbG93ZWQgdG8gY2hh" +
           "bmdlIHRoZSBFc3RpbWF0ZWREb3dudGltZS4gSWYgZHVyaW5nIHRoZSBleGVjdXRpb24gb2YgdGhlIG1h" +
           "aW50ZW5hbmNlIGFjdGl2aXR5IHRoZSBFc3RpbWF0ZWREb3dudGltZSBjYW4gYmUgYWRqdXN0ZWQgKGUu" +
           "Zy4sIHRoZSBhc3NldCBuZWVkcyB0byBiZSByZXBhaXJlZCBiZWNhdXNlIGFuIGluc3BlY3Rpb24gZm91" +
           "bmQgc29tZSBpc3N1ZXMpIHRoaXMgc2hvdWxkIGJlIGRvbmUuIENsaWVudHMgY2FuIGFjY2VzcyB0aGUg" +
           "aGlzdG9yeSBvZiBFdmVudHMgdG8gcmVjZWl2ZSB0aGUgaW5mb3JtYXRpb24gb24gdGhlIG9yaWdpbmFs" +
           "IGVzdGltYXRlcyB3aGVuIHRoZSBtYWludGVuYW5jZSBhY3Rpdml0eSBzdGFydGVkLgAuAESUFwAAAQAi" +
           "Af////8DA/////8AAAAANWCJCgIAAAABABEAAABNYWludGVuYW5jZU1ldGhvZAEBmRcDAAAAAAwBAABJ" +
           "bmZvcm1hdGlvbiBhYm91dCB0aGUgcGxhbm5lZCBvciB1c2VkIG1haW50ZW5hbmNlIG1ldGhvZC4gVGhl" +
           "IGNvbnRlbnQgbWF5IGNoYW5nZSBkdXJpbmcgdGhlIGRpZmZlcmVudCBNYWludGVuYW5jZVN0YXRlcy4g" +
           "QnkgYWNjZXNzaW5nIHRoZSBoaXN0b3J5IG9mIEV2ZW50cyBhIENsaWVudCBjYW4gZGlzdGluZ3Vpc2gg" +
           "YmV0d2VlbiB0aGUgcGxhbm5lZCBhbmQgYWN0dWFsIHVzZWQgbWFpbnRlbmFuY2UgbWV0aG9kIGR1cmlu" +
           "ZyB0aGUgbWFpbnRlbmFuY2UgYWN0aXZpdHkuAC4ARJkXAAABAbwL/////wMD/////wAAAAAkYIAKAQAA" +
           "AAEAEAAAAE1haW50ZW5hbmNlU3RhdGUBAZYTAwAAAABvAAAASW5mb3JtYXRpb24gaWYgdGhlIG1haW50" +
           "ZW5hbmNlIGFjdGl2aXR5IGlzIHN0aWxsIHBsYW5uZWQsIGN1cnJlbnRseSBpbiBleGVjdXRpb24sIG9y" +
           "IGhhcyBhbHJlYWR5IGJlZW4gZXhlY3V0ZWQuAC8BAfUDlhMAAP////8BAAAAFWCJCgIAAAAAAAwAAABD" +
           "dXJyZW50U3RhdGUBAZEXAC8BAMgKkRcAAAAV/////wEB/////wEAAAAVYIkKAgAAAAAAAgAAAElkAQGS" +
           "FwAuAESSFwAAABH/////AQH/////AAAAADVgiQoCAAAAAQATAAAATWFpbnRlbmFuY2VTdXBwbGllcgEB" +
           "lRcDAAAAANABAABJbmZvcm1hdGlvbiBvbiB0aGUgc3VwcGxpZXIgdGhhdCBpcyBwbGFubmVkIHRvIGV4" +
           "ZWN1dGUsIGN1cnJlbnRseSBleGVjdXRpbmcgb3IgaGFzIGV4ZWN1dGVkIHRoZSBtYWludGVuYW5jZSBh" +
           "Y3Rpdml0eS4gVGhlIGNvbnRlbnQgbWF5IGNoYW5nZSBkdXJpbmcgdGhlIGRpZmZlcmVudCBNYWludGVu" +
           "YW5jZVN0YXRlcy4gQnkgYWNjZXNzaW5nIHRoZSBoaXN0b3J5IG9mIEV2ZW50cyBhIENsaWVudCBjYW4g" +
           "ZGlzdGluZ3Vpc2ggYmV0d2VlbiB0aGUgcGxhbm5lZCBhbmQgYWN0dWFsIHN1cHBsaWVyIHRoYXQgZXhl" +
           "Y3V0ZWQgdGhlIG1haW50ZW5hbmNlIGFjdGl2aXR5LiBUaGUgdmFsdWUgY29udGFpbnMgYWx3YXlzIGEg" +
           "aHVtYW4tcmVhZGFibGUgbmFtZSBvZiB0aGUgc3VwcGxpZXIgYW5kIG9wdGlvbmFsbHkgcmVmZXJlbmNl" +
           "cyBhIE5vZGUgcmVwcmVzZW50aW5nIHRoZSBzdXBwbGllciBpbiB0aGUgQWRkcmVzc1NwYWNlLgAuAESV" +
           "FwAAAQG7C/////8DA/////8AAAAAN2CJCgIAAAABABQAAABQYXJ0c09mQXNzZXRSZXBsYWNlZAEBlxcD" +
           "AAAAAGoCAABJbmZvcm1hdGlvbiBvbiB0aGUgcGFydHMgb2YgdGhlIGFzc2V0cyB0aGF0IGFyZSBwbGFu" +
           "bmVkIHRvIGJlIHNlcnZpY2VkIGR1cmluZyB0aGUgbWFpbnRlbmFuY2UgYWN0aXZpdHksIGN1cnJlbnRs" +
           "eSBzZXJ2aWNlZCBvciBoYXZlIGJlZW4gc2VydmljZWQsIGRlcGVuZGluZyBvbiB0aGUgZGlmZmVyZW50" +
           "IE1haW50ZW5hbmNlU3RhdGVzLiBUaGUgY29udGVudCBtYXkgY2hhbmdlIGR1cmluZyB0aGUgZGlmZmVy" +
           "ZW50IE1haW50ZW5hbmNlU3RhdGVzLiBCeSBhY2Nlc3NpbmcgdGhlIGhpc3Rvcnkgb2YgRXZlbnRzIGEg" +
           "Q2xpZW50IGNhbiBkaXN0aW5ndWlzaCBiZXR3ZWVuIHRoZSBwbGFubmVkIGFuZCBhY3R1YWwgcGFydHMg" +
           "b2YgdGhlIGFzc2V0cyBzZXJ2aWNlZCBkdXJpbmcgdGhlIG1haW50ZW5hbmNlIGFjdGl2aXR5LiBUaGUg" +
           "dmFsdWUgY29udGFpbnMgYWx3YXlzIGFuIGFycmF5IG9mIGEgaHVtYW4tcmVhZGFibGUgbmFtZSBvZiB0" +
           "aGUgcXVhbGlmaWNhdGlvbiBvZiB0aGUgcGFydHMgb2YgdGhlIGFzc2V0IHRvIGJlIHNlcnZpY2VkIGFu" +
           "ZCBvcHRpb25hbGx5IHJlZmVyZW5jZXMgYSBOb2RlIHJlcHJlc2VudGluZyB0aGUgcGFydCBvZiB0aGUg" +
           "YXNzZXQgaW4gdGhlIEFkZHJlc3NTcGFjZS4ALgBElxcAAAEBuwsBAAAAAQAAAAAAAAADA/////8AAAAA" +
           "N2CJCgIAAAABABQAAABQYXJ0c09mQXNzZXRTZXJ2aWNlZAEBmBcDAAAAAGoCAABJbmZvcm1hdGlvbiBv" +
           "biB0aGUgcGFydHMgb2YgdGhlIGFzc2V0cyB0aGF0IGFyZSBwbGFubmVkIHRvIGJlIHNlcnZpY2VkIGR1" +
           "cmluZyB0aGUgbWFpbnRlbmFuY2UgYWN0aXZpdHksIGN1cnJlbnRseSBzZXJ2aWNlZCBvciBoYXZlIGJl" +
           "ZW4gc2VydmljZWQsIGRlcGVuZGluZyBvbiB0aGUgZGlmZmVyZW50IE1haW50ZW5hbmNlU3RhdGVzLiBU" +
           "aGUgY29udGVudCBtYXkgY2hhbmdlIGR1cmluZyB0aGUgZGlmZmVyZW50IE1haW50ZW5hbmNlU3RhdGVz" +
           "LiBCeSBhY2Nlc3NpbmcgdGhlIGhpc3Rvcnkgb2YgRXZlbnRzIGEgQ2xpZW50IGNhbiBkaXN0aW5ndWlz" +
           "aCBiZXR3ZWVuIHRoZSBwbGFubmVkIGFuZCBhY3R1YWwgcGFydHMgb2YgdGhlIGFzc2V0cyBzZXJ2aWNl" +
           "ZCBkdXJpbmcgdGhlIG1haW50ZW5hbmNlIGFjdGl2aXR5LiBUaGUgdmFsdWUgY29udGFpbnMgYWx3YXlz" +
           "IGFuIGFycmF5IG9mIGEgaHVtYW4tcmVhZGFibGUgbmFtZSBvZiB0aGUgcXVhbGlmaWNhdGlvbiBvZiB0" +
           "aGUgcGFydHMgb2YgdGhlIGFzc2V0IHRvIGJlIHNlcnZpY2VkIGFuZCBvcHRpb25hbGx5IHJlZmVyZW5j" +
           "ZXMgYSBOb2RlIHJlcHJlc2VudGluZyB0aGUgcGFydCBvZiB0aGUgYXNzZXQgaW4gdGhlIEFkZHJlc3NT" +
           "cGFjZS4ALgBEmBcAAAEBuwsBAAAAAQAAAAAAAAADA/////8AAAAANWCJCgIAAAABAAsAAABQbGFubmVk" +
           "RGF0ZQEBkxcDAAAAAIABAABEYXRlIGZvciB3aGljaCB0aGUgbWFpbnRlbmFuY2UgYWN0aXZpdHkgaGFz" +
           "IGJlZW4gc2NoZWR1bGVkLiBJbiBjYXNlIG9mIHJlcGxhbm5pbmcsIGl0IGlzIGFsbG93ZWQgdG8gY2hh" +
           "bmdlIHRoZSBQbGFubmVkRGF0ZS4gSG93ZXZlciwgaXQgaXMgbm90IHRoZSBpbnRlbnRpb24gdGhhdCB0" +
           "aGUgUGxhbm5lZERhdGUgaXMgbW9kaWZpZWQgYmVjYXVzZSB0aGUgbWFpbnRlbmFuY2UgYWN0aXZpdHkg" +
           "c3RhcnRzIHRvIGdldCBleGVjdXRlZC4gSWYgdGhlIFBsYW5uZWREYXRlIGRlcGVuZHMgZm9yIGV4YW1w" +
           "bGUgb24gdGhlIG9wZXJhdGlvbiBob3VycyBvZiB0aGUgYXNzZXQsIGl0IG1pZ2h0IGdldCBhZGFwdGVk" +
           "IGRlcGVuZGluZyBvbiB0aGUgcGFzc2VkIG9wZXJhdGlvbiBob3Vycy4ALgBEkxcAAAEAJgH/////AwP/" +
           "////AAAAADVgiQoCAAAAAQAYAAAAUXVhbGlmaWNhdGlvbk9mUGVyc29ubmVsAQGWFwMAAAAAKAIAAElu" +
           "Zm9ybWF0aW9uIG9uIHRoZSBxdWFsaWZpY2F0aW9uIG9mIHRoZSBwZXJzb25uZWwgdGhhdCBpcyBwbGFu" +
           "bmVkIHRvIGV4ZWN1dGUsIGN1cnJlbnRseSBleGVjdXRpbmcgb3IgaGFzIGV4ZWN1dGVkIHRoZSBtYWlu" +
           "dGVuYW5jZSBhY3Rpdml0eS4gVGhlIGNvbnRlbnQgbWF5IGNoYW5nZSBkdXJpbmcgdGhlIGRpZmZlcmVu" +
           "dCBNYWludGVuYW5jZVN0YXRlcy4gQnkgYWNjZXNzaW5nIHRoZSBoaXN0b3J5IG9mIEV2ZW50cyBhIENs" +
           "aWVudCBjYW4gZGlzdGluZ3Vpc2ggYmV0d2VlbiB0aGUgcGxhbm5lZCBhbmQgYWN0dWFsIHF1YWxpZmlj" +
           "YXRpb24gb2YgdGhlIHBlcnNvbm5lbCB0aGF0IGV4ZWN1dGVkIHRoZSBtYWludGVuYW5jZSBhY3Rpdml0" +
           "eS4gVGhlIHZhbHVlIGNvbnRhaW5zIGFsd2F5cyBhIGh1bWFuLXJlYWRhYmxlIG5hbWUgb2YgdGhlIHF1" +
           "YWxpZmljYXRpb24gb2YgdGhlIHBlcnNvbm5lbCBhbmQgb3B0aW9uYWxseSByZWZlcmVuY2VzIGEgTm9k" +
           "ZSByZXByZXNlbnRpbmcgdGhlIHF1YWxpZmljYXRpb24gb2YgdGhlIHBlcnNvbm5lbCBpbiB0aGUgQWRk" +
           "cmVzc1NwYWNlLgAuAESWFwAAAQG7C/////8DA/////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public PropertyState<bool> ConfigurationChanged
        {
            get => m_configurationChanged;

            set
            {
                if (!Object.ReferenceEquals(m_configurationChanged, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_configurationChanged = value;
            }
        }

        public PropertyState<double> EstimatedDowntime
        {
            get => m_estimatedDowntime;

            set
            {
                if (!Object.ReferenceEquals(m_estimatedDowntime, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_estimatedDowntime = value;
            }
        }

        public PropertyState<MaintenanceMethodEnum> MaintenanceMethod
        {
            get => m_maintenanceMethod;

            set
            {
                if (!Object.ReferenceEquals(m_maintenanceMethod, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_maintenanceMethod = value;
            }
        }

        public MaintenanceEventStateMachineTypeState MaintenanceState
        {
            get => m_maintenanceState;

            set
            {
                if (!Object.ReferenceEquals(m_maintenanceState, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_maintenanceState = value;
            }
        }

        public PropertyState<NameNodeIdDataType> MaintenanceSupplier
        {
            get => m_maintenanceSupplier;

            set
            {
                if (!Object.ReferenceEquals(m_maintenanceSupplier, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_maintenanceSupplier = value;
            }
        }

        public PropertyState<NameNodeIdDataType[]> PartsOfAssetReplaced
        {
            get => m_partsOfAssetReplaced;

            set
            {
                if (!Object.ReferenceEquals(m_partsOfAssetReplaced, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_partsOfAssetReplaced = value;
            }
        }

        public PropertyState<NameNodeIdDataType[]> PartsOfAssetServiced
        {
            get => m_partsOfAssetServiced;

            set
            {
                if (!Object.ReferenceEquals(m_partsOfAssetServiced, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_partsOfAssetServiced = value;
            }
        }

        public PropertyState<DateTime> PlannedDate
        {
            get => m_plannedDate;

            set
            {
                if (!Object.ReferenceEquals(m_plannedDate, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_plannedDate = value;
            }
        }

        public PropertyState<NameNodeIdDataType> QualificationOfPersonnel
        {
            get => m_qualificationOfPersonnel;

            set
            {
                if (!Object.ReferenceEquals(m_qualificationOfPersonnel, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_qualificationOfPersonnel = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_configurationChanged != null)
            {
                children.Add(m_configurationChanged);
            }

            if (m_estimatedDowntime != null)
            {
                children.Add(m_estimatedDowntime);
            }

            if (m_maintenanceMethod != null)
            {
                children.Add(m_maintenanceMethod);
            }

            if (m_maintenanceState != null)
            {
                children.Add(m_maintenanceState);
            }

            if (m_maintenanceSupplier != null)
            {
                children.Add(m_maintenanceSupplier);
            }

            if (m_partsOfAssetReplaced != null)
            {
                children.Add(m_partsOfAssetReplaced);
            }

            if (m_partsOfAssetServiced != null)
            {
                children.Add(m_partsOfAssetServiced);
            }

            if (m_plannedDate != null)
            {
                children.Add(m_plannedDate);
            }

            if (m_qualificationOfPersonnel != null)
            {
                children.Add(m_qualificationOfPersonnel);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_configurationChanged, child))
            {
                m_configurationChanged = null;
                return;
            }

            if (Object.ReferenceEquals(m_estimatedDowntime, child))
            {
                m_estimatedDowntime = null;
                return;
            }

            if (Object.ReferenceEquals(m_maintenanceMethod, child))
            {
                m_maintenanceMethod = null;
                return;
            }

            if (Object.ReferenceEquals(m_maintenanceState, child))
            {
                m_maintenanceState = null;
                return;
            }

            if (Object.ReferenceEquals(m_maintenanceSupplier, child))
            {
                m_maintenanceSupplier = null;
                return;
            }

            if (Object.ReferenceEquals(m_partsOfAssetReplaced, child))
            {
                m_partsOfAssetReplaced = null;
                return;
            }

            if (Object.ReferenceEquals(m_partsOfAssetServiced, child))
            {
                m_partsOfAssetServiced = null;
                return;
            }

            if (Object.ReferenceEquals(m_plannedDate, child))
            {
                m_plannedDate = null;
                return;
            }

            if (Object.ReferenceEquals(m_qualificationOfPersonnel, child))
            {
                m_qualificationOfPersonnel = null;
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
                case UAModel.AMB.BrowseNames.ConfigurationChanged:
                {
                    if (createOrReplace)
                    {
                        if (ConfigurationChanged == null)
                        {
                            if (replacement == null)
                            {
                                ConfigurationChanged = new PropertyState<bool>(this);
                            }
                            else
                            {
                                ConfigurationChanged = (PropertyState<bool>)replacement;
                            }
                        }
                    }

                    instance = ConfigurationChanged;
                    break;
                }

                case UAModel.AMB.BrowseNames.EstimatedDowntime:
                {
                    if (createOrReplace)
                    {
                        if (EstimatedDowntime == null)
                        {
                            if (replacement == null)
                            {
                                EstimatedDowntime = new PropertyState<double>(this);
                            }
                            else
                            {
                                EstimatedDowntime = (PropertyState<double>)replacement;
                            }
                        }
                    }

                    instance = EstimatedDowntime;
                    break;
                }

                case UAModel.AMB.BrowseNames.MaintenanceMethod:
                {
                    if (createOrReplace)
                    {
                        if (MaintenanceMethod == null)
                        {
                            if (replacement == null)
                            {
                                MaintenanceMethod = new PropertyState<MaintenanceMethodEnum>(this);
                            }
                            else
                            {
                                MaintenanceMethod = (PropertyState<MaintenanceMethodEnum>)replacement;
                            }
                        }
                    }

                    instance = MaintenanceMethod;
                    break;
                }

                case UAModel.AMB.BrowseNames.MaintenanceState:
                {
                    if (createOrReplace)
                    {
                        if (MaintenanceState == null)
                        {
                            if (replacement == null)
                            {
                                MaintenanceState = new MaintenanceEventStateMachineTypeState(this);
                            }
                            else
                            {
                                MaintenanceState = (MaintenanceEventStateMachineTypeState)replacement;
                            }
                        }
                    }

                    instance = MaintenanceState;
                    break;
                }

                case UAModel.AMB.BrowseNames.MaintenanceSupplier:
                {
                    if (createOrReplace)
                    {
                        if (MaintenanceSupplier == null)
                        {
                            if (replacement == null)
                            {
                                MaintenanceSupplier = new PropertyState<NameNodeIdDataType>(this);
                            }
                            else
                            {
                                MaintenanceSupplier = (PropertyState<NameNodeIdDataType>)replacement;
                            }
                        }
                    }

                    instance = MaintenanceSupplier;
                    break;
                }

                case UAModel.AMB.BrowseNames.PartsOfAssetReplaced:
                {
                    if (createOrReplace)
                    {
                        if (PartsOfAssetReplaced == null)
                        {
                            if (replacement == null)
                            {
                                PartsOfAssetReplaced = new PropertyState<NameNodeIdDataType[]>(this);
                            }
                            else
                            {
                                PartsOfAssetReplaced = (PropertyState<NameNodeIdDataType[]>)replacement;
                            }
                        }
                    }

                    instance = PartsOfAssetReplaced;
                    break;
                }

                case UAModel.AMB.BrowseNames.PartsOfAssetServiced:
                {
                    if (createOrReplace)
                    {
                        if (PartsOfAssetServiced == null)
                        {
                            if (replacement == null)
                            {
                                PartsOfAssetServiced = new PropertyState<NameNodeIdDataType[]>(this);
                            }
                            else
                            {
                                PartsOfAssetServiced = (PropertyState<NameNodeIdDataType[]>)replacement;
                            }
                        }
                    }

                    instance = PartsOfAssetServiced;
                    break;
                }

                case UAModel.AMB.BrowseNames.PlannedDate:
                {
                    if (createOrReplace)
                    {
                        if (PlannedDate == null)
                        {
                            if (replacement == null)
                            {
                                PlannedDate = new PropertyState<DateTime>(this);
                            }
                            else
                            {
                                PlannedDate = (PropertyState<DateTime>)replacement;
                            }
                        }
                    }

                    instance = PlannedDate;
                    break;
                }

                case UAModel.AMB.BrowseNames.QualificationOfPersonnel:
                {
                    if (createOrReplace)
                    {
                        if (QualificationOfPersonnel == null)
                        {
                            if (replacement == null)
                            {
                                QualificationOfPersonnel = new PropertyState<NameNodeIdDataType>(this);
                            }
                            else
                            {
                                QualificationOfPersonnel = (PropertyState<NameNodeIdDataType>)replacement;
                            }
                        }
                    }

                    instance = QualificationOfPersonnel;
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
        private PropertyState<bool> m_configurationChanged;
        private PropertyState<double> m_estimatedDowntime;
        private PropertyState<MaintenanceMethodEnum> m_maintenanceMethod;
        private MaintenanceEventStateMachineTypeState m_maintenanceState;
        private PropertyState<NameNodeIdDataType> m_maintenanceSupplier;
        private PropertyState<NameNodeIdDataType[]> m_partsOfAssetReplaced;
        private PropertyState<NameNodeIdDataType[]> m_partsOfAssetServiced;
        private PropertyState<DateTime> m_plannedDate;
        private PropertyState<NameNodeIdDataType> m_qualificationOfPersonnel;
        #endregion
    }
    #endif
    #endregion

    #region IRootCauseIndicationTypeState Class
    #if (!OPCUA_EXCLUDE_IRootCauseIndicationTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class IRootCauseIndicationTypeState : BaseInterfaceState
    {
        #region Constructors
        public IRootCauseIndicationTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.IRootCauseIndicationType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAIAAAAElS" +
           "b290Q2F1c2VJbmRpY2F0aW9uVHlwZUluc3RhbmNlAQHqAwEB6gPqAwAA/////wEAAAA3YIkKAgAAAAEA" +
           "EwAAAFBvdGVudGlhbFJvb3RDYXVzZXMBAX8XAwAAAADuAQAAQW4gYXJyYXkgb2YgcG90ZW50aWFsIHJv" +
           "b3QgY2F1c2VzIG9mIHRoZSBhbGFybS4gVGhpcyBpcyBpbnRlbmRlZCB0byBiZSBhIGhpbnQgdG8gdGhl" +
           "IGNsaWVudCBhbmQgbWlnaHQgYmUgYSBsb2NhbCB2aWV3IG9uIHRoZSBwb3RlbnRpYWwgcm9vdCBjYXVz" +
           "ZXMgb2YgdGhlIGFsYXJtLiBUaGUgbGlzdCBtaWdodCBub3QgY29udGFpbiBhbGwgcG90ZW50aWFsIHJv" +
           "b3QgY2F1c2VzLCB0aGF0IGlzLCBvdGhlciBwb3RlbnRpYWwgcm9vdCBjYXVzZXMgbWlnaHQgZXhpc3Qg" +
           "YXMgd2VsbC4gSWYgdGhlIGFsYXJtIGl0c2VsZiBpcyBjb25zaWRlcmVkIHRvIGJlIHRoZSByb290IGNh" +
           "dXNlLCB0aGUgYXJyYXkgc2hhbGwgYmUgZW1wdHkuIElmIG5vIHBvdGVudGlhbCByb290IGNhdXNlcyBo" +
           "YXZlIGJlZW4gaWRlbnRpZmllZCwgdGhlcmUgc2hhbGwgYmUgYXQgbGVhc3Qgb25lIGVudHJ5IGluIHRo" +
           "ZSBhcnJheSBpbmRpY2F0aW5nIHRoYXQgdGhlIHJvb3QgY2F1c2UgaXMgdW5rbm93bi4ALgBEfxcAAAEB" +
           "ugsBAAAAAQAAAAAAAAADA/////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public PropertyState<RootCauseDataType[]> PotentialRootCauses
        {
            get => m_potentialRootCauses;

            set
            {
                if (!Object.ReferenceEquals(m_potentialRootCauses, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_potentialRootCauses = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_potentialRootCauses != null)
            {
                children.Add(m_potentialRootCauses);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_potentialRootCauses, child))
            {
                m_potentialRootCauses = null;
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
                case UAModel.AMB.BrowseNames.PotentialRootCauses:
                {
                    if (createOrReplace)
                    {
                        if (PotentialRootCauses == null)
                        {
                            if (replacement == null)
                            {
                                PotentialRootCauses = new PropertyState<RootCauseDataType[]>(this);
                            }
                            else
                            {
                                PotentialRootCauses = (PropertyState<RootCauseDataType[]>)replacement;
                            }
                        }
                    }

                    instance = PotentialRootCauses;
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
        private PropertyState<RootCauseDataType[]> m_potentialRootCauses;
        #endregion
    }
    #endif
    #endregion

    #region DocumentationLinksTypeState Class
    #if (!OPCUA_EXCLUDE_DocumentationLinksTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class DocumentationLinksTypeState : BaseObjectState
    {
        #region Constructors
        public DocumentationLinksTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.DocumentationLinksType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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

            if (AddLink != null)
            {
                AddLink.Initialize(context, AddLink_InitializationString);
            }

            if (RemoveLink != null)
            {
                RemoveLink.Initialize(context, RemoveLink_InitializationString);
            }
        }

        #region Initialization String
        private const string AddLink_InitializationString =
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8kYYIKBAAAAAEABwAAAEFk" +
           "ZExpbmsBAVwbAwAAAABSAAAATWV0aG9kIHRvIGFkZCBhbiBlbmQtdXNlciBzcGVjaWZpYyBsaW5rIHRo" +
           "YXQgaXMgc3RvcmVkIHBlcnNpc3RlbnRseSBpbiB0aGUgc2VydmVyLgAvAQFcG1wbAAABAf////8CAAAA" +
           "F2CpCgIAAAAAAA4AAABJbnB1dEFyZ3VtZW50cwEBghcALgBEghcAAJYEAAAAAQAqAQGsAAAAFAAAAExp" +
           "bmtUb0V4dGVybmFsU291cmNlAQDHXP////8AAAAAAoMAAABMaW5rIHRvIGFuIGV4dGVybmFsIHNvdXJj" +
           "ZS4gVGhlIHNlcnZlciBtaWdodCBvciBtaWdodCBub3QgY2hlY2sgaWYgYSBjb3JyZWN0IFVSSSBpcyBw" +
           "cm92aWRlZCwgb3IgaWYgdGhlIFVSSSBpcyBhdmFpbGFibGUvcmVhY2hhYmxlLgEAKgEBiAAAAAoAAABC" +
           "cm93c2VOYW1lABT/////AAAAAAJrAAAAVGhlIEJyb3dzZU5hbWUgb2YgdGhlIG5ldyBjcmVhdGVkIE5v" +
           "ZGUuIE1ldGhvZCBmYWlscyBpZiBhIFZhcmlhYmxlIHdpdGggdGhlIHNhbWUgQnJvd3NlTmFtZSBhbHJl" +
           "YWR5IGV4aXN0cy4BACoBAdgAAAALAAAARGlzcGxheU5hbWUAFf////8AAAAAAroAAABUaGUgRGlzcGxh" +
           "eU5hbWUgb2YgdGhlIG5ldyBjcmVhdGVkIE5vZGUuIElmIHRoZSBzZXJ2ZXIgc3VwcG9ydHMgbXVsdGlw" +
           "bGUgbG9jYWxlcywgYW5kIHRoZSBDbGllbnQgd2FudHMgdG8gcHJvdmlkZSBtb3JlIHRoYW4gb25lIGxv" +
           "Y2FsZSwgdGhlIFdyaXRlIG9wZXJhdGlvbiBvbiB0aGUgVmFyaWFibGUgc2hhbGwgYmUgdXNlZC4BACoB" +
           "AdgAAAALAAAARGVzY3JpcHRpb24AFf////8AAAAAAroAAABUaGUgRGVzY3JpcHRpb24gb2YgdGhlIG5l" +
           "dyBjcmVhdGVkIE5vZGUuIElmIHRoZSBzZXJ2ZXIgc3VwcG9ydHMgbXVsdGlwbGUgbG9jYWxlcywgYW5k" +
           "IHRoZSBDbGllbnQgd2FudHMgdG8gcHJvdmlkZSBtb3JlIHRoYW4gb25lIGxvY2FsZSwgdGhlIFdyaXRl" +
           "IG9wZXJhdGlvbiBvbiB0aGUgVmFyaWFibGUgc2hhbGwgYmUgdXNlZC4BACgBAQAAAAEAAAAEAAAAAQH/" +
           "////AAAAABdgqQoCAAAAAAAPAAAAT3V0cHV0QXJndW1lbnRzAQGDFwAuAESDFwAAlgEAAAABACoBAUgA" +
           "AAAMAAAATGlua1ZhcmlhYmxlABH/////AAAAAAIpAAAAVGhlIE5vZGVJZCBvZiB0aGUgbmV3bHkgY3Jl" +
           "YXRlZCBWYXJpYWJsZS4BACgBAQAAAAEAAAABAAAAAQH/////AAAAAA==";

        private const string RemoveLink_InitializationString =
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8kYYIKBAAAAAEACgAAAFJl" +
           "bW92ZUxpbmsBAV0bAwAAAABJAAAATWV0aG9kIHRvIHJlbW92ZSBhbiBlbmQtdXNlciBzcGVjaWZpYyBs" +
           "aW5rIHRoYXQgaXMgbWFuYWdlZCBpbiB0aGUgc2VydmVyLgAvAQFdG10bAAABAf////8BAAAAF2CpCgIA" +
           "AAAAAA4AAABJbnB1dEFyZ3VtZW50cwEBhBcALgBEhBcAAJYBAAAAAQAqAQHRAAAAEwAAAFZhcmlhYmxl" +
           "VG9CZURlbGV0ZWQAEf////8AAAAAAqsAAABOb2RlSWQgb2YgdGhlIFZhcmlhYmxlIGNvbnRhaW5pbmcg" +
           "YSBsaW5rLCB0aGF0IHNob3VsZCBiZSBkZWxldGVkLiBWYXJpYWJsZSBzaGFsbCBiZSByZWZlcmVuY2Vk" +
           "IGZyb20gdGhlIE9iamVjdCB3aXRoIGEgSGFzQ29tcG9uZW50IFJlZmVyZW5jZSB3aGVyZSB0aGUgTWV0" +
           "aG9kIGlzIGNhbGxlZCBvbi4BACgBAQAAAAEAAAABAAAAAQH/////AAAAAA==";

        private const string InitializationString =
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAHgAAAERv" +
           "Y3VtZW50YXRpb25MaW5rc1R5cGVJbnN0YW5jZQEB8wMBAfMD8wMAAP////8EAAAANWDJCgIAAAAQAAAA" +
           "TGlua19QbGFjZWhvbGRlcgEABgAAADxMaW5rPgEBgRcDAAAAAEUAAABSZXByZXNlbnRzIGxpbmtzIHRv" +
           "IGV4dGVybmFsbHkgbWFuYWdlZCBkb2N1bWVudGF0aW9uLCB0eXBpY2FsbHkgVVJMcy4ALwA/gRcAAAEA" +
           "x1z/////AwP/////AAAAACRhggoEAAAAAQAHAAAAQWRkTGluawEBXBsDAAAAAFIAAABNZXRob2QgdG8g" +
           "YWRkIGFuIGVuZC11c2VyIHNwZWNpZmljIGxpbmsgdGhhdCBpcyBzdG9yZWQgcGVyc2lzdGVudGx5IGlu" +
           "IHRoZSBzZXJ2ZXIuAC8BAVwbXBsAAAEB/////wIAAAAXYKkKAgAAAAAADgAAAElucHV0QXJndW1lbnRz" +
           "AQGCFwAuAESCFwAAlgQAAAABACoBAawAAAAUAAAATGlua1RvRXh0ZXJuYWxTb3VyY2UBAMdc/////wAA" +
           "AAACgwAAAExpbmsgdG8gYW4gZXh0ZXJuYWwgc291cmNlLiBUaGUgc2VydmVyIG1pZ2h0IG9yIG1pZ2h0" +
           "IG5vdCBjaGVjayBpZiBhIGNvcnJlY3QgVVJJIGlzIHByb3ZpZGVkLCBvciBpZiB0aGUgVVJJIGlzIGF2" +
           "YWlsYWJsZS9yZWFjaGFibGUuAQAqAQGIAAAACgAAAEJyb3dzZU5hbWUAFP////8AAAAAAmsAAABUaGUg" +
           "QnJvd3NlTmFtZSBvZiB0aGUgbmV3IGNyZWF0ZWQgTm9kZS4gTWV0aG9kIGZhaWxzIGlmIGEgVmFyaWFi" +
           "bGUgd2l0aCB0aGUgc2FtZSBCcm93c2VOYW1lIGFscmVhZHkgZXhpc3RzLgEAKgEB2AAAAAsAAABEaXNw" +
           "bGF5TmFtZQAV/////wAAAAACugAAAFRoZSBEaXNwbGF5TmFtZSBvZiB0aGUgbmV3IGNyZWF0ZWQgTm9k" +
           "ZS4gSWYgdGhlIHNlcnZlciBzdXBwb3J0cyBtdWx0aXBsZSBsb2NhbGVzLCBhbmQgdGhlIENsaWVudCB3" +
           "YW50cyB0byBwcm92aWRlIG1vcmUgdGhhbiBvbmUgbG9jYWxlLCB0aGUgV3JpdGUgb3BlcmF0aW9uIG9u" +
           "IHRoZSBWYXJpYWJsZSBzaGFsbCBiZSB1c2VkLgEAKgEB2AAAAAsAAABEZXNjcmlwdGlvbgAV/////wAA" +
           "AAACugAAAFRoZSBEZXNjcmlwdGlvbiBvZiB0aGUgbmV3IGNyZWF0ZWQgTm9kZS4gSWYgdGhlIHNlcnZl" +
           "ciBzdXBwb3J0cyBtdWx0aXBsZSBsb2NhbGVzLCBhbmQgdGhlIENsaWVudCB3YW50cyB0byBwcm92aWRl" +
           "IG1vcmUgdGhhbiBvbmUgbG9jYWxlLCB0aGUgV3JpdGUgb3BlcmF0aW9uIG9uIHRoZSBWYXJpYWJsZSBz" +
           "aGFsbCBiZSB1c2VkLgEAKAEBAAAAAQAAAAQAAAABAf////8AAAAAF2CpCgIAAAAAAA8AAABPdXRwdXRB" +
           "cmd1bWVudHMBAYMXAC4ARIMXAACWAQAAAAEAKgEBSAAAAAwAAABMaW5rVmFyaWFibGUAEf////8AAAAA" +
           "AikAAABUaGUgTm9kZUlkIG9mIHRoZSBuZXdseSBjcmVhdGVkIFZhcmlhYmxlLgEAKAEBAAAAAQAAAAEA" +
           "AAABAf////8AAAAAFWCpCgIAAAAAABkAAABEZWZhdWx0SW5zdGFuY2VCcm93c2VOYW1lAQGAFwAuAESA" +
           "FwAAFAEAEgAAAERvY3VtZW50YXRpb25MaW5rcwAU/////wMD/////wAAAAAkYYIKBAAAAAEACgAAAFJl" +
           "bW92ZUxpbmsBAV0bAwAAAABJAAAATWV0aG9kIHRvIHJlbW92ZSBhbiBlbmQtdXNlciBzcGVjaWZpYyBs" +
           "aW5rIHRoYXQgaXMgbWFuYWdlZCBpbiB0aGUgc2VydmVyLgAvAQFdG10bAAABAf////8BAAAAF2CpCgIA" +
           "AAAAAA4AAABJbnB1dEFyZ3VtZW50cwEBhBcALgBEhBcAAJYBAAAAAQAqAQHRAAAAEwAAAFZhcmlhYmxl" +
           "VG9CZURlbGV0ZWQAEf////8AAAAAAqsAAABOb2RlSWQgb2YgdGhlIFZhcmlhYmxlIGNvbnRhaW5pbmcg" +
           "YSBsaW5rLCB0aGF0IHNob3VsZCBiZSBkZWxldGVkLiBWYXJpYWJsZSBzaGFsbCBiZSByZWZlcmVuY2Vk" +
           "IGZyb20gdGhlIE9iamVjdCB3aXRoIGEgSGFzQ29tcG9uZW50IFJlZmVyZW5jZSB3aGVyZSB0aGUgTWV0" +
           "aG9kIGlzIGNhbGxlZCBvbi4BACgBAQAAAAEAAAABAAAAAQH/////AAAAAA==";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public AddLinkMethodState AddLink
        {
            get => m_addLinkMethod;

            set
            {
                if (!Object.ReferenceEquals(m_addLinkMethod, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_addLinkMethod = value;
            }
        }

        public RemoveLinkMethodState RemoveLink
        {
            get => m_removeLinkMethod;

            set
            {
                if (!Object.ReferenceEquals(m_removeLinkMethod, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_removeLinkMethod = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_addLinkMethod != null)
            {
                children.Add(m_addLinkMethod);
            }

            if (m_removeLinkMethod != null)
            {
                children.Add(m_removeLinkMethod);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_addLinkMethod, child))
            {
                m_addLinkMethod = null;
                return;
            }

            if (Object.ReferenceEquals(m_removeLinkMethod, child))
            {
                m_removeLinkMethod = null;
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
                case UAModel.AMB.BrowseNames.AddLink:
                {
                    if (createOrReplace)
                    {
                        if (AddLink == null)
                        {
                            if (replacement == null)
                            {
                                AddLink = new AddLinkMethodState(this);
                            }
                            else
                            {
                                AddLink = (AddLinkMethodState)replacement;
                            }
                        }
                    }

                    instance = AddLink;
                    break;
                }

                case UAModel.AMB.BrowseNames.RemoveLink:
                {
                    if (createOrReplace)
                    {
                        if (RemoveLink == null)
                        {
                            if (replacement == null)
                            {
                                RemoveLink = new RemoveLinkMethodState(this);
                            }
                            else
                            {
                                RemoveLink = (RemoveLinkMethodState)replacement;
                            }
                        }
                    }

                    instance = RemoveLink;
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
        private AddLinkMethodState m_addLinkMethod;
        private RemoveLinkMethodState m_removeLinkMethod;
        #endregion
    }
    #endif
    #endregion

    #region MaintenanceEventStateMachineTypeState Class
    #if (!OPCUA_EXCLUDE_MaintenanceEventStateMachineTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class MaintenanceEventStateMachineTypeState : FiniteStateMachineState
    {
        #region Constructors
        public MaintenanceEventStateMachineTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.AMB.ObjectTypes.MaintenanceEventStateMachineType, UAModel.AMB.Namespaces.AMB, namespaceUris);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYIACAQAAAAEAKAAAAE1h" +
           "aW50ZW5hbmNlRXZlbnRTdGF0ZU1hY2hpbmVUeXBlSW5zdGFuY2UBAfUDAQH1A/UDAAD/////BwAAABVg" +
           "iQgCAAAAAAAMAAAAQ3VycmVudFN0YXRlAQEAAAAvAQDICgAV/////wEB/////wEAAAAVYIkIAgAAAAAA" +
           "AgAAAElkAQEAAAAuAEQAEf////8BAf////8AAAAABGCACgEAAAABAAkAAABFeGVjdXRpbmcBAY8TAC8B" +
           "AAMJjxMAAAIAAAAAMwEBAZITADQBAQGREwEAAAAVYKkKAgAAAAAACwAAAFN0YXRlTnVtYmVyAQGGFwAu" +
           "AESGFwAABwIAAAAAB/////8BAf////8AAAAABGCACgEAAAABAAgAAABGaW5pc2hlZAEBkBMALwEAAwmQ" +
           "EwAAAgAAAAA0AQEBkhMAMwEBAZMTAQAAABVgqQoCAAAAAAALAAAAU3RhdGVOdW1iZXIBAYcXAC4ARIcX" +
           "AAAHAwAAAAAH/////wEB/////wAAAAAEYIAKAQAAAAEAFwAAAEZyb21FeGVjdXRpbmdUb0ZpbmlzaGVk" +
           "AQGSEwAvAQAGCZITAAACAAAAADMAAQGPEwA0AAEBkBMBAAAAFWCpCgIAAAAAABAAAABUcmFuc2l0aW9u" +
           "TnVtYmVyAQGJFwAuAESJFwAABwIAAAAAB/////8BAf////8AAAAABGCACgEAAAABABUAAABGcm9tRmlu" +
           "aXNoZWRUb1BsYW5uZWQBAZMTAC8BAAYJkxMAAAIAAAAAMwABAZATADQAAQGOEwEAAAAVYKkKAgAAAAAA" +
           "EAAAAFRyYW5zaXRpb25OdW1iZXIBAYoXAC4ARIoXAAAHAwAAAAAH/////wEB/////wAAAAAEYIAKAQAA" +
           "AAEAFgAAAEZyb21QbGFubmVkVG9FeGVjdXRpbmcBAZETAC8BAAYJkRMAAAIAAAAANAABAY8TADMAAQGO" +
           "EwEAAAAVYKkKAgAAAAAAEAAAAFRyYW5zaXRpb25OdW1iZXIBAYgXAC4ARIgXAAAHAQAAAAAH/////wEB" +
           "/////wAAAAAEYIAKAQAAAAEABwAAAFBsYW5uZWQBAY4TAC8BAAUJjhMAAAIAAAAANAEBAZMTADMBAQGR" +
           "EwEAAAAVYKkKAgAAAAAACwAAAFN0YXRlTnVtYmVyAQGFFwAuAESFFwAABwEAAAAAB/////8BAf////8A" +
           "AAAA";
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

    #region AddLinkMethodState Class
    #if (!OPCUA_EXCLUDE_AddLinkMethodState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class AddLinkMethodState : MethodState
    {
        #region Constructors
        public AddLinkMethodState(NodeState parent) : base(parent)
        {
        }

        public new static NodeState Construct(NodeState parent)
        {
            return new AddLinkMethodState(parent);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYYIABAAAAAEAEQAAAEFk" +
           "ZExpbmtNZXRob2RUeXBlAQEAAAEBAAABAf////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Event Callbacks
        public AddLinkMethodStateMethodCallHandler OnCall;

        public AddLinkMethodStateMethodAsyncCallHandler OnCallAsync;
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

            string linkToExternalSource = (string)_inputArguments[0];
            QualifiedName browseName = (QualifiedName)_inputArguments[1];
            LocalizedText displayName = (LocalizedText)_inputArguments[2];
            LocalizedText description = (LocalizedText)_inputArguments[3];

            NodeId linkVariable = (NodeId)_outputArguments[0];

            if (OnCall != null)
            {
                _result = OnCall(
                    _context,
                    this,
                    _objectId,
                    linkToExternalSource,
                    browseName,
                    displayName,
                    description,
                    ref linkVariable);
            }

            _outputArguments[0] = linkVariable;

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

            AddLinkMethodStateResult _result = null;

            string linkToExternalSource = (string)_inputArguments[0];
            QualifiedName browseName = (QualifiedName)_inputArguments[1];
            LocalizedText displayName = (LocalizedText)_inputArguments[2];
            LocalizedText description = (LocalizedText)_inputArguments[3];

            if (OnCallAsync != null)
            {
                _result = await OnCallAsync(
                    _context,
                    this,
                    _objectId,
                    linkToExternalSource,
                    browseName,
                    displayName,
                    description,
                    cancellationToken).ConfigureAwait(false);
            }
            else if (OnCall != null)
            {
                return Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            _outputArguments[0] = _result.LinkVariable;

            return _result.ServiceResult;
        }
        #endif

        #endregion

        #region Private Fields
        #endregion
    }

    /// <exclude />
    public delegate ServiceResult AddLinkMethodStateMethodCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        string linkToExternalSource,
        QualifiedName browseName,
        LocalizedText displayName,
        LocalizedText description,
        ref NodeId linkVariable);

    /// <exclude />
    public partial class AddLinkMethodStateResult
    {
        public ServiceResult ServiceResult { get; set; }
        public NodeId LinkVariable { get; set; }
    }

    /// <exclude />
    public delegate ValueTask<AddLinkMethodStateResult> AddLinkMethodStateMethodAsyncCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        string linkToExternalSource,
        QualifiedName browseName,
        LocalizedText displayName,
        LocalizedText description,
        CancellationToken cancellationToken);
    #endif
    #endregion

    #region RemoveLinkMethodState Class
    #if (!OPCUA_EXCLUDE_RemoveLinkMethodState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class RemoveLinkMethodState : MethodState
    {
        #region Constructors
        public RemoveLinkMethodState(NodeState parent) : base(parent)
        {
        }

        public new static NodeState Construct(NodeState parent)
        {
            return new RemoveLinkMethodState(parent);
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
           "AQAAACAAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvQU1CL/////8EYYIABAAAAAEAFAAAAFJl" +
           "bW92ZUxpbmtNZXRob2RUeXBlAQEAAAEBAAABAf////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Event Callbacks
        public RemoveLinkMethodStateMethodCallHandler OnCall;

        public RemoveLinkMethodStateMethodAsyncCallHandler OnCallAsync;
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

            NodeId variableToBeDeleted = (NodeId)_inputArguments[0];

            if (OnCall != null)
            {
                _result = OnCall(
                    _context,
                    this,
                    _objectId,
                    variableToBeDeleted);
            }

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

            RemoveLinkMethodStateResult _result = null;

            NodeId variableToBeDeleted = (NodeId)_inputArguments[0];

            if (OnCallAsync != null)
            {
                _result = await OnCallAsync(
                    _context,
                    this,
                    _objectId,
                    variableToBeDeleted,
                    cancellationToken).ConfigureAwait(false);
            }
            else if (OnCall != null)
            {
                return Call(_context, _objectId, _inputArguments, _outputArguments);
            }

            return _result.ServiceResult;
        }
        #endif

        #endregion

        #region Private Fields
        #endregion
    }

    /// <exclude />
    public delegate ServiceResult RemoveLinkMethodStateMethodCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        NodeId variableToBeDeleted);

    /// <exclude />
    public partial class RemoveLinkMethodStateResult
    {
        public ServiceResult ServiceResult { get; set; }
    }

    /// <exclude />
    public delegate ValueTask<RemoveLinkMethodStateResult> RemoveLinkMethodStateMethodAsyncCallHandler(
        ISystemContext _context,
        MethodState _method,
        NodeId _objectId,
        NodeId variableToBeDeleted,
        CancellationToken cancellationToken);
    #endif
    #endregion
}