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

namespace UAModel.MachineryResult;

#region ResultEvaluationEnum Enumeration
#if (!OPCUA_EXCLUDE_ResultEvaluationEnum)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[DataContract(Namespace = UAModel.MachineryResult.Namespaces.MachineryResult)]

public enum ResultEvaluationEnum
{
    [EnumMember(Value = "Undefined_0")]
    Undefined = 0,

    [EnumMember(Value = "OK_1")]
    OK = 1,

    [EnumMember(Value = "NotOK_2")]
    NotOK = 2,

    [EnumMember(Value = "NotDecidable_3")]
    NotDecidable = 3,
}

#region ResultEvaluationEnumCollection Class
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[CollectionDataContract(Name = "ListOfResultEvaluationEnum", Namespace = UAModel.MachineryResult.Namespaces.MachineryResult, ItemName = "ResultEvaluationEnum")]
public partial class ResultEvaluationEnumCollection : List<ResultEvaluationEnum>, ICloneable
{
    #region Constructors
    public ResultEvaluationEnumCollection() { }

    public ResultEvaluationEnumCollection(int capacity) : base(capacity) { }

    public ResultEvaluationEnumCollection(IEnumerable<ResultEvaluationEnum> collection) : base(collection) { }
    #endregion

    #region Static Operators
    public static implicit operator ResultEvaluationEnumCollection(ResultEvaluationEnum[] values)
    {
        if (values != null)
        {
            return new ResultEvaluationEnumCollection(values);
        }

        return new ResultEvaluationEnumCollection();
    }

    public static explicit operator ResultEvaluationEnum[](ResultEvaluationEnumCollection values)
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
        return (ResultEvaluationEnumCollection)this.MemberwiseClone();
    }
    #endregion

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        ResultEvaluationEnumCollection clone = new ResultEvaluationEnumCollection(this.Count);

        for (int ii = 0; ii < this.Count; ii++)
        {
            clone.Add((ResultEvaluationEnum)Utils.Clone(this[ii]));
        }

        return clone;
    }
}
#endregion
#endif
#endregion

#region BaseResultTransferOptionsDataType Class
#if (!OPCUA_EXCLUDE_BaseResultTransferOptionsDataType)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[DataContract(Namespace = UAModel.MachineryResult.Namespaces.MachineryResult)]
public partial class BaseResultTransferOptionsDataType : IEncodeable, IJsonEncodeable
{
    #region Constructors
    public BaseResultTransferOptionsDataType()
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
        m_resultId = null;
    }
    #endregion

    #region Public Properties
    [DataMember(Name = "ResultId", IsRequired = false, Order = 1)]
    public string ResultId
    {
        get { return m_resultId; }
        set { m_resultId = value; }
    }
    #endregion

    #region IEncodeable Members
    /// <summary cref="IEncodeable.TypeId" />
    public virtual ExpandedNodeId TypeId => DataTypeIds.BaseResultTransferOptionsDataType;

    /// <summary cref="IEncodeable.BinaryEncodingId" />
    public virtual ExpandedNodeId BinaryEncodingId => NodeId.Null;

    /// <summary cref="IEncodeable.XmlEncodingId" />
    public virtual ExpandedNodeId XmlEncodingId => NodeId.Null;

    /// <summary cref="IJsonEncodeable.JsonEncodingId" />
    public virtual ExpandedNodeId JsonEncodingId => NodeId.Null;

    /// <summary cref="IEncodeable.Encode(IEncoder)" />
    public virtual void Encode(IEncoder encoder)
    {
        encoder.PushNamespace(UAModel.MachineryResult.Namespaces.MachineryResult);

        encoder.WriteString("ResultId", ResultId);

        encoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.Decode(IDecoder)" />
    public virtual void Decode(IDecoder decoder)
    {
        decoder.PushNamespace(UAModel.MachineryResult.Namespaces.MachineryResult);

        ResultId = decoder.ReadString("ResultId");

        decoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
    public virtual bool IsEqual(IEncodeable encodeable)
    {
        if (Object.ReferenceEquals(this, encodeable))
        {
            return true;
        }

        BaseResultTransferOptionsDataType value = encodeable as BaseResultTransferOptionsDataType;

        if (value == null)
        {
            return false;
        }

        if (!Utils.IsEqual(m_resultId, value.m_resultId)) return false;

        return true;
    }

    /// <summary cref="ICloneable.Clone" />
    public virtual object Clone()
    {
        return (BaseResultTransferOptionsDataType)this.MemberwiseClone();
    }

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        BaseResultTransferOptionsDataType clone = (BaseResultTransferOptionsDataType)base.MemberwiseClone();

        clone.m_resultId = (string)Utils.Clone(this.m_resultId);

        return clone;
    }
    #endregion

    #region Private Fields
    private string m_resultId;
    #endregion
}

#region BaseResultTransferOptionsDataTypeCollection Class
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[CollectionDataContract(Name = "ListOfBaseResultTransferOptionsDataType", Namespace = UAModel.MachineryResult.Namespaces.MachineryResult, ItemName = "BaseResultTransferOptionsDataType")]
public partial class BaseResultTransferOptionsDataTypeCollection : List<BaseResultTransferOptionsDataType>, ICloneable
{
    #region Constructors
    public BaseResultTransferOptionsDataTypeCollection() { }

    public BaseResultTransferOptionsDataTypeCollection(int capacity) : base(capacity) { }

