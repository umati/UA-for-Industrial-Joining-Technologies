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
using System.Linq;
using System.Runtime.Serialization;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Xml;
using Opc.Ua;

#pragma warning disable CS1591 // Missing XML comment for publicly visible type or member
#pragma warning disable CA1515 // Consider making public types internal
#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1028 // Enum Storage should be Int32

namespace UAModel.DI;

#region DeviceHealthEnumeration Enumeration
#if (!OPCUA_EXCLUDE_DeviceHealthEnumeration)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[DataContract(Namespace = UAModel.DI.Namespaces.DIXsd)]

public enum DeviceHealthEnumeration
{
    [EnumMember(Value = "NORMAL_0")]
    NORMAL = 0,

    [EnumMember(Value = "FAILURE_1")]
    FAILURE = 1,

    [EnumMember(Value = "CHECK_FUNCTION_2")]
    CHECK_FUNCTION = 2,

    [EnumMember(Value = "OFF_SPEC_3")]
    OFF_SPEC = 3,

    [EnumMember(Value = "MAINTENANCE_REQUIRED_4")]
    MAINTENANCE_REQUIRED = 4,
}

#region DeviceHealthEnumerationCollection Class
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[CollectionDataContract(Name = "ListOfDeviceHealthEnumeration", Namespace = UAModel.DI.Namespaces.DIXsd, ItemName = "DeviceHealthEnumeration")]
public partial class DeviceHealthEnumerationCollection : List<DeviceHealthEnumeration>, ICloneable
{
    #region Constructors
    public DeviceHealthEnumerationCollection() { }

    public DeviceHealthEnumerationCollection(int capacity) : base(capacity) { }

    public DeviceHealthEnumerationCollection(IEnumerable<DeviceHealthEnumeration> collection) : base(collection) { }
    #endregion

    #region Static Operators
    public static implicit operator DeviceHealthEnumerationCollection(DeviceHealthEnumeration[] values)
    {
        if (values != null)
        {
            return new DeviceHealthEnumerationCollection(values);
        }

        return new DeviceHealthEnumerationCollection();
    }

    public static explicit operator DeviceHealthEnumeration[](DeviceHealthEnumerationCollection values)
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
        return (DeviceHealthEnumerationCollection)this.MemberwiseClone();
    }
    #endregion

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        DeviceHealthEnumerationCollection clone = new DeviceHealthEnumerationCollection(this.Count);

        for (int ii = 0; ii < this.Count; ii++)
        {
            clone.Add((DeviceHealthEnumeration)Utils.Clone(this[ii]));
        }

        return clone;
    }
}
#endregion
#endif
#endregion

#region FetchResultDataType Class
#if (!OPCUA_EXCLUDE_FetchResultDataType)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[DataContract(Namespace = UAModel.DI.Namespaces.DIXsd)]
public partial class FetchResultDataType : IEncodeable, IJsonEncodeable
{
    #region Constructors
    public FetchResultDataType()
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
    }
    #endregion

    #region Public Properties
    #endregion

    #region IEncodeable Members
    /// <summary cref="IEncodeable.TypeId" />
    public virtual ExpandedNodeId TypeId => DataTypeIds.FetchResultDataType;

    /// <summary cref="IEncodeable.BinaryEncodingId" />
    public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.FetchResultDataType_Encoding_DefaultBinary;

    /// <summary cref="IEncodeable.XmlEncodingId" />
    public virtual ExpandedNodeId XmlEncodingId => ObjectIds.FetchResultDataType_Encoding_DefaultXml;

    /// <summary cref="IJsonEncodeable.JsonEncodingId" />
    public virtual ExpandedNodeId JsonEncodingId => ObjectIds.FetchResultDataType_Encoding_DefaultJson;

    /// <summary cref="IEncodeable.Encode(IEncoder)" />
    public virtual void Encode(IEncoder encoder)
    {
        encoder.PushNamespace(UAModel.DI.Namespaces.DIXsd);


        encoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.Decode(IDecoder)" />
    public virtual void Decode(IDecoder decoder)
    {
        decoder.PushNamespace(UAModel.DI.Namespaces.DIXsd);


        decoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
    public virtual bool IsEqual(IEncodeable encodeable)
    {
        if (Object.ReferenceEquals(this, encodeable))
        {
            return true;
        }

        FetchResultDataType value = encodeable as FetchResultDataType;

        if (value == null)
        {
            return false;
        }


        return true;
    }

    /// <summary cref="ICloneable.Clone" />
    public virtual object Clone()
    {
        return (FetchResultDataType)this.MemberwiseClone();
    }

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        FetchResultDataType clone = (FetchResultDataType)base.MemberwiseClone();


        return clone;
    }
    #endregion

    #region Private Fields
    #endregion
}

