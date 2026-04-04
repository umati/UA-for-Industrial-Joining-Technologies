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
    #region MaintenanceMethodEnum Enumeration
    #if (!OPCUA_EXCLUDE_MaintenanceMethodEnum)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [DataContract(Namespace = UAModel.AMB.Namespaces.AMB)]
    
    public enum MaintenanceMethodEnum
    {
        [EnumMember(Value = "Local_0")]
        Local = 0,

        [EnumMember(Value = "Remote_1")]
        Remote = 1,
    }

    #region MaintenanceMethodEnumCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfMaintenanceMethodEnum", Namespace = UAModel.AMB.Namespaces.AMB, ItemName = "MaintenanceMethodEnum")]
    public partial class MaintenanceMethodEnumCollection : List<MaintenanceMethodEnum>, ICloneable
    {
        #region Constructors
        public MaintenanceMethodEnumCollection() {}

        public MaintenanceMethodEnumCollection(int capacity) : base(capacity) {}

        public MaintenanceMethodEnumCollection(IEnumerable<MaintenanceMethodEnum> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator MaintenanceMethodEnumCollection(MaintenanceMethodEnum[] values)
        {
            if (values != null)
            {
                return new MaintenanceMethodEnumCollection(values);
            }

            return new MaintenanceMethodEnumCollection();
        }

        public static explicit operator MaintenanceMethodEnum[](MaintenanceMethodEnumCollection values)
        {
            if (values != null)
            {
                return values.ToArray();
            }

            return null;
        }
        #endregion

        #region ICloneable Methods
        public object Clone()
        {
            return (MaintenanceMethodEnumCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            MaintenanceMethodEnumCollection clone = new MaintenanceMethodEnumCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((MaintenanceMethodEnum)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region NameNodeIdDataType Class
    #if (!OPCUA_EXCLUDE_NameNodeIdDataType)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.AMB.Namespaces.AMB)]
    public partial class NameNodeIdDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public NameNodeIdDataType()
        {
            Initialize();
        }

        [OnDeserializing]
        private void Initialize(StreamingContext context)
        {
            Initialize();
        }

        private void Initialize()
        {
            m_name = null;
            m_nodeId = null;
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "Name", IsRequired = false, Order = 1)]
        public LocalizedText Name
        {
            get { return m_name;  }
            set { m_name = value; }
        }

        [DataMember(Name = "NodeId", IsRequired = false, Order = 2)]
        public NodeId NodeId
        {
            get { return m_nodeId;  }
            set { m_nodeId = value; }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.NameNodeIdDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.NameNodeIdDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.NameNodeIdDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => NodeId.Null;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.AMB.Namespaces.AMB);

            encoder.WriteLocalizedText("Name", Name);
            encoder.WriteNodeId("NodeId", NodeId);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.AMB.Namespaces.AMB);

            Name = decoder.ReadLocalizedText("Name");
            NodeId = decoder.ReadNodeId("NodeId");

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            NameNodeIdDataType value = encodeable as NameNodeIdDataType;

            if (value == null)
            {
                return false;
            }

            if (!Utils.IsEqual(m_name, value.m_name)) return false;
            if (!Utils.IsEqual(m_nodeId, value.m_nodeId)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (NameNodeIdDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            NameNodeIdDataType clone = (NameNodeIdDataType)base.MemberwiseClone();

            clone.m_name = (LocalizedText)Utils.Clone(this.m_name);
            clone.m_nodeId = (NodeId)Utils.Clone(this.m_nodeId);

            return clone;
        }
        #endregion

        #region Private Fields
        private LocalizedText m_name;
        private NodeId m_nodeId;
        #endregion
    }

    #region NameNodeIdDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfNameNodeIdDataType", Namespace = UAModel.AMB.Namespaces.AMB, ItemName = "NameNodeIdDataType")]
    public partial class NameNodeIdDataTypeCollection : List<NameNodeIdDataType>, ICloneable
    {
        #region Constructors
        public NameNodeIdDataTypeCollection() {}

        public NameNodeIdDataTypeCollection(int capacity) : base(capacity) {}

        public NameNodeIdDataTypeCollection(IEnumerable<NameNodeIdDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator NameNodeIdDataTypeCollection(NameNodeIdDataType[] values)
        {
            if (values != null)
            {
                return new NameNodeIdDataTypeCollection(values);
            }

            return new NameNodeIdDataTypeCollection();
        }

        public static explicit operator NameNodeIdDataType[](NameNodeIdDataTypeCollection values)
        {
            if (values != null)
            {
                return values.ToArray();
            }

            return null;
        }
        #endregion

        #region ICloneable Methods
        public object Clone()
        {
            return (NameNodeIdDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            NameNodeIdDataTypeCollection clone = new NameNodeIdDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((NameNodeIdDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region RootCauseDataType Class
    #if (!OPCUA_EXCLUDE_RootCauseDataType)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.AMB.Namespaces.AMB)]
    public partial class RootCauseDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public RootCauseDataType()
        {
            Initialize();
        }

        [OnDeserializing]
        private void Initialize(StreamingContext context)
        {
            Initialize();
        }

        private void Initialize()
        {
            m_rootCauseId = null;
            m_rootCause = null;
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "RootCauseId", IsRequired = false, Order = 1)]
        public NodeId RootCauseId
        {
            get { return m_rootCauseId;  }
            set { m_rootCauseId = value; }
        }

        [DataMember(Name = "RootCause", IsRequired = false, Order = 2)]
        public LocalizedText RootCause
        {
            get { return m_rootCause;  }
            set { m_rootCause = value; }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.RootCauseDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.RootCauseDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.RootCauseDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => NodeId.Null;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.AMB.Namespaces.AMB);

            encoder.WriteNodeId("RootCauseId", RootCauseId);
            encoder.WriteLocalizedText("RootCause", RootCause);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.AMB.Namespaces.AMB);

            RootCauseId = decoder.ReadNodeId("RootCauseId");
            RootCause = decoder.ReadLocalizedText("RootCause");

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            RootCauseDataType value = encodeable as RootCauseDataType;

            if (value == null)
            {
                return false;
            }

            if (!Utils.IsEqual(m_rootCauseId, value.m_rootCauseId)) return false;
            if (!Utils.IsEqual(m_rootCause, value.m_rootCause)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (RootCauseDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            RootCauseDataType clone = (RootCauseDataType)base.MemberwiseClone();

            clone.m_rootCauseId = (NodeId)Utils.Clone(this.m_rootCauseId);
            clone.m_rootCause = (LocalizedText)Utils.Clone(this.m_rootCause);

            return clone;
        }
        #endregion

        #region Private Fields
        private NodeId m_rootCauseId;
        private LocalizedText m_rootCause;
        #endregion
    }

    #region RootCauseDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfRootCauseDataType", Namespace = UAModel.AMB.Namespaces.AMB, ItemName = "RootCauseDataType")]
    public partial class RootCauseDataTypeCollection : List<RootCauseDataType>, ICloneable
    {
        #region Constructors
        public RootCauseDataTypeCollection() {}

        public RootCauseDataTypeCollection(int capacity) : base(capacity) {}

        public RootCauseDataTypeCollection(IEnumerable<RootCauseDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator RootCauseDataTypeCollection(RootCauseDataType[] values)
        {
            if (values != null)
            {
                return new RootCauseDataTypeCollection(values);
            }

            return new RootCauseDataTypeCollection();
        }

        public static explicit operator RootCauseDataType[](RootCauseDataTypeCollection values)
        {
            if (values != null)
            {
                return values.ToArray();
            }

            return null;
        }
        #endregion

        #region ICloneable Methods
        public object Clone()
        {
            return (RootCauseDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            RootCauseDataTypeCollection clone = new RootCauseDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((RootCauseDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion
}