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
    print("Cleaning old entries")
    with ChartingDao(discord_meta) as dao:
        dao.cleanup()

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
            roles = []
            for role in member.roles:
                roles.append(str(role))
            if 'member' not in roles or 'bot' in roles:
                # This person is not someone an admin has registered on the server
                # We don't care about you, sir
                continue
            if int(member.id) not in known_members:
                # add them to our list of members if they're new
                charting_dao.create_member(member.id, str(member.name), now)

            is_afk = member.status == discord.Status.idle
            entries = charting_dao.get_stats(member.id)
            if is_afk:
                # The user is AFK. close up any games they were playing
                for entry in entries:
                    charting_dao.close_stat(entry['id'], now)
                # We're done here. they're AFK
            else:
                if member.game:
                    charting_dao.create_stat(member.id, str(member.game), now)
                else:
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
