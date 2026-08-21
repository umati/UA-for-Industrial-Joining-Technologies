# OPC UA for Industrial Joining Technologies (IJT)

[![CI](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/ci.yml/badge.svg?branch=main&event=push)](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/ci.yml)
[![Integration](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/integration.yml/badge.svg?branch=main&event=push)](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/integration.yml)
[![CodeQL](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/codeql.yml/badge.svg?branch=main&event=push)](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/workflows/codeql.yml)

The **VDMA OPC UA Industrial Joining Technologies (IJT)** Working Group defines a standard
information model for joining technologies such as Tightening, Gluing, Riveting, Flow Drill
Fastening, and additional joining technologies. This repository provides reference implementations
of OPC UA IJT clients and servers, supporting documents, and specification testing tools.

## Contact

- **Author:** Mohit Agarwal - mohit.agarwal@atlascopco.com
- **Coordinator:** Bernd Heitzmann - bernd.heitzmann@vdma.eu

## Repository Contents

| Component | Purpose | Example Use |
|-----------|---------|-------------|
| [IJT Server Simulator](OPC_UA_Servers/Release2) | Provides a local OPC UA IJT server simulator | Demonstrations, client development, interoperability testing |
| [IJT Web Client](OPC_UA_Clients/Release2/IJT_Web_Client) | Provides a browser-based client for IJT data | Visual inspection of data, events, assets, results, and traces |
| [IJT Console Client](OPC_UA_Clients/Release2/IJT_Console_Client) | Provides a command-line IJT client | Scripting, automation, and direct server interaction |
| [IJT C# Client](OPC_UA_Clients/Release2/IJT_CSharp_Client) | Provides a C#/.NET client and reusable type libraries | Building .NET applications against IJT |
| [IJT Test Client](OPC_UA_Clients/Release2/IJT_Test_Client) | Provides a specification test client | Specification testing for OPC UA IJT servers |

## Quick Start

### Run the IJT Server Simulator

The easiest way to explore IJT is to run the server simulator locally and connect with an OPC UA client:

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/umati/UA-for-Industrial-Joining-Technologies.git
cd UA-for-Industrial-Joining-Technologies

# Start the server simulator
cd OPC_UA_Servers/Release2
python run_server.py
```

**Default endpoint:** `opc.tcp://localhost:40451`

**Tip:** Use any OPC UA client against the endpoint if you already have one installed.

### Explore the Reference Implementations

Use any of the provided clients to connect to the running server:

1. **[IJT Web Client](OPC_UA_Clients/Release2/IJT_Web_Client)** — Browser-based interface for data, events, assets, results, and traces
2. **[IJT Console Client](OPC_UA_Clients/Release2/IJT_Console_Client)** — Command-line tool for scripting and automation
3. **[IJT C# Client](OPC_UA_Clients/Release2/IJT_CSharp_Client)** — .NET client and reusable OPC UA type libraries
4. **[IJT Test Client](OPC_UA_Clients/Release2/IJT_Test_Client)** — Specification testing

## Contributing & Development

For development setup, testing, and contribution guidelines, see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

For detailed technical information on runtime configuration, Docker, troubleshooting, and advanced testing, see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Specifications and References

- [OPC UA IJT Group Presentation](IJT_Documents/OPC_UA_IJT_Group_Presentation.pdf)
- [OPC 40450-1 Joining - Online Reference](https://reference.opcfoundation.org/IJT/Base/v100/docs/)
- [OPC 40451-1 Tightening - Online Reference](https://reference.opcfoundation.org/IJT/Tightening/v200/docs/)
- [OPC Foundation IJT Page](https://opcfoundation.org/markets-collaboration/IJT/)
- [VDMA IJT Page](https://vdma.org/viewer/-/v2article/render/88084510)

## Security

To report a security vulnerability, see [SECURITY.md](SECURITY.md).
