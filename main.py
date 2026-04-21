import flet as ft
import yt_dlp
import os


def main(page: ft.Page):
    page.title = "DL TOOL"
    page.theme_mode = ft.ThemeMode.DARK

    url_input = ft.TextField(label="Введите ссылку", expand=True)
    status_text = ft.Text("")

    downloads_path = None

    def init_paths(e):
        nonlocal downloads_path
        downloads_path = page.storage_paths.get_downloads_directory()

    page.on_mount = init_paths

    def request_permissions():
        perms = [
            ft.PermissionType.STORAGE,
            ft.PermissionType.MEDIA_LIBRARY,
        ]

        result = page.request_permissions(perms)

        if not all(result.values()):
            status_text.value = "Нет разрешений на память"
            page.update()
            return False

        return True

    def download_video(e):
        url = url_input.value.strip()

        if not url:
            status_text.value = "Введите ссылку"
            page.update()
            return

        if not request_permissions():
            return

        try:
            status_text.value = "Загрузка..."
            page.update()

            ydl_opts = {
                "outtmpl": os.path.join(downloads_path, "%(title)s.%(ext)s"),
                "format": "mp4",
                "noplaylist": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            status_text.value = f"Скачано:\n{filename}"

        except Exception as ex:
            status_text.value = f"Ошибка: {ex}"

        page.update()

    page.add(
        ft.Column(
            [
                url_input,
                ft.ElevatedButton("Скачать", on_click=download_video),
                status_text,
            ],
            expand=True,
        )
    )


ft.run(main, assets_dir="assets")
