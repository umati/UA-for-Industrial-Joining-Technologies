import asyncio
import importlib
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from asyncua import Client, ua

logger = logging.getLogger(__name__)


@dataclass
class MethodSpec:
    name: str
    object_node: dict[str, Any]
    method_node: dict[str, Any]
    arguments: list[dict[str, Any]]


def nodeid_to_payload(nodeid: ua.NodeId) -> dict[str, Any]:
    return {
        "NamespaceIndex": int(nodeid.NamespaceIndex),
        "Identifier": nodeid.Identifier,
    }


def payload_to_nodeid_string(payload: dict[str, Any]) -> str:
    ns = int(payload["NamespaceIndex"])
    identifier = payload["Identifier"]
    if isinstance(identifier, int):
        return f"ns={ns};i={identifier}"
    return f"ns={ns};s={identifier}"


def default_arg_value(dtype_identifier: int) -> Any:
    mapping = {
        1: True,                  # Boolean
        2: 1,                     # SByte
        3: 1,                     # Byte
        4: 1,                     # Int16
        5: 1,                     # UInt16
        6: 1,                     # Int32
        7: 1,                     # UInt32
        8: 1,                     # Int64
        9: 1,                     # UInt64
        10: 1.0,                  # Float
        11: 1.0,                  # Double
        12: "1",                  # String
        13: "2026-01-01T00:00:00Z",  # DateTime
        31918: "1",               # TrimmedString (IJT custom type)
    }
    return mapping.get(dtype_identifier, "1")


def map_nodeid_to_varianttype(nodeid_identifier: int) -> ua.VariantType:
    mapping = {
        1: ua.VariantType.Boolean,   # Boolean
        2: ua.VariantType.SByte,     # SByte
        3: ua.VariantType.Byte,      # Byte
        4: ua.VariantType.Int16,     # Int16
        5: ua.VariantType.UInt16,    # UInt16
        6: ua.VariantType.Int32,     # Int32
        7: ua.VariantType.UInt32,    # UInt32
        8: ua.VariantType.Int64,     # Int64
        9: ua.VariantType.UInt64,    # UInt64
        10: ua.VariantType.Float,    # Float
        11: ua.VariantType.Double,   # Double
        12: ua.VariantType.String,   # String
        13: ua.VariantType.DateTime, # DateTime
        31918: ua.VariantType.String,  # TrimmedString (IJT custom type)
    }
    return mapping.get(nodeid_identifier, ua.VariantType.String)


def create_variants(arguments: list[dict[str, Any]]) -> list[ua.Variant]:
    result: list[ua.Variant] = []
    for arg in arguments:
        dtype = int(arg.get("dataType", 12))
        value = arg.get("value")
        variant_type = map_nodeid_to_varianttype(dtype)

        if isinstance(value, list):
            result.append(ua.Variant(value, variant_type, is_array=True))
        else:
            if value is None and variant_type == ua.VariantType.String:
                value = ""
            result.append(ua.Variant(value, variant_type))
    return result


async def discover_simulation_methods(endpoint: str) -> list[MethodSpec]:
    methods: list[MethodSpec] = []
    targets = {"SimulateSingleResult", "SimulateJobResult", "SimulateEvents"}

    async with Client(endpoint, timeout=10) as client:
        await client.load_data_type_definitions()
        objects = await client.nodes.root.get_child(["0:Objects"])

        queue: list[tuple[Any, int]] = [(objects, 0)]
        visited: set[str] = set()
        simulation_nodes: list[Any] = []

        while queue:
            node, depth = queue.pop(0)
            node_id = str(node.nodeid)
            if node_id in visited or depth > 6:
                continue
            visited.add(node_id)

            try:
                browse_name = await node.read_browse_name()
                if browse_name.Name == "Simulations":
                    simulation_nodes.append(node)
            except Exception as exc:
                logger.debug("Failed to inspect browse name while finding simulation node: %s", exc)

            try:
                children = await node.get_children()
            except Exception:
                continue

            for child in children:
                queue.append((child, depth + 1))

        for sim_node in simulation_nodes:
            child_nodes = await sim_node.get_children()
            for folder in child_nodes:
                try:
                    maybe_methods = await folder.get_children()
                except Exception:
                    continue

                for method in maybe_methods:
                    try:
                        node_class = await method.read_node_class()
                        if node_class != ua.NodeClass.Method:
                            continue

                        browse = await method.read_browse_name()
                        if browse.Name not in targets:
                            continue

                        parent = await method.get_parent()
                        input_args: list[dict[str, Any]] = []

                        try:
                            args_node = await method.get_child("0:InputArguments")
                            args_meta = await args_node.get_value()
                            for arg_meta in args_meta:
                                dtype = int(getattr(arg_meta.DataType, "Identifier", 12))
                                input_args.append(
                                    {
                                        "dataType": dtype,
                                        "value": default_arg_value(dtype),
                                    }
                                )
                        except Exception as exc:
                            logger.debug("Could not infer method input args for %s: %s", browse.Name, exc)

                        methods.append(
                            MethodSpec(
                                name=browse.Name,
                                object_node=nodeid_to_payload(parent.nodeid),
                                method_node=nodeid_to_payload(method.nodeid),
                                arguments=input_args,
                            )
                        )
                    except Exception:
                        continue

    dedup: dict[str, MethodSpec] = {}
    for method in methods:
        dedup[method.name] = method
    return list(dedup.values())


