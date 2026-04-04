import telebot
import json
import os
from datetime import datetime, timedelta

# 你的机器人Token
BOT_TOKEN = "8756349976:AAGWdUy9-c3aSh6RsHe8JGeww2YOFX4dl74"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# 数据文件（永久保存，重启不丢）
DATA_FILE = "orders.json"
ADMIN_FILE = "admins.json"

# 北京时间
def beijing_time():
    return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

# 加载/保存订单
def load_orders():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_orders(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 加载/保存管理员
def load_admins():
    if os.path.exists(ADMIN_FILE):
        with open(ADMIN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # 你的主账号ID
    return ["72406269073"]

def save_admins(data):
    with open(ADMIN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 主菜单按钮
def main_menu():
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📥 提交订单", callback_data="submit"),
        InlineKeyboardButton("🔍 查询手机号", callback_data="query"),
        InlineKeyboardButton("📋 所有订单", callback_data="all"),
        InlineKeyboardButton("⚙️ 管理订单", callback_data="manage")
    )
    return kb

# 等待输入状态
wait_add_admin = {}
wait_remove_admin = {}
wait_query_phone = {}

# /start 命令
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "✅ 订单管理机器人已启动！\n请选择功能：",
        reply_markup=main_menu()
    )

# /myid 命令
@bot.message_handler(commands=["myid"])
def myid(message):
    bot.send_message(message.chat.id, f"你的ID：`{message.chat.id}`", parse_mode="Markdown")

# /addadmin 命令
@bot.message_handler(commands=["addadmin"])
def addadmin(message):
    admins = load_admins()
    if str(message.chat.id) not in admins:
        bot.send_message(message.chat.id, "❌ 你没有管理员权限")
        return
    wait_add_admin[str(message.chat.id)] = True
    bot.send_message(message.chat.id, "👤 请发送要添加的管理员ID")

# /removeadmin 命令
@bot.message_handler(commands=["removeadmin"])
def removeadmin(message):
    admins = load_admins()
    if str(message.chat.id) not in admins:
        bot.send_message(message.chat.id, "❌ 你没有管理员权限")
        return
    wait_remove_admin[str(message.chat.id)] = True
    bot.send_message(message.chat.id, "👤 请发送要移除的管理员ID")

# 处理文本消息
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    cid = str(message.chat.id)
    text = message.text.strip()
    admins = load_admins()

    # 处理添加管理员
    if cid in wait_add_admin:
        if text in admins:
            bot.send_message(message.chat.id, "❌ 该用户已是管理员")
        else:
            admins.append(text)
            save_admins(admins)
            bot.send_message(message.chat.id, f"✅ 已添加管理员：{text}")
        del wait_add_admin[cid]
        return

    # 处理移除管理员
    if cid in wait_remove_admin:
        if text not in admins:
            bot.send_message(message.chat.id, "❌ 该用户不是管理员")
        elif text == "72406269073":
            bot.send_message(message.chat.id, "❌ 不能移除主管理员")
        else:
            admins.remove(text)
            save_admins(admins)
            bot.send_message(message.chat.id, f"✅ 已移除管理员：{text}")
        del wait_remove_admin[cid]
        return

    # 处理查询手机号
    if cid in wait_query_phone:
        orders = load_orders()
        result = [order for order in orders.values() if order["phone"] == text]
        if not result:
            bot.send_message(message.chat.id, "❌ 未找到该手机号的订单")
        else:
            for order in result:
                kb = InlineKeyboardMarkup(row_width=2)
                kb.add(
                    InlineKeyboardButton("✅ 标记完成", callback_data=f"done_{order['id']}"),
                    InlineKeyboardButton("🗑️ 删除", callback_data=f"del_{order['id']}")
                )
                bot.send_message(
                    message.chat.id,
                    f"📦 订单号：{order['id']}\n📞 手机号：{order['phone']}\n💰 金额：{order['amount']}\n⏰ 时间：{order['time']}\n状态：{order['status']}",
                    reply_markup=kb
                )
        del wait_query_phone[cid]
        return

    # 处理提交订单（格式：订单号 手机号 金额）
    parts = text.split()
    if len(parts) == 3:
        order_id, phone, amount = parts
        orders = load_orders()
        orders[order_id] = {
            "id": order_id,
            "phone": phone,
            "amount": amount,
            "time": beijing_time(),
            "status": "待处理"
        }
        save_orders(orders)
        bot.send_message(message.chat.id, f"✅ 订单提交成功！\n订单号：{order_id}")
    else:
        bot.send_message(message.chat.id, "❌ 格式错误！请使用：订单号 手机号 金额（一行一条）")

# 处理按钮回调
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    cid = str(call.message.chat.id)
    admins = load_admins()
    if cid not in admins:
        bot.answer_callback_query(call.id, "❌ 你没有管理员权限")
        return

    # 主菜单按钮
    if call.data == "submit":
        bot.edit_message_text(
            "📥 请发送订单，格式：订单号 手机号 金额（一行一条）",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    elif call.data == "query":
        wait_query_phone[cid] = True
        bot.edit_message_text(
            "🔍 请输入要查询的手机号",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    elif call.data == "all":
        orders = load_orders()
        if not orders:
            bot.edit_message_text(
                "📋 暂无订单",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            return
        for order in orders.values():
            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(
                InlineKeyboardButton("✅ 标记完成", callback_data=f"done_{order['id']}"),
                InlineKeyboardButton("🗑️ 删除", callback_data=f"del_{order['id']}")
            )
            bot.send_message(
                call.message.chat.id,
                f"📦 订单号：{order['id']}\n📞 手机号：{order['phone']}\n💰 金额：{order['amount']}\n⏰ 时间：{order['time']}\n状态：{order['status']}",
                reply_markup=kb
            )
        bot.delete_message(call.message.chat.id, call.message.message_id)
    elif call.data == "manage":
        orders = load_orders()
        if not orders:
            bot.edit_message_text(
                "⚙️ 暂无订单可管理",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            return
        for order in orders.values():
            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(
                InlineKeyboardButton("✅ 标记完成", callback_data=f"done_{order['id']}"),
                InlineKeyboardButton("🗑️ 删除", callback_data=f"del_{order['id']}")
            )
            bot.send_message(
                call.message.chat.id,
                f"📦 订单号：{order['id']}\n📞 手机号：{order['phone']}\n💰 金额：{order['amount']}\n⏰ 时间：{order['time']}\n状态：{order['status']}",
                reply_markup=kb
            )
        bot.delete_message(call.message.chat.id, call.message.message_id)
    # 订单操作按钮
    elif call.data.startswith("done_"):
        order_id = call.data.split("_")[1]
        orders = load_orders()
        if order_id in orders:
            orders[order_id]["status"] = "已完成"
            save_orders(orders)
            bot.edit_message_text(
                f"📦 订单号：{orders[order_id]['id']}\n📞 手机号：{orders[order_id]['phone']}\n💰 金额：{orders[order_id]['amount']}\n⏰ 时间：{orders[order_id]['time']}\n状态：{orders[order_id]['status']}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            bot.answer_callback_query(call.id, "✅ 已标记完成")
    elif call.data.startswith("del_"):
        order_id = call.data.split("_")[1]
        orders = load_orders()
        if order_id in orders:
            del orders[order_id]
            save_orders(orders)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "🗑️ 已删除订单")

# 启动机器人
if __name__ == "__main__":
    print("机器人启动成功，7×24小时在线运行...")
    bot.infinity_polling()
