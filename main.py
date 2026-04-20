import flet as ft
import yt_dlp
import os

def main(page: ft.Page):
    page.title = "Video Downloader"
    page.theme_mode = ft.ThemeMode.DARK

    url_input = ft.TextField(label="Введите ссылку", expand=True)
    status_text = ft.Text("")
    
    video_player = ft.Video(
        expand=True,
        autoplay=False,
    )

    downloads_path = ft.StoragePaths.get_downloads_directory()

    def download_video(e):
        url = url_input.value.strip()

        if not url:
            status_text.value = "Введите ссылку"
            page.update()
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

            video_player.src = filename
            video_player.play()

        except Exception as ex:
            status_text.value = f"Ошибка: {ex}"

        page.update()

    page.add(
        ft.Column(
            [
                url_input,
                ft.ElevatedButton("Скачать", on_click=download_video),
                status_text,
                video_player,
            ],
            expand=True,
        )
    )


ft.app(target=main)
