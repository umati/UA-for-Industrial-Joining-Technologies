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
    #region LevelDisplayMode Enumeration
    #if (!OPCUA_EXCLUDE_LevelDisplayMode)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [DataContract(Namespace = UAModel.IA.Namespaces.IA)]
    
    public enum LevelDisplayMode
    {
        [EnumMember(Value = "Dimmed_0")]
        Dimmed = 0,

        [EnumMember(Value = "Blinking_1")]
        Blinking = 1,

        [EnumMember(Value = "Other_2")]
        Other = 2,
    }

    #region LevelDisplayModeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfLevelDisplayMode", Namespace = UAModel.IA.Namespaces.IA, ItemName = "LevelDisplayMode")]
    public partial class LevelDisplayModeCollection : List<LevelDisplayMode>, ICloneable
    {
        #region Constructors
        public LevelDisplayModeCollection() {}

        public LevelDisplayModeCollection(int capacity) : base(capacity) {}

        public LevelDisplayModeCollection(IEnumerable<LevelDisplayMode> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator LevelDisplayModeCollection(LevelDisplayMode[] values)
        {
            if (values != null)
            {
                return new LevelDisplayModeCollection(values);
            }

            return new LevelDisplayModeCollection();
        }

        public static explicit operator LevelDisplayMode[](LevelDisplayModeCollection values)
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
            return (LevelDisplayModeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            LevelDisplayModeCollection clone = new LevelDisplayModeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((LevelDisplayMode)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region SignalColor Enumeration
    #if (!OPCUA_EXCLUDE_SignalColor)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [DataContract(Namespace = UAModel.IA.Namespaces.IA)]
    
    public enum SignalColor
    {
        [EnumMember(Value = "Off_0")]
        Off = 0,

        [EnumMember(Value = "Red_1")]
        Red = 1,

        [EnumMember(Value = "Green_2")]
        Green = 2,

        [EnumMember(Value = "Blue_3")]
        Blue = 3,

        [EnumMember(Value = "Yellow_4")]
        Yellow = 4,

        [EnumMember(Value = "Purple_5")]
        Purple = 5,

        [EnumMember(Value = "Cyan_6")]
        Cyan = 6,

        [EnumMember(Value = "White_7")]
        White = 7,
    }

    #region SignalColorCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfSignalColor", Namespace = UAModel.IA.Namespaces.IA, ItemName = "SignalColor")]
    public partial class SignalColorCollection : List<SignalColor>, ICloneable
    {
        #region Constructors
        public SignalColorCollection() {}

        public SignalColorCollection(int capacity) : base(capacity) {}

        public SignalColorCollection(IEnumerable<SignalColor> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator SignalColorCollection(SignalColor[] values)
        {
            if (values != null)
            {
                return new SignalColorCollection(values);
            }

            return new SignalColorCollection();
        }

        public static explicit operator SignalColor[](SignalColorCollection values)
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
            return (SignalColorCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            SignalColorCollection clone = new SignalColorCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((SignalColor)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region SignalModeLight Enumeration
    #if (!OPCUA_EXCLUDE_SignalModeLight)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [DataContract(Namespace = UAModel.IA.Namespaces.IA)]
    
    public enum SignalModeLight
    {
        [EnumMember(Value = "Continuous_0")]
        Continuous = 0,

        [EnumMember(Value = "Blinking_1")]
        Blinking = 1,

        [EnumMember(Value = "Flashing_2")]
        Flashing = 2,

        [EnumMember(Value = "Other_3")]
        Other = 3,
    }

    #region SignalModeLightCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfSignalModeLight", Namespace = UAModel.IA.Namespaces.IA, ItemName = "SignalModeLight")]
    public partial class SignalModeLightCollection : List<SignalModeLight>, ICloneable
    {
        #region Constructors
        public SignalModeLightCollection() {}

        public SignalModeLightCollection(int capacity) : base(capacity) {}

        public SignalModeLightCollection(IEnumerable<SignalModeLight> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator SignalModeLightCollection(SignalModeLight[] values)
        {
            if (values != null)
            {
                return new SignalModeLightCollection(values);
            }

            return new SignalModeLightCollection();
        }

        public static explicit operator SignalModeLight[](SignalModeLightCollection values)
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
            return (SignalModeLightCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            SignalModeLightCollection clone = new SignalModeLightCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((SignalModeLight)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region StacklightOperationMode Enumeration
    #if (!OPCUA_EXCLUDE_StacklightOperationMode)
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [DataContract(Namespace = UAModel.IA.Namespaces.IA)]
    
    public enum StacklightOperationMode
    {
        [EnumMember(Value = "Segmented_0")]
        Segmented = 0,

        [EnumMember(Value = "Levelmeter_1")]
        Levelmeter = 1,

        [EnumMember(Value = "Running_Light_2")]
        Running_Light = 2,

        [EnumMember(Value = "Other_3")]
        Other = 3,
    }

    #region StacklightOperationModeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfStacklightOperationMode", Namespace = UAModel.IA.Namespaces.IA, ItemName = "StacklightOperationMode")]
    public partial class StacklightOperationModeCollection : List<StacklightOperationMode>, ICloneable
    {
        #region Constructors
        public StacklightOperationModeCollection() {}

        public StacklightOperationModeCollection(int capacity) : base(capacity) {}

        public StacklightOperationModeCollection(IEnumerable<StacklightOperationMode> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator StacklightOperationModeCollection(StacklightOperationMode[] values)
        {
            if (values != null)
            {
                return new StacklightOperationModeCollection(values);
            }

            return new StacklightOperationModeCollection();
        }

        public static explicit operator StacklightOperationMode[](StacklightOperationModeCollection values)
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
            return (StacklightOperationModeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            StacklightOperationModeCollection clone = new StacklightOperationModeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((StacklightOperationMode)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion

    #region RGBWDataType Class
    #if (!OPCUA_EXCLUDE_RGBWDataType)
    /// <exclude />
    [Flags]
    public enum RGBWDataTypeFields : uint
    {
        None = 0,
        White = 0x1,
    }

    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [DataContract(Namespace = UAModel.IA.Namespaces.IA)]
    public partial class RGBWDataType : IEncodeable, IJsonEncodeable
    {
        #region Constructors
        public RGBWDataType()
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
            EncodingMask = (uint)RGBWDataTypeFields.None;
            m_red = (byte)0;
            m_green = (byte)0;
            m_blue = (byte)0;
            m_white = (byte)0;
        }
        #endregion

        #region Public Properties
        [DataMember(Name = "EncodingMask", IsRequired = true, Order = 0)]
        public virtual uint EncodingMask { get; set; }

        [DataMember(Name = "Red", IsRequired = false, Order = 1)]
        public byte Red
        {
            get { return m_red;  }
            set { m_red = value; }
        }

        [DataMember(Name = "Green", IsRequired = false, Order = 2)]
        public byte Green
        {
            get { return m_green;  }
            set { m_green = value; }
        }

        [DataMember(Name = "Blue", IsRequired = false, Order = 3)]
        public byte Blue
        {
            get { return m_blue;  }
            set { m_blue = value; }
        }

        [DataMember(Name = "White", IsRequired = false, Order = 4)]
        public byte White
        {
            get { return m_white;  }
            set { m_white = value; }
        }
        #endregion

        #region IEncodeable Members
        /// <summary cref="IEncodeable.TypeId" />
        public virtual ExpandedNodeId TypeId => DataTypeIds.RGBWDataType;

        /// <summary cref="IEncodeable.BinaryEncodingId" />
        public virtual ExpandedNodeId BinaryEncodingId => ObjectIds.RGBWDataType_Encoding_DefaultBinary;

        /// <summary cref="IEncodeable.XmlEncodingId" />
        public virtual ExpandedNodeId XmlEncodingId => ObjectIds.RGBWDataType_Encoding_DefaultXml;

        /// <summary cref="IJsonEncodeable.JsonEncodingId" />
        public virtual ExpandedNodeId JsonEncodingId => NodeId.Null;

        /// <summary cref="IEncodeable.Encode(IEncoder)" />
        public virtual void Encode(IEncoder encoder)
        {
            encoder.PushNamespace(UAModel.IA.Namespaces.IA);
            encoder.WriteEncodingMask((uint)EncodingMask);

            encoder.WriteByte("Red", Red);
            encoder.WriteByte("Green", Green);
            encoder.WriteByte("Blue", Blue);
            if ((EncodingMask & (uint)RGBWDataTypeFields.White) != 0) encoder.WriteByte("White", White);

            encoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.Decode(IDecoder)" />
        public virtual void Decode(IDecoder decoder)
        {
            decoder.PushNamespace(UAModel.IA.Namespaces.IA);

            EncodingMask = decoder.ReadEncodingMask(m_FieldNames);

            Red = decoder.ReadByte("Red");
            Green = decoder.ReadByte("Green");
            Blue = decoder.ReadByte("Blue");
            if ((EncodingMask & (uint)RGBWDataTypeFields.White) != 0) White = decoder.ReadByte("White");

            decoder.PopNamespace();
        }

        /// <summary cref="IEncodeable.IsEqual(IEncodeable)" />
        public virtual bool IsEqual(IEncodeable encodeable)
        {
            if (Object.ReferenceEquals(this, encodeable))
            {
                return true;
            }

            RGBWDataType value = encodeable as RGBWDataType;

            if (value == null)
            {
                return false;
            }

            if (value.EncodingMask != this.EncodingMask) return false;

            if (!Utils.IsEqual(m_red, value.m_red)) return false;
            if (!Utils.IsEqual(m_green, value.m_green)) return false;
            if (!Utils.IsEqual(m_blue, value.m_blue)) return false;
            if ((EncodingMask & (uint)RGBWDataTypeFields.White) != 0) if (!Utils.IsEqual(m_white, value.m_white)) return false;

            return true;
        }

        /// <summary cref="ICloneable.Clone" />
        public virtual object Clone()
        {
            return (RGBWDataType)this.MemberwiseClone();
        }

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            RGBWDataType clone = (RGBWDataType)base.MemberwiseClone();

            clone.EncodingMask = this.EncodingMask;

            clone.m_red = (byte)Utils.Clone(this.m_red);
            clone.m_green = (byte)Utils.Clone(this.m_green);
            clone.m_blue = (byte)Utils.Clone(this.m_blue);
            if ((EncodingMask & (uint)RGBWDataTypeFields.White) != 0) clone.m_white = (byte)Utils.Clone(this.m_white);

            return clone;
        }
        #endregion

        #region Private Fields
        private byte m_red;
        private byte m_green;
        private byte m_blue;
        private byte m_white;

        private static readonly string[] m_FieldNames = Enum.GetNames(typeof(RGBWDataTypeFields)).Where(x => x != nameof(RGBWDataTypeFields.None)).ToArray();
        #endregion
    }

    #region RGBWDataTypeCollection Class
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    [CollectionDataContract(Name = "ListOfRGBWDataType", Namespace = UAModel.IA.Namespaces.IA, ItemName = "RGBWDataType")]
    public partial class RGBWDataTypeCollection : List<RGBWDataType>, ICloneable
    {
        #region Constructors
        public RGBWDataTypeCollection() {}

        public RGBWDataTypeCollection(int capacity) : base(capacity) {}

        public RGBWDataTypeCollection(IEnumerable<RGBWDataType> collection) : base(collection) {}
        #endregion

        #region Static Operators
        public static implicit operator RGBWDataTypeCollection(RGBWDataType[] values)
        {
            if (values != null)
            {
                return new RGBWDataTypeCollection(values);
            }

            return new RGBWDataTypeCollection();
        }

        public static explicit operator RGBWDataType[](RGBWDataTypeCollection values)
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
            return (RGBWDataTypeCollection)this.MemberwiseClone();
        }
        #endregion

        /// <summary cref="Object.MemberwiseClone" />
        public new object MemberwiseClone()
        {
            RGBWDataTypeCollection clone = new RGBWDataTypeCollection(this.Count);

            for (int ii = 0; ii < this.Count; ii++)
            {
                clone.Add((RGBWDataType)Utils.Clone(this[ii]));
            }

            return clone;
        }
    }
    #endregion
    #endif
    #endregion
}