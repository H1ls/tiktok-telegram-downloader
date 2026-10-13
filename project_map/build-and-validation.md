# Сборка, обновление и проверки

## Локальная разработка

README указывает Python 3.11+ и Windows как основную целевую платформу. Установка зависимостей и запуск:

```powershell
python -m venv .venv
\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Для проверки unit tests:

```powershell
python -m unittest discover -s tests
```

Core-тесты находятся в `tests/test_core_debt.py`; GUI-проверки — в `test_bot_ui.py`, `test_settings_ui.py`, `test_main_window_ui.py`. GUI-тесты проверяют сигналы, отображение прогресса, Logs, Settings, JSON persistence в temp directory с mock реестра, размеры и tray. Это не live-тесты Telegram/TikTok.

Для проверки аудиодорожки код вызывает внешний `ffprobe`. README требует его в `PATH`; PyInstaller spec явно собирает зависимости `curl_cffi` и `yt_dlp`, но не заявляет упаковку FFmpeg/ffprobe.

## PyInstaller

Файл `tiktok_telegram_downloader.spec` собирает `app.py` в оконный executable `tiktok-telegram-downloader.exe` с `console=False`. Через `collect_all` добавляются данные, бинарные файлы и hidden imports для `curl_cffi` и `yt_dlp`. Также включены `ui/styles`, `ui/icons` и ICO executable; ресурсный root внутри exe — `sys._MEIPASS/ui`.

## GitHub Actions release

`.github/workflows/release.yml` запускается при push в `main`, по тегу `v*` или вручную и выполняется на `windows-latest`:

1. Устанавливает Python 3.11 и зависимости.
2. Выполняет `python -m unittest discover -s tests`.
3. Для тега проверяет совпадение с `core.version.CURRENT_VERSION`, затем собирает приложение через PyInstaller spec.
4. Генерирует `sha256.txt`.
5. Загружает exe и checksum как artifact; при запуске по тегу публикует их в GitHub Release.

Описание workflow фиксирует настроенный pipeline, но не подтверждает, что конкретный запуск CI успешно завершился.

## Обновление приложения

`core.updater.update_application()` выбирает сценарий по типу запуска:

- исходники: `git fetch --prune`, затем `git pull --ff-only`;
- frozen `.exe`: получает latest GitHub Release, загружает exe и `sha256.txt`, сверяет SHA-256 и запускает PowerShell-скрипт замены/перезапуска.

Updater работает из `UpdateThread` в GUI, чтобы сетевые операции не блокировали основной поток. SHA-256 из того же релиза защищает от случайного повреждения/несовпадения скачанного файла, но не удостоверяет издателя криптографической подписью.

## Границы проверок

Локальные результаты GUI, unit tests, сборки и запуска exe описаны в [отчёте редизайна](../tasks/task_05_result.md). Live TikTok/Telegram, реальное применение autostart, установка обновления и конкретный запуск GitHub Actions требуют отдельных проверок.
