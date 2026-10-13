# Архитектура и жизненный цикл

## Компоненты и границы

```text
Главный поток Qt
  app.py → MainWindow
             ├── BotControlTab
             ├── SettingsTab
             └── CommandTab
        │ Qt signals
        ▼
ServiceThread (QThread)
  отдельный asyncio event loop
        └── TikTokBotService
            ├── aiogram Dispatcher / polling
            ├── asyncio.Queue[Job] / workers
            ├── JobProcessor / DownloadService
            └── TelegramSender / FolderFlusher / FlushService
```

`app.main()` загружает конфигурацию, создает Qt-приложение и окно, затем запускает `ServiceThread`. В `ServiceThread.run()` создается новый asyncio loop и экземпляр `TikTokBotService`. Команды GUI передаются в loop через `asyncio.run_coroutine_threadsafe`; логи и состояние возвращаются в GUI Qt-сигналами.

## Запуск сервиса

При `TikTokBotService.start()` сервис:

1. Перечитывает конфигурацию и создает aiogram `Bot` и `Dispatcher`.
2. Создает отправитель, flusher и `JobProcessor` с общими сервисами/lock callbacks.
3. Регистрирует handlers.
4. Запускает worker tasks, polling task и задачу отправки уже накопившихся готовых пачек.

Количество workers ограничено `DOWNLOAD_WORKERS` и `MAX_ALBUM_ITEMS`; в текущей конфигурации это максимум четыре worker task. Параллельное скачивание дополнительно ограничено `asyncio.Semaphore(4)`.

При остановке выставляется stop event, tasks отменяются и ожидаются через `gather`, закрывается сессия бота и очищается runtime-состояние и пользовательские locks. `ServiceThread` также отменяет оставшиеся tasks и закрывает loop при выходе.

## Обработка Job

```text
Telegram message
  → link handler: extract URL / expand redirect / reject photo carousel
  → JobQueueService.enqueue(Job)
  → worker: mark_started
  → processing_lock(user_id)
  → JobProcessor.process
  → download semaphore
  → asyncio.to_thread(download_tiktok)
  → requested chat | DM | group batch
  → mark_finished / queue.task_done
```

Ссылки передаются на раскрытие редиректа в `asyncio.to_thread`. Сама задача скачивания также выполняется через `asyncio.to_thread`, чтобы блокирующая загрузка не занимала event loop. Задачи разных пользователей могут обрабатываться разными workers; processing lock сериализует задачи одного пользователя. Отдельный `user_lock` защищает flush-процедуры.

## Загрузка

`core.downloader` предоставляет фасад над `DownloadService`. Стратегии перебираются по порядку: `CurlTikTokDownloader`, затем `YtDlpTikTokDownloader`; ошибка одной стратегии приводит к попытке следующей. `JobProcessor` проверяет результат и вызывает `has_audio_stream`, затем выбирает маршрут доставки.

## Доставка

- `TelegramSender` проверяет файлы, разбивает списки по размеру и количеству и отправляет одиночные файлы или media groups.
- При ошибке Telegram `EntityTooLarge` альбом делится рекурсивно; одиночный файл может быть отправлен как document.
- `FolderFlusher` читает накопленные медиафайлы пользователя, отправляет их блоками и удаляет файлы, подтвержденно отправленные sender-ом.
- `FlushService` координирует ручной и стартовый flush, пользовательский lock и уведомления.

Автоматические повторы отправки не обеспечивают exactly-once delivery. При сетевой ошибке исход отправки может быть неопределенным, поэтому sender прекращает автоматический retry для соответствующих сетевых ошибок.

## Отказоустойчивость и границы

- Polling повторяет соединение после сетевых ошибок с задержкой от 2 до 60 секунд.
- Невалидный token и конфликт запуска бота останавливают polling без бесконечного повтора.
- Объекты `Job` в очереди существуют только в памяти процесса. Перезапуск не восстанавливает еще не обработанные задачи.
- Локальные видеофайлы могут сохраняться между запусками, но это не дает гарантии доставки или отсутствия дублей.
- Отмена coroutine, ожидающей `asyncio.to_thread`, не доказывает немедленное прерывание уже выполняющейся блокирующей функции.
