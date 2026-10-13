from __future__ import annotations

import re
from dataclasses import dataclass


DEFAULT_COMMAND_ALIASES: dict[str, list[str]] = {
    "start": ["start", "начало", "запуск"],
    "my": ["my"],
    "bind": ["bind"],
    "bind_id": ["bind_id"],
    "route": ["route"],
    "batch": ["batch"],
    "keep": ["keep"],
    "quality": ["quality"],
    "status": ["status"],
    "flush": ["flush"],
    "last": ["last"],
    "id": ["id"],
}

COMMAND_TITLES: dict[str, str] = {
    "start": "Старт",
    "my": "Мои настройки",
    "bind": "Привязать группу",
    "bind_id": "Привязать группу по ID",
    "route": "Режим доставки",
    "batch": "Размер пачки",
    "keep": "Лимит хранения",
    "quality": "Качество",
    "status": "Статус",
    "flush": "Отправить пачку",
    "last": "Отправить в текущий чат",
    "id": "Мой ID",
}

COMMAND_PATTERN = re.compile(r"^[^\s,/]+$")


@dataclass(frozen=True)
class CommandValidationError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def normalize_alias(alias: str) -> str:
    return alias.strip().lstrip("/").lower()


def normalize_aliases(raw_aliases: list[str] | tuple[str, ...] | str) -> list[str]:
    if isinstance(raw_aliases, str):
        parts = raw_aliases.split(",")
    else:
        parts = list(raw_aliases)

    aliases: list[str] = []
    seen: set[str] = set()
    for part in parts:
        alias = normalize_alias(str(part))
        if not alias:
            continue
        if not COMMAND_PATTERN.match(alias):
            raise CommandValidationError(f"Недопустимое имя команды: {alias}")
        if alias in seen:
            continue
        seen.add(alias)
        aliases.append(alias)

    return aliases


def normalize_command_aliases(data: dict[str, object] | None) -> dict[str, list[str]]:
    source = data or {}
    result: dict[str, list[str]] = {}

    for command_key, default_aliases in DEFAULT_COMMAND_ALIASES.items():
        raw_aliases = source.get(command_key, default_aliases)
        aliases = normalize_aliases(raw_aliases if isinstance(raw_aliases, (list, tuple, str)) else default_aliases)
        if not aliases:
            aliases = list(default_aliases)
        result[command_key] = aliases

    validate_unique_aliases(result)
    return result


def validate_unique_aliases(command_aliases: dict[str, list[str]]) -> None:
    owners: dict[str, str] = {}
    for command_key, aliases in command_aliases.items():
        for alias in normalize_aliases(aliases):
            previous = owners.get(alias)
            if previous and previous != command_key:
                raise CommandValidationError(
                    f"Команда /{alias} указана одновременно для `{previous}` и `{command_key}`"
                )
            owners[alias] = command_key


def aliases_for(command_aliases: dict[str, list[str]], command_key: str) -> list[str]:
    return command_aliases.get(command_key) or DEFAULT_COMMAND_ALIASES[command_key]
