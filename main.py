import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import socket
import threading
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 删除顶部的错误导入语句：from database import DatabaseManager

# 在 main() 函数开始处添加：
def tcp_health_check():
    """简单的TCP健康检查服务器"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('0.0.0.0', 8080))
    sock.listen(1)
    print("🔌 TCP健康检查服务器启动在端口 8080")
    
    while True:
        conn, addr = sock.accept()
        conn.close()

# 启动TCP服务器线程
tcp_thread = threading.Thread(target=tcp_health_check, daemon=True)
tcp_thread.start()

# 1. 从环境变量获取Token和配置
TOKEN = os.environ.get('TOKEN')
DATABASE_URL = os.environ.get('DATABASE_URL')

# 修改点 1: 定义一个全局变量，用于存储数据库管理器
DB_MANAGER = None

if not TOKEN:
    print("❌ 错误：没有找到TOKEN环境变量！")
    print("请在Koyeb中设置TOKEN环境变量")
    exit(1)

if not DATABASE_URL:
    print("⚠️  警告：没有找到DATABASE_URL环境变量！")
    print("数据库功能将不可用，仅内存运行")

# 2. 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

print("=" * 50)
print("🤖 机器人启动中...")
print(f"📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 50)

# 3. 处理 /start 命令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # 保存用户信息到数据库
    # 修改点 2: 检查 DATABASE_URL 和 DB_MANAGER 是否可用
    if DATABASE_URL and DB_MANAGER is not None:
        try:
            DB_MANAGER.save_user({  # 修改点 3: 使用 DB_MANAGER 而非 DatabaseManager
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'language_code': user.language_code,
                'is_bot': user.is_bot
            })
            
            # 保存消息记录
            DB_MANAGER.save_message(user.id, chat_id, '/start', is_command=True)  # 修改点
            # 更新命令统计
            DB_MANAGER.update_command_stats(user.id, '/start')  # 修改点
            
            logger.info(f"✅ 用户 {user.id} ({user.username}) 启动机器人")
        except Exception as e:
            logger.error(f"❌ 数据库操作失败: {e}")
    
    # 发送欢迎消息
    welcome_text = f"""
🎉 你好 {user.first_name}！

欢迎使用我的机器人！我已经记住了你的信息。

📊 你可以使用以下命令：
/start - 显示此消息
/help - 查看详细帮助
/ping - 测试机器人响应
/stats - 查看你的使用统计
/admin - 管理员功能（如有权限）

💡 试试发送任意消息，我会回应你！
客服@TelegramSheng
客服@WIBSIBKB
    """
    await update.message.reply_text(welcome_text)

# 4. 处理 /help 命令
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # 修改点 4: 统一使用 DB_MANAGER 和可用性检查
    if DATABASE_URL and DB_MANAGER is not None:
        try:
            DB_MANAGER.save_message(user.id, chat_id, '/help', is_command=True)
            DB_MANAGER.update_command_stats(user.id, '/help')
        except Exception as e:
            logger.error(f"❌ 数据库操作失败: {e}")
    
    help_text = """
📚 可用命令：

🔹 基础命令
/start - 开始使用机器人
/help - 查看此帮助信息
/ping - 测试机器人是否在线

📊 统计命令
/stats - 查看你的使用统计
/rank - 查看活跃度排名（如有数据）

🛠️ 功能命令
/echo <文本> - 回声测试
/time - 显示当前时间
/weather <城市> - 查询天气（待实现）

