import asyncio
import argparse
import re
import traceback
import os
import sys

from opcua_client import OPCUAClient
from client_config import SERVER_URL as DEFAULT_SERVER_URL
from ijt_logger import ijt_log

URL_PATTERN = re.compile(r"opc\.tcp://[a-zA-Z0-9\.\-]+:\d+")


def validate_url(url: str) -> str:
    if url and URL_PATTERN.match(url):
        return url
    env_url = os.getenv("OPCUA_SERVER_URL")
    if env_url and URL_PATTERN.match(env_url):
        ijt_log.info(f"Using OPC UA server URL from environment: {env_url}")
        return env_url
    ijt_log.warning("Invalid or missing OPC UA URL. Falling back to default.")
    return DEFAULT_SERVER_URL


async def run_client(server_url: str):
    client = OPCUAClient(server_url)
    await client.connect()
    await client.subscribe_to_events()

    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        ijt_log.info("Run loop cancelled.")
    finally:
        await client.cleanup()
        ijt_log.info("Client shutdown complete.")
        ijt_log.info(
            "Note: Any late server responses after disconnect can be safely ignored."
        )


def main():
    parser = argparse.ArgumentParser(description="Run OPC UA Event Client")
    parser.add_argument("--url", type=str, help="OPC UA server URL")
    args = parser.parse_args()

    server_url = validate_url(args.url)
    ijt_log.info(f"Using OPC UA server URL: {server_url}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    task = loop.create_task(run_client(server_url))

    try:
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        ijt_log.info("KeyboardInterrupt received. Cancelling tasks...")
        task.cancel()
        try:
            loop.run_until_complete(task)
        except asyncio.CancelledError:
            ijt_log.info("Client task cancelled.")
    except Exception as e:
        ijt_log.error(f"Unhandled exception: {e}")
        ijt_log.error(traceback.format_exc())
    finally:
        loop.close()
        ijt_log.info("Event loop closed.")


if __name__ == "__main__":
    main()
