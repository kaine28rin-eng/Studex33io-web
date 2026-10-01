#!/usr/bin/env python3
"""Main entry point for the Academic Study Bot (STUDYX)."""
import asyncio
import logging
import sys
import os
import aiohttp

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    WebAppInfo,
    InputMediaPhoto,
    FSInputFile,
    BotCommand,
    BotCommandScopeDefault,
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, WEBAPP_URL
from db.database import init_db, get_all_modules, get_module_by_name, add_course_notes
from webapp.sync_db_to_json import sync

from handlers.material import router as material_router
from handlers.quiz import router as quiz_router
from handlers.study import router as study_router
from handlers.timetable import router as timetable_router
from handlers.timetable_monitor import check_timetable_update

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


MODULE_EMOJI = {
    "19th Century Literature": "📖",
    "Cultural Studies": "🌍",
    "Applied Linguistics": "🗣️",
    "Advanced Research Techniques": "🔬",
    "General Linguistics": "🔤",
}


def build_start_keyboard():
    """Build the premium /start inline keyboard."""
    from config import MODULES

    buttons = []

    # Top row: Web App button
    buttons.append([
        InlineKeyboardButton(
            text="📱 Open Study Web App",
            web_app=WebAppInfo(url=WEBAPP_URL),
        )
    ])

    # Module rows with emojis
    for module in MODULES:
        emoji = MODULE_EMOJI.get(module, "📌")
        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} {module}",
                callback_data=f"module_{module}",
            )
        ])

    # Google Classroom Codes row
    buttons.append([
        InlineKeyboardButton(text="🏛️ Google Classroom Codes", callback_data="classroom_codes"),
    ])
    # Timetable row
    buttons.append([
        InlineKeyboardButton(text="📅 Timetable", callback_data="view_timetable"),
    ])

    # Bottom row: Upload / Contribute
    buttons.append([
        InlineKeyboardButton(text="🔧 Upload Material", callback_data="admin_upload")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def start_handler(message: Message):
    """Handle /start command — auto-show modules as inline keyboard."""
    user_name = message.from_user.full_name or "there"
    from config import MODULES

    if not MODULES:
        await message.reply(
            "👋 Welcome!\n\nNo modules are currently configured.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 Open Study Web App", web_app=WebAppInfo(url=WEBAPP_URL))]
            ]),
        )
        return

    keyboard = build_start_keyboard()

    await message.reply(
        "👋 Welcome, {user_name}!\n"
        "────────────────────────\n"
        "🎓 FLSHM • English Studies S5 (Literature)\n"
        "Hassan II University • Mohammedia\n"
        "Select a module below to view materials, or launch the Web App:".format(user_name=user_name),
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def help_handler(message: Message):
    """Handle /help command."""
    await message.reply(
        "📚 **STUDYX — Academic Study Bot**\n\n"
        "Commands:\n"
        "  /start — Start bot & view modules\n"
        "  /modules — List all study modules\n"
        "  /upload — Upload study materials\n"
        "  /generate_quiz <module> — Create quiz from materials\n"
        "  /review — Start spaced-repetition review\n"
        "  /active_recall <module> — Active recall practice\n"
        "  /pomodoro <task> — 25-min focused study\n"
        "  /define <word> — Universal dictionary lookup\n"
        "  \n"
        "Spaced Repetition uses SM-2 algorithm.\n"
        "Active Recall: write from memory before checking notes.",
        parse_mode="Markdown"
    )


async def webapp_handler(message: Message):
    """Handle /webapp command — link to the materials portal."""
    await message.reply(
        "🌐 **STUDYX Materials Portal**\n\n"
        "Browse all course materials, download PDFs, and search across modules:\n"
        "https://kaine28rin-eng.github.io/Studex33io-web/\n\n"
        "The portal is synced with the bot's database and updated automatically.",
        parse_mode="Markdown",
        disable_web_page_preview=False
    )


async def inject_handler(message: Message):
    """Handle /inject command — admin can push course text into a module.

    Usage: /inject <module> <topic>\n<course notes text>
    Example:
      /inject '19th Century Literature' 'Gothic Elements'
      The Romantic movement in English literature emerged in the late 18th century...
    """
    from config import is_admin
    if not is_admin(message.from_user.id):
        await message.reply("🚫 This command is admin-only.")
        return
    args = message.text.split(None, 2)  # /inject, module, topic+content
    if len(args) < 3:
        await message.reply(
            "📌 Usage: /inject <module> <topic>\n<course text>\n\n"
            "Example:\n"
            "  /inject \"Cultural Studies\" \"Postcolonial Theory\"\n"
            "  Your notes here..."
        )
        return

    module_name = args[1]
    # Remaining args: "topic\ncourse text" — split on newline for topic vs content
    rest = args[2]
    if "\n" in rest:
        topic, notes_text = rest.split("\n", 1)
    else:
        topic, notes_text = rest, ""

    if not notes_text.strip():
        await message.reply("❗ Please provide course notes after the topic line.")
        return

    module_name = args[1]
    if not notes_text.strip():
        await message.reply("❗ Please provide course notes after the topic line.")
        return

    try:
        material_id = await add_course_notes(module_name, topic.strip(), notes_text.strip(), message.from_user.id)
        await message.reply(
            f"✅ Notes added to **{module_name}**\n"
            f"   Topic: `{topic.strip()}`\n"
            f"   Material ID: {material_id}\n"
            f"   Size: {len(notes_text)} chars",
            parse_mode="Markdown"
        )
    except ValueError as e:
        await message.reply(f"❌ {e}")


async def schedule_handler(message: Message):
    """Handle /schedule command — view the S5 GR02 timetable."""
    from config import TIMETABLE
    lines = ["📅 <b>S5 GR02 Weekly Timetable</b>\n────────────────────────"]
    for day, entries in TIMETABLE.items():
        lines.append(f"\n<b>{day}</b>")
        if entries:
            for entry in entries:
                lines.append(f"  • {entry}")
        else:
            lines.append("  <i>No classes</i>")
    text = "\n".join(lines)
    await message.reply(text, parse_mode="HTML")


async def deadlines_handler(message: Message):
    """Handle /deadlines command — view upcoming deadlines."""
    from config import DEADLINES
    if not DEADLINES:
        await message.reply("📭 No upcoming deadlines.", parse_mode="HTML")
        return
    lines = ["📋 <b>Upcoming Deadlines</b>\n────────────────────────"]
    for d in DEADLINES:
        lines.append(
            f"\n📅 <b>{d['due_date']}</b>\n"
            f"<b>{d['title']}</b>\n"
            f"<i>{d['description']}</i>\n"
            f"📖 Module: {d['module']}"
        )
    text = "\n".join(lines)
    await message.reply(text, parse_mode="HTML")


async def modules_handler(message: Message):
    """Handle /modules command — show the same clean start menu."""
    user_name = message.from_user.full_name or "there"
    keyboard = build_start_keyboard()

    await message.reply(
        "👋 Welcome, {}!\n"
        "────────────────────────\n"
        "🎓 FLSHM • English Studies S5 (Literature)\n"
        "Hassan II University • Mohammedia\n\n"
        "Select a module below to view materials, or launch the Web App:".format(user_name),
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def module_callback(callback: CallbackQuery):
    """Handle inline keyboard button clicks for module selection and admin actions."""
    data = callback.data
    if not data:
        return

    # Admin-only upload button
    if data == "admin_upload":
        from config import is_admin
        if not is_admin(callback.from_user.id):
            await callback.answer("🚫 Admin only.", show_alert=True)
            return
        await callback.message.reply(
            "📎 **Admin Upload Mode**\n\n"
            "Use the `/upload` command to start uploading materials.\n"
            "You can send: PDF, DOCX, TXT, images, or paste text.\n"
            "Use /cancel to abort at any time.",
            parse_mode="Markdown"
        )
        await callback.answer("Upload mode activated. Use /upload.")
        return

    if not data.startswith("module_"):
        return

    module_name = data[len("module_"):]

    # Fetch module details from DB
    module = await get_module_by_name(module_name)
    if module:
        # Build a richer info message with materials count
        from db.database import get_materials_by_module
        materials = await get_materials_by_module(module_name)

        desc = module['description'] or "No description available."
        classroom_code = module.get('classroom_code')
        classroom_url = module.get('classroom_url')

        info_text = (
            f"📘 <b>{module['name']}</b>\n\n"
            f"📄 <i>{desc}</i>\n"
            f"📊 Materials: {len(materials)} uploaded\n"
        )
        if materials:
            info_text += "\n📎 Uploaded materials:\n"
            for mat in materials[:5]:  # show first 5
                info_text += f"  • <code>{mat['title']}</code> ({mat['file_size']} bytes)\n"
            if len(materials) > 5:
                info_text += f"  ...and {len(materials) - 5} more\n"

        # Google Classroom section
        info_text += "\n🏛️ Google Classroom:\n"
        if classroom_code:
            info_text += f"Code: <code>{classroom_code}</code> (tap to copy)\n"
        else:
            info_text += "Code: <i>Not available yet</i>\n"

        info_text += "\n💡 Tip: Use /upload to add materials to this module, or /generate_quiz " + module_name + " to create a quiz."
    else:
        info_text = f"❓ Module '{module_name}' not found in database."

    # Build inline keyboard with Back, Web App, and (conditionally) Classroom button
    keyboard_rows = [
        [InlineKeyboardButton(text="🔙 Back to Modules", callback_data="back_to_modules")],
        [InlineKeyboardButton(text="🌐 Open Web App", url=WEBAPP_URL)],
    ]
    if classroom_url:
        keyboard_rows.append(
            [InlineKeyboardButton(text="🏫 Join Google Classroom", url=classroom_url)]
        )
    module_kb = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    await callback.message.edit_text(info_text, reply_markup=module_kb, parse_mode="HTML")
    await callback.answer()


async def back_to_modules_callback(callback: CallbackQuery):
    """Handle the 'Back to Modules' button — return to the main /start menu."""
    user_name = callback.from_user.full_name or "there"
    from config import MODULES

    keyboard = build_start_keyboard()

    await callback.message.edit_text(
        "👋 Welcome, {user_name}!\n"
        "────────────────────────\n"
        "🎓 FLSHM • English Studies S5 (Literature)\n"
        "Hassan II University • Mohammedia\n"
        "Select a module below to view materials, or launch the Web App:".format(user_name=user_name),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


# Dictionary API base
DICT_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"

async def define_handler(message: Message):
    """Handle /define <word> — look up a word using the Free Dictionary API.
    Returns a premium HTML-formatted definition card.
    """
    args = message.text.split(None, 1)
    if len(args) < 2 or not args[1].strip():
        await message.reply(
            "🔍 <b>Usage:</b> /define &lt;word&gt;\n\n"
            "Example: /define epistemology",
            parse_mode="HTML",
        )
        return

    word = args[1].strip().lower()
    url = f"{DICT_API_URL}{word}"

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.get(url) as resp:
                if resp.status == 404:
                    await message.reply(
                        f"❌ <b>No results</b> for &lt;{word}&gt;.\n"
                        "Please check your spelling and try again.",
                        parse_mode="HTML",
                    )
                    return
                if resp.status != 200:
                    logger.warning("Dictionary API returned status %d for word '%s'", resp.status, word)
                    await message.reply(
                        f"⚠️ Dictionary API returned status {resp.status}.\n"
                        "Try again later.",
                        parse_mode="HTML",
                    )
                    return
                data = await resp.json()
    except Exception as e:
        logger.error("Dictionary API error for '%s': %s", word, e, exc_info=True)
        await message.reply(
            "❌ Sorry, I couldn't reach the dictionary service right now.\n"
            "Try again in a moment.",
            parse_mode="HTML",
        )
        return

    if not data or not isinstance(data, list):
        await message.reply(
            f"❌ No definition found for &lt;{word}&gt;. Try another word.",
            parse_mode="HTML",
        )
        return

    entry = data[0]
    word_title = entry.get("word", word)

    # Extract phonetic if available
    phonetic = ""
    phonetics = entry.get("phonetics", [])
    if phonetics and isinstance(phonetics, list) and len(phonetics) > 0:
        phonetic = phonetics[0].get("text", "")

    # Extract first meaning's first definition + example
    meanings = entry.get("meanings", [])
    if not meanings:
        await message.reply(
            f"❌ No definitions found for &lt;{word}&gt;.",
            parse_mode="HTML",
        )
        return

    meaning = meanings[0]
    part_of_speech = meaning.get("partOfSpeech", "unknown")
    definitions = meaning.get("definitions", [])
    if not definitions:
        await message.reply(
            f"❌ No definitions found for &lt;{word}&gt;.",
            parse_mode="HTML",
        )
        return

    definition = definitions[0].get("definition", "No definition available.")
    example = definitions[0].get("example", "")

    # Build premium UI layout
    text = f"📖 <b>{word_title}</b>"
    if phonetic:
        text += f"  <i>{phonetic}</i>"
    text += f"\n────────────────────────\n"
    text += f"🏷️ <b>{part_of_speech}</b>\n"
    text += f"🔹 <b>Definition:</b> {definition}\n"
    if example:
        text += f"\n💬 <b>Example:</b> <i>\"{example}\"</i>\n"

    await message.reply(text, parse_mode="HTML")


async def classroom_codes_callback(callback: CallbackQuery):
    """Handle the 'Google Classroom Codes' inline button callback.
    Shows classroom codes as text with a Back button.
    """
    from config import MODULES

    lines = ["🏛️ FLSHM S5 Google Classroom Codes:\n"]
    for module_name, info in MODULES.items():
        code = info.get("classroom_code")
        if code:
            lines.append(f"• {module_name}: <code>{code}</code>")
    lines.append("\n(Tap a code to copy it. More modules will be added soon.)")
    text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="back_to_modules")],
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


async def timetable_callback(callback: CallbackQuery):
    """Handle the 'Timetable' inline button callback.
    Shows the timetable image with a Back button.
    Uses delete + answer_photo because Telegram cannot edit a pure text message
    into a media message.
    """
    timetable_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timetable_s5gr02.jpg")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="back_to_modules")],
    ])

    try:
        photo = FSInputFile(timetable_path)
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=photo,
            caption="📅 <b>S5 GR02 Weekly Timetable</b>\n\n📍 FLSH Mohammedia",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Timetable send failed: %s", e, exc_info=True)
        await callback.message.answer(
            "📅 <b>S5 GR02 Weekly Timetable</b>\n\n(Image failed to load)\n\nError: {}".format(e),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    await callback.answer()


async def check_token():
    """Check that BOT_TOKEN is configured."""
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN environment variable not set.")
        print("   Set it with: export TELEGRAM_BOT_TOKEN='your_bot_token_here'")
        return False
    return True


async def main():
    """Run the bot."""
    if not await check_token():
        sys.exit(1)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Sync DB to JSON for GitHub Pages
    try:
        await sync()
        logger.info("DB-to-JSON sync completed")
    except Exception as e:
        logger.warning("DB-to-JSON sync failed: %s", e)
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()

    # Set bot command menu (autocomplete when typing /)
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Open the main study hub menu"),
            BotCommand(command="define", description="Look up a word (e.g. /define syntax)"),
            BotCommand(command="schedule", description="View S5 GR02 timetable"),
            BotCommand(command="deadlines", description="View upcoming dates"),
            BotCommand(command="upload", description="(Admin) Upload study materials"),
            BotCommand(command="broadcast", description="(Admin) Send announcement to group"),
        ],
        scope=BotCommandScopeDefault(),
    )
    logger.info("Bot commands registered for autocomplete menu")

    # Register routers
    dp.include_router(material_router)
    dp.include_router(quiz_router)
    dp.include_router(study_router)
    dp.include_router(timetable_router)

    # Register basic handlers
    dp.message.register(start_handler, Command("start"))
    dp.message.register(help_handler, Command("help"))
    dp.message.register(modules_handler, Command("modules"))
    dp.message.register(inject_handler, Command("inject"))
    dp.message.register(webapp_handler, Command("webapp"))
    dp.message.register(define_handler, Command("define"))
    dp.message.register(schedule_handler, Command("schedule"))
    dp.message.register(deadlines_handler, Command("deadlines"))

    # Register callback query handlers for module inline buttons
    dp.callback_query.register(module_callback, lambda cb: cb.data and cb.data.startswith("module_"))
    dp.callback_query.register(back_to_modules_callback, lambda cb: cb.data == "back_to_modules")
    dp.callback_query.register(classroom_codes_callback, lambda cb: cb.data == "classroom_codes")
    dp.callback_query.register(timetable_callback, lambda cb: cb.data == "view_timetable")

    # Periodic timetable check (background task)
    async def periodic_timetable_check():
        """Check timetable every 6 hours and sync materials JSON every 3 hours."""
        group_chat_id = os.environ.get("GROUP_CHAT_ID", "")
        if not group_chat_id:
            logger.warning("GROUP_CHAT_ID not set — timetable auto-check will be skipped for notifications")

        while True:
            try:
                await asyncio.sleep(3 * 3600)  # 3 hours
                await sync()
                logger.info("Periodic DB-to-JSON sync completed")
                if group_chat_id:
                    await asyncio.sleep(3 * 3600)  # stagger
                    check_timetable_update(bot, int(group_chat_id))
            except Exception as e:
                logger.error("Periodic sync/check failed: %s", e)

    # Start background task
    asyncio.create_task(periodic_timetable_check())
    logger.info("Background timetable monitor started (checks every 6h)")

    logger.info("Bot started! Listening for messages...")
    print("🚀 STUDYX bot is running!")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped.")
