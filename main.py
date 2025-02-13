import discord
from discord.ext import commands
from datetime import datetime, timezone
import os
import aiosqlite
from dotenv import load_dotenv
    

allowed_mentions = discord.AllowedMentions(everyone = True)
intents = discord.Intents.all()
status = discord.Status.online


bot = commands.Bot(intents=intents,
                   command_prefix="!",
                   status=status,
                   help_command=None,
                   case_insensitive=True)



invites = {}

@bot.event
async def on_ready():
    print("Clarity bot is ready")
    for guild in bot.guilds:
        invites[guild.id] = await guild.invites()

    async with aiosqlite.connect("verification.sqlite") as connection:
        await connection.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, email TEXT NOT NULL, code TEXT NOT NULL, verified BOOLEAN NOT NULL DEFAULT 0)")
        await connection.commit()
    async with aiosqlite.connect("introduction.sqlite") as connection:
        await connection.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT DEFAULT None, location TEXT DEFAULT None, 
                                 occupation TEXT DEFAULT None, bio TEXT DEFAULT None, goal TEXT DEFAULT None,
                                 skills TEXT DEFAULT None, looking_for TEXT DEFAULT None, long_goal TEXT DEFAULT None,
                                 portfolio_website TEXT DEFAULT None, social_media TEXT DEFAULT None)""")
        await connection.commit()
        
        await connection.execute("CREATE TABLE IF NOT EXISTS msg(msg_id INTEGER PRIMARY KEY, anchor)")
        await connection.commit()


def find_invite_by_code(invite_list, code):
    for inv in invite_list:
        if inv.code == code:
            return inv



@bot.event
async def on_member_join(member):
    invites_before_join = invites.get(member.guild.id, [])
    invites_after_join = await member.guild.invites()

    for invite in invites_before_join:
        if invite.uses < find_invite_by_code(invites_after_join, invite.code).uses:

            channel = discord.utils.get(member.guild.channels, name='joined')
            created_at = member.created_at.strftime("%d. %b %Y %H:%M:%S")
            now_utc = datetime.now(timezone.utc)
            account_age = now_utc - member.created_at

            days = account_age.days
            hours, remainder = divmod(account_age.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            embed = discord.Embed(color=discord.Color.blue(), description=f"{member.mention} just joined the server.\n\n**Name:** {member.name}\n**ID:** {member.id}")
            embed.add_field(name=f"Invited by", value=f"{invite.inviter.mention} ({invite.inviter.name})\n({invite.uses +1} uses)")
            embed.add_field(name=f"Invite code", value=f"{invite.code}\n({invite.uses +1} uses)")
            embed.add_field(name=f"Account created:", value=f"{created_at}")
            embed.add_field(name=f"Account age:", value=f"{days} days, {hours} hours and {seconds} seconds")
            embed.set_author(name=member.name, icon_url=member.display_avatar)
            embed.timestamp = discord.utils.utcnow()

            embed.set_image(url=member.display_avatar)
                
            await channel.send(embed=embed)
            invites[member.guild.id] = invites_after_join

            async with aiosqlite.connect("verification.sqlite") as connection:
                cursor = await connection.cursor()
                
                await cursor.execute("SELECT verified FROM users WHERE user_id = ?", (member.id,))
                user_verify_status = await cursor.fetchone()

                if user_verify_status:
                    if user_verify_status[0] == 1: # falls der User bereits verifiziert ist (z.B wenn er sich verifiziert hat, den server verlässt und wieder beitritt)
                        await member.add_roles(member.guild.get_role(1290383638680305777)) 
                        await member.remove_roles(member.guild.get_role(1149437289034960906))
                
            return

@bot.event
async def on_member_remove(member):
    invites[member.guild.id] = await member.guild.invites()



if __name__ == "__main__":
    for filename in os.listdir("util"):
        if filename.endswith(".py"):
            print(f"loaded: {filename}")
            bot.load_extension(f"util.{filename[:-3]}") # fügt alle .py dateien zum Bot hinzu


load_dotenv()
bot.run(os.getenv("BOT_TOKEN"))