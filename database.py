import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    _connection_pool = None
    
    @classmethod
    def initialize(cls):
        """初始化数据库连接池"""
        try:
            database_url = os.environ.get('DATABASE_URL')
            if not database_url:
                raise ValueError("DATABASE_URL环境变量未设置")
            
            # 解析Railway的DATABASE_URL
            # 格式：postgresql://user:password@host:port/dbname
            cls._connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20, database_url, sslmode='require'
            )
            logger.info("✅ 数据库连接池初始化成功")
            
            # 初始化表
            cls._init_tables()
            
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            raise
    
    @classmethod
    def _init_tables(cls):
        """创建数据库表"""
        create_tables_sql = """
        -- 用户表
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(255),
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            language_code VARCHAR(10),
            is_bot BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            last_active TIMESTAMP DEFAULT NOW(),
            message_count INT DEFAULT 0
        );
        
        -- 消息历史表
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
            chat_id BIGINT NOT NULL,
            text TEXT,
            is_command BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        -- 用户统计表
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
            start_count INT DEFAULT 0,
            help_count INT DEFAULT 0,
            ping_count INT DEFAULT 0,
            last_command_used VARCHAR(50),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        -- ========== 新增积分相关表 ==========
        -- 积分记录表：记录所有积分变动
        CREATE TABLE IF NOT EXISTS points_history (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
            points_change INT NOT NULL CHECK (points_change != 0),
            reason VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        -- 用户积分汇总表：快速查询用户当前积分
        CREATE TABLE IF NOT EXISTS user_points (
            user_id BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
            total_points INT DEFAULT 0,
            sign_in_count INT DEFAULT 0,
            last_sign_in TIMESTAMP,
            sign_in_streak INT DEFAULT 0,
            max_streak INT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        -- 每日签到记录表：确保每天只能签到一次
        CREATE TABLE IF NOT EXISTS daily_sign_ins (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
            sign_date DATE NOT NULL,
            points_awarded INT DEFAULT 1,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, sign_date)  -- 确保每天只能有一条记录
        );
        
        -- ========== 创建索引 ==========
        CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
        CREATE INDEX IF NOT EXISTS idx_points_history_user_id ON points_history(user_id);
        CREATE INDEX IF NOT EXISTS idx_points_history_created_at ON points_history(created_at);
        CREATE INDEX IF NOT EXISTS idx_daily_sign_ins_user_date ON daily_sign_ins(user_id, sign_date);
        CREATE INDEX IF NOT EXISTS idx_daily_sign_ins_date ON daily_sign_ins(sign_date);
        
        -- ========== 创建视图：简化积分查询 ==========
        CREATE OR REPLACE VIEW v_user_points_summary AS
        SELECT 
            u.telegram_id,
            u.username,
            u.first_name,
            COALESCE(up.total_points, 0) as total_points,
            COALESCE(up.sign_in_count, 0) as sign_in_count,
            COALESCE(up.sign_in_streak, 0) as current_streak,
            COALESCE(up.max_streak, 0) as max_streak,
            up.last_sign_in,
            (SELECT COUNT(*) 
             FROM daily_sign_ins dsi 
             WHERE dsi.user_id = u.telegram_id 
             AND dsi.sign_date = CURRENT_DATE) as signed_in_today
        FROM users u
        LEFT JOIN user_points up ON u.telegram_id = up.user_id;
        """
        
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(create_tables_sql)
            conn.commit()
            logger.info("✅ 数据库表初始化成功（包含积分表）")
        except Exception as e:
            logger.error(f"❌ 创建积分表失败: {e}")
            conn.rollback()
            raise
        finally:
            cls.return_connection(conn)
    
    @classmethod
    def get_connection(cls):
        """从连接池获取连接"""
        if cls._connection_pool is None:
            cls.initialize()
        return cls._connection_pool.getconn()
    
    @classmethod
    def return_connection(cls, conn):
        """归还连接到连接池"""
        if cls._connection_pool:
            cls._connection_pool.putconn(conn)
    
    @classmethod
    def close_all_connections(cls):
        """关闭所有连接"""
        if cls._connection_pool:
            cls._connection_pool.closeall()
            logger.info("✅ 数据库连接已关闭")
    
    # 用户相关操作
    @classmethod
    def save_user(cls, user_data: dict):
        """保存或更新用户信息"""
        sql = """
        INSERT INTO users 
            (telegram_id, username, first_name, last_name, language_code, is_bot, last_active)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (telegram_id) 
        DO UPDATE SET
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            last_active = NOW()
        RETURNING id;
        """
        
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (
                user_data['id'],
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name'),
                user_data.get('language_code'),
                user_data.get('is_bot', False)
            ))
            conn.commit()
            return cursor.fetchone()[0]
        finally:
            cls.return_connection(conn)
    
    @classmethod
    def save_message(cls, telegram_id: int, chat_id: int, text: str, is_command: bool = False):
        """保存消息记录并更新用户统计"""
        sql = """
        WITH user_update AS (
            UPDATE users 
            SET message_count = message_count + 1,
                last_active = NOW()
            WHERE telegram_id = %s
        )
        INSERT INTO messages (user_id, chat_id, text, is_command)
        VALUES (%s, %s, %s, %s);
        """
        
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (telegram_id, telegram_id, chat_id, text, is_command))
            conn.commit()
        finally:
            cls.return_connection(conn)
    
    @classmethod
    def update_command_stats(cls, telegram_id: int, command: str):
        """更新命令使用统计"""
        sql = """
        INSERT INTO user_stats (user_id, start_count, help_count, ping_count, last_command_used)
        VALUES (
            %s,
            CASE WHEN %s = '/start' THEN 1 ELSE 0 END,
            CASE WHEN %s = '/help' THEN 1 ELSE 0 END,
            CASE WHEN %s = '/ping' THEN 1 ELSE 0 END,
            %s
        )
        ON CONFLICT (user_id) 
        DO UPDATE SET
            start_count = user_stats.start_count + CASE WHEN %s = '/start' THEN 1 ELSE 0 END,
            help_count = user_stats.help_count + CASE WHEN %s = '/help' THEN 1 ELSE 0 END,
            ping_count = user_stats.ping_count + CASE WHEN %s = '/ping' THEN 1 ELSE 0 END,
            last_command_used = %s,
            updated_at = NOW();
        """
        
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (telegram_id, command, command, command, command, 
                               command, command, command, command))
            conn.commit()
        finally:
            cls.return_connection(conn)
    
    @classmethod
    def get_user_stats(cls, telegram_id: int):
        """获取用户统计信息"""
        sql = """
        SELECT 
            u.telegram_id,
            u.username,
            u.first_name,
            u.message_count,
            u.created_at as join_date,
            COALESCE(s.start_count, 0) as start_count,
            COALESCE(s.help_count, 0) as help_count,
            COALESCE(s.ping_count, 0) as ping_count,
            s.last_command_used,
            s.updated_at as last_command_time
        FROM users u
        LEFT JOIN user_stats s ON u.telegram_id = s.user_id
        WHERE u.telegram_id = %s;
        """
        
        conn = cls.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(sql, (telegram_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            cls.return_connection(conn)
    
    @classmethod
    def get_bot_stats(cls):
        """获取机器人整体统计"""
        sql = """
        SELECT 
            COUNT(DISTINCT telegram_id) as total_users,
            COUNT(*) as total_messages,
            SUM(CASE WHEN is_command THEN 1 ELSE 0 END) as total_commands,
            MAX(created_at) as last_message_time
        FROM messages;
        """
        
        conn = cls.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(sql)
            return dict(cursor.fetchone())
        finally:
            cls.return_connection(conn)

    # ========== 新增：积分相关方法 ==========
    
    @classmethod
    def daily_sign_in(cls, telegram_id: int, username: str = None, first_name: str = None):
        """
        用户每日签到
        返回: (success, message, points_awarded)
        """
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. 检查今天是否已经签到
            cursor.execute("""
                SELECT 1 FROM daily_sign_ins 
                WHERE user_id = %s AND sign_date = CURRENT_DATE
            """, (telegram_id,))
            
            if cursor.fetchone():
                logger.info(f"用户 {telegram_id} 今天已经签到过了")
                return False, "今天已经签到过了，请明天再来！", 0
            
            # 2. 获取昨天的签到记录，计算连续签到
            cursor.execute("""
                SELECT 1 FROM daily_sign_ins 
                WHERE user_id = %s AND sign_date = CURRENT_DATE - INTERVAL '1 day'
            """, (telegram_id,))
            
            signed_yesterday = cursor.fetchone() is not None
            
            # 3. 获取当前连续签到天数
            current_streak = 0
            cursor.execute("""
                SELECT sign_in_streak FROM user_points 
                WHERE user_id = %s
            """, (telegram_id,))
            result = cursor.fetchone()
            current_streak = result[0] if result else 0
            
            # 4. 计算新的连续天数
            new_streak = current_streak + 1 if signed_yesterday else 1
            
            # 5. 计算奖励积分（基础1分 + 连续签到奖励）
            base_points = 1
            streak_bonus = 0
            
            # 连续签到奖励规则
            if new_streak >= 7:
                streak_bonus = 2  # 连续7天额外2分
            elif new_streak >= 3:
                streak_bonus = 1  # 连续3天额外1分
            
            total_points = base_points + streak_bonus
            
            # 6. 使用独立的连接执行签到操作，避免事务冲突
            try:
                # 6.1 插入签到记录
                cursor.execute("""
                    INSERT INTO daily_sign_ins (user_id, sign_date, points_awarded)
                    VALUES (%s, CURRENT_DATE, %s)
                """, (telegram_id, total_points))
                
                # 6.2 插入积分变动记录
                reason = f'sign_in_streak_{new_streak}' if streak_bonus > 0 else 'sign_in'
                description = f"每日签到" + (f"（连续{new_streak}天奖励+{streak_bonus}）" if streak_bonus > 0 else "")
                
                cursor.execute("""
                    INSERT INTO points_history (user_id, points_change, reason, description)
                    VALUES (%s, %s, %s, %s)
                """, (telegram_id, total_points, reason, description))
                
                # 6.3 更新或插入用户积分汇总
                cursor.execute("""
                    INSERT INTO user_points (user_id, total_points, sign_in_count, last_sign_in, sign_in_streak, max_streak)
                    VALUES (%s, %s, 1, NOW(), %s, %s)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET
                        total_points = user_points.total_points + EXCLUDED.total_points,
                        sign_in_count = user_points.sign_in_count + 1,
                        last_sign_in = NOW(),
                        sign_in_streak = EXCLUDED.sign_in_streak,
                        max_streak = GREATEST(user_points.max_streak, EXCLUDED.sign_in_streak),
                        updated_at = NOW()
                """, (telegram_id, total_points, new_streak, new_streak))
                
                # 6.4 确保用户存在于users表
                cursor.execute("""
                    INSERT INTO users (telegram_id, username, first_name, last_active)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (telegram_id) 
                    DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_active = NOW()
                """, (telegram_id, username, first_name))
                
                conn.commit()
                
                logger.info(f"✅ 用户 {telegram_id} 签到成功，获得 {total_points} 积分，连续 {new_streak} 天")
                return True, f"签到成功！获得 {total_points} 积分", total_points
                
            except Exception as e:
                logger.error(f"❌ 签到操作失败: {e}")
                conn.rollback()
                return False, f"签到失败: {str(e)}", 0
                
        except Exception as e:
            logger.error(f"❌ 签到过程出错: {e}")
            return False, f"签到失败: {str(e)}", 0
        finally:
            cls.return_connection(conn)
    
    @classmethod
    def get_user_points_info(cls, telegram_id: int):
        """获取用户积分详细信息"""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # 获取积分汇总信息
            cursor.execute("""
                SELECT * FROM v_user_points_summary 
                WHERE telegram_id = %s
            """, (telegram_id,))
            
            summary = cursor.fetchone()
            
            if not summary:
                return {
                    'total_points': 0,
                    'signed_in_today': False,
                    'sign_in_count': 0,
                    'current_streak': 0,
                    'max_streak': 0,
                    'last_sign_in': None
                }
            
            # 获取最近7天签到情况
            cursor.execute("""
                SELECT 
                    sign_date,
                    points_awarded,
                    CASE 
                        WHEN sign_date = CURRENT_DATE THEN 'today'
                        WHEN sign_date = CURRENT_DATE - INTERVAL '1 day' THEN 'yesterday'
                        ELSE TO_CHAR(sign_date, 'MM-DD')
                    END as display_date
                FROM daily_sign_ins 
                WHERE user_id = %s 
                AND sign_date >= CURRENT_DATE - INTERVAL '6 days'
                ORDER BY sign_date DESC
            """, (telegram_id,))
            
            recent_sign_ins = cursor.fetchall()
            
            # 获取最近5条积分记录
            cursor.execute("""
                SELECT 
                    points_change,
                    reason,
                    description,
                    created_at,
                    TO_CHAR(created_at, 'MM-DD HH24:MI') as time_str
                FROM points_history 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT 5
            """, (telegram_id,))
            
            recent_transactions = cursor.fetchall()
            
            # 计算排名（简化版）
            cursor.execute("""
                SELECT COUNT(*) + 1 as rank
                FROM user_points 
                WHERE total_points > (SELECT total_points FROM user_points WHERE user_id = %s)
            """, (telegram_id,))
            
            rank_result = cursor.fetchone()
            rank = rank_result['rank'] if rank_result else 1
            
            result = dict(summary)
            result['recent_sign_ins'] = recent_sign_ins
            result['recent_transactions'] = recent_transactions
            result['rank'] = rank
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 获取积分信息失败: {e}")
            return None
        finally:
            cls.return_connection(conn)
    
    @classmethod
    def get_top_users(cls, limit: int = 10):
        """获取积分排行榜"""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    up.user_id,
                    u.username,
                    u.first_name,
                    up.total_points,
                    up.sign_in_count,
                    up.sign_in_streak,
                    up.last_sign_in,
                    ROW_NUMBER() OVER (ORDER BY up.total_points DESC, up.sign_in_streak DESC) as rank
                FROM user_points up
                JOIN users u ON up.user_id = u.telegram_id
                ORDER BY up.total_points DESC, up.sign_in_streak DESC
                LIMIT %s
            """, (limit,))
            
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"❌ 获取排行榜失败: {e}")
            return []
        finally:
            cls.return_connection(conn)