#region FetchResultDataTypeCollection Class
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[CollectionDataContract(Name = "ListOfFetchResultDataType", Namespace = UAModel.DI.Namespaces.DIXsd, ItemName = "FetchResultDataType")]
public partial class FetchResultDataTypeCollection : List<FetchResultDataType>, ICloneable
{
    #region Constructors
    public FetchResultDataTypeCollection() { }

    public FetchResultDataTypeCollection(int capacity) : base(capacity) { }

    public FetchResultDataTypeCollection(IEnumerable<FetchResultDataType> collection) : base(collection) { }
    #endregion

    #region Static Operators
    public static implicit operator FetchResultDataTypeCollection(FetchResultDataType[] values)
    {
        if (values != null)
        {
            return new FetchResultDataTypeCollection(values);
        }

        return new FetchResultDataTypeCollection();
    }

    public static explicit operator FetchResultDataType[](FetchResultDataTypeCollection values)
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
        return (FetchResultDataTypeCollection)this.MemberwiseClone();
    }
    #endregion

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        FetchResultDataTypeCollection clone = new FetchResultDataTypeCollection(this.Count);

        for (int ii = 0; ii < this.Count; ii++)
        {
            clone.Add((FetchResultDataType)Utils.Clone(this[ii]));
        }

        return clone;
    }
}
#endregion
#endif
#endregion

#region TransferResultErrorDataType Class
#if (!OPCUA_EXCLUDE_TransferResultErrorDataType)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[DataContract(Namespace = UAModel.DI.Namespaces.DIXsd)]
public partial class TransferResultErrorDataType : UAModel.DI.FetchResultDataType
{
    #region Constructors
    public TransferResultErrorDataType()
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
        m_status = (int)0;
        m_diagnostics = null;
    }
    #endregion

    #region Public Properties
    [DataMember(Name = "Status", IsRequired = false, Order = 1)]
    public int Status
    {
        get { return m_status; }
        set { m_status = value; }
    }

    [DataMember(Name = "Diagnostics", IsRequired = false, Order = 2)]
    public DiagnosticInfo Diagnostics
    {
        get { return m_diagnostics; }
        set { m_diagnostics = value; }
    }
    #endregion

    #region IEncodeable Members
    /// <summary cref="IEncodeable.TypeId" />
    public override ExpandedNodeId TypeId => DataTypeIds.TransferResultErrorDataType;

    /// <summary cref="IEncodeable.BinaryEncodingId" />
    public override ExpandedNodeId BinaryEncodingId => ObjectIds.TransferResultErrorDataType_Encoding_DefaultBinary;

    /// <summary cref="IEncodeable.XmlEncodingId" />
    public override ExpandedNodeId XmlEncodingId => ObjectIds.TransferResultErrorDataType_Encoding_DefaultXml;

    /// <summary cref="IJsonEncodeable.JsonEncodingId" />
    public override ExpandedNodeId JsonEncodingId => ObjectIds.TransferResultErrorDataType_Encoding_DefaultJson;

    /// <summary cref="IEncodeable.Encode(IEncoder)" />
    public override void Encode(IEncoder encoder)
    {
        base.Encode(encoder);

        encoder.PushNamespace(UAModel.DI.Namespaces.DIXsd);

        encoder.WriteInt32("Status", Status);
        encoder.WriteDiagnosticInfo("Diagnostics", Diagnostics);

        encoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.Decode(IDecoder)" />
    public override void Decode(IDecoder decoder)
    {
        base.Decode(decoder);

        decoder.PushNamespace(UAModel.DI.Namespaces.DIXsd);

        Status = decoder.ReadInt32("Status");
        Diagnostics = decoder.ReadDiagnosticInfo("Diagnostics");

        decoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
    public override bool IsEqual(IEncodeable encodeable)
    {
        if (Object.ReferenceEquals(this, encodeable))
        {
            return true;
        }

        TransferResultErrorDataType value = encodeable as TransferResultErrorDataType;

        if (value == null)
        {
            return false;
        }

        if (!Utils.IsEqual(m_status, value.m_status)) return false;
        if (!Utils.IsEqual(m_diagnostics, value.m_diagnostics)) return false;

        return base.IsEqual(encodeable);
    }

    /// <summary cref="ICloneable.Clone" />
    public override object Clone()
    {
        return (TransferResultErrorDataType)this.MemberwiseClone();
    }

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        TransferResultErrorDataType clone = (TransferResultErrorDataType)base.MemberwiseClone();

        clone.m_status = (int)Utils.Clone(this.m_status);
        clone.m_diagnostics = (DiagnosticInfo)Utils.Clone(this.m_diagnostics);

        return clone;
    }
    #endregion

    #region Private Fields
    private int m_status;
    private DiagnosticInfo m_diagnostics;
    #endregion
}

