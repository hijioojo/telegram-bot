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

# 定义一个全局变量，用于存储数据库管理器
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
    if DATABASE_URL and DB_MANAGER is not None:
        try:
            DB_MANAGER.save_user({  
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'language_code': user.language_code,
                'is_bot': user.is_bot
            })
            
            # 保存消息记录
            DB_MANAGER.save_message(user.id, chat_id, '/start', is_command=True)  
            # 更新命令统计
            DB_MANAGER.update_command_stats(user.id, '/start')  
            
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

💰 积分命令：
/sign - 每日签到获取1积分
/points - 查看我的积分详情
/rank - 查看积分排行榜

💡 试试发送任意消息，我会回应你！
    """
    await update.message.reply_text(welcome_text)

# 4. 处理 /help 命令
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # 统一使用 DB_MANAGER 和可用性检查
    if DATABASE_URL and DB_MANAGER is not None:
        try:
            DB_MANAGER.save_message(user.id, chat_id, '/help', is_command=True)
            DB_MANAGER.update_command_stats(user.id, '/help')
        except Exception as e:
            logger.error(f"❌ 数据库操作失败: {e}")
    
    help_text = """
🤖 *机器人命令手册*

🎯 *基础命令*
/start - 开始使用机器人
/help - 查看此帮助信息
/ping - 测试机器人是否在线

💰 *积分签到系统*
/sign - 每日签到获取积分（每天一次）
/points - 查看我的积分详情
/rank - 查看积分排行榜
/leaderboard - 排行榜（/rank 的别名）

📊 *统计命令*
/stats - 查看你的使用统计

🛠️ *功能命令*
/echo <文本> - 回声测试
/time - 显示当前时间

👮 *管理员命令* (仅管理员可用)
/addpoints <用户ID> <积分> [原因] - 调整用户积分
/setpoints <用户ID> <积分> - 直接设置用户积分
/admin - 查看机器人统计

🎮 *积分规则*
• 每日签到：+1 基础积分
• 连续3天：额外 +1 积分
• 连续7天：额外 +2 积分
• 每天只能签到一次
• 午夜后重置签到机会

💬 *智能聊天*
直接发送消息，我会智能回复：
- 你好、hi、hello
- 时间、几点
- 日期、今天几号
- 其他消息我会随机回复

📞 *客服联系*
@TelegranSheng
@WIBSIBKB

💡 *提示*：使用 /sign 开始你的签到之旅吧！
    """
    await update.message.reply_text(help_text, parse_mode='None')

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

# 6. 处理 /stats 命令
async def user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看用户统计"""
    user = update.effective_user
    
    if not DATABASE_URL or DB_MANAGER is None:  
        await update.message.reply_text("📊 数据库未配置或不可用，统计功能不可用")
        return
    
    try:
        stats = DB_MANAGER.get_user_stats(user.id)  
        
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
        DB_MANAGER.save_message(user.id, update.effective_chat.id, '/stats', is_command=True)  
        
    except Exception as e:
        logger.error(f"❌ 获取统计失败: {e}")
        await update.message.reply_text("❌ 获取统计信息时出错")

