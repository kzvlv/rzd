import telebot
from telebot import types
from datetime import date
from sqlalchemy import func
import io
import matplotlib

# Включаем режим без экрана для сервера
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Импортируем модули проекта
from app import app
from models import Room, Booking, Dorm, User
import excel_handler  # Ваш модуль для Excel

# === НАСТРОЙКИ ===
API_TOKEN = '8304034581:AAELNQJ31JUdLhcIlpCcWmILLt-_cNx780Q'
ADMIN_IDS = [1185205915,54469827]  # Вставьте ваш ID

bot = telebot.TeleBot(API_TOKEN)
user_data = {}  # Память для пошаговых действий


def is_admin(user_id):
    if not ADMIN_IDS: return True
    return user_id in ADMIN_IDS


# ==========================================
#                  МЕНЮ
# ==========================================

def menu_start():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🏢 Блок: Общежития")
    btn2 = types.KeyboardButton("📦 Блок: Склад")
    markup.add(btn1, btn2)
    return markup


def menu_dorms():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📊 Инфографика (Общ)", "👥 Статистика М/Ж")
    markup.add("🏢 Загрузка (Текст)", "👮‍♂️ Коменданты")
    markup.add("🔍 Проверить комнату", "🔙 В Главное меню")
    return markup


def menu_warehouse():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📈 Дашборд Склада", "📉 Детальная Аналитика")
    markup.add("✅ Приемка товара", "📥 Скачать Excel")
    markup.add("🔙 В Главное меню")
    return markup


# ==========================================
#           ОБЩАЯ НАВИГАЦИЯ
# ==========================================

@bot.message_handler(commands=['start'])
def start(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ Доступ запрещен.")
        return
    bot.send_message(message.chat.id, "👋 Привет! Выберите режим работы:", reply_markup=menu_start())


@bot.message_handler(func=lambda m: m.text == "🔙 В Главное меню")
def back_main(message):
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=menu_start())


# ==========================================
#         БЛОК 1: ОБЩЕЖИТИЯ
# ==========================================

@bot.message_handler(func=lambda m: m.text == "🏢 Блок: Общежития")
def open_dorms(message):
    bot.send_message(message.chat.id, "Управление общежитиями:", reply_markup=menu_dorms())