💬 自动回复：
- 发送"你好"或"hi"
- 发送"时间"或"time"
- 发送"日期"或"date"
- 发送其他消息我会智能回复
    """
    await update.message.reply_text(help_text)

# 5. 处理 /ping 命令
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    if DATABASE_URL and DB_MANAGER is not None:
        try:
            DB_MANAGER.save_message(user.id, chat_id, '/ping', is_command=True)
            DB_MANAGER.update_command_stats(user.id, '/ping')
        except Exception as e:
            logger.error(f"❌ 数据库操作失败: {e}")
    
    await update.message.reply_text("🏓 Pong! 机器人正在运行！")

# 6. 新增：处理 /stats 命令
async def user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看用户统计"""
    user = update.effective_user
    
    if not DATABASE_URL or DB_MANAGER is None:  # 修改点
        await update.message.reply_text("📊 数据库未配置或不可用，统计功能不可用")
        return
    
    try:
        stats = DB_MANAGER.get_user_stats(user.id)  # 修改点
        
        if stats:
            response = f"""
📊 *{user.first_name} 的使用统计*

👤 用户信息：
- ID: `{stats['telegram_id']}`
- 用户名: @{stats['username'] or '无'}
- 加入时间: {stats['join_date'].strftime('%Y-%m-%d %H:%M')}

📈 活跃度统计：
- 总消息数: {stats['message_count']} 条
- /start 使用次数: {stats['start_count']}
- /help 使用次数: {stats['help_count']}
- /ping 使用次数: {stats['ping_count']}

🕐 最后命令: {stats['last_command_used'] or '无'}
最后时间: {stats['last_command_time'].strftime('%Y-%m-%d %H:%M') if stats['last_command_time'] else '无'}
            """
        else:
            response = "📭 还没有你的使用记录，请先使用一些命令吧！"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
        # 记录此命令
        DB_MANAGER.save_message(user.id, update.effective_chat.id, '/stats', is_command=True)  # 修改点
        
    except Exception as e:
        logger.error(f"❌ 获取统计失败: {e}")
        await update.message.reply_text("❌ 获取统计信息时出错")

# 7. 新增：处理 /admin 命令（基础版）
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员查看机器人统计"""
    user = update.effective_user
    
    # 这里可以添加权限检查，例如只允许特定用户ID
    # if user.id not in [YOUR_ADMIN_ID]:
    #     await update.message.reply_text("⛔ 权限不足")
    #     return
    
    if not DATABASE_URL or DB_MANAGER is None:  # 修改点
        await update.message.reply_text("📊 数据库未配置或不可用，管理员功能不可用")
        return
    
    try:
        bot_stats = DB_MANAGER.get_bot_stats()  # 修改点
        
        response = f"""
🤖 *机器人全局统计*

👥 用户数据：
- 总用户数: {bot_stats['total_users'] or 0}
- 总消息数: {bot_stats['total_messages'] or 0}
- 命令总数: {bot_stats['total_commands'] or 0}

⏰ 最后活动: {bot_stats['last_message_time'].strftime('%Y-%m-%d %H:%M') if bot_stats['last_message_time'] else '无'}

