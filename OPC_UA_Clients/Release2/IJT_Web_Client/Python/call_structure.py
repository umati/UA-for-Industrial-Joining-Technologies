from asyncua import ua
from typing import Any
from Python.ijt_logger import ijt_log


def createCallStructure(argument: dict[str, Any]) -> Any:
    """
    This function creates the input call structures
    """

    value = argument["value"]
    # ijt_log.info("value:")
    # ijt_log.info(value)
    inp = 0

    # ijt_log.info("argument - datatype")
    # ijt_log.info(argument["dataType"])

    match argument["dataType"]:
        case 3029:
            inp = ua.JoiningProcessIdentificationDataType()
            arg0 = value[0]
            inp.JoiningProcessId = arg0["value"]
            arg1 = value[1]
            inp.JoiningProcessOriginId = arg1["value"]
            arg2 = value[2]
            inp.SelectionName = arg2["value"]
        case 3010:
            lst = []

            for row in value:
                entityRow = row["value"]
                entity = ua.EntityDataType()
                entity.Name = entityRow["Name"]
                entity.Description = entityRow["Description"]
                entity.EntityId = entityRow["EntityId"]
                entity.EntityOriginId = entityRow["EntityOriginId"]
                entity.IsExternal = entityRow["IsExternal"]
                entity.EntityType = entityRow["EntityType"]

                lst.append(entity)

            inp = ua.Variant(lst, ua.VariantType.ExtensionObject)
            # ijt_log.info(inp.__dict__)
        case _:
            ijt_log.warning(
                f"[createCallStructure] Unknown dataType: {argument['dataType']}, using generic Variant"
            )

            # fallback mapping
            mapping = {
                1: ua.VariantType.Boolean,
                3: ua.VariantType.Byte,
                4: ua.VariantType.Float,
                5: ua.VariantType.Double,
                7: ua.VariantType.Int32,
                8: ua.VariantType.Int64,
                9: ua.VariantType.UInt64,
                10: ua.VariantType.Byte,
                11: ua.VariantType.UInt32,
                12: ua.VariantType.String,
                13: ua.VariantType.String,
                31918: ua.VariantType.String,  # TrimmedString
            }

            variant_type = mapping.get(argument["dataType"], ua.VariantType.String)
            inp = ua.Variant(value, variant_type)

    return inp
