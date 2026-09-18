import os
import sqlite3
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
)

# =========================================================
# SOZLAMALAR
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi!")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =========================================================
# PAKETLAR
# =========================================================

PACKAGES = {
    "premium_3": {
        "months": 3,
        "display_price": "110 000 so'm",
        "customer_stars": 1100,
        "gift_stars": 1000,
    },
    "premium_6": {
        "months": 6,
        "display_price": "160 000 so'm",
        "customer_stars": 1600,
        "gift_stars": 1500,
    },
    "premium_12": {
        "months": 12,
        "display_price": "260 000 so'm",
        "customer_stars": 2600,
        "gift_stars": 2500,
    },
}

# =========================================================
# DATABASE
# =========================================================

DB_NAME = "payments.db"

db = sqlite3.connect(DB_NAME)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    package TEXT NOT NULL,
    months INTEGER NOT NULL,
    stars INTEGER NOT NULL,
    charge_id TEXT UNIQUE,
    status TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()


# =========================================================
# PAKETLAR KLAVIATURASI
# =========================================================

def packages_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ Premium 3 oy — 110 000 so'm",
                    callback_data="premium_3"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Premium 6 oy — 160 000 so'm",
                    callback_data="premium_6"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Premium 12 oy — 260 000 so'm",
                    callback_data="premium_12"
                )
            ],
        ]
    )


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message):

    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "⭐ Telegram Premium sotib olish uchun paketni tanlang:\n\n"
        "⭐ 3 oy — 110 000 so'm\n"
        "⭐ 6 oy — 160 000 so'm\n"
        "⭐ 12 oy — 260 000 so'm\n\n"
        "👇 Paketni tanlang:",
        reply_markup=packages_keyboard()
    )


# =========================================================
# PAKET TANLASH
# =========================================================

@dp.callback_query(F.data.in_(PACKAGES.keys()))
async def select_package(callback: CallbackQuery):

    package_id = callback.data
    package = PACKAGES[package_id]

    months = package["months"]
    stars = package["customer_stars"]

    await callback.answer()

    await callback.message.answer(
        f"⭐ Telegram Premium — {months} oy\n\n"
        f"💰 Narx: {package['display_price']}\n"
        f"⭐ To'lov: {stars} Telegram Stars\n\n"
        f"👇 To'lovni amalga oshiring."
    )

    # Telegram Stars invoice
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Telegram Premium {months} oy",
        description=(
            f"Telegram Premium {months} oylik obuna."
        ),
        payload=f"premium:{package_id}:{callback.from_user.id}",
        provider_token="",
        currency="XTR",
        prices=[
            LabeledPrice(
                label=f"Premium {months} oy",
                amount=stars
            )
        ],
    )


# =========================================================
# PRE-CHECKOUT
# =========================================================

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):

    payload = pre_checkout_query.invoice_payload

    if not payload.startswith("premium:"):
        await pre_checkout_query.answer(
            ok=False,
            error_message="Buyurtma topilmadi."
        )
        return

    parts = payload.split(":")

    if len(parts) != 3:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Buyurtma ma'lumotlari noto'g'ri."
        )
        return

    package_id = parts[1]
    user_id = int(parts[2])

    if package_id not in PACKAGES:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Paket topilmadi."
        )
        return

    # Foydalanuvchi boshqa invoice narxini o'zgartirib yubormasligi uchun
    expected_stars = PACKAGES[package_id]["customer_stars"]

    if pre_checkout_query.total_amount != expected_stars:
        await pre_checkout_query.answer(
            ok=False,
            error_message="To'lov summasi noto'g'ri."
        )
        return

    if pre_checkout_query.from_user.id != user_id:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Buyurtma foydalanuvchiga mos kelmaydi."
        )
        return

    await pre_checkout_query.answer(ok=True)


# =========================================================
# TO'LOV MUVAFFAQIYATLI BO'LGANDA
# =========================================================

@dp.message(F.successful_payment)
async def successful_payment(message: Message):

    payment = message.successful_payment

    payload = payment.invoice_payload

    if not payload.startswith("premium:"):
        return

    parts = payload.split(":")

    if len(parts) != 3:
        return

    package_id = parts[1]
    user_id = int(parts[2])

    if package_id not in PACKAGES:
        return

    package = PACKAGES[package_id]

    months = package["months"]
    paid_stars = payment.total_amount
    charge_id = payment.telegram_payment_charge_id

    # Bir xil to'lovni ikki marta ishlatmaslik
    cursor.execute(
        "SELECT id FROM payments WHERE charge_id = ?",
        (charge_id,)
    )

    existing = cursor.fetchone()

    if existing:
        await message.answer(
            "✅ Bu to'lov allaqachon qayta ishlangan."
        )
        return

    # Avval to'lovni bazaga yozamiz
    cursor.execute(
        """
        INSERT INTO payments
        (user_id, package, months, stars, charge_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            package_id,
            months,
            paid_stars,
            charge_id,
            "paid"
        )
    )

    db.commit()

    # =====================================================
    # PREMIUM BERISH
    # =====================================================

    try:

        result = await bot.gift_premium_subscription(
            user_id=user_id,
            month_count=months,
            star_count=package["gift_stars"],
            text=f"⭐ {months} oylik Telegram Premium"
        )

        if result:

            cursor.execute(
                """
                UPDATE payments
                SET status = ?
                WHERE charge_id = ?
                """,
                ("premium_sent", charge_id)
            )

            db.commit()

            await message.answer(
                f"✅ To'lov muvaffaqiyatli!\n\n"
                f"⭐ Telegram Premium {months} oyga yuborildi.\n"
                f"💳 To'langan: {paid_stars} Stars\n\n"
                f"Rahmat! 🙏"
            )

            # Admin xabari
            if ADMIN_ID:
                await bot.send_message(
                    ADMIN_ID,
                    "💰 YANGI TO'LOV\n\n"
                    f"👤 User ID: {user_id}\n"
                    f"⭐ Paket: {months} oy\n"
                    f"💳 To'lov: {paid_stars} Stars\n"
                    f"🧾 Charge ID: {charge_id}\n"
                    f"✅ Premium yuborildi."
                )

    except Exception as e:

        logging.exception("Premium yuborishda xato")

        cursor.execute(
            """
            UPDATE payments
            SET status = ?
            WHERE charge_id = ?
            """,
            ("paid_pending", charge_id)
        )

        db.commit()

        await message.answer(
            "✅ To'lovingiz qabul qilindi.\n\n"
            "⚠️ Premium yuborishda texnik xatolik yuz berdi.\n"
            "Admin tez orada tekshiradi."
        )

        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                "🚨 MUAMMO!\n\n"
                f"👤 User ID: {user_id}\n"
                f"⭐ Paket: {months} oy\n"
                f"💳 To'lov: {paid_stars} Stars\n"
                f"🧾 Charge ID: {charge_id}\n\n"
                f"❌ Premium yuborilmadi.\n"
                f"Xato: {e}"
            )


# =========================================================
# PAYMENT SUPPORT
# =========================================================

@dp.message(Command("paysupport"))
async def pay_support(message: Message):

    await message.answer(
        "💳 To'lov bo'yicha yordam kerak bo'lsa,\n"
        "admin bilan bog'laning."
    )


# =========================================================
# ISHGA TUSHIRISH
# =========================================================

async def main():

    print("🤖 Bot ishga tushdi...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
