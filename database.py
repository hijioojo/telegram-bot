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
        
        -- 创建索引以提高查询性能
        CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
        """
        
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(create_tables_sql)
            conn.commit()
            logger.info("✅ 数据库表初始化成功")
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