# MCP Server Setup Guide

## MongoDB
1. Install Node.js (which includes `npx`).

2. **Test Command (Optional):** Validate the connection in your terminal:
   `npx -y mongodb-mcp-server "mongodb://guest:guest@localhost:27017/?authSource=admin"`

3. Run the MCP server using the start button inside the `.vscode/mcp.json` file.

## RabbitMQ
1. Install Python.

2. Install `uv` (Python package manager):
   * **macOS / Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
   * **Windows (PowerShell):** `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

3. Validate that `uv` installed successfully by running: 
   `uv --version`
   *(Note: If the command is not recognized, completely close and reopen VS Code and your terminal to refresh your environment variables, then try again).*

4. Install the RabbitMQ MCP server globally: 
   `uv tool install amq-mcp-server-rabbitmq@latest`

5. Run the MCP server using the `.vscode/mcp.json` file.
   *(Note: The `mcp.json` explicitly forces `fastmcp<2.14.0` to bypass a known crashing bug with the `BearerAuthProvider` module in newer versions. Do not remove this version pin).*