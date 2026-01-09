import sys
import os
from getpass import getpass

# Импортируем app, db, и модели
# app нужен для app_context
from app import app
# db нужен для создания таблиц
from extensions import db
# Модели нужны для создания данных
from models import Dorm, Room, User


def create_initial_data():
    # Обязательно "входим" в контекст приложения
    with app.app_context():
        print("Creating database tables...")
        db.create_all()

        # Проверяем, есть ли уже общежития
        if Dorm.query.first() is None:
            print("Creating initial dorms...")
            d1 = Dorm(
                name="ул. Революции 1905 г., д. 73 к2",
                address="г. Улан-Удэ, ул. Революции 1905 г., д. 73 к2",
                description="г. Улан-Удэ, ул. Революции 1905 г., д. 73 к2",
                contact_info="Тел: +7 (495) 000-00-01"
            )
            d2 = Dorm(
                name="ул. Гольдсобеля д. 1",
                address="г. Улан-Удэ, ул. Гагарина, д. 56А",
                description="г. Улан-Удэ, ул. Гольдсобеля д. 1",
                contact_info="Тел: +7 (495) 000-00-02"
            )
            db.session.add_all([d1, d2])
            db.session.commit()  # Сохраняем, чтобы получить ID

            # Создаем комнаты
            rooms_d1 = []
            for i in range(1, 7):  # 6 комнат на 3 чел
                rooms_d1.append(Room(dorm_id=d1.id, room_number=f"1{i:02d}", capacity=3))
            for i in range(1, 4):  # 3 комнаты на 2 чел
                rooms_d1.append(Room(dorm_id=d1.id, room_number=f"2{i:02d}", capacity=2))

            rooms_d2 = []
            for i in range(1, 7):  # 6 комнат на 3 чел
                rooms_d2.append(Room(dorm_id=d2.id, room_number=f"3{i:02d}", capacity=3))
            for i in range(1, 4):  # 3 комнаты на 2 чел
                rooms_d2.append(Room(dorm_id=d2.id, room_number=f"4{i:02d}", capacity=2))

            db.session.add_all(rooms_d1)
            db.session.add_all(rooms_d2)

            print("Initial dorms and rooms created.")
        else:
            print("Database already contains dorms.")

        # Создание первого Администратора
        if User.query.filter_by(role='Admin').first() is None:
            print("Creating first Admin user...")
            username = input("Enter Admin username: ")
            password = input("Enter Admin password: ")
            full_name = input("Enter Admin full name: ")
            phone = input("Enter Admin phone: ")

            admin_user = User(
                username=username,
                full_name=full_name,
                phone=phone,
                role='Admin'
            )
            admin_user.set_password(password)
            db.session.add(admin_user)
            print("Admin user created successfully.")
        else:
            print("Admin user already exists.")

        # Финальный коммит
        db.session.commit()


if __name__ == '__main__':
    create_initial_data()
    print("Database initialization complete.")