# --- 1. ИНФОГРАФИКА ОБЩЕЖИТИЙ ---
@bot.message_handler(func=lambda m: m.text == "📊 Инфографика (Общ)")
def dorm_dashboard(message):
    msg = bot.send_message(message.chat.id, "🎨 Рисую статистику по общежитиям...")
    try:
        # Настройка стиля
        sns.set_style("whitegrid")
        fig, axs = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(f'Сводка по заселению на {date.today().strftime("%d.%m.%Y")}', fontsize=16)
        today = date.today()

        with app.app_context():
            # 1. М/Ж
            males = Booking.query.filter(Booking.gender == 'male', Booking.status.in_(['living', 'booked']),
                                         Booking.start_date <= today, Booking.end_date > today).count()
            females = Booking.query.filter(Booking.gender == 'female', Booking.status.in_(['living', 'booked']),
                                           Booking.start_date <= today, Booking.end_date > today).count()

            if males + females > 0:
                axs[0, 0].pie([males, females], labels=['М', 'Ж'], autopct='%1.1f%%', colors=['#3498db', '#e74c3c'],
                              startangle=90)
                axs[0, 0].set_title('Демография')
            else:
                axs[0, 0].text(0.5, 0.5, 'Нет данных', ha='center')

            # 2. Загрузка общежитий
            dorms = Dorm.query.all()
            names, percents = [], []
            for d in dorms:
                cap = sum(r.capacity for r in d.rooms)
                occ = Booking.query.join(Room).filter(Room.dorm_id == d.id, Booking.status.in_(['living', 'booked']),
                                                      Booking.start_date <= today, Booking.end_date > today).count()
                perc = (occ / cap * 100) if cap > 0 else 0
                names.append(d.name.split(',')[0][:10])  # Короткое имя
                percents.append(perc)

            bars = sns.barplot(x=names, y=percents, ax=axs[0, 1], palette="viridis")
            axs[0, 1].set_title('Загрузка (%)')
            axs[0, 1].set_ylim(0, 100)
            # Цифры на барах
            for bar in bars.patches:
                axs[0, 1].annotate(f'{int(bar.get_height())}%',
                                   (bar.get_x() + bar.get_width() / 2., bar.get_height()),
                                   ha='center', va='bottom')

            # 3. Свободно/Занято
            total_cap = Room.query.with_entities(func.sum(Room.capacity)).scalar() or 0
            total_occ = Booking.query.filter(Booking.status.in_(['living', 'booked']), Booking.start_date <= today,
                                             Booking.end_date > today).count()
            total_free = total_cap - total_occ

            axs[1, 0].pie([total_occ, total_free], labels=['Занято', 'Свободно'], colors=['#e67e22', '#2ecc71'],
                          autopct='%1.1f%%', pctdistance=0.85)
            centre_circle = plt.Circle((0, 0), 0.70, fc='white')
            axs[1, 0].add_artist(centre_circle)
            axs[1, 0].set_title(f'Общий фонд: {total_cap}')

            # 4. Топ предприятий
            bookings = Booking.query.filter(Booking.status.in_(['living', 'booked']), Booking.start_date <= today,
                                            Booking.end_date > today).all()
            ent_stats = {}
            for b in bookings:
                name = b.enterprise_user.enterprise_name or "Неизвестно"
                ent_stats[name] = ent_stats.get(name, 0) + 1
            sorted_ent = sorted(ent_stats.items(), key=lambda item: item[1], reverse=True)[:5]

            if sorted_ent:
                names = [x[0][:10] for x in sorted_ent]
                counts = [x[1] for x in sorted_ent]
                sns.barplot(x=counts, y=names, ax=axs[1, 1], palette="magma", orient='h')
                axs[1, 1].set_title('Топ Предприятий')
            else:
                axs[1, 1].text(0.5, 0.5, 'Нет жильцов', ha='center')

        # Сохранение и отправка
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        bot.send_photo(message.chat.id, buf)
        bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")


# --- ТЕКСТОВАЯ СТАТИСТИКА ОБЩЕЖИТИЙ ---
@bot.message_handler(func=lambda m: m.text == "👥 Статистика М/Ж")
def gender_stats(message):
    with app.app_context():
        today = date.today()
        m = Booking.query.filter(Booking.gender == 'male', Booking.status.in_(['living', 'booked']),
                                 Booking.start_date <= today, Booking.end_date > today).count()
        f = Booking.query.filter(Booking.gender == 'female', Booking.status.in_(['living', 'booked']),
                                 Booking.start_date <= today, Booking.end_date > today).count()
        bot.send_message(message.chat.id, f"👥 <b>Сейчас проживают:</b>\n👨 Мужчин: {m}\n👩 Женщин: {f}",
                         parse_mode='HTML')


@bot.message_handler(func=lambda m: m.text == "🏢 Загрузка (Текст)")
def dorm_text_stats(message):
    with app.app_context():
        dorms = Dorm.query.all()
        text = "🏢 <b>Детализация:</b>\n\n"
        for d in dorms:
            cap = sum(r.capacity for r in d.rooms)
            occ = Booking.query.join(Room).filter(Room.dorm_id == d.id, Booking.status.in_(['living', 'booked']),
                                                  Booking.start_date <= date.today(),
                                                  Booking.end_date > date.today()).count()
            text += f"🔹 {d.name}: {occ} / {cap} занято\n"
        bot.send_message(message.chat.id, text, parse_mode='HTML')


