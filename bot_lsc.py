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


# ---------- VIEWS PERSISTENTES (pra botão funcionar mesmo depois de reiniciar) ----------

class NickModal(discord.ui.Modal, title="Definir meu Nick"):
    nick = discord.ui.TextInput(label="Seu nick no Call of War", placeholder="Digite seu nick igual do jogo", max_length=32)

    async def on_submit(self, interaction: discord.Interaction):
        nick = self.nick.value.strip()
        member = interaction.user
        guild = interaction.guild
        if guild is None:
            guild = bot.guilds[0]
            member = guild.get_member(interaction.user.id)
        await interaction.response.send_message(f"✅ Nick definido como **{nick}**!", ephemeral=True)
        try:
            await member.edit(nick=nick)
        except:
            pass
        try:
            canal = discord.utils.get(guild.text_channels, name="boas-vindas")
            if canal:
                embed = discord.Embed(title="🎉 NOVO COMANDANTE NA LIGA!", description=f"{member.mention} acabou de entrar para a Liga Supremo Comando! Nick no Call of War: {nick}\n\nDeem boas-vindas para ele! ⚔️", color=0xFFD700)
                await canal.send(embed=embed)
        except:
            pass

class DefinirNickView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✏️ Definir meu Nick", style=discord.ButtonStyle.primary, custom_id="definir_nick")
    async def definir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NickModal())

class RegrasView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Li e Concordo", style=discord.ButtonStyle.success, custom_id="li_e_concordo")
    async def concordo(self, interaction: discord.Interaction, button: discord.ui.Button):
        cargo = discord.utils.get(interaction.guild.roles, name="Registrado")
        if not cargo:
            await interaction.response.send_message("Cargo 'Registrado' não encontrado. Fala com um ADM!", ephemeral=True)
            return
        await interaction.user.add_roles(cargo)
        await interaction.response.send_message("Bem-vindo à Liga! Você aceitou as regras e ganhou o cargo **Registrado** ✅", ephemeral=True)

    @bot.event
    async def on_ready():
        # Faz os botões antigos voltarem a funcionar
        bot.add_view(DefinirNickView())
        bot.add_view(RegrasView())
        synced = await bot.tree.sync()
        print(f"Sincronizado {len(synced)} comandos")
        print(f"Bot online como {bot.user}")

# ---------- 1. PV QUANDO ENTRA ----------
@bot.event
async def on_member_join(member):
    if member.bot:
        return
    try:
        embed = discord.Embed(
            title="👋 Bem-vindo à Liga Supremo Comando!",
            description="Antes de entrar, qual seu nick no Call of War? Clique no botão abaixo e digite seu nick. Seu nome aqui no Discord vai mudar automaticamente.",
            color=0xFFD700
        )
        await member.send(embed=embed, view=DefinirNickView())
    except:
        return

# ---------- 3. COMANDO PRA POSTAR REGRAS DE NOVO ----------
@bot.command()
@commands.has_permissions(administrator=True)
async def postar_regras(ctx):
    embed = discord.Embed(
        description="Ao clicar em Li e Concordo, você aceita todas as regras. Quebra de regra = punição.",
        color=0xFFD700
    )
    await ctx.send(embed=embed, view=RegrasView())

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
        categoria = discord.utils.get(guild.categories, name="🎫 TICKETS")
        canal = await guild.create_text_channel(nome, overwrites=overwrites, category=categoria)
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
import asyncio, random

