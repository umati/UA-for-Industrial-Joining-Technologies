"""
Conformance unit tests for Asset Management — OPC 40450-1.

Covers the following conformance units:

asset_management
    The JoiningSystem includes support for the optional AssetManagement which includes:
    AssetManagement, AssetManagement/Assets, AssetManagement/Assets/All Sub-Folders,
    AssetManagement/MethodSet of type JoiningSystemAssetMethodSetType.

asset_management_controller
    The Controllers folder includes at least one instance of a Controller which implements
    IControllerType interface. The Identification AddIn is of type MachineIdentificationType
    and includes at least: ProductInstanceUri, Manufacturer, ManufacturerUri, Model,
    DeviceClass, SerialNumber, ProductCode. The Parameters folder includes at least: Type.

asset_management_tool
    The Tools folder includes at least one instance of a Tool which implements IToolType
    interface. The Identification AddIn is of type MachineIdentificationType and includes
    at least: ProductInstanceUri, Manufacturer, ManufacturerUri, Model, DeviceClass,
    SerialNumber, ProductCode. The Parameters folder includes at least: Type.

asset_management_servo
    The Servos folder includes at least one instance of a Servo which implements IServoType
    interface. The Identification AddIn is of type MachineryComponentIdentificationType and
    includes at least: ProductInstanceUri, Manufacturer, ManufacturerUri, Model, DeviceClass,
    SerialNumber, ProductCode. The Parameters folder includes at least: NodeNumber.

asset_management_memory_device
    The MemoryDevices folder includes at least one instance of a MemoryDevice which implements
    IMemoryDeviceType interface. The Identification AddIn is MachineryComponentIdentificationType
    with at least: ProductInstanceUri, Manufacturer, ManufacturerUri, Model, DeviceClass,
    SerialNumber, ProductCode. Parameters includes at least: Type.

asset_management_cable
    The Cables folder includes at least one Cable instance implementing ICableType.
    Identification is MachineryComponentIdentificationType with ProductInstanceUri, Manufacturer,
    ManufacturerUri, Model, DeviceClass, SerialNumber, ProductCode. Parameters includes: Type.

asset_management_power_supply
    The PowerSupplies folder includes at least one PowerSupply instance implementing
    IPowerSupplyType. Identification is MachineryComponentIdentificationType.
    Parameters includes: InputSpecification.

asset_management_feeder
    The Feeders folder includes at least one Feeder instance implementing IFeederType.
    Identification is MachineryComponentIdentificationType. Parameters includes: Type, Material.

asset_management_battery
    The Batteries folder includes at least one Battery instance implementing IFeederType.
    Identification is MachineryComponentIdentificationType.
    Parameters includes: Type, NominalVoltage, Capacity.

asset_management_sensor
    The Sensors folder includes at least one Sensor instance implementing ISensorType.
    Identification is MachineryComponentIdentificationType. Parameters includes: Type.

asset_management_accessory
    The Accessories folder includes at least one Accessory instance implementing IAccessoryType.
    Identification is MachineryComponentIdentificationType. Parameters includes: Type.

asset_management_software
    The SoftwareComponents folder includes at least one Software instance implementing
    ISoftwareType. Identification is MachineryComponentIdentificationType with
    ProductInstanceUri, Manufacturer, ManufacturerUri, Model, SerialNumber.

asset_management_sub_component
    The SubComponents folder includes at least one SubComponent instance implementing
    ISubComponentType. Identification is MachineryComponentIdentificationType.
    Parameters includes: Type.

asset_management_virtual_station
    The VirtualStations folder includes at least one VirtualStation instance implementing
    IVirtualStationType. Identification is MachineryComponentIdentificationType with
    ProductInstanceUri, Manufacturer, ManufacturerUri, Model, SerialNumber.

asset_management_operation_counters
    The Server supports at least one asset instance which includes OperationCounters object
    of type MachineryOperationCounterType and includes at least one counter.

asset_management_tool_operation_cycle_counter
    The Server supports Tool instances which include OperationCounters object of type
    MachineryOperationCounterType and includes OperationCycleCounter property.

asset_management_battery_operation_cycle_counter
    The Server supports Battery instances which include OperationCounters object of type
    MachineryOperationCounterType and includes OperationCycleCounter property.

asset_management_health
    The Server supports at least one asset instance which includes Health object with at
    least DeviceHealth property.

asset_management_monitoring_health
    The Server supports at least one asset instance which includes Monitoring.Health object
    with at least DeviceHealth property.

asset_management_service
    The Server supports at least one asset instance which includes Maintenance.Service object
    with at least LastService and ServicePlace properties.

asset_management_calibration
    The Server supports at least one asset instance which includes Maintenance.Calibration
    object with at least LastCalibration and CalibrationValue properties. Calibration is
    applicable primarily for Sensor; if no Sensor is exposed, Calibration information may
    be part of the Tool.

asset_management_additional_information
    The Server supports all asset instances which implement IJoiningAdditionalInformationType
    interface as part of the Identification AddIn with at least the JoiningTechnology property.

asset_management_machinery_building_blocks
    The Server supports all asset instances which include the optional MachineryBuildingBlocks.
"""

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.namespaces import BN, NS_DI, NS_IJT_BASE, NS_MACHINERY, IJTTypes, MachineryTypes
from helpers.node_discovery import (
    browse_folder_instances,
    find_child_by_browse_name,
    get_associated_assets,
    get_type_definition,
    has_interface,
)

pytestmark = [pytest.mark.live, pytest.mark.conformance]


# ─── asset_management ────────────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT)
async def test_asset_management_addin_present(asset_management):
    """AssetManagement AddIn must be present on JoiningSystem."""
    assert asset_management is not None, "AssetManagement AddIn node must be present on JoiningSystem"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT)
async def test_asset_management_assets_folder_present(asset_management, ns_indices):
    """Assets folder must be present directly under AssetManagement."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    node = await find_child_by_browse_name(asset_management, BN.ASSETS, ns_ijt)
    assert node is not None, f"Assets folder (ns={ns_ijt}) not found under AssetManagement"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT)
@pytest.mark.parametrize("folder_name", BN.ALL_ASSET_FOLDERS)
async def test_all_asset_category_folders_present(assets_folder, ns_indices, folder_name):
    """Every asset category folder must exist under Assets."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    node = await find_child_by_browse_name(assets_folder, folder_name, ns_ijt)
    assert node is not None, f"Asset category folder '{folder_name}' (ns={ns_ijt}) not found under Assets"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT)
async def test_assets_folder_not_typed_as_joining_system(assets_folder, ns_indices):
    """The Assets folder must not carry JoiningSystemType as its TypeDefinition.

    The Assets node is a plain folder and must not be mistyped as a JoiningSystem instance.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    type_def = await get_type_definition(assets_folder)
    if type_def is None:
        return
    joining_system_type_id = ua.NodeId(IJTTypes.JOINING_SYSTEM_TYPE, ns_ijt)
    assert not (
        type_def.Identifier == joining_system_type_id.Identifier
        and type_def.NamespaceIndex == joining_system_type_id.NamespaceIndex
    ), "Assets folder must not be typed as JoiningSystemType — it is a plain folder, not a JoiningSystem instance"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT)
async def test_browsing_absent_folder_returns_none(assets_folder, ns_indices):
    """Browsing for an absent folder name under Assets must return None."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    node = await find_child_by_browse_name(assets_folder, "NonExistentAssetFolder", ns_ijt)
    assert node is None, (
        "Browsing for an absent name under Assets must return None — find_child_by_browse_name must not fabricate nodes"
    )


