import asyncio
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = "8004523182:AAFtqzYrVIMsrYzcIa-TbdcGmlpZfrHttzc"
DATA_FILE = "bot_data.json"

channel_messages = {}
service_messages = {}
user_channels = {}
auto_pin_tasks = {}
auto_pin_intervals = {}

E = {'menu':'🎛','channel':'📢','pin':'📌','unpin':'🔓','delete':'🗑','auto':'🔄','add':'➕','back':'◀️','success':'✅','error':'❌','info':'ℹ️','warning':'⚠️','clock':'⏱','active':'🟢','inactive':'🔴','stats':'📊','fire':'🔥','chart':'📈'}

def save_data():
    data = {
        'channel_messages': {str(k): v for k, v in channel_messages.items()},
        'service_messages': {str(k): v for k, v in service_messages.items()},
        'auto_pin_intervals': {str(k): v for k, v in auto_pin_intervals.items()}
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"{E['success']} Данные сохранены")
    except Exception as e:
        print(f"{E['error']} Ошибка: {e}")

def load_data():
    global channel_messages, service_messages, auto_pin_intervals
    if not os.path.exists(DATA_FILE):
        print(f"{E['info']} База создана: {DATA_FILE}")
        save_data()
        return
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        channel_messages = {int(k): v for k, v in data.get('channel_messages', {}).items()}
        service_messages = {int(k): v for k, v in data.get('service_messages', {}).items()}
        auto_pin_intervals = {int(k): v for k, v in data.get('auto_pin_intervals', {}).items()}
        print(f"{E['success']} База загружена: {len(channel_messages)} каналов")
    except Exception as e:
        print(f"{E['error']} Ошибка: {e}")

