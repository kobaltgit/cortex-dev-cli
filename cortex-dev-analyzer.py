#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CortexDev Local Project Analyzer
Version: 1.2.0

Этот скрипт сканирует директорию, в которой он запущен, и создает
`cortex-snapshot.json`. Этот файл содержит:
1. Полное дерево всех файлов и папок проекта.
2. Содержимое только текстовых файлов.
"""

import os
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- НАЧАЛО ИЗМЕНЕНИЙ: Импорт для GUI-сообщений ---
try:
    import tkinter as tk
    from tkinter import messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
# --- КОНЕЦ ИЗМЕНЕНИЙ ---


# --- КОНФИГУРАЦИЯ ---
DEFAULT_IGNORE_DIRS = {
    '.git', '__pycache__', 'node_modules', 'venv', '.venv',
    'dist', 'build', '.idea', '.vscode', 'target', 'out'
}
BINARY_FILE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
    '.zip', '.gz', '.tar', '.rar',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.exe', '.dll', '.so', '.o', '.a',
    '.jar', '.class',
    '.mp3', '.wav', '.flac',
    '.mp4', '.mkv', '.avi', '.mov',
    '.ttf', '.woff', '.woff2', '.eot',
    '.db', '.sqlite', '.sqlite3'
}
OUTPUT_FILENAME = "cortex-snapshot.json"

FORCE_TEXT_FILE_EXTENSIONS = {
    '.json', '.yaml', '.yml', '.md', '.txt', '.log', '.xml', '.ini', '.cfg', '.conf',
    '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss', '.less',
    '.java', '.cs', '.c', '.cpp', '.h', '.hpp', '.go', '.rb', '.rs', '.sh',
    '.vue', '.svelte', '.toml', '.env'
}

# --- НАЧАЛО ИЗМЕНЕНИЙ: Новая функция для вывода сообщений ---
def show_message_and_exit(title: str, message: str, is_error: bool = False):
    """
    Показывает сообщение в GUI-окне (если tkinter доступен) или в консоли,
    а затем завершает работу скрипта.
    """
    print(message) # Всегда выводим в консоль на всякий случай
    if TKINTER_AVAILABLE:
        try:
            root = tk.Tk()
            root.withdraw()  # Скрываем основное пустое окно
            if is_error:
                messagebox.showerror(title, message)
            else:
                messagebox.showinfo(title, message)
            root.destroy()
        except Exception:
            # Если GUI не сработало, просто завершаем
            pass
    
    # Завершаем скрипт с кодом ошибки или успеха
    sys.exit(1 if is_error else 0)
# --- КОНЕЦ ИЗМЕНЕНИЙ ---


def is_text_file(file_path: Path) -> bool:
    """
    Определяет, является ли файл текстовым.
    Если расширение файла явно указано как текстовое, считаем его текстовым
    без дальнейших проверок на NULL-байты.
    """
    file_ext = file_path.suffix.lower()

    # НАЧАЛО ИЗМЕНЕНИЙ
    if file_ext in FORCE_TEXT_FILE_EXTENSIONS:
        return True
    # КОНЕЦ ИЗМЕНЕНИЙ

    if file_ext in BINARY_FILE_EXTENSIONS:
        return False
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:
                return False
    except (IOError, OSError):
        return False
    return True


def analyze_directory(root_path: Path) -> tuple[list, dict]:
    """
    Рекурсивно обходит директорию, собирая структуру и содержимое.
    """
    print("Начинаю сканирование директории...")
    
    all_file_paths = []
    text_file_contents = {}

    for root, dirs, files in os.walk(root_path, topdown=True):
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS]

        current_path = Path(root)
        
        for filename in files:
            if filename in {os.path.basename(__file__), OUTPUT_FILENAME}:
                continue

            file_path = current_path / filename
            relative_path_str = str(file_path.relative_to(root_path))

            relative_path_str = relative_path_str.replace(os.sep, '/')
            
            all_file_paths.append(relative_path_str)

            if is_text_file(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    text_file_contents[relative_path_str] = content
                except Exception as e:
                    print(f"  [Предупреждение] Не удалось прочитать текстовый файл {file_path}: {e}")

    print(f"Сканирование завершено. Найдено {len(all_file_paths)} файлов для дерева.")
    print(f"Из них {len(text_file_contents)} текстовых, их содержимое сохранено.")
    return all_file_paths, text_file_contents


def build_tree_from_paths(paths: list) -> list:
    """
    Строит древовидную структуру из плоского списка путей.
    """
    tree = {}
    for path in sorted(paths):
        parts = Path(path).parts
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = None

    def format_tree(node_dict: dict, current_path: str = "") -> list:
        """Рекурсивно форматирует словарь в нужный JSON-формат."""
        formatted_list = []
        for name, content in sorted(node_dict.items()):
            key_path = os.path.join(current_path, name) if current_path else name
            key_path = key_path.replace('\\', '/')

            if content is None:
                formatted_list.append({
                    "key": key_path,
                    "title": name,
                    "type": "file",
                })
            else:
                formatted_list.append({
                    "key": key_path,
                    "title": name,
                    "type": "folder",
                    "children": format_tree(content, key_path)
                })
        return formatted_list

    return format_tree(tree)


def main():
    """
    Главная функция скрипта.
    """
    print("--- CortexDev Local Project Analyzer ---")
    
    project_root = Path.cwd()
    
    all_paths, text_contents = analyze_directory(project_root)
    
    if not all_paths:
        # --- ИЗМЕНЕНИЕ: Используем новую функцию ---
        show_message_and_exit(
            title="Анализ завершен",
            message="В директории не найдено файлов для анализа. Snapshot не создан."
        )
        
    print("Строю дерево файлов...")
    file_tree = build_tree_from_paths(all_paths)
    
    snapshot_data = {
        "version": "1.2.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "tree": file_tree,
        "files": text_contents
    }
    
    output_path = project_root / OUTPUT_FILENAME
    print(f"Сохраняю результат в файл: {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(snapshot_data, f, ensure_ascii=False)
        
    final_message = f"Готово! Файл '{OUTPUT_FILENAME}' успешно создан.\n\nТеперь вы можете загрузить его в веб-интерфейс CortexDev."
    # --- ИЗМЕНЕНИЕ: Используем новую функцию ---
    show_message_and_exit(
        title="Анализ успешно завершен",
        message=final_message
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_message = f"[Критическая ошибка]\nПроизошла ошибка во время выполнения:\n\n{e}"
        # --- ИЗМЕНЕНИЕ: Используем новую функцию для вывода ошибки ---
        show_message_and_exit(
            title="Критическая ошибка",
            message=error_message,
            is_error=True
        )