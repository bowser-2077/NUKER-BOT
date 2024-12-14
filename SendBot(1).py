import discord
from discord.ext import commands, tasks
import asyncio
import requests
import os
import random
import string
import time
from pypresence import Presence, exceptions

# Initialisez le bot avec un préfixe de commande
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Assurez-vous que le bot a accès aux membres du serveur
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Lien Pastebin pour les mises à jour
PASTEBIN_URL = "https://pastebin.com/raw/H27bTf54"  # Remplacez <ID> par l'ID réel du pastebin

# ID du rôle autorisé
AUTHORIZED_ROLE_ID = 1317160081107980344

# Dictionnaire pour stocker les codes générés
generated_codes = {}

# Commande !smp_dms pour démarrer le spam
@bot.command()
async def smp_dms(ctx, user_id: int, message: str, delay: int):
    """Envoie des messages en boucle à un utilisateur avec un délai entre chaque message."""
    if user_id in spamming_tasks:  # Si l'utilisateur est déjà dans la boucle, l'arrêter d'abord
        await ctx.send(f"Stoping...")
        spamming_tasks[user_id]["task"].cancel()
    
    # Récupérer l'utilisateur par son ID
    user = await bot.fetch_user(user_id)
    if not user:
        await ctx.send(f"User with id : {user_id} not found.")
        return

    # Fonction pour envoyer des messages en boucle
    async def send_spam():
        while True:
            try:
                await user.send(message)
                await asyncio.sleep(delay)  # Attendre le délai entre chaque message
            except discord.Forbidden:
                await ctx.send(f"Cant send messages to {user.name}: error.")
                break  # Arrêter la boucle si l'accès est refusé
            except discord.HTTPException as e:
                print(f"Error: {e}")
                break

    # Démarrer la boucle de spam
    task = bot.loop.create_task(send_spam())
    spamming_tasks[user_id] = {"task": task, "message": message, "delay": delay}
    await ctx.send(f"Spam started to {user.name}.")

# !Clearchat

@bot.command()
async def clearchat(ctx, amount: int):
    """Supprime un nombre donné de messages dans le canal actuel."""
    
    # Vérifier si l'utilisateur a la permission de gérer les messages
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send(f"{ctx.author.mention} You don't have permission to manage messages.")
        return

    # Vérifier si le bot a la permission de gérer les messages
    if not ctx.guild.me.guild_permissions.manage_messages:
        await ctx.send(f"{ctx.author.mention} I don't have permission to manage messages.")
        return

    # Limiter le nombre de messages à supprimer (maximum 100 messages à la fois)
    if amount > 100:
        await ctx.send(f"{ctx.author.mention} You can only delete up to 100 messages at once.")
        return

    # Supprimer les messages dans le canal
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"{ctx.author.mention} {len(deleted)} message(s) have been deleted.", delete_after=5)

# send invite

@bot.command()
async def add_bot(ctx):
    """Sends the bot's invite link to the user in DM."""
    try:
        # The bot's invite link
        invite_link = "https://discord.com/oauth2/authorize?client_id=1316102626516926464"
        
        # Try sending the invite link to the user's DM
        await ctx.author.send(f"Here is the bot invite link: {invite_link}")
        await ctx.send(f"{ctx.author.mention}, I have sent you the invite link in DM!")
    except discord.Forbidden:
        # Handle the case where the bot can't send a DM
        await ctx.send(f"{ctx.author.mention}, I couldn't send you a DM. Please make sure your DMs are open.")


# Commande !smp_dms <UserId> stop pour arrêter le spam
@bot.command()
async def smp_dms_stop(ctx, user_id: int):
    """Arrête le spam des messages pour un utilisateur donné."""
    if user_id in spamming_tasks:
        spamming_tasks[user_id]["task"].cancel()  # Annuler la tâche du spam
        del spamming_tasks[user_id]  # Supprimer l'entrée du dictionnaire
        await ctx.send(f"Spam for {user_id} stoped.")
    else:
        await ctx.send(f"No spam in progress for {user_id}.")

# Vérifier si l'utilisateur a le rôle autorisé
def is_admin(ctx):
    return any(role.id == AUTHORIZED_ROLE_ID for role in ctx.author.roles)

# Générer un code aléatoire
def generate_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

# Commande pour envoyer un message personnalisé à tous les membres du serveur
@bot.command()
async def message_all(ctx, *, content):
    """Envoie un message personnalisé à tous les membres en message privé."""
    if ctx.author.guild_permissions.administrator:
        for member in ctx.guild.members:
            if not member.bot:  # Ignorer les bots
                try:
                    if member.dm_channel is None:
                        await member.create_dm()
                    await member.send(content)
                except discord.Forbidden:
                    print(f"Cant send messages to {member.name}: error.")
                except discord.HTTPException as e:
                    print(f"Cant send messages to {member.name}: {e}")
        
        # Message visible uniquement pour l'utilisateur qui a lancé la commande
        bot_message = await ctx.send(f"{ctx.author.mention} React to send messages.")
        await bot_message.add_reaction("👀")  # Ajouter une réaction de confirmation

        # Attendre la réaction de l'utilisateur
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "👀"
        
        await bot.wait_for('reaction_add', check=check)
        await bot_message.delete()  # Supprimer le message après que l'utilisateur a réagi
    else:
        await ctx.send(f"{ctx.author.mention} You dont have perms.")

