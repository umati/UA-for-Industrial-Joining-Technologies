from asyncua import ua

def createCallStructure(argument):
    """
    This function creates the input call structures
    """

    value = argument["value"]
    print(value)
    inp = 0

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
          entityRow = row['value']
          entity = ua.EntityDataType()
          entity.Name = entityRow["Name"]
          entity.Description = entityRow["Description"]
          entity.EntityId = entityRow["EntityId"]
          entity.EntityOriginId = entityRow["EntityOriginId"]
          entity.IsExternal = entityRow["IsExternal"]
          entity.EntityType = entityRow["EntityType"]

          lst.append(entity)
        
        inp = ua.Variant(lst, ua.VariantType.ExtensionObject)
        print(inp.__dict__)
      case _:
        inp = ua.Variant(value, ua.VariantType(argument["dataType"]))
    
    return inp
