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

#pragma warning disable CS1591 // Missing XML comment for publicly visible type or member
#pragma warning disable CA1515 // Consider making public types internal
#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1028 // Enum Storage should be Int32

namespace UAModel.IA
{
    #region CalibrationValueTypeState Class
    #if (!OPCUA_EXCLUDE_CalibrationValueTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class CalibrationValueTypeState : DataItemState
    {
        #region Constructors
        public CalibrationValueTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.VariableTypes.CalibrationValueType, UAModel.IA.Namespaces.IA, namespaceUris);
        }

        protected override NodeId GetDefaultDataTypeId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(Opc.Ua.DataTypes.Number, Opc.Ua.Namespaces.OpcUa, namespaceUris);
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
        }

        #region Initialization String
        private const string InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////FWCBAgIAAAABABwAAABDYWxpYnJhdGlvblZhbHVlVHlwZUluc3RhbmNl" +
           "AQHSBwEB0gfSBwAAABoBAf////8BAAAAFWCJCgIAAAAAABAAAABFbmdpbmVlcmluZ1VuaXRzAQGpFwAu" +
           "AESpFwAAAQB3A/////8DA/////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public PropertyState<EUInformation> EngineeringUnits
        {
            get => m_engineeringUnits;

            set
            {
                if (!Object.ReferenceEquals(m_engineeringUnits, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_engineeringUnits = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_engineeringUnits != null)
            {
                children.Add(m_engineeringUnits);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_engineeringUnits, child))
            {
                m_engineeringUnits = null;
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
                case Opc.Ua.BrowseNames.EngineeringUnits:
                {
                    if (createOrReplace)
                    {
                        if (EngineeringUnits == null)
                        {
                            if (replacement == null)
                            {
                                EngineeringUnits = new PropertyState<EUInformation>(this);
                            }
                            else
                            {
                                EngineeringUnits = (PropertyState<EUInformation>)replacement;
                            }
                        }
                    }

                    instance = EngineeringUnits;
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
        private PropertyState<EUInformation> m_engineeringUnits;
        #endregion
    }

    #region CalibrationValueTypeState<T> Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public class CalibrationValueTypeState<T> : CalibrationValueTypeState
    {
        #region Constructors
        public CalibrationValueTypeState(NodeState parent) : base(parent)
        {
            Value = default(T);
        }

        protected override void Initialize(ISystemContext context)
        {
            base.Initialize(context);

            Value = default(T);
            DataType = TypeInfo.GetDataTypeId(typeof(T));
            ValueRank = TypeInfo.GetValueRank(typeof(T));
        }

        protected override void Initialize(ISystemContext context, NodeState source)
        {
            InitializeOptionalChildren(context);
            base.Initialize(context, source);
        }
        #endregion

        #region Public Members
        public new T Value
        {
            get
            {
                return CheckTypeBeforeCast<T>(((BaseVariableState)this).Value, true);
            }

            set
            {
                ((BaseVariableState)this).Value = value;
            }
        }
        #endregion
    }
    #endregion
    #endif
    #endregion

    #region CapacityRangeTypeState Class
    #if (!OPCUA_EXCLUDE_CapacityRangeTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class CapacityRangeTypeState : DataItemState<Opc.Ua.Range>
    {
        #region Constructors
        public CapacityRangeTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.VariableTypes.CapacityRangeType, UAModel.IA.Namespaces.IA, namespaceUris);
        }

        protected override NodeId GetDefaultDataTypeId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(Opc.Ua.DataTypes.Range, Opc.Ua.Namespaces.OpcUa, namespaceUris);
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
        }

        #region Initialization String
        private const string InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////FWCJAgIAAAABABkAAABDYXBhY2l0eVJhbmdlVHlwZUluc3RhbmNlAQHT" +
           "BwEB0wfTBwAAAQB0A/////8BAf////8CAAAAFWCJCgIAAAAAABAAAABFbmdpbmVlcmluZ1VuaXRzAQGq" +
           "FwAuAESqFwAAAQB3A/////8DA/////8AAAAAFWCJCgIAAAABAAoAAABSZXNvbHV0aW9uAQGrFwAuAESr" +
           "FwAAAAv/////AwP/////AAAAAA==";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public PropertyState<EUInformation> EngineeringUnits
        {
            get => m_engineeringUnits;

            set
            {
                if (!Object.ReferenceEquals(m_engineeringUnits, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_engineeringUnits = value;
            }
        }

        public PropertyState<double> Resolution
        {
            get => m_resolution;

            set
            {
                if (!Object.ReferenceEquals(m_resolution, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_resolution = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_engineeringUnits != null)
            {
                children.Add(m_engineeringUnits);
            }

            if (m_resolution != null)
            {
                children.Add(m_resolution);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_engineeringUnits, child))
            {
                m_engineeringUnits = null;
                return;
            }

            if (Object.ReferenceEquals(m_resolution, child))
            {
                m_resolution = null;
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
                case Opc.Ua.BrowseNames.EngineeringUnits:
                {
                    if (createOrReplace)
                    {
                        if (EngineeringUnits == null)
                        {
                            if (replacement == null)
                            {
                                EngineeringUnits = new PropertyState<EUInformation>(this);
                            }
                            else
                            {
                                EngineeringUnits = (PropertyState<EUInformation>)replacement;
                            }
                        }
                    }

                    instance = EngineeringUnits;
                    break;
                }

                case UAModel.IA.BrowseNames.Resolution:
                {
                    if (createOrReplace)
                    {
                        if (Resolution == null)
                        {
                            if (replacement == null)
                            {
                                Resolution = new PropertyState<double>(this);
                            }
                            else
                            {
                                Resolution = (PropertyState<double>)replacement;
                            }
                        }
                    }

                    instance = Resolution;
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
        private PropertyState<EUInformation> m_engineeringUnits;
        private PropertyState<double> m_resolution;
        #endregion
    }
    #endif
    #endregion

    #region AcousticSignalTypeState Class
    #if (!OPCUA_EXCLUDE_AcousticSignalTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class AcousticSignalTypeState : BaseObjectState
    {
        #region Constructors
        public AcousticSignalTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.AcousticSignalType, UAModel.IA.Namespaces.IA, namespaceUris);
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

            if (AudioSample != null)
            {
                AudioSample.Initialize(context, AudioSample_InitializationString);
            }
        }

        #region Initialization String
        private const string AudioSample_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABAAsAAABBdWRpb1NhbXBsZQEBjRcDAAAAAEQAAABDb250" +
           "YWlucyB0aGUgYXVkaW8gZGF0YSwgZS5nLiBmb3IgZGV2aWNlcyBjYXBhYmxlIG9mIGF1ZGlvIHBsYXli" +
           "YWNrLgAvAD+NFwAAAQCzP/////8DA/////8AAAAA";

        private const string InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABABoAAABBY291c3RpY1NpZ25hbFR5cGVJbnN0YW5jZQEB" +
           "8QMBAfED8QMAAAEAAAABAMNEAAEA2VsCAAAANWCJCgIAAAABAAsAAABBdWRpb1NhbXBsZQEBjRcDAAAA" +
           "AEQAAABDb250YWlucyB0aGUgYXVkaW8gZGF0YSwgZS5nLiBmb3IgZGV2aWNlcyBjYXBhYmxlIG9mIGF1" +
           "ZGlvIHBsYXliYWNrLgAvAD+NFwAAAQCzP/////8DA/////8AAAAANWCJCgIAAAAAAAwAAABOdW1iZXJJ" +
           "bkxpc3QBAYwXAwAAAAB+AAAARW51bWVyYXRlIHRoZSBhY291c3RpYyBzaWduYWxzLiBJbnN0YW5jZXMg" +
           "b2YgU3RhY2tFbGVtZW50QWNvdXN0aWNUeXBlIGluZGV4IGludG8gdGhpcyBudW1iZXIgdXNpbmcgdGhl" +
           "IE9wZXJhdGlvbk1vZGUgUHJvcGVydHkuAC4ARIwXAAAAHP////8DA/////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public BaseDataVariableState<byte[]> AudioSample
        {
            get => m_audioSample;

            set
            {
                if (!Object.ReferenceEquals(m_audioSample, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_audioSample = value;
            }
        }

        public PropertyState NumberInList
        {
            get => m_numberInList;

            set
            {
                if (!Object.ReferenceEquals(m_numberInList, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_numberInList = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_audioSample != null)
            {
                children.Add(m_audioSample);
            }

            if (m_numberInList != null)
            {
                children.Add(m_numberInList);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_audioSample, child))
            {
                m_audioSample = null;
                return;
            }

            if (Object.ReferenceEquals(m_numberInList, child))
            {
                m_numberInList = null;
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
                case UAModel.IA.BrowseNames.AudioSample:
                {
                    if (createOrReplace)
                    {
                        if (AudioSample == null)
                        {
                            if (replacement == null)
                            {
                                AudioSample = new BaseDataVariableState<byte[]>(this);
                            }
                            else
                            {
                                AudioSample = (BaseDataVariableState<byte[]>)replacement;
                            }
                        }
                    }

                    instance = AudioSample;
                    break;
                }

                case Opc.Ua.BrowseNames.NumberInList:
                {
                    if (createOrReplace)
                    {
                        if (NumberInList == null)
                        {
                            if (replacement == null)
                            {
                                NumberInList = new PropertyState(this);
                            }
                            else
                            {
                                NumberInList = (PropertyState)replacement;
                            }
                        }
                    }

                    instance = NumberInList;
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
        private BaseDataVariableState<byte[]> m_audioSample;
        private PropertyState m_numberInList;
        #endregion
    }
    #endif
    #endregion

    #region BaseCalibrationTargetCategoryTypeState Class
    #if (!OPCUA_EXCLUDE_BaseCalibrationTargetCategoryTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class BaseCalibrationTargetCategoryTypeState : BaseObjectState
    {
        #region Constructors
        public BaseCalibrationTargetCategoryTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.BaseCalibrationTargetCategoryType, UAModel.IA.Namespaces.IA, namespaceUris);
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
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABACkAAABCYXNlQ2FsaWJyYXRpb25UYXJnZXRDYXRlZ29y" +
           "eVR5cGVJbnN0YW5jZQEB9gMBAfYD9gMAAP////8AAAAA";
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

    #region DynamicCalibrationTargetCategoryTypeState Class
    #if (!OPCUA_EXCLUDE_DynamicCalibrationTargetCategoryTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class DynamicCalibrationTargetCategoryTypeState : BaseCalibrationTargetCategoryTypeState
    {
        #region Constructors
        public DynamicCalibrationTargetCategoryTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.DynamicCalibrationTargetCategoryType, UAModel.IA.Namespaces.IA, namespaceUris);
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
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABACwAAABEeW5hbWljQ2FsaWJyYXRpb25UYXJnZXRDYXRl" +
           "Z29yeVR5cGVJbnN0YW5jZQEB+gMBAfoD+gMAAP////8AAAAA";
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

    #region OneTimeCalibrationTargetCategoryTypeState Class
    #if (!OPCUA_EXCLUDE_OneTimeCalibrationTargetCategoryTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class OneTimeCalibrationTargetCategoryTypeState : BaseCalibrationTargetCategoryTypeState
    {
        #region Constructors
        public OneTimeCalibrationTargetCategoryTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.OneTimeCalibrationTargetCategoryType, UAModel.IA.Namespaces.IA, namespaceUris);
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
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABACwAAABPbmVUaW1lQ2FsaWJyYXRpb25UYXJnZXRDYXRl" +
           "Z29yeVR5cGVJbnN0YW5jZQEB+QMBAfkD+QMAAP////8AAAAA";
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

    #region ReusableCalibrationTargetCategoryTypeState Class
    #if (!OPCUA_EXCLUDE_ReusableCalibrationTargetCategoryTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class ReusableCalibrationTargetCategoryTypeState : BaseCalibrationTargetCategoryTypeState
    {
        #region Constructors
        public ReusableCalibrationTargetCategoryTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.ReusableCalibrationTargetCategoryType, UAModel.IA.Namespaces.IA, namespaceUris);
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
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABAC0AAABSZXVzYWJsZUNhbGlicmF0aW9uVGFyZ2V0Q2F0" +
           "ZWdvcnlUeXBlSW5zdGFuY2UBAfcDAQH3A/cDAAD/////AAAAAA==";
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

    #region ReusableDeviceCalibrationTargetCategoryTypeState Class
    #if (!OPCUA_EXCLUDE_ReusableDeviceCalibrationTargetCategoryTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class ReusableDeviceCalibrationTargetCategoryTypeState : ReusableCalibrationTargetCategoryTypeState
    {
        #region Constructors
        public ReusableDeviceCalibrationTargetCategoryTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.ReusableDeviceCalibrationTargetCategoryType, UAModel.IA.Namespaces.IA, namespaceUris);
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
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABADMAAABSZXVzYWJsZURldmljZUNhbGlicmF0aW9uVGFy" +
           "Z2V0Q2F0ZWdvcnlUeXBlSW5zdGFuY2UBAfgDAQH4A/gDAAD/////AAAAAA==";
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

    #region IStatisticsTypeState Class
    #if (!OPCUA_EXCLUDE_IStatisticsTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class IStatisticsTypeState : BaseInterfaceState
    {
        #region Constructors
        public IStatisticsTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.IStatisticsType, UAModel.IA.Namespaces.IA, namespaceUris);
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

            if (ResetStatistics != null)
            {
                ResetStatistics.Initialize(context, ResetStatistics_InitializationString);
            }

            if (StartTime != null)
            {
                StartTime.Initialize(context, StartTime_InitializationString);
            }
        }

        #region Initialization String
        private const string ResetStatistics_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////JGGCCgQAAAABAA8AAABSZXNldFN0YXRpc3RpY3MBAVkbAwAAAABWAAAA" +
           "UmVzdGFydHMgYWxsIHN0YXRpc3RpY2FsIGRhdGEsIGluY2x1ZGluZyBhIHJlc2V0IG9mIHRoZSBTdGFy" +
           "dFRpbWUgdG8gdGhlIGN1cnJlbnQgdGltZS4ALwEBWRtZGwAAAQH/////AAAAAA==";

        private const string StartTime_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABAAkAAABTdGFydFRpbWUBAZ4XAwAAAABdAAAASW5kaWNh" +
           "dGVzIHRoZSBwb2ludCBpbiB0aW1lIGF0IHdoaWNoIHRoZSBjb2xsZWN0aW9uIG9mIHRoZSBzdGF0aXN0" +
           "aWNhbCBkYXRhIGhhcyBiZWVuIHN0YXJ0ZWQuAC4ARJ4XAAAADf////8DA/////8AAAAA";

        private const string InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABABcAAABJU3RhdGlzdGljc1R5cGVJbnN0YW5jZQEB8wMB" +
           "AfMD8wMAAP////8CAAAAJGGCCgQAAAABAA8AAABSZXNldFN0YXRpc3RpY3MBAVkbAwAAAABWAAAAUmVz" +
           "dGFydHMgYWxsIHN0YXRpc3RpY2FsIGRhdGEsIGluY2x1ZGluZyBhIHJlc2V0IG9mIHRoZSBTdGFydFRp" +
           "bWUgdG8gdGhlIGN1cnJlbnQgdGltZS4ALwEBWRtZGwAAAQH/////AAAAADVgiQoCAAAAAQAJAAAAU3Rh" +
           "cnRUaW1lAQGeFwMAAAAAXQAAAEluZGljYXRlcyB0aGUgcG9pbnQgaW4gdGltZSBhdCB3aGljaCB0aGUg" +
           "Y29sbGVjdGlvbiBvZiB0aGUgc3RhdGlzdGljYWwgZGF0YSBoYXMgYmVlbiBzdGFydGVkLgAuAESeFwAA" +
           "AA3/////AwP/////AAAAAA==";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public MethodState ResetStatistics
        {
            get => m_resetStatisticsMethod;

            set
            {
                if (!Object.ReferenceEquals(m_resetStatisticsMethod, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_resetStatisticsMethod = value;
            }
        }

        public PropertyState<DateTime> StartTime
        {
            get => m_startTime;

            set
            {
                if (!Object.ReferenceEquals(m_startTime, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_startTime = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_resetStatisticsMethod != null)
            {
                children.Add(m_resetStatisticsMethod);
            }

            if (m_startTime != null)
            {
                children.Add(m_startTime);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_resetStatisticsMethod, child))
            {
                m_resetStatisticsMethod = null;
                return;
            }

            if (Object.ReferenceEquals(m_startTime, child))
            {
                m_startTime = null;
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
                case UAModel.IA.BrowseNames.ResetStatistics:
                {
                    if (createOrReplace)
                    {
                        if (ResetStatistics == null)
                        {
                            if (replacement == null)
                            {
                                ResetStatistics = new MethodState(this);
                            }
                            else
                            {
                                ResetStatistics = (MethodState)replacement;
                            }
                        }
                    }

                    instance = ResetStatistics;
                    break;
                }

                case UAModel.IA.BrowseNames.StartTime:
                {
                    if (createOrReplace)
                    {
                        if (StartTime == null)
                        {
                            if (replacement == null)
                            {
                                StartTime = new PropertyState<DateTime>(this);
                            }
                            else
                            {
                                StartTime = (PropertyState<DateTime>)replacement;
                            }
                        }
                    }

                    instance = StartTime;
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
        private MethodState m_resetStatisticsMethod;
        private PropertyState<DateTime> m_startTime;
        #endregion
    }
    #endif
    #endregion

    #region IAggregateStatisticsTypeState Class
    #if (!OPCUA_EXCLUDE_IAggregateStatisticsTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class IAggregateStatisticsTypeState : IStatisticsTypeState
    {
        #region Constructors
        public IAggregateStatisticsTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.IAggregateStatisticsType, UAModel.IA.Namespaces.IA, namespaceUris);
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

            if (ResetCondition != null)
            {
                ResetCondition.Initialize(context, ResetCondition_InitializationString);
            }
        }

        #region Initialization String
        private const string ResetCondition_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABAA4AAABSZXNldENvbmRpdGlvbgEBnxcDAAAAANIBAABU" +
           "aGUgcmVhc29uIGFuZCBjb250ZXh0IGZvciB0aGUgcmVzZXQgb2YgdGhlIHN0YXRpc3RpY3MsIHdoaWNo" +
           "IGlzIGRvbmUgd2l0aG91dCBhIHRyaWdnZXIgZnJvbSBhbiBPUEMgVUEgQ2xpZW50LCBsaWtlIGNhbGxp" +
           "bmcgdGhlIFJlc2V0U3RhdGlzdGljcyBNZXRob2QuIFJlc2V0Q29uZGl0aW9uIGlzIGEgdmVuZG9yLXNw" +
           "ZWNpZmljLCBodW1hbiByZWFkYWJsZSBzdHJpbmcuIFJlc2V0Q29uZGl0aW9uIGlzIG5vbi1sb2NhbGl6" +
           "ZWQgYW5kIG1pZ2h0IGNvbnRhaW4gYW4gZXhwcmVzc2lvbiB0aGF0IGNhbiBiZSBwYXJzZWQgYnkgY2Vy" +
           "dGFpbiBjbGllbnRzLiBFeGFtcGxlcyBhcmU6IOKAnEFGVEVSIDQgSE9VUlPigJ0sIOKAnEFGVEVSIDEw" +
           "MDAgSVRFTVPigJ0sIOKAnE9QRVJBVE9S4oCdLiDigJxPUEVSQVRPUuKAnSBtZWFucywgdGhhdCBhbiBv" +
           "cGVyYXRvciByZXNldHMgdGhlIHN0YXRpc3RpY3Mgb24gYSBsb2NhbCBITUkuAC4ARJ8XAAAADP////8D" +
           "A/////8AAAAA";

        private const string InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABACAAAABJQWdncmVnYXRlU3RhdGlzdGljc1R5cGVJbnN0" +
           "YW5jZQEB9AMBAfQD9AMAAP////8BAAAANWCJCgIAAAABAA4AAABSZXNldENvbmRpdGlvbgEBnxcDAAAA" +
           "ANIBAABUaGUgcmVhc29uIGFuZCBjb250ZXh0IGZvciB0aGUgcmVzZXQgb2YgdGhlIHN0YXRpc3RpY3Ms" +
           "IHdoaWNoIGlzIGRvbmUgd2l0aG91dCBhIHRyaWdnZXIgZnJvbSBhbiBPUEMgVUEgQ2xpZW50LCBsaWtl" +
           "IGNhbGxpbmcgdGhlIFJlc2V0U3RhdGlzdGljcyBNZXRob2QuIFJlc2V0Q29uZGl0aW9uIGlzIGEgdmVu" +
           "ZG9yLXNwZWNpZmljLCBodW1hbiByZWFkYWJsZSBzdHJpbmcuIFJlc2V0Q29uZGl0aW9uIGlzIG5vbi1s" +
           "b2NhbGl6ZWQgYW5kIG1pZ2h0IGNvbnRhaW4gYW4gZXhwcmVzc2lvbiB0aGF0IGNhbiBiZSBwYXJzZWQg" +
           "YnkgY2VydGFpbiBjbGllbnRzLiBFeGFtcGxlcyBhcmU6IOKAnEFGVEVSIDQgSE9VUlPigJ0sIOKAnEFG" +
           "VEVSIDEwMDAgSVRFTVPigJ0sIOKAnE9QRVJBVE9S4oCdLiDigJxPUEVSQVRPUuKAnSBtZWFucywgdGhh" +
           "dCBhbiBvcGVyYXRvciByZXNldHMgdGhlIHN0YXRpc3RpY3Mgb24gYSBsb2NhbCBITUkuAC4ARJ8XAAAA" +
           "DP////8DA/////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public PropertyState<string> ResetCondition
        {
            get => m_resetCondition;

            set
            {
                if (!Object.ReferenceEquals(m_resetCondition, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_resetCondition = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_resetCondition != null)
            {
                children.Add(m_resetCondition);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_resetCondition, child))
            {
                m_resetCondition = null;
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
                case UAModel.IA.BrowseNames.ResetCondition:
                {
                    if (createOrReplace)
                    {
                        if (ResetCondition == null)
                        {
                            if (replacement == null)
                            {
                                ResetCondition = new PropertyState<string>(this);
                            }
                            else
                            {
                                ResetCondition = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = ResetCondition;
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
        private PropertyState<string> m_resetCondition;
        #endregion
    }
    #endif
    #endregion

    #region IRollingStatisticsTypeState Class
    #if (!OPCUA_EXCLUDE_IRollingStatisticsTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class IRollingStatisticsTypeState : IStatisticsTypeState
    {
        #region Constructors
        public IRollingStatisticsTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.IRollingStatisticsType, UAModel.IA.Namespaces.IA, namespaceUris);
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

            if (WindowDuration != null)
            {
                WindowDuration.Initialize(context, WindowDuration_InitializationString);
            }

            if (WindowNumberOfValues != null)
            {
                WindowNumberOfValues.Initialize(context, WindowNumberOfValues_InitializationString);
            }
        }

        #region Initialization String
        private const string WindowDuration_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABAA4AAABXaW5kb3dEdXJhdGlvbgEBoBcDAAAAAOcAAABU" +
           "aGUgZHVyYXRpb24gYWZ0ZXIgdGhlIHN0YXRpc3RpY2FsIGRhdGEgYXJlIHJvbGxlZCBvdmVyLiBPbmx5" +
           "IHRoZSBkYXRhIHRoYXQgd2VyZSBnYXRoZXJlZCBkdXJpbmcgdGhhdCBkdXJhdGlvbiBhcmUgY29uc2lk" +
           "ZXJlZCBmb3IgdGhlIHN0YXRpc3RpY2FsIGRhdGEsIGV2ZW4gaWYgdGhlIHRpbWUgaW50ZXJ2YWwgYmV0" +
           "d2VlbiB0aGUgU3RhcnRUaW1lIGFuZCB0aGUgY3VycmVudCB0aW1lIGlzIGxvbmdlci4ALgBEoBcAAAEA" +
           "IgH/////AwP/////AAAAAA==";

        private const string WindowNumberOfValues_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABABQAAABXaW5kb3dOdW1iZXJPZlZhbHVlcwEBoRcDAAAA" +
           "AMAAAABUaGUgbnVtYmVyIG9mIHZhbHVlcyBiZWZvcmUgdGhlIGRhdGEgZ2V0cyByb2xsZWQgb3Zlci4g" +
           "Rm9yIHRoZSBzdGF0aXN0aWNhbCBkYXRhLCBvbmx5IHRoZSBkYXRhIGZpdHRpbmcgaW50byB0aGUgbnVt" +
           "YmVyIG9mIHZhbHVlcyBpcyBjb25zaWRlcmVkLCBldmVuIGlmIG1vcmUgZGF0YSB3ZXJlIGdhdGhlcmVk" +
           "IHNpbmNlIFN0YXJ0VGltZS4ALgBEoRcAAAAH/////wMD/////wAAAAA=";

        private const string InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABAB4AAABJUm9sbGluZ1N0YXRpc3RpY3NUeXBlSW5zdGFu" +
           "Y2UBAfUDAQH1A/UDAAD/////AgAAADVgiQoCAAAAAQAOAAAAV2luZG93RHVyYXRpb24BAaAXAwAAAADn" +
           "AAAAVGhlIGR1cmF0aW9uIGFmdGVyIHRoZSBzdGF0aXN0aWNhbCBkYXRhIGFyZSByb2xsZWQgb3Zlci4g" +
           "T25seSB0aGUgZGF0YSB0aGF0IHdlcmUgZ2F0aGVyZWQgZHVyaW5nIHRoYXQgZHVyYXRpb24gYXJlIGNv" +
           "bnNpZGVyZWQgZm9yIHRoZSBzdGF0aXN0aWNhbCBkYXRhLCBldmVuIGlmIHRoZSB0aW1lIGludGVydmFs" +
           "IGJldHdlZW4gdGhlIFN0YXJ0VGltZSBhbmQgdGhlIGN1cnJlbnQgdGltZSBpcyBsb25nZXIuAC4ARKAX" +
           "AAABACIB/////wMD/////wAAAAA1YIkKAgAAAAEAFAAAAFdpbmRvd051bWJlck9mVmFsdWVzAQGhFwMA" +
           "AAAAwAAAAFRoZSBudW1iZXIgb2YgdmFsdWVzIGJlZm9yZSB0aGUgZGF0YSBnZXRzIHJvbGxlZCBvdmVy" +
           "LiBGb3IgdGhlIHN0YXRpc3RpY2FsIGRhdGEsIG9ubHkgdGhlIGRhdGEgZml0dGluZyBpbnRvIHRoZSBu" +
           "dW1iZXIgb2YgdmFsdWVzIGlzIGNvbnNpZGVyZWQsIGV2ZW4gaWYgbW9yZSBkYXRhIHdlcmUgZ2F0aGVy" +
           "ZWQgc2luY2UgU3RhcnRUaW1lLgAuAEShFwAAAAf/////AwP/////AAAAAA==";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public PropertyState<double> WindowDuration
        {
            get => m_windowDuration;

            set
            {
                if (!Object.ReferenceEquals(m_windowDuration, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_windowDuration = value;
            }
        }

        public PropertyState<uint> WindowNumberOfValues
        {
            get => m_windowNumberOfValues;

            set
            {
                if (!Object.ReferenceEquals(m_windowNumberOfValues, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_windowNumberOfValues = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_windowDuration != null)
            {
                children.Add(m_windowDuration);
            }

            if (m_windowNumberOfValues != null)
            {
                children.Add(m_windowNumberOfValues);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_windowDuration, child))
            {
                m_windowDuration = null;
                return;
            }

            if (Object.ReferenceEquals(m_windowNumberOfValues, child))
            {
                m_windowNumberOfValues = null;
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
                case UAModel.IA.BrowseNames.WindowDuration:
                {
                    if (createOrReplace)
                    {
                        if (WindowDuration == null)
                        {
                            if (replacement == null)
                            {
                                WindowDuration = new PropertyState<double>(this);
                            }
                            else
                            {
                                WindowDuration = (PropertyState<double>)replacement;
                            }
                        }
                    }

                    instance = WindowDuration;
                    break;
                }

                case UAModel.IA.BrowseNames.WindowNumberOfValues:
                {
                    if (createOrReplace)
                    {
                        if (WindowNumberOfValues == null)
                        {
                            if (replacement == null)
                            {
                                WindowNumberOfValues = new PropertyState<uint>(this);
                            }
                            else
                            {
                                WindowNumberOfValues = (PropertyState<uint>)replacement;
                            }
                        }
                    }

                    instance = WindowNumberOfValues;
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
        private PropertyState<double> m_windowDuration;
        private PropertyState<uint> m_windowNumberOfValues;
        #endregion
    }
    #endif
    #endregion

    #region CalibrationTargetTypeState Class
    #if (!OPCUA_EXCLUDE_CalibrationTargetTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class CalibrationTargetTypeState : BaseObjectState
    {
        #region Constructors
        public CalibrationTargetTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.CalibrationTargetType, UAModel.IA.Namespaces.IA, namespaceUris);
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

            if (CertificateUri != null)
            {
                CertificateUri.Initialize(context, CertificateUri_InitializationString);
            }

            if (LastValidationDate != null)
            {
                LastValidationDate.Initialize(context, LastValidationDate_InitializationString);
            }

            if (NextValidationDate != null)
            {
                NextValidationDate.Initialize(context, NextValidationDate_InitializationString);
            }

            if (OperationalConditions != null)
            {
                OperationalConditions.Initialize(context, OperationalConditions_InitializationString);
            }

            if (Quality != null)
            {
                Quality.Initialize(context, Quality_InitializationString);
            }
        }

        #region Initialization String
        private const string CertificateUri_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABAA4AAABDZXJ0aWZpY2F0ZVVyaQEBrxcDAAAAALIAAABD" +
           "b250YWlucyB0aGUgVXJpIG9mIGEgY2VydGlmaWNhdGUgb2YgdGhlIGNhbGlicmF0aW9uIHRhcmdldCwg" +
           "aW4gY2FzZSB0aGUgY2FsaWJyYXRpb24gdGFyZ2V0IGlzIGNlcnRpZmllZCBhbmQgdGhlIGluZm9ybWF0" +
           "aW9uIGF2YWlsYWJsZS4gT3RoZXJ3aXNlLCB0aGUgUHJvcGVydHkgc2hvdWxkIGJlIG9taXR0ZWQuAC4A" +
           "RK8XAAAADP////8DA/////8AAAAA";

        private const string LastValidationDate_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABABIAAABMYXN0VmFsaWRhdGlvbkRhdGUBAawXAwAAAADA" +
           "AAAAUHJvdmlkZXMgdGhlIGRhdGUsIHRoZSBjYWxpYnJhdGlvbiB0YXJnZXQgd2FzIHZhbGlkYXRlZCB0" +
           "aGUgbGFzdCB0aW1lLiBJZiB0aGVyZSBpcyBubyBzcGVjaWZpYyB2YWxpZGF0aW9uIGRhdGUga25vd24s" +
           "IHRoZSBkYXRlIHdoZW4gdGhlIGNhbGlicmF0aW9uIHRhcmdldCB3YXMgYm91Z2h0IG9yIGNyZWF0ZWQg" +
           "c2hvdWxkIGJlIHVzZWQuAC4ARKwXAAABACYB/////wMD/////wAAAAA=";

        private const string NextValidationDate_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABABIAAABOZXh0VmFsaWRhdGlvbkRhdGUBAa0XAwAAAADy" +
           "AAAAUHJvdmlkZXMgdGhlIGRhdGUsIHdoZW4gdGhlIGNhbGlicmF0aW9uIHRhcmdldCBzaG91bGQgYmUg" +
           "dmFsaWRhdGVkIHRoZSBuZXh0IHRpbWUuIElmIHRoaXMgZGF0ZSBpcyBub3Qga25vd24sIHRoZSBQcm9w" +
           "ZXJ0eSBzaG91bGQgYmUgb21pdHRlZC4gTm90ZTogUG90ZW50aWFsbHkgdGhlIE5leHRWYWxpZGF0aW9u" +
           "RGF0ZSBpcyBpbiB0aGUgcGFzdCwgd2hlbiB0aGUgbmV4dCB2YWxpZGF0aW9uIGRpZCBub3QgdGFrZSBw" +
           "bGFjZS4ALgBErRcAAAEAJgH/////AwP/////AAAAAA==";

        private const string OperationalConditions_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////JGCACgEAAAABABUAAABPcGVyYXRpb25hbENvbmRpdGlvbnMBAZQTAwAA" +
           "AADPAQAAQSBmb2xkZXIgY29udGFpbmluZyBpbmZvcm1hdGlvbiBhYm91dCBvcGVyYXRpb25hbCBjb25k" +
           "aXRpb25zIG9mIHRoZSBjYWxpYnJhdGlvbiB0YXJnZXQuIEZvciBleGFtcGxlLCBpdCBtaWdodCBwcm92" +
           "aWRlIGluIHdoYXQgcmFuZ2VzIG9mIGh1bWlkaXR5IHRoZSBjYWxpYnJhdGlvbiB0YXJnZXQgY2FuIGJl" +
           "IG9wZXJhdGVkLiBJdCBtaWdodCBhbHNvIHByb3ZpZGUgY29ycmVjdGlvbiBpbmZvcm1hdGlvbiwgZm9y" +
           "IGV4YW1wbGUsIGRlcGVuZGluZyBvbiB0aGUgdGVtcGVyYXR1cmUgdGhlIGNhbGlicmF0aW9uIHZhbHVl" +
           "cyBuZWVkIHRvIGJlIGNvcnJlY3RlZCAoaW4gY2FzZSBvZiBhIGxlbmd0aCwgdGhlIGxlbmd0aCBtaWdo" +
           "dCBpbmNyZWFzZSB3aXRoIGhpZ2ggdGVtcGVyYXR1cmVzKS4gSWYgbm8gb3BlcmF0aW9uYWwgY29uZGl0" +
           "aW9ucyBhcmUgcHJvdmlkZWQsIHRoaXMgZm9sZGVyIHNob3VsZCBiZSBvbWl0dGVkLgAvAD2UEwAA////" +
           "/wAAAAA=";

        private const string Quality_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABAAcAAABRdWFsaXR5AQGuFwMAAAAAzgAAAFByb3ZpZGVz" +
           "IHRoZSBxdWFsaXR5IG9mIHRoZSBjYWxpYnJhdGlvbiB0YXJnZXQgaW4gcGVyY2VudGFnZSwgdGhpcyBp" +
           "cywgdGhlIHZhbHVlIHNoYWxsIGJlIGJldHdlZW4gMCBhbmQgMTAwLiAxMDAgbWVhbnMgdGhlIGhpZ2hl" +
           "c3QgcXVhbGl0eSwgMCB0aGUgbG93ZXN0LiBUaGUgc2VtYW50aWMgb2YgdGhlIHF1YWxpdHkgaXMgYXBw" +
           "bGljYXRpb24tc3BlY2lmaWMuAC4ARK4XAAAAA/////8DA/////8AAAAA";

        private const string InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABAB0AAABDYWxpYnJhdGlvblRhcmdldFR5cGVJbnN0YW5j" +
           "ZQEB+wMBAfsD+wMAAP////8IAAAAJGCACgEAAAABABkAAABDYWxpYnJhdGlvblRhcmdldENhdGVnb3J5" +
           "AQGTEwMAAAAAMwAAAERlZmluZXMgd2hhdCBjYXRlZ29yeSB0aGUgY2FsaWJyYXRpb24gdGFyZ2V0IGlz" +
           "IG9mLgAvAQH2A5MTAAD/////AAAAACRggAoBAAAAAQAZAAAAQ2FsaWJyYXRpb25UYXJnZXRGZWF0dXJl" +
           "cwEBlRMDAAAAAIgAAABBIGZvbGRlciBjb250YWluaW5nIGluZm9ybWF0aW9uIGFib3V0IHRoZSBmZWF0" +
           "dXJlcyBvZiBhIGNhbGlicmF0aW9uIHRhcmdldCwgdGhhdCBpcywgd2hhdCBjYW4gYmUgY2FsaWJyYXRl" +
           "ZCB3aXRoIHRoZSBjYWxpYnJhdGlvbiB0YXJnZXQuAC8APZUTAAD/////AgAAADVgyQoCAAAAHAAAAENh" +
           "bGlicmF0aW9uVmFsdWVfUGxhY2Vob2xkZXIBABIAAAA8Q2FsaWJyYXRpb25WYWx1ZT4BAbAXAwAAAACH" +
           "AAAAQSBjYWxpYnJhdGlvbiB2YWx1ZSBpbmRpY2F0ZXMgdGhlIHZhbHVlIHRoZSBjYWxpYnJhdGlvbiB0" +
           "YXJnZXQgcHJvdmlkZXMgZm9yIGNhbGlicmF0aW9uIGFuZCBpbmNsdWRlcyBpdHMgcXVhbnRpdHkgYW5k" +
           "IGVuZ2luZWVyaW5nIHVuaXQuAC8BAdIHsBcAAAAa/////wMD/////wEAAAAVYIkKAgAAAAAAEAAAAEVu" +
           "Z2luZWVyaW5nVW5pdHMBAbEXAC4ARLEXAAABAHcD/////wMD/////wAAAAA1YMkKAgAAABkAAABDYXBh" +
           "Y2l0eVJhbmdlX1BsYWNlaG9sZGVyAQAPAAAAPENhcGFjaXR5UmFuZ2U+AQGyFwMAAAAA1AAAAEEgY2Fw" +
           "YWNpdHkgcmFuZ2UgaW5kaWNhdGVzIGEgcmFuZ2UgKGxvdyBhbmQgaGlnaCB2YWx1ZSkgYXMgd2VsbCBh" +
           "cyBhIHJlc29sdXRpb24sIGFuZCB0aHVzIGRlZmluZXMgYSBudW1iZXIgb2YgdmFsdWVzIHRoZSBjYWxp" +
           "YnJhdGlvbiB0YXJnZXQgcHJvdmlkZXMgZm9yIGNhbGlicmF0aW9uIGFuZCBpbmNsdWRlcyB0aGUgcXVh" +
           "bnRpdHkgYW5kIGVuZ2luZWVyaW5nIHVuaXQuAC8BAdMHshcAAAEAdAP/////AwP/////AgAAABVgiQoC" +
           "AAAAAAAQAAAARW5naW5lZXJpbmdVbml0cwEBsxcALgBEsxcAAAEAdwP/////AwP/////AAAAABVgiQoC" +
           "AAAAAQAKAAAAUmVzb2x1dGlvbgEBtBcALgBEtBcAAAAL/////wMD/////wAAAAA1YIkKAgAAAAEADgAA" +
           "AENlcnRpZmljYXRlVXJpAQGvFwMAAAAAsgAAAENvbnRhaW5zIHRoZSBVcmkgb2YgYSBjZXJ0aWZpY2F0" +
           "ZSBvZiB0aGUgY2FsaWJyYXRpb24gdGFyZ2V0LCBpbiBjYXNlIHRoZSBjYWxpYnJhdGlvbiB0YXJnZXQg" +
           "aXMgY2VydGlmaWVkIGFuZCB0aGUgaW5mb3JtYXRpb24gYXZhaWxhYmxlLiBPdGhlcndpc2UsIHRoZSBQ" +
           "cm9wZXJ0eSBzaG91bGQgYmUgb21pdHRlZC4ALgBErxcAAAAM/////wMD/////wAAAAAkYIAKAQAAAAIA" +
           "DgAAAElkZW50aWZpY2F0aW9uAQGSEwMAAAAAJAAAAFByb3ZpZGVzIGlkZW50aWZpY2F0aW9uIGluZm9y" +
           "bWF0aW9uLgAvAQLtA5ITAAACAAAAAQDDRAABAsg6AQDDRAABArs6DgAAABVgiQoCAAAAAgAHAAAAQXNz" +
           "ZXRJZAEBwBcALgBEwBcAAAAM/////wMD/////wAAAAAVYIkKAgAAAAIADQAAAENvbXBvbmVudE5hbWUB" +
           "AcEXAC4ARMEXAAAAFf////8DA/////8AAAAAFWCJCgIAAAACAAsAAABEZXZpY2VDbGFzcwEBvBcALgBE" +
           "vBcAAAAM/////wMD/////wAAAAAVYIkKAgAAAAIADAAAAERldmljZU1hbnVhbAEBwhcALgBEwhcAAAAM" +
           "/////wMD/////wAAAAAVYIkKAgAAAAIADgAAAERldmljZVJldmlzaW9uAQG7FwAuAES7FwAAAAz/////" +
           "AwP/////AAAAABVgiQoCAAAAAgAQAAAASGFyZHdhcmVSZXZpc2lvbgEBuRcALgBEuRcAAAAM/////wMD" +
           "/////wAAAAAVYIkKAgAAAAIADAAAAE1hbnVmYWN0dXJlcgEBtRcALgBEtRcAAAAV/////wMD/////wAA" +
           "AAAVYIkKAgAAAAIADwAAAE1hbnVmYWN0dXJlclVyaQEBthcALgBEthcAAAAM/////wMD/////wAAAAAV" +
           "YIkKAgAAAAIABQAAAE1vZGVsAQG3FwAuAES3FwAAABX/////AwP/////AAAAABVgiQoCAAAAAgALAAAA" +
           "UHJvZHVjdENvZGUBAbgXAC4ARLgXAAAADP////8DA/////8AAAAAFWCJCgIAAAACABIAAABQcm9kdWN0" +
           "SW5zdGFuY2VVcmkBAb4XAC4ARL4XAAAADP////8DA/////8AAAAAFWCJCgIAAAACAA8AAABSZXZpc2lv" +
           "bkNvdW50ZXIBAb8XAC4ARL8XAAAABv////8DA/////8AAAAAFWCJCgIAAAACAAwAAABTZXJpYWxOdW1i" +
           "ZXIBAb0XAC4ARL0XAAAADP////8DA/////8AAAAAFWCJCgIAAAACABAAAABTb2Z0d2FyZVJldmlzaW9u" +
           "AQG6FwAuAES6FwAAAAz/////AwP/////AAAAADVgiQoCAAAAAQASAAAATGFzdFZhbGlkYXRpb25EYXRl" +
           "AQGsFwMAAAAAwAAAAFByb3ZpZGVzIHRoZSBkYXRlLCB0aGUgY2FsaWJyYXRpb24gdGFyZ2V0IHdhcyB2" +
           "YWxpZGF0ZWQgdGhlIGxhc3QgdGltZS4gSWYgdGhlcmUgaXMgbm8gc3BlY2lmaWMgdmFsaWRhdGlvbiBk" +
           "YXRlIGtub3duLCB0aGUgZGF0ZSB3aGVuIHRoZSBjYWxpYnJhdGlvbiB0YXJnZXQgd2FzIGJvdWdodCBv" +
           "ciBjcmVhdGVkIHNob3VsZCBiZSB1c2VkLgAuAESsFwAAAQAmAf////8DA/////8AAAAANWCJCgIAAAAB" +
           "ABIAAABOZXh0VmFsaWRhdGlvbkRhdGUBAa0XAwAAAADyAAAAUHJvdmlkZXMgdGhlIGRhdGUsIHdoZW4g" +
           "dGhlIGNhbGlicmF0aW9uIHRhcmdldCBzaG91bGQgYmUgdmFsaWRhdGVkIHRoZSBuZXh0IHRpbWUuIElm" +
           "IHRoaXMgZGF0ZSBpcyBub3Qga25vd24sIHRoZSBQcm9wZXJ0eSBzaG91bGQgYmUgb21pdHRlZC4gTm90" +
           "ZTogUG90ZW50aWFsbHkgdGhlIE5leHRWYWxpZGF0aW9uRGF0ZSBpcyBpbiB0aGUgcGFzdCwgd2hlbiB0" +
           "aGUgbmV4dCB2YWxpZGF0aW9uIGRpZCBub3QgdGFrZSBwbGFjZS4ALgBErRcAAAEAJgH/////AwP/////" +
           "AAAAACRggAoBAAAAAQAVAAAAT3BlcmF0aW9uYWxDb25kaXRpb25zAQGUEwMAAAAAzwEAAEEgZm9sZGVy" +
           "IGNvbnRhaW5pbmcgaW5mb3JtYXRpb24gYWJvdXQgb3BlcmF0aW9uYWwgY29uZGl0aW9ucyBvZiB0aGUg" +
           "Y2FsaWJyYXRpb24gdGFyZ2V0LiBGb3IgZXhhbXBsZSwgaXQgbWlnaHQgcHJvdmlkZSBpbiB3aGF0IHJh" +
           "bmdlcyBvZiBodW1pZGl0eSB0aGUgY2FsaWJyYXRpb24gdGFyZ2V0IGNhbiBiZSBvcGVyYXRlZC4gSXQg" +
           "bWlnaHQgYWxzbyBwcm92aWRlIGNvcnJlY3Rpb24gaW5mb3JtYXRpb24sIGZvciBleGFtcGxlLCBkZXBl" +
           "bmRpbmcgb24gdGhlIHRlbXBlcmF0dXJlIHRoZSBjYWxpYnJhdGlvbiB2YWx1ZXMgbmVlZCB0byBiZSBj" +
           "b3JyZWN0ZWQgKGluIGNhc2Ugb2YgYSBsZW5ndGgsIHRoZSBsZW5ndGggbWlnaHQgaW5jcmVhc2Ugd2l0" +
           "aCBoaWdoIHRlbXBlcmF0dXJlcykuIElmIG5vIG9wZXJhdGlvbmFsIGNvbmRpdGlvbnMgYXJlIHByb3Zp" +
           "ZGVkLCB0aGlzIGZvbGRlciBzaG91bGQgYmUgb21pdHRlZC4ALwA9lBMAAP////8AAAAANWCJCgIAAAAB" +
           "AAcAAABRdWFsaXR5AQGuFwMAAAAAzgAAAFByb3ZpZGVzIHRoZSBxdWFsaXR5IG9mIHRoZSBjYWxpYnJh" +
           "dGlvbiB0YXJnZXQgaW4gcGVyY2VudGFnZSwgdGhpcyBpcywgdGhlIHZhbHVlIHNoYWxsIGJlIGJldHdl" +
           "ZW4gMCBhbmQgMTAwLiAxMDAgbWVhbnMgdGhlIGhpZ2hlc3QgcXVhbGl0eSwgMCB0aGUgbG93ZXN0LiBU" +
           "aGUgc2VtYW50aWMgb2YgdGhlIHF1YWxpdHkgaXMgYXBwbGljYXRpb24tc3BlY2lmaWMuAC4ARK4XAAAA" +
           "A/////8DA/////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public BaseCalibrationTargetCategoryTypeState CalibrationTargetCategory
        {
            get => m_calibrationTargetCategory;

            set
            {
                if (!Object.ReferenceEquals(m_calibrationTargetCategory, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_calibrationTargetCategory = value;
            }
        }

        public FolderState CalibrationTargetFeatures
        {
            get => m_calibrationTargetFeatures;

            set
            {
                if (!Object.ReferenceEquals(m_calibrationTargetFeatures, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_calibrationTargetFeatures = value;
            }
        }

        public PropertyState<string> CertificateUri
        {
            get => m_certificateUri;

            set
            {
                if (!Object.ReferenceEquals(m_certificateUri, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_certificateUri = value;
            }
        }

        public FunctionalGroupTypeState Identification
        {
            get => m_identification;

            set
            {
                if (!Object.ReferenceEquals(m_identification, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_identification = value;
            }
        }

        public PropertyState<DateTime> LastValidationDate
        {
            get => m_lastValidationDate;

            set
            {
                if (!Object.ReferenceEquals(m_lastValidationDate, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_lastValidationDate = value;
            }
        }

        public PropertyState<DateTime> NextValidationDate
        {
            get => m_nextValidationDate;

            set
            {
                if (!Object.ReferenceEquals(m_nextValidationDate, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_nextValidationDate = value;
            }
        }

        public FolderState OperationalConditions
        {
            get => m_operationalConditions;

            set
            {
                if (!Object.ReferenceEquals(m_operationalConditions, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_operationalConditions = value;
            }
        }

        public PropertyState<byte> Quality
        {
            get => m_quality;

            set
            {
                if (!Object.ReferenceEquals(m_quality, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_quality = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_calibrationTargetCategory != null)
            {
                children.Add(m_calibrationTargetCategory);
            }

            if (m_calibrationTargetFeatures != null)
            {
                children.Add(m_calibrationTargetFeatures);
            }

            if (m_certificateUri != null)
            {
                children.Add(m_certificateUri);
            }

            if (m_identification != null)
            {
                children.Add(m_identification);
            }

            if (m_lastValidationDate != null)
            {
                children.Add(m_lastValidationDate);
            }

            if (m_nextValidationDate != null)
            {
                children.Add(m_nextValidationDate);
            }

            if (m_operationalConditions != null)
            {
                children.Add(m_operationalConditions);
            }

            if (m_quality != null)
            {
                children.Add(m_quality);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_calibrationTargetCategory, child))
            {
                m_calibrationTargetCategory = null;
                return;
            }

            if (Object.ReferenceEquals(m_calibrationTargetFeatures, child))
            {
                m_calibrationTargetFeatures = null;
                return;
            }

            if (Object.ReferenceEquals(m_certificateUri, child))
            {
                m_certificateUri = null;
                return;
            }

            if (Object.ReferenceEquals(m_identification, child))
            {
                m_identification = null;
                return;
            }

            if (Object.ReferenceEquals(m_lastValidationDate, child))
            {
                m_lastValidationDate = null;
                return;
            }

            if (Object.ReferenceEquals(m_nextValidationDate, child))
            {
                m_nextValidationDate = null;
                return;
            }

            if (Object.ReferenceEquals(m_operationalConditions, child))
            {
                m_operationalConditions = null;
                return;
            }

            if (Object.ReferenceEquals(m_quality, child))
            {
                m_quality = null;
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
                case UAModel.IA.BrowseNames.CalibrationTargetCategory:
                {
                    if (createOrReplace)
                    {
                        if (CalibrationTargetCategory == null)
                        {
                            if (replacement == null)
                            {
                                CalibrationTargetCategory = new BaseCalibrationTargetCategoryTypeState(this);
                            }
                            else
                            {
                                CalibrationTargetCategory = (BaseCalibrationTargetCategoryTypeState)replacement;
                            }
                        }
                    }

                    instance = CalibrationTargetCategory;
                    break;
                }

                case UAModel.IA.BrowseNames.CalibrationTargetFeatures:
                {
                    if (createOrReplace)
                    {
                        if (CalibrationTargetFeatures == null)
                        {
                            if (replacement == null)
                            {
                                CalibrationTargetFeatures = new FolderState(this);
                            }
                            else
                            {
                                CalibrationTargetFeatures = (FolderState)replacement;
                            }
                        }
                    }

                    instance = CalibrationTargetFeatures;
                    break;
                }

                case UAModel.IA.BrowseNames.CertificateUri:
                {
                    if (createOrReplace)
                    {
                        if (CertificateUri == null)
                        {
                            if (replacement == null)
                            {
                                CertificateUri = new PropertyState<string>(this);
                            }
                            else
                            {
                                CertificateUri = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = CertificateUri;
                    break;
                }

                case UAModel.DI.BrowseNames.Identification:
                {
                    if (createOrReplace)
                    {
                        if (Identification == null)
                        {
                            if (replacement == null)
                            {
                                Identification = new FunctionalGroupTypeState(this);
                            }
                            else
                            {
                                Identification = (FunctionalGroupTypeState)replacement;
                            }
                        }
                    }

                    instance = Identification;
                    break;
                }

                case UAModel.IA.BrowseNames.LastValidationDate:
                {
                    if (createOrReplace)
                    {
                        if (LastValidationDate == null)
                        {
                            if (replacement == null)
                            {
                                LastValidationDate = new PropertyState<DateTime>(this);
                            }
                            else
                            {
                                LastValidationDate = (PropertyState<DateTime>)replacement;
                            }
                        }
                    }

                    instance = LastValidationDate;
                    break;
                }

                case UAModel.IA.BrowseNames.NextValidationDate:
                {
                    if (createOrReplace)
                    {
                        if (NextValidationDate == null)
                        {
                            if (replacement == null)
                            {
                                NextValidationDate = new PropertyState<DateTime>(this);
                            }
                            else
                            {
                                NextValidationDate = (PropertyState<DateTime>)replacement;
                            }
                        }
                    }

                    instance = NextValidationDate;
                    break;
                }

                case UAModel.IA.BrowseNames.OperationalConditions:
                {
                    if (createOrReplace)
                    {
                        if (OperationalConditions == null)
                        {
                            if (replacement == null)
                            {
                                OperationalConditions = new FolderState(this);
                            }
                            else
                            {
                                OperationalConditions = (FolderState)replacement;
                            }
                        }
                    }

                    instance = OperationalConditions;
                    break;
                }

                case UAModel.IA.BrowseNames.Quality:
                {
                    if (createOrReplace)
                    {
                        if (Quality == null)
                        {
                            if (replacement == null)
                            {
                                Quality = new PropertyState<byte>(this);
                            }
                            else
                            {
                                Quality = (PropertyState<byte>)replacement;
                            }
                        }
                    }

                    instance = Quality;
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
        private BaseCalibrationTargetCategoryTypeState m_calibrationTargetCategory;
        private FolderState m_calibrationTargetFeatures;
        private PropertyState<string> m_certificateUri;
        private FunctionalGroupTypeState m_identification;
        private PropertyState<DateTime> m_lastValidationDate;
        private PropertyState<DateTime> m_nextValidationDate;
        private FolderState m_operationalConditions;
        private PropertyState<byte> m_quality;
        #endregion
    }
    #endif
    #endregion

    #region ControlChannelTypeState Class
    #if (!OPCUA_EXCLUDE_ControlChannelTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class ControlChannelTypeState : BaseObjectState
    {
        #region Constructors
        public ControlChannelTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.ControlChannelType, UAModel.IA.Namespaces.IA, namespaceUris);
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

            if (Intensity != null)
            {
                Intensity.Initialize(context, Intensity_InitializationString);
            }
        }

        #region Initialization String
        private const string Intensity_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABAAkAAABJbnRlbnNpdHkBAYoXAwAAAAAtAQAAU2hvd3Mg" +
           "dGhlIGNoYW5uZWzigJlzIGludGVuc2l0eSwgdGh1cyBpdHMgYnJpZ2h0bmVzcy4gVGhlIG1hbmRhdG9y" +
           "eSBFVVJhbmdlIFByb3BlcnR5IG9mIHRoZSBWYXJpYWJsZSBpbmRpY2F0ZXMgdGhlIGxvd2VzdCBhbmQg" +
           "aGlnaGVzdCB2YWx1ZSBhbmQgdGhlcmVieSBhbGxvd3MgdG8gY2FsY3VsYXRlIHRoZSBwZXJjZW50YWdl" +
           "IHJlcHJlc2VudGVkIGJ5IHRoZSB2YWx1ZS4gVGhlIGxvd2VzdCB2YWx1ZSBpcyBpbnRlcnByZXRlZCBh" +
           "cyAwIHBlcmNlbnQsIHRoZSBoaWdoZXN0IGlzIGludGVycHJldGVkIGFzIDEwMCBwZXJjZW50LgAvAQBA" +
           "CYoXAAAACv////8DA/////8BAAAAFWCJCgIAAAAAAAcAAABFVVJhbmdlAQGLFwAuAESLFwAAAQB0A///" +
           "//8BAf////8AAAAA";

        private const string InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABABoAAABDb250cm9sQ2hhbm5lbFR5cGVJbnN0YW5jZQEB" +
           "8AMBAfAD8AMAAP////8EAAAANWCJCgIAAAABAAwAAABDaGFubmVsQ29sb3IBAYgXAwAAAABjAAAASW5k" +
           "aWNhdGVzIGluIHdoYXQgbW9kZSAoY29udGludW91c2x5IG9uLCBibGlua2luZywgZmxhc2hpbmcpIHRo" +
           "ZSBjaGFubmVsIG9wZXJhdGVzIHdoZW4gc3dpdGNoZWQgb24uAC8AP4gXAAABAbwL/////wMD/////wAA" +
           "AAA1YIkKAgAAAAEACQAAAEludGVuc2l0eQEBihcDAAAAAC0BAABTaG93cyB0aGUgY2hhbm5lbOKAmXMg" +
           "aW50ZW5zaXR5LCB0aHVzIGl0cyBicmlnaHRuZXNzLiBUaGUgbWFuZGF0b3J5IEVVUmFuZ2UgUHJvcGVy" +
           "dHkgb2YgdGhlIFZhcmlhYmxlIGluZGljYXRlcyB0aGUgbG93ZXN0IGFuZCBoaWdoZXN0IHZhbHVlIGFu" +
           "ZCB0aGVyZWJ5IGFsbG93cyB0byBjYWxjdWxhdGUgdGhlIHBlcmNlbnRhZ2UgcmVwcmVzZW50ZWQgYnkg" +
           "dGhlIHZhbHVlLiBUaGUgbG93ZXN0IHZhbHVlIGlzIGludGVycHJldGVkIGFzIDAgcGVyY2VudCwgdGhl" +
           "IGhpZ2hlc3QgaXMgaW50ZXJwcmV0ZWQgYXMgMTAwIHBlcmNlbnQuAC8BAEAJihcAAAAK/////wMD////" +
           "/wEAAAAVYIkKAgAAAAAABwAAAEVVUmFuZ2UBAYsXAC4ARIsXAAABAHQD/////wEB/////wAAAAA1YIkK" +
           "AgAAAAEACgAAAFNpZ25hbE1vZGUBAYkXAwAAAABKAAAAQ29udGFpbnMgYSBsaXN0IG9mIGF1ZGlvIHNp" +
           "Z25hbHMgdXNlZCBieSB0aGlzIGFjb3VzdGljIHN0YWNrbGlnaHQgZWxlbWVudC4ALwA/iRcAAAEBvQv/" +
           "////AwP/////AAAAADVgiQoCAAAAAQAIAAAAU2lnbmFsT24BAYcXAwAAAAAnAAAASW5kaWNhdGVzIGlm" +
           "IHRoZSBjb2xvdXIgaXMgc3dpdGNoZWQgb24uAC4ARIcXAAAAAf////8DA/////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public BaseDataVariableState<SignalColor> ChannelColor
        {
            get => m_channelColor;

            set
            {
                if (!Object.ReferenceEquals(m_channelColor, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_channelColor = value;
            }
        }

        public AnalogItemState<float> Intensity
        {
            get => m_intensity;

            set
            {
                if (!Object.ReferenceEquals(m_intensity, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_intensity = value;
            }
        }

        public BaseDataVariableState<SignalModeLight> SignalMode
        {
            get => m_signalMode;

            set
            {
                if (!Object.ReferenceEquals(m_signalMode, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_signalMode = value;
            }
        }

        public PropertyState<bool> SignalOn
        {
            get => m_signalOn;

            set
            {
                if (!Object.ReferenceEquals(m_signalOn, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_signalOn = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_channelColor != null)
            {
                children.Add(m_channelColor);
            }

            if (m_intensity != null)
            {
                children.Add(m_intensity);
            }

            if (m_signalMode != null)
            {
                children.Add(m_signalMode);
            }

            if (m_signalOn != null)
            {
                children.Add(m_signalOn);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_channelColor, child))
            {
                m_channelColor = null;
                return;
            }

            if (Object.ReferenceEquals(m_intensity, child))
            {
                m_intensity = null;
                return;
            }

            if (Object.ReferenceEquals(m_signalMode, child))
            {
                m_signalMode = null;
                return;
            }

            if (Object.ReferenceEquals(m_signalOn, child))
            {
                m_signalOn = null;
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
                case UAModel.IA.BrowseNames.ChannelColor:
                {
                    if (createOrReplace)
                    {
                        if (ChannelColor == null)
                        {
                            if (replacement == null)
                            {
                                ChannelColor = new BaseDataVariableState<SignalColor>(this);
                            }
                            else
                            {
                                ChannelColor = (BaseDataVariableState<SignalColor>)replacement;
                            }
                        }
                    }

                    instance = ChannelColor;
                    break;
                }

                case UAModel.IA.BrowseNames.Intensity:
                {
                    if (createOrReplace)
                    {
                        if (Intensity == null)
                        {
                            if (replacement == null)
                            {
                                Intensity = new AnalogItemState<float>(this);
                            }
                            else
                            {
                                Intensity = (AnalogItemState<float>)replacement;
                            }
                        }
                    }

                    instance = Intensity;
                    break;
                }

                case UAModel.IA.BrowseNames.SignalMode:
                {
                    if (createOrReplace)
                    {
                        if (SignalMode == null)
                        {
                            if (replacement == null)
                            {
                                SignalMode = new BaseDataVariableState<SignalModeLight>(this);
                            }
                            else
                            {
                                SignalMode = (BaseDataVariableState<SignalModeLight>)replacement;
                            }
                        }
                    }

                    instance = SignalMode;
                    break;
                }

                case UAModel.IA.BrowseNames.SignalOn:
                {
                    if (createOrReplace)
                    {
                        if (SignalOn == null)
                        {
                            if (replacement == null)
                            {
                                SignalOn = new PropertyState<bool>(this);
                            }
                            else
                            {
                                SignalOn = (PropertyState<bool>)replacement;
                            }
                        }
                    }

                    instance = SignalOn;
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
        private BaseDataVariableState<SignalColor> m_channelColor;
        private AnalogItemState<float> m_intensity;
        private BaseDataVariableState<SignalModeLight> m_signalMode;
        private PropertyState<bool> m_signalOn;
        #endregion
    }
    #endif
    #endregion

    #region BasicStacklightTypeState Class
    #if (!OPCUA_EXCLUDE_BasicStacklightTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class BasicStacklightTypeState : OrderedListState
    {
        #region Constructors
        public BasicStacklightTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.BasicStacklightType, UAModel.IA.Namespaces.IA, namespaceUris);
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

            if (StackLevel != null)
            {
                StackLevel.Initialize(context, StackLevel_InitializationString);
            }

            if (StackRunning != null)
            {
                StackRunning.Initialize(context, StackRunning_InitializationString);
            }
        }

        #region Initialization String
        private const string StackLevel_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////JGCACgEAAAABAAoAAABTdGFja0xldmVsAQGJEwMAAAAA6QAAAFZhbGlk" +
           "IGlmIHRoZSBzdGFja2xpZ2h0IGlzIHVzZWQgaW4g4oCcTGV2ZWxtZXRlcuKAnSBTdGFja2xpZ2h0TW9k" +
           "ZS4gSWYgc28sIHRoZSB3aG9sZSBzdGFjayBpcyBjb250cm9sbGVkIGJ5IGEgc2luZ2xlIHBlcmNlbnR1" +
           "YWwgdmFsdWUuIEluIHRoaXMgY2FzZSwgdGhlIFNpZ25hbE9uIHBhcmFtZXRlciBvZiBhbnkgc3RhY2sg" +
           "ZWxlbWVudCBvZiBTdGFja0VsZW1lbnRMaWdodFR5cGUgaGFzIG5vIG1lYW5pbmcuAC8BAesDiRMAAP//" +
           "//8CAAAANWCJCgIAAAABAAsAAABEaXNwbGF5TW9kZQEBkhcDAAAAAEwAAABJbmRpY2F0ZXMgaW4gd2hh" +
           "dCB3YXkgdGhlIHBlcmNlbnR1YWwgdmFsdWUgaXMgZGlzcGxheWVkIHdpdGggdGhlIHN0YWNrbGlnaHQu" +
           "AC8AP5IXAAABAbsL/////wMD/////wAAAAA1YIkKAgAAAAEADAAAAExldmVsUGVyY2VudAEBkxcDAAAA" +
           "ADIBAABTaG93cyB0aGUgcGVyY2VudHVhbCB2YWx1ZSB0aGUgc3RhY2tsaWdodCBpcyByZXByZXNlbnRp" +
           "bmcuIFRoZSBtYW5kYXRvcnkgRVVSYW5nZSBQcm9wZXJ0eSBvZiB0aGUgVmFyaWFibGUgaW5kaWNhdGVz" +
           "IHRoZSBsb3dlc3QgYW5kIGhpZ2hlc3QgdmFsdWUgYW5kIHRoZXJlYnkgYWxsb3dzIHRvIGNhbGN1bGF0" +
           "ZSB0aGUgcGVyY2VudGFnZSByZXByZXNlbnRlZCBieSB0aGUgdmFsdWUuIFRoZSBsb3dlc3QgdmFsdWUg" +
           "aXMgaW50ZXJwcmV0ZWQgYXMgMCBwZXJjZW50LCB0aGUgaGlnaGVzdCBpcyBpbnRlcnByZXRlZCBhcyAx" +
           "MDAgcGVyY2VudC4ALwEAQAmTFwAAAAr/////AwP/////AQAAABVgiQoCAAAAAAAHAAAARVVSYW5nZQEB" +
           "lBcALgBElBcAAAEAdAP/////AQH/////AAAAAA==";

        private const string StackRunning_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////JGCACgEAAAABAAwAAABTdGFja1J1bm5pbmcBAY0TAwAAAABGAAAAVmFs" +
           "aWQgaWYgdGhlIHN0YWNrbGlnaHQgaXMgdXNlZCBpbiDigJxSdW5uaW5nX0xpZ2h04oCdIFN0YWNrbGln" +
           "aHRNb2RlLgAvAQHsA40TAAD/////AAAAAA==";

        private const string InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABABsAAABCYXNpY1N0YWNrbGlnaHRUeXBlSW5zdGFuY2UB" +
           "AeoDAQHqA+oDAAD/////BAAAACRgwAoBAAAAGQAAAE9yZGVyZWRPYmplY3RfUGxhY2Vob2xkZXIAAA8A" +
           "AAA8T3JkZXJlZE9iamVjdD4BAY4TAwAAAAC5AAAAUmVwcmVzZW50IHRoZSBzdGFjayBlbGVtZW50cyAo" +
           "bGFtcHMgYW5kIGFjb3VzdGljIGVsZW1lbnRzKSB0aGUgc3RhY2tsaWdodCBpcyBjb21wb3NlZCBvZi4g" +
           "VGhlIEhhc09yZGVyZWRDb21wb25lbnQgUmVmZXJlbmNlIHNoYWxsIHJlcHJlc2VudCB0aGUgb3JkZXJp" +
           "bmcgZnJvbSB0aGUgYmFzZSBvZiB0aGUgc3RhY2tsaWdodC4AMQEB7QOOEwAAAQAAAAEAw0QAAQDZWwEA" +
           "AAA1YIkKAgAAAAAADAAAAE51bWJlckluTGlzdAEBlRcDAAAAAF0AAABFbnVtZXJhdGUgdGhlIHN0YWNr" +
           "bGlnaHQgZWxlbWVudHMgY291bnRpbmcgdXB3YXJkcyBiZWdpbm5pbmcgZnJvbSB0aGUgYmFzZSBvZiB0" +
           "aGUgc3RhY2tsaWdodC4ALgBElRcAAAAc/////wEB/////wAAAAAkYIAKAQAAAAEACgAAAFN0YWNrTGV2" +
           "ZWwBAYkTAwAAAADpAAAAVmFsaWQgaWYgdGhlIHN0YWNrbGlnaHQgaXMgdXNlZCBpbiDigJxMZXZlbG1l" +
           "dGVy4oCdIFN0YWNrbGlnaHRNb2RlLiBJZiBzbywgdGhlIHdob2xlIHN0YWNrIGlzIGNvbnRyb2xsZWQg" +
           "YnkgYSBzaW5nbGUgcGVyY2VudHVhbCB2YWx1ZS4gSW4gdGhpcyBjYXNlLCB0aGUgU2lnbmFsT24gcGFy" +
           "YW1ldGVyIG9mIGFueSBzdGFjayBlbGVtZW50IG9mIFN0YWNrRWxlbWVudExpZ2h0VHlwZSBoYXMgbm8g" +
           "bWVhbmluZy4ALwEB6wOJEwAA/////wIAAAA1YIkKAgAAAAEACwAAAERpc3BsYXlNb2RlAQGSFwMAAAAA" +
           "TAAAAEluZGljYXRlcyBpbiB3aGF0IHdheSB0aGUgcGVyY2VudHVhbCB2YWx1ZSBpcyBkaXNwbGF5ZWQg" +
           "d2l0aCB0aGUgc3RhY2tsaWdodC4ALwA/khcAAAEBuwv/////AwP/////AAAAADVgiQoCAAAAAQAMAAAA" +
           "TGV2ZWxQZXJjZW50AQGTFwMAAAAAMgEAAFNob3dzIHRoZSBwZXJjZW50dWFsIHZhbHVlIHRoZSBzdGFj" +
           "a2xpZ2h0IGlzIHJlcHJlc2VudGluZy4gVGhlIG1hbmRhdG9yeSBFVVJhbmdlIFByb3BlcnR5IG9mIHRo" +
           "ZSBWYXJpYWJsZSBpbmRpY2F0ZXMgdGhlIGxvd2VzdCBhbmQgaGlnaGVzdCB2YWx1ZSBhbmQgdGhlcmVi" +
           "eSBhbGxvd3MgdG8gY2FsY3VsYXRlIHRoZSBwZXJjZW50YWdlIHJlcHJlc2VudGVkIGJ5IHRoZSB2YWx1" +
           "ZS4gVGhlIGxvd2VzdCB2YWx1ZSBpcyBpbnRlcnByZXRlZCBhcyAwIHBlcmNlbnQsIHRoZSBoaWdoZXN0" +
           "IGlzIGludGVycHJldGVkIGFzIDEwMCBwZXJjZW50LgAvAQBACZMXAAAACv////8DA/////8BAAAAFWCJ" +
           "CgIAAAAAAAcAAABFVVJhbmdlAQGUFwAuAESUFwAAAQB0A/////8BAf////8AAAAANWCJCgIAAAABAA4A" +
           "AABTdGFja2xpZ2h0TW9kZQEBeRcDAAAAAGcAAABTaG93cyBpbiB3aGF0IHdheSAoc3RhY2sgb2YgaW5k" +
           "aXZpZHVhbCBsaWdodHMsIGxldmVsIG1ldGVyLCBydW5uaW5nIGxpZ2h0KSB0aGUgc3RhY2tsaWdodCB1" +
           "bml0IGlzIHVzZWQuAC4ARHkXAAABAboL/////wMD/////wAAAAAkYIAKAQAAAAEADAAAAFN0YWNrUnVu" +
           "bmluZwEBjRMDAAAAAEYAAABWYWxpZCBpZiB0aGUgc3RhY2tsaWdodCBpcyB1c2VkIGluIOKAnFJ1bm5p" +
           "bmdfTGlnaHTigJ0gU3RhY2tsaWdodE1vZGUuAC8BAewDjRMAAP////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public StackLevelTypeState StackLevel
        {
            get => m_stackLevel;

            set
            {
                if (!Object.ReferenceEquals(m_stackLevel, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_stackLevel = value;
            }
        }

        public PropertyState<StacklightOperationMode> StacklightMode
        {
            get => m_stacklightMode;

            set
            {
                if (!Object.ReferenceEquals(m_stacklightMode, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_stacklightMode = value;
            }
        }

        public StackRunningTypeState StackRunning
        {
            get => m_stackRunning;

            set
            {
                if (!Object.ReferenceEquals(m_stackRunning, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_stackRunning = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_stackLevel != null)
            {
                children.Add(m_stackLevel);
            }

            if (m_stacklightMode != null)
            {
                children.Add(m_stacklightMode);
            }

            if (m_stackRunning != null)
            {
                children.Add(m_stackRunning);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_stackLevel, child))
            {
                m_stackLevel = null;
                return;
            }

            if (Object.ReferenceEquals(m_stacklightMode, child))
            {
                m_stacklightMode = null;
                return;
            }

            if (Object.ReferenceEquals(m_stackRunning, child))
            {
                m_stackRunning = null;
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
                case UAModel.IA.BrowseNames.StackLevel:
                {
                    if (createOrReplace)
                    {
                        if (StackLevel == null)
                        {
                            if (replacement == null)
                            {
                                StackLevel = new StackLevelTypeState(this);
                            }
                            else
                            {
                                StackLevel = (StackLevelTypeState)replacement;
                            }
                        }
                    }

                    instance = StackLevel;
                    break;
                }

                case UAModel.IA.BrowseNames.StacklightMode:
                {
                    if (createOrReplace)
                    {
                        if (StacklightMode == null)
                        {
                            if (replacement == null)
                            {
                                StacklightMode = new PropertyState<StacklightOperationMode>(this);
                            }
                            else
                            {
                                StacklightMode = (PropertyState<StacklightOperationMode>)replacement;
                            }
                        }
                    }

                    instance = StacklightMode;
                    break;
                }

                case UAModel.IA.BrowseNames.StackRunning:
                {
                    if (createOrReplace)
                    {
                        if (StackRunning == null)
                        {
                            if (replacement == null)
                            {
                                StackRunning = new StackRunningTypeState(this);
                            }
                            else
                            {
                                StackRunning = (StackRunningTypeState)replacement;
                            }
                        }
                    }

                    instance = StackRunning;
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
        private StackLevelTypeState m_stackLevel;
        private PropertyState<StacklightOperationMode> m_stacklightMode;
        private StackRunningTypeState m_stackRunning;
        #endregion
    }
    #endif
    #endregion

    #region StacklightTypeState Class
    #if (!OPCUA_EXCLUDE_StacklightTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class StacklightTypeState : BasicStacklightTypeState
    {
        #region Constructors
        public StacklightTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.StacklightType, UAModel.IA.Namespaces.IA, namespaceUris);
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

            if (DeviceHealth != null)
            {
                DeviceHealth.Initialize(context, DeviceHealth_InitializationString);
            }

            if (DeviceHealthAlarms != null)
            {
                DeviceHealthAlarms.Initialize(context, DeviceHealthAlarms_InitializationString);
            }
        }

        #region Initialization String
        private const string DeviceHealth_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAACAAwAAABEZXZpY2VIZWFsdGgBAZYXAwAAAAA5AAAAQ29u" +
           "dGFpbnMgdGhlIGhlYWx0aCBzdGF0dXMgaW5mb3JtYXRpb24gb2YgdGhlIHN0YWNrbGlnaHQuAC8AP5YX" +
           "AAABAmQY/////wMD/////wAAAAA=";

        private const string DeviceHealthAlarms_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////JGCACgEAAAACABIAAABEZXZpY2VIZWFsdGhBbGFybXMBAY8TAwAAAABn" +
           "AAAAQ29udGFpbnMgYWxhcm1zIG9mIHRoZSBzdGFja2xpZ2h0cyBwcm92aWRpbmcgbW9yZSBkZXRhaWxl" +
           "ZCBpbmZvcm1hdGlvbiBvbiB0aGUgaGVhbHRoIG9mIHRoZSBzdGFja2xpZ2h0LgAvAD2PEwAA/////wAA" +
           "AAA=";

        private const string InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABABYAAABTdGFja2xpZ2h0VHlwZUluc3RhbmNlAQHyAwEB" +
           "8gPyAwAAAQAAAAEAw0QAAQLLOgMAAAA1YIkKAgAAAAEADgAAAFN0YWNrbGlnaHRNb2RlAQF5FwMAAAAA" +
           "ZwAAAFNob3dzIGluIHdoYXQgd2F5IChzdGFjayBvZiBpbmRpdmlkdWFsIGxpZ2h0cywgbGV2ZWwgbWV0" +
           "ZXIsIHJ1bm5pbmcgbGlnaHQpIHRoZSBzdGFja2xpZ2h0IHVuaXQgaXMgdXNlZC4ALgBEeRcAAAEBugv/" +
           "////AwP/////AAAAADVgiQoCAAAAAgAMAAAARGV2aWNlSGVhbHRoAQGWFwMAAAAAOQAAAENvbnRhaW5z" +
           "IHRoZSBoZWFsdGggc3RhdHVzIGluZm9ybWF0aW9uIG9mIHRoZSBzdGFja2xpZ2h0LgAvAD+WFwAAAQJk" +
           "GP////8DA/////8AAAAAJGCACgEAAAACABIAAABEZXZpY2VIZWFsdGhBbGFybXMBAY8TAwAAAABnAAAA" +
           "Q29udGFpbnMgYWxhcm1zIG9mIHRoZSBzdGFja2xpZ2h0cyBwcm92aWRpbmcgbW9yZSBkZXRhaWxlZCBp" +
           "bmZvcm1hdGlvbiBvbiB0aGUgaGVhbHRoIG9mIHRoZSBzdGFja2xpZ2h0LgAvAD2PEwAA/////wAAAAA=";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public BaseDataVariableState<DeviceHealthEnumeration> DeviceHealth
        {
            get => m_deviceHealth;

            set
            {
                if (!Object.ReferenceEquals(m_deviceHealth, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_deviceHealth = value;
            }
        }

        public FolderState DeviceHealthAlarms
        {
            get => m_deviceHealthAlarms;

            set
            {
                if (!Object.ReferenceEquals(m_deviceHealthAlarms, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_deviceHealthAlarms = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_deviceHealth != null)
            {
                children.Add(m_deviceHealth);
            }

            if (m_deviceHealthAlarms != null)
            {
                children.Add(m_deviceHealthAlarms);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_deviceHealth, child))
            {
                m_deviceHealth = null;
                return;
            }

            if (Object.ReferenceEquals(m_deviceHealthAlarms, child))
            {
                m_deviceHealthAlarms = null;
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
                case UAModel.DI.BrowseNames.DeviceHealth:
                {
                    if (createOrReplace)
                    {
                        if (DeviceHealth == null)
                        {
                            if (replacement == null)
                            {
                                DeviceHealth = new BaseDataVariableState<DeviceHealthEnumeration>(this);
                            }
                            else
                            {
                                DeviceHealth = (BaseDataVariableState<DeviceHealthEnumeration>)replacement;
                            }
                        }
                    }

                    instance = DeviceHealth;
                    break;
                }

                case UAModel.DI.BrowseNames.DeviceHealthAlarms:
                {
                    if (createOrReplace)
                    {
                        if (DeviceHealthAlarms == null)
                        {
                            if (replacement == null)
                            {
                                DeviceHealthAlarms = new FolderState(this);
                            }
                            else
                            {
                                DeviceHealthAlarms = (FolderState)replacement;
                            }
                        }
                    }

                    instance = DeviceHealthAlarms;
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
        private BaseDataVariableState<DeviceHealthEnumeration> m_deviceHealth;
        private FolderState m_deviceHealthAlarms;
        #endregion
    }
    #endif
    #endregion

    #region StackElementTypeState Class
    #if (!OPCUA_EXCLUDE_StackElementTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class StackElementTypeState : BaseObjectState
    {
        #region Constructors
        public StackElementTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.StackElementType, UAModel.IA.Namespaces.IA, namespaceUris);
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

            if (IsPartOfBase != null)
            {
                IsPartOfBase.Initialize(context, IsPartOfBase_InitializationString);
            }

            if (SignalOn != null)
            {
                SignalOn.Initialize(context, SignalOn_InitializationString);
            }
        }

        #region Initialization String
        private const string IsPartOfBase_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABAAwAAABJc1BhcnRPZkJhc2UBAX4XAwAAAACzAAAASW5k" +
           "aWNhdGVzLCBpZiB0aGUgZWxlbWVudCBpcyBjb250YWluZWQgaW4gdGhlIG1vdW50aW5nIGJhc2Ugb2Yg" +
           "dGhlIHN0YWNrbGlnaHQuIEFsbCBlbGVtZW50cyBjb250YWluZWQgaW4gdGhlIG1vdW50aW5nIGJhc2Ug" +
           "c2hhbGwgYmUgYXQgdGhlIGJlZ2lubmluZyBvZiB0aGUgbGlzdCBvZiBzdGFjayBlbGVtZW50cy4ALgBE" +
           "fhcAAAAB/////wMD/////wAAAAA=";

        private const string SignalOn_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABAAgAAABTaWduYWxPbgEBfRcDAAAAAFUAAABJbmRpY2F0" +
           "ZXMgaWYgdGhlIHNpZ25hbCBlbWl0dGVkIGJ5IHRoZSBzdGFjayBlbGVtZW50IGlzIGN1cnJlbnRseSBz" +
           "d2l0Y2hlZCBvbiBvciBub3QuAC4ARH0XAAAAAf////8DA/////8AAAAA";

        private const string InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABABgAAABTdGFja0VsZW1lbnRUeXBlSW5zdGFuY2UBAe0D" +
           "AQHtA+0DAAABAAAAAQDDRAABANlbAwAAADVgiQoCAAAAAQAMAAAASXNQYXJ0T2ZCYXNlAQF+FwMAAAAA" +
           "swAAAEluZGljYXRlcywgaWYgdGhlIGVsZW1lbnQgaXMgY29udGFpbmVkIGluIHRoZSBtb3VudGluZyBi" +
           "YXNlIG9mIHRoZSBzdGFja2xpZ2h0LiBBbGwgZWxlbWVudHMgY29udGFpbmVkIGluIHRoZSBtb3VudGlu" +
           "ZyBiYXNlIHNoYWxsIGJlIGF0IHRoZSBiZWdpbm5pbmcgb2YgdGhlIGxpc3Qgb2Ygc3RhY2sgZWxlbWVu" +
           "dHMuAC4ARH4XAAAAAf////8DA/////8AAAAANWCJCgIAAAAAAAwAAABOdW1iZXJJbkxpc3QBAX8XAwAA" +
           "AABdAAAARW51bWVyYXRlIHRoZSBzdGFja2xpZ2h0IGVsZW1lbnRzIGNvdW50aW5nIHVwd2FyZHMgYmVn" +
           "aW5uaW5nIGZyb20gdGhlIGJhc2Ugb2YgdGhlIHN0YWNrbGlnaHQuAC4ARH8XAAAAHP////8BAf////8A" +
           "AAAANWCJCgIAAAABAAgAAABTaWduYWxPbgEBfRcDAAAAAFUAAABJbmRpY2F0ZXMgaWYgdGhlIHNpZ25h" +
           "bCBlbWl0dGVkIGJ5IHRoZSBzdGFjayBlbGVtZW50IGlzIGN1cnJlbnRseSBzd2l0Y2hlZCBvbiBvciBu" +
           "b3QuAC4ARH0XAAAAAf////8DA/////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public PropertyState<bool> IsPartOfBase
        {
            get => m_isPartOfBase;

            set
            {
                if (!Object.ReferenceEquals(m_isPartOfBase, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_isPartOfBase = value;
            }
        }

        public PropertyState NumberInList
        {
            get => m_numberInList;

            set
            {
                if (!Object.ReferenceEquals(m_numberInList, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_numberInList = value;
            }
        }

        public PropertyState<bool> SignalOn
        {
            get => m_signalOn;

            set
            {
                if (!Object.ReferenceEquals(m_signalOn, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_signalOn = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_isPartOfBase != null)
            {
                children.Add(m_isPartOfBase);
            }

            if (m_numberInList != null)
            {
                children.Add(m_numberInList);
            }

            if (m_signalOn != null)
            {
                children.Add(m_signalOn);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_isPartOfBase, child))
            {
                m_isPartOfBase = null;
                return;
            }

            if (Object.ReferenceEquals(m_numberInList, child))
            {
                m_numberInList = null;
                return;
            }

            if (Object.ReferenceEquals(m_signalOn, child))
            {
                m_signalOn = null;
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
                case UAModel.IA.BrowseNames.IsPartOfBase:
                {
                    if (createOrReplace)
                    {
                        if (IsPartOfBase == null)
                        {
                            if (replacement == null)
                            {
                                IsPartOfBase = new PropertyState<bool>(this);
                            }
                            else
                            {
                                IsPartOfBase = (PropertyState<bool>)replacement;
                            }
                        }
                    }

                    instance = IsPartOfBase;
                    break;
                }

                case Opc.Ua.BrowseNames.NumberInList:
                {
                    if (createOrReplace)
                    {
                        if (NumberInList == null)
                        {
                            if (replacement == null)
                            {
                                NumberInList = new PropertyState(this);
                            }
                            else
                            {
                                NumberInList = (PropertyState)replacement;
                            }
                        }
                    }

                    instance = NumberInList;
                    break;
                }

                case UAModel.IA.BrowseNames.SignalOn:
                {
                    if (createOrReplace)
                    {
                        if (SignalOn == null)
                        {
                            if (replacement == null)
                            {
                                SignalOn = new PropertyState<bool>(this);
                            }
                            else
                            {
                                SignalOn = (PropertyState<bool>)replacement;
                            }
                        }
                    }

                    instance = SignalOn;
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
        private PropertyState<bool> m_isPartOfBase;
        private PropertyState m_numberInList;
        private PropertyState<bool> m_signalOn;
        #endregion
    }
    #endif
    #endregion

    #region StackElementAcousticTypeState Class
    #if (!OPCUA_EXCLUDE_StackElementAcousticTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class StackElementAcousticTypeState : StackElementTypeState
    {
        #region Constructors
        public StackElementAcousticTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.StackElementAcousticType, UAModel.IA.Namespaces.IA, namespaceUris);
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

            if (Intensity != null)
            {
                Intensity.Initialize(context, Intensity_InitializationString);
            }
        }

        #region Initialization String
        private const string Intensity_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABAAkAAABJbnRlbnNpdHkBAYUXAwAAAABvAQAASW5kaWNh" +
           "dGVzIHRoZSBzb3VuZCBwcmVzc3VyZSBsZXZlbCBvZiB0aGUgYWNvdXN0aWMgc2lnbmFsIHdoZW4gc3dp" +
           "dGNoZWQgb24uIFRoaXMgdmFsdWUgc2hhbGwgb25seSBoYXZlIHBvc2l0aXZlIHZhbHVlcy4gVGhlIG1h" +
           "bmRhdG9yeSBFVVJhbmdlIFByb3BlcnR5IG9mIHRoZSBWYXJpYWJsZSBpbmRpY2F0ZXMgdGhlIGxvd2Vz" +
           "dCBhbmQgaGlnaGVzdCB2YWx1ZSBhbmQgdGhlcmVieSBhbGxvd3MgdG8gY2FsY3VsYXRlIHRoZSBwZXJj" +
           "ZW50YWdlIHJlcHJlc2VudGVkIGJ5IHRoZSB2YWx1ZS4gVGhlIGxvd2VzdCB2YWx1ZSBpcyBpbnRlcnBy" +
           "ZXRlZCBhcyAwIHBlcmNlbnQsIHRoZSBoaWdoZXN0IGlzIGludGVycHJldGVkIGFzIDEwMCBwZXJjZW50" +
           "LgAvAQBACYUXAAAACv////8DA/////8BAAAAFWCJCgIAAAAAAAcAAABFVVJhbmdlAQGGFwAuAESGFwAA" +
           "AQB0A/////8BAf////8AAAAA";

        private const string InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABACAAAABTdGFja0VsZW1lbnRBY291c3RpY1R5cGVJbnN0" +
           "YW5jZQEB7wMBAe8D7wMAAP////8EAAAANWCJCgIAAAAAAAwAAABOdW1iZXJJbkxpc3QBAX8XAwAAAABd" +
           "AAAARW51bWVyYXRlIHRoZSBzdGFja2xpZ2h0IGVsZW1lbnRzIGNvdW50aW5nIHVwd2FyZHMgYmVnaW5u" +
           "aW5nIGZyb20gdGhlIGJhc2Ugb2YgdGhlIHN0YWNrbGlnaHQuAC4ARH8XAAAAHP////8BAf////8AAAAA" +
           "JGCACgEAAAABAA8AAABBY291c3RpY1NpZ25hbHMBAYsTAwAAAABKAAAAQ29udGFpbnMgYSBsaXN0IG9m" +
           "IGF1ZGlvIHNpZ25hbHMgdXNlZCBieSB0aGlzIGFjb3VzdGljIHN0YWNrbGlnaHQgZWxlbWVudC4ALwEA" +
           "3luLEwAAAQAAAAApAAEAVQgBAAAAJGDACgEAAAANAAAAT3JkZXJlZE9iamVjdAAADwAAADxPcmRlcmVk" +
           "T2JqZWN0PgEBjBMDAAAAAB4AAABSZXByZXNlbnRzIGFuIGFjb3VzdGljIHNpZ25hbC4AMQEB8QOMEwAA" +
           "AQAAAAEAw0QAAQDZWwEAAAA1YIkKAgAAAAAADAAAAE51bWJlckluTGlzdAEBjhcDAAAAAH4AAABFbnVt" +
           "ZXJhdGUgdGhlIGFjb3VzdGljIHNpZ25hbHMuIEluc3RhbmNlcyBvZiBTdGFja0VsZW1lbnRBY291c3Rp" +
           "Y1R5cGUgaW5kZXggaW50byB0aGlzIG51bWJlciB1c2luZyB0aGUgT3BlcmF0aW9uTW9kZSBQcm9wZXJ0" +
           "eS4ALgBEjhcAAAAc/////wMD/////wAAAAA1YIkKAgAAAAEACQAAAEludGVuc2l0eQEBhRcDAAAAAG8B" +
           "AABJbmRpY2F0ZXMgdGhlIHNvdW5kIHByZXNzdXJlIGxldmVsIG9mIHRoZSBhY291c3RpYyBzaWduYWwg" +
           "d2hlbiBzd2l0Y2hlZCBvbi4gVGhpcyB2YWx1ZSBzaGFsbCBvbmx5IGhhdmUgcG9zaXRpdmUgdmFsdWVz" +
           "LiBUaGUgbWFuZGF0b3J5IEVVUmFuZ2UgUHJvcGVydHkgb2YgdGhlIFZhcmlhYmxlIGluZGljYXRlcyB0" +
           "aGUgbG93ZXN0IGFuZCBoaWdoZXN0IHZhbHVlIGFuZCB0aGVyZWJ5IGFsbG93cyB0byBjYWxjdWxhdGUg" +
           "dGhlIHBlcmNlbnRhZ2UgcmVwcmVzZW50ZWQgYnkgdGhlIHZhbHVlLiBUaGUgbG93ZXN0IHZhbHVlIGlz" +
           "IGludGVycHJldGVkIGFzIDAgcGVyY2VudCwgdGhlIGhpZ2hlc3QgaXMgaW50ZXJwcmV0ZWQgYXMgMTAw" +
           "IHBlcmNlbnQuAC8BAEAJhRcAAAAK/////wMD/////wEAAAAVYIkKAgAAAAAABwAAAEVVUmFuZ2UBAYYX" +
           "AC4ARIYXAAABAHQD/////wEB/////wAAAAA1YIkKAgAAAAEADQAAAE9wZXJhdGlvbk1vZGUBAYQXAwAA" +
           "AADhAAAASW5kaWNhdGVzIHdoYXQgc2lnbmFsIG9mIHRoZSBsaXN0IG9mIEFjb3VzdGljU2lnbmFsVHlw" +
           "ZSBub2RlcyBpcyBwbGF5ZWQgd2hlbiB0aGUgYWNvdXN0aWMgZWxlbWVudCBpcyBzd2l0Y2hlZCBvbi4g" +
           "SXQgc2hhbGwgY29udGFpbiBhbiBpbmRleCBpbnRvIHRoZSBOdW1iZXJJbkxpc3Qgb2YgdGhlIHJlc3Bl" +
           "Y3RpdmUgQWNvdXN0aWNTaWduYWxUeXBlIE9iamVjdCBvZiBBY291c3RpY1NpZ25hbHMuAC8AP4QXAAAA" +
           "HP////8DA/////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public OrderedListState AcousticSignals
        {
            get => m_acousticSignals;

            set
            {
                if (!Object.ReferenceEquals(m_acousticSignals, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_acousticSignals = value;
            }
        }

        public AnalogItemState<float> Intensity
        {
            get => m_intensity;

            set
            {
                if (!Object.ReferenceEquals(m_intensity, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_intensity = value;
            }
        }

        public BaseDataVariableState OperationMode
        {
            get => m_operationMode;

            set
            {
                if (!Object.ReferenceEquals(m_operationMode, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_operationMode = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_acousticSignals != null)
            {
                children.Add(m_acousticSignals);
            }

            if (m_intensity != null)
            {
                children.Add(m_intensity);
            }

            if (m_operationMode != null)
            {
                children.Add(m_operationMode);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_acousticSignals, child))
            {
                m_acousticSignals = null;
                return;
            }

            if (Object.ReferenceEquals(m_intensity, child))
            {
                m_intensity = null;
                return;
            }

            if (Object.ReferenceEquals(m_operationMode, child))
            {
                m_operationMode = null;
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
                case UAModel.IA.BrowseNames.AcousticSignals:
                {
                    if (createOrReplace)
                    {
                        if (AcousticSignals == null)
                        {
                            if (replacement == null)
                            {
                                AcousticSignals = new OrderedListState(this);
                            }
                            else
                            {
                                AcousticSignals = (OrderedListState)replacement;
                            }
                        }
                    }

                    instance = AcousticSignals;
                    break;
                }

                case UAModel.IA.BrowseNames.Intensity:
                {
                    if (createOrReplace)
                    {
                        if (Intensity == null)
                        {
                            if (replacement == null)
                            {
                                Intensity = new AnalogItemState<float>(this);
                            }
                            else
                            {
                                Intensity = (AnalogItemState<float>)replacement;
                            }
                        }
                    }

                    instance = Intensity;
                    break;
                }

                case UAModel.IA.BrowseNames.OperationMode:
                {
                    if (createOrReplace)
                    {
                        if (OperationMode == null)
                        {
                            if (replacement == null)
                            {
                                OperationMode = new BaseDataVariableState(this);
                            }
                            else
                            {
                                OperationMode = (BaseDataVariableState)replacement;
                            }
                        }
                    }

                    instance = OperationMode;
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
        private OrderedListState m_acousticSignals;
        private AnalogItemState<float> m_intensity;
        private BaseDataVariableState m_operationMode;
        #endregion
    }
    #endif
    #endregion

    #region StackElementLightTypeState Class
    #if (!OPCUA_EXCLUDE_StackElementLightTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class StackElementLightTypeState : StackElementTypeState
    {
        #region Constructors
        public StackElementLightTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.StackElementLightType, UAModel.IA.Namespaces.IA, namespaceUris);
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

            if (Intensity != null)
            {
                Intensity.Initialize(context, Intensity_InitializationString);
            }

            if (SignalColor != null)
            {
                SignalColor.Initialize(context, SignalColor_InitializationString);
            }

            if (SignalMode != null)
            {
                SignalMode.Initialize(context, SignalMode_InitializationString);
            }

            if (SignalRGBWValue != null)
            {
                SignalRGBWValue.Initialize(context, SignalRGBWValue_InitializationString);
            }
        }

        #region Initialization String
        private const string Intensity_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABAAkAAABJbnRlbnNpdHkBAYIXAwAAAAAjAQAASW50ZW5z" +
           "aXR5IG9mIHRoZSBsYW1wLCB0aHVzIGl0cyBicmlnaHRuZXNzLiBUaGUgbWFuZGF0b3J5IEVVUmFuZ2Ug" +
           "UHJvcGVydHkgb2YgdGhlIFZhcmlhYmxlIGluZGljYXRlcyB0aGUgbG93ZXN0IGFuZCBoaWdoZXN0IHZh" +
           "bHVlIGFuZCB0aGVyZWJ5IGFsbG93cyB0byBjYWxjdWxhdGUgdGhlIHBlcmNlbnRhZ2UgcmVwcmVzZW50" +
           "ZWQgYnkgdGhlIHZhbHVlLiBUaGUgbG93ZXN0IHZhbHVlIGlzIGludGVycHJldGVkIGFzIDAgcGVyY2Vu" +
           "dCwgdGhlIGhpZ2hlc3QgaXMgaW50ZXJwcmV0ZWQgYXMgMTAwIHBlcmNlbnQuAC8BAEAJghcAAAAK////" +
           "/wMD/////wEAAAAVYIkKAgAAAAAABwAAAEVVUmFuZ2UBAYMXAC4ARIMXAAABAHQD/////wEB/////wAA" +
           "AAA=";

        private const string SignalColor_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABAAsAAABTaWduYWxDb2xvcgEBgBcDAAAAADsAAABJbmRp" +
           "Y2F0ZXMgdGhlIGNvbG91ciB0aGUgbGFtcCBlbGVtZW50IGhhcyB3aGVuIHN3aXRjaGVkIG9uLgAvAD+A" +
           "FwAAAQG8C/////8DA/////8AAAAA";

        private const string SignalMode_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////NWCJCgIAAAABAAoAAABTaWduYWxNb2RlAQGBFwMAAAAAWwAAAFNob3dz" +
           "IGluIHdoYXQgd2F5IHRoZSBsYW1wIGlzIHVzZWQgKGNvbnRpbnVvdXMgbGlnaHQsIGZsYXNoaW5nLCBi" +
           "bGlua2luZykgd2hlbiBzd2l0Y2hlZCBvbi4ALwA/gRcAAAEBvQv/////AwP/////AAAAAA==";

        private const string SignalRGBWValue_InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////FWCJCgIAAAABAA8AAABTaWduYWxSR0JXVmFsdWUBAaQXAC8AP6QXAAAB" +
           "Ab8L/////wMD/////wAAAAA=";

        private const string InitializationString =
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABAB0AAABTdGFja0VsZW1lbnRMaWdodFR5cGVJbnN0YW5j" +
           "ZQEB7gMBAe4D7gMAAP////8GAAAANWCJCgIAAAAAAAwAAABOdW1iZXJJbkxpc3QBAX8XAwAAAABdAAAA" +
           "RW51bWVyYXRlIHRoZSBzdGFja2xpZ2h0IGVsZW1lbnRzIGNvdW50aW5nIHVwd2FyZHMgYmVnaW5uaW5n" +
           "IGZyb20gdGhlIGJhc2Ugb2YgdGhlIHN0YWNrbGlnaHQuAC4ARH8XAAAAHP////8BAf////8AAAAAJGDA" +
           "CgEAAAAaAAAAQ29udHJvbENoYW5uZWxfUGxhY2Vob2xkZXIBABAAAAA8Q29udHJvbENoYW5uZWw+AQGK" +
           "EwMAAAAAgAAAAFRoZSBsaXN0IG9mIDxDb250cm9sQ2hhbm5lbD4gaW5zdGFuY2VzIHNob3dzIHRoZSBj" +
           "b250cm9sIGluZm9ybWF0aW9uIGZvciBlYWNoIGluZGVwZW5kZW50IGNvbG91ciBjaGFubmVsIG9mIHRo" +
           "ZSBzdGFja2VkIGVsZW1lbnQuAC8BAfADihMAAP////8DAAAANWCJCgIAAAABAAwAAABDaGFubmVsQ29s" +
           "b3IBAY8XAwAAAABjAAAASW5kaWNhdGVzIGluIHdoYXQgbW9kZSAoY29udGludW91c2x5IG9uLCBibGlu" +
           "a2luZywgZmxhc2hpbmcpIHRoZSBjaGFubmVsIG9wZXJhdGVzIHdoZW4gc3dpdGNoZWQgb24uAC8AP48X" +
           "AAABAbwL/////wMD/////wAAAAA1YIkKAgAAAAEACgAAAFNpZ25hbE1vZGUBAZAXAwAAAABKAAAAQ29u" +
           "dGFpbnMgYSBsaXN0IG9mIGF1ZGlvIHNpZ25hbHMgdXNlZCBieSB0aGlzIGFjb3VzdGljIHN0YWNrbGln" +
           "aHQgZWxlbWVudC4ALwA/kBcAAAEBvQv/////AwP/////AAAAADVgiQoCAAAAAQAIAAAAU2lnbmFsT24B" +
           "AZEXAwAAAAAnAAAASW5kaWNhdGVzIGlmIHRoZSBjb2xvdXIgaXMgc3dpdGNoZWQgb24uAC4ARJEXAAAA" +
           "Af////8DA/////8AAAAANWCJCgIAAAABAAkAAABJbnRlbnNpdHkBAYIXAwAAAAAjAQAASW50ZW5zaXR5" +
           "IG9mIHRoZSBsYW1wLCB0aHVzIGl0cyBicmlnaHRuZXNzLiBUaGUgbWFuZGF0b3J5IEVVUmFuZ2UgUHJv" +
           "cGVydHkgb2YgdGhlIFZhcmlhYmxlIGluZGljYXRlcyB0aGUgbG93ZXN0IGFuZCBoaWdoZXN0IHZhbHVl" +
           "IGFuZCB0aGVyZWJ5IGFsbG93cyB0byBjYWxjdWxhdGUgdGhlIHBlcmNlbnRhZ2UgcmVwcmVzZW50ZWQg" +
           "YnkgdGhlIHZhbHVlLiBUaGUgbG93ZXN0IHZhbHVlIGlzIGludGVycHJldGVkIGFzIDAgcGVyY2VudCwg" +
           "dGhlIGhpZ2hlc3QgaXMgaW50ZXJwcmV0ZWQgYXMgMTAwIHBlcmNlbnQuAC8BAEAJghcAAAAK/////wMD" +
           "/////wEAAAAVYIkKAgAAAAAABwAAAEVVUmFuZ2UBAYMXAC4ARIMXAAABAHQD/////wEB/////wAAAAA1" +
           "YIkKAgAAAAEACwAAAFNpZ25hbENvbG9yAQGAFwMAAAAAOwAAAEluZGljYXRlcyB0aGUgY29sb3VyIHRo" +
           "ZSBsYW1wIGVsZW1lbnQgaGFzIHdoZW4gc3dpdGNoZWQgb24uAC8AP4AXAAABAbwL/////wMD/////wAA" +
           "AAA1YIkKAgAAAAEACgAAAFNpZ25hbE1vZGUBAYEXAwAAAABbAAAAU2hvd3MgaW4gd2hhdCB3YXkgdGhl" +
           "IGxhbXAgaXMgdXNlZCAoY29udGludW91cyBsaWdodCwgZmxhc2hpbmcsIGJsaW5raW5nKSB3aGVuIHN3" +
           "aXRjaGVkIG9uLgAvAD+BFwAAAQG9C/////8DA/////8AAAAAFWCJCgIAAAABAA8AAABTaWduYWxSR0JX" +
           "VmFsdWUBAaQXAC8AP6QXAAABAb8L/////wMD/////wAAAAA=";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public AnalogItemState<float> Intensity
        {
            get => m_intensity;

            set
            {
                if (!Object.ReferenceEquals(m_intensity, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_intensity = value;
            }
        }

        public BaseDataVariableState<SignalColor> SignalColor
        {
            get => m_signalColor;

            set
            {
                if (!Object.ReferenceEquals(m_signalColor, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_signalColor = value;
            }
        }

        public BaseDataVariableState<SignalModeLight> SignalMode
        {
            get => m_signalMode;

            set
            {
                if (!Object.ReferenceEquals(m_signalMode, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_signalMode = value;
            }
        }

        public BaseDataVariableState<RGBWDataType> SignalRGBWValue
        {
            get => m_signalRGBWValue;

            set
            {
                if (!Object.ReferenceEquals(m_signalRGBWValue, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_signalRGBWValue = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_intensity != null)
            {
                children.Add(m_intensity);
            }

            if (m_signalColor != null)
            {
                children.Add(m_signalColor);
            }

            if (m_signalMode != null)
            {
                children.Add(m_signalMode);
            }

            if (m_signalRGBWValue != null)
            {
                children.Add(m_signalRGBWValue);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_intensity, child))
            {
                m_intensity = null;
                return;
            }

            if (Object.ReferenceEquals(m_signalColor, child))
            {
                m_signalColor = null;
                return;
            }

            if (Object.ReferenceEquals(m_signalMode, child))
            {
                m_signalMode = null;
                return;
            }

            if (Object.ReferenceEquals(m_signalRGBWValue, child))
            {
                m_signalRGBWValue = null;
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
                case UAModel.IA.BrowseNames.Intensity:
                {
                    if (createOrReplace)
                    {
                        if (Intensity == null)
                        {
                            if (replacement == null)
                            {
                                Intensity = new AnalogItemState<float>(this);
                            }
                            else
                            {
                                Intensity = (AnalogItemState<float>)replacement;
                            }
                        }
                    }

                    instance = Intensity;
                    break;
                }

                case UAModel.IA.BrowseNames.SignalColor:
                {
                    if (createOrReplace)
                    {
                        if (SignalColor == null)
                        {
                            if (replacement == null)
                            {
                                SignalColor = new BaseDataVariableState<SignalColor>(this);
                            }
                            else
                            {
                                SignalColor = (BaseDataVariableState<SignalColor>)replacement;
                            }
                        }
                    }

                    instance = SignalColor;
                    break;
                }

                case UAModel.IA.BrowseNames.SignalMode:
                {
                    if (createOrReplace)
                    {
                        if (SignalMode == null)
                        {
                            if (replacement == null)
                            {
                                SignalMode = new BaseDataVariableState<SignalModeLight>(this);
                            }
                            else
                            {
                                SignalMode = (BaseDataVariableState<SignalModeLight>)replacement;
                            }
                        }
                    }

                    instance = SignalMode;
                    break;
                }

                case UAModel.IA.BrowseNames.SignalRGBWValue:
                {
                    if (createOrReplace)
                    {
                        if (SignalRGBWValue == null)
                        {
                            if (replacement == null)
                            {
                                SignalRGBWValue = new BaseDataVariableState<RGBWDataType>(this);
                            }
                            else
                            {
                                SignalRGBWValue = (BaseDataVariableState<RGBWDataType>)replacement;
                            }
                        }
                    }

                    instance = SignalRGBWValue;
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
        private AnalogItemState<float> m_intensity;
        private BaseDataVariableState<SignalColor> m_signalColor;
        private BaseDataVariableState<SignalModeLight> m_signalMode;
        private BaseDataVariableState<RGBWDataType> m_signalRGBWValue;
        #endregion
    }
    #endif
    #endregion

    #region StackLevelTypeState Class
    #if (!OPCUA_EXCLUDE_StackLevelTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class StackLevelTypeState : BaseObjectState
    {
        #region Constructors
        public StackLevelTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.StackLevelType, UAModel.IA.Namespaces.IA, namespaceUris);
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
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABABYAAABTdGFja0xldmVsVHlwZUluc3RhbmNlAQHrAwEB" +
           "6wPrAwAA/////wIAAAA1YIkKAgAAAAEACwAAAERpc3BsYXlNb2RlAQF8FwMAAAAATAAAAEluZGljYXRl" +
           "cyBpbiB3aGF0IHdheSB0aGUgcGVyY2VudHVhbCB2YWx1ZSBpcyBkaXNwbGF5ZWQgd2l0aCB0aGUgc3Rh" +
           "Y2tsaWdodC4ALwA/fBcAAAEBuwv/////AwP/////AAAAADVgiQoCAAAAAQAMAAAATGV2ZWxQZXJjZW50" +
           "AQF6FwMAAAAAMgEAAFNob3dzIHRoZSBwZXJjZW50dWFsIHZhbHVlIHRoZSBzdGFja2xpZ2h0IGlzIHJl" +
           "cHJlc2VudGluZy4gVGhlIG1hbmRhdG9yeSBFVVJhbmdlIFByb3BlcnR5IG9mIHRoZSBWYXJpYWJsZSBp" +
           "bmRpY2F0ZXMgdGhlIGxvd2VzdCBhbmQgaGlnaGVzdCB2YWx1ZSBhbmQgdGhlcmVieSBhbGxvd3MgdG8g" +
           "Y2FsY3VsYXRlIHRoZSBwZXJjZW50YWdlIHJlcHJlc2VudGVkIGJ5IHRoZSB2YWx1ZS4gVGhlIGxvd2Vz" +
           "dCB2YWx1ZSBpcyBpbnRlcnByZXRlZCBhcyAwIHBlcmNlbnQsIHRoZSBoaWdoZXN0IGlzIGludGVycHJl" +
           "dGVkIGFzIDEwMCBwZXJjZW50LgAvAQBACXoXAAAACv////8DA/////8BAAAAFWCJCgIAAAAAAAcAAABF" +
           "VVJhbmdlAQF7FwAuAER7FwAAAQB0A/////8BAf////8AAAAA";
        #endregion
        #endif
        #endregion

        #region Public Properties
        public BaseDataVariableState<LevelDisplayMode> DisplayMode
        {
            get => m_displayMode;

            set
            {
                if (!Object.ReferenceEquals(m_displayMode, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_displayMode = value;
            }
        }

        public AnalogItemState<float> LevelPercent
        {
            get => m_levelPercent;

            set
            {
                if (!Object.ReferenceEquals(m_levelPercent, value))
                {
                    ChangeMasks |= NodeStateChangeMasks.Children;
                }

                m_levelPercent = value;
            }
        }
        #endregion

        #region Overridden Methods
        public override void GetChildren(
            ISystemContext context,
            IList<BaseInstanceState> children)
        {
            if (m_displayMode != null)
            {
                children.Add(m_displayMode);
            }

            if (m_levelPercent != null)
            {
                children.Add(m_levelPercent);
            }

            base.GetChildren(context, children);
        }
            
        protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
        {
            if (Object.ReferenceEquals(m_displayMode, child))
            {
                m_displayMode = null;
                return;
            }

            if (Object.ReferenceEquals(m_levelPercent, child))
            {
                m_levelPercent = null;
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
                case UAModel.IA.BrowseNames.DisplayMode:
                {
                    if (createOrReplace)
                    {
                        if (DisplayMode == null)
                        {
                            if (replacement == null)
                            {
                                DisplayMode = new BaseDataVariableState<LevelDisplayMode>(this);
                            }
                            else
                            {
                                DisplayMode = (BaseDataVariableState<LevelDisplayMode>)replacement;
                            }
                        }
                    }

                    instance = DisplayMode;
                    break;
                }

                case UAModel.IA.BrowseNames.LevelPercent:
                {
                    if (createOrReplace)
                    {
                        if (LevelPercent == null)
                        {
                            if (replacement == null)
                            {
                                LevelPercent = new AnalogItemState<float>(this);
                            }
                            else
                            {
                                LevelPercent = (AnalogItemState<float>)replacement;
                            }
                        }
                    }

                    instance = LevelPercent;
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
        private BaseDataVariableState<LevelDisplayMode> m_displayMode;
        private AnalogItemState<float> m_levelPercent;
        #endregion
    }
    #endif
    #endregion

    #region StackRunningTypeState Class
    #if (!OPCUA_EXCLUDE_StackRunningTypeState)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public partial class StackRunningTypeState : BaseObjectState
    {
        #region Constructors
        public StackRunningTypeState(NodeState parent) : base(parent)
        {
        }

        protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
        {
            return Opc.Ua.NodeId.Create(UAModel.IA.ObjectTypes.StackRunningType, UAModel.IA.Namespaces.IA, namespaceUris);
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
           "AgAAAB8AAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0" +
           "aW9uLm9yZy9VQS9ESS//////BGCAAgEAAAABABgAAABTdGFja1J1bm5pbmdUeXBlSW5zdGFuY2UBAewD" +
           "AQHsA+wDAAD/////AAAAAA==";
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
}