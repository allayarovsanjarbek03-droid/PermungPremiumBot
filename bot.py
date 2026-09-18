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
        "name": "Telegram Premium — 3 oy",
        "stars": 150,
    },
    "6": {
        "name": "Telegram Premium — 6 oy",
        "stars": 200,
    },
    "12": {
        "name": "Telegram Premium — 12 oy",
        "stars": 289,
    },
}


def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ Premium 3 oy",
                    callback_data="premium_3"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Premium 6 oy",
                    callback_data="premium_6"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Premium 12 oy",
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
        "Telegram Premium paketini tanlang:",
        reply_markup=main_menu()
    )


# =========================
# INVOICE
# =========================

@dp.callback_query(F.data.startswith("premium_"))
async def premium_callback(callback: CallbackQuery):

    months = callback.data.split("_")[1]
    package = PACKAGES[months]

    prices = [
        LabeledPrice(
            label=package["name"],
            amount=package["stars"]
        )
    ]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=package["name"],
        description=f"Telegram Premium — {months} oy",
        payload=f"premium_{months}_{callback.from_user.id}",
        provider_token="",
        currency="XTR",
        prices=prices,
    )

    await callback.answer()


# =========================
# PRE-CHECKOUT
# =========================

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):

    await pre_checkout_query.answer(
        ok=True
    )


# =========================
# SUCCESSFUL PAYMENT
# =========================

@dp.message(F.successful_payment)
async def successful_payment(message: Message):

    payment = message.successful_payment

    payload = payment.invoice_payload

    await message.answer(
        "✅ To‘lov muvaffaqiyatli qabul qilindi!\n\n"
        "⭐ Premium buyurtmangiz qabul qilindi.\n"
        "Admin siz bilan bog‘lanadi."
    )

    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            "💰 YANGI TO‘LOV!\n\n"
            f"👤 Foydalanuvchi: "
            f"{message.from_user.full_name}\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"📦 Buyurtma: {payload}\n"
            f"⭐ Summa: {payment.total_amount} Stars\n"
            f"💳 Payment ID: "
            f"{payment.telegram_payment_charge_id}"
        )


# =========================
# RUN
# =========================

async def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN GitHub Secrets ichida mavjud emas."
        )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
