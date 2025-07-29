from asyncua import ua
from typing import Any
import logging


def createCallStructure(argument: dict[str, Any]) -> Any:
    """
    This function creates the input call structures
    """

    value = argument["value"]
    # logging.info("value:")
    # logging.info(value)
    inp = 0

    # logging.info("argument - datatype")
    # logging.info(argument["dataType"])

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
            # logging.info(inp.__dict__)
        case _:
            inp = ua.Variant(value, ua.VariantType(argument["dataType"]))

    return inp
