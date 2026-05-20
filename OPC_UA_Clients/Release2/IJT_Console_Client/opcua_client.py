import asyncio
import logging
import os
import socket
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from asyncua import Client, ua
from asyncua.crypto import security_policies
from asyncua.ua.uaerrors import UaError

from event_handler import EventHandler
from event_types import get_event_types
from ijt_logger import ijt_log
from method_caller import OPCUAMethodCaller
from result_event_handler import ResultEventHandler

_OPCUA_TIMEOUT_S = 60
_SUBSCRIPTION_PERIOD_MS = 100
_QUEUE_SIZE = 200
_CONNECT_RETRIES_DEFAULT = "8"
_CONNECT_DELAY_DEFAULT = "1.0"
_CONNECT_MAX_DELAY_DEFAULT = "4.0"

# Reduce asyncua late-response noise during shutdown windows.
logging.getLogger("asyncua").setLevel(logging.CRITICAL)
logging.getLogger("asyncua.client.ua_client").setLevel(logging.CRITICAL)


UserIdentityKind = Literal["anonymous", "username", "x509"]


@dataclass(frozen=True)
class OPCUASecurityConfig:
    security_policy_uri: str | None = None
    security_mode: ua.MessageSecurityMode | None = None
    client_certificate_path: Path | None = None
    client_private_key_path: Path | None = None
    user_identity: UserIdentityKind = "anonymous"
    username: str | None = None
    password: str | None = None
    x509_certificate_path: Path | None = None
    x509_private_key_path: Path | None = None


_SECURITY_POLICY_CLASSES = {
    security_policies.SecurityPolicyBasic256Sha256.URI: security_policies.SecurityPolicyBasic256Sha256,
    security_policies.SecurityPolicyAes128Sha256RsaOaep.URI: security_policies.SecurityPolicyAes128Sha256RsaOaep,
    security_policies.SecurityPolicyAes256Sha256RsaPss.URI: security_policies.SecurityPolicyAes256Sha256RsaPss,
}


def validate_user_token_policy(
    endpoint: ua.EndpointDescription,
    token_type: ua.UserTokenType,
    token_name: str,
    expected_security_policy_uri: str,
) -> None:
    token = next(
        (policy for policy in endpoint.UserIdentityTokens if policy.TokenType == token_type),
        None,
    )
    if token is None:
        raise ValueError(f"Selected endpoint does not advertise a {token_name} user-token policy.")

    if expected_security_policy_uri == security_policies.SecurityPolicyNone.URI:
        raise ValueError(f"{token_name} user-token policy requires a secure endpoint policy.")

    token_policy_uri = token.SecurityPolicyUri or ""
    if token_policy_uri == security_policies.SecurityPolicyNone.URI:
        raise ValueError(
            f"{token_name} user-token policy must not use SecurityPolicy#None. "
            "Rebuild the IJT simulator package from source that registers concrete "
            f"{token_name} token policies for secure endpoints."
        )
    if token_policy_uri and token_policy_uri != expected_security_policy_uri:
        raise ValueError(
            f"{token_name} user-token policy URI "
            f"{token_policy_uri!r} does not match endpoint policy {expected_security_policy_uri!r}."
        )


def validate_x509_user_token_policy(endpoint: ua.EndpointDescription, expected_security_policy_uri: str) -> None:
    validate_user_token_policy(
        endpoint,
        ua.UserTokenType.Certificate,
        "X509 Certificate",
        expected_security_policy_uri,
    )


def validate_username_user_token_policy(endpoint: ua.EndpointDescription, expected_security_policy_uri: str) -> None:
    validate_user_token_policy(
        endpoint,
        ua.UserTokenType.UserName,
        "UserName",
        expected_security_policy_uri,
    )


def _preserve_test_artifacts() -> bool:
    return os.environ.get("IJT_PRESERVE_TEST_ARTIFACTS", "0").strip().lower() in {"1", "true", "yes", "on"}


