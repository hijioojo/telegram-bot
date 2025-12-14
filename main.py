import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ========== HTTP 健康检查服务器 ==========
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is running')

    def log_message(self, format, *args):
        logging.info(f"HTTP {self.client_address[0]} - {format % args}")

def run_http_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logging.info(f"HTTP health check server started on port {port}")
    server.serve_forever()

# ========== Telegram 机器人 ==========
TOKEN = os.environ.get('TOKEN')

if not TOKEN:
    logging.error("TOKEN environment variable not set!")
    exit(1)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Bot started!')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'You said: {update.message.text}')

def main():
    # 启动HTTP服务器线程
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # 创建Telegram应用
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    logger.info("Starting Telegram bot...")
    
    # 启动机器人
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES

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
        '📅 创建于 2024年
    )

if __name__ == '__main__':
    main()