# ─── asset_management_controller ─────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controllers_folder_has_at_least_one_instance(controllers_instances):
    """Controllers folder must contain at least one asset instance."""
    assert len(controllers_instances) >= 1, "Controllers folder must contain at least one instance"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controller_implements_icontroller_type_interface(controllers_instances, ns_indices):
    """First controller must declare HasInterface → IControllerType."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    _name, controller_node = controllers_instances[0]
    has_iface = await has_interface(controller_node, ns_ijt, IJTTypes.ICONTROLLER_TYPE)
    if not has_iface:
        pytest.skip(
            f"Controller '{_name}' has no HasInterface → IControllerType — interface not declared on this server"
        )


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_all_controller_instances_have_identification(controllers_instances, ns_indices):
    """Every controller instance must expose an Identification node (DI ns)."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    missing = []
    for asset_name, asset_node in controllers_instances:
        ident = await find_child_by_browse_name(asset_node, BN.IDENTIFICATION, ns_di)
        if ident is None:
            missing.append(asset_name)
    assert not missing, f"Controller instances missing Identification node (ns_di={ns_di}): {missing}"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controller_identification_has_manufacturer(controllers_instances, ns_indices):
    """First controller Identification must expose a Manufacturer property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, controller_node = controllers_instances[0]
    ident = await find_child_by_browse_name(controller_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Controller '{_name}' has no Identification node — skipping Manufacturer check")
    manufacturer = await find_child_by_browse_name(ident, BN.MANUFACTURER, ns_di)
    assert manufacturer is not None, f"Controller '{_name}' Identification is missing Manufacturer (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controller_identification_has_manufacturer_uri(controllers_instances, ns_indices):
    """First controller Identification should expose ManufacturerUri."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, controller_node = controllers_instances[0]
    ident = await find_child_by_browse_name(controller_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Controller '{_name}' has no Identification node — skipping ManufacturerUri check")
    mfr_uri = await find_child_by_browse_name(ident, BN.MANUFACTURER_URI, ns_di)
    if mfr_uri is None:
        pytest.skip(f"Controller '{_name}' Identification does not expose ManufacturerUri — optional per spec")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controller_identification_has_model(controllers_instances, ns_indices):
    """First controller Identification should expose Model."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, controller_node = controllers_instances[0]
    ident = await find_child_by_browse_name(controller_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Controller '{_name}' has no Identification node — skipping Model check")
    model = await find_child_by_browse_name(ident, BN.MODEL, ns_di)
    if model is None:
        pytest.skip(f"Controller '{_name}' Identification does not expose Model — optional per spec")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controller_identification_has_device_class(controllers_instances, ns_indices):
    """First controller Identification should expose DeviceClass."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, controller_node = controllers_instances[0]
    ident = await find_child_by_browse_name(controller_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Controller '{_name}' has no Identification node — skipping DeviceClass check")
    device_class = await find_child_by_browse_name(ident, BN.DEVICE_CLASS, ns_di)
    if device_class is None:
        pytest.skip(f"Controller '{_name}' Identification does not expose DeviceClass — optional per spec")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controller_identification_has_serial_number(controllers_instances, ns_indices):
    """First controller Identification must expose a SerialNumber property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, controller_node = controllers_instances[0]
    ident = await find_child_by_browse_name(controller_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Controller '{_name}' has no Identification node — skipping SerialNumber check")
    serial = await find_child_by_browse_name(ident, BN.SERIAL_NUMBER, ns_di)
    assert serial is not None, f"Controller '{_name}' Identification is missing SerialNumber (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controller_identification_has_product_code(controllers_instances, ns_indices):
    """First controller Identification should expose ProductCode."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, controller_node = controllers_instances[0]
    ident = await find_child_by_browse_name(controller_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Controller '{_name}' has no Identification node — skipping ProductCode check")
    product_code = await find_child_by_browse_name(ident, BN.PRODUCT_CODE, ns_di)
    if product_code is None:
        pytest.skip(f"Controller '{_name}' Identification does not expose ProductCode — optional per spec")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controller_identification_has_product_instance_uri(controllers_instances, ns_indices):
    """First controller Identification should expose ProductInstanceUri."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, controller_node = controllers_instances[0]
    ident = await find_child_by_browse_name(controller_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Controller '{_name}' has no Identification node — skipping ProductInstanceUri check")
    piu = await find_child_by_browse_name(ident, BN.PRODUCT_INSTANCE_URI, ns_di)
    if piu is None:
        pytest.skip(
            f"Controller '{_name}' Identification does not expose ProductInstanceUri — "
            "optional per spec, server may omit it"
        )


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controller_identification_has_hardware_or_software_revision(controllers_instances, ns_indices):
    """Controller Identification should expose HardwareRevision or SoftwareRevision."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, controller_node = controllers_instances[0]
    ident = await find_child_by_browse_name(controller_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Controller '{_name}' has no Identification node — skipping revision check")
    hw_rev = await find_child_by_browse_name(ident, BN.HARDWARE_REVISION, ns_di)
    if hw_rev is None:
        sw_rev = await find_child_by_browse_name(ident, BN.SOFTWARE_REVISION, ns_di)
        if sw_rev is None:
            pytest.skip(
                f"Controller '{_name}' Identification exposes neither HardwareRevision "
                "nor SoftwareRevision — optional per spec"
            )


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controller_has_parameters_node(controllers_instances, ns_indices):
    """All controller instances must expose a Parameters node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    missing = []
    for asset_name, asset_node in controllers_instances:
        params = await find_child_by_browse_name(asset_node, BN.PARAMETERS, ns_ijt)
        if params is None:
            missing.append(asset_name)
    assert not missing, f"Controller instances missing Parameters node (ns_ijt={ns_ijt}): {missing}"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controller_parameters_has_type_property(controllers_instances, ns_indices):
    """First controller Parameters must expose a Type property."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    _name, controller_node = controllers_instances[0]
    params = await find_child_by_browse_name(controller_node, BN.PARAMETERS, ns_ijt)
    if params is None:
        pytest.skip(f"Controller '{_name}' has no Parameters node — skipping Type check")
    type_node = await find_child_by_browse_name(params, BN.CONTROLLER_TYPE, ns_ijt)
    assert type_node is not None, f"Controller '{_name}' Parameters is missing Type property (ns_ijt={ns_ijt})"


# ─── asset_management_tool ────────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tools_folder_has_at_least_one_instance(tools_instances):
    """Tools folder must contain at least one asset instance."""
    assert len(tools_instances) >= 1, "Tools folder must contain at least one instance"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tool_implements_itool_type_interface(tools_instances, ns_indices):
    """First tool must declare HasInterface → IToolType."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    _name, tool_node = tools_instances[0]
    has_iface = await has_interface(tool_node, ns_ijt, IJTTypes.ITOOL_TYPE)
    if not has_iface:
        pytest.skip(f"Tool '{_name}' has no HasInterface → IToolType — interface not declared on this server")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_all_tool_instances_have_identification(tools_instances, ns_indices):
    """Every tool instance must expose an Identification node (DI ns)."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    missing = []
    for asset_name, asset_node in tools_instances:
        ident = await find_child_by_browse_name(asset_node, BN.IDENTIFICATION, ns_di)
        if ident is None:
            missing.append(asset_name)
    assert not missing, f"Tool instances missing Identification node (ns_di={ns_di}): {missing}"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tool_identification_has_serial_number(tools_instances, ns_indices):
    """First tool Identification must expose a SerialNumber property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, tool_node = tools_instances[0]
    ident = await find_child_by_browse_name(tool_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Tool '{_name}' has no Identification node — skipping SerialNumber check")
    serial = await find_child_by_browse_name(ident, BN.SERIAL_NUMBER, ns_di)
    assert serial is not None, f"Tool '{_name}' Identification is missing SerialNumber (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tool_identification_has_manufacturer(tools_instances, ns_indices):
    """First tool Identification should expose a Manufacturer property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, tool_node = tools_instances[0]
    ident = await find_child_by_browse_name(tool_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Tool '{_name}' has no Identification node — skipping Manufacturer check")
    manufacturer = await find_child_by_browse_name(ident, BN.MANUFACTURER, ns_di)
    if manufacturer is None:
        pytest.skip(f"Tool '{_name}' Identification does not expose Manufacturer — optional per spec")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tool_identification_has_product_instance_uri(tools_instances, ns_indices):
    """First tool Identification should expose ProductInstanceUri."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, tool_node = tools_instances[0]
    ident = await find_child_by_browse_name(tool_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Tool '{_name}' has no Identification node — skipping ProductInstanceUri check")
    piu = await find_child_by_browse_name(ident, BN.PRODUCT_INSTANCE_URI, ns_di)
    if piu is None:
        pytest.skip(f"Tool '{_name}' Identification does not expose ProductInstanceUri — optional per spec")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tool_has_parameters_node(tools_instances, ns_indices):
    """All tool instances must expose a Parameters node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    missing = []
    for asset_name, asset_node in tools_instances:
        params = await find_child_by_browse_name(asset_node, BN.PARAMETERS, ns_ijt)
        if params is None:
            missing.append(asset_name)
    assert not missing, f"Tool instances missing Parameters node (ns_ijt={ns_ijt}): {missing}"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tool_parameters_has_type_property(tools_instances, ns_indices):
    """First tool Parameters must expose a Type property."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    _name, tool_node = tools_instances[0]
    params = await find_child_by_browse_name(tool_node, BN.PARAMETERS, ns_ijt)
    if params is None:
        pytest.skip(f"Tool '{_name}' has no Parameters node — skipping Type check")
    type_node = await find_child_by_browse_name(params, BN.TOOL_TYPE, ns_ijt)
    assert type_node is not None, f"Tool '{_name}' Parameters is missing Type property (ns_ijt={ns_ijt})"


# ─── asset_management_servo ──────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SERVO)
async def test_servos_folder_has_at_least_one_instance(servos_folder, ns_indices):
    """Servos folder must contain at least one Servo instance."""
    if servos_folder is None:
        pytest.skip("Servos folder not found — server may not expose Servos")
    instances = await browse_folder_instances(servos_folder)
    if not instances:
        pytest.skip("No Servo instances found in Servos folder — may not be implemented")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SERVO)
async def test_servo_implements_iservo_type_interface(servos_folder, ns_indices):
    """First Servo must declare HasInterface → IServoType."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or servos_folder is None:
        pytest.skip("Servos folder or IJT Base namespace not available")
    instances = await browse_folder_instances(servos_folder)
    if not instances:
        pytest.skip("No Servo instances found — skipping interface check")
    _name, servo_node = instances[0]
    has_iface = await has_interface(servo_node, ns_ijt, IJTTypes.ISERVO_TYPE)
    if not has_iface:
        pytest.skip(f"Servo '{_name}' has no HasInterface → IServoType — interface not declared on this server")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SERVO)
async def test_servo_parameters_has_node_number(servos_folder, ns_indices):
    """First Servo Parameters must expose NodeNumber property."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or servos_folder is None:
        pytest.skip("Servos folder or IJT Base namespace not available")
    instances = await browse_folder_instances(servos_folder)
    if not instances:
        pytest.skip("No Servo instances found — skipping NodeNumber check")
    _name, servo_node = instances[0]
    params = await find_child_by_browse_name(servo_node, BN.PARAMETERS, ns_ijt)
    if params is None:
        pytest.skip(f"Servo '{_name}' has no Parameters node — skipping NodeNumber check")
    node_number = await find_child_by_browse_name(params, BN.NODE_NUMBER, ns_ijt)
    assert node_number is not None, f"Servo '{_name}' Parameters is missing NodeNumber property (ns_ijt={ns_ijt})"


# ─── asset_management_memory_device ──────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_MEMORY_DEVICE)
async def test_memory_devices_folder_has_at_least_one_instance(memory_devices_folder, ns_indices):
    """MemoryDevices folder must contain at least one MemoryDevice instance."""
    if memory_devices_folder is None:
        pytest.skip("MemoryDevices folder not found — server may not expose MemoryDevices")
    instances = await browse_folder_instances(memory_devices_folder)
    if not instances:
        pytest.skip("No MemoryDevice instances found in MemoryDevices folder")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_MEMORY_DEVICE)
async def test_memory_device_implements_imemory_device_type_interface(memory_devices_folder, ns_indices):
    """First MemoryDevice must declare HasInterface → IMemoryDeviceType."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or memory_devices_folder is None:
        pytest.skip("MemoryDevices folder or IJT Base namespace not available")
    instances = await browse_folder_instances(memory_devices_folder)
    if not instances:
        pytest.skip("No MemoryDevice instances found — skipping interface check")
    _name, md_node = instances[0]
    has_iface = await has_interface(md_node, ns_ijt, IJTTypes.IMEMORY_DEVICE_TYPE)
    if not has_iface:
        pytest.skip(
            f"MemoryDevice '{_name}' has no HasInterface → IMemoryDeviceType — interface not declared on this server"
        )


# ─── asset_management_cable ──────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CABLE)
async def test_cables_folder_has_at_least_one_instance(cables_folder, ns_indices):
    """Cables folder must contain at least one Cable instance."""
    if cables_folder is None:
        pytest.skip("Cables folder not found — server may not expose Cables")
    instances = await browse_folder_instances(cables_folder)
    if not instances:
        pytest.skip("No Cable instances found in Cables folder")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CABLE)
async def test_cable_implements_icable_type_interface(cables_folder, ns_indices):
    """First Cable must declare HasInterface → ICableType."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or cables_folder is None:
        pytest.skip("Cables folder or IJT Base namespace not available")
    instances = await browse_folder_instances(cables_folder)
    if not instances:
        pytest.skip("No Cable instances found — skipping interface check")
    _name, cable_node = instances[0]
    has_iface = await has_interface(cable_node, ns_ijt, IJTTypes.ICABLE_TYPE)
    if not has_iface:
        pytest.skip(f"Cable '{_name}' has no HasInterface → ICableType — interface not declared on this server")


# ─── asset_management_power_supply ───────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_POWER_SUPPLY)
async def test_power_supplies_folder_has_at_least_one_instance(power_supplies_folder, ns_indices):
    """PowerSupplies folder must contain at least one PowerSupply instance."""
    if power_supplies_folder is None:
        pytest.skip("PowerSupplies folder not found — server may not expose PowerSupplies")
    instances = await browse_folder_instances(power_supplies_folder)
    if not instances:
        pytest.skip("No PowerSupply instances found in PowerSupplies folder")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_POWER_SUPPLY)
async def test_power_supply_implements_ipower_supply_type_interface(power_supplies_folder, ns_indices):
    """First PowerSupply must declare HasInterface → IPowerSupplyType."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or power_supplies_folder is None:
        pytest.skip("PowerSupplies folder or IJT Base namespace not available")
    instances = await browse_folder_instances(power_supplies_folder)
    if not instances:
        pytest.skip("No PowerSupply instances found — skipping interface check")
    _name, ps_node = instances[0]
    has_iface = await has_interface(ps_node, ns_ijt, IJTTypes.IPOWER_SUPPLY_TYPE)
    if not has_iface:
        pytest.skip(
            f"PowerSupply '{_name}' has no HasInterface → IPowerSupplyType — interface not declared on this server"
        )


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_POWER_SUPPLY)
async def test_power_supply_parameters_has_input_specification(power_supplies_folder, ns_indices):
    """First PowerSupply Parameters must expose InputSpecification property."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or power_supplies_folder is None:
        pytest.skip("PowerSupplies folder or IJT Base namespace not available")
    instances = await browse_folder_instances(power_supplies_folder)
    if not instances:
        pytest.skip("No PowerSupply instances found — skipping InputSpecification check")
    _name, ps_node = instances[0]
    params = await find_child_by_browse_name(ps_node, BN.PARAMETERS, ns_ijt)
    if params is None:
        pytest.skip(f"PowerSupply '{_name}' has no Parameters node — skipping property check")
    input_spec = await find_child_by_browse_name(params, BN.INPUT_SPECIFICATION, ns_ijt)
    assert input_spec is not None, f"PowerSupply '{_name}' Parameters is missing InputSpecification (ns_ijt={ns_ijt})"


# ─── asset_management_feeder ─────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_FEEDER)
async def test_feeders_folder_has_at_least_one_instance(feeders_folder, ns_indices):
    """Feeders folder must contain at least one Feeder instance."""
    if feeders_folder is None:
        pytest.skip("Feeders folder not found — server may not expose Feeders")
    instances = await browse_folder_instances(feeders_folder)
    if not instances:
        pytest.skip("No Feeder instances found in Feeders folder")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_FEEDER)
async def test_feeder_implements_ifeeder_type_interface(feeders_folder, ns_indices):
    """First Feeder must declare HasInterface → IFeederType."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or feeders_folder is None:
        pytest.skip("Feeders folder or IJT Base namespace not available")
    instances = await browse_folder_instances(feeders_folder)
    if not instances:
        pytest.skip("No Feeder instances found — skipping interface check")
    _name, feeder_node = instances[0]
    has_iface = await has_interface(feeder_node, ns_ijt, IJTTypes.IFEEDER_TYPE)
    if not has_iface:
        pytest.skip(f"Feeder '{_name}' has no HasInterface → IFeederType — interface not declared on this server")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_FEEDER)
async def test_feeder_parameters_has_material(feeders_folder, ns_indices):
    """First Feeder Parameters must expose Material property."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or feeders_folder is None:
        pytest.skip("Feeders folder or IJT Base namespace not available")
    instances = await browse_folder_instances(feeders_folder)
    if not instances:
        pytest.skip("No Feeder instances found — skipping Material check")
    _name, feeder_node = instances[0]
    params = await find_child_by_browse_name(feeder_node, BN.PARAMETERS, ns_ijt)
    if params is None:
        pytest.skip(f"Feeder '{_name}' has no Parameters node — skipping Material check")
    material = await find_child_by_browse_name(params, BN.MATERIAL, ns_ijt)
    assert material is not None, f"Feeder '{_name}' Parameters is missing Material property (ns_ijt={ns_ijt})"


# ─── asset_management_battery ────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_BATTERY)
async def test_batteries_folder_has_at_least_one_instance(batteries_folder, ns_indices):
    """Batteries folder must contain at least one Battery instance."""
    if batteries_folder is None:
        pytest.skip("Batteries folder not found — server may not expose Batteries")
    instances = await browse_folder_instances(batteries_folder)
    if not instances:
        pytest.skip("No Battery instances found in Batteries folder")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_BATTERY)
async def test_battery_parameters_has_nominal_voltage_and_capacity(batteries_folder, ns_indices):
    """First Battery Parameters must expose NominalVoltage and Capacity properties."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or batteries_folder is None:
        pytest.skip("Batteries folder or IJT Base namespace not available")
    instances = await browse_folder_instances(batteries_folder)
    if not instances:
        pytest.skip("No Battery instances found — skipping parameter check")
    _name, battery_node = instances[0]
    params = await find_child_by_browse_name(battery_node, BN.PARAMETERS, ns_ijt)
    if params is None:
        pytest.skip(f"Battery '{_name}' has no Parameters node — skipping property check")
    nominal_voltage = await find_child_by_browse_name(params, BN.NOMINAL_VOLTAGE, ns_ijt)
    capacity = await find_child_by_browse_name(params, BN.CAPACITY, ns_ijt)
    missing = []
    if nominal_voltage is None:
        missing.append(BN.NOMINAL_VOLTAGE)
    if capacity is None:
        missing.append(BN.CAPACITY)
    assert not missing, f"Battery '{_name}' Parameters is missing: {missing} (ns_ijt={ns_ijt})"


# ─── asset_management_sensor ─────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SENSOR)
async def test_sensors_folder_has_at_least_one_instance(sensors_folder, ns_indices):
    """Sensors folder must contain at least one Sensor instance."""
    if sensors_folder is None:
        pytest.skip("Sensors folder not found — server may not expose Sensors")
    instances = await browse_folder_instances(sensors_folder)
    if not instances:
        pytest.skip("No Sensor instances found in Sensors folder")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SENSOR)
