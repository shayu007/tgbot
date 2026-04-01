from flask import Flask
from threading import Thread
import time
import telebot
from telebot import types

app = Flask(__name__)

@app.route('/')
def index():
    return "Bot running"

def keep_alive():
    app.run(host="0.0.0.0", port=8080)

# 机器人配置
BOT_TOKEN = "你自己的机器人TOKEN"
REVIEW_GROUP_ID = -1003839457254
ADMIN_ID = 2120267316

bot = telebot.TeleBot(BOT_TOKEN)

# 开始
@bot.message_handler(commands=['start','post'])
def start(msg):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("✅ 我要投稿", callback_data="go"))
    bot.send_message(msg.chat.id, "点击投稿", reply_markup=mk)

# 进入投稿
@bot.callback_query_handler(func=lambda c:c.data=="go")
def go(c):
    bot.send_message(c.message.chat.id, "发送图片/视频，完成后点按钮：")
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("✅ 完成投稿", callback_data="done"))
    bot.send_message(c.message.chat.id, "点我完成", reply_markup=mk)

# 完成投稿 → 发审核群
@bot.callback_query_handler(func=lambda c:c.data=="done")
def done(c):
    bot.forward_message(REVIEW_GROUP_ID, c.message.chat.id, c.message.message_id-1)
    mk = types.InlineKeyboardMarkup()
    mk.row(
        types.InlineKeyboardButton("✅ 通过", callback_data="ok"),
        types.InlineKeyboardButton("❌ 拒绝", callback_data="no")
    )
    bot.send_message(REVIEW_GROUP_ID, "新投稿", reply_markup=mk)
    bot.send_message(c.message.chat.id, "✅ 投稿成功")

# 审核
@bot.callback_query_handler(func=lambda c:c.data in ["ok","no"])
def review(c):
    if c.from_user.id != ADMIN_ID:
        bot.answer_callback_query(c.id, "无权限")
        return
    if c.data == "ok":
        bot.edit_message_text("✅ 通过", c.message.chat.id, c.message.id)
    else:
        bot.edit_message_text("❌ 拒绝", c.message.chat.id, c.message.id)

# 启动
Thread(target=keep_alive, daemon=True).start()
print("机器人启动")
bot.infinity_polling()