async def get_event_types(client, root):
    ns_result = await client.get_namespace_index(
        "http://opcfoundation.org/UA/Machinery/Result/"
    )
    ns_joining = await client.get_namespace_index(
        "http://opcfoundation.org/UA/IJT/Base/"
    )

    result_event_type = await root.get_child(
        [
            "0:Types",
            "0:EventTypes",
            "0:BaseEventType",
            f"{ns_result}:ResultReadyEventType",
        ]
    )
    joining_event_type = await root.get_child(
        [
            "0:Types",
            "0:EventTypes",
            "0:BaseEventType",
            f"{ns_result}:ResultReadyEventType",
            f"{ns_joining}:JoiningSystemResultReadyEventType",
        ]
    )
    return result_event_type, joining_event_type
