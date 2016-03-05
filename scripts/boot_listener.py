import discord
import asyncio
from configparser import ConfigParser
import os


class BootListener:
    def __init__(self, now_playing):
        config = ConfigParser()
        config.read(os.path.join('..', 'config.ini'))
        conf = {
            'discord': {
                'email': config.get('discord', 'email'),
                'pass': config.get('discord', 'pass'),
            },
        }

        print('Starting new event loop for discord api')
        loop = asyncio.new_event_loop()
        try:
            self.client = discord.Client(loop=loop)
            print('Discord client created')

            @self.client.event
            async def on_ready():
                print('Client ready')
                await self.client.change_status(game=discord.Game(name=now_playing))
                print('Status set')
                loop.run_until_complete(self.client.close())
                print('Shutting down client')

            self.client.run(conf['discord']['email'], conf['discord']['pass'])
        except Exception:
            print("Exception! Quitting")
            loop.run_until_complete(self.client.close())
        finally:
            print('Closing event loop')
            loop.close()