@bot.message_handler(func=lambda m: m.text == "👮‍♂️ Коменданты")
def list_commandants(message):
    with app.app_context():
        users = User.query.filter_by(role='Commandant').all()
        text = "👮‍♂️ <b>Коменданты:</b>\n\n"
        for u in users:
            d_name = u.dorm.name if u.dorm else "Нет общежития"
            text += f"👤 {u.full_name}\n📞 {u.phone}\n🏠 {d_name}\n\n"
        bot.send_message(message.chat.id, text, parse_mode='HTML')


@bot.message_handler(func=lambda m: m.text == "🔍 Проверить комнату")
def check_room_start(message):
    msg = bot.send_message(message.chat.id, "Введите номер комнаты (например, 101):")
    bot.register_next_step_handler(msg, check_room_process)


def check_room_process(message):
    room_num = message.text.strip()
    with app.app_context():
        rooms = Room.query.filter_by(room_number=room_num).all()
        if not rooms:
            bot.send_message(message.chat.id, "❌ Комната не найдена.")
            return

        text = f"🔍 <b>Комната {room_num}:</b>\n\n"
        for r in rooms:
            text += f"🏢 {r.dorm.name} (Мест: {r.capacity})\n"
            bookings = Booking.query.filter(Booking.room_id == r.id, Booking.status.in_(['living', 'booked']),
                                            Booking.start_date <= date.today(), Booking.end_date > date.today()).all()
            if not bookings:
                text += "✅ Свободна\n"
            else:
                for b in bookings:
                    text += f"👤 {b.full_name} (до {b.end_date})\n"
            text += "\n"
        bot.send_message(message.chat.id, text, parse_mode='HTML')


# ==========================================
#         БЛОК 2: СКЛАД
# ==========================================

@bot.message_handler(func=lambda m: m.text == "📦 Блок: Склад")
def open_warehouse(message):
    bot.send_message(message.chat.id, "Управление поставками:", reply_markup=menu_warehouse())


# --- 1. КРАСИВЫЙ ДАШБОРД (С ЦИФРАМИ) ---
@bot.message_handler(func=lambda m: m.text == "📈 Дашборд Склада")
def warehouse_dash(message):
    msg = bot.send_message(message.chat.id, "🎨 Генерирую дашборд склада...")
    try:
        data = excel_handler.get_warehouse_analytics()

        sns.set_style("whitegrid")
        fig, axs = plt.subplots(2, 2, figsize=(14, 12))
        fig.suptitle(f'Склад: Сводка на {date.today().strftime("%d.%m.%Y")}', fontsize=20)

        # График 1: Бюджет
        bars = axs[0, 0].bar(['План', 'Факт'], [data['sum_plan'], data['sum_fact']], color=['#95a5a6', '#2ecc71'])
        axs[0, 0].set_title('Бюджет (Рублей)', fontsize=14)
        for bar in bars:
            height = bar.get_height()
            val_str = f'{height / 1000000:.1f}M' if height > 1000000 else f'{height / 1000:.0f}k'
            axs[0, 0].text(bar.get_x() + bar.get_width() / 2., height, val_str, ha='center', va='bottom', fontsize=12,
                           fontweight='bold')

        # График 2: Статус
        labels = ['Выполнено', 'Частично', 'Ожидаем']
        sizes = [data['completed_positions'], data['partial_positions'],
                 data['total_positions'] - data['completed_positions'] - data['partial_positions']]
        colors = ['#2ecc71', '#f1c40f', '#ecf0f1']

        def make_autopct(values):
            def my_autopct(pct):
                total = sum(values)
                val = int(round(pct * total / 100.0))
                return '{p:.1f}%\n({v})'.format(p=pct, v=val) if pct > 0 else ''

            return my_autopct

        axs[0, 1].pie(sizes, labels=labels, colors=colors, autopct=make_autopct(sizes), startangle=140)
        axs[0, 1].set_title('Статус позиций (шт)', fontsize=14)

        # График 3: Топ категорий
        sorted_cats = sorted(data['categories'].items(), key=lambda x: x[1]['plan'], reverse=True)[:5]
        if sorted_cats:
            cats = [x[0][:15] for x in sorted_cats]
            plans = [x[1]['plan'] for x in sorted_cats]
            facts = [x[1]['fact'] for x in sorted_cats]
            y_pos = np.arange(len(cats))

            axs[1, 0].barh(y_pos, plans, align='center', alpha=0.4, color='gray', label='План')
            axs[1, 0].barh(y_pos, facts, align='center', alpha=0.9, color='#27ae60', label='Факт')
            axs[1, 0].set_yticks(y_pos)
            axs[1, 0].set_yticklabels(cats)
            axs[1, 0].invert_yaxis()
            axs[1, 0].set_title('Топ-5 категорий', fontsize=14)
            axs[1, 0].legend()
        else:
            axs[1, 0].text(0.5, 0.5, "Нет данных", ha='center')

        # Блок 4: Текст
        axs[1, 1].axis('off')
        budget_perc = int(data['sum_fact'] / data['sum_plan'] * 100) if data['sum_plan'] else 0
        summary_text = (
            f"📋 <b>ОБЩАЯ СВОДКА</b>\n"
            f"📦 <b>Позиций:</b> {data['total_positions']}\n"
            f"   🟢 Готово: {data['completed_positions']}\n"
            f"   🟡 Частично: {data['partial_positions']}\n\n"
            f"💰 <b>БЮДЖЕТ</b>\n"
            f"План:  {data['sum_plan']:,.0f} ₽\n"
            f"Факт:  {data['sum_fact']:,.0f} ₽\n"
            f"<b>Исп: {budget_perc}%</b>"
        )

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        bot.send_photo(message.chat.id, buf, caption=summary_text, parse_mode='HTML')
        bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")


