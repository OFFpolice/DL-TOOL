import os
import yt_dlp
import threading

import flet as ft
import flet_permission_handler as fph


DEFAULT_DOWNLOAD_PATH = "/storage/emulated/0/dl_tool"


def ensure_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def main(page: ft.Page):
    page.title = "DL-TOOL"
    page.bgcolor = "#0b0f1a"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    ph = fph.PermissionHandler()

    download_path = DEFAULT_DOWNLOAD_PATH
    ensure_dir(download_path)

    status_text = ft.Text("Готов к скачиванию", size=16, weight="bold")
    status_sub = ft.Text("Вставьте ссылку и нажмите «Скачать»", size=12, color="#8a8f9c")

    url_input = ft.TextField(
        hint_text="Введите ссылку",
        expand=True,
        bgcolor="#111827",
        border_radius=12,
        border_color="#1f2937",
        color="white"
    )

    downloads_column = ft.Column()
    history_column = ft.Column()

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

    def get_files():
        try:
            files = os.listdir(download_path)
            files = [f for f in files if os.path.isfile(os.path.join(download_path, f))]
            files.sort(reverse=True)
            return files
        except Exception:
            return []

    def build_file_item(name):
        return ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.VIDEO_FILE, size=18, color="#3b82f6"),
                ft.Text(name, size=12, expand=True)
            ]),
            padding=10,
            bgcolor="#111827",
            border_radius=10
        )

    def refresh_lists():
        files = get_files()

        downloads_column.controls.clear()
        history_column.controls.clear()

        if not files:
            downloads_container.content = empty_block
            history_container.content = empty_block
        else:
            for f in files:
                item = build_file_item(f)
                downloads_column.controls.append(item)
                history_column.controls.append(build_file_item(f))

            downloads_container.content = downloads_column
            history_container.content = history_column

        page.update()

    async def check_permissions():
        required = [
            fph.Permission.STORAGE,
            fph.Permission.VIDEOS
        ]

        for perm in required:
            try:
                status = await ph.get_status(perm)

                if not status or status.name != "GRANTED":
                    status = await ph.request(perm)

                if not status or status.name != "GRANTED":
                    show_snackbar(f"Нет разрешения: {perm.name}")
                    await ph.open_app_settings()
                    return False
            except Exception:
                continue

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

            ensure_dir(download_path)

            update_status("Загрузка...", "Подождите")
            set_loading(True)

            def run():
                try:
                    ydl_opts = {
                        "outtmpl": os.path.join(download_path, "%(title)s.%(ext)s"),
                        "noplaylist": True,
                    }

                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.extract_info(url, download=True)

                    page.call_from_thread(lambda: update_status("Готово", "Видео скачано"))
                    page.call_from_thread(refresh_lists)

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
                show_snackbar("Буфер пуст")
        except Exception:
            show_snackbar("Ошибка буфера")

    def open_settings(e):
        path_field.value = download_path
        page.dialog = settings_dialog
        settings_dialog.open = True
        page.update()

    def save_settings(e):
        nonlocal download_path
        new_path = path_field.value.strip()

        if not new_path:
            show_snackbar("Путь не может быть пустым")
            return

        download_path = new_path
        ensure_dir(download_path)

        settings_dialog.open = False
        refresh_lists()
        page.update()

    paste_btn = ft.ElevatedButton(
        "Вставить",
        icon=ft.Icons.CONTENT_PASTE,
        style=ft.ButtonStyle(bgcolor="#1f2937", color="white"),
        on_click=paste_clipboard
    )

    download_btn = ft.ElevatedButton(
        "Скачать",
        icon=ft.Icons.DOWNLOAD,
        style=ft.ButtonStyle(bgcolor="#2563eb", color="white"),
        on_click=lambda e: download()
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

    downloads_container = ft.Container(padding=20)
    history_container = ft.Container(padding=20)

    downloads_block = ft.Container(
        content=ft.Column([
            ft.Text("Последние загрузки", size=16, weight="bold"),
            downloads_container
        ]),
        padding=15,
        border_radius=20,
        bgcolor="#0f172a"
    )

    history_block = ft.Container(
        content=ft.Column([
            ft.Text("История", size=16, weight="bold"),
            history_container
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

    def on_nav_change(e):
        if nav.selected_index == 0:
            main_view.visible = True
            history_view.visible = False
        else:
            main_view.visible = False
            history_view.visible = True
            refresh_lists()
        page.update()

    nav.on_change = on_nav_change

    path_field = ft.TextField(label="Папка загрузки", value=download_path)

    settings_dialog = ft.AlertDialog(
        title=ft.Text("Настройки"),
        content=path_field,
        actions=[
            ft.TextButton("Сохранить", on_click=save_settings)
        ]
    )

    header = ft.Row([
        ft.Row([
            ft.Text("DL", size=28, weight="bold", color="#3b82f6"),
            ft.Text("TOOL", size=28, weight="bold"),
        ]),
        ft.IconButton(icon=ft.Icons.SETTINGS, on_click=open_settings)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    main_view = ft.Column([
        header,
        ft.Container(
            content=ft.Column([
                url_input,
                ft.Row([paste_btn, download_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], spacing=15),
            padding=20,
            border_radius=20,
            bgcolor="#0f172a",
            border=ft.border.all(1, "#1f2937")
        ),
        ft.Text("Статус", size=16, weight="bold"),
        ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color="#3b82f6"),
                ft.Column([status_text, status_sub])
            ]),
            padding=15,
            border_radius=15,
            bgcolor="#0f172a"
        ),
        downloads_block
    ], spacing=15)

    history_view = ft.Column([
        header,
        history_block
    ], spacing=15, visible=False)

    content = ft.SafeArea(
        content=ft.Container(
            content=ft.Column([
                main_view,
                history_view
            ]),
            padding=20
        )
    )

    page.add(content)
    page.navigation_bar = nav

    refresh_lists()


ft.run(main, assets_dir="assets")