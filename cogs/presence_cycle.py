from discord.ext import commands
from discord.ext import tasks
from itertools import cycle
import discord


class Presence(commands.Cog):

    presence_change_time = 15

    bot: commands.Bot = None

    activity = cycle([
        discord.Activity(
            name="moe moe kyun", type=discord.ActivityType.watching, status=discord.Status.online)
    ])

    def __init__(self, bot) -> None:
        self.bot = bot
        self.update_presence.start()

    def cog_unload(self):
        self.update_presence.cancel()

    """For changing Presence"""

    @tasks.loop(seconds=presence_change_time)
    async def update_presence(self):
        await self.set_presence()

    @update_presence.before_loop
    async def waiter(self):
        await self.bot.wait_until_ready()

    async def set_presence(self):
        await self.bot.change_presence(activity=self.activity.__next__())


def setup(bot):
    bot.add_cog(Presence(bot))
