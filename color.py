import openpyxl

# Загружаем вашу таблицу
wb = openpyxl.load_workbook('table.xlsx')
ws = wb.active

# ВВЕДИТЕ СЮДА НОМЕР СТРОКИ, КОТОРАЯ ТОЧНО ЗЕЛЕНАЯ В EXCEL
ROW_NUMBER = 2  # Например, строка 2

cell = ws[f'A{ROW_NUMBER}']
print(f"--- АНАЛИЗ ЦВЕТА СТРОКИ {ROW_NUMBER} ---")
print(f"Тип заливки: {cell.fill.fill_type}")
print(f"Код цвета (Start Color): {cell.fill.start_color.index}")

# Иногда цвет в theme
if hasattr(cell.fill.start_color, 'theme'):
     print(f"Theme index: {cell.fill.start_color.theme}")