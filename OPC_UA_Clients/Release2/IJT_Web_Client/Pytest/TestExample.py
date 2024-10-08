import pytest
import asyncio
import sys    

sys.path.append("..")

from Python.Connection import Connection
from Pytest.TestSubscriptionHandler import SubHandler, combinedNameFilter

# Make sure you are in the venv
# python -m pytest Pytest/TestExample.py


@pytest.fixture
async def connect(url):
      connection = Connection(url, None)
      await connection.connect()
      return connection

@pytest.fixture
async def subscribe(connection, cond):
      handler= SubHandler(cond) 
      await connection.subscribe({"eventtype" : ["joiningsystemevent"]}, handler)
      return asyncio.wait_for(handler.getFuture(), timeout=10)

@pytest.mark.asyncio
async def test_opcua_client(connect, subscribe):
    def cond(ev):
        return combinedNameFilter(ev, 'SystemConditionClassType', ['AssetConnectedConditionClassType'])
    url = 'opc.tcp://10.46.19.106:40451'
    
    try:
      #connection = Connection(url, None)
      #await connection.connect()

      #handler= SubHandler(cond) 
      #await connection.subscribe({"eventtype" : ["joiningsystemevent"]}, handler)
      #timedFuture = asyncio.wait_for(handler.getFuture(), timeout=10)

      connection = connect(url, cond)
      timedFuture = subscribe(connection, cond)

      call = {
          'objectnode': {
              'Identifier': 'TighteningSystem/Simulations/SimulateEventsAndConditions', 
              'NamespaceIndex': '1'}, 
          'methodnode': {
              'Identifier': 'TighteningSystem/Simulations/SimulateEventsAndConditions/SimulateEvents', 
              'NamespaceIndex': '1'}, 
          'arguments': [
              {'dataType': 7, 'value': 1} # 1 means 'Tool connected' simulation
          ]}
      await connection.methodcall(call)

      eventRaw = await timedFuture

      event = eventRaw.get_event_props_as_fields_dict()

      # Test joining technology
      assert event['JoiningSystemEventContent/JoiningTechnology'].Value.Text == 'Tightening'

      # test severity
      assert event['Severity'].Value == 1001  # Severity of event should be 100

      #Test message
      assert event['Message'].Value.Text == 'Tool Connected' # Message of event should be 'Tool Connected'

      # Test associatedEntities
      associatedEntities = event['JoiningSystemEventContent/AssociatedEntities'].Value
      productInstanceNr = 0
      for entity in associatedEntities:
          if entity.EntityType == 4:
              productInstanceNr = productInstanceNr+1
      assert productInstanceNr == 1 # Exactly one associatedEntity for productInstanceUri

      await connection.terminate()

    except asyncio.TimeoutError:
      assert 1==0 # No answer in 10 seconds
      await connection.terminate()


if __name__ == "__main__":
    asyncio.run(test_opcua_client())