    public BaseResultTransferOptionsDataTypeCollection(IEnumerable<BaseResultTransferOptionsDataType> collection) : base(collection) { }
    #endregion

    #region Static Operators
    public static implicit operator BaseResultTransferOptionsDataTypeCollection(BaseResultTransferOptionsDataType[] values)
    {
        if (values != null)
        {
            return new BaseResultTransferOptionsDataTypeCollection(values);
        }

        return new BaseResultTransferOptionsDataTypeCollection();
    }

    public static explicit operator BaseResultTransferOptionsDataType[](BaseResultTransferOptionsDataTypeCollection values)
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
        return (BaseResultTransferOptionsDataTypeCollection)this.MemberwiseClone();
    }
    #endregion

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        BaseResultTransferOptionsDataTypeCollection clone = new BaseResultTransferOptionsDataTypeCollection(this.Count);

        for (int ii = 0; ii < this.Count; ii++)
        {
            clone.Add((BaseResultTransferOptionsDataType)Utils.Clone(this[ii]));
        }

        return clone;
    }
}
#endregion
#endif
#endregion

#region ResultTransferOptionsDataType Class
#if (!OPCUA_EXCLUDE_ResultTransferOptionsDataType)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[DataContract(Namespace = UAModel.MachineryResult.Namespaces.MachineryResult)]
public partial class ResultTransferOptionsDataType : UAModel.MachineryResult.BaseResultTransferOptionsDataType
{
    #region Constructors
    public ResultTransferOptionsDataType()
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
    public override ExpandedNodeId TypeId => DataTypeIds.ResultTransferOptionsDataType;

    /// <summary cref="IEncodeable.BinaryEncodingId" />
    public override ExpandedNodeId BinaryEncodingId => ObjectIds.ResultTransferOptionsDataType_Encoding_DefaultBinary;

    /// <summary cref="IEncodeable.XmlEncodingId" />
    public override ExpandedNodeId XmlEncodingId => ObjectIds.ResultTransferOptionsDataType_Encoding_DefaultXml;

    /// <summary cref="IJsonEncodeable.JsonEncodingId" />
    public override ExpandedNodeId JsonEncodingId => ObjectIds.ResultTransferOptionsDataType_Encoding_DefaultJson;

    /// <summary cref="IEncodeable.Encode(IEncoder)" />
    public override void Encode(IEncoder encoder)
    {
        base.Encode(encoder);

        encoder.PushNamespace(UAModel.MachineryResult.Namespaces.MachineryResult);


        encoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.Decode(IDecoder)" />
    public override void Decode(IDecoder decoder)
    {
        base.Decode(decoder);

        decoder.PushNamespace(UAModel.MachineryResult.Namespaces.MachineryResult);


        decoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
    public override bool IsEqual(IEncodeable encodeable)
    {
        if (Object.ReferenceEquals(this, encodeable))
        {
            return true;
        }

        ResultTransferOptionsDataType value = encodeable as ResultTransferOptionsDataType;

        if (value == null)
        {
            return false;
        }


        return base.IsEqual(encodeable);
    }

    /// <summary cref="ICloneable.Clone" />
    public override object Clone()
    {
        return (ResultTransferOptionsDataType)this.MemberwiseClone();
    }

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        ResultTransferOptionsDataType clone = (ResultTransferOptionsDataType)base.MemberwiseClone();


        return clone;
    }
    #endregion

    #region Private Fields
    #endregion
}

#region ResultTransferOptionsDataTypeCollection Class
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[CollectionDataContract(Name = "ListOfResultTransferOptionsDataType", Namespace = UAModel.MachineryResult.Namespaces.MachineryResult, ItemName = "ResultTransferOptionsDataType")]
public partial class ResultTransferOptionsDataTypeCollection : List<ResultTransferOptionsDataType>, ICloneable
{
    #region Constructors
    public ResultTransferOptionsDataTypeCollection() { }

    public ResultTransferOptionsDataTypeCollection(int capacity) : base(capacity) { }

    public ResultTransferOptionsDataTypeCollection(IEnumerable<ResultTransferOptionsDataType> collection) : base(collection) { }
    #endregion

    #region Static Operators
    public static implicit operator ResultTransferOptionsDataTypeCollection(ResultTransferOptionsDataType[] values)
    {
        if (values != null)
        {
            return new ResultTransferOptionsDataTypeCollection(values);
        }

        return new ResultTransferOptionsDataTypeCollection();
    }

    public static explicit operator ResultTransferOptionsDataType[](ResultTransferOptionsDataTypeCollection values)
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
        return (ResultTransferOptionsDataTypeCollection)this.MemberwiseClone();
    }
    #endregion

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        ResultTransferOptionsDataTypeCollection clone = new ResultTransferOptionsDataTypeCollection(this.Count);

        for (int ii = 0; ii < this.Count; ii++)
        {
            clone.Add((ResultTransferOptionsDataType)Utils.Clone(this[ii]));
        }

        return clone;
    }
}
#endregion
#endif
#endregion

#region ProcessingTimesDataType Class
#if (!OPCUA_EXCLUDE_ProcessingTimesDataType)
/// <exclude />
[Flags]
public enum ProcessingTimesDataTypeFields : uint
{
    None = 0,
    AcquisitionDuration = 0x1,
    ProcessingDuration = 0x2,
}

