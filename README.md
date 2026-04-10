# OPC UA for Industrial Joining Technologies (IJT)

[![CI Required](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/ci-required.yml/badge.svg)](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/ci-required.yml)
[![CI Extended](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/ci-extended.yml/badge.svg)](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/ci-extended.yml)
[![CodeQL](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/codeql.yml/badge.svg)](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/codeql.yml)

The **VDMA OPC UA Industrial Joining Technologies (IJT)** Working Group defines a standard information model for **joining technologies** such as Tightening, Gluing, Riveting, Flow Drill Fastening, etc. This repository provides reference implementations of OPC UA IJT Clients and Servers.

## Contact
- Mohit Agarwal — mohit.agarwal@atlascopco.com
- Bernd Heitzmann — bernd.heitzmann@vdma.eu

## Clients & Servers

| Component | Description |
|-----------|-------------|
| [IJT Server Simulator](OPC_UA_Servers/Release2) | OPC UA server exposing the IJT information model |
| [IJT Web Client](OPC_UA_Clients/Release2/IJT_Web_Client) | GUI client — trace graphs, result visualization (Python + Node.js) |
| [IJT Console Client](OPC_UA_Clients/Release2/IJT_Console_Client) | Minimal reference client — event subscription and result parsing (Python) |
| [IJT Test Client](OPC_UA_Clients/Release2/IJT_Test_Client) | Conformance test suite against the IJT specification (Python pytest) |
| [IJT C# Client](OPC_UA_Clients/Release2/IJT_CSharp_Client) | Reference client using the OPC Foundation .NET Standard SDK |

## Specifications & References

- [OPC 40450-1 Joining — Online Reference](https://reference.opcfoundation.org/IJT/Base/v100/docs/)
- [OPC 40451-1 Tightening — Online Reference](https://reference.opcfoundation.org/IJT/Tightening/v200/docs/)
- [OPC Foundation IJT Page](https://opcfoundation.org/markets-collaboration/IJT/)
- [VDMA IJT Page](https://vdma.org/viewer/-/v2article/render/88084510)
- [IJT Documents](IJT_Documents)

## Test Suite

Run `python run_all_tests.py` — covers all clients, static analysis, and live tests.
