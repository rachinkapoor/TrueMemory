# ChatGPT Desktop Setup (Experimental)

> **Important — read this first.** ChatGPT Desktop does **not** currently load
> local MCP servers. As of mid-2026, OpenAI supports only **remote HTTPS MCP
> connectors**, enabled via developer mode in the ChatGPT *web* UI — and the
> macOS desktop app cannot enable developer mode at all. There is no ChatGPT
> Desktop for Linux.
>
> This adapter is **forward-looking**: it pre-stages a local stdio MCP config
> for when/if OpenAI enables local MCP support in the desktop app. Until then,
> TrueMemory will **not** appear in ChatGPT, and the adapter prints an explicit
> experimental warning whenever it writes config.

ChatGPT Desktop does not expose TrueMemory lifecycle hooks either, so even if
OpenAI enables local MCP, this integration would provide MCP tools but not
automatic session-start recall or session-end conversation extraction.

## Prerequisites

- ChatGPT Desktop installed (the adapter refuses to write config — and refuses
  to report success — if the app is not present)
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

Config path by platform (matching the adapter code):

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/com.openai.chat/mcp.json` |
| Windows | `%LOCALAPPDATA%\com.openai.chat\mcp.json` (falls back to `%APPDATA%` if `LOCALAPPDATA` is unset) |
| Linux | Not applicable — no ChatGPT Desktop exists for Linux |

Note: this filename and location are TrueMemory's own staging convention.
OpenAI has not documented any local MCP config file for ChatGPT Desktop.

If an existing `mcp.json` is present but not valid JSON, setup backs it up to
`mcp.json.bak-<timestamp>` before writing, and never deletes other MCP server
entries from a parseable config.

## Manual Setup

Add the same JSON block to the config path above for your platform.

Find your Python path:

```bash
python3 -c "import sys; print(sys.executable)"
```

## Limitations

- **ChatGPT Desktop does not currently load this config at all** (see the
  notice at the top). The supported OpenAI mechanism is remote HTTPS MCP
  connectors via web developer mode, which is architecturally different from
  this local stdio config.
- ChatGPT exposes MCP tools, not lifecycle hooks.
- Automatic session-start recall is unavailable.
- Automatic session-end ingestion is unavailable.

## Verification

```bash
truememory-ingest setup --cli chatgpt
```

Expect the explicit `EXPERIMENTAL` warning in the output. The config file
existing on disk is the only thing that can be verified today; there is no
way to make the current ChatGPT Desktop app load it.
