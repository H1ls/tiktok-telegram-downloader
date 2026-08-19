from __future__ import annotations


def format_mode(mode: str) -> str:
    mode = (mode or "").lower()
    if mode == "dm":
        return "dm (сразу в ЛС)"
    if mode in ("group_batch", "group"):
        return "group_batch (копить и отправлять пачкой в группу)"
    return mode or "dm"


def start_text() -> str:
    return (
        "Кидай TikTok-ссылку, я скачаю и пришлю видео.\n\n"
        "Режимы:\n"
        "/route dm - сразу в ЛС\n"
        "/route group - копить и отправлять пачкой в группу\n\n"
        "Привязка группы:\n"
        "В группе: /bind\n"
        "В ЛС: /bind_id -1003115579453\n\n"
        "Пачка: /batch 1..10\n"
        "Хранение: /keep 1..1000\n"
        "Качество: /quality 360|480|720|1080\n"
        "Настройки: /my\n\n"
        "Если написать ссылку + me или мне, видео отправится в этот чат."
    )


def settings_text(user_id: int, user_cfg: dict, queue_len: int) -> str:
    mode = (user_cfg.get("delivery_mode") or "dm").lower()
    return (
        "Твои настройки:\n"
        f"user_id = {user_id}\n"
        f"mode = {format_mode(mode)}\n"
        f"target_chat_id = {user_cfg.get('target_chat_id')}\n"
        f"batch_size = {int(user_cfg.get('batch_size') or 1)}\n"
        f"queue_keep_max = {int(user_cfg.get('queue_keep_max') or 1)}\n"
        f"queue_len = {queue_len}\n"
        f"max_height = {user_cfg.get('max_height')}\n"
    )
