from __future__ import annotations

from dataclasses import dataclass

from core.command_aliases import COMMAND_TITLES, DEFAULT_COMMAND_ALIASES, normalize_command_aliases
from core.config import load_config, save_config


@dataclass(frozen=True)
class CommandAliasRow:
    key: str
    title: str
    aliases: list[str]


class CommandSettingsService:
    def load(self) -> list[CommandAliasRow]:
        cfg = load_config()
        aliases = normalize_command_aliases(cfg.command_aliases)
        return [
            CommandAliasRow(
                key=key,
                title=COMMAND_TITLES.get(key, key),
                aliases=aliases[key],
            )
            for key in DEFAULT_COMMAND_ALIASES
        ]

    def save(self, command_aliases: dict[str, str]) -> list[CommandAliasRow]:
        normalized = normalize_command_aliases(command_aliases)
        cfg = load_config()
        cfg.command_aliases = normalized
        save_config(cfg)
        return self.load()
