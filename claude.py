import os
import pdb
from anthropic import AsyncAnthropic
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters


client = AsyncAnthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)
USER_IDS = os.getenv("USER_IDS").split(",")
USER_IDS = [int(user_id) for user_id in USER_IDS]
MODEL = "claude-3-sonnet-20240229"
max_tokens = 1024
CONCAT_SYMBOL = " || LCG || \n"


def check_user(func):
    async def wrapper(*args, **kwargs):
        update = args[0]
        if os.getenv("DEBUG"):
            print(update.message.chat.id)
        if update.message.chat.id in USER_IDS:
            result = await func(*args, **kwargs)
            return result
        return await update.message.reply_text(f"WRONG USER: {update.message.chat.id}")

    return wrapper


async def request(messages, model):
    if os.getenv("DEBUG"):
        return "DEBUG"
    chat_completion = await client.messages.create(model=MODEL, max_tokens=max_tokens, messages=messages)
    result = ""
    for content in chat_completion.content:
        result += content.text
    return result


async def reply(content, update):
    MAX_LENGTH = 4096
    length = len(content)
    if length < MAX_LENGTH:
        await update.message.reply_text(content, reply_to_message_id=update.message.message_id)
    else:
        content = content.split(CONCAT_SYMBOL)[-1]
        for i in range(0, len(content), MAX_LENGTH):
            await update.message.reply_text(content[i : i + MAX_LENGTH])


# ----- START GPT Function -----


async def gpt(question, user_data):
    topic = user_data.get("topic")
    model = user_data.get("model", MODEL)
    msgs = [{"role": "user", "content": question}]
    if topic:
        msgs[-1]["content"] = f"你是{topic}领域专家，{question}"
    return await request(msgs, model)


async def gpt_with_history(question, history, user_data):
    topic = user_data.get("topic")
    model = user_data.get("model", MODEL)
    history_ = history.split(CONCAT_SYMBOL)
    msgs = [
        {"role": "user", "content": history_[0]},
        {"role": "assistant", "content": history_[1]},
        {"role": "user", "content": question},
    ]
    if topic:
        msgs[-1]["content"] = f"你是{topic}领域专家，{question}"
    return await request(msgs, model)


async def gpt_translate(question, user_data):
    model = user_data.get("model", MODEL)
    msgs = [{"role": "user", "content": question}]
    msgs[-1]["content"] = f"你是一个中英、英中翻译机器人，翻译以下内容：{question}"
    return await request(msgs, model)


async def gpt_code(question, user_data):
    topic = user_data.get("topic")
    model = user_data.get("model", MODEL)
    msgs = [{"role": "user", "content": question}]
    msgs[-1]["content"] = f"你是{topic}领域专家，讲解以下代码：{question}"
    return await request(msgs, model)


async def gpt_eng(question, user_data):
    model = user_data.get("model", MODEL)
    msgs = [{"role": "user", "content": question}]
    msgs[-1]["content"] = f"我希望你能扮演一位英语老师和改进者的角色。介绍一下以下词或句子的基本英语语法规则和用法，并提供例句和练习题。{question}"
    return await request(msgs, model)


# ----- END GPT Function -----


# ----- START Callback Function -----


@check_user
async def topic_callback(update, context):
    msg = update.message.text.lstrip("/tp").strip()
    user_data = context.user_data
    user_data["topic"] = msg
    await update.message.reply_text(f"TOPIC = {msg}")


@check_user
async def clear_callback(update, context):
    msg = update.message.text.lstrip("/c").strip()
    context.user_data["topic"] = None
    if msg:
        content = await gpt(msg, context.user_data)
    else:
        content = "TOPIC was Cleared."
    await update.message.reply_text(content)


@check_user
async def translate_callback(update, context):
    msg = update.message.text.lstrip("/t").strip()
    content = await gpt_translate(msg.strip(), context.user_data)
    await update.message.reply_text(content, reply_to_message_id=update.message.message_id)


@check_user
async def code_callback(update, context):
    msg = update.message.text.lstrip("/code")
    user_data = context.user_data
    content = await gpt_code(msg, context.user_data)
    await update.message.reply_text(content, reply_to_message_id=update.message.message_id)


@check_user
async def eng_callback(update, context):
    msg = update.message.text.lstrip("/eng").strip()
    user_data = context.user_data
    content = await gpt_eng(msg, context.user_data)
    await update.message.reply_text(content, reply_to_message_id=update.message.message_id)


@check_user
async def general_callback(update, context):
    msg = update.message.text.strip()
    user_data = context.user_data
    if update.message.reply_to_message:
        content = await gpt_with_history(msg, update.message.reply_to_message.text, context.user_data)
    else:
        content = await gpt(msg, context.user_data)
    await reply(f"{msg}{CONCAT_SYMBOL}{content}", update)


@check_user
async def version_callback(update, context):
    content = "NOT SUPPORT!"
    await update.message.reply_text(content, reply_to_message_id=update.message.message_id)


@check_user
async def introduction_callback(update, context):
    msg = update.message.text.lstrip("/i").strip()
    msg = f"详细讲解一下{msg}"
    user_data = context.user_data
    if update.message.reply_to_message:
        content = await gpt_with_history(msg, update.message.reply_to_message.text, context.user_data)
    else:
        content = await gpt(msg, context.user_data)
    await reply(f"{msg}{CONCAT_SYMBOL}{content}", update)


# ----- END Callback Function -----


def main() -> None:
    application = Application.builder().token(os.environ.get("BOT_TOKEN_CLUADE")).build()
    application.add_handler(CommandHandler("tp", topic_callback))
    application.add_handler(CommandHandler("c", clear_callback))
    application.add_handler(CommandHandler("t", translate_callback))
    application.add_handler(CommandHandler("code", code_callback))
    application.add_handler(CommandHandler("eng", eng_callback))
    application.add_handler(CommandHandler("v", version_callback))
    application.add_handler(CommandHandler("i", introduction_callback))
    application.add_handler(MessageHandler(filters.TEXT, general_callback))
    application.run_polling()


if __name__ == "__main__":
    main()
