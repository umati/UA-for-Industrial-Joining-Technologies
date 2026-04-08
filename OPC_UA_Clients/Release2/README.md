# IJT Reference Clients

## Contact
- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Overview
OPC UA Reference Clients with complete source code demonstrating how to consume data from an OPC UA server based on the **IJT Companion Specifications**.

## IJT Web Client
- A GUI-based client for understanding and demonstrating IJT concepts — Trace Graphs, Combined Result visualization, and more. Python (`asyncua`) backend, Node.js frontend.

## IJT Console Client
- This is a simple console client useful for integration of automated testing and evaluation of Result performance. It demonstrates a simple way to consume the Results and parse them in JSON.

## IJT Test Client
- A Python pytest suite that validates an OPC UA server against the IJT Companion Specification. Covers address space structure, asset management, result retrieval, event subscriptions, joining process management, joint management, and §11.1 Conformance Units.

## IJT C# Client
- A C# OPC UA client example built with the OPC Foundation .NET Standard SDK. Demonstrates subscribing to result events, calling result methods (`GetLatestResult`, `GetResultById`), subscribing to variables, and managing assets and joining processes.

## Running Tests

Each client project contains a `run_all_tests.py` that can be used independently — the OPC UA server is launched automatically if needed:

```bash
python run_all_tests.py
```

The root `run_all_tests.py` orchestrates all suites in one command.

## OPC UA Reference Server
- Use the following [**OPC UA IJT Server Simulator**](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2) to connect from the **IJT Reference Clients**.