# ===== SISTEMA DE DRAFT SNAKE =====
PAISES_POOL = [
    {"nome": "Alemanha", "bandeira": "🇩🇪", "faccao": "Axis", "cor": "⚫", "stats": [5, 3, 3]},
    {"nome": "Itália", "bandeira": "🇮🇹", "faccao": "Axis", "cor": "⚫", "stats": [3, 3, 5]},
    {"nome": "Polônia", "bandeira": "🇵🇱", "faccao": "Allies", "cor": "🔵", "stats": [3, 3, 5]},
    {"nome": "Romênia", "bandeira": "🇷🇴", "faccao": "Axis", "cor": "⚫", "stats": [3, 3, 5]},
    {"nome": "Ucrânia", "bandeira": "🇺🇦", "faccao": "Comintern", "cor": "🔴", "stats": [3, 3, 5]},
    {"nome": "Arkhangelsk", "bandeira": "🏴", "faccao": "Comintern", "cor": "🔴", "stats": [5, 3, 3]},
    {"nome": "Espanha", "bandeira": "🇪🇸", "faccao": "Axis", "cor": "⚫", "stats": [3, 3, 5]},
    {"nome": "Finlândia", "bandeira": "🇫🇮", "faccao": "Axis", "cor": "⚫", "stats": [3, 3, 5]},
    {"nome": "França", "bandeira": "🇫🇷", "faccao": "Allies", "cor": "🔵", "stats": [3, 5, 3]},
    {"nome": "Iugoslávia", "bandeira": "🇷🇸", "faccao": "Comintern", "cor": "🔴", "stats": [3, 5, 3]},
    {"nome": "Reino Unido", "bandeira": "🇬🇧", "faccao": "Allies", "cor": "🔵", "stats": [5, 3, 3]},
    {"nome": "Rússia Central", "bandeira": "🇷🇺", "faccao": "Comintern", "cor": "🔴", "stats": [3, 5, 3]},
    {"nome": "Suécia", "bandeira": "🇸🇪", "faccao": "Axis", "cor": "⚫", "stats": [3, 5, 3]},
]# ===== ÁSIA OCIDENTAL =====
PAISES_ASIA_OCIDENTAL = [
    {"nome": "Arábia Saudita", "bandeira": "🇸🇦", "faccao": "Axis", "cor": "⚫", "stats": [3, 5, 3]},
    {"nome": "Cazaquistão", "bandeira": "🇰🇿", "faccao": "Comintern", "cor": "🔴", "stats": [3, 3, 5]},
    {"nome": "Clique Ma", "bandeira": "🇨🇳", "faccao": "Pan-Asian", "cor": "🟠", "stats": [3, 3, 5]},
    {"nome": "Índia do Norte", "bandeira": "🇮🇳", "faccao": "Allies", "cor": "🔵", "stats": [3, 3, 5]},
    {"nome": "Índia do Sul", "bandeira": "🇮🇳", "faccao": "Allies", "cor": "🔵", "stats": [5, 3, 3]},
    {"nome": "Orissa Britânica", "bandeira": "🇧🇩", "faccao": "Allies", "cor": "🔵", "stats": [3, 5, 3]},
    {"nome": "Paquistão", "bandeira": "🇵🇰", "faccao": "Comintern", "cor": "🔴", "stats": [5, 3, 3]},
    {"nome": "Pérsia", "bandeira": "🇮🇷", "faccao": "Axis", "cor": "⚫", "stats": [3, 3, 5]},
    {"nome": "Sibéria", "bandeira": "🇷🇺", "faccao": "Comintern", "cor": "🔴", "stats": [5, 3, 3]},
    {"nome": "Síria", "bandeira": "🇸🇾", "faccao": "Allies", "cor": "🔵", "stats": [5, 3, 3]},
    {"nome": "Tibete", "bandeira": "🇨🇳", "faccao": "Pan-Asian", "cor": "🟠", "stats": [5, 3, 3]},
    {"nome": "Turquia", "bandeira": "🇹🇷", "faccao": "Comintern", "cor": "🔴", "stats": [3, 5, 3]},
    {"nome": "Urais do Norte", "bandeira": "🇷🇺", "faccao": "Comintern", "cor": "🔴", "stats": [3, 3, 5]},
    {"nome": "Volga Nizhny", "bandeira": "🇷🇺", "faccao": "Comintern", "cor": "🔴", "stats": [3, 3, 5]},
    {"nome": "Xinjiang", "bandeira": "🇨🇳", "faccao": "Pan-Asian", "cor": "🟠", "stats": [3, 5, 3]},
]

