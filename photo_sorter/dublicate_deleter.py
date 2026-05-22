#!/usr/bin/env python3
"""
Скрипт для удаления дубликатов фотографий по MD5 хешу.
Сохраняет первый найденный файл, удаляет все дубликаты.
"""

import os
import hashlib
import sys
from pathlib import Path
from collections import defaultdict

def get_file_hash(filepath, chunk_size=8192):
    """Вычисляет MD5 хеш файла"""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except (IOError, OSError) as e:
        print(f"Ошибка при чтении файла {filepath}: {e}")
        return None

def find_duplicates(folder_path):
    """Находит дубликаты файлов в указанной папке"""
    # Поддерживаемые форматы изображений
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', 
                       '.webp', '.raw', '.cr2', '.nef', '.arw', '.dng'}
    
    hash_map = defaultdict(list)
    total_files = 0
    
    print(f"Сканируем папку: {folder_path}")
    
    # Рекурсивный обход всех файлов
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            ext = Path(filename).suffix.lower()
            if ext in image_extensions:
                filepath = os.path.join(root, filename)
                total_files += 1
                
                if total_files % 100 == 0:
                    print(f"Обработано файлов: {total_files}")
                
                file_hash = get_file_hash(filepath)
                if file_hash:
                    hash_map[file_hash].append(filepath)
    
    return hash_map, total_files

def remove_duplicates(hash_map, dry_run=True):
    """Удаляет дубликаты файлов"""
    duplicates_count = 0
    freed_space = 0
    
    for file_hash, file_list in hash_map.items():
        if len(file_list) > 1:
            # Сохраняем первый файл, остальные - дубликаты
            original = file_list[0]
            duplicates = file_list[1:]
            
            print(f"\nОригинал: {original}")
            print(f"Дубликаты ({len(duplicates)}):")
            
            for duplicate in duplicates:
                print(f"  - {duplicate}")
                duplicates_count += 1
                
                if not dry_run:
                    try:
                        file_size = os.path.getsize(duplicate)
                        os.remove(duplicate)
                        freed_space += file_size
                        print(f"    Удален (освобождено: {file_size / 1024:.2f} КБ)")
                    except OSError as e:
                        print(f"    Ошибка при удалении: {e}")
    
    return duplicates_count, freed_space

def main():
    if len(sys.argv) != 2:
        print("Использование: python remove_duplicates.py <путь_к_папке>")
        print("Пример: python remove_duplicates.py /home/user/photos")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    
    if not os.path.exists(folder_path):
        print(f"Ошибка: папка '{folder_path}' не существует!")
        sys.exit(1)
    
    if not os.path.isdir(folder_path):
        print(f"Ошибка: '{folder_path}' не является папкой!")
        sys.exit(1)
    
    # Сначала показываем, что будет удалено
    print("=" * 60)
    print("РЕЖИМ ПРЕДПРОСМОТРА (файлы не будут удалены)")
    print("=" * 60)
    
    hash_map, total_files = find_duplicates(folder_path)
    print(f"\nВсего обработано изображений: {total_files}")
    print(f"Уникальных файлов: {len(hash_map)}")
    
    duplicates_count, freed_space = remove_duplicates(hash_map, dry_run=True)
    
    if duplicates_count == 0:
        print("\nДубликатов не найдено!")
        return
    
    print(f"\nНайдено дубликатов: {duplicates_count}")
    print(f"Будет освобождено: {freed_space / (1024*1024):.2f} МБ")
    
    # Запрашиваем подтверждение на удаление
    response = input("\nУдалить найденные дубликаты? (да/нет): ").strip().lower()
    
    if response in ['да', 'д', 'yes', 'y']:
        print("\n" + "=" * 60)
        print("УДАЛЕНИЕ ДУБЛИКАТОВ")
        print("=" * 60)
        
        duplicates_count, freed_space = remove_duplicates(hash_map, dry_run=False)
        
        print(f"\nРезультат:")
        print(f"Удалено дубликатов: {duplicates_count}")
        print(f"Освобождено места: {freed_space / (1024*1024):.2f} МБ")
    else:
        print("\nУдаление отменено.")

if __name__ == "__main__":
    main()