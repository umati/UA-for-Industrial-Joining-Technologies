

def isInstanceOfClass(cls):
    """
    The best I could find to detect that something is an instance of a user defined class
    """
    return str(type(cls)).startswith("<class") and hasattr(cls, '__weakref__')

def serializeTuple(listOfTuples):
    """
    Serialize a special zipped list of key - values 
    """
    result = "{"
    first = True
    for pair in listOfTuples:
        if not first:
            result = result + ","
        first = False
        result = result + "\"" + pair[0] + "\":" + serializeValue(pair[1])
    return result + "}"

def serializeValue(value):
    """
    Serialize an value
    """
    # print(type(value).__name__)
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
        return "\"" + str(value).replace('\n', '\\n') + "\""

def serializeClassInstance(obj):
    """
    Serialize an instance of a class (or something implementing __dict___)
    """
    result = "\"pythonclass\":\"" + type(obj).__name__ + "\""
    # print(type(obj).__name__)
    dict = obj.__dict__
    for key, value in dict.items():
        # print(type(value).__name__)
        if key!="_freeze":
            result = result + ","
            result = result + "\"" + key + "\"" + ":" + serializeValue(value)
    return result    