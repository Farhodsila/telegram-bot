import asyncio
import random
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import anthropic

load_dotenv()

TOKEN = os.getenv("TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
ai_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

class GameStates(StatesGroup):
    number_game   = State()
    quiz_game     = State()
    word_game     = State()
    roleplay_game = State()
    riddle_game   = State()

scores: dict[int, dict] = {}

def get_user(uid: int) -> dict:
    if uid not in scores:
        scores[uid] = {"score": 0, "games": 0, "name": ""}
    return scores[uid]

def ai_ask(prompt: str, system: str = "Sen o'zbek tilida javob beradigan yordamchisan.") -> str:
    try:
        msg = ai_client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception as e:
        return f"AI xatolik: {e}"

def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 O'yin boshlash"), KeyboardButton(text="📊 Reyting")],
            [KeyboardButton(text="🏆 Natijalarim"),    KeyboardButton(text="ℹ️ Yordam")],
        ],
        resize_keyboard=True,
    )

def games_kb() -> InlineKeyboardMarkup:
    games = [
        ("🔢 Son topish",    "g_number"),
        ("🧠 Viktorina",     "g_quiz"),
        ("📖 So'z zanjiri",  "g_word"),
        ("🎭 Rol o'yini",    "g_roleplay"),
        ("🔡 Topishmoq",     "g_riddle"),
    ]
    buttons = [[InlineKeyboardButton(text=name, callback_data=cb)] for name, cb in games]
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def quiz_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="A", callback_data="qa_A"),
         InlineKeyboardButton(text="B", callback_data="qa_B")],
        [InlineKeyboardButton(text="C", callback_data="qa_C"),
         InlineKeyboardButton(text="D", callback_data="qa_D")],
    ])

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = get_user(message.from_user.id)
    user["name"] = message.from_user.first_name or "Foydalanuvchi"
    await message.answer(
        f"👋 Salom, *{user['name']}*!\n\n"
        "🤖 Men *AIgram Bot* — sun'iy intellekt bilan ishlaydigan o'yin botiman!\n\n"
        "Quyidagi tugmalardan birini bosing:",
        parse_mode="Markdown",
        reply_markup=main_kb(),
    )
@dp.message(F.text == "ℹ️ Yordam")
@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📋 *O'yin turlari:*\n\n"
        "🔢 *Son topish* — 1-100 orasidagi sonni top (7 urinish)\n"
        "🧠 *Viktorina* — AI tomonidan 5 ta savol\n"
        "📖 *So'z zanjiri* — AI bilan so'z o'yini\n"
        "🎭 *Rol o'yini* — AI bilan sarguzasht (*stop* — tugatish)\n"
        "🔡 *Topishmoq* — AI topishmoqlarini yech\n\n"
        "⭐ Har o'yin uchun ball yig'asiz!",
        parse_mode="Markdown",
    )

@dp.message(F.text == "📊 Reyting")
async def cmd_leaderboard(message: Message):
    if not scores:
        await message.answer("Hali hech kim o'ynamagan 😅")
        return
    top = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)[:10]
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 *TOP 10 O'yinchilar:*\n"]
    for i, (uid, d) in enumerate(top):
        m = medals[i] if i < 3 else f"{i+1}."
        name = d.get("name") or f"ID:{uid}"
        lines.append(f"{m} {name} — *{d['score']}* ball ({d['games']} o'yin)")
    await message.answer("\n".join(lines), parse_mode="Markdown")

@dp.message(F.text == "🏆 Natijalarim")
async def cmd_mystats(message: Message):
    d = get_user(message.from_user.id)
    await message.answer(
        f"📊 *Sizning natijalaringiz:*\n\n"
        f"⭐ Ball: *{d['score']}*\n"
        f"🎮 O'yinlar: *{d['games']}*",
        parse_mode="Markdown",
    )

