import discord
from discord.ext import commands
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
import aiosqlite
import requests
from dotenv import load_dotenv
import os

today = date.today()

bot = commands.Bot(command_prefix="!",
                   help_command=None,
                   case_insensitive=True)

load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
SENDER_NAME = os.getenv("SENDER_NAME")

BEEHIIV_API_TOKEN = os.getenv("BEEHIIV_API_TOKEN")
BEEHIIV_API_URL = os.getenv("BEEHIIV_API_URL")


def send_verification_email(to_email, code, username):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} <{EMAIL}>"
    msg['To'] = to_email
    msg['Subject'] = "Your Verification Code"

    html_content = f"""
            <html>
            <body>
                <p>Hey {username},</p>
                <p>Your verification code is:</p>
                <h2 style="font-weight:bold;">{code}</h2>
            </body>
            </html>
        """
    
    msg.attach(MIMEText(html_content, 'html'))
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(EMAIL, PASSWORD)

        text = msg.as_string()
        server.sendmail(EMAIL, to_email, text)
        print(f"Verification email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        server.quit()



def get_beehiiv_subscription(email):
    url = f"{BEEHIIV_API_URL}?email={email}"
    headers = {
        "Authorization": f"Bearer {BEEHIIV_API_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data["data"]:
            print("DATA")
            print(data)
            return data["data"][0] 
    return None




def create_or_update_beehiiv_subscription(email, discord_id, discord_name, member):
    headers = {
        "Authorization": f"Bearer {BEEHIIV_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # Überprüfen ob die email des Users hinterlegt ist (im BEEHIIV Newsletter)
    response = requests.get(f"https://api.beehiiv.com/v2/publications/pub_e40bb0fa-a3c4-47f3-a391-f70ca9312e0f/subscriptions/by_email/{email}?expand%5B%5D=custom_fields", headers=headers)
    if response.status_code in [200, 201]:
        data = response.json()

        if "data" in data and data["data"]:
            subscriber_data = data["data"]
            custom_fields = {field['name']: field['value'] for field in subscriber_data.get('custom_fields', [])}
            print(f"Custom Fields: {custom_fields}")
            
            existing_discord_id = custom_fields.get('discordID')
        else:
            print("No subscriber data or custom fields found")


        if existing_discord_id:
            # Wenn die Discord ID des nutzers bereits im BEEHIIV newsletter hinterlegt ist, wird sie hinzugefügt
            if discord_id not in existing_discord_id:
                updated_discord_id = f"{existing_discord_id} / {discord_id}"
                custom_fields['discordID'] = updated_discord_id
                print(f"Updating subscriber with added discord IDs: {updated_discord_id}")

                existing_discord_name = custom_fields.get('discordName', '')
                updated_discord_name = f"{existing_discord_name} / {discord_name}" if existing_discord_name else discord_name
                custom_fields['discordName'] = updated_discord_name
                print(f"Updating subscriber with added discord names: {updated_discord_name}")

                email_verifier = Emailverify(bot)  
                # system zur erkennung von zweit-accounts, die die gleich email verwenden
                bot.loop.create_task(email_verifier.log_action(description=f"**Alt account detected**\n\nOwner: <@{existing_discord_id}> ({existing_discord_id})\nAlt: <@{discord_id}> ({discord_id})", member=member))

            else:
                # wenn die discord ID nicht im newsletter ist, wird sie hinzugefügt
                custom_fields['discordID'] = discord_id
                custom_fields['discordName'] = discord_name
                print(f"Adding new discordID: {discord_id} and discordName: {discord_name}")

                email_verifier = Emailverify(bot)

        else:
            # wenn die discord ID des users nicht im newsletter ist, jedoch eine passende email, wird sie zusammen mit dem Namen hinzugefügt. Das kann z.B passieren, wenn sich jemand bereits über die BEEHIIV Website beim newsletter angemeldet hat, jedoch noch nicht über Discord
            custom_fields['discordID'] = discord_id
            custom_fields['discordName'] = discord_name
            print(f"Updating subscriber by adding discordID: {discord_id} and discordName: {discord_name}")


        # subscription updaten, API Anfrage schicken
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
        # wenn absolut keine daten des users im newsletter vorhanden sind, erstelle eine neue subscription
        print(f"Subscriber not found, creating a new subscription for {email}")
        create_beehiiv_subscription(email, discord_id, discord_name)

        email_verifier = Emailverify(bot)


def create_beehiiv_subscription(email, discord_id, discord_name):
    headers = {
        "Authorization": f"Bearer {BEEHIIV_API_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "email": email,
        "send_welcome_email": False,
        "utm_source": "discord",
        "tags": ["discord"],
        "custom_fields": [
            {
                "name": "discordID",
                "value": discord_id
            },
            {
                "name": "discordName",
                "value": discord_name
            }
        ]
    }

    response = requests.post(BEEHIIV_API_URL, headers=headers, json=data)

    if response.status_code == 201: 
        print(f"Successfully created subscription for {email}")
    else:
        print(f"Failed to create subscription: {response.status_code} - {response.text}")





def activate_beehiiv_automation(email):
    automation_id = os.getenv("AUTOMATION_ID")
    publication_id = os.getenv("PUB_ID") 
    url = f"https://api.beehiiv.com/v2/publications/{publication_id}/automations/{automation_id}/journeys"
    
    payload = {
        "email": email,
        "double_opt_override": "on"
    }
    
    headers = {
        "Authorization": f"Bearer {BEEHIIV_API_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code in [200, 201]:
        print(f"Successfully activated automation for {email}")
    else:
        print(f"Failed to activate automation: {response.status_code} - {response.text}")



def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))





class Emailverify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    async def log_action(self, description: str, member): # schickt eine Log Nachricht in den Discord server
        channel = discord.utils.get(member.guild.channels, name='log')

        embed = discord.Embed(
            description=f"{description}",
            color=discord.Color.blue())
        
        if channel:
            await channel.send(embed=embed) 
        else:
            print("channel not found")

        
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(VerifyButton(self.bot)) # erneuert den Button, sodass dieser auch nach einem Neustart funktioniert


    @commands.command(name="verifybutton")
    @commands.has_permissions(administrator=True)
    async def verifybutton(self, ctx):
        embed = discord.Embed(
            description=f"Click the button below to verify and gain access to the server!", 
            color=discord.Color.blue()
        )

        await ctx.send(embed=embed, view=VerifyButton(self.bot))


class VerifyButton(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.primary, custom_id="verify_btn")
    async def button_callback4(self, button, interaction: discord.Interaction):
        user_id = interaction.user.id

        async with aiosqlite.connect("verification.sqlite") as connection:
            cursor = await connection.cursor()
            
            await cursor.execute("SELECT verified FROM users WHERE user_id = ?", (user_id,))
            user_verify_status = await cursor.fetchone()

            if user_verify_status:
                if user_verify_status[0] == 1:
                    return await interaction.response.send_message("You are already verified!", ephemeral=True)

        await interaction.response.send_modal(EmailModal(self.bot))





class EmailModal(discord.ui.Modal): # sendet dem User ein Discord Formular zum ausfüllen der Daten
    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__(
            discord.ui.InputText(
                label="Enter your email", placeholder="you@example.com", min_length=3, max_length=75, required=True), title="Verify your email")

    async def callback(self, interaction: discord.Interaction):
        email = self.children[0].value
        user_id = interaction.user.id
        username = interaction.user.name

        code = generate_code()
        async with aiosqlite.connect("verification.sqlite") as connection:
            await connection.execute(
                "INSERT OR REPLACE INTO users (user_id, email, code, verified) VALUES (?, ?, ?, ?)",  
                (user_id, email, code, False)
            )
            await connection.commit()

        embed = discord.Embed(
            description=f"**An email with the verification code has been sent to:**\n\n```{email}```\nCan't find it? Check your spam folder or try again!", 
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=SendEmailButton(self.bot), ephemeral=True)
        send_verification_email(to_email = email, code = code, username = username)
        


class SendEmailButton(discord.ui.View):
    def __init__(self, bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Enter code", style=discord.ButtonStyle.primary, custom_id="sendmail_btn")
    async def button_callback4(self, button, interaction: discord.Interaction):
        user_id = interaction.user.id

        async with aiosqlite.connect("verification.sqlite") as connection:
            cursor = await connection.cursor()
            await cursor.execute("SELECT email, code FROM users WHERE user_id = ?", (user_id,))
            user_data = await cursor.fetchone()

        if user_data:
            email, code = user_data
            await interaction.response.send_modal(VerifyCodeModal(self.bot, user_id, email, code))
        else:

            await interaction.response.send_message("No verification data found for you. Please try again later.", ephemeral=True)



class VerifyCodeModal(discord.ui.Modal):
    def __init__(self, bot, user_id, email, code) -> None:
        self.bot = bot
        self.user_id = user_id 
        self.email = email
        self.code = code

        super().__init__(
            discord.ui.InputText(
                label="Enter your code", placeholder=f"Enter the code that was sent to {email}",
                min_length=3, max_length=6, required=True), title="Enter the verification code"
        )

    async def callback(self, interaction: discord.Interaction):
        input_code = self.children[0].value
        user_id = interaction.user.id
        username = interaction.user.name

        async with aiosqlite.connect("verification.sqlite") as connection:
            cursor = await connection.cursor()
            await cursor.execute("SELECT code FROM users WHERE user_id = ?", (user_id,))
            user_code = await cursor.fetchone()

        if not user_code:
            embed = discord.Embed(description=f"No verification code found for you.", color=discord.Color.red())
        elif str(user_code[0]) != str(input_code):
            embed = discord.Embed(
                title="Wrong code",
                description=f"That code is not the same as the verification code sent to **{self.email}**. Please try again.",
                color=discord.Color.red())
            
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        else:
            embed = discord.Embed(title="Verified", description="You were successfully verified!", color=discord.Color.green())

            await interaction.user.add_roles(interaction.user.guild.get_role(1290383638680305777)) # fügt dem User die verifizierte rolle hinzu
            await interaction.user.remove_roles(interaction.user.guild.get_role(1149437289034960906))
            await interaction.response.send_message(embed=embed, ephemeral=True)

            async with aiosqlite.connect("verification.sqlite") as connection:
                await connection.execute("UPDATE users SET verified = 1 WHERE user_id = ?", (self.user_id,))
                await connection.commit()

            create_or_update_beehiiv_subscription(self.email, str(user_id), str(username), member=interaction.user)
            activate_beehiiv_automation(email=str(self.email)) # sendet dem User automatisch zukünftige newsletter beiträge

            email_verifier = Emailverify(bot)
            await email_verifier.log_action(member=interaction.user, description=f"{interaction.user.mention} just verified!")





def setup(bot):
    bot.add_cog(Emailverify(bot))

