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
using UAModel.DI;
using UAModel.AMB;
using UAModel.IA;
using UAModel.Machinery;
using UAModel.MachineryResult;
using UAModel.IJTBase;

#pragma warning disable CS1591 // Missing XML comment for publicly visible type or member
#pragma warning disable CA1707 // Identifiers should not contain underscores

namespace UAModel.IJTTightening
{
    #region ObjectType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectTypes
    {
        public const uint ITighteningToolParametersType = 1003;
    }
    #endregion

    #region Variable Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Variables
    {
        public const uint ITighteningToolParametersType_DesignType = 6005;

        public const uint ITighteningToolParametersType_DesignType_EnumStrings = 6006;

        public const uint ITighteningToolParametersType_DriveMethod = 6014;

        public const uint ITighteningToolParametersType_DriveMethod_EnumStrings = 6015;

        public const uint ITighteningToolParametersType_DriveType = 6016;

        public const uint ITighteningToolParametersType_DriveType_EnumStrings = 6017;

        public const uint ITighteningToolParametersType_MaxSpeed = 6022;

        public const uint ITighteningToolParametersType_MaxSpeed_EngineeringUnits = 6036;

        public const uint ITighteningToolParametersType_MaxSpeed_PhysicalQuantity = 6026;

        public const uint ITighteningToolParametersType_MaxSpeed_PhysicalQuantity_EnumStrings = 6027;

        public const uint ITighteningToolParametersType_MaxTorque = 6020;

        public const uint ITighteningToolParametersType_MaxTorque_EngineeringUnits = 6028;

        public const uint ITighteningToolParametersType_MaxTorque_PhysicalQuantity = 6029;

        public const uint ITighteningToolParametersType_MaxTorque_PhysicalQuantity_EnumStrings = 6032;

        public const uint ITighteningToolParametersType_MinTorque = 6021;

        public const uint ITighteningToolParametersType_MinTorque_EngineeringUnits = 6024;

        public const uint ITighteningToolParametersType_MinTorque_PhysicalQuantity = 6025;

        public const uint ITighteningToolParametersType_MinTorque_PhysicalQuantity_EnumStrings = 6033;

        public const uint ITighteningToolParametersType_MotorType = 6023;

        public const uint ITighteningToolParametersType_ShutOffMethod = 6018;

        public const uint ITighteningToolParametersType_ShutOffMethod_EnumStrings = 6019;
    }
    #endregion

    #region ObjectType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectTypeIds
    {
        public static readonly ExpandedNodeId ITighteningToolParametersType = new ExpandedNodeId(UAModel.IJTTightening.ObjectTypes.ITighteningToolParametersType, UAModel.IJTTightening.Namespaces.IJTTightening);
    }
    #endregion

    #region Variable Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class VariableIds
    {
        public static readonly ExpandedNodeId ITighteningToolParametersType_DesignType = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_DesignType, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_DesignType_EnumStrings = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_DesignType_EnumStrings, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_DriveMethod = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_DriveMethod, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_DriveMethod_EnumStrings = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_DriveMethod_EnumStrings, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_DriveType = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_DriveType, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_DriveType_EnumStrings = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_DriveType_EnumStrings, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_MaxSpeed = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_MaxSpeed, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_MaxSpeed_EngineeringUnits = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_MaxSpeed_EngineeringUnits, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_MaxSpeed_PhysicalQuantity = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_MaxSpeed_PhysicalQuantity, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_MaxSpeed_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_MaxSpeed_PhysicalQuantity_EnumStrings, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_MaxTorque = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_MaxTorque, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_MaxTorque_EngineeringUnits = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_MaxTorque_EngineeringUnits, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_MaxTorque_PhysicalQuantity = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_MaxTorque_PhysicalQuantity, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_MaxTorque_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_MaxTorque_PhysicalQuantity_EnumStrings, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_MinTorque = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_MinTorque, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_MinTorque_EngineeringUnits = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_MinTorque_EngineeringUnits, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_MinTorque_PhysicalQuantity = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_MinTorque_PhysicalQuantity, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_MinTorque_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_MinTorque_PhysicalQuantity_EnumStrings, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_MotorType = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_MotorType, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_ShutOffMethod = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_ShutOffMethod, UAModel.IJTTightening.Namespaces.IJTTightening);

        public static readonly ExpandedNodeId ITighteningToolParametersType_ShutOffMethod_EnumStrings = new ExpandedNodeId(UAModel.IJTTightening.Variables.ITighteningToolParametersType_ShutOffMethod_EnumStrings, UAModel.IJTTightening.Namespaces.IJTTightening);
    }
    #endregion

    #region BrowseName Declarations
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class BrowseNames
    {
        public const string DesignType = "DesignType";

        public const string DriveMethod = "DriveMethod";

        public const string DriveType = "DriveType";

        public const string ITighteningToolParametersType = "ITighteningToolParametersType";

        public const string MaxSpeed = "MaxSpeed";

        public const string MaxTorque = "MaxTorque";

        public const string MinTorque = "MinTorque";

        public const string MotorType = "MotorType";

        public const string ShutOffMethod = "ShutOffMethod";
    }
    #endregion

    #region Namespace Declarations
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Namespaces
    {
        /// <summary>
        /// The URI for the IJTTightening namespace (.NET code namespace is 'UAModel.IJTTightening').
        /// </summary>
        public const string IJTTightening = "http://opcfoundation.org/UA/IJT/Tightening/";

        /// <summary>
        /// The URI for the OpcUa namespace (.NET code namespace is 'Opc.Ua').
        /// </summary>
        public const string OpcUa = "http://opcfoundation.org/UA/";

        /// <summary>
        /// The URI for the DI namespace (.NET code namespace is 'UAModel.DI').
        /// </summary>
        public const string DI = "http://opcfoundation.org/UA/DI/";

        /// <summary>
        /// The URI for the AMB namespace (.NET code namespace is 'UAModel.AMB').
        /// </summary>
        public const string AMB = "http://opcfoundation.org/UA/AMB/";

        /// <summary>
        /// The URI for the IA namespace (.NET code namespace is 'UAModel.IA').
        /// </summary>
        public const string IA = "http://opcfoundation.org/UA/IA/";

        /// <summary>
        /// The URI for the Machinery namespace (.NET code namespace is 'UAModel.Machinery').
        /// </summary>
        public const string Machinery = "http://opcfoundation.org/UA/Machinery/";

        /// <summary>
        /// The URI for the MachineryResult namespace (.NET code namespace is 'UAModel.MachineryResult').
        /// </summary>
        public const string MachineryResult = "http://opcfoundation.org/UA/Machinery/Result/";

        /// <summary>
        /// The URI for the IJTBase namespace (.NET code namespace is 'UAModel.IJTBase').
        /// </summary>
        public const string IJTBase = "http://opcfoundation.org/UA/IJT/Base/";
    }
    #endregion
}