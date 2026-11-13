import telebot
from telebot import types
import sqlite3
import time
import random

import os
TOKEN = os.environ.get('TOKEN', 'ТВОЙ_ТОКЕН_ЗДЕСЬ')
OWNER_ID = IDTG # НЕ ЗАБУДЬ ВСТАВИТЬ СВОЙ ID!

bot = telebot.TeleBot(TOKEN)
def get_admins():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (OWNER_ID,))
    c.execute("SELECT user_id FROM admins")
    admins = [row[0] for row in c.fetchall()]
    conn.close()
    return admins

def is_admin(user_id):
    return user_id in get_admins()
def parse_amount(text, user_balance=None):
    text = str(text).lower().strip()

    if text in ['все', 'всё', 'all'] and user_balance is not None:
        return user_balance
    elif text in ['пол', 'half'] and user_balance is not None:
        return user_balance // 2

    try:
        if 'кк' in text or 'kk' in text:
            num = text.replace('кк', '').replace('kk', '').replace(',', '.')
            return int(float(num) * 1000000)
        elif 'к' in text or 'k' in text:
            num = text.replace('к', '').replace('k', '').replace(',', '.')
            return int(float(num) * 1000)
        else:
            return int(float(text.replace(',', '.')))
    except ValueError:
        return None

def format_money(amount):
    if amount >= 1000000: return f"{amount/1000000:.2f}".replace('.00', '') + "кк"
    return f"{amount:,}".replace(',', "'")

# --- АНТИСПАМ (КД 5 СЕКУНД) ---
user_cooldowns = {}
frog_games = {}
hilo_games = {}
crash_games = {}
piggy_games = {}