/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[DataContract(Namespace = UAModel.MachineryResult.Namespaces.MachineryResult)]
public partial class ProcessingTimesDataType : IEncodeable, IJsonEncodeable
{
    #region Constructors
    public ProcessingTimesDataType()
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
        EncodingMask = (uint)ProcessingTimesDataTypeFields.None;
        m_startTime = DateTime.MinValue;
        m_endTime = DateTime.MinValue;
        m_acquisitionDuration = (double)0;
        m_processingDuration = (double)0;
    }
    #endregion

    #region Public Properties
    [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
    public virtual uint EncodingMask { get; set; }

    [DataMember(Name = "StartTime", IsRequired = false, Order = 1)]
    public DateTime StartTime
    {
        get { return m_startTime; }
        set { m_startTime = value; }
    }

    [DataMember(Name = "EndTime", IsRequired = false, Order = 2)]
    public DateTime EndTime
    {
        get { return m_endTime; }
        set { m_endTime = value; }
    }

    [DataMember(Name = "AcquisitionDuration", IsRequired = false, Order = 3)]
    public double AcquisitionDuration
    {
        get { return m_acquisitionDuration; }
        set { m_acquisitionDuration = value; }
    }

    [DataMember(Name = "ProcessingDuration", IsRequired = false, Order = 4)]
    public double ProcessingDuration
    {
        get { return m_processingDuration; }
        set { m_processingDuration = value; }
    }
    #endregion

    #region IEncodeable Members
    /// <summary cref="IEncodeable.TypeId" />
    public virtual ExpandedNodeId TypeId => DataTypeIds.ProcessingTimesDataType;

    /// <summary cref="IEncodeable.BinaryEncodingId" />
    public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.ProcessingTimesDataType_Encoding_DefaultBinary;

    /// <summary cref="IEncodeable.XmlEncodingId" />
    public virtual ExpandedNodeId XmlEncodingId => ObjectIds.ProcessingTimesDataType_Encoding_DefaultXml;

    /// <summary cref="IJsonEncodeable.JsonEncodingId" />
    public virtual ExpandedNodeId JsonEncodingId => ObjectIds.ProcessingTimesDataType_Encoding_DefaultJson;

    /// <summary cref="IEncodeable.Encode(IEncoder)" />
    public virtual void Encode(IEncoder encoder)
    {
        encoder.PushNamespace(UAModel.MachineryResult.Namespaces.MachineryResult);
        encoder.WriteEncodingMask((uint)EncodingMask);

        encoder.WriteDateTime("StartTime", StartTime);
        encoder.WriteDateTime("EndTime", EndTime);
        if ((EncodingMask & (uint)ProcessingTimesDataTypeFields.AcquisitionDuration) != 0) encoder.WriteDouble("AcquisitionDuration", AcquisitionDuration);
        if ((EncodingMask & (uint)ProcessingTimesDataTypeFields.ProcessingDuration) != 0) encoder.WriteDouble("ProcessingDuration", ProcessingDuration);

        encoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.Decode(IDecoder)" />
    public virtual void Decode(IDecoder decoder)
    {
        decoder.PushNamespace(UAModel.MachineryResult.Namespaces.MachineryResult);

        EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

        StartTime = decoder.ReadDateTime("StartTime");
        EndTime = decoder.ReadDateTime("EndTime");
        if ((EncodingMask & (uint)ProcessingTimesDataTypeFields.AcquisitionDuration) != 0) AcquisitionDuration = decoder.ReadDouble("AcquisitionDuration");
        if ((EncodingMask & (uint)ProcessingTimesDataTypeFields.ProcessingDuration) != 0) ProcessingDuration = decoder.ReadDouble("ProcessingDuration");

        decoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
    public virtual bool IsEqual(IEncodeable encodeable)
    {
        if (Object.ReferenceEquals(this, encodeable))
        {
            return true;
        }

        ProcessingTimesDataType value = encodeable as ProcessingTimesDataType;

        if (value == null)
        {
            return false;
        }

        if (value.EncodingMask != this.EncodingMask) return false;

        if (!Utils.IsEqual(m_startTime, value.m_startTime)) return false;
        if (!Utils.IsEqual(m_endTime, value.m_endTime)) return false;
        if ((EncodingMask & (uint)ProcessingTimesDataTypeFields.AcquisitionDuration) != 0) if (!Utils.IsEqual(m_acquisitionDuration, value.m_acquisitionDuration)) return false;
        if ((EncodingMask & (uint)ProcessingTimesDataTypeFields.ProcessingDuration) != 0) if (!Utils.IsEqual(m_processingDuration, value.m_processingDuration)) return false;

        return true;
    }

    /// <summary cref="ICloneable.Clone" />
    public virtual object Clone()
    {
        return (ProcessingTimesDataType)this.MemberwiseClone();
    }

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        ProcessingTimesDataType clone = (ProcessingTimesDataType)base.MemberwiseClone();

        clone.EncodingMask = this.EncodingMask;

        clone.m_startTime = (DateTime)Utils.Clone(this.m_startTime);
        clone.m_endTime = (DateTime)Utils.Clone(this.m_endTime);
        if ((EncodingMask & (uint)ProcessingTimesDataTypeFields.AcquisitionDuration) != 0) clone.m_acquisitionDuration = (double)Utils.Clone(this.m_acquisitionDuration);
        if ((EncodingMask & (uint)ProcessingTimesDataTypeFields.ProcessingDuration) != 0) clone.m_processingDuration = (double)Utils.Clone(this.m_processingDuration);

        return clone;
    }
    #endregion

    #region Private Fields
    private DateTime m_startTime;
    private DateTime m_endTime;
    private double m_acquisitionDuration;
    private double m_processingDuration;

    private static readonly string[] m_FieldNames = Enum.GetNames(typeof(ProcessingTimesDataTypeFields)).Where(x => x != nameof(ProcessingTimesDataTypeFields.None)).ToArray();
    #endregion
}

#region ProcessingTimesDataTypeCollection Class
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[CollectionDataContract(Name = "ListOfProcessingTimesDataType", Namespace = UAModel.MachineryResult.Namespaces.MachineryResult, ItemName = "ProcessingTimesDataType")]
public partial class ProcessingTimesDataTypeCollection : List<ProcessingTimesDataType>, ICloneable
{
    #region Constructors
    public ProcessingTimesDataTypeCollection() { }

    public ProcessingTimesDataTypeCollection(int capacity) : base(capacity) { }

    public ProcessingTimesDataTypeCollection(IEnumerable<ProcessingTimesDataType> collection) : base(collection) { }
    #endregion

    #region Static Operators
    public static implicit operator ProcessingTimesDataTypeCollection(ProcessingTimesDataType[] values)
    {
        if (values != null)
        {
            return new ProcessingTimesDataTypeCollection(values);
        }

        return new ProcessingTimesDataTypeCollection();
    }

    public static explicit operator ProcessingTimesDataType[](ProcessingTimesDataTypeCollection values)
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
        return (ProcessingTimesDataTypeCollection)this.MemberwiseClone();
    }
    #endregion

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        ProcessingTimesDataTypeCollection clone = new ProcessingTimesDataTypeCollection(this.Count);

        for (int ii = 0; ii < this.Count; ii++)
        {
            clone.Add((ProcessingTimesDataType)Utils.Clone(this[ii]));
        }

        return clone;
    }
}
#endregion
#endif
#endregion

