# IJT Reference Clients

Release 2 reference clients for the OPC UA Industrial Joining Technologies (IJT) companion specifications.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Available Clients

| Client | Purpose | Technology |
|--------|---------|------------|
| [IJT Web Client](IJT_Web_Client) | Browser-based IJT data exploration | Python, WebSockets, Node.js |
| [IJT Console Client](IJT_Console_Client) | Command-line IJT client | Python |
| [IJT C# Client](IJT_CSharp_Client) | .NET reference client and type libraries | C#/.NET |
| [IJT Test Client](IJT_Test_Client) | IJT specification validation | Python, pytest |

## Quick Start

1. Run the [IJT Server Simulator](../../OPC_UA_Servers/Release2) for local testing.
2. Open the client you want to use.
3. Follow the client-specific README for setup and options.

**Default endpoint:** `opc.tcp://localhost:40451`

## Learn More

- [Shared contribution guide](../../docs/CONTRIBUTING.md)
