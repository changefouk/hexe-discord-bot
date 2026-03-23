import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio

# ---------------------------------------------
# 1. สร้างหน้าต่าง Form (Modal) สำหรับพิมพ์ข้อมูล
# ---------------------------------------------
class TicketModal(discord.ui.Modal, title='แจ้งปัญหา / ติดต่อทีมงาน'):
    in_game_name = discord.ui.TextInput(
        label='ชื่อในเกมของคุณ',
        style=discord.TextStyle.short,
        required=True
    )
    contact_purpose = discord.ui.TextInput(
        label='จุดประสงค์ที่ติดต่อ',
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild

        # 1. ตั้งค่าสิทธิ์พื้นฐาน (ปิดทุกคน / เปิดให้คนกด)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        # 2. ดึงยศแอดมินจาก Secrets มาให้สิทธิ์มองเห็นห้อง
        admin_roles_str = os.environ.get('ADMIN_ROLE_ID', '')
        if admin_roles_str:
            for role_id in admin_roles_str.split(','):
                role_id = role_id.strip()
                if role_id.isdigit(): # เช็กให้ชัวร์ว่าเป็นตัวเลข
                    role = guild.get_role(int(role_id))
                    if role:
                        overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        # 3. สร้างห้องแบบไม่สนใจ Category
        channel = await guild.create_text_channel(
            name=f'ticket-{interaction.user.name}',
            overwrites=overwrites
        )

        embed = discord.Embed(title="แจ้งปัญหา / ติดต่อทีมงาน", color=discord.Color.blue())
        embed.add_field(name="ชื่อในเกม:", value=self.in_game_name.value, inline=False)
        embed.add_field(name="จุดประสงค์:", value=self.contact_purpose.value, inline=False)

        view = CloseTicketView()
        await channel.send(f"สวัสดีครับ {interaction.user.mention} ทีมงานจะรีบมาตอบกลับนะครับ", embed=embed, view=view)
        await interaction.response.send_message(f"✅ สร้าง Ticket สำเร็จ! เข้าไปคุยได้ที่ {channel.mention}", ephemeral=True)

# ---------------------------------------------
# 2. สร้างปุ่มกดต่างๆ (Views)
# ---------------------------------------------
class TicketButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.button(label="🔮 สัมผัสศิลาเวท", style=discord.ButtonStyle.primary, custom_id="create_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 ปิด Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("กำลังปิด Ticket ใน 5 วินาที...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

# ---------------------------------------------
# 3. ตั้งค่าบอทและโหลดคำสั่ง
# ---------------------------------------------
class TicketBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(TicketButtonView())
        self.add_view(CloseTicketView())
        await self.tree.sync()
        print("✅ ซิงค์ปุ่มและ Slash Commands เรียบร้อย!")

bot = TicketBot()

@bot.event
async def on_ready():
    print(f'🤖 บอท {bot.user} พร้อมทำงานแล้วบน Replit!')

@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    view = TicketButtonView()
    await ctx.send("ปลดผนึกศิลาเวทด้านล่าง \nหากเจ้าปรารถนาจะเชื่อมต่อห้วงมิติเพื่อเจรจากับสภาแม่มด", view=view)

@bot.tree.command(name="contact", description="แอดมินเปิด Ticket เรียกคุยเป็นการส่วนตัว")
@app_commands.default_permissions(administrator=True)
async def contact(interaction: discord.Interaction, user1: discord.Member, user2: discord.Member = None):
    users = [u for u in [user1, user2] if u is not None]

    # 1. ตั้งค่าสิทธิ์พื้นฐาน
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True) # แอดมินที่พิมพ์สั่ง
    }

    # ให้คนที่ถูกเรียกทุกคนเห็นห้อง
    for u in users:
        overwrites[u] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    # 2. ดึงยศแอดมินจาก Secrets มาให้สิทธิ์มองเห็นห้องด้วย (เผื่อแอดมินคนอื่นอยากเข้ามาดู)
    admin_roles_str = os.environ.get('ADMIN_ROLE_ID', '')
    if admin_roles_str:
        for role_id in admin_roles_str.split(','):
            role_id = role_id.strip()
            if role_id.isdigit():
                role = interaction.guild.get_role(int(role_id))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    # 3. สร้างห้อง
    channel = await interaction.guild.create_text_channel(
        name=f'ticket-{users[0].name}',
        overwrites=overwrites
    )

    tags = " ".join([u.mention for u in users])
    view = CloseTicketView()
    await channel.send(f"สวัสดีครับ {tags} ทีมงานเรียกคุยเป็นการส่วนตัวครับ", view=view)
    await interaction.response.send_message(f"✅ สร้างห้องส่วนตัวสำเร็จ! เข้าไปคุยได้ที่ {channel.mention}", ephemeral=True)

# ---------------------------------------------
# 4. สั่งรัน Web Server และ Bot
# ---------------------------------------------
keep_alive()
bot.run(os.environ.get('TOKEN'))