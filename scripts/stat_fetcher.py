import discord
from sqlalchemy import create_engine, MetaData
from configparser import ConfigParser
from scripts.charting_dao import ChartingDao
import datetime
import asyncio
import os

client = discord.Client()


@client.event
async def on_ready():
    # TODO: migrate the background_task code to a function so we can call from here or there
    print("Ready to poll")

async def background_task():
    await client.wait_until_ready()
    while not client.is_closed:
        now = datetime.datetime.now()
        print("Polling at", now)
        charting_dao = ChartingDao(discord_meta)
        members = client.get_all_members()
        known_members = charting_dao.get_members()

        # check to see if we've seen this member before or not
        for member in members:
            if member.id not in known_members:
                # add them to our list of members if they're new
                charting_dao.create_member(member.id, str(member.name), now)
            if member.status == discord.Status.idle:
                is_afk = True
            else:
                is_afk = False
            entries = charting_dao.get_stats(member.id)
            if len(entries) > 0 and is_afk:
                # The user is AFK and we think they're playing at least one game. close 'em up!
                for entry in entries:
                    charting_dao.close_stat(entry[1], now)
                # We're done here. they're AFK
                continue
            if member.game and not is_afk:
                charting_dao.create_stat(member.id, str(member.game), now)
            elif not member.game:
                charting_dao.close_stats(member.id, str(member.game), now)
        # wait 60 seconds before polling discord again
        await asyncio.sleep(60)

config = ConfigParser()
config.read(os.path.join('..', 'config.ini'))
conf = {
    'mysql': {
        'user': config.get('mysql', 'user'),
        'pass': config.get('mysql', 'pass'),
        'host': config.get('mysql', 'host'),
        'port': config.get('mysql', 'port'),
        'db': config.get('mysql', 'db'),
    },
    'discord': {
        'email': config.get('discord', 'email'),
        'pass': config.get('discord', 'pass'),
    },
}
engine = create_engine(
    'mysql+pymysql://{user}:{password}@{host}:{port}/{db}'.format(
        user=conf['mysql']['user'],
        password=conf['mysql']['pass'],
        host=conf['mysql']['host'],
        port=conf['mysql']['port'],
        db=conf['mysql']['db'],
    )
)
discord_meta = MetaData(bind=engine, reflect=True)

loop = asyncio.get_event_loop()

try:
    loop.create_task(background_task())
    loop.run_until_complete(client.run(conf['discord']['email'], conf['discord']['pass']))
except Exception:
    print("Exception! Quitting")
    loop.run_until_complete(client.close())
finally:
    loop.close()

# Comment the loop stuff above and uncomment this to instead run a one-time update
#client.run(conf['discord']['email'], conf['discord']['pass'])