async def safe_edit(query, text, reply_markup=None):
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            print(f"{E['error']} {e}")

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🎛 Мои каналы")],
        [KeyboardButton("➕ Добавить канал"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "╔═══════════════════════╗\n"
        "║   📌 PIN MANAGER BOT   ║\n"
        "╚═══════════════════════╝\n\n"
        "🎯 Добро пожаловать!\n\n"
        "⚡️ Возможности:\n"
        "  🔄 Автозакрепление\n"
        "  📌 Управление постами\n"
        "  📊 Статистика\n"
        "  💾 Автосохранение\n\n"
        "💡 Отправьте ссылку на пост!"
    )
    await update.message.reply_text(welcome, reply_markup=get_main_keyboard())

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Мои каналы" in text:
        await show_channels_menu_text(update, context)
    elif "Добавить канал" in text:
        instruction = (
            "╔═══════════════════════╗\n"
            "║  ➕ ДОБАВИТЬ КАНАЛ  ║\n"
            "╚═══════════════════════╝\n\n"
            "📋 Инструкция:\n\n"
            "1️⃣ Добавьте бота в канал\n"
            "2️⃣ Дайте права администратора\n"
            "3️⃣ Скопируйте ссылку на пост\n"
            "4️⃣ Отправьте 3 ссылки боту\n\n"
            "📎 Пример:\n"
            "t.me/yourchannel/123"
        )
        await update.message.reply_text(instruction)
    elif "Статистика" in text:
        await show_stats(update, context)
    elif "Помощь" in text:
        help_text = (
            "╔═══════════════════════╗\n"
            "║      ℹ️ СПРАВКА      ║\n"
            "╚═══════════════════════╝\n\n"
            "📌 Закрепить 3 поста\n"
            "   └ Последние 3 поста\n\n"
            "🔄 Автозакрепление\n"
            "   └ По таймеру\n\n"
            "🗑 Удалить уведомления\n"
            "   └ Чистка канала\n\n"
            "🔄 Сбросить посты\n"
            "   └ Новые ссылки\n\n"
            "💡 Отправляйте ссылки боту!"
        )
        await update.message.reply_text(help_text)
    elif text.startswith('@'):
        await add_channel_by_username(update, context, text)
    elif "t.me/" in text:
        await handle_post_link(update, context, text)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_channels = len(channel_messages)
    total_posts = sum(len(posts) for posts in channel_messages.values())
    active_auto = len(auto_pin_tasks)
    
    stats = (
        "╔═══════════════════════╗\n"
        "║   📊 СТАТИСТИКА      ║\n"
        "╚═══════════════════════╝\n\n"
        f"📢 Каналов: {total_channels}\n"
        f"📌 Постов: {total_posts}\n"
        f"🔄 Авто активно: {active_auto}\n"
        f"💾 База: {DATA_FILE}\n\n"
        f"{'🟢 Всё отлично!' if total_channels > 0 else '⚠️ Добавьте каналы'}"
    )
    await update.message.reply_text(stats)

async def handle_post_link(update: Update, context: ContextTypes.DEFAULT_TYPE, link: str):
    msg = await update.message.reply_text("⏳ Обработка...")
    await asyncio.sleep(0.3)
    await msg.edit_text("🔍 Проверяю канал...")
    
    try:
        parts = link.split('/')
        if '/c/' in link:
            channel_id_str = parts[-2]
            message_id = int(parts[-1].split('?')[0])
            chat_id = int(f"-100{channel_id_str}")
        else:
            channel_username = parts[-2]
            message_id = int(parts[-1].split('?')[0])
            if not channel_username.startswith('@'):
                channel_username = '@' + channel_username
            chat = await context.bot.get_chat(channel_username)
            chat_id = chat.id
        
        if chat_id not in channel_messages:
            channel_messages[chat_id] = []
            service_messages[chat_id] = []
        
        if message_id not in channel_messages[chat_id]:
            channel_messages[chat_id].append(message_id)
            channel_messages[chat_id] = sorted(channel_messages[chat_id])[-20:]
        
        await msg.edit_text("💾 Сохраняю...")
        save_data()
        await asyncio.sleep(0.3)
        
        total = len(channel_messages[chat_id])
        chat = await context.bot.get_chat(chat_id)
        
        progress_bar = '▰' * total + '▱' * (3 - min(total, 3))
        
        result = (
            f"✅ Пост добавлен!\n\n"
            f"┏━━━━━━━━━━━━━━━━━━━┓\n"
            f"┃ 📢 {chat.title[:15]}\n"
            f"┣━━━━━━━━━━━━━━━━━━━┫\n"
            f"┃ 📌 ID: {message_id}\n"
            f"┃ 📊 Всего: {total}\n"
            f"┃ {progress_bar} {total}/3\n"
            f"┗━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"{'🎉 Готово к закреплению!' if total >= 3 else f'💡 Осталось: {3-total}'}"
        )
        
        await msg.edit_text(result, reply_markup=get_main_keyboard())
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {str(e)}\n\nПроверьте ссылку")

async def add_channel_by_username(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str):
    if not username.startswith('@'):
        username = '@' + username
    msg = await update.message.reply_text("🔍 Проверяю канал...")
    try:
        chat = await context.bot.get_chat(username)
        chat_id = chat.id
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if bot_member.status not in ["administrator","creator"]:
            await msg.edit_text(f"❌ Бот не админ в {chat.title}\n\nДобавьте права!")
            return
        if chat_id not in channel_messages:
            channel_messages[chat_id] = []
            service_messages[chat_id] = []
        await msg.edit_text("💾 Сохраняю...")
        save_data()
        await asyncio.sleep(0.3)
        await msg.edit_text(f"✅ Канал добавлен!\n\n📢 {chat.title}\n\n💡 Отправьте 3 ссылки на посты")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")

async def show_channels_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not channel_messages:
        await update.message.reply_text("ℹ️ Нет каналов\n\nИспользуйте ➕ Добавить канал")
        return
    keyboard = []
    for chat_id in channel_messages.keys():
        try:
            chat = await context.bot.get_chat(chat_id)
            status = "🔥" if chat_id in auto_pin_tasks else "💤"
            posts = len(channel_messages.get(chat_id,[]))
            keyboard.append([InlineKeyboardButton(f"{status} {chat.title} • {posts} постов",callback_data=f"ch_{chat_id}")])
        except:
            continue
    if keyboard:
        header = (
            "╔═══════════════════════╗\n"
            "║   🎛 МОИ КАНАЛЫ     ║\n"
            "╚═══════════════════════╝\n\n"
            "🔥 = Авто активно\n"
            "💤 = Авто выключено"
        )
        await update.message.reply_text(header, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_channel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if "_" in query.data:
        chat_id = int(query.data.split("_")[1])
        user_channels[update.effective_user.id] = chat_id
    else:
        chat_id = user_channels.get(update.effective_user.id)
        if not chat_id:
            await safe_edit(query, "❌ Канал не выбран")
            return
    try:
        chat = await context.bot.get_chat(chat_id)
        posts = len(channel_messages.get(chat_id,[]))
        auto_status = "🔥 Активно" if chat_id in auto_pin_tasks else "💤 Выключено"
        interval = auto_pin_intervals.get(chat_id,30)
        
        card = (
            "┏━━━━━━━━━━━━━━━━━━━┓\n"
            f"┃ 📢 {chat.title[:15]}\n"
            "┣━━━━━━━━━━━━━━━━━━━┫\n"
            f"┃ 📊 Постов: {posts}\n"
            f"┃ 🔄 Авто: {auto_status}\n"
            f"┃ ⏱ Интервал: {interval}м\n"
            "┗━━━━━━━━━━━━━━━━━━━┛"
        )
        
        keyboard = [
            [InlineKeyboardButton("📌 Закрепить",callback_data="pin"), InlineKeyboardButton("🔓 Открепить",callback_data="unpin")],
            [InlineKeyboardButton("🗑 Очистить",callback_data="del"), InlineKeyboardButton("🔄 Сбросить",callback_data="reset")],
            [InlineKeyboardButton(f"⚙️ Автозакрепление ({interval}м)",callback_data="auto")],
            [InlineKeyboardButton("◀️ Назад",callback_data="back")]
        ]
        await safe_edit(query, card, InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await safe_edit(query, f"❌ {e}")

async def pin_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = user_channels.get(update.effective_user.id)
    if not chat_id:
        return
    try:
        if len(channel_messages.get(chat_id,[])) < 3:
            await safe_edit(query, "❌ Недостаточно постов!\n\n💡 Отправьте боту 3 ссылки")
            return
        
        await safe_edit(query, "🔓 Открепляю все...")
        await context.bot.unpin_all_chat_messages(chat_id)
        await asyncio.sleep(0.5)
        
        await safe_edit(query, "📌 Закрепляю посты...")
        last_three = sorted(channel_messages[chat_id])[-3:]
        pinned = 0
        for msg_id in last_three:
            try:
                await context.bot.pin_chat_message(chat_id=chat_id,message_id=msg_id)
                pinned += 1
                await asyncio.sleep(0.3)
            except:
                pass
        
        await query.answer(f"🎉 Закреплено: {pinned}/3", show_alert=True)
        await asyncio.sleep(1)
        await show_channel_menu(update,context)
    except Exception as e:
        await query.answer(f"❌ {e}", show_alert=True)

async def unpin_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = user_channels.get(update.effective_user.id)
    if chat_id:
        try:
            await context.bot.unpin_all_chat_messages(chat_id)
            await query.answer("✅ Все посты откреплены", show_alert=True)
            await show_channel_menu(update,context)
        except Exception as e:
            await query.answer(f"❌ {e}", show_alert=True)

async def delete_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = user_channels.get(update.effective_user.id)
    if not chat_id:
        return
    deleted = 0
    if chat_id in service_messages:
        for msg_id in service_messages[chat_id]:
            try:
                await context.bot.delete_message(chat_id,msg_id)
                deleted += 1
                await asyncio.sleep(0.2)
            except:
                pass
        service_messages[chat_id] = []
        save_data()
    await query.answer(f"🗑 Удалено: {deleted}" if deleted else "ℹ️ Нет уведомлений", show_alert=True)

async def reset_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = user_channels.get(update.effective_user.id)
    if not chat_id:
        return
    try:
        old_count = len(channel_messages.get(chat_id, []))
        channel_messages[chat_id] = []
        service_messages[chat_id] = []
        save_data()
        await query.answer(f"🔄 Сброшено: {old_count} постов", show_alert=True)
        await show_channel_menu(update, context)
    except Exception as e:
        await query.answer(f"❌ {e}", show_alert=True)

async def show_auto_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = user_channels.get(update.effective_user.id)
    if not chat_id:
        return
    is_active = chat_id in auto_pin_tasks
    interval = auto_pin_intervals.get(chat_id,30)
    
    menu = (
        "╔═══════════════════════╗\n"
        "║  🔄 АВТОЗАКРЕПЛЕНИЕ  ║\n"
        "╚═══════════════════════╝\n\n"
        f"Статус: {'🔥 Активно' if is_active else '💤 Выключено'}\n"
        f"Интервал: {interval} мин\n\n"
        "Цикл:\n"
        "1️⃣ Открепить все\n"
        "2️⃣ Удалить уведомления\n"
        "3️⃣ Закрепить 3 поста"
    )
    
    keyboard = [
        [InlineKeyboardButton("⏱ 15м",callback_data="ai_15"), InlineKeyboardButton("⏱ 30м",callback_data="ai_30")],
        [InlineKeyboardButton("⏱ 1ч",callback_data="ai_60"), InlineKeyboardButton("⏱ 2ч",callback_data="ai_120")],
        [InlineKeyboardButton("🧪 Тест (выполнить сейчас)",callback_data="test")]
    ]
    if is_active:
        keyboard.append([InlineKeyboardButton("⛔️ Остановить",callback_data="as")])
    else:
        keyboard.append([InlineKeyboardButton("▶️ Запустить",callback_data="ar")])
    keyboard.append([InlineKeyboardButton("◀️ Назад",callback_data=f"ch_{chat_id}")])
    
    await safe_edit(query, menu, InlineKeyboardMarkup(keyboard))

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = user_channels.get(update.effective_user.id)
    if chat_id:
        interval = int(query.data.split("_")[1])
        auto_pin_intervals[chat_id] = interval
        save_data()
        await query.answer(f"⚡️ Интервал: {interval} мин", show_alert=True)
        await show_auto_menu(update,context)

async def auto_cycle(context: ContextTypes.DEFAULT_TYPE, chat_id: int, is_first_run: bool = False):
    try:
        if not is_first_run:
            if chat_id in service_messages:
                for msg_id in service_messages[chat_id]:
                    try:
                        await context.bot.delete_message(chat_id, msg_id)
                        await asyncio.sleep(0.2)
                    except:
                        pass
                service_messages[chat_id] = []
            await asyncio.sleep(1)
        
        await context.bot.unpin_all_chat_messages(chat_id)
        await asyncio.sleep(1)
        
        if chat_id in channel_messages and len(channel_messages[chat_id]) >= 3:
            for msg_id in sorted(channel_messages[chat_id])[-3:]:
                try:
                    await context.bot.pin_chat_message(chat_id=chat_id, message_id=msg_id)
                    await asyncio.sleep(0.3)
                except:
                    pass
        print(f"🔥 Автоцикл: {chat_id}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def test_auto_cycle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = user_channels.get(update.effective_user.id)
    if not chat_id:
        return
    try:
        await query.answer("🧪 Запуск теста...", show_alert=True)
        await safe_edit(query, "🧪 Выполняю тестовый цикл...\n\n⏳ Пожалуйста, подождите")
        await auto_cycle(context, chat_id, is_first_run=False)
        chat = await context.bot.get_chat(chat_id)
        await asyncio.sleep(1)
        
        result = (
            "✅ Тест завершён!\n\n"
            f"📢 {chat.title}\n"
            "━━━━━━━━━━━━━━\n"
            "✓ Посты закреплены\n"
            "✓ Уведомления удалены\n"
            "✓ Всё работает!"
        )
        await safe_edit(query, result)
        await asyncio.sleep(2)
        await show_auto_menu(update, context)
    except Exception as e:
        await query.answer(f"❌ {e}", show_alert=True)

async def start_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = user_channels.get(update.effective_user.id)
    if not chat_id:
        return
    interval = auto_pin_intervals.get(chat_id,30)
    if chat_id in auto_pin_tasks:
        await query.answer("⚠️ Уже запущено!", show_alert=True)
        return
    
    async def task():
        is_first = True
        while chat_id in auto_pin_tasks:
            await auto_cycle(context, chat_id, is_first_run=is_first)
            is_first = False
            await asyncio.sleep(interval * 60)
    
    auto_pin_tasks[chat_id] = asyncio.create_task(task())
    await query.answer(f"🔥 Автозакрепление запущено!\nИнтервал: {interval} мин", show_alert=True)
    await show_auto_menu(update,context)

async def stop_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = user_channels.get(update.effective_user.id)
    if chat_id and chat_id in auto_pin_tasks:
        auto_pin_tasks[chat_id].cancel()
        del auto_pin_tasks[chat_id]
        await query.answer("⛔️ Автозакрепление остановлено", show_alert=True)
    else:
        await query.answer("ℹ️ Не было запущено", show_alert=True)
    await show_auto_menu(update,context)

async def track_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post:
        chat_id = update.channel_post.chat_id
        message_id = update.channel_post.message_id
        if chat_id not in channel_messages:
            channel_messages[chat_id] = []
            service_messages[chat_id] = []
        if update.channel_post.pinned_message:
            if message_id not in service_messages[chat_id]:
                service_messages[chat_id].append(message_id)
        else:
            if message_id not in channel_messages[chat_id]:
                channel_messages[chat_id].append(message_id)
                channel_messages[chat_id] = channel_messages[chat_id][-20:]
                save_data()

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    routes = {'ch_':show_channel_menu,'pin':pin_posts,'unpin':unpin_posts,'del':delete_service,'reset':reset_posts,'auto':show_auto_menu,'ai_':set_interval,'ar':start_auto,'as':stop_auto,'test':test_auto_cycle,'back':show_channels_menu_callback}
    for prefix, handler in routes.items():
        if data.startswith(prefix) or data == prefix:
            await handler(update,context)
            return

async def show_channels_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not channel_messages:
        await safe_edit(query, "ℹ️ Нет каналов")
        return
    keyboard = []
    for chat_id in channel_messages.keys():
        try:
            chat = await context.bot.get_chat(chat_id)
            status = "🔥" if chat_id in auto_pin_tasks else "💤"
            posts = len(channel_messages.get(chat_id,[]))
            keyboard.append([InlineKeyboardButton(f"{status} {chat.title} • {posts}",callback_data=f"ch_{chat_id}")])
        except:
            continue
    if keyboard:
        await safe_edit(query, "🎛 Выберите канал:", InlineKeyboardMarkup(keyboard))

def main():
    load_data()
    app = Application.builder().token(BOT_TOKEN).build()
    
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        if "message is not modified" not in str(context.error).lower():
            print(f"❌ {context.error}")
    
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start",start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,handle_text_messages))
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL,track_messages))
    app.add_handler(CallbackQueryHandler(callback_router))
    
    print("\n╔═══════════════════════════╗")
    print("║  🔥 PIN MANAGER BOT 🔥  ║")
    print("╚═══════════════════════════╝")
    print(f"✅ Бот запущен успешно!")
    print(f"💾 База: {DATA_FILE}\n")
    
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        save_data()
        print("\n⛔️ Бот остановлен")
        print("💾 Данные сохранены\n")

if __name__ == "__main__":
    main()