#region ResultDataType Class
#if (!OPCUA_EXCLUDE_ResultDataType)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[DataContract(Namespace = UAModel.MachineryResult.Namespaces.MachineryResult)]
public partial class ResultDataType : IEncodeable, IJsonEncodeable
{
    #region Constructors
    public ResultDataType()
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
        m_resultMetaData = new ResultMetaDataType();
        m_resultContent = new VariantCollection();
    }
    #endregion

    #region Public Properties
    [DataMember(Name = "ResultMetaData", IsRequired = false, Order = 1)]
    public ResultMetaDataType ResultMetaData
    {
        get { return m_resultMetaData; }
        set { m_resultMetaData = value; }
    }

    /// <remarks />
    [DataMember(Name = "ResultContent", IsRequired = false, Order = 2)]
    public VariantCollection ResultContent
    {
        get
        {
            return m_resultContent;
        }

        set
        {
            m_resultContent = value;

            if (value == null)
            {
                m_resultContent = new VariantCollection();
            }
        }
    }
    #endregion

    #region IEncodeable Members
    /// <summary cref="IEncodeable.TypeId" />
    public virtual ExpandedNodeId TypeId => DataTypeIds.ResultDataType;

    /// <summary cref="IEncodeable.BinaryEncodingId" />
    public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.ResultDataType_Encoding_DefaultBinary;

    /// <summary cref="IEncodeable.XmlEncodingId" />
    public virtual ExpandedNodeId XmlEncodingId => ObjectIds.ResultDataType_Encoding_DefaultXml;

    /// <summary cref="IJsonEncodeable.JsonEncodingId" />
    public virtual ExpandedNodeId JsonEncodingId => ObjectIds.ResultDataType_Encoding_DefaultJson;

    /// <summary cref="IEncodeable.Encode(IEncoder)" />
    public virtual void Encode(IEncoder encoder)
    {
        encoder.PushNamespace(UAModel.MachineryResult.Namespaces.MachineryResult);

        encoder.WriteExtensionObject("ResultMetaData", new ExtensionObject(ResultMetaData));
        encoder.WriteVariantArray("ResultContent", ResultContent);

        encoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.Decode(IDecoder)" />
    public virtual void Decode(IDecoder decoder)
    {
        decoder.PushNamespace(UAModel.MachineryResult.Namespaces.MachineryResult);

        ResultMetaData = (ResultMetaDataType)ExtensionObject.ToEncodeable(decoder.ReadExtensionObject("ResultMetaData"));
        ResultContent = decoder.ReadVariantArray("ResultContent");

        decoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
    public virtual bool IsEqual(IEncodeable encodeable)
    {
        if (Object.ReferenceEquals(this, encodeable))
        {
            return true;
        }

        ResultDataType value = encodeable as ResultDataType;

        if (value == null)
        {
            return false;
        }

        if (!Utils.IsEqual(m_resultMetaData, value.m_resultMetaData)) return false;
        if (!Utils.IsEqual(m_resultContent, value.m_resultContent)) return false;

        return true;
    }

    /// <summary cref="ICloneable.Clone" />
    public virtual object Clone()
    {
        return (ResultDataType)this.MemberwiseClone();
    }

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        ResultDataType clone = (ResultDataType)base.MemberwiseClone();

        clone.m_resultMetaData = (ResultMetaDataType)Utils.Clone(this.m_resultMetaData);
        clone.m_resultContent = (VariantCollection)Utils.Clone(this.m_resultContent);

        return clone;
    }
    #endregion

    #region Private Fields
    private ResultMetaDataType m_resultMetaData;
    private VariantCollection m_resultContent;
    #endregion
}