class BaseAdapter:
    name = "base"

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

    async def connect(self) -> dict[str, Any]:
        raise NotImplementedError

    async def namespaces(self) -> dict[str, Any]:
        raise NotImplementedError

    async def read_objects(self) -> dict[str, Any]:
        raise NotImplementedError

    async def subscribe(self) -> dict[str, Any]:
        raise NotImplementedError

    async def call_method(self, spec: MethodSpec) -> dict[str, Any]:
        raise NotImplementedError

    async def collect_events(self, seconds: float = 6.0) -> dict[str, int]:
        raise NotImplementedError

    async def terminate(self) -> dict[str, Any]:
        raise NotImplementedError


class WebAdapter(BaseAdapter):
    name = "web"
    def __init__(self, endpoint: str, ws_url: str):
        self._websockets = None
        self.endpoint = endpoint
        self.ws_url = ws_url
        self.ws = None
        self._next_id = 1
        self._events: list[dict[str, Any]] = []

    async def start(self) -> None:
        if self._websockets is None:
            import websockets as _websockets
            self._websockets = _websockets
        self.ws = await self._websockets.connect(self.ws_url)

    async def stop(self) -> None:
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def _send_recv(self, command: str, payload: dict[str, Any] | None = None):
        if self.ws is None:
            raise RuntimeError("WebSocket not started.")

        msg = dict(payload or {})
        uid = self._next_id
        self._next_id += 1
        msg.update({"command": command, "endpoint": self.endpoint, "uniqueid": uid})
        await self.ws.send(json.dumps(msg))

        deadline = time.time() + 20
        while time.time() < deadline:
            raw = await asyncio.wait_for(self.ws.recv(), timeout=20)
            rsp = json.loads(raw)
            if rsp.get("command") == "event":
                self._events.append(rsp)
            if rsp.get("uniqueid") == uid:
                return rsp.get("data", rsp)
        raise TimeoutError(f"Timeout waiting for websocket response: {command}")

    async def connect(self) -> dict[str, Any]:
        return await self._send_recv("connect to")

    async def namespaces(self) -> dict[str, Any]:
        return await self._send_recv("namespaces")

    async def read_objects(self) -> dict[str, Any]:
        return await self._send_recv("read", {"nodeid": "ns=0;i=85"})

    async def subscribe(self) -> dict[str, Any]:
        if self.ws is None:
            raise RuntimeError("WebSocket not started.")
        await self.ws.send(json.dumps({"command": "subscribe", "endpoint": self.endpoint}))
        return {"ok": True}

    async def call_method(self, spec: MethodSpec) -> dict[str, Any]:
        payload = {
            "objectnode": spec.object_node,
            "methodnode": spec.method_node,
            "arguments": spec.arguments,
        }
        response = await self._send_recv("methodcall", payload)
        if "exception" not in str(response).lower():
            return response

        # Retry once for transient simulator-side request races.
        await asyncio.sleep(0.4)
        response = await self._send_recv("methodcall", payload)
        if "exception" not in str(response).lower():
            return response

        # Simulator profiles may differ for first boolean argument handling.
        if spec.arguments and isinstance(spec.arguments[0].get("value"), bool):
            alt_arguments = [dict(x) for x in spec.arguments]
            alt_arguments[0]["value"] = not bool(alt_arguments[0]["value"])
            alt_payload = {
                "objectnode": spec.object_node,
                "methodnode": spec.method_node,
                "arguments": alt_arguments,
            }
            response = await self._send_recv("methodcall", alt_payload)
            if isinstance(response, dict):
                response = dict(response)
                response["note"] = "used_bool_fallback"
            return response

        return response

    async def collect_events(self, seconds: float = 6.0) -> dict[str, int]:
        if self.ws is None:
            raise RuntimeError("WebSocket not started.")

        end = time.time() + seconds
        while time.time() < end:
            try:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            rsp = json.loads(raw)
            if rsp.get("command") == "event":
                self._events.append(rsp)

        total = len(self._events)
        result_events = sum(
            1
            for evt in self._events
            if isinstance(evt.get("data"), dict) and evt["data"].get("Result") is not None
        )
        return {"total": total, "result_events": result_events}

    async def terminate(self) -> dict[str, Any]:
        return await self._send_recv("terminate connection")


