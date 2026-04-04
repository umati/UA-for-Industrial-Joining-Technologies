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

#pragma warning disable CS1591 // Missing XML comment for publicly visible type or member
#pragma warning disable CA1515 // Consider making public types internal
#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1028 // Enum Storage should be Int32

namespace UAModel.IJTBase
{
    #region CalibrationDataType Class
    #if (!OPCUA_EXCLUDE_CalibrationDataType)
    /// <exclude />
    [Flags]
    public enum CalibrationDataTypeFields : uint
    {
        None = 0,
        CalibrationPlace = 0x1,
        NextCalibration = 0x2,
        CalibrationValue = 0x4,
        SensorScale = 0x8,
        CertificateUri = 0x10,
        EngineeringUnits = 0x20,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class CalibrationDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public CalibrationDataType()
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
            EncodingMask = (uint)CalibrationDataTypeFields.None;
            m_lastCalibration = DateTime.MinValue;
            m_calibrationPlace = null;
            m_nextCalibration = DateTime.MinValue;
            m_calibrationValue = (double)0;
            m_sensorScale = (double)0;
            m_certificateUri = null;
            m_engineeringUnits = new Opc.Ua.EUInformation();
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "LastCalibration", IsRequired = false, Order = 1)]
        public DateTime LastCalibration
        {
            get { return m_lastCalibration;  }
            set { m_lastCalibration = value; }
        }

        [DataMember(Name = "CalibrationPlace", IsRequired = false, Order = 2)]
        public string CalibrationPlace
        {
            get { return m_calibrationPlace;  }
            set { m_calibrationPlace = value; }
        }

        [DataMember(Name = "NextCalibration", IsRequired = false, Order = 3)]
        public DateTime NextCalibration
        {
            get { return m_nextCalibration;  }
            set { m_nextCalibration = value; }
        }

        [DataMember(Name = "CalibrationValue", IsRequired = false, Order = 4)]
        public double CalibrationValue
        {
            get { return m_calibrationValue;  }
            set { m_calibrationValue = value; }
        }

        [DataMember(Name = "SensorScale", IsRequired = false, Order = 5)]
        public double SensorScale
        {
            get { return m_sensorScale;  }
            set { m_sensorScale = value; }
        }

        [DataMember(Name = "CertificateUri", IsRequired = false, Order = 6)]
        public string CertificateUri
        {
            get { return m_certificateUri;  }
            set { m_certificateUri = value; }
        }

        /// <remarks />
        [DataMember(Name = "EngineeringUnits", IsRequired = false, Order = 7)]
        public Opc.Ua.EUInformation EngineeringUnits
        {
            get
            {
                return m_engineeringUnits;
            }

            set
            {
                m_engineeringUnits = value;

                if (value == null)
                {
                    m_engineeringUnits = new Opc.Ua.EUInformation();
                }
            }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.CalibrationDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.CalibrationDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.CalibrationDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.CalibrationDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            encoder.WriteDateTime("LastCalibration", LastCalibration);
            if ((EncodingMask & (uint)CalibrationDataTypeFields.CalibrationPlace) != 0) encoder.WriteString("CalibrationPlace", CalibrationPlace);
            if ((EncodingMask & (uint)CalibrationDataTypeFields.NextCalibration) != 0) encoder.WriteDateTime("NextCalibration", NextCalibration);
            if ((EncodingMask & (uint)CalibrationDataTypeFields.CalibrationValue) != 0) encoder.WriteDouble("CalibrationValue", CalibrationValue);
            if ((EncodingMask & (uint)CalibrationDataTypeFields.SensorScale) != 0) encoder.WriteDouble("SensorScale", SensorScale);
            if ((EncodingMask & (uint)CalibrationDataTypeFields.CertificateUri) != 0) encoder.WriteString("CertificateUri", CertificateUri);
            if ((EncodingMask & (uint)CalibrationDataTypeFields.EngineeringUnits) != 0) encoder.WriteEncodeable("EngineeringUnits", EngineeringUnits, typeof(Opc.Ua.EUInformation));

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            LastCalibration = decoder.ReadDateTime("LastCalibration");
            if ((EncodingMask & (uint)CalibrationDataTypeFields.CalibrationPlace) != 0) CalibrationPlace = decoder.ReadString("CalibrationPlace");
            if ((EncodingMask & (uint)CalibrationDataTypeFields.NextCalibration) != 0) NextCalibration = decoder.ReadDateTime("NextCalibration");
            if ((EncodingMask & (uint)CalibrationDataTypeFields.CalibrationValue) != 0) CalibrationValue = decoder.ReadDouble("CalibrationValue");
            if ((EncodingMask & (uint)CalibrationDataTypeFields.SensorScale) != 0) SensorScale = decoder.ReadDouble("SensorScale");
            if ((EncodingMask & (uint)CalibrationDataTypeFields.CertificateUri) != 0) CertificateUri = decoder.ReadString("CertificateUri");
            if ((EncodingMask & (uint)CalibrationDataTypeFields.EngineeringUnits) != 0) EngineeringUnits = (Opc.Ua.EUInformation)decoder.ReadEncodeable("EngineeringUnits", typeof(Opc.Ua.EUInformation));

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            CalibrationDataType value = encodeable as CalibrationDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if (!Utils.IsEqual(m_lastCalibration, value.m_lastCalibration)) return false;
            if ((EncodingMask & (uint)CalibrationDataTypeFields.CalibrationPlace) != 0) if (!Utils.IsEqual(m_calibrationPlace, value.m_calibrationPlace)) return false;
            if ((EncodingMask & (uint)CalibrationDataTypeFields.NextCalibration) != 0) if (!Utils.IsEqual(m_nextCalibration, value.m_nextCalibration)) return false;
            if ((EncodingMask & (uint)CalibrationDataTypeFields.CalibrationValue) != 0) if (!Utils.IsEqual(m_calibrationValue, value.m_calibrationValue)) return false;
            if ((EncodingMask & (uint)CalibrationDataTypeFields.SensorScale) != 0) if (!Utils.IsEqual(m_sensorScale, value.m_sensorScale)) return false;
            if ((EncodingMask & (uint)CalibrationDataTypeFields.CertificateUri) != 0) if (!Utils.IsEqual(m_certificateUri, value.m_certificateUri)) return false;
            if ((EncodingMask & (uint)CalibrationDataTypeFields.EngineeringUnits) != 0) if (!Utils.IsEqual(m_engineeringUnits, value.m_engineeringUnits)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (CalibrationDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            CalibrationDataType clone = (CalibrationDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            clone.m_lastCalibration = (DateTime)Utils.Clone(this.m_lastCalibration);
            if ((EncodingMask & (uint)CalibrationDataTypeFields.CalibrationPlace) != 0) clone.m_calibrationPlace = (string)Utils.Clone(this.m_calibrationPlace);
            if ((EncodingMask & (uint)CalibrationDataTypeFields.NextCalibration) != 0) clone.m_nextCalibration = (DateTime)Utils.Clone(this.m_nextCalibration);
            if ((EncodingMask & (uint)CalibrationDataTypeFields.CalibrationValue) != 0) clone.m_calibrationValue = (double)Utils.Clone(this.m_calibrationValue);
            if ((EncodingMask & (uint)CalibrationDataTypeFields.SensorScale) != 0) clone.m_sensorScale = (double)Utils.Clone(this.m_sensorScale);
            if ((EncodingMask & (uint)CalibrationDataTypeFields.CertificateUri) != 0) clone.m_certificateUri = (string)Utils.Clone(this.m_certificateUri);
            if ((EncodingMask & (uint)CalibrationDataTypeFields.EngineeringUnits) != 0) clone.m_engineeringUnits = (Opc.Ua.EUInformation)Utils.Clone(this.m_engineeringUnits);

            return clone;
        }
        #endregion

        #region Private Fields
        private DateTime m_lastCalibration;
        private string m_calibrationPlace;
        private DateTime m_nextCalibration;
        private double m_calibrationValue;
        private double m_sensorScale;
        private string m_certificateUri;
        private Opc.Ua.EUInformation m_engineeringUnits;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(CalibrationDataTypeFields)).Where(x => x != nameof(CalibrationDataTypeFields.None)).ToArray();
        #endregion
    }

    #region CalibrationDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfCalibrationDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "CalibrationDataType")]
    public partial class CalibrationDataTypeCollection : List<CalibrationDataType>, ICloneable
    {
        #region Constructors
        public CalibrationDataTypeCollection() {}

        public CalibrationDataTypeCollection(int capacity) : base(capacity) {}

        public CalibrationDataTypeCollection(IEnumerable<CalibrationDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator CalibrationDataTypeCollection(CalibrationDataType[] values)
        {
            if (values != null)
            {
                return new CalibrationDataTypeCollection(values);
            }

            return new CalibrationDataTypeCollection();
        }

        public static explicit operator CalibrationDataType[](CalibrationDataTypeCollection values)
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
            return (CalibrationDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            CalibrationDataTypeCollection clone = new CalibrationDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((CalibrationDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region DesignValueDataType Class
    #if (!OPCUA_EXCLUDE_DesignValueDataType)
    /// <exclude />
    [Flags]
    public enum DesignValueDataTypeFields : uint
    {
        None = 0,
        PhysicalQuantity = 0x1,
        Name = 0x2,
        DesignValue = 0x4,
        EngineeringUnits = 0x8,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class DesignValueDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public DesignValueDataType()
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
            EncodingMask = (uint)DesignValueDataTypeFields.None;
            m_physicalQuantity = (byte)0;
            m_name = null;
            m_designValue = Variant.Null;
            m_engineeringUnits = new Opc.Ua.EUInformation();
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "PhysicalQuantity", IsRequired = false, Order = 1)]
        public byte PhysicalQuantity
        {
            get { return m_physicalQuantity;  }
            set { m_physicalQuantity = value; }
        }

        [DataMember(Name = "Name", IsRequired = false, Order = 2)]
        public string Name
        {
            get { return m_name;  }
            set { m_name = value; }
        }

        [DataMember(Name = "DesignValue", IsRequired = false, Order = 3)]
        public Variant DesignValue
        {
            get { return m_designValue;  }
            set { m_designValue = value; }
        }

        /// <remarks />
        [DataMember(Name = "EngineeringUnits", IsRequired = false, Order = 4)]
        public Opc.Ua.EUInformation EngineeringUnits
        {
            get
            {
                return m_engineeringUnits;
            }

            set
            {
                m_engineeringUnits = value;

                if (value == null)
                {
                    m_engineeringUnits = new Opc.Ua.EUInformation();
                }
            }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.DesignValueDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.DesignValueDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.DesignValueDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.DesignValueDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            if ((EncodingMask & (uint)DesignValueDataTypeFields.PhysicalQuantity) != 0) encoder.WriteByte("PhysicalQuantity", PhysicalQuantity);
            if ((EncodingMask & (uint)DesignValueDataTypeFields.Name) != 0) encoder.WriteString("Name", Name);
            if ((EncodingMask & (uint)DesignValueDataTypeFields.DesignValue) != 0) encoder.WriteVariant("DesignValue", DesignValue);
            if ((EncodingMask & (uint)DesignValueDataTypeFields.EngineeringUnits) != 0) encoder.WriteEncodeable("EngineeringUnits", EngineeringUnits, typeof(Opc.Ua.EUInformation));

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            if ((EncodingMask & (uint)DesignValueDataTypeFields.PhysicalQuantity) != 0) PhysicalQuantity = decoder.ReadByte("PhysicalQuantity");
            if ((EncodingMask & (uint)DesignValueDataTypeFields.Name) != 0) Name = decoder.ReadString("Name");
            if ((EncodingMask & (uint)DesignValueDataTypeFields.DesignValue) != 0) DesignValue = decoder.ReadVariant("DesignValue");
            if ((EncodingMask & (uint)DesignValueDataTypeFields.EngineeringUnits) != 0) EngineeringUnits = (Opc.Ua.EUInformation)decoder.ReadEncodeable("EngineeringUnits", typeof(Opc.Ua.EUInformation));

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            DesignValueDataType value = encodeable as DesignValueDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if ((EncodingMask & (uint)DesignValueDataTypeFields.PhysicalQuantity) != 0) if (!Utils.IsEqual(m_physicalQuantity, value.m_physicalQuantity)) return false;
            if ((EncodingMask & (uint)DesignValueDataTypeFields.Name) != 0) if (!Utils.IsEqual(m_name, value.m_name)) return false;
            if ((EncodingMask & (uint)DesignValueDataTypeFields.DesignValue) != 0) if (!Utils.IsEqual(m_designValue, value.m_designValue)) return false;
            if ((EncodingMask & (uint)DesignValueDataTypeFields.EngineeringUnits) != 0) if (!Utils.IsEqual(m_engineeringUnits, value.m_engineeringUnits)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (DesignValueDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            DesignValueDataType clone = (DesignValueDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            if ((EncodingMask & (uint)DesignValueDataTypeFields.PhysicalQuantity) != 0) clone.m_physicalQuantity = (byte)Utils.Clone(this.m_physicalQuantity);
            if ((EncodingMask & (uint)DesignValueDataTypeFields.Name) != 0) clone.m_name = (string)Utils.Clone(this.m_name);
            if ((EncodingMask & (uint)DesignValueDataTypeFields.DesignValue) != 0) clone.m_designValue = (Variant)Utils.Clone(this.m_designValue);
            if ((EncodingMask & (uint)DesignValueDataTypeFields.EngineeringUnits) != 0) clone.m_engineeringUnits = (Opc.Ua.EUInformation)Utils.Clone(this.m_engineeringUnits);

            return clone;
        }
        #endregion

        #region Private Fields
        private byte m_physicalQuantity;
        private string m_name;
        private Variant m_designValue;
        private Opc.Ua.EUInformation m_engineeringUnits;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(DesignValueDataTypeFields)).Where(x => x != nameof(DesignValueDataTypeFields.None)).ToArray();
        #endregion
    }

    #region DesignValueDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfDesignValueDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "DesignValueDataType")]
    public partial class DesignValueDataTypeCollection : List<DesignValueDataType>, ICloneable
    {
        #region Constructors
        public DesignValueDataTypeCollection() {}

        public DesignValueDataTypeCollection(int capacity) : base(capacity) {}

        public DesignValueDataTypeCollection(IEnumerable<DesignValueDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator DesignValueDataTypeCollection(DesignValueDataType[] values)
        {
            if (values != null)
            {
                return new DesignValueDataTypeCollection(values);
            }

            return new DesignValueDataTypeCollection();
        }

        public static explicit operator DesignValueDataType[](DesignValueDataTypeCollection values)
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
            return (DesignValueDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            DesignValueDataTypeCollection clone = new DesignValueDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((DesignValueDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region EntityDataType Class
    #if (!OPCUA_EXCLUDE_EntityDataType)
    /// <exclude />
    [Flags]
    public enum EntityDataTypeFields : uint
    {
        None = 0,
        Name = 0x1,
        Description = 0x2,
        EntityOriginId = 0x4,
        IsExternal = 0x8,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class EntityDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public EntityDataType()
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
            EncodingMask = (uint)EntityDataTypeFields.None;
            m_name = null;
            m_description = null;
            m_entityId = null;
            m_entityOriginId = null;
            m_isExternal = true;
            m_entityType = (short)0;
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "Name", IsRequired = false, Order = 1)]
        public string Name
        {
            get { return m_name;  }
            set { m_name = value; }
        }

        [DataMember(Name = "Description", IsRequired = false, Order = 2)]
        public string Description
        {
            get { return m_description;  }
            set { m_description = value; }
        }

        [DataMember(Name = "EntityId", IsRequired = false, Order = 3)]
        public string EntityId
        {
            get { return m_entityId;  }
            set { m_entityId = value; }
        }

        [DataMember(Name = "EntityOriginId", IsRequired = false, Order = 4)]
        public string EntityOriginId
        {
            get { return m_entityOriginId;  }
            set { m_entityOriginId = value; }
        }

        [DataMember(Name = "IsExternal", IsRequired = false, Order = 5)]
        public bool IsExternal
        {
            get { return m_isExternal;  }
            set { m_isExternal = value; }
        }

        [DataMember(Name = "EntityType", IsRequired = false, Order = 6)]
        public short EntityType
        {
            get { return m_entityType;  }
            set { m_entityType = value; }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.EntityDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.EntityDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.EntityDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.EntityDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            if ((EncodingMask & (uint)EntityDataTypeFields.Name) != 0) encoder.WriteString("Name", Name);
            if ((EncodingMask & (uint)EntityDataTypeFields.Description) != 0) encoder.WriteString("Description", Description);
            encoder.WriteString("EntityId", EntityId);
            if ((EncodingMask & (uint)EntityDataTypeFields.EntityOriginId) != 0) encoder.WriteString("EntityOriginId", EntityOriginId);
            if ((EncodingMask & (uint)EntityDataTypeFields.IsExternal) != 0) encoder.WriteBoolean("IsExternal", IsExternal);
            encoder.WriteInt16("EntityType", EntityType);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            if ((EncodingMask & (uint)EntityDataTypeFields.Name) != 0) Name = decoder.ReadString("Name");
            if ((EncodingMask & (uint)EntityDataTypeFields.Description) != 0) Description = decoder.ReadString("Description");
            EntityId = decoder.ReadString("EntityId");
            if ((EncodingMask & (uint)EntityDataTypeFields.EntityOriginId) != 0) EntityOriginId = decoder.ReadString("EntityOriginId");
            if ((EncodingMask & (uint)EntityDataTypeFields.IsExternal) != 0) IsExternal = decoder.ReadBoolean("IsExternal");
            EntityType = decoder.ReadInt16("EntityType");

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            EntityDataType value = encodeable as EntityDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if ((EncodingMask & (uint)EntityDataTypeFields.Name) != 0) if (!Utils.IsEqual(m_name, value.m_name)) return false;
            if ((EncodingMask & (uint)EntityDataTypeFields.Description) != 0) if (!Utils.IsEqual(m_description, value.m_description)) return false;
            if (!Utils.IsEqual(m_entityId, value.m_entityId)) return false;
            if ((EncodingMask & (uint)EntityDataTypeFields.EntityOriginId) != 0) if (!Utils.IsEqual(m_entityOriginId, value.m_entityOriginId)) return false;
            if ((EncodingMask & (uint)EntityDataTypeFields.IsExternal) != 0) if (!Utils.IsEqual(m_isExternal, value.m_isExternal)) return false;
            if (!Utils.IsEqual(m_entityType, value.m_entityType)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (EntityDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            EntityDataType clone = (EntityDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            if ((EncodingMask & (uint)EntityDataTypeFields.Name) != 0) clone.m_name = (string)Utils.Clone(this.m_name);
            if ((EncodingMask & (uint)EntityDataTypeFields.Description) != 0) clone.m_description = (string)Utils.Clone(this.m_description);
            clone.m_entityId = (string)Utils.Clone(this.m_entityId);
            if ((EncodingMask & (uint)EntityDataTypeFields.EntityOriginId) != 0) clone.m_entityOriginId = (string)Utils.Clone(this.m_entityOriginId);
            if ((EncodingMask & (uint)EntityDataTypeFields.IsExternal) != 0) clone.m_isExternal = (bool)Utils.Clone(this.m_isExternal);
            clone.m_entityType = (short)Utils.Clone(this.m_entityType);

            return clone;
        }
        #endregion

        #region Private Fields
        private string m_name;
        private string m_description;
        private string m_entityId;
        private string m_entityOriginId;
        private bool m_isExternal;
        private short m_entityType;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(EntityDataTypeFields)).Where(x => x != nameof(EntityDataTypeFields.None)).ToArray();
        #endregion
    }

    #region EntityDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfEntityDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "EntityDataType")]
    public partial class EntityDataTypeCollection : List<EntityDataType>, ICloneable
    {
        #region Constructors
        public EntityDataTypeCollection() {}

        public EntityDataTypeCollection(int capacity) : base(capacity) {}

        public EntityDataTypeCollection(IEnumerable<EntityDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator EntityDataTypeCollection(EntityDataType[] values)
        {
            if (values != null)
            {
                return new EntityDataTypeCollection(values);
            }

            return new EntityDataTypeCollection();
        }

        public static explicit operator EntityDataType[](EntityDataTypeCollection values)
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
            return (EntityDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            EntityDataTypeCollection clone = new EntityDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((EntityDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region ErrorInformationDataType Class
    #if (!OPCUA_EXCLUDE_ErrorInformationDataType)
    /// <exclude />
    [Flags]
    public enum ErrorInformationDataTypeFields : uint
    {
        None = 0,
        ErrorId = 0x1,
        LegacyError = 0x2,
        ErrorMessage = 0x4,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class ErrorInformationDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public ErrorInformationDataType()
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
            EncodingMask = (uint)ErrorInformationDataTypeFields.None;
            m_errorType = (byte)0;
            m_errorId = null;
            m_legacyError = null;
            m_errorMessage = null;
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "ErrorType", IsRequired = false, Order = 1)]
        public byte ErrorType
        {
            get { return m_errorType;  }
            set { m_errorType = value; }
        }

        [DataMember(Name = "ErrorId", IsRequired = false, Order = 2)]
        public string ErrorId
        {
            get { return m_errorId;  }
            set { m_errorId = value; }
        }

        [DataMember(Name = "LegacyError", IsRequired = false, Order = 3)]
        public string LegacyError
        {
            get { return m_legacyError;  }
            set { m_legacyError = value; }
        }

        [DataMember(Name = "ErrorMessage", IsRequired = false, Order = 4)]
        public LocalizedText ErrorMessage
        {
            get { return m_errorMessage;  }
            set { m_errorMessage = value; }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.ErrorInformationDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.ErrorInformationDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.ErrorInformationDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.ErrorInformationDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            encoder.WriteByte("ErrorType", ErrorType);
            if ((EncodingMask & (uint)ErrorInformationDataTypeFields.ErrorId) != 0) encoder.WriteString("ErrorId", ErrorId);
            if ((EncodingMask & (uint)ErrorInformationDataTypeFields.LegacyError) != 0) encoder.WriteString("LegacyError", LegacyError);
            if ((EncodingMask & (uint)ErrorInformationDataTypeFields.ErrorMessage) != 0) encoder.WriteLocalizedText("ErrorMessage", ErrorMessage);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            ErrorType = decoder.ReadByte("ErrorType");
            if ((EncodingMask & (uint)ErrorInformationDataTypeFields.ErrorId) != 0) ErrorId = decoder.ReadString("ErrorId");
            if ((EncodingMask & (uint)ErrorInformationDataTypeFields.LegacyError) != 0) LegacyError = decoder.ReadString("LegacyError");
            if ((EncodingMask & (uint)ErrorInformationDataTypeFields.ErrorMessage) != 0) ErrorMessage = decoder.ReadLocalizedText("ErrorMessage");

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            ErrorInformationDataType value = encodeable as ErrorInformationDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if (!Utils.IsEqual(m_errorType, value.m_errorType)) return false;
            if ((EncodingMask & (uint)ErrorInformationDataTypeFields.ErrorId) != 0) if (!Utils.IsEqual(m_errorId, value.m_errorId)) return false;
            if ((EncodingMask & (uint)ErrorInformationDataTypeFields.LegacyError) != 0) if (!Utils.IsEqual(m_legacyError, value.m_legacyError)) return false;
            if ((EncodingMask & (uint)ErrorInformationDataTypeFields.ErrorMessage) != 0) if (!Utils.IsEqual(m_errorMessage, value.m_errorMessage)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (ErrorInformationDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            ErrorInformationDataType clone = (ErrorInformationDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            clone.m_errorType = (byte)Utils.Clone(this.m_errorType);
            if ((EncodingMask & (uint)ErrorInformationDataTypeFields.ErrorId) != 0) clone.m_errorId = (string)Utils.Clone(this.m_errorId);
            if ((EncodingMask & (uint)ErrorInformationDataTypeFields.LegacyError) != 0) clone.m_legacyError = (string)Utils.Clone(this.m_legacyError);
            if ((EncodingMask & (uint)ErrorInformationDataTypeFields.ErrorMessage) != 0) clone.m_errorMessage = (LocalizedText)Utils.Clone(this.m_errorMessage);

            return clone;
        }
        #endregion

        #region Private Fields
        private byte m_errorType;
        private string m_errorId;
        private string m_legacyError;
        private LocalizedText m_errorMessage;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(ErrorInformationDataTypeFields)).Where(x => x != nameof(ErrorInformationDataTypeFields.None)).ToArray();
        #endregion
    }

    #region ErrorInformationDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfErrorInformationDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "ErrorInformationDataType")]
    public partial class ErrorInformationDataTypeCollection : List<ErrorInformationDataType>, ICloneable
    {
        #region Constructors
        public ErrorInformationDataTypeCollection() {}

        public ErrorInformationDataTypeCollection(int capacity) : base(capacity) {}

        public ErrorInformationDataTypeCollection(IEnumerable<ErrorInformationDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator ErrorInformationDataTypeCollection(ErrorInformationDataType[] values)
        {
            if (values != null)
            {
                return new ErrorInformationDataTypeCollection(values);
            }

            return new ErrorInformationDataTypeCollection();
        }

        public static explicit operator ErrorInformationDataType[](ErrorInformationDataTypeCollection values)
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
            return (ErrorInformationDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            ErrorInformationDataTypeCollection clone = new ErrorInformationDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((ErrorInformationDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region JoiningProcessDataType Class
    #if (!OPCUA_EXCLUDE_JoiningProcessDataType)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class JoiningProcessDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public JoiningProcessDataType()
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
            m_joiningProcessMetaData = new JoiningProcessMetaDataType();
            m_joiningProcessContent = new VariantCollection();
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "JoiningProcessMetaData", IsRequired = false, Order = 1)]
        public JoiningProcessMetaDataType JoiningProcessMetaData
        {
            get { return m_joiningProcessMetaData;  }
            set { m_joiningProcessMetaData = value; }
        }

        /// <remarks />
        [DataMember(Name = "JoiningProcessContent", IsRequired = false, Order = 2)]
        public VariantCollection JoiningProcessContent
        {
            get
            {
                return m_joiningProcessContent;
            }

            set
            {
                m_joiningProcessContent = value;

                if (value == null)
                {
                    m_joiningProcessContent = new VariantCollection();
                }
            }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.JoiningProcessDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.JoiningProcessDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.JoiningProcessDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.JoiningProcessDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            encoder.WriteExtensionObject("JoiningProcessMetaData", new ExtensionObject(JoiningProcessMetaData));
            encoder.WriteVariantArray("JoiningProcessContent", JoiningProcessContent);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            JoiningProcessMetaData = (JoiningProcessMetaDataType)ExtensionObject.ToEncodeable(decoder.ReadExtensionObject("JoiningProcessMetaData"));
            JoiningProcessContent = decoder.ReadVariantArray("JoiningProcessContent");

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            JoiningProcessDataType value = encodeable as JoiningProcessDataType;

            if (value == null)
            {
                return false;
            }

            if (!Utils.IsEqual(m_joiningProcessMetaData, value.m_joiningProcessMetaData)) return false;
            if (!Utils.IsEqual(m_joiningProcessContent, value.m_joiningProcessContent)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (JoiningProcessDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JoiningProcessDataType clone = (JoiningProcessDataType)base.MemberwiseClone();

            clone.m_joiningProcessMetaData = (JoiningProcessMetaDataType)Utils.Clone(this.m_joiningProcessMetaData);
            clone.m_joiningProcessContent = (VariantCollection)Utils.Clone(this.m_joiningProcessContent);

            return clone;
        }
        #endregion

        #region Private Fields
        private JoiningProcessMetaDataType m_joiningProcessMetaData;
        private VariantCollection m_joiningProcessContent;
        #endregion
    }

    #region JoiningProcessDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfJoiningProcessDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "JoiningProcessDataType")]
    public partial class JoiningProcessDataTypeCollection : List<JoiningProcessDataType>, ICloneable
    {
        #region Constructors
        public JoiningProcessDataTypeCollection() {}

        public JoiningProcessDataTypeCollection(int capacity) : base(capacity) {}

        public JoiningProcessDataTypeCollection(IEnumerable<JoiningProcessDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator JoiningProcessDataTypeCollection(JoiningProcessDataType[] values)
        {
            if (values != null)
            {
                return new JoiningProcessDataTypeCollection(values);
            }

            return new JoiningProcessDataTypeCollection();
        }

        public static explicit operator JoiningProcessDataType[](JoiningProcessDataTypeCollection values)
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
            return (JoiningProcessDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JoiningProcessDataTypeCollection clone = new JoiningProcessDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((JoiningProcessDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region JoiningProcessIdentificationDataType Class
    #if (!OPCUA_EXCLUDE_JoiningProcessIdentificationDataType)
    /// <exclude />
    [Flags]
    public enum JoiningProcessIdentificationDataTypeFields : uint
    {
        None = 0,
        JoiningProcessId = 0x1,
        JoiningProcessOriginId = 0x2,
        SelectionName = 0x4,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class JoiningProcessIdentificationDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public JoiningProcessIdentificationDataType()
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
            EncodingMask = (uint)JoiningProcessIdentificationDataTypeFields.None;
            m_joiningProcessId = null;
            m_joiningProcessOriginId = null;
            m_selectionName = null;
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "JoiningProcessId", IsRequired = false, Order = 1)]
        public string JoiningProcessId
        {
            get { return m_joiningProcessId;  }
            set { m_joiningProcessId = value; }
        }

        [DataMember(Name = "JoiningProcessOriginId", IsRequired = false, Order = 2)]
        public string JoiningProcessOriginId
        {
            get { return m_joiningProcessOriginId;  }
            set { m_joiningProcessOriginId = value; }
        }

        [DataMember(Name = "SelectionName", IsRequired = false, Order = 3)]
        public string SelectionName
        {
            get { return m_selectionName;  }
            set { m_selectionName = value; }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.JoiningProcessIdentificationDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.JoiningProcessIdentificationDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.JoiningProcessIdentificationDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.JoiningProcessIdentificationDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            if ((EncodingMask & (uint)JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0) encoder.WriteString("JoiningProcessId", JoiningProcessId);
            if ((EncodingMask & (uint)JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId) != 0) encoder.WriteString("JoiningProcessOriginId", JoiningProcessOriginId);
            if ((EncodingMask & (uint)JoiningProcessIdentificationDataTypeFields.SelectionName) != 0) encoder.WriteString("SelectionName", SelectionName);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            if ((EncodingMask & (uint)JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0) JoiningProcessId = decoder.ReadString("JoiningProcessId");
            if ((EncodingMask & (uint)JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId) != 0) JoiningProcessOriginId = decoder.ReadString("JoiningProcessOriginId");
            if ((EncodingMask & (uint)JoiningProcessIdentificationDataTypeFields.SelectionName) != 0) SelectionName = decoder.ReadString("SelectionName");

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            JoiningProcessIdentificationDataType value = encodeable as JoiningProcessIdentificationDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if ((EncodingMask & (uint)JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0) if (!Utils.IsEqual(m_joiningProcessId, value.m_joiningProcessId)) return false;
            if ((EncodingMask & (uint)JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId) != 0) if (!Utils.IsEqual(m_joiningProcessOriginId, value.m_joiningProcessOriginId)) return false;
            if ((EncodingMask & (uint)JoiningProcessIdentificationDataTypeFields.SelectionName) != 0) if (!Utils.IsEqual(m_selectionName, value.m_selectionName)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (JoiningProcessIdentificationDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JoiningProcessIdentificationDataType clone = (JoiningProcessIdentificationDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            if ((EncodingMask & (uint)JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0) clone.m_joiningProcessId = (string)Utils.Clone(this.m_joiningProcessId);
            if ((EncodingMask & (uint)JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId) != 0) clone.m_joiningProcessOriginId = (string)Utils.Clone(this.m_joiningProcessOriginId);
            if ((EncodingMask & (uint)JoiningProcessIdentificationDataTypeFields.SelectionName) != 0) clone.m_selectionName = (string)Utils.Clone(this.m_selectionName);

            return clone;
        }
        #endregion

        #region Private Fields
        private string m_joiningProcessId;
        private string m_joiningProcessOriginId;
        private string m_selectionName;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(JoiningProcessIdentificationDataTypeFields)).Where(x => x != nameof(JoiningProcessIdentificationDataTypeFields.None)).ToArray();
        #endregion
    }

    #region JoiningProcessIdentificationDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfJoiningProcessIdentificationDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "JoiningProcessIdentificationDataType")]
    public partial class JoiningProcessIdentificationDataTypeCollection : List<JoiningProcessIdentificationDataType>, ICloneable
    {
        #region Constructors
        public JoiningProcessIdentificationDataTypeCollection() {}

        public JoiningProcessIdentificationDataTypeCollection(int capacity) : base(capacity) {}

        public JoiningProcessIdentificationDataTypeCollection(IEnumerable<JoiningProcessIdentificationDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator JoiningProcessIdentificationDataTypeCollection(JoiningProcessIdentificationDataType[] values)
        {
            if (values != null)
            {
                return new JoiningProcessIdentificationDataTypeCollection(values);
            }

            return new JoiningProcessIdentificationDataTypeCollection();
        }

        public static explicit operator JoiningProcessIdentificationDataType[](JoiningProcessIdentificationDataTypeCollection values)
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
            return (JoiningProcessIdentificationDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JoiningProcessIdentificationDataTypeCollection clone = new JoiningProcessIdentificationDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((JoiningProcessIdentificationDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region JoiningProcessMetaDataType Class
    #if (!OPCUA_EXCLUDE_JoiningProcessMetaDataType)
    /// <exclude />
    [Flags]
    public enum JoiningProcessMetaDataTypeFields : uint
    {
        None = 0,
        JoiningProcessOriginId = 0x1,
        CreationTime = 0x2,
        LastUpdatedTime = 0x4,
        Name = 0x8,
        Description = 0x10,
        JoiningTechnology = 0x20,
        Classification = 0x40,
        AssociatedEntities = 0x80,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class JoiningProcessMetaDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public JoiningProcessMetaDataType()
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
            EncodingMask = (uint)JoiningProcessMetaDataTypeFields.None;
            m_joiningProcessId = null;
            m_joiningProcessOriginId = null;
            m_creationTime = DateTime.MinValue;
            m_lastUpdatedTime = DateTime.MinValue;
            m_name = null;
            m_description = null;
            m_joiningTechnology = null;
            m_classification = (short)0;
            m_associatedEntities = new EntityDataTypeCollection();
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "JoiningProcessId", IsRequired = false, Order = 1)]
        public string JoiningProcessId
        {
            get { return m_joiningProcessId;  }
            set { m_joiningProcessId = value; }
        }

        [DataMember(Name = "JoiningProcessOriginId", IsRequired = false, Order = 2)]
        public string JoiningProcessOriginId
        {
            get { return m_joiningProcessOriginId;  }
            set { m_joiningProcessOriginId = value; }
        }

        [DataMember(Name = "CreationTime", IsRequired = false, Order = 3)]
        public DateTime CreationTime
        {
            get { return m_creationTime;  }
            set { m_creationTime = value; }
        }

        [DataMember(Name = "LastUpdatedTime", IsRequired = false, Order = 4)]
        public DateTime LastUpdatedTime
        {
            get { return m_lastUpdatedTime;  }
            set { m_lastUpdatedTime = value; }
        }

        [DataMember(Name = "Name", IsRequired = false, Order = 5)]
        public string Name
        {
            get { return m_name;  }
            set { m_name = value; }
        }

        [DataMember(Name = "Description", IsRequired = false, Order = 6)]
        public LocalizedText Description
        {
            get { return m_description;  }
            set { m_description = value; }
        }

        [DataMember(Name = "JoiningTechnology", IsRequired = false, Order = 7)]
        public LocalizedText JoiningTechnology
        {
            get { return m_joiningTechnology;  }
            set { m_joiningTechnology = value; }
        }

        [DataMember(Name = "Classification", IsRequired = false, Order = 8)]
        public short Classification
        {
            get { return m_classification;  }
            set { m_classification = value; }
        }

        /// <remarks />
        [DataMember(Name = "AssociatedEntities", IsRequired = false, Order = 9)]
        public EntityDataTypeCollection AssociatedEntities
        {
            get
            {
                return m_associatedEntities;
            }

            set
            {
                m_associatedEntities = value;

                if (value == null)
                {
                    m_associatedEntities = new EntityDataTypeCollection();
                }
            }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.JoiningProcessMetaDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.JoiningProcessMetaDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.JoiningProcessMetaDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.JoiningProcessMetaDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            encoder.WriteString("JoiningProcessId", JoiningProcessId);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.JoiningProcessOriginId) != 0) encoder.WriteString("JoiningProcessOriginId", JoiningProcessOriginId);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.CreationTime) != 0) encoder.WriteDateTime("CreationTime", CreationTime);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.LastUpdatedTime) != 0) encoder.WriteDateTime("LastUpdatedTime", LastUpdatedTime);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.Name) != 0) encoder.WriteString("Name", Name);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.Description) != 0) encoder.WriteLocalizedText("Description", Description);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.JoiningTechnology) != 0) encoder.WriteLocalizedText("JoiningTechnology", JoiningTechnology);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.Classification) != 0) encoder.WriteInt16("Classification", Classification);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.AssociatedEntities) != 0) encoder.WriteEncodeableArray("AssociatedEntities", AssociatedEntities.ToArray(), typeof(EntityDataType));

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            JoiningProcessId = decoder.ReadString("JoiningProcessId");
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.JoiningProcessOriginId) != 0) JoiningProcessOriginId = decoder.ReadString("JoiningProcessOriginId");
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.CreationTime) != 0) CreationTime = decoder.ReadDateTime("CreationTime");
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.LastUpdatedTime) != 0) LastUpdatedTime = decoder.ReadDateTime("LastUpdatedTime");
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.Name) != 0) Name = decoder.ReadString("Name");
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.Description) != 0) Description = decoder.ReadLocalizedText("Description");
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.JoiningTechnology) != 0) JoiningTechnology = decoder.ReadLocalizedText("JoiningTechnology");
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.Classification) != 0) Classification = decoder.ReadInt16("Classification");
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.AssociatedEntities) != 0) AssociatedEntities = (EntityDataTypeCollection)decoder.ReadEncodeableArray("AssociatedEntities", typeof(EntityDataType));

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            JoiningProcessMetaDataType value = encodeable as JoiningProcessMetaDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if (!Utils.IsEqual(m_joiningProcessId, value.m_joiningProcessId)) return false;
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.JoiningProcessOriginId) != 0) if (!Utils.IsEqual(m_joiningProcessOriginId, value.m_joiningProcessOriginId)) return false;
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.CreationTime) != 0) if (!Utils.IsEqual(m_creationTime, value.m_creationTime)) return false;
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.LastUpdatedTime) != 0) if (!Utils.IsEqual(m_lastUpdatedTime, value.m_lastUpdatedTime)) return false;
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.Name) != 0) if (!Utils.IsEqual(m_name, value.m_name)) return false;
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.Description) != 0) if (!Utils.IsEqual(m_description, value.m_description)) return false;
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.JoiningTechnology) != 0) if (!Utils.IsEqual(m_joiningTechnology, value.m_joiningTechnology)) return false;
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.Classification) != 0) if (!Utils.IsEqual(m_classification, value.m_classification)) return false;
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.AssociatedEntities) != 0) if (!Utils.IsEqual(m_associatedEntities, value.m_associatedEntities)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (JoiningProcessMetaDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JoiningProcessMetaDataType clone = (JoiningProcessMetaDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            clone.m_joiningProcessId = (string)Utils.Clone(this.m_joiningProcessId);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.JoiningProcessOriginId) != 0) clone.m_joiningProcessOriginId = (string)Utils.Clone(this.m_joiningProcessOriginId);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.CreationTime) != 0) clone.m_creationTime = (DateTime)Utils.Clone(this.m_creationTime);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.LastUpdatedTime) != 0) clone.m_lastUpdatedTime = (DateTime)Utils.Clone(this.m_lastUpdatedTime);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.Name) != 0) clone.m_name = (string)Utils.Clone(this.m_name);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.Description) != 0) clone.m_description = (LocalizedText)Utils.Clone(this.m_description);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.JoiningTechnology) != 0) clone.m_joiningTechnology = (LocalizedText)Utils.Clone(this.m_joiningTechnology);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.Classification) != 0) clone.m_classification = (short)Utils.Clone(this.m_classification);
            if ((EncodingMask & (uint)JoiningProcessMetaDataTypeFields.AssociatedEntities) != 0) clone.m_associatedEntities = (EntityDataTypeCollection)Utils.Clone(this.m_associatedEntities);

            return clone;
        }
        #endregion

        #region Private Fields
        private string m_joiningProcessId;
        private string m_joiningProcessOriginId;
        private DateTime m_creationTime;
        private DateTime m_lastUpdatedTime;
        private string m_name;
        private LocalizedText m_description;
        private LocalizedText m_joiningTechnology;
        private short m_classification;
        private EntityDataTypeCollection m_associatedEntities;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(JoiningProcessMetaDataTypeFields)).Where(x => x != nameof(JoiningProcessMetaDataTypeFields.None)).ToArray();
        #endregion
    }

    #region JoiningProcessMetaDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfJoiningProcessMetaDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "JoiningProcessMetaDataType")]
    public partial class JoiningProcessMetaDataTypeCollection : List<JoiningProcessMetaDataType>, ICloneable
    {
        #region Constructors
        public JoiningProcessMetaDataTypeCollection() {}

        public JoiningProcessMetaDataTypeCollection(int capacity) : base(capacity) {}

        public JoiningProcessMetaDataTypeCollection(IEnumerable<JoiningProcessMetaDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator JoiningProcessMetaDataTypeCollection(JoiningProcessMetaDataType[] values)
        {
            if (values != null)
            {
                return new JoiningProcessMetaDataTypeCollection(values);
            }

            return new JoiningProcessMetaDataTypeCollection();
        }

        public static explicit operator JoiningProcessMetaDataType[](JoiningProcessMetaDataTypeCollection values)
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
            return (JoiningProcessMetaDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JoiningProcessMetaDataTypeCollection clone = new JoiningProcessMetaDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((JoiningProcessMetaDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region JoiningResultDataType Class
    #if (!OPCUA_EXCLUDE_JoiningResultDataType)
    /// <exclude />
    [Flags]
    public enum JoiningResultDataTypeFields : uint
    {
        None = 0,
        FailureReason = 0x1,
        StepResults = 0x2,
        Errors = 0x4,
        FailingStepResultId = 0x8,
        Trace = 0x10,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class JoiningResultDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public JoiningResultDataType()
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
            EncodingMask = (uint)JoiningResultDataTypeFields.None;
            m_failureReason = (byte)0;
            m_overallResultValues = new ResultValueDataTypeCollection();
            m_stepResults = new StepResultDataTypeCollection();
            m_errors = new ErrorInformationDataTypeCollection();
            m_failingStepResultId = null;
            m_trace = new JoiningTraceDataType();
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "FailureReason", IsRequired = false, Order = 1)]
        public byte FailureReason
        {
            get { return m_failureReason;  }
            set { m_failureReason = value; }
        }

        /// <remarks />
        [DataMember(Name = "OverallResultValues", IsRequired = false, Order = 2)]
        public ResultValueDataTypeCollection OverallResultValues
        {
            get
            {
                return m_overallResultValues;
            }

            set
            {
                m_overallResultValues = value;

                if (value == null)
                {
                    m_overallResultValues = new ResultValueDataTypeCollection();
                }
            }
        }

        /// <remarks />
        [DataMember(Name = "StepResults", IsRequired = false, Order = 3)]
        public StepResultDataTypeCollection StepResults
        {
            get
            {
                return m_stepResults;
            }

            set
            {
                m_stepResults = value;

                if (value == null)
                {
                    m_stepResults = new StepResultDataTypeCollection();
                }
            }
        }

        /// <remarks />
        [DataMember(Name = "Errors", IsRequired = false, Order = 4)]
        public ErrorInformationDataTypeCollection Errors
        {
            get
            {
                return m_errors;
            }

            set
            {
                m_errors = value;

                if (value == null)
                {
                    m_errors = new ErrorInformationDataTypeCollection();
                }
            }
        }

        [DataMember(Name = "FailingStepResultId", IsRequired = false, Order = 5)]
        public string FailingStepResultId
        {
            get { return m_failingStepResultId;  }
            set { m_failingStepResultId = value; }
        }

        /// <remarks />
        [DataMember(Name = "Trace", IsRequired = false, Order = 6)]
        public JoiningTraceDataType Trace
        {
            get
            {
                return m_trace;
            }

            set
            {
                m_trace = value;

                if (value == null)
                {
                    m_trace = new JoiningTraceDataType();
                }
            }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.JoiningResultDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.JoiningResultDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.JoiningResultDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.JoiningResultDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            if ((EncodingMask & (uint)JoiningResultDataTypeFields.FailureReason) != 0) encoder.WriteByte("FailureReason", FailureReason);
            encoder.WriteEncodeableArray("OverallResultValues", OverallResultValues.ToArray(), typeof(ResultValueDataType));
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.StepResults) != 0) encoder.WriteEncodeableArray("StepResults", StepResults.ToArray(), typeof(StepResultDataType));
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.Errors) != 0) encoder.WriteEncodeableArray("Errors", Errors.ToArray(), typeof(ErrorInformationDataType));
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.FailingStepResultId) != 0) encoder.WriteString("FailingStepResultId", FailingStepResultId);
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.Trace) != 0) encoder.WriteEncodeable("Trace", Trace, typeof(JoiningTraceDataType));

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            if ((EncodingMask & (uint)JoiningResultDataTypeFields.FailureReason) != 0) FailureReason = decoder.ReadByte("FailureReason");
            OverallResultValues = (ResultValueDataTypeCollection)decoder.ReadEncodeableArray("OverallResultValues", typeof(ResultValueDataType));
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.StepResults) != 0) StepResults = (StepResultDataTypeCollection)decoder.ReadEncodeableArray("StepResults", typeof(StepResultDataType));
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.Errors) != 0) Errors = (ErrorInformationDataTypeCollection)decoder.ReadEncodeableArray("Errors", typeof(ErrorInformationDataType));
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.FailingStepResultId) != 0) FailingStepResultId = decoder.ReadString("FailingStepResultId");
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.Trace) != 0) Trace = (JoiningTraceDataType)decoder.ReadEncodeable("Trace", typeof(JoiningTraceDataType));

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            JoiningResultDataType value = encodeable as JoiningResultDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if ((EncodingMask & (uint)JoiningResultDataTypeFields.FailureReason) != 0) if (!Utils.IsEqual(m_failureReason, value.m_failureReason)) return false;
            if (!Utils.IsEqual(m_overallResultValues, value.m_overallResultValues)) return false;
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.StepResults) != 0) if (!Utils.IsEqual(m_stepResults, value.m_stepResults)) return false;
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.Errors) != 0) if (!Utils.IsEqual(m_errors, value.m_errors)) return false;
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.FailingStepResultId) != 0) if (!Utils.IsEqual(m_failingStepResultId, value.m_failingStepResultId)) return false;
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.Trace) != 0) if (!Utils.IsEqual(m_trace, value.m_trace)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (JoiningResultDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JoiningResultDataType clone = (JoiningResultDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            if ((EncodingMask & (uint)JoiningResultDataTypeFields.FailureReason) != 0) clone.m_failureReason = (byte)Utils.Clone(this.m_failureReason);
            clone.m_overallResultValues = (ResultValueDataTypeCollection)Utils.Clone(this.m_overallResultValues);
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.StepResults) != 0) clone.m_stepResults = (StepResultDataTypeCollection)Utils.Clone(this.m_stepResults);
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.Errors) != 0) clone.m_errors = (ErrorInformationDataTypeCollection)Utils.Clone(this.m_errors);
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.FailingStepResultId) != 0) clone.m_failingStepResultId = (string)Utils.Clone(this.m_failingStepResultId);
            if ((EncodingMask & (uint)JoiningResultDataTypeFields.Trace) != 0) clone.m_trace = (JoiningTraceDataType)Utils.Clone(this.m_trace);

            return clone;
        }
        #endregion

        #region Private Fields
        private byte m_failureReason;
        private ResultValueDataTypeCollection m_overallResultValues;
        private StepResultDataTypeCollection m_stepResults;
        private ErrorInformationDataTypeCollection m_errors;
        private string m_failingStepResultId;
        private JoiningTraceDataType m_trace;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(JoiningResultDataTypeFields)).Where(x => x != nameof(JoiningResultDataTypeFields.None)).ToArray();
        #endregion
    }

    #region JoiningResultDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfJoiningResultDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "JoiningResultDataType")]
    public partial class JoiningResultDataTypeCollection : List<JoiningResultDataType>, ICloneable
    {
        #region Constructors
        public JoiningResultDataTypeCollection() {}

        public JoiningResultDataTypeCollection(int capacity) : base(capacity) {}

        public JoiningResultDataTypeCollection(IEnumerable<JoiningResultDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator JoiningResultDataTypeCollection(JoiningResultDataType[] values)
        {
            if (values != null)
            {
                return new JoiningResultDataTypeCollection(values);
            }

            return new JoiningResultDataTypeCollection();
        }

        public static explicit operator JoiningResultDataType[](JoiningResultDataTypeCollection values)
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
            return (JoiningResultDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JoiningResultDataTypeCollection clone = new JoiningResultDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((JoiningResultDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region JointComponentDataType Class
    #if (!OPCUA_EXCLUDE_JointComponentDataType)
    /// <exclude />
    [Flags]
    public enum JointComponentDataTypeFields : uint
    {
        None = 0,
        Name = 0x1,
        Description = 0x2,
        Manufacturer = 0x4,
        ManufacturerUri = 0x8,
        JointComponentContent = 0x10,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class JointComponentDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public JointComponentDataType()
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
            EncodingMask = (uint)JointComponentDataTypeFields.None;
            m_jointComponentId = null;
            m_name = null;
            m_description = null;
            m_manufacturer = null;
            m_manufacturerUri = null;
            m_jointComponentContent = Variant.Null;
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "JointComponentId", IsRequired = false, Order = 1)]
        public string JointComponentId
        {
            get { return m_jointComponentId;  }
            set { m_jointComponentId = value; }
        }

        [DataMember(Name = "Name", IsRequired = false, Order = 2)]
        public string Name
        {
            get { return m_name;  }
            set { m_name = value; }
        }

        [DataMember(Name = "Description", IsRequired = false, Order = 3)]
        public LocalizedText Description
        {
            get { return m_description;  }
            set { m_description = value; }
        }

        [DataMember(Name = "Manufacturer", IsRequired = false, Order = 4)]
        public LocalizedText Manufacturer
        {
            get { return m_manufacturer;  }
            set { m_manufacturer = value; }
        }

        [DataMember(Name = "ManufacturerUri", IsRequired = false, Order = 5)]
        public string ManufacturerUri
        {
            get { return m_manufacturerUri;  }
            set { m_manufacturerUri = value; }
        }

        [DataMember(Name = "JointComponentContent", IsRequired = false, Order = 6)]
        public Variant JointComponentContent
        {
            get { return m_jointComponentContent;  }
            set { m_jointComponentContent = value; }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.JointComponentDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.JointComponentDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.JointComponentDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.JointComponentDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            encoder.WriteString("JointComponentId", JointComponentId);
            if ((EncodingMask & (uint)JointComponentDataTypeFields.Name) != 0) encoder.WriteString("Name", Name);
            if ((EncodingMask & (uint)JointComponentDataTypeFields.Description) != 0) encoder.WriteLocalizedText("Description", Description);
            if ((EncodingMask & (uint)JointComponentDataTypeFields.Manufacturer) != 0) encoder.WriteLocalizedText("Manufacturer", Manufacturer);
            if ((EncodingMask & (uint)JointComponentDataTypeFields.ManufacturerUri) != 0) encoder.WriteString("ManufacturerUri", ManufacturerUri);
            if ((EncodingMask & (uint)JointComponentDataTypeFields.JointComponentContent) != 0) encoder.WriteVariant("JointComponentContent", JointComponentContent);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            JointComponentId = decoder.ReadString("JointComponentId");
            if ((EncodingMask & (uint)JointComponentDataTypeFields.Name) != 0) Name = decoder.ReadString("Name");
            if ((EncodingMask & (uint)JointComponentDataTypeFields.Description) != 0) Description = decoder.ReadLocalizedText("Description");
            if ((EncodingMask & (uint)JointComponentDataTypeFields.Manufacturer) != 0) Manufacturer = decoder.ReadLocalizedText("Manufacturer");
            if ((EncodingMask & (uint)JointComponentDataTypeFields.ManufacturerUri) != 0) ManufacturerUri = decoder.ReadString("ManufacturerUri");
            if ((EncodingMask & (uint)JointComponentDataTypeFields.JointComponentContent) != 0) JointComponentContent = decoder.ReadVariant("JointComponentContent");

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            JointComponentDataType value = encodeable as JointComponentDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if (!Utils.IsEqual(m_jointComponentId, value.m_jointComponentId)) return false;
            if ((EncodingMask & (uint)JointComponentDataTypeFields.Name) != 0) if (!Utils.IsEqual(m_name, value.m_name)) return false;
            if ((EncodingMask & (uint)JointComponentDataTypeFields.Description) != 0) if (!Utils.IsEqual(m_description, value.m_description)) return false;
            if ((EncodingMask & (uint)JointComponentDataTypeFields.Manufacturer) != 0) if (!Utils.IsEqual(m_manufacturer, value.m_manufacturer)) return false;
            if ((EncodingMask & (uint)JointComponentDataTypeFields.ManufacturerUri) != 0) if (!Utils.IsEqual(m_manufacturerUri, value.m_manufacturerUri)) return false;
            if ((EncodingMask & (uint)JointComponentDataTypeFields.JointComponentContent) != 0) if (!Utils.IsEqual(m_jointComponentContent, value.m_jointComponentContent)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (JointComponentDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JointComponentDataType clone = (JointComponentDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            clone.m_jointComponentId = (string)Utils.Clone(this.m_jointComponentId);
            if ((EncodingMask & (uint)JointComponentDataTypeFields.Name) != 0) clone.m_name = (string)Utils.Clone(this.m_name);
            if ((EncodingMask & (uint)JointComponentDataTypeFields.Description) != 0) clone.m_description = (LocalizedText)Utils.Clone(this.m_description);
            if ((EncodingMask & (uint)JointComponentDataTypeFields.Manufacturer) != 0) clone.m_manufacturer = (LocalizedText)Utils.Clone(this.m_manufacturer);
            if ((EncodingMask & (uint)JointComponentDataTypeFields.ManufacturerUri) != 0) clone.m_manufacturerUri = (string)Utils.Clone(this.m_manufacturerUri);
            if ((EncodingMask & (uint)JointComponentDataTypeFields.JointComponentContent) != 0) clone.m_jointComponentContent = (Variant)Utils.Clone(this.m_jointComponentContent);

            return clone;
        }
        #endregion

        #region Private Fields
        private string m_jointComponentId;
        private string m_name;
        private LocalizedText m_description;
        private LocalizedText m_manufacturer;
        private string m_manufacturerUri;
        private Variant m_jointComponentContent;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(JointComponentDataTypeFields)).Where(x => x != nameof(JointComponentDataTypeFields.None)).ToArray();
        #endregion
    }

    #region JointComponentDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfJointComponentDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "JointComponentDataType")]
    public partial class JointComponentDataTypeCollection : List<JointComponentDataType>, ICloneable
    {
        #region Constructors
        public JointComponentDataTypeCollection() {}

        public JointComponentDataTypeCollection(int capacity) : base(capacity) {}

        public JointComponentDataTypeCollection(IEnumerable<JointComponentDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator JointComponentDataTypeCollection(JointComponentDataType[] values)
        {
            if (values != null)
            {
                return new JointComponentDataTypeCollection(values);
            }

            return new JointComponentDataTypeCollection();
        }

        public static explicit operator JointComponentDataType[](JointComponentDataTypeCollection values)
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
            return (JointComponentDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JointComponentDataTypeCollection clone = new JointComponentDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((JointComponentDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region JointDataType Class
    #if (!OPCUA_EXCLUDE_JointDataType)
    /// <exclude />
    [Flags]
    public enum JointDataTypeFields : uint
    {
        None = 0,
        JointOriginId = 0x1,
        JointDesignId = 0x2,
        CreationTime = 0x4,
        LastUpdatedTime = 0x8,
        Name = 0x10,
        Description = 0x20,
        Classification = 0x40,
        ClassificationDetails = 0x80,
        JointStatus = 0x100,
        AssociatedEntities = 0x200,
        JoiningTechnology = 0x400,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class JointDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public JointDataType()
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
            EncodingMask = (uint)JointDataTypeFields.None;
            m_jointId = null;
            m_jointOriginId = null;
            m_jointDesignId = null;
            m_creationTime = DateTime.MinValue;
            m_lastUpdatedTime = DateTime.MinValue;
            m_name = null;
            m_description = null;
            m_classification = (short)0;
            m_classificationDetails = null;
            m_jointStatus = null;
            m_associatedEntities = new EntityDataTypeCollection();
            m_joiningTechnology = null;
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "JointId", IsRequired = false, Order = 1)]
        public string JointId
        {
            get { return m_jointId;  }
            set { m_jointId = value; }
        }

        [DataMember(Name = "JointOriginId", IsRequired = false, Order = 2)]
        public string JointOriginId
        {
            get { return m_jointOriginId;  }
            set { m_jointOriginId = value; }
        }

        [DataMember(Name = "JointDesignId", IsRequired = false, Order = 3)]
        public string JointDesignId
        {
            get { return m_jointDesignId;  }
            set { m_jointDesignId = value; }
        }

        [DataMember(Name = "CreationTime", IsRequired = false, Order = 4)]
        public DateTime CreationTime
        {
            get { return m_creationTime;  }
            set { m_creationTime = value; }
        }

        [DataMember(Name = "LastUpdatedTime", IsRequired = false, Order = 5)]
        public DateTime LastUpdatedTime
        {
            get { return m_lastUpdatedTime;  }
            set { m_lastUpdatedTime = value; }
        }

        [DataMember(Name = "Name", IsRequired = false, Order = 6)]
        public string Name
        {
            get { return m_name;  }
            set { m_name = value; }
        }

        [DataMember(Name = "Description", IsRequired = false, Order = 7)]
        public LocalizedText Description
        {
            get { return m_description;  }
            set { m_description = value; }
        }

        [DataMember(Name = "Classification", IsRequired = false, Order = 8)]
        public short Classification
        {
            get { return m_classification;  }
            set { m_classification = value; }
        }

        [DataMember(Name = "ClassificationDetails", IsRequired = false, Order = 9)]
        public LocalizedText ClassificationDetails
        {
            get { return m_classificationDetails;  }
            set { m_classificationDetails = value; }
        }

        [DataMember(Name = "JointStatus", IsRequired = false, Order = 10)]
        public string JointStatus
        {
            get { return m_jointStatus;  }
            set { m_jointStatus = value; }
        }

        /// <remarks />
        [DataMember(Name = "AssociatedEntities", IsRequired = false, Order = 11)]
        public EntityDataTypeCollection AssociatedEntities
        {
            get
            {
                return m_associatedEntities;
            }

            set
            {
                m_associatedEntities = value;

                if (value == null)
                {
                    m_associatedEntities = new EntityDataTypeCollection();
                }
            }
        }

        [DataMember(Name = "JoiningTechnology", IsRequired = false, Order = 12)]
        public LocalizedText JoiningTechnology
        {
            get { return m_joiningTechnology;  }
            set { m_joiningTechnology = value; }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.JointDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.JointDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.JointDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.JointDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            encoder.WriteString("JointId", JointId);
            if ((EncodingMask & (uint)JointDataTypeFields.JointOriginId) != 0) encoder.WriteString("JointOriginId", JointOriginId);
            if ((EncodingMask & (uint)JointDataTypeFields.JointDesignId) != 0) encoder.WriteString("JointDesignId", JointDesignId);
            if ((EncodingMask & (uint)JointDataTypeFields.CreationTime) != 0) encoder.WriteDateTime("CreationTime", CreationTime);
            if ((EncodingMask & (uint)JointDataTypeFields.LastUpdatedTime) != 0) encoder.WriteDateTime("LastUpdatedTime", LastUpdatedTime);
            if ((EncodingMask & (uint)JointDataTypeFields.Name) != 0) encoder.WriteString("Name", Name);
            if ((EncodingMask & (uint)JointDataTypeFields.Description) != 0) encoder.WriteLocalizedText("Description", Description);
            if ((EncodingMask & (uint)JointDataTypeFields.Classification) != 0) encoder.WriteInt16("Classification", Classification);
            if ((EncodingMask & (uint)JointDataTypeFields.ClassificationDetails) != 0) encoder.WriteLocalizedText("ClassificationDetails", ClassificationDetails);
            if ((EncodingMask & (uint)JointDataTypeFields.JointStatus) != 0) encoder.WriteString("JointStatus", JointStatus);
            if ((EncodingMask & (uint)JointDataTypeFields.AssociatedEntities) != 0) encoder.WriteEncodeableArray("AssociatedEntities", AssociatedEntities.ToArray(), typeof(EntityDataType));
            if ((EncodingMask & (uint)JointDataTypeFields.JoiningTechnology) != 0) encoder.WriteLocalizedText("JoiningTechnology", JoiningTechnology);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            JointId = decoder.ReadString("JointId");
            if ((EncodingMask & (uint)JointDataTypeFields.JointOriginId) != 0) JointOriginId = decoder.ReadString("JointOriginId");
            if ((EncodingMask & (uint)JointDataTypeFields.JointDesignId) != 0) JointDesignId = decoder.ReadString("JointDesignId");
            if ((EncodingMask & (uint)JointDataTypeFields.CreationTime) != 0) CreationTime = decoder.ReadDateTime("CreationTime");
            if ((EncodingMask & (uint)JointDataTypeFields.LastUpdatedTime) != 0) LastUpdatedTime = decoder.ReadDateTime("LastUpdatedTime");
            if ((EncodingMask & (uint)JointDataTypeFields.Name) != 0) Name = decoder.ReadString("Name");
            if ((EncodingMask & (uint)JointDataTypeFields.Description) != 0) Description = decoder.ReadLocalizedText("Description");
            if ((EncodingMask & (uint)JointDataTypeFields.Classification) != 0) Classification = decoder.ReadInt16("Classification");
            if ((EncodingMask & (uint)JointDataTypeFields.ClassificationDetails) != 0) ClassificationDetails = decoder.ReadLocalizedText("ClassificationDetails");
            if ((EncodingMask & (uint)JointDataTypeFields.JointStatus) != 0) JointStatus = decoder.ReadString("JointStatus");
            if ((EncodingMask & (uint)JointDataTypeFields.AssociatedEntities) != 0) AssociatedEntities = (EntityDataTypeCollection)decoder.ReadEncodeableArray("AssociatedEntities", typeof(EntityDataType));
            if ((EncodingMask & (uint)JointDataTypeFields.JoiningTechnology) != 0) JoiningTechnology = decoder.ReadLocalizedText("JoiningTechnology");

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            JointDataType value = encodeable as JointDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if (!Utils.IsEqual(m_jointId, value.m_jointId)) return false;
            if ((EncodingMask & (uint)JointDataTypeFields.JointOriginId) != 0) if (!Utils.IsEqual(m_jointOriginId, value.m_jointOriginId)) return false;
            if ((EncodingMask & (uint)JointDataTypeFields.JointDesignId) != 0) if (!Utils.IsEqual(m_jointDesignId, value.m_jointDesignId)) return false;
            if ((EncodingMask & (uint)JointDataTypeFields.CreationTime) != 0) if (!Utils.IsEqual(m_creationTime, value.m_creationTime)) return false;
            if ((EncodingMask & (uint)JointDataTypeFields.LastUpdatedTime) != 0) if (!Utils.IsEqual(m_lastUpdatedTime, value.m_lastUpdatedTime)) return false;
            if ((EncodingMask & (uint)JointDataTypeFields.Name) != 0) if (!Utils.IsEqual(m_name, value.m_name)) return false;
            if ((EncodingMask & (uint)JointDataTypeFields.Description) != 0) if (!Utils.IsEqual(m_description, value.m_description)) return false;
            if ((EncodingMask & (uint)JointDataTypeFields.Classification) != 0) if (!Utils.IsEqual(m_classification, value.m_classification)) return false;
            if ((EncodingMask & (uint)JointDataTypeFields.ClassificationDetails) != 0) if (!Utils.IsEqual(m_classificationDetails, value.m_classificationDetails)) return false;
            if ((EncodingMask & (uint)JointDataTypeFields.JointStatus) != 0) if (!Utils.IsEqual(m_jointStatus, value.m_jointStatus)) return false;
            if ((EncodingMask & (uint)JointDataTypeFields.AssociatedEntities) != 0) if (!Utils.IsEqual(m_associatedEntities, value.m_associatedEntities)) return false;
            if ((EncodingMask & (uint)JointDataTypeFields.JoiningTechnology) != 0) if (!Utils.IsEqual(m_joiningTechnology, value.m_joiningTechnology)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (JointDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JointDataType clone = (JointDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            clone.m_jointId = (string)Utils.Clone(this.m_jointId);
            if ((EncodingMask & (uint)JointDataTypeFields.JointOriginId) != 0) clone.m_jointOriginId = (string)Utils.Clone(this.m_jointOriginId);
            if ((EncodingMask & (uint)JointDataTypeFields.JointDesignId) != 0) clone.m_jointDesignId = (string)Utils.Clone(this.m_jointDesignId);
            if ((EncodingMask & (uint)JointDataTypeFields.CreationTime) != 0) clone.m_creationTime = (DateTime)Utils.Clone(this.m_creationTime);
            if ((EncodingMask & (uint)JointDataTypeFields.LastUpdatedTime) != 0) clone.m_lastUpdatedTime = (DateTime)Utils.Clone(this.m_lastUpdatedTime);
            if ((EncodingMask & (uint)JointDataTypeFields.Name) != 0) clone.m_name = (string)Utils.Clone(this.m_name);
            if ((EncodingMask & (uint)JointDataTypeFields.Description) != 0) clone.m_description = (LocalizedText)Utils.Clone(this.m_description);
            if ((EncodingMask & (uint)JointDataTypeFields.Classification) != 0) clone.m_classification = (short)Utils.Clone(this.m_classification);
            if ((EncodingMask & (uint)JointDataTypeFields.ClassificationDetails) != 0) clone.m_classificationDetails = (LocalizedText)Utils.Clone(this.m_classificationDetails);
            if ((EncodingMask & (uint)JointDataTypeFields.JointStatus) != 0) clone.m_jointStatus = (string)Utils.Clone(this.m_jointStatus);
            if ((EncodingMask & (uint)JointDataTypeFields.AssociatedEntities) != 0) clone.m_associatedEntities = (EntityDataTypeCollection)Utils.Clone(this.m_associatedEntities);
            if ((EncodingMask & (uint)JointDataTypeFields.JoiningTechnology) != 0) clone.m_joiningTechnology = (LocalizedText)Utils.Clone(this.m_joiningTechnology);

            return clone;
        }
        #endregion

        #region Private Fields
        private string m_jointId;
        private string m_jointOriginId;
        private string m_jointDesignId;
        private DateTime m_creationTime;
        private DateTime m_lastUpdatedTime;
        private string m_name;
        private LocalizedText m_description;
        private short m_classification;
        private LocalizedText m_classificationDetails;
        private string m_jointStatus;
        private EntityDataTypeCollection m_associatedEntities;
        private LocalizedText m_joiningTechnology;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(JointDataTypeFields)).Where(x => x != nameof(JointDataTypeFields.None)).ToArray();
        #endregion
    }

    #region JointDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfJointDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "JointDataType")]
    public partial class JointDataTypeCollection : List<JointDataType>, ICloneable
    {
        #region Constructors
        public JointDataTypeCollection() {}

        public JointDataTypeCollection(int capacity) : base(capacity) {}

        public JointDataTypeCollection(IEnumerable<JointDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator JointDataTypeCollection(JointDataType[] values)
        {
            if (values != null)
            {
                return new JointDataTypeCollection(values);
            }

            return new JointDataTypeCollection();
        }

        public static explicit operator JointDataType[](JointDataTypeCollection values)
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
            return (JointDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JointDataTypeCollection clone = new JointDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((JointDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region JointDesignDataType Class
    #if (!OPCUA_EXCLUDE_JointDesignDataType)
    /// <exclude />
    [Flags]
    public enum JointDesignDataTypeFields : uint
    {
        None = 0,
        Name = 0x1,
        Description = 0x2,
        JointDesignContent = 0x4,
        JointComponentIdList = 0x8,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class JointDesignDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public JointDesignDataType()
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
            EncodingMask = (uint)JointDesignDataTypeFields.None;
            m_jointDesignId = null;
            m_name = null;
            m_description = null;
            m_jointDesignContent = new DesignValueDataTypeCollection();
            m_jointComponentIdList = new StringCollection();
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "JointDesignId", IsRequired = false, Order = 1)]
        public string JointDesignId
        {
            get { return m_jointDesignId;  }
            set { m_jointDesignId = value; }
        }

        [DataMember(Name = "Name", IsRequired = false, Order = 2)]
        public string Name
        {
            get { return m_name;  }
            set { m_name = value; }
        }

        [DataMember(Name = "Description", IsRequired = false, Order = 3)]
        public LocalizedText Description
        {
            get { return m_description;  }
            set { m_description = value; }
        }

        /// <remarks />
        [DataMember(Name = "JointDesignContent", IsRequired = false, Order = 4)]
        public DesignValueDataTypeCollection JointDesignContent
        {
            get
            {
                return m_jointDesignContent;
            }

            set
            {
                m_jointDesignContent = value;

                if (value == null)
                {
                    m_jointDesignContent = new DesignValueDataTypeCollection();
                }
            }
        }

        /// <remarks />
        [DataMember(Name = "JointComponentIdList", IsRequired = false, Order = 5)]
        public StringCollection JointComponentIdList
        {
            get
            {
                return m_jointComponentIdList;
            }

            set
            {
                m_jointComponentIdList = value;

                if (value == null)
                {
                    m_jointComponentIdList = new StringCollection();
                }
            }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.JointDesignDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.JointDesignDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.JointDesignDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.JointDesignDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            encoder.WriteString("JointDesignId", JointDesignId);
            if ((EncodingMask & (uint)JointDesignDataTypeFields.Name) != 0) encoder.WriteString("Name", Name);
            if ((EncodingMask & (uint)JointDesignDataTypeFields.Description) != 0) encoder.WriteLocalizedText("Description", Description);
            if ((EncodingMask & (uint)JointDesignDataTypeFields.JointDesignContent) != 0) encoder.WriteEncodeableArray("JointDesignContent", JointDesignContent.ToArray(), typeof(DesignValueDataType));
            if ((EncodingMask & (uint)JointDesignDataTypeFields.JointComponentIdList) != 0) encoder.WriteStringArray("JointComponentIdList", JointComponentIdList);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            JointDesignId = decoder.ReadString("JointDesignId");
            if ((EncodingMask & (uint)JointDesignDataTypeFields.Name) != 0) Name = decoder.ReadString("Name");
            if ((EncodingMask & (uint)JointDesignDataTypeFields.Description) != 0) Description = decoder.ReadLocalizedText("Description");
            if ((EncodingMask & (uint)JointDesignDataTypeFields.JointDesignContent) != 0) JointDesignContent = (DesignValueDataTypeCollection)decoder.ReadEncodeableArray("JointDesignContent", typeof(DesignValueDataType));
            if ((EncodingMask & (uint)JointDesignDataTypeFields.JointComponentIdList) != 0) JointComponentIdList = decoder.ReadStringArray("JointComponentIdList");

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            JointDesignDataType value = encodeable as JointDesignDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if (!Utils.IsEqual(m_jointDesignId, value.m_jointDesignId)) return false;
            if ((EncodingMask & (uint)JointDesignDataTypeFields.Name) != 0) if (!Utils.IsEqual(m_name, value.m_name)) return false;
            if ((EncodingMask & (uint)JointDesignDataTypeFields.Description) != 0) if (!Utils.IsEqual(m_description, value.m_description)) return false;
            if ((EncodingMask & (uint)JointDesignDataTypeFields.JointDesignContent) != 0) if (!Utils.IsEqual(m_jointDesignContent, value.m_jointDesignContent)) return false;
            if ((EncodingMask & (uint)JointDesignDataTypeFields.JointComponentIdList) != 0) if (!Utils.IsEqual(m_jointComponentIdList, value.m_jointComponentIdList)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (JointDesignDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JointDesignDataType clone = (JointDesignDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            clone.m_jointDesignId = (string)Utils.Clone(this.m_jointDesignId);
            if ((EncodingMask & (uint)JointDesignDataTypeFields.Name) != 0) clone.m_name = (string)Utils.Clone(this.m_name);
            if ((EncodingMask & (uint)JointDesignDataTypeFields.Description) != 0) clone.m_description = (LocalizedText)Utils.Clone(this.m_description);
            if ((EncodingMask & (uint)JointDesignDataTypeFields.JointDesignContent) != 0) clone.m_jointDesignContent = (DesignValueDataTypeCollection)Utils.Clone(this.m_jointDesignContent);
            if ((EncodingMask & (uint)JointDesignDataTypeFields.JointComponentIdList) != 0) clone.m_jointComponentIdList = (StringCollection)Utils.Clone(this.m_jointComponentIdList);

            return clone;
        }
        #endregion

        #region Private Fields
        private string m_jointDesignId;
        private string m_name;
        private LocalizedText m_description;
        private DesignValueDataTypeCollection m_jointDesignContent;
        private StringCollection m_jointComponentIdList;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(JointDesignDataTypeFields)).Where(x => x != nameof(JointDesignDataTypeFields.None)).ToArray();
        #endregion
    }

    #region JointDesignDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfJointDesignDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "JointDesignDataType")]
    public partial class JointDesignDataTypeCollection : List<JointDesignDataType>, ICloneable
    {
        #region Constructors
        public JointDesignDataTypeCollection() {}

        public JointDesignDataTypeCollection(int capacity) : base(capacity) {}

        public JointDesignDataTypeCollection(IEnumerable<JointDesignDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator JointDesignDataTypeCollection(JointDesignDataType[] values)
        {
            if (values != null)
            {
                return new JointDesignDataTypeCollection(values);
            }

            return new JointDesignDataTypeCollection();
        }

        public static explicit operator JointDesignDataType[](JointDesignDataTypeCollection values)
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
            return (JointDesignDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JointDesignDataTypeCollection clone = new JointDesignDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((JointDesignDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region KeyValueDataType Class
    #if (!OPCUA_EXCLUDE_KeyValueDataType)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class KeyValueDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public KeyValueDataType()
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
            m_key = null;
            m_value = Variant.Null;
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "Key", IsRequired = false, Order = 1)]
        public string Key
        {
            get { return m_key;  }
            set { m_key = value; }
        }

        [DataMember(Name = "Value", IsRequired = false, Order = 2)]
        public Variant Value
        {
            get { return m_value;  }
            set { m_value = value; }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.KeyValueDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.KeyValueDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.KeyValueDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.KeyValueDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            encoder.WriteString("Key", Key);
            encoder.WriteVariant("Value", Value);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            Key = decoder.ReadString("Key");
            Value = decoder.ReadVariant("Value");

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            KeyValueDataType value = encodeable as KeyValueDataType;

            if (value == null)
            {
                return false;
            }

            if (!Utils.IsEqual(m_key, value.m_key)) return false;
            if (!Utils.IsEqual(m_value, value.m_value)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (KeyValueDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            KeyValueDataType clone = (KeyValueDataType)base.MemberwiseClone();

            clone.m_key = (string)Utils.Clone(this.m_key);
            clone.m_value = (Variant)Utils.Clone(this.m_value);

            return clone;
        }
        #endregion

        #region Private Fields
        private string m_key;
        private Variant m_value;
        #endregion
    }

    #region KeyValueDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfKeyValueDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "KeyValueDataType")]
    public partial class KeyValueDataTypeCollection : List<KeyValueDataType>, ICloneable
    {
        #region Constructors
        public KeyValueDataTypeCollection() {}

        public KeyValueDataTypeCollection(int capacity) : base(capacity) {}

        public KeyValueDataTypeCollection(IEnumerable<KeyValueDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator KeyValueDataTypeCollection(KeyValueDataType[] values)
        {
            if (values != null)
            {
                return new KeyValueDataTypeCollection(values);
            }

            return new KeyValueDataTypeCollection();
        }

        public static explicit operator KeyValueDataType[](KeyValueDataTypeCollection values)
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
            return (KeyValueDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            KeyValueDataTypeCollection clone = new KeyValueDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((KeyValueDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region ReportedValueDataType Class
    #if (!OPCUA_EXCLUDE_ReportedValueDataType)
    /// <exclude />
    [Flags]
    public enum ReportedValueDataTypeFields : uint
    {
        None = 0,
        PhysicalQuantity = 0x1,
        Name = 0x2,
        PreviousValue = 0x4,
        LowLimit = 0x8,
        HighLimit = 0x10,
        EngineeringUnits = 0x20,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class ReportedValueDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public ReportedValueDataType()
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
            EncodingMask = (uint)ReportedValueDataTypeFields.None;
            m_physicalQuantity = (byte)0;
            m_name = null;
            m_currentValue = Variant.Null;
            m_previousValue = Variant.Null;
            m_lowLimit = (double)0;
            m_highLimit = (double)0;
            m_engineeringUnits = new Opc.Ua.EUInformation();
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "PhysicalQuantity", IsRequired = false, Order = 1)]
        public byte PhysicalQuantity
        {
            get { return m_physicalQuantity;  }
            set { m_physicalQuantity = value; }
        }

        [DataMember(Name = "Name", IsRequired = false, Order = 2)]
        public string Name
        {
            get { return m_name;  }
            set { m_name = value; }
        }

        [DataMember(Name = "CurrentValue", IsRequired = false, Order = 3)]
        public Variant CurrentValue
        {
            get { return m_currentValue;  }
            set { m_currentValue = value; }
        }

        [DataMember(Name = "PreviousValue", IsRequired = false, Order = 4)]
        public Variant PreviousValue
        {
            get { return m_previousValue;  }
            set { m_previousValue = value; }
        }

        [DataMember(Name = "LowLimit", IsRequired = false, Order = 5)]
        public double LowLimit
        {
            get { return m_lowLimit;  }
            set { m_lowLimit = value; }
        }

        [DataMember(Name = "HighLimit", IsRequired = false, Order = 6)]
        public double HighLimit
        {
            get { return m_highLimit;  }
            set { m_highLimit = value; }
        }

        /// <remarks />
        [DataMember(Name = "EngineeringUnits", IsRequired = false, Order = 7)]
        public Opc.Ua.EUInformation EngineeringUnits
        {
            get
            {
                return m_engineeringUnits;
            }

            set
            {
                m_engineeringUnits = value;

                if (value == null)
                {
                    m_engineeringUnits = new Opc.Ua.EUInformation();
                }
            }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.ReportedValueDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.ReportedValueDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.ReportedValueDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.ReportedValueDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            if ((EncodingMask & (uint)ReportedValueDataTypeFields.PhysicalQuantity) != 0) encoder.WriteByte("PhysicalQuantity", PhysicalQuantity);
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.Name) != 0) encoder.WriteString("Name", Name);
            encoder.WriteVariant("CurrentValue", CurrentValue);
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.PreviousValue) != 0) encoder.WriteVariant("PreviousValue", PreviousValue);
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.LowLimit) != 0) encoder.WriteDouble("LowLimit", LowLimit);
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.HighLimit) != 0) encoder.WriteDouble("HighLimit", HighLimit);
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.EngineeringUnits) != 0) encoder.WriteEncodeable("EngineeringUnits", EngineeringUnits, typeof(Opc.Ua.EUInformation));

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            if ((EncodingMask & (uint)ReportedValueDataTypeFields.PhysicalQuantity) != 0) PhysicalQuantity = decoder.ReadByte("PhysicalQuantity");
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.Name) != 0) Name = decoder.ReadString("Name");
            CurrentValue = decoder.ReadVariant("CurrentValue");
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.PreviousValue) != 0) PreviousValue = decoder.ReadVariant("PreviousValue");
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.LowLimit) != 0) LowLimit = decoder.ReadDouble("LowLimit");
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.HighLimit) != 0) HighLimit = decoder.ReadDouble("HighLimit");
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.EngineeringUnits) != 0) EngineeringUnits = (Opc.Ua.EUInformation)decoder.ReadEncodeable("EngineeringUnits", typeof(Opc.Ua.EUInformation));

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            ReportedValueDataType value = encodeable as ReportedValueDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if ((EncodingMask & (uint)ReportedValueDataTypeFields.PhysicalQuantity) != 0) if (!Utils.IsEqual(m_physicalQuantity, value.m_physicalQuantity)) return false;
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.Name) != 0) if (!Utils.IsEqual(m_name, value.m_name)) return false;
            if (!Utils.IsEqual(m_currentValue, value.m_currentValue)) return false;
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.PreviousValue) != 0) if (!Utils.IsEqual(m_previousValue, value.m_previousValue)) return false;
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.LowLimit) != 0) if (!Utils.IsEqual(m_lowLimit, value.m_lowLimit)) return false;
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.HighLimit) != 0) if (!Utils.IsEqual(m_highLimit, value.m_highLimit)) return false;
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.EngineeringUnits) != 0) if (!Utils.IsEqual(m_engineeringUnits, value.m_engineeringUnits)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (ReportedValueDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            ReportedValueDataType clone = (ReportedValueDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            if ((EncodingMask & (uint)ReportedValueDataTypeFields.PhysicalQuantity) != 0) clone.m_physicalQuantity = (byte)Utils.Clone(this.m_physicalQuantity);
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.Name) != 0) clone.m_name = (string)Utils.Clone(this.m_name);
            clone.m_currentValue = (Variant)Utils.Clone(this.m_currentValue);
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.PreviousValue) != 0) clone.m_previousValue = (Variant)Utils.Clone(this.m_previousValue);
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.LowLimit) != 0) clone.m_lowLimit = (double)Utils.Clone(this.m_lowLimit);
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.HighLimit) != 0) clone.m_highLimit = (double)Utils.Clone(this.m_highLimit);
            if ((EncodingMask & (uint)ReportedValueDataTypeFields.EngineeringUnits) != 0) clone.m_engineeringUnits = (Opc.Ua.EUInformation)Utils.Clone(this.m_engineeringUnits);

            return clone;
        }
        #endregion

        #region Private Fields
        private byte m_physicalQuantity;
        private string m_name;
        private Variant m_currentValue;
        private Variant m_previousValue;
        private double m_lowLimit;
        private double m_highLimit;
        private Opc.Ua.EUInformation m_engineeringUnits;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(ReportedValueDataTypeFields)).Where(x => x != nameof(ReportedValueDataTypeFields.None)).ToArray();
        #endregion
    }

    #region ReportedValueDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfReportedValueDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "ReportedValueDataType")]
    public partial class ReportedValueDataTypeCollection : List<ReportedValueDataType>, ICloneable
    {
        #region Constructors
        public ReportedValueDataTypeCollection() {}

        public ReportedValueDataTypeCollection(int capacity) : base(capacity) {}

        public ReportedValueDataTypeCollection(IEnumerable<ReportedValueDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator ReportedValueDataTypeCollection(ReportedValueDataType[] values)
        {
            if (values != null)
            {
                return new ReportedValueDataTypeCollection(values);
            }

            return new ReportedValueDataTypeCollection();
        }

        public static explicit operator ReportedValueDataType[](ReportedValueDataTypeCollection values)
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
            return (ReportedValueDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            ReportedValueDataTypeCollection clone = new ReportedValueDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((ReportedValueDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region ResultCounterDataType Class
    #if (!OPCUA_EXCLUDE_ResultCounterDataType)
    /// <exclude />
    [Flags]
    public enum ResultCounterDataTypeFields : uint
    {
        None = 0,
        Name = 0x1,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class ResultCounterDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public ResultCounterDataType()
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
            EncodingMask = (uint)ResultCounterDataTypeFields.None;
            m_name = null;
            m_counterValue = (uint)0;
            m_counterType = (short)0;
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "Name", IsRequired = false, Order = 1)]
        public string Name
        {
            get { return m_name;  }
            set { m_name = value; }
        }

        [DataMember(Name = "CounterValue", IsRequired = false, Order = 2)]
        public uint CounterValue
        {
            get { return m_counterValue;  }
            set { m_counterValue = value; }
        }

        [DataMember(Name = "CounterType", IsRequired = false, Order = 3)]
        public short CounterType
        {
            get { return m_counterType;  }
            set { m_counterType = value; }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.ResultCounterDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.ResultCounterDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.ResultCounterDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.ResultCounterDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            if ((EncodingMask & (uint)ResultCounterDataTypeFields.Name) != 0) encoder.WriteString("Name", Name);
            encoder.WriteUInt32("CounterValue", CounterValue);
            encoder.WriteInt16("CounterType", CounterType);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            if ((EncodingMask & (uint)ResultCounterDataTypeFields.Name) != 0) Name = decoder.ReadString("Name");
            CounterValue = decoder.ReadUInt32("CounterValue");
            CounterType = decoder.ReadInt16("CounterType");

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            ResultCounterDataType value = encodeable as ResultCounterDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if ((EncodingMask & (uint)ResultCounterDataTypeFields.Name) != 0) if (!Utils.IsEqual(m_name, value.m_name)) return false;
            if (!Utils.IsEqual(m_counterValue, value.m_counterValue)) return false;
            if (!Utils.IsEqual(m_counterType, value.m_counterType)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (ResultCounterDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            ResultCounterDataType clone = (ResultCounterDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            if ((EncodingMask & (uint)ResultCounterDataTypeFields.Name) != 0) clone.m_name = (string)Utils.Clone(this.m_name);
            clone.m_counterValue = (uint)Utils.Clone(this.m_counterValue);
            clone.m_counterType = (short)Utils.Clone(this.m_counterType);

            return clone;
        }
        #endregion

        #region Private Fields
        private string m_name;
        private uint m_counterValue;
        private short m_counterType;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(ResultCounterDataTypeFields)).Where(x => x != nameof(ResultCounterDataTypeFields.None)).ToArray();
        #endregion
    }

    #region ResultCounterDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfResultCounterDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "ResultCounterDataType")]
    public partial class ResultCounterDataTypeCollection : List<ResultCounterDataType>, ICloneable
    {
        #region Constructors
        public ResultCounterDataTypeCollection() {}

        public ResultCounterDataTypeCollection(int capacity) : base(capacity) {}

        public ResultCounterDataTypeCollection(IEnumerable<ResultCounterDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator ResultCounterDataTypeCollection(ResultCounterDataType[] values)
        {
            if (values != null)
            {
                return new ResultCounterDataTypeCollection(values);
            }

            return new ResultCounterDataTypeCollection();
        }

        public static explicit operator ResultCounterDataType[](ResultCounterDataTypeCollection values)
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
            return (ResultCounterDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            ResultCounterDataTypeCollection clone = new ResultCounterDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((ResultCounterDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region JoiningResultMetaDataType Class
    #if (!OPCUA_EXCLUDE_JoiningResultMetaDataType)
    /// <exclude />
    [Flags]
    public enum JoiningResultMetaDataTypeFields : uint
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
        JoiningTechnology = 0x80000,
        SequenceNumber = 0x100000,
        Name = 0x200000,
        Description = 0x400000,
        Classification = 0x800000,
        OperationMode = 0x1000000,
        AssemblyType = 0x2000000,
        AssociatedEntities = 0x4000000,
        ResultCounters = 0x8000000,
        InterventionType = 0x10000000,
        IsGeneratedOffline = 0x20000000,
        ExtendedMetaData = 0x40000000,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class JoiningResultMetaDataType : UAModel.MachineryResult.ResultMetaDataType
    {
        #region Constructors
        public JoiningResultMetaDataType()
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
            m_joiningTechnology = null;
            m_sequenceNumber = (ulong)0;
            m_name = null;
            m_description = null;
            m_classification = (byte)0;
            m_operationMode = (byte)0;
            m_assemblyType = (byte)0;
            m_associatedEntities = new EntityDataTypeCollection();
            m_resultCounters = new ResultCounterDataTypeCollection();
            m_interventionType = (byte)0;
            m_isGeneratedOffline = true;
            m_extendedMetaData = new KeyValueDataTypeCollection();
        }
        #endregion

        #region Public Properties
        
        [DataMember(Name = "JoiningTechnology", IsRequired = false, Order = 1)]
        public LocalizedText JoiningTechnology
        {
            get { return m_joiningTechnology;  }
            set { m_joiningTechnology = value; }
        }

        [DataMember(Name = "SequenceNumber", IsRequired = false, Order = 2)]
        public ulong SequenceNumber
        {
            get { return m_sequenceNumber;  }
            set { m_sequenceNumber = value; }
        }

        [DataMember(Name = "Name", IsRequired = false, Order = 3)]
        public string Name
        {
            get { return m_name;  }
            set { m_name = value; }
        }

        [DataMember(Name = "Description", IsRequired = false, Order = 4)]
        public LocalizedText Description
        {
            get { return m_description;  }
            set { m_description = value; }
        }

        [DataMember(Name = "Classification", IsRequired = false, Order = 5)]
        public byte Classification
        {
            get { return m_classification;  }
            set { m_classification = value; }
        }

        [DataMember(Name = "OperationMode", IsRequired = false, Order = 6)]
        public byte OperationMode
        {
            get { return m_operationMode;  }
            set { m_operationMode = value; }
        }

        [DataMember(Name = "AssemblyType", IsRequired = false, Order = 7)]
        public byte AssemblyType
        {
            get { return m_assemblyType;  }
            set { m_assemblyType = value; }
        }

        /// <remarks />
        [DataMember(Name = "AssociatedEntities", IsRequired = false, Order = 8)]
        public EntityDataTypeCollection AssociatedEntities
        {
            get
            {
                return m_associatedEntities;
            }

            set
            {
                m_associatedEntities = value;

                if (value == null)
                {
                    m_associatedEntities = new EntityDataTypeCollection();
                }
            }
        }

        /// <remarks />
        [DataMember(Name = "ResultCounters", IsRequired = false, Order = 9)]
        public ResultCounterDataTypeCollection ResultCounters
        {
            get
            {
                return m_resultCounters;
            }

            set
            {
                m_resultCounters = value;

                if (value == null)
                {
                    m_resultCounters = new ResultCounterDataTypeCollection();
                }
            }
        }

        [DataMember(Name = "InterventionType", IsRequired = false, Order = 10)]
        public byte InterventionType
        {
            get { return m_interventionType;  }
            set { m_interventionType = value; }
        }

        [DataMember(Name = "IsGeneratedOffline", IsRequired = false, Order = 11)]
        public bool IsGeneratedOffline
        {
            get { return m_isGeneratedOffline;  }
            set { m_isGeneratedOffline = value; }
        }

        /// <remarks />
        [DataMember(Name = "ExtendedMetaData", IsRequired = false, Order = 12)]
        public KeyValueDataTypeCollection ExtendedMetaData
        {
            get
            {
                return m_extendedMetaData;
            }

            set
            {
                m_extendedMetaData = value;

                if (value == null)
                {
                    m_extendedMetaData = new KeyValueDataTypeCollection();
                }
            }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public override ExpandedNodeId TypeId => DataTypeIds.JoiningResultMetaDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public override ExpandedNodeId BinaryEncodingId => ObjectIds.JoiningResultMetaDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public override ExpandedNodeId XmlEncodingId => ObjectIds.JoiningResultMetaDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public override ExpandedNodeId JsonEncodingId => ObjectIds.JoiningResultMetaDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public override void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            
            encoder.PopNamespace();

            base.Encode(encoder);

            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.JoiningTechnology) != 0) encoder.WriteLocalizedText("JoiningTechnology", JoiningTechnology);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.SequenceNumber) != 0) encoder.WriteUInt64("SequenceNumber", SequenceNumber);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.Name) != 0) encoder.WriteString("Name", Name);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.Description) != 0) encoder.WriteLocalizedText("Description", Description);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.Classification) != 0) encoder.WriteByte("Classification", Classification);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.OperationMode) != 0) encoder.WriteByte("OperationMode", OperationMode);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.AssemblyType) != 0) encoder.WriteByte("AssemblyType", AssemblyType);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.AssociatedEntities) != 0) encoder.WriteEncodeableArray("AssociatedEntities", AssociatedEntities.ToArray(), typeof(EntityDataType));
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.ResultCounters) != 0) encoder.WriteEncodeableArray("ResultCounters", ResultCounters.ToArray(), typeof(ResultCounterDataType));
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.InterventionType) != 0) encoder.WriteByte("InterventionType", InterventionType);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.IsGeneratedOffline) != 0) encoder.WriteBoolean("IsGeneratedOffline", IsGeneratedOffline);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.ExtendedMetaData) != 0) encoder.WriteEncodeableArray("ExtendedMetaData", ExtendedMetaData.ToArray(), typeof(KeyValueDataType));

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public override void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            
            decoder.PopNamespace();
                
            base.Decode(decoder);

            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.JoiningTechnology) != 0) JoiningTechnology = decoder.ReadLocalizedText("JoiningTechnology");
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.SequenceNumber) != 0) SequenceNumber = decoder.ReadUInt64("SequenceNumber");
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.Name) != 0) Name = decoder.ReadString("Name");
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.Description) != 0) Description = decoder.ReadLocalizedText("Description");
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.Classification) != 0) Classification = decoder.ReadByte("Classification");
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.OperationMode) != 0) OperationMode = decoder.ReadByte("OperationMode");
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.AssemblyType) != 0) AssemblyType = decoder.ReadByte("AssemblyType");
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.AssociatedEntities) != 0) AssociatedEntities = (EntityDataTypeCollection)decoder.ReadEncodeableArray("AssociatedEntities", typeof(EntityDataType));
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.ResultCounters) != 0) ResultCounters = (ResultCounterDataTypeCollection)decoder.ReadEncodeableArray("ResultCounters", typeof(ResultCounterDataType));
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.InterventionType) != 0) InterventionType = decoder.ReadByte("InterventionType");
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.IsGeneratedOffline) != 0) IsGeneratedOffline = decoder.ReadBoolean("IsGeneratedOffline");
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.ExtendedMetaData) != 0) ExtendedMetaData = (KeyValueDataTypeCollection)decoder.ReadEncodeableArray("ExtendedMetaData", typeof(KeyValueDataType));

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public override bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            JoiningResultMetaDataType value = encodeable as JoiningResultMetaDataType;

            if (value == null)
            {
                return false;
            }

            

            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.JoiningTechnology) != 0) if (!Utils.IsEqual(m_joiningTechnology, value.m_joiningTechnology)) return false;
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.SequenceNumber) != 0) if (!Utils.IsEqual(m_sequenceNumber, value.m_sequenceNumber)) return false;
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.Name) != 0) if (!Utils.IsEqual(m_name, value.m_name)) return false;
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.Description) != 0) if (!Utils.IsEqual(m_description, value.m_description)) return false;
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.Classification) != 0) if (!Utils.IsEqual(m_classification, value.m_classification)) return false;
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.OperationMode) != 0) if (!Utils.IsEqual(m_operationMode, value.m_operationMode)) return false;
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.AssemblyType) != 0) if (!Utils.IsEqual(m_assemblyType, value.m_assemblyType)) return false;
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.AssociatedEntities) != 0) if (!Utils.IsEqual(m_associatedEntities, value.m_associatedEntities)) return false;
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.ResultCounters) != 0) if (!Utils.IsEqual(m_resultCounters, value.m_resultCounters)) return false;
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.InterventionType) != 0) if (!Utils.IsEqual(m_interventionType, value.m_interventionType)) return false;
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.IsGeneratedOffline) != 0) if (!Utils.IsEqual(m_isGeneratedOffline, value.m_isGeneratedOffline)) return false;
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.ExtendedMetaData) != 0) if (!Utils.IsEqual(m_extendedMetaData, value.m_extendedMetaData)) return false;

            return base.IsEqual(encodeable);
        }

        /// <summary cref="ICloneable.Clone" />
        public override object Clone()
        {
            return (JoiningResultMetaDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JoiningResultMetaDataType clone = (JoiningResultMetaDataType)base.MemberwiseClone();
                
            
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.JoiningTechnology) != 0) clone.m_joiningTechnology = (LocalizedText)Utils.Clone(this.m_joiningTechnology);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.SequenceNumber) != 0) clone.m_sequenceNumber = (ulong)Utils.Clone(this.m_sequenceNumber);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.Name) != 0) clone.m_name = (string)Utils.Clone(this.m_name);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.Description) != 0) clone.m_description = (LocalizedText)Utils.Clone(this.m_description);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.Classification) != 0) clone.m_classification = (byte)Utils.Clone(this.m_classification);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.OperationMode) != 0) clone.m_operationMode = (byte)Utils.Clone(this.m_operationMode);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.AssemblyType) != 0) clone.m_assemblyType = (byte)Utils.Clone(this.m_assemblyType);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.AssociatedEntities) != 0) clone.m_associatedEntities = (EntityDataTypeCollection)Utils.Clone(this.m_associatedEntities);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.ResultCounters) != 0) clone.m_resultCounters = (ResultCounterDataTypeCollection)Utils.Clone(this.m_resultCounters);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.InterventionType) != 0) clone.m_interventionType = (byte)Utils.Clone(this.m_interventionType);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.IsGeneratedOffline) != 0) clone.m_isGeneratedOffline = (bool)Utils.Clone(this.m_isGeneratedOffline);
            if ((EncodingMask & (uint)JoiningResultMetaDataTypeFields.ExtendedMetaData) != 0) clone.m_extendedMetaData = (KeyValueDataTypeCollection)Utils.Clone(this.m_extendedMetaData);

            return clone;
        }
        #endregion

        #region Private Fields
        private LocalizedText m_joiningTechnology;
        private ulong m_sequenceNumber;
        private string m_name;
        private LocalizedText m_description;
        private byte m_classification;
        private byte m_operationMode;
        private byte m_assemblyType;
        private EntityDataTypeCollection m_associatedEntities;
        private ResultCounterDataTypeCollection m_resultCounters;
        private byte m_interventionType;
        private bool m_isGeneratedOffline;
        private KeyValueDataTypeCollection m_extendedMetaData;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(JoiningResultMetaDataTypeFields)).Where(x => x != nameof(JoiningResultMetaDataTypeFields.None)).ToArray();
        #endregion
    }

    #region JoiningResultMetaDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfJoiningResultMetaDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "JoiningResultMetaDataType")]
    public partial class JoiningResultMetaDataTypeCollection : List<JoiningResultMetaDataType>, ICloneable
    {
        #region Constructors
        public JoiningResultMetaDataTypeCollection() {}

        public JoiningResultMetaDataTypeCollection(int capacity) : base(capacity) {}

        public JoiningResultMetaDataTypeCollection(IEnumerable<JoiningResultMetaDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator JoiningResultMetaDataTypeCollection(JoiningResultMetaDataType[] values)
        {
            if (values != null)
            {
                return new JoiningResultMetaDataTypeCollection(values);
            }

            return new JoiningResultMetaDataTypeCollection();
        }

        public static explicit operator JoiningResultMetaDataType[](JoiningResultMetaDataTypeCollection values)
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
            return (JoiningResultMetaDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JoiningResultMetaDataTypeCollection clone = new JoiningResultMetaDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((JoiningResultMetaDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region ResultValueDataType Class
    #if (!OPCUA_EXCLUDE_ResultValueDataType)
    /// <exclude />
    [Flags]
    public enum ResultValueDataTypeFields : uint
    {
        None = 0,
        Name = 0x1,
        ResultEvaluation = 0x2,
        ValueId = 0x4,
        ValueTag = 0x8,
        TracePointIndex = 0x10,
        TracePointTimeOffset = 0x20,
        ParameterIdList = 0x40,
        ViolationType = 0x80,
        ViolationConsequence = 0x100,
        SensorId = 0x200,
        LowLimit = 0x400,
        High = 0x800,
        TargetValue = 0x1000,
        ResultStep = 0x2000,
        PhysicalQuantity = 0x4000,
        EngineeringUnits = 0x8000,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class ResultValueDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public ResultValueDataType()
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
            EncodingMask = (uint)ResultValueDataTypeFields.None;
            m_measuredValue = (double)0;
            m_name = null;
            m_resultEvaluation = ResultEvaluationEnum.Undefined;
            m_valueId = null;
            m_valueTag = (short)0;
            m_tracePointIndex = (int)0;
            m_tracePointTimeOffset = (double)0;
            m_parameterIdList = new StringCollection();
            m_violationType = (byte)0;
            m_violationConsequence = (byte)0;
            m_sensorId = null;
            m_lowLimit = (double)0;
            m_high = (double)0;
            m_targetValue = (double)0;
            m_resultStep = null;
            m_physicalQuantity = (byte)0;
            m_engineeringUnits = new Opc.Ua.EUInformation();
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "MeasuredValue", IsRequired = false, Order = 1)]
        public double MeasuredValue
        {
            get { return m_measuredValue;  }
            set { m_measuredValue = value; }
        }

        [DataMember(Name = "Name", IsRequired = false, Order = 2)]
        public string Name
        {
            get { return m_name;  }
            set { m_name = value; }
        }

        [DataMember(Name = "ResultEvaluation", IsRequired = false, Order = 3)]
        public ResultEvaluationEnum ResultEvaluation
        {
            get { return m_resultEvaluation;  }
            set { m_resultEvaluation = value; }
        }

        [DataMember(Name = "ValueId", IsRequired = false, Order = 4)]
        public string ValueId
        {
            get { return m_valueId;  }
            set { m_valueId = value; }
        }

        [DataMember(Name = "ValueTag", IsRequired = false, Order = 5)]
        public short ValueTag
        {
            get { return m_valueTag;  }
            set { m_valueTag = value; }
        }

        [DataMember(Name = "TracePointIndex", IsRequired = false, Order = 6)]
        public int TracePointIndex
        {
            get { return m_tracePointIndex;  }
            set { m_tracePointIndex = value; }
        }

        [DataMember(Name = "TracePointTimeOffset", IsRequired = false, Order = 7)]
        public double TracePointTimeOffset
        {
            get { return m_tracePointTimeOffset;  }
            set { m_tracePointTimeOffset = value; }
        }

        /// <remarks />
        [DataMember(Name = "ParameterIdList", IsRequired = false, Order = 8)]
        public StringCollection ParameterIdList
        {
            get
            {
                return m_parameterIdList;
            }

            set
            {
                m_parameterIdList = value;

                if (value == null)
                {
                    m_parameterIdList = new StringCollection();
                }
            }
        }

        [DataMember(Name = "ViolationType", IsRequired = false, Order = 9)]
        public byte ViolationType
        {
            get { return m_violationType;  }
            set { m_violationType = value; }
        }

        [DataMember(Name = "ViolationConsequence", IsRequired = false, Order = 10)]
        public byte ViolationConsequence
        {
            get { return m_violationConsequence;  }
            set { m_violationConsequence = value; }
        }

        [DataMember(Name = "SensorId", IsRequired = false, Order = 11)]
        public string SensorId
        {
            get { return m_sensorId;  }
            set { m_sensorId = value; }
        }

        [DataMember(Name = "LowLimit", IsRequired = false, Order = 12)]
        public double LowLimit
        {
            get { return m_lowLimit;  }
            set { m_lowLimit = value; }
        }

        [DataMember(Name = "High", IsRequired = false, Order = 13)]
        public double High
        {
            get { return m_high;  }
            set { m_high = value; }
        }

        [DataMember(Name = "TargetValue", IsRequired = false, Order = 14)]
        public double TargetValue
        {
            get { return m_targetValue;  }
            set { m_targetValue = value; }
        }

        [DataMember(Name = "ResultStep", IsRequired = false, Order = 15)]
        public string ResultStep
        {
            get { return m_resultStep;  }
            set { m_resultStep = value; }
        }

        [DataMember(Name = "PhysicalQuantity", IsRequired = false, Order = 16)]
        public byte PhysicalQuantity
        {
            get { return m_physicalQuantity;  }
            set { m_physicalQuantity = value; }
        }

        /// <remarks />
        [DataMember(Name = "EngineeringUnits", IsRequired = false, Order = 17)]
        public Opc.Ua.EUInformation EngineeringUnits
        {
            get
            {
                return m_engineeringUnits;
            }

            set
            {
                m_engineeringUnits = value;

                if (value == null)
                {
                    m_engineeringUnits = new Opc.Ua.EUInformation();
                }
            }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.ResultValueDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.ResultValueDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.ResultValueDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.ResultValueDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            encoder.WriteDouble("MeasuredValue", MeasuredValue);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.Name) != 0) encoder.WriteString("Name", Name);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ResultEvaluation) != 0) encoder.WriteEnumerated("ResultEvaluation", ResultEvaluation);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ValueId) != 0) encoder.WriteString("ValueId", ValueId);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ValueTag) != 0) encoder.WriteInt16("ValueTag", ValueTag);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.TracePointIndex) != 0) encoder.WriteInt32("TracePointIndex", TracePointIndex);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.TracePointTimeOffset) != 0) encoder.WriteDouble("TracePointTimeOffset", TracePointTimeOffset);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ParameterIdList) != 0) encoder.WriteStringArray("ParameterIdList", ParameterIdList);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ViolationType) != 0) encoder.WriteByte("ViolationType", ViolationType);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ViolationConsequence) != 0) encoder.WriteByte("ViolationConsequence", ViolationConsequence);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.SensorId) != 0) encoder.WriteString("SensorId", SensorId);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.LowLimit) != 0) encoder.WriteDouble("LowLimit", LowLimit);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.High) != 0) encoder.WriteDouble("High", High);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.TargetValue) != 0) encoder.WriteDouble("TargetValue", TargetValue);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ResultStep) != 0) encoder.WriteString("ResultStep", ResultStep);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.PhysicalQuantity) != 0) encoder.WriteByte("PhysicalQuantity", PhysicalQuantity);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.EngineeringUnits) != 0) encoder.WriteEncodeable("EngineeringUnits", EngineeringUnits, typeof(Opc.Ua.EUInformation));

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            MeasuredValue = decoder.ReadDouble("MeasuredValue");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.Name) != 0) Name = decoder.ReadString("Name");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ResultEvaluation) != 0) ResultEvaluation = (ResultEvaluationEnum)decoder.ReadEnumerated("ResultEvaluation", typeof(ResultEvaluationEnum));
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ValueId) != 0) ValueId = decoder.ReadString("ValueId");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ValueTag) != 0) ValueTag = decoder.ReadInt16("ValueTag");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.TracePointIndex) != 0) TracePointIndex = decoder.ReadInt32("TracePointIndex");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.TracePointTimeOffset) != 0) TracePointTimeOffset = decoder.ReadDouble("TracePointTimeOffset");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ParameterIdList) != 0) ParameterIdList = decoder.ReadStringArray("ParameterIdList");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ViolationType) != 0) ViolationType = decoder.ReadByte("ViolationType");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ViolationConsequence) != 0) ViolationConsequence = decoder.ReadByte("ViolationConsequence");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.SensorId) != 0) SensorId = decoder.ReadString("SensorId");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.LowLimit) != 0) LowLimit = decoder.ReadDouble("LowLimit");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.High) != 0) High = decoder.ReadDouble("High");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.TargetValue) != 0) TargetValue = decoder.ReadDouble("TargetValue");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ResultStep) != 0) ResultStep = decoder.ReadString("ResultStep");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.PhysicalQuantity) != 0) PhysicalQuantity = decoder.ReadByte("PhysicalQuantity");
            if ((EncodingMask & (uint)ResultValueDataTypeFields.EngineeringUnits) != 0) EngineeringUnits = (Opc.Ua.EUInformation)decoder.ReadEncodeable("EngineeringUnits", typeof(Opc.Ua.EUInformation));

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            ResultValueDataType value = encodeable as ResultValueDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if (!Utils.IsEqual(m_measuredValue, value.m_measuredValue)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.Name) != 0) if (!Utils.IsEqual(m_name, value.m_name)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ResultEvaluation) != 0) if (!Utils.IsEqual(m_resultEvaluation, value.m_resultEvaluation)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ValueId) != 0) if (!Utils.IsEqual(m_valueId, value.m_valueId)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ValueTag) != 0) if (!Utils.IsEqual(m_valueTag, value.m_valueTag)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.TracePointIndex) != 0) if (!Utils.IsEqual(m_tracePointIndex, value.m_tracePointIndex)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.TracePointTimeOffset) != 0) if (!Utils.IsEqual(m_tracePointTimeOffset, value.m_tracePointTimeOffset)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ParameterIdList) != 0) if (!Utils.IsEqual(m_parameterIdList, value.m_parameterIdList)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ViolationType) != 0) if (!Utils.IsEqual(m_violationType, value.m_violationType)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ViolationConsequence) != 0) if (!Utils.IsEqual(m_violationConsequence, value.m_violationConsequence)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.SensorId) != 0) if (!Utils.IsEqual(m_sensorId, value.m_sensorId)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.LowLimit) != 0) if (!Utils.IsEqual(m_lowLimit, value.m_lowLimit)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.High) != 0) if (!Utils.IsEqual(m_high, value.m_high)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.TargetValue) != 0) if (!Utils.IsEqual(m_targetValue, value.m_targetValue)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ResultStep) != 0) if (!Utils.IsEqual(m_resultStep, value.m_resultStep)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.PhysicalQuantity) != 0) if (!Utils.IsEqual(m_physicalQuantity, value.m_physicalQuantity)) return false;
            if ((EncodingMask & (uint)ResultValueDataTypeFields.EngineeringUnits) != 0) if (!Utils.IsEqual(m_engineeringUnits, value.m_engineeringUnits)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (ResultValueDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            ResultValueDataType clone = (ResultValueDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            clone.m_measuredValue = (double)Utils.Clone(this.m_measuredValue);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.Name) != 0) clone.m_name = (string)Utils.Clone(this.m_name);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ResultEvaluation) != 0) clone.m_resultEvaluation = (ResultEvaluationEnum)Utils.Clone(this.m_resultEvaluation);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ValueId) != 0) clone.m_valueId = (string)Utils.Clone(this.m_valueId);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ValueTag) != 0) clone.m_valueTag = (short)Utils.Clone(this.m_valueTag);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.TracePointIndex) != 0) clone.m_tracePointIndex = (int)Utils.Clone(this.m_tracePointIndex);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.TracePointTimeOffset) != 0) clone.m_tracePointTimeOffset = (double)Utils.Clone(this.m_tracePointTimeOffset);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ParameterIdList) != 0) clone.m_parameterIdList = (StringCollection)Utils.Clone(this.m_parameterIdList);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ViolationType) != 0) clone.m_violationType = (byte)Utils.Clone(this.m_violationType);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ViolationConsequence) != 0) clone.m_violationConsequence = (byte)Utils.Clone(this.m_violationConsequence);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.SensorId) != 0) clone.m_sensorId = (string)Utils.Clone(this.m_sensorId);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.LowLimit) != 0) clone.m_lowLimit = (double)Utils.Clone(this.m_lowLimit);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.High) != 0) clone.m_high = (double)Utils.Clone(this.m_high);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.TargetValue) != 0) clone.m_targetValue = (double)Utils.Clone(this.m_targetValue);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.ResultStep) != 0) clone.m_resultStep = (string)Utils.Clone(this.m_resultStep);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.PhysicalQuantity) != 0) clone.m_physicalQuantity = (byte)Utils.Clone(this.m_physicalQuantity);
            if ((EncodingMask & (uint)ResultValueDataTypeFields.EngineeringUnits) != 0) clone.m_engineeringUnits = (Opc.Ua.EUInformation)Utils.Clone(this.m_engineeringUnits);

            return clone;
        }
        #endregion

        #region Private Fields
        private double m_measuredValue;
        private string m_name;
        private ResultEvaluationEnum m_resultEvaluation;
        private string m_valueId;
        private short m_valueTag;
        private int m_tracePointIndex;
        private double m_tracePointTimeOffset;
        private StringCollection m_parameterIdList;
        private byte m_violationType;
        private byte m_violationConsequence;
        private string m_sensorId;
        private double m_lowLimit;
        private double m_high;
        private double m_targetValue;
        private string m_resultStep;
        private byte m_physicalQuantity;
        private Opc.Ua.EUInformation m_engineeringUnits;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(ResultValueDataTypeFields)).Where(x => x != nameof(ResultValueDataTypeFields.None)).ToArray();
        #endregion
    }

    #region ResultValueDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfResultValueDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "ResultValueDataType")]
    public partial class ResultValueDataTypeCollection : List<ResultValueDataType>, ICloneable
    {
        #region Constructors
        public ResultValueDataTypeCollection() {}

        public ResultValueDataTypeCollection(int capacity) : base(capacity) {}

        public ResultValueDataTypeCollection(IEnumerable<ResultValueDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator ResultValueDataTypeCollection(ResultValueDataType[] values)
        {
            if (values != null)
            {
                return new ResultValueDataTypeCollection(values);
            }

            return new ResultValueDataTypeCollection();
        }

        public static explicit operator ResultValueDataType[](ResultValueDataTypeCollection values)
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
            return (ResultValueDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            ResultValueDataTypeCollection clone = new ResultValueDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((ResultValueDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region SignalDataType Class
    #if (!OPCUA_EXCLUDE_SignalDataType)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class SignalDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public SignalDataType()
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
            m_signalId = null;
            m_signalValue = (double)0;
            m_signalDescription = null;
            m_signalType = (short)0;
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "SignalId", IsRequired = false, Order = 1)]
        public string SignalId
        {
            get { return m_signalId;  }
            set { m_signalId = value; }
        }

        [DataMember(Name = "SignalValue", IsRequired = false, Order = 2)]
        public Variant SignalValue
        {
            get { return m_signalValue;  }
            set { m_signalValue = value; }
        }

        [DataMember(Name = "SignalDescription", IsRequired = false, Order = 3)]
        public string SignalDescription
        {
            get { return m_signalDescription;  }
            set { m_signalDescription = value; }
        }

        [DataMember(Name = "SignalType", IsRequired = false, Order = 4)]
        public short SignalType
        {
            get { return m_signalType;  }
            set { m_signalType = value; }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.SignalDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.SignalDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.SignalDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.SignalDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            encoder.WriteString("SignalId", SignalId);
            encoder.WriteVariant("SignalValue", SignalValue);
            encoder.WriteString("SignalDescription", SignalDescription);
            encoder.WriteInt16("SignalType", SignalType);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            SignalId = decoder.ReadString("SignalId");
            SignalValue = decoder.ReadVariant("SignalValue");
            SignalDescription = decoder.ReadString("SignalDescription");
            SignalType = decoder.ReadInt16("SignalType");

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            SignalDataType value = encodeable as SignalDataType;

            if (value == null)
            {
                return false;
            }

            if (!Utils.IsEqual(m_signalId, value.m_signalId)) return false;
            if (!Utils.IsEqual(m_signalValue, value.m_signalValue)) return false;
            if (!Utils.IsEqual(m_signalDescription, value.m_signalDescription)) return false;
            if (!Utils.IsEqual(m_signalType, value.m_signalType)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (SignalDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            SignalDataType clone = (SignalDataType)base.MemberwiseClone();

            clone.m_signalId = (string)Utils.Clone(this.m_signalId);
            clone.m_signalValue = (Variant)Utils.Clone(this.m_signalValue);
            clone.m_signalDescription = (string)Utils.Clone(this.m_signalDescription);
            clone.m_signalType = (short)Utils.Clone(this.m_signalType);

            return clone;
        }
        #endregion

        #region Private Fields
        private string m_signalId;
        private Variant m_signalValue;
        private string m_signalDescription;
        private short m_signalType;
        #endregion
    }

    #region SignalDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfSignalDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "SignalDataType")]
    public partial class SignalDataTypeCollection : List<SignalDataType>, ICloneable
    {
        #region Constructors
        public SignalDataTypeCollection() {}

        public SignalDataTypeCollection(int capacity) : base(capacity) {}

        public SignalDataTypeCollection(IEnumerable<SignalDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator SignalDataTypeCollection(SignalDataType[] values)
        {
            if (values != null)
            {
                return new SignalDataTypeCollection(values);
            }

            return new SignalDataTypeCollection();
        }

        public static explicit operator SignalDataType[](SignalDataTypeCollection values)
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
            return (SignalDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            SignalDataTypeCollection clone = new SignalDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((SignalDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region StepResultDataType Class
    #if (!OPCUA_EXCLUDE_StepResultDataType)
    /// <exclude />
    [Flags]
    public enum StepResultDataTypeFields : uint
    {
        None = 0,
        ProgramStepId = 0x1,
        ProgramStep = 0x2,
        Name = 0x4,
        ResultEvaluation = 0x8,
        StartTimeOffset = 0x10,
        StepTraceId = 0x20,
        StepResultValues = 0x40,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class StepResultDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public StepResultDataType()
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
            EncodingMask = (uint)StepResultDataTypeFields.None;
            m_stepResultId = null;
            m_programStepId = null;
            m_programStep = null;
            m_name = null;
            m_resultEvaluation = ResultEvaluationEnum.Undefined;
            m_startTimeOffset = (double)0;
            m_stepTraceId = null;
            m_stepResultValues = new ResultValueDataTypeCollection();
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "StepResultId", IsRequired = false, Order = 1)]
        public string StepResultId
        {
            get { return m_stepResultId;  }
            set { m_stepResultId = value; }
        }

        [DataMember(Name = "ProgramStepId", IsRequired = false, Order = 2)]
        public string ProgramStepId
        {
            get { return m_programStepId;  }
            set { m_programStepId = value; }
        }

        [DataMember(Name = "ProgramStep", IsRequired = false, Order = 3)]
        public string ProgramStep
        {
            get { return m_programStep;  }
            set { m_programStep = value; }
        }

        [DataMember(Name = "Name", IsRequired = false, Order = 4)]
        public string Name
        {
            get { return m_name;  }
            set { m_name = value; }
        }

        [DataMember(Name = "ResultEvaluation", IsRequired = false, Order = 5)]
        public ResultEvaluationEnum ResultEvaluation
        {
            get { return m_resultEvaluation;  }
            set { m_resultEvaluation = value; }
        }

        [DataMember(Name = "StartTimeOffset", IsRequired = false, Order = 6)]
        public double StartTimeOffset
        {
            get { return m_startTimeOffset;  }
            set { m_startTimeOffset = value; }
        }

        [DataMember(Name = "StepTraceId", IsRequired = false, Order = 7)]
        public string StepTraceId
        {
            get { return m_stepTraceId;  }
            set { m_stepTraceId = value; }
        }

        /// <remarks />
        [DataMember(Name = "StepResultValues", IsRequired = false, Order = 8)]
        public ResultValueDataTypeCollection StepResultValues
        {
            get
            {
                return m_stepResultValues;
            }

            set
            {
                m_stepResultValues = value;

                if (value == null)
                {
                    m_stepResultValues = new ResultValueDataTypeCollection();
                }
            }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.StepResultDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.StepResultDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.StepResultDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.StepResultDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            encoder.WriteString("StepResultId", StepResultId);
            if ((EncodingMask & (uint)StepResultDataTypeFields.ProgramStepId) != 0) encoder.WriteString("ProgramStepId", ProgramStepId);
            if ((EncodingMask & (uint)StepResultDataTypeFields.ProgramStep) != 0) encoder.WriteString("ProgramStep", ProgramStep);
            if ((EncodingMask & (uint)StepResultDataTypeFields.Name) != 0) encoder.WriteString("Name", Name);
            if ((EncodingMask & (uint)StepResultDataTypeFields.ResultEvaluation) != 0) encoder.WriteEnumerated("ResultEvaluation", ResultEvaluation);
            if ((EncodingMask & (uint)StepResultDataTypeFields.StartTimeOffset) != 0) encoder.WriteDouble("StartTimeOffset", StartTimeOffset);
            if ((EncodingMask & (uint)StepResultDataTypeFields.StepTraceId) != 0) encoder.WriteString("StepTraceId", StepTraceId);
            if ((EncodingMask & (uint)StepResultDataTypeFields.StepResultValues) != 0) encoder.WriteEncodeableArray("StepResultValues", StepResultValues.ToArray(), typeof(ResultValueDataType));

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            StepResultId = decoder.ReadString("StepResultId");
            if ((EncodingMask & (uint)StepResultDataTypeFields.ProgramStepId) != 0) ProgramStepId = decoder.ReadString("ProgramStepId");
            if ((EncodingMask & (uint)StepResultDataTypeFields.ProgramStep) != 0) ProgramStep = decoder.ReadString("ProgramStep");
            if ((EncodingMask & (uint)StepResultDataTypeFields.Name) != 0) Name = decoder.ReadString("Name");
            if ((EncodingMask & (uint)StepResultDataTypeFields.ResultEvaluation) != 0) ResultEvaluation = (ResultEvaluationEnum)decoder.ReadEnumerated("ResultEvaluation", typeof(ResultEvaluationEnum));
            if ((EncodingMask & (uint)StepResultDataTypeFields.StartTimeOffset) != 0) StartTimeOffset = decoder.ReadDouble("StartTimeOffset");
            if ((EncodingMask & (uint)StepResultDataTypeFields.StepTraceId) != 0) StepTraceId = decoder.ReadString("StepTraceId");
            if ((EncodingMask & (uint)StepResultDataTypeFields.StepResultValues) != 0) StepResultValues = (ResultValueDataTypeCollection)decoder.ReadEncodeableArray("StepResultValues", typeof(ResultValueDataType));

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            StepResultDataType value = encodeable as StepResultDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if (!Utils.IsEqual(m_stepResultId, value.m_stepResultId)) return false;
            if ((EncodingMask & (uint)StepResultDataTypeFields.ProgramStepId) != 0) if (!Utils.IsEqual(m_programStepId, value.m_programStepId)) return false;
            if ((EncodingMask & (uint)StepResultDataTypeFields.ProgramStep) != 0) if (!Utils.IsEqual(m_programStep, value.m_programStep)) return false;
            if ((EncodingMask & (uint)StepResultDataTypeFields.Name) != 0) if (!Utils.IsEqual(m_name, value.m_name)) return false;
            if ((EncodingMask & (uint)StepResultDataTypeFields.ResultEvaluation) != 0) if (!Utils.IsEqual(m_resultEvaluation, value.m_resultEvaluation)) return false;
            if ((EncodingMask & (uint)StepResultDataTypeFields.StartTimeOffset) != 0) if (!Utils.IsEqual(m_startTimeOffset, value.m_startTimeOffset)) return false;
            if ((EncodingMask & (uint)StepResultDataTypeFields.StepTraceId) != 0) if (!Utils.IsEqual(m_stepTraceId, value.m_stepTraceId)) return false;
            if ((EncodingMask & (uint)StepResultDataTypeFields.StepResultValues) != 0) if (!Utils.IsEqual(m_stepResultValues, value.m_stepResultValues)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (StepResultDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            StepResultDataType clone = (StepResultDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            clone.m_stepResultId = (string)Utils.Clone(this.m_stepResultId);
            if ((EncodingMask & (uint)StepResultDataTypeFields.ProgramStepId) != 0) clone.m_programStepId = (string)Utils.Clone(this.m_programStepId);
            if ((EncodingMask & (uint)StepResultDataTypeFields.ProgramStep) != 0) clone.m_programStep = (string)Utils.Clone(this.m_programStep);
            if ((EncodingMask & (uint)StepResultDataTypeFields.Name) != 0) clone.m_name = (string)Utils.Clone(this.m_name);
            if ((EncodingMask & (uint)StepResultDataTypeFields.ResultEvaluation) != 0) clone.m_resultEvaluation = (ResultEvaluationEnum)Utils.Clone(this.m_resultEvaluation);
            if ((EncodingMask & (uint)StepResultDataTypeFields.StartTimeOffset) != 0) clone.m_startTimeOffset = (double)Utils.Clone(this.m_startTimeOffset);
            if ((EncodingMask & (uint)StepResultDataTypeFields.StepTraceId) != 0) clone.m_stepTraceId = (string)Utils.Clone(this.m_stepTraceId);
            if ((EncodingMask & (uint)StepResultDataTypeFields.StepResultValues) != 0) clone.m_stepResultValues = (ResultValueDataTypeCollection)Utils.Clone(this.m_stepResultValues);

            return clone;
        }
        #endregion

        #region Private Fields
        private string m_stepResultId;
        private string m_programStepId;
        private string m_programStep;
        private string m_name;
        private ResultEvaluationEnum m_resultEvaluation;
        private double m_startTimeOffset;
        private string m_stepTraceId;
        private ResultValueDataTypeCollection m_stepResultValues;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(StepResultDataTypeFields)).Where(x => x != nameof(StepResultDataTypeFields.None)).ToArray();
        #endregion
    }

    #region StepResultDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfStepResultDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "StepResultDataType")]
    public partial class StepResultDataTypeCollection : List<StepResultDataType>, ICloneable
    {
        #region Constructors
        public StepResultDataTypeCollection() {}

        public StepResultDataTypeCollection(int capacity) : base(capacity) {}

        public StepResultDataTypeCollection(IEnumerable<StepResultDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator StepResultDataTypeCollection(StepResultDataType[] values)
        {
            if (values != null)
            {
                return new StepResultDataTypeCollection(values);
            }

            return new StepResultDataTypeCollection();
        }

        public static explicit operator StepResultDataType[](StepResultDataTypeCollection values)
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
            return (StepResultDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            StepResultDataTypeCollection clone = new StepResultDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((StepResultDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region StepTraceDataType Class
    #if (!OPCUA_EXCLUDE_StepTraceDataType)
    /// <exclude />
    [Flags]
    public enum StepTraceDataTypeFields : uint
    {
        None = 0,
        SamplingInterval = 0x1,
        StartTimeOffset = 0x2,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class StepTraceDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public StepTraceDataType()
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
            EncodingMask = (uint)StepTraceDataTypeFields.None;
            m_stepTraceId = null;
            m_stepResultId = null;
            m_numberOfTracePoints = (uint)0;
            m_samplingInterval = (double)0;
            m_startTimeOffset = (double)0;
            m_stepTraceContent = new TraceContentDataTypeCollection();
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "StepTraceId", IsRequired = false, Order = 1)]
        public string StepTraceId
        {
            get { return m_stepTraceId;  }
            set { m_stepTraceId = value; }
        }

        [DataMember(Name = "StepResultId", IsRequired = false, Order = 2)]
        public string StepResultId
        {
            get { return m_stepResultId;  }
            set { m_stepResultId = value; }
        }

        [DataMember(Name = "NumberOfTracePoints", IsRequired = false, Order = 3)]
        public uint NumberOfTracePoints
        {
            get { return m_numberOfTracePoints;  }
            set { m_numberOfTracePoints = value; }
        }

        [DataMember(Name = "SamplingInterval", IsRequired = false, Order = 4)]
        public double SamplingInterval
        {
            get { return m_samplingInterval;  }
            set { m_samplingInterval = value; }
        }

        [DataMember(Name = "StartTimeOffset", IsRequired = false, Order = 5)]
        public double StartTimeOffset
        {
            get { return m_startTimeOffset;  }
            set { m_startTimeOffset = value; }
        }

        /// <remarks />
        [DataMember(Name = "StepTraceContent", IsRequired = false, Order = 6)]
        public TraceContentDataTypeCollection StepTraceContent
        {
            get
            {
                return m_stepTraceContent;
            }

            set
            {
                m_stepTraceContent = value;

                if (value == null)
                {
                    m_stepTraceContent = new TraceContentDataTypeCollection();
                }
            }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.StepTraceDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.StepTraceDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.StepTraceDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.StepTraceDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            encoder.WriteString("StepTraceId", StepTraceId);
            encoder.WriteString("StepResultId", StepResultId);
            encoder.WriteUInt32("NumberOfTracePoints", NumberOfTracePoints);
            if ((EncodingMask & (uint)StepTraceDataTypeFields.SamplingInterval) != 0) encoder.WriteDouble("SamplingInterval", SamplingInterval);
            if ((EncodingMask & (uint)StepTraceDataTypeFields.StartTimeOffset) != 0) encoder.WriteDouble("StartTimeOffset", StartTimeOffset);
            encoder.WriteEncodeableArray("StepTraceContent", StepTraceContent.ToArray(), typeof(TraceContentDataType));

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            StepTraceId = decoder.ReadString("StepTraceId");
            StepResultId = decoder.ReadString("StepResultId");
            NumberOfTracePoints = decoder.ReadUInt32("NumberOfTracePoints");
            if ((EncodingMask & (uint)StepTraceDataTypeFields.SamplingInterval) != 0) SamplingInterval = decoder.ReadDouble("SamplingInterval");
            if ((EncodingMask & (uint)StepTraceDataTypeFields.StartTimeOffset) != 0) StartTimeOffset = decoder.ReadDouble("StartTimeOffset");
            StepTraceContent = (TraceContentDataTypeCollection)decoder.ReadEncodeableArray("StepTraceContent", typeof(TraceContentDataType));

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            StepTraceDataType value = encodeable as StepTraceDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if (!Utils.IsEqual(m_stepTraceId, value.m_stepTraceId)) return false;
            if (!Utils.IsEqual(m_stepResultId, value.m_stepResultId)) return false;
            if (!Utils.IsEqual(m_numberOfTracePoints, value.m_numberOfTracePoints)) return false;
            if ((EncodingMask & (uint)StepTraceDataTypeFields.SamplingInterval) != 0) if (!Utils.IsEqual(m_samplingInterval, value.m_samplingInterval)) return false;
            if ((EncodingMask & (uint)StepTraceDataTypeFields.StartTimeOffset) != 0) if (!Utils.IsEqual(m_startTimeOffset, value.m_startTimeOffset)) return false;
            if (!Utils.IsEqual(m_stepTraceContent, value.m_stepTraceContent)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (StepTraceDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            StepTraceDataType clone = (StepTraceDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            clone.m_stepTraceId = (string)Utils.Clone(this.m_stepTraceId);
            clone.m_stepResultId = (string)Utils.Clone(this.m_stepResultId);
            clone.m_numberOfTracePoints = (uint)Utils.Clone(this.m_numberOfTracePoints);
            if ((EncodingMask & (uint)StepTraceDataTypeFields.SamplingInterval) != 0) clone.m_samplingInterval = (double)Utils.Clone(this.m_samplingInterval);
            if ((EncodingMask & (uint)StepTraceDataTypeFields.StartTimeOffset) != 0) clone.m_startTimeOffset = (double)Utils.Clone(this.m_startTimeOffset);
            clone.m_stepTraceContent = (TraceContentDataTypeCollection)Utils.Clone(this.m_stepTraceContent);

            return clone;
        }
        #endregion

        #region Private Fields
        private string m_stepTraceId;
        private string m_stepResultId;
        private uint m_numberOfTracePoints;
        private double m_samplingInterval;
        private double m_startTimeOffset;
        private TraceContentDataTypeCollection m_stepTraceContent;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(StepTraceDataTypeFields)).Where(x => x != nameof(StepTraceDataTypeFields.None)).ToArray();
        #endregion
    }

    #region StepTraceDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfStepTraceDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "StepTraceDataType")]
    public partial class StepTraceDataTypeCollection : List<StepTraceDataType>, ICloneable
    {
        #region Constructors
        public StepTraceDataTypeCollection() {}

        public StepTraceDataTypeCollection(int capacity) : base(capacity) {}

        public StepTraceDataTypeCollection(IEnumerable<StepTraceDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator StepTraceDataTypeCollection(StepTraceDataType[] values)
        {
            if (values != null)
            {
                return new StepTraceDataTypeCollection(values);
            }

            return new StepTraceDataTypeCollection();
        }

        public static explicit operator StepTraceDataType[](StepTraceDataTypeCollection values)
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
            return (StepTraceDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            StepTraceDataTypeCollection clone = new StepTraceDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((StepTraceDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region TraceContentDataType Class
    #if (!OPCUA_EXCLUDE_TraceContentDataType)
    /// <exclude />
    [Flags]
    public enum TraceContentDataTypeFields : uint
    {
        None = 0,
        SensorId = 0x1,
        Name = 0x2,
        Description = 0x4,
        PhysicalQuantity = 0x8,
        EngineeringUnits = 0x10,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class TraceContentDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public TraceContentDataType()
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
            EncodingMask = (uint)TraceContentDataTypeFields.None;
            m_values = new DoubleCollection();
            m_sensorId = null;
            m_name = null;
            m_description = null;
            m_physicalQuantity = (byte)0;
            m_engineeringUnits = new Opc.Ua.EUInformation();
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        /// <remarks />
        [DataMember(Name = "Values", IsRequired = false, Order = 1)]
        public DoubleCollection Values
        {
            get
            {
                return m_values;
            }

            set
            {
                m_values = value;

                if (value == null)
                {
                    m_values = new DoubleCollection();
                }
            }
        }

        [DataMember(Name = "SensorId", IsRequired = false, Order = 2)]
        public string SensorId
        {
            get { return m_sensorId;  }
            set { m_sensorId = value; }
        }

        [DataMember(Name = "Name", IsRequired = false, Order = 3)]
        public string Name
        {
            get { return m_name;  }
            set { m_name = value; }
        }

        [DataMember(Name = "Description", IsRequired = false, Order = 4)]
        public string Description
        {
            get { return m_description;  }
            set { m_description = value; }
        }

        [DataMember(Name = "PhysicalQuantity", IsRequired = false, Order = 5)]
        public byte PhysicalQuantity
        {
            get { return m_physicalQuantity;  }
            set { m_physicalQuantity = value; }
        }

        /// <remarks />
        [DataMember(Name = "EngineeringUnits", IsRequired = false, Order = 6)]
        public Opc.Ua.EUInformation EngineeringUnits
        {
            get
            {
                return m_engineeringUnits;
            }

            set
            {
                m_engineeringUnits = value;

                if (value == null)
                {
                    m_engineeringUnits = new Opc.Ua.EUInformation();
                }
            }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.TraceContentDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.TraceContentDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.TraceContentDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.TraceContentDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);
            encoder.WriteEncodingMask((uint)EncodingMask);

            encoder.WriteDoubleArray("Values", Values);
            if ((EncodingMask & (uint)TraceContentDataTypeFields.SensorId) != 0) encoder.WriteString("SensorId", SensorId);
            if ((EncodingMask & (uint)TraceContentDataTypeFields.Name) != 0) encoder.WriteString("Name", Name);
            if ((EncodingMask & (uint)TraceContentDataTypeFields.Description) != 0) encoder.WriteString("Description", Description);
            if ((EncodingMask & (uint)TraceContentDataTypeFields.PhysicalQuantity) != 0) encoder.WriteByte("PhysicalQuantity", PhysicalQuantity);
            if ((EncodingMask & (uint)TraceContentDataTypeFields.EngineeringUnits) != 0) encoder.WriteEncodeable("EngineeringUnits", EngineeringUnits, typeof(Opc.Ua.EUInformation));

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            Values = decoder.ReadDoubleArray("Values");
            if ((EncodingMask & (uint)TraceContentDataTypeFields.SensorId) != 0) SensorId = decoder.ReadString("SensorId");
            if ((EncodingMask & (uint)TraceContentDataTypeFields.Name) != 0) Name = decoder.ReadString("Name");
            if ((EncodingMask & (uint)TraceContentDataTypeFields.Description) != 0) Description = decoder.ReadString("Description");
            if ((EncodingMask & (uint)TraceContentDataTypeFields.PhysicalQuantity) != 0) PhysicalQuantity = decoder.ReadByte("PhysicalQuantity");
            if ((EncodingMask & (uint)TraceContentDataTypeFields.EngineeringUnits) != 0) EngineeringUnits = (Opc.Ua.EUInformation)decoder.ReadEncodeable("EngineeringUnits", typeof(Opc.Ua.EUInformation));

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            TraceContentDataType value = encodeable as TraceContentDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if (!Utils.IsEqual(m_values, value.m_values)) return false;
            if ((EncodingMask & (uint)TraceContentDataTypeFields.SensorId) != 0) if (!Utils.IsEqual(m_sensorId, value.m_sensorId)) return false;
            if ((EncodingMask & (uint)TraceContentDataTypeFields.Name) != 0) if (!Utils.IsEqual(m_name, value.m_name)) return false;
            if ((EncodingMask & (uint)TraceContentDataTypeFields.Description) != 0) if (!Utils.IsEqual(m_description, value.m_description)) return false;
            if ((EncodingMask & (uint)TraceContentDataTypeFields.PhysicalQuantity) != 0) if (!Utils.IsEqual(m_physicalQuantity, value.m_physicalQuantity)) return false;
            if ((EncodingMask & (uint)TraceContentDataTypeFields.EngineeringUnits) != 0) if (!Utils.IsEqual(m_engineeringUnits, value.m_engineeringUnits)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (TraceContentDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            TraceContentDataType clone = (TraceContentDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            clone.m_values = (DoubleCollection)Utils.Clone(this.m_values);
            if ((EncodingMask & (uint)TraceContentDataTypeFields.SensorId) != 0) clone.m_sensorId = (string)Utils.Clone(this.m_sensorId);
            if ((EncodingMask & (uint)TraceContentDataTypeFields.Name) != 0) clone.m_name = (string)Utils.Clone(this.m_name);
            if ((EncodingMask & (uint)TraceContentDataTypeFields.Description) != 0) clone.m_description = (string)Utils.Clone(this.m_description);
            if ((EncodingMask & (uint)TraceContentDataTypeFields.PhysicalQuantity) != 0) clone.m_physicalQuantity = (byte)Utils.Clone(this.m_physicalQuantity);
            if ((EncodingMask & (uint)TraceContentDataTypeFields.EngineeringUnits) != 0) clone.m_engineeringUnits = (Opc.Ua.EUInformation)Utils.Clone(this.m_engineeringUnits);

            return clone;
        }
        #endregion

        #region Private Fields
        private DoubleCollection m_values;
        private string m_sensorId;
        private string m_name;
        private string m_description;
        private byte m_physicalQuantity;
        private Opc.Ua.EUInformation m_engineeringUnits;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(TraceContentDataTypeFields)).Where(x => x != nameof(TraceContentDataTypeFields.None)).ToArray();
        #endregion
    }

    #region TraceContentDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfTraceContentDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "TraceContentDataType")]
    public partial class TraceContentDataTypeCollection : List<TraceContentDataType>, ICloneable
    {
        #region Constructors
        public TraceContentDataTypeCollection() {}

        public TraceContentDataTypeCollection(int capacity) : base(capacity) {}

        public TraceContentDataTypeCollection(IEnumerable<TraceContentDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator TraceContentDataTypeCollection(TraceContentDataType[] values)
        {
            if (values != null)
            {
                return new TraceContentDataTypeCollection(values);
            }

            return new TraceContentDataTypeCollection();
        }

        public static explicit operator TraceContentDataType[](TraceContentDataTypeCollection values)
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
            return (TraceContentDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            TraceContentDataTypeCollection clone = new TraceContentDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((TraceContentDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region TraceDataType Class
    #if (!OPCUA_EXCLUDE_TraceDataType)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class TraceDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public TraceDataType()
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
            m_traceId = null;
            m_resultId = null;
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "TraceId", IsRequired = false, Order = 1)]
        public string TraceId
        {
            get { return m_traceId;  }
            set { m_traceId = value; }
        }

        [DataMember(Name = "ResultId", IsRequired = false, Order = 2)]
        public string ResultId
        {
            get { return m_resultId;  }
            set { m_resultId = value; }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.TraceDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.TraceDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.TraceDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => ObjectIds.TraceDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            encoder.WriteString("TraceId", TraceId);
            encoder.WriteString("ResultId", ResultId);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            TraceId = decoder.ReadString("TraceId");
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

            TraceDataType value = encodeable as TraceDataType;

            if (value == null)
            {
                return false;
            }

            if (!Utils.IsEqual(m_traceId, value.m_traceId)) return false;
            if (!Utils.IsEqual(m_resultId, value.m_resultId)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (TraceDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            TraceDataType clone = (TraceDataType)base.MemberwiseClone();

            clone.m_traceId = (string)Utils.Clone(this.m_traceId);
            clone.m_resultId = (string)Utils.Clone(this.m_resultId);

            return clone;
        }
        #endregion

        #region Private Fields
        private string m_traceId;
        private string m_resultId;
        #endregion
    }

    #region TraceDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfTraceDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "TraceDataType")]
    public partial class TraceDataTypeCollection : List<TraceDataType>, ICloneable
    {
        #region Constructors
        public TraceDataTypeCollection() {}

        public TraceDataTypeCollection(int capacity) : base(capacity) {}

        public TraceDataTypeCollection(IEnumerable<TraceDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator TraceDataTypeCollection(TraceDataType[] values)
        {
            if (values != null)
            {
                return new TraceDataTypeCollection(values);
            }

            return new TraceDataTypeCollection();
        }

        public static explicit operator TraceDataType[](TraceDataTypeCollection values)
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
            return (TraceDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            TraceDataTypeCollection clone = new TraceDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((TraceDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region JoiningTraceDataType Class
    #if (!OPCUA_EXCLUDE_JoiningTraceDataType)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IJTBase.Namespaces.IJTBase)]
    public partial class JoiningTraceDataType : UAModel.IJTBase.TraceDataType
    {
        #region Constructors
        public JoiningTraceDataType()
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
            m_stepTraces = new StepTraceDataTypeCollection();
        }
        #endregion

        #region Public Properties
        /// <remarks />
        [DataMember(Name = "StepTraces", IsRequired = false, Order = 1)]
        public StepTraceDataTypeCollection StepTraces
        {
            get
            {
                return m_stepTraces;
            }

            set
            {
                m_stepTraces = value;

                if (value == null)
                {
                    m_stepTraces = new StepTraceDataTypeCollection();
                }
            }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public override ExpandedNodeId TypeId => DataTypeIds.JoiningTraceDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public override ExpandedNodeId BinaryEncodingId => ObjectIds.JoiningTraceDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public override ExpandedNodeId XmlEncodingId => ObjectIds.JoiningTraceDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public override ExpandedNodeId JsonEncodingId => ObjectIds.JoiningTraceDataType_Encoding_DefaultJson;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public override void Encode(IEncoder encoder)
        {
            base.Encode(encoder);

            encoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            encoder.WriteEncodeableArray("StepTraces", StepTraces.ToArray(), typeof(StepTraceDataType));

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public override void Decode(IDecoder decoder)
        {
            base.Decode(decoder);

            decoder.PushNamespace(UAModel.IJTBase.Namespaces.IJTBase);

            StepTraces = (StepTraceDataTypeCollection)decoder.ReadEncodeableArray("StepTraces", typeof(StepTraceDataType));

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public override bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            JoiningTraceDataType value = encodeable as JoiningTraceDataType;

            if (value == null)
            {
                return false;
            }

            if (!Utils.IsEqual(m_stepTraces, value.m_stepTraces)) return false;

            return base.IsEqual(encodeable);
        }

        /// <summary cref="ICloneable.Clone" />
        public override object Clone()
        {
            return (JoiningTraceDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JoiningTraceDataType clone = (JoiningTraceDataType)base.MemberwiseClone();

            clone.m_stepTraces = (StepTraceDataTypeCollection)Utils.Clone(this.m_stepTraces);

            return clone;
        }
        #endregion

        #region Private Fields
        private StepTraceDataTypeCollection m_stepTraces;
        #endregion
    }

    #region JoiningTraceDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfJoiningTraceDataType", Namespace = UAModel.IJTBase.Namespaces.IJTBase, ItemName = "JoiningTraceDataType")]
    public partial class JoiningTraceDataTypeCollection : List<JoiningTraceDataType>, ICloneable
    {
        #region Constructors
        public JoiningTraceDataTypeCollection() {}

        public JoiningTraceDataTypeCollection(int capacity) : base(capacity) {}

        public JoiningTraceDataTypeCollection(IEnumerable<JoiningTraceDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator JoiningTraceDataTypeCollection(JoiningTraceDataType[] values)
        {
            if (values != null)
            {
                return new JoiningTraceDataTypeCollection(values);
            }

            return new JoiningTraceDataTypeCollection();
        }

        public static explicit operator JoiningTraceDataType[](JoiningTraceDataTypeCollection values)
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
            return (JoiningTraceDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            JoiningTraceDataTypeCollection clone = new JoiningTraceDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((JoiningTraceDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion
}