# IJT Reference Clients

Release 2 reference clients for the OPC UA Industrial Joining Technologies (IJT) companion
specifications.

## Contact

- **Author:** Mohit Agarwal - mohit.agarwal@atlascopco.com

## Available Clients

| Client | Description | Technology |
|--------|-------------|------------|
| [IJT Web Client](IJT_Web_Client) | GUI reference client for visualizing OPC UA IJT server data, events, traces, assets, and results in a web browser | Python, WebSockets, Node.js |
| [IJT Console Client](IJT_Console_Client) | Command-line reference client for connecting to an OPC UA IJT server, subscribing to events, calling methods, and reading results | Python |
| [IJT C# Client](IJT_CSharp_Client) | C#/.NET reference client with an interactive client and reusable generated type libraries for the IJT companion specifications | C#/.NET |
| [IJT Test Client](IJT_Test_Client) | Self-Testing client for validating OPC UA IJT servers against the Industrial Joining Technologies (IJT) companion specifications | Python, pytest |

## OPC UA Server

- Use the [IJT Server Simulator](../../OPC_UA_Servers/Release2) for local testing.
  - Default OPC UA endpoint: `opc.tcp://localhost:40451`
