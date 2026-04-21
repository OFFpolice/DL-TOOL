import flet as ft
import yt_dlp
import os
import re


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name)


def main(page: ft.Page):
    page.title = "DL TOOL"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.bgcolor = "#0f1115"

    downloads_path = None
    history = []

    def init_paths(e):
        nonlocal downloads_path
        downloads_path = page.storage_paths.get_downloads_directory()

    page.on_mount = init_paths

    url_input = ft.TextField(
        hint_text="Введите ссылку",
        border_radius=12,
        expand=True,
        filled=True,
    )

    status_title = ft.Text("Готов к скачиванию", size=16, weight="bold")
    status_sub = ft.Text("Вставьте ссылку и нажмите «Скачать»", size=12, color="grey")

    history_column = ft.Column(spacing=10)

    def update_history():
        history_column.controls.clear()

        if not history:
            history_column.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.FOLDER, size=48, color="blue"),
                            ft.Text("Здесь пока пусто"),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    height=150,
                )
            )
        else:
            for item in history[-5:][::-1]:
                history_column.controls.append(
                    ft.Container(
                        content=ft.Text(item, size=12),
                        padding=10,
                        border_radius=10,
                        bgcolor="#1a1d24",
                    )
                )

        page.update()

    def download_video(e):
        nonlocal downloads_path

        url = url_input.value.strip()

        if not url:
            status_title.value = "Ошибка"
            status_sub.value = "Введите ссылку"
            page.update()
            return

        if not downloads_path:
            status_title.value = "Ошибка"
            status_sub.value = "Путь загрузки недоступен"
            page.update()
            return

        try:
            status_title.value = "Загрузка..."
            status_sub.value = "Подождите"
            page.update()

            ydl_opts = {
                "outtmpl": os.path.join(downloads_path, "%(title)s.%(ext)s"),
                "format": "mp4",
                "noplaylist": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            filename = sanitize_filename(os.path.basename(filename))

            history.append(filename)

            status_title.value = "Скачано"
            status_sub.value = filename

            update_history()

        except Exception as ex:
            status_title.value = "Ошибка"
            status_sub.value = str(ex)

        page.update()

    header = ft.Row(
        [
            ft.Text("DL TOOL", size=24, weight="bold"),
            ft.IconButton(ft.Icons.SETTINGS),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    input_card = ft.Container(
        content=ft.Column(
            [
                url_input,
                ft.Row(
                    [
                        ft.OutlinedButton("Вставить"),
                        ft.ElevatedButton("Скачать", on_click=download_video),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ]
        ),
        padding=15,
        border_radius=16,
        bgcolor="#1a1d24",
    )

    status_card = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.INFO, color="blue"),
                ft.Column([status_title, status_sub]),
            ]
        ),
        padding=15,
        border_radius=16,
        bgcolor="#1a1d24",
    )

    history_block = ft.Column(
        [
            ft.Row(
                [
                    ft.Text("Последние загрузки", size=16),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            history_column,
        ]
    )

    update_history()

    page.add(
        ft.Column(
            [
                header,
                input_card,
                ft.Text("Статус"),
                status_card,
                history_block,
            ],
            spacing=20,
            expand=True,
        )
    )


ft.run(main, assets_dir="assets")

