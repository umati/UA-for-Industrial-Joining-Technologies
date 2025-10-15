import asyncio
import argparse
import re
import traceback
from opcua_client import OPCUAEventClient
from client_config import SERVER_URL as DEFAULT_SERVER_URL
from ijt_logger import ijt_log

URL_PATTERN = r"opc\.tcp://[a-zA-Z0-9\.\-]+:\d+"


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, help="OPC UA server URL")
    args = parser.parse_args()
    server_url = (
        args.url if args.url and re.match(URL_PATTERN, args.url) else DEFAULT_SERVER_URL
    )

    ijt_log.info(f"Using OPC UA server URL: {server_url}")
    client = OPCUAEventClient(server_url)

    try:
        await client.connect()
        await client.subscribe_to_events()
        await client.run_forever()
    except asyncio.CancelledError:
        ijt_log.info("Run loop cancelled by user.")
    except Exception as e:
        ijt_log.error(f"Unhandled exception in main: {e}")
        ijt_log.error(traceback.format_exc())
    finally:
        await client.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        ijt_log.info("Client stopped by user (KeyboardInterrupt).")
