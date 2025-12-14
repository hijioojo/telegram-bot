import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. 从环境变量获取Token
TOKEN = os.environ.get('TOKEN')

if not TOKEN:
    print("❌ 错误：没有找到TOKEN！")
    print("请在Koyeb中设置TOKEN环境变量")
    exit(1)

# 2. 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

print("=" * 50)
print("🤖 机器人启动中...")
print("=" * 50)

# 3. 处理 /start 命令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🎉 你好！我是你的机器人！')

# 4. 处理 /help 命令
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 可用命令：
/start - 开始使用
/help - 查看帮助
/ping - 测试机器人

💬 自动回复：
- 发送"你好"
- 发送"时间"
- 发送其他消息我会重复
    """
    await update.message.reply_text(help_text)

# 5. 处理 /ping 命令
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! 机器人正在运行！")

# 6. 处理所有普通消息
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    if '你好' in user_message:
        reply = '👋 你好呀！'
    elif '时间' in user_message:
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        reply = f'🕐 当前时间：{now}'
    else:
        reply = f'你说：{user_message}'
    
    await update.message.reply_text(reply)

# 7. 主函数
def main():
    # 创建应用
    application = Application.builder().token(TOKEN).build()
    
    # 添加处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    print("🚀 正在启动机器人...")
    
    # 启动机器人
    application.run_polling(
        drop_pending_updates=True,  # 忽略启动前的消息
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    main()
