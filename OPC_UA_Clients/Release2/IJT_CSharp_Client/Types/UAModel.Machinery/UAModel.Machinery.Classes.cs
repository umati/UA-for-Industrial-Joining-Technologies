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
using UAModel.DI;
using UAModel.IA;

#pragma warning disable CS1591 // Missing XML comment for publicly visible type or member
#pragma warning disable CA1515 // Consider making public types internal
#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1028 // Enum Storage should be Int32

namespace UAModel.Machinery;

#region IMachineTagNameplateTypeState Class
#if (!OPCUA_EXCLUDE_IMachineTagNameplateTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class IMachineTagNameplateTypeState : ITagNameplateTypeState
{
    #region Constructors
    public IMachineTagNameplateTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.IMachineTagNameplateType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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

        if (Location != null)
        {
            Location.Initialize(context, Location_InitializationString);
        }
    }

    #region Initialization String
    private const string Location_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAABAAgAAABMb2NhdGlvbgEBjBcDAAAAACwBAABUbyBiZSB1c2VkIGJ5IGVuZCB1c2VycyB0" +
       "byBzdG9yZSB0aGUgbG9jYXRpb24gb2YgdGhlIG1hY2hpbmUgaW4gYSBzY2hlbWUgc3BlY2lmaWMgdG8g" +
       "dGhlIGVuZCB1c2VyIFNlcnZlcnMgc2hhbGwgc3VwcG9ydCBhdCBsZWFzdCA2MCBVbmljb2RlIGNoYXJh" +
       "Y3RlcnMgZm9yIHRoZSBjbGllbnRzIHdyaXRpbmcgdGhpcyB2YWx1ZSwgdGhpcyBtZWFucyBjbGllbnRz" +
       "IGNhbiBleHBlY3QgdG8gYmUgYWJsZSB0byB3cml0ZSBzdHJpbmdzIHdpdGggYSBsZW5ndGggb2YgNjAg" +
       "VW5pY29kZSBjaGFyYWN0ZXJzIGludG8gdGhhdCBmaWVsZC4ALgBEjBcAAAAM/////wMD/////wAAAAA=";

    private const string InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABACAAAABJTWFjaGluZVRhZ05hbWVwbGF0ZVR5cGVJbnN0YW5jZQEB8wMBAfMD8wMAAAEA" +
       "AAABAMNEAQEB9AMBAAAANWCJCgIAAAABAAgAAABMb2NhdGlvbgEBjBcDAAAAACwBAABUbyBiZSB1c2Vk" +
       "IGJ5IGVuZCB1c2VycyB0byBzdG9yZSB0aGUgbG9jYXRpb24gb2YgdGhlIG1hY2hpbmUgaW4gYSBzY2hl" +
       "bWUgc3BlY2lmaWMgdG8gdGhlIGVuZCB1c2VyIFNlcnZlcnMgc2hhbGwgc3VwcG9ydCBhdCBsZWFzdCA2" +
       "MCBVbmljb2RlIGNoYXJhY3RlcnMgZm9yIHRoZSBjbGllbnRzIHdyaXRpbmcgdGhpcyB2YWx1ZSwgdGhp" +
       "cyBtZWFucyBjbGllbnRzIGNhbiBleHBlY3QgdG8gYmUgYWJsZSB0byB3cml0ZSBzdHJpbmdzIHdpdGgg" +
       "YSBsZW5ndGggb2YgNjAgVW5pY29kZSBjaGFyYWN0ZXJzIGludG8gdGhhdCBmaWVsZC4ALgBEjBcAAAAM" +
       "/////wMD/////wAAAAA=";
    #endregion