@dp.message(F.text == "🎮 O'yin boshlash")
async def cmd_choose_game(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🎮 *Qaysi o'yinni tanlaysiz?*", parse_mode="Markdown", reply_markup=games_kb())

@dp.callback_query(F.data == "back")
async def cb_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🏠 Bosh menyu")
    await call.message.answer("Bosh menyu:", reply_markup=main_kb())

@dp.callback_query(F.data == "g_number")
async def start_number(call: CallbackQuery, state: FSMContext):
    secret = random.randint(1, 100)
    await state.set_state(GameStates.number_game)
    await state.update_data(secret=secret, attempts=0)
    await call.message.edit_text(
        "🔢 *Son topish o'yini!*\n\n"
        "Men 1 dan 100 gacha son o'yladim.\n"
        "Sizda *7 urinish* bor. Boshlang! 🎯",
        parse_mode="Markdown",
    )

@dp.message(GameStates.number_game)
async def play_number(message: Message, state: FSMContext):
    data = await state.get_data()
    secret, attempts = data["secret"], data["attempts"] + 1
    uid = message.from_user.id

    try:
        guess = int(message.text)
    except ValueError:
        await message.answer("❗ Iltimos, faqat son kiriting!")
        return

    remaining = 7 - attempts

    if guess == secret:
        pts = max(10, 70 - attempts * 10)
        get_user(uid)["score"] += pts
        get_user(uid)["games"] += 1
        await state.clear()
        await message.answer(
            f"🎉 *To'g'ri! {secret} edi!*\n"
            f"Urinishlar: *{attempts}*\n"
            f"Yutilgan ball: *+{pts}*\n\n"
            f"Jami ballingiz: *{get_user(uid)['score']}* ⭐",
            parse_mode="Markdown", reply_markup=main_kb(),
        )
    elif attempts >= 7:
        get_user(uid)["games"] += 1
        await state.clear()
        await message.answer(
            f"😔 *Urinishlar tugadi!*\nMen *{secret}* deb o'ylagan edim.\n\nQayta urinib ko'ring! 💪",
            parse_mode="Markdown", reply_markup=main_kb(),
        )
    elif guess < secret:
        await state.update_data(attempts=attempts)
        await message.answer(f"⬆️ Kattaroq! (Qolgan urinish: *{remaining}*)", parse_mode="Markdown")
    else:
        await state.update_data(attempts=attempts)
        await message.answer(f"⬇️ Kichikroq! (Qolgan urinish: *{remaining}*)", parse_mode="Markdown")

# ═══════════════════════════════════════════════════════════════════════════════
#  2. VIKTORINA
# ═══════════════════════════════════════════════════════════════════════════════
async def send_quiz_question(chat_id: int, state: FSMContext):
    data = await state.get_data()
    q_num = data.get("q_num", 0) + 1
    await state.update_data(q_num=q_num)

    raw = ai_ask(
        "O'zbek tilida qiziqarli viktorina savoli ber.\n"
        "Format (faqat shunday yoz):\n"
        "SAVOL: ...\nA) ...\nB) ...\nC) ...\nD) ...\nTO'G'RI: A",
        "Sen viktorina ustasissan. Faqat berilgan formatda yoz.",
    )
    correct = "A"
    for line in raw.splitlines():
        if line.upper().startswith("TO'G'RI:") or line.upper().startswith("TOGRI:"):
            correct = line.split(":")[-1].strip().upper()[:1]

    await state.update_data(correct=correct)
    display = "\n".join(l for l in raw.splitlines()
                        if not l.upper().startswith("TO'G'RI") and not l.upper().startswith("TOGRI"))
    await bot.send_message(
        chat_id,
        f"❓ *Savol {q_num}/5:*\n\n{display}",
        parse_mode="Markdown",
        reply_markup=quiz_kb(),
    )

@dp.callback_query(F.data == "g_quiz")
async def start_quiz(call: CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.quiz_game)
    await state.update_data(q_num=0, q_score=0)
    await call.message.edit_text("🧠 *Viktorina!* AI savollarni tayyorlamoqda...", parse_mode="Markdown")
    await send_quiz_question(call.message.chat.id, state)

@dp.callback_query(GameStates.quiz_game, F.data.startswith("qa_"))
async def quiz_answer(call: CallbackQuery, state: FSMContext):
    data  = await state.get_data()
    chosen  = call.data.split("_")[1]
    correct = data.get("correct", "A")
    q_score = data.get("q_score", 0)
    q_num   = data.get("q_num", 0)
    uid     = call.from_user.id

    if chosen == correct:
        q_score += 1
        await call.answer("✅ To'g'ri!")
        await call.message.answer(f"✅ *To'g'ri javob!*", parse_mode="Markdown")
    else:
        await call.answer(f"❌ Noto'g'ri! To'g'risi: {correct}")
        await call.message.answer(f"❌ *Noto'g'ri!* To'g'ri javob: *{correct}*", parse_mode="Markdown")

    await state.update_data(q_score=q_score)

    if q_num >= 5:
        pts = q_score * 10
        get_user(uid)["score"] += pts
        get_user(uid)["games"]  += 1
        await state.clear()
        await call.message.answer(
            f"🏁 *Viktorina tugadi!*\n\n"
            f"Natija: *{q_score}/5*\n"
            f"Yutilgan ball: *+{pts}*\n\n"
            f"Jami: *{get_user(uid)['score']}* ⭐",
            parse_mode="Markdown", reply_markup=main_kb(),
        )
    else:
        await send_quiz_question(call.message.chat.id, state)

# ═══════════════════════════════════════════════════════════════════════════════
#  3. SO'Z ZANJIRI
# ═══════════════════════════════════════════════════════════════════════════════
@dp.callback_query(F.data == "g_word")
async def start_word(call: CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.word_game)
    await state.update_data(last_word="", chain=[])
    await call.message.edit_text(
        "📖 *So'z zanjiri o'yini!*\n\n"
        "• Har so'z oldingi so'zning *oxirgi harfi* bilan boshlansin\n"
        "• O'zbek tilida\n"
        "• Takrorlanmasin\n\n"
        "Birinchi so'zni yozing! ✍️",
        parse_mode="Markdown",
    )

@dp.message(GameStates.word_game)
async def play_word(message: Message, state: FSMContext):
    data = await state.get_data()
    last_word: str = data.get("last_word", "")
    chain: list   = data.get("chain", [])
    word = message.text.strip().lower()
    uid  = message.from_user.id

    if last_word and word[0] != last_word[-1]:
        await message.answer(f"❌ So'z *'{last_word[-1].upper()}'* harfi bilan boshlanishi kerak!", parse_mode="Markdown")
        return
    if word in chain:
        await message.answer("❌ Bu so'z allaqachon ishlatilgan!")
        return

    chain.append(word)
    get_user(uid)["score"] += 1

    ai_word = ai_ask(
        f"So'z zanjiri o'yini. Oxirgi so'z: '{word}'. "
        f"'{word[-1]}' harfi bilan boshlanadigan bitta o'zbek so'zi top. "
        f"Faqat bitta so'z yoz.",
        "Sen so'z o'yini ustasissan.",
    ).strip().lower().split()[0]

    if ai_word in chain:
        get_user(uid)["games"] += 1
        await state.clear()
        await message.answer(
            f"🤖 AI so'z topa olmadi! Siz yutdingiz! 🎉\n\n"
            f"Zanjir uzunligi: *{len(chain)}*\n"
            f"Jami ball: *{get_user(uid)['score']}* ⭐",
            parse_mode="Markdown", reply_markup=main_kb(),
        )
    else:
        chain.append(ai_word)
        await state.update_data(last_word=ai_word, chain=chain)
        await message.answer(
            f"✅ _{word}_\n🤖 Mening so'zim: *{ai_word}*\n\n"
            f"*'{ai_word[-1].upper()}'* harfi bilan davom eting!",
            parse_mode="Markdown",
        )

# ═══════════════════════════════════════════════════════════════════════════════
#  4. ROL O'YINI
# ═══════════════════════════════════════════════════════════════════════════════
@dp.callback_query(F.data == "g_roleplay")
async def start_roleplay(call: CallbackQuery, state: FSMContext):
    scenarios = [
        "kosmik kemada kapitan",
        "qadimgi Samarqandda savdogar",
        "zamonaviy detektiv",
        "sehrli dunyo qahramoni",
    ]
    scenario = random.choice(scenarios)
    await state.set_state(GameStates.roleplay_game)
    await state.update_data(scenario=scenario, history=[])

    await call.message.edit_text("🎭 *Rol o'yini* tayyorlanmoqda...", parse_mode="Markdown")
    intro = ai_ask(
        f"Sen {scenario} rolini o'ynaysan. O'zbek tilida qisqa va qiziqarli kirish matni yoz. Foydalanuvchini sarguzashtga taklif qil.",
        "Sen ijodiy rol o'yini ustasissan.",
    )
    await call.message.answer(
        f"🎭 *Rol o'yini: {scenario.upper()}*\n\n{intro}\n\n_('stop' deb yozing — tugatish)_",
        parse_mode="Markdown",
    )

@dp.message(GameStates.roleplay_game)
async def play_roleplay(message: Message, state: FSMContext):
    uid  = message.from_user.id
    text = message.text.strip()

    if text.lower() == "stop":
        get_user(uid)["score"] += 20
        get_user(uid)["games"]  += 1
        await state.clear()
        await message.answer(
            f"🎭 *Rol o'yini tugadi!*\n+20 ball!\nJami: *{get_user(uid)['score']}* ⭐",
            parse_mode="Markdown", reply_markup=main_kb(),
        )
        return

    data    = await state.get_data()
    history = data.get("history", [])
    scenario = data.get("scenario", "qahramon")
    history.append({"role": "user", "content": text})

    try:
        resp = ai_client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            system=f"Sen {scenario} rolini o'ynaysan. O'zbek tilida qisqa, dramatik javob ber. Sarguzashtni davom ettir.",
            messages=history[-6:],
        )
        ai_text = resp.content[0].text
    except Exception as e:
        ai_text = "Bir lahza kuting..."

    history.append({"role": "assistant", "content": ai_text})
    await state.update_data(history=history)
    get_user(uid)["score"] += 2

    await message.answer(f"🎭 {ai_text}\n\n_('stop' — tugatish)_", parse_mode="Markdown")

