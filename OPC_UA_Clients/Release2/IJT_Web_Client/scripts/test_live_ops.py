#!/usr/bin/env python
"""Test live OPC UA operations"""
import asyncio

OPCUA_ENDPOINT = "opc.tcp://localhost:40451"
IJT_NAMESPACE_URI = "http://opcfoundation.org/UA/IJT/Base/"


async def live_test():
    from asyncua import Client
    
    results = {}
    client = None
    
    try:
        # Test 1: Connect
        print('[1/5] Testing connect...')
        client = Client(OPCUA_ENDPOINT, timeout=10)
        await client.connect()
        print(f'  Connect: OK')
        results['connect'] = True
        
        # Test 2: Load data types
        print('[2/5] Loading data type definitions...')
        await client.load_data_type_definitions()
        print(f'  Data types loaded: OK')
        results['data_types'] = True
        
        # Test 3: Get Namespaces
        print('[3/5] Testing namespaces...')
        ns_array = await client.get_namespace_array()
        ns_ok = len(ns_array) > 0
        ijt_found = any(IJT_NAMESPACE_URI in uri for uri in ns_array)
        print(f'  Namespaces: {len(ns_array)} total, IJT found: {ijt_found}')
        results['namespaces'] = ns_ok
        results['ijt_namespace'] = ijt_found
        
        # Test 4: Read server time
        print('[4/5] Testing read (server time)...')
        node = client.get_node("ns=0;i=2258")
        value = await node.read_value()
        read_ok = value is not None
        print(f'  Read server time: {str(value)[:40]}...')
        results['read'] = read_ok
        
        # Test 5: Browse root
        print('[5/5] Testing browse (Objects)...')
        objects = await client.nodes.root.get_child(["0:Objects"])
        children = await objects.get_children()
        browse_ok = len(children) > 0
        print(f'  Browse Objects: {len(children)} children')
        results['browse'] = browse_ok
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
        results['error'] = str(e)
    finally:
        if client:
            try:
                await client.disconnect()
                print('Disconnect: OK')
            except Exception as e:
                print(f'Disconnect error: {e}')
    
    return results


if __name__ == '__main__':
    results = asyncio.run(live_test())
    print()
    print('=' * 60)
    print('LIVE OPC UA OPERATIONS TEST SUMMARY')
    print('=' * 60)
    for test, passed in results.items():
        if test != 'error':
            status = 'PASS' if passed else 'FAIL'
            print(f'{test:20s}: {status}')

    all_pass = all(v for k, v in results.items() if k != 'error')
    print()
    print('OVERALL:', 'PASS' if all_pass else 'FAIL')