drafts = {}

def ordem_snake(qtd_picks):
    ordem = []
    rodada = 0
    while len(ordem) < qtd_picks:
        if rodada % 2 == 0:
            ordem += [0, 1, 1, 0] # ABBA
        else:
            ordem += [1, 0, 0, 1] # BAAB - continua a serpente
        rodada += 1
    return ordem[:qtd_picks]

class DraftSelect(discord.ui.Select):
    def __init__(self, draft_id):
        self.draft_id = draft_id
        d = drafts[draft_id]
        options = []
        for p in d["pool"]:
            options.append(discord.SelectOption(label=f"{p['bandeira']} {p['nome']}", description=f"{p['doutrina']} | Eco: {p['eco']}", value=p["nome"]))
        super().__init__(placeholder="Escolha o país do seu time...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        d = drafts.get(self.draft_id)
        if not d:
            await interaction.response.send_message("Draft encerrado.", ephemeral=True)
            return
        
        time_da_vez = d["ordem"][d["turno"]]
        capitao_id = d["capitaes"][time_da_vez]
        
        # TRAVA DE PERMISSÃO - Anti-Troll
        if interaction.user.id != capitao_id:
            await interaction.response.send_message("❌ Não é a sua vez de escolher! Só o Capitão do time da vez pode escolher.", ephemeral=True)
            return

        pais_nome = self.values[0]
        pais = next(p for p in d["pool"] if p["nome"] == pais_nome)
        d["pool"].remove(pais)
        d["picks"][time_da_vez].append(pais)
        d["turno"] += 1
        
        # Cancela timer antigo
        if d.get("timer_task"):
            d["timer_task"].cancel()

        if d["turno"] >= len(d["ordem"]) or not d["pool"]:
            texto = "🏁 **DRAFT FINALIZADO!**\n\n"
            for i, time_nome in enumerate(d["times"]):
                lista = ", ".join([f"{p['bandeira']} {p['nome']}" for p in d["picks"][i]])
                texto += f"**{time_nome}:** {lista}\n"
            await interaction.response.send_message(texto)
            del drafts[self.draft_id]
            return

        # Próxima vez
        prox_time = d["ordem"][d["turno"]]
        prox_cap = d["capitaes"][prox_time]
        embed = discord.Embed(title="🎲 DRAFT - SNAKE (ABBA)", description=f"Vez de **{d['times'][prox_time]}** - <@{prox_cap}>\nVocê tem **5 min** ou o sistema escolhe aleatório!", color=0xFFD700)
        view = DraftView(self.draft_id)
        await interaction.response.send_message(embed=embed, view=view)
        # Reinicia timer
        d["timer_task"] = asyncio.create_task(timer_autopick(self.draft_id, interaction.channel, view))

class DraftView(discord.ui.View):
    def __init__(self, draft_id):
        super().__init__(timeout=None)
        self.add_item(DraftSelect(draft_id))

async def timer_autopick(draft_id, canal, view):
    try:
        await asyncio.sleep(300) # 5 minutos
        d = drafts.get(draft_id)
        if not d: return
        # Auto-pick aleatório
        pais = random.choice(d["pool"])
        time_da_vez = d["ordem"][d["turno"]]
        d["pool"].remove(pais)
        d["picks"][time_da_vez].append(pais)
        d["turno"] += 1
        await canal.send(f"⏰ Tempo esgotado! Auto-pick para **{d['times'][time_da_vez]}**: {pais['bandeira']} {pais['nome']}")
        # Chama próxima rodada
        if d["turno"] < len(d["ordem"]):
            prox_time = d["ordem"][d["turno"]]
            prox_cap = d["capitaes"][prox_time]
            embed = discord.Embed(title="🎲 DRAFT - SNAKE (ABBA)", description=f"Vez de **{d['times'][prox_time]}** - <@{prox_cap}>", color=0xFFD700)
            await canal.send(embed=embed, view=DraftView(draft_id))
            d["timer_task"] = asyncio.create_task(timer_autopick(draft_id, canal, DraftView(draft_id)))
    except asyncio.CancelledError:
        pass

# ===== SISTEMA DE DRAFT V2 - ESTILO DROGON =====
import asyncio, random

MAPA_URL = "https://cdn.discordapp.com/attachments/1569082136101785654/1573198989615169607/Screenshot_20261112-185316.Discord2.jpg?ex=6b01233b&is=6affd1bb&hm=2887014f9dd3935c5388b7bf35770245182e7d94aaf065faa9e4c4cdf39de311&"


drafts = {}

def ordem_snake(qtd):
    ordem = []
    r = 0
    while len(ordem) < qtd:
        ordem += [0, 1, 1, 0] if r % 2 == 0 else [1, 0, 0, 1]
        r += 1
    return ordem[:qtd]

def montar_embed(d):
    turno = d["turno"]
    time_vez = d["ordem"][turno] if turno < len(d["ordem"]) else 0
    cap_vez = d["capitaes"][time_vez]

    texto = f"**{d['times'][0]} vs {d['times'][1]}**\n"
    texto += f"Região : 🟢 {d.get('regiao', 'Europa')}\n\n"
    texto += f"➔ Sua vez, <@{cap_vez}>! ({d['times'][time_vez]})\n"
    texto += f"*Selecione uma nação disponível no menu abaixo:*\n\n"

    for i in range(2):
        cor = "🔵" if i == 0 else "🔴"
        cargo = "(Mandante)" if i == 0 else "(Visitante)"
        texto += f"{cor} **{d['times'][i]} {cargo}**\n"
        texto += f"[ 🪖 | 🏭 | 🛢️ ]\n"
        if not d["picks"][i]:
            texto += "*Nenhuma nação ainda*\n"
        for p in d["picks"][i]:
            texto += f"{p['stats']} - {p['bandeira']} {p['nome']}\n"
        texto += "\n"

    embed = discord.Embed(title="Draft de Nações", description=texto, color=0x2B2D31)
    embed.set_image(url=MAPA_URL)
    embed.set_footer(text=f"Pick {turno+1}/{len(d['ordem'])} | Você tem 5 min ou auto-pick")
    return embed

class DraftSelect(discord.ui.Select):
    def __init__(self, draft_id):
        self.draft_id = draft_id
        d = drafts[draft_id]
        options = [discord.SelectOption(label=p["nome"], description=f"{p['stats']} | {p['bandeira']}", value=p["nome"], emoji=p["bandeira"]) for p in d["pool"]]
        super().__init__(placeholder="Selecione uma nação", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        d = drafts.get(self.draft_id)
        if not d:
            await interaction.response.send_message("Draft encerrado.", ephemeral=True)
            return
        time_vez = d["ordem"][d["turno"]]
        if interaction.user.id != d["capitaes"][time_vez]:
            await interaction.response.send_message("❌ Não é a sua vez! Só o Capitão da vez pode escolher.", ephemeral=True)
            return

        pais = next(p for p in d["pool"] if p["nome"] == self.values[0])
        d["pool"].remove(pais)
        d["picks"][time_vez].append(pais)
        d["turno"] += 1
        if d.get("timer_task"):
            d["timer_task"].cancel()

        # FIM DO DRAFT
        if d["turno"] >= len(d["ordem"]):
            texto_final = "🏁 **DRAFT FINALIZADO!**\n\n"
            for i in range(2):
                lista = ", ".join([f"{p['bandeira']} {p['nome']}" for p in d["picks"][i]])
                texto_final += f"**{d['times'][i]}:** {lista}\n"
            embed_final = discord.Embed(title="Draft de Nações - Finalizado", description=texto_final, color=0x00FF00)
            embed_final.set_image(url=MAPA_URL)
            await interaction.response.edit_message(embed=embed_final, view=None)
            del drafts[self.draft_id]
            return

        # EDITA A MESMA MENSAGEM - NÃO MANDA NOVA
        await interaction.response.edit_message(embed=montar_embed(d), view=DraftView(self.draft_id))
        d["timer_task"] = asyncio.create_task(timer_autopick(self.draft_id, interaction))

class DraftView(discord.ui.View):
    def __init__(self, draft_id):
        super().__init__(timeout=None)
        self.add_item(DraftSelect(draft_id))

async def timer_autopick(draft_id, interaction):
    try:
        await asyncio.sleep(300)
        d = drafts.get(draft_id)
        if not d: return
        pais = random.choice(d["pool"])
        time_vez = d["ordem"][d["turno"]]
        d["pool"].remove(pais)
        d["picks"][time_vez].append(pais)
        d["turno"] += 1
        # Edita a mesma mensagem com o auto-pick
        try:
            await interaction.message.edit(embed=montar_embed(d), view=DraftView(draft_id))
            await interaction.channel.send(f"⏰ Tempo esgotado! Auto-pick para **{d['times'][time_vez]}**: {pais['bandeira']} {pais['nome']}")
        except: pass
        if d["turno"] < len(d["ordem"]):
            d["timer_task"] = asyncio.create_task(timer_autopick(draft_id, interaction))
    except asyncio.CancelledError:
        pass

@bot.tree.command(name="draft", description="Inicia o Draft Snake")
async def draft(interaction: discord.Interaction, time_a: str, capitao_a: discord.Member, time_b: str, capitao_b: discord.Member, picks_por_time: int = 4):
    draft_id = interaction.channel_id
    drafts[draft_id] = {
        "times": [time_a, time_b],
        "capitaes": [capitao_a.id, capitao_b.id],
        "picks": [[], []],
        "pool": PAISES_POOL.copy(),
        "ordem": ordem_snake(picks_por_time * 2),
        "turno": 0,
        "timer_task": None
    }
    await interaction.response.send_message(embed=montar_embed(drafts[draft_id]), view=DraftView(draft_id))
    drafts[draft_id]["timer_task"] = asyncio.create_task(timer_autopick(draft_id, interaction)) 
@bot.tree.command(name="draft_asia_ocidental", description="Inicia Draft - Asia Ocidental")
async def draft_asia_ocidental(interaction: discord.Interaction, time_a: str, time_b: str, capitao_a: discord.Member, capitao_b: discord.Member, picks_por_time: int):
    draft_id = interaction.channel_id
    drafts[draft_id] = {
        "times": [time_a, time_b],
        "capitaes": [capitao_a.id, capitao_b.id],
        "picks": [[], []],
        "pool": PAISES_ASIA_OCIDENTAL.copy(),
        "ordem": ordem_snake(picks_por_time * 2),
        "turno": 0,
        "timer_task": None,
        "regiao": "Asia Ocidental",
        "imagem": "https://cdn.discordapp.com/attachments/1569082136101785654/1574135455316840589/areas_map_focus_cmtowb2590002ob1s49kmjpl7_3_1788676275146.jpg?ex=6b048b62&is=6b0339e2&hm=906e9cd7fce460016a4f1da48c11acb22b26197e2f55246321542d34a3af96bd&"
    await interaction.response.send_message(embed=montar_embed(drafts[draft_id]), view=DraftView(draft_id))
    drafts[draft_id]["timer_task"] = asyncio.create_task(timer_draft(draft_id, interaction))
@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizado {len(synced)} comandos")
    except Exception as e:
        print(e)
bot.run(TOKEN)
