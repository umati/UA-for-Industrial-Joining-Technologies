import asyncio
import traceback
import socket
from pathlib import Path
from asyncua.ua.uaerrors import UaError
from asyncua import Client
from result_event_handler import ResultEventHandler
from event_handler import EventHandler
from ijt_logger import ijt_log
from event_types import get_event_types


class OPCUAEventClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.client = Client(server_url)
        self.sub_result_event = None
        self.sub_joining_event = None
        self.handler_result_event = ResultEventHandler(server_url, self.client)
        self.handler_joining_event = EventHandler(None, server_url, self.client)

    def setup_client_metadata(self):
        computer_name = socket.getfqdn()
        self.client.name = f"urn:{computer_name}:IJT:ConsoleClient"
        self.client.description = f"urn:{computer_name}:IJT:ConsoleClient"
        self.client.application_uri = f"urn:{computer_name}:IJT:ConsoleClient"
        self.client.product_uri = "urn:IJT:ConsoleClient"

    async def connect(self):
        # Clear old log files
        await self.clear_old_logs()

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                self.setup_client_metadata()
                await self.client.connect()
                await self.client.load_type_definitions()
                ijt_log.info(f"Connected to OPC UA server at {self.server_url}")
                return
            except Exception as e:
                ijt_log.warning(f"Connection attempt {attempt} failed: {e}")
                ijt_log.error(traceback.format_exc())

                if attempt < max_attempts:
                    backoff = 2**attempt
                    ijt_log.info(f"Retrying in {backoff} seconds...")
                    await asyncio.sleep(backoff)
                else:
                    ijt_log.info("Attempting failover connection...")

                    # Reinitialize client with original server_url
                    self.client = Client(self.server_url)
                    self.setup_client_metadata()

                    try:
                        await self.client.connect()
                        await self.client.load_type_definitions()
                        ijt_log.info(
                            f"Connected to OPC UA server via failover at {self.server_url}"
                        )
                        return
                    except Exception as e2:
                        ijt_log.error(f"Failover connection also failed: {e2}")
                        ijt_log.error(traceback.format_exc())
                        raise

        # Clear old log files
        await self.clear_old_logs()
        self.setup_client_metadata()

        try:
            await self.client.connect()
            await self.client.load_type_definitions()
            ijt_log.info(f"Connected to OPC UA server at {self.server_url}")
        except Exception as e:
            ijt_log.warning(f"Initial connection failed: {e}")
            ijt_log.info("Attempting to connect again using original Server URL...")

            # Reinitialize client with original server_url
            self.client = Client(self.server_url)
            self.setup_client_metadata()

            try:
                await self.client.connect()
                await self.client.load_type_definitions()
                ijt_log.info(
                    f"Connected to OPC UA server via failover at {self.server_url}"
                )
            except Exception as e2:
                ijt_log.error(f"Failover connection also failed: {e2}")
                ijt_log.error(traceback.format_exc())
                raise

    async def subscribe_to_events(self):
        try:
            root = self.client.get_root_node()
            server_node = await root.get_child(["0:Objects", "0:Server"])

            ns_machinery_result = await self.client.get_namespace_index(
                "http://opcfoundation.org/UA/Machinery/Result/"
            )
            ns_joining_base = await self.client.get_namespace_index(
                "http://opcfoundation.org/UA/IJT/Base/"
            )

            result_event_node = await self.client.nodes.root.get_child(
                [
                    "0:Types",
                    "0:EventTypes",
                    "0:BaseEventType",
                    f"{ns_machinery_result}:ResultReadyEventType",
                ]
            )
            joining_result_event_node = await self.client.nodes.root.get_child(
                [
                    "0:Types",
                    "0:EventTypes",
                    "0:BaseEventType",
                    f"{ns_machinery_result}:ResultReadyEventType",
                    f"{ns_joining_base}:JoiningSystemResultReadyEventType",
                ]
            )
            joining_system_event_node = await self.client.nodes.root.get_child(
                [
                    "0:Types",
                    "0:EventTypes",
                    "0:BaseEventType",
                    f"{ns_joining_base}:JoiningSystemEventType",
                ]
            )

            await self.client.load_data_type_definitions()

            # Subscribe to Result and Joining Result Events
            if self.sub_result_event is None:
                self.sub_result_event = await self.client.create_subscription(
                    100, self.handler_result_event
                )
            await self.sub_result_event.subscribe_events(
                server_node,
                [result_event_node, joining_result_event_node],
                queuesize=200,
            )

            # Subscribe to Joining System Events
            if self.sub_joining_event is None:
                self.sub_joining_event = await self.client.create_subscription(
                    100, self.handler_joining_event
                )
            await self.sub_joining_event.subscribe_events(
                server_node, [joining_system_event_node], queuesize=200
            )

            ijt_log.info("Subscribed to all relevant event types.")
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
            ijt_log.error(traceback.format_exc())
        finally:
            await self.cleanup()

    async def cleanup(self):
        try:
            for sub, name in [
                (self.sub_result_event, "ResultEvent"),
                (self.sub_joining_event, "JoiningEvent"),
            ]:
                if sub:
                    try:
                        await sub.delete()
                        ijt_log.info(f"{name} subscription deleted.")
                    except Exception as sub_err:
                        ijt_log.warning(
                            f"Failed to delete {name} subscription: {sub_err}"
                        )
                        ijt_log.error(traceback.format_exc())

            self.sub_result_event = None
            self.sub_joining_event = None

            await asyncio.sleep(0.5)

            if self.client and getattr(self.client, "_connected", False):
                try:
                    await self.client.disconnect()
                    ijt_log.info("Disconnected from OPC UA server.")
                except UaError as ua_err:
                    ijt_log.warning(f"UaError during disconnect: {ua_err}")
                    ijt_log.error(traceback.format_exc())
                except Exception as dis_err:
                    ijt_log.warning(f"Failed to disconnect client: {dis_err}")
                    ijt_log.error(traceback.format_exc())
                finally:
                    self.client = None
            else:
                ijt_log.warning("Client not connected. Skipping disconnect.")
        except Exception as e:
            ijt_log.error(f"Cleanup error: {e}")
            ijt_log.error(traceback.format_exc())

    async def clear_old_logs(self):
        log_dir = Path("result_logs")
        if log_dir.exists():
            for file in log_dir.glob("*.json"):
                file.unlink()
        else:
            log_dir.mkdir()
