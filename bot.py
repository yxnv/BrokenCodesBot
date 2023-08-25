import discord
from discord.ext import commands, tasks
import aiohttp
import time
import asyncio
from discord import option

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    intents=intents,
)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="Generating Broken Codes // made by yxnv#0"))

async def get_roblox_item_name(item_id):
    base_url = "https://api.roblox.com/"
    endpoint = f"marketplace/productinfo?assetId={item_id}"

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}{endpoint}", timeout=5, allow_redirects=False) as response:
            if response.ok:
                data = await response.json()
                if "Name" in data:
                    return data["Name"]
                else:
                    return "Item not found"
            else:
                return "Error fetching data"

async def get_roblox_item_thumbnail(item_id):
    base_url = "https://thumbnails.roblox.com/v1/assets"
    params = {
        "assetIds": item_id,
        "returnPolicy": "PlaceHolder",
        "size": "140x140",
        "format": "Png",
        "isCircular": "false"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}", params=params, timeout=5, allow_redirects=False) as response:
            if response.ok:
                data = await response.json()
                if "data" in data and len(data["data"]) > 0:
                    thumbnail_url = data["data"][0]["imageUrl"]
                    return thumbnail_url
                else:
                    return "Item thumbnail not found"
            else:
                return "Error fetching data"


class CodeGenerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.generators = {}  # Dictionary to store user-specific generators
        self.log_channel = 1143937435579990087

    @commands.slash_command(
        guild_ids=[]
    )
    @commands.has_permissions(administrator=True)
    @option("secret", description="Secret from BrokenCode Game. DO NOT SHARE THIS WITH ANY PERSON!!!")
    @option("interval", description="How many seconds per code? (ex. 5s, 1m)")
    @option("stock", description="How much stock per code")
    @option("channel",discord.TextChannel,description="Select a channel where the codes will be sent to")
    @option("spoiler", description="Whether generated codes should be spoilers (ex. true, false, yes, no)")
    async def generatecodes(self, ctx, secret, interval, stock, channel, spoiler):
        if ctx.author.id in self.generators:
            await ctx.send("Code generation is already running for you.")
            return

        interval_in_seconds = self.parse_interval(interval)
        if interval_in_seconds is None:
            await ctx.send("Invalid interval format. Please use Xs, Xm, or Xh.")
            return

        target_channel = channel
        if target_channel is None:
            await ctx.send("Invalid channel selection. Please select a valid channel.")
            return

        async def generate_loop():
            base_url = "https://brkn.codes/"
            generate_endpoint = "public/generatecode"
            getinfo_endpoint = "public/getinfo"
            generated_count = 0

            while self.generators.get(ctx.author.id, False):
                async with aiohttp.ClientSession() as session:
                    print("Generating code...")
                    generate_params = {
                        "stock": stock,
                        "secret": secret
                    }

                    id_params = {
                        "secret": secret
                    }
                    generate_response = await session.get(f"{base_url}{generate_endpoint}", params=generate_params, timeout=5, allow_redirects=False)
                    id_response = await session.get(f'{base_url}{getinfo_endpoint}',params=id_params, timeout=5, allow_redirects=False)

                    if id_response.ok:
                        print(id_response.status)
                        id_data = await id_response.json()
                        item_id = id_data["ProductId"]
                    
                    if generate_response.ok:
                        generate_data = await generate_response.json()
                        if "Code" in generate_data and "Code" in generate_data["Code"]:
                            generated_code = generate_data["Code"]["Code"]

                            getinfo_params = {
                                "secret": secret
                            }

                            getinfo_response = await session.get(f"{base_url}{getinfo_endpoint}", params=getinfo_params, timeout=5, allow_redirects=False)

                            if getinfo_response.ok:
                                getinfo_data = await getinfo_response.json()
                                if "Item" in getinfo_data and "Name" in getinfo_data["Item"]:
                                    item_name = getinfo_data["Item"]["Name"]

                                    item_thumbnail = get_roblox_item_thumbnail(item_id)
                                    if not item_thumbnail.startswith("Error"):
                                        spoiler_option = True if spoiler == "true" else False
                                        embed = discord.Embed(
                                            title=f"Code has been generated for [Item {item_id}] - {item_name}",
                                            description=f"{'||' if spoiler_option else ''}{generated_code}{'||' if spoiler_option else ''}",
                                            color=discord.Color.green()
                                        )
                                        embed.set_footer(text=f"Generated {generated_count + 1} codes | Interval: {interval} | Stock: {stock}")
                                        embed.set_thumbnail(url=item_thumbnail)

                                        await target_channel.send(embed=embed)

                                        generated_count += 1
                                    else:
                                        await ctx.send("Error fetching item thumbnail.")
                                else:
                                    await ctx.send("Failed to retrieve item info from response.")
                            else:
                                await ctx.send(f"Getinfo request failed with status code: {getinfo_response.status_code}")
                        else:
                            await ctx.send("Failed to retrieve code from response.")
                    else:
                        await ctx.send(f"Generate request failed with status code: {generate_response.status_code}")

                    await asyncio.sleep(interval_in_seconds)

            await ctx.send("Code generation stopped.")

        self.generators[ctx.author.id] = True
        await ctx.send("Code generation started. Say \"stop\" to stop the generation.")

        self.bot.loop.create_task(generate_loop())

    def parse_interval(self, interval):
        unit = interval[-1]
        value = interval[:-1]
        try:
            value = int(value)
            if unit == 's':
                return value
            elif unit == 'm':
                return value * 60
            elif unit == 'h':
                return value * 3600
            else:
                return None
        except ValueError:
            return None

    @commands.slash_command(
        guild_ids=[]
    )
    async def stop(self, ctx):
        if ctx.author.id in self.generators:
            self.generators[ctx.author.id] = False
            await ctx.send("Code generation stopped.")
            del self.generators[ctx.author.id]
        else:
            await ctx.send("You are not currently generating codes.")

bot.add_cog(CodeGenerator(bot))

bot.run('<<BOT TOKEN GOES HERE>>')