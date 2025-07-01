import os
import discord
from discord.ext import commands, tasks
import datetime
import re
import json

# ---- 환경변수에서 토큰 읽기 ----
TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

SETTINGS_FILE = 'settings.json'

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

settings = load_settings()

COOKING_PRICE_RANGES = {
    '무트볼': (37,51), '베이글': (37,51), '타코': (37,51), '고구마맛탕': (37,51),
    '해물카레': (25,34), '고로케': (16,22),
    '라면': (61,85), '콘 마카로니': (61,85),
    '감자튀김': (58,80), '브리또': (58,80),
    '미역국': (54,74),
    '와플': (61,85), '마늘빵': (61,85),
    '블루베리 치즈케이크': (58,80), '스테이크': (58,80),
    '전복죽': (71,97),
    '샌드위치': (103,142), '핫도그': (103,142),
    '과일케이크': (65,89), '오믈렛': (65,89), '로스트 치킨': (65,89), '고구마 팬케이크': (65,89),
    '홍합파스타': (108,149)
}

RUNE_PRICE_RANGES = {
    '투시': (206,240), '저항': (253,296), '치유': (292,341), '호흡': (306,357),
    '성급': (378,441), '반감': (402,469), '경험': (2192,2557)
}

sent_messages = {
    'cooking': {},  # 요리 고점 메시지 저장용
    'rune': {}      # 룬 고점 메시지 저장용
}

@bot.command(name='요리변동채널', aliases=['setpricechannel'])
@commands.has_permissions(administrator=True)
async def set_price_channel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)
    if guild_id not in settings:
        settings[guild_id] = {}
    settings[guild_id]['cooking_price_channel'] = channel.id
    save_settings(settings)
    await ctx.send(f"✅ 요리 변동가격 채널이 {channel.mention} 으로 설정되었습니다.")

@bot.command(name='요리고점채널', aliases=['setalertchannel'])
@commands.has_permissions(administrator=True)
async def set_alert_channel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)
    if guild_id not in settings:
        settings[guild_id] = {}
    settings[guild_id]['cooking_alert_channel'] = channel.id
    save_settings(settings)
    await ctx.send(f"✅ 요리 고점 알림 채널이 {channel.mention} 으로 설정되었습니다.")

@bot.command(name='룬변동채널', aliases=['setrunepricechannel'])
@commands.has_permissions(administrator=True)
async def set_rune_price_channel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)
    if guild_id not in settings:
        settings[guild_id] = {}
    settings[guild_id]['rune_price_channel'] = channel.id
    save_settings(settings)
    await ctx.send(f"✅ 룬 변동가격 채널이 {channel.mention} 으로 설정되었습니다.")

@bot.command(name='룬고점채널', aliases=['setrunealertchannel'])
@commands.has_permissions(administrator=True)
async def set_rune_alert_channel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)
    if guild_id not in settings:
        settings[guild_id] = {}
    settings[guild_id]['rune_alert_channel'] = channel.id
    save_settings(settings)
    await ctx.send(f"✅ 룬 고점 알림 채널이 {channel.mention} 으로 설정되었습니다.")

def parse_cooking_message(content):
    pattern = r'🍳\[(.+?)\] \| (\d+) → (\d+)'
    return re.findall(pattern, content)

def parse_rune_message(content):
    pattern = r'🧪\[룬 ㅣ (.+?)\] \| (\d+) → (\d+)'
    return re.findall(pattern, content)

def get_cooking_tier(item):
    price = COOKING_PRICE_RANGES.get(item)
    if not price:
        return None
    low, high = price
    if low >= 103:
        return 4
    if low >= 71:
        return 3
    if low >= 54:
        return 2
    if low >= 16:
        return 1
    return None

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    guild_id = str(message.guild.id)
    guild_settings = settings.get(guild_id, {})

    cooking_price_channel = guild_settings.get('cooking_price_channel')
    cooking_alert_channel = guild_settings.get('cooking_alert_channel')
    if cooking_price_channel and cooking_alert_channel and message.channel.id == cooking_price_channel:
        matches = parse_cooking_message(message.content)
        if matches:
            await process_cooking_prices(guild_id, cooking_alert_channel, matches)

    rune_price_channel = guild_settings.get('rune_price_channel')
    rune_alert_channel = guild_settings.get('rune_alert_channel')
    if rune_price_channel and rune_alert_channel and message.channel.id == rune_price_channel:
        matches = parse_rune_message(message.content)
        if matches:
            await process_rune_prices(guild_id, rune_alert_channel, matches)

    await bot.process_commands(message)