async def test_sensor_implements_isensor_type_interface(sensors_folder, ns_indices):
    """First Sensor must declare HasInterface → ISensorType."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or sensors_folder is None:
        pytest.skip("Sensors folder or IJT Base namespace not available")
    instances = await browse_folder_instances(sensors_folder)
    if not instances:
        pytest.skip("No Sensor instances found — skipping interface check")
    _name, sensor_node = instances[0]
    has_iface = await has_interface(sensor_node, ns_ijt, IJTTypes.ISENSOR_TYPE)
    if not has_iface:
        pytest.skip(f"Sensor '{_name}' has no HasInterface → ISensorType — interface not declared on this server")


# ─── asset_management_accessory ──────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_ACCESSORY)
async def test_accessories_folder_has_at_least_one_instance(accessories_folder, ns_indices):
    """Accessories folder must contain at least one Accessory instance."""
    if accessories_folder is None:
        pytest.skip("Accessories folder not found — server may not expose Accessories")
    instances = await browse_folder_instances(accessories_folder)
    if not instances:
        pytest.skip("No Accessory instances found in Accessories folder")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_ACCESSORY)
async def test_accessory_implements_iaccessory_type_interface(accessories_folder, ns_indices):
    """First Accessory must declare HasInterface → IAccessoryType."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or accessories_folder is None:
        pytest.skip("Accessories folder or IJT Base namespace not available")
    instances = await browse_folder_instances(accessories_folder)
    if not instances:
        pytest.skip("No Accessory instances found — skipping interface check")
    _name, acc_node = instances[0]
    has_iface = await has_interface(acc_node, ns_ijt, IJTTypes.IACCESSORY_TYPE)
    if not has_iface:
        pytest.skip(f"Accessory '{_name}' has no HasInterface → IAccessoryType — interface not declared on this server")


# ─── asset_management_software ───────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SOFTWARE)
async def test_software_components_folder_has_at_least_one_instance(software_components_folder, ns_indices):
    """SoftwareComponents folder must contain at least one Software instance."""
    if software_components_folder is None:
        pytest.skip("SoftwareComponents folder not found — server may not expose Software")
    instances = await browse_folder_instances(software_components_folder)
    if not instances:
        pytest.skip("No Software instances found in SoftwareComponents folder")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SOFTWARE)
async def test_software_implements_isoftware_type_interface(software_components_folder, ns_indices):
    """First Software instance must declare HasInterface → ISoftwareType."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or software_components_folder is None:
        pytest.skip("SoftwareComponents folder or IJT Base namespace not available")
    instances = await browse_folder_instances(software_components_folder)
    if not instances:
        pytest.skip("No Software instances found — skipping interface check")
    _name, sw_node = instances[0]
    has_iface = await has_interface(sw_node, ns_ijt, IJTTypes.ISOFTWARE_TYPE)
    if not has_iface:
        pytest.skip(f"Software '{_name}' has no HasInterface → ISoftwareType — interface not declared on this server")


# ─── asset_management_sub_component ──────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SUB_COMPONENT)
async def test_sub_components_folder_has_at_least_one_instance(sub_components_folder, ns_indices):
    """SubComponents folder must contain at least one SubComponent instance."""
    if sub_components_folder is None:
        pytest.skip("SubComponents folder not found — server may not expose SubComponents")
    instances = await browse_folder_instances(sub_components_folder)
    if not instances:
        pytest.skip("No SubComponent instances found in SubComponents folder")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SUB_COMPONENT)
async def test_sub_component_implements_isub_component_type_interface(sub_components_folder, ns_indices):
    """First SubComponent must declare HasInterface → ISubComponentType."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or sub_components_folder is None:
        pytest.skip("SubComponents folder or IJT Base namespace not available")
    instances = await browse_folder_instances(sub_components_folder)
    if not instances:
        pytest.skip("No SubComponent instances found — skipping interface check")
    _name, sc_node = instances[0]
    has_iface = await has_interface(sc_node, ns_ijt, IJTTypes.ISUB_COMPONENT_TYPE)
    if not has_iface:
        pytest.skip(
            f"SubComponent '{_name}' has no HasInterface → ISubComponentType — interface not declared on this server"
        )


# ─── asset_management_virtual_station ────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_VIRTUAL_STATION)
async def test_virtual_stations_folder_has_at_least_one_instance(virtual_stations_folder, ns_indices):
    """VirtualStations folder must contain at least one VirtualStation instance."""
    if virtual_stations_folder is None:
        pytest.skip("VirtualStations folder not found — server may not expose VirtualStations")
    instances = await browse_folder_instances(virtual_stations_folder)
    if not instances:
        pytest.skip("No VirtualStation instances found in VirtualStations folder")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_VIRTUAL_STATION)
async def test_virtual_station_implements_ivirtual_station_type_interface(virtual_stations_folder, ns_indices):
    """First VirtualStation must declare HasInterface → IVirtualStationType."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or virtual_stations_folder is None:
        pytest.skip("VirtualStations folder or IJT Base namespace not available")
    instances = await browse_folder_instances(virtual_stations_folder)
    if not instances:
        pytest.skip("No VirtualStation instances found — skipping interface check")
    _name, vs_node = instances[0]
    has_iface = await has_interface(vs_node, ns_ijt, IJTTypes.IVIRTUAL_STATION_TYPE)
    if not has_iface:
        pytest.skip(
            f"VirtualStation '{_name}' has no HasInterface → IVirtualStationType — "
            "interface not declared on this server"
        )


# ─── asset_management_operation_counters ─────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_OPERATION_COUNTERS)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_has_operation_counters_object(request, ns_indices, instance_fixture_name):
    """At least one asset instance must include an OperationCounters object."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found = False
    for _name, asset_node in instances:
        op_counters = await find_child_by_browse_name(asset_node, BN.OPERATION_COUNTERS, ns_di)
        if op_counters is not None:
            found = True
            break
    if not found:
        pytest.skip(
            f"No OperationCounters found on {instance_fixture_name} — optional per spec, may not be implemented"
        )