# Commande !getcode
@bot.command()
async def getcode(ctx):
    """Génère un code unique pour que le créateur du serveur puisse l'envoyer à un utilisateur."""
    if ctx.author.id == ctx.guild.owner.id:  # Vérifie si l'utilisateur est le créateur du serveur
        code = generate_code()
        # Stocke le code généré avec un indicateur "non utilisé"
        generated_codes[code] = {"used": False, "user": None}
        
        # Message visible uniquement pour le créateur
        bot_message = await ctx.send(f"{ctx.author.mention} Here the one time usage code.")
        await bot_message.add_reaction("👀")  # Ajouter une réaction de confirmation
        
        # Attendre la réaction du créateur
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "👀"
        
        await bot.wait_for('reaction_add', check=check)
        await bot_message.delete()  # Supprimer le message après que l'utilisateur a réagi
        
        # Envoi du code privé
        try:
            await ctx.author.send(f"Here the one time usage code : {code}")
            await ctx.send(f"{ctx.author.mention} Code have been sent.")
        except discord.Forbidden:
            await ctx.send(f"{ctx.author.mention} Error.")
    else:
        await ctx.send(f"{ctx.author.mention} You dont have perms.")

# Commande !getaccess <code>
@bot.command()
async def getaccess(ctx, code: str):
    """Permet à un utilisateur de demander l'accès au rôle avec un code unique."""
    if code in generated_codes:
        if not generated_codes[code]["used"]:
            # Marquer le code comme utilisé
            generated_codes[code]["used"] = True
            generated_codes[code]["user"] = ctx.author.id
            role = discord.utils.get(ctx.guild.roles, id=AUTHORIZED_ROLE_ID)
            if role:
                await ctx.author.add_roles(role)
                # Message visible uniquement pour l'utilisateur
                bot_message = await ctx.send(f"{ctx.author.mention}, You are now {role.name}.")
                await bot_message.add_reaction("👀")  # Ajouter une réaction de confirmation
                # Attendre la réaction de l'utilisateur
                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) == "👀"
                
                await bot.wait_for('reaction_add', check=check)
                await bot_message.delete()  # Supprimer le message après que l'utilisateur a réagi
            else:
                await ctx.send("Cant find role.")
        else:
            await ctx.send("Code already used.")
    else:
        await ctx.send(f"{ctx.author.mention} Invalid code.")

# Commande !unrank <pseudo> pour enlever le rôle
@bot.command()
async def unrank(ctx, member: discord.Member):
    """Retirer le rôle autorisé à un membre donné."""
    if ctx.author.guild_permissions.administrator:
        role = discord.utils.get(ctx.guild.roles, id=AUTHORIZED_ROLE_ID)
        if role in member.roles:
            await member.remove_roles(role)
            # Message visible uniquement pour l'utilisateur
            bot_message = await ctx.send(f"{ctx.author.mention} {member.mention} code removed : {role.name}.")
            await bot_message.add_reaction("👀")  # Ajouter une réaction de confirmation
            # Attendre la réaction de l'utilisateur
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) == "👀"
            
            await bot.wait_for('reaction_add', check=check)
            await bot_message.delete()  # Supprimer le message après que l'utilisateur a réagi
        else:
            await ctx.send(f"{member.mention} dont have this role.")
    else:
        await ctx.send(f"{ctx.author.mention} you dont have perms.")

# Commande !ban <pseudo>
@bot.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    """Bannir un membre du serveur."""
    # Vérifier si l'utilisateur a la permission de bannir des membres
    if not ctx.author.guild_permissions.ban_members:
        await ctx.send(f"{ctx.author.mention} You don't have permission to ban members.")
        return

    # Vérifier si le bot a la permission de bannir
    if not ctx.guild.me.guild_permissions.ban_members:
        await ctx.send(f"{ctx.author.mention} I don't have permission to ban members.")
        return

    # Vérifier si le bot peut bannir la personne (le bot doit avoir un rôle plus élevé que celui de la personne à bannir)
    if member.top_role >= ctx.guild.me.top_role:
        await ctx.send(f"{ctx.author.mention} I cannot ban {member.mention} because they have a higher or equal role to mine.")
        return

    # Bannir l'utilisateur
    try:
        await member.ban(reason=reason)
        # Message visible uniquement pour l'utilisateur
        bot_message = await ctx.send(f"{ctx.author.mention} {member.mention} has been banned successfully.")
        await bot_message.add_reaction("👀")  # Ajouter une réaction de confirmation
        # Attendre la réaction de l'utilisateur
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "👀"

        await bot.wait_for('reaction_add', check=check)
        await bot_message.delete()  # Supprimer le message après que l'utilisateur a réagi
    except discord.Forbidden:
        await ctx.send(f"{ctx.author.mention} I do not have permission to ban {member.mention}.")
    except discord.HTTPException as e:
        await ctx.send(f"{ctx.author.mention} An error occurred while trying to ban {member.mention}: {e}")

