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

# 봇 초기화
bot = commands.Bot(command_prefix="!", intents=intents)

# 설정 로드
config = load_config()

# — 전장 순환 설정 —
BATTLEFIELDS = [
    "봉인된 바위섬(쟁탈전)",
    "영광의 평원(쇄빙전)",
    "온살 하카이르(계절끝 합전)"
]
BASE_DATE   = date(2025, 4, 27)
KST         = ZoneInfo("Asia/Seoul")

# — 청약 주기 설정 —
APP_LEN    = 5
RAFFLE_LEN = 4
CYCLE_LEN  = APP_LEN + RAFFLE_LEN
CYCLE_BASE = date(2025, 4, 27)

def fmt(d: date) -> str:
    return f"{d.month}월 {d.day}일"

# — 자정 태스크 —
@tasks.loop(time=time(hour=0, minute=0, tzinfo=KST))
async def at_midnight():
    today = datetime.now(KST).date()
    channel = bot.get_channel(config.get("channel_id"))
    if not channel:
        return
    # 전장 알림 임베드
    if config["alerts"]["battle"]:
        idx = (today - BASE_DATE).days % len(BATTLEFIELDS)
        embed = discord.Embed(
            title="오늘의 전장",
            description=f"[{BATTLEFIELDS[idx]}]",
            color=discord.Color.blurple()
        )
        embed.set_footer(text=str(today))
        await channel.send(embed=embed)
    # 청약 알림 임베드
    cycle_day = (today - CYCLE_BASE).days % CYCLE_LEN
    if cycle_day == 0 and config["alerts"]["application"]:
        start, end = today, today + timedelta(days=APP_LEN-1)
        embed = discord.Embed(
            title="청약 신청날",
            description=f"{fmt(start)} ~ {fmt(end)} 시작되었습니다!",
            color=discord.Color.green()
        )
        await channel.send(embed=embed)
    elif cycle_day == APP_LEN and config["alerts"]["raffle"]:
        start, end = today, today + timedelta(days=RAFFLE_LEN-1)
        embed = discord.Embed(
            title="청약 추첨확인",
            description=f"{fmt(start)} ~ {fmt(end)} 시작되었습니다!",
            color=discord.Color.gold()
        )
        await channel.send(embed=embed)

@at_midnight.before_loop
async def before_midnight():
    await bot.wait_until_ready()

# — 마감 10분 전 —
@tasks.loop(time=time(hour=23, minute=50, tzinfo=KST))
async def at_2350():
    today = datetime.now(KST).date()
    channel = bot.get_channel(config.get("channel_id"))
    if not channel or not config["alerts"]["application"]:
        return
    cycle_day = (today - CYCLE_BASE).days % CYCLE_LEN
    if cycle_day == APP_LEN - 1:
        embed = discord.Embed(
            title="마감 임박",
            description="청약 신청 마감까지 10분 남았습니다!",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)

@at_2350.before_loop
async def before_2350():
    await bot.wait_until_ready()

# — 슬래시 커맨드 등록 및 on_ready —
@bot.event
async def on_ready():
    await bot.tree.sync()
    if not at_midnight.is_running():
        at_midnight.start()
    if not at_2350.is_running():
        at_2350.start()
    print(f"Logged in as {bot.user}")

# 채널 설정 슬래시 커맨드
@bot.tree.command(name="채널설정", description="알림 채널 설정")
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    config["channel_id"] = channel.id
    save_config(config)
    await interaction.response.send_message(
        f"알림 채널을 {channel.mention}로 설정했습니다.", ephemeral=True
    )

# 알림 토글 슬래시 커맨드
@bot.tree.command(name="알림설정", description="알림 on/off")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(alert="알림 종류", state="on/off")
@app_commands.choices(alert=[
    app_commands.Choice(name="전장알림", value="battle"),
    app_commands.Choice(name="청약신청알림", value="application"),
    app_commands.Choice(name="청약추첨알림", value="raffle"),
])
@app_commands.choices(state=[
    app_commands.Choice(name="on", value="on"),
    app_commands.Choice(name="off", value="off"),
])
async def toggle(interaction: discord.Interaction, alert: str, state: str):
    enabled = (state == "on")
    config["alerts"][alert] = enabled
    save_config(config)
    await interaction.response.send_message(
        f"`{alert}` 알림 {'활성화' if enabled else '비활성화'} 되었습니다.",
        ephemeral=True
    )

# 즉시 정보 조회 슬래시 커맨드
@bot.tree.command(name="알려줘", description="오늘의 전장 또는 청약 상황을 보여줍니다")
@app_commands.describe(choice="전장 또는 청약을 선택")
@app_commands.choices(choice=[
    app_commands.Choice(name="전장", value="battle"),
    app_commands.Choice(name="청약", value="application"),
])
async def 알려줘(interaction: discord.Interaction, choice: str):
    today = datetime.now(KST).date()
    if choice == "battle":
        idx = (today - BASE_DATE).days % len(BATTLEFIELDS)
        embed = discord.Embed(
            title="오늘의 전장",
            description=f"[{BATTLEFIELDS[idx]}]",
            color=discord.Color.blurple()
        )
    else:
        cycle_day = (today - CYCLE_BASE).days % CYCLE_LEN
        if cycle_day < APP_LEN:
            start, end = today - timedelta(days=cycle_day), (today - timedelta(days=cycle_day)) + timedelta(days=APP_LEN-1)
            desc = f"[{fmt(start)} ~ {fmt(end)}] 신청 {cycle_day+1}일차"
            embed = discord.Embed(title="청약 신청날", description=desc, color=discord.Color.green())
        else:
            start = today - timedelta(days=cycle_day - APP_LEN)
            end = start + timedelta(days=RAFFLE_LEN-1)
            desc = f"[{fmt(start)} ~ {fmt(end)}] 추첨 {cycle_day-APP_LEN+1}일차"
            embed = discord.Embed(title="청약 추첨확인", description=desc, color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, ephemeral=True)

# bot 실행
if __name__ == "__main__":
    bot.run(TOKEN)
