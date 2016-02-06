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
        raw_known_members = charting_dao.get_known_members()
        known_members = []
        for member in raw_known_members:
            known_members.append(member[0])

        raw_known_games = charting_dao.get_known_games()
        known_games = {}
        for game in raw_known_games:
            known_games[game[1]] = game[0]

        members = client.get_all_members()
        # check to see if we've seen this member before or not
        for member in members:
            if int(member.id) not in known_members:
                # add them to our list of members if they're new
                charting_dao.insert_new_member(member.id, member.name, now)
            if member.status == discord.Status.idle:
                is_afk = True
            else:
                is_afk = False
            # if the user is in a game and not afk, we're interested
            if member.game and not is_afk:
                the_game = str(member.game).lower()
                # if we've never seen this game before, add it to the list of games
                if the_game not in known_games:
                    game_id = charting_dao.insert_new_game_and_get_id(the_game, member.id, now)
                    known_games[the_game] = game_id
                # if we have seen this game before, grab entries for this user where there is no end time
                else:
                    game_id = known_games[the_game]
                num_entries = charting_dao.get_count_active_stats_for_user_and_game(member.id, the_game)

                # if there are no entries with no end time, then this user just started playing
                if num_entries == 0:
                    charting_dao.insert_statistic(member.id, game_id, now)
                # if there is more than 1 entry, we haven't cleaned up after ourselves nicely...
                elif num_entries > 1:
                    # oh dear something went wrong
                    print("Something went wrong, bubs. User", member.name, "|", member.game)
            # this user is either not in game or they have gone afk
            else:
                # we want to figure out what game they were playing so we can set an end time
                entries = charting_dao.get_active_games_for_user(member.id)
                # if they only have one entry with no end time, then set the end time for that game
                if len(entries) == 1:
                    charting_dao.update_end_time_for_stat(entries[0][0], now)
                # if there are multiple entries with no end time, then we didn't clean up after ourselves at some point
                elif len(entries) > 1:
                    # oh dear something went wrong
                    print("Something went wrong, bubs. User", member.name, "|", member.game)
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
