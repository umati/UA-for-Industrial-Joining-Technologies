from typing import Any
from Python.ijt_logger import ijt_log
from datetime import datetime as std_datetime
from Lib import datetime as custom_datetime


def isInstanceOfClass(cls: Any) -> bool:
    """
    The best I could find to detect that something is an instance of a user defined class
    """
    return str(type(cls)).startswith("<class") and hasattr(cls, "__weakref__")


def serializeTuple(listOfTuples: list[tuple[str, Any]]) -> str:
    """
    Serialize a special zipped list of key - values
    """
    result = "{"
    first = True
    for pair in listOfTuples:
        if not first:
            result = result + ","
        first = False
        result = result + '"' + pair[0] + '":' + serializeValue(pair[1])
    return result + "}"


def serializeValue(value: Any) -> str:
    """
    Serialize an value
    """
    # ijt_log.info(type(value).__name__)
    if isInstanceOfClass(value):
        return "{" + serializeClassInstance(value) + "}"
    elif value == None:
        return "null"
    elif isinstance(value, list):
        result = "["
        first = True
        for item in value:
            if not first:
                result = result + ","
            first = False
            result = result + serializeValue(item)
        return result + "]"
    else:
        return '"' + str(value).replace("\n", "\\n") + '"'


def serializeClassInstance(obj: Any) -> str:
    """
    Serialize an instance of a class (or something implementing __dict___)
    """
    result = '"pythonclass":"' + type(obj).__name__ + '"'
    # ijt_log.info(type(obj).__name__)
    dict = obj.__dict__
    for key, value in dict.items():
        # ijt_log.info(type(value).__name__)
        if key != "_freeze":
            result = result + ","
            result = result + '"' + key + '"' + ":" + serializeValue(value)
    return result


def serializeFullEvent(value: Any) -> Any:
    if isInstanceOfClass(value):
        return serializeClassInstanceAsDict(value)
    elif value is None:
        return None
    elif isinstance(value, list):
        return [serializeFullEvent(item) for item in value]
    elif isinstance(value, dict):
        return {k: serializeFullEvent(v) for k, v in value.items()}
    elif isinstance(value, std_datetime):
        return value.isoformat()
    elif isinstance(value, (str, int, float, bool)):
        return value
    else:
        return str(value)


def serializeClassInstanceAsDict(obj: Any) -> dict:
    result = {"pythonclass": type(obj).__name__}
    dict_obj = obj.__dict__
    for key, value in dict_obj.items():
        if key != "_freeze":
            result[key] = serializeFullEvent(value)
    return result