# --- 2. ВАРИАТИВНАЯ АНАЛИТИКА (По фильтрам) ---
@bot.message_handler(func=lambda m: m.text == "📉 Детальная Аналитика")
def ask_analytics_type(message):
    # Создаем кнопки под сообщением (Инлайн)
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("📅 По Кварталу (1-4)", callback_data="an_quarter")
    btn2 = types.InlineKeyboardButton("🗂 По Категории (Название)", callback_data="an_category")
    btn3 = types.InlineKeyboardButton("🌎 Итог за весь год", callback_data="an_total")
    markup.add(btn1, btn2, btn3)
    bot.send_message(message.chat.id, "Выберите, как фильтровать данные:", reply_markup=markup)


# Обработчик нажатия на кнопки (callback)
@bot.callback_query_handler(func=lambda call: call.data.startswith('an_'))
def analytics_callback(call):
    mode = call.data.split('_')[1]

    # Чтобы часики "загрузки" на кнопке исчезли
    bot.answer_callback_query(call.id)

    if mode == 'total':
        # Сразу считаем и отправляем
        data = excel_handler.get_analytics('total')
        send_analytics_report(call.message.chat.id, data, "Весь 2025 год")

    elif mode == 'quarter':
        msg = bot.send_message(call.message.chat.id, "Введите номер квартала (цифру 1, 2, 3 или 4):")
        bot.register_next_step_handler(msg, step_process_quarter)

    elif mode == 'category':
        msg = bot.send_message(call.message.chat.id,
                               "Введите название категории (можно часть слова, например 'спецодежда'):")
        bot.register_next_step_handler(msg, step_process_category)


# Шаг: Получение квартала
def step_process_quarter(message):
    kvartal = message.text.strip()
    # Защита от дурака
    if kvartal not in ['1', '2', '3', '4']:
        bot.send_message(message.chat.id, "❌ Неверный квартал. Введите число от 1 до 4.")
        return

    data = excel_handler.get_analytics('quarter', kvartal)
    send_analytics_report(message.chat.id, data, f"Квартал {kvartal}")


# Шаг: Получение категории
def step_process_category(message):
    category = message.text.strip()
    data = excel_handler.get_analytics('category', category)
    send_analytics_report(message.chat.id, data, f"Категория: {category}")


