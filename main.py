import flet as ft
import yt_dlp
import threading
import os
import re
import subprocess

DOWNLOAD_PATH = "/storage/emulated/0/Download"

def main(page: ft.Page):
    page.title = "DL-TOOL"
    page.bgcolor = "#0b0f1a"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    status_text = ft.Text("Готов к скачиванию", size=16, weight="bold")
    status_sub = ft.Text("Вставьте ссылку и нажмите «Скачать»", size=12, color="#8a8f9c")

    progress_bar = ft.ProgressBar(value=0, width=400, color="#3b82f6")

    url_input = ft.TextField(
        hint_text="Введите ссылку",
        expand=True,
        bgcolor="#111827",
        border_radius=12,
        border_color="#1f2937",
        color="white",
        cursor_color="#3b82f6"
    )

    downloads_column = ft.Column(spacing=10)

    def update_status(main, sub):
        status_text.value = main
        status_sub.value = sub
        page.update()

    def update_progress(value):
        progress_bar.value = value
        page.update()

    def refresh_downloads():
        downloads_container.content = downloads_column if downloads_column.controls else empty_block
        page.update()

    def sanitize_filename(name):
        return re.sub(r'[\\/*?:"<>|]', "_", name)

    def add_download_item(title, filepath):
        item = ft.Container(
            content=ft.Column([
                ft.Text(title, size=12, weight="bold"),
                ft.Text(filepath, size=10, color="#8a8f9c")
            ]),
            padding=10,
            bgcolor="#111827",
            border_radius=10,
            on_click=lambda e: open_file(filepath)
        )
        downloads_column.controls.insert(0, item)
        refresh_downloads()

    def open_file(path):
        try:
            subprocess.Popen(["xdg-open", path])
        except:
            pass

    def open_folder(e):
        try:
            subprocess.Popen(["xdg-open", DOWNLOAD_PATH])
        except:
            pass

    def download():
        url = url_input.value.strip()
        if not url:
            update_status("Ошибка", "Введите ссылку")
            return

        update_status("Загрузка...", "Подготовка")
        update_progress(0)

        def progress_hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
                downloaded = d.get("downloaded_bytes", 0)
                percent = downloaded / total
                page.call_from_thread(lambda: update_progress(percent))
            elif d["status"] == "finished":
                page.call_from_thread(lambda: update_progress(1))

        def run():
            try:
                ydl_opts = {
                    "outtmpl": os.path.join(DOWNLOAD_PATH, "%(title)s.%(ext)s"),
                    "noplaylist": True,
                    "progress_hooks": [progress_hook],
                    "quiet": True
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = sanitize_filename(info.get("title", "video"))
                    ext = info.get("ext", "mp4")
                    filepath = os.path.join(DOWNLOAD_PATH, f"{title}.{ext}")

                page.call_from_thread(lambda: update_status("Готово", "Видео скачано"))
                page.call_from_thread(lambda: add_download_item(title, filepath))

            except Exception as e:
                page.call_from_thread(lambda: update_status("Ошибка", str(e)))

        threading.Thread(target=run, daemon=True).start()

    paste_btn = ft.ElevatedButton(
        "Вставить",
        icon=ft.Icons.CONTENT_PASTE,
        style=ft.ButtonStyle(bgcolor="#1f2937", color="white"),
        on_click=lambda e: (
            setattr(url_input, "value", page.get_clipboard()),
            page.update()
        )
    )

    download_btn = ft.ElevatedButton(
        "Скачать",
        icon=ft.Icons.DOWNLOAD,
        style=ft.ButtonStyle(bgcolor="#2563eb", color="white", padding=20),
        on_click=lambda e: download()
    )

    input_card = ft.Container(
        content=ft.Column([
            url_input,
            ft.Row([paste_btn, download_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], spacing=15),
        padding=20,
        border_radius=20,
        bgcolor="#0f172a",
        border=ft.border.all(1, "#1f2937")
    )

    status_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color="#3b82f6"),
                ft.Column([status_text, status_sub])
            ]),
            progress_bar
        ], spacing=10),
        padding=15,
        border_radius=15,
        bgcolor="#0f172a"
    )

    empty_block = ft.Column(
        [
            ft.Icon(ft.Icons.FOLDER, size=50, color="#3b82f6"),
            ft.Text("Здесь пока пусто"),
            ft.Text("Ваши скачанные видео появятся здесь", size=12, color="#8a8f9c")
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

    downloads_container = ft.Container(
        content=empty_block,
        padding=20,
        alignment=ft.alignment.center
    )

    downloads_block = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Последние загрузки", size=16, weight="bold"),
                ft.TextButton("Открыть папку", on_click=open_folder)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            downloads_container
        ]),
        padding=15,
        border_radius=20,
        bgcolor="#0f172a"
    )

    header = ft.Row([
        ft.Row([
            ft.Text("DL", size=28, weight="bold", color="#3b82f6"),
            ft.Text("TOOL", size=28, weight="bold"),
        ]),
        ft.IconButton(icon=ft.Icons.SETTINGS)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    main_view = ft.Column([
        header,
        input_card,
        ft.Text("Статус", size=16, weight="bold"),
        status_card,
        downloads_block
    ], spacing=15)

    history_view = ft.Column([
        ft.Text("История загрузок", size=18, weight="bold"),
        downloads_container
    ])

    content_container = ft.Container(padding=20)

    def switch_tab(e):
        if nav.selected_index == 0:
            content_container.content = main_view
        else:
            content_container.content = history_view
        page.update()

    nav = ft.NavigationBar(
        selected_index=0,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.DOWNLOAD, label="Скачать"),
            ft.NavigationBarDestination(icon=ft.Icons.HISTORY, label="История"),
        ],
        bgcolor="#0f172a",
        on_change=switch_tab
    )

    content = ft.SafeArea(content=content_container)

    page.add(content)
    page.navigation_bar = nav

    content_container.content = main_view
    page.update()

ft.run(main, assets_dir="assets")