#region TransferResultErrorDataTypeCollection Class
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[CollectionDataContract(Name = "ListOfTransferResultErrorDataType", Namespace = UAModel.DI.Namespaces.DIXsd, ItemName = "TransferResultErrorDataType")]
public partial class TransferResultErrorDataTypeCollection : List<TransferResultErrorDataType>, ICloneable
{
    #region Constructors
    public TransferResultErrorDataTypeCollection() { }

    public TransferResultErrorDataTypeCollection(int capacity) : base(capacity) { }

    public TransferResultErrorDataTypeCollection(IEnumerable<TransferResultErrorDataType> collection) : base(collection) { }
    #endregion

    #region Static Operators
    public static implicit operator TransferResultErrorDataTypeCollection(TransferResultErrorDataType[] values)
    {
        if (values != null)
        {
            return new TransferResultErrorDataTypeCollection(values);
        }

        return new TransferResultErrorDataTypeCollection();
    }

    public static explicit operator TransferResultErrorDataType[](TransferResultErrorDataTypeCollection values)
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
        return (TransferResultErrorDataTypeCollection)this.MemberwiseClone();
    }
    #endregion

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        TransferResultErrorDataTypeCollection clone = new TransferResultErrorDataTypeCollection(this.Count);

        for (int ii = 0; ii < this.Count; ii++)
        {
            clone.Add((TransferResultErrorDataType)Utils.Clone(this[ii]));
        }

        return clone;
    }
}
#endregion
#endif
#endregion

#region TransferResultDataDataType Class
#if (!OPCUA_EXCLUDE_TransferResultDataDataType)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[DataContract(Namespace = UAModel.DI.Namespaces.DIXsd)]
public partial class TransferResultDataDataType : UAModel.DI.FetchResultDataType
{
    #region Constructors
    public TransferResultDataDataType()
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
        m_sequenceNumber = (int)0;
        m_endOfResults = true;
        m_parameterDefs = new ParameterResultDataTypeCollection();
    }
    #endregion

    #region Public Properties
    [DataMember(Name = "SequenceNumber", IsRequired = false, Order = 1)]
    public int SequenceNumber
    {
        get { return m_sequenceNumber; }
        set { m_sequenceNumber = value; }
    }

    [DataMember(Name = "EndOfResults", IsRequired = false, Order = 2)]
    public bool EndOfResults
    {
        get { return m_endOfResults; }
        set { m_endOfResults = value; }
    }

    /// <remarks />
    [DataMember(Name = "ParameterDefs", IsRequired = false, Order = 3)]
    public ParameterResultDataTypeCollection ParameterDefs
    {
        get
        {
            return m_parameterDefs;
        }

        set
        {
            m_parameterDefs = value;

            if (value == null)
            {
                m_parameterDefs = new ParameterResultDataTypeCollection();
            }
        }
    }
    #endregion

    #region IEncodeable Members
    /// <summary cref="IEncodeable.TypeId" />
    public override ExpandedNodeId TypeId => DataTypeIds.TransferResultDataDataType;

    /// <summary cref="IEncodeable.BinaryEncodingId" />
    public override ExpandedNodeId BinaryEncodingId => ObjectIds.TransferResultDataDataType_Encoding_DefaultBinary;

    /// <summary cref="IEncodeable.XmlEncodingId" />
    public override ExpandedNodeId XmlEncodingId => ObjectIds.TransferResultDataDataType_Encoding_DefaultXml;

    /// <summary cref="IJsonEncodeable.JsonEncodingId" />
    public override ExpandedNodeId JsonEncodingId => ObjectIds.TransferResultDataDataType_Encoding_DefaultJson;

    /// <summary cref="IEncodeable.Encode(IEncoder)" />
    public override void Encode(IEncoder encoder)
    {
        base.Encode(encoder);

        encoder.PushNamespace(UAModel.DI.Namespaces.DIXsd);

        encoder.WriteInt32("SequenceNumber", SequenceNumber);
        encoder.WriteBoolean("EndOfResults", EndOfResults);
        encoder.WriteEncodeableArray("ParameterDefs", ParameterDefs.ToArray(), typeof(ParameterResultDataType));

        encoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.Decode(IDecoder)" />
    public override void Decode(IDecoder decoder)
    {
        base.Decode(decoder);

        decoder.PushNamespace(UAModel.DI.Namespaces.DIXsd);

        SequenceNumber = decoder.ReadInt32("SequenceNumber");
        EndOfResults = decoder.ReadBoolean("EndOfResults");
        ParameterDefs = (ParameterResultDataTypeCollection)decoder.ReadEncodeableArray("ParameterDefs", typeof(ParameterResultDataType));

        decoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
    public override bool IsEqual(IEncodeable encodeable)
    {
        if (Object.ReferenceEquals(this, encodeable))
        {
            return true;
        }

        TransferResultDataDataType value = encodeable as TransferResultDataDataType;

        if (value == null)
        {
            return false;
        }

        if (!Utils.IsEqual(m_sequenceNumber, value.m_sequenceNumber)) return false;
        if (!Utils.IsEqual(m_endOfResults, value.m_endOfResults)) return false;
        if (!Utils.IsEqual(m_parameterDefs, value.m_parameterDefs)) return false;

        return base.IsEqual(encodeable);
    }

    /// <summary cref="ICloneable.Clone" />
    public override object Clone()
    {
        return (TransferResultDataDataType)this.MemberwiseClone();
    }

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        TransferResultDataDataType clone = (TransferResultDataDataType)base.MemberwiseClone();

        clone.m_sequenceNumber = (int)Utils.Clone(this.m_sequenceNumber);
        clone.m_endOfResults = (bool)Utils.Clone(this.m_endOfResults);
        clone.m_parameterDefs = (ParameterResultDataTypeCollection)Utils.Clone(this.m_parameterDefs);

        return clone;
    }
    #endregion

    #region Private Fields
    private int m_sequenceNumber;
    private bool m_endOfResults;
    private ParameterResultDataTypeCollection m_parameterDefs;
    #endregion
}