#region ResultDataTypeCollection Class
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[CollectionDataContract(Name = "ListOfResultDataType", Namespace = UAModel.MachineryResult.Namespaces.MachineryResult, ItemName = "ResultDataType")]
public partial class ResultDataTypeCollection : List<ResultDataType>, ICloneable
{
    #region Constructors
    public ResultDataTypeCollection() { }

    public ResultDataTypeCollection(int capacity) : base(capacity) { }

    public ResultDataTypeCollection(IEnumerable<ResultDataType> collection) : base(collection) { }
    #endregion

    #region Static Operators
    public static implicit operator ResultDataTypeCollection(ResultDataType[] values)
    {
        if (values != null)
        {
            return new ResultDataTypeCollection(values);
        }

        return new ResultDataTypeCollection();
    }

    public static explicit operator ResultDataType[](ResultDataTypeCollection values)
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
        return (ResultDataTypeCollection)this.MemberwiseClone();
    }
    #endregion

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        ResultDataTypeCollection clone = new ResultDataTypeCollection(this.Count);

        for (int ii = 0; ii < this.Count; ii++)
        {
            clone.Add((ResultDataType)Utils.Clone(this[ii]));
        }

        return clone;
    }
}
#endregion
#endif
#endregion

#region ResultMetaDataType Class
#if (!OPCUA_EXCLUDE_ResultMetaDataType)
/// <exclude />
[Flags]
public enum ResultMetaDataTypeFields : uint
{
    None = 0,
    HasTransferableDataOnFile = 0x1,
    IsPartial = 0x2,
    IsSimulated = 0x4,
    ResultState = 0x8,
    StepId = 0x10,
    PartId = 0x20,
    ExternalRecipeId = 0x40,
    InternalRecipeId = 0x80,
    ProductId = 0x100,
    ExternalConfigurationId = 0x200,
    InternalConfigurationId = 0x400,
    JobId = 0x800,
    CreationTime = 0x1000,
    ProcessingTimes = 0x2000,
    ResultUri = 0x4000,
    ResultEvaluation = 0x8000,
    ResultEvaluationCode = 0x10000,
    ResultEvaluationDetails = 0x20000,
    FileFormat = 0x40000,
}

