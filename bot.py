import asyncio
import logging
import discord
import pymysql
from discord.ext import commands, tasks
from discord import app_commands
from config import TOKEN, STEAM_API_KEY, FACEIT_API_KEY
from database import add_or_update_unban_request, get_request_count, reset_request_counts_older_than
from database import get_db_connection
import re
import requests

# Initialize the bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Helper function to fetch FaceIT player data based on SteamID64
def get_faceit_player_by_steamid(steamid64):
    """Fetch FaceIT player details based on SteamID64."""
    url = f'https://open.faceit.com/data/v4/players?game=csgo&game_player_id={steamid64}'
    headers = {
        'Authorization': f'Bearer {FACEIT_API_KEY}',
        'Content-Type': 'application/json'
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if 'player_id' in data:
            return data
        else:
            print(f"SteamID '{steamid64}' could not be found on FaceIT.")
    else:
        print(f"Error fetching player details: {response.status_code} - {response.text}")
    
    return None

def is_valid_steamid(steamid):
    """Checks if SteamID is valid. Only checks the format here."""
    return re.match(r'^\d{17}$', steamid) is not None

def get_steam_player_details(steamid):
    """Fetch Steam player details based on SteamID."""
    url = f'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&steamids={steamid}'
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if 'response' in data and 'players' in data['response'] and len(data['response']['players']) > 0:
            return data['response']['players'][0]
        else:
            print(f"SteamID '{steamid}' could not be found.")
            print(f"Data: {data}")  # Debug output
    else:
        print(f"Error fetching player details: {response.status_code} - {response.text}")
    
    return None

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}!')
    try:
        await bot.tree.sync()  # Sync slash commands with Discord
        print("Slash commands synced")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

    # Start the periodic task to reset request counts
    reset_counts.start()

@bot.tree.command(name="help", description="Creates a help channel for the user")
async def help(interaction: discord.Interaction):
    """Creates a help channel for the user."""
    guild = interaction.guild
    existing_channel = discord.utils.get(guild.channels, name=f'help-{interaction.user.id}')
    
    if existing_channel is None:
        try:
            # Create a new channel
            channel = await guild.create_text_channel(f'help-{interaction.user.id}', reason='Help channel for unban request')

            # Set permissions for the user
            await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            await channel.set_permissions(guild.default_role, read_messages=False, send_messages=False)
            admin_role = discord.utils.get(guild.roles, name="admin")
            if admin_role:
                await channel.set_permissions(admin_role, read_messages=True, send_messages=True)

                # Send instructions
                embed = discord.Embed(
                    title="Unban Request Instructions",
                    description=f"Hi {interaction.user.mention}, here is your help channel! To submit an unban request, use the following format:\n"
                                "`!unban <steamid> <faceit_nickname> <hub> <reason>`\n\n"
                                "Example:\n"
                                "`!unban 12345678901234567 muuki DPLB crash`\n\n"
                                f"An admin with the role {admin_role.mention} will be present in the room to assist you.\n\n"
                                "**Important Information:**\n"
                                "If you are found to be using an incorrect SteamID or FaceIT nickname, it will result in a 3-day ban from using the bot.\n\n"
                                "**Evidence:**\n"
                                "You can provide evidence here in the room that may strengthen your unban request. "
                                "This can include screenshots, links to matches, or other relevant material. "
                                "Make sure to provide all relevant information that can support your case.",
                    color=discord.Color.green()
                )
                await channel.send(embed=embed)
            
            response_message = await interaction.response.send_message(f'I have created a help channel for you: {channel.mention}', ephemeral=True)
            
            # If the message was sent successfully, delete it after 10 seconds
            if response_message:
                await response_message.delete(delay=10)
            logging.info(f"Created help channel for {interaction.user.name}")
            
        except Exception as e:
            logging.error(f"An error occurred while creating the help channel: {e}")
            await interaction.followup.send(f"An error occurred while creating the help channel: {e}", ephemeral=True)
    else:
        await interaction.response.send_message(f'You already have an open help channel: {existing_channel.mention}', ephemeral=True)
        logging.info(f"{interaction.user.name} already has an open help channel")


