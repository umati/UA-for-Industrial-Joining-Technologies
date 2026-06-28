# OPC UA for Industrial Joining Technologies (IJT)

[![CI](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/ci.yml/badge.svg?branch=main&event=push)](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/ci.yml)
[![Integration](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/integration.yml/badge.svg?branch=main&event=push)](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/integration.yml)
[![CodeQL](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/codeql.yml/badge.svg?branch=main&event=push)](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/codeql.yml)

The **VDMA OPC UA Industrial Joining Technologies (IJT)** Working Group defines a standard
information model for joining technologies such as Tightening, Gluing, Riveting, Flow Drill
Fastening, and additional joining technologies. This repository provides reference implementations
of OPC UA IJT clients and servers, supporting documents, and self-testing tools.

## Contact

- **Author:** Mohit Agarwal - mohit.agarwal@atlascopco.com
- **Coordinator:** Bernd Heitzmann - bernd.heitzmann@vdma.eu

## Repository Contents

| Component | Purpose |
|-----------|---------|
| [IJT Server Simulator](OPC_UA_Servers/Release2) | Provides a local OPC UA IJT server simulator for demonstrations, client development, and interoperability testing |
| [IJT Web Client](OPC_UA_Clients/Release2/IJT_Web_Client) | Provides a browser-based client for exploring IJT data, events, assets, results, and traces |
| [IJT Console Client](OPC_UA_Clients/Release2/IJT_Console_Client) | Provides a command-line client for connecting to a server, subscribing to events, and calling IJT methods |
| [IJT C# Client](OPC_UA_Clients/Release2/IJT_CSharp_Client) | Provides a C#/.NET client and reusable generated OPC UA type libraries |
| [IJT Test Client](OPC_UA_Clients/Release2/IJT_Test_Client) | Provides a self-testing client for validating OPC UA IJT server behavior |

## Getting Started

- Start the **[IJT Server Simulator](OPC_UA_Servers/Release2)** and connect with any OPC UA client such as
  **UaExpert**, or use one of the reference clients in this repository.
  - **Default endpoint:** `opc.tcp://localhost:40451`

## Specifications and References

- [OPC UA IJT Group Presentation](IJT_Documents/OPC_UA_IJT_Group_Presentation.pdf)
- [OPC 40450-1 Joining - Online Reference](https://reference.opcfoundation.org/IJT/Base/v100/docs/)
- [OPC 40451-1 Tightening - Online Reference](https://reference.opcfoundation.org/IJT/Tightening/v200/docs/)
- [OPC Foundation IJT Page](https://opcfoundation.org/markets-collaboration/IJT/)
- [VDMA IJT Page](https://vdma.org/viewer/-/v2article/render/88084510)

## Security

To report a security vulnerability, see [SECURITY.md](SECURITY.md).
