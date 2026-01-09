from app import app, db
# Импортируем только то, что реально существует в models.py
from models import Room, Booking

with app.app_context():
    # 1. Ищем комнату
    # В models.py поле называется room_number, а не number
    room_to_delete = Room.query.filter_by(room_number='301').first()

    if room_to_delete:
        print(f"Найдена комната ID {room_to_delete.id} (Номер {room_to_delete.room_number})")

        # 2. Находим ВСЕ бронирования, привязанные к этой комнате
        # (Так как таблицы Bed нет, мы ищем сразу по room_id)
        bookings = Booking.query.filter_by(room_id=room_to_delete.id).all()

        if bookings:
            print(f"Найдено {len(bookings)} бронирований. Удаляем их...")
            for b in bookings:
                db.session.delete(b)
        else:
            print("Бронирований в этой комнате нет.")

        # 3. Удаляем саму комнату
        db.session.delete(room_to_delete)

        # 4. Сохраняем изменения
        db.session.commit()
        print("✅ УСПЕХ: Комната 301 полностью удалена.")
    else:
        print("❌ Ошибка: Комната 301 не найдена в базе данных.")