import os
import yt_dlp
import threading

import flet as ft
import flet_permission_handler as fph


DOWNLOAD_PATH = "/storage/emulated/0/Download"


def main(page: ft.Page):
    page.title = "DL-TOOL"
    page.bgcolor = "#0b0f1a"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    ph = fph.PermissionHandler()

    status_text = ft.Text("Готов к скачиванию", size=16, weight="bold")
    status_sub = ft.Text("Вставьте ссылку и нажмите «Скачать»", size=12, color="#8a8f9c")

    url_input = ft.TextField(
        hint_text="Введите ссылку",
        expand=True,
        bgcolor="#111827",
        border_radius=12,
        border_color="#1f2937",
        color="white",
        cursor_color="#3b82f6"
    )

    downloads_column = ft.Column()

    def show_snackbar(message: str):
        page.open(ft.SnackBar(ft.Text(message)))

    def update_status(main, sub):
        status_text.value = main
        status_sub.value = sub
        page.update()

    def set_loading(state: bool):
        download_btn.disabled = state
        paste_btn.disabled = state
        page.update()

    def refresh_downloads():
        if downloads_column.controls:
            downloads_container.content = downloads_column
        else:
            downloads_container.content = empty_block
        page.update()

    def add_download_item(text):
        downloads_column.controls.insert(
            0,
            ft.Container(
                content=ft.Text(text, size=12),
                padding=10,
                bgcolor="#111827",
                border_radius=10
            )
        )
        refresh_downloads()

    async def check_permissions():
        status = await ph.get_status(fph.Permission.STORAGE)
        if status != fph.PermissionStatus.GRANTED:
            status = await ph.request(fph.Permission.STORAGE)
        if status != fph.PermissionStatus.GRANTED:
            show_snackbar("Нет доступа к памяти")
            await ph.open_app_settings()
            return False
        return True

    def download():
        url = url_input.value.strip()
        if not url:
            update_status("Ошибка", "Введите ссылку")
            return

        async def start():
            ok = await check_permissions()
            if not ok:
                return

            update_status("Загрузка...", "Подождите")
            set_loading(True)

            def run():
                try:
                    ydl_opts = {
                        "outtmpl": os.path.join(DOWNLOAD_PATH, "%(title)s.%(ext)s"),
                        "noplaylist": True,
                    }

                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        title = info.get("title", "video")

                    page.call_from_thread(lambda: update_status("Готово", "Видео скачано"))
                    page.call_from_thread(lambda: add_download_item(title))
                except yt_dlp.utils.DownloadError as e:
                    page.call_from_thread(lambda: update_status("Ошибка загрузки", str(e)))
                except Exception as e:
                    page.call_from_thread(lambda: update_status("Ошибка", str(e)))
                finally:
                    page.call_from_thread(lambda: set_loading(False))

            threading.Thread(target=run).start()

        page.run_task(start)

    async def paste_clipboard(e):
        try:
            text = await page.clipboard.get()
            if text:
                url_input.value = text
                page.update()
            else:
                show_snackbar("Буфер обмена пуст")
        except Exception:
            show_snackbar("Ошибка доступа к буферу")

    paste_btn = ft.ElevatedButton(
        "Вставить",
        icon=ft.Icons.CONTENT_PASTE,
        style=ft.ButtonStyle(bgcolor="#1f2937", color="white"),
        on_click=paste_clipboard
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
        content=ft.Row([
            ft.Icon(ft.Icons.INFO_OUTLINE, color="#3b82f6"),
            ft.Column([status_text, status_sub])
        ]),
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
        alignment=ft.Alignment(0, 0)
    )

    downloads_block = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Последние загрузки", size=16, weight="bold"),
                ft.TextButton("Открыть папку")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            downloads_container
        ]),
        padding=15,
        border_radius=20,
        bgcolor="#0f172a"
    )

    nav = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.DOWNLOAD, label="Скачать"),
            ft.NavigationBarDestination(icon=ft.Icons.HISTORY, label="История"),
        ],
        bgcolor="#0f172a"
    )

    header = ft.Row([
        ft.Row([
            ft.Text("DL", size=28, weight="bold", color="#3b82f6"),
            ft.Text("TOOL", size=28, weight="bold"),
        ]),
        ft.IconButton(icon=ft.Icons.SETTINGS)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    content = ft.SafeArea(
        content=ft.Container(
            content=ft.Column([
                header,
                input_card,
                ft.Text("Статус", size=16, weight="bold"),
                status_card,
                downloads_block
            ], spacing=15),
            padding=20
        )
    )

    page.add(content)
    page.navigation_bar = nav


ft.run(main, assets_dir="assets")