class OPCUAClient:
    def __init__(self, server_url: str, security_config: OPCUASecurityConfig | None = None) -> None:
        self.server_url = server_url
        self.security_config = security_config or OPCUASecurityConfig()
        self._security_configured = False
        # 60-second service-call timeout — methods like SimulateJobResult fire
        # many separate OPC UA publish messages before returning; the default
        # asyncua 4-second window is far too short.
        self.client = Client(server_url, timeout=_OPCUA_TIMEOUT_S)
        self.sub_result_event = None
        self.sub_joining_event = None
        # Handlers are created inside subscribe_to_events() which runs in an async
        # context, allowing asyncio.create_task() to be used safely.
        self.handler_result_event = None
        self.handler_joining_event = None
        self.methods = OPCUAMethodCaller(self.client)

    def setup_client_metadata(self) -> None:
        computer_name = socket.getfqdn()
        self.client.name = f"urn:{computer_name}:IJT:ConsoleClient"  # type: ignore[union-attr]
        self.client.description = f"urn:{computer_name}:IJT:ConsoleClient"  # type: ignore[union-attr]
        self.client.application_uri = f"urn:{computer_name}:IJT:ConsoleClient"  # type: ignore[union-attr]
        self.client.product_uri = "urn:IJT:ConsoleClient"  # type: ignore[union-attr]

    async def connect(self):
        await self.clear_old_logs()
        self.setup_client_metadata()
        await self.configure_security()

        max_attempts = max(1, int(os.getenv("OPCUA_CONNECT_RETRIES", _CONNECT_RETRIES_DEFAULT)))
        base_backoff = max(0.2, float(os.getenv("OPCUA_CONNECT_DELAY_SEC", _CONNECT_DELAY_DEFAULT)))
        max_backoff = max(
            base_backoff,
            float(os.getenv("OPCUA_CONNECT_MAX_DELAY_SEC", _CONNECT_MAX_DELAY_DEFAULT)),
        )
        for attempt in range(1, max_attempts + 1):
            try:
                start_time = time.time()
                await self.client.connect()  # type: ignore[union-attr]
                await self.client.load_data_type_definitions()  # type: ignore[union-attr]
                duration = time.time() - start_time
                ijt_log.info(f"Connected to OPC UA server at {self.server_url} in {duration:.2f}s")
                return
            except Exception as e:
                ijt_log.warning(f"Connection attempt {attempt}/{max_attempts} failed for {self.server_url}: {e}")
                ijt_log.error(traceback.format_exc())
                if attempt < max_attempts:
                    backoff = min(max_backoff, base_backoff * (2 ** (attempt - 1)))
                    ijt_log.info(f"Retrying in {backoff:.1f} seconds...")
                    await asyncio.sleep(backoff)
                else:
                    ijt_log.error(f"All connection attempts failed for {self.server_url} after {max_attempts} tries.")
                    raise

    async def configure_security(self) -> None:
        if self._security_configured:
            return

        config = self.security_config
        if config.security_policy_uri and config.security_policy_uri != security_policies.SecurityPolicyNone.URI:
            policy_class = _SECURITY_POLICY_CLASSES.get(config.security_policy_uri)
            if policy_class is None:
                raise ValueError(f"Unsupported OPC UA security policy: {config.security_policy_uri}")
            if config.client_certificate_path is None or config.client_private_key_path is None:
                raise ValueError("Secure OPC UA connections require a client certificate and private key.")
            await self.client.set_security(
                policy_class,  # type: ignore[type-abstract]
                str(config.client_certificate_path),
                str(config.client_private_key_path),
                mode=config.security_mode or ua.MessageSecurityMode.SignAndEncrypt,
            )

        if config.user_identity == "username":
            if config.username is None or config.password is None:
                raise ValueError("UserName identity requires username and password.")
            await self.validate_configured_user_token_policy(
                config,
                ua.UserTokenType.UserName,
                "UserName",
            )
            self.client.set_user(config.username)
            self.client.set_password(config.password)
        elif config.user_identity == "x509":
            if config.x509_certificate_path is None or config.x509_private_key_path is None:
                raise ValueError("X509 identity requires a certificate and private key.")
            await self.client.load_client_certificate(str(config.x509_certificate_path))
            await self.client.load_private_key(config.x509_private_key_path)
            await self.validate_configured_user_token_policy(
                config,
                ua.UserTokenType.Certificate,
                "X509 Certificate",
            )
        elif config.user_identity != "anonymous":
            raise ValueError(f"Unsupported user identity kind: {config.user_identity}")

        self._security_configured = True

    async def validate_configured_user_token_policy(
        self,
        config: OPCUASecurityConfig,
        token_type: ua.UserTokenType,
        token_name: str,
    ) -> None:
        expected_policy_uri = config.security_policy_uri or security_policies.SecurityPolicyNone.URI
        expected_mode = config.security_mode or (
            ua.MessageSecurityMode.None_
            if expected_policy_uri == security_policies.SecurityPolicyNone.URI
            else ua.MessageSecurityMode.SignAndEncrypt
        )
        probe = Client(self.server_url, timeout=_OPCUA_TIMEOUT_S)
        endpoints = await probe.connect_and_get_server_endpoints()
        endpoint = next(
            (
                candidate
                for candidate in endpoints
                if candidate.SecurityPolicyUri == expected_policy_uri and candidate.SecurityMode == expected_mode
            ),
            None,
        )
        if endpoint is None:
            raise ValueError(f"Endpoint not found for policy={expected_policy_uri!r}, mode={expected_mode!r}.")
        validate_user_token_policy(endpoint, token_type, token_name, expected_policy_uri)

    async def validate_configured_x509_user_token_policy(self, config: OPCUASecurityConfig) -> None:
        await self.validate_configured_user_token_policy(
            config,
            ua.UserTokenType.Certificate,
            "X509 Certificate",
        )

    async def subscribe_to_events(self):
        try:
            # Handlers are created here (async context) so asyncio.create_task() works.
            self.handler_result_event = ResultEventHandler(self.server_url)
            self.handler_joining_event = EventHandler(None, self.server_url, self.client)

            root = self.client.get_root_node()  # type: ignore[union-attr]
            server_node = await root.get_child(["0:Objects", "0:Server"])

            (
                result_event_node,
                joining_result_event_node,
                joining_system_event_node,
            ) = await get_event_types(self.client, root)

            await self.client.load_data_type_definitions()  # type: ignore[union-attr]

            # Subscribe to Result and Joining Result Events
            if self.sub_result_event is None:
                self.sub_result_event = await self.client.create_subscription(  # type: ignore[union-attr]
                    _SUBSCRIPTION_PERIOD_MS, self.handler_result_event
                )
                await self.sub_result_event.subscribe_events(
                    server_node,
                    [result_event_node, joining_result_event_node],
                    queuesize=_QUEUE_SIZE,
                )

            # Subscribe to Joining System Events
            if self.sub_joining_event is None:
                self.sub_joining_event = await self.client.create_subscription(  # type: ignore[union-attr]
                    _SUBSCRIPTION_PERIOD_MS, self.handler_joining_event
                )
                await self.sub_joining_event.subscribe_events(
                    server_node,
                    [joining_system_event_node],
                    queuesize=_QUEUE_SIZE,
                )

            ijt_log.info("Subscribed to all relevant event types.")
        except Exception as e:
            ijt_log.error(f"Subscription failed: {e}")
            ijt_log.error(traceback.format_exc())
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
                        ijt_log.warning(f"Failed to delete {name} subscription: {sub_err}")
                        ijt_log.error(traceback.format_exc())

            self.sub_result_event = None
            self.sub_joining_event = None

            await asyncio.sleep(0.5)

            if self.client is not None:
                try:
                    await self.client.disconnect()
                    ijt_log.info("Disconnected from OPC UA server.")
                except UaError as ua_err:
                    if "No request found" in str(ua_err):
                        ijt_log.warning("Late server response ignored during shutdown.")
                    else:
                        ijt_log.warning(f"UaError during disconnect: {ua_err}")
                        ijt_log.error(traceback.format_exc())
                except Exception as dis_err:
                    ijt_log.warning(f"Failed to disconnect client: {dis_err}")
                    ijt_log.error(traceback.format_exc())
                finally:
                    self.client = None
            else:
                ijt_log.info("Client already cleaned up or not initialized.")
        except Exception as e:
            ijt_log.error(f"Cleanup error: {e}")
            ijt_log.error(traceback.format_exc())

    async def clear_old_logs(self):
        if _preserve_test_artifacts():
            return

        log_dir = Path("logs") / "results"
        if log_dir.exists():
            for file in log_dir.glob("*.json"):
                file.unlink()
        else:
            log_dir.mkdir()
