# Карта проекта

Краткий навигатор по исходникам **TikTok Telegram Downloader**. Подробные блоки находятся в папке [project_map](project_map/architecture.md).

## Назначение

Windows desktop-приложение на PyQt6 запускает Telegram-бота на aiogram. Бот принимает TikTok-ссылки, ставит загрузки в очередь, скачивает видео через `curl_cffi` с fallback на `yt-dlp` и отправляет результат в личный чат либо в привязанную группу.

## Поток верхнего уровня

```text
app.py / PyQt6 GUI
    └── ServiceThread / asyncio event loop
        └── TikTokBotService / aiogram polling
            ├── bot/handlers.py → bot/link_handler.py → JobQueueService
            ├── workers → JobProcessor → DownloadService
            │                         └── curl_cffi → yt-dlp fallback
            └── TelegramSender / FolderFlusher → Telegram
```

Подробности потоков и жизненного цикла: [Архитектура](project_map/architecture.md).

## Каталоги

| Путь | Назначение |
| --- | --- |
| [app.py](app.py) | Точка входа, создание GUI, сервисного `QThread` и asyncio loop. |
| [bot/](bot/handlers.py) | Регистрация Telegram-команд и обработка сообщений со ссылками. |
| [core/](core/service.py) | Сервис бота, задачи и очередь, конфигурация, скачивание, отправка, обновление. |
| [core/downloaders/](core/downloaders/service.py) | Контракт загрузчика и стратегии `curl_cffi` / `yt-dlp`. |
| [gui/](gui/main_window.py) | Главное окно, вкладки, системный трей и интерфейс управления ботом. |
| [ui/](ui/theme.py) | Общая тема, SVG-ресурсы и UI helpers; [карта интеграций редизайна](tasks/ui_foundation.md). |
| [tests/](tests/test_core_debt.py) | Regression-тесты core; GUI-тесты [Bot](tests/test_bot_ui.py) и [Settings](tests/test_settings_ui.py). |
| [.github/workflows/](.github/workflows/release.yml) | Windows workflow тестирования, сборки и публикации release. |
| [tools/](tools/) | Вспомогательные инструменты проекта. |

## Блоки карты

- [Архитектура и жизненный цикл](project_map/architecture.md)
- [Каталог модулей](project_map/modules.md)
- [Настройки, данные и файлы](project_map/configuration-and-files.md)
- [Сценарии Telegram-бота](project_map/bot-workflows.md)
- [Сборка, обновление и проверки](project_map/build-and-validation.md)

## Быстрые ориентиры

- Изменить запуск GUI или связку Qt/asyncio: `app.py`, `gui/main_window.py`.
- Изменить команды и разбор входящих ссылок: `bot/commands.py`, `bot/link_handler.py`.
- Изменить обработку одной загрузки: `core/job_processor.py`.
- Изменить порядок/параллелизм workers: `core/service.py`, `core/job_queue.py`, `core/config.py`.
- Изменить загрузчики или их порядок: `core/downloaders/`.
- Изменить отправку одного файла/альбома: `core/sender.py`; накопленных файлов: `core/flusher.py`, `core/flush_service.py`.
- Изменить расположение конфигурации или загрузок: `core/config.py`, `core/paths.py`, `core/settings_service.py`.
- Изменить обновление и Windows release: `core/updater.py`, `tiktok_telegram_downloader.spec`, `.github/workflows/release.yml`.

## Ограничения фактической модели

- Очередь `Job` в `JobQueueService` основана на `asyncio.Queue` и находится в памяти. Это не durable queue; скачанные файлы хранятся отдельно на диске.
- Для пользовательских загрузок сервис запускает несколько workers; обработка одного пользователя сериализуется processing lock, а число одновременных скачиваний дополнительно ограничивается semaphore.
- SHA-256 updater сверяет скачанный файл с checksum из того же GitHub Release. Это проверка целостности относительно опубликованного checksum, не цифровая подпись издателя.
- Карта описывает исходники статически. GUI, сетевые сценарии и workflow при подготовке карты не запускались; тесты не прогонялись.