# 处理 /admin 命令（基础版）
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员查看机器人统计"""
    user = update.effective_user
    
    # 这里可以添加权限检查，例如只允许特定用户ID
    # if user.id not in [YOUR_ADMIN_ID]:
    #     await update.message.reply_text("⛔ 权限不足")
    #     return
    
    if not DATABASE_URL or DB_MANAGER is None:  
        await update.message.reply_text("📊 数据库未配置或不可用，管理员功能不可用")
        return
    
    try:
        bot_stats = DB_MANAGER.get_bot_stats()  
        
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

# 8. 处理 /echo 命令
async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """回声命令"""
    user = update.effective_user
    
    if context.args:
        text = ' '.join(context.args)
        await update.message.reply_text(f"🔊 回声: {text}")
        
        if DATABASE_URL and DB_MANAGER is not None:  
            try:
                DB_MANAGER.save_message(user.id, update.effective_chat.id, f'/echo {text}', is_command=True)  
            except Exception as e:
                logger.error(f"❌ 数据库操作失败: {e}")
    else:
        await update.message.reply_text("用法: /echo <文本>")
# 9. 处理 /sign 命令 - 每日签到
async def sign_in_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /sign 命令 - 每日签到"""
    user = update.effective_user
    
    if not DATABASE_URL or DB_MANAGER is None:
        await update.message.reply_text("❌ 数据库未配置，签到功能不可用")
        return
    
    try:
        # 执行签到
        success, message, points_awarded = DB_MANAGER.daily_sign_in(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        
        if success:
            # 获取签到后的详细信息
            points_info = DB_MANAGER.get_user_points_info(user.id)
            
            if points_info:
                # 构建成功响应
                from datetime import datetime
                now = datetime.now()
                
                # 根据连续天数选择不同的表情
                streak = points_info.get('current_streak', 1)
                if streak == 1:
                    streak_emoji = "🎯"
                    encouragement = "这是你的第一次签到，坚持就是胜利！"
                elif streak <= 3:
                    streak_emoji = "🔥"
                    encouragement = "良好的开始是成功的一半！"
                elif streak <= 7:
                    streak_emoji = "⚡"
                    encouragement = "连续签到，习惯正在养成！"
                elif streak <= 30:
                    streak_emoji = "🏆"
                    encouragement = "惊人的毅力，继续加油！"
                else:
                    streak_emoji = "👑"
                    encouragement = "你是签到王者，无人能敌！"
                
                # 检查是否有连续签到奖励
                base_points = 1
                bonus_points = points_awarded - base_points
                
                response = f"""
{streak_emoji} *签到成功！*

👤 {user.first_name}，签到成功！

💰 *积分详情*
├ 基础奖励: +{base_points}分
{f"├ 连续签到奖励: +{bonus_points}分" if bonus_points > 0 else ""}
└ 本次获得: **+{points_awarded}分**

📊 *签到统计*
├ 当前积分: **{points_info.get('total_points', 0)}分**
├ 连续签到: {streak}天 {streak_emoji}
├ 总签到次数: {points_info.get('sign_in_count', 1)}次
└ 今日排名: 第{points_info.get('rank', 1)}名

⏰ *时间信息*
├ 签到时间: {now.strftime('%Y-%m-%d %H:%M:%S')}
└ 下次签到: 明天{now.strftime('%H:%M')}后

{encouragement}

💡 使用 /points 查看详细积分
💎 使用 /rank 查看排行榜
                """
            else:
                response = f"""
✅ 签到成功！
获得 {points_awarded} 积分！

{message}

使用 /points 查看你的积分详情。
                """
        else:
            # 签到失败（可能已经签到过）
            points_info = DB_MANAGER.get_user_points_info(user.id)
            
            if points_info and points_info.get('signed_in_today'):
                last_sign = points_info.get('last_sign_in')
                last_time = last_sign.strftime('%H:%M:%S') if last_sign else "未知时间"
                
                response = f"""
⏰ *签到提醒*

{user.first_name}，你今天已经签到过了哦！

📅 签到时间: {last_time}
💰 当前积分: **{points_info.get('total_points', 0)}分**
🔥 连续签到: {points_info.get('current_streak', 0)}天

💡 明天记得再来签到！
⏳ 下次可签到: 明天 00:00 后
                """
            else:
                response = f"❌ {message}"
        
        # 详细的成功日志记录
        logger.info(f"✅ 签到成功 - 用户: {user.id}, 响应长度: {len(response)}")
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
        # 保存消息记录
        if DB_MANAGER:
            DB_MANAGER.save_message(user.id, update.effective_chat.id, '/sign', is_command=True)
        
    except Exception as e:
        logger.error(f"❌ 处理签到命令失败: {e}")
        logger.error(f"❌ 用户信息 - ID: {user.id}, 用户名: {repr(user.username)}, 姓名: {repr(user.first_name)}")

        # 如果响应变量已定义，打印其内容
        if 'response' in locals():
            try:
                response_preview = response[:50] if len(response) > 50 else response
                logger.error(f"❌ 响应内容前50字符: {repr(response_preview)}")
            except Exception as log_error:
                logger.error(f"❌ 记录响应内容时出错: {log_error}")
    
    # 确保只在捕获到异常时才显示错误信息
    if 'e' in locals():
        await update.message.reply_text("❌ 签到失败，系统错误，请稍后重试")
        
# 10. 处理 /points 命令 - 查看积分详情
async def points_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /points 命令 - 查看积分详情"""
    user = update.effective_user
    
    if not DATABASE_URL or DB_MANAGER is None:
        await update.message.reply_text("❌ 数据库未配置，积分功能不可用")
        return
    
    try:
        # 获取积分信息
        points_info = DB_MANAGER.get_user_points_info(user.id)
        
        if not points_info:
            response = f"""
💰 *积分详情*

👤 {user.first_name}，你还没有积分记录。

💡 使用 /sign 进行每日签到，获得积分！
🎯 每天只能签到一次，每次获得1积分
✨ 连续签到还有额外奖励！
            """
        else:
            # 构建积分详情响应
            signed_today = "✅ 今日已签到" if points_info.get('signed_in_today') else "⏳ 今日未签到"
            last_sign = points_info.get('last_sign_in')
            last_sign_str = last_sign.strftime('%Y-%m-%d %H:%M') if last_sign else "从未签到"
            
            # 构建最近7天签到日历
            recent_sign_ins = points_info.get('recent_sign_ins', [])
            week_calendar = []
            for i in range(6, -1, -1):
                sign_date = None
                for sign_in in recent_sign_ins:
                    if sign_in['display_date'] == 'today' and i == 0:
                        sign_date = '✅'
                        break
                    elif sign_in['display_date'] == 'yesterday' and i == 1:
                        sign_date = '✓'
                        break
                if not sign_date:
                    sign_date = '○'
                week_calendar.append(sign_date)
            
            response = f"""
💰 *积分详情*

👤 **{user.first_name}** (@{user.username or '无用户名'})

📊 *积分概览*
├ 总积分: **{points_info.get('total_points', 0)} 分**
├ 签到次数: {points_info.get('sign_in_count', 0)} 次
├ 当前连胜: {points_info.get('current_streak', 0)} 天
├ 最高连胜: {points_info.get('max_streak', 0)} 天
├ 今日状态: {signed_today}
└ 上次签到: {last_sign_str}

📈 *最近7天签到日历*
{" ".join(week_calendar)}
← 最近7天
✓=已签 ○=未签 ✅=今日

🏆 *排行榜*
当前排名: 第 {points_info.get('rank', 1)} 名

📝 *最近积分变动*
"""
        
            # 添加最近积分记录
            recent_transactions = points_info.get('recent_transactions', [])
            if recent_transactions:
                for trans in recent_transactions:
                    change = trans['points_change']
                    change_str = f"+{change}" if change > 0 else f"{change}"
                    reason_map = {
                        'sign_in': '每日签到',
                        'sign_in_streak_3': '连续3天奖励',
                        'sign_in_streak_7': '连续7天奖励'
                    }
                    reason = reason_map.get(trans['reason'], trans.get('description', trans['reason']))
                    response += f"• {trans['time_str']} {change_str} 分 ({reason})\n"
            else:
                response += "暂无积分记录\n"
        
            # 添加提示信息
            if not points_info.get('signed_in_today'):
                response += f"\n🎯 使用 /sign 进行今日签到，获得积分！"
            else:
                response += f"\n💡 每天坚持签到，积分越来越多！"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
        # 保存消息记录
        if DB_MANAGER:
            DB_MANAGER.save_message(user.id, update.effective_chat.id, '/points', is_command=True)
        
    except Exception as e:
        logger.error(f"❌ 查询积分失败: {e}")
        await update.message.reply_text("❌ 查询积分失败，请稍后再试")

# 11. 处理 /rank 命令 - 查看积分排行榜
async def rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /rank 命令 - 查看积分排行榜"""
    user = update.effective_user
    
    if not DATABASE_URL or DB_MANAGER is None:
        await update.message.reply_text("❌ 数据库未配置，排行榜功能不可用")
        return
    
    try:
        # 获取排行榜
        top_users = DB_MANAGER.get_top_users(limit=10)
        
        if not top_users:
            response = """
🏆 *积分排行榜*

暂无用户数据。

💡 使用 /sign 开始签到，成为排行榜第一名！
            """
        else:
            # 获取当前用户排名
            user_points_info = DB_MANAGER.get_user_points_info(user.id)
            user_rank_num = user_points_info.get('rank', 0) if user_points_info else 0
            
            response = f"""
🏆 *积分排行榜*

🏅 *Top 10 签到达人*
"""
            
            # 显示前10名
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            for i, user_data in enumerate(top_users):
                if i < len(medals):
                    medal = medals[i]
                else:
                    medal = f"{i+1}."
                
                name = user_data['first_name'] or user_data['username'] or f"用户{user_data['user_id']}"
                points = user_data['total_points']
                streak = user_data['sign_in_streak']
                
                response += f"{medal} {name}: {points} 分"
                if streak > 1:
                    response += f" (🔥{streak}天)"
                response += "\n"
            
            # 显示当前用户排名（如果不在前10）
            if user_points_info and user_rank_num > 10:
                user_points = user_points_info.get('total_points', 0)
                response += f"\n📊 你的排名: 第 {user_rank_num} 名 ({user_points} 分)"
            elif user_points_info:
                response += f"\n📊 恭喜你在排行榜上！"
        
        response += "\n\n💡 每日签到可获得积分，连续签到有额外奖励！"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
        # 保存消息记录
        if DB_MANAGER:
            DB_MANAGER.save_message(user.id, update.effective_chat.id, '/rank', is_command=True)
        
    except Exception as e:
        logger.error(f"❌ 查询排行榜失败: {e}")
        await update.message.reply_text("❌ 查询排行榜失败，请稍后再试")

# 12. 处理 /addpoints 命令 - 管理员添加积分
async def add_points_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员添加积分（格式：/addpoints <用户ID> <积分> [原因]）"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # 权限检查（只允许特定管理员）
    ADMIN_IDS = [8318755495]  
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ 权限不足")
        return
    
    if not DATABASE_URL or DB_MANAGER is None:
        await update.message.reply_text("❌ 数据库未配置")
        return
    
    # 检查参数
    if len(context.args) < 2:
        await update.message.reply_text(
            "用法: /addpoints <用户ID> <积分> [原因]\n"
            "示例: /addpoints 8318755495 100 活动奖励\n"
            "示例: /addpoints 8318755495 -50 扣除违规积分"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        points = int(context.args[1])
        reason = ' '.join(context.args[2:]) if len(context.args) > 2 else "管理员调整"
        
        # 调用积分修改方法
        success, message = DB_MANAGER.add_points_to_user(target_user_id, points, reason)
        
        if success:
            # 获取修改后的积分信息
            points_info = DB_MANAGER.get_user_points_info(target_user_id)
            
            response = f"""
✅ *积分调整成功*

👤 目标用户ID: `{target_user_id}`
💰 积分变动: **{points}** 分
📝 原因: {reason}

📊 *调整后状态*
- 总积分: **{points_info.get('total_points', 0)}** 分
- 签到次数: {points_info.get('sign_in_count', 0)} 次
- 连续签到: {points_info.get('current_streak', 0)} 天

⏰ 操作时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👮 操作人: {user.first_name} (@{user.username})
            """
        else:
            response = f"❌ {message}"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
        # 记录操作日志
        DB_MANAGER.save_message(user.id, chat_id, 
                               f'/addpoints {target_user_id} {points} {reason}', 
                               is_command=True)
        
    except ValueError:
        await update.message.reply_text("❌ 参数错误：用户ID和积分必须是数字")
    except Exception as e:
        logger.error(f"❌ 调整积分失败: {e}")
        await update.message.reply_text(f"❌ 调整积分失败: {str(e)}")

# 13. 处理 /setpoints 命令 - 直接设置积分
async def set_points_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员设置积分（格式：/setpoints <用户ID> <积分>）"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    ADMIN_IDS = [8318755495]  
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ 权限不足")
        return
    
    if not DATABASE_URL or DB_MANAGER is None:
        await update.message.reply_text("❌ 数据库未配置")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("用法: /setpoints <用户ID> <积分>")
        return
    
    try:
        target_user_id = int(context.args[0])
        points = int(context.args[1])
        
        # 调用设置积分方法
        success, message = DB_MANAGER.set_user_points(target_user_id, points)
        
        if success:
            response = f"""
✅ *积分设置成功*

👤 目标用户ID: `{target_user_id}`
🎯 设置积分: **{points}** 分

⏰ 操作时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👮 操作人: {user.first_name}
            """
        else:
            response = f"❌ {message}"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
        # 记录操作日志
        DB_MANAGER.save_message(user.id, chat_id, 
                               f'/setpoints {target_user_id} {points}', 
                               is_command=True)
        
    except ValueError:
        await update.message.reply_text("❌ 参数错误：用户ID和积分必须是数字")
    except Exception as e:
        logger.error(f"❌ 设置积分失败: {e}")
        await update.message.reply_text(f"❌ 设置积分失败: {str(e)}")

# 13. 改进的智能回复函数
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

# 14. 错误处理
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

# 15. 主函数
def main():
    global DB_MANAGER  

    print("🚀 正在启动机器人...")
    
    # 初始化数据库
    if DATABASE_URL:
        try:
            from database import DatabaseManager
            DatabaseManager.initialize()
            DB_MANAGER = DatabaseManager  
            print("✅ 数据库连接成功")
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
            print("⚠️  机器人将以无数据库模式运行")
    else:
        print("⚠️  未配置DATABASE_URL，机器人将以无数据库模式运行")
    
    # 创建应用
    application = Application.builder().token(TOKEN).build()
    
    # 添加处理
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
    
    # 新增积分命令
    application.add_handler(CommandHandler("sign", sign_in_command))
    application.add_handler(CommandHandler("points", points_command))
    application.add_handler(CommandHandler("rank", rank_command))
    application.add_handler(CommandHandler("leaderboard", rank_command))  # 别名

    # 新增积分管理命令
    application.add_handler(CommandHandler("addpoints", add_points_command))  
    application.add_handler(CommandHandler("setpoints", set_points_command))  
    
    # 消息处理（放在最后，因为它是兜底的）
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_reply))
    
    # 错误处理
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
    if DB_MANAGER is not None:  
        DB_MANAGER.close_all_connections()

if __name__ == '__main__':
    main()
