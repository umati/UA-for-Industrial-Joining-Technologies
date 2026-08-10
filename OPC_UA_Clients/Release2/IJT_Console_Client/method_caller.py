import traceback

from asyncua import ua

from ijt_logger import ijt_log
from utils import read_tool_identifier


class OPCUAMethodCaller:
    def __init__(self, client):
        self.client = client

    @staticmethod
    def _parse_outputs(ret):
        status = None
        message = None

        if isinstance(ret, (tuple, list)):
            if len(ret) >= 1:
                try:
                    status = int(ret[0])
                except (ValueError, TypeError) as e:
                    ijt_log.warning(f"Could not parse method return status from {ret[0]!r}: {e}")
                    status = None
            if len(ret) >= 2:
                msg = ret[1]
                message = getattr(msg, "Text", str(msg))

        return status, message

    @staticmethod
    def _normalize_method_result(ret):
        status, message = OPCUAMethodCaller._parse_outputs(ret)
        return {
            "status": status,
            "status_message": message,
            "raw": ret,
        }

    async def _read_product_instance_uri(self):
        product_instance_uri = await read_tool_identifier(self.client)
        if not product_instance_uri:
            return None
        return str(product_instance_uri)

    @staticmethod
    def _extract_joint_list(ret):
        if isinstance(ret, (tuple, list)) and len(ret) >= 1 and isinstance(ret[0], list):
            return ret[0]
        return []

    @staticmethod
    def _parse_status_after_items(ret):
        if isinstance(ret, (tuple, list)) and len(ret) >= 3:
            return OPCUAMethodCaller._parse_outputs((ret[1], ret[2]))
        return OPCUAMethodCaller._parse_outputs(ret)

    async def get_joint_list(self, object_nodeid: str, method_nodeid: str):
        """Return the current joint list for the active tool.

        This mirrors the Web Client method defaults flow: first resolve the live
        Tool.ProductInstanceUri, then call JointManagement/GetJointList so demo
        applications can discover usable JointIds before mapping them to joining
        process selections.
        """
        try:
            product_instance_uri = await self._read_product_instance_uri()
            if not product_instance_uri:
                ijt_log.error("GetJointList failed: ProductInstanceUri is NULL")
                return None

            obj = self.client.get_node(object_nodeid)
            mth = self.client.get_node(method_nodeid)
            args = [ua.Variant(product_instance_uri, ua.VariantType.String)]

            ijt_log.info(f"Calling GetJointList: PIUri={product_instance_uri}")
            ret = await obj.call_method(mth, *args)
            status, message = self._parse_status_after_items(ret)
            return {
                "status": status,
                "status_message": message,
                "joints": self._extract_joint_list(ret),
                "raw": ret,
            }
        except Exception as e:
            ijt_log.error(f"GetJointList failed: {e}")
            ijt_log.error(traceback.format_exc())
            return None

    async def select_joint(
        self,
        object_nodeid: str,
        method_nodeid: str,
        joint_id: str,
        joint_origin_id: str | None = None,  # optional
    ):
        try:
            # 1) Auto-load ProductInstanceUri (required)
            product_instance_uri = await self._read_product_instance_uri()
            if not product_instance_uri:
                ijt_log.error("SelectJoint failed: ProductInstanceUri is NULL")
                return None

            obj = self.client.get_node(object_nodeid)
            mth = self.client.get_node(method_nodeid)

            # 3) Build arguments (3 input args required by OPC UA method)
            args = [
                ua.Variant(product_instance_uri, ua.VariantType.String),
                ua.Variant(joint_id, ua.VariantType.String),
                ua.Variant(joint_origin_id or "", ua.VariantType.String),
            ]

            ijt_log.info(
                f"Calling SelectJoint: PIUri={product_instance_uri}, JointId={joint_id}, Origin={joint_origin_id!r}"
            )

            ret = await obj.call_method(mth, *args)
            return self._normalize_method_result(ret)

        except Exception as e:
            ijt_log.error(f"SelectJoint failed: {e}")
            ijt_log.error(traceback.format_exc())
            return None

    async def enable_asset(self, object_nodeid, method_nodeid, enable: bool):
        try:
            pi = await self._read_product_instance_uri()
            if not pi:
                ijt_log.error("ProductInstanceUri is NULL")
                return None

            obj = self.client.get_node(object_nodeid)
            mth = self.client.get_node(method_nodeid)

            args = [
                ua.Variant(pi, ua.VariantType.String),
                ua.Variant(bool(enable), ua.VariantType.Boolean),
            ]

            ijt_log.info(f"Calling EnableAsset: PIUri={pi}, enable={enable}")
            ret = await obj.call_method(mth, *args)

            return self._normalize_method_result(ret)

        except Exception as e:
            ijt_log.error(f"EnableAsset failed: {e}")
            ijt_log.error(traceback.format_exc())
            return None

    async def start_selected_joining(self, object_nodeid, method_nodeid, deselect_after_joining: bool):
        try:
            pi = await self._read_product_instance_uri()
            if not pi:
                ijt_log.error("ProductInstanceUri is NULL")
                return None

            obj = self.client.get_node(object_nodeid)
            mth = self.client.get_node(method_nodeid)

            args = [
                ua.Variant(pi, ua.VariantType.String),
                ua.Variant(bool(deselect_after_joining), ua.VariantType.Boolean),
            ]
            ijt_log.info(f"Calling StartSelectedJoining: PIUri={pi}, deselect={deselect_after_joining}")
            ret = await obj.call_method(mth, *args)
            ret = await obj.call_method(mth, *args)

            return self._normalize_method_result(ret)

        except Exception as e:
            ijt_log.error(f"StartSelectedJoining failed: {e}")
            ijt_log.error(traceback.format_exc())
            return None
