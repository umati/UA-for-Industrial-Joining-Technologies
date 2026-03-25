"""Helper script: browse the live OPC UA server and print all callable methods + args."""
import asyncio
from asyncua import Client, ua


async def main():
    client = Client("opc.tcp://localhost:40451", timeout=10)
    await client.connect()
    await client.load_data_type_definitions()

    methods = []

    async def recurse(node, path, depth=0):
        if depth > 8:
            return
        try:
            children = await node.get_children()
        except Exception:
            return
        for child in children:
            try:
                nc = await child.read_node_class()
                bn = await child.read_browse_name()
                child_path = path + "/" + bn.Name
                if nc == ua.NodeClass.Method:
                    parent = await child.get_parent()
                    parent_bn = await parent.read_browse_name()
                    args_info = []
                    try:
                        for prop in await child.get_children():
                            pbn = await prop.read_browse_name()
                            if pbn.Name == "InputArguments":
                                for a in await prop.get_value():
                                    args_info.append(
                                        f"{a.Name}(type={a.DataType.Identifier})"
                                    )
                    except Exception:
                        pass
                    methods.append({
                        "name": bn.Name,
                        "nodeid": str(child.nodeid),
                        "parent_nodeid": str(parent.nodeid),
                        "parent_name": parent_bn.Name,
                        "path": child_path,
                        "args": args_info,
                    })
                elif nc in (ua.NodeClass.Object, ua.NodeClass.ObjectType):
                    await recurse(child, child_path, depth + 1)
            except Exception:
                continue

    root = await client.nodes.root.get_child(["0:Objects"])
    await recurse(root, "Objects")
    await client.disconnect()

    for m in sorted(methods, key=lambda x: x["name"]):
        print(f"METHOD: {m['name']}")
        print(f"  NodeId      : {m['nodeid']}")
        print(f"  Parent      : {m['parent_nodeid']}  ({m['parent_name']})")
        print(f"  Path        : {m['path']}")
        print(f"  InputArgs   : {m['args']}")
        print()


asyncio.run(main())
