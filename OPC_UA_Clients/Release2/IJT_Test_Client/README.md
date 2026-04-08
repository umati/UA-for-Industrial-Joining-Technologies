# IJT Test Client

## Contact
- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Overview

A Python pytest suite that validates an OPC UA server against the
**OPC UA Industrial Joining Technologies (IJT) Companion Specification**.
Tests cover address space structure, asset management, result retrieval,
event subscriptions, joining process management, joint management, and
§11.1 Conformance Units — all against a live running OPC UA IJT server.

## Prerequisites

- **Python 3.14+** — add to system `PATH`
- A running **OPC UA IJT Server** — see [OPC UA IJT Server Simulator](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2)
- Default endpoint: `opc.tcp://localhost:40451`

## Quick Start
- Run all tests: `python run_all_tests.py`

## Project Structure

```
IJT_Test_Client/
├── run_all_tests.py  # Entry point
├── conftest.py       # Shared pytest fixtures (server, client, namespace indices)
├── helpers/          # Node discovery, event collector, server manager
├── common/           # Connection + namespace registration tests
├── assets/           # Asset management structure and interfaces
├── results/          # Result management, retrieval, simulation
├── events/           # Event type hierarchy and subscriptions
├── joining_process/  # JoiningProcessManagement structure + methods
├── joint/            # JointManagement structure + methods
└── conformance/      # §11.1 Conformance Unit tests (CU-AM, CU-RM, CU-EM, CU-JP, CU-JT)
```
