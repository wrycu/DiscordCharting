import discord
from sqlalchemy import create_engine, MetaData, select, and_
from configparser import ConfigParser
import datetime
import asyncio
import os

client = discord.Client()


@client.event
async def on_ready():
    # TODO: migrate the background_task code to a function so we can call from here or there
    pass

async def background_task():
    await client.wait_until_ready()
    while not client.is_closed:
        members_table = discord_meta.tables['users']
        games_table = discord_meta.tables['games']
        stats_table = discord_meta.tables['statistics']
        raw_known_members = select([
            members_table.c.id
        ]).execute().fetchall()
        known_members = []
        for member in raw_known_members:
            known_members.append(member[0])

        raw_known_games = select([
            games_table.c.id,
            games_table.c.name
        ]).execute().fetchall()
        known_games = {}
        for game in raw_known_games:
            known_games[game[1]] = game[0]

        members = client.get_all_members()
        now = datetime.datetime.now()
        for member in members:
            if int(member.id) not in known_members:
                members_table.insert({'id': member.id, 'username': member.name, 'firstSeen': now}).execute()
            if member.game:
                the_game = str(member.game).lower()
                if the_game not in known_games:
                    game_id = games_table.insert({'name': the_game, 'firstUser': member.id, 'firstSeen': now}).execute().inserted_primary_key
                    known_games[the_game] = game_id
                else:
                    game_id = known_games[the_game]
                num_entries = len(
                    select([
                        stats_table.c.id
                    ]).where(
                        and_(
                            stats_table.c.userId == member.id,
                            stats_table.c.gameId == select([
                                games_table.c.id
                            ]).where(
                                games_table.c.name == the_game
                            ).execute().fetchone()[0],
                            stats_table.c.endTime == None,
                        )
                    ).execute().fetchall()
                )
                if num_entries == 0:
                    stats_table.insert({
                        'gameId': game_id,
                        'userId': member.id,
                        'startTime': now,
                    }).execute()
                elif num_entries > 1:
                    # oh dear something went wrong
                    print("Something went wrong, bubs. User", member.name, "|", member.game)
            else:
                entries = select([
                    stats_table.c.id
                ]).where(
                    and_(
                        stats_table.c.userId == member.id,
                        stats_table.c.endTime == None,
                    )
                ).execute().fetchall()
                if len(entries) == 1:
                    stats_table.update(
                        stats_table.c.id == entries[0][0],
                        {'endTime': now}
                    ).execute()
                elif len(entries) > 1:
                    # oh dear something went wrong
                    print("Something went wrong, bubs. User", member.name, "|", member.game)
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
