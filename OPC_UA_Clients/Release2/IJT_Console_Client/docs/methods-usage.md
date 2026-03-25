# Methods Usage — IJT Console Client

Quick reference for invoking OPC UA IJT methods via `main.py`.

## First Run

```powershell
python setup_client.py --url "opc.tcp://localhost:40451"
```

## Subsequent Method Calls

Activate the venv first:
```powershell
.\venv\Scripts\Activate.ps1
```

### Select Joint
```powershell
python main.py --origin-id= --joint-id Joint_1 --call select_joint --url "opc.tcp://localhost:40451"
```

### Enable Asset
```powershell
python main.py --url "opc.tcp://localhost:40451" --call enable_asset --enable true
```

### Start Selected Joining
```powershell
python main.py --url "opc.tcp://localhost:40451" --call start_selected_joining --deselect false
```