# ═══════════════════════════════════════════════════════════════════════════════
#  5. TOPISHMOQ
# ═══════════════════════════════════════════════════════════════════════════════
async def send_riddle(chat_id: int, state: FSMContext):
    raw = ai_ask(
        "O'zbek tilida qiziqarli topishmoq ber.\n"
        "Format (faqat shunday yoz):\nTOPISHMOQ: ...\nJAVOB: ...",
        "Sen topishmoq ustasissan.",
    )
    riddle_text = answer = ""
    for line in raw.splitlines():
        if line.upper().startswith("TOPISHMOQ:"):
            riddle_text = line.split(":", 1)[-1].strip()
        elif line.upper().startswith("JAVOB:"):
            answer = line.split(":", 1)[-1].strip().lower()

    await state.update_data(riddle=riddle_text, answer=answer)
    await bot.send_message(
        chat_id,
        f"🔡 *Topishmoq:*\n\n_{riddle_text}_\n\nJavobni yozing! 💭",
        parse_mode="Markdown",
    )

@dp.callback_query(F.data == "g_riddle")
async def start_riddle(call: CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.riddle_game)
    await call.message.edit_text("🔡 *Topishmoq* tayyorlanmoqda...", parse_mode="Markdown")
    await send_riddle(call.message.chat.id, state)

@dp.message(GameStates.riddle_game)
async def play_riddle(message: Message, state: FSMContext):
    data   = await state.get_data()
    answer = data.get("answer", "")
    uid    = message.from_user.id

    check = ai_ask(
        f"Topishmoq javobi: '{answer}'. Foydalanuvchi javobi: '{message.text.lower()}'. "
        "Agar to'g'ri yoki yaqin bo'lsa faqat 'HA' yoz, aks holda faqat 'YOQ' yoz.",
        "Sen topishmoq hakamissan.",
    ).strip().upper()

    if "HA" in check:
        get_user(uid)["score"] += 15
        get_user(uid)["games"]  += 1
        await state.clear()
        await message.answer(
            f"🎉 *To'g'ri!* Javob: _{answer}_\n\n+15 ball!\nJami: *{get_user(uid)['score']}* ⭐",
            parse_mode="Markdown", reply_markup=main_kb(),
        )
    else:
        await message.answer("❌ Noto'g'ri! Qayta urinib ko'ring 🤔")

# ─── main ─────────────────────────────────────────────────────────────────────
async def main():
    print("🤖 AIgram Bot (aiogram 3) ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
