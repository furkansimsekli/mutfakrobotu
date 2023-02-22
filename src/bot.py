import logging

import openai
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

from .config import TELEGRAM_API_KEY, WEBHOOK_CONNECTED, PORT, WEBHOOK_URL, OPEN_AI_TOKEN

# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger()

# Global Variables
ACTOR: str = ""
ENGINE = {
    "Davinci": "text-davinci-003",
    "Curie": "text-curie-001",
    "Babbage": "text-babbage-001",
    "Ada": "text-ada-001"
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_user.id,
                                   text="Hello there!\n\n"
                                        "See /help if you want")


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=update.effective_user.id,
                                   text="/chat   -->   Talk to wise people around the world")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_markup = create_keyboard(["Davinci", "Curie", "Babbage", "Ada"])
    await context.bot.send_message(chat_id=update.effective_user.id,
                                   text="Choose someone to talk to...\n"
                                        "If you don't want to speak, say /cancel",
                                   reply_markup=reply_markup)
    return 1


async def choose_actor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global ACTOR
    ACTOR = update.message.text
    await context.bot.send_message(chat_id=update.effective_user.id,
                                   text="Tell me dear!\n"
                                        "If you don't want to speak, say /cancel",
                                   reply_markup=ReplyKeyboardRemove())
    return 2


async def interact_with_actor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        response = openai.Completion.create(
            engine=ENGINE[ACTOR],
            prompt=update.message.text,
            temperature=0.5,
            max_tokens=256,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        answer = response["choices"][0]['text'].strip()
        logging.info(f"Question: {update.message.text}\nAnswer: {answer}\nActor: {ENGINE[ACTOR]}")
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text=answer,
                                       reply_markup=ReplyKeyboardRemove())
        return 2
    except openai.error.RateLimitError:
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="OpenAI quote has been exceeded, please contact to developer!")
        return -1
    except openai.error.APIError:
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="Internal Server Error - OpenAI\n"
                                            "Try again!")
        return 2


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_message(chat_id=update.effective_user.id,
                                   text="Process has been canceled!")
    return -1


async def timeout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id=update.effective_user.id,
                                   text="Timeout! Conversation has added.",
                                   reply_markup=ReplyKeyboardRemove())


# Utils
def create_keyboard(people_list: list[str]):
    buttons = [[KeyboardButton(elem)] for elem in people_list]
    return ReplyKeyboardMarkup(buttons)


def main() -> None:
    app: Application = Application.builder().token(TELEGRAM_API_KEY).build()
    openai.api_key = OPEN_AI_TOKEN

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("chat", chat)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_actor)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, interact_with_actor)],
            ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout_callback)]
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("chat", chat)],
        conversation_timeout=300
    ))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))

    if WEBHOOK_CONNECTED:
        app.run_webhook(listen="0.0.0.0",
                        port=int(PORT),
                        url_path=TELEGRAM_API_KEY,
                        webhook_url=WEBHOOK_URL)
    else:
        app.run_polling()


if __name__ == "__main__":
    main()
