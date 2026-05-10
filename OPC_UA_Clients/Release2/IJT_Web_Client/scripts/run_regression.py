#!/usr/bin/env python3
import argparse
import asyncio
import contextlib
import errno
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from venv_bootstrap import ensure_regression_env, is_current_interpreter

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _ensure_test_interpreter_and_relaunch() -> Path:
    test_python = ensure_regression_env(PROJECT_ROOT)
    if not is_current_interpreter(test_python):
        cmd = [str(test_python), str(Path(__file__).resolve()), *sys.argv[1:]]
        raise SystemExit(subprocess.call(cmd, cwd=str(PROJECT_ROOT)))
    return test_python


_ = _ensure_test_interpreter_and_relaunch()

import websockets
from asyncua import Client, ua

warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"asyncua\..*")
logging.getLogger("asyncua").setLevel(logging.ERROR)
logging.getLogger("asyncua.client.ua_client").setLevel(logging.CRITICAL)


@dataclass
class MethodSpec:
    name: str
    object_node: dict[str, Any]
    method_node: dict[str, Any]
    arguments: list[dict[str, Any]]


CANONICAL_METHOD_ALIASES: dict[str, list[str]] = {
    "SimulateSingleResult": ["SimulateSingleResult"],
    "SimulateJobResult": ["SimulateJobResult"],
    "Simulate_Batch_or_SYNC_Result": [
        "Simulate_Batch_or_SYNC_Result",
        "SimulateBatch_Or_Sync_Result",
        "SimulateBatchOrSyncResult",
    ],
    "SimulateEvents": ["SimualteEvents", "SimulateEvents"],
    "GetJointList": ["GetJointList"],
    "SelectJoint": ["SelectJoint"],
    "StartSelectedJoining": ["StartSelectedJoining"],
}

PRODUCT_ID_OVERRIDE = os.getenv("REGRESSION_PRODUCT_ID")
DEFAULT_PRODUCT_ID = PRODUCT_ID_OVERRIDE or "www.atlascopco.com/CABLE-B0000000-"
JOINT_1_OVERRIDE = os.getenv("REGRESSION_JOINT_1")
JOINT_2_OVERRIDE = os.getenv("REGRESSION_JOINT_2")


def nodeid_to_payload(nodeid: ua.NodeId) -> dict[str, Any]:
    return {
        "NamespaceIndex": int(nodeid.NamespaceIndex),
        "Identifier": nodeid.Identifier,
    }


def default_arg_value(dtype_identifier: int) -> Any:
    mapping = {
        1: True,  # Boolean
        2: 1,  # SByte
        3: 1,  # Byte
        4: 1,  # Int16
        5: 1,  # UInt16
        6: 1,  # Int32
        7: 1,  # UInt32
        8: 1,  # Int64
        9: 1,  # UInt64
        10: 1.0,  # Float
        11: 1.0,  # Double
        12: "1",  # String
        13: "2026-01-01T00:00:00Z",  # DateTime (string fallback)
        31918: "1",  # TrimmedString
    }
    return mapping.get(dtype_identifier, "1")


def _target_method_names() -> set[str]:
    names: set[str] = set()
    for aliases in CANONICAL_METHOD_ALIASES.values():
        names.update(aliases)
    return names


