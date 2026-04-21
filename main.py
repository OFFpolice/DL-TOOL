import flet as ft
import yt_dlp
import os
import threading
from pathlib import Path

# Глобальные переменные
download_folder = str(Path.home() / "Downloads")
history_list = []  # Список для хранения истории загрузок

def main(page: ft.Page):
    page.title = "DL TOOL"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.window_width = 400
    page.window_height = 700
    page.scroll = ft.ScrollMode.AUTO

    # --- UI Компоненты ---
    
    # Поле для ввода ссылки
    url_field = ft.TextField(
        hint_text="Введите ссылку",
        border_color=ft.Colors.BLUE_400,
        focused_border_color=ft.Colors.BLUE_600,
        border_radius=8,
    )

    # Статус
    status_text = ft.Text(
        "Готов к скачиванию\nВставьте ссылку и нажмите «Скачать»",
        size=14,
        weight=ft.FontWeight.W_400,
        color=ft.Colors.GREY_400,
        text_align=ft.TextAlign.CENTER,
    )

    # Прогресс-бар
    progress_bar = ft.ProgressBar(width=300, visible=False)
    
    # Процент выполнения
    progress_percent = ft.Text("", size=12, color=ft.Colors.BLUE_400, visible=False)

    # Список последних загрузок
    downloads_column = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)

    # Кнопки управления
    paste_button = ft.OutlinedButton(
        "Вставить",
        icon=ft.icons.PASTE,
        on_click=lambda _: paste_from_clipboard(),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
    )
    
    download_button = ft.ElevatedButton(
        "Скачать",
        icon=ft.icons.DOWNLOAD,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_400,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        on_click=lambda _: start_download(),
    )

    open_folder_button = ft.TextButton(
        "Открыть папку",
        icon=ft.icons.FOLDER_OPEN,
        on_click=lambda _: open_download_folder(),
    )

    # FilePicker для выбора папки сохранения
    file_picker = ft.FilePicker(on_result=on_file_picker_result)
    page.overlay.append(file_picker)

    def paste_from_clipboard():
        """Вставка текста из буфера обмена."""
        clipboard_text = page.get_clipboard()
        if clipboard_text:
            url_field.value = clipboard_text
            page.update()

    def on_file_picker_result(e: ft.FilePickerResultEvent):
        """Обработчик выбора папки."""
        global download_folder
        if e.path:
            download_folder = e.path
            status_text.value = f"Папка сохранения:\n{e.path}"
            page.update()

    def open_download_folder():
        """Открытие папки с загрузками."""
        try:
            os.startfile(download_folder) if os.name == 'nt' else os.system(f'xdg-open "{download_folder}"')
        except Exception as ex:
            status_text.value = f"Ошибка: {ex}"
            page.update()

    def add_to_history(filename, status="Завершено"):
        """Добавление записи в историю загрузок."""
        history_list.append({"filename": filename, "status": status})
        update_history_ui()

    def update_history_ui():
        """Обновление UI списка истории."""
        downloads_column.controls.clear()
        if not history_list:
            downloads_column.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.HISTORY, size=40, color=ft.Colors.GREY_400),
                        ft.Text("Здесь пока пусто", color=ft.Colors.GREY_400),
                        ft.Text("Ваши скачанные видео появятся здесь", size=12, color=ft.Colors.GREY_400),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=20,
                )
            )
        else:
            for item in history_list[-5:]:  # Показываем последние 5 загрузок
                icon = ft.icons.CHECK_CIRCLE if item["status"] == "Завершено" else ft.icons.ERROR
                color = ft.Colors.GREEN_400 if item["status"] == "Завершено" else ft.Colors.RED_400
                downloads_column.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(icon, color=color, size=20),
                        title=ft.Text(item["filename"], size=12),
                        dense=True,
                    )
                )
        page.update()

    # --- Логика загрузки ---
    
    def progress_hook(d):
        """Хук для отслеживания прогресса загрузки."""
        if d['status'] == 'downloading':
            if d.get('total_bytes'):
                percent = d['downloaded_bytes'] / d['total_bytes']
                progress_bar.value = percent
                progress_percent.value = f"{percent:.1%}"
                
                # Обновление статуса
                speed = d.get('speed', 0)
                if speed:
                    speed_str = f"{speed/1024/1024:.1f} МБ/с"
                else:
                    speed_str = ""
                eta = d.get('eta', 0)
                eta_str = f"Осталось: {eta} сек" if eta else ""
                
                status_text.value = f"Загрузка... {progress_percent.value}\n{speed_str} {eta_str}"
            else:
                # Если общий размер неизвестен, показываем только загруженные байты
                downloaded = d.get('downloaded_bytes', 0)
                downloaded_mb = downloaded / 1024 / 1024
                status_text.value = f"Загружено: {downloaded_mb:.1f} МБ"
            
            page.update()
            
        elif d['status'] == 'finished':
            progress_bar.visible = False
            progress_percent.visible = False
            status_text.value = "Обработка видео..."
            page.update()
            
        elif d['status'] == 'error':
            progress_bar.visible = False
            progress_percent.visible = False
            status_text.value = f"Ошибка загрузки: {d.get('error', 'Неизвестная ошибка')}"
            add_to_history(url_field.value, "Ошибка")
            page.update()

    def download_video():
        """Функция загрузки видео в отдельном потоке."""
        url = url_field.value.strip()
        if not url:
            status_text.value = "Введите ссылку на видео"
            page.update()
            return

        # Настройка UI перед загрузкой
        download_button.disabled = True
        progress_bar.visible = True
        progress_percent.visible = True
        progress_bar.value = 0
        progress_percent.value = "0%"
        status_text.value = "Подготовка к загрузке..."
        page.update()

        # Опции для yt-dlp
        ydl_opts = {
            'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'noplaylist': True,  # Не загружать плейлисты, только одно видео
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Получаем информацию о видео
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'video')
                
                # Начинаем загрузку
                ydl.download([url])
                
                # После успешной загрузки
                status_text.value = f"Готово! Видео сохранено в:\n{download_folder}"
                add_to_history(video_title, "Завершено")
                
        except Exception as e:
            status_text.value = f"Ошибка: {str(e)}"
            add_to_history(url, "Ошибка")
            
        finally:
            download_button.disabled = False
            progress_bar.visible = False
            progress_percent.visible = False
            page.update()

    def start_download():
        """Запуск загрузки в отдельном потоке."""
        threading.Thread(target=download_video, daemon=True).start()

    # --- Сборка UI ---
    
    # Верхняя часть с вводом ссылки и кнопками
    top_section = ft.Column([
        ft.Text("DL TOOL", size=28, weight=ft.FontWeight.BOLD),
        ft.Text("Введите ссылку", size=16),
        url_field,
        ft.Row([
            paste_button,
            download_button,
        ], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(height=20),
        
        # Статус
        ft.Text("Статус", size=16, weight=ft.FontWeight.BOLD),
        ft.Container(
            content=status_text,
            padding=10,
            bgcolor=ft.Colors.GREY_900,
            border_radius=8,
            alignment=ft.alignment.center,
        ),
        progress_bar,
        progress_percent,
        
        ft.Divider(height=20),
        
        # Последние загрузки
        ft.Row([
            ft.Text("Последние загрузки", size=16, weight=ft.FontWeight.BOLD),
            open_folder_button,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
    ])

    # Добавляем все на страницу
    page.add(
        top_section,
        ft.Container(
            content=downloads_column,
            padding=10,
            bgcolor=ft.Colors.GREY_900,
            border_radius=8,
            height=250,
        ),
    )

    # Инициализация истории
    update_history_ui()

ft.run(main, assets_dir="assets")

