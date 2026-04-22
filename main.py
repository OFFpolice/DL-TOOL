import flet as ft
import yt_dlp
import threading
import os

DEFAULT_PATH = "/storage/emulated/0/Download"

def main(page: ft.Page):
    page.title = "DL-TOOL"
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    download_path = DEFAULT_PATH
    current_theme = "custom"

    def apply_theme(mode):
        nonlocal current_theme
        current_theme = mode

        if mode == "dark":
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = None
        elif mode == "light":
            page.theme_mode = ft.ThemeMode.LIGHT
            page.bgcolor = None
        elif mode == "system":
            page.theme_mode = ft.ThemeMode.SYSTEM
            page.bgcolor = None
        else:
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = "#0b0f1a"

        page.update()

    apply_theme("custom")

    status_text = ft.Text("Готов к скачиванию", size=16, weight="bold")
    status_sub = ft.Text("Вставьте ссылку и нажмите «Скачать»", size=12)

    url_input = ft.TextField(
        hint_text="Введите ссылку",
        expand=True,
        border_radius=12,
    )

    downloads_column = ft.Column()

    def update_status(main, sub):
        status_text.value = main
        status_sub.value = sub
        page.update()

    def refresh_downloads():
        downloads_container.content = downloads_column if downloads_column.controls else empty_block
        page.update()

    def add_download_item(text):
        downloads_column.controls.insert(
            0,
            ft.Container(
                content=ft.Text(text, size=12),
                padding=10,
                border_radius=10
            )
        )
        refresh_downloads()

    def download():
        url = url_input.value.strip()
        if not url:
            update_status("Ошибка", "Введите ссылку")
            return

        update_status("Загрузка...", "Подождите")

        def run():
            try:
                ydl_opts = {
                    "outtmpl": os.path.join(download_path, "%(title)s.%(ext)s"),
                    "noplaylist": True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get("title", "video")

                page.call_from_thread(lambda: update_status("Готово", "Видео скачано"))
                page.call_from_thread(lambda: add_download_item(title))

            except Exception as e:
                page.call_from_thread(lambda: update_status("Ошибка", str(e)))

        threading.Thread(target=run).start()

    async def paste_click(e):
        try:
            clip = await page.get_clipboard()
            if clip:
                url_input.value = clip
                page.update()
        except:
            pass

    paste_btn = ft.ElevatedButton(
        "Вставить",
        icon=ft.Icons.CONTENT_PASTE,
        on_click=paste_click
    )

    download_btn = ft.ElevatedButton(
        "Скачать",
        icon=ft.Icons.DOWNLOAD,
        on_click=lambda e: download()
    )

    def pick_folder_result(e):
        nonlocal download_path
        if e.path:
            download_path = e.path
            folder_text.value = f"Папка: {download_path}"
            page.update()

    file_picker = ft.FilePicker(on_result=pick_folder_result)
    page.overlay.append(file_picker)

    def open_settings(e):
        dialog.open = True
        page.update()

    def set_theme(e):
        apply_theme(e.control.value)

    folder_text = ft.Text(f"Папка: {download_path}", size=12)

    dialog = ft.AlertDialog(
        title=ft.Text("Настройки"),
        content=ft.Column(
            [
                ft.Text("Тема"),
                ft.Dropdown(
                    value="custom",
                    options=[
                        ft.dropdown.Option("custom", "Стандартная"),
                        ft.dropdown.Option("dark", "Темная"),
                        ft.dropdown.Option("light", "Светлая"),
                        ft.dropdown.Option("system", "Система"),
                    ],
                    on_change=set_theme
                ),
                ft.Divider(),
                ft.Text("Папка загрузки"),
                folder_text,
                ft.ElevatedButton(
                    "Выбрать папку",
                    on_click=lambda e: file_picker.get_directory_path()
                ),
            ],
            tight=True
        ),
        actions=[
            ft.TextButton("Закрыть", on_click=lambda e: setattr(dialog, "open", False) or page.update())
        ]
    )

    page.dialog = dialog

    input_card = ft.Container(
        content=ft.Column([
            url_input,
            ft.Row([paste_btn, download_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], spacing=15),
        padding=20,
        border_radius=20,
    )

    status_card = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.INFO_OUTLINE),
            ft.Column([status_text, status_sub])
        ]),
        padding=15,
        border_radius=15,
    )

    empty_block = ft.Column(
        [
            ft.Icon(ft.Icons.FOLDER, size=50),
            ft.Text("Здесь пока пусто"),
            ft.Text("Ваши скачанные видео появятся здесь", size=12)
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
            ft.Text("Последние загрузки", size=16, weight="bold"),
            downloads_container
        ]),
        padding=15,
        border_radius=20,
    )

    nav = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.DOWNLOAD, label="Скачать"),
            ft.NavigationBarDestination(icon=ft.Icons.HISTORY, label="История"),
        ]
    )

    header = ft.Row([
        ft.Row([
            ft.Text("DL", size=28, weight="bold"),
            ft.Text("TOOL", size=28, weight="bold"),
        ]),
        ft.IconButton(icon=ft.Icons.SETTINGS, on_click=open_settings)
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