#endif
    #endregion

    #region Public Properties
    public PropertyState<string> Location
    {
        get => m_location;

        set
        {
            if (!Object.ReferenceEquals(m_location, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_location = value;
        }
    }
    #endregion

    #region Overridden Methods
    public override void GetChildren(
        ISystemContext context,
        IList<BaseInstanceState> children)
    {
        if (m_location != null)
        {
            children.Add(m_location);
        }

        base.GetChildren(context, children);
    }

    protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
    {
        if (Object.ReferenceEquals(m_location, child))
        {
            m_location = null;
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
            case UAModel.Machinery.BrowseNames.Location:
                {
                    if (createOrReplace)
                    {
                        if (Location == null)
                        {
                            if (replacement == null)
                            {
                                Location = new PropertyState<string>(this);
                            }
                            else
                            {
                                Location = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = Location;
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
    private PropertyState<string> m_location;
    #endregion
}
#endif
#endregion

#region IMachineryEquipmentTypeState Class
#if (!OPCUA_EXCLUDE_IMachineryEquipmentTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class IMachineryEquipmentTypeState : IMachineTagNameplateTypeState
{
    #region Constructors
    public IMachineryEquipmentTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.IMachineryEquipmentType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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

        if (Description != null)
        {
            Description.Initialize(context, Description_InitializationString);
        }

        if (EquipmentLife != null)
        {
            EquipmentLife.Initialize(context, EquipmentLife_InitializationString);
        }
    }

    #region Initialization String
    private const string Description_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAABAAsAAABEZXNjcmlwdGlvbgEB2xcDAAAAAMMAAABBZGRpdGlvbmFsIGluZm9ybWF0aW9u" +
       "IGFuZCBkZXNjcmlwdGlvbiBhYm91dCB0aGUgTWFjaGluZXJ5RXF1aXBtZW50LiBTaG91bGQgYmUgdXNl" +
       "ZCBpZiBEZXNjcmlwdGlvbiBBdHRyaWJ1dGUgY2Fubm90IGJlIHdyaXR0ZW4gdmlhIE9QQyBVQSBhbmQg" +
       "c2hvdWxkIGJlIGlkZWFsbHkgaWRlbnRpY2FsIHRvIERlc2NyaXB0aW9uIEF0dHJpYnV0ZS4ALgBE2xcA" +
       "AAAV/////wMD/////wAAAAA=";

    private const string EquipmentLife_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAABAA0AAABFcXVpcG1lbnRMaWZlAQHdFwMAAAAALgAAAExpZmV0aW1lIGluZGljYXRpb24g" +
       "b2YgdGhlIE1hY2hpbmVyeUVxdWlwbWVudC4ALwED1AHdFwAAABr/////AQH/////AwAAABVgiQoCAAAA" +
       "AAAQAAAARW5naW5lZXJpbmdVbml0cwEB4BcALgBE4BcAAAEAdwP/////AQH/////AAAAADVgiQoCAAAA" +
       "AwAKAAAAU3RhcnRWYWx1ZQEB3xcDAAAAAFMAAABTdGFydFZhbHVlIGluZGljYXRlcyB0aGUgaW5pdGlh" +
       "bCB2YWx1ZSwgd2hlbiB0aGVyZSBpcyBzdGlsbCB0aGUgZnVsbCBsaWZldGltZSBsZWZ0LgAuAETfFwAA" +
       "ABr/////AQH/////AAAAADVgiQoCAAAAAwAKAAAATGltaXRWYWx1ZQEB3hcDAAAAAD8AAABMaW1pdFZh" +
       "bHVlIGluZGljYXRlcyB3aGVuIHRoZSBlbmQgb2YgbGlmZXRpbWUgaGFzIGJlZW4gcmVhY2hlZC4ALgBE" +
       "3hcAAAAa/////wEB/////wAAAAA=";

    private const string InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABAB8AAABJTWFjaGluZXJ5RXF1aXBtZW50VHlwZUluc3RhbmNlAQHvAwEB7wPvAwAA////" +
       "/wMAAAA1YIkKAgAAAAEACwAAAERlc2NyaXB0aW9uAQHbFwMAAAAAwwAAAEFkZGl0aW9uYWwgaW5mb3Jt" +
       "YXRpb24gYW5kIGRlc2NyaXB0aW9uIGFib3V0IHRoZSBNYWNoaW5lcnlFcXVpcG1lbnQuIFNob3VsZCBi" +
       "ZSB1c2VkIGlmIERlc2NyaXB0aW9uIEF0dHJpYnV0ZSBjYW5ub3QgYmUgd3JpdHRlbiB2aWEgT1BDIFVB" +
       "IGFuZCBzaG91bGQgYmUgaWRlYWxseSBpZGVudGljYWwgdG8gRGVzY3JpcHRpb24gQXR0cmlidXRlLgAu" +
       "AETbFwAAABX/////AwP/////AAAAADVgiQoCAAAAAQANAAAARXF1aXBtZW50TGlmZQEB3RcDAAAAAC4A" +
       "AABMaWZldGltZSBpbmRpY2F0aW9uIG9mIHRoZSBNYWNoaW5lcnlFcXVpcG1lbnQuAC8BA9QB3RcAAAAa" +
       "/////wEB/////wMAAAAVYIkKAgAAAAAAEAAAAEVuZ2luZWVyaW5nVW5pdHMBAeAXAC4AROAXAAABAHcD" +
       "/////wEB/////wAAAAA1YIkKAgAAAAMACgAAAFN0YXJ0VmFsdWUBAd8XAwAAAABTAAAAU3RhcnRWYWx1" +
       "ZSBpbmRpY2F0ZXMgdGhlIGluaXRpYWwgdmFsdWUsIHdoZW4gdGhlcmUgaXMgc3RpbGwgdGhlIGZ1bGwg" +
       "bGlmZXRpbWUgbGVmdC4ALgBE3xcAAAAa/////wEB/////wAAAAA1YIkKAgAAAAMACgAAAExpbWl0VmFs" +
       "dWUBAd4XAwAAAAA/AAAATGltaXRWYWx1ZSBpbmRpY2F0ZXMgd2hlbiB0aGUgZW5kIG9mIGxpZmV0aW1l" +
       "IGhhcyBiZWVuIHJlYWNoZWQuAC4ARN4XAAAAGv////8BAf////8AAAAANWCJCgIAAAABABgAAABNYWNo" +
       "aW5lcnlFcXVpcG1lbnRUeXBlSWQBAdwXAwAAAACMAAAASWRlbnRpZmljYXRpb24gb2YgYSBnZW5lcmlj" +
       "IE1hY2hpbmVyeUVxdWlwbWVudC4gRGVmaW5lZCBieSBlYWNoIGNvbXBhbnkgKGUuZy4sIGNvbXBhbnkg" +
       "aGFzIGFuIE1hY2hpbmVyeUVxdWlwbWVudFR5cGVJZCBmb3IgYWxsIDggbW0gZHJpbGxzKS4ALgBE3BcA" +
       "AAAM/////wMD/////wAAAAA=";
    #endregion
#endif
    #endregion

    #region Public Properties
    public new PropertyState<LocalizedText> Description
    {
        get => m_description;

        set
        {
            if (!Object.ReferenceEquals(m_description, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_description = value;
        }
    }

    public LifetimeVariableTypeState EquipmentLife
    {
        get => m_equipmentLife;

        set
        {
            if (!Object.ReferenceEquals(m_equipmentLife, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_equipmentLife = value;
        }
    }

    public PropertyState<string> MachineryEquipmentTypeId
    {
        get => m_machineryEquipmentTypeId;

        set
        {
            if (!Object.ReferenceEquals(m_machineryEquipmentTypeId, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_machineryEquipmentTypeId = value;
        }
    }
    #endregion

    #region Overridden Methods
    public override void GetChildren(
        ISystemContext context,
        IList<BaseInstanceState> children)
    {
        if (m_description != null)
        {
            children.Add(m_description);
        }

        if (m_equipmentLife != null)
        {
            children.Add(m_equipmentLife);
        }

        if (m_machineryEquipmentTypeId != null)
        {
            children.Add(m_machineryEquipmentTypeId);
        }

        base.GetChildren(context, children);
    }

    protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
    {
        if (Object.ReferenceEquals(m_description, child))
        {
            m_description = null;
            return;
        }

        if (Object.ReferenceEquals(m_equipmentLife, child))
        {
            m_equipmentLife = null;
            return;
        }

        if (Object.ReferenceEquals(m_machineryEquipmentTypeId, child))
        {
            m_machineryEquipmentTypeId = null;
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
            case UAModel.Machinery.BrowseNames.Description:
                {
                    if (createOrReplace)
                    {
                        if (Description == null)
                        {
                            if (replacement == null)
                            {
                                Description = new PropertyState<LocalizedText>(this);
                            }
                            else
                            {
                                Description = (PropertyState<LocalizedText>)replacement;
                            }
                        }
                    }

                    instance = Description;
                    break;
                }

            case UAModel.Machinery.BrowseNames.EquipmentLife:
                {
                    if (createOrReplace)
                    {
                        if (EquipmentLife == null)
                        {
                            if (replacement == null)
                            {
                                EquipmentLife = new LifetimeVariableTypeState(this);
                            }
                            else
                            {
                                EquipmentLife = (LifetimeVariableTypeState)replacement;
                            }
                        }
                    }

                    instance = EquipmentLife;
                    break;
                }

            case UAModel.Machinery.BrowseNames.MachineryEquipmentTypeId:
                {
                    if (createOrReplace)
                    {
                        if (MachineryEquipmentTypeId == null)
                        {
                            if (replacement == null)
                            {
                                MachineryEquipmentTypeId = new PropertyState<string>(this);
                            }
                            else
                            {
                                MachineryEquipmentTypeId = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = MachineryEquipmentTypeId;
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
    private PropertyState<LocalizedText> m_description;
    private LifetimeVariableTypeState m_equipmentLife;
    private PropertyState<string> m_machineryEquipmentTypeId;
    #endregion
}
#endif
#endregion

#region IMachineryItemVendorNameplateTypeState Class
#if (!OPCUA_EXCLUDE_IMachineryItemVendorNameplateTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class IMachineryItemVendorNameplateTypeState : IVendorNameplateTypeState
{
    #region Constructors
    public IMachineryItemVendorNameplateTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.IMachineryItemVendorNameplateType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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

        if (InitialOperationDate != null)
        {
            InitialOperationDate.Initialize(context, InitialOperationDate_InitializationString);
        }

        if (MonthOfConstruction != null)
        {
            MonthOfConstruction.Initialize(context, MonthOfConstruction_InitializationString);
        }

        if (YearOfConstruction != null)
        {
            YearOfConstruction.Initialize(context, YearOfConstruction_InitializationString);
        }
    }

    #region Initialization String
    private const string InitialOperationDate_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAABABQAAABJbml0aWFsT3BlcmF0aW9uRGF0ZQEBixcDAAAAAGkAAABUaGUgZGF0ZSwgd2hl" +
       "biB0aGUgTWFjaGluZXJ5SXRlbSB3YXMgc3dpdGNoZWQgb24gdGhlIGZpcnN0IHRpbWUgYWZ0ZXIgaXQg" +
       "aGFzIGxlZnQgdGhlIG1hbnVmYWN0dXJlciBwbGFudC4ALgBEixcAAAAN/////wEB/////wAAAAA=";

    private const string MonthOfConstruction_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAABABMAAABNb250aE9mQ29uc3RydWN0aW9uAQGKFwMAAAAArQAAAFRoZSBtb250aCBpbiB3" +
       "aGljaCB0aGUgbWFudWZhY3R1cmluZyBwcm9jZXNzIG9mIHRoZSBNYWNoaW5lcnlJdGVtIGhhcyBiZWVu" +
       "IGNvbXBsZXRlZC4gSXQgc2hhbGwgYmUgYSBudW1iZXIgYmV0d2VlbiAxIGFuZCAxMiwgcmVwcmVzZW50" +
       "aW5nIHRoZSBtb250aCBmcm9tIEphbnVhcnkgdG8gRGVjZW1iZXIuAC4ARIoXAAAAA/////8BAf////8A" +
       "AAAA";

    private const string YearOfConstruction_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAABABIAAABZZWFyT2ZDb25zdHJ1Y3Rpb24BAYkXAwAAAADEAAAAVGhlIHllYXIgKEdyZWdv" +
       "cmlhbiBjYWxlbmRhcikgaW4gd2hpY2ggdGhlIG1hbnVmYWN0dXJpbmcgcHJvY2VzcyBvZiB0aGUgTWFj" +
       "aGluZXJ5SXRlbSBoYXMgYmVlbiBjb21wbGV0ZWQuIEl0IHNoYWxsIGJlIGEgZm91ci1kaWdpdCBudW1i" +
       "ZXIgYW5kIG5ldmVyIGNoYW5nZSBkdXJpbmcgdGhlIGxpZmUtY3ljbGUgb2YgYSBNYWNoaW5lcnlJdGVt" +
       "LgAuAESJFwAAAAX/////AQH/////AAAAAA==";

    private const string InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABACkAAABJTWFjaGluZXJ5SXRlbVZlbmRvck5hbWVwbGF0ZVR5cGVJbnN0YW5jZQEB6wMB" +
       "AesD6wMAAAEAAAABAMNEAQEB7AMFAAAANWCJCgIAAAADAAwAAABNYW51ZmFjdHVyZXIBAYYXAwAAAABK" +
       "AAAAQSBodW1hbi1yZWFkYWJsZSwgbG9jYWxpemVkIG5hbWUgb2YgdGhlIG1hbnVmYWN0dXJlciBvZiB0" +
       "aGUgTWFjaGluZXJ5SXRlbS4ALgBEhhcAAAAV/////wEB/////wAAAAA1YIkKAgAAAAMADAAAAFNlcmlh" +
       "bE51bWJlcgEBiBcDAAAAABcBAABBIHN0cmluZyBjb250YWluaW5nIGEgdW5pcXVlIHByb2R1Y3Rpb24g" +
       "bnVtYmVyIG9mIHRoZSBtYW51ZmFjdHVyZXIgb2YgdGhlIE1hY2hpbmVyeUl0ZW0uIFRoZSBnbG9iYWwg" +
       "dW5pcXVlbmVzcyBvZiB0aGUgc2VyaWFsIG51bWJlciBpcyBvbmx5IGdpdmVuIGluIHRoZSBjb250ZXh0" +
       "IG9mIHRoZSBtYW51ZmFjdHVyZXIsIGFuZCBwb3RlbnRpYWxseSB0aGUgbW9kZWwuIFRoZSB2YWx1ZSBz" +
       "aGFsbCBub3QgY2hhbmdlIGR1cmluZyB0aGUgbGlmZS1jeWNsZSBvZiB0aGUgTWFjaGluZXJ5SXRlbS4A" +
       "LgBEiBcAAAAM/////wEB/////wAAAAA1YIkKAgAAAAEAFAAAAEluaXRpYWxPcGVyYXRpb25EYXRlAQGL" +
       "FwMAAAAAaQAAAFRoZSBkYXRlLCB3aGVuIHRoZSBNYWNoaW5lcnlJdGVtIHdhcyBzd2l0Y2hlZCBvbiB0" +
       "aGUgZmlyc3QgdGltZSBhZnRlciBpdCBoYXMgbGVmdCB0aGUgbWFudWZhY3R1cmVyIHBsYW50LgAuAESL" +
       "FwAAAA3/////AQH/////AAAAADVgiQoCAAAAAQATAAAATW9udGhPZkNvbnN0cnVjdGlvbgEBihcDAAAA" +
       "AK0AAABUaGUgbW9udGggaW4gd2hpY2ggdGhlIG1hbnVmYWN0dXJpbmcgcHJvY2VzcyBvZiB0aGUgTWFj" +
       "aGluZXJ5SXRlbSBoYXMgYmVlbiBjb21wbGV0ZWQuIEl0IHNoYWxsIGJlIGEgbnVtYmVyIGJldHdlZW4g" +
       "MSBhbmQgMTIsIHJlcHJlc2VudGluZyB0aGUgbW9udGggZnJvbSBKYW51YXJ5IHRvIERlY2VtYmVyLgAu" +
       "AESKFwAAAAP/////AQH/////AAAAADVgiQoCAAAAAQASAAAAWWVhck9mQ29uc3RydWN0aW9uAQGJFwMA" +
       "AAAAxAAAAFRoZSB5ZWFyIChHcmVnb3JpYW4gY2FsZW5kYXIpIGluIHdoaWNoIHRoZSBtYW51ZmFjdHVy" +
       "aW5nIHByb2Nlc3Mgb2YgdGhlIE1hY2hpbmVyeUl0ZW0gaGFzIGJlZW4gY29tcGxldGVkLiBJdCBzaGFs" +
       "bCBiZSBhIGZvdXItZGlnaXQgbnVtYmVyIGFuZCBuZXZlciBjaGFuZ2UgZHVyaW5nIHRoZSBsaWZlLWN5" +
       "Y2xlIG9mIGEgTWFjaGluZXJ5SXRlbS4ALgBEiRcAAAAF/////wEB/////wAAAAA=";
    #endregion
#endif
    #endregion

    #region Public Properties
    public PropertyState<DateTime> InitialOperationDate
    {
        get => m_initialOperationDate;

        set
        {
            if (!Object.ReferenceEquals(m_initialOperationDate, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_initialOperationDate = value;
        }
    }

    public PropertyState<byte> MonthOfConstruction
    {
        get => m_monthOfConstruction;

        set
        {
            if (!Object.ReferenceEquals(m_monthOfConstruction, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_monthOfConstruction = value;
        }
    }

    public PropertyState<ushort> YearOfConstruction
    {
        get => m_yearOfConstruction;

        set
        {
            if (!Object.ReferenceEquals(m_yearOfConstruction, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_yearOfConstruction = value;
        }
    }
    #endregion

    #region Overridden Methods
    public override void GetChildren(
        ISystemContext context,
        IList<BaseInstanceState> children)
    {
        if (m_initialOperationDate != null)
        {
            children.Add(m_initialOperationDate);
        }

        if (m_monthOfConstruction != null)
        {
            children.Add(m_monthOfConstruction);
        }

        if (m_yearOfConstruction != null)
        {
            children.Add(m_yearOfConstruction);
        }

        base.GetChildren(context, children);
    }

    protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
    {
        if (Object.ReferenceEquals(m_initialOperationDate, child))
        {
            m_initialOperationDate = null;
            return;
        }

        if (Object.ReferenceEquals(m_monthOfConstruction, child))
        {
            m_monthOfConstruction = null;
            return;
        }

        if (Object.ReferenceEquals(m_yearOfConstruction, child))
        {
            m_yearOfConstruction = null;
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
            case UAModel.Machinery.BrowseNames.InitialOperationDate:
                {
                    if (createOrReplace)
                    {
                        if (InitialOperationDate == null)
                        {
                            if (replacement == null)
                            {
                                InitialOperationDate = new PropertyState<DateTime>(this);
                            }
                            else
                            {
                                InitialOperationDate = (PropertyState<DateTime>)replacement;
                            }
                        }
                    }

                    instance = InitialOperationDate;
                    break;
                }

            case UAModel.Machinery.BrowseNames.MonthOfConstruction:
                {
                    if (createOrReplace)
                    {
                        if (MonthOfConstruction == null)
                        {
                            if (replacement == null)
                            {
                                MonthOfConstruction = new PropertyState<byte>(this);
                            }
                            else
                            {
                                MonthOfConstruction = (PropertyState<byte>)replacement;
                            }
                        }
                    }

                    instance = MonthOfConstruction;
                    break;
                }

            case UAModel.Machinery.BrowseNames.YearOfConstruction:
                {
                    if (createOrReplace)
                    {
                        if (YearOfConstruction == null)
                        {
                            if (replacement == null)
                            {
                                YearOfConstruction = new PropertyState<ushort>(this);
                            }
                            else
                            {
                                YearOfConstruction = (PropertyState<ushort>)replacement;
                            }
                        }
                    }

                    instance = YearOfConstruction;
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
    private PropertyState<DateTime> m_initialOperationDate;
    private PropertyState<byte> m_monthOfConstruction;
    private PropertyState<ushort> m_yearOfConstruction;
    #endregion
}
#endif
#endregion

#region IMachineVendorNameplateTypeState Class
#if (!OPCUA_EXCLUDE_IMachineVendorNameplateTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class IMachineVendorNameplateTypeState : IMachineryItemVendorNameplateTypeState
{
    #region Constructors
    public IMachineVendorNameplateTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.IMachineVendorNameplateType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABACMAAABJTWFjaGluZVZlbmRvck5hbWVwbGF0ZVR5cGVJbnN0YW5jZQEB8gMBAfID8gMA" +
       "AAEAAAABAMNEAQEB9AMDAAAANWCJCgIAAAADAAwAAABNYW51ZmFjdHVyZXIBAYYXAwAAAABKAAAAQSBo" +
       "dW1hbi1yZWFkYWJsZSwgbG9jYWxpemVkIG5hbWUgb2YgdGhlIG1hbnVmYWN0dXJlciBvZiB0aGUgTWFj" +
       "aGluZXJ5SXRlbS4ALgBEhhcAAAAV/////wEB/////wAAAAA1YIkKAgAAAAMADAAAAFNlcmlhbE51bWJl" +
       "cgEBiBcDAAAAABcBAABBIHN0cmluZyBjb250YWluaW5nIGEgdW5pcXVlIHByb2R1Y3Rpb24gbnVtYmVy" +
       "IG9mIHRoZSBtYW51ZmFjdHVyZXIgb2YgdGhlIE1hY2hpbmVyeUl0ZW0uIFRoZSBnbG9iYWwgdW5pcXVl" +
       "bmVzcyBvZiB0aGUgc2VyaWFsIG51bWJlciBpcyBvbmx5IGdpdmVuIGluIHRoZSBjb250ZXh0IG9mIHRo" +
       "ZSBtYW51ZmFjdHVyZXIsIGFuZCBwb3RlbnRpYWxseSB0aGUgbW9kZWwuIFRoZSB2YWx1ZSBzaGFsbCBu" +
       "b3QgY2hhbmdlIGR1cmluZyB0aGUgbGlmZS1jeWNsZSBvZiB0aGUgTWFjaGluZXJ5SXRlbS4ALgBEiBcA" +
       "AAAM/////wEB/////wAAAAA1YIkKAgAAAAMAEgAAAFByb2R1Y3RJbnN0YW5jZVVyaQEBhxcDAAAAAFEA" +
       "AABBIGdsb2JhbGx5IHVuaXF1ZSByZXNvdXJjZSBpZGVudGlmaWVyIHByb3ZpZGVkIGJ5IHRoZSBtYW51" +
       "ZmFjdHVyZXIgb2YgdGhlIG1hY2hpbmUALgBEhxcAAAAM/////wEB/////wAAAAA=";
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

#region MachineryItemIdentificationTypeState Class
#if (!OPCUA_EXCLUDE_MachineryItemIdentificationTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class MachineryItemIdentificationTypeState : FunctionalGroupTypeState
{
    #region Constructors
    public MachineryItemIdentificationTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.MachineryItemIdentificationType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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

        if (AssetId != null)
        {
            AssetId.Initialize(context, AssetId_InitializationString);
        }

        if (ComponentName != null)
        {
            ComponentName.Initialize(context, ComponentName_InitializationString);
        }

        if (DeviceClass != null)
        {
            DeviceClass.Initialize(context, DeviceClass_InitializationString);
        }

        if (HardwareRevision != null)
        {
            HardwareRevision.Initialize(context, HardwareRevision_InitializationString);
        }

        if (InitialOperationDate != null)
        {
            InitialOperationDate.Initialize(context, InitialOperationDate_InitializationString);
        }

        if (ManufacturerUri != null)
        {
            ManufacturerUri.Initialize(context, ManufacturerUri_InitializationString);
        }

        if (Model != null)
        {
            Model.Initialize(context, Model_InitializationString);
        }

        if (MonthOfConstruction != null)
        {
            MonthOfConstruction.Initialize(context, MonthOfConstruction_InitializationString);
        }

        if (ProductCode != null)
        {
            ProductCode.Initialize(context, ProductCode_InitializationString);
        }

        if (ProductInstanceUri != null)
        {
            ProductInstanceUri.Initialize(context, ProductInstanceUri_InitializationString);
        }

        if (SoftwareRevision != null)
        {
            SoftwareRevision.Initialize(context, SoftwareRevision_InitializationString);
        }

        if (YearOfConstruction != null)
        {
            YearOfConstruction.Initialize(context, YearOfConstruction_InitializationString);
        }
    }

    #region Initialization String
    private const string AssetId_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCpCgIAAAADAAcAAABBc3NldElkAQF9FwMAAAAAMAEAAFRvIGJlIHVzZWQgYnkgZW5kIHVzZXJzIHRv" +
       "IHN0b3JlIGEgdW5pcXVlIGlkZW50aWZpY2F0aW9uIGluIHRoZSBjb250ZXh0IG9mIHRoZWlyIG92ZXJh" +
       "bGwgYXBwbGljYXRpb24uIFNlcnZlcnMgc2hhbGwgc3VwcG9ydCBhdCBsZWFzdCA0MCBVbmljb2RlIGNo" +
       "YXJhY3RlcnMgZm9yIHRoZSBjbGllbnRzIHdyaXRpbmcgdGhpcyB2YWx1ZSwgdGhpcyBtZWFucyBjbGll" +
       "bnRzIGNhbiBleHBlY3QgdG8gYmUgYWJsZSB0byB3cml0ZSBzdHJpbmdzIHdpdGggYSBsZW5ndGggb2Yg" +
       "NDAgVW5pY29kZSBjaGFyYWN0ZXJzIGludG8gdGhhdCBmaWVsZC4ALgBEfRcAAAwAAAAAAAz/////AwP/" +
       "////AAAAAA==";

    private const string ComponentName_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCpCgIAAAADAA0AAABDb21wb25lbnROYW1lAQF+FwMAAAAAegEAAFRvIGJlIHVzZWQgYnkgZW5kIHVz" +
       "ZXJzIHRvIHN0b3JlIGEgaHVtYW4tcmVhZGFibGUgbG9jYWxpemVkIHRleHQgZm9yIHRoZSBNYWNoaW5l" +
       "cnlJdGVtLiBUaGUgbWluaW11bSBudW1iZXIgb2YgbG9jYWxlcyBzdXBwb3J0ZWQgZm9yIHRoaXMgcHJv" +
       "cGVydHkgc2hhbGwgYmUgdHdvLiBTZXJ2ZXJzIHNoYWxsIHN1cHBvcnQgYXQgbGVhc3QgNDAgVW5pY29k" +
       "ZSBjaGFyYWN0ZXJzIGZvciB0aGUgY2xpZW50cyB3cml0aW5nIHRoZSB0ZXh0IHBhcnQgb2YgZWFjaCBs" +
       "b2NhbGUsIHRoaXMgbWVhbnMgY2xpZW50cyBjYW4gZXhwZWN0IHRvIGJlIGFibGUgdG8gd3JpdGUgdGV4" +
       "dHMgd2l0aCBhIGxlbmd0aCBvZiA0MCBVbmljb2RlIGNoYXJhY3RlcnMgaW50byB0aGF0IGZpZWxkLgAu" +
       "AER+FwAAFQAAFf////8DA/////8AAAAA";

    private const string DeviceClass_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAADAAsAAABEZXZpY2VDbGFzcwEBfBcDAAAAAEgAAABJbmRpY2F0ZXMgaW4gd2hpY2ggZG9t" +
       "YWluIG9yIGZvciB3aGF0IHB1cnBvc2UgdGhlIE1hY2hpbmVyeUl0ZW0gaXMgdXNlZC4ALgBEfBcAAAAM" +
       "/////wEB/////wAAAAA=";

    private const string HardwareRevision_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAADABAAAABIYXJkd2FyZVJldmlzaW9uAQF6FwMAAAAAJAEAAEEgc3RyaW5nIHJlcHJlc2Vu" +
       "dGF0aW9uIG9mIHRoZSByZXZpc2lvbiBsZXZlbCBvZiB0aGUgaGFyZHdhcmUgb2YgYSBNYWNoaW5lcnlJ" +
       "dGVtLiBIYXJkd2FyZSBpcyBwaHlzaWNhbCBlcXVpcG1lbnQsIGFzIG9wcG9zZWQgdG8gcHJvZ3JhbXMs" +
       "IHByb2NlZHVyZXMsIHJ1bGVzIGFuZCBhc3NvY2lhdGVkIGRvY3VtZW50YXRpb24uIE1hbnkgbWFjaGlu" +
       "ZXMgd2lsbCBub3QgcHJvdmlkZSBzdWNoIGluZm9ybWF0aW9uIGR1ZSB0byB0aGUgbW9kdWxhciBhbmQg" +
       "Y29uZmlndXJhYmxlIG5hdHVyZSBvZiB0aGUgbWFjaGluZS4ALgBEehcAAAAM/////wEB/////wAAAAA=";

    private const string InitialOperationDate_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAABABQAAABJbml0aWFsT3BlcmF0aW9uRGF0ZQEBdhcDAAAAAGkAAABUaGUgZGF0ZSwgd2hl" +
       "biB0aGUgTWFjaGluZXJ5SXRlbSB3YXMgc3dpdGNoZWQgb24gdGhlIGZpcnN0IHRpbWUgYWZ0ZXIgaXQg" +
       "aGFzIGxlZnQgdGhlIG1hbnVmYWN0dXJlciBwbGFudC4ALgBEdhcAAAAN/////wEB/////wAAAAA=";

    private const string ManufacturerUri_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAADAA8AAABNYW51ZmFjdHVyZXJVcmkBAXcXAwAAAABGAAAAQSBnbG9iYWxseSB1bmlxdWUg" +
       "aWRlbnRpZmllciBvZiB0aGUgbWFudWZhY3R1cmVyIG9mIHRoZSBNYWNoaW5lcnlJdGVtLgAuAER3FwAA" +
       "AAz/////AQH/////AAAAAA==";

    private const string Model_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAADAAUAAABNb2RlbAEBeBcDAAAAAEMAAABBIGh1bWFuLXJlYWRhYmxlLCBsb2NhbGl6ZWQg" +
       "bmFtZSBvZiB0aGUgbW9kZWwgb2YgdGhlIE1hY2hpbmVyeUl0ZW0uAC4ARHgXAAAAFf////8BAf////8A" +
       "AAAA";

    private const string MonthOfConstruction_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAABABMAAABNb250aE9mQ29uc3RydWN0aW9uAQF1FwMAAAAArQAAAFRoZSBtb250aCBpbiB3" +
       "aGljaCB0aGUgbWFudWZhY3R1cmluZyBwcm9jZXNzIG9mIHRoZSBNYWNoaW5lcnlJdGVtIGhhcyBiZWVu" +
       "IGNvbXBsZXRlZC4gSXQgc2hhbGwgYmUgYSBudW1iZXIgYmV0d2VlbiAxIGFuZCAxMiwgcmVwcmVzZW50" +
       "aW5nIHRoZSBtb250aCBmcm9tIEphbnVhcnkgdG8gRGVjZW1iZXIuAC4ARHUXAAAAA/////8BAf////8A" +
       "AAAA";

    private const string ProductCode_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAADAAsAAABQcm9kdWN0Q29kZQEBeRcDAAAAAPsAAABBIG1hY2hpbmUtcmVhZGFibGUgc3Ry" +
       "aW5nIG9mIHRoZSBtb2RlbCBvZiB0aGUgTWFjaGluZXJ5SXRlbSwgdGhhdCBtaWdodCBpbmNsdWRlIG9w" +
       "dGlvbnMgbGlrZSB0aGUgaGFyZHdhcmUgY29uZmlndXJhdGlvbiBvZiB0aGUgbW9kZWwuIFRoaXMgaW5m" +
       "b3JtYXRpb24gbWlnaHQgYmUgcHJvdmlkZWQgYnkgdGhlIEVSUCBzeXN0ZW0gb2YgdGhlIHZlbmRvci4g" +
       "Rm9yIGV4YW1wbGUsIGl0IGNhbiBiZSB1c2VkIGFzIG9yZGVyIGluZm9ybWF0aW9uLgAuAER5FwAAAAz/" +
       "////AQH/////AAAAAA==";

    private const string ProductInstanceUri_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAADABIAAABQcm9kdWN0SW5zdGFuY2VVcmkBAXEXAwAAAABYAAAAQSBnbG9iYWxseSB1bmlx" +
       "dWUgcmVzb3VyY2UgaWRlbnRpZmllciBwcm92aWRlZCBieSB0aGUgbWFudWZhY3R1cmVyIG9mIHRoZSBN" +
       "YWNoaW5lcnlJdGVtLgAuAERxFwAAAAz/////AQH/////AAAAAA==";

    private const string SoftwareRevision_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAADABAAAABTb2Z0d2FyZVJldmlzaW9uAQF7FwMAAAAA0AEAAEEgc3RyaW5nIHJlcHJlc2Vu" +
       "dGF0aW9uIG9mIHRoZSByZXZpc2lvbiBsZXZlbCBvZiBhIE1hY2hpbmVyeUl0ZW0uIEluIG1vc3QgY2Fz" +
       "ZXMsIE1hY2hpbmVyeUl0ZW1zIGNvbnNpc3Qgb2Ygc2V2ZXJhbCBzb2Z0d2FyZSBjb21wb25lbnRzLiBJ" +
       "biB0aGF0IGNhc2UsIGluZm9ybWF0aW9uIGFib3V0IHRoZSBzb2Z0d2FyZSBjb21wb25lbnRzIG1pZ2h0" +
       "IGJlIHByb3ZpZGVkIGFzIGFkZGl0aW9uYWwgaW5mb3JtYXRpb24gaW4gdGhlIGFkZHJlc3Mgc3BhY2Us" +
       "IGluY2x1ZGluZyBpbmRpdmlkdWFsIHJldmlzaW9uIGluZm9ybWF0aW9uLiBJbiB0aGF0IGNhc2UsIHRo" +
       "aXMgcHJvcGVydHkgaXMgZWl0aGVyIG5vdCBwcm92aWRlZCBvciBwcm92aWRlcyBhbiBvdmVyYWxsIHNv" +
       "ZnR3YXJlIHJldmlzaW9uIGxldmVsLiBUaGUgdmFsdWUgbWlnaHQgY2hhbmdlIGR1cmluZyB0aGUgbGlm" +
       "ZS1jeWNsZSBvZiBhIE1hY2hpbmVyeUl0ZW0uAC4ARHsXAAAADP////8BAf////8AAAAA";

    private const string YearOfConstruction_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAABABIAAABZZWFyT2ZDb25zdHJ1Y3Rpb24BAXQXAwAAAADEAAAAVGhlIHllYXIgKEdyZWdv" +
       "cmlhbiBjYWxlbmRhcikgaW4gd2hpY2ggdGhlIG1hbnVmYWN0dXJpbmcgcHJvY2VzcyBvZiB0aGUgTWFj" +
       "aGluZXJ5SXRlbSBoYXMgYmVlbiBjb21wbGV0ZWQuIEl0IHNoYWxsIGJlIGEgZm91ci1kaWdpdCBudW1i" +
       "ZXIgYW5kIG5ldmVyIGNoYW5nZSBkdXJpbmcgdGhlIGxpZmUtY3ljbGUgb2YgYSBNYWNoaW5lcnlJdGVt" +
       "LgAuAER0FwAAAAX/////AQH/////AAAAAA==";

    private const string InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABACcAAABNYWNoaW5lcnlJdGVtSWRlbnRpZmljYXRpb25UeXBlSW5zdGFuY2UBAewDAQHs" +
       "A+wDAAACAAAAAQDDRAABAesDAQDDRAABA8g6DwAAADVgqQoCAAAAAwAHAAAAQXNzZXRJZAEBfRcDAAAA" +
       "ADABAABUbyBiZSB1c2VkIGJ5IGVuZCB1c2VycyB0byBzdG9yZSBhIHVuaXF1ZSBpZGVudGlmaWNhdGlv" +
       "biBpbiB0aGUgY29udGV4dCBvZiB0aGVpciBvdmVyYWxsIGFwcGxpY2F0aW9uLiBTZXJ2ZXJzIHNoYWxs" +
       "IHN1cHBvcnQgYXQgbGVhc3QgNDAgVW5pY29kZSBjaGFyYWN0ZXJzIGZvciB0aGUgY2xpZW50cyB3cml0" +
       "aW5nIHRoaXMgdmFsdWUsIHRoaXMgbWVhbnMgY2xpZW50cyBjYW4gZXhwZWN0IHRvIGJlIGFibGUgdG8g" +
       "d3JpdGUgc3RyaW5ncyB3aXRoIGEgbGVuZ3RoIG9mIDQwIFVuaWNvZGUgY2hhcmFjdGVycyBpbnRvIHRo" +
       "YXQgZmllbGQuAC4ARH0XAAAMAAAAAAAM/////wMD/////wAAAAA1YKkKAgAAAAMADQAAAENvbXBvbmVu" +
       "dE5hbWUBAX4XAwAAAAB6AQAAVG8gYmUgdXNlZCBieSBlbmQgdXNlcnMgdG8gc3RvcmUgYSBodW1hbi1y" +
       "ZWFkYWJsZSBsb2NhbGl6ZWQgdGV4dCBmb3IgdGhlIE1hY2hpbmVyeUl0ZW0uIFRoZSBtaW5pbXVtIG51" +
       "bWJlciBvZiBsb2NhbGVzIHN1cHBvcnRlZCBmb3IgdGhpcyBwcm9wZXJ0eSBzaGFsbCBiZSB0d28uIFNl" +
       "cnZlcnMgc2hhbGwgc3VwcG9ydCBhdCBsZWFzdCA0MCBVbmljb2RlIGNoYXJhY3RlcnMgZm9yIHRoZSBj" +
       "bGllbnRzIHdyaXRpbmcgdGhlIHRleHQgcGFydCBvZiBlYWNoIGxvY2FsZSwgdGhpcyBtZWFucyBjbGll" +
       "bnRzIGNhbiBleHBlY3QgdG8gYmUgYWJsZSB0byB3cml0ZSB0ZXh0cyB3aXRoIGEgbGVuZ3RoIG9mIDQw" +
       "IFVuaWNvZGUgY2hhcmFjdGVycyBpbnRvIHRoYXQgZmllbGQuAC4ARH4XAAAVAAAV/////wMD/////wAA" +
       "AAA1YKkKAgAAAAAAGQAAAERlZmF1bHRJbnN0YW5jZUJyb3dzZU5hbWUBAcgXAwAAAAAxAAAAVGhlIGRl" +
       "ZmF1bHQgQnJvd3NlTmFtZSBmb3IgaW5zdGFuY2VzIG9mIHRoZSB0eXBlLgAuAETIFwAAFAMADgAAAElk" +
       "ZW50aWZpY2F0aW9uABT/////AwP/////AAAAADVgiQoCAAAAAwALAAAARGV2aWNlQ2xhc3MBAXwXAwAA" +
       "AABIAAAASW5kaWNhdGVzIGluIHdoaWNoIGRvbWFpbiBvciBmb3Igd2hhdCBwdXJwb3NlIHRoZSBNYWNo" +
       "aW5lcnlJdGVtIGlzIHVzZWQuAC4ARHwXAAAADP////8BAf////8AAAAANWCJCgIAAAADABAAAABIYXJk" +
       "d2FyZVJldmlzaW9uAQF6FwMAAAAAJAEAAEEgc3RyaW5nIHJlcHJlc2VudGF0aW9uIG9mIHRoZSByZXZp" +
       "c2lvbiBsZXZlbCBvZiB0aGUgaGFyZHdhcmUgb2YgYSBNYWNoaW5lcnlJdGVtLiBIYXJkd2FyZSBpcyBw" +
       "aHlzaWNhbCBlcXVpcG1lbnQsIGFzIG9wcG9zZWQgdG8gcHJvZ3JhbXMsIHByb2NlZHVyZXMsIHJ1bGVz" +
       "IGFuZCBhc3NvY2lhdGVkIGRvY3VtZW50YXRpb24uIE1hbnkgbWFjaGluZXMgd2lsbCBub3QgcHJvdmlk" +
       "ZSBzdWNoIGluZm9ybWF0aW9uIGR1ZSB0byB0aGUgbW9kdWxhciBhbmQgY29uZmlndXJhYmxlIG5hdHVy" +
       "ZSBvZiB0aGUgbWFjaGluZS4ALgBEehcAAAAM/////wEB/////wAAAAA1YIkKAgAAAAEAFAAAAEluaXRp" +
       "YWxPcGVyYXRpb25EYXRlAQF2FwMAAAAAaQAAAFRoZSBkYXRlLCB3aGVuIHRoZSBNYWNoaW5lcnlJdGVt" +
       "IHdhcyBzd2l0Y2hlZCBvbiB0aGUgZmlyc3QgdGltZSBhZnRlciBpdCBoYXMgbGVmdCB0aGUgbWFudWZh" +
       "Y3R1cmVyIHBsYW50LgAuAER2FwAAAA3/////AQH/////AAAAADVgiQoCAAAAAwAMAAAATWFudWZhY3R1" +
       "cmVyAQFyFwMAAAAASgAAAEEgaHVtYW4tcmVhZGFibGUsIGxvY2FsaXplZCBuYW1lIG9mIHRoZSBtYW51" +
       "ZmFjdHVyZXIgb2YgdGhlIE1hY2hpbmVyeUl0ZW0uAC4ARHIXAAAAFf////8BAf////8AAAAANWCJCgIA" +
       "AAADAA8AAABNYW51ZmFjdHVyZXJVcmkBAXcXAwAAAABGAAAAQSBnbG9iYWxseSB1bmlxdWUgaWRlbnRp" +
       "ZmllciBvZiB0aGUgbWFudWZhY3R1cmVyIG9mIHRoZSBNYWNoaW5lcnlJdGVtLgAuAER3FwAAAAz/////" +
       "AQH/////AAAAADVgiQoCAAAAAwAFAAAATW9kZWwBAXgXAwAAAABDAAAAQSBodW1hbi1yZWFkYWJsZSwg" +
       "bG9jYWxpemVkIG5hbWUgb2YgdGhlIG1vZGVsIG9mIHRoZSBNYWNoaW5lcnlJdGVtLgAuAER4FwAAABX/" +
       "////AQH/////AAAAADVgiQoCAAAAAQATAAAATW9udGhPZkNvbnN0cnVjdGlvbgEBdRcDAAAAAK0AAABU" +
       "aGUgbW9udGggaW4gd2hpY2ggdGhlIG1hbnVmYWN0dXJpbmcgcHJvY2VzcyBvZiB0aGUgTWFjaGluZXJ5" +
       "SXRlbSBoYXMgYmVlbiBjb21wbGV0ZWQuIEl0IHNoYWxsIGJlIGEgbnVtYmVyIGJldHdlZW4gMSBhbmQg" +
       "MTIsIHJlcHJlc2VudGluZyB0aGUgbW9udGggZnJvbSBKYW51YXJ5IHRvIERlY2VtYmVyLgAuAER1FwAA" +
       "AAP/////AQH/////AAAAADVgiQoCAAAAAwALAAAAUHJvZHVjdENvZGUBAXkXAwAAAAD7AAAAQSBtYWNo" +
       "aW5lLXJlYWRhYmxlIHN0cmluZyBvZiB0aGUgbW9kZWwgb2YgdGhlIE1hY2hpbmVyeUl0ZW0sIHRoYXQg" +
       "bWlnaHQgaW5jbHVkZSBvcHRpb25zIGxpa2UgdGhlIGhhcmR3YXJlIGNvbmZpZ3VyYXRpb24gb2YgdGhl" +
       "IG1vZGVsLiBUaGlzIGluZm9ybWF0aW9uIG1pZ2h0IGJlIHByb3ZpZGVkIGJ5IHRoZSBFUlAgc3lzdGVt" +
       "IG9mIHRoZSB2ZW5kb3IuIEZvciBleGFtcGxlLCBpdCBjYW4gYmUgdXNlZCBhcyBvcmRlciBpbmZvcm1h" +
       "dGlvbi4ALgBEeRcAAAAM/////wEB/////wAAAAA1YIkKAgAAAAMAEgAAAFByb2R1Y3RJbnN0YW5jZVVy" +
       "aQEBcRcDAAAAAFgAAABBIGdsb2JhbGx5IHVuaXF1ZSByZXNvdXJjZSBpZGVudGlmaWVyIHByb3ZpZGVk" +
       "IGJ5IHRoZSBtYW51ZmFjdHVyZXIgb2YgdGhlIE1hY2hpbmVyeUl0ZW0uAC4ARHEXAAAADP////8BAf//" +
       "//8AAAAANWCJCgIAAAADAAwAAABTZXJpYWxOdW1iZXIBAXMXAwAAAAAXAQAAQSBzdHJpbmcgY29udGFp" +
       "bmluZyBhIHVuaXF1ZSBwcm9kdWN0aW9uIG51bWJlciBvZiB0aGUgbWFudWZhY3R1cmVyIG9mIHRoZSBN" +
       "YWNoaW5lcnlJdGVtLiBUaGUgZ2xvYmFsIHVuaXF1ZW5lc3Mgb2YgdGhlIHNlcmlhbCBudW1iZXIgaXMg" +
       "b25seSBnaXZlbiBpbiB0aGUgY29udGV4dCBvZiB0aGUgbWFudWZhY3R1cmVyLCBhbmQgcG90ZW50aWFs" +
       "bHkgdGhlIG1vZGVsLiBUaGUgdmFsdWUgc2hhbGwgbm90IGNoYW5nZSBkdXJpbmcgdGhlIGxpZmUtY3lj" +
       "bGUgb2YgdGhlIE1hY2hpbmVyeUl0ZW0uAC4ARHMXAAAADP////8BAf////8AAAAANWCJCgIAAAADABAA" +
       "AABTb2Z0d2FyZVJldmlzaW9uAQF7FwMAAAAA0AEAAEEgc3RyaW5nIHJlcHJlc2VudGF0aW9uIG9mIHRo" +
       "ZSByZXZpc2lvbiBsZXZlbCBvZiBhIE1hY2hpbmVyeUl0ZW0uIEluIG1vc3QgY2FzZXMsIE1hY2hpbmVy" +
       "eUl0ZW1zIGNvbnNpc3Qgb2Ygc2V2ZXJhbCBzb2Z0d2FyZSBjb21wb25lbnRzLiBJbiB0aGF0IGNhc2Us" +
       "IGluZm9ybWF0aW9uIGFib3V0IHRoZSBzb2Z0d2FyZSBjb21wb25lbnRzIG1pZ2h0IGJlIHByb3ZpZGVk" +
       "IGFzIGFkZGl0aW9uYWwgaW5mb3JtYXRpb24gaW4gdGhlIGFkZHJlc3Mgc3BhY2UsIGluY2x1ZGluZyBp" +
       "bmRpdmlkdWFsIHJldmlzaW9uIGluZm9ybWF0aW9uLiBJbiB0aGF0IGNhc2UsIHRoaXMgcHJvcGVydHkg" +
       "aXMgZWl0aGVyIG5vdCBwcm92aWRlZCBvciBwcm92aWRlcyBhbiBvdmVyYWxsIHNvZnR3YXJlIHJldmlz" +
       "aW9uIGxldmVsLiBUaGUgdmFsdWUgbWlnaHQgY2hhbmdlIGR1cmluZyB0aGUgbGlmZS1jeWNsZSBvZiBh" +
       "IE1hY2hpbmVyeUl0ZW0uAC4ARHsXAAAADP////8BAf////8AAAAANWCJCgIAAAABABIAAABZZWFyT2ZD" +
       "b25zdHJ1Y3Rpb24BAXQXAwAAAADEAAAAVGhlIHllYXIgKEdyZWdvcmlhbiBjYWxlbmRhcikgaW4gd2hp" +
       "Y2ggdGhlIG1hbnVmYWN0dXJpbmcgcHJvY2VzcyBvZiB0aGUgTWFjaGluZXJ5SXRlbSBoYXMgYmVlbiBj" +
       "b21wbGV0ZWQuIEl0IHNoYWxsIGJlIGEgZm91ci1kaWdpdCBudW1iZXIgYW5kIG5ldmVyIGNoYW5nZSBk" +
       "dXJpbmcgdGhlIGxpZmUtY3ljbGUgb2YgYSBNYWNoaW5lcnlJdGVtLgAuAER0FwAAAAX/////AQH/////" +
       "AAAAAA==";
    #endregion
#endif
    #endregion

    #region Public Properties
    public PropertyState<string> AssetId
    {
        get => m_assetId;

        set
        {
            if (!Object.ReferenceEquals(m_assetId, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_assetId = value;
        }
    }

    public PropertyState<LocalizedText> ComponentName
    {
        get => m_componentName;

        set
        {
            if (!Object.ReferenceEquals(m_componentName, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_componentName = value;
        }
    }

    public PropertyState<string> DeviceClass
    {
        get => m_deviceClass;

        set
        {
            if (!Object.ReferenceEquals(m_deviceClass, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_deviceClass = value;
        }
    }

    public PropertyState<string> HardwareRevision
    {
        get => m_hardwareRevision;

        set
        {
            if (!Object.ReferenceEquals(m_hardwareRevision, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_hardwareRevision = value;
        }
    }

    public PropertyState<DateTime> InitialOperationDate
    {
        get => m_initialOperationDate;

        set
        {
            if (!Object.ReferenceEquals(m_initialOperationDate, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_initialOperationDate = value;
        }
    }

    public PropertyState<LocalizedText> Manufacturer
    {
        get => m_manufacturer;

        set
        {
            if (!Object.ReferenceEquals(m_manufacturer, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_manufacturer = value;
        }
    }

    public PropertyState<string> ManufacturerUri
    {
        get => m_manufacturerUri;

        set
        {
            if (!Object.ReferenceEquals(m_manufacturerUri, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_manufacturerUri = value;
        }
    }

    public PropertyState<LocalizedText> Model
    {
        get => m_model;

        set
        {
            if (!Object.ReferenceEquals(m_model, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_model = value;
        }
    }

    public PropertyState<byte> MonthOfConstruction
    {
        get => m_monthOfConstruction;

        set
        {
            if (!Object.ReferenceEquals(m_monthOfConstruction, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_monthOfConstruction = value;
        }
    }

    public PropertyState<string> ProductCode
    {
        get => m_productCode;

        set
        {
            if (!Object.ReferenceEquals(m_productCode, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_productCode = value;
        }
    }

    public PropertyState<string> ProductInstanceUri
    {
        get => m_productInstanceUri;

        set
        {
            if (!Object.ReferenceEquals(m_productInstanceUri, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_productInstanceUri = value;
        }
    }

    public PropertyState<string> SerialNumber
    {
        get => m_serialNumber;

        set
        {
            if (!Object.ReferenceEquals(m_serialNumber, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_serialNumber = value;
        }
    }

    public PropertyState<string> SoftwareRevision
    {
        get => m_softwareRevision;

        set
        {
            if (!Object.ReferenceEquals(m_softwareRevision, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_softwareRevision = value;
        }
    }

    public PropertyState<ushort> YearOfConstruction
    {
        get => m_yearOfConstruction;

        set
        {
            if (!Object.ReferenceEquals(m_yearOfConstruction, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_yearOfConstruction = value;
        }
    }
    #endregion

    #region Overridden Methods
    public override void GetChildren(
        ISystemContext context,
        IList<BaseInstanceState> children)
    {
        if (m_assetId != null)
        {
            children.Add(m_assetId);
        }

        if (m_componentName != null)
        {
            children.Add(m_componentName);
        }

        if (m_deviceClass != null)
        {
            children.Add(m_deviceClass);
        }

        if (m_hardwareRevision != null)
        {
            children.Add(m_hardwareRevision);
        }

        if (m_initialOperationDate != null)
        {
            children.Add(m_initialOperationDate);
        }

        if (m_manufacturer != null)
        {
            children.Add(m_manufacturer);
        }

        if (m_manufacturerUri != null)
        {
            children.Add(m_manufacturerUri);
        }

        if (m_model != null)
        {
            children.Add(m_model);
        }

        if (m_monthOfConstruction != null)
        {
            children.Add(m_monthOfConstruction);
        }

        if (m_productCode != null)
        {
            children.Add(m_productCode);
        }

        if (m_productInstanceUri != null)
        {
            children.Add(m_productInstanceUri);
        }

        if (m_serialNumber != null)
        {
            children.Add(m_serialNumber);
        }

        if (m_softwareRevision != null)
        {
            children.Add(m_softwareRevision);
        }

        if (m_yearOfConstruction != null)
        {
            children.Add(m_yearOfConstruction);
        }

        base.GetChildren(context, children);
    }

    protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
    {
        if (Object.ReferenceEquals(m_assetId, child))
        {
            m_assetId = null;
            return;
        }

        if (Object.ReferenceEquals(m_componentName, child))
        {
            m_componentName = null;
            return;
        }

        if (Object.ReferenceEquals(m_deviceClass, child))
        {
            m_deviceClass = null;
            return;
        }

        if (Object.ReferenceEquals(m_hardwareRevision, child))
        {
            m_hardwareRevision = null;
            return;
        }

        if (Object.ReferenceEquals(m_initialOperationDate, child))
        {
            m_initialOperationDate = null;
            return;
        }

        if (Object.ReferenceEquals(m_manufacturer, child))
        {
            m_manufacturer = null;
            return;
        }

        if (Object.ReferenceEquals(m_manufacturerUri, child))
        {
            m_manufacturerUri = null;
            return;
        }

        if (Object.ReferenceEquals(m_model, child))
        {
            m_model = null;
            return;
        }

        if (Object.ReferenceEquals(m_monthOfConstruction, child))
        {
            m_monthOfConstruction = null;
            return;
        }

        if (Object.ReferenceEquals(m_productCode, child))
        {
            m_productCode = null;
            return;
        }

        if (Object.ReferenceEquals(m_productInstanceUri, child))
        {
            m_productInstanceUri = null;
            return;
        }

        if (Object.ReferenceEquals(m_serialNumber, child))
        {
            m_serialNumber = null;
            return;
        }

        if (Object.ReferenceEquals(m_softwareRevision, child))
        {
            m_softwareRevision = null;
            return;
        }

        if (Object.ReferenceEquals(m_yearOfConstruction, child))
        {
            m_yearOfConstruction = null;
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
            case UAModel.DI.BrowseNames.AssetId:
                {
                    if (createOrReplace)
                    {
                        if (AssetId == null)
                        {
                            if (replacement == null)
                            {
                                AssetId = new PropertyState<string>(this);
                            }
                            else
                            {
                                AssetId = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = AssetId;
                    break;
                }

            case UAModel.DI.BrowseNames.ComponentName:
                {
                    if (createOrReplace)
                    {
                        if (ComponentName == null)
                        {
                            if (replacement == null)
                            {
                                ComponentName = new PropertyState<LocalizedText>(this);
                            }
                            else
                            {
                                ComponentName = (PropertyState<LocalizedText>)replacement;
                            }
                        }
                    }

                    instance = ComponentName;
                    break;
                }

            case UAModel.DI.BrowseNames.DeviceClass:
                {
                    if (createOrReplace)
                    {
                        if (DeviceClass == null)
                        {
                            if (replacement == null)
                            {
                                DeviceClass = new PropertyState<string>(this);
                            }
                            else
                            {
                                DeviceClass = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = DeviceClass;
                    break;
                }

            case UAModel.DI.BrowseNames.HardwareRevision:
                {
                    if (createOrReplace)
                    {
                        if (HardwareRevision == null)
                        {
                            if (replacement == null)
                            {
                                HardwareRevision = new PropertyState<string>(this);
                            }
                            else
                            {
                                HardwareRevision = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = HardwareRevision;
                    break;
                }

            case UAModel.Machinery.BrowseNames.InitialOperationDate:
                {
                    if (createOrReplace)
                    {
                        if (InitialOperationDate == null)
                        {
                            if (replacement == null)
                            {
                                InitialOperationDate = new PropertyState<DateTime>(this);
                            }
                            else
                            {
                                InitialOperationDate = (PropertyState<DateTime>)replacement;
                            }
                        }
                    }

                    instance = InitialOperationDate;
                    break;
                }

            case UAModel.DI.BrowseNames.Manufacturer:
                {
                    if (createOrReplace)
                    {
                        if (Manufacturer == null)
                        {
                            if (replacement == null)
                            {
                                Manufacturer = new PropertyState<LocalizedText>(this);
                            }
                            else
                            {
                                Manufacturer = (PropertyState<LocalizedText>)replacement;
                            }
                        }
                    }

                    instance = Manufacturer;
                    break;
                }

            case UAModel.DI.BrowseNames.ManufacturerUri:
                {
                    if (createOrReplace)
                    {
                        if (ManufacturerUri == null)
                        {
                            if (replacement == null)
                            {
                                ManufacturerUri = new PropertyState<string>(this);
                            }
                            else
                            {
                                ManufacturerUri = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = ManufacturerUri;
                    break;
                }

            case UAModel.DI.BrowseNames.Model:
                {
                    if (createOrReplace)
                    {
                        if (Model == null)
                        {
                            if (replacement == null)
                            {
                                Model = new PropertyState<LocalizedText>(this);
                            }
                            else
                            {
                                Model = (PropertyState<LocalizedText>)replacement;
                            }
                        }
                    }

                    instance = Model;
                    break;
                }

            case UAModel.Machinery.BrowseNames.MonthOfConstruction:
                {
                    if (createOrReplace)
                    {
                        if (MonthOfConstruction == null)
                        {
                            if (replacement == null)
                            {
                                MonthOfConstruction = new PropertyState<byte>(this);
                            }
                            else
                            {
                                MonthOfConstruction = (PropertyState<byte>)replacement;
                            }
                        }
                    }

                    instance = MonthOfConstruction;
                    break;
                }

            case UAModel.DI.BrowseNames.ProductCode:
                {
                    if (createOrReplace)
                    {
                        if (ProductCode == null)
                        {
                            if (replacement == null)
                            {
                                ProductCode = new PropertyState<string>(this);
                            }
                            else
                            {
                                ProductCode = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = ProductCode;
                    break;
                }

            case UAModel.DI.BrowseNames.ProductInstanceUri:
                {
                    if (createOrReplace)
                    {
                        if (ProductInstanceUri == null)
                        {
                            if (replacement == null)
                            {
                                ProductInstanceUri = new PropertyState<string>(this);
                            }
                            else
                            {
                                ProductInstanceUri = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = ProductInstanceUri;
                    break;
                }

            case UAModel.DI.BrowseNames.SerialNumber:
                {
                    if (createOrReplace)
                    {
                        if (SerialNumber == null)
                        {
                            if (replacement == null)
                            {
                                SerialNumber = new PropertyState<string>(this);
                            }
                            else
                            {
                                SerialNumber = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = SerialNumber;
                    break;
                }

            case UAModel.DI.BrowseNames.SoftwareRevision:
                {
                    if (createOrReplace)
                    {
                        if (SoftwareRevision == null)
                        {
                            if (replacement == null)
                            {
                                SoftwareRevision = new PropertyState<string>(this);
                            }
                            else
                            {
                                SoftwareRevision = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = SoftwareRevision;
                    break;
                }

            case UAModel.Machinery.BrowseNames.YearOfConstruction:
                {
                    if (createOrReplace)
                    {
                        if (YearOfConstruction == null)
                        {
                            if (replacement == null)
                            {
                                YearOfConstruction = new PropertyState<ushort>(this);
                            }
                            else
                            {
                                YearOfConstruction = (PropertyState<ushort>)replacement;
                            }
                        }
                    }

                    instance = YearOfConstruction;
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
    private PropertyState<string> m_assetId;
    private PropertyState<LocalizedText> m_componentName;
    private PropertyState<string> m_deviceClass;
    private PropertyState<string> m_hardwareRevision;
    private PropertyState<DateTime> m_initialOperationDate;
    private PropertyState<LocalizedText> m_manufacturer;
    private PropertyState<string> m_manufacturerUri;
    private PropertyState<LocalizedText> m_model;
    private PropertyState<byte> m_monthOfConstruction;
    private PropertyState<string> m_productCode;
    private PropertyState<string> m_productInstanceUri;
    private PropertyState<string> m_serialNumber;
    private PropertyState<string> m_softwareRevision;
    private PropertyState<ushort> m_yearOfConstruction;
    #endregion
}
#endif
#endregion

#region MachineIdentificationTypeState Class
#if (!OPCUA_EXCLUDE_MachineIdentificationTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class MachineIdentificationTypeState : MachineryItemIdentificationTypeState
{
    #region Constructors
    public MachineIdentificationTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.MachineIdentificationType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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

        if (Location != null)
        {
            Location.Initialize(context, Location_InitializationString);
        }
    }

    #region Initialization String
    private const string Location_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAABAAgAAABMb2NhdGlvbgEBjRcDAAAAAC0BAABUbyBiZSB1c2VkIGJ5IGVuZCB1c2VycyB0" +
       "byBzdG9yZSB0aGUgbG9jYXRpb24gb2YgdGhlIG1hY2hpbmUgaW4gYSBzY2hlbWUgc3BlY2lmaWMgdG8g" +
       "dGhlIGVuZCB1c2VyLiBTZXJ2ZXJzIHNoYWxsIHN1cHBvcnQgYXQgbGVhc3QgNjAgVW5pY29kZSBjaGFy" +
       "YWN0ZXJzIGZvciB0aGUgY2xpZW50cyB3cml0aW5nIHRoaXMgdmFsdWUsIHRoaXMgbWVhbnMgY2xpZW50" +
       "cyBjYW4gZXhwZWN0IHRvIGJlIGFibGUgdG8gd3JpdGUgc3RyaW5ncyB3aXRoIGEgbGVuZ3RoIG9mIDYw" +
       "IFVuaWNvZGUgY2hhcmFjdGVycyBpbnRvIHRoYXQgZmllbGQuAC4ARI0XAAAADP////8DA/////8AAAAA";

    private const string InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABACEAAABNYWNoaW5lSWRlbnRpZmljYXRpb25UeXBlSW5zdGFuY2UBAfQDAQH0A/QDAAAC" +
       "AAAAAQDDRAABAfMDAQDDRAABAfIDBQAAADVgqQoCAAAAAAAZAAAARGVmYXVsdEluc3RhbmNlQnJvd3Nl" +
       "TmFtZQEBjhcDAAAAADEAAABUaGUgZGVmYXVsdCBCcm93c2VOYW1lIGZvciBpbnN0YW5jZXMgb2YgdGhl" +
       "IHR5cGUuAC4ARI4XAAAUAwAOAAAASWRlbnRpZmljYXRpb24AFP////8BAf////8AAAAANWCJCgIAAAAD" +
       "AAwAAABNYW51ZmFjdHVyZXIBAXIXAwAAAABKAAAAQSBodW1hbi1yZWFkYWJsZSwgbG9jYWxpemVkIG5h" +
       "bWUgb2YgdGhlIG1hbnVmYWN0dXJlciBvZiB0aGUgTWFjaGluZXJ5SXRlbS4ALgBEchcAAAAV/////wEB" +
       "/////wAAAAA1YIkKAgAAAAMAEgAAAFByb2R1Y3RJbnN0YW5jZVVyaQEBfxcDAAAAAFEAAABBIGdsb2Jh" +
       "bGx5IHVuaXF1ZSByZXNvdXJjZSBpZGVudGlmaWVyIHByb3ZpZGVkIGJ5IHRoZSBtYW51ZmFjdHVyZXIg" +
       "b2YgdGhlIG1hY2hpbmUALgBEfxcAAAAM/////wEB/////wAAAAA1YIkKAgAAAAMADAAAAFNlcmlhbE51" +
       "bWJlcgEBcxcDAAAAABcBAABBIHN0cmluZyBjb250YWluaW5nIGEgdW5pcXVlIHByb2R1Y3Rpb24gbnVt" +
       "YmVyIG9mIHRoZSBtYW51ZmFjdHVyZXIgb2YgdGhlIE1hY2hpbmVyeUl0ZW0uIFRoZSBnbG9iYWwgdW5p" +
       "cXVlbmVzcyBvZiB0aGUgc2VyaWFsIG51bWJlciBpcyBvbmx5IGdpdmVuIGluIHRoZSBjb250ZXh0IG9m" +
       "IHRoZSBtYW51ZmFjdHVyZXIsIGFuZCBwb3RlbnRpYWxseSB0aGUgbW9kZWwuIFRoZSB2YWx1ZSBzaGFs" +
       "bCBub3QgY2hhbmdlIGR1cmluZyB0aGUgbGlmZS1jeWNsZSBvZiB0aGUgTWFjaGluZXJ5SXRlbS4ALgBE" +
       "cxcAAAAM/////wEB/////wAAAAA1YIkKAgAAAAEACAAAAExvY2F0aW9uAQGNFwMAAAAALQEAAFRvIGJl" +
       "IHVzZWQgYnkgZW5kIHVzZXJzIHRvIHN0b3JlIHRoZSBsb2NhdGlvbiBvZiB0aGUgbWFjaGluZSBpbiBh" +
       "IHNjaGVtZSBzcGVjaWZpYyB0byB0aGUgZW5kIHVzZXIuIFNlcnZlcnMgc2hhbGwgc3VwcG9ydCBhdCBs" +
       "ZWFzdCA2MCBVbmljb2RlIGNoYXJhY3RlcnMgZm9yIHRoZSBjbGllbnRzIHdyaXRpbmcgdGhpcyB2YWx1" +
       "ZSwgdGhpcyBtZWFucyBjbGllbnRzIGNhbiBleHBlY3QgdG8gYmUgYWJsZSB0byB3cml0ZSBzdHJpbmdz" +
       "IHdpdGggYSBsZW5ndGggb2YgNjAgVW5pY29kZSBjaGFyYWN0ZXJzIGludG8gdGhhdCBmaWVsZC4ALgBE" +
       "jRcAAAAM/////wMD/////wAAAAA=";
    #endregion
#endif
    #endregion

    #region Public Properties
    public PropertyState<string> Location
    {
        get => m_location;

        set
        {
            if (!Object.ReferenceEquals(m_location, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_location = value;
        }
    }
    #endregion

    #region Overridden Methods
    public override void GetChildren(
        ISystemContext context,
        IList<BaseInstanceState> children)
    {
        if (m_location != null)
        {
            children.Add(m_location);
        }

        base.GetChildren(context, children);
    }

    protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
    {
        if (Object.ReferenceEquals(m_location, child))
        {
            m_location = null;
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
            case UAModel.Machinery.BrowseNames.Location:
                {
                    if (createOrReplace)
                    {
                        if (Location == null)
                        {
                            if (replacement == null)
                            {
                                Location = new PropertyState<string>(this);
                            }
                            else
                            {
                                Location = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = Location;
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
    private PropertyState<string> m_location;
    #endregion
}
#endif
#endregion

#region MachineryComponentIdentificationTypeState Class
#if (!OPCUA_EXCLUDE_MachineryComponentIdentificationTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class MachineryComponentIdentificationTypeState : MachineryItemIdentificationTypeState
{
    #region Constructors
    public MachineryComponentIdentificationTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.MachineryComponentIdentificationType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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

        if (DeviceRevision != null)
        {
            DeviceRevision.Initialize(context, DeviceRevision_InitializationString);
        }
    }

    #region Initialization String
    private const string DeviceRevision_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAADAA4AAABEZXZpY2VSZXZpc2lvbgEBgRcDAAAAAAgBAABBIHN0cmluZyByZXByZXNlbnRh" +
       "dGlvbiBvZiB0aGUgb3ZlcmFsbCByZXZpc2lvbiBsZXZlbCBvZiB0aGUgY29tcG9uZW50LiBPZnRlbiwg" +
       "aXQgaXMgaW5jcmVhc2VkIHdoZW4gZWl0aGVyIHRoZSBTb2Z0d2FyZVJldmlzaW9uIGFuZCAvIG9yIHRo" +
       "ZSBIYXJkd2FyZVJldmlzaW9uIG9mIHRoZSBjb21wb25lbnQgaXMgaW5jcmVhc2VkLiBBcyBhbiBleGFt" +
       "cGxlLCBpdCBjYW4gYmUgdXNlZCBpbiBFUlAgc3lzdGVtcyB0b2dldGhlciB3aXRoIHRoZSBQcm9kdWN0" +
       "Q29kZS4ALgBEgRcAAAAM/////wEB/////wAAAAA=";

    private const string InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABACwAAABNYWNoaW5lcnlDb21wb25lbnRJZGVudGlmaWNhdGlvblR5cGVJbnN0YW5jZQEB" +
       "7QMBAe0D7QMAAP////8EAAAANWCpCgIAAAAAABkAAABEZWZhdWx0SW5zdGFuY2VCcm93c2VOYW1lAQGA" +
       "FwMAAAAAMQAAAFRoZSBkZWZhdWx0IEJyb3dzZU5hbWUgZm9yIGluc3RhbmNlcyBvZiB0aGUgdHlwZS4A" +
       "LgBEgBcAABQDAA4AAABJZGVudGlmaWNhdGlvbgAU/////wMD/////wAAAAA1YIkKAgAAAAMADAAAAE1h" +
       "bnVmYWN0dXJlcgEBchcDAAAAAEoAAABBIGh1bWFuLXJlYWRhYmxlLCBsb2NhbGl6ZWQgbmFtZSBvZiB0" +
       "aGUgbWFudWZhY3R1cmVyIG9mIHRoZSBNYWNoaW5lcnlJdGVtLgAuAERyFwAAABX/////AQH/////AAAA" +
       "ADVgiQoCAAAAAwAMAAAAU2VyaWFsTnVtYmVyAQFzFwMAAAAAFwEAAEEgc3RyaW5nIGNvbnRhaW5pbmcg" +
       "YSB1bmlxdWUgcHJvZHVjdGlvbiBudW1iZXIgb2YgdGhlIG1hbnVmYWN0dXJlciBvZiB0aGUgTWFjaGlu" +
       "ZXJ5SXRlbS4gVGhlIGdsb2JhbCB1bmlxdWVuZXNzIG9mIHRoZSBzZXJpYWwgbnVtYmVyIGlzIG9ubHkg" +
       "Z2l2ZW4gaW4gdGhlIGNvbnRleHQgb2YgdGhlIG1hbnVmYWN0dXJlciwgYW5kIHBvdGVudGlhbGx5IHRo" +
       "ZSBtb2RlbC4gVGhlIHZhbHVlIHNoYWxsIG5vdCBjaGFuZ2UgZHVyaW5nIHRoZSBsaWZlLWN5Y2xlIG9m" +
       "IHRoZSBNYWNoaW5lcnlJdGVtLgAuAERzFwAAAAz/////AQH/////AAAAADVgiQoCAAAAAwAOAAAARGV2" +
       "aWNlUmV2aXNpb24BAYEXAwAAAAAIAQAAQSBzdHJpbmcgcmVwcmVzZW50YXRpb24gb2YgdGhlIG92ZXJh" +
       "bGwgcmV2aXNpb24gbGV2ZWwgb2YgdGhlIGNvbXBvbmVudC4gT2Z0ZW4sIGl0IGlzIGluY3JlYXNlZCB3" +
       "aGVuIGVpdGhlciB0aGUgU29mdHdhcmVSZXZpc2lvbiBhbmQgLyBvciB0aGUgSGFyZHdhcmVSZXZpc2lv" +
       "biBvZiB0aGUgY29tcG9uZW50IGlzIGluY3JlYXNlZC4gQXMgYW4gZXhhbXBsZSwgaXQgY2FuIGJlIHVz" +
       "ZWQgaW4gRVJQIHN5c3RlbXMgdG9nZXRoZXIgd2l0aCB0aGUgUHJvZHVjdENvZGUuAC4ARIEXAAAADP//" +
       "//8BAf////8AAAAA";
    #endregion
#endif
    #endregion

    #region Public Properties
    public PropertyState<string> DeviceRevision
    {
        get => m_deviceRevision;

        set
        {
            if (!Object.ReferenceEquals(m_deviceRevision, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_deviceRevision = value;
        }
    }
    #endregion

    #region Overridden Methods
    public override void GetChildren(
        ISystemContext context,
        IList<BaseInstanceState> children)
    {
        if (m_deviceRevision != null)
        {
            children.Add(m_deviceRevision);
        }

        base.GetChildren(context, children);
    }

    protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
    {
        if (Object.ReferenceEquals(m_deviceRevision, child))
        {
            m_deviceRevision = null;
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
            case UAModel.DI.BrowseNames.DeviceRevision:
                {
                    if (createOrReplace)
                    {
                        if (DeviceRevision == null)
                        {
                            if (replacement == null)
                            {
                                DeviceRevision = new PropertyState<string>(this);
                            }
                            else
                            {
                                DeviceRevision = (PropertyState<string>)replacement;
                            }
                        }
                    }

                    instance = DeviceRevision;
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
    private PropertyState<string> m_deviceRevision;
    #endregion
}
#endif
#endregion

#region MachineryOperationCounterTypeState Class
#if (!OPCUA_EXCLUDE_MachineryOperationCounterTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class MachineryOperationCounterTypeState : FunctionalGroupTypeState
{
    #region Constructors
    public MachineryOperationCounterTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.MachineryOperationCounterType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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

        if (OperationCycleCounter != null)
        {
            OperationCycleCounter.Initialize(context, OperationCycleCounter_InitializationString);
        }

        if (OperationDuration != null)
        {
            OperationDuration.Initialize(context, OperationDuration_InitializationString);
        }

        if (PowerOnDuration != null)
        {
            PowerOnDuration.Initialize(context, PowerOnDuration_InitializationString);
        }
    }

    #region Initialization String
    private const string OperationCycleCounter_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAADABUAAABPcGVyYXRpb25DeWNsZUNvdW50ZXIBAcEXAwAAAAAzAQAAT3BlcmF0aW9uQ3lj" +
       "bGVDb3VudGVyIGlzIGNvdW50aW5nIHRoZSB0aW1lcyB0aGUgY29tcG9uZW50IHN3aXRjaGVzIGZyb20g" +
       "bm90IHBlcmZvcm1pbmcgYW4gYWN0aXZpdHkgdG8gcGVyZm9ybWluZyBhbiBhY3Rpdml0eS4gRm9yIGV4" +
       "YW1wbGUsIGVhY2ggdGltZSBhIHZhbHZlIHN0YXJ0cyBtb3ZpbmcsIGlzIGNvdW50ZWQuIFRoaXMgdmFs" +
       "dWUgc2hhbGwgb25seSBpbmNyZWFzZSBkdXJpbmcgdGhlIGxpZmV0aW1lIG9mIHRoZSBjb21wb25lbnQg" +
       "YW5kIHNoYWxsIG5vdCBiZSByZXNldCB3aGVuIHRoZSBjb21wb25lbnQgaXMgcmVzdGFydGVkLgAuAETB" +
       "FwAAABz/////AwP/////AAAAAA==";

    private const string OperationDuration_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAADABEAAABPcGVyYXRpb25EdXJhdGlvbgEBwBcDAAAAAPoCAABPcGVyYXRpb25EdXJhdGlv" +
       "biBpcyB0aGUgZHVyYXRpb24gdGhlIE1hY2hpbmVyeUl0ZW0gaGFzIGJlZW4gcG93ZXJlZCBhbmQgcGVy" +
       "Zm9ybWluZyBhbiBhY3Rpdml0eS4gVGhpcyBjb3VudGVyIGlzIGludGVuZGVkIGZvciBtYWNoaW5lcyBh" +
       "bmQgY29tcG9uZW50cyB3aGVyZSBhIGRpc3RpbmN0aW9uIGlzIG1hZGUgYmV0d2VlbiBzd2l0Y2hlZCBv" +
       "biBhbmQgaW4gb3BlcmF0aW9uLiBGb3IgZXhhbXBsZSwgYSBkcml2ZSBtaWdodCBiZSBwb3dlcmVkIG9u" +
       "IGJ1dCBub3Qgb3BlcmF0aW5nLiBJdCBpcyBub3QgaW50ZW5kZWQgZm9yIG1hY2hpbmVzIG9yIGNvbXBv" +
       "bmVudHMgYWx3YXlzIHBlcmZvcm1pbmcgYW4gYWN0aXZpdHkgbGlrZSBzZW5zb3JzIGFsd2F5cyBtZWFz" +
       "dXJpbmcgZGF0YS4gVGhpcyB2YWx1ZSBzaGFsbCBvbmx5IGluY3JlYXNlIGR1cmluZyB0aGUgbGlmZXRp" +
       "bWUgb2YgdGhlIE1hY2hpbmVyeUl0ZW0gYW5kIHNoYWxsIG5vdCBiZSByZXNldCB3aGVuIGl0IGlzIHJl" +
       "c3RhcnRlZC4gVGhlIE9wZXJhdGlvbkR1cmF0aW9uIGlzIHByb3ZpZGVkIGFzIER1cmF0aW9uLCBpLmUu" +
       "LCBpbiBtaWxsaXNlY29uZHMgb3IgZXZlbiBmcmFjdGlvbnMgb2YgYSBtaWxsaXNlY29uZC4gSG93ZXZl" +
       "ciwgdGhlIFNlcnZlciBpcyBub3QgZXhwZWN0ZWQgdG8gdXBkYXRlIHRoZSB2YWx1ZSBpbiBzdWNoIGEg" +
       "aGlnaCBmcmVxdWVuY3ksIGJ1dCBtYXliZSBvbmNlIGEgbWludXRlIG9yIG9uY2UgYW4gaG91ciwgZGVw" +
       "ZW5kaW5nIG9uIHRoZSBhcHBsaWNhdGlvbi4ALgBEwBcAAAEAIgH/////AwP/////AAAAAA==";

    private const string PowerOnDuration_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "NWCJCgIAAAADAA8AAABQb3dlck9uRHVyYXRpb24BAb8XAwAAAABFAwAAUG93ZXJPbkR1cmF0aW9uIGlz" +
       "IHRoZSBkdXJhdGlvbiB0aGUgTWFjaGluZXJ5SXRlbSBoYXMgYmVlbiBwb3dlcmVkLiBUaGUgbWFpbiBw" +
       "dXJwb3NlIGlzIHRvIGRldGVybWluZSB0aGUgdGltZSBpbiB3aGljaCBkZWdyYWRhdGlvbiBvZiB0aGUg" +
       "TWFjaGluZXJ5SXRlbSBvY2N1cnJlZC4gVGhlIGRldGFpbHMsIHdoZW4gdGhlIHRpbWUgaXMgY291bnRl" +
       "ZCwgaXMgaW1wbGVtZW50YXRpb24tc3BlY2lmaWMuIENvbXBhbmlvbiBzcGVjaWZpY2F0aW9ucyBtaWdo" +
       "dCBkZWZpbmUgc3BlY2lmaWMgcnVsZXMuIFR5cGljYWxseSwgd2hlbiB0aGUgTWFjaGluZXJ5SXRlbSBo" +
       "YXMgc3VwcGx5IHZvbHRhZ2UgYW5kIHRoZSBtYWluIENQVSBpcyBydW5uaW5nLCB0aGUgdGltZSBpcyBj" +
       "b3VudGVkLiBUaGlzIG1heSBpbmNsdWRlIGFueSBraW5kIG9mIHNsZWVwIG1vZGUsIGJ1dCBtYXkgbm90" +
       "IGluY2x1ZGUgcHVyZSBXYWtlIG9uIExBTi4gVGhpcyB2YWx1ZSBzaGFsbCBvbmx5IGluY3JlYXNlIGR1" +
       "cmluZyB0aGUgbGlmZXRpbWUgb2YgdGhlIE1hY2hpbmVyeUl0ZW0gYW5kIHNoYWxsIG5vdCBiZSByZXNl" +
       "dCB3aGVuIGl0IGlzIHJlc3RhcnRlZC4gVGhlIFBvd2VyT25EdXJhdGlvbiBpcyBwcm92aWRlZCBhcyBE" +
       "dXJhdGlvbiwgaS5lLiwgaW4gbWlsbGlzZWNvbmRzIG9yIGV2ZW4gZnJhY3Rpb25zIG9mIGEgbWlsbGlz" +
       "ZWNvbmQuIEhvd2V2ZXIsIHRoZSBTZXJ2ZXIgaXMgbm90IGV4cGVjdGVkIHRvIHVwZGF0ZSB0aGUgdmFs" +
       "dWUgaW4gc3VjaCBhIGhpZ2ggZnJlcXVlbmN5LCBidXQgbWF5YmUgb25jZSBhIG1pbnV0ZSBvciBvbmNl" +
       "IGFuIGhvdXIsIGRlcGVuZGluZyBvbiB0aGUgYXBwbGljYXRpb24uAC4ARL8XAAABACIB/////wMD////" +
       "/wAAAAA=";

    private const string InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABACUAAABNYWNoaW5lcnlPcGVyYXRpb25Db3VudGVyVHlwZUluc3RhbmNlAQHxAwEB8QPx" +
       "AwAAAQAAAAEAw0QAAQPgAQQAAAA1YKkKAgAAAAAAGQAAAERlZmF1bHRJbnN0YW5jZUJyb3dzZU5hbWUB" +
       "AcIXAwAAAAAwAAAAVGhlIGRlZmF1bHQgQnJvd3NlTmFtZSBmb3IgaW5zdGFuY2VzIG9mIHRoZSB0eXBl" +
       "AC4ARMIXAAAUAwARAAAAT3BlcmF0aW9uQ291bnRlcnMAFP////8DA/////8AAAAANWCJCgIAAAADABUA" +
       "AABPcGVyYXRpb25DeWNsZUNvdW50ZXIBAcEXAwAAAAAzAQAAT3BlcmF0aW9uQ3ljbGVDb3VudGVyIGlz" +
       "IGNvdW50aW5nIHRoZSB0aW1lcyB0aGUgY29tcG9uZW50IHN3aXRjaGVzIGZyb20gbm90IHBlcmZvcm1p" +
       "bmcgYW4gYWN0aXZpdHkgdG8gcGVyZm9ybWluZyBhbiBhY3Rpdml0eS4gRm9yIGV4YW1wbGUsIGVhY2gg" +
       "dGltZSBhIHZhbHZlIHN0YXJ0cyBtb3ZpbmcsIGlzIGNvdW50ZWQuIFRoaXMgdmFsdWUgc2hhbGwgb25s" +
       "eSBpbmNyZWFzZSBkdXJpbmcgdGhlIGxpZmV0aW1lIG9mIHRoZSBjb21wb25lbnQgYW5kIHNoYWxsIG5v" +
       "dCBiZSByZXNldCB3aGVuIHRoZSBjb21wb25lbnQgaXMgcmVzdGFydGVkLgAuAETBFwAAABz/////AwP/" +
       "////AAAAADVgiQoCAAAAAwARAAAAT3BlcmF0aW9uRHVyYXRpb24BAcAXAwAAAAD6AgAAT3BlcmF0aW9u" +
       "RHVyYXRpb24gaXMgdGhlIGR1cmF0aW9uIHRoZSBNYWNoaW5lcnlJdGVtIGhhcyBiZWVuIHBvd2VyZWQg" +
       "YW5kIHBlcmZvcm1pbmcgYW4gYWN0aXZpdHkuIFRoaXMgY291bnRlciBpcyBpbnRlbmRlZCBmb3IgbWFj" +
       "aGluZXMgYW5kIGNvbXBvbmVudHMgd2hlcmUgYSBkaXN0aW5jdGlvbiBpcyBtYWRlIGJldHdlZW4gc3dp" +
       "dGNoZWQgb24gYW5kIGluIG9wZXJhdGlvbi4gRm9yIGV4YW1wbGUsIGEgZHJpdmUgbWlnaHQgYmUgcG93" +
       "ZXJlZCBvbiBidXQgbm90IG9wZXJhdGluZy4gSXQgaXMgbm90IGludGVuZGVkIGZvciBtYWNoaW5lcyBv" +
       "ciBjb21wb25lbnRzIGFsd2F5cyBwZXJmb3JtaW5nIGFuIGFjdGl2aXR5IGxpa2Ugc2Vuc29ycyBhbHdh" +
       "eXMgbWVhc3VyaW5nIGRhdGEuIFRoaXMgdmFsdWUgc2hhbGwgb25seSBpbmNyZWFzZSBkdXJpbmcgdGhl" +
       "IGxpZmV0aW1lIG9mIHRoZSBNYWNoaW5lcnlJdGVtIGFuZCBzaGFsbCBub3QgYmUgcmVzZXQgd2hlbiBp" +
       "dCBpcyByZXN0YXJ0ZWQuIFRoZSBPcGVyYXRpb25EdXJhdGlvbiBpcyBwcm92aWRlZCBhcyBEdXJhdGlv" +
       "biwgaS5lLiwgaW4gbWlsbGlzZWNvbmRzIG9yIGV2ZW4gZnJhY3Rpb25zIG9mIGEgbWlsbGlzZWNvbmQu" +
       "IEhvd2V2ZXIsIHRoZSBTZXJ2ZXIgaXMgbm90IGV4cGVjdGVkIHRvIHVwZGF0ZSB0aGUgdmFsdWUgaW4g" +
       "c3VjaCBhIGhpZ2ggZnJlcXVlbmN5LCBidXQgbWF5YmUgb25jZSBhIG1pbnV0ZSBvciBvbmNlIGFuIGhv" +
       "dXIsIGRlcGVuZGluZyBvbiB0aGUgYXBwbGljYXRpb24uAC4ARMAXAAABACIB/////wMD/////wAAAAA1" +
       "YIkKAgAAAAMADwAAAFBvd2VyT25EdXJhdGlvbgEBvxcDAAAAAEUDAABQb3dlck9uRHVyYXRpb24gaXMg" +
       "dGhlIGR1cmF0aW9uIHRoZSBNYWNoaW5lcnlJdGVtIGhhcyBiZWVuIHBvd2VyZWQuIFRoZSBtYWluIHB1" +
       "cnBvc2UgaXMgdG8gZGV0ZXJtaW5lIHRoZSB0aW1lIGluIHdoaWNoIGRlZ3JhZGF0aW9uIG9mIHRoZSBN" +
       "YWNoaW5lcnlJdGVtIG9jY3VycmVkLiBUaGUgZGV0YWlscywgd2hlbiB0aGUgdGltZSBpcyBjb3VudGVk" +
       "LCBpcyBpbXBsZW1lbnRhdGlvbi1zcGVjaWZpYy4gQ29tcGFuaW9uIHNwZWNpZmljYXRpb25zIG1pZ2h0" +
       "IGRlZmluZSBzcGVjaWZpYyBydWxlcy4gVHlwaWNhbGx5LCB3aGVuIHRoZSBNYWNoaW5lcnlJdGVtIGhh" +
       "cyBzdXBwbHkgdm9sdGFnZSBhbmQgdGhlIG1haW4gQ1BVIGlzIHJ1bm5pbmcsIHRoZSB0aW1lIGlzIGNv" +
       "dW50ZWQuIFRoaXMgbWF5IGluY2x1ZGUgYW55IGtpbmQgb2Ygc2xlZXAgbW9kZSwgYnV0IG1heSBub3Qg" +
       "aW5jbHVkZSBwdXJlIFdha2Ugb24gTEFOLiBUaGlzIHZhbHVlIHNoYWxsIG9ubHkgaW5jcmVhc2UgZHVy" +
       "aW5nIHRoZSBsaWZldGltZSBvZiB0aGUgTWFjaGluZXJ5SXRlbSBhbmQgc2hhbGwgbm90IGJlIHJlc2V0" +
       "IHdoZW4gaXQgaXMgcmVzdGFydGVkLiBUaGUgUG93ZXJPbkR1cmF0aW9uIGlzIHByb3ZpZGVkIGFzIER1" +
       "cmF0aW9uLCBpLmUuLCBpbiBtaWxsaXNlY29uZHMgb3IgZXZlbiBmcmFjdGlvbnMgb2YgYSBtaWxsaXNl" +
       "Y29uZC4gSG93ZXZlciwgdGhlIFNlcnZlciBpcyBub3QgZXhwZWN0ZWQgdG8gdXBkYXRlIHRoZSB2YWx1" +
       "ZSBpbiBzdWNoIGEgaGlnaCBmcmVxdWVuY3ksIGJ1dCBtYXliZSBvbmNlIGEgbWludXRlIG9yIG9uY2Ug" +
       "YW4gaG91ciwgZGVwZW5kaW5nIG9uIHRoZSBhcHBsaWNhdGlvbi4ALgBEvxcAAAEAIgH/////AwP/////" +
       "AAAAAA==";
    #endregion
#endif
    #endregion

    #region Public Properties
    public PropertyState OperationCycleCounter
    {
        get => m_operationCycleCounter;

        set
        {
            if (!Object.ReferenceEquals(m_operationCycleCounter, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_operationCycleCounter = value;
        }
    }

    public PropertyState<double> OperationDuration
    {
        get => m_operationDuration;

        set
        {
            if (!Object.ReferenceEquals(m_operationDuration, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_operationDuration = value;
        }
    }

    public PropertyState<double> PowerOnDuration
    {
        get => m_powerOnDuration;

        set
        {
            if (!Object.ReferenceEquals(m_powerOnDuration, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_powerOnDuration = value;
        }
    }
    #endregion

    #region Overridden Methods
    public override void GetChildren(
        ISystemContext context,
        IList<BaseInstanceState> children)
    {
        if (m_operationCycleCounter != null)
        {
            children.Add(m_operationCycleCounter);
        }

        if (m_operationDuration != null)
        {
            children.Add(m_operationDuration);
        }

        if (m_powerOnDuration != null)
        {
            children.Add(m_powerOnDuration);
        }

        base.GetChildren(context, children);
    }

    protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
    {
        if (Object.ReferenceEquals(m_operationCycleCounter, child))
        {
            m_operationCycleCounter = null;
            return;
        }

        if (Object.ReferenceEquals(m_operationDuration, child))
        {
            m_operationDuration = null;
            return;
        }

        if (Object.ReferenceEquals(m_powerOnDuration, child))
        {
            m_powerOnDuration = null;
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
            case UAModel.DI.BrowseNames.OperationCycleCounter:
                {
                    if (createOrReplace)
                    {
                        if (OperationCycleCounter == null)
                        {
                            if (replacement == null)
                            {
                                OperationCycleCounter = new PropertyState(this);
                            }
                            else
                            {
                                OperationCycleCounter = (PropertyState)replacement;
                            }
                        }
                    }

                    instance = OperationCycleCounter;
                    break;
                }

            case UAModel.DI.BrowseNames.OperationDuration:
                {
                    if (createOrReplace)
                    {
                        if (OperationDuration == null)
                        {
                            if (replacement == null)
                            {
                                OperationDuration = new PropertyState<double>(this);
                            }
                            else
                            {
                                OperationDuration = (PropertyState<double>)replacement;
                            }
                        }
                    }

                    instance = OperationDuration;
                    break;
                }

            case UAModel.DI.BrowseNames.PowerOnDuration:
                {
                    if (createOrReplace)
                    {
                        if (PowerOnDuration == null)
                        {
                            if (replacement == null)
                            {
                                PowerOnDuration = new PropertyState<double>(this);
                            }
                            else
                            {
                                PowerOnDuration = (PropertyState<double>)replacement;
                            }
                        }
                    }

                    instance = PowerOnDuration;
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
    private PropertyState m_operationCycleCounter;
    private PropertyState<double> m_operationDuration;
    private PropertyState<double> m_powerOnDuration;
    #endregion
}
#endif
#endregion

#region MachineryEquipmentFolderTypeState Class
#if (!OPCUA_EXCLUDE_MachineryEquipmentFolderTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class MachineryEquipmentFolderTypeState : FolderState
{
    #region Constructors
    public MachineryEquipmentFolderTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.MachineryEquipmentFolderType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABACQAAABNYWNoaW5lcnlFcXVpcG1lbnRGb2xkZXJUeXBlSW5zdGFuY2UBAfUDAQH1A/UD" +
       "AAD/////AgAAACRgwAoBAAAAHgAAAE1hY2hpbmVyeUVxdWlwbWVudF9QbGFjZWhvbGRlcgEAFAAAADxN" +
       "YWNoaW5lcnlFcXVpcG1lbnQ+AQG8EwMAAAAATwAAAFBsYWNlaG9sZGVyIGZvciBNYWNoaW5lcnlFcXVp" +
       "cG1lbnQgdGhhdCBpbXBsZW1lbnRzIHRoZSBJTWFjaGluZXJ5RXF1aXBtZW50VHlwZS4ALwA6vBMAAAIA" +
       "AAABAMNEAAEB7wMBAMNEAAEDuzoJAAAANWCJCgIAAAADAAcAAABBc3NldElkAQHQFwMAAAAAhQAAAENv" +
       "bXBhbnl3aWRlIHVuaXF1ZSBJRCBmb3IgYSBzcGVjaWZpYyBhc3NldCAoRWFjaCA4IG1tIGRyaWxsIG9m" +
       "IGEgY29tcGFueSBoYXMgdGhlIHNhbWUgTWFjaGluZXJ5RXF1aXBtZW50VHlwZUlkIGFuZCBhIHVuaXF1" +
       "ZSBBc3NldElkKS4ALgBE0BcAAAAM/////wMD/////wAAAAA1YIkKAgAAAAMADQAAAENvbXBvbmVudE5h" +
       "bWUBAdEXAwAAAAAlAAAAVXNlZCBuYW1lIGZvciB0aGUgTWFjaGluZXJ5RXF1aXBtZW50LgAuAETRFwAA" +
       "ABX/////AwP/////AAAAADVgiQoCAAAAAQALAAAARGVzY3JpcHRpb24BAdIXAwAAAADDAAAAQWRkaXRp" +
       "b25hbCBpbmZvcm1hdGlvbiBhbmQgZGVzY3JpcHRpb24gYWJvdXQgdGhlIE1hY2hpbmVyeUVxdWlwbWVu" +
       "dC4gU2hvdWxkIGJlIHVzZWQgaWYgRGVzY3JpcHRpb24gQXR0cmlidXRlIGNhbm5vdCBiZSB3cml0dGVu" +
       "IHZpYSBPUEMgVUEgYW5kIHNob3VsZCBiZSBpZGVhbGx5IGlkZW50aWNhbCB0byBEZXNjcmlwdGlvbiBB" +
       "dHRyaWJ1dGUuAC4ARNIXAAAAFf////8DA/////8AAAAANWCJCgIAAAADAAsAAABEZXZpY2VDbGFzcwEB" +
       "0xcDAAAAAFwAAABDbGFzcyBvZiB0aGUgTWFjaGluZXJ5RXF1aXBtZW50IChlLmcuOiBFYWNoIGRyaWxs" +
       "IG9mIGEgY29tcGFueSBoYXMgdGhlIERldmljZUNsYXNzICJkcmlsbCIpLgAuAETTFwAAAAz/////AQH/" +
       "////AAAAADVgiQoCAAAAAQAIAAAATG9jYXRpb24BAdQXAwAAAABzAAAATG9jYXRpb24gb2YgdGhlIE1h" +
       "Y2hpbmVyeUVxdWlwbWVudCAoZS5nLjogU3RvcmFnZSBMb2NhdGlvbjsgUG9zaXRpb24gaW4gdGhlIFRv" +
       "b2wgQ2hhbmdlcjsgUG9zaXRpb24gb24gdGhlIG1hY2hpbmUpLgAuAETUFwAAAAz/////AwP/////AAAA" +
       "ADVgiQoCAAAAAQAYAAAATWFjaGluZXJ5RXF1aXBtZW50VHlwZUlkAQHVFwMAAAAAjAAAAElkZW50aWZp" +
       "Y2F0aW9uIG9mIGEgZ2VuZXJpYyBNYWNoaW5lcnlFcXVpcG1lbnQuIERlZmluZWQgYnkgZWFjaCBjb21w" +
       "YW55IChlLmcuLCBjb21wYW55IGhhcyBhbiBNYWNoaW5lcnlFcXVpcG1lbnRUeXBlSWQgZm9yIGFsbCA4" +
       "IG1tIGRyaWxscykuAC4ARNUXAAAADP////8DA/////8AAAAANWCJCgIAAAADAA8AAABNYW51ZmFjdHVy" +
       "ZXJVcmkBAdYXAwAAAAAnAAAATWFudWZhY3R1cmVyIG9mIHRoZSBNYWNoaW5lcnlFcXVpcG1lbnQuAC4A" +
       "RNYXAAAADP////8BAf////8AAAAANWCJCgIAAAADAAUAAABNb2RlbAEB1xcDAAAAACAAAABNb2RlbCBv" +
       "ZiB0aGUgTWFjaGluZXJ5RXF1aXBtZW50LgAuAETXFwAAABX/////AQH/////AAAAADVgiQoCAAAAAwAM" +
       "AAAAU2VyaWFsTnVtYmVyAQHYFwMAAAAAKAAAAFNlcmlhbCBOdW1iZXIgb2YgdGhlIE1hY2hpbmVyeUVx" +
       "dWlwbWVudC4ALgBE2BcAAAAM/////wEB/////wAAAAA1YKkKAgAAAAAAGQAAAERlZmF1bHRJbnN0YW5j" +
       "ZUJyb3dzZU5hbWUBAdkXAwAAAAAxAAAAVGhlIGRlZmF1bHQgQnJvd3NlTmFtZSBmb3IgaW5zdGFuY2Vz" +
       "IG9mIHRoZSB0eXBlLgAuAETZFwAAFAEAEgAAAE1hY2hpbmVyeUVxdWlwbWVudAAU/////wMD/////wAA" +
       "AAA=";
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

#region MachineryLifetimeCounterTypeState Class
#if (!OPCUA_EXCLUDE_MachineryLifetimeCounterTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class MachineryLifetimeCounterTypeState : FolderState
{
    #region Constructors
    public MachineryLifetimeCounterTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.MachineryLifetimeCounterType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABACQAAABNYWNoaW5lcnlMaWZldGltZUNvdW50ZXJUeXBlSW5zdGFuY2UBAfcDAQH3A/cD" +
       "AAD/////AgAAABVgyQoCAAAAHAAAAExpZmV0aW1lVmFyaWFibGVfUGxhY2Vob2xkZXIBABIAAAA8TGlm" +
       "ZXRpbWVWYXJpYWJsZT4BAcMXAC8BA9QBwxcAAAAa/////wMD/////wMAAAAVYIkKAgAAAAAAEAAAAEVu" +
       "Z2luZWVyaW5nVW5pdHMBAcYXAC4ARMYXAAABAHcD/////wEB/////wAAAAA1YIkKAgAAAAMACgAAAFN0" +
       "YXJ0VmFsdWUBAcUXAwAAAABTAAAAU3RhcnRWYWx1ZSBpbmRpY2F0ZXMgdGhlIGluaXRpYWwgdmFsdWUs" +
       "IHdoZW4gdGhlcmUgaXMgc3RpbGwgdGhlIGZ1bGwgbGlmZXRpbWUgbGVmdC4ALgBExRcAAAAa/////wEB" +
       "/////wAAAAA1YIkKAgAAAAMACgAAAExpbWl0VmFsdWUBAcQXAwAAAAA/AAAATGltaXRWYWx1ZSBpbmRp" +
       "Y2F0ZXMgd2hlbiB0aGUgZW5kIG9mIGxpZmV0aW1lIGhhcyBiZWVuIHJlYWNoZWQuAC4ARMQXAAAAGv//" +
       "//8BAf////8AAAAANWCpCgIAAAAAABkAAABEZWZhdWx0SW5zdGFuY2VCcm93c2VOYW1lAQHHFwMAAAAA" +
       "MAAAAFRoZSBkZWZhdWx0IEJyb3dzZU5hbWUgZm9yIGluc3RhbmNlcyBvZiB0aGUgdHlwZQAuAETHFwAA" +
       "FAEAEAAAAExpZmV0aW1lQ291bnRlcnMAFP////8DA/////8AAAAA";
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

#region MonitoringTypeState Class
#if (!OPCUA_EXCLUDE_MonitoringTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class MonitoringTypeState : FolderState
{
    #region Constructors
    public MonitoringTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.MonitoringType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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

        if (Consumption != null)
        {
            Consumption.Initialize(context, Consumption_InitializationString);
        }

        if (Health != null)
        {
            Health.Initialize(context, Health_InitializationString);
        }

        if (Process != null)
        {
            Process.Initialize(context, Process_InitializationString);
        }

        if (Status != null)
        {
            Status.Initialize(context, Status_InitializationString);
        }
    }

    #region Initialization String
    private const string Consumption_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "JGCACgEAAAABAAsAAABDb25zdW1wdGlvbgEBtxMDAAAAAD0AAABFbnRyeSBwb2ludCBmb3IgY29uc3Vt" +
       "cHRpb24gaW5mb3JtYXRpb24gb2YgdGhlIE1hY2hpbmVyeUl0ZW0uAC8APbcTAAD/////AAAAAA==";

    private const string Health_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "JGCACgEAAAABAAYAAABIZWFsdGgBAbUTAwAAAAA3AAAARW50cnkgcG9pbnQgb2YgaGVhbHRoIGluZm9y" +
       "bWF0aW9uIG9mIHRoZSBNYWNoaW5lcnlJdGVtLgAvAD21EwAAAQAAAAEAw0QAAQPLOgIAAAAVYIkKAgAA" +
       "AAMADAAAAERldmljZUhlYWx0aAEBzxcALwA/zxcAAAEDZBj/////AwP/////AAAAAARggAoBAAAAAwAS" +
       "AAAARGV2aWNlSGVhbHRoQWxhcm1zAQG7EwAvAD27EwAA/////wAAAAA=";

    private const string Process_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "JGCACgEAAAABAAcAAABQcm9jZXNzAQG2EwMAAAAAOQAAAEVudHJ5IHBvaW50IGZvciBwcm9jZXNzIGlu" +
       "Zm9ybWF0aW9uIG9mIHRoZSBNYWNoaW5lcnlJdGVtLgAvAD22EwAA/////wAAAAA=";

    private const string Status_InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "JGCACgEAAAABAAYAAABTdGF0dXMBAbQTAwAAAADzAAAARW50cnkgcG9pbnQgZm9yIHN0YXR1cyBpbmZv" +
       "cm1hdGlvbiBvZiB0aGUgTWFjaGluZXJ5SXRlbS4gSWYgdGhpcyBPYmplY3QgaXMgcHJvdmlkZWQsIGFu" +
       "ZCB0aGUgTWFjaGluZXJ5SXRlbVN0YXRlIGlzIHByb3ZpZGVkLCBpdCBzaGFsbCBiZSByZWZlcmVuY2Vk" +
       "LiBJZiB0aGlzIE9iamVjdCBpcyBwcm92aWRlZCBhbmQgdGhlIE1hY2hpbmVyeU9wZXJhdGlvbk1vZGUg" +
       "aXMgcHJvdmlkZWQsIGl0IHNoYWxsIGJlIHJlZmVyZW5jZWQuAC8APbQTAAD/////AwAAAARggAoBAAAA" +
       "AQASAAAATWFjaGluZXJ5SXRlbVN0YXRlAQG4EwAvAQHqA7gTAAD/////AQAAABVgiQoCAAAAAAAMAAAA" +
       "Q3VycmVudFN0YXRlAQHKFwAvAQDICsoXAAAAFf////8BAf////8BAAAAFWCJCgIAAAAAAAIAAABJZAEB" +
       "yxcALgBEyxcAAAAR/////wEB/////wAAAAAEYIAKAQAAAAEADQAAAE9wZXJhdGlvbk1vZGUBAbkTAC8B" +
       "AfADuRMAAP////8BAAAAFWCJCgIAAAAAAAwAAABDdXJyZW50U3RhdGUBAcwXAC8BAMgKzBcAAAAV////" +
       "/wEB/////wEAAAAVYIkKAgAAAAAAAgAAAElkAQHNFwAuAETNFwAAABH/////AQH/////AAAAAARggAoB" +
       "AAAAAQAKAAAAU3RhY2tsaWdodAEBuhMALwEC6gO6EwAA/////wEAAAA1YIkKAgAAAAIADgAAAFN0YWNr" +
       "bGlnaHRNb2RlAQHOFwMAAAAAZwAAAFNob3dzIGluIHdoYXQgd2F5IChzdGFjayBvZiBpbmRpdmlkdWFs" +
       "IGxpZ2h0cywgbGV2ZWwgbWV0ZXIsIHJ1bm5pbmcgbGlnaHQpIHRoZSBzdGFja2xpZ2h0IHVuaXQgaXMg" +
       "dXNlZC4ALgBEzhcAAAECugv/////AwP/////AAAAAA==";

    private const string InitializationString =
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABABYAAABNb25pdG9yaW5nVHlwZUluc3RhbmNlAQH2AwEB9gP2AwAA/////wUAAAAkYIAK" +
       "AQAAAAEACwAAAENvbnN1bXB0aW9uAQG3EwMAAAAAPQAAAEVudHJ5IHBvaW50IGZvciBjb25zdW1wdGlv" +
       "biBpbmZvcm1hdGlvbiBvZiB0aGUgTWFjaGluZXJ5SXRlbS4ALwA9txMAAP////8AAAAANWCpCgIAAAAA" +
       "ABkAAABEZWZhdWx0SW5zdGFuY2VCcm93c2VOYW1lAQHJFwMAAAAAMQAAAFRoZSBkZWZhdWx0IEJyb3dz" +
       "ZU5hbWUgZm9yIGluc3RhbmNlcyBvZiB0aGUgdHlwZS4ALgBEyRcAABQBAAoAAABNb25pdG9yaW5nABT/" +
       "////AQH/////AAAAACRggAoBAAAAAQAGAAAASGVhbHRoAQG1EwMAAAAANwAAAEVudHJ5IHBvaW50IG9m" +
       "IGhlYWx0aCBpbmZvcm1hdGlvbiBvZiB0aGUgTWFjaGluZXJ5SXRlbS4ALwA9tRMAAAEAAAABAMNEAAED" +
       "yzoCAAAAFWCJCgIAAAADAAwAAABEZXZpY2VIZWFsdGgBAc8XAC8AP88XAAABA2QY/////wMD/////wAA" +
       "AAAEYIAKAQAAAAMAEgAAAERldmljZUhlYWx0aEFsYXJtcwEBuxMALwA9uxMAAP////8AAAAAJGCACgEA" +
       "AAABAAcAAABQcm9jZXNzAQG2EwMAAAAAOQAAAEVudHJ5IHBvaW50IGZvciBwcm9jZXNzIGluZm9ybWF0" +
       "aW9uIG9mIHRoZSBNYWNoaW5lcnlJdGVtLgAvAD22EwAA/////wAAAAAkYIAKAQAAAAEABgAAAFN0YXR1" +
       "cwEBtBMDAAAAAPMAAABFbnRyeSBwb2ludCBmb3Igc3RhdHVzIGluZm9ybWF0aW9uIG9mIHRoZSBNYWNo" +
       "aW5lcnlJdGVtLiBJZiB0aGlzIE9iamVjdCBpcyBwcm92aWRlZCwgYW5kIHRoZSBNYWNoaW5lcnlJdGVt" +
       "U3RhdGUgaXMgcHJvdmlkZWQsIGl0IHNoYWxsIGJlIHJlZmVyZW5jZWQuIElmIHRoaXMgT2JqZWN0IGlz" +
       "IHByb3ZpZGVkIGFuZCB0aGUgTWFjaGluZXJ5T3BlcmF0aW9uTW9kZSBpcyBwcm92aWRlZCwgaXQgc2hh" +
       "bGwgYmUgcmVmZXJlbmNlZC4ALwA9tBMAAP////8DAAAABGCACgEAAAABABIAAABNYWNoaW5lcnlJdGVt" +
       "U3RhdGUBAbgTAC8BAeoDuBMAAP////8BAAAAFWCJCgIAAAAAAAwAAABDdXJyZW50U3RhdGUBAcoXAC8B" +
       "AMgKyhcAAAAV/////wEB/////wEAAAAVYIkKAgAAAAAAAgAAAElkAQHLFwAuAETLFwAAABH/////AQH/" +
       "////AAAAAARggAoBAAAAAQANAAAAT3BlcmF0aW9uTW9kZQEBuRMALwEB8AO5EwAA/////wEAAAAVYIkK" +
       "AgAAAAAADAAAAEN1cnJlbnRTdGF0ZQEBzBcALwEAyArMFwAAABX/////AQH/////AQAAABVgiQoCAAAA" +
       "AAACAAAASWQBAc0XAC4ARM0XAAAAEf////8BAf////8AAAAABGCACgEAAAABAAoAAABTdGFja2xpZ2h0" +
       "AQG6EwAvAQLqA7oTAAD/////AQAAADVgiQoCAAAAAgAOAAAAU3RhY2tsaWdodE1vZGUBAc4XAwAAAABn" +
       "AAAAU2hvd3MgaW4gd2hhdCB3YXkgKHN0YWNrIG9mIGluZGl2aWR1YWwgbGlnaHRzLCBsZXZlbCBtZXRl" +
       "ciwgcnVubmluZyBsaWdodCkgdGhlIHN0YWNrbGlnaHQgdW5pdCBpcyB1c2VkLgAuAETOFwAAAQK6C///" +
       "//8DA/////8AAAAA";
    #endregion
#endif
    #endregion

    #region Public Properties
    public FolderState Consumption
    {
        get => m_consumption;

        set
        {
            if (!Object.ReferenceEquals(m_consumption, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_consumption = value;
        }
    }

    public FolderState Health
    {
        get => m_health;

        set
        {
            if (!Object.ReferenceEquals(m_health, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_health = value;
        }
    }

    public FolderState Process
    {
        get => m_process;

        set
        {
            if (!Object.ReferenceEquals(m_process, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_process = value;
        }
    }

    public FolderState Status
    {
        get => m_status;

        set
        {
            if (!Object.ReferenceEquals(m_status, value))
            {
                ChangeMasks |= NodeStateChangeMasks.Children;
            }

            m_status = value;
        }
    }
    #endregion

    #region Overridden Methods
    public override void GetChildren(
        ISystemContext context,
        IList<BaseInstanceState> children)
    {
        if (m_consumption != null)
        {
            children.Add(m_consumption);
        }

        if (m_health != null)
        {
            children.Add(m_health);
        }

        if (m_process != null)
        {
            children.Add(m_process);
        }

        if (m_status != null)
        {
            children.Add(m_status);
        }

        base.GetChildren(context, children);
    }

    protected override void RemoveExplicitlyDefinedChild(BaseInstanceState child)
    {
        if (Object.ReferenceEquals(m_consumption, child))
        {
            m_consumption = null;
            return;
        }

        if (Object.ReferenceEquals(m_health, child))
        {
            m_health = null;
            return;
        }

        if (Object.ReferenceEquals(m_process, child))
        {
            m_process = null;
            return;
        }

        if (Object.ReferenceEquals(m_status, child))
        {
            m_status = null;
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
            case UAModel.Machinery.BrowseNames.Consumption:
                {
                    if (createOrReplace)
                    {
                        if (Consumption == null)
                        {
                            if (replacement == null)
                            {
                                Consumption = new FolderState(this);
                            }
                            else
                            {
                                Consumption = (FolderState)replacement;
                            }
                        }
                    }

                    instance = Consumption;
                    break;
                }

            case UAModel.Machinery.BrowseNames.Health:
                {
                    if (createOrReplace)
                    {
                        if (Health == null)
                        {
                            if (replacement == null)
                            {
                                Health = new FolderState(this);
                            }
                            else
                            {
                                Health = (FolderState)replacement;
                            }
                        }
                    }

                    instance = Health;
                    break;
                }

            case UAModel.Machinery.BrowseNames.Process:
                {
                    if (createOrReplace)
                    {
                        if (Process == null)
                        {
                            if (replacement == null)
                            {
                                Process = new FolderState(this);
                            }
                            else
                            {
                                Process = (FolderState)replacement;
                            }
                        }
                    }

                    instance = Process;
                    break;
                }

            case UAModel.Machinery.BrowseNames.Status:
                {
                    if (createOrReplace)
                    {
                        if (Status == null)
                        {
                            if (replacement == null)
                            {
                                Status = new FolderState(this);
                            }
                            else
                            {
                                Status = (FolderState)replacement;
                            }
                        }
                    }

                    instance = Status;
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
    private FolderState m_consumption;
    private FolderState m_health;
    private FolderState m_process;
    private FolderState m_status;
    #endregion
}
#endif
#endregion

#region NotificationsTypeState Class
#if (!OPCUA_EXCLUDE_NotificationsTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class NotificationsTypeState : FolderState
{
    #region Constructors
    public NotificationsTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.NotificationsType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABABkAAABOb3RpZmljYXRpb25zVHlwZUluc3RhbmNlAQH5AwEB+QP5AwAA/////wEAAAA1" +
       "YKkKAgAAAAAAGQAAAERlZmF1bHRJbnN0YW5jZUJyb3dzZU5hbWUBAdoXAwAAAAAxAAAAVGhlIGRlZmF1" +
       "bHQgQnJvd3NlTmFtZSBmb3IgaW5zdGFuY2VzIG9mIHRoZSB0eXBlLgAuAETaFwAAFAEADQAAAE5vdGlm" +
       "aWNhdGlvbnMAFP////8DA/////8AAAAA";
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

#region MachineComponentsTypeState Class
#if (!OPCUA_EXCLUDE_MachineComponentsTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class MachineComponentsTypeState : BaseObjectState
{
    #region Constructors
    public MachineComponentsTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.MachineComponentsType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABAB0AAABNYWNoaW5lQ29tcG9uZW50c1R5cGVJbnN0YW5jZQEB7gMBAe4D7gMAAP////8C" +
       "AAAAJGDACgEAAAAVAAAAQ29tcG9uZW50X1BsYWNlaG9sZGVyAQALAAAAPENvbXBvbmVudD4BAYoTAwAA" +
       "AAA0AAAAUmVwcmVzZW50cyB0aGUgaWRlbnRpZmlhYmxlIGNvbXBvbmVudHMgb2YgYSBtYWNoaW5lLgAv" +
       "ADqKEwAA/////wEAAAAkYIAKAQAAAAMADgAAAElkZW50aWZpY2F0aW9uAQGLEwMAAAAATgAAAENvbnRh" +
       "aW5zIGluZm9ybWF0aW9uIGFib3V0IHRoZSBpZGVudGlmaWNhdGlvbiBhbmQgbmFtZXBsYXRlIG9mIGEg" +
       "TWFjaGluZXJ5SXRlbQEAxEQBAewDixMAAAIAAAABAMNEAAEB6wMBAMNEAAEDyDoCAAAANWCJCgIAAAAD" +
       "AAwAAABNYW51ZmFjdHVyZXIBAYMXAwAAAABKAAAAQSBodW1hbi1yZWFkYWJsZSwgbG9jYWxpemVkIG5h" +
       "bWUgb2YgdGhlIG1hbnVmYWN0dXJlciBvZiB0aGUgTWFjaGluZXJ5SXRlbS4ALgBEgxcAAAAV/////wEB" +
       "/////wAAAAA1YIkKAgAAAAMADAAAAFNlcmlhbE51bWJlcgEBhBcDAAAAABcBAABBIHN0cmluZyBjb250" +
       "YWluaW5nIGEgdW5pcXVlIHByb2R1Y3Rpb24gbnVtYmVyIG9mIHRoZSBtYW51ZmFjdHVyZXIgb2YgdGhl" +
       "IE1hY2hpbmVyeUl0ZW0uIFRoZSBnbG9iYWwgdW5pcXVlbmVzcyBvZiB0aGUgc2VyaWFsIG51bWJlciBp" +
       "cyBvbmx5IGdpdmVuIGluIHRoZSBjb250ZXh0IG9mIHRoZSBtYW51ZmFjdHVyZXIsIGFuZCBwb3RlbnRp" +
       "YWxseSB0aGUgbW9kZWwuIFRoZSB2YWx1ZSBzaGFsbCBub3QgY2hhbmdlIGR1cmluZyB0aGUgbGlmZS1j" +
       "eWNsZSBvZiB0aGUgTWFjaGluZXJ5SXRlbS4ALgBEhBcAAAAM/////wEB/////wAAAAA1YKkKAgAAAAAA" +
       "GQAAAERlZmF1bHRJbnN0YW5jZUJyb3dzZU5hbWUBAYIXAwAAAAAxAAAAVGhlIGRlZmF1bHQgQnJvd3Nl" +
       "TmFtZSBmb3IgaW5zdGFuY2VzIG9mIHRoZSB0eXBlLgAuAESCFwAAFAEACgAAAENvbXBvbmVudHMAFP//" +
       "//8DA/////8AAAAA";
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

#region MachineryItemState_StateMachineTypeState Class
#if (!OPCUA_EXCLUDE_MachineryItemState_StateMachineTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class MachineryItemState_StateMachineTypeState : FiniteStateMachineState
{
    #region Constructors
    public MachineryItemState_StateMachineTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.MachineryItemState_StateMachineType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABACsAAABNYWNoaW5lcnlJdGVtU3RhdGVfU3RhdGVNYWNoaW5lVHlwZUluc3RhbmNlAQHq" +
       "AwEB6gPqAwAA/////xYAAAAVYIkIAgAAAAAADAAAAEN1cnJlbnRTdGF0ZQEBAAAALwEAyAoAFf////8B" +
       "Af////8BAAAAFWCJCAIAAAAAAAIAAABJZAEBAAAALgBEABH/////AQH/////AAAAADVgqQoCAAAAAAAZ" +
       "AAAARGVmYXVsdEluc3RhbmNlQnJvd3NlTmFtZQEBhRcDAAAAADAAAABUaGUgZGVmYXVsdCBCcm93c2VO" +
       "YW1lIGZvciBpbnN0YW5jZXMgb2YgdGhlIHR5cGUALgBEhRcAABQBABIAAABNYWNoaW5lcnlJdGVtU3Rh" +
       "dGUAFP////8DA/////8AAAAAJGCACgEAAAABAAkAAABFeGVjdXRpbmcBAY4TAwAAAABgAAAAVGhlIG1h" +
       "Y2hpbmUgaXMgYXZhaWxhYmxlICYgZnVuY3Rpb25hbCBhbmQgaXMgYWN0aXZlbHkgcGVyZm9ybWluZyBh" +
       "biBhY3Rpdml0eSAocHVyc3VlcyBhIHB1cnBvc2UpAC8BAAMJjhMAAAgAAAAAMwEBAZ8TADQBAQGfEwAz" +
       "AQEBnBMAMwEBAZ4TADMBAQGdEwA0AQEBkhMANAEBAZoTADQBAQGWEwEAAAAVYKkKAgAAAAAACwAAAFN0" +
       "YXRlTnVtYmVyAQGYFwAuAESYFwAABwMAAAAAB/////8BAf////8AAAAAJGCACgEAAAABABgAAABGcm9t" +
       "RXhlY3V0aW5nVG9FeGVjdXRpbmcBAZ8TAwAAAAAyAAAAVHJhbnNpdGlvbiBmcm9tIHN0YXRlIEV4ZWN1" +
       "dGluZyB0byBzdGF0ZSBFeGVjdXRpbmcALwEABgmfEwAAAgAAAAAzAAEBjhMANAABAY4TAQAAABVgqQoC" +
       "AAAAAAAQAAAAVHJhbnNpdGlvbk51bWJlcgEBqRcALgBEqRcAAAcOAAAAAAf/////AQH/////AAAAACRg" +
       "gAoBAAAAAQAbAAAARnJvbUV4ZWN1dGluZ1RvTm90QXZhaWxhYmxlAQGcEwMAAAAANQAAAFRyYW5zaXRp" +
       "b24gZnJvbSBzdGF0ZSBFeGVjdXRpbmcgdG8gc3RhdGUgTm90QXZhaWxhYmxlAC8BAAYJnBMAAAIAAAAA" +
       "MwABAY4TADQAAQGNEwEAAAAVYKkKAgAAAAAAEAAAAFRyYW5zaXRpb25OdW1iZXIBAaYXAC4ARKYXAAAH" +
       "BgAAAAAH/////wEB/////wAAAAAkYIAKAQAAAAEAGwAAAEZyb21FeGVjdXRpbmdUb05vdEV4ZWN1dGlu" +
       "ZwEBnhMDAAAAADUAAABUcmFuc2l0aW9uIGZyb20gc3RhdGUgRXhlY3V0aW5nIHRvIHN0YXRlIE5vdEV4" +
       "ZWN1dGluZwAvAQAGCZ4TAAACAAAAADMAAQGOEwA0AAEBjxMBAAAAFWCpCgIAAAAAABAAAABUcmFuc2l0" +
       "aW9uTnVtYmVyAQGoFwAuAESoFwAABwgAAAAAB/////8BAf////8AAAAAJGCACgEAAAABABsAAABGcm9t" +
       "RXhlY3V0aW5nVG9PdXRPZlNlcnZpY2UBAZ0TAwAAAAA1AAAAVHJhbnNpdGlvbiBmcm9tIHN0YXRlIEV4" +
       "ZWN1dGluZyB0byBzdGF0ZSBPdXRPZlNlcnZpY2UALwEABgmdEwAAAgAAAAAzAAEBjhMANAABAYwTAQAA" +
       "ABVgqQoCAAAAAAAQAAAAVHJhbnNpdGlvbk51bWJlcgEBpxcALgBEpxcAAAcHAAAAAAf/////AQH/////" +
       "AAAAACRggAoBAAAAAQAbAAAARnJvbU5vdEF2YWlsYWJsZVRvRXhlY3V0aW5nAQGSEwMAAAAANQAAAFRy" +
       "YW5zaXRpb24gZnJvbSBzdGF0ZSBOb3RBdmFpbGFibGUgdG8gc3RhdGUgRXhlY3V0aW5nAC8BAAYJkhMA" +
       "AAIAAAAANAABAY4TADMAAQGNEwEAAAAVYKkKAgAAAAAAEAAAAFRyYW5zaXRpb25OdW1iZXIBAZwXAC4A" +
       "RJwXAAAHAQAAAAAH/////wEB/////wAAAAAkYIAKAQAAAAEAHgAAAEZyb21Ob3RBdmFpbGFibGVUb05v" +
       "dEF2YWlsYWJsZQEBkxMDAAAAADgAAABUcmFuc2l0aW9uIGZyb20gc3RhdGUgTm90QXZhaWxhYmxlIHRv" +
       "IHN0YXRlIE5vdEF2YWlsYWJsZQAvAQAGCZMTAAACAAAAADMAAQGNEwA0AAEBjRMBAAAAFWCpCgIAAAAA" +
       "ABAAAABUcmFuc2l0aW9uTnVtYmVyAQGdFwAuAESdFwAABwwAAAAAB/////8BAf////8AAAAAJGCACgEA" +
       "AAABAB4AAABGcm9tTm90QXZhaWxhYmxlVG9Ob3RFeGVjdXRpbmcBAZETAwAAAAA4AAAAVHJhbnNpdGlv" +
       "biBmcm9tIHN0YXRlIE5vdEF2YWlsYWJsZSB0byBzdGF0ZSBOb3RFeGVjdXRpbmcALwEABgmREwAAAgAA" +
       "AAAzAAEBjRMANAABAY8TAQAAABVgqQoCAAAAAAAQAAAAVHJhbnNpdGlvbk51bWJlcgEBmxcALgBEmxcA" +
       "AAcCAAAAAAf/////AQH/////AAAAACRggAoBAAAAAQAeAAAARnJvbU5vdEF2YWlsYWJsZVRvT3V0T2ZT" +
       "ZXJ2aWNlAQGQEwMAAAAAOAAAAFRyYW5zaXRpb24gZnJvbSBzdGF0ZSBOb3RBdmFpbGFibGUgdG8gc3Rh" +
       "dGUgT3V0T2ZTZXJ2aWNlAC8BAAYJkBMAAAIAAAAAMwABAY0TADQAAQGMEwEAAAAVYKkKAgAAAAAAEAAA" +
       "AFRyYW5zaXRpb25OdW1iZXIBAZoXAC4ARJoXAAAHAAAAAAAH/////wEB/////wAAAAAkYIAKAQAAAAEA" +
       "GwAAAEZyb21Ob3RFeGVjdXRpbmdUb0V4ZWN1dGluZwEBmhMDAAAAADUAAABUcmFuc2l0aW9uIGZyb20g" +
       "c3RhdGUgTm90RXhlY3V0aW5nIHRvIHN0YXRlIEV4ZWN1dGluZwAvAQAGCZoTAAACAAAAADQAAQGOEwAz" +
       "AAEBjxMBAAAAFWCpCgIAAAAAABAAAABUcmFuc2l0aW9uTnVtYmVyAQGkFwAuAESkFwAABwsAAAAAB///" +
       "//8BAf////8AAAAAJGCACgEAAAABAB4AAABGcm9tTm90RXhlY3V0aW5nVG9Ob3RBdmFpbGFibGUBAZgT" +
       "AwAAAAA4AAAAVHJhbnNpdGlvbiBmcm9tIHN0YXRlIE5vdEV4ZWN1dGluZyB0byBzdGF0ZSBOb3RBdmFp" +
       "bGFibGUALwEABgmYEwAAAgAAAAA0AAEBjRMAMwABAY8TAQAAABVgqQoCAAAAAAAQAAAAVHJhbnNpdGlv" +
       "bk51bWJlcgEBohcALgBEohcAAAcJAAAAAAf/////AQH/////AAAAACRggAoBAAAAAQAeAAAARnJvbU5v" +
       "dEV4ZWN1dGluZ1RvTm90RXhlY3V0aW5nAQGbEwMAAAAAOAAAAFRyYW5zaXRpb24gZnJvbSBzdGF0ZSBO" +
       "b3RFeGVjdXRpbmcgdG8gc3RhdGUgTm90RXhlY3V0aW5nAC8BAAYJmxMAAAIAAAAAMwABAY8TADQAAQGP" +
       "EwEAAAAVYKkKAgAAAAAAEAAAAFRyYW5zaXRpb25OdW1iZXIBAaUXAC4ARKUXAAAHDwAAAAAH/////wEB" +
       "/////wAAAAAkYIAKAQAAAAEAHgAAAEZyb21Ob3RFeGVjdXRpbmdUb091dE9mU2VydmljZQEBmRMDAAAA" +
       "ADgAAABUcmFuc2l0aW9uIGZyb20gc3RhdGUgTm90RXhlY3V0aW5nIHRvIHN0YXRlIE91dE9mU2Vydmlj" +
       "ZQAvAQAGCZkTAAACAAAAADMAAQGPEwA0AAEBjBMBAAAAFWCpCgIAAAAAABAAAABUcmFuc2l0aW9uTnVt" +
       "YmVyAQGjFwAuAESjFwAABwoAAAAAB/////8BAf////8AAAAAJGCACgEAAAABABsAAABGcm9tT3V0T2ZT" +
       "ZXJ2aWNlVG9FeGVjdXRpbmcBAZYTAwAAAAA1AAAAVHJhbnNpdGlvbiBmcm9tIHN0YXRlIE91dE9mU2Vy" +
       "dmljZSB0byBzdGF0ZSBFeGVjdXRpbmcALwEABgmWEwAAAgAAAAA0AAEBjhMAMwABAYwTAQAAABVgqQoC" +
       "AAAAAAAQAAAAVHJhbnNpdGlvbk51bWJlcgEBoBcALgBEoBcAAAcEAAAAAAf/////AQH/////AAAAACRg" +
       "gAoBAAAAAQAeAAAARnJvbU91dE9mU2VydmljZVRvTm90QXZhaWxhYmxlAQGUEwMAAAAAOAAAAFRyYW5z" +
       "aXRpb24gZnJvbSBzdGF0ZSBPdXRPZlNlcnZpY2UgdG8gc3RhdGUgTm90QXZhaWxhYmxlAC8BAAYJlBMA" +
       "AAIAAAAANAABAY0TADMAAQGMEwEAAAAVYKkKAgAAAAAAEAAAAFRyYW5zaXRpb25OdW1iZXIBAZ4XAC4A" +
       "RJ4XAAAHAwAAAAAH/////wEB/////wAAAAAkYIAKAQAAAAEAHgAAAEZyb21PdXRPZlNlcnZpY2VUb05v" +
       "dEV4ZWN1dGluZwEBlRMDAAAAADgAAABUcmFuc2l0aW9uIGZyb20gc3RhdGUgT3V0T2ZTZXJ2aWNlIHRv" +
       "IHN0YXRlIE5vdEV4ZWN1dGluZwAvAQAGCZUTAAACAAAAADQAAQGPEwAzAAEBjBMBAAAAFWCpCgIAAAAA" +
       "ABAAAABUcmFuc2l0aW9uTnVtYmVyAQGfFwAuAESfFwAABwUAAAAAB/////8BAf////8AAAAAJGCACgEA" +
       "AAABAB4AAABGcm9tT3V0T2ZTZXJ2aWNlVG9PdXRPZlNlcnZpY2UBAZcTAwAAAAA4AAAAVHJhbnNpdGlv" +
       "biBmcm9tIHN0YXRlIE91dE9mU2VydmljZSB0byBzdGF0ZSBPdXRPZlNlcnZpY2UALwEABgmXEwAAAgAA" +
       "AAAzAAEBjBMANAABAYwTAQAAABVgqQoCAAAAAAAQAAAAVHJhbnNpdGlvbk51bWJlcgEBoRcALgBEoRcA" +
       "AAcNAAAAAAf/////AQH/////AAAAACRggAoBAAAAAQAMAAAATm90QXZhaWxhYmxlAQGNEwMAAAAAagAA" +
       "AFRoZSBtYWNoaW5lIGlzIG5vdCBhdmFpbGFibGUgYW5kIGRvZXMgbm90IHBlcmZvcm0gYW55IGFjdGl2" +
       "aXR5IChlLmcuLCBzd2l0Y2hlZCBvZmYsIGluIGVuZXJneSBzYXZpbmcgbW9kZSkALwEAAwmNEwAACAAA" +
       "AAA0AQEBnBMAMwEBAZITADMBAQGTEwA0AQEBkxMAMwEBAZETADMBAQGQEwA0AQEBmBMANAEBAZQTAQAA" +
       "ABVgqQoCAAAAAAALAAAAU3RhdGVOdW1iZXIBAZcXAC4ARJcXAAAHAAAAAAAH/////wEB/////wAAAAAk" +
       "YIAKAQAAAAEADAAAAE5vdEV4ZWN1dGluZwEBjxMDAAAAAIwAAABUaGUgbWFjaGluZSBpcyBhdmFpbGFi" +
       "bGUgJiBmdW5jdGlvbmFsIGFuZCBkb2VzIG5vdCBwZXJmb3JtIGFueSBhY3Rpdml0eS4gSXQgd2FpdHMg" +
       "Zm9yIGFuIGFjdGlvbiBmcm9tIG91dHNpZGUgdG8gc3RhcnQgb3IgcmVzdGFydCBhbiBhY3Rpdml0eQAv" +
       "AQADCY8TAAAIAAAAADQBAQGeEwA0AQEBkRMAMwEBAZoTADMBAQGYEwAzAQEBmxMANAEBAZsTADMBAQGZ" +
       "EwA0AQEBlRMBAAAAFWCpCgIAAAAAAAsAAABTdGF0ZU51bWJlcgEBmRcALgBEmRcAAAcCAAAAAAf/////" +
       "AQH/////AAAAACRggAoBAAAAAQAMAAAAT3V0T2ZTZXJ2aWNlAQGMEwMAAAAAVgAAAFRoZSBtYWNoaW5l" +
       "IGlzIG5vdCBmdW5jdGlvbmFsIGFuZCBkb2VzIG5vdCBwZXJmb3JtIGFueSBhY3Rpdml0eSAoZS5nLiwg" +
       "ZXJyb3IsIGJsb2NrZWQpAC8BAAMJjBMAAAgAAAAANAEBAZ0TADQBAQGQEwA0AQEBmRMAMwEBAZYTADMB" +
       "AQGUEwAzAQEBlRMAMwEBAZcTADQBAQGXEwEAAAAVYKkKAgAAAAAACwAAAFN0YXRlTnVtYmVyAQGWFwAu" +
       "AESWFwAABwEAAAAAB/////8BAf////8AAAAA";
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

#region MachineryOperationModeStateMachineTypeState Class
#if (!OPCUA_EXCLUDE_MachineryOperationModeStateMachineTypeState)
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public partial class MachineryOperationModeStateMachineTypeState : FiniteStateMachineState
{
    #region Constructors
    public MachineryOperationModeStateMachineTypeState(NodeState parent) : base(parent)
    {
    }

    protected override NodeId GetDefaultTypeDefinitionId(NamespaceTable namespaceUris)
    {
        return Opc.Ua.NodeId.Create(UAModel.Machinery.ObjectTypes.MachineryOperationModeStateMachineType, UAModel.Machinery.Namespaces.Machinery, namespaceUris);
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
       "AwAAACYAAABodHRwOi8vb3BjZm91bmRhdGlvbi5vcmcvVUEvTWFjaGluZXJ5Lx8AAABodHRwOi8vb3Bj" +
       "Zm91bmRhdGlvbi5vcmcvVUEvSUEvHwAAAGh0dHA6Ly9vcGNmb3VuZGF0aW9uLm9yZy9VQS9ESS//////" +
       "BGCAAgEAAAABAC4AAABNYWNoaW5lcnlPcGVyYXRpb25Nb2RlU3RhdGVNYWNoaW5lVHlwZUluc3RhbmNl" +
       "AQHwAwEB8APwAwAA/////xYAAAAVYIkIAgAAAAAADAAAAEN1cnJlbnRTdGF0ZQEBAAAALwEAyAoAFf//" +
       "//8BAf////8BAAAAFWCJCAIAAAAAAAIAAABJZAEBAAAALgBEABH/////AQH/////AAAAADVgqQoCAAAA" +
       "AAAZAAAARGVmYXVsdEluc3RhbmNlQnJvd3NlTmFtZQEBqhcDAAAAADAAAABUaGUgZGVmYXVsdCBCcm93" +
       "c2VOYW1lIGZvciBpbnN0YW5jZXMgb2YgdGhlIHR5cGUALgBEqhcAABQBABYAAABNYWNoaW5lcnlPcGVy" +
       "YXRpb25Nb2RlABT/////AwP/////AAAAACRggAoBAAAAAQAcAAAARnJvbU1haW50ZW5hbmNlVG9NYWlu" +
       "dGVuYW5jZQEBqxMDAAAAADYAAABUcmFuc2l0aW9uIGZyb20gc3RhdGUgTWFpbnRlbmFuY2UgdG8gc3Rh" +
       "dGUgTWFpbnRlbmFuY2UALwEABgmrEwAAAgAAAAAzAAEBoRMANAABAaETAQAAABVgqQoCAAAAAAAQAAAA" +
       "VHJhbnNpdGlvbk51bWJlcgEBthcALgBEthcAAAcNAAAAAAf/////AQH/////AAAAACRggAoBAAAAAQAV" +
       "AAAARnJvbU1haW50ZW5hbmNlVG9Ob25lAQGoEwMAAAAALwAAAFRyYW5zaXRpb24gZnJvbSBzdGF0ZSBN" +
       "YWludGVuYW5jZSB0byBzdGF0ZSBOb25lAC8BAAYJqBMAAAIAAAAAMwABAaETADQAAQGgEwEAAAAVYKkK" +
       "AgAAAAAAEAAAAFRyYW5zaXRpb25OdW1iZXIBAbMXAC4ARLMXAAAHAwAAAAAH/////wEB/////wAAAAAk" +
       "YIAKAQAAAAEAGwAAAEZyb21NYWludGVuYW5jZVRvUHJvY2Vzc2luZwEBqhMDAAAAADUAAABUcmFuc2l0" +
       "aW9uIGZyb20gc3RhdGUgTWFpbnRlbmFuY2UgdG8gc3RhdGUgUHJvY2Vzc2luZwAvAQAGCaoTAAACAAAA" +
       "ADMAAQGhEwA0AAEBohMBAAAAFWCpCgIAAAAAABAAAABUcmFuc2l0aW9uTnVtYmVyAQG1FwAuAES1FwAA" +
       "BwQAAAAAB/////8BAf////8AAAAAJGCACgEAAAABABYAAABGcm9tTWFpbnRlbmFuY2VUb1NldHVwAQGp" +
       "EwMAAAAAMAAAAFRyYW5zaXRpb24gZnJvbSBzdGF0ZSBNYWludGVuYW5jZSB0byBzdGF0ZSBTZXR1cAAv" +
       "AQAGCakTAAACAAAAADMAAQGhEwA0AAEBoxMBAAAAFWCpCgIAAAAAABAAAABUcmFuc2l0aW9uTnVtYmVy" +
       "AQG0FwAuAES0FwAABwUAAAAAB/////8BAf////8AAAAAJGCACgEAAAABABUAAABGcm9tTm9uZVRvTWFp" +
       "bnRlbmFuY2UBAaQTAwAAAAAvAAAAVHJhbnNpdGlvbiBmcm9tIHN0YXRlIE5vbmUgdG8gc3RhdGUgTWFp" +
       "bnRlbmFuY2UALwEABgmkEwAAAgAAAAA0AAEBoRMAMwABAaATAQAAABVgqQoCAAAAAAAQAAAAVHJhbnNp" +
       "dGlvbk51bWJlcgEBrxcALgBErxcAAAcAAAAAAAf/////AQH/////AAAAACRggAoBAAAAAQAOAAAARnJv" +
       "bU5vbmVUb05vbmUBAacTAwAAAAAoAAAAVHJhbnNpdGlvbiBmcm9tIHN0YXRlIE5vbmUgdG8gc3RhdGUg" +
       "Tm9uZQAvAQAGCacTAAACAAAAADMAAQGgEwA0AAEBoBMBAAAAFWCpCgIAAAAAABAAAABUcmFuc2l0aW9u" +
       "TnVtYmVyAQGyFwAuAESyFwAABwwAAAAAB/////8BAf////8AAAAAJGCACgEAAAABABQAAABGcm9tTm9u" +
       "ZVRvUHJvY2Vzc2luZwEBphMDAAAAAC4AAABUcmFuc2l0aW9uIGZyb20gc3RhdGUgTm9uZSB0byBzdGF0" +
       "ZSBQcm9jZXNzaW5nAC8BAAYJphMAAAIAAAAAMwABAaATADQAAQGiEwEAAAAVYKkKAgAAAAAAEAAAAFRy" +
       "YW5zaXRpb25OdW1iZXIBAbEXAC4ARLEXAAAHAQAAAAAH/////wEB/////wAAAAAkYIAKAQAAAAEADwAA" +
       "AEZyb21Ob25lVG9TZXR1cAEBpRMDAAAAACkAAABUcmFuc2l0aW9uIGZyb20gc3RhdGUgTm9uZSB0byBz" +
       "dGF0ZSBTZXR1cAAvAQAGCaUTAAACAAAAADMAAQGgEwA0AAEBoxMBAAAAFWCpCgIAAAAAABAAAABUcmFu" +
       "c2l0aW9uTnVtYmVyAQGwFwAuAESwFwAABwIAAAAAB/////8BAf////8AAAAAJGCACgEAAAABABsAAABG" +
       "cm9tUHJvY2Vzc2luZ1RvTWFpbnRlbmFuY2UBAbETAwAAAAA1AAAAVHJhbnNpdGlvbiBmcm9tIHN0YXRl" +
       "IFByb2Nlc3NpbmcgdG8gc3RhdGUgTWFpbnRlbmFuY2UALwEABgmxEwAAAgAAAAA0AAEBoRMAMwABAaIT" +
       "AQAAABVgqQoCAAAAAAAQAAAAVHJhbnNpdGlvbk51bWJlcgEBvBcALgBEvBcAAAcHAAAAAAf/////AQH/" +
       "////AAAAACRggAoBAAAAAQAUAAAARnJvbVByb2Nlc3NpbmdUb05vbmUBAbATAwAAAAAuAAAAVHJhbnNp" +
       "dGlvbiBmcm9tIHN0YXRlIFByb2Nlc3NpbmcgdG8gc3RhdGUgTm9uZQAvAQAGCbATAAACAAAAADQAAQGg" +
       "EwAzAAEBohMBAAAAFWCpCgIAAAAAABAAAABUcmFuc2l0aW9uTnVtYmVyAQG7FwAuAES7FwAABwYAAAAA" +
       "B/////8BAf////8AAAAAJGCACgEAAAABABoAAABGcm9tUHJvY2Vzc2luZ1RvUHJvY2Vzc2luZwEBsxMD" +
       "AAAAADQAAABUcmFuc2l0aW9uIGZyb20gc3RhdGUgUHJvY2Vzc2luZyB0byBzdGF0ZSBQcm9jZXNzaW5n" +
       "AC8BAAYJsxMAAAIAAAAAMwABAaITADQAAQGiEwEAAAAVYKkKAgAAAAAAEAAAAFRyYW5zaXRpb25OdW1i" +
       "ZXIBAb4XAC4ARL4XAAAHDgAAAAAH/////wEB/////wAAAAAkYIAKAQAAAAEAFQAAAEZyb21Qcm9jZXNz" +
       "aW5nVG9TZXR1cAEBshMDAAAAAC8AAABUcmFuc2l0aW9uIGZyb20gc3RhdGUgUHJvY2Vzc2luZyB0byBz" +
       "dGF0ZSBTZXR1cAAvAQAGCbITAAACAAAAADMAAQGiEwA0AAEBoxMBAAAAFWCpCgIAAAAAABAAAABUcmFu" +
       "c2l0aW9uTnVtYmVyAQG9FwAuAES9FwAABwgAAAAAB/////8BAf////8AAAAAJGCACgEAAAABABYAAABG" +
       "cm9tU2V0dXBUb01haW50ZW5hbmNlAQGtEwMAAAAAMAAAAFRyYW5zaXRpb24gZnJvbSBzdGF0ZSBTZXR1" +
       "cCB0byBzdGF0ZSBNYWludGVuYW5jZQAvAQAGCa0TAAACAAAAADQAAQGhEwAzAAEBoxMBAAAAFWCpCgIA" +
       "AAAAABAAAABUcmFuc2l0aW9uTnVtYmVyAQG4FwAuAES4FwAABwoAAAAAB/////8BAf////8AAAAAJGCA" +
       "CgEAAAABAA8AAABGcm9tU2V0dXBUb05vbmUBAawTAwAAAAApAAAAVHJhbnNpdGlvbiBmcm9tIHN0YXRl" +
       "IFNldHVwIHRvIHN0YXRlIE5vbmUALwEABgmsEwAAAgAAAAA0AAEBoBMAMwABAaMTAQAAABVgqQoCAAAA" +
       "AAAQAAAAVHJhbnNpdGlvbk51bWJlcgEBtxcALgBEtxcAAAcJAAAAAAf/////AQH/////AAAAACRggAoB" +
       "AAAAAQAVAAAARnJvbVNldHVwVG9Qcm9jZXNzaW5nAQGuEwMAAAAALwAAAFRyYW5zaXRpb24gZnJvbSBz" +
       "dGF0ZSBTZXR1cCB0byBzdGF0ZSBQcm9jZXNzaW5nAC8BAAYJrhMAAAIAAAAANAABAaITADMAAQGjEwEA" +
       "AAAVYKkKAgAAAAAAEAAAAFRyYW5zaXRpb25OdW1iZXIBAbkXAC4ARLkXAAAHCwAAAAAH/////wEB////" +
       "/wAAAAAkYIAKAQAAAAEAEAAAAEZyb21TZXR1cFRvU2V0dXABAa8TAwAAAAAqAAAAVHJhbnNpdGlvbiBm" +
       "cm9tIHN0YXRlIFNldHVwIHRvIHN0YXRlIFNldHVwAC8BAAYJrxMAAAIAAAAAMwABAaMTADQAAQGjEwEA" +
       "AAAVYKkKAgAAAAAAEAAAAFRyYW5zaXRpb25OdW1iZXIBAboXAC4ARLoXAAAHDwAAAAAH/////wEB////" +
       "/wAAAAAkYIAKAQAAAAEACwAAAE1haW50ZW5hbmNlAQGhEwMAAAAAbgAAAE1hY2hpbmVyeUl0ZW0gaXMg" +
       "c2V0IGludG8gbWFpbnRlbmFuY2UgbW9kZSB3aXRoIHRoZSBpbnRlbnRpb24gdG8gY2Fycnkgb3V0IG1h" +
       "aW50ZW5hbmNlIG9yIHNlcnZpY2luZyBhY3Rpdml0aWVzAC8BAAMJoRMAAAgAAAAAMwEBAasTADQBAQGr" +
       "EwAzAQEBqBMAMwEBAaoTADMBAQGpEwA0AQEBpBMANAEBAbETADQBAQGtEwEAAAAVYKkKAgAAAAAACwAA" +
       "AFN0YXRlTnVtYmVyAQGsFwAuAESsFwAABwEAAAAAB/////8BAf////8AAAAAJGCACgEAAAABAAQAAABO" +
       "b25lAQGgEwMAAAAALgAAAFRoZXJlIGlzIGN1cnJlbnRseSBubyBvcGVyYXRpb24gbW9kZSBhdmFpbGFi" +
       "bGUALwEAAwmgEwAACAAAAAA0AQEBqBMAMwEBAaQTADMBAQGnEwA0AQEBpxMAMwEBAaYTADMBAQGlEwA0" +
       "AQEBsBMANAEBAawTAQAAABVgqQoCAAAAAAALAAAAU3RhdGVOdW1iZXIBAasXAC4ARKsXAAAHAAAAAAAH" +
       "/////wEB/////wAAAAAkYIAKAQAAAAEACgAAAFByb2Nlc3NpbmcBAaITAwAAAABlAAAATWFjaGluZXJ5" +
       "SXRlbSBpcyBzZXQgaW50byBwcm9jZXNzaW5nIG1vZGUgd2l0aCB0aGUgaW50ZW50aW9uIHRvIGNhcnJ5" +
       "IG91dCB0aGUgdmFsdWUgYWRkaW5nIGFjdGl2aXRpZXMALwEAAwmiEwAACAAAAAA0AQEBqhMANAEBAaYT" +
       "ADMBAQGxEwAzAQEBsBMAMwEBAbMTADQBAQGzEwAzAQEBshMANAEBAa4TAQAAABVgqQoCAAAAAAALAAAA" +
       "U3RhdGVOdW1iZXIBAa0XAC4ARK0XAAAHAwAAAAAH/////wEB/////wAAAAAkYIAKAQAAAAEABQAAAFNl" +
       "dHVwAQGjEwMAAAAAjAAAAE1hY2hpbmVyeUl0ZW0gaXMgc2V0IGludG8gc2V0dXAgbW9kZSB3aXRoIHRo" +
       "ZSBpbnRlbnRpb24gdG8gY2Fycnkgb3V0IHNldHVwLCBwcmVwYXJhdGlvbiBvciBwb3N0cHJvY2Vzc2lu" +
       "ZyBhY3Rpdml0aWVzIG9mIGEgcHJvZHVjdGlvbiBwcm9jZXNzAC8BAAMJoxMAAAgAAAAANAEBAakTADQB" +
       "AQGlEwA0AQEBshMAMwEBAa0TADMBAQGsEwAzAQEBrhMAMwEBAa8TADQBAQGvEwEAAAAVYKkKAgAAAAAA" +
       "CwAAAFN0YXRlTnVtYmVyAQGuFwAuAESuFwAABwIAAAAAB/////8BAf////8AAAAA";
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
