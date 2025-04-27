import os
import sqlite3
from dotenv import load_dotenv

# 환경변수(.env) 로드
load_dotenv()

# DATABASE_URL 환경변수, 기본값은 data/bot.db
DATABASE_URL = os.getenv("DATABASE_URL", "data/bot.db")

def get_connection():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    최초 1회 실행: guild_settings 테이블 생성
    """
    conn = get_connection()
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            alert_battle BOOLEAN NOT NULL DEFAULT 1,
            alert_application BOOLEAN NOT NULL DEFAULT 1,
            alert_raffle BOOLEAN NOT NULL DEFAULT 1
        );
        """
        )
    conn.close()

def get_settings(guild_id):
    conn = get_connection()
    cur = conn.execute(
        "SELECT * FROM guild_settings WHERE guild_id = ?", (str(guild_id),)
    )
    row = cur.fetchone()
    conn.close()
    return row

def upsert_settings(
    guild_id,
    channel_id=None,
    alert_battle=None,
    alert_application=None,
    alert_raffle=None
):
    """
    기존 레코드가 있으면 UPDATE, 없으면 INSERT
    """
    existing = get_settings(guild_id)
    conn = get_connection()
    with conn:
        if existing:
            fields = []
            params = []
            if channel_id is not None:
                fields.append("channel_id = ?")
                params.append(str(channel_id))
            if alert_battle is not None:
                fields.append("alert_battle = ?")
                params.append(int(alert_battle))
            if alert_application is not None:
                fields.append("alert_application = ?")
                params.append(int(alert_application))
            if alert_raffle is not None:
                fields.append("alert_raffle = ?")
                params.append(int(alert_raffle))
            params.append(str(guild_id))
            conn.execute(
                f"UPDATE guild_settings SET {', '.join(fields)} WHERE guild_id = ?", params
            )
        else:
            conn.execute(
                "INSERT INTO guild_settings (guild_id, channel_id, alert_battle, alert_application, alert_raffle) VALUES (?, ?, ?, ?, ?)",
                (
                    str(guild_id),
                    str(channel_id or 0),
                    int(alert_battle or True),
                    int(alert_application or True),
                    int(alert_raffle or True),
                )
            )
    conn.close()