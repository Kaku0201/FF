import os
import json
from datetime import date, time, datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

# — 환경변수 & config 파일 경로 —
CONFIG_FILE = "config.json"

# config 로드/저장 함수 —

def load_config():
    if not os.path.isfile(CONFIG_FILE):
        cfg = {
            "channel_id": int(os.getenv("CHANNEL_ID", 0)),
            "alerts": {
                # 전장알림, 청약신청알림(시작+마감10분전), 청약추첨알림
                "battle": True,
                "application": True,
                "raffle": True
            }
        }
        save_config(cfg)
        return cfg
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

# .env 로드
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Intents 설정
intents = discord.Intents.default()
intents.message_content = True

# Bot 초기화
bot = commands.Bot(command_prefix="!", intents=intents)

# 설정 로드
config = load_config()

# — 전장 순환 설정 —
BATTLEFIELDS = [
    "봉인된 바위섬(쟁탈전)",
    "영광의 평원(쇄빙전)",
    "온살 하카이르(계절끝 합전)"
]
BASE_DATE = date(2025, 4, 27)       # 기준일
KST       = ZoneInfo("Asia/Seoul")

# — 청약 주기 설정 —
APP_LEN    = 5  # 신청 기간 (일수)
RAFFLE_LEN = 4  # 추첨 기간
CYCLE_LEN  = APP_LEN + RAFFLE_LEN
CYCLE_BASE = date(2025, 4, 27)     # 첫 사이클 기준일

def fmt(d: date) -> str:
    return f"{d.month}월 {d.day}일"

# — 자정(00:00) 태스크 —
@tasks.loop(time=time(hour=0, minute=0, tzinfo=KST))
async def at_midnight():
    today   = datetime.now(KST).date()
    channel = bot.get_channel(config.get("channel_id"))
    if channel is None:
        print(f"[Error] 알림 채널이 설정되지 않았거나 찾을 수 없습니다.")
        return

    # 전장알림
    if config["alerts"]["battle"]:
        idx = (today - BASE_DATE).days % len(BATTLEFIELDS)
        await channel.send(f"오늘의 전장은 [{BATTLEFIELDS[idx]}] 입니다. 🎮")

    # 사이클 위치 계산
    cycle_day = (today - CYCLE_BASE).days % CYCLE_LEN
    # 청약신청알림 (시작)
    if cycle_day == 0 and config["alerts"]["application"]:
        start, end = today, today + timedelta(days=APP_LEN-1)
        await channel.send(f"🔔 청약 신청날 [{fmt(start)} ~ {fmt(end)}] 시작되었습니다!")
    # 청약추첨알림 (시작)
    elif cycle_day == APP_LEN and config["alerts"]["raffle"]:
        start, end = today, today + timedelta(days=RAFFLE_LEN-1)
        await channel.send(f"🔔 청약 추첨확인 [{fmt(start)} ~ {fmt(end)}] 시작되었습니다!")

@at_midnight.before_loop
async def before_midnight():
    await bot.wait_until_ready()
    print("✅ at_midnight 태스크 시작")

# — 23:50 태스크 (마감 10분 전) —
@tasks.loop(time=time(hour=23, minute=50, tzinfo=KST))
async def at_2350():
    today   = datetime.now(KST).date()
    channel = bot.get_channel(config.get("channel_id"))
    if channel is None:
        return

    cycle_day = (today - CYCLE_BASE).days % CYCLE_LEN
    # 신청 마감 10분 전通知 (마감전10)
    if cycle_day == APP_LEN - 1 and config["alerts"]["application"]:
        await channel.send("⏰ 청약 신청 마감까지 10분 남았습니다!")

@at_2350.before_loop
async def before_2350():
    await bot.wait_until_ready()
    print("✅ at_2350 태스크 시작")

# — 슬래시 커맨드: 채널 설정 —
@bot.tree.command(name="setchannel", description="알림 채널을 설정합니다")
@discord.app_commands.default_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    config["channel_id"] = channel.id
    save_config(config)
    await interaction.response.send_message(f"✅ 알림 채널을 {channel.mention} 로 설정했습니다.", ephemeral=True)

# — 슬래시 커맨드: 토글 알림 —
@bot.tree.command(name="toggle", description="알림을 켜거나 끕니다")
@discord.app_commands.default_permissions(administrator=True)
@app_commands.describe(
    alert="알림 종류 (전장알림, 청약신청알림, 청약추첨알림)",
    state="on 또는 off"
)
@app_commands.choices(
    alert=[
        app_commands.Choice(name="전장알림", value="battle"),
        app_commands.Choice(name="청약신청알림", value="application"),
        app_commands.Choice(name="청약추첨알림", value="raffle"),
    ],
)
@app_commands.choices(
    state=[
        app_commands.Choice(name="on", value="on"),
        app_commands.Choice(name="off", value="off"),
    ],
)
async def toggle(interaction: discord.Interaction, alert: str, state: str):
    enabled = (state == "on")
    config["alerts"][alert] = enabled
    save_config(config)
    await interaction.response.send_message(
        f"✅ `{alert}` 알림을 {'활성화' if enabled else '비활성화'}했습니다.", ephemeral=True
    )

# — 슬래시 커맨드: 즉시 알림 (/알려줘) —
@bot.tree.command(name="알려줘", description="오늘의 전장 또는 청약 상황을 바로 보여줍니다")
@app_commands.describe(
    choice="어떤 정보를 원하는지 선택하세요: 전장 또는 청약"
)
@app_commands.choices(
    choice=[
        app_commands.Choice(name="전장", value="battle"),
        app_commands.Choice(name="청약", value="application"),
    ]
)
async def 알려줘(interaction: discord.Interaction, choice: str):
    today = datetime.now(KST).date()
    # 전장 정보
    if choice == "battle":
        idx = (today - BASE_DATE).days % len(BATTLEFIELDS)
        msg = f"오늘의 전장은 [{BATTLEFIELDS[idx]}] 입니다. 🎮"
    # 청약 정보
    else:
        cycle_day = (today - CYCLE_BASE).days % CYCLE_LEN
        if cycle_day < APP_LEN:
            start, end = today, today + timedelta(days=APP_LEN-1-cycle_day)
            msg = f"🔔 청약 신청날 [{fmt(today - timedelta(days=cycle_day))} ~ {fmt(today - timedelta(days=cycle_day) + timedelta(days=APP_LEN-1))}] 현재 {cycle_day+1}일차입니다."
        else:
            # 추첨 기간
            start = (today - timedelta(days=(cycle_day - APP_LEN)))
            end = start + timedelta(days=RAFFLE_LEN-1)
            msg = f"🔔 청약 추첨확인 [{fmt(start)} ~ {fmt(end)}] 현재 {cycle_day-APP_LEN+1}일차입니다."
    await interaction.response.send_message(msg, ephemeral=True)

# — 봇 이벤트 & 실행 —
@bot.event
async def on_ready():
    # 슬래시 커맨드 동기화
    await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    if not at_midnight.is_running():
        at_midnight.start()
    if not at_2350.is_running():
        at_2350.start()

if __name__ == "__main__":
    bot.run(TOKEN)
