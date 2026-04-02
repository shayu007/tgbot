from flask import Flask
from threading import Thread
import time
import telebot
from telebot import types
import os

print("=" * 50)
print("🚀 投稿机器人启动中...（Railway + 菜单管理目标群）")
print("=" * 50)

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running 24/7 on Railway!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

# ================== 配置 ==================
BOT_TOKEN = "8640961726:AAEtYBHxk_y_TzfNENGxd_flCpcIQd8hVnU"
REVIEW_GROUP_ID = -1003839457254
ADMIN_ID = 2120267316

# 优先从 Railway 环境变量读取（推荐方式）
TARGET_CHANNEL_ID = os.environ.get("TARGET_CHANNEL_ID")
if TARGET_CHANNEL_ID:
    try:
        TARGET_CHANNEL_ID = int(TARGET_CHANNEL_ID)
        print(f"✅ 从环境变量加载目标群: {TARGET_CHANNEL_ID}")
    except:
        TARGET_CHANNEL_ID = None
else:
    TARGET_CHANNEL_ID = None

bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)
user_data = {}

# ================== 设置菜单（仅管理员可用） ==================
@bot.message_handler(commands=['settings'])
def settings_menu(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ 你没有权限使用设置菜单")
        return

    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("📍 查看当前目标群", callback_data="view_target"))
    mk.add(types.InlineKeyboardButton("✏️ 设置新目标群ID", callback_data="set_target"))

    current = TARGET_CHANNEL_ID if TARGET_CHANNEL_ID else "未设置"
    text = (
        f"⚙️ **目标群管理菜单**\n\n"
        f"当前发布目标群/频道：\n"
        f"`{current}`\n\n"
        f"• 设置后，审核通过会自动发布到该群\n"
        f"• 推荐在 Railway 添加环境变量 `TARGET_CHANNEL_ID`（更稳定）"
    )

    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=mk)

# 查看当前目标群
@bot.callback_query_handler(func=lambda c: c.data == "view_target")
def view_target(c):
    if c.from_user.id != ADMIN_ID:
        return
    current = TARGET_CHANNEL_ID if TARGET_CHANNEL_ID else "未设置"
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, f"📍 当前目标群ID：\n`{current}`", parse_mode="Markdown")

# 开始设置新目标群
@bot.callback_query_handler(func=lambda c: c.data == "set_target")
def start_set_target(c):
    if c.from_user.id != ADMIN_ID:
        return
    bot.answer_callback_query(c.id)
    bot.send_message(
        c.message.chat.id,
        "请输入新的**目标群/频道 ID**（必须以 -100 开头）：\n\n"
        "示例：`-1001234567890`\n"
        "发送 /cancel 取消设置"
    )
    user_data[c.from_user.id] = {"step": "waiting_target_id"}

# 处理输入的目标群ID
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_data.get(m.from_user.id, {}).get("step") == "waiting_target_id")
def set_target_id(message):
    global TARGET_CHANNEL_ID
    try:
        new_id = int(message.text.strip())
        if not str(new_id).startswith("-100"):
            bot.send_message(message.chat.id, "❌ 错误！目标群ID必须以 `-100` 开头，请重新输入。")
            return

        TARGET_CHANNEL_ID = new_id
        bot.send_message(
            message.chat.id,
            f"✅ 设置成功！\n\n新目标群ID：`{new_id}`\n\n"
            f"审核通过后将自动发布到此群。\n"
            f"注意：Railway 重启后会恢复为环境变量的值。\n"
            f"建议直接在 Railway Variables 中添加 `TARGET_CHANNEL_ID` = `{new_id}`",
            parse_mode="Markdown"
        )
        del user_data[message.from_user.id]

    except ValueError:
        bot.send_message(message.chat.id, "❌ 输入格式错误，请输入纯数字（如 -1001234567890）")

# ================== 投稿流程（简化稳定版） ==================
@bot.message_handler(commands=['start', 'post'])
def start(message):
    user_id = message.from_user.id
    user_data[user_id] = {"step": "anon"}

    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("🕵 匿名投稿", callback_data="anon_yes"))
    mk.add(types.InlineKeyboardButton("🔍 实名投稿", callback_data="anon_no"))
    bot.send_message(message.chat.id, "👋 欢迎使用投稿机器人！\n\n请选择投稿方式：", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("anon_"))
def set_anon(c):
    user_id = c.from_user.id
    user_data[user_id]["anon"] = (c.data == "anon_yes")
    user_data[user_id]["step"] = "gender"
    bot.send_message(c.message.chat.id, "请输入你的**性别**：")

