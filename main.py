import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get('TOKEN')
PORT = int(os.environ.get('PORT', 10000))

# 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 处理 /start 命令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f'你好 {user.first_name}！\n'
        '机器人已启动！\n\n'
        '试试发送：\n'
        '- 你好\n'
        '- 时间\n'
        '- 笑话\n'
        '- 其他任何消息'
    )

# 处理文本消息
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.lower()
    
    if any(word in user_message for word in ['你好', 'hi', 'hello', '嗨']):
        reply = '👋 你好呀！有什么可以帮你的吗？'
    elif '时间' in user_message:
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        reply = f'🕐 当前时间：{now}'
    elif '笑话' in user_message:
        reply = '😄 为什么程序员不喜欢大自然？\n因为里面有太多的 bugs！'
    elif '帮助' in user_message:
        reply = '💡 试试发送：你好、时间、笑话'
    else:
        reply = f'收到：{update.message.text}\n\n发送"帮助"查看功能'
    
    await update.message.reply_text(reply)

# 处理 /help 命令
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '📋 可用命令：\n'
        '/start - 开始使用\n'
        '/help - 显示帮助\n\n'
        '💬 自动回复：\n'
        '- 发送"你好"打招呼\n'
        '- 发送"时间"查看当前时间\n'
        '- 发送"笑话"听个笑话\n'
        '- 发送其他消息我会回复'
    )

def main():
    # 创建应用
    application = Application.builder().token(TOKEN).build()
    
    # 添加处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("机器人启动中...")
    
    # 使用 Polling 模式（Render 支持）
    # 注意：Render 免费版也支持 polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()