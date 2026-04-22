import flet as ft
import yt_dlp
import threading
import os
import time
from datetime import datetime

DOWNLOAD_PATH = "/storage/emulated/0/Download"

# -------------------- Глобальные стили --------------------
BG_COLOR = "#0b0f1a"
CARD_COLOR = "#0f172a"
ACCENT_COLOR = "#3b82f6"
SECONDARY_COLOR = "#1f2937"
TEXT_SECONDARY = "#8a8f9c"

class DownloadManager:
    """Хранит список загруженных файлов для истории."""
    history = []  # каждый элемент: {"title": str, "path": str, "date": str}

def main(page: ft.Page):
    page.title = "DL-TOOL"
    page.bgcolor = BG_COLOR
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    # -------------------- Состояние приложения --------------------
    current_view = 0  # 0 - загрузка, 1 - история
    status_text = ft.Text("Готов к скачиванию", size=16, weight="bold")
    status_sub = ft.Text("Вставьте ссылку и нажмите «Скачать»", size=12, color=TEXT_SECONDARY)
    progress_bar = ft.ProgressBar(width=float("inf"), visible=False, color=ACCENT_COLOR)
    progress_text = ft.Text("", size=12, color=TEXT_SECONDARY, visible=False)

    url_input = ft.TextField(
        hint_text="Введите ссылку",
        expand=True,
        bgcolor="#111827",
        border_radius=12,
        border_color=SECONDARY_COLOR,
        color="white",
        cursor_color=ACCENT_COLOR,
        on_submit=lambda e: download()
    )

    format_dropdown = ft.Dropdown(
        width=120,
        options=[
            ft.dropdown.Option("video", "Видео"),
            ft.dropdown.Option("audio", "Аудио (mp3)"),
        ],
        value="video",
        bgcolor="#111827",
        border_color=SECONDARY_COLOR,
        color="white",
    )

    downloads_column = ft.Column(spacing=10)  # для отображения истории на вкладке "Загрузки"
    history_column = ft.Column(spacing=10)    # для отображения истории на вкладке "История"

    # -------------------- Вспомогательные функции --------------------
    def update_status(main, sub):
        status_text.value = main
        status_sub.value = sub
        page.update()

    def update_progress(d):
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "0%").strip()
            speed = d.get("_speed_str", "N/A").strip()
            progress_bar.visible = True
            progress_text.visible = True
            progress_bar.value = float(percent.replace("%", "")) / 100 if "%" in percent else None
            progress_text.value = f"{percent} • {speed}"
            page.update()
        elif d["status"] == "finished":
            progress_bar.visible = False
            progress_text.visible = False
            page.update()

    def refresh_downloads_ui():
        """Обновляет виджеты с историей."""
        if downloads_column.controls:
            downloads_container.content = downloads_column
        else:
            downloads_container.content = empty_block
        page.update()

    def refresh_history_ui():
        """Обновляет вкладку истории."""
        if DownloadManager.history:
            history_items = []
            for item in reversed(DownloadManager.history):
                history_items.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(item["title"], weight="bold", size=14),
                            ft.Text(f"Дата: {item['date']} • {os.path.basename(item['path'])}", size=12, color=TEXT_SECONDARY),
                        ]),
                        padding=10,
                        bgcolor="#111827",
                        border_radius=10,
                        on_click=lambda e, p=item["path"]: open_folder(p)
                    )
                )
            history_column.controls = history_items
        else:
            history_column.controls = [
                ft.Column([
                    ft.Icon(ft.Icons.HISTORY, size=50, color=ACCENT_COLOR),
                    ft.Text("История пуста"),
                    ft.Text("Скачанные файлы появятся здесь", size=12, color=TEXT_SECONDARY)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            ]
        history_container.content = history_column
        page.update()

    def add_to_history(title, filepath):
        """Добавляет запись в историю."""
        DownloadManager.history.append({
            "title": title,
            "path": filepath,
            "date": datetime.now().strftime("%d.%m.%Y %H:%M")
        })
        refresh_history_ui()
        # Также добавляем на главный экран (последние загрузки)
        downloads_column.controls.insert(
            0,
            ft.Container(
                content=ft.Column([
                    ft.Text(title, weight="bold", size=14),
                    ft.Text(f"Скачано: {datetime.now().strftime('%H:%M')}", size=12, color=TEXT_SECONDARY)
                ]),
                padding=10,
                bgcolor="#111827",
                border_radius=10,
                on_click=lambda e, p=filepath: open_folder(p)
            )
        )
        refresh_downloads_ui()

    def open_folder(path=None):
        """Открывает папку загрузок или конкретный файл."""
        target = path if path else DOWNLOAD_PATH
        if os.path.exists(target):
            # Попытка открыть файловым менеджером (работает на Android)
            page.launch_url(f"file://{target}")
        else:
            update_status("Ошибка", "Папка не найдена")

    # -------------------- Загрузка --------------------
    def download():
        url = url_input.value.strip()
        if not url:
            update_status("Ошибка", "Введите ссылку")
            return

        choice = format_dropdown.value
        update_status("Подготовка...", "Получение информации")
        progress_bar.visible = False
        progress_text.visible = False
        page.update()

        def run():
            try:
                ydl_opts = {
                    "outtmpl": os.path.join(DOWNLOAD_PATH, "%(title)s.%(ext)s"),
                    "noplaylist": True,
                    "progress_hooks": [lambda d: page.call_from_thread(lambda: update_progress(d))],
                }

                if choice == "audio":
                    ydl_opts.update({
                        "format": "bestaudio/best",
                        "postprocessors": [{
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }],
                    })
                else:
                    ydl_opts.update({"format": "bestvideo+bestaudio/best"})

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get("title", "video")
                    ext = "mp3" if choice == "audio" else info.get("ext", "mp4")
                    filename = f"{title}.{ext}"
                    filepath = os.path.join(DOWNLOAD_PATH, filename)

                page.call_from_thread(lambda: update_status("Готово", "Файл сохранён"))
                page.call_from_thread(lambda: add_to_history(title, filepath))
                page.call_from_thread(lambda: url_input.focus())

            except Exception as e:
                error_msg = str(e)
                page.call_from_thread(lambda: update_status("Ошибка", error_msg[:100]))
            finally:
                page.call_from_thread(lambda: setattr(progress_bar, "visible", False))
                page.call_from_thread(lambda: setattr(progress_text, "visible", False))
                page.call_from_thread(page.update)

        threading.Thread(target=run).start()

    # -------------------- Обработчики UI --------------------
    def paste_from_clipboard(e):
        clipboard = page.get_clipboard()
        if clipboard:
            url_input.value = clipboard
            page.update()

    def switch_view(e):
        nonlocal current_view
        current_view = e.control.selected_index
        if current_view == 0:
            main_content.content = download_view
        else:
            main_content.content = history_view
            refresh_history_ui()
        page.update()

    # -------------------- Компоненты интерфейса --------------------
    paste_btn = ft.ElevatedButton(
        "Вставить",
        icon=ft.Icons.CONTENT_PASTE,
        style=ft.ButtonStyle(bgcolor=SECONDARY_COLOR, color="white"),
        on_click=paste_from_clipboard
    )

    download_btn = ft.ElevatedButton(
        "Скачать",
        icon=ft.Icons.DOWNLOAD,
        style=ft.ButtonStyle(bgcolor=ACCENT_COLOR, color="white", padding=20),
        on_click=lambda e: download()
    )

    input_card = ft.Container(
        content=ft.Column([
            url_input,
            ft.Row([format_dropdown, paste_btn, download_btn], spacing=10),
            ft.Column([progress_bar, progress_text], spacing=5)
        ], spacing=15),
        padding=20,
        border_radius=20,
        bgcolor=CARD_COLOR,
        border=ft.border.all(1, SECONDARY_COLOR)
    )

    status_card = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.INFO_OUTLINE, color=ACCENT_COLOR),
            ft.Column([status_text, status_sub])
        ]),
        padding=15,
        border_radius=15,
        bgcolor=CARD_COLOR
    )

    empty_block = ft.Column(
        [
            ft.Icon(ft.Icons.FOLDER, size=50, color=ACCENT_COLOR),
            ft.Text("Здесь пока пусто"),
            ft.Text("Ваши скачанные видео появятся здесь", size=12, color=TEXT_SECONDARY)
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

    downloads_container = ft.Container(
        content=empty_block,
        padding=20,
        alignment=ft.Alignment(0, 0)
    )

    downloads_block = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Последние загрузки", size=16, weight="bold"),
                ft.TextButton("Открыть папку", on_click=lambda e: open_folder())
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            downloads_container
        ]),
        padding=15,
        border_radius=20,
        bgcolor=CARD_COLOR
    )

    # -------------------- Представления (вкладки) --------------------
    header = ft.Row([
        ft.Row([
            ft.Text("DL", size=28, weight="bold", color=ACCENT_COLOR),
            ft.Text("TOOL", size=28, weight="bold"),
        ]),
        ft.IconButton(icon=ft.Icons.SETTINGS, on_click=lambda e: page.launch_url("app-settings:"))
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    download_view = ft.Column([
        header,
        input_card,
        ft.Text("Статус", size=16, weight="bold"),
        status_card,
        downloads_block
    ], spacing=15)

    history_container = ft.Container(
        content=history_column,
        padding=20,
        alignment=ft.Alignment(0, 0) if not history_column.controls else None
    )

    history_view = ft.Column([
        header,
        ft.Text("История загрузок", size=20, weight="bold"),
        history_container
    ], spacing=15)

    # Главный контейнер, который будет меняться
    main_content = ft.Container(
        content=download_view,
        padding=20,
        expand=True
    )

    # Навигационная панель
    nav = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.DOWNLOAD, label="Скачать"),
            ft.NavigationBarDestination(icon=ft.Icons.HISTORY, label="История"),
        ],
        bgcolor=CARD_COLOR,
        on_change=switch_view
    )

    # -------------------- Финальная сборка --------------------
    page.add(
        ft.SafeArea(
            content=main_content,
            expand=True
        )
    )
    page.navigation_bar = nav

    # Инициализация истории (можно загрузить из файла при необходимости)
    refresh_history_ui()

ft.app(target=main, assets_dir="assets")