#region TransferResultDataDataTypeCollection Class
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[CollectionDataContract(Name = "ListOfTransferResultDataDataType", Namespace = UAModel.DI.Namespaces.DIXsd, ItemName = "TransferResultDataDataType")]
public partial class TransferResultDataDataTypeCollection : List<TransferResultDataDataType>, ICloneable
{
    #region Constructors
    public TransferResultDataDataTypeCollection() { }

    public TransferResultDataDataTypeCollection(int capacity) : base(capacity) { }

    public TransferResultDataDataTypeCollection(IEnumerable<TransferResultDataDataType> collection) : base(collection) { }
    #endregion

    #region Static Operators
    public static implicit operator TransferResultDataDataTypeCollection(TransferResultDataDataType[] values)
    {
        if (values != null)
        {
            return new TransferResultDataDataTypeCollection(values);
        }

        return new TransferResultDataDataTypeCollection();
    }

    public static explicit operator TransferResultDataDataType[](TransferResultDataDataTypeCollection values)
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
        return (TransferResultDataDataTypeCollection)this.MemberwiseClone();
    }
    #endregion

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        TransferResultDataDataTypeCollection clone = new TransferResultDataDataTypeCollection(this.Count);

        for (int ii = 0; ii < this.Count; ii++)
        {
            clone.Add((TransferResultDataDataType)Utils.Clone(this[ii]));
        }

        return clone;
    }
}
#endregion
#endif
#endregion

