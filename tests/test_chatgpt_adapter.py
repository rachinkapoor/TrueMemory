"""Tests for the ChatGPT Desktop adapter."""
from __future__ import annotations

import inspect
import json
from pathlib import Path


def test_import_chatgpt_adapter():
    from truememory.hooks.adapters.chatgpt import ChatGPTAdapter  # noqa: F401


def test_chatgpt_in_registry():
    from truememory.hooks.registry import get_adapter

    adapter = get_adapter("chatgpt")
    assert adapter is not None
    assert adapter.cli_id == "chatgpt"


def test_chatgpt_adapter_properties():
    from truememory.hooks.adapters.chatgpt import ChatGPTAdapter

    adapter = ChatGPTAdapter()
    assert adapter.name == "ChatGPT Desktop"
    assert adapter.cli_id == "chatgpt"
    assert isinstance(adapter.config_path, Path)
    assert adapter.config_path.name == "mcp.json"


def test_chatgpt_implements_all_abstract_methods():
    from truememory.hooks.adapters.base import CLIAdapter
    from truememory.hooks.adapters.chatgpt import ChatGPTAdapter

    abstract_methods = {
        name for name, _ in inspect.getmembers(CLIAdapter)
        if getattr(getattr(CLIAdapter, name, None), "__isabstractmethod__", False)
    }
    adapter = ChatGPTAdapter()
    for method_name in abstract_methods:
        assert hasattr(adapter, method_name), f"Missing: {method_name}"


def test_detect_false_without_app(tmp_path, monkeypatch):
    from truememory.hooks.adapters import chatgpt as chatgpt_mod
    from truememory.hooks.adapters.chatgpt import ChatGPTAdapter

    monkeypatch.setattr(chatgpt_mod, "_app_installed", lambda: False)
    monkeypatch.setattr(chatgpt_mod, "_CHATGPT_DIR", tmp_path / "missing")
    monkeypatch.setattr(chatgpt_mod, "_CONFIG_PATH", tmp_path / "missing" / "mcp.json")

    assert not ChatGPTAdapter().detect()


def test_detect_true_with_app_installed(tmp_path, monkeypatch):
    from truememory.hooks.adapters import chatgpt as chatgpt_mod
    from truememory.hooks.adapters.chatgpt import ChatGPTAdapter

    chatgpt_dir = tmp_path / "com.openai.chat"
    chatgpt_dir.mkdir()
    monkeypatch.setattr(chatgpt_mod, "_app_installed", lambda: True)
    monkeypatch.setattr(chatgpt_mod, "_CHATGPT_DIR", chatgpt_dir)
    monkeypatch.setattr(chatgpt_mod, "_CONFIG_PATH", chatgpt_dir / "mcp.json")

    assert ChatGPTAdapter().detect()


def test_install_mcp_creates_config(tmp_path, monkeypatch):
    from truememory.hooks.adapters import chatgpt as chatgpt_mod
    from truememory.hooks.adapters.chatgpt import ChatGPTAdapter

    config_path = tmp_path / "mcp.json"
    monkeypatch.setattr(chatgpt_mod, "_app_installed", lambda: True)
    monkeypatch.setattr(chatgpt_mod, "_CONFIG_PATH", config_path)

    ChatGPTAdapter().install_mcp(python_path="/usr/bin/python3")

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["mcpServers"]["truememory"]["command"] == "/usr/bin/python3"
    assert data["mcpServers"]["truememory"]["args"] == ["-m", "truememory.mcp_server"]


def test_install_mcp_preserves_existing(tmp_path, monkeypatch):
    from truememory.hooks.adapters import chatgpt as chatgpt_mod
    from truememory.hooks.adapters.chatgpt import ChatGPTAdapter

    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        json.dumps({"mcpServers": {"other": {"command": "node", "args": ["server.js"]}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(chatgpt_mod, "_app_installed", lambda: True)
    monkeypatch.setattr(chatgpt_mod, "_CONFIG_PATH", config_path)

    ChatGPTAdapter().install_mcp(python_path="/usr/bin/python3")

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert "other" in data["mcpServers"]
    assert "truememory" in data["mcpServers"]


def test_install_hooks_is_noop(tmp_path, monkeypatch):
    from truememory.hooks.adapters import chatgpt as chatgpt_mod
    from truememory.hooks.adapters.chatgpt import ChatGPTAdapter

    config_path = tmp_path / "mcp.json"
    monkeypatch.setattr(chatgpt_mod, "_CONFIG_PATH", config_path)

    ChatGPTAdapter().install_hooks(python_path="/usr/bin/python3", user_id="alice")

    assert not config_path.exists()


def test_verify_requires_mcp_entry(tmp_path, monkeypatch):
    from truememory.hooks.adapters import chatgpt as chatgpt_mod
    from truememory.hooks.adapters.chatgpt import ChatGPTAdapter

    config_path = tmp_path / "mcp.json"
    monkeypatch.setattr(chatgpt_mod, "_app_installed", lambda: True)
    monkeypatch.setattr(chatgpt_mod, "_CONFIG_PATH", config_path)
    adapter = ChatGPTAdapter()

    assert not adapter.verify()
    adapter.install_mcp(python_path="/usr/bin/python3")
    assert adapter.verify()


def test_uninstall_removes_only_truememory(tmp_path, monkeypatch):
    from truememory.hooks.adapters import chatgpt as chatgpt_mod
    from truememory.hooks.adapters.chatgpt import ChatGPTAdapter

    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        json.dumps({
            "mcpServers": {
                "other": {"command": "node"},
                "truememory": {"command": "python", "args": ["-m", "truememory.mcp_server"]},
            }
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(chatgpt_mod, "_CONFIG_PATH", config_path)

    ChatGPTAdapter().uninstall()

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert "other" in data["mcpServers"]
    assert "truememory" not in data["mcpServers"]


def test_no_system_prompt_path():
    from truememory.hooks.adapters.chatgpt import ChatGPTAdapter

    adapter = ChatGPTAdapter()
    assert adapter.get_system_prompt_path() is None
    assert adapter.get_system_prompt_content() == ""
