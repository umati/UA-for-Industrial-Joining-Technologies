import asyncio
from asyncua.ua.uaerrors import UaError
from asyncua import Client
from result_event_handler import ResultEventHandler
from ijt_logger import ijt_log
from event_types import get_event_types
import socket


class OPCUAEventClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.client = Client(server_url)
        self.subscription = None
        self.handler = ResultEventHandler(server_url)

    async def connect(self):
        computer_name = socket.getfqdn()

        self.client.name = f"urn:{computer_name}:IJT:ConsoleClient"
        self.client.description = f"urn:{computer_name}:IJT:ConsoleClient"
        self.client.application_uri = f"urn:{computer_name}:IJT:ConsoleClient"
        self.client.product_uri = f"urn:IJT:ConsoleClient"

        try:
            await self.client.connect()
            await self.client.load_type_definitions()
            ijt_log.info(f"Connected to OPC UA server at {self.server_url}")
        except Exception as e:
            ijt_log.warning(f"Initial connection failed: {e}")
            ijt_log.info("Attempting to connect again using original Server URL...")

            # Reinitialize client with original server_url
            self.client = Client(self.server_url)
            self.client.name = f"urn:{computer_name}:IJT:ConsoleClient"
            self.client.description = f"urn:{computer_name}:IJT:ConsoleClient"
            self.client.application_uri = f"urn:{computer_name}:IJT:ConsoleClient"
            self.client.product_uri = f"urn:IJT:ConsoleClient"

            try:
                await self.client.connect()
                await self.client.load_type_definitions()
                ijt_log.info(
                    f"Connected to OPC UA server via failover at {self.server_url}"
                )
            except Exception as e2:
                ijt_log.error(f"Failover connection also failed: {e2}")
                raise

    async def subscribe_to_events(self):
        try:
            root = self.client.get_root_node()
            server_node = await root.get_child(["0:Objects", "0:Server"])
            result_event_type, joining_event_type = await get_event_types(
                self.client, root
            )

            self.subscription = await self.client.create_subscription(100, self.handler)
            await self.subscription.subscribe_events(
                server_node,
                [result_event_type, joining_event_type],
                queuesize=200,
            )
            ijt_log.info(
                "Subscribed to ResultReadyEventType and JoiningSystemResultReadyEventType."
            )
        except Exception as e:
            ijt_log.error(f"Subscription failed: {e}")
            await self.cleanup()
            raise

    async def run_forever(self):
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            ijt_log.info("Run loop cancelled.")
        except Exception as e:
            ijt_log.warning(f"Unexpected error in run loop: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        try:
            if self.subscription:
                try:
                    await self.subscription.delete()
                    ijt_log.info("Subscription deleted.")
                except Exception as sub_err:
                    ijt_log.warning(f"Failed to delete subscription: {sub_err}")
                self.subscription = None

            # Add a short delay before disconnecting
            await asyncio.sleep(0.5)

            if self.client:
                try:
                    await self.client.disconnect()
                    ijt_log.info("Disconnected from OPC UA server.")
                except UaError as ua_err:
                    ijt_log.warning(f"UaError during disconnect: {ua_err}")
                except Exception as dis_err:
                    ijt_log.warning(f"Failed to disconnect client: {dis_err}")
                self.client = None
        except Exception as e:
            ijt_log.error(f"Cleanup error: {e}")