#region ParameterResultDataType Class
#if (!OPCUA_EXCLUDE_ParameterResultDataType)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[DataContract(Namespace = UAModel.DI.Namespaces.DIXsd)]
public partial class ParameterResultDataType : IEncodeable, IJsonEncodeable
{
    #region Constructors
    public ParameterResultDataType()
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
        m_nodePath = new QualifiedNameCollection();
        m_statusCode = StatusCodes.Good;
        m_diagnostics = null;
    }
    #endregion

    #region Public Properties
    /// <remarks />
    [DataMember(Name = "NodePath", IsRequired = false, Order = 1)]
    public QualifiedNameCollection NodePath
    {
        get
        {
            return m_nodePath;
        }

        set
        {
            m_nodePath = value;

            if (value == null)
            {
                m_nodePath = new QualifiedNameCollection();
            }
        }
    }

    [DataMember(Name = "StatusCode", IsRequired = false, Order = 2)]
    public StatusCode StatusCode
    {
        get { return m_statusCode; }
        set { m_statusCode = value; }
    }

    [DataMember(Name = "Diagnostics", IsRequired = false, Order = 3)]
    public DiagnosticInfo Diagnostics
    {
        get { return m_diagnostics; }
        set { m_diagnostics = value; }
    }
    #endregion

    #region IEncodeable Members
    /// <summary cref="IEncodeable.TypeId" />
    public virtual ExpandedNodeId TypeId => DataTypeIds.ParameterResultDataType;

    /// <summary cref="IEncodeable.BinaryEncodingId" />
    public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.ParameterResultDataType_Encoding_DefaultBinary;

    /// <summary cref="IEncodeable.XmlEncodingId" />
    public virtual ExpandedNodeId XmlEncodingId => ObjectIds.ParameterResultDataType_Encoding_DefaultXml;

    /// <summary cref="IJsonEncodeable.JsonEncodingId" />
    public virtual ExpandedNodeId JsonEncodingId => ObjectIds.ParameterResultDataType_Encoding_DefaultJson;

    /// <summary cref="IEncodeable.Encode(IEncoder)" />
    public virtual void Encode(IEncoder encoder)
    {
        encoder.PushNamespace(UAModel.DI.Namespaces.DIXsd);

        encoder.WriteQualifiedNameArray("NodePath", NodePath);
        encoder.WriteStatusCode("StatusCode", StatusCode);
        encoder.WriteDiagnosticInfo("Diagnostics", Diagnostics);

        encoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.Decode(IDecoder)" />
    public virtual void Decode(IDecoder decoder)
    {
        decoder.PushNamespace(UAModel.DI.Namespaces.DIXsd);

        NodePath = decoder.ReadQualifiedNameArray("NodePath");
        StatusCode = decoder.ReadStatusCode("StatusCode");
        Diagnostics = decoder.ReadDiagnosticInfo("Diagnostics");

        decoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
    public virtual bool IsEqual(IEncodeable encodeable)
    {
        if (Object.ReferenceEquals(this, encodeable))
        {
            return true;
        }

        ParameterResultDataType value = encodeable as ParameterResultDataType;

        if (value == null)
        {
            return false;
        }

        if (!Utils.IsEqual(m_nodePath, value.m_nodePath)) return false;
        if (!Utils.IsEqual(m_statusCode, value.m_statusCode)) return false;
        if (!Utils.IsEqual(m_diagnostics, value.m_diagnostics)) return false;

        return true;
    }

    /// <summary cref="ICloneable.Clone" />
    public virtual object Clone()
    {
        return (ParameterResultDataType)this.MemberwiseClone();
    }

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        ParameterResultDataType clone = (ParameterResultDataType)base.MemberwiseClone();

        clone.m_nodePath = (QualifiedNameCollection)Utils.Clone(this.m_nodePath);
        clone.m_statusCode = (StatusCode)Utils.Clone(this.m_statusCode);
        clone.m_diagnostics = (DiagnosticInfo)Utils.Clone(this.m_diagnostics);

        return clone;
    }
    #endregion

    #region Private Fields
    private QualifiedNameCollection m_nodePath;
    private StatusCode m_statusCode;
    private DiagnosticInfo m_diagnostics;
    #endregion
}

#region ParameterResultDataTypeCollection Class
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[CollectionDataContract(Name = "ListOfParameterResultDataType", Namespace = UAModel.DI.Namespaces.DIXsd, ItemName = "ParameterResultDataType")]
public partial class ParameterResultDataTypeCollection : List<ParameterResultDataType>, ICloneable
{
    #region Constructors
    public ParameterResultDataTypeCollection() { }

    public ParameterResultDataTypeCollection(int capacity) : base(capacity) { }

    public ParameterResultDataTypeCollection(IEnumerable<ParameterResultDataType> collection) : base(collection) { }
    #endregion

    #region Static Operators
    public static implicit operator ParameterResultDataTypeCollection(ParameterResultDataType[] values)
    {
        if (values != null)
        {
            return new ParameterResultDataTypeCollection(values);
        }

        return new ParameterResultDataTypeCollection();
    }