🛠️ 系统状态：
- 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 健康检查: ✅ 运行中 (端口 8080)
- 数据库: {'✅ 已连接' if DATABASE_URL else '❌ 未配置'}
        """
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ 获取管理员统计失败: {e}")
        await update.message.reply_text("❌ 获取管理员统计时出错")

# 8. 新增：处理 /echo 命令
async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """回声命令"""
    user = update.effective_user
    
    if context.args:
        text = ' '.join(context.args)
        await update.message.reply_text(f"🔊 回声: {text}")
        
        if DATABASE_URL and DB_MANAGER is not None:  # 修改点
            try:
                DB_MANAGER.save_message(user.id, update.effective_chat.id, f'/echo {text}', is_command=True)  # 修改点
            except Exception as e:
                logger.error(f"❌ 数据库操作失败: {e}")
    else:
        await update.message.reply_text("用法: /echo <文本>")

# 9. 改进的智能回复函数
async def smart_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理所有普通消息的智能回复"""
    user_message = update.message.text
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # 保存消息到数据库
    if DATABASE_URL and DB_MANAGER is not None:  # 修改点
        try:
            DB_MANAGER.save_message(user.id, chat_id, user_message)  # 修改点
        except Exception as e:
            logger.error(f"❌ 保存消息失败: {e}")
    
    # 智能回复逻辑
    user_message_lower = user_message.lower()
    
    greetings = ['你好', 'hi', 'hello', 'hey', 'hola']
    time_keywords = ['时间', 'time', '几点', '钟点']
    date_keywords = ['日期', 'date', '今天几号', '年月日']
    thanks = ['谢谢', 'thank', 'thanks', 'merci', 'gracias']
    
    if any(greet in user_message_lower for greet in greetings):
        reply = f'👋 你好呀 {user.first_name}！'
    
    elif any(keyword in user_message_lower for keyword in time_keywords):
        now = datetime.now().strftime('%H:%M:%S')
        reply = f'🕐 当前时间：{now}'
    
    elif any(keyword in user_message_lower for keyword in date_keywords):
        today = datetime.now().strftime('%Y年%m月%d日')
        weekday = ['一', '二', '三', '四', '五', '六', '日'][datetime.now().weekday()]
        reply = f'📅 今天是：{today} 星期{weekday}'
    
    elif any(thank in user_message_lower for thank in thanks):
        reply = '😊 不客气！随时为你服务！'
    
    elif '天气' in user_message_lower:
        reply = '🌤️ 天气功能正在开发中，敬请期待！'
    
    elif '谁' in user_message_lower and ('你' in user_message_lower or '谁' == user_message_lower):
        reply = f'🤖 我是你的专属机器人，由 {user.first_name} 的好友打造！'
    
    else:
        # 默认回复，可以更智能一些
        replies = [
            f'收到你的消息了，{user.first_name}！',
            f'「{user_message}」... 有意思的观点！',
            f'{user.first_name}，我在听呢！',
            '嗯，我记下了！',
            '继续说吧，我听着呢！'
        ]
        import random
        reply = random.choice(replies)
    
    await update.message.reply_text(reply)

# 10. 错误处理
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理机器人错误"""
    logger.error(f"机器人错误: {context.error}")
    
    if update and update.effective_chat:
        try:
            await update.effective_chat.send_message(
                "❌ 处理你的请求时出了点问题，请稍后再试。"
            )
        except:
            pass

# 11. 主函数
def main():
    global DB_MANAGER  # 修改点 5: 声明我们要修改全局变量 DB_MANAGER

    print("🚀 正在启动机器人...")
    
    # 初始化数据库
    if DATABASE_URL:
        try:
            from database import DatabaseManager
            DatabaseManager.initialize()
            DB_MANAGER = DatabaseManager  # 修改点 6: 将类赋值给全局变量
            print("✅ 数据库连接成功")
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
            print("⚠️  机器人将以无数据库模式运行")
    else:
        print("⚠️  未配置DATABASE_URL，机器人将以无数据库模式运行")
    
    # 创建应用
    application = Application.builder().token(TOKEN).build()
    
    # 添加处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("stats", user_stats))
    application.add_handler(CommandHandler("admin", admin_stats))
    application.add_handler(CommandHandler("echo", echo_command))
    application.add_handler(CommandHandler("time", 
        lambda update, context: update.message.reply_text(
            f"🕐 当前时间：{datetime.now().strftime('%H:%M:%S')}"
        )))
    
    # 消息处理器（放在最后，因为它是兜底的）
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_reply))
    
    # 错误处理器
    application.add_error_handler(error_handler)
    
    print("=" * 50)
    print("✅ 机器人启动完成！")
    print(f"📊 运行模式: {'数据库模式' if DATABASE_URL and DB_MANAGER is not None else '内存模式'}")
    print("=" * 50)
    
    # 启动机器人
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        close_loop=False
    )
    
    # 机器人停止时关闭数据库连接
    if DB_MANAGER is not None:  # 修改点 7: 使用全局变量判断
        DB_MANAGER.close_all_connections()

if __name__ == '__main__':
    main()
