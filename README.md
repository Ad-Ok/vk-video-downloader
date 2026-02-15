# VK Video Mass Downloader

CLI-инструмент для массового скачивания видео с vkvideo.ru / vk.com.  
Построен на [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Установка

```bash
pip install -r requirements.txt
```

Также нужен **ffmpeg** (для объединения видео и аудио потоков) и **Node.js** ≥ 20 (для скачивания YouTube-embed видео):

```bash
# macOS
brew install ffmpeg node

# Ubuntu/Debian
sudo apt install ffmpeg nodejs
```

## Быстрый старт

```bash
# Одно видео
python download.py https://vkvideo.ru/video4725344_14264835

# Все видео канала
python download.py https://vkvideo.ru/@channel_name

# Плейлист
python download.py https://vkvideo.ru/playlist/-204353299_426

# Несколько ссылок из файла
python download.py -f urls.txt

# С выбором качества
python download.py -f urls.txt --quality 720
```

## Авторизация (для приватных видео)

По умолчанию cookies берутся из Chrome. Можно указать другой браузер:

```bash
python download.py --cookies-browser firefox URL
```

Или использовать файл cookies.txt (в Netscape-формате):

```bash
python download.py --cookies-file ./cookies.txt URL
```

> **Совет:** Для экспорта cookies используйте расширение
> [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)

## Все параметры

| Параметр | Описание | По умолч. |
|---|---|---|
| `URL ...` | URL видео, канала или плейлиста | — |
| `-f FILE` | Текстовый файл со ссылками (по одной на строку, `#` — комментарий) | — |
| `-o DIR` | Папка для загрузок | `./downloads` |
| `-q QUALITY` | Качество: `best`, `1080`, `720`, `480`, `360`, `worst` | best |
| `-c N` | Параллельных загрузок | 3 |
| `--cookies-browser` | Браузер для cookies: `chrome`, `firefox`, `edge`, `safari` | chrome |
| `--cookies-file` | Путь к cookies.txt | — |
| `--rate-limit` | Лимит скорости, напр. `5M` | ∞ |
| `--no-archive` | Не пропускать ранее скачанные | — |
| `--list-formats` | Показать доступные форматы (без скачивания) | — |
| `--dry-run` | Показать список видео (без скачивания) | — |

## Файл urls.txt

```
# Каналы
https://vkvideo.ru/@channel_one
https://vkvideo.ru/@channel_two

# Отдельные видео
https://vkvideo.ru/video4725344_14264835
https://vkvideo.ru/video-123456_789012
```

## Настройки

Отредактируйте `config.py` для изменения дефолтных параметров:
- `DOWNLOAD_DIR` — папка загрузок
- `COOKIES_BROWSER` — браузер по умолчанию
- `OUTPUT_TEMPLATE` — шаблон имени файла
- `MAX_CONCURRENT` — параллельные загрузки
- и др.

## Что происходит под капотом

1. yt-dlp извлекает прямые ссылки на видео через API VK (blob: URL игнорируется)
2. Если видео — YouTube-embed, yt-dlp автоматически переходит на YouTube и решает JS challenge через Node.js
3. Скачивает лучшее качество (видео + аудио отдельно)  
4. ffmpeg объединяет в один MP4
5. Встраивает метаданные и обложку
6. Запоминает скачанные видео в `downloaded.txt` (пропускает при повторном запуске)
7. Результаты сохраняются в `logs/`

## Извлечение ссылок из HTML-дампа

Если нужно скачать все видео со страницы, сохраните её HTML и извлеките ссылки:

```bash
python parse_dump.py dump.html -o urls.txt
python parse_dump.py dump.html --owner 4725344 -o urls.txt  # только конкретный владелец
python download.py -f urls.txt
```