    public static explicit operator ParameterResultDataType[](ParameterResultDataTypeCollection values)
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
        return (ParameterResultDataTypeCollection)this.MemberwiseClone();
    }
    #endregion

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        ParameterResultDataTypeCollection clone = new ParameterResultDataTypeCollection(this.Count);

        for (int ii = 0; ii < this.Count; ii++)
        {
            clone.Add((ParameterResultDataType)Utils.Clone(this[ii]));
        }

        return clone;
    }
}
#endregion
#endif
#endregion

#region SoftwareVersionFileType Enumeration
#if (!OPCUA_EXCLUDE_SoftwareVersionFileType)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[DataContract(Namespace = UAModel.DI.Namespaces.DIXsd)]

public enum SoftwareVersionFileType
{
    [EnumMember(Value = "Current_0")]
    Current = 0,

    [EnumMember(Value = "Pending_1")]
    Pending = 1,

    [EnumMember(Value = "Fallback_2")]
    Fallback = 2,
}

#region SoftwareVersionFileTypeCollection Class
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[CollectionDataContract(Name = "ListOfSoftwareVersionFileType", Namespace = UAModel.DI.Namespaces.DIXsd, ItemName = "SoftwareVersionFileType")]
public partial class SoftwareVersionFileTypeCollection : List<SoftwareVersionFileType>, ICloneable
{
    #region Constructors
    public SoftwareVersionFileTypeCollection() { }

    public SoftwareVersionFileTypeCollection(int capacity) : base(capacity) { }

    public SoftwareVersionFileTypeCollection(IEnumerable<SoftwareVersionFileType> collection) : base(collection) { }
    #endregion

    #region Static Operators
    public static implicit operator SoftwareVersionFileTypeCollection(SoftwareVersionFileType[] values)
    {
        if (values != null)
        {
            return new SoftwareVersionFileTypeCollection(values);
        }

        return new SoftwareVersionFileTypeCollection();
    }

    public static explicit operator SoftwareVersionFileType[](SoftwareVersionFileTypeCollection values)
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
        return (SoftwareVersionFileTypeCollection)this.MemberwiseClone();
    }
    #endregion

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        SoftwareVersionFileTypeCollection clone = new SoftwareVersionFileTypeCollection(this.Count);

        for (int ii = 0; ii < this.Count; ii++)
        {
            clone.Add((SoftwareVersionFileType)Utils.Clone(this[ii]));
        }

        return clone;
    }
}
#endregion
#endif
#endregion

#region UpdateBehavior Enumeration
#if (!OPCUA_EXCLUDE_UpdateBehavior)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[DataContract(Namespace = UAModel.DI.Namespaces.DIXsd)]
[Flags]
public enum UpdateBehavior : UInt32
{
    [EnumMember(Value = "None_0")]
    None = 0,

    [EnumMember(Value = "KeepsParameters_1")]
    KeepsParameters = 1,

    [EnumMember(Value = "WillDisconnect_2")]
    WillDisconnect = 2,

    [EnumMember(Value = "RequiresPowerCycle_4")]
    RequiresPowerCycle = 4,

    [EnumMember(Value = "WillReboot_8")]
    WillReboot = 8,

    [EnumMember(Value = "NeedsPreparation_16")]
    NeedsPreparation = 16,
}

#region UpdateBehaviorCollection Class
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[CollectionDataContract(Name = "ListOfUpdateBehavior", Namespace = UAModel.DI.Namespaces.DIXsd, ItemName = "UpdateBehavior")]
public partial class UpdateBehaviorCollection : List<UpdateBehavior>, ICloneable
{
    #region Constructors
    public UpdateBehaviorCollection() { }

    public UpdateBehaviorCollection(int capacity) : base(capacity) { }

    public UpdateBehaviorCollection(IEnumerable<UpdateBehavior> collection) : base(collection) { }
    #endregion

    #region Static Operators
    public static implicit operator UpdateBehaviorCollection(UpdateBehavior[] values)
    {
        if (values != null)
        {
            return new UpdateBehaviorCollection(values);
        }

        return new UpdateBehaviorCollection();
    }

    public static explicit operator UpdateBehavior[](UpdateBehaviorCollection values)
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
        return (UpdateBehaviorCollection)this.MemberwiseClone();
    }
    #endregion

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        UpdateBehaviorCollection clone = new UpdateBehaviorCollection(this.Count);

        for (int ii = 0; ii < this.Count; ii++)
        {
            clone.Add((UpdateBehavior)Utils.Clone(this[ii]));
        }

        return clone;
    }
}
#endregion
#endif
#endregion