/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[DataContract(Namespace = UAModel.MachineryResult.Namespaces.MachineryResult)]
public partial class ResultMetaDataType : IEncodeable, IJsonEncodeable
{
    #region Constructors
    public ResultMetaDataType()
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
        EncodingMask = (uint)ResultMetaDataTypeFields.None;
        m_resultId = null;
        m_hasTransferableDataOnFile = true;
        m_isPartial = true;
        m_isSimulated = true;
        m_resultState = (int)0;
        m_stepId = null;
        m_partId = null;
        m_externalRecipeId = null;
        m_internalRecipeId = null;
        m_productId = null;
        m_externalConfigurationId = null;
        m_internalConfigurationId = null;
        m_jobId = null;
        m_creationTime = DateTime.MinValue;
        m_processingTimes = new ProcessingTimesDataType();
        m_resultUri = new StringCollection();
        m_resultEvaluation = ResultEvaluationEnum.Undefined;
        m_resultEvaluationCode = (long)0;
        m_resultEvaluationDetails = null;
        m_fileFormat = new StringCollection();
    }
    #endregion

    #region Public Properties
    [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
    public virtual uint EncodingMask { get; set; }

    [DataMember(Name = "ResultId", IsRequired = false, Order = 1)]
    public string ResultId
    {
        get { return m_resultId; }
        set { m_resultId = value; }
    }

    [DataMember(Name = "HasTransferableDataOnFile", IsRequired = false, Order = 2)]
    public bool HasTransferableDataOnFile
    {
        get { return m_hasTransferableDataOnFile; }
        set { m_hasTransferableDataOnFile = value; }
    }

    [DataMember(Name = "IsPartial", IsRequired = false, Order = 3)]
    public bool IsPartial
    {
        get { return m_isPartial; }
        set { m_isPartial = value; }
    }

    [DataMember(Name = "IsSimulated", IsRequired = false, Order = 4)]
    public bool IsSimulated
    {
        get { return m_isSimulated; }
        set { m_isSimulated = value; }
    }

    [DataMember(Name = "ResultState", IsRequired = false, Order = 5)]
    public int ResultState
    {
        get { return m_resultState; }
        set { m_resultState = value; }
    }

    [DataMember(Name = "StepId", IsRequired = false, Order = 6)]
    public string StepId
    {
        get { return m_stepId; }
        set { m_stepId = value; }
    }

    [DataMember(Name = "PartId", IsRequired = false, Order = 7)]
    public string PartId
    {
        get { return m_partId; }
        set { m_partId = value; }
    }

    [DataMember(Name = "ExternalRecipeId", IsRequired = false, Order = 8)]
    public string ExternalRecipeId
    {
        get { return m_externalRecipeId; }
        set { m_externalRecipeId = value; }
    }

    [DataMember(Name = "InternalRecipeId", IsRequired = false, Order = 9)]
    public string InternalRecipeId
    {
        get { return m_internalRecipeId; }
        set { m_internalRecipeId = value; }
    }

    [DataMember(Name = "ProductId", IsRequired = false, Order = 10)]
    public string ProductId
    {
        get { return m_productId; }
        set { m_productId = value; }
    }

    [DataMember(Name = "ExternalConfigurationId", IsRequired = false, Order = 11)]
    public string ExternalConfigurationId
    {
        get { return m_externalConfigurationId; }
        set { m_externalConfigurationId = value; }
    }

    [DataMember(Name = "InternalConfigurationId", IsRequired = false, Order = 12)]
    public string InternalConfigurationId
    {
        get { return m_internalConfigurationId; }
        set { m_internalConfigurationId = value; }
    }

    [DataMember(Name = "JobId", IsRequired = false, Order = 13)]
    public string JobId
    {
        get { return m_jobId; }
        set { m_jobId = value; }
    }

    [DataMember(Name = "CreationTime", IsRequired = false, Order = 14)]
    public DateTime CreationTime
    {
        get { return m_creationTime; }
        set { m_creationTime = value; }
    }

    /// <remarks />
    [DataMember(Name = "ProcessingTimes", IsRequired = false, Order = 15)]
    public ProcessingTimesDataType ProcessingTimes
    {
        get
        {
            return m_processingTimes;
        }

        set
        {
            m_processingTimes = value;

            if (value == null)
            {
                m_processingTimes = new ProcessingTimesDataType();
            }
        }
    }

    /// <remarks />
    [DataMember(Name = "ResultUri", IsRequired = false, Order = 16)]
    public StringCollection ResultUri
    {
        get
        {
            return m_resultUri;
        }

        set
        {
            m_resultUri = value;

            if (value == null)
            {
                m_resultUri = new StringCollection();
            }
        }
    }

    [DataMember(Name = "ResultEvaluation", IsRequired = false, Order = 17)]
    public ResultEvaluationEnum ResultEvaluation
    {
        get { return m_resultEvaluation; }
        set { m_resultEvaluation = value; }
    }

    [DataMember(Name = "ResultEvaluationCode", IsRequired = false, Order = 18)]
    public long ResultEvaluationCode
    {
        get { return m_resultEvaluationCode; }
        set { m_resultEvaluationCode = value; }
    }

    [DataMember(Name = "ResultEvaluationDetails", IsRequired = false, Order = 19)]
    public LocalizedText ResultEvaluationDetails
    {
        get { return m_resultEvaluationDetails; }
        set { m_resultEvaluationDetails = value; }
    }

    /// <remarks />
    [DataMember(Name = "FileFormat", IsRequired = false, Order = 20)]
    public StringCollection FileFormat
    {
        get
        {
            return m_fileFormat;
        }

        set
        {
            m_fileFormat = value;

            if (value == null)
            {
                m_fileFormat = new StringCollection();
            }
        }
    }
    #endregion

    #region IEncodeable Members
    /// <summary cref="IEncodeable.TypeId" />
    public virtual ExpandedNodeId TypeId => DataTypeIds.ResultMetaDataType;

    /// <summary cref="IEncodeable.BinaryEncodingId" />
    public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.ResultMetaDataType_Encoding_DefaultBinary;

    /// <summary cref="IEncodeable.XmlEncodingId" />
    public virtual ExpandedNodeId XmlEncodingId => ObjectIds.ResultMetaDataType_Encoding_DefaultXml;

    /// <summary cref="IJsonEncodeable.JsonEncodingId" />
    public virtual ExpandedNodeId JsonEncodingId => ObjectIds.ResultMetaDataType_Encoding_DefaultJson;

    /// <summary cref="IEncodeable.Encode(IEncoder)" />
    public virtual void Encode(IEncoder encoder)
    {
        encoder.PushNamespace(UAModel.MachineryResult.Namespaces.MachineryResult);
        encoder.WriteEncodingMask((uint)EncodingMask);

        encoder.WriteString("ResultId", ResultId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.HasTransferableDataOnFile) != 0) encoder.WriteBoolean("HasTransferableDataOnFile", HasTransferableDataOnFile);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.IsPartial) != 0) encoder.WriteBoolean("IsPartial", IsPartial);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.IsSimulated) != 0) encoder.WriteBoolean("IsSimulated", IsSimulated);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultState) != 0) encoder.WriteInt32("ResultState", ResultState);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.StepId) != 0) encoder.WriteString("StepId", StepId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.PartId) != 0) encoder.WriteString("PartId", PartId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ExternalRecipeId) != 0) encoder.WriteString("ExternalRecipeId", ExternalRecipeId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.InternalRecipeId) != 0) encoder.WriteString("InternalRecipeId", InternalRecipeId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ProductId) != 0) encoder.WriteString("ProductId", ProductId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ExternalConfigurationId) != 0) encoder.WriteString("ExternalConfigurationId", ExternalConfigurationId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.InternalConfigurationId) != 0) encoder.WriteString("InternalConfigurationId", InternalConfigurationId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.JobId) != 0) encoder.WriteString("JobId", JobId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.CreationTime) != 0) encoder.WriteDateTime("CreationTime", CreationTime);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ProcessingTimes) != 0) encoder.WriteEncodeable("ProcessingTimes", ProcessingTimes, typeof(ProcessingTimesDataType));
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultUri) != 0) encoder.WriteStringArray("ResultUri", ResultUri);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultEvaluation) != 0) encoder.WriteEnumerated("ResultEvaluation", ResultEvaluation);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultEvaluationCode) != 0) encoder.WriteInt64("ResultEvaluationCode", ResultEvaluationCode);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultEvaluationDetails) != 0) encoder.WriteLocalizedText("ResultEvaluationDetails", ResultEvaluationDetails);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.FileFormat) != 0) encoder.WriteStringArray("FileFormat", FileFormat);

        encoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.Decode(IDecoder)" />
    public virtual void Decode(IDecoder decoder)
    {
        decoder.PushNamespace(UAModel.MachineryResult.Namespaces.MachineryResult);

        EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

        ResultId = decoder.ReadString("ResultId");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.HasTransferableDataOnFile) != 0) HasTransferableDataOnFile = decoder.ReadBoolean("HasTransferableDataOnFile");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.IsPartial) != 0) IsPartial = decoder.ReadBoolean("IsPartial");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.IsSimulated) != 0) IsSimulated = decoder.ReadBoolean("IsSimulated");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultState) != 0) ResultState = decoder.ReadInt32("ResultState");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.StepId) != 0) StepId = decoder.ReadString("StepId");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.PartId) != 0) PartId = decoder.ReadString("PartId");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ExternalRecipeId) != 0) ExternalRecipeId = decoder.ReadString("ExternalRecipeId");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.InternalRecipeId) != 0) InternalRecipeId = decoder.ReadString("InternalRecipeId");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ProductId) != 0) ProductId = decoder.ReadString("ProductId");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ExternalConfigurationId) != 0) ExternalConfigurationId = decoder.ReadString("ExternalConfigurationId");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.InternalConfigurationId) != 0) InternalConfigurationId = decoder.ReadString("InternalConfigurationId");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.JobId) != 0) JobId = decoder.ReadString("JobId");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.CreationTime) != 0) CreationTime = decoder.ReadDateTime("CreationTime");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ProcessingTimes) != 0) ProcessingTimes = (ProcessingTimesDataType)decoder.ReadEncodeable("ProcessingTimes", typeof(ProcessingTimesDataType));
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultUri) != 0) ResultUri = decoder.ReadStringArray("ResultUri");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultEvaluation) != 0) ResultEvaluation = (ResultEvaluationEnum)decoder.ReadEnumerated("ResultEvaluation", typeof(ResultEvaluationEnum));
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultEvaluationCode) != 0) ResultEvaluationCode = decoder.ReadInt64("ResultEvaluationCode");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultEvaluationDetails) != 0) ResultEvaluationDetails = decoder.ReadLocalizedText("ResultEvaluationDetails");
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.FileFormat) != 0) FileFormat = decoder.ReadStringArray("FileFormat");

        decoder.PopNamespace();
    }

    /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
    public virtual bool IsEqual(IEncodeable encodeable)
    {
        if (Object.ReferenceEquals(this, encodeable))
        {
            return true;
        }

        ResultMetaDataType value = encodeable as ResultMetaDataType;

        if (value == null)
        {
            return false;
        }

        if (value.EncodingMask != this.EncodingMask) return false;

        if (!Utils.IsEqual(m_resultId, value.m_resultId)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.HasTransferableDataOnFile) != 0) if (!Utils.IsEqual(m_hasTransferableDataOnFile, value.m_hasTransferableDataOnFile)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.IsPartial) != 0) if (!Utils.IsEqual(m_isPartial, value.m_isPartial)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.IsSimulated) != 0) if (!Utils.IsEqual(m_isSimulated, value.m_isSimulated)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultState) != 0) if (!Utils.IsEqual(m_resultState, value.m_resultState)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.StepId) != 0) if (!Utils.IsEqual(m_stepId, value.m_stepId)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.PartId) != 0) if (!Utils.IsEqual(m_partId, value.m_partId)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ExternalRecipeId) != 0) if (!Utils.IsEqual(m_externalRecipeId, value.m_externalRecipeId)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.InternalRecipeId) != 0) if (!Utils.IsEqual(m_internalRecipeId, value.m_internalRecipeId)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ProductId) != 0) if (!Utils.IsEqual(m_productId, value.m_productId)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ExternalConfigurationId) != 0) if (!Utils.IsEqual(m_externalConfigurationId, value.m_externalConfigurationId)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.InternalConfigurationId) != 0) if (!Utils.IsEqual(m_internalConfigurationId, value.m_internalConfigurationId)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.JobId) != 0) if (!Utils.IsEqual(m_jobId, value.m_jobId)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.CreationTime) != 0) if (!Utils.IsEqual(m_creationTime, value.m_creationTime)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ProcessingTimes) != 0) if (!Utils.IsEqual(m_processingTimes, value.m_processingTimes)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultUri) != 0) if (!Utils.IsEqual(m_resultUri, value.m_resultUri)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultEvaluation) != 0) if (!Utils.IsEqual(m_resultEvaluation, value.m_resultEvaluation)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultEvaluationCode) != 0) if (!Utils.IsEqual(m_resultEvaluationCode, value.m_resultEvaluationCode)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultEvaluationDetails) != 0) if (!Utils.IsEqual(m_resultEvaluationDetails, value.m_resultEvaluationDetails)) return false;
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.FileFormat) != 0) if (!Utils.IsEqual(m_fileFormat, value.m_fileFormat)) return false;

        return true;
    }

    /// <summary cref="ICloneable.Clone" />
    public virtual object Clone()
    {
        return (ResultMetaDataType)this.MemberwiseClone();
    }

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        ResultMetaDataType clone = (ResultMetaDataType)base.MemberwiseClone();

        clone.EncodingMask = this.EncodingMask;

        clone.m_resultId = (string)Utils.Clone(this.m_resultId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.HasTransferableDataOnFile) != 0) clone.m_hasTransferableDataOnFile = (bool)Utils.Clone(this.m_hasTransferableDataOnFile);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.IsPartial) != 0) clone.m_isPartial = (bool)Utils.Clone(this.m_isPartial);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.IsSimulated) != 0) clone.m_isSimulated = (bool)Utils.Clone(this.m_isSimulated);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultState) != 0) clone.m_resultState = (int)Utils.Clone(this.m_resultState);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.StepId) != 0) clone.m_stepId = (string)Utils.Clone(this.m_stepId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.PartId) != 0) clone.m_partId = (string)Utils.Clone(this.m_partId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ExternalRecipeId) != 0) clone.m_externalRecipeId = (string)Utils.Clone(this.m_externalRecipeId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.InternalRecipeId) != 0) clone.m_internalRecipeId = (string)Utils.Clone(this.m_internalRecipeId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ProductId) != 0) clone.m_productId = (string)Utils.Clone(this.m_productId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ExternalConfigurationId) != 0) clone.m_externalConfigurationId = (string)Utils.Clone(this.m_externalConfigurationId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.InternalConfigurationId) != 0) clone.m_internalConfigurationId = (string)Utils.Clone(this.m_internalConfigurationId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.JobId) != 0) clone.m_jobId = (string)Utils.Clone(this.m_jobId);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.CreationTime) != 0) clone.m_creationTime = (DateTime)Utils.Clone(this.m_creationTime);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ProcessingTimes) != 0) clone.m_processingTimes = (ProcessingTimesDataType)Utils.Clone(this.m_processingTimes);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultUri) != 0) clone.m_resultUri = (StringCollection)Utils.Clone(this.m_resultUri);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultEvaluation) != 0) clone.m_resultEvaluation = (ResultEvaluationEnum)Utils.Clone(this.m_resultEvaluation);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultEvaluationCode) != 0) clone.m_resultEvaluationCode = (long)Utils.Clone(this.m_resultEvaluationCode);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.ResultEvaluationDetails) != 0) clone.m_resultEvaluationDetails = (LocalizedText)Utils.Clone(this.m_resultEvaluationDetails);
        if ((EncodingMask & (uint)ResultMetaDataTypeFields.FileFormat) != 0) clone.m_fileFormat = (StringCollection)Utils.Clone(this.m_fileFormat);

        return clone;
    }
    #endregion

    #region Private Fields
    private string m_resultId;
    private bool m_hasTransferableDataOnFile;
    private bool m_isPartial;
    private bool m_isSimulated;
    private int m_resultState;
    private string m_stepId;
    private string m_partId;
    private string m_externalRecipeId;
    private string m_internalRecipeId;
    private string m_productId;
    private string m_externalConfigurationId;
    private string m_internalConfigurationId;
    private string m_jobId;
    private DateTime m_creationTime;
    private ProcessingTimesDataType m_processingTimes;
    private StringCollection m_resultUri;
    private ResultEvaluationEnum m_resultEvaluation;
    private long m_resultEvaluationCode;
    private LocalizedText m_resultEvaluationDetails;
    private StringCollection m_fileFormat;

    private static readonly string[] m_FieldNames = Enum.GetNames(typeof(ResultMetaDataTypeFields)).Where(x => x != nameof(ResultMetaDataTypeFields.None)).ToArray();
    #endregion
}

