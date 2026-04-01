from flask import Flask
from threading import Thread
import time
import telebot
from telebot import types
import os
import sys

# 强制输出日志，方便排查
print("="*50)
print("🚀 服务启动中...")
print(f"Python版本: {sys.version}")
print(f"当前目录: {os.getcwd()}")
print(f"目录文件: {os.listdir('.')}")
print("="*50)

# ================== 保活服务（Railway必须，防止休眠）===================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    print(f"✅ 保活服务启动，端口: {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

# ================== 机器人核心配置 ==================
# 【关键】这里填你自己的机器人Token！
BOT_TOKEN = "8640961726:AAEtYBHxk_y_TzfNENGxd_flCpcIQd8hVnU"
# 审核群ID
REVIEW_GROUP_ID = -1003839457254
# 管理员ID（你的Telegram ID）
ADMIN_ID = 2120267316

print(f"✅ 机器人Token: {BOT_TOKEN[:10]}...")
print(f"✅ 审核群ID: {REVIEW_GROUP_ID}")
print(f"✅ 管理员ID: {ADMIN_ID}")

# 初始化机器人
bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)

# ================== 核心命令：/start ==================
@bot.message_handler(commands=['start'])
def start(message):
    print(f"✅ 收到 /start，用户ID: {message.from_user.id}")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ 我要投稿", callback_data="start_post"))
    bot.send_message(
        message.chat.id,
        "👋 欢迎使用投稿机器人！点击下方按钮开始投稿",
        reply_markup=markup
    )

# ================== 投稿按钮 ==================
@bot.callback_query_handler(func=lambda call: call.data == "start_post")
def start_post(call):
    print(f"✅ 收到投稿请求，用户ID: {call.from_user.id}")
    done_markup = types.InlineKeyboardMarkup()
    done_markup.add(types.InlineKeyboardButton("✅ 完成投稿", callback_data="submit_done"))
    bot.send_message(
        call.message.chat.id,
        "请发送图片/视频，发送完成后点击下方「完成」按钮",
        reply_markup=done_markup
    )
    bot.answer_callback_query(call.id, "✅ 已进入投稿流程")

# ================== 完成投稿 & 发审核群 ==================
@bot.callback_query_handler(func=lambda call: call.data == "submit_done")
def submit_done(call):
    print(f"✅ 投稿完成，用户ID: {call.from_user.id}")
    # 发送到审核群
    bot.send_message(
        REVIEW_GROUP_ID,
        f"📨 新投稿待审核\n投稿人ID: {call.from_user.id}"
    )
    # 审核按钮
    review_markup = types.InlineKeyboardMarkup()
    review_markup.row(
        types.InlineKeyboardButton("✅ 通过", callback_data=f"approve_{call.from_user.id}"),
        types.InlineKeyboardButton("❌ 拒绝", callback_data=f"reject_{call.from_user.id}")
    )
    bot.send_message(REVIEW_GROUP_ID, "请审核该投稿", reply_markup=review_markup)
    # 通知投稿人
    bot.send_message(call.message.chat.id, "✅ 投稿成功！已提交至审核群，等待管理员审核")
    bot.answer_callback_query(call.id, "✅ 投稿已提交")

# ================== 审核处理 ==================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_review(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ 无审核权限")
        return
    action, user_id = call.data.split("_", 1)
    print(f"✅ 审核操作: {action}，用户ID: {user_id}")
    if action == "approve":
        bot.edit_message_text("✅ 投稿已通过", call.message.chat.id, call.message.message_id)
        bot.send_message(int(user_id), "✅ 你的投稿已通过审核，感谢投稿！")
    else:
        bot.edit_message_text("❌ 投稿已拒绝", call.message.chat.id, call.message.message_id)
        bot.send_message(int(user_id), "❌ 你的投稿未通过审核，如有疑问可联系管理员")
    bot.answer_callback_query(call.id, f"✅ 已{action}")

# ================== 启动机器人 ==================
def run_bot():
    print("✅ 机器人启动中...")
    while True:
        try:
            # 用long_polling，Railway环境稳定
            bot.polling(non_stop=True, timeout=10, long_polling_timeout=10)
        except Exception as e:
            print(f"❌ 机器人异常，2秒后重试: {e}")
            time.sleep(2)

# ================== 启动所有服务 ==================
if __name__ == "__main__":
    # 启动保活服务（守护线程，不阻塞主程序）
    Thread(target=run_web, daemon=True).start()
    time.sleep(1)
    # 启动机器人（主程序，阻塞运行）
    run_bot()