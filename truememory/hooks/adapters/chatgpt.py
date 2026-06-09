"""ChatGPT Desktop adapter - local MCP config (EXPERIMENTAL).

IMPORTANT: ChatGPT Desktop does not currently load local MCP servers.
As of mid-2026, OpenAI supports only remote HTTPS MCP connectors, enabled
via developer mode in the ChatGPT *web* UI — and the macOS desktop app
cannot enable developer mode at all. There is no ChatGPT Desktop for Linux.

This adapter pre-stages a local stdio MCP config for when/if OpenAI enables
local MCP support in the desktop app. It refuses to run (and refuses to
claim success) unless the actual ChatGPT Desktop app is installed, and it
prints an explicit experimental warning whenever it writes config.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

from truememory.hooks.adapters.base import CLIAdapter

if sys.platform == "darwin":
    _CHATGPT_DIR = Path.home() / "Library" / "Application Support" / "com.openai.chat"
    _CONFIG_PATH = _CHATGPT_DIR / "mcp.json"
elif sys.platform == "win32":
    _base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    _CHATGPT_DIR = Path(_base) / "com.openai.chat" if _base else Path.home() / "AppData" / "Local" / "com.openai.chat"
    _CONFIG_PATH = _CHATGPT_DIR / "mcp.json"
else:
    # No ChatGPT Desktop exists for Linux; placeholder so the module imports.
    _CHATGPT_DIR = Path.home() / ".config" / "com.openai.chat"
    _CONFIG_PATH = _CHATGPT_DIR / "mcp.json"

_TRUEMEMORY_MARKER = "truememory"

_EXPERIMENTAL_WARNING = """\
\033[33m⚠ EXPERIMENTAL: ChatGPT Desktop does not currently load local MCP servers.
  OpenAI supports only remote HTTPS MCP connectors, enabled via developer mode
  in the ChatGPT web UI; the macOS desktop app cannot enable it (as of mid-2026).
  This adapter pre-stages a local MCP config for when/if OpenAI enables local
  MCP support. TrueMemory will NOT appear in ChatGPT until then.\033[0m"""

_APP_NOT_FOUND_MESSAGE = (
    "ChatGPT Desktop app not found — refusing to write config for an app that "
    "is not installed. Note: ChatGPT Desktop does not currently load local MCP "
    "servers anyway (OpenAI supports only remote HTTPS connectors via developer "
    "mode on the web UI). See docs/setup-chatgpt.md for details and manual setup."
)


def _app_installed() -> bool:
    """Return True only if the actual ChatGPT Desktop app is present.

    The Application Support / config directory is NOT sufficient evidence:
    our own install would create it, making detection self-fulfilling.
    """
    if sys.platform == "darwin":
        candidates = (
            Path("/Applications/ChatGPT.app"),
            Path.home() / "Applications" / "ChatGPT.app",
        )
        return any(p.exists() for p in candidates)
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            return False
        packages = Path(base) / "Packages"
        try:
            return any(packages.glob("OpenAI.ChatGPT*"))
        except OSError:
            return False
    # No ChatGPT Desktop for Linux.
    return False


class ChatGPTAdapter(CLIAdapter):
    """Adapter for ChatGPT Desktop MCP servers (experimental, forward-looking)."""

    @property
    def name(self) -> str:
        return "ChatGPT Desktop"

    @property
    def cli_id(self) -> str:
        return "chatgpt"

    @property
    def config_path(self) -> Path:
        return _CONFIG_PATH

    def detect(self) -> bool:
        return _app_installed()

    def is_configured(self) -> bool:
        return self._has_mcp_entry()

    def install_mcp(self, python_path: str | None = None) -> None:
        if not _app_installed():
            raise RuntimeError(_APP_NOT_FOUND_MESSAGE)

        py = python_path or sys.executable

        existing: dict = {}
        if _CONFIG_PATH.exists():
            try:
                data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = None
            if isinstance(data, dict):
                existing = data
            else:
                # Unparseable (or non-object) config: never silently destroy
                # it. Back it up first; if the backup fails, refuse.
                backup = _CONFIG_PATH.with_name(
                    f"{_CONFIG_PATH.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
                )
                try:
                    shutil.copy2(_CONFIG_PATH, backup)
                except OSError as e:
                    raise RuntimeError(
                        f"Existing {_CONFIG_PATH} is not valid JSON and could "
                        f"not be backed up ({e}); refusing to overwrite it."
                    ) from e
                print(
                    f"\033[33m⚠ Existing {_CONFIG_PATH} is not valid JSON; "
                    f"backed it up to {backup} and starting fresh.\033[0m",
                    file=sys.stderr,
                )

        servers = existing.setdefault("mcpServers", {})
        if not isinstance(servers, dict):
            servers = {}
            existing["mcpServers"] = servers

        servers["truememory"] = {
            "command": py,
            "args": ["-m", "truememory.mcp_server"],
        }

        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_PATH.write_text(
            json.dumps(existing, indent=2),
            encoding="utf-8",
        )
        print(_EXPERIMENTAL_WARNING, file=sys.stderr)

    def install_hooks(
        self,
        python_path: str | None = None,
        user_id: str = "",
        db_path: str = "",
    ) -> None:
        # ChatGPT Desktop exposes MCP tools, but not TrueMemory lifecycle hooks.
        del python_path, user_id, db_path

    def uninstall(self) -> None:
        # Match the Cursor house pattern: never write unless the file parsed
        # cleanly AND our entry is actually present. A corrupt config must be
        # left untouched (it may be user-recoverable).
        if not _CONFIG_PATH.exists():
            return
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return
            servers = data.get("mcpServers", {})
            if isinstance(servers, dict) and _TRUEMEMORY_MARKER in servers:
                del servers[_TRUEMEMORY_MARKER]
                _CONFIG_PATH.write_text(
                    json.dumps(data, indent=2), encoding="utf-8",
                )
        except (json.JSONDecodeError, OSError):
            pass

    def verify(self) -> bool:
        return self._has_mcp_entry()

    def get_system_prompt_path(self) -> Path | None:
        return None

    def get_system_prompt_content(self) -> str:
        return ""

    def _has_mcp_entry(self) -> bool:
        data = self._read_config()
        servers = data.get("mcpServers", {})
        return isinstance(servers, dict) and _TRUEMEMORY_MARKER in servers

    @staticmethod
    def _read_config() -> dict:
        if not _CONFIG_PATH.exists():
            return {}
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}