def check_cooldown(message, seconds=5):
    user_id = message.from_user.id
    if user_id == OWNER_ID:
        return True

    current_time = time.time()
    last_time = user_cooldowns.get(user_id, 0)

    if current_time - last_time < seconds:
        time_left = round(seconds - (current_time - last_time), 1)
        bot.reply_to(message, f"⏳ Не так быстро, брат! Подожди {time_left} сек.")
        return False

    user_cooldowns[user_id] = current_time
    return True

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, balance INTEGER, last_bonus REAL, active_title TEXT)''')

    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    if 'active_title' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN active_title TEXT DEFAULT 'Нет'")
    if 'd1_cd' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN d1_cd REAL DEFAULT 0")
    if 'd2_cd' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN d2_cd REAL DEFAULT 0")
    if 'd3_cd' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN d3_cd REAL DEFAULT 0")

    c.execute('''CREATE TABLE IF NOT EXISTS shop
                 (item_id INTEGER PRIMARY KEY, name TEXT, price INTEGER)''')

    c.execute('''CREATE TABLE IF NOT EXISTS inventory
                 (user_id INTEGER, item_id INTEGER)''')

    c.execute("SELECT COUNT(*) FROM shop")
    if c.fetchone()[0] == 0:
        items = [
            (1, "Мемчик 🐸", 30000),
            (2, "Великий мем 🗿", 200000),
            (3, "Легендарный мем 🚀", 3000000)
        ]
        for item_id, name, price in items:
            c.execute("INSERT INTO shop (item_id, name, price) VALUES (?, ?, ?)", (item_id, name, price))

    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT balance, last_bonus, active_title FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, balance, last_bonus, active_title) VALUES (?, ?, ?, ?)", (user_id, 0, 0, 'Нет'))
        conn.commit()
        user = (0, 0, 'Нет')
    conn.close()
    return user

def update_balance(user_id, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def update_bonus_time(user_id, timestamp):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET last_bonus = ? WHERE user_id = ?", (timestamp, user_id))
    conn.commit()
    conn.close()

init_db()

# --- КОМАНДЫ ДЛЯ ВСЕХ ---

@bot.message_handler(commands=['help', 'хелп'])
@bot.message_handler(func=lambda message: message.text and message.text.lower() in ['хелп', 'помощь'])
def help_command(message):
    if not check_cooldown(message): return
    help_text = (
        "🤖 **СПИСОК КОМАНД БОТА** 🤖\n\n"
        "💳 **б** — баланс и титул\n"
        "🎁 **бонус** — от 1к до 5к монет (раз в 6 часов)\n"
        "🎰 **казино [сумма]** — рулетка (шанс 50/50)\n"
        "🏇 **скачки [1-5] [сумма]** — гонки (выигрыш x4)\n"
        "🎲 **кубик [сумма]** - игра в кубик \n"
        "🥤 **стаканы [сумма]** - игра в стаканы \n"
        "🐸 **квак [сумма]** -пирамида с лягушкой \n"
        "🃏 **хило [сумма]** - больше или меньше \n"
        "🚀 **краш** [сумма]** - ракетка \n"
        "🐽 **свинья [сумма]** - бей по свинье вплоть до 25х \n"
        "⚔️ **подземелья** — заходить в данжи (нужны титулы)\n"
        "🏆 **топ** — 10 богачей\n"
        "🛒 **магазин** — титулы\n"
        "🎒 **инвентарь** — твои титулы\n\n"
        "🤝 **Переводы:**\n"
        "`перевод 100` (реплай) / `перевод ID 100`\n\n"
        "👑 *Админка:*\n"
        "`/give 100` (реплай) / `/give ID 100`\n"
        "`/reset` (реплай) / `/reset ID` / `/reset all` (баланс)\n"
        "`/resettitle` (реплай) / `/resettitle ID` / `/resettitle all` (титулы)"
        "`/setprice` айди сумма - менять цену на титул"
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['balance'])
@bot.message_handler(func=lambda message: message.text and message.text.lower() == 'б')
def show_balance(message):
    if not check_cooldown(message): return
    balance, _, active_title = get_user(message.from_user.id)
    title_text = f"\n🏅 Титул: **{active_title}**" if active_title != "Нет" else "\n🏅 Титул: *Не надет*"
    bot.reply_to(message, f"💳 Твой баланс: {format_money(balance)} монет{title_text}", parse_mode='Markdown')

@bot.message_handler(commands=['bonus'])
@bot.message_handler(func=lambda message: message.text and message.text.lower() == 'бонус')
def get_bonus(message):
    if not check_cooldown(message): return
    user_id = message.from_user.id
    balance, last_bonus, _ = get_user(user_id)
    now = time.time()
    cooldown = 6 * 60 * 60
    if now - last_bonus < cooldown:
        time_left = int(cooldown - (now - last_bonus))
        hours = time_left // 3600
        minutes = (time_left % 3600) // 60
        bot.reply_to(message, f"⏳ Бонус еще не готов! Жди {hours} ч. {minutes} мин.")
    else:
        reward = random.randint(1000, 5000)
        update_balance(user_id, reward)
        update_bonus_time(user_id, now)
        bot.reply_to(message, f"🎁 Ты получил свой бонус: **{reward} монет**! Приходи через 6 часов.", parse_mode='Markdown')

# --- ПОДЗЕМЕЛЬЯ ---
def dungeons_menu():
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🐸 Пещера Мемчика (2000-10000 монет)", callback_data="dungeon_1")
    btn2 = types.InlineKeyboardButton("🗿 Гробница Великого (20000-80000 монет)", callback_data="dungeon_2")
    btn3 = types.InlineKeyboardButton("🚀 Космос Легенды (100000-250000 монет)", callback_data="dungeon_3")
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    return markup

@bot.message_handler(commands=['dungeons', 'подземелья'])
@bot.message_handler(func=lambda message: message.text and message.text.lower() == 'подземелья')
def show_dungeons(message):
    if not check_cooldown(message): return
    text = "⚔️ **ВЫБЕРИ ПОДЗЕМЕЛЬЕ** ⚔️\n\nДля входа нужен соответствующий титул!"
    bot.reply_to(message, text, reply_markup=dungeons_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('dungeon_'))
def enter_dungeon(call):
    user_id = call.from_user.id
    dungeon_id = int(call.data.split('_')[1])

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT active_title, d1_cd, d2_cd, d3_cd FROM users WHERE user_id = ?", (user_id,))
    user_data = c.fetchone()

    if not user_data:
        c.execute("INSERT INTO users (user_id, balance, last_bonus, active_title) VALUES (?, ?, ?, ?)", (user_id, 0, 0, 'Нет'))
        conn.commit()
        user_data = ('Нет', 0, 0, 0)

    active_title, d1_cd, d2_cd, d3_cd = user_data
    now = time.time()

    if dungeon_id == 1:
        required_title = "Мемчик 🐸"
        cooldown = 6 * 60 * 60
        last_time = d1_cd
        min_reward, max_reward = 2000, 10000
        col_name = "d1_cd"
    elif dungeon_id == 2:
        required_title = "Великий мем 🗿"
        cooldown = 12 * 60 * 60
        last_time = d2_cd
        min_reward, max_reward = 20000, 80000
        col_name = "d2_cd"
    else:
        required_title = "Легендарный мем 🚀"
        cooldown = 24 * 60 * 60
        last_time = d3_cd
        min_reward, max_reward = 100000, 250000
        col_name = "d3_cd"

    if active_title != required_title:
        bot.answer_callback_query(call.id, f"❌ Для входа нужен титул: {required_title}", show_alert=True)
        conn.close()
        return

    if now - last_time < cooldown:
        time_left = int(cooldown - (now - last_time))
        hours = time_left // 3600
        minutes = (time_left % 3600) // 60
        bot.answer_callback_query(call.id, f"⏳ Подземелье восстанавливается! Жди {hours} ч. {minutes} мин.", show_alert=True)
        conn.close()
        return

    reward = random.randint(min_reward, max_reward)
    c.execute("UPDATE users SET balance = balance + ?, {} = ? WHERE user_id = ?".format(col_name), (reward, now, user_id))
    conn.commit()
    conn.close()

    bot.answer_callback_query(call.id, f"Ты прошел подземелье и нашел {reward} монет! 🪙", show_alert=True)
    bot.send_message(call.message.chat.id, f"⚔️ **{call.from_user.first_name}** спустился в подземелье и вынес оттуда **{format_money(reward)}** монет! 🪙", parse_mode='Markdown')

# --- СКАЧКИ С АНИМАЦИЕЙ ---
@bot.message_handler(commands=['скачки', 'race'])
@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('скачки'))
def horse_race(message):
    if not check_cooldown(message): return
    parts = message.text.split()

    if len(parts) != 3 or not parts[1].isdigit():
        bot.reply_to(message, "🏇 **Как играть:**\nНапиши `скачки [номер] [ставка]`\nПример: `скачки 3 1000` или `скачки 3 1к`.", parse_mode='Markdown')
        return

    horse_choice = int(parts[1])
    balance, _, _ = get_user(message.from_user.id)
    amount = parse_amount(parts[2], balance)

    if horse_choice < 1 or horse_choice > 5:
        bot.reply_to(message, "❌ Выбери лошадь от 1 до 5!")
        return

    if amount is None or amount <= 0:
        bot.reply_to(message, "❌ Ошибка! Введи нормальную сумму.")
        return

    if balance < amount:
        bot.reply_to(message, "❌ У тебя недостаточно монет!")
        return

    update_balance(message.from_user.id, -amount)

    msg = bot.reply_to(message, "🏁 Гонка начинается! Лошади на старте...")

    positions = [0, 0, 0, 0, 0]
    winner = None

    for step in range(8):
        time.sleep(0.5)
        track = "🏁 **ГОНКА В РАЗГАРЕ!** 🏁\n\n"

        for i in range(5):
            if winner is None and positions[i] < 10:
                positions[i] += random.randint(0, 2)

            track_line = "🔲" * min(positions[i], 10) + "🐎" + "🔲" * (10 - min(positions[i], 10))
            track += f"Лошадь {i+1}: {track_line}\n"

        if winner is None:
            for i in range(5):
                if positions[i] >= 10:
                    winner = i + 1
                    break

        bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id, text=track)

        if winner is not None:
            break

    if winner is None:
        winner = positions.index(max(positions)) + 1

    final_text = "🏁 **ФИНИШ!** 🏁\n\n"
    if winner == horse_choice:
        win_amount = amount * 4
        update_balance(message.from_user.id, win_amount)
        final_text += f"🏆 Победила лошадь №{winner}!\n\n🎉 **ТЫ ВЫИГРАЛ!** ..."
    else:
        final_text += f"🏆 Победила лошадь №{winner}!\n\n😢 **ТЫ ПРОИГРАЛ!** ..."

        bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id, text=final_text, parse_mode='Markdown')

# --- ИГРА: КУБИК С ВЫБОРОМ ---
@bot.message_handler(commands=['кубик', 'dice'])
@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('кубик'))
def dice_game_start(message):
    if not check_cooldown(message): return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "🎲 **Как играть:**\nНапиши `кубик [ставка]`", parse_mode='Markdown')
        return

    balance, _, _ = get_user(message.from_user.id)
    amount = parse_amount(parts[1], balance)

    if amount is None or amount <= 0:
        bot.reply_to(message, "❌ Ошибка! Введи нормальную сумму.")
        return

    if balance < amount:
        bot.reply_to(message, "❌ У тебя недостаточно монет!")
        return

    update_balance(message.from_user.id, -amount)

    markup = types.InlineKeyboardMarkup()
    btn_more = types.InlineKeyboardButton("Больше 3 (x1.85)", callback_data=f"dice_play_{amount}_more_{message.from_user.id}")
    btn_less = types.InlineKeyboardButton("Меньше 3 (x2.5)", callback_data=f"dice_play_{amount}_less_{message.from_user.id}")
    btn_exact = types.InlineKeyboardButton("Ровно 3 (x5.8)", callback_data=f"dice_play_{amount}_exact_{message.from_user.id}")
    markup.add(btn_more)
    markup.add(btn_less)
    markup.add(btn_exact)

    bot.reply_to(message, f"Ставка {amount} принята! На что ставишь?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('dice_play_'))
def dice_game_play(call):
    parts = call.data.split('_')
    amount = int(parts[2])
    choice = parts[3]
    owner_id = int(parts[4]) # ID того, кто запустил игру

    # Проверка: если нажал не тот, кто запустил
    if call.from_user.id != owner_id:
        bot.answer_callback_query(call.id, "❌ Это не твоя игра! Напиши свою команду, чтобы сыграть.", show_alert=True)
        return

    user_id = call.from_user.id

    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

    sent_msg = bot.send_dice(call.message.chat.id, emoji='🎲')
    dice_value = sent_msg.dice.value

    if choice == 'more' and dice_value > 3:
        win_amount = int(amount * 1.85)
        update_balance(user_id, win_amount)
        bot.reply_to(call.message, f"🎲 Выпало **{dice_value}**! Ты ставил на **Больше 3**.\n🎉 Ты выиграл **{win_amount}** монет!", parse_mode='Markdown')
    elif choice == 'less' and dice_value < 3:
        win_amount = int(amount * 2.5)
        update_balance(user_id, win_amount)
        bot.reply_to(call.message, f"🎲 Выпало **{dice_value}**! Ты ставил на **Меньше 3**.\n🎉 Ты выиграл **{win_amount}** монет!", parse_mode='Markdown')
    elif choice == 'exact' and dice_value == 3:
        win_amount = int(amount * 5.8)
        update_balance(user_id, win_amount)
        bot.reply_to(call.message, f"🔥 **ДЖЕКПОТ!** Выпало ровно **3**!\n💸 Ты сорвал куш **{win_amount}** монет!", parse_mode='Markdown')
    else:
        bot.reply_to(call.message, f"🎲 Выпало **{dice_value}**.\n😢 Твоя ставка в **{amount}** монет сгорела.", parse_mode='Markdown')

# --- ПЕРЕВОД ---
@bot.message_handler(commands=['перевод'])
@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('перевод'))
def pay_money(message):
    if not check_cooldown(message): return
    try:
        parts = message.text.split()

        if message.reply_to_message and len(parts) == 2:
            recipient = message.reply_to_message.from_user
            amount = parse_amount(parts[1])
        elif len(parts) == 3 and parts[1].isdigit():
            user_id = int(parts[1])
            get_user(user_id)
            recipient = types.User(id=user_id, is_bot=False, first_name=f"ID {user_id}")
            amount = parse_amount(parts[2])
        else:
            bot.reply_to(message, "🤝 Форматы перевода:\n`перевод 1000` или `перевод 1к` (реплай)\n`перевод ID 5000`", parse_mode='Markdown')
            return

        if amount is None or amount <= 0:
            bot.reply_to(message, "❌ Ошибка! Введи нормальную сумму.")
            return

        if recipient.id == message.from_user.id:
            bot.reply_to(message, "Себе переводить нельзя! 🤦‍♂️")
            return

        sender_balance, _, _ = get_user(message.from_user.id)
        if sender_balance < amount:
            bot.reply_to(message, "У тебя недостаточно монет! 😢")
            return

        update_balance(message.from_user.id, -amount)
        update_balance(recipient.id, amount)
        bot.reply_to(message, f"✅ Успешно переведено {format_money(amount)} монет пользователю **{recipient.first_name}**!")

    except Exception:
        bot.reply_to(message, "Ошибка! Проверь формат. Пример: `перевод 1к` (реплай)")


@bot.message_handler(commands=['казино', 'casino'])
@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('казино'))
def casino(message):
    if not check_cooldown(message): return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "🎰 Напиши сумму ставки! Пример: `казино 1000` или `казино 1к`", parse_mode='Markdown')
            return

        balance, _, _ = get_user(message.from_user.id)
        amount = parse_amount(parts[1], balance)

        if amount is None or amount <= 0:
            bot.reply_to(message, "❌ Ошибка! Введи нормальную сумму. Пример: `казино 5000` или `казино 5к`.")
            return

        if balance < amount:
            bot.reply_to(message, "❌ У тебя недостаточно монет для такой ставки!")
            return

        update_balance(message.from_user.id, -amount)
        win = random.choice([True, False])
        if win:
            win_amount = amount * 2
            update_balance(message.from_user.id, win_amount)
            bot.reply_to(message, f"🎰 **КРУТИМ!** Выпало **КРАСНОЕ**! 🎉\nТы выиграл **{format_money(amount)}** монет (Баланс пополнен на {format_money(win_amount)}).", parse_mode='Markdown')
        else:
              bot.reply_to(message, f"🎰 **КРУТИМ!** Выпало **ЧЁРНОЕ**... 😢\nТы проиграл **{format_money(amount)}** монет.", parse_mode='Markdown')
    except Exception:
        bot.reply_to(message, "❌ Ошибка ввода. Проверь формат.")

@bot.message_handler(commands=['top', 'топ'])
@bot.message_handler(func=lambda message: message.text and message.text.lower() == 'топ')
def show_top(message):
    if not check_cooldown(message): return
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
    top_users = c.fetchall()
    conn.close()
    if not top_users:
        bot.reply_to(message, "🏆 Топ пока пуст. Начните играть, чтобы попасть в историю!")
        return
    text = "🏆 **ТОП-10 БОГАЧЕЙ ЧАТА** 🏆\n\n"
    for index, (user_id, balance) in enumerate(top_users, start=1):
        if user_id == OWNER_ID:
            name = "👑 ВЛАДЕЛЕЦ"
        else:
            try:
                member = bot.get_chat_member(message.chat.id, user_id)
                name = member.user.first_name
            except:
                name = f"Игрок {user_id}"
        medal = ""
        if index == 1: medal = "🥇"
        elif index == 2: medal = "🥈"
        elif index == 3: medal = "🥉"
        else: medal = f"{index}."
        text += f"{medal} {name} — **{format_money(balance)}** монет\n"
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['shop', 'магазин'])
@bot.message_handler(func=lambda message: message.text and message.text.lower() == 'магазин')
def shop_command(message):
    if not check_cooldown(message): return
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT item_id, name, price FROM shop ORDER BY item_id ASC")
    items = c.fetchall()
    conn.close()
    text = "🛒 **МАГАЗИН ТИТУЛОВ** 🛒\n\n"
    for item_id, name, price in items:
        text += f"🔹 **{item_id}**. {name} — {price} монет\n"
    text += "\nЧтобы купить, напиши: `купить [номер]`\nНапример: `купить 1`"
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('купить'))
def buy_title(message):
    if not check_cooldown(message): return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Напиши номер титула из магазина. Пример: `купить 1`")
            return
        item_id = int(parts[1])
        user_id = message.from_user.id

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT name, price FROM shop WHERE item_id = ?", (item_id,))
        item = c.fetchone()

        if not item:
            bot.reply_to(message, "❌ Такого титула нет в магазине!")
            conn.close()
            return

        item_name, item_price = item

        c.execute("SELECT * FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id))
        if c.fetchone():
            bot.reply_to(message, "У тебя уже есть этот титул в коллекции! 😎")
            conn.close()
            return

        balance, _, _ = get_user(user_id)
        if balance < item_price:
            bot.reply_to(message, f"❌ У тебя недостаточно монет! Нужно {item_price}, а у тебя {balance}.")
            conn.close()
            return

        c.execute("UPDATE users SET balance = balance - ?, active_title = ? WHERE user_id = ?", (item_price, item_name, user_id))
        c.execute("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", (user_id, item_id))
        conn.commit()
        conn.close()

        bot.reply_to(message, f"🎉 Поздравляю! Ты купил и сразу надел титул **{item_name}** за {item_price} монет. Напиши 'б', чтобы проверить!", parse_mode='Markdown')
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Ошибка! Напиши номер титула. Пример: `купить 1`")

@bot.message_handler(commands=['inv', 'инвентарь'])
@bot.message_handler(func=lambda message: message.text and message.text.lower() in ['инвентарь', 'инв'])
def inventory_command(message):
    if not check_cooldown(message): return
    user_id = message.from_user.id
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT shop.name FROM inventory
                 JOIN shop ON inventory.item_id = shop.item_id
                 WHERE inventory.user_id = ?''', (user_id,))
    items = c.fetchall()
    conn.close()

    if not items:
        bot.reply_to(message, "🎒 Твой инвентарь пуст. Купи что-нибудь в магазине (`магазин`)!")
        return

    text = "🎒 **ТВОЙ ИНВЕНТАРЬ** 🎒\n\n"
    for index, item in enumerate(items, start=1):
        text += f"{index}. {item[0]}\n"

    text += "\nЧтобы надеть титул, напиши: `надеть [номер из списка]`"
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('надеть'))
def equip_title(message):
    if not check_cooldown(message): return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Напиши номер титула из инвентаря. Пример: `надеть 1`")
            return
        index = int(parts[1]) - 1
        user_id = message.from_user.id

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''SELECT shop.name FROM inventory
                     JOIN shop ON inventory.item_id = shop.item_id
                     WHERE inventory.user_id = ?''', (user_id,))
        items = c.fetchall()

        if index < 0 or index >= len(items):
            bot.reply_to(message, "❌ У тебя нет титула с таким номером! Напиши `инвентарь`, чтобы посмотреть список.")
            conn.close()
            return

        new_title = items[index][0]
        c.execute("UPDATE users SET active_title = ? WHERE user_id = ?", (new_title, user_id))
        conn.commit()
        conn.close()

        bot.reply_to(message, f"✅ Ты надел титул **{new_title}**! Напиши 'б', чтобы проверить.", parse_mode='Markdown')
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Ошибка! Напиши номер из списка. Пример: `надеть 1`")

# --- АДМИНСКИЕ КОМАНДЫ ---

@bot.message_handler(commands=['give'])
def give_money(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Ты не владелец бота! 😡")
        return
    try:
        parts = message.text.split()

        if message.reply_to_message and len(parts) == 2:
            recipient = message.reply_to_message.from_user
            amount = parse_amount(parts[1])
        elif len(parts) == 3 and parts[1].isdigit():
            user_id = int(parts[1])
            get_user(user_id)
            recipient = types.User(id=user_id, is_bot=False, first_name=f"ID {user_id}")
            amount = parse_amount(parts[2])
        else:
            bot.reply_to(message, "👑 Форматы выдачи:\n`/give 1000` или `/give 1к` (реплай)\n`/give ID 5000`", parse_mode='Markdown')
            return

        if amount is None or amount <= 0:
            bot.reply_to(message, "❌ Ошибка! Введи нормальную сумму.")
            return

        update_balance(recipient.id, amount)
        bot.reply_to(message, f"👑 Выдано {amount} монет пользователю **{recipient.first_name}**!")

    except Exception:
        bot.reply_to(message, "Ошибка! Проверь формат. Пример: `/give 1к` (реплай)")

@bot.message_handler(commands=['reset'])
def reset_balance(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Ты не владелец бота! 😡")
        return
    try:
        parts = message.text.split()

        if len(parts) == 2 and parts[1].lower() == "all":
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("UPDATE users SET balance = 0")
            conn.commit()
            conn.close()
            bot.reply_to(message, "💥 БАМ! Баланс ВСЕХ пользователей обнулен до нуля!")
            return

        if message.reply_to_message and len(parts) == 1:
            recipient = message.reply_to_message.from_user
        elif len(parts) == 2 and parts[1].isdigit():
            user_id = int(parts[1])
            get_user(user_id)
            recipient = types.User(id=user_id, is_bot=False, first_name=f"ID {user_id}")
        else:
            bot.reply_to(message, "🧹 Форматы обнуления:\n`/reset` (реплай)\n`/reset ID`\n`/reset all` (всем)", parse_mode='Markdown')
            return

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (recipient.id,))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"🧹 Баланс пользователя **{recipient.first_name}** обнулен!")

    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

# --- СБРОС ТИТУЛОВ ---
@bot.message_handler(commands=['resettitle'])
def reset_title(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Ты не владелец бота! 😡")
        return
    try:
        parts = message.text.split()

        if len(parts) == 2 and parts[1].lower() == "all":
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("UPDATE users SET active_title = 'Нет'")
            c.execute("DELETE FROM inventory")
            conn.commit()
            conn.close()
            bot.reply_to(message, "💥 БАМ! Все титулы сняты, инвентари очищены у ВСЕХ!")
            return

        if message.reply_to_message and len(parts) == 1:
            recipient = message.reply_to_message.from_user
        elif len(parts) == 2 and parts[1].isdigit():
            user_id = int(parts[1])
            get_user(user_id)
            recipient = types.User(id=user_id, is_bot=False, first_name=f"ID {user_id}")
        else:
            bot.reply_to(message, "🧹 Форматы сброса титулов:\n`/resettitle` (реплай)\n`/resettitle ID`\n`/resettitle all` (всем)", parse_mode='Markdown')
            return

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET active_title = 'Нет' WHERE user_id = ?", (recipient.id,))
        c.execute("DELETE FROM inventory WHERE user_id = ?", (recipient.id,))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"🧹 Титулы пользователя **{recipient.first_name}** сброшены, а инвентарь очищен!")

    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['setprice'])
def set_price(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "Ты не владелец бота! 😡")
        return
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "Формат: /setprice [ID] [Цена]")
            return
        item_id = int(parts[1])
        new_price = parse_amount(parts[2])
        if new_price is None or new_price < 0:
            bot.reply_to(message, "Ошибка! Введи нормальную цену.")
            return
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT name FROM shop WHERE item_id = ?", (item_id,))
        item = c.fetchone()
        if not item:
            bot.reply_to(message, "Титула с таким ID нет!")
            conn.close()
            return
        c.execute("UPDATE shop SET price = ? WHERE item_id = ?", (new_price, item_id))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"Цена на {item[0]} изменена на {new_price}!")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

    # --- ИГРА: СТАКАНЧИКИ ---
@bot.message_handler(commands=['стаканы', 'cups'])
@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('стаканы'))
def cups_game_start(message):
    if not check_cooldown(message): return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "🥤 **Как играть:**\nНапиши `стаканы [ставка]`")
        return

    balance, _, _ = get_user(message.from_user.id)
    amount = parse_amount(parts[1], balance)

    if amount is None or amount <= 0:
        bot.reply_to(message, "❌ Ошибка! Введи нормальную сумму.")
        return

    if balance < amount:
        bot.reply_to(message, "❌ У тебя недостаточно монет!")
        return

    update_balance(message.from_user.id, -amount)
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🥤 1", callback_data=f"cup_{amount}_1_{message.from_user.id}")
    btn2 = types.InlineKeyboardButton("🥤 2", callback_data=f"cup_{amount}_2_{message.from_user.id}")
    btn3 = types.InlineKeyboardButton("🥤 3", callback_data=f"cup_{amount}_3_{message.from_user.id}")
    markup.add(btn1, btn2, btn3)
    bot.reply_to(message, f"Ставка {amount} принята!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cup_'))
def cups_game_play(call):
    parts = call.data.split('_')
    amount = int(parts[1])
    choice = int(parts[2])
    owner_id = int(parts[3])
    if call.from_user.id != owner_id:
        bot.answer_callback_query(call.id, "Не твоя игра!", show_alert=True)
        return
    user_id = call.from_user.id
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    ball_position = random.randint(1, 3)
    cups = ["🥤", "🥤", "🥤"]
    if ball_position == 1: cups[0] = "⚪️"
    elif ball_position == 2: cups[1] = "⚪️"
    else: cups[2] = "⚪️"
    cup_text = " ".join(cups)
    if choice == ball_position:
        win_amount = int(amount * 2.5)
        update_balance(user_id, win_amount)
        bot.reply_to(call.message, f"🪄 **Поднимаем стаканы...**\n\n{cup_text}\n\n🎉 **ТЫ УГАДАЛ!** Шарик был под стаканом №{choice}.\nТы выиграл **{format_money(win_amount)}** монет (x2.5)!", parse_mode='Markdown')
    else:
        bot.reply_to(call.message, f"🪄 **Поднимаем стаканы...**\n\n{cup_text}\n\n😢 **ТЫ НЕ УГАДАЛ!** Шарик был под стаканом №{ball_position}, а ты выбрал №{choice}.\nТы потерял **{format_money(amount)}** монет.", parse_mode='Markdown')

    # --- ИГРА: КВАК (ЛЯГУШКА) ---
import random

@bot.message_handler(commands=['квак', 'frog'])
@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('квак'))
def frog_start(message):
    if not check_cooldown(message): return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "🐸 **Как играть:**\nНапиши `квак [ставка]`", parse_mode='Markdown')
        return

    balance, _, _ = get_user(message.from_user.id)
    amount = parse_amount(parts[1], balance)

    if amount is None or amount <= 0 or balance < amount:
        bot.reply_to(message, "❌ Ошибка! Проверь баланс и сумму.")
        return

    update_balance(message.from_user.id, -amount)

    # СОХРАНЯЕМ ПО ID ИГРОКА, А НЕ ЧАТА!
    frog_games[message.from_user.id] = {
        'uid': message.from_user.id,
        'amount': amount,
        'level': 1,
        'mult': 1.21,
        'mines': 1,
        'active': True
    }

    markup = types.InlineKeyboardMarkup()
    btns = [types.InlineKeyboardButton("🍀", callback_data=f"frog_click_{i}") for i in range(1, 6)]
    markup.row(*btns)
    btn_cash = types.InlineKeyboardButton("💰 Забрать", callback_data="frog_cash")
    markup.add(btn_cash)

    text = f"🐸 Ставка {format_money(amount)} принята!\nУровень 1. Выбери кувшинку:"
    bot.reply_to(message, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('frog_'))
def frog_play(call):
    user_id = call.from_user.id # Берем ID игрока

    if user_id not in frog_games:
        bot.answer_callback_query(call.id, "Игра не найдена. Напиши `квак` заново.", show_alert=True)
        return

    game = frog_games[user_id]

    if not game['active']:
        return

    if call.data == "frog_cash":
        win_amount = int(game['amount'] * game['mult'])
        update_balance(user_id, win_amount)
        game['active'] = False
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"💰 Ты забрал **{format_money(win_amount)}** монет (x{game['mult']})!", reply_markup=None, parse_mode='Markdown')
        del frog_games[user_id]
        return

    choice = int(call.data.split('_')[2])
    mines_positions = random.sample(range(1, 6), game['mines'])

    if choice in mines_positions:
        game['active'] = False
        markup = types.InlineKeyboardMarkup()
        for i in range(1, 6):
            if i in mines_positions:
                markup.add(types.InlineKeyboardButton("💥", callback_data="ignore"))
            else:
                markup.add(types.InlineKeyboardButton("🍀", callback_data="ignore"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"💥 **БУМ!** Ты наступил на мину и потерял **{format_money(game['amount'])}**.", reply_markup=markup, parse_mode='Markdown')
        del frog_games[user_id]
        return

    game['level'] += 1
    levels = [
        {'mult': 1.21, 'mines': 1},
        {'mult': 2.00, 'mines': 2},
        {'mult': 5.05, 'mines': 3},
        {'mult': 25.25, 'mines': 4}
    ]

    if game['level'] > len(levels):
        win_amount = int(game['amount'] * 25.25)
        update_balance(user_id, win_amount)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"🏆 **ТЫ ПРОШЕЛ ВСЁ!** Выиграл {format_money(win_amount)}!", reply_markup=None, parse_mode='Markdown')
        del frog_games[user_id]
        return

    current_level = levels[game['level'] - 1]
    game['mult'] = current_level['mult']
    game['mines'] = current_level['mines']

    markup = types.InlineKeyboardMarkup()
    btns = [types.InlineKeyboardButton("🍀", callback_data=f"frog_click_{i}") for i in range(1, 6)]
    markup.row(*btns)
    btn_cash = types.InlineKeyboardButton("💰 Забрать", callback_data="frog_cash")
    markup.add(btn_cash)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"🍀 Уровень {game['level']} (Мин: {game['mines']}). Множитель: x{game['mult']}\nЗаберешь {format_money(int(game['amount'] * game['mult']))}?",
        reply_markup=markup,
        parse_mode='Markdown'
    )

# # --- ИГРА: ХИЛО (HILO) С ОБНОВЛЕНИЕМ ---
def draw_card():
    return random.randint(2, 14), random.choice(['♠️', '♥️', '♦️', '♣️'])

def get_card_name(val):
    if val == 11: return "В"
    if val == 12: return "Д"
    if val == 13: return "К"
    if val == 14: return "Т"
    return str(val)

def hilo_keyboard(val, refreshes):
    chance_more = (14 - val) / 13
    chance_less = (val - 2) / 13

    mult_more = round(1 / chance_more, 2) if chance_more > 0 else 0
    mult_less = round(1 / chance_less, 2) if chance_less > 0 else 0

    markup = types.InlineKeyboardMarkup()
    btn_more = types.InlineKeyboardButton(f"⬆️ {int(chance_more*100)}% (x{mult_more})", callback_data="hilo_more")
    btn_less = types.InlineKeyboardButton(f"⬇️ {int(chance_less*100)}% (x{mult_less})", callback_data="hilo_less")

    btn_refresh = types.InlineKeyboardButton(f"🔄 Обновить карту ({refreshes}/3)", callback_data="hilo_refresh")
    btn_cash = types.InlineKeyboardButton("💰 Забрать", callback_data="hilo_cash")

    markup.add(btn_more, btn_less)
    markup.add(btn_refresh)
    markup.add(btn_cash)
    return markup

@bot.message_handler(commands=['хило', 'hilo'])
@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('хило'))
def hilo_start(message):
    if not check_cooldown(message): return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "🃏 **Как играть:**\nНапиши `хило [ставка]`", parse_mode='Markdown')
        return

    balance, _, _ = get_user(message.from_user.id)
    amount = parse_amount(parts[1], balance)

    if amount is None or amount <= 0 or balance < amount:
        bot.reply_to(message, "❌ Ошибка! Проверь баланс и сумму.")
        return

    update_balance(message.from_user.id, -amount)
    current_val, current_suit = draw_card()

    # СОХРАНЯЕМ ПО ID ИГРОКА!
    hilo_games[message.from_user.id] = {
        'uid': message.from_user.id, 'amount': amount, 'mult': 1.0,
        'current_val': current_val, 'current_suit': current_suit, 'active': True,
        'refreshes': 3
    }

    markup = hilo_keyboard(current_val, 3)
    card_name = f"{get_card_name(current_val)} {current_suit}"

    text = (
        f"🃏 **HiLo · игра идёт.**\n"
        f"........................\n"
        f"💸 Ставка: {format_money(amount)}\n"
        f"💰 Выигрыш: x1.0 / {format_money(amount)}\n\n"
        f"🃏 Карта: **{card_name}**\n\n"
        f"✊ Какая будет след. карта?"
    )
    bot.reply_to(message, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('hilo_'))
def hilo_play(call):
    user_id = call.from_user.id
    if user_id not in hilo_games:
        bot.answer_callback_query(call.id, "Игра не найдена. Напиши `хило` заново.", show_alert=True)
        return

    game = hilo_games[user_id]

    if not game['active']:
        return

    if call.data == "hilo_refresh":
        if game['refreshes'] > 0:
            game['refreshes'] -= 1
            new_val, new_suit = draw_card()
            game['current_val'] = new_val
            game['current_suit'] = new_suit

            markup = hilo_keyboard(new_val, game['refreshes'])
            card_name = f"{get_card_name(new_val)} {new_suit}"

            text = (
                f"🃏 **HiLo · игра идёт.**\n"
                f"........................\n"
                f"💸 Ставка: {format_money(game['amount'])}\n"
                f"💰 Выигрыш: x{round(game['mult'], 2)} / {format_money(int(game['amount'] * game['mult']))}\n\n"
                f"🃏 Карта: **{card_name}** (Обновлено!)\n\n"
                f"✊ Какая будет след. карта?"
            )
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode='Markdown')
            bot.answer_callback_query(call.id, f"Карта обновлена! Осталось попыток: {game['refreshes']}")
        else:
            bot.answer_callback_query(call.id, "❌ У тебя закончились попытки обновления!", show_alert=True)
        return

    if call.data == "hilo_cash":
        win_amount = int(game['amount'] * game['mult'])
        update_balance(user_id, win_amount)
        game['active'] = False
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"💰 Ты забрал **{format_money(win_amount)}** монет (x{round(game['mult'], 2)})!", reply_markup=None, parse_mode='Markdown')
        del hilo_games[user_id]
        return

    old_val = game['current_val']
    old_suit = game['current_suit']
    new_val, new_suit = draw_card()

    choice = call.data.split('_')[1]

    win = False
    if choice == 'more' and new_val > old_val: win = True
    elif choice == 'less' and new_val < old_val: win = True

    if new_val == old_val:
        bot.answer_callback_query(call.id, "Выпала та же карта! Попробуй еще раз.", show_alert=True)
        return

    if win:
        chance = (14 - old_val) / 13 if choice == 'more' else (old_val - 2) / 13
        if chance < 0.1: chance = 0.1
        game['mult'] *= (1 / chance)

        game['current_val'] = new_val
        game['current_suit'] = new_suit

        markup = hilo_keyboard(new_val, game['refreshes'])
        new_card_name = f"{get_card_name(new_val)} {new_suit}"
        old_card_name = f"{get_card_name(old_val)} {old_suit}"

        text = (
            f"🃏 **HiLo · игра идёт.**\n"
            f"........................\n"
            f"💸 Ставка: {format_money(game['amount'])}\n"
            f"💰 Выигрыш: x{round(game['mult'], 2)} / {format_money(int(game['amount'] * game['mult']))}\n\n"
            f"🃏 Карта: **{new_card_name}**\n"
            f"📥 Предыдущие: {old_card_name}\n\n"
            f"✊ Какая будет след. карта?"
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode='Markdown')
    else:
        game['active'] = False
        old_card_name = f"{get_card_name(old_val)} {old_suit}"
        new_card_name = f"{get_card_name(new_val)} {new_suit}"
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"💥 **ТЫ ПРОИГРАЛ!**\nВыпала **{new_card_name}**, а была **{old_card_name}**.\nТы потерял {format_money(game['amount'])}.", reply_markup=None, parse_mode='Markdown')
        del hilo_games[user_id]

    # --- ИГРА: КРАШ ---
crash_games = {} # Не забудь добавить это в начало, где frog_games!

@bot.message_handler(commands=['краш', 'crash'])
@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('краш'))
def crash_start(message):
    if not check_cooldown(message): return
    parts = message.text.split()

    if len(parts) != 3:
        bot.reply_to(message, "🚀 **Как играть:**\nНапиши `краш [ставка] [множитель]`\nПример: `краш 1к 2.5` (хочешь забрать на x2.5)", parse_mode='Markdown')
        return

    balance, _, _ = get_user(message.from_user.id)
    amount = parse_amount(parts[1], balance)

    try:
        target_mult = float(parts[2].replace(',', '.'))
    except ValueError:
        bot.reply_to(message, "❌ Ошибка! Множитель должен быть числом. Пример: `краш 1к 2.5`")
        return

    if target_mult < 1.1 or target_mult > 100:
        bot.reply_to(message, "❌ Множитель должен быть от 1.1 до 100!")
        return

    if amount is None or amount <= 0 or balance < amount:
        bot.reply_to(message, "❌ Ошибка! Проверь баланс и сумму.")
        return

    update_balance(message.from_user.id, -amount)

    # Генерируем точку краша (от 1.0 до 10.0)
    crash_point = round(random.uniform(1.0, 10.0), 2)

    msg = bot.reply_to(message, f"🚀 **Ракета летит!**\nТвоя цель: **x{target_mult}**\n\nУспей забрать до краша!", parse_mode='Markdown')

    # Имитация полета (пауза)
    time.sleep(random.randint(2, 5))

    if target_mult <= crash_point:
        # Игрок выиграл (успел забрать)
        win_amount = int(amount * target_mult)
        update_balance(message.from_user.id, win_amount)
        bot.edit_message_text(
            chat_id=msg.chat.id,
            message_id=msg.message_id,
            text=f"💰 **УСПЕХ!** Ты забрал **{format_money(win_amount)}** на **x{target_mult}**!\n\n(Ракета взорвалась на x{crash_point})",
            parse_mode='Markdown'
        )
    else:
        # Игрок проиграл
        bot.edit_message_text(
            chat_id=msg.chat.id,
            message_id=msg.message_id,
            text=f"💥 **КРАШ!** Ракета взорвалась на **x{crash_point}**.\nТы хотел забрать на x{target_mult}, но не успел. Ты потерял **{format_money(amount)}**.",
            parse_mode='Markdown'
        )

# --- ИГРА: СВИНЬЯ-КОПИЛКА ---
piggy_games = {} # Не забудь добавить это в начало, где frog_games!

@bot.message_handler(commands=['свинья', 'piggy'])
@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('свинья'))
def piggy_start(message):
    if not check_cooldown(message): return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "🐷 **Как играть:**\nНапиши `свинья [ставка]`", parse_mode='Markdown')
        return

    balance, _, _ = get_user(message.from_user.id)
    amount = parse_amount(parts[1], balance)

    if amount is None or amount <= 0 or balance < amount:
        bot.reply_to(message, "❌ Ошибка! Проверь баланс и сумму.")
        return

    update_balance(message.from_user.id, -amount)

    # СОХРАНЯЕМ ПО ID ИГРОКА!
    piggy_games[message.from_user.id] = {
        'uid': message.from_user.id,
        'amount': amount,
        'mult': 1.0,
        'level': 0,
        'active': True
    }

    markup = types.InlineKeyboardMarkup()
    btn_hit = types.InlineKeyboardButton("🥊 Ударить", callback_data="piggy_hit")
    btn_cash = types.InlineKeyboardButton("💰 Забрать", callback_data="piggy_cash")
    markup.add(btn_hit)
    markup.add(btn_cash)

    bot.reply_to(message, f"🐷 Ставка **{format_money(amount)}** принята!\nКопилка цела. Бей или забирай!", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('piggy_'))
def piggy_play(call):
    user_id = call.from_user.id
    if user_id not in piggy_games:
        bot.answer_callback_query(call.id, "Игра не найдена. Напиши `свинья` заново.", show_alert=True)
        return

    game = piggy_games[user_id]

    if not game['active']:
        return

    if call.data == "piggy_cash":
        win_amount = int(game['amount'] * game['mult'])
        update_balance(user_id, win_amount)
        game['active'] = False
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"💰 Ты забрал **{format_money(win_amount)}** монет (x{game['mult']})! Свинья осталась цела.", reply_markup=None, parse_mode='Markdown')
        del piggy_games[user_id]
        return

    break_chance = 0.15 * (game['level'] + 1)

    if random.random() < break_chance:
        game['active'] = False
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"💥 **ХРЯСЬ!** Ты разбил копилку на **{game['level']+1}** ударе и потерял **{format_money(game['amount'])}**.", reply_markup=None, parse_mode='Markdown')
        del piggy_games[user_id]
        return

    game['level'] += 1
    multipliers = [1.2, 1.5, 2.0, 3.0, 5.0, 10.0, 25.0]

    if game['level'] > len(multipliers):
        win_amount = int(game['amount'] * 25.0)
        update_balance(user_id, win_amount)
        game['active'] = False
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"🏆 **НЕВЕРОЯТНО!** Свинья выдержала всё! Ты выиграл {format_money(win_amount)} (x25)!", reply_markup=None, parse_mode='Markdown')
        del piggy_games[user_id]
        return

    game['mult'] = multipliers[game['level'] - 1]

    markup = types.InlineKeyboardMarkup()
    btn_hit = types.InlineKeyboardButton("🥊 Ударить", callback_data="piggy_hit")
    btn_cash = types.InlineKeyboardButton("💰 Забрать", callback_data="piggy_cash")
    markup.add(btn_hit)
    markup.add(btn_cash)

    text = (
        f"🐷 Свинья выдержала удар!\n"
        f"Текущий множитель: **x{game['mult']}**\n"
        f"Выигрыш: **{format_money(int(game['amount'] * game['mult']))}**\n\n"
        f"Шанс сломать: **{int(break_chance*100)}%**\n"
        f"Бьешь дальше или забираешь?"
    )

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode='Markdown')

print("Бот запущен!")
bot.infinity_polling()