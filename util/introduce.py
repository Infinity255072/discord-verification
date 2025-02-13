import discord
from discord.ext import commands, tasks
from discord import utils
from discord.utils import get
import aiosqlite
import requests
import asyncio
import os
from dotenv import load_dotenv

sticky_channel_id = 1293262744518398096

BEEHIIV_API_TOKEN = os.getenv("BEEHIIV_API_TOKEN")
BEEHIIV_API_URL = os.getenv("BEEHIIV_API_URL")

async def add_tag(discord_id):
    headers = {
        "Authorization": f"Bearer {BEEHIIV_API_TOKEN}",
        "Content-Type": "application/json"
    }

    async with aiosqlite.connect("verification.sqlite") as connection:
            cursor = await connection.cursor()
            
            await cursor.execute("SELECT email FROM users WHERE user_id = ?", (discord_id,))
            email = await cursor.fetchone()

    email = email[0]

    response = requests.get(f"https://api.beehiiv.com/v2/publications/pub_e40bb0fa-a3c4-47f3-a391-f70ca9312e0f/subscriptions/by_email/{email}?expand%5B%5D=custom_fields", headers=headers)
    if response.status_code in [200, 201]:
        data = response.json()
        
        if "data" in data and data["data"]:
            subscriber_data = data["data"]
        else:
            print("No subscriber data or custom fields found.")
            return
        
    url = f"https://api.beehiiv.com/v2/publications/pub_e40bb0fa-a3c4-47f3-a391-f70ca9312e0f/subscriptions/{subscriber_data['id']}/tags"
    payload = {"tags": ["introduced"]}
    headers = {
        "Authorization": f"Bearer {BEEHIIV_API_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    print(response)
    print(response.status_code)




async def update_beehiiv_subscription(discord_id):
    headers = {
        "Authorization": f"Bearer {BEEHIIV_API_TOKEN}",
        "Content-Type": "application/json"
    }

    async with aiosqlite.connect("verification.sqlite") as connection:
            cursor = await connection.cursor()
            
            await cursor.execute("SELECT email FROM users WHERE user_id = ?", (discord_id,))
            email = await cursor.fetchone()

    email = email[0]

    async with aiosqlite.connect("introduction.sqlite") as connection:
        cursor = await connection.cursor()

        await cursor.execute("""
            SELECT name, location, occupation, bio, goal, skills, looking_for, long_goal, portfolio_website, social_media 
            FROM users WHERE user_id = ?
        """, (discord_id,))
        user_data = await cursor.fetchone()

        if user_data is None:
            print("No data found for the user.")
            return
        
        custom_fields = {
            "Name": user_data[0],
            "Location": user_data[1],
            "Occupation": user_data[2],
            "Bio": user_data[3],
            "Goal Working Towards": user_data[4],
            "Skills": user_data[5] or "-",
            "Looking For": user_data[6] or "-",
            "Long Term Life Goal": user_data[7] or "-",
            "Website": user_data[8] or "-",
            "Social Media": user_data[9] or "-"
        }

    response = requests.get(f"https://api.beehiiv.com/v2/publications/pub_e40bb0fa-a3c4-47f3-a391-f70ca9312e0f/subscriptions/by_email/{email}?expand%5B%5D=custom_fields", headers=headers)
    if response.status_code in [200, 201]:
        data = response.json()
        
        if "data" in data and data["data"]:
            subscriber_data = data["data"]
        else:
            print("No subscriber data or custom fields found.")
            return
        
        update_payload = {
            "email": email,
            "utm_source": "discord",
            "tags": ["discord"], 
            "custom_fields": [{"name": name, "value": value} for name, value in custom_fields.items()]
        }
        
        update_response = requests.put(f"{BEEHIIV_API_URL}/{subscriber_data['id']}", headers=headers, json=update_payload)
        
        if update_response.status_code in [200, 201]:
            print(f"Successfully updated subscription for {email}")
        else:
            print(f"Failed to update subscription: {update_response.status_code} - {update_response.text}")
    else:
        print(f"Failed to fetch subscription: {response.status_code} - {response.text}")



        
        

class StickyMessage(commands.Cog): # sendet eine sticky message. das bedeutet, dass diese nachricht dauerhaft ganz unten bleibt, auch wenn eine andere in den kanal gesendet wird
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(StickyMessageButtonNr1(self.bot))
        self.bot.add_view(StickyMessageButtonNr2(self.bot))


    @commands.Cog.listener()
    async def on_message(self, message):

        if message.channel.id != sticky_channel_id:
            return
        
        if message.author == self.bot.user:
            return
        
        async with aiosqlite.connect("introduction.sqlite") as connection:
            cursor = await connection.cursor()
            await cursor.execute("SELECT msg_id FROM msg WHERE anchor = 1")
                
            sticky_message_id = await cursor.fetchone()
            
            if sticky_message_id:
                sticky_message_id = sticky_message_id[0]
            
                

        
        if sticky_message_id:
            try:
                sticky_message = await message.channel.fetch_message(sticky_message_id)
                await sticky_message.delete()
            except discord.NotFound:
                pass  # Falls die Nachricht bereits gelöscht wurde
        
        embed = discord.Embed(
            description=f"__**Introduce Yourself**__ 👋\n\nGain access to the Clarity Community!\n\nInstead of copy and pasting the format, use our easy form bot!\n\nWe accept/reject introductions to keep scammers and bots out.\nSo we recommend putting effort into your introduction.\n\nClick the button below to introduce yourself.", 
            color=discord.Color.blue()
        )
        new_sticky_message = await message.channel.send(embed=embed, view=StickyMessageButtonNr1(self.bot))

        if sticky_message_id:
            async with aiosqlite.connect("introduction.sqlite") as connection:
                cursor = await connection.cursor()

                await connection.execute(
                    "UPDATE msg SET msg_id = ? WHERE anchor=1", (new_sticky_message.id,)
                )
                await connection.commit()
        else:
            async with aiosqlite.connect("introduction.sqlite") as connection:
                cursor = await connection.cursor()

                await connection.execute(
                    "INSERT OR REPLACE INTO msg(msg_id, anchor) VALUES (?, ?)", (new_sticky_message.id, 1))
                await connection.commit()  



class StickyMessageButtonNr1(discord.ui.View):
    def __init__(self, bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Introduce Yourself", style=discord.ButtonStyle.primary, custom_id="introduce_button1")
    async def button_callback4(self, button, interaction: discord.Interaction):
        await interaction.response.send_modal(StickyMessageModalNr1(self.bot))



class StickyMessageModalNr1(discord.ui.Modal):
    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__(
            discord.ui.InputText(
                label="Name", placeholder="Name", max_length=50, required=True
            ),
            discord.ui.InputText(
                label="Location", placeholder="Country", max_length=50, required=True
            ),
            discord.ui.InputText(
                label="Occupation", placeholder="Occupation", max_length=100, required=True
            ),
            discord.ui.InputText(
                label="Bio", placeholder="Tell us about you", max_length=500, style=discord.InputTextStyle.paragraph, required=True
            ),
            discord.ui.InputText(
                label="Goal You're Working Towards", placeholder="Goal", max_length=500, style=discord.InputTextStyle.paragraph, required=True
            ),
            title="Introduce Yourself"
            ),


    async def callback(self, interaction):
        await interaction.response.send_message("You filled out first half of the introduction!\nFill in the second and final part below!", ephemeral=True, view=StickyMessageButtonNr2(self.bot))

        async with aiosqlite.connect("introduction.sqlite") as connection:
            await connection.execute(
                "INSERT OR REPLACE INTO users(user_id, name, location, occupation, bio, goal) VALUES (?, ?, ?, ?, ?, ?)",  
                (interaction.user.id, str(self.children[0].value), str(self.children[1].value), str(self.children[2].value),
                 str(self.children[3].value), str(self.children[4].value),) # fügt die erste hälfte der Daten schonmal in die Datenbank hinzu
            )
            await connection.commit()
        

class StickyMessageButtonNr2(discord.ui.View):
    def __init__(self, bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot


    @discord.ui.button(label="Part 2", style=discord.ButtonStyle.primary, custom_id="introduce_button2")
    async def button_callback2(self, button, interaction: discord.Interaction):

        async with aiosqlite.connect("introduction.sqlite") as connection:
            cursor = await connection.cursor()

            await cursor.execute("SELECT name FROM users WHERE user_id = ?", (interaction.user.id,))
            user_data = await cursor.fetchone()

            if user_data:
                if user_data[0] == "None":
                    return await interaction.response.send_message("You have to do the other introduction first before you can start the second one!", ephemeral=True)
            else:
                return await interaction.response.send_message("You have to do the other introduction first before you can start the second one!", ephemeral=True)


        await interaction.response.send_modal(StickyMessageModalNr2(self.bot))



class StickyMessageModalNr2(discord.ui.Modal):
    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__(
            discord.ui.InputText(
                label="Skills", placeholder="Copywriting, javascript, finance, etc", max_length=200, style=discord.InputTextStyle.long, required=True
            ),
            discord.ui.InputText(
                label="Looking For (Networking)", placeholder="I'm looking for...", max_length=200, style=discord.InputTextStyle.long, required=False
            ),
            discord.ui.InputText(
                label="Long Term Life Goal", placeholder="Long term goal", max_length=200, required=False, style=discord.InputTextStyle.long
            ), 
            discord.ui.InputText(
                label="Portfolio / Website", placeholder="Your website", max_length=200, required=False, style=discord.InputTextStyle.short
            ), 
            discord.ui.InputText(
                label="Social Media Links", placeholder="Your social media links", max_length=100, required=False, style=discord.InputTextStyle.long
            ), 
            title="Part 2"
            ),

    async def callback(self, interaction):
        user_data = [child.value or "-" for child in self.children] 

        async with aiosqlite.connect("introduction.sqlite") as connection:
            cursor = await connection.cursor()
            await connection.execute(
                """UPDATE users 
                   SET skills=?, looking_for=?, long_goal=?, portfolio_website=?, social_media=? 
                   WHERE user_id=?""", (*user_data, interaction.user.id)
            )
            await connection.commit()

            await cursor.execute(
                "SELECT name, location, occupation, bio, goal FROM users WHERE user_id = ?", (interaction.user.id,)
            )
            user_first_data = await cursor.fetchone()

        embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(name=f"{interaction.user.display_name} just introduced themselves!",
                         icon_url=interaction.user.display_avatar)
        
        guild = self.bot.get_guild(1306253223195050037) 
        forum_channel = guild.get_channel(1307422918371835995)

        thread = discord.utils.get(forum_channel.threads, name=f"{interaction.user.display_name} | {interaction.user.name}")
        if not thread:
            try:
                thread = await forum_channel.create_thread(
                    name=f"{interaction.user.display_name} | {interaction.user.name}",
                    content="New Intro",
                )

            except discord.Forbidden:
                print("missing perms to create thread channel")
            except discord.HTTPException as e:
                print(f"error while trying to create thread for {interaction.user.display_name}: {e}")

        thread = discord.utils.get(forum_channel.threads, name=thread.name) ###
        await interaction.response.send_message("Your introduction has been submitted! We will review it and then message you with the decision.", ephemeral=True)
        await thread.send(embed=embed)


        msg = await thread.send(f"Name: {user_first_data[0]} ({interaction.user.mention})\nLocation: {user_first_data[1]}\nOccupation: {user_first_data[2]}\nBio: {user_first_data[3]}\nGoal: {user_first_data[4]}\nSkills: {user_data[0]}\nLooking for: {user_data[1]}\nLong term life goal: {user_data[2]}\nPortfolio / Website: {user_data[3]}\nSocial Media Links: {user_data[4]}\n\n<@&1338589623324246088>", view=ProcessIntroButtons(self.bot, interaction.user))
        await msg.edit(suppress=True)
        


class ProcessIntroButtons(discord.ui.View):
    def __init__(self, bot, intro_user: discord.Member) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.intro_user = intro_user


    @discord.ui.button(label="Accept ✅", style=discord.ButtonStyle.green, custom_id="accept_intro")
    async def button_callback1(self, button, interaction: discord.Interaction):
        guild = self.bot.get_guild(1146069588086366349)
        
        await interaction.response.send_message("Successfully accepted introduction!", ephemeral=True)

        embed = discord.Embed(color=discord.Color.blue(), description=f"Hey {self.intro_user.mention}!\nYour clarity introduction just got accepted.")
        embed.set_author(name=f"Introduction accepted")
        try:
            await self.intro_user.send(embed=embed)
        except:
            print(f"Couldn't send DM to {self.intro_user.display_name}. Continuing with process.")
            await interaction.channel.send(f"Couldn't send DM to {self.intro_user.display_name}. Continuing with process.")

        async with aiosqlite.connect("introduction.sqlite") as connection:
            cursor = await connection.cursor()

            await cursor.execute(
                "SELECT name, location, occupation, bio, goal, skills, looking_for, long_goal, portfolio_website, social_media FROM users WHERE user_id = ?", (self.intro_user.id,)
            )
            user_data = await cursor.fetchone()

        unverified_channel = discord.utils.get(guild.channels, name='introduce-yourself')
        embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(name=f"{self.intro_user.display_name} just introduced themselves!", icon_url=self.intro_user.display_avatar)
        
        await unverified_channel.send(embed=embed)
        msg = await unverified_channel.send(f"Name: {user_data[0]}\nLocation: {user_data[1]}\nOccupation: {user_data[2]}\nBio: {user_data[3]}\nGoal: {user_data[4]}\nSkills: {user_data[5]}\nLooking for: {user_data[6]}\nLong term life goal: {user_data[7]}\nPortfolio / Website: {user_data[8]}\nSocial Media Links: {user_data[9]}")
        await msg.edit(suppress=True)
        async with aiosqlite.connect("introduction.sqlite") as connection:
            cursor = await connection.cursor()
            await cursor.execute("SELECT msg_id FROM msg WHERE anchor = 1")
                
            sticky_message_id = await cursor.fetchone()
            
            if sticky_message_id:
                sticky_message_id = sticky_message_id[0]
            
                
        if sticky_message_id:
            try:
                sticky_message = await unverified_channel.fetch_message(sticky_message_id)
                await sticky_message.delete()
            except discord.NotFound:
                pass  
        
        embed = discord.Embed(
            description=f"__**Introduce Yourself**__ 👋\n\nGain access to the Clarity Community!\n\nInstead of copy and pasting the format, use our easy form bot!\n\nWe accept/reject introductions to keep scammers and bots out.\nSo we recommend putting effort into your introduction.\n\nClick the button below to introduce yourself.", 
            color=discord.Color.blue()
        )
        new_sticky_message = await unverified_channel.send(embed=embed, view=StickyMessageButtonNr1(self.bot))

        if sticky_message_id:
            async with aiosqlite.connect("introduction.sqlite") as connection:
                cursor = await connection.cursor()

                await connection.execute(
                    "UPDATE msg SET msg_id = ? WHERE anchor=1""", (new_sticky_message.id,)
                )
                await connection.commit()
        else:
            async with aiosqlite.connect("introduction.sqlite") as connection:
                cursor = await connection.cursor()

                await connection.execute(
                    "INSERT OR REPLACE INTO msg(msg_id, anchor) VALUES (?, ?)", (new_sticky_message.id, 1))
                await connection.commit()
        

        
        verified_channel = discord.utils.get(guild.channels, name='introductions')
        embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(name=f"{self.intro_user.display_name} just introduced themselves!", icon_url=self.intro_user.display_avatar)
        
        await verified_channel.send(embed=embed)
        message = await verified_channel.send(f"Name: {user_data[0]} / {self.intro_user.mention}\nLocation: {user_data[1]}\nOccupation: {user_data[2]}\nBio: {user_data[3]}\nGoal: {user_data[4]}\nSkills: {user_data[5]}\nLooking for: {user_data[6]}\nLong term life goal: {user_data[7]}\nPortfolio / Website: {user_data[8]}\nSocial Media Links: {user_data[9]}")
        await message.edit(suppress=True)        

        await self.intro_user.add_roles(guild.get_role(1293547484492075048))
        await self.intro_user.remove_roles(guild.get_role(1290383638680305777))
        await self.intro_user.remove_roles(guild.get_role(1149437289034960906))

        main_chat = discord.utils.get(guild.channels, name='main-chat')
        await main_chat.send(f"{self.intro_user.mention} just got accepted into the server, check out their introduction [here](https://discord.com/channels/{interaction.guild.id}/1293263111436112034/{message.id}).")

        await update_beehiiv_subscription(self.intro_user.id)
        await interaction.channel.send(f"{interaction.user.mention} just accepted {self.intro_user.mention}'s introduction.")
        await add_tag(self.intro_user.id)

        
        await asyncio.sleep(2)
        await interaction.channel.delete()
        accepted_log = discord.utils.get(interaction.user.guild.channels, name='accepted')
        await accepted_log.send(f"{interaction.user.mention} just accepted {self.intro_user.mention}'s introduction.\n\nName: {user_data[0]} / {self.intro_user.mention}\nLocation: {user_data[1]}\nOccupation: {user_data[2]}\nBio: {user_data[3]}\nGoal: {user_data[4]}\nSkills: {user_data[5]}\nLooking for: {user_data[6]}\nLong term life goal: {user_data[7]}\nPortfolio / Website: {user_data[8]}\nSocial Media Links: {user_data[9]}")
    
    
    
    @discord.ui.button(label="Redo 🔁", style=discord.ButtonStyle.primary, custom_id="redo_intro")
    async def button_callback2(self, button, interaction: discord.Interaction):
        await interaction.response.send_modal(RedoIntroModal(self.bot, self.intro_user))
        

    @discord.ui.button(label="Ban ❌", style=discord.ButtonStyle.red, custom_id="ban_intro")
    async def button_callback3(self, button, interaction: discord.Interaction):
        try:
            await self.intro_user.ban()

            async with aiosqlite.connect("verification.sqlite") as connection:
                cursor = await connection.cursor()

                await cursor.execute(
                    "SELECT email FROM users WHERE user_id = ?", (self.intro_user.id,)
                )
                email = await cursor.fetchone()
                email = email[0]

            headers = {
                "Authorization": f"Bearer {BEEHIIV_API_TOKEN}",
                "Content-Type": "application/json"
            }

            response = requests.get(f"https://api.beehiiv.com/v2/publications/pub_e40bb0fa-a3c4-47f3-a391-f70ca9312e0f/subscriptions/by_email/{email}?expand%5B%5D=custom_fields", headers=headers)
            if response.status_code in [200, 201]:
                data = response.json()

                if "data" in data and data["data"]:
                    subscriber_data = data["data"]

                    update_payload = {
                        "unsubscribe": True
                    }
    
                    response = requests.put(f"{BEEHIIV_API_URL}/{subscriber_data['id']}", headers=headers, json=update_payload)
        
                    if response.status_code in [200, 201]:
                        await interaction.channel.send(f"successfully deleted {self.intro_user.display_name}'s beehiiv subscription")
                    else:
                        return await interaction.response.send_message(f"{self.intro_user.display_name}'s beehiiv subscription couldn't be deleted. Banning them from beehiiv was not possible, please do it manually.")
                    
                else:
                    return await interaction.response.send_message(f"{self.intro_user.display_name}'s beehiiv subscription couldn't be found. Banning them from beehiiv was not possible, please do it manually.")

        except Exception as e:
            return await interaction.response.send_message(f"Error while trying to ban {self.intro_user.display_name}.\n\n```{e}```")
        
        await interaction.channel.send(f"{interaction.user.mention} successfully banned {self.intro_user.display_name}.")

        async with aiosqlite.connect("introduction.sqlite") as connection:
            cursor = await connection.cursor()

            await cursor.execute(
                "SELECT name, location, occupation, bio, goal, skills, looking_for, long_goal, portfolio_website, social_media FROM users WHERE user_id = ?", (self.intro_user.id,)
            )
            user_data = await cursor.fetchone()
        

        await asyncio.sleep(2)
        await interaction.channel.delete()
        banned_log = discord.utils.get(interaction.user.guild.channels, name='banned')
        await banned_log.send(f"{interaction.user.mention} successfully banned {self.intro_user.display_name}.\n**Introduction**:\n\nName: {user_data[0]} / {self.intro_user.mention}\nLocation: {user_data[1]}\nOccupation: {user_data[2]}\nBio: {user_data[3]}\nGoal: {user_data[4]}\nSkills: {user_data[5]}\nLooking for: {user_data[6]}\nLong term life goal: {user_data[7]}\nPortfolio / Website: {user_data[8]}\nSocial Media Links: {user_data[9]}")
    
    
        

 

class RedoIntroModal(discord.ui.Modal):
    def __init__(self, bot, intro_user: discord.Member) -> None:
        self.bot = bot
        self.intro_user = intro_user
        super().__init__(
            discord.ui.InputText(
                label="Reason", placeholder="Why did youdeny the introduction of this user?", max_length=500, required=True
            ),
            title="Deny introduction"
            ),


    async def callback(self, interaction):
        await interaction.response.send_message(f"You successfully denied {self.intro_user.mention}'s introduction. A private message has been sent to them.", ephemeral=True)

        async with aiosqlite.connect("introduction.sqlite") as connection:
            cursor = await connection.cursor()

            await cursor.execute(
                "SELECT name, location, occupation, bio, goal, skills, looking_for, long_goal, portfolio_website, social_media FROM users WHERE user_id = ?", (self.intro_user.id,)
            )
            user_data = await cursor.fetchone()

        embed = discord.Embed(color=discord.Color.blue(), description=f"Hey {self.intro_user.mention}!\nYour clarity introduction just got rejected.\n\n**Reason:**\n```{self.children[0].value}```\n\nPlease redo your introduction and send it again [here](https://discord.com/channels/1146069588086366349/1293262744518398096).\n\n**Your introduction:**\nName: {user_data[0]}\nLocation: {user_data[1]}\nOccupation: {user_data[2]}\nBio: {user_data[3]}\nGoal: {user_data[4]}\nSkills: {user_data[5]}\nLooking for: {user_data[6]}\nLong term life goal: {user_data[7]}\nPortfolio / Website: {user_data[8]}\nSocial Media Links: {user_data[9]}")
        embed.set_author(name=f"Introduction Rejected",)

        try:
            await self.intro_user.send(embed=embed)
        except:
            print(f"Couldn't send DM to {self.intro_user.display_name}. Continuing with process.")
            await interaction.channel.send(f"Couldn't send DM to {self.intro_user.display_name}. Continuing with process.")

        await update_beehiiv_subscription(self.intro_user.id)

        await asyncio.sleep(2)
        await interaction.channel.delete()
        denied_log = discord.utils.get(interaction.user.guild.channels, name='denied')
        await denied_log.send(f"{interaction.user.mention} just rejected {self.intro_user.mention}'s introduction.\n\n**Reason:**\n```{self.children[0].value}```\n\n**introduction:**\nName: {user_data[0]}\nLocation: {user_data[1]}\nOccupation: {user_data[2]}\nBio: {user_data[3]}\nGoal: {user_data[4]}\nSkills: {user_data[5]}\nLooking for: {user_data[6]}\nLong term life goal: {user_data[7]}\nPortfolio / Website: {user_data[8]}\nSocial Media Links: {user_data[9]}")
    



def setup(bot):
    bot.add_cog(StickyMessage(bot))

