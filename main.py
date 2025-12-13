import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get('TOKEN')

# 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 处理 /start 命令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🤖 机器人已启动！\n发送 /help 查看帮助')

# 处理 /help 命令
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📋 **可用命令**：
/start - 启动机器人
/help - 显示此帮助
/about - 关于机器人

💬 **自动回复**：
- 发送"你好"打招呼
- 发送"时间"查看当前时间
- 发送"笑话"听个笑话
- 发送任何其他消息我会回应
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# 处理 /about 命令
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🔧 这是一个使用 Python 编写的 Telegram 机器人\n'
        '🚀 部署在 Koyeb 平台\n'
        '📅 创建于 2024年'
    )

# 处理普通消息
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.lower()
    
    if any(word in user_message for word in ['你好', 'hi', 'hello']):
        reply = '👋 你好呀！'
    elif '时间' in user_message:
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        reply = f'🕐 当前时间：{now}'
    elif '笑话' in user_message:
        reply = '😄 为什么程序员讨厌大自然？\n因为有太多的 bugs！'
    else:
        reply = f'你说：{update.message.text}'
    
    await update.message.reply_text(reply)

# 主函数
def main():
    # 创建应用
    application = Application.builder().token(TOKEN).build()
    
    # 添加处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    logger.info("机器人启动中...")
    
    # 使用Polling模式（Koyeb支持）
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    # Koyeb可能需要处理SIGTERM信号
    try:
        main()
    except KeyboardInterrupt:
        print("机器人已停止")