#region ResultMetaDataTypeCollection Class
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
[CollectionDataContract(Name = "ListOfResultMetaDataType", Namespace = UAModel.MachineryResult.Namespaces.MachineryResult, ItemName = "ResultMetaDataType")]
public partial class ResultMetaDataTypeCollection : List<ResultMetaDataType>, ICloneable
{
    #region Constructors
    public ResultMetaDataTypeCollection() { }

    public ResultMetaDataTypeCollection(int capacity) : base(capacity) { }

    public ResultMetaDataTypeCollection(IEnumerable<ResultMetaDataType> collection) : base(collection) { }
    #endregion

    #region Static Operators
    public static implicit operator ResultMetaDataTypeCollection(ResultMetaDataType[] values)
    {
        if (values != null)
        {
            return new ResultMetaDataTypeCollection(values);
        }

        return new ResultMetaDataTypeCollection();
    }

    public static explicit operator ResultMetaDataType[](ResultMetaDataTypeCollection values)
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
        return (ResultMetaDataTypeCollection)this.MemberwiseClone();
    }
    #endregion

    /// <summary cref="Object.MemberwiseClone" />
    public new object MemberwiseClone()
    {
        ResultMetaDataTypeCollection clone = new ResultMetaDataTypeCollection(this.Count);

        for (int ii = 0; ii < this.Count; ii++)
        {
            clone.Add((ResultMetaDataType)Utils.Clone(this[ii]));
        }

        return clone;
    }
}
#endregion
#endif
#endregion