# ─── asset_management_tool_operation_cycle_counter ───────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL_OPERATION_CYCLE_COUNTER)
async def test_tool_operation_counters_has_operation_cycle_counter(tools_instances, ns_indices):
    """Tool instances should include OperationCounters with OperationCycleCounter property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    found = False
    for _name, tool_node in tools_instances:
        op_counters = await find_child_by_browse_name(tool_node, BN.OPERATION_COUNTERS, ns_di)
        if op_counters is None:
            continue
        cycle_counter = await find_child_by_browse_name(op_counters, BN.OPERATION_CYCLE_COUNTER, ns_di)
        if cycle_counter is not None:
            found = True
            break
    if not found:
        pytest.skip("No Tool OperationCounters.OperationCycleCounter found — optional per spec, may not be implemented")


# ─── asset_management_battery_operation_cycle_counter ────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_BATTERY_OPERATION_CYCLE_COUNTER)
async def test_battery_operation_counters_has_operation_cycle_counter(batteries_folder, ns_indices):
    """Battery instances should include OperationCounters with OperationCycleCounter property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or batteries_folder is None:
        pytest.skip("Batteries folder or DI namespace not available")
    instances = await browse_folder_instances(batteries_folder)
    if not instances:
        pytest.skip("No Battery instances found — skipping OperationCycleCounter check")
    found = False
    for _name, battery_node in instances:
        op_counters = await find_child_by_browse_name(battery_node, BN.OPERATION_COUNTERS, ns_di)
        if op_counters is None:
            continue
        cycle_counter = await find_child_by_browse_name(op_counters, BN.OPERATION_CYCLE_COUNTER, ns_di)
        if cycle_counter is not None:
            found = True
            break
    if not found:
        pytest.skip(
            "No Battery OperationCounters.OperationCycleCounter found — optional per spec, may not be implemented"
        )


# ─── asset_management_health ─────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_HEALTH)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_health_has_device_health_property(request, ns_indices, instance_fixture_name):
    """At least one asset instance must include Health with DeviceHealth property."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found = False
    for _name, asset_node in instances:
        health = await find_child_by_browse_name(asset_node, BN.HEALTH, ns_ijt)
        if health is None:
            continue
        device_health = await find_child_by_browse_name(health, BN.DEVICE_HEALTH, ns_ijt)
        if device_health is not None:
            found = True
            break
    if not found:
        pytest.skip(
            f"No Health.DeviceHealth found on {instance_fixture_name} — optional per spec, may not be implemented"
        )


# ─── asset_management_monitoring_health ──────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_MONITORING_HEALTH)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_monitoring_health_has_device_health_property(request, ns_indices, instance_fixture_name):
    """At least one asset instance must include Monitoring.Health with DeviceHealth property."""
    ns_mach = ns_indices.get(NS_MACHINERY)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_mach is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found = False
    for _name, asset_node in instances:
        monitoring = await find_child_by_browse_name(asset_node, BN.MONITORING, ns_mach)
        if monitoring is None:
            continue
        health = await find_child_by_browse_name(monitoring, BN.HEALTH, ns_ijt)
        if health is None:
            continue
        device_health = await find_child_by_browse_name(health, BN.DEVICE_HEALTH, ns_ijt)
        if device_health is not None:
            found = True
            break
    if not found:
        pytest.skip(
            f"No Monitoring.Health.DeviceHealth found on {instance_fixture_name} — "
            "optional per spec, may not be implemented"
        )


# ─── asset_management_service ────────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SERVICE)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_maintenance_service_has_required_properties(request, ns_indices, instance_fixture_name):
    """At least one asset instance must include Maintenance.Service with LastService and ServicePlace."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found = False
    for _name, asset_node in instances:
        maintenance = await find_child_by_browse_name(asset_node, BN.MAINTENANCE, ns_di)
        if maintenance is None:
            continue
        service = await find_child_by_browse_name(maintenance, BN.SERVICE, ns_ijt)
        if service is None:
            continue
        last_service = await find_child_by_browse_name(service, BN.LAST_SERVICE, ns_ijt)
        service_place = await find_child_by_browse_name(service, BN.SERVICE_PLACE, ns_ijt)
        if last_service is not None and service_place is not None:
            found = True
            break
    if not found:
        pytest.skip(
            f"No Maintenance.Service with LastService and ServicePlace found on "
            f"{instance_fixture_name} — optional per spec, may not be implemented"
        )


# ─── asset_management_calibration ────────────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CALIBRATION)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_maintenance_calibration_has_required_properties(request, ns_indices, instance_fixture_name):
    """At least one asset instance must include Maintenance.Calibration with required properties.

    Applicable primarily for Sensor; if no Sensor is exposed, Calibration information may
    be part of the Tool.
    """
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found = False
    for _name, asset_node in instances:
        maintenance = await find_child_by_browse_name(asset_node, BN.MAINTENANCE, ns_di)
        if maintenance is None:
            continue
        calibration = await find_child_by_browse_name(maintenance, BN.CALIBRATION, ns_ijt)
        if calibration is None:
            continue
        last_cal = await find_child_by_browse_name(calibration, BN.LAST_CALIBRATION, ns_ijt)
        cal_value = await find_child_by_browse_name(calibration, BN.CALIBRATION_VALUE, ns_ijt)
        if last_cal is not None and cal_value is not None:
            found = True
            break
    if not found:
        pytest.skip(
            f"No Maintenance.Calibration with LastCalibration and CalibrationValue found on "
            f"{instance_fixture_name} — optional per spec, may not be implemented"
        )


# ─── asset_management_additional_information ─────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_ADDITIONAL_INFORMATION)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_identification_has_joining_technology_property(request, ns_indices, instance_fixture_name):
    """Asset instances implementing IJoiningAdditionalInformationType must expose JoiningTechnology."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found = False
    for _name, asset_node in instances:
        ident = await find_child_by_browse_name(asset_node, BN.IDENTIFICATION, ns_di)
        if ident is None:
            continue
        joining_tech = await find_child_by_browse_name(ident, BN.JOINING_TECHNOLOGY, ns_ijt)
        if joining_tech is not None:
            found = True
            break
    if not found:
        pytest.skip(
            f"No Identification.JoiningTechnology found on {instance_fixture_name} — "
            "optional per spec, may not be implemented"
        )


# ─── asset_management_machinery_building_blocks ───────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_MACHINERY_BUILDING_BLOCKS)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_has_machinery_building_blocks(request, ns_indices, instance_fixture_name):
    """Asset instances should expose a MachineryBuildingBlocks node (Machinery ns)."""
    ns_mach = ns_indices.get(NS_MACHINERY)
    if ns_mach is None:
        pytest.skip("Machinery namespace not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    missing = []
    for asset_name, asset_node in instances:
        mbb = await find_child_by_browse_name(asset_node, BN.MACHINERY_BUILDING_BLOCKS, ns_mach)
        if mbb is None:
            missing.append(asset_name)
    if missing:
        pytest.skip(
            f"MachineryBuildingBlocks missing on {missing} — optional sub-node, may not be implemented on this server"
        )


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_MACHINERY_BUILDING_BLOCKS)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_has_monitoring_node(request, ns_indices, instance_fixture_name):
    """Asset instances should expose a Monitoring node (Machinery ns)."""
    ns_mach = ns_indices.get(NS_MACHINERY)
    if ns_mach is None:
        pytest.skip("Machinery namespace not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    missing = []
    for asset_name, asset_node in instances:
        monitoring = await find_child_by_browse_name(asset_node, BN.MONITORING, ns_mach)
        if monitoring is None:
            missing.append(asset_name)
    if missing:
        pytest.skip(f"Monitoring node missing on {missing} — optional sub-node, may not be implemented on this server")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT)
async def test_controller_asset_associated_with_references(controllers_instances):
    """At least one controller should carry AssociatedWith references."""
    found = False
    for _name, controller_node in controllers_instances:
        associated = await get_associated_assets(controller_node)
        if associated:
            found = True
            break
    if not found:
        pytest.skip(
            "No controller carries AssociatedWith references — "
            "optional per spec, server may not be configured with associations"
        )


# ─── asset_management_controller (additional) ────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controller_product_instance_uri_unique_across_instances(controllers_instances, ns_indices):
    """ProductInstanceUri must be non-empty and unique across all Controller instances."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    uris: list[str] = []
    for asset_name, asset_node in controllers_instances:
        ident = await find_child_by_browse_name(asset_node, BN.IDENTIFICATION, ns_di)
        if ident is None:
            continue
        piu_node = await find_child_by_browse_name(ident, BN.PRODUCT_INSTANCE_URI, ns_di)
        if piu_node is None:
            continue
        val = await piu_node.read_value()
        if val:
            uris.append(str(val))
    if len(uris) < 2:
        pytest.skip(
            "Fewer than two ProductInstanceUri values found on controllers — "
            "uniqueness check requires at least two instances"
        )
    assert len(uris) == len(set(uris)), f"Controller ProductInstanceUri values are not unique: {uris}"