class _CountingHandler:
    def __init__(self):
        self.count = 0

    async def event_notification(self, _event):
        self.count += 1


class ConsoleAdapter(BaseAdapter):
    name = "console"

    def __init__(self, endpoint: str, console_dir: str):
        self.endpoint = endpoint
        self.console_dir = Path(console_dir)
        self.client_wrapper = None
        self._event_sub = None
        self._event_handler = None

    async def start(self) -> None:
        if not self.console_dir.exists():
            raise FileNotFoundError(f"Console project not found: {self.console_dir}")
        if str(self.console_dir) not in sys.path:
            sys.path.insert(0, str(self.console_dir))

        try:
            module = importlib.import_module("opcua_client")
        except ModuleNotFoundError as exc:
            raise RuntimeError(f"Console adapter dependency missing: {exc.name}") from exc
        self.client_wrapper = module.OPCUAClient(self.endpoint)

    async def stop(self) -> None:
        return None

    async def connect(self) -> dict[str, Any]:
        await self.client_wrapper.connect()
        return {"connected": True}

    async def namespaces(self) -> dict[str, Any]:
        namespaces = await self.client_wrapper.client.get_namespace_array()
        return {"namespaces": namespaces}

    async def read_objects(self) -> dict[str, Any]:
        node = self.client_wrapper.client.get_node("ns=0;i=85")
        browse_name = await node.read_browse_name()
        return {"browse_name": getattr(browse_name, "Name", None)}

    async def subscribe(self) -> dict[str, Any]:
        await self.client_wrapper.subscribe_to_events()
        return {"ok": True}

    async def call_method(self, spec: MethodSpec) -> dict[str, Any]:
        obj = self.client_wrapper.client.get_node(payload_to_nodeid_string(spec.object_node))
        method = self.client_wrapper.client.get_node(payload_to_nodeid_string(spec.method_node))
        args = create_variants(spec.arguments)

        try:
            output = await obj.call_method(method, *args)
            return {"output": str(output)}
        except Exception:
            # Retry transient method-call races once for console adapter.
            await asyncio.sleep(0.4)

        try:
            output = await obj.call_method(method, *args)
            return {"output": str(output)}
        except Exception as first_retry_exc:
            # Simulator profiles may differ for first boolean argument handling.
            if spec.arguments and isinstance(spec.arguments[0].get("value"), bool):
                alt_arguments = [dict(x) for x in spec.arguments]
                alt_arguments[0]["value"] = not bool(alt_arguments[0]["value"])
                alt_args = create_variants(alt_arguments)
                output = await obj.call_method(method, *alt_args)
                return {"output": str(output), "note": "used_bool_fallback"}
            raise first_retry_exc

    async def collect_events(self, seconds: float = 6.0) -> dict[str, int]:
        # Console adapter already subscribes through OPCUAClient.subscribe_to_events().
        # Avoid creating extra transient subscriptions, which can make simulator teardown noisy.
        await asyncio.sleep(seconds)
        return {"total": 0, "result_events": 0}

    async def terminate(self) -> dict[str, Any]:
        if self.client_wrapper is None:
            return {"terminated": False, "reason": "client_not_initialized"}
        await self.client_wrapper.cleanup()
        return {"terminated": True}


def make_adapter(adapter_name: str, endpoint: str, ws_url: str, console_dir: str) -> BaseAdapter:
    name = adapter_name.strip().lower()
    if name == "web":
        return WebAdapter(endpoint=endpoint, ws_url=ws_url)
    if name == "console":
        return ConsoleAdapter(endpoint=endpoint, console_dir=console_dir)
    raise ValueError(f"Unknown adapter name: {adapter_name}")


def adapters_from_env() -> list[str]:
    raw = os.getenv("OPCUA_CLIENT_ADAPTERS", "web,console")
    names = [x.strip().lower() for x in raw.split(",") if x.strip()]
    return names or ["web", "console"]