@bot.message_handler(content_types=['text'])
def text_step(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        return
    step = user_data[user_id].get("step")
    text = message.text.strip()

    if step == "gender":
        user_data[user_id]["gender"] = text
        user_data[user_id]["step"] = "age"
        bot.send_message(message.chat.id, "请输入你的**年龄**：")
    elif step == "age":
        user_data[user_id]["age"] = text
        user_data[user_id]["step"] = "attr"
        bot.send_message(message.chat.id, "请输入你的**属性**：")
    elif step == "attr":
        user_data[user_id]["attr"] = text
        user_data[user_id]["step"] = "city"
        bot.send_message(message.chat.id, "请输入你的**地区**：")
    elif step == "city":
        user_data[user_id]["city"] = text
        user_data[user_id]["step"] = "media"
        user_data[user_id]["media"] = []
        bot.send_message(message.chat.id, "✅ 信息填写完成！\n现在发送图片或视频（可多条），全部发完后输入**投稿宣言**：")
    elif step == "declaration":
        user_data[user_id]["declaration"] = text
        user_data[user_id]["step"] = "confirm"
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("✅ 提交审核", callback_data="done"))
        bot.send_message(message.chat.id, "✅ 宣言已记录！点击下方按钮提交审核。", reply_markup=mk)

@bot.message_handler(content_types=['photo', 'video'])
def catch_media(message):
    user_id = message.from_user.id
    if user_id not in user_data or user_data[user_id].get("step") != "media":
        return
    if "media" not in user_data[user_id]:
        user_data[user_id]["media"] = []
    user_data[user_id]["media"].append(message)
    bot.send_message(message.chat.id, f"✅ 已接收第 {len(user_data[user_id]['media'])} 个媒体\n继续发送或直接输入投稿宣言：")

# ================== 提交审核 ==================
@bot.callback_query_handler(func=lambda c: c.data == "done")
def done(c):
    user_id = c.from_user.id
    if user_id not in user_data or not user_data[user_id].get("media"):
        bot.send_message(c.message.chat.id, "❌ 请至少发送一张图片或视频！")
        return

    data = user_data[user_id]
    declaration = data.get("declaration", "未填写宣言")

    try:
        group_media = []
        info = (
            f"📥 新投稿\n"
            f"匿名：{'是' if data.get('anon') else '否'}\n"
            f"性别：{data.get('gender', '未填')}\n"
            f"年龄：{data.get('age', '未填')}\n"
            f"属性：{data.get('attr', '未填')}\n"
            f"地区：{data.get('city', '未填')}\n"
            f"用户ID：{user_id}\n\n"
            f"投稿宣言：\n{declaration}"
        )

        for i, msg in enumerate(data["media"]):
            if msg.content_type == 'photo':
                item = types.InputMediaPhoto(msg.photo[-1].file_id)
            elif msg.content_type == 'video':
                item = types.InputMediaVideo(msg.video.file_id)
            else:
                continue
            if i == 0:
                item.caption = info
            group_media.append(item)

        bot.send_media_group(REVIEW_GROUP_ID, group_media)

        mk = types.InlineKeyboardMarkup()
        mk.row(
            types.InlineKeyboardButton("✅ 通过并发布", callback_data=f"ok_{user_id}"),
            types.InlineKeyboardButton("❌ 拒绝", callback_data=f"no_{user_id}")
        )
        bot.send_message(REVIEW_GROUP_ID, "⏳ 新投稿等待审核", reply_markup=mk)

        bot.send_message(c.message.chat.id, "✅ 投稿已提交审核！")
        del user_data[user_id]

    except Exception as e:
        bot.send_message(c.message.chat.id, "❌ 提交失败，请重试")
        print("提交错误:", e)

# ================== 审核 + 发布到目标群 ==================
@bot.callback_query_handler(func=lambda c: c.data.startswith(("ok_", "no_")))
def review(c):
    if c.from_user.id != ADMIN_ID:
        bot.answer_callback_query(c.id, "❌ 无权限")
        return

    act, uid_str = c.data.split("_")
    uid = int(uid_str)

    try:
        if act == "ok":
            bot.edit_message_text("✅ 已通过并发布", c.message.chat.id, c.message.message_id)
            bot.send_message(uid, "🎉 恭喜！你的投稿已通过审核并发布！")

            if TARGET_CHANNEL_ID:
                bot.forward_message(
                    chat_id=TARGET_CHANNEL_ID,
                    from_chat_id=REVIEW_GROUP_ID,
                    message_id=c.message.message_id - 1   # 媒体组通常在按钮消息前一条
                )
                print(f"✅ 投稿已发布到目标群 {TARGET_CHANNEL_ID}")
            else:
                bot.send_message(REVIEW_GROUP_ID, "⚠️ 目标群未设置！请用 /settings 设置或在 Railway 添加环境变量 TARGET_CHANNEL_ID")
        else:
            bot.edit_message_text("❌ 已拒绝", c.message.chat.id, c.message.message_id)
            bot.send_message(uid, "😔 很遗憾，你的投稿未通过审核。")
    except Exception as e:
        print("发布错误:", e)
        bot.send_message(ADMIN_ID, f"⚠️ 发布失败：{str(e)}")

# ================== 取消 ==================
@bot.message_handler(commands=['cancel'])
def cancel(message):
    user_id = message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    bot.send_message(message.chat.id, "✅ 已取消当前操作。")

# ================== 启动 ==================
def run_bot():
    while True:
        try:
            print("🤖 机器人运行中... 发送 /settings 管理目标群")
            bot.polling(non_stop=True, interval=0, timeout=30)
        except Exception as e:
            print("Polling 异常，重启中...", e)
            time.sleep(8)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    time.sleep(2)
    run_bot()