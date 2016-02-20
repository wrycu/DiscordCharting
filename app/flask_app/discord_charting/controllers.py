from sqlalchemy import select, and_
from flask import Blueprint, render_template, Response
from app import config
import json
from datetime import timedelta
import collections

discord_charting = Blueprint(
    'discord_charting',
    __name__,
)


@discord_charting.route('/', methods=['GET'])
def landing():
    return render_template(
        'base.html',
        current_games=games_currently_being_played()
    )


@discord_charting.route('/global/top_games_by_play_time', methods=['GET'])
def top_games_by_play_time():
    stats = {}
    game_mapping = {}
    results = select([
        config.STATS_TABLE.c.gameId,
        config.STATS_TABLE.c.startTime,
        config.STATS_TABLE.c.endTime,
        config.GAMES_TABLE.c.name,
    ]).select_from(
        config.STATS_TABLE.join(
            config.GAMES_TABLE,
            config.GAMES_TABLE.c.id == config.STATS_TABLE.c.gameId
        )
    ).where(
        config.STATS_TABLE.c.endTime != None
    ).execute().fetchall()
    for result in results:
        if result['gameId'] not in stats:
            game_mapping[result['gameId']] = result['name']
            stats[result['gameId']] = 0
        stats[result['gameId']] += (result['endTime'] - result['startTime']).total_seconds() / 60 / 60
    raw_top_games = sorted(stats, key=stats.get, reverse=True)[:5]

    top_games = []
    for game in raw_top_games:
        top_games.append({'name': game_mapping[game], 'data': [stats[game]]})
    return Response(json.dumps(top_games), mimetype='application/json')

@discord_charting.route('/global/top_games_by_user_count', methods=['GET'])
def top_games_by_user_count():
    stats = {}
    game_mapping = {}
    results = select([
        config.STATS_TABLE.c.gameId,
        config.STATS_TABLE.c.userId,
        config.GAMES_TABLE.c.name,
    ]).select_from(
        config.STATS_TABLE.join(
            config.GAMES_TABLE,
            config.GAMES_TABLE.c.id == config.STATS_TABLE.c.gameId
        )
    ).where(
        config.STATS_TABLE.c.endTime != None
    ).execute().fetchall()
    for result in results:
        if result['gameId'] not in stats:
            game_mapping[result['gameId']] = result['name']
            stats[result['gameId']] = []
        if result['userId'] not in stats[result['gameId']]:
            stats[result['gameId']].append(result['userId'])
    raw_top_games = sorted(stats, key=lambda k: len(stats[k]), reverse=True)[:5]

    top_games = []
    for game in raw_top_games:
        top_games.append({'name': game_mapping[game], 'data': [len(stats[game])]})
    return Response(json.dumps(top_games), mimetype='application/json')


def games_currently_being_played():
    stats = {}
    results = select([
        config.STATS_TABLE.c.gameId,
        config.GAMES_TABLE.c.name,
    ]).select_from(
        config.STATS_TABLE.join(
            config.GAMES_TABLE,
            config.GAMES_TABLE.c.id == config.STATS_TABLE.c.gameId
        )
    ).where(
        config.STATS_TABLE.c.endTime == None
    ).execute().fetchall()
    for result in results:
        if result['name'] not in stats:
            stats[result['name']] = 0
        stats[result['name']] += 1
    return stats


@discord_charting.route('/global/top_active_time_of_day', methods=['GET'])
def top_active_time_of_day():
    results = select([
        config.STATS_TABLE.c.userId,
        config.STATS_TABLE.c.startTime,
        config.STATS_TABLE.c.endTime,
    ]).where(
        config.STATS_TABLE.c.endTime != None
    ).execute().fetchall()

    # HourEachDay -> [userId]
    hour_map = {}
    for result in results:
        current_time = result['startTime'].replace(minute=0, second=0, microsecond=0)
        end_time = result['endTime'].replace(minute=0, second=0, microsecond=0)
        while current_time <= end_time:
            if hour_map.get(current_time) is None:
                hour_map[current_time] = []
            if result['userId'] not in hour_map[current_time]:
                hour_map[current_time].append(result['userId'])

            current_time += timedelta(hours=1)

    # Hour -> (# People, # Samples)
    stats = [(0, 0)] * 24
    for hour, users in hour_map.items():
        stats[hour.hour] = (stats[hour.hour][0] + len(users), stats[hour.hour][1] + 1)

    # convert stats for highcharts
    final_stats = []
    for hour in range(0, 24):
        final_stats.append({
            'name': str(hour) + ':00 - ' + str(hour + 1) + ':00',
            'data': [stats[hour][0] / stats[hour][1]]
        })

    return Response(json.dumps(final_stats), mimetype='application/json')

@discord_charting.route('/global/game_user_count_over_time', methods=['GET'])
def game_user_count_over_time():
    results = select([
        config.STATS_TABLE.c.userId,
        config.GAMES_TABLE.c.name.label('gameName'),
        config.STATS_TABLE.c.startTime,
        config.STATS_TABLE.c.endTime,
    ]).select_from(
        config.STATS_TABLE.join(
            config.GAMES_TABLE,
            config.STATS_TABLE.c.gameId == config.GAMES_TABLE.c.id
        )
    ).where(
        config.STATS_TABLE.c.endTime != None
    ).execute().fetchall()

    hour_map = dict()
    for result in results:
        current_time = result['startTime'].replace(minute=0, second=0, microsecond=0)
        end_time = result['endTime'].replace(minute=0, second=0, microsecond=0)
        while current_time <= end_time:
            if not hour_map.get(current_time):
                hour_map[current_time] = dict()
            if result['gameName'] not in hour_map[current_time]:
                hour_map[current_time][result['gameName']] = []
            if result['userId'] not in hour_map[current_time][result['gameName']]:
                hour_map[current_time][result['gameName']].append(result['userId'])

            current_time += timedelta(hours=1)

    known_games = select([
        config.GAMES_TABLE.c.name
    ]).execute().fetchall()

    times = sorted(list(hour_map.keys()))
    formatted_times = []

    games = dict()
    for time in times:
        formatted_times.append(time.strftime('%Y-%m-%dT%H:00'))

        for game_row in known_games:
            game_name = game_row['name']
            if games.get(game_name) is None:
                games[game_name] = []
            games[game_name].append(len(hour_map[time].get(game_name, [])))
    game_series = []
    for game, data in games.items():
        game_series.append({'name': game, 'data': data, 'visible': False})

    stats = {'times': formatted_times, 'games': game_series}
    return Response(json.dumps(stats), mimetype='application/json')


@discord_charting.route('/global/total_games_played', methods=['GET'])
def total_games_played():
    pass


@discord_charting.route('/global/top_active_users', methods=['GET'])
def top_active_users():
    pass


@discord_charting.route('/global/user_contribution_to_total_game_time', methods=['GET'])
def user_contribution_to_total_game_time():
    pass


@discord_charting.route('/global/most_concurrent_players_by_game', methods=['GET'])
def most_concurrent_players_by_game():
    pass
