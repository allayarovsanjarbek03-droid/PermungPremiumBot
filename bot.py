import os
import asyncio
import logging
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
)

# =========================
# SOZLAMALAR
# =========================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi!")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

bot = Bot(TOKEN)
dp = Dispatcher()

# =========================
# PREMIUM PAKETLAR
# =========================

PLANS = {
    "premium_3": {
        "months": 3,
        "sell_stars": 1500,
        "cost_stars": 1000,
        "name": "Telegram Premium — 3 oy",
        "price_text": "150 000 so'm",
    },
    "premium_6": {
        "months": 6,
        "sell_stars": 2000,
        "cost_stars": 1500,
        "name": "Telegram Premium — 6 oy",
        "price_text": "200 000 so'm",
    },
    "premium_12": {
        "months": 12,
        "sell_stars": 2890,
        "cost_stars": 2500,
        "name": "Telegram Premium — 12 oy",
        "price_text": "289 000 so'm",
    },
}

# =========================
# DATABASE
# =========================

DB_FILE = "orders.db"

db = sqlite3.connect(DB_FILE, check_same_thread=False)
db.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL,
    username TEXT,
    plan TEXT NOT NULL,
    months INTEGER NOT NULL,
    paid_stars INTEGER NOT NULL,
    telegram_charge_id TEXT UNIQUE,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
)
""")
db.commit()


def save_order(
    user_id: int,
    username: str | None,
    plan_key: str,
    months: int,
    paid_stars: int,
    charge_id: str,
    status: str,
):
    db.execute(
        """
        INSERT OR IGNORE INTO orders
        (
            telegram_user_id,
            username,
            plan,
            months,
            paid_stars,
            telegram_charge_id,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            username,
            plan_key,
            months,
            paid_stars,
            charge_id,
            status,
            datetime.now().isoformat(),
        ),
    )
    db.commit()


# =========================
# MENYU
# =========================

def premium_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ Premium 3 oy — 150 000 so'm",
                    callback_data="premium_3",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Premium 6 oy — 200 000 so'm",
                    callback_data="premium_6",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Premium 12 oy — 289 000 so'm",
                    callback_data="premium_12",
                )
            ],
        ]
    )


# =========================
# /START
# =========================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "⭐ Telegram Premium sotib olish uchun paketni tanlang:\n\n"
        "⭐ 3 oy — 150 000 so'm\n"
        "⭐ 6 oy — 200 000 so'm\n"
        "⭐ 12 oy — 289 000 so'm",
        reply_markup=premium_keyboard(),
    )


# =========================
# PAKET TANLASH
# =========================

@dp.callback_query(F.data.in_(PLANS.keys()))
async def choose_plan(callback: CallbackQuery):
    plan_key = callback.data
    plan = PLANS[plan_key]

    await callback.answer()

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=plan["name"],
        description=(
            f"Telegram Premium {plan['months']} oy.\n"
            f"Narxi: {plan['price_text']}"
        ),
        payload=plan_key,
        provider_token="",
        currency="XTR",
        prices=[
            LabeledPrice(
                label=plan["name"],
                amount=plan["sell_stars"],
            )
        ],
    )


# =========================
# PRE-CHECKOUT
# =========================

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    plan = PLANS.get(query.invoice_payload)

    if not plan:
        await query.answer(
            ok=False,
            error_message="Buyurtma topilmadi."
        )
        return

    if query.currency != "XTR":
        await query.answer(
            ok=False,
            error_message="To'lov valyutasi noto'g'ri."
        )
        return

    if query.total_amount != plan["sell_stars"]:
        await query.answer(
            ok=False,
            error_message="To'lov summasi noto'g'ri."
        )
        return

    await query.answer(ok=True)


# =========================
# TO'LOV MUVAFFAQIYATLI
# =========================

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payment = message.successful_payment

    plan_key = payment.invoice_payload
    plan = PLANS.get(plan_key)

    if not plan:
        await message.answer(
            "⚠️ To'lov qabul qilindi, lekin paket aniqlanmadi.\n"
            "Admin bilan bog'laning."
        )
        return

    charge_id = payment.telegram_payment_charge_id

    # Bir xil to'lovni ikkinchi marta qayta ishlamaslik
    existing = db.execute(
        """
        SELECT id FROM orders
        WHERE telegram_charge_id = ?
        """,
        (charge_id,),
    ).fetchone()

    if existing:
        await message.answer(
            "ℹ️ Bu to'lov allaqachon qayta ishlangan."
        )
        return

    user_id = message.from_user.id
    username = message.from_user.username

    save_order(
        user_id=user_id,
        username=username,
        plan_key=plan_key,
        months=plan["months"],
        paid_stars=plan["sell_stars"],
        charge_id=charge_id,
        status="PAYMENT_RECEIVED",
    )

    try:
        # Telegram Premium'ni avtomatik yuborish
        result = await bot.gift_premium_subscription(
            user_id=user_id,
            month_count=plan["months"],
            star_count=plan["cost_stars"],
            text=f"🎁 Telegram Premium — {plan['months']} oy",
        )

        if result:
            db.execute(
                """
                UPDATE orders
                SET status = ?
                WHERE telegram_charge_id = ?
                """,
                ("PREMIUM_SENT", charge_id),
            )
            db.commit()

            await message.answer(
                "✅ To'lov muvaffaqiyatli!\n\n"
                f"🎁 Telegram Premium {plan['months']} oyga "
                "avtomatik yuborildi.\n\n"
                "⭐ Xaridingiz uchun rahmat!"
            )

            # Admin xabari
            if ADMIN_ID:
                try:
                    await bot.send_message(
                        int(ADMIN_ID),
                        "💰 YANGI BUYURTMA\n\n"
                        f"👤 User ID: {user_id}\n"
                        f"👤 Username: @{username or 'yo‘q'}\n"
                        f"📦 Paket: {plan['months']} oy\n"
                        f"💳 To'lov: {plan['sell_stars']} ⭐\n"
                        f"🎁 Xarajat: {plan['cost_stars']} ⭐\n"
                        "✅ Premium yuborildi."
                    )
                except Exception:
                    logging.exception("Admin xabarini yuborishda xato")

        else:
            raise RuntimeError("Premium yuborish muvaffaqiyatsiz")

    except Exception:
        logging.exception("Premium yuborishda xatolik")

        db.execute(
            """
            UPDATE orders
            SET status = ?
            WHERE telegram_charge_id = ?
            """,
            ("PREMIUM_SEND_ERROR", charge_id),
        )
        db.commit()

        await message.answer(
            "✅ To'lovingiz qabul qilindi.\n\n"
            "⏳ Premium yuborishda texnik muammo yuz berdi.\n"
            "Buyurtmangiz saqlandi va admin tekshiradi."
        )

        if ADMIN_ID:
            try:
                await bot.send_message(
                    int(ADMIN_ID),
                    "🚨 PREMIUM YUBORISHDA XATO!\n\n"
                    f"User ID: {user_id}\n"
                    f"Username: @{username or 'yo‘q'}\n"
                    f"Paket: {plan['months']} oy\n"
                    f"To'lov: {plan['sell_stars']} ⭐\n"
                    f"Charge ID: {charge_id}"
                )
            except Exception:
                logging.exception("Admin xabarini yuborishda xato")


# =========================
# BOTNI ISHGA TUSHIRISH
# =========================

async def main():
    me = await bot.get_me()

    logging.info(
        "Bot ishga tushdi: @%s",
        me.username
    )

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types()
    )


if __name__ == "__main__":
    asyncio.run(main())
