# ChatGPT Desktop Setup

ChatGPT Desktop can load local MCP servers from its MCP config file. TrueMemory
adds a stdio MCP entry for `truememory` there.

ChatGPT Desktop does not expose TrueMemory lifecycle hooks, so this integration
provides MCP tools but not automatic session-start recall or session-end
conversation extraction.

## Prerequisites

- ChatGPT Desktop installed
- TrueMemory installed: `uv tool install truememory`
- Python 3.10+

## Automatic Setup

```bash
truememory-ingest setup --cli chatgpt
```

This writes:

```json
{
  "mcpServers": {
    "truememory": {
      "command": "/path/to/python",
      "args": ["-m", "truememory.mcp_server"]
    }
  }
}
```

On macOS the config path is:

```text
~/Library/Application Support/com.openai.chat/mcp.json
```

Fully quit and reopen ChatGPT Desktop after setup.

## Manual Setup

Add this to `~/Library/Application Support/com.openai.chat/mcp.json`:

```json
{
  "mcpServers": {
    "truememory": {
      "command": "/path/to/python",
      "args": ["-m", "truememory.mcp_server"]
    }
  }
}
```

Find your Python path:

```bash
python3 -c "import sys; print(sys.executable)"
```

## Limitations

- ChatGPT Desktop exposes MCP tools, not lifecycle hooks.
- Automatic session-start recall is unavailable.
- Automatic session-end ingestion is unavailable.
- ChatGPT Desktop may require enabling MCP servers in Settings or Beta features.

## Verification

```bash
truememory-ingest setup --cli chatgpt
truememory-ingest status
```

Then restart ChatGPT Desktop and look for `truememory` in the MCP/tools UI.
