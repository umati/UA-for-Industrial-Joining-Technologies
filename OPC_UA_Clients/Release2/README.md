# IJT Reference Clients

## Contact
- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Overview
Reference clients for the **OPC UA Industrial Joining Technologies (IJT) Companion Specification**.

## IJT Web Client
- GUI client for visualization of IJT data and traces. Python (`asyncua`) backend and Node.js frontend.

## IJT Console Client
- Command-line client for core IJT operations, including subscriptions, method calls, and result parsing.

## IJT Test Client
- Conformance test suite for the IJT Companion Specification, built with Python `pytest`.

## IJT C# Client
- C#/.NET reference client based on the OPC Foundation .NET Standard SDK.

## Running Tests

Each client project contains a `run_all_tests.py` that can be used independently — the OPC UA server is launched automatically if needed:

```bash
python run_all_tests.py
```

The root `run_all_tests.py` orchestrates all suites in one command.

## OPC UA Reference Server
- Use the following [**OPC UA IJT Server Simulator**](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2) to connect from the **IJT Reference Clients**.