async def process_cooking_prices(guild_id, alert_channel_id, matches):
    prices = []
    for item, old_p, new_p in matches:
        new_p = int(new_p)
        if item not in COOKING_PRICE_RANGES:
            continue
        low, high = COOKING_PRICE_RANGES[item]
        prices.append((item, new_p, high))

    high_items = []
    one_less_items = []

    for item, price, max_price in prices:
        if price == max_price:
            high_items.append((item, price))
        elif price == max_price - 1:
            one_less_items.append((item, price))

    if not high_items and not one_less_items:
        return

    channel = bot.get_channel(alert_channel_id)
    if not channel:
        return

    tiers = {1:[], 2:[], 3:[], 4:[]}
    for item, price in high_items + one_less_items:
        tier = get_cooking_tier(item)
        if tier:
            tiers[tier].append((item, price))

    lines = ["# 📢 **🍳요리ㅣ고점알림봇 알림** 📢", ""]
    for tier in range(1, 5):
        if not tiers[tier]:
            continue
        lines.append(f"▶ {tier}차 요리")

        tier_high = [x for x in tiers[tier] if x in high_items]
        if tier_high:
            lines.append("🥇 최고점 요리")
            for i, p in tier_high:
                lines.append(f"- {i} ({p}원)")

        tier_one_less = [x for x in tiers[tier] if x in one_less_items]
        if tier_one_less:
            lines.append("🟡 -1원 차이 요리")
            for i, p in tier_one_less:
                lines.append(f"- {i} ({p}원)")

        lines.append("")

    sent = await channel.send('\n'.join(lines))

    if guild_id not in sent_messages['cooking']:
        sent_messages['cooking'][guild_id] = []
    sent_messages['cooking'][guild_id].append(sent)

async def process_rune_prices(guild_id, alert_channel_id, matches):
    high_runes = []
    within_10_runes = []

    for rune, old_p, new_p in matches:
        new_p = int(new_p)
        if rune not in RUNE_PRICE_RANGES:
            continue
        _, max_price = RUNE_PRICE_RANGES[rune]
        if new_p == max_price:
            high_runes.append((rune, new_p, 0))
        elif max_price - 10 <= new_p < max_price:
            diff = max_price - new_p
            within_10_runes.append((rune, new_p, diff))

    if not high_runes and not within_10_runes:
        return

    channel = bot.get_channel(alert_channel_id)
    if not channel:
        return

    lines = ["# 📢 **🧪룬ㅣ고점알림봇 알림** 📢", ""]

    if high_runes:
        lines.append("🥇 최고점 룬")
        for r, p, diff in high_runes:
            lines.append(f"- {r} ({p}원) (0원)")

    if within_10_runes:
        lines.append("🟡 -10원 이내 룬")
        for r, p, diff in within_10_runes:
            lines.append(f"- {r} ({p}원) (-{diff}원)")

    lines.append("")

    sent = await channel.send('\n'.join(lines))

    if guild_id not in sent_messages['rune']:
        sent_messages['rune'][guild_id] = []
    sent_messages['rune'][guild_id].append(sent)

@tasks.loop(time=datetime.time(hour=23, minute=58))
async def daily_delete_messages():
    for category in ['cooking', 'rune']:
        for guild_id, messages in list(sent_messages[category].items()):
            from discord.errors import NotFound
            channel_id_key = 'cooking_alert_channel' if category == 'cooking' else 'rune_alert_channel'
            guild_settings = settings.get(guild_id, {})
            alert_channel_id = guild_settings.get(channel_id_key)
            if not alert_channel_id:
                continue
            for msg in messages:
                try:
                    await msg.delete()
                except Exception as e:
                    print(f"메시지 삭제 실패: {e}")
            sent_messages[category][guild_id] = []

@bot.event
async def on_ready():
    print(f"✅ 봇 온라인: {bot.user}")
    if not daily_delete_messages.is_running():
        daily_delete_messages.start()

# ---- 실제 실행 ----
if __name__ == "__main__":
    bot.run(TOKEN)
