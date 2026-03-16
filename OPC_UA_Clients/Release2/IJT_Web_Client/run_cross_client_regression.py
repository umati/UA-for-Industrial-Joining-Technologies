#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

from tests.shared_opcua.adapters import adapters_from_env, discover_simulation_methods, make_adapter


def _endpoint_reachable(endpoint: str, timeout: float = 1.0) -> bool:
    parsed = urlparse(endpoint)
    host = parsed.hostname or "localhost"
    port = parsed.port or 40451
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


async def run_for_adapter(adapter_name: str, endpoint: str, ws_url: str, console_dir: str) -> dict:
    adapter = make_adapter(adapter_name, endpoint, ws_url, console_dir)
    report = {
        "adapter": adapter_name,
        "connect": False,
        "namespaces": False,
        "read_objects": False,
        "methods": [],
        "events": {"total": 0, "result_events": 0},
        "ok": False,
    }

    methods = await discover_simulation_methods(endpoint)
    wanted = ["SimulateSingleResult", "SimulateJobResult", "SimulateEvents"]

    try:
        await adapter.start()

        connect_rsp = await adapter.connect()
        report["connect"] = "exception" not in str(connect_rsp).lower()

        ns_rsp = await adapter.namespaces()
        report["namespaces"] = bool(ns_rsp.get("namespaces"))

        read_rsp = await adapter.read_objects()
        report["read_objects"] = "exception" not in str(read_rsp).lower()

        await adapter.subscribe()

        for name in wanted:
            spec = next((m for m in methods if m.name == name), None)
            if not spec:
                report["methods"].append({"name": name, "status": "not_found"})
                continue

            try:
                result = await adapter.call_method(spec)
                ok = "exception" not in str(result).lower()
                report["methods"].append({"name": name, "status": "ok" if ok else "failed", "result": result})
            except Exception as exc:
                report["methods"].append({"name": name, "status": "failed", "error": str(exc)})

        report["events"] = await adapter.collect_events(seconds=6.0)

    except Exception as exc:
        report["fatal_error"] = str(exc)
    finally:
        try:
            await adapter.terminate()
        except Exception as exc:
            report["terminate_error"] = str(exc)
        try:
            await adapter.stop()
        except Exception as exc:
            report["stop_error"] = str(exc)

    checks_ok = report["connect"] and report["namespaces"] and report["read_objects"]
    methods_ok = all(m["status"] in {"ok", "not_found"} for m in report["methods"])
    report["ok"] = checks_ok and methods_ok
    return report


async def run_all(endpoint: str, ws_url: str, console_dir: str, adapters: list[str]) -> dict:
    runs = []
    for name in adapters:
        runs.append(await run_for_adapter(name, endpoint, ws_url, console_dir))
    return {
        "endpoint": endpoint,
        "ws_url": ws_url,
        "console_dir": console_dir,
        "runs": runs,
        "ok": all(r.get("ok") for r in runs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run shared OPC UA regression through both client adapters")
    parser.add_argument("--endpoint", default=os.getenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40451"))
    parser.add_argument("--ws-url", default=os.getenv("OPCUA_WS_URL", "ws://localhost:8001"))
    parser.add_argument(
        "--console-dir",
        default=os.getenv(
            "OPCUA_CONSOLE_CLIENT_DIR",
            str((Path(__file__).resolve().parent / ".." / "IJT_Console_Client").resolve()),
        ),
    )
    parser.add_argument("--adapters", default=",".join(adapters_from_env()))
    parser.add_argument("--out", default="cross_client_regression_report.json")
    args = parser.parse_args()

    adapter_names = [x.strip().lower() for x in args.adapters.split(",") if x.strip()]
    if not _endpoint_reachable(args.endpoint):
        print(
            f"[ERROR] No OPC UA Server running on {args.endpoint}. "
            "If Web/Console clients and server are in separate folders/downloads, "
            "start the OPC UA server first and re-run tests."
        )
        return 1

    report = asyncio.run(run_all(args.endpoint, args.ws_url, args.console_dir, adapter_names))

    out = Path(args.out)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
