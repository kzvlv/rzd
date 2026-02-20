from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

# Мы создаем объекты здесь
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

# Настройки для login_manager
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Пожалуйста, авторизуйтесь, чтобы получить доступ к этой странице.'