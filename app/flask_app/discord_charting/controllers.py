from sqlalchemy import select, and_
from flask import Blueprint, render_template, Response
from app import config
import json

discord_charting = Blueprint(
    'discord_charting',
    __name__,
)


@discord_charting.route('/', methods=['GET'])
def landing():
    return render_template('base.html')


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
    pass


@discord_charting.route('/global/games_currently_being_played', methods=['GET'])
def games_currently_being_played():
    pass


@discord_charting.route('/global/top_active_time_of_day', methods=['GET'])
def top_active_time_of_day():
    pass


@discord_charting.route('/global/game_user_count_over_time', methods=['GET'])
def game_user_count_over_time():
    pass


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
