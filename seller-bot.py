import discord
import random
import string
import os
from discord.ext import commands
from flask import Flask
from threading import Thread

# ---------- Keep Alive ----------
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# ---------- Bot Setup ----------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.dm_messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- ID Generator ----------
def generate_id(prefix: str, length: int = 8) -> str:
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f"{prefix}{suffix}"

# ---------- In-Memory ID Store ----------
user_id_codes = {}

# ---------- Role Assignment + DM ----------
async def assign_role_and_dm(ctx, user_id: int, role_name: str, prefix: str):
    guild = ctx.guild
    try:
        member = await guild.fetch_member(user_id)
    except discord.NotFound:
        await ctx.send(f"❌ No member found with ID `{user_id}`.")
        return
    except discord.Forbidden:
        await ctx.send("🚫 Bot lacks permission to fetch that member.")
        return

    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        try:
            role = await guild.create_role(name=role_name)
            await ctx.send(f"🛠️ Created role `{role_name}`.")
        except discord.Forbidden:
            await ctx.send("🚫 Bot lacks permission to create roles.")
            return

    try:
        await member.add_roles(role)
        await ctx.send(f"✅ Assigned role `{role_name}` to <@{user_id}>.")
    except discord.Forbidden:
        await ctx.send("🚫 Bot lacks permission to assign that role.")
        return

    id_code = generate_id(prefix)
    user_id_codes[user_id] = id_code

    try:
        await member.send(
            f"🎉 You’ve been accepted as a **{role_name}**!\n"
            f"🔐 Your ID Portal Code: `{id_code}`"
        )
        await ctx.send(f"📨 DM sent to {member.display_name}")
    except discord.Forbidden:
        await ctx.send(f"🚫 Could not DM {member.display_name}. DMs may be disabled.")

# ---------- Accept Commands ----------
@bot.command()
@commands.has_permissions(administrator=True)
async def acceptseller(ctx, user_id: int):
    await assign_role_and_dm(ctx, user_id, "Seller", "SE")

@bot.command()
@commands.has_permissions(administrator=True)
async def acceptauthenticator(ctx, user_id: int):
    await assign_role_and_dm(ctx, user_id, "Authenticator", "AU")

@bot.command()
@commands.has_permissions(administrator=True)
async def acceptstaff(ctx, user_id: int):
    await assign_role_and_dm(ctx, user_id, "Staff", "ST")

# ---------- Admin-Only Role Changer ----------
@bot.command()
@commands.has_permissions(administrator=True)
async def changerole(ctx, user_id: int, *, role_name: str):
    guild = ctx.guild
    try:
        member = await guild.fetch_member(user_id)
    except discord.NotFound:
        await ctx.send(f"❌ No member found with ID `{user_id}`.")
        return
    except discord.Forbidden:
        await ctx.send("🚫 Bot lacks permission to fetch that member.")
        return

    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        try:
            role = await guild.create_role(name=role_name)
            await ctx.send(f"🛠️ Created role `{role_name}`.")
        except discord.Forbidden:
            await ctx.send("🚫 Bot lacks permission to create roles.")
            return

    # Remove all roles except @everyone and the new role
    roles_to_remove = [r for r in member.roles if r != guild.default_role and r != role]
    try:
        await member.remove_roles(*roles_to_remove)
        await member.add_roles(role)
        await ctx.send(f"✅ Changed roles for <@{user_id}> to `{role_name}`.")
    except discord.Forbidden:
        await ctx.send("🚫 Bot lacks permission to modify roles.")
    except discord.HTTPException:
        await ctx.send("⚠️ Failed to update roles due to network error.")

# ---------- Admin-Only ID Lookup ----------
@bot.command()
@commands.has_permissions(administrator=True)
async def getid(ctx, user_id: int):
    id_code = user_id_codes.get(user_id)
    if id_code:
        await ctx.send(f"🔍 ID for user `{user_id}`: `{id_code}`")
    else:
        await ctx.send(f"❌ No ID code found for user `{user_id}`.")

# ---------- Listing Command ----------
@bot.command()
async def list(ctx, *, item: str):
    seller_input_channel_id = 1416580355346923602  # Replace with your seller-only input channel ID
    listings_output_channel_id = 1416580327316389898  # Replace with your public listings channel ID

    if ctx.channel.id != seller_input_channel_id:
        await ctx.send("🚫 You can only use this command in the designated seller input channel.")
        return

    customer_role = discord.utils.get(ctx.guild.roles, name="Customer")
    if customer_role in ctx.author.roles:
        await ctx.send("❌ You are marked as a Customer and cannot post listings.")
        return

    listings_channel = bot.get_channel(listings_output_channel_id)
    if listings_channel:
        embed = discord.Embed(
            title="🛍️ New Listing",
            description=item,
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Listed by {ctx.author.display_name}")
        await listings_channel.send(embed=embed)
        await ctx.send("✅ Listing posted successfully.")
    else:
        await ctx.send("⚠️ Listings channel not found. Check your channel ID.")

# ---------- Keep Alive ----------
keep_alive()

# ---------- Run Bot ----------
bot.run(os.getenv("DISCORD_TOKEN"))

