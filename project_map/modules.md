# Каталог модулей

## Точка входа и интерфейс

| Модуль | Ответственность |
| --- | --- |
| `app.py` | Создает QApplication, окно, `ServiceThread`, передает сигналы и завершает сервис при выходе. |
| `gui/main_window.py` | Header, версия, status badge, SVG-навигация Bot/Settings/Command и QStackedWidget; сигналы, окно и сворачивание в tray. |
| `ui/theme.py`, `ui/styles/dark_theme.qss`, `ui/icons/` | Общая тема, дизайн-токены, SVG и загрузка ресурсов из исходников / exe. |
| `ui/widgets/status_badge.py` | Running/Stopped badge, обновляемый через MainWindow.set_running. |
| `ui/widgets/card.py` | Общая карточка с QSS-ролью, отступами и content_layout. |
| `gui/bot_control_tab.py` | Controls/Status, tray option, Logs с Clear/Copy/Auto-scroll, Download card и запуск updater в `QThread`. |
| `ui/widgets/download_card.py`, `ui/widgets/elided_label.py` | Отображение последнего download-события из существующего лога и сокращение длинных подписей без расширения layout. |
| `gui/settings_tab.py` | Компактные карточки autostart/Telegram/folders, видимость токена, связанные Browse, Save и inline Saved. |
| `ui/widgets/toggle_switch.py`, `ui/widgets/folder_row.py` | Checkable switch с keyboard support и переиспользуемая строка пути. |
| `gui/command_tab.py` | Редактирование алиасов bot-команд. |
| `gui/tray.py` | Системный трей и связанные действия. |

## Telegram bot

| Модуль | Ответственность |
| --- | --- |
| `bot/handlers.py` | Общая регистрация command handlers и link handlers. |
| `bot/commands.py` | Команды, пользовательские настройки и вызов flush. |
| `bot/link_handler.py` | Извлечение/раскрытие TikTok URL, создание `Job`, специальная пометка `me`/`мне`. |
| `bot/messages.py` | Тексты справки и форматирование пользовательского режима. |

## Core-сервисы

| Модуль | Ответственность |
| --- | --- |
| `core/service.py` | Runtime бота: polling, workers, stop, locks, semaphore и композиция сервисов. |
| `core/jobs.py` | Dataclass `Job` для ссылки, пользователя, исходного чата и целевого чата. |
| `core/job_queue.py` | In-memory asyncio queue, счетчики задач, состояние workers и число файлов пользователя. |
| `core/job_processor.py` | Скачивание одной задачи, предупреждение о звуке и выбор DM/group/requested-chat доставки. |
| `core/flush_service.py` | Ручной и startup flush для накопленных пачек. |
| `core/flusher.py` | Поиск пользовательских медиафайлов, отправка группами и удаление отправленного. |
| `core/sender.py` | Валидация, отправка одного файла/альбома, retry и разбиение слишком больших групп. |
| `core/user_settings.py` | Применение пользовательских значений по умолчанию и нормализация. |
| `core/rate_limiter.py` | Async rate limiter для сообщений прогресса/статуса. |

## Загрузка

| Модуль | Ответственность |
| --- | --- |
| `core/downloader.py` | Публичный фасад для загрузки, раскрытия ссылок и вспомогательных проверок. |
| `core/downloaders/base.py` | Общий Protocol/тип прогресса для стратегий. |
| `core/downloaders/service.py` | Последовательный fallback по зарегистрированным стратегиям. |
| `core/downloaders/curl_downloader.py` | Прямая стратегия через `curl_cffi`. |
| `core/downloaders/ytdlp_downloader.py` | Резервная стратегия через `yt-dlp`. |
| `core/downloaders/common.py` | Общие операции с TikTok URL и медиа. |

## Настройки, пути и поставка

| Модуль/файл | Ответственность |
| --- | --- |
| `core/config.py` | `AppConfig`, чтение/валидация/сохранение JSON-конфигурации и выбор data directory. |
| `core/settings_service.py` | API загрузки/сохранения настроек GUI и Windows autostart. |
| `core/paths.py`, `core/app_paths.py` | Корневые директории загрузок, пользовательские папки и путь приложения. |
| `core/autostart.py` | Интеграция автозапуска Windows. |
| `core/updater.py` | Git update для исходников и release update для frozen `.exe`. |
| `core/version.py` | Версия приложения. |
| `core/command_aliases.py`, `core/command_settings_service.py` | Нормализация/валидация алиасов и сервис командных настроек. |
| `core/files.py` | Перечисление поддерживаемых медиафайлов. |

## Прочие файлы

- `core/downloader_old.py` и `core/queue_store.py` присутствуют в репозитории. Перед изменением проверьте реальные импорты и вызовы; их наличие само по себе не доказывает использование в текущем runtime-потоке.
- `requirements.txt` содержит прямые зависимости проекта.
- `tiktok_telegram_downloader.spec` задает PyInstaller build.
- `tests/test_core_debt.py` содержит текущие unit/regression проверки.
- `tests/test_bot_ui.py` проверяет сигналы управления, логи, scroll и отображение download progress без запуска backend.
- `tests/test_settings_ui.py` проверяет Settings UI и сохранение/повторную загрузку JSON в изолированной папке с mock реестра.
- `tests/test_main_window_ui.py` проверяет три страницы в четырёх размерах, сигналы, status и ветки закрытия/трея.
