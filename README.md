# OPC UA for Industrial Joining Technologies (IJT)

[![CI](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/ci.yml/badge.svg)](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/ci.yml)
[![Integration](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/integration.yml/badge.svg)](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/integration.yml)
[![CodeQL](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/codeql.yml/badge.svg)](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/codeql.yml)

The **VDMA OPC UA Industrial Joining Technologies (IJT)** Working Group defines a standard information model for **joining technologies** such as Tightening, Gluing, Riveting, Flow Drill Fastening, etc. This repository provides reference implementations of OPC UA IJT Clients and Servers.

## Security

To report a security vulnerability, see [SECURITY.md](SECURITY.md).

## Contact
- Mohit Agarwal — mohit.agarwal@atlascopco.com
- Bernd Heitzmann — bernd.heitzmann@vdma.eu

## Clients & Servers

| Component | Description |
|-----------|-------------|
| [IJT Server Simulator](OPC_UA_Servers/Release2) | OPC UA server for IJT information models |
| [IJT Web Client](OPC_UA_Clients/Release2/IJT_Web_Client) | GUI client for visualization of IJT data and traces |
| [IJT Console Client](OPC_UA_Clients/Release2/IJT_Console_Client) | Command-line client for core IJT operations (for example, subscriptions and method calls) |
| [IJT Test Client](OPC_UA_Clients/Release2/IJT_Test_Client) | Conformance test suite for the IJT Companion Specification |
| [IJT C# Client](OPC_UA_Clients/Release2/IJT_CSharp_Client) | C#/.NET reference client based on the OPC Foundation .NET Standard SDK |

## Specifications & References

- [IJT Documents](IJT_Documents)
- [OPC 40450-1 Joining — Online Reference](https://reference.opcfoundation.org/IJT/Base/v100/docs/)
- [OPC 40451-1 Tightening — Online Reference](https://reference.opcfoundation.org/IJT/Tightening/v200/docs/)
- [OPC Foundation IJT Page](https://opcfoundation.org/markets-collaboration/IJT/)
- [VDMA IJT Page](https://vdma.org/viewer/-/v2article/render/88084510)

## Test Suite

Run `python run_all_tests.py` — covers all clients, static analysis, and live tests.
