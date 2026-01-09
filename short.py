import zipfile
import io
from pypdf import PdfReader

# Впиши сюда название твоего архива
archive_name = 'archive.zip'
total_pages = 0

try:
    with zipfile.ZipFile(archive_name, 'r') as zf:
        # Проходим по всем файлам внутри архива (включая вложенные папки)
        for filename in zf.namelist():
            if filename.lower().endswith('.pdf'):
                try:
                    # Читаем файл в память без распаковки
                    with zf.open(filename) as f:
                        pdf_file = io.BytesIO(f.read())
                        reader = PdfReader(pdf_file)
                        # Проверяем, не зашифрован ли файл (если нужно)
                        if not reader.is_encrypted:
                            total_pages += len(reader.pages)
                        else:
                            print(f"Файл зашифрован: {filename}")
                except Exception as e:
                    print(f"Ошибка при чтении {filename}: {e}")

    print(f"\n--- ИТОГ ---")
    print(f"Всего страниц во всех PDF: {total_pages}")

except FileNotFoundError:
    print("Ошибка: Архив не найден. Проверь имя файла.")