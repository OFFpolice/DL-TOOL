import os
import json
import yt_dlp
import threading

import flet as ft
import flet_permission_handler as fph

# Путь по умолчанию (будет переопределён из client_storage)
DEFAULT_DOWNLOAD_PATH = "/storage/emulated/0/dl_tool"

def main(page: ft.Page):
    page.title = "DL-TOOL"
    page.bgcolor = "#0b0f1a"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    ph = fph.PermissionHandler()

    # ------------------------------------------------------------
    # Состояния и настройки
    # ------------------------------------------------------------
    status_text = ft.Text("Готов к скачиванию", size=16, weight="bold")
    status_sub = ft.Text("Вставьте ссылку и нажмите «Скачать»", size=12, color="#8a8f9c")

    url_input = ft.TextField(
        hint_text="Введите ссылку",
        expand=True,
        bgcolor="#111827",
        border_radius=12,
        border_color="#1f2937",
        color="white",
    )

    # Два независимых списка: для главной и для истории
    last_downloads_column = ft.Column()  # на главной
    history_downloads_column = ft.Column()  # в разделе «История»

    # Путь, загружаемый из client_storage
    download_path = DEFAULT_DOWNLOAD_PATH

    # ------------------------------------------------------------
    # Вспомогательные функции
    # ------------------------------------------------------------
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

    def refresh_main_downloads():
        if last_downloads_column.controls:
            main_downloads_container.content = last_downloads_column
        else:
            main_downloads_container.content = empty_block
        page.update()

    def refresh_history_downloads():
        if history_downloads_column.controls:
            history_downloads_container.content = history_downloads_column
        else:
            history_downloads_container.content = empty_block_history
        page.update()

    def add_download_item(title):
        """Добавляет одну запись в оба списка и сохраняет историю."""
        item = ft.Container(
            content=ft.Text(title, size=12),
            padding=10,
            bgcolor="#111827",
            border_radius=10,
        )
        # Добавляем в начало обоих списков
        last_downloads_column.controls.insert(0, item)
        history_downloads_column.controls.insert(0, ft.Container(
            content=ft.Text(title, size=12),
            padding=10,
            bgcolor="#111827",
            border_radius=10,
        ))
        # Обновляем отображения
        refresh_main_downloads()
        refresh_history_downloads()
        # Сохраняем историю в client_storage (только названия)
        page.run_task(save_history)

    async def save_history():
        titles = [c.content.value for c in history_downloads_column.controls if isinstance(c.content, ft.Text)]
        await page.client_storage.set_async("history", json.dumps(titles))

    async def load_history():
        data = await page.client_storage.get_async("history")
        if data:
            try:
                titles = json.loads(data)
                for t in titles:
                    # Добавляем в оба списка без повторного сохранения
                    item = ft.Container(
                        content=ft.Text(t, size=12),
                        padding=10,
                        bgcolor="#111827",
                        border_radius=10,
                    )
                    last_downloads_column.controls.append(item)
                    history_downloads_column.controls.append(item)
            except Exception:
                pass

    async def check_permissions():
        required = [
            fph.Permission.STORAGE,
            fph.Permission.VIDEOS,
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

            update_status("Загрузка...", "Подождите")
            set_loading(True)

            def run():
                try:
                    # Создаём папку, если её нет
                    os.makedirs(download_path, exist_ok=True)
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

    # ------------------------------------------------------------
    # UI элементы
    # ------------------------------------------------------------
    paste_btn = ft.ElevatedButton(
        "Вставить",
        icon=ft.Icons.CONTENT_PASTE,
        style=ft.ButtonStyle(bgcolor="#1f2937", color="white"),
        on_click=paste_clipboard,
    )
    download_btn = ft.ElevatedButton(
        "Скачать",
        icon=ft.Icons.DOWNLOAD,
        style=ft.ButtonStyle(bgcolor="#2563eb", color="white"),
        on_click=lambda e: download(),
    )

    empty_block = ft.Column(
        [
            ft.Icon(ft.Icons.FOLDER, size=50, color="#3b82f6"),
            ft.Text("Здесь пока пусто"),
            ft.Text("Ваши скачанные видео появятся здесь", size=12, color="#8a8f9c"),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
    empty_block_history = ft.Column(
        [
            ft.Icon(ft.Icons.HISTORY, size=50, color="#3b82f6"),
            ft.Text("История пуста"),
            ft.Text("Здесь будут отображаться все ваши загрузки", size=12, color="#8a8f9c"),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Контейнеры для отображения списков
    main_downloads_container = ft.Container(
        content=empty_block,
        padding=20,
        alignment=ft.Alignment(0, 0),
    )
    history_downloads_container = ft.Container(
        content=empty_block_history,
        padding=20,
        alignment=ft.Alignment(0, 0),
    )

    # Блок на главной (без кнопки "Открыть папку")
    downloads_block = ft.Container(
        content=ft.Column([
            ft.Text("Последние загрузки", size=16, weight="bold"),
            main_downloads_container,
        ]),
        padding=15,
        border_radius=20,
        bgcolor="#0f172a",
    )

    # Заголовок
    header = ft.Row([
        ft.Row([
            ft.Text("DL", size=28, weight="bold", color="#3b82f6"),
            ft.Text("TOOL", size=28, weight="bold"),
        ]),
        ft.IconButton(icon=ft.Icons.SETTINGS, on_click=lambda e: open_settings()),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # ------------------------------------------------------------
    # Интерфейс смены папки
    # ------------------------------------------------------------
    async def open_settings():
        path_field = ft.TextField(
            value=download_path,
            hint_text="/storage/emulated/0/dl_tool",
            expand=True,
            bgcolor="#111827",
            border_radius=12,
            border_color="#1f2937",
            color="white",
        )

        async def save_path(e):
            nonlocal download_path
            new_path = path_field.value.strip()
            if not new_path:
                show_snackbar("Путь не может быть пустым")
                return
            # Пытаемся создать папку
            try:
                os.makedirs(new_path, exist_ok=True)
                download_path = new_path
                await page.client_storage.set_async("download_path", new_path)
                show_snackbar("Папка сохранена")
                page.close(dialog)
            except Exception as ex:
                show_snackbar(f"Ошибка: {ex}")

        dialog = ft.AlertDialog(
            title=ft.Text("Настройки папки загрузок"),
            content=ft.Column([
                ft.Text("Введите полный путь к папке:"),
                path_field,
            ], tight=True),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: page.close(dialog)),
                ft.ElevatedButton("Сохранить", on_click=save_path),
            ],
        )
        page.open(dialog)

    # ------------------------------------------------------------
    # Навигация
    # ------------------------------------------------------------
    view_main = ft.Column([
        header,
        ft.Container(
            content=ft.Column([
                url_input,
                ft.Row([paste_btn, download_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=15),
            padding=20,
            border_radius=20,
            bgcolor="#0f172a",
            border=ft.border.all(1, "#1f2937"),
        ),
        ft.Text("Статус", size=16, weight="bold"),
        ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color="#3b82f6"),
                ft.Column([status_text, status_sub]),
            ]),
            padding=15,
            border_radius=15,
            bgcolor="#0f172a",
        ),
        downloads_block,
    ], spacing=15)

    view_history = ft.Column([
        header,
        ft.Text("История загрузок", size=20, weight="bold"),
        history_downloads_container,
    ], spacing=15)

    main_container = ft.Container(
        content=ft.Stack([
            ft.Container(content=view_main, visible=True),
            ft.Container(content=view_history, visible=False),
        ]),
        padding=20,
        expand=True,
    )

    def switch_tab(index):
        # Получаем детей Stack (их всего два)
        stack_children = main_container.content.controls
        stack_children[0].visible = (index == 0)
        stack_children[1].visible = (index == 1)
        page.update()

    nav = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.DOWNLOAD, label="Скачать"),
            ft.NavigationBarDestination(icon=ft.Icons.HISTORY, label="История"),
        ],
        bgcolor="#0f172a",
        on_change=lambda e: switch_tab(e.control.selected_index),
    )

    # ------------------------------------------------------------
    # Инициализация приложения
    # ------------------------------------------------------------
    async def init():
        nonlocal download_path
        # Загружаем путь
        saved_path = await page.client_storage.get_async("download_path")
        if saved_path and isinstance(saved_path, str):
            download_path = saved_path
        # Пытаемся создать папку
        try:
            os.makedirs(download_path, exist_ok=True)
        except Exception:
            show_snackbar(f"Не удалось создать папку {download_path}")
            download_path = DEFAULT_DOWNLOAD_PATH
            await page.client_storage.set_async("download_path", download_path)

        # Загружаем историю
        await load_history()
        refresh_main_downloads()
        refresh_history_downloads()
        page.update()

    page.add(main_container)
    page.navigation_bar = nav
    page.run_task(init)

ft.run(main, assets_dir="assets")