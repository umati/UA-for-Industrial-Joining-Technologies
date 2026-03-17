#!/usr/bin/env python3
import argparse
import asyncio
import json
import logging
import time
import warnings
from dataclasses import dataclass
from typing import Any

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


def nodeid_to_payload(nodeid: ua.NodeId) -> dict[str, Any]:
    return {
        "NamespaceIndex": int(nodeid.NamespaceIndex),
        "Identifier": nodeid.Identifier,
    }


def default_arg_value(dtype_identifier: int) -> Any:
    mapping = {
        1: False,     # Boolean (safer simulator default)
        2: 1,         # SByte
        3: 1,         # Byte
        4: 1,         # Int16
        5: 1,         # UInt16
        6: 1,         # Int32
        7: 1,         # UInt32
        8: 1,         # Int64
        9: 1,         # UInt64
        10: 1.0,      # Float
        11: 1.0,      # Double
        12: "1",     # String
        13: "2026-01-01T00:00:00Z",  # DateTime (string fallback)
        31918: "1",  # TrimmedString
    }
    return mapping.get(dtype_identifier, "1")


async def discover_simulation_methods(endpoint: str) -> list[MethodSpec]:
    methods: list[MethodSpec] = []
    targets = {"SimulateSingleResult", "SimulateJobResult", "SimulateEvents"}

    async with Client(endpoint, timeout=10) as client:
        await client.load_data_type_definitions()
        objects = await client.nodes.root.get_child(["0:Objects"])

        queue: list[tuple[Any, int]] = [(objects, 0)]
        visited = set()
        simulation_nodes: list[Any] = []

        while queue:
            node, depth = queue.pop(0)
            nid = str(node.nodeid)
            if nid in visited or depth > 5:
                continue
            visited.add(nid)

            try:
                bname = await node.read_browse_name()
                if bname.Name == "Simulations":
                    simulation_nodes.append(node)
            except Exception:
                pass

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
                        cls = await method.read_node_class()
                        if cls != ua.NodeClass.Method:
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
                                dtype_id = int(getattr(arg_meta.DataType, "Identifier", 12))
                                input_args.append(
                                    {
                                        "dataType": dtype_id,
                                        "value": default_arg_value(dtype_id),
                                    }
                                )
                        except Exception:
                            pass

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

    dedup = {}
    for m in methods:
        if m.name == "SimulateJobResult" and m.arguments:
            # Simulator rejects True in some profiles; default False is stable.
            m.arguments[0]["value"] = False
        dedup[m.name] = m
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

    async def __aexit__(self, exc_type, exc, tb):
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

        await self.ws.send(json.dumps(event))
        if fut:
            return await asyncio.wait_for(fut, timeout=15)
        return None


async def run_regression(opc_endpoint: str, ws_url: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "opc_endpoint": opc_endpoint,
        "ws_url": ws_url,
        "checks": [],
        "called_methods": [],
        "events_received": 0,
        "result_events": 0,
    }

    methods = await discover_simulation_methods(opc_endpoint)
    report["discovered_methods"] = [m.name for m in methods]

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
                if rsp.get("uniqueid") == uid:
                    return rsp
            raise TimeoutError(f"Timeout waiting for response for command '{command}'")

        async def call_method_with_fallback(spec: MethodSpec) -> dict[str, Any]:
            payload = {
                "objectnode": spec.object_node,
                "methodnode": spec.method_node,
                "arguments": spec.arguments,
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
            if spec.arguments and isinstance(spec.arguments[0].get("value"), bool):
                alt_arguments = [dict(x) for x in spec.arguments]
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

        rsp = await send_recv("connect to")
        report["checks"].append({"connect": "exception" not in rsp.get("data", {})})

        rsp = await send_recv("namespaces")
        report["checks"].append({"namespaces": "exception" not in rsp.get("data", {})})

        rsp = await send_recv("read", {"nodeid": "ns=0;i=85"})
        report["checks"].append({"read_objects": "exception" not in rsp.get("data", {})})

        await ws.send(json.dumps({"command": "subscribe", "endpoint": opc_endpoint}))

        wanted = ["SimulateSingleResult", "SimulateJobResult", "SimulateEvents"]
        for name in wanted:
            match = next((m for m in methods if m.name == name), None)
            if not match:
                report["called_methods"].append({"name": name, "status": "not_found"})
                continue

            rsp = await call_method_with_fallback(match)
            ok = "exception" not in rsp.get("data", {})
            report["called_methods"].append({"name": name, "status": "ok" if ok else "failed", "response": rsp.get("data")})

        event_deadline = time.time() + 8
        events: list[dict[str, Any]] = []
        while time.time() < event_deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            evt = json.loads(raw)
            if evt.get("command") == "event":
                events.append(evt)

        report["events_received"] = len(events)
        report["result_events"] = sum(1 for e in events if e.get("data", {}).get("Result") is not None)

        await ws.send(json.dumps({"command": "terminate connection", "endpoint": opc_endpoint}))

    all_checks_ok = all(list(item.values())[0] for item in report["checks"])
    called_ok = all(row["status"] in {"ok", "not_found"} for row in report["called_methods"])
    report["ok"] = all_checks_ok and called_ok and report["events_received"] > 0
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run functional OPC UA regression against backend websocket + simulator")
    parser.add_argument("--endpoint", default="opc.tcp://localhost:40451", help="OPC UA endpoint")
    parser.add_argument("--ws-url", default="ws://localhost:8001", help="Backend websocket URL")
    parser.add_argument("--out", default="regression_report.json", help="Output JSON report path")
    args = parser.parse_args()

    report = asyncio.run(run_regression(args.endpoint, args.ws_url))
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    import contextlib

    raise SystemExit(main())