# Commande !unban <pseudo>
@bot.command()
async def unban(ctx, *, member):
    """Débannir un membre du serveur."""
    if ctx.author.guild_permissions.ban_members:
        banned_users = await ctx.guild.bans()
        member_name, member_discriminator = member.split('#')
        for ban_entry in banned_users:
            user = ban_entry.user
            if user.name == member_name and user.discriminator == member_discriminator:
                await ctx.guild.unban(user)
                # Message visible uniquement pour l'utilisateur
                bot_message = await ctx.send(f"{ctx.author.mention} {user.mention} Got unbaned, NO WAY.")
                await bot_message.add_reaction("👀")  # Ajouter une réaction de confirmation
                # Attendre la réaction de l'utilisateur
                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) == "👀"
                
                await bot.wait_for('reaction_add', check=check)
                await bot_message.delete()  # Supprimer le message après que l'utilisateur a réagi
                return
        await ctx.send(f"{ctx.author.mention} Cant finde server {member}.")
    else:
        await ctx.send(f"{ctx.author.mention} You cant unban people XD.")

# Commande !stop pour arrêter le bot
@bot.command()
async def stop(ctx):
    """Arrêter le bot."""
    if ctx.author.guild_permissions.administrator:
        bot_message = await ctx.send(f"{ctx.author.mention} Stoping...")
        await bot_message.add_reaction("👀")  # Ajouter une réaction de confirmation
        # Attendre la réaction de l'utilisateur
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "👀"
        
        await bot.wait_for('reaction_add', check=check)
        await bot_message.delete()  # Supprimer le message après que l'utilisateur a réagi
        await bot.close()  # Fermer le bot
    else:
        await ctx.send(f"{ctx.author.mention} You dont have perms.")

# Commande !rank <pseudo> pour attribuer un rôle
@bot.command()
async def rank(ctx, member: discord.Member):
    """Attribue le rôle autorisé à un membre donné."""
    if ctx.author.guild_permissions.administrator:
        role = discord.utils.get(ctx.guild.roles, id=AUTHORIZED_ROLE_ID)
        if role not in member.roles:
            await member.add_roles(role)
            await ctx.send(f"{member.mention} alreadu have the role : {role.name}.")
        else:
            await ctx.send(f"{member.mention} already have this role.")
    else:
        await ctx.send("You dont have perms.")

# Spam
@bot.command()
async def spam_channel(ctx, *, message: str):
    """Envoie un message toutes les secondes sur le canal actuel"""
    # S'assurer que l'utilisateur a les permissions appropriées
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send(f"{ctx.author.mention} You dont have perms.")
        return
    
    # Fonction pour envoyer un message toutes les secondes
    async def send_spam():
        while True:
            await ctx.send(message)  # Envoie le message sur le canal
            await asyncio.sleep(1)  # Attendre 1 seconde avant d'envoyer à nouveau
    
    # Lancer le spam dans une tâche asynchrone
    await ctx.send(f"Spam started with : {message}")
    await send_spam()

@bot.command()
async def stop_spam(ctx):
    """Arrête le spam de messages."""
    # Enlever le spam si nécessaire (en utilisant une variable ou tâche globale)
    await ctx.send("Spam stoped.")
    # Pour arrêter le spam, vous devez arrêter la tâche en cours, mais ce code est simplifié

@bot.command()
async def help(ctx):
    """Affiche la liste des commandes disponibles."""
    commands_list = (
        "!message_all <message> : Sends a personalized message to all members via DM.\n"
"!start_delayed <delay> : Starts sending automated messages with a custom delay (in seconds).\n"
"!stop_delayed : Stops sending automated messages.\n"
"!update : Updates the bot's file from the configured Pastebin link and restarts the bot.\n"
"!ban <username> : Bans a member from the server.\n"
"!unban <username> : Unbans a member from the server.\n"
"!getaccess <code> : Grants access to the role if the code is valid.\n"
"!getcode : Generates a unique access code to send to the user.\n"
"!unrank <username> : Removes the authorized role from a member.\n"
"!rank <username> : Assigns the authorized role to a member.\n"
"!stop : Stops the bot.\n"
"!help : Displays this list of commands."
"!add_bot : send you an invite link in your DMs"
"!clearchat <Amount> : purge the chat (up to 100 messages)"
    )
    # Envoie un message privé à l'utilisateur qui a utilisé la commande
    await ctx.author.send(f"Here the command list :\n{commands_list}")
    # Informer l'utilisateur que le message a été envoyé en privé
    await ctx.send("Cmd list send on your DMs")

@bot.event
async def on_ready():
    print(f"Get Ready For V2!")
    # Définir une activité de base
    activity = discord.Game(name="Updating....")
    await bot.change_presence(status=discord.Status.online, activity=activity)


# Lancer le bot avec votre token
bot.run('INSERT CODE HERE')