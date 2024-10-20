from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
import sqlite3
import atexit
import time

# ایجاد یا اتصال به دیتابیس
conn = sqlite3.connect('invites.db', check_same_thread=False)
cursor = conn.cursor()

# بستن اتصال به دیتابیس هنگام خروج
atexit.register(conn.close)

# تنظیم timeout برای قفل پایگاه داده
cursor.execute("PRAGMA busy_timeout = 3000")  # 3000 میلی‌ثانیه (3 ثانیه)

# ایجاد جدول برای ذخیره دعوت‌ها
cursor.execute('''CREATE TABLE IF NOT EXISTS invites (
                  user_id INTEGER PRIMARY KEY,
                  inviter_id INTEGER
                  )''')
conn.commit()

# ذخیره دعوت در دیتابیس
def save_invite(user_id, inviter_id):
    for _ in range(3):  # تلاش برای ذخیره 3 بار
        try:
            cursor.execute("INSERT INTO invites (user_id, inviter_id) VALUES (?, ?)", (user_id, inviter_id))
            conn.commit()
            return  # اگر ذخیره موفق بود، تابع را ترک کن
        except sqlite3.OperationalError as e:
            if str(e) == 'database is locked':
                print("Database is locked, trying again...")
                time.sleep(1)  # یک ثانیه صبر کن و دوباره تلاش کن
            else:
                print(f"Error saving invite: {e}")
                break  # در صورت خطای دیگر، از حلقه خارج شو

# گرفتن کاربران دعوت‌شده از دیتابیس
def get_invited_users(inviter_id):
    cursor.execute("SELECT user_id FROM invites WHERE inviter_id = ?", (inviter_id,))
    return cursor.fetchall()

# تولید لینک دعوت
def generate_invite_link(user_id, bot_username):
    return f"https://t.me/{bot_username}?start={user_id}"

# تابع برای نمایش منوی اصلی
async def main_menu(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("آیدی شما", callback_data='show_id')],
        [InlineKeyboardButton("دریافت لینک دعوت", callback_data='get_invite_link')],
        [InlineKeyboardButton("مشاهده کاربران دعوت‌شده", callback_data='show_invited_users')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("لطفاً یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=reply_markup)

# مدیریت انتخاب دکمه‌ها
async def button_handler(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id
    bot_username = context.bot.username

    if query.data == 'show_id':
        await query.answer()
        await query.edit_message_text(f"آیدی شما: {user_id}")

    elif query.data == 'get_invite_link':
        invite_link = generate_invite_link(user_id, bot_username)
        await query.answer()
        await query.edit_message_text(f"لینک دعوت مخصوص شما: {invite_link}")

    elif query.data == 'show_invited_users':
        invited_users = get_invited_users(user_id)
        if invited_users:
            invited_list = "\n".join([f"User ID: {user[0]}" for user in invited_users])
            await query.edit_message_text(f"کاربران دعوت‌شده:\n{invited_list}")
        else:
            await query.edit_message_text("هیچ کاربری از طریق لینک شما دعوت نشده است.")

# تابع استارت
async def start(update: Update, context):
    user_id = update.message.from_user.id
    if context.args:
        inviter_id = context.args[0]
        if inviter_id.isdigit():
            save_invite(user_id, inviter_id)
            await update.message.reply_text(f"شما توسط کاربر {inviter_id} دعوت شدید.")
        else:
            await update.message.reply_text("لینک دعوت نامعتبر است.")
    await main_menu(update, context)

if __name__ == '__main__':
    # وارد کردن توکن ربات
    from config import TOKEN  # توکن را از فایل config وارد کنید

    # ساختن اپلیکیشن ربات
    app = ApplicationBuilder().token(TOKEN).build()

    # هندلرها
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # شروع ربات
    app.run_polling()
