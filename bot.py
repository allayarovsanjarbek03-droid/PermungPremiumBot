import os
import asyncio
import logging

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

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================
# PREMIUM PAKETLAR
# =========================

PACKAGES = {
    "3": {
        "name": "Telegram Premium 3 oy",
        "uzs": "150 000 so'm",
        "stars": 150,
    },
    "6": {
        "name": "Telegram Premium 6 oy",
        "uzs": "200 000 so'm",
        "stars": 200,
    },
    "12": {
        "name": "Telegram Premium 12 oy",
        "uzs": "289 000 so'm",
        "stars": 289,
    },
}


# =========================
# ASOSIY MENYU
# =========================

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ 3 oy — 150 000 so'm",
                    callback_data="premium_3"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ 6 oy — 200 000 so'm",
                    callback_data="premium_6"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ 12 oy — 289 000 so'm",
                    callback_data="premium_12"
                )
            ],
        ]
    )


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):

    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "⭐ Telegram Premium\n\n"
        "Kerakli paketni tanlang:",
        reply_markup=main_menu()
    )


# =========================
# PREMIUM TANLASH
# =========================

@dp.callback_query(F.data.startswith("premium_"))
async def premium_callback(callback: CallbackQuery):

    months = callback.data.split("_")[1]
    package = PACKAGES.get(months)

    if not package:
        await callback.answer("Paket topilmadi.", show_alert=True)
        return

    prices = [
        LabeledPrice(
            label=package["name"],
            amount=package["stars"]
        )
    ]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=package["name"],
        description=(
            f"{months} oylik Telegram Premium\n"
            f"Narxi: {package['uzs']}"
        ),
        payload=f"premium_{months}_{callback.from_user.id}",
        currency="XTR",
        prices=prices,
    )

    await callback.answer()


# =========================
# PRE-CHECKOUT
# =========================

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):

    await pre_checkout_query.answer(ok=True)


# =========================
# TO'LOV MUVAFFAQIYATLI
# =========================

@dp.message(F.successful_payment)
async def successful_payment(message: Message):

    payment = message.successful_payment

    payload = payment.invoice_payload

    await message.answer(
        "✅ To‘lov muvaffaqiyatli qabul qilindi!\n\n"
        "⭐ Buyurtmangiz qabul qilindi.\n"
        "Premium yetkazib berish jarayoni boshlanadi."
    )

    # ADMINGA XABAR

    if ADMIN_ID:

        await bot.send_message(
            ADMIN_ID,
            "💰 YANGI PREMIUM BUYURTMASI\n\n"
            f"👤 Ism: {message.from_user.full_name}\n"
            f"🆔 Telegram ID: {message.from_user.id}\n"
            f"📦 Buyurtma: {payload}\n"
            f"⭐ To‘lov: {payment.total_amount} Stars\n"
            f"💳 Payment ID:\n"
            f"{payment.telegram_payment_charge_id}"
        )


# =========================
# BOTNI ISHGA TUSHIRISH
# =========================

async def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN GitHub Secrets ichida mavjud emas."
        )

    if not ADMIN_ID:
        raise RuntimeError(
            "ADMIN_ID GitHub Secrets ichida mavjud emas."
        )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
