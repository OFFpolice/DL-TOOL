import os
import yt_dlp
import threading
import json

import flet as ft
import flet_permission_handler as fph

DEFAULT_DOWNLOAD_PATH = "/storage/emulated/0/dl_tool"
SETTINGS_FILE = "/storage/emulated/0/dl_tool/.settings.json"


def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"download_path": DEFAULT_DOWNLOAD_PATH}


def save_settings(settings: dict):
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)
    except Exception:
        pass


def main(page: ft.Page):
    page.title = "DL-TOOL"
    page.bgcolor = "#0b0f1a"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    ph = fph.PermissionHandler()

    # --- Настройки ---
    settings = load_settings()
    download_path = settings.get("download_path", DEFAULT_DOWNLOAD_PATH)

    # --- История загрузок ---
    download_history: list[str] = []

    def load_history_from_folder(path: str) -> list[str]:
        try:
            files = [
                f for f in os.listdir(path)
                if os.path.isfile(os.path.join(path, f))
                and f.lower().endswith(
                    (".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".m4v")
                )
                and not f.startswith(".")
            ]
            files.sort(
                key=lambda x: os.path.getmtime(os.path.join(path, x)),
                reverse=True,
            )
            return files
        except Exception:
            return []

    # ─── Вспомогательные функции ────────────────────────────────────────────

    def show_snackbar(message: str):
        page.snack_bar = ft.SnackBar(ft.Text(message), open=True)
        page.update()

    # ─── Разрешения ─────────────────────────────────────────────────────────

    async def request_all_permissions() -> bool:
        """
        Запрашивает все необходимые разрешения.
        MANAGE_EXTERNAL_STORAGE даёт полный доступ к /storage/emulated/0/
        на Android 11+. Без него создать папку вне app-каталога невозможно.
        """
        required = [
            fph.Permission.STORAGE,
            fph.Permission.MANAGE_EXTERNAL_STORAGE,
            fph.Permission.VIDEOS,
        ]
        all_granted = True
        for perm in required:
            try:
                status = await ph.get_status(perm)
                if not status or status.name != "GRANTED":
                    status = await ph.request(perm)
                if not status or status.name != "GRANTED":
                    if perm == fph.Permission.MANAGE_EXTERNAL_STORAGE:
                        # Открываем системный экран «Доступ ко всем файлам»
                        await ph.open_app_settings()
                    all_granted = False
            except Exception:
                continue
        return all_granted

    # ─── Навигация / хедер ──────────────────────────────────────────────────

    current_tab = [0]
    body = ft.Container(expand=True)

    back_btn = ft.IconButton(
        icon=ft.Icons.ARROW_BACK,
        icon_color="white",
        visible=False,
        on_click=lambda e: go_home(),
    )
    header_title = ft.Row(
        [
            ft.Text("DL", size=28, weight="bold", color="#3b82f6"),
            ft.Text("TOOL", size=28, weight="bold"),
        ]
    )
    header = ft.Row(
        [
            ft.Row([back_btn, header_title]),
        ],
        alignment=ft.MainAxisAlignment.START,
    )

    nav = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.DOWNLOAD, label="Скачать"),
            ft.NavigationBarDestination(icon=ft.Icons.HISTORY, label="История"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Настройки"),
        ],
        bgcolor="#0f172a",
        on_change=lambda e: show_page(e.control.selected_index),
    )

    def go_home():
        nav.selected_index = 0
        show_page(0)

    # ─── Состояние загрузчика ────────────────────────────────────────────────

    status_text = ft.Text("Готов к скачиванию", size=16, weight="bold")
    status_sub = ft.Text(
        "Вставьте ссылку и нажмите «Скачать»", size=12, color="#8a8f9c"
    )

    url_input = ft.TextField(
        hint_text="Введите ссылку",
        expand=True,
        bgcolor="#111827",
        border_radius=12,
        border_color="#1f2937",
        color="white",
    )

    downloads_column = ft.Column()

    def update_status(main_text, sub):
        status_text.value = main_text
        status_sub.value = sub
        page.update()

    def build_video_item(filename: str) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.VIDEO_FILE, color="#3b82f6", size=20),
                    ft.Text(filename, size=12, expand=True, no_wrap=False),
                ],
                spacing=10,
            ),
            padding=10,
            bgcolor="#111827",
            border_radius=10,
        )

    empty_block = ft.Column(
        [
            ft.Icon(ft.Icons.FOLDER, size=50, color="#3b82f6"),
            ft.Text("Здесь пока пусто"),
            ft.Text(
                "Ваши скачанные видео появятся здесь",
                size=12,
                color="#8a8f9c",
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    downloads_container = ft.Container(
        content=empty_block,
        padding=20,
        alignment=ft.Alignment(0, 0),
    )

    def refresh_downloads():
        downloads_container.content = (
            downloads_column if downloads_column.controls else empty_block
        )
        page.update()

    def add_download_item(filename: str):
        download_history.insert(0, filename)
        downloads_column.controls.insert(0, build_video_item(filename))
        refresh_downloads()

    def rebuild_history_from_folder():
        files = load_history_from_folder(download_path)
        downloads_column.controls.clear()
        for f in files:
            downloads_column.controls.append(build_video_item(f))
        refresh_downloads()

    # ─── Скачивание ─────────────────────────────────────────────────────────

    paste_btn = ft.ElevatedButton(
        "Вставить",
        icon=ft.Icons.CONTENT_PASTE,
        style=ft.ButtonStyle(bgcolor="#1f2937", color="white"),
    )
    download_btn = ft.ElevatedButton(
        "Скачать",
        icon=ft.Icons.DOWNLOAD,
        style=ft.ButtonStyle(bgcolor="#2563eb", color="white"),
    )

    def set_loading(state: bool):
        download_btn.disabled = state
        paste_btn.disabled = state
        page.update()

    def download():
        url = url_input.value.strip()
        if not url:
            update_status("Ошибка", "Введите ссылку")
            return

        async def start():
            ok = await request_all_permissions()
            if not ok:
                show_snackbar("Нет необходимых разрешений")
                return
            try:
                os.makedirs(download_path, exist_ok=True)
            except Exception as ex:
                update_status("Ошибка", f"Не удалось создать папку: {ex}")
                return

            update_status("Загрузка...", "Подождите")
            set_loading(True)

            def run():
                try:
                    ydl_opts = {
                        "outtmpl": os.path.join(
                            download_path, "%(title)s.%(ext)s"
                        ),
                        "noplaylist": True,
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        title = info.get("title", "video")
                    page.call_from_thread(
                        lambda: update_status("Готово", "Видео скачано")
                    )
                    page.call_from_thread(lambda: add_download_item(title))
                except Exception as e:
                    page.call_from_thread(
                        lambda: update_status("Ошибка", str(e))
                    )
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

    paste_btn.on_click = paste_clipboard
    download_btn.on_click = lambda e: download()

    # ─── Страница «Скачать» ──────────────────────────────────────────────────

    downloads_block = ft.Container(
        content=ft.Column(
            [
                ft.Text("Последние загрузки", size=16, weight="bold"),
                downloads_container,
            ]
        ),
        padding=15,
        border_radius=20,
        bgcolor="#0f172a",
    )

    download_page_content = ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        url_input,
                        ft.Row(
                            [paste_btn, download_btn],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=15,
                ),
                padding=20,
                border_radius=20,
                bgcolor="#0f172a",
                border=ft.border.all(1, "#1f2937"),
            ),
            ft.Text("Статус", size=16, weight="bold"),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.INFO_OUTLINE, color="#3b82f6"),
                        ft.Column([status_text, status_sub]),
                    ]
                ),
                padding=15,
                border_radius=15,
                bgcolor="#0f172a",
            ),
            downloads_block,
        ],
        spacing=15,
    )

    # ─── Страница «История» ──────────────────────────────────────────────────

    history_column = ft.Column(spacing=10)

    history_empty = ft.Column(
        [
            ft.Icon(ft.Icons.HISTORY, size=50, color="#3b82f6"),
            ft.Text("История пуста"),
            ft.Text(
                "Скачанные видео появятся здесь", size=12, color="#8a8f9c"
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    history_container = ft.Container(
        content=history_empty,
        padding=20,
        alignment=ft.Alignment(0, 0),
        expand=True,
    )

    def refresh_history_page():
        files = load_history_from_folder(download_path)
        history_column.controls.clear()
        if files:
            for f in files:
                history_column.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.VIDEO_FILE, color="#3b82f6", size=20),
                                ft.Text(f, size=12, expand=True, no_wrap=False),
                            ],
                            spacing=10,
                        ),
                        padding=10,
                        bgcolor="#111827",
                        border_radius=10,
                    )
                )
            history_container.content = history_column
        else:
            history_container.content = history_empty
        page.update()

    history_page_content = ft.Column(
        [history_container],
        spacing=15,
        expand=True,
    )

    # ─── Страница «Настройки» ────────────────────────────────────────────────

    path_field = ft.TextField(
        value=download_path,
        label="Папка для загрузки",
        bgcolor="#111827",
        border_radius=12,
        border_color="#1f2937",
        color="white",
        expand=True,
    )

    def save_path(e):
        new_path = path_field.value.strip()
        if not new_path:
            show_snackbar("Путь не может быть пустым")
            return

        async def do_save():
            nonlocal download_path
            ok = await request_all_permissions()
            if not ok:
                show_snackbar(
                    "Нет разрешения на запись. Выдайте «Доступ ко всем файлам» в настройках."
                )
                return
            try:
                os.makedirs(new_path, exist_ok=True)
            except Exception as ex:
                show_snackbar(f"Ошибка создания папки: {ex}")
                return
            download_path = new_path
            settings["download_path"] = download_path
            save_settings(settings)
            path_field.value = download_path
            page.update()
            show_snackbar("Папка сохранена")
            rebuild_history_from_folder()

        page.run_task(do_save)

    def reset_path(e):
        path_field.value = DEFAULT_DOWNLOAD_PATH
        page.update()

    settings_page_content = ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Папка для загрузки видео", size=14, weight="bold"),
                        ft.Text(
                            "Укажите путь, куда будут сохраняться видео",
                            size=12,
                            color="#8a8f9c",
                        ),
                        ft.Row([path_field]),
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    "Сохранить",
                                    icon=ft.Icons.SAVE,
                                    style=ft.ButtonStyle(
                                        bgcolor="#2563eb", color="white"
                                    ),
                                    on_click=save_path,
                                ),
                                ft.TextButton(
                                    "По умолчанию",
                                    on_click=reset_path,
                                ),
                            ],
                            spacing=10,
                        ),
                    ],
                    spacing=12,
                ),
                padding=15,
                border_radius=15,
                bgcolor="#0f172a",
                border=ft.border.all(1, "#1f2937"),
            ),
        ],
        spacing=15,
    )

    # ─── show_page ───────────────────────────────────────────────────────────

    def show_page(index: int):
        current_tab[0] = index

        # Кнопка «назад» видна на истории (1) и настройках (2)
        back_btn.visible = index in (1, 2)
        # Кнопка настроек скрыта, когда уже на странице настроек
        # Навбар скрываем на странице настроек
        page.navigation_bar = nav if index != 2 else None
        if index < 2:
            nav.selected_index = index

        if index == 0:
            body.content = download_page_content
        elif index == 1:
            refresh_history_page()
            body.content = history_page_content
        elif index == 2:
            path_field.value = download_path
            body.content = settings_page_content

        page.update()

    # ─── Сборка страницы ─────────────────────────────────────────────────────

    content = ft.SafeArea(
        content=ft.Container(
            content=ft.Column(
                [header, body],
                spacing=15,
                expand=True,
            ),
            padding=20,
            expand=True,
        )
    )

    page.add(content)
    page.navigation_bar = nav
    show_page(0)

    # ─── Запрос разрешений при старте ───────────────────────────────────────

    async def request_permissions_on_start():
        granted = await request_all_permissions()
        if granted:
            try:
                os.makedirs(download_path, exist_ok=True)
            except Exception:
                pass
            rebuild_history_from_folder()
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text(
                    "Выдайте разрешение «Доступ ко всем файлам» в настройках приложения."
                ),
                open=True,
            )
            page.update()

    page.run_task(request_permissions_on_start)


ft.run(main, assets_dir="assets")