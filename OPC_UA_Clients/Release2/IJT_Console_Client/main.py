import asyncio
from opcua_client import OPCUAEventClient
from client_config import SERVER_URL
from ijt_logger import ijt_log


async def main():
    client = OPCUAEventClient(SERVER_URL)
    try:
        await client.connect()
        await client.subscribe_to_events()
        await client.run_forever()
    except Exception as e:
        ijt_log.error(f"Unhandled exception in main: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        ijt_log.info("Client stopped by user (KeyboardInterrupt).")