# Функция отправки красивого отчета
def send_analytics_report(chat_id, data, title):
    if data['sum_plan'] == 0:
        bot.send_message(chat_id, f"❌ По запросу '{title}' данных не найдено.")
        return

    # Считаем проценты
    percent = int((data['sum_fact'] / data['sum_plan']) * 100)

    # Рисуем прогресс-бар из смайликов
    # 10 квадратиков: зеленые - выполненная часть, белые - остаток
    filled_len = percent // 10
    if filled_len > 10: filled_len = 10
    progress_bar = "🟩" * filled_len + "⬜" * (10 - filled_len)

    # Форматируем большие числа с пробелами (1 000 000)
    fact_fmt = "{:,.0f}".format(data['sum_fact']).replace(',', ' ')
    plan_fmt = "{:,.0f}".format(data['sum_plan']).replace(',', ' ')

    text = (
        f"📊 <b>ОТЧЕТ: {title}</b>\n"
        f"──────────────────\n"
        f"💰 <b>Финансы:</b>\n"
        f"   План:  {plan_fmt} ₽\n"
        f"   Факт:  {fact_fmt} ₽\n"
        f"   {progress_bar} <b>{percent}%</b>\n\n"
        f"📦 <b>Позиции (шт):</b>\n"
        f"   Получено: {int(data['qty_fact'])} из {int(data['qty_plan'])}\n"
    )

    # Добавляем список позиций (если их не слишком много)
    if data['items']:
        text += f"\n📋 <b>Детализация (первые 10):</b>\n"
        for item in data['items'][:10]:
            icon = "✅" if item['is_received'] else "⚪"  # Зеленая галочка или белый круг
            # Обрезаем длинные названия, чтобы не засорять чат
            short_name = (item['name'][:30] + '..') if len(item['name']) > 30 else item['name']
            text += f"{icon} {short_name} — <b>{int(item['qty'])} шт.</b>\n"

        # Если позиций больше 10, пишем сколько осталось
        remaining = len(data['items']) - 10
        if remaining > 0:
            text += f"<i>...и еще {remaining} позиций.</i>"

    bot.send_message(chat_id, text, parse_mode='HTML')



# --- 3. ПРИЕМКА ТОВАРА ---
@bot.message_handler(func=lambda m: m.text == "✅ Приемка товара")
def recv_start(message):
    msg = bot.send_message(message.chat.id, "Введите ID товара или название:")
    bot.register_next_step_handler(msg, recv_search)


def recv_search(message):
    info = excel_handler.get_item_info(message.text)
    if not info['found']:
        bot.send_message(message.chat.id, "❌ Не найдено.")
        return
    user_data[message.chat.id] = info['row_idx']
    status = "🟢" if info['fact'] >= info['plan'] else ("🟡" if info['fact'] > 0 else "⚪")
    text = (
        f"📦 <b>{info['name']}</b>\n🆔 {info['id']}\n"
        f"📋 План: {info['plan']} | {status} Факт: {info['fact']}\n"
        f"✍ <b>Сколько добавить?</b>"
    )
    msg = bot.send_message(message.chat.id, text, parse_mode='HTML')
    bot.register_next_step_handler(msg, recv_save)


def recv_save(message):
    try:
        qty = float(message.text.replace(',', '.'))
        row = user_data.get(message.chat.id)
        if row:
            res = excel_handler.update_item_qty(row, qty)
            bot.send_message(message.chat.id, res)
        else:
            bot.send_message(message.chat.id, "Ошибка сессии.")
    except:
        bot.send_message(message.chat.id, "❌ Введите число.")


# --- 4. СКАЧАТЬ EXCEL ---
@bot.message_handler(func=lambda m: m.text == "📥 Скачать Excel")
def download_db(message):
    try:
        file = excel_handler.get_full_database_file()
        bot.send_document(message.chat.id, file, visible_file_name="Склад_База.xlsx")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")


# ЗАПУСК
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()