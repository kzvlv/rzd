from flask_login import UserMixin
# Импортируем из нового файла extensions.py
from extensions import db, bcrypt


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False)  # 'Admin', 'Commandant', 'Enterprise'

    # Для Коменданта
    dorm_id = db.Column(db.Integer, db.ForeignKey('dorm.id'), nullable=True)

    # Для Предприятия
    enterprise_name = db.Column(db.String(120), nullable=True)

    # Связи
    bookings = db.relationship('Booking', backref='enterprise_user', lazy=True, foreign_keys='Booking.enterprise_id')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class Dorm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    description = db.Column(db.Text)
    contact_info = db.Column(db.String(100))
    rooms = db.relationship('Room', backref='dorm', lazy=True)
    commandants = db.relationship('User', backref='dorm', lazy=True)


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dorm_id = db.Column(db.Integer, db.ForeignKey('dorm.id'), nullable=False)
    room_number = db.Column(db.String(10), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='available')  # available, repair
    bookings = db.relationship('Booking', backref='room', lazy=True)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    enterprise_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Данные гостя
    full_name = db.Column(db.String(120), nullable=False)
    study_group = db.Column(db.String(50))
    gender = db.Column(db.String(10), nullable=False)
    bed_id = db.Column(db.Integer, nullable=False)  # Уникальный номер места в комнате

    # Даты
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    practice_start = db.Column(db.Date, nullable=True)
    practice_end = db.Column(db.Date, nullable=True)

    # Статус брони
    status = db.Column(db.String(20), default='booked')  # booked, living, cancelled, completed