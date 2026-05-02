"""
Unit tests for helpers/namespaces.py

Tests namespace URI constants, enum values, and type NodeId classes.
No OPC UA server required.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

# Legacy aliases
from helpers.namespaces import (
    ALL_NAMESPACE_URIS,
    BN,
    NS_AMB,
    NS_AMB_URI,
    NS_APP,
    NS_APP_URI,
    NS_DI,
    NS_DI_URI,
    NS_IA,
    NS_IA_URI,
    NS_IJT_BASE,
    NS_IJT_BASE_URI,
    NS_IJT_TIGHTENING,
    NS_IJT_TIGHTENING_URI,
    NS_MACH_RESULT,
    NS_MACH_RESULT_URI,
    NS_MACHINERY,
    NS_MACHINERY_URI,
    NS_OPC_UA,
    NS_OPC_UA_URI,
    DITypes,
    IJTTighteningTypes,
    IJTTypes,
    MachineryResultTypes,
    MachineryTypes,
    NsIndices,
    RefTypes,
    ResultClassification,
    ResultEvaluation,
    ResultType,
    SimulateEventType,
)

# ---------------------------------------------------------------------------
# Namespace URI constants
# ---------------------------------------------------------------------------


class TestNamespaceURIs:
    def test_all_uris_are_non_empty_strings(self):
        uris = [
            NS_OPC_UA,
            NS_DI,
            NS_AMB,
            NS_IA,
            NS_MACHINERY,
            NS_MACH_RESULT,
            NS_IJT_BASE,
            NS_IJT_TIGHTENING,
            NS_APP,
        ]
        for uri in uris:
            assert isinstance(uri, str) and uri, f"URI {uri!r} is empty or not a string"

    def test_uris_start_with_http_or_urn(self):
        uris = [
            NS_OPC_UA,
            NS_DI,
            NS_AMB,
            NS_IA,
            NS_MACHINERY,
            NS_MACH_RESULT,
            NS_IJT_BASE,
            NS_IJT_TIGHTENING,
            NS_APP,
        ]
        for uri in uris:
            assert uri.startswith("http://") or uri.startswith("urn:"), (
                f"URI {uri!r} does not start with http:// or urn:"
            )

    def test_ns_opc_ua_value(self):
        assert NS_OPC_UA == "http://opcfoundation.org/UA/"

    def test_ns_di_value(self):
        assert NS_DI == "http://opcfoundation.org/UA/DI/"

    def test_ns_machinery_value(self):
        assert NS_MACHINERY == "http://opcfoundation.org/UA/Machinery/"

    def test_ns_ijt_base_value(self):
        assert NS_IJT_BASE == "http://opcfoundation.org/UA/IJT/Base/"

    def test_ns_app_starts_with_urn(self):
        assert NS_APP.startswith("urn:")


# ---------------------------------------------------------------------------
# ALL_NAMESPACE_URIS
# ---------------------------------------------------------------------------


class TestAllNamespaceUris:
    def test_is_a_list(self):
        assert isinstance(ALL_NAMESPACE_URIS, list)

    def test_contains_exactly_9_uris(self):
        assert len(ALL_NAMESPACE_URIS) == 9

    def test_contains_all_expected_uris(self):
        expected = {
            NS_OPC_UA,
            NS_DI,
            NS_AMB,
            NS_IA,
            NS_MACHINERY,
            NS_MACH_RESULT,
            NS_IJT_BASE,
            NS_IJT_TIGHTENING,
            NS_APP,
        }
        assert set(ALL_NAMESPACE_URIS) == expected

    def test_no_duplicates(self):
        assert len(ALL_NAMESPACE_URIS) == len(set(ALL_NAMESPACE_URIS))


# ---------------------------------------------------------------------------
# Legacy aliases
# ---------------------------------------------------------------------------


class TestLegacyAliases:
    def test_ns_opc_ua_uri_equals_ns_opc_ua(self):
        assert NS_OPC_UA_URI == NS_OPC_UA

    def test_ns_di_uri_equals_ns_di(self):
        assert NS_DI_URI == NS_DI

    def test_ns_amb_uri_equals_ns_amb(self):
        assert NS_AMB_URI == NS_AMB

    def test_ns_ia_uri_equals_ns_ia(self):
        assert NS_IA_URI == NS_IA

    def test_ns_machinery_uri_equals_ns_machinery(self):
        assert NS_MACHINERY_URI == NS_MACHINERY

    def test_ns_mach_result_uri_equals_ns_mach_result(self):
        assert NS_MACH_RESULT_URI == NS_MACH_RESULT

    def test_ns_ijt_base_uri_equals_ns_ijt_base(self):
        assert NS_IJT_BASE_URI == NS_IJT_BASE

    def test_ns_ijt_tightening_uri_equals_ns_ijt_tightening(self):
        assert NS_IJT_TIGHTENING_URI == NS_IJT_TIGHTENING

    def test_ns_app_uri_equals_ns_app(self):
        assert NS_APP_URI == NS_APP


# ---------------------------------------------------------------------------
# RefTypes
# ---------------------------------------------------------------------------


class TestRefTypes:
    def test_all_values_are_positive_integers(self):
        import inspect

        for name, value in inspect.getmembers(RefTypes):
            if not name.startswith("_") and isinstance(value, int):
                assert value > 0, f"RefTypes.{name} = {value} is not positive"

    def test_has_has_component(self):
        assert RefTypes.HAS_COMPONENT == 47

    def test_has_has_property(self):
        assert RefTypes.HAS_PROPERTY == 46

    def test_has_has_type_definition(self):
        assert RefTypes.HAS_TYPE_DEFINITION == 40

    def test_has_organizes(self):
        assert RefTypes.ORGANIZES == 35

    def test_has_has_interface(self):
        assert RefTypes.HAS_INTERFACE == 17603

    def test_has_has_add_in(self):
        assert RefTypes.HAS_ADD_IN == 17604

    def test_has_associated_with(self):
        assert RefTypes.ASSOCIATED_WITH == 24137

    def test_has_has_subtype(self):
        assert RefTypes.HAS_SUBTYPE == 45

    def test_has_generates_event(self):
        assert RefTypes.GENERATES_EVENT == 41


# ---------------------------------------------------------------------------
# BN class (BrowseName string constants)
# ---------------------------------------------------------------------------


class TestBNClass:
    def test_identification_is_non_empty(self):
        assert BN.IDENTIFICATION == "Identification"

    def test_method_set_is_non_empty(self):
        assert BN.METHOD_SET == "MethodSet"

    def test_result_management_is_non_empty(self):
        assert BN.RESULT_MANAGEMENT == "ResultManagement"

    def test_asset_id_is_correct(self):
        assert BN.ASSET_ID == "AssetId"

    def test_serial_number_is_correct(self):
        assert BN.SERIAL_NUMBER == "SerialNumber"

    def test_all_asset_folders_is_list(self):
        assert isinstance(BN.ALL_ASSET_FOLDERS, list)
        assert len(BN.ALL_ASSET_FOLDERS) > 0

    def test_all_asset_folders_non_empty_strings(self):
        for folder in BN.ALL_ASSET_FOLDERS:
            assert isinstance(folder, str) and folder

    def test_all_asset_management_methods_is_list(self):
        assert isinstance(BN.ALL_ASSET_MANAGEMENT_METHODS, list)

    def test_all_simulate_methods_is_list(self):
        assert isinstance(BN.ALL_SIMULATE_METHODS, list)

    def test_simulate_single_result(self):
        assert BN.SIMULATE_SINGLE_RESULT == "SimulateSingleResult"

    def test_result_id(self):
        assert BN.RESULT_ID == "ResultId"

    def test_classification(self):
        assert BN.CLASSIFICATION == "Classification"

    def test_joining_technology(self):
        assert BN.JOINING_TECHNOLOGY == "JoiningTechnology"

    def test_all_joining_process_methods_is_list(self):
        assert isinstance(BN.ALL_JOINING_PROCESS_METHODS, list)

    def test_all_joint_methods_is_list(self):
        assert isinstance(BN.ALL_JOINT_METHODS, list)

    def test_string_constants_are_non_empty(self):
        import inspect

        for name, value in inspect.getmembers(BN):
            if not name.startswith("_") and isinstance(value, str):
                assert value, f"BN.{name} is empty"


# ---------------------------------------------------------------------------
# ResultClassification
# ---------------------------------------------------------------------------


class TestResultClassification:
    def test_valid_values_is_set(self):
        assert isinstance(ResultClassification.VALID_VALUES, set)

    def test_valid_values_contains_expected(self):
        assert ResultClassification.VALID_VALUES == {0, 1, 2, 3, 4, 5, 6, 7}

    def test_named_constants_in_valid_values(self):
        assert ResultClassification.UNDEFINED in ResultClassification.VALID_VALUES
        assert ResultClassification.SINGLE_RESULT in ResultClassification.VALID_VALUES
        assert ResultClassification.SYNC_RESULT in ResultClassification.VALID_VALUES
        assert ResultClassification.BATCH_RESULT in ResultClassification.VALID_VALUES
        assert ResultClassification.JOB_RESULT in ResultClassification.VALID_VALUES
        assert ResultClassification.STITCHING_RESULT in ResultClassification.VALID_VALUES
        assert ResultClassification.INTERVENTION_RESULT in ResultClassification.VALID_VALUES
        assert ResultClassification.TEXT_RESULT in ResultClassification.VALID_VALUES

    def test_undefined_is_zero(self):
        assert ResultClassification.UNDEFINED == 0

    def test_single_result_is_one(self):
        assert ResultClassification.SINGLE_RESULT == 1

    def test_text_result_is_seven(self):
        assert ResultClassification.TEXT_RESULT == 7


# ---------------------------------------------------------------------------
# ResultEvaluation
# ---------------------------------------------------------------------------


class TestResultEvaluation:
    def test_valid_values_is_set(self):
        assert isinstance(ResultEvaluation.VALID_VALUES, set)

    def test_valid_values_contains_expected(self):
        assert ResultEvaluation.VALID_VALUES == {0, 1, 2, 3}

    def test_undefined_is_zero(self):
        assert ResultEvaluation.UNDEFINED == 0

    def test_ok_is_one(self):
        assert ResultEvaluation.OK == 1

    def test_nok_is_two(self):
        assert ResultEvaluation.NOK == 2

    def test_not_decidable_is_three(self):
        assert ResultEvaluation.NOT_DECIDABLE == 3

    def test_named_constants_in_valid_values(self):
        assert ResultEvaluation.UNDEFINED in ResultEvaluation.VALID_VALUES
        assert ResultEvaluation.OK in ResultEvaluation.VALID_VALUES
        assert ResultEvaluation.NOK in ResultEvaluation.VALID_VALUES
        assert ResultEvaluation.NOT_DECIDABLE in ResultEvaluation.VALID_VALUES


# ---------------------------------------------------------------------------
# IJTTypes
# ---------------------------------------------------------------------------


class TestIJTTypes:
    def test_joining_system_type(self):
        assert IJTTypes.JOINING_SYSTEM_TYPE == 1005

    def test_joining_system_event_type(self):
        assert IJTTypes.JOINING_SYSTEM_EVENT_TYPE == 1006

    def test_joining_system_result_ready_event_type(self):
        assert IJTTypes.JOINING_SYSTEM_RESULT_READY_EVENT_TYPE == 1007

    def test_joining_system_condition_type(self):
        assert IJTTypes.JOINING_SYSTEM_CONDITION_TYPE == 1020

    def test_all_type_ids_are_positive_integers(self):
        import inspect

        for name, value in inspect.getmembers(IJTTypes):
            if not name.startswith("_") and isinstance(value, int):
                assert value > 0, f"IJTTypes.{name} = {value} is not positive"


# ---------------------------------------------------------------------------
# MachineryTypes
# ---------------------------------------------------------------------------


class TestMachineryTypes:
    def test_has_machinery_operation_counter_type(self):
        assert MachineryTypes.MACHINERY_OPERATION_COUNTER_TYPE == 1009

    def test_has_machine_identification_type(self):
        assert MachineryTypes.MACHINE_IDENTIFICATION_TYPE == 1012


# ---------------------------------------------------------------------------
# MachineryResultTypes
# ---------------------------------------------------------------------------


class TestMachineryResultTypes:
    def test_has_result_management_type(self):
        assert MachineryResultTypes.RESULT_MANAGEMENT_TYPE == 1004

    def test_has_result_ready_event_type(self):
        assert MachineryResultTypes.RESULT_READY_EVENT_TYPE == 1002


# ---------------------------------------------------------------------------
# ResultType
# ---------------------------------------------------------------------------


class TestResultType:
    def test_simple_ok_result(self):
        assert ResultType.SIMPLE_OK_RESULT == 0

    def test_one_step_ok_result(self):
        assert ResultType.ONE_STEP_OK_RESULT == 1

    def test_all_basic_is_list(self):
        assert isinstance(ResultType.ALL_BASIC, list)
        assert 0 in ResultType.ALL_BASIC

    def test_multi_step_is_list(self):
        assert isinstance(ResultType.MULTI_STEP, list)
        assert 2 in ResultType.MULTI_STEP

    def test_empty_single_result(self):
        assert ResultType.EMPTY_SINGLE_RESULT == 7


# ---------------------------------------------------------------------------
# DITypes
# ---------------------------------------------------------------------------


class TestDITypes:
    def test_device_type(self):
        assert DITypes.DEVICE_TYPE == 1002

    def test_functional_group_type(self):
        assert DITypes.FUNCTIONAL_GROUP_TYPE == 1005


# ---------------------------------------------------------------------------
# SimulateEventType
# ---------------------------------------------------------------------------


class TestSimulateEventType:
    def test_tool_connected(self):
        assert SimulateEventType.TOOL_CONNECTED == 1

    def test_tool_disconnected(self):
        assert SimulateEventType.TOOL_DISCONNECTED == 2

    def test_all_values_are_positive_integers(self):
        import inspect

        for name, value in inspect.getmembers(SimulateEventType):
            if not name.startswith("_") and isinstance(value, int):
                assert value > 0, f"SimulateEventType.{name} = {value} is not positive"


# ---------------------------------------------------------------------------
# NsIndices (legacy class)
# ---------------------------------------------------------------------------


class TestNsIndices:
    def test_init_defaults(self):
        ns = NsIndices()
        assert ns.opc_ua == -1  # resolved dynamically — starts at -1
        assert ns.di == 0
        assert ns.amb == 0
        assert ns.ia == 0
        assert ns.machinery == 0
        assert ns.mach_result == 0
        assert ns.ijt_base == 0
        assert ns.ijt_tightening == 0
        assert ns.app == 0

    def test_attributes_can_be_set(self):
        ns = NsIndices()
        ns.di = 2
        assert ns.di == 2

    def test_has_all_expected_slots(self):
        expected = {"opc_ua", "di", "amb", "ia", "machinery", "mach_result", "ijt_base", "ijt_tightening", "app"}
        assert set(NsIndices.__slots__) == expected


# ---------------------------------------------------------------------------
# IJTTighteningTypes
# ---------------------------------------------------------------------------


class TestIJTTighteningTypes:
    def test_itightening_tool_parameters_type(self):
        assert IJTTighteningTypes.ITIGHTENING_TOOL_PARAMETERS_TYPE == 1003


# ---------------------------------------------------------------------------
# NsIndices.resolve_all
# ---------------------------------------------------------------------------


class TestNsIndicesResolveAll:
    @pytest.mark.asyncio
    async def test_resolve_all_populates_all_slots(self):
        """resolve_all() must call get_namespace_index once per namespace and
        store the result in the corresponding slot."""
        ns = NsIndices()
        client = MagicMock()
        client.get_namespace_index = AsyncMock(side_effect=range(1, 10))
        await ns.resolve_all(client)
        assert ns.opc_ua == 1
        assert ns.di == 2
        assert ns.amb == 3
        assert ns.ia == 4
        assert ns.machinery == 5
        assert ns.mach_result == 6
        assert ns.ijt_base == 7
        assert ns.ijt_tightening == 8
        assert ns.app == 9
        assert client.get_namespace_index.await_count == 9
