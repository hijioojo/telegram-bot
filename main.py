import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# 从环境变量获取Token（Railway会提供）
TOKEN = os.environ.get('TOKEN')

if not TOKEN:
    logging.error("未找到TOKEN环境变量，请检查Railway设置")
    exit(1)

# 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 处理 /start 命令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f'你好 {user.first_name}！\n'
        '我是自动回复机器人。\n'
        '发送 /help 查看可用命令。'
    )

# 处理 /help 命令
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 *可用命令*：
/start - 开始使用
/help - 显示此帮助信息
/about - 关于本机器人

💬 *自动回复示例*：
- 发送"你好"或"hi"
- 发送"时间"查看当前时间
- 发送其他消息我会重复
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# 处理 /about 命令
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🔧 这是一个使用 Python 编写的 Telegram 机器人\n'
        '🚀 部署在 Railway 平台\n'
        '📅 创建于 2024年'
    )

# 处理普通文本消息
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.lower()
    
    # 根据关键词回复
    if any(word in user_message for word in ['你好', 'hi', 'hello', '嗨']):
        reply = '👋 你好呀！有什么可以帮你的吗？'
    elif '时间' in user_message:
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        reply = f'🕐 当前时间：{now}'
    elif '天气' in user_message:
        reply = '🌤️ 天气功能开发中...'
    elif '笑话' in user_message or '笑话' in user_message:
        reply = '😄 为什么程序员不喜欢大自然？\n因为里面有太多的 bugs！'
    else:
        # 默认回复（重复用户消息）
        reply = f'收到你的消息：{update.message.text}'
    
    await update.message.reply_text(reply)

# 错误处理
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f'更新 {update} 导致错误: {context.error}')

# 主函数
def main():
    # 创建应用
    application = ApplicationBuilder().token(TOKEN).build()
    
    # 添加命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about))
    
    # 添加消息处理器
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 添加错误处理器
    application.add_error_handler(error_handler)
    
    # 启动机器人
    logging.info("机器人启动中...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True  # 忽略机器人离线时的消息
    )

if __name__ == '__main__':
    main()