def _build_method_arguments(method_name: str, default_arguments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Joint demo flow methods need explicit argument payloads.
    if method_name == "GetJointList":
        return [
            {
                "value": DEFAULT_PRODUCT_ID,
                "dataType": 12,  # String NodeId fallback used by current backend mapper
            },
        ]
    if method_name == "SelectJoint":
        return [
            {
                "value": DEFAULT_PRODUCT_ID,
                "dataType": 12,  # String NodeId fallback used by current backend mapper
            },
            {
                "value": JOINT_1_OVERRIDE or "",
                "dataType": 31918,  # TrimmedString
            },
            {
                "value": "",
                "dataType": 31918,
            },
        ]
    if method_name == "StartSelectedJoining":
        return [
            {
                "value": DEFAULT_PRODUCT_ID,
                "dataType": 12,  # String NodeId fallback used by current backend mapper
            },
            {
                "value": False,
                "dataType": 1,  # Boolean
            },
        ]

    arguments = [dict(arg) for arg in default_arguments]
    return arguments


def _pick_method_for_alias(methods_by_name: dict[str, MethodSpec], canonical_name: str) -> MethodSpec | None:
    for alias in CANONICAL_METHOD_ALIASES[canonical_name]:
        if alias in methods_by_name:
            return methods_by_name[alias]
    return None


def _joint_id_from_entry(entry: Any) -> str:
    value = entry.get("Value", entry) if isinstance(entry, dict) else entry
    sources = [value]
    if isinstance(value, dict):
        sources.append(value.get("JointMetaData"))
    for source in sources:
        if isinstance(source, dict):
            joint_id = source.get("JointId") or source.get("Id")
            if joint_id:
                return str(joint_id).strip()
    return value.strip() if isinstance(value, str) else ""


def _extract_joint_ids(output: Any) -> list[str]:
    first = output[0] if isinstance(output, list) and output and isinstance(output[0], list) else output
    entries = first if isinstance(first, list) else [first]
    ids: list[str] = []
    for entry in entries:
        joint_id = _joint_id_from_entry(entry)
        if joint_id and joint_id not in ids:
            ids.append(joint_id)
    return ids


def _extract_product_instance_uri(response: dict[str, Any]) -> str:
    data = response.get("data")
    tools = data.get("tools") if isinstance(data, dict) else None
    if not isinstance(tools, list):
        return ""
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        value = str(tool.get("productInstanceUri") or "").strip()
        if value:
            return value
    return ""


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed >= 0 else default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    return parsed if parsed >= 0 else default


def _is_connection_refused(exc: Exception) -> bool:
    if isinstance(exc, ConnectionRefusedError):
        return True
    winerror = getattr(exc, "winerror", None)
    if winerror in {10061, 1225}:
        return True
    err_no = getattr(exc, "errno", None)
    return err_no in {errno.ECONNREFUSED, 111}


async def discover_target_methods(endpoint: str) -> list[MethodSpec]:
    retries = max(1, _env_int("OPCUA_CONNECT_RETRIES", 6))
    delay_sec = _env_float("OPCUA_CONNECT_DELAY_SEC", 0.4)
    max_delay_sec = _env_float("OPCUA_CONNECT_MAX_DELAY_SEC", 2.0)

    methods: list[MethodSpec] = []
    targets = _target_method_names()

    attempt = 1
    current_delay = max(delay_sec, 0.0)
    while True:
        try:
            async with Client(endpoint, timeout=10) as client:
                await client.load_data_type_definitions()
                objects = await client.nodes.root.get_child(["0:Objects"])

                queue: list[tuple[Any, int]] = [(objects, 0)]
                visited: set[str] = set()

                while queue:
                    node, depth = queue.pop(0)
                    node_id = str(node.nodeid)
                    if node_id in visited or depth > 7:
                        continue
                    visited.add(node_id)

                    try:
                        node_class = await node.read_node_class()
                    except Exception:
                        node_class = None

                    if node_class == ua.NodeClass.Method:
                        try:
                            browse = await node.read_browse_name()
                        except Exception:
                            browse = None

                        if browse and browse.Name in targets:
                            try:
                                parent = await node.get_parent()
                                input_args: list[dict[str, Any]] = []
                                try:
                                    args_node = await node.get_child("0:InputArguments")
                                    args_meta = await args_node.get_value()
                                    for arg_meta in args_meta:
                                        dtype_id = int(getattr(arg_meta.DataType, "Identifier", 12))
                                        input_args.append(
                                            {
                                                "dataType": dtype_id,
                                                "value": default_arg_value(dtype_id),
                                            }
                                        )
                                except Exception as exc:
                                    logging.debug("Could not infer method input args for %s: %s", browse.Name, exc)

                                methods.append(
                                    MethodSpec(
                                        name=browse.Name,
                                        object_node=nodeid_to_payload(parent.nodeid),
                                        method_node=nodeid_to_payload(node.nodeid),
                                        arguments=_build_method_arguments(browse.Name, input_args),
                                    )
                                )
                            except Exception as exc:
                                logging.debug("Failed to parse method node %s: %s", browse.Name, exc)

                    try:
                        children = await node.get_children()
                    except Exception:
                        children = []
                    for child in children:
                        queue.append((child, depth + 1))
            break
        except Exception as exc:
            if not _is_connection_refused(exc) or attempt >= retries:
                raise ConnectionError(
                    f"Unable to connect to OPC UA endpoint '{endpoint}' after {attempt} attempt(s). "
                    "Start the simulator/backend first or increase OPCUA_CONNECT_RETRIES."
                ) from exc
            await asyncio.sleep(current_delay)
            current_delay = min(max_delay_sec, max(current_delay * 2, delay_sec))
            attempt += 1

    dedup: dict[str, MethodSpec] = {}
    for method in methods:
        dedup[method.name] = method
    return list(dedup.values())


class WsHarness:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self.pending: dict[int, asyncio.Future] = {}
        self.events: list[dict[str, Any]] = []
        self.raw: list[dict[str, Any]] = []
        self._reader_task = None
        self._next_id = 1

    async def __aenter__(self):
        self.ws = await websockets.connect(self.ws_url)
        self._reader_task = asyncio.create_task(self._reader())
        return self

    async def __aexit__(self, _exc_type, exc, _tb):
        if self.ws:
            await self.ws.close()
        if self._reader_task:
            self._reader_task.cancel()
            with contextlib.suppress(Exception):
                await self._reader_task

    async def _reader(self):
        async for message in self.ws:
            payload = json.loads(message)
            self.raw.append(payload)
            uid = payload.get("uniqueid")
            if uid is not None and uid in self.pending and not self.pending[uid].done():
                self.pending[uid].set_result(payload)
            if payload.get("command") == "event":
                self.events.append(payload)

    async def send(self, command: str, endpoint: str, body: dict | None = None, with_id: bool = False):
        event = dict(body or {})
        event["command"] = command
        event["endpoint"] = endpoint
        fut = None
        if with_id:
            uid = self._next_id
            self._next_id += 1
            event["uniqueid"] = uid
            fut = asyncio.get_running_loop().create_future()
            self.pending[uid] = fut

        await self.ws.send(json.dumps(event))  # type: ignore[attr-defined]
        if fut:
            return await asyncio.wait_for(fut, timeout=15)
        return None


async def run_regression(opc_endpoint: str, ws_url: str) -> dict[str, Any]:
    min_single_results = max(1, _env_int("REGRESSION_MIN_SINGLE_RESULTS", 2))
    min_job_tree = max(0, _env_int("REGRESSION_MIN_JOB_TREE_RESULTS", 0))

    report: dict[str, Any] = {
        "opc_endpoint": opc_endpoint,
        "ws_url": ws_url,
        "checks": [],
        "called_methods": [],
        "events_received": 0,
        "result_events": 0,
        "general_events": 0,
        "valid_result_payloads": 0,
        "valid_general_payloads": 0,
        "single_result_entries": 0,
        "job_results_with_full_tree": 0,
    }

    methods = await discover_target_methods(opc_endpoint)
    methods_by_name = {m.name: m for m in methods}
    report["discovered_methods"] = sorted(methods_by_name.keys())
    events: list[dict[str, Any]] = []

    async with websockets.connect(ws_url) as ws:

        async def send_recv(command: str, payload: dict | None = None):
            msg = dict(payload or {})
            uid = int(time.time() * 1000) % 1000000
            msg.update({"command": command, "endpoint": opc_endpoint, "uniqueid": uid})
            await ws.send(json.dumps(msg))
            deadline = time.time() + 15
            while time.time() < deadline:
                raw = await asyncio.wait_for(ws.recv(), timeout=15)
                rsp = json.loads(raw)
                if rsp.get("command") == "event":
                    events.append(rsp)
                    continue
                if rsp.get("uniqueid") == uid:
                    return rsp
            raise TimeoutError(f"Timeout waiting for response for command '{command}'")

        async def call_method_with_fallback(
            spec: MethodSpec, override_arguments: list[dict[str, Any]] | None = None
        ) -> dict[str, Any]:
            arguments = override_arguments if override_arguments is not None else spec.arguments
            payload = {
                "objectnode": spec.object_node,
                "methodnode": spec.method_node,
                "arguments": arguments,
            }
            rsp = await send_recv("methodcall", payload)
            if "exception" not in rsp.get("data", {}):
                return rsp

            # Retry transient simulator-side method races once.
            await asyncio.sleep(0.4)
            retry_rsp = await send_recv("methodcall", payload)
            if "exception" not in retry_rsp.get("data", {}):
                return retry_rsp

            # Some simulator profiles require the first boolean argument inverted.
            if arguments and isinstance(arguments[0].get("value"), bool):
                alt_arguments = [dict(x) for x in arguments]
                alt_arguments[0]["value"] = not bool(alt_arguments[0]["value"])
                alt_payload = {
                    "objectnode": spec.object_node,
                    "methodnode": spec.method_node,
                    "arguments": alt_arguments,
                }
                alt_rsp = await send_recv("methodcall", alt_payload)
                if "exception" not in alt_rsp.get("data", {}):
                    data = dict(alt_rsp.get("data", {}))
                    data["note"] = "used_bool_fallback"
                    alt_rsp = dict(alt_rsp)
                    alt_rsp["data"] = data
                    return alt_rsp

            return retry_rsp

        def result_is_valid(data: dict[str, Any]) -> bool:
            if not isinstance(data, dict):
                return False
            result = data.get("Result")
            if not isinstance(result, dict):
                return False
            event_type = data.get("EventType")
            metadata = result.get("ResultMetaData")
            return event_type is not None and isinstance(metadata, dict)

        def general_event_is_valid(data: dict[str, Any]) -> bool:
            if not isinstance(data, dict):
                return False
            if data.get("Result") is not None:
                return False
            return data.get("EventType") is not None and (
                data.get("Message") is not None
                or data.get("EventCode") is not None
                or data.get("JoiningTechnology") is not None
            )

        def extract_result_id(result_obj: dict[str, Any]) -> str | None:
            metadata = result_obj.get("ResultMetaData")
            if not isinstance(metadata, dict):
                return None
            rid = metadata.get("ResultId")
            if rid is None:
                return None
            return str(rid)

        def extract_classification(result_obj: dict[str, Any]) -> int | None:
            metadata = result_obj.get("ResultMetaData")
            if not isinstance(metadata, dict):
                return None
            raw = metadata.get("Classification")
            if raw is None:
                return None
            text = str(raw)
            digits = "".join(ch for ch in text if ch.isdigit())
            if digits:
                try:
                    return int(digits)
                except ValueError:
                    return None
            return None

        def has_nested_tree(result_obj: dict[str, Any]) -> bool:
            content = result_obj.get("ResultContent")
            if not isinstance(content, list) or not content:
                return False
            for child in content:
                if isinstance(child, dict) and (
                    isinstance(child.get("ResultContent"), list) or child.get("ResultMetaData") is not None
                ):
                    return True
            return False

        async def call_and_record(canonical_name: str, *, arguments: list[dict[str, Any]] | None = None) -> None:
            method = _pick_method_for_alias(methods_by_name, canonical_name)
            if not method:
                report["called_methods"].append({"name": canonical_name, "status": "not_found"})
                return
            response = await call_method_with_fallback(method, override_arguments=arguments)
            ok = "exception" not in response.get("data", {})
            report["called_methods"].append(
                {
                    "name": canonical_name,
                    "resolved_method": method.name,
                    "status": "ok" if ok else "failed",
                    "response": response.get("data"),
                }
            )

        def with_argument_values(arguments: list[dict[str, Any]], values: dict[int, Any]) -> list[dict[str, Any]]:
            updated = [dict(arg) for arg in arguments]
            for index, value in values.items():
                if index < len(updated):
                    updated[index]["value"] = value
            return updated

        rsp = await send_recv("connect to")
        report["checks"].append({"connect": "exception" not in rsp.get("data", {})})

        rsp = await send_recv("namespaces")
        report["checks"].append({"namespaces": "exception" not in rsp.get("data", {})})

        rsp = await send_recv("read", {"nodeid": "ns=0;i=85"})
        report["checks"].append({"read_objects": "exception" not in rsp.get("data", {})})

        rsp = await send_recv("subscribe")
        report["checks"].append({"subscribe": "exception" not in rsp.get("data", {})})

        rsp = await send_recv("read product instance uri")
        discovered_product_id = _extract_product_instance_uri(rsp)
        active_product_id = PRODUCT_ID_OVERRIDE or discovered_product_id or DEFAULT_PRODUCT_ID
        report["discovered_product_instance_uri"] = discovered_product_id
        report["active_product_instance_uri"] = active_product_id

        # Method flow:
        # 1) Simulation methods
        # 2) Joint Demo actions using server-discovered JointIds from GetJointList.
        await call_and_record("SimulateSingleResult")
        await call_and_record("SimulateJobResult")
        await call_and_record("Simulate_Batch_or_SYNC_Result")
        await call_and_record("SimulateEvents")

        discovered_joint_ids: list[str] = []
        get_joint_list = _pick_method_for_alias(methods_by_name, "GetJointList")
        if get_joint_list:
            get_joint_response = await call_method_with_fallback(
                get_joint_list,
                override_arguments=with_argument_values(get_joint_list.arguments, {0: active_product_id}),
            )
            ok = "exception" not in get_joint_response.get("data", {})
            output = get_joint_response.get("data", {}).get("output")
            discovered_joint_ids = _extract_joint_ids(output)
            report["called_methods"].append(
                {
                    "name": "GetJointList",
                    "resolved_method": get_joint_list.name,
                    "status": "ok" if ok else "failed",
                    "response": get_joint_response.get("data"),
                    "joint_ids": discovered_joint_ids,
                }
            )
        else:
            report["called_methods"].append({"name": "GetJointList", "status": "not_found"})

        joint_1 = JOINT_1_OVERRIDE or (discovered_joint_ids[0] if discovered_joint_ids else "")
        joint_2 = JOINT_2_OVERRIDE or (discovered_joint_ids[1] if len(discovered_joint_ids) > 1 else joint_1)
        report["discovered_joint_ids"] = discovered_joint_ids

        select_joint = _pick_method_for_alias(methods_by_name, "SelectJoint")
        start_selected_joining = _pick_method_for_alias(methods_by_name, "StartSelectedJoining")
        if select_joint and joint_1:
            select_joint_1_args = with_argument_values(select_joint.arguments, {0: active_product_id, 1: joint_1})
            await call_and_record("SelectJoint", arguments=select_joint_1_args)

            start_args = (
                with_argument_values(start_selected_joining.arguments, {0: active_product_id})
                if start_selected_joining
                else None
            )
            await call_and_record("StartSelectedJoining", arguments=start_args)

            select_joint_2_args = with_argument_values(select_joint.arguments, {0: active_product_id, 1: joint_2})
            await call_and_record("SelectJoint", arguments=select_joint_2_args)
            await call_and_record("StartSelectedJoining", arguments=start_args)
        elif select_joint:
            report["called_methods"].append({"name": "SelectJoint", "status": "not_run_without_joint_id"})
            report["called_methods"].append({"name": "StartSelectedJoining", "status": "not_run_without_select_joint"})
        else:
            report["called_methods"].append({"name": "SelectJoint", "status": "not_found"})
            report["called_methods"].append({"name": "StartSelectedJoining", "status": "not_run_without_select_joint"})

        event_deadline = time.time() + 14
        while time.time() < event_deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            evt = json.loads(raw)
            if evt.get("command") == "event":
                events.append(evt)

        report["events_received"] = len(events)
        result_events = [e for e in events if isinstance(e.get("data"), dict) and e["data"].get("Result") is not None]
        general_events = [e for e in events if isinstance(e.get("data"), dict) and e["data"].get("Result") is None]
        report["result_events"] = len(result_events)
        report["general_events"] = len(general_events)

        report["valid_result_payloads"] = sum(1 for e in result_events if result_is_valid(e.get("data", {})))
        report["valid_general_payloads"] = sum(1 for e in general_events if general_event_is_valid(e.get("data", {})))

        single_ids: set[str] = set()
        job_with_tree = 0
        for evt in result_events:
            data = evt.get("data", {})
            result_obj = data.get("Result")
            if not isinstance(result_obj, dict):
                continue

            classification = extract_classification(result_obj)
            if classification == 1:
                result_id = extract_result_id(result_obj)
                if result_id:
                    single_ids.add(result_id)
            if classification == 4 and has_nested_tree(result_obj):
                job_with_tree += 1

        report["single_result_entries"] = len(single_ids)
        report["job_results_with_full_tree"] = job_with_tree

        await ws.send(json.dumps({"command": "terminate connection", "endpoint": opc_endpoint}))

    all_checks_ok = all(list(item.values())[0] for item in report["checks"])
    required_ok = []
    for row in report["called_methods"]:
        name = row.get("name")
        status = row.get("status")
        if name in {
            "SimulateSingleResult",
            "SimulateJobResult",
            "Simulate_Batch_or_SYNC_Result",
            "SimulateEvents",
            "SelectJoint",
            "StartSelectedJoining",
        }:
            required_ok.append(status == "ok")

    report["ok"] = (
        all_checks_ok
        and all(required_ok)
        and report["events_received"] > 0
        and report["valid_result_payloads"] > 0
        and report["valid_general_payloads"] > 0
        and report["single_result_entries"] >= min_single_results
        and report["job_results_with_full_tree"] >= min_job_tree
    )
    return report


def run_ui_assertions(ui_base_url: str) -> dict[str, Any]:
    npm = shutil.which("npm")
    npx = shutil.which("npx")
    if not npm or not npx:
        return {
            "ok": False,
            "exit_code": -1,
            "error": "npm/npx are required for --ui-assertions but were not found in PATH.",
        }

    node_modules = PROJECT_ROOT / "node_modules"
    if not node_modules.exists():
        install_cmd = (
            [npm, "ci"] if (PROJECT_ROOT / "package-lock.json").exists() else [npm, "install", "--legacy-peer-deps"]
        )
        install = subprocess.run(
            install_cmd,
            cwd=str(PROJECT_ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        if install.returncode != 0:
            return {
                "ok": False,
                "exit_code": install.returncode,
                "error": "Failed to install JavaScript dependencies for UI assertions.",
                "stdout_tail": "\n".join(install.stdout.splitlines()[-40:]),
                "stderr_tail": "\n".join(install.stderr.splitlines()[-40:]),
            }

    env = os.environ.copy()
    env.setdefault("PLAYWRIGHT_TEST_BASE_URL", ui_base_url)
    cmd = [
        npx,
        "playwright",
        "test",
        "tests/e2e/regression-ui.spec.mjs",
        "--reporter=line",
    ]

    try:
        completed = subprocess.run(
            cmd,
            cwd=os.getcwd(),
            check=False,
            env=env,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "exit_code": -1,
            "error": f"Failed to run Playwright UI assertions: {exc}",
        }

    return {
        "ok": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout_tail": "\n".join(completed.stdout.splitlines()[-40:]),
        "stderr_tail": "\n".join(completed.stderr.splitlines()[-40:]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run functional OPC UA regression against backend websocket + simulator"
    )
    parser.add_argument("--endpoint", default="opc.tcp://localhost:40451", help="OPC UA endpoint")
    parser.add_argument("--ws-url", default="ws://localhost:8001", help="Backend websocket URL")
    parser.add_argument("--out", default="regression_report.json", help="Output JSON report path")
    parser.add_argument(
        "--ui-assertions",
        action="store_true",
        help="Run Playwright UI assertions after backend regression checks.",
    )
    parser.add_argument(
        "--ui-base-url",
        default="http://127.0.0.1:3000",
        help="Base URL for browser UI assertions.",
    )
    args = parser.parse_args()

    try:
        report = asyncio.run(run_regression(args.endpoint, args.ws_url))
    except ConnectionError as exc:
        print(str(exc))
        return 1
    if args.ui_assertions:
        ui_report = run_ui_assertions(args.ui_base_url)
        report["ui_assertions"] = ui_report
        if not ui_report.get("ok"):
            report["ok"] = False

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
