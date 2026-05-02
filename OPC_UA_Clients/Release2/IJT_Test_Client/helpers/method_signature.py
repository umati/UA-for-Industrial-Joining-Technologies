"""
Runtime helpers for validating OPC UA method signatures.

The IJT test client exercises methods from several companion namespaces. These
helpers read the method node's standard InputArguments property so conformance
tests can assert the current NodeSet signature before invoking a method.
"""

from __future__ import annotations

from asyncua import ua

from helpers.node_discovery import find_child_by_browse_name


async def read_input_argument_names(method_node, ns_opcua: int = 0, timeout: float = 15.0) -> list[str]:
    """Return InputArguments names for *method_node*, or an empty list when absent."""
    input_args_node = await find_child_by_browse_name(method_node, "InputArguments", ns_opcua, timeout=timeout)
    if input_args_node is None:
        return []
    try:
        args = await input_args_node.read_value()
    except ua.UaError:
        return []
    if args is None:
        return []
    return [str(getattr(arg, "Name", "")) for arg in args]


async def assert_input_argument_names(
    method_node,
    expected_names: tuple[str, ...],
    *,
    ns_opcua: int = 0,
    method_name: str = "",
    timeout: float = 15.0,
) -> None:
    """Assert that a method's InputArguments match the expected current NodeSet names."""
    actual = await read_input_argument_names(method_node, ns_opcua=ns_opcua, timeout=timeout)
    assert actual == list(expected_names), (
        f"{method_name or 'method'} InputArguments mismatch: expected {list(expected_names)!r}, got {actual!r}"
    )


ASSET_METHOD_INPUTS: dict[str, tuple[str, ...]] = {
    "EnableAsset": ("ProductInstanceUri", "Enable"),
    "DisconnectAsset": ("ProductInstanceUri", "Disconnect"),
    "SetCalibration": ("ProductInstanceUri", "CalibrationData"),
    "RebootAsset": ("ProductInstanceUri",),
    "GetErrorInformation": ("ProductInstanceUri", "ErrorId"),
    "ExecuteOperation": ("ProductInstanceUri", "OperationType", "OperationText", "VendorName"),
}

ASSET_MANAGEMENT_METHOD_INPUTS: dict[str, tuple[str, ...]] = {
    "GetIdentifiers": ("ProductInstanceUri", "IdentifierNames"),
    "SendIdentifiers": ("ProductInstanceUri", "EntityList"),
    "SendTextIdentifiers": ("ProductInstanceUri", "IdentifierList"),
    "ResetIdentifiers": ("ProductInstanceUri", "IdentifierList", "ResetAll", "ResetLatest"),
    "GetFeedbackFileList": ("ProductInstanceUri",),
    "SendFeedback": ("ProductInstanceUri", "FeedbackType", "FeedbackText", "FeedbackFile"),
    "SetTime": ("ProductInstanceUri", "InputTime"),
    "SetOfflineTimer": ("ProductInstanceUri", "OfflineTimer"),
    "GetIOSignals": ("ProductInstanceUri", "SignalIdList"),
    "SetIOSignals": ("ProductInstanceUri", "SignalList"),
}

JOINING_PROCESS_METHOD_INPUTS: dict[str, tuple[str, ...]] = {
    "GetJoiningProcessList": ("ProductInstanceUri",),
    "GetSelectedJoiningProgram": ("ProductInstanceUri",),
    "SelectJoiningProcess": ("ProductInstanceUri", "JoiningProcessIdentification"),
    "StartSelectedJoining": ("ProductInstanceUri", "DeselectAfterJoining"),
    "DeselectJoiningProcess": ("ProductInstanceUri",),
    "StartJoiningProcess": ("ProductInstanceUri", "JoiningProcessIdentification", "AssociatedEntities"),
    "AbortJoiningProcess": ("ProductInstanceUri", "JoiningProcessIdentification", "AbortMessage"),
    "ResetJoiningProcess": ("ProductInstanceUri", "JoiningProcessIdentification"),
    "IncrementJoiningProcessCounter": ("ProductInstanceUri", "JoiningProcessIdentification", "IncrementCount"),
    "DecrementJoiningProcessCounter": ("ProductInstanceUri", "JoiningProcessIdentification", "DecrementCount"),
    "SetJoiningProcessSize": ("ProductInstanceUri", "JoiningProcessIdentification", "MaxCounterSize"),
    "SetJoiningProcessCounter": ("ProductInstanceUri", "JoiningProcessIdentification", "CounterValue"),
    "SetJoiningProcessMapping": ("ProductInstanceUri", "JoiningProcessIdentification"),
    "DeleteJoiningProcess": ("ProductInstanceUri", "JoiningProcessIdentification"),
    "GetJoiningProcess": ("ProductInstanceUri", "JoiningProcessId"),
    "GetJoiningProcessRevisionList": ("ProductInstanceUri", "JoiningProcessOriginId"),
    "SendJoiningProcess": ("ProductInstanceUri", "JoiningProcess", "SelectionName"),
}

JOINT_METHOD_INPUTS: dict[str, tuple[str, ...]] = {
    "GetJoint": ("ProductInstanceUri", "JointId"),
    "GetJointList": ("ProductInstanceUri",),
    "SelectJoint": ("ProductInstanceUri", "JointId", "JointOriginId"),
    "DeleteJoint": ("ProductInstanceUri", "JointId", "JointOriginId"),
    "SendJoint": ("ProductInstanceUri", "Joint"),
    "SendJointDesign": ("ProductInstanceUri", "JointDesign"),
    "GetJointDesign": ("ProductInstanceUri", "JointDesignId"),
    "DeleteJointDesign": ("ProductInstanceUri", "JointDesignId"),
    "SendJointComponent": ("ProductInstanceUri", "JointComponent"),
    "GetJointComponent": ("ProductInstanceUri", "JointComponentId"),
    "DeleteJointComponent": ("ProductInstanceUri", "JointComponentId"),
    "GetJointDesignList": ("ProductInstanceUri",),
    "GetJointComponentList": ("ProductInstanceUri",),
    "GetJointRevisionList": ("ProductInstanceUri", "JointOriginId"),
}
