import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot online!")
    def log_message(self, *args):
        pass
def keep_alive():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
threading.Thread(target=keep_alive, daemon=True).start()

import discord
from discord.ext import commands
from discord import app_commands
import json, os, datetime, asyncio

# Token vem do Render, não deixa o token escrito aqui
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ARQUIVO_PERFIS = "perfis_lsc.json"
ARQUIVO_EQUIPES = "equipes_lsc.json"

def carregar(arq):
    if not os.path.exists(arq):
        return {}
    with open(arq, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar(arq, dados):
    with open(arq, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizado {len(synced)} comandos")
    except Exception as e:
        print(e)

@bot.event
async def on_member_join(member):
    if member.bot:
        return
    guild = member.guild
    canal = discord.utils.get(guild.text_channels, name="boas-vindas") or guild.system_channel
    if not canal:
        return

    nome_topico = f"{member.name}-{member.id}"
    try:
        thread = await canal.create_thread(name=nome_topico, type=discord.ChannelType.private_thread, auto_archive_duration=60)
        await thread.add_user(member)
    except:
        thread = canal

    embed = discord.Embed(description=f"Bem-vindo(a) {member.mention}! Por favor, digite seu ID do Call of War para registro.", color=0xFF0000)
    await thread.send(embed=embed)

    def check(m):
        return m.author == member and m.channel == thread

    try:
        # 1. PEDE ID
        msg = await bot.wait_for("message", check=check, timeout=86400)
        id_cow = msg.content.strip()
        if not id_cow.isdigit():
            await thread.send("❌ ID inválido. Tem que ser só números. Digite novamente:")
            msg = await bot.wait_for("message", check=check, timeout=86400)
            id_cow = msg.content.strip()

        # 2. PEDE NICK
        await thread.send(f"✅ ID **{id_cow}** salvo! Agora digite seu **nick no Call of War**:")
        msg2 = await bot.wait_for("message", check=check, timeout=86400)
        nick_cow = msg2.content.strip()

        # 3. PEDE NÍVEL
        await thread.send(f"✅ Nick **{nick_cow}** salvo! Agora digite seu **nível** no Call of War:")
        msg3 = await bot.wait_for("message", check=check, timeout=86400)
        nivel = msg3.content.strip()

        # SALVA TUDO
        perfis = carregar(ARQUIVO_PERFIS)
        perfis[str(member.id)] = {
            "discord_nome": str(member),
            "discord_id": str(member.id),
            "id_cow": id_cow,
            "nick_cow": nick_cow,
            "nivel": nivel,
            "avatar": str(member.display_avatar.url),
            "conta_criada_em": member.created_at.strftime("%d/%m/%Y"),
            "entrou_no_servidor_em": datetime.datetime.now().strftime("%d/%m/%Y"),
            "cadastrado_em": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "verificado": True
        }
        salvar(ARQUIVO_PERFIS, perfis)

        cargo = discord.utils.get(guild.roles, name="Registrado")
        if cargo:
            try:
                await member.add_roles(cargo)
            except:
                pass

        embed2 = discord.Embed(title="✅ REGISTRO CONCLUÍDO!", color=0x00FF88)
        embed2.set_thumbnail(url=str(member.display_avatar.url))
        embed2.add_field(name="🎮 Nick CoW", value=nick_cow, inline=True)
        embed2.add_field(name="🆔 ID CoW", value=id_cow, inline=True)
        embed2.add_field(name="⭐ Nível", value=nivel, inline=True)
        embed2.add_field(name="💬 Discord", value=member.mention, inline=True)
        embed2.add_field(name="📋 Próximo passo", value="Use `/inscrever` para criar equipe ou `/entrar-equipe` para entrar em uma!", inline=False)
        await thread.send(embed=embed2)
        await asyncio.sleep(10)
        try:
            await thread.edit(archived=True, locked=True)
        except:
            pass

    except asyncio.TimeoutError:
        await thread.send(f"⏰ {member.mention} Tempo esgotado. Use `/registrar-id` para tentar de novo.")
    except Exception as e:
        print(e)

@bot.tree.command(name="registrar-id", description="Registrar ID manualmente se perdeu o tópico")
@app_commands.describe(id_cow="Seu ID numérico", nick="Seu nick no CoW", nivel="Seu nível")
async def registrar_id(interaction: discord.Interaction, id_cow: str, nick: str, nivel: str):
    perfis = carregar(ARQUIVO_PERFIS)
    perfis[str(interaction.user.id)] = {
        "discord_nome": str(interaction.user),
        "discord_id": str(interaction.user.id),
        "id_cow": id_cow,
        "nick_cow": nick,
        "nivel": nivel,
        "avatar": str(interaction.user.display_avatar.url),
        "verificado": True,
        "cadastrado_em": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    salvar(ARQUIVO_PERFIS, perfis)
    cargo = discord.utils.get(interaction.guild.roles, name="Registrado")
    if cargo:
        try:
            await interaction.user.add_roles(cargo)
        except:
            pass
    await interaction.response.send_message(f"✅ Registrado! Nick: **{nick}** | ID: **{id_cow}** | Nível: **{nivel}**", ephemeral=True)

@bot.tree.command(name="perfil", description="Ver perfil de um jogador")
@app_commands.describe(jogador="Marque o jogador")
async def perfil(interaction: discord.Interaction, jogador: discord.Member):
    p = carregar(ARQUIVO_PERFIS).get(str(jogador.id))
    if not p:
        await interaction.response.send_message(f"❌ {jogador.mention} ainda não se registrou.", ephemeral=True)
        return
    embed = discord.Embed(title=f"👤 PERFIL - {p.get('nick_cow')}", color=0xD4AF37)
    embed.set_thumbnail(url=str(jogador.display_avatar.url))
    embed.add_field(name="🎮 Nick CoW", value=p.get("nick_cow"), inline=True)
    embed.add_field(name="🆔 ID CoW", value=p.get("id_cow"), inline=True)
    embed.add_field(name="⭐ Nível", value=p.get("nivel"), inline=True)
    embed.add_field(name="💬 Discord", value=jogador.mention, inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="inscrever", description="Criar sua equipe na Liga")
@app_commands.describe(nome_equipe="Nome da equipe", pais="País que vai jogar")
async def inscrever(interaction: discord.Interaction, nome_equipe: str, pais: str):
    equipes = carregar(ARQUIVO_EQUIPES)
    perfis = carregar(ARQUIVO_PERFIS)
    p = perfis.get(str(interaction.user.id))
    if not p:
        await interaction.response.send_message("❌ Você precisa se registrar primeiro. Aguarde o tópico de boas-vindas ou use `/registrar-id`.", ephemeral=True)
        return
    equipes[str(interaction.user.id)] = {
        "lider": str(interaction.user),
        "lider_id": str(interaction.user.id),
        "equipe": nome_equipe,
        "pais": pais,
        "membros": [str(interaction.user.id)],
        "nick_cow": p.get("nick_cow"),
        "pontos": 0,
        "vitorias": 0
    }
    salvar(ARQUIVO_EQUIPES, equipes)
    await interaction.response.send_message(f"✅ Equipe **{nome_equipe}** criada! Líder: {interaction.user.mention} | País: {pais} | Nick CoW: {p.get('nick_cow')}")

@bot.tree.command(name="entrar-equipe", description="Entrar em uma equipe existente")
@app_commands.describe(lider="Marque o líder da equipe")
async def entrar_equipe(interaction: discord.Interaction, lider: discord.Member):
    equipes = carregar(ARQUIVO_EQUIPES)
    perfis = carregar(ARQUIVO_PERFIS)
    if str(interaction.user.id) not in perfis:
        await interaction.response.send_message("❌ Você precisa se registrar primeiro.", ephemeral=True)
        return
    equipe = equipes.get(str(lider.id))
    if not equipe:
        await interaction.response.send_message("❌ Essa pessoa não tem equipe criada.", ephemeral=True)
        return
    if str(interaction.user.id) in equipe["membros"]:
        await interaction.response.send_message("Você já está nessa equipe.", ephemeral=True)
        return
    equipe["membros"].append(str(interaction.user.id))
    salvar(ARQUIVO_EQUIPES, equipes)
    await interaction.response.send_message(f"✅ Você entrou na equipe **{equipe['equipe']}**!")

@bot.tree.command(name="tabela", description="Ver classificação da Liga")
async def tabela(interaction: discord.Interaction):
    equipes = carregar(ARQUIVO_EQUIPES)
    if not equipes:
        await interaction.response.send_message("🏆 Nenhuma equipe inscrita ainda.")
        return
    lista = sorted(equipes.values(), key=lambda x: x.get("pontos", 0), reverse=True)
    texto = ""
    for i, e in enumerate(lista, 1):
        texto += f"**{i}º** {e['equipe']} - {e.get('pontos',0)} pts | {e.get('vitorias',0)} vitórias | Líder: {e.get('nick_cow')}\n"
    embed = discord.Embed(title="🏆 TABELA - LIGA SUPREMO COMANDO", description=texto, color=0xD4AF37)
    await interaction.response.send_message(embed=embed)
# ===== SISTEMA DE TICKET =====
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Abrir Ticket", style=discord.ButtonStyle.primary, custom_id="abrir_ticket")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        nome = f"ticket-{user.name.lower().replace(' ', '-')}"
        canal_existente = discord.utils.get(guild.text_channels, name=nome)
        if canal_existente:
            await interaction.response.send_message(f"Você já tem um ticket aberto: {canal_existente.mention}", ephemeral=True)
            return
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        canal = await guild.create_text_channel(nome, overwrites=overwrites)
        await canal.send(f"{user.mention} Ticket criado! Descreva seu problema que a staff vai te atender.", view=FecharView())
        await interaction.response.send_message(f"Ticket criado: {canal.mention}", ephemeral=True)

class FecharView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="fechar_ticket")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fechando ticket em 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()



@bot.tree.command(name="setup_suporte", description="Enviar painel de suporte")
async def setup_suporte(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Só admin pode usar isso.", ephemeral=True)
        return
    embed = discord.Embed(title="🎧 SUPORTE - LIGA SUPREMO", description="Precisa de ajuda?\n\nClique no botão abaixo para abrir um ticket e falar com a staff.", color=0x2b2d31)
    await interaction.response.send_message(embed=embed, view=TicketView())
    await interaction.channel.send("Painel criado! Agora testa o botão acima.")

# ===== FIM TICKET =====
bot.run(TOKEN)