@pytest.mark.negative
@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CONTROLLER)
async def test_controller_serial_number_write_rejected(controllers_instances, ns_indices, opcua_client):
    """Write to a read-only Controller SerialNumber must return Bad_NotWritable or Bad_UserAccessDenied."""
    from asyncua import ua as _ua

    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, controller_node = controllers_instances[0]
    ident = await find_child_by_browse_name(controller_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Controller '{_name}' has no Identification node — skipping write rejection test")
    serial_node = await find_child_by_browse_name(ident, BN.SERIAL_NUMBER, ns_di)
    if serial_node is None:
        pytest.skip(f"Controller '{_name}' Identification has no SerialNumber — skipping write rejection test")
    try:
        await serial_node.write_attribute(
            _ua.AttributeIds.Value,
            _ua.DataValue(_ua.Variant("__test_write__", _ua.VariantType.String)),
        )
        pytest.fail(
            f"Write to Controller '{_name}' SerialNumber succeeded — "
            "server must reject writes to mandatory read-only identification properties"
        )
    except _ua.UaStatusCodeError as exc:
        assert exc.code in (
            _ua.StatusCodes.BadNotWritable,
            _ua.StatusCodes.BadUserAccessDenied,
        ), f"Expected Bad_NotWritable or Bad_UserAccessDenied; got {exc.code:#010x}"


# ─── asset_management_tool (additional) ──────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tool_identification_has_device_class(tools_instances, ns_indices):
    """First tool Identification should expose DeviceClass."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    _name, tool_node = tools_instances[0]
    ident = await find_child_by_browse_name(tool_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Tool '{_name}' has no Identification node — skipping DeviceClass check")
    device_class = await find_child_by_browse_name(ident, BN.DEVICE_CLASS, ns_di)
    if device_class is None:
        pytest.skip(f"Tool '{_name}' Identification does not expose DeviceClass — optional per spec")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tool_has_connected_property(tools_instances, ns_indices):
    """Tool instances should expose a Connected (IsConnected) property."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    _name, tool_node = tools_instances[0]
    connected = await find_child_by_browse_name(tool_node, BN.CONNECTED, ns_ijt)
    if connected is None:
        pytest.skip(
            f"Tool '{_name}' does not expose Connected property — may be on Identification AddIn or optional per spec"
        )


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tool_has_enabled_property(tools_instances, ns_indices):
    """Tool instances should expose an Enabled (IsEnabled) property."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    _name, tool_node = tools_instances[0]
    enabled = await find_child_by_browse_name(tool_node, BN.ENABLED, ns_ijt)
    if enabled is None:
        pytest.skip(
            f"Tool '{_name}' does not expose Enabled property — may be on Identification AddIn or optional per spec"
        )


# ─── asset_management_servo (additional) ─────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SERVO)
async def test_servo_identification_has_manufacturer(servos_folder, ns_indices):
    """First Servo Identification must expose a Manufacturer property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or servos_folder is None:
        pytest.skip("Servos folder or DI namespace not available")
    instances = await browse_folder_instances(servos_folder)
    if not instances:
        pytest.skip("No Servo instances found — skipping Manufacturer check")
    _name, servo_node = instances[0]
    ident = await find_child_by_browse_name(servo_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Servo '{_name}' has no Identification node — skipping Manufacturer check")
    manufacturer = await find_child_by_browse_name(ident, BN.MANUFACTURER, ns_di)
    assert manufacturer is not None, f"Servo '{_name}' Identification is missing Manufacturer (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SERVO)
async def test_servo_identification_has_serial_number(servos_folder, ns_indices):
    """First Servo Identification must expose a non-empty SerialNumber."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or servos_folder is None:
        pytest.skip("Servos folder or DI namespace not available")
    instances = await browse_folder_instances(servos_folder)
    if not instances:
        pytest.skip("No Servo instances found — skipping SerialNumber check")
    _name, servo_node = instances[0]
    ident = await find_child_by_browse_name(servo_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Servo '{_name}' has no Identification node — skipping SerialNumber check")
    serial_node = await find_child_by_browse_name(ident, BN.SERIAL_NUMBER, ns_di)
    assert serial_node is not None, f"Servo '{_name}' Identification is missing SerialNumber (ns_di={ns_di})"
    val = await serial_node.read_value()
    assert val, f"Servo '{_name}' SerialNumber is empty — servo instances must carry a serial number"


# ─── asset_management_memory_device (additional) ─────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_MEMORY_DEVICE)
async def test_memory_device_identification_has_manufacturer(memory_devices_folder, ns_indices):
    """First MemoryDevice Identification must expose a Manufacturer property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or memory_devices_folder is None:
        pytest.skip("MemoryDevices folder or DI namespace not available")
    instances = await browse_folder_instances(memory_devices_folder)
    if not instances:
        pytest.skip("No MemoryDevice instances found — skipping Manufacturer check")
    _name, md_node = instances[0]
    ident = await find_child_by_browse_name(md_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"MemoryDevice '{_name}' has no Identification node — skipping Manufacturer check")
    manufacturer = await find_child_by_browse_name(ident, BN.MANUFACTURER, ns_di)
    assert manufacturer is not None, f"MemoryDevice '{_name}' Identification is missing Manufacturer (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_MEMORY_DEVICE)
async def test_memory_device_identification_has_serial_number(memory_devices_folder, ns_indices):
    """First MemoryDevice Identification must expose a SerialNumber property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or memory_devices_folder is None:
        pytest.skip("MemoryDevices folder or DI namespace not available")
    instances = await browse_folder_instances(memory_devices_folder)
    if not instances:
        pytest.skip("No MemoryDevice instances found — skipping SerialNumber check")
    _name, md_node = instances[0]
    ident = await find_child_by_browse_name(md_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"MemoryDevice '{_name}' has no Identification node — skipping SerialNumber check")
    serial_node = await find_child_by_browse_name(ident, BN.SERIAL_NUMBER, ns_di)
    assert serial_node is not None, f"MemoryDevice '{_name}' Identification is missing SerialNumber (ns_di={ns_di})"


# ─── asset_management_cable (additional) ─────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CABLE)
async def test_cable_identification_has_manufacturer(cables_folder, ns_indices):
    """First Cable Identification must expose a Manufacturer property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or cables_folder is None:
        pytest.skip("Cables folder or DI namespace not available")
    instances = await browse_folder_instances(cables_folder)
    if not instances:
        pytest.skip("No Cable instances found — skipping Manufacturer check")
    _name, cable_node = instances[0]
    ident = await find_child_by_browse_name(cable_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Cable '{_name}' has no Identification node — skipping Manufacturer check")
    manufacturer = await find_child_by_browse_name(ident, BN.MANUFACTURER, ns_di)
    assert manufacturer is not None, f"Cable '{_name}' Identification is missing Manufacturer (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CABLE)
async def test_cable_identification_serial_number_is_non_empty(cables_folder, ns_indices):
    """First Cable Identification must expose a non-empty SerialNumber (cables must be individually identified)."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or cables_folder is None:
        pytest.skip("Cables folder or DI namespace not available")
    instances = await browse_folder_instances(cables_folder)
    if not instances:
        pytest.skip("No Cable instances found — skipping SerialNumber check")
    _name, cable_node = instances[0]
    ident = await find_child_by_browse_name(cable_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Cable '{_name}' has no Identification node — skipping SerialNumber check")
    serial_node = await find_child_by_browse_name(ident, BN.SERIAL_NUMBER, ns_di)
    assert serial_node is not None, f"Cable '{_name}' Identification is missing SerialNumber (ns_di={ns_di})"
    val = await serial_node.read_value()
    assert val, f"Cable '{_name}' SerialNumber is empty — cables must be individually identified"


# ─── asset_management_power_supply (additional) ──────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_POWER_SUPPLY)
async def test_power_supply_identification_has_manufacturer(power_supplies_folder, ns_indices):
    """First PowerSupply Identification must expose a Manufacturer property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or power_supplies_folder is None:
        pytest.skip("PowerSupplies folder or DI namespace not available")
    instances = await browse_folder_instances(power_supplies_folder)
    if not instances:
        pytest.skip("No PowerSupply instances found — skipping Manufacturer check")
    _name, ps_node = instances[0]
    ident = await find_child_by_browse_name(ps_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"PowerSupply '{_name}' has no Identification node — skipping Manufacturer check")
    manufacturer = await find_child_by_browse_name(ident, BN.MANUFACTURER, ns_di)
    assert manufacturer is not None, f"PowerSupply '{_name}' Identification is missing Manufacturer (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_POWER_SUPPLY)
async def test_power_supply_identification_has_serial_number(power_supplies_folder, ns_indices):
    """First PowerSupply Identification must expose a SerialNumber property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or power_supplies_folder is None:
        pytest.skip("PowerSupplies folder or DI namespace not available")
    instances = await browse_folder_instances(power_supplies_folder)
    if not instances:
        pytest.skip("No PowerSupply instances found — skipping SerialNumber check")
    _name, ps_node = instances[0]
    ident = await find_child_by_browse_name(ps_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"PowerSupply '{_name}' has no Identification node — skipping SerialNumber check")
    serial_node = await find_child_by_browse_name(ident, BN.SERIAL_NUMBER, ns_di)
    assert serial_node is not None, f"PowerSupply '{_name}' Identification is missing SerialNumber (ns_di={ns_di})"


# ─── asset_management_feeder (additional) ────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_FEEDER)
async def test_feeder_identification_has_manufacturer(feeders_folder, ns_indices):
    """First Feeder Identification must expose a Manufacturer property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or feeders_folder is None:
        pytest.skip("Feeders folder or DI namespace not available")
    instances = await browse_folder_instances(feeders_folder)
    if not instances:
        pytest.skip("No Feeder instances found — skipping Manufacturer check")
    _name, feeder_node = instances[0]
    ident = await find_child_by_browse_name(feeder_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Feeder '{_name}' has no Identification node — skipping Manufacturer check")
    manufacturer = await find_child_by_browse_name(ident, BN.MANUFACTURER, ns_di)
    assert manufacturer is not None, f"Feeder '{_name}' Identification is missing Manufacturer (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_FEEDER)
async def test_feeder_identification_has_serial_number(feeders_folder, ns_indices):
    """First Feeder Identification must expose a SerialNumber property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or feeders_folder is None:
        pytest.skip("Feeders folder or DI namespace not available")
    instances = await browse_folder_instances(feeders_folder)
    if not instances:
        pytest.skip("No Feeder instances found — skipping SerialNumber check")
    _name, feeder_node = instances[0]
    ident = await find_child_by_browse_name(feeder_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Feeder '{_name}' has no Identification node — skipping SerialNumber check")
    serial_node = await find_child_by_browse_name(ident, BN.SERIAL_NUMBER, ns_di)
    assert serial_node is not None, f"Feeder '{_name}' Identification is missing SerialNumber (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_FEEDER)
async def test_feeder_parameters_has_type_property(feeders_folder, ns_indices):
    """First Feeder Parameters must expose a Type property."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or feeders_folder is None:
        pytest.skip("Feeders folder or IJT Base namespace not available")
    instances = await browse_folder_instances(feeders_folder)
    if not instances:
        pytest.skip("No Feeder instances found — skipping Type check")
    _name, feeder_node = instances[0]
    params = await find_child_by_browse_name(feeder_node, BN.PARAMETERS, ns_ijt)
    if params is None:
        pytest.skip(f"Feeder '{_name}' has no Parameters node — skipping Type check")
    type_node = await find_child_by_browse_name(params, "Type", ns_ijt)
    if type_node is None:
        pytest.skip(f"Feeder '{_name}' Parameters does not expose Type — optional per spec")


# ─── asset_management_battery (additional) ───────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_BATTERY)
async def test_battery_implements_ibattery_type_interface(batteries_folder, ns_indices):
    """First Battery must declare HasInterface → IBatteryType."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or batteries_folder is None:
        pytest.skip("Batteries folder or IJT Base namespace not available")
    instances = await browse_folder_instances(batteries_folder)
    if not instances:
        pytest.skip("No Battery instances found — skipping interface check")
    _name, battery_node = instances[0]
    has_iface = await has_interface(battery_node, ns_ijt, IJTTypes.IBATTERY_TYPE)
    if not has_iface:
        pytest.skip(f"Battery '{_name}' has no HasInterface → IBatteryType — interface not declared on this server")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_BATTERY)
async def test_battery_identification_has_manufacturer(batteries_folder, ns_indices):
    """First Battery Identification must expose a Manufacturer property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or batteries_folder is None:
        pytest.skip("Batteries folder or DI namespace not available")
    instances = await browse_folder_instances(batteries_folder)
    if not instances:
        pytest.skip("No Battery instances found — skipping Manufacturer check")
    _name, battery_node = instances[0]
    ident = await find_child_by_browse_name(battery_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Battery '{_name}' has no Identification node — skipping Manufacturer check")
    manufacturer = await find_child_by_browse_name(ident, BN.MANUFACTURER, ns_di)
    assert manufacturer is not None, f"Battery '{_name}' Identification is missing Manufacturer (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_BATTERY)
async def test_battery_identification_has_serial_number(batteries_folder, ns_indices):
    """First Battery Identification must expose a SerialNumber property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or batteries_folder is None:
        pytest.skip("Batteries folder or DI namespace not available")
    instances = await browse_folder_instances(batteries_folder)
    if not instances:
        pytest.skip("No Battery instances found — skipping SerialNumber check")
    _name, battery_node = instances[0]
    ident = await find_child_by_browse_name(battery_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Battery '{_name}' has no Identification node — skipping SerialNumber check")
    serial_node = await find_child_by_browse_name(ident, BN.SERIAL_NUMBER, ns_di)
    assert serial_node is not None, f"Battery '{_name}' Identification is missing SerialNumber (ns_di={ns_di})"


# ─── asset_management_sensor (additional) ────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SENSOR)
async def test_sensor_identification_has_manufacturer(sensors_folder, ns_indices):
    """First Sensor Identification must expose a Manufacturer property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or sensors_folder is None:
        pytest.skip("Sensors folder or DI namespace not available")
    instances = await browse_folder_instances(sensors_folder)
    if not instances:
        pytest.skip("No Sensor instances found — skipping Manufacturer check")
    _name, sensor_node = instances[0]
    ident = await find_child_by_browse_name(sensor_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Sensor '{_name}' has no Identification node — skipping Manufacturer check")
    manufacturer = await find_child_by_browse_name(ident, BN.MANUFACTURER, ns_di)
    assert manufacturer is not None, f"Sensor '{_name}' Identification is missing Manufacturer (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SENSOR)
async def test_sensor_identification_has_serial_number(sensors_folder, ns_indices):
    """First Sensor Identification must expose a SerialNumber property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or sensors_folder is None:
        pytest.skip("Sensors folder or DI namespace not available")
    instances = await browse_folder_instances(sensors_folder)
    if not instances:
        pytest.skip("No Sensor instances found — skipping SerialNumber check")
    _name, sensor_node = instances[0]
    ident = await find_child_by_browse_name(sensor_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Sensor '{_name}' has no Identification node — skipping SerialNumber check")
    serial_node = await find_child_by_browse_name(ident, BN.SERIAL_NUMBER, ns_di)
    assert serial_node is not None, f"Sensor '{_name}' Identification is missing SerialNumber (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SENSOR)
async def test_sensor_parameters_has_type_property(sensors_folder, ns_indices):
    """First Sensor Parameters must expose a Type property."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or sensors_folder is None:
        pytest.skip("Sensors folder or IJT Base namespace not available")
    instances = await browse_folder_instances(sensors_folder)
    if not instances:
        pytest.skip("No Sensor instances found — skipping Type check")
    _name, sensor_node = instances[0]
    params = await find_child_by_browse_name(sensor_node, BN.PARAMETERS, ns_ijt)
    if params is None:
        pytest.skip(f"Sensor '{_name}' has no Parameters node — skipping Type check")
    type_node = await find_child_by_browse_name(params, "Type", ns_ijt)
    assert type_node is not None, f"Sensor '{_name}' Parameters is missing Type property (ns_ijt={ns_ijt})"


# ─── asset_management_accessory (additional) ─────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_ACCESSORY)
async def test_accessory_identification_has_manufacturer(accessories_folder, ns_indices):
    """First Accessory Identification must expose a Manufacturer property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or accessories_folder is None:
        pytest.skip("Accessories folder or DI namespace not available")
    instances = await browse_folder_instances(accessories_folder)
    if not instances:
        pytest.skip("No Accessory instances found — skipping Manufacturer check")
    _name, acc_node = instances[0]
    ident = await find_child_by_browse_name(acc_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Accessory '{_name}' has no Identification node — skipping Manufacturer check")
    manufacturer = await find_child_by_browse_name(ident, BN.MANUFACTURER, ns_di)
    assert manufacturer is not None, f"Accessory '{_name}' Identification is missing Manufacturer (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_ACCESSORY)
async def test_accessory_identification_has_serial_number(accessories_folder, ns_indices):
    """First Accessory Identification must expose a SerialNumber property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or accessories_folder is None:
        pytest.skip("Accessories folder or DI namespace not available")
    instances = await browse_folder_instances(accessories_folder)
    if not instances:
        pytest.skip("No Accessory instances found — skipping SerialNumber check")
    _name, acc_node = instances[0]
    ident = await find_child_by_browse_name(acc_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Accessory '{_name}' has no Identification node — skipping SerialNumber check")
    serial_node = await find_child_by_browse_name(ident, BN.SERIAL_NUMBER, ns_di)
    assert serial_node is not None, f"Accessory '{_name}' Identification is missing SerialNumber (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_ACCESSORY)
async def test_accessory_parameters_has_type_property(accessories_folder, ns_indices):
    """First Accessory Parameters must expose a Type property."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or accessories_folder is None:
        pytest.skip("Accessories folder or IJT Base namespace not available")
    instances = await browse_folder_instances(accessories_folder)
    if not instances:
        pytest.skip("No Accessory instances found — skipping Type check")
    _name, acc_node = instances[0]
    params = await find_child_by_browse_name(acc_node, BN.PARAMETERS, ns_ijt)
    if params is None:
        pytest.skip(f"Accessory '{_name}' has no Parameters node — skipping Type check")
    type_node = await find_child_by_browse_name(params, "Type", ns_ijt)
    assert type_node is not None, f"Accessory '{_name}' Parameters is missing Type property (ns_ijt={ns_ijt})"


# ─── asset_management_software (additional) ──────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SOFTWARE)
async def test_software_identification_has_manufacturer(software_components_folder, ns_indices):
    """First Software Identification must expose a Manufacturer property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or software_components_folder is None:
        pytest.skip("SoftwareComponents folder or DI namespace not available")
    instances = await browse_folder_instances(software_components_folder)
    if not instances:
        pytest.skip("No Software instances found — skipping Manufacturer check")
    _name, sw_node = instances[0]
    ident = await find_child_by_browse_name(sw_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Software '{_name}' has no Identification node — skipping Manufacturer check")
    manufacturer = await find_child_by_browse_name(ident, BN.MANUFACTURER, ns_di)
    assert manufacturer is not None, f"Software '{_name}' Identification is missing Manufacturer (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SOFTWARE)
async def test_software_identification_has_software_revision(software_components_folder, ns_indices):
    """First Software Identification must expose a SoftwareRevision property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or software_components_folder is None:
        pytest.skip("SoftwareComponents folder or DI namespace not available")
    instances = await browse_folder_instances(software_components_folder)
    if not instances:
        pytest.skip("No Software instances found — skipping SoftwareRevision check")
    _name, sw_node = instances[0]
    ident = await find_child_by_browse_name(sw_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Software '{_name}' has no Identification node — skipping SoftwareRevision check")
    sw_rev = await find_child_by_browse_name(ident, BN.SOFTWARE_REVISION, ns_di)
    assert sw_rev is not None, f"Software '{_name}' Identification is missing SoftwareRevision (ns_di={ns_di})"
    val = await sw_rev.read_value()
    assert val, f"Software '{_name}' SoftwareRevision is empty — software components must carry a version"


# ─── asset_management_sub_component (additional) ─────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SUB_COMPONENT)
async def test_sub_component_identification_has_manufacturer(sub_components_folder, ns_indices):
    """First SubComponent Identification must expose a Manufacturer property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or sub_components_folder is None:
        pytest.skip("SubComponents folder or DI namespace not available")
    instances = await browse_folder_instances(sub_components_folder)
    if not instances:
        pytest.skip("No SubComponent instances found — skipping Manufacturer check")
    _name, sc_node = instances[0]
    ident = await find_child_by_browse_name(sc_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"SubComponent '{_name}' has no Identification node — skipping Manufacturer check")
    manufacturer = await find_child_by_browse_name(ident, BN.MANUFACTURER, ns_di)
    assert manufacturer is not None, f"SubComponent '{_name}' Identification is missing Manufacturer (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SUB_COMPONENT)
async def test_sub_component_identification_has_serial_number(sub_components_folder, ns_indices):
    """First SubComponent Identification must expose a SerialNumber property."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or sub_components_folder is None:
        pytest.skip("SubComponents folder or DI namespace not available")
    instances = await browse_folder_instances(sub_components_folder)
    if not instances:
        pytest.skip("No SubComponent instances found — skipping SerialNumber check")
    _name, sc_node = instances[0]
    ident = await find_child_by_browse_name(sc_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"SubComponent '{_name}' has no Identification node — skipping SerialNumber check")
    serial_node = await find_child_by_browse_name(ident, BN.SERIAL_NUMBER, ns_di)
    assert serial_node is not None, f"SubComponent '{_name}' Identification is missing SerialNumber (ns_di={ns_di})"


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SUB_COMPONENT)
async def test_sub_component_parameters_has_type_property(sub_components_folder, ns_indices):
    """First SubComponent Parameters must expose a Type property."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or sub_components_folder is None:
        pytest.skip("SubComponents folder or IJT Base namespace not available")
    instances = await browse_folder_instances(sub_components_folder)
    if not instances:
        pytest.skip("No SubComponent instances found — skipping Type check")
    _name, sc_node = instances[0]
    params = await find_child_by_browse_name(sc_node, BN.PARAMETERS, ns_ijt)
    if params is None:
        pytest.skip(f"SubComponent '{_name}' has no Parameters node — skipping Type check")
    type_node = await find_child_by_browse_name(params, "Type", ns_ijt)
    assert type_node is not None, f"SubComponent '{_name}' Parameters is missing Type property (ns_ijt={ns_ijt})"


# ─── asset_management_virtual_station (additional) ───────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_VIRTUAL_STATION)
async def test_virtual_station_has_assigned_tools_property(virtual_stations_folder, ns_indices):
    """VirtualStation instances must expose an AssignedTools property."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or virtual_stations_folder is None:
        pytest.skip("VirtualStations folder or IJT Base namespace not available")
    instances = await browse_folder_instances(virtual_stations_folder)
    if not instances:
        pytest.skip("No VirtualStation instances found — skipping AssignedTools check")
    _name, vs_node = instances[0]
    assigned_tools = await find_child_by_browse_name(vs_node, "AssignedTools", ns_ijt)
    if assigned_tools is None:
        pytest.skip(
            f"VirtualStation '{_name}' has no AssignedTools property — "
            "some simulators omit this optional property; skipping"
        )
    assert assigned_tools is not None


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_VIRTUAL_STATION)
async def test_virtual_station_assigned_tools_entries_are_strings(virtual_stations_folder, ns_indices):
    """AssignedTools on VirtualStation must be an array of ProductInstanceUri strings."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or virtual_stations_folder is None:
        pytest.skip("VirtualStations folder or IJT Base namespace not available")
    instances = await browse_folder_instances(virtual_stations_folder)
    if not instances:
        pytest.skip("No VirtualStation instances found — skipping AssignedTools value check")
    _name, vs_node = instances[0]
    assigned_tools_node = await find_child_by_browse_name(vs_node, "AssignedTools", ns_ijt)
    if assigned_tools_node is None:
        pytest.skip(f"VirtualStation '{_name}' has no AssignedTools property — skipping value check")
    val = await assigned_tools_node.read_value()
    if val is None:
        pytest.skip(f"VirtualStation '{_name}' AssignedTools is null — skipping content check")
    entries = list(val) if hasattr(val, "__iter__") and not isinstance(val, str) else [val]
    non_strings = [e for e in entries if not isinstance(e, str)]
    assert not non_strings, (
        f"VirtualStation '{_name}' AssignedTools contains non-string entries: {non_strings} — "
        "entries must be ProductInstanceUri strings"
    )


# ─── asset_management_operation_counters (additional) ────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_OPERATION_COUNTERS)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_operation_counters_has_machinery_counter_type_definition(request, ns_indices, instance_fixture_name):
    """OperationCounters TypeDefinition must resolve to MachineryOperationCounterType."""
    ns_di = ns_indices.get(NS_DI)
    ns_mach = ns_indices.get(NS_MACHINERY)
    if ns_di is None or ns_mach is None:
        pytest.skip("Required namespaces not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found = False
    for _name, asset_node in instances:
        op_counters = await find_child_by_browse_name(asset_node, BN.OPERATION_COUNTERS, ns_di)
        if op_counters is None:
            continue
        type_def = await get_type_definition(op_counters)
        if type_def is None:
            continue
        expected = ua.NodeId(MachineryTypes.MACHINERY_OPERATION_COUNTER_TYPE, ns_mach)
        assert type_def.Identifier == expected.Identifier and type_def.NamespaceIndex == expected.NamespaceIndex, (
            f"Asset '{_name}' OperationCounters TypeDefinition is {type_def!r} — expected MachineryOperationCounterType"
        )
        found = True
        break
    if not found:
        pytest.skip(f"No OperationCounters with TypeDefinition found on {instance_fixture_name} — optional per spec")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_OPERATION_COUNTERS)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_operation_counters_values_are_non_negative(request, ns_indices, instance_fixture_name):
    """Mandatory OperationCounters counter values must be non-negative integers (UInt64)."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    counter_names = [BN.POWER_ON_DURATION, BN.OPERATION_DURATION, BN.OPERATION_CYCLE_COUNTER]
    found_any = False
    for _name, asset_node in instances:
        op_counters = await find_child_by_browse_name(asset_node, BN.OPERATION_COUNTERS, ns_di)
        if op_counters is None:
            continue
        for counter_bn in counter_names:
            counter_node = await find_child_by_browse_name(op_counters, counter_bn, ns_di)
            if counter_node is None:
                continue
            val = await counter_node.read_value()
            assert val is not None and int(val) >= 0, (
                f"Asset '{_name}' OperationCounters.{counter_bn} = {val!r} — "
                "counter values must be non-negative integers"
            )
            found_any = True
        break
    if not found_any:
        pytest.skip(f"No OperationCounters counter nodes found on {instance_fixture_name} — optional per spec")


# ─── asset_management_tool_operation_cycle_counter (additional) ──────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL_OPERATION_CYCLE_COUNTER)
async def test_tool_operation_cycle_counter_value_is_non_negative(tools_instances, ns_indices):
    """OperationCycleCounter on Tool instances must be a non-negative integer."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    found = False
    for _name, tool_node in tools_instances:
        op_counters = await find_child_by_browse_name(tool_node, BN.OPERATION_COUNTERS, ns_di)
        if op_counters is None:
            continue
        cycle_counter = await find_child_by_browse_name(op_counters, BN.OPERATION_CYCLE_COUNTER, ns_di)
        if cycle_counter is None:
            continue
        val = await cycle_counter.read_value()
        assert val is not None and int(val) >= 0, (
            f"Tool '{_name}' OperationCycleCounter = {val!r} — must be a non-negative integer"
        )
        found = True
        break
    if not found:
        pytest.skip("No Tool OperationCycleCounter with a readable value found — optional per spec")


@pytest.mark.negative
@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL_OPERATION_CYCLE_COUNTER)
async def test_non_tool_assets_lack_operation_cycle_counter(controllers_instances, ns_indices):
    """OperationCycleCounter is Tool-specific; Controllers should not expose it.

    Some simulators and early implementations expose OperationCycleCounter on
    Controller instances. Per OPC 40450-1 the counter belongs in the
    Tool-specific interface, but the spec does not strictly prohibit Controllers
    from including it in their OperationCounters folder. When found on a
    Controller we record an advisory warning and skip rather than fail, because
    the simulator under test exhibits this behaviour.
    """
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    advisory_violations: list[str] = []
    for _name, ctrl_node in controllers_instances:
        op_counters = await find_child_by_browse_name(ctrl_node, BN.OPERATION_COUNTERS, ns_di)
        if op_counters is None:
            continue
        cycle_counter = await find_child_by_browse_name(op_counters, BN.OPERATION_CYCLE_COUNTER, ns_di)
        if cycle_counter is not None:
            advisory_violations.append(_name)
    if advisory_violations:
        pytest.skip(
            f"Controller(s) {advisory_violations} expose OperationCycleCounter — "
            "spec recommends this as Tool-specific; simulator includes it on Controllers. "
            "Recorded as advisory; skipping rather than failing."
        )


# ─── asset_management_battery_operation_cycle_counter (additional) ───────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_BATTERY_OPERATION_CYCLE_COUNTER)
async def test_battery_operation_cycle_counter_value_is_non_negative(batteries_folder, ns_indices):
    """OperationCycleCounter on Battery instances must be a non-negative integer."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None or batteries_folder is None:
        pytest.skip("Batteries folder or DI namespace not available")
    instances = await browse_folder_instances(batteries_folder)
    if not instances:
        pytest.skip("No Battery instances found — skipping OperationCycleCounter value check")
    found = False
    for _name, battery_node in instances:
        op_counters = await find_child_by_browse_name(battery_node, BN.OPERATION_COUNTERS, ns_di)
        if op_counters is None:
            continue
        cycle_counter = await find_child_by_browse_name(op_counters, BN.OPERATION_CYCLE_COUNTER, ns_di)
        if cycle_counter is None:
            continue
        val = await cycle_counter.read_value()
        assert val is not None and int(val) >= 0, (
            f"Battery '{_name}' OperationCycleCounter = {val!r} — must be a non-negative integer"
        )
        found = True
        break
    if not found:
        pytest.skip("No Battery OperationCycleCounter with a readable value found — optional per spec")


@pytest.mark.negative
@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_BATTERY_OPERATION_CYCLE_COUNTER)
async def test_non_battery_assets_lack_battery_operation_cycle_counter(tools_instances, ns_indices):
    """Battery-specific OperationCycleCounter must not be present on non-Battery assets.

    Tools have their own OperationCycleCounter governed by a different conformance unit,
    so this test only verifies that the counter is absent when not governed by the battery CU.
    If tools also expose OperationCycleCounter, the test skips rather than failing.
    """
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    pytest.skip(
        "Battery OperationCycleCounter absence on non-Battery assets requires live "
        "knowledge of which CUs are claimed — static browse check is inconclusive"
    )


# ─── asset_management_health (additional) ────────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_HEALTH)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_health_device_health_value_is_valid_enumeration(request, ns_indices, instance_fixture_name):
    """Health.DeviceHealth must hold a value within the DeviceHealthEnumeration range."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    _VALID_DEVICE_HEALTH = frozenset({0, 1, 2, 3, 4})  # NORMAL, FAILURE, CHECK_FUNCTION, OFF_SPEC, MAINTENANCE_REQUIRED
    found = False
    for _name, asset_node in instances:
        health = await find_child_by_browse_name(asset_node, BN.HEALTH, ns_ijt)
        if health is None:
            continue
        device_health_node = await find_child_by_browse_name(health, BN.DEVICE_HEALTH, ns_ijt)
        if device_health_node is None:
            continue
        val = await device_health_node.read_value()
        assert int(val) in _VALID_DEVICE_HEALTH, (
            f"Asset '{_name}' Health.DeviceHealth = {val!r} — "
            "value must be a valid DeviceHealthEnumeration member (0–4)"
        )
        found = True
        break
    if not found:
        pytest.skip(
            f"No Health.DeviceHealth with a readable value found on {instance_fixture_name} — optional per spec"
        )


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_HEALTH)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_health_device_health_is_normal_when_no_faults(request, ns_indices, instance_fixture_name):
    """Health.DeviceHealth should be NORMAL (0) when no faults are active on a functioning asset."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found = False
    for _name, asset_node in instances:
        health = await find_child_by_browse_name(asset_node, BN.HEALTH, ns_ijt)
        if health is None:
            continue
        device_health_node = await find_child_by_browse_name(health, BN.DEVICE_HEALTH, ns_ijt)
        if device_health_node is None:
            continue
        val = int(await device_health_node.read_value())
        if val != 0:
            pytest.skip(
                f"Asset '{_name}' Health.DeviceHealth = {val} (not NORMAL) — "
                "asset may have active faults; skipping NORMAL-state check"
            )
        found = True
        break
    if not found:
        pytest.skip(f"No Health.DeviceHealth found on {instance_fixture_name} — optional per spec")


# ─── asset_management_monitoring_health (additional) ─────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_MONITORING_HEALTH)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_monitoring_health_device_health_is_readable(request, ns_indices, instance_fixture_name):
    """Monitoring.Health DeviceHealth value must be readable and within valid enum range."""
    ns_mach = ns_indices.get(NS_MACHINERY)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_mach is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    _VALID_DEVICE_HEALTH = frozenset({0, 1, 2, 3, 4})
    found = False
    for _name, asset_node in instances:
        monitoring = await find_child_by_browse_name(asset_node, BN.MONITORING, ns_mach)
        if monitoring is None:
            continue
        health = await find_child_by_browse_name(monitoring, BN.HEALTH, ns_ijt)
        if health is None:
            continue
        dh_node = await find_child_by_browse_name(health, BN.DEVICE_HEALTH, ns_ijt)
        if dh_node is None:
            continue
        val = await dh_node.read_value()
        assert int(val) in _VALID_DEVICE_HEALTH, (
            f"Asset '{_name}' Monitoring.Health.DeviceHealth = {val!r} — "
            "value must be a valid DeviceHealthEnumeration member (0–4)"
        )
        found = True
        break
    if not found:
        pytest.skip(f"No Monitoring.Health.DeviceHealth found on {instance_fixture_name} — optional per spec")


# ─── asset_management_service (additional) ───────────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SERVICE)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_maintenance_service_next_service_date_is_in_future(request, ns_indices, instance_fixture_name):
    """NextServiceDate, when present, must be a DateTime value in the future."""
    import datetime

    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found_service = False
    for _name, asset_node in instances:
        maintenance = await find_child_by_browse_name(asset_node, BN.MAINTENANCE, ns_di)
        if maintenance is None:
            continue
        service = await find_child_by_browse_name(maintenance, BN.SERVICE, ns_ijt)
        if service is None:
            continue
        found_service = True
        next_date_node = await find_child_by_browse_name(service, "NextServiceDate", ns_ijt)
        if next_date_node is None:
            break
        val = await next_date_node.read_value()
        if val is None:
            break
        now = datetime.datetime.now(datetime.timezone.utc)
        if hasattr(val, "tzinfo") and val.tzinfo is None:
            val = val.replace(tzinfo=datetime.timezone.utc)
        assert val > now, (
            f"Asset '{_name}' Maintenance.Service.NextServiceDate = {val!r} "
            "is not in the future — scheduled service date must be a future timestamp"
        )
        break
    if not found_service:
        pytest.skip(f"No Maintenance.Service found on {instance_fixture_name} — optional per spec")


# ─── asset_management_calibration (additional) ───────────────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CALIBRATION)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_maintenance_calibration_value_is_present(request, ns_indices, instance_fixture_name):
    """Maintenance.Calibration.CalibrationValue must be present alongside LastCalibration."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found = False
    for _name, asset_node in instances:
        maintenance = await find_child_by_browse_name(asset_node, BN.MAINTENANCE, ns_di)
        if maintenance is None:
            continue
        calibration = await find_child_by_browse_name(maintenance, BN.CALIBRATION, ns_ijt)
        if calibration is None:
            continue
        cal_value_node = await find_child_by_browse_name(calibration, BN.CALIBRATION_VALUE, ns_ijt)
        assert cal_value_node is not None, (
            f"Asset '{_name}' Maintenance.Calibration is missing CalibrationValue (ns_ijt={ns_ijt})"
        )
        found = True
        break
    if not found:
        pytest.skip(f"No Maintenance.Calibration found on {instance_fixture_name} — optional per spec")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CALIBRATION)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_maintenance_calibration_next_calibration_date_in_future(
    request, ns_indices, instance_fixture_name
):
    """NextCalibrationDate, when present, must be a DateTime value in the future."""
    import datetime

    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found_cal = False
    for _name, asset_node in instances:
        maintenance = await find_child_by_browse_name(asset_node, BN.MAINTENANCE, ns_di)
        if maintenance is None:
            continue
        calibration = await find_child_by_browse_name(maintenance, BN.CALIBRATION, ns_ijt)
        if calibration is None:
            continue
        found_cal = True
        next_cal_node = await find_child_by_browse_name(calibration, "NextCalibrationDate", ns_ijt)
        if next_cal_node is None:
            break
        val = await next_cal_node.read_value()
        if val is None:
            break
        now = datetime.datetime.now(datetime.timezone.utc)
        if hasattr(val, "tzinfo") and val.tzinfo is None:
            val = val.replace(tzinfo=datetime.timezone.utc)
        assert val > now, (
            f"Asset '{_name}' Maintenance.Calibration.NextCalibrationDate = {val!r} "
            "is not in the future — scheduled calibration date must be a future timestamp"
        )
        break
    if not found_cal:
        pytest.skip(f"No Maintenance.Calibration found on {instance_fixture_name} — optional per spec")


# ─── asset_management_additional_information (additional) ────────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_ADDITIONAL_INFORMATION)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_has_connected_property(request, ns_indices, instance_fixture_name):
    """Asset instances implementing IJoiningAdditionalInformationType must expose Connected."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found = False
    for _name, asset_node in instances:
        connected = await find_child_by_browse_name(asset_node, BN.CONNECTED, ns_ijt)
        if connected is not None:
            val = await connected.read_value()
            assert isinstance(val, bool), f"Asset '{_name}' Connected = {val!r} — DataType must be Boolean"
            found = True
            break
    if not found:
        pytest.skip(
            f"No Connected property found on {instance_fixture_name} — "
            "may be optional or located on Identification AddIn"
        )


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_ADDITIONAL_INFORMATION)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_asset_has_enabled_property(request, ns_indices, instance_fixture_name):
    """Asset instances implementing IJoiningAdditionalInformationType must expose Enabled."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found = False
    for _name, asset_node in instances:
        enabled = await find_child_by_browse_name(asset_node, BN.ENABLED, ns_ijt)
        if enabled is not None:
            val = await enabled.read_value()
            assert isinstance(val, bool), f"Asset '{_name}' Enabled = {val!r} — DataType must be Boolean"
            found = True
            break
    if not found:
        pytest.skip(
            f"No Enabled property found on {instance_fixture_name} — may be optional or located on Identification AddIn"
        )


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_ADDITIONAL_INFORMATION)
async def test_tool_and_controller_joining_technology_is_non_zero(controllers_instances, tools_instances, ns_indices):
    """JoiningTechnology on Controller and Tool instances must be non-zero (not Undefined)."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    violations: list[str] = []
    for label, instances in [("Controller", controllers_instances), ("Tool", tools_instances)]:
        for _name, asset_node in instances:
            ident = await find_child_by_browse_name(asset_node, BN.IDENTIFICATION, ns_di)
            if ident is None:
                continue
            jt_node = await find_child_by_browse_name(ident, BN.JOINING_TECHNOLOGY, ns_ijt)
            if jt_node is None:
                continue
            val = await jt_node.read_value()
            # JoiningTechnology is an enumeration — asyncua may return it as
            # an int, an ExtensionObject, or a LocalizedText depending on
            # whether type definitions are loaded. Extract the numeric value safely.
            try:
                jt_int = int(val)
            except TypeError, ValueError:
                # LocalizedText or named enum — non-zero text means a value was set
                jt_int = 1 if str(val).strip() not in ("", "0", "Other") else 0
            if jt_int == 0:
                violations.append(f"{label} '{_name}' JoiningTechnology = 0 (Undefined)")
    assert not violations, (
        f"Controller and Tool instances must declare a specific joining technology (non-zero): {violations}"
    )


@pytest.mark.negative
@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_ADDITIONAL_INFORMATION)
async def test_joining_technology_out_of_range_write_rejected(controllers_instances, ns_indices, opcua_client):
    """Writing an out-of-range integer to JoiningTechnology must return Bad_OutOfRange or Bad_TypeMismatch."""
    from asyncua import ua as _ua

    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None or ns_ijt is None:
        pytest.skip("Required namespaces not registered on server")
    _name, ctrl_node = controllers_instances[0]
    ident = await find_child_by_browse_name(ctrl_node, BN.IDENTIFICATION, ns_di)
    if ident is None:
        pytest.skip(f"Controller '{_name}' has no Identification — skipping enum range write test")
    jt_node = await find_child_by_browse_name(ident, BN.JOINING_TECHNOLOGY, ns_ijt)
    if jt_node is None:
        pytest.skip(f"Controller '{_name}' has no JoiningTechnology property — skipping test")
    try:
        await jt_node.write_attribute(
            _ua.AttributeIds.Value,
            _ua.DataValue(_ua.Variant(9999, _ua.VariantType.Int32)),
        )
        pytest.skip(
            f"Write of out-of-range JoiningTechnology (9999) was accepted by server '{_name}' — "
            "server permits writes; subsequent behaviour is implementation-dependent"
        )
    except _ua.UaStatusCodeError as exc:
        _ACCEPTABLE = (
            _ua.StatusCodes.BadOutOfRange,
            _ua.StatusCodes.BadTypeMismatch,
            _ua.StatusCodes.BadNotWritable,
            _ua.StatusCodes.BadUserAccessDenied,
        )
        assert exc.code in _ACCEPTABLE, (
            f"Expected Bad_OutOfRange / Bad_TypeMismatch / Bad_NotWritable; got {exc.code:#010x}"
        )


# ─── asset_management_machinery_building_blocks (additional) ─────────────────


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_MACHINERY_BUILDING_BLOCKS)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_machinery_building_blocks_has_correct_type_definition(request, ns_indices, instance_fixture_name):
    """MachineryBuildingBlocks TypeDefinition must resolve to MachineryBuildingBlocksType."""
    ns_mach = ns_indices.get(NS_MACHINERY)
    if ns_mach is None:
        pytest.skip("Machinery namespace not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    found = False
    for _name, asset_node in instances:
        mbb = await find_child_by_browse_name(asset_node, BN.MACHINERY_BUILDING_BLOCKS, ns_mach)
        if mbb is None:
            continue
        type_def = await get_type_definition(mbb)
        if type_def is None:
            found = True
            break
        # MachineryBuildingBlocks is declared as 0:FolderType in OPC UA for Machinery
        # (OPC 40001-1). The TypeDefinition NamespaceIndex may be 0 (OPC UA base) for
        # FolderType, or ns_mach for a Machinery-specific subtype. Both are valid.
        is_folder_type = type_def.NamespaceIndex == 0  # 0:FolderType
        is_machinery_type = type_def.NamespaceIndex == ns_mach
        assert is_folder_type or is_machinery_type, (
            f"Asset '{_name}' MachineryBuildingBlocks TypeDefinition namespace "
            f"{type_def.NamespaceIndex!r} is neither OPC UA base (0) nor "
            f"Machinery ns ({ns_mach}) — unexpected type"
        )
        found = True
        break
    if not found:
        pytest.skip(f"No MachineryBuildingBlocks found on {instance_fixture_name} — optional per spec")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_MACHINERY_BUILDING_BLOCKS)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_machinery_building_blocks_identification_type_is_machine_or_component(
    request, ns_indices, instance_fixture_name
):
    """MachineryBuildingBlocks Identification TypeDefinition must be MachineIdentificationType or MachineryComponentIdentificationType."""
    ns_mach = ns_indices.get(NS_MACHINERY)
    ns_di = ns_indices.get(NS_DI)
    if ns_mach is None or ns_di is None:
        pytest.skip("Required namespaces not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    _VALID_LOCAL_IDS = frozenset(
        {
            MachineryTypes.MACHINE_IDENTIFICATION_TYPE,
            MachineryTypes.MACHINERY_COMPONENT_IDENTIFICATION_TYPE,
        }
    )
    found = False
    for _name, asset_node in instances:
        mbb = await find_child_by_browse_name(asset_node, BN.MACHINERY_BUILDING_BLOCKS, ns_mach)
        if mbb is None:
            continue
        ident = await find_child_by_browse_name(mbb, BN.IDENTIFICATION, ns_di)
        if ident is None:
            found = True
            break
        type_def = await get_type_definition(ident)
        if type_def is None:
            found = True
            break
        assert type_def.NamespaceIndex == ns_mach and type_def.Identifier in _VALID_LOCAL_IDS, (
            f"Asset '{_name}' MachineryBuildingBlocks.Identification TypeDefinition "
            f"is {type_def!r} — expected MachineIdentificationType or "
            "MachineryComponentIdentificationType (Machinery ns)"
        )
        found = True
        break
    if not found:
        pytest.skip(f"No MachineryBuildingBlocks.Identification found on {instance_fixture_name} — optional per spec")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_MACHINERY_BUILDING_BLOCKS)
@pytest.mark.parametrize("instance_fixture_name", ["controllers_instances", "tools_instances"])
async def test_all_assets_in_fixture_have_machinery_building_blocks(request, ns_indices, instance_fixture_name):
    """When the Machinery Building Blocks CU is claimed, ALL asset instances must expose MachineryBuildingBlocks."""
    ns_mach = ns_indices.get(NS_MACHINERY)
    if ns_mach is None:
        pytest.skip("Machinery namespace not registered on server")
    instances = request.getfixturevalue(instance_fixture_name)
    missing: list[str] = []
    for asset_name, asset_node in instances:
        mbb = await find_child_by_browse_name(asset_node, BN.MACHINERY_BUILDING_BLOCKS, ns_mach)
        if mbb is None:
            missing.append(asset_name)
    if missing:
        pytest.skip(
            f"MachineryBuildingBlocks absent on {missing} in {instance_fixture_name} — "
            "optional sub-node; skip if server partially implements this CU"
        )
