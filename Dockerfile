# 1. С чего начинаем
FROM python:3.11-slim

# 2. Устанавливаем Gunicorn (наш WSGI-сервер)
RUN pip install gunicorn

# 3. Создаем папку /app внутри "коробки"
WORKDIR /app

# 4. Копируем requirements.txt и устанавливаем библиотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копируем ВЕСЬ остальной проект (app.py, static, templates) внутрь "коробки"
COPY . .

# 6. Говорим Docker, что Gunicorn будет работать на порту 8000
EXPOSE 8000

# 7. Команда, которая запускается при старте "коробки"
# Она запускает Gunicorn, который, в свою очередь, запускает ваш app:app
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]