class AdminButtons(discord.ui.View):
    def __init__(self, user_id, channel, steamid):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.channel = channel
        self.steamid = steamid

    @discord.ui.button(label="Not Connected", style=discord.ButtonStyle.red)
    async def not_connected(self, interaction: discord.Interaction, button: discord.ui.Button):
        if "admin" in [role.name for role in interaction.user.roles]:
            await interaction.response.send_message(f"The player's SteamID and FaceIT account do not match.", ephemeral=True)
            
            # Update the bans column in the database to "not connected" and save the admin's name
            self.update_bans("not connected", interaction.user.name)

            # Delete the channel
            await self.channel.delete(reason="Admin selected 'Not Connected'")
        else:
            await interaction.response.send_message("You do not have permission to use this button.", ephemeral=True)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.grey)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if "admin" in [role.name for role in interaction.user.roles]:
            await interaction.response.send_message(f"The player has left the game.", ephemeral=True)
            
            # Update the bans column in the database to "leave" and save the admin's name
            self.update_bans("leave", interaction.user.name)

            # Delete the channel
            await self.channel.delete(reason="Admin selected 'Leave'")
        else:
            await interaction.response.send_message("You do not have permission to use this button.", ephemeral=True)

    def update_bans(self, ban_type, admin_name):
        """Updates the bans column in the database with the specified type and saves the admin's name."""
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                sql = "UPDATE unban_requests SET bans = %s, admin = %s WHERE steamid = %s"
                cursor.execute(sql, (ban_type, admin_name, self.steamid))
                connection.commit()
        except pymysql.MySQLError as e:
            print(f"An error occurred while updating bans: {e}")
        finally:
            if connection:
                connection.close()

@bot.command()
async def unban(ctx, steamid: str, faceit_nickname: str, hub: str, reason: str):
    """Handles unban requests via text command."""
    if not all([steamid, faceit_nickname, hub, reason]):
        await ctx.send('All arguments (steamid, faceit_nickname, hub, reason) are required.')
        return
    
    if not is_valid_steamid(steamid):
        await ctx.send("Invalid SteamID. Make sure it is a 64-bit number.")
        return

    # Fetch Steam player details
    player_details = get_steam_player_details(steamid)
    if not player_details:
        await ctx.send("The provided SteamID could not be found.")
        return

    # Add or update unban request
    max_requests = 3  # Adjust this value as needed
    request_count = get_request_count(steamid)
    
    if request_count >= max_requests:
        embed = discord.Embed(
            title="Unban Request Limit Reached",
            description=f"You have already submitted {request_count} unban requests, reaching the maximum limit of {max_requests} requests.\n\n"
                        "**Important Information:**\n"
                        "If you continue to submit requests, your counter will be updated. If you do not submit any requests for a week, "
                        "your counter will be reset. Be sure to plan your requests carefully,"
                        " This room will be deleted automatically after 30 seconds.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        
        # Wait for 30 seconds to give the user time to read the message
        await asyncio.sleep(30)
        
        # Close the help channel if it exists
        help_channel = discord.utils.get(ctx.guild.channels, name=f'help-{ctx.author.id}')
        if help_channel:
            try:
                await help_channel.delete(reason="Unban request limit reached.")
            except discord.Forbidden:
                await ctx.send("I do not have permission to delete the channel.")
            except discord.HTTPException as e:
                await ctx.send(f"An error occurred while attempting to delete the channel: {e}")
    else:
        success = add_or_update_unban_request(steamid, faceit_nickname, hub, reason)
        if success:
            embed = discord.Embed(
                title="Unban Request Submitted",
                description=f"Your unban request has been accepted!\n\n"
                            "Important Information: If you are found to be using an incorrect SteamID or FaceIT nickname, it will result in a 3-day ban from the hub.",
                color=discord.Color.green()
            )
            view = AdminButtons(user_id=ctx.author.id, channel=ctx.channel, steamid=steamid)
            await ctx.send(embed=embed, view=view)
        else:
            embed = discord.Embed(
                title="Unban Request Failed",
                description=f"An error occurred while processing your request.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)



@tasks.loop(hours=24)
async def reset_counts():
    """Resets request counts for users who have not submitted a request in the last 7 days."""
    reset_request_counts_older_than(days=7)

bot.run(TOKEN)
























