from flask import Flask
from threading import Thread
import time
import telebot
from telebot import types
import os
import sys

print("="*50)
print("🚀 完整版机器人启动中...")
print("版本：完整投稿机器人（含年龄/性别/图片视频捕获）")
print("="*50)

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================== 你的配置 ==================
BOT_TOKEN = "8640961726:AAEtYBHxk_y_TzfNENGxd_flCpcIQd8hVnU"
REVIEW_GROUP_ID = -1003839457254
ADMIN_ID = 2120267316

bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)
user_data = {}
submissions = {}

# ================== /start ==================
@bot.message_handler(commands=['start', 'post'])
def start(message):
    user_id = message.from_user.id
    user_data[user_id] = {"step": "anon"}

    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🕵 匿名", callback_data="anon_yes"))
    mk.add(types.InlineKeyboardButton("🔍 实名", callback_data="anon_no"))
    bot.send_message(message.chat.id, "你要匿名投稿吗？", reply_markup=mk)

# ================== 匿名选择 ==================
@bot.callback_query_handler(func=lambda c: c.data.startswith("anon_"))
def set_anon(c):
    user_id = c.from_user.id
    user_data[user_id]["anon"] = c.data
    user_data[user_id]["step"] = "gender"
    bot.send_message(c.message.chat.id, "请输入你的性别：")

# ================== 文字输入流程 ==================
@bot.message_handler(content_types=['text'])
def text_step(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        return

    step = user_data[user_id]["step"]
    text = message.text.strip()

    if step == "gender":
        user_data[user_id]["gender"] = text
        user_data[user_id]["step"] = "age"
        bot.send_message(message.chat.id, "请输入年龄：")

    elif step == "age":
        user_data[user_id]["age"] = text
        user_data[user_id]["step"] = "attr"
        bot.send_message(message.chat.id, "请输入属性：")

    elif step == "attr":
        user_data[user_id]["attr"] = text
        user_data[user_id]["step"] = "city"
        bot.send_message(message.chat.id, "请输入地区：")

    elif step == "city":
        user_data[user_id]["city"] = text
        user_data[user_id]["step"] = "media"
        bot.send_message(message.chat.id, "✅ 信息填写完成！\n现在发送**图片或视频**，发完点【完成投稿】按钮")

        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("✅ 完成投稿", callback_data="done"))
        bot.send_message(message.chat.id, "点击完成", reply_markup=mk)

# ================== 捕获 图片 / 视频 ==================
@bot.message_handler(content_types=['photo', 'video'])
def catch_media(message):
    user_id = message.from_user.id
    if user_id not in user_data or user_data[user_id]["step"] != "media":
        return

    if "media" not in user_data[user_id]:
        user_data[user_id]["media"] = []

    user_data[user_id]["media"].append(message)
    bot.send_message(message.chat.id, f"✅ 已接收媒体：{len(user_data[user_id]['media'])} 个")

# ================== 完成投稿 ==================
@bot.callback_query_handler(func=lambda c: c.data == "done")
def done(c):
    user_id = c.from_user.id
    if user_id not in user_data or "media" not in user_data[user_id]:
        bot.send_message(c.message.chat.id, "❌ 请先发送图片/视频！")
        return

    data = user_data[user_id]
    media_list = data["media"]

    # 发送到审核群
    try:
        group_msg = []
        for m in media_list:
            if m.photo:
                group_msg.append(types.InputMediaPhoto(m.photo[-1].file_id))
            if m.video:
                group_msg.append(types.InputMediaVideo(m.video.file_id))

        info = (
            f"📥 新投稿\n"
            f"匿名：{'是' if data['anon'] == 'anon_yes' else '否'}\n"
            f"性别：{data['gender']}\n"
            f"年龄：{data['age']}\n"
            f"属性：{data['attr']}\n"
            f"地区：{data['city']}"
        )

        if group_msg:
            group_msg[0].caption = info
            bot.send_media_group(REVIEW_GROUP_ID, group_msg)

        # 审核按钮
        mk = types.InlineKeyboardMarkup()
        mk.row(
            types.InlineKeyboardButton("✅ 通过", callback_data=f"ok_{user_id}"),
            types.InlineKeyboardButton("❌ 拒绝", callback_data=f"no_{user_id}")
        )
        bot.send_message(REVIEW_GROUP_ID, "⏳ 等待审核", reply_markup=mk)
        bot.send_message(c.message.chat.id, "✅ 投稿成功！等待审核")

        del user_data[user_id]
    except Exception as e:
        bot.send_message(c.message.chat.id, "❌ 投稿失败")
        print(e)

# ================== 审核 ==================
@bot.callback_query_handler(func=lambda c: c.data.startswith(("ok_", "no_")))
def review(c):
    if c.from_user.id != ADMIN_ID:
        bot.answer_callback_query(c.id, "❌ 无权限")
        return

    act, uid = c.data.split("_")
    uid = int(uid)

    if act == "ok":
        bot.edit_message_text("✅ 已通过", c.message.chat.id, c.message.message_id)
        bot.send_message(uid, "✅ 你的投稿已通过！")
    else:
        bot.edit_message_text("❌ 已拒绝", c.message.chat.id, c.message.message_id)
        bot.send_message(uid, "❌ 你的投稿未通过")

# ================== 启动 ==================
def run_bot():
    while True:
        try:
            bot.polling(non_stop=True)
        except:
            time.sleep(2)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    time.sleep(1)
    run_bot()