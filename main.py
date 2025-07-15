import os
import sqlite3
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ChatMember
from telegram.ext import (
    Application, ChatMemberHandler,
    CommandHandler, ContextTypes
)

# Получение переменных окружения
TOKEN = os.getenv("8097493214:AAEn2-fFVZ-pt3C39aZt6uiLP3ibHqigwgo")
CHANNEL_IDS = list(map(int, os.getenv("CHANNEL_IDS", "").split(",")))

# Подключение к SQLite
conn = sqlite3.connect("channel_members.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS members (
    user_id INTEGER,
    channel_id INTEGER,
    join_date TEXT,
    PRIMARY KEY (user_id, channel_id)
)
''')
conn.commit()

# Обработка события вступления в канал
async def track_channel_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = update.chat_member
    chat_id = status.chat.id
    user_id = status.new_chat_member.user.id

    if chat_id in CHANNEL_IDS and status.new_chat_member.status in [ChatMember.MEMBER, ChatMember.RESTRICTED]:
        join_time = datetime.utcnow().isoformat()
        cursor.execute("INSERT OR REPLACE INTO members (user_id, channel_id, join_date) VALUES (?, ?, ?)",
                       (user_id, chat_id, join_time))
        conn.commit()
        print(f"[INFO] User {user_id} joined channel {chat_id} at {join_time}")

# Удаление пользователей спустя 90 дней
async def remove_old_members(app: Application):
    while True:
        await asyncio.sleep(86400)  # каждый день
        cutoff = datetime.utcnow() - timedelta(days=90)
        cursor.execute("SELECT user_id, channel_id, join_date FROM members")
        for user_id, channel_id, join_date in cursor.fetchall():
            try:
                if datetime.fromisoformat(join_date) < cutoff:
                    await app.bot.ban_chat_member(channel_id, user_id)
                    await app.bot.unban_chat_member(channel_id, user_id)
                    cursor.execute("DELETE FROM members WHERE user_id = ? AND channel_id = ?", (user_id, channel_id))
                    conn.commit()
                    print(f"[INFO] Removed user {user_id} from channel {channel_id}")
            except Exception as e:
                print(f"[ERROR] Failed to remove user {user_id} from {channel_id}: {e}")

# Команда /id для получения channel_id
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"ID этого канала: {chat_id}")

# Основной запуск бота
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(track_channel_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("id", get_chat_id))
    app.job_queue.run_once(lambda *_: asyncio.create_task(remove_old_members(app)), 1)
    print("[INFO] Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
