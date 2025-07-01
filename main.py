@bot.event
async def on_ready():
    print(f"✅ 봇 온라인: {bot.user}")
    if not daily_delete_messages.is_running():
        daily_delete_messages.start()

if __name__ == "__main__":
    import asyncio
    TOKEN = os.environ['DISCORD_TOKEN']
    asyncio.run(bot.start(TOKEN))
