import json
from datetime import timedelta

from flask import Blueprint, render_template, Response, request
from sqlalchemy import select, and_, asc, desc, func

from app import config
from scripts.boot_listener import BootListener

discord_charting = Blueprint(
    'discord_charting',
    __name__,
)

user_blacklist = [
    129132240239198208,
]


@discord_charting.route('/bootlistener', methods=['POST', 'OPTIONS'])
def boot_listener():
    now_playing = request.form['song']
    BootListener(now_playing)
    return Response('SUCCESS')


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
        and_(
            config.STATS_TABLE.c.endTime != None,
            ~config.STATS_TABLE.c.userId.in_(user_blacklist),
        )
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
        and_(
            config.STATS_TABLE.c.endTime != None,
            ~config.STATS_TABLE.c.userId.in_(user_blacklist),
        )
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
        config.USER_TABLE.c.username,
        config.STATS_TABLE.c.gameId,
        config.GAMES_TABLE.c.name,
    ]).select_from(
        config.STATS_TABLE.join(
            config.GAMES_TABLE,
            config.GAMES_TABLE.c.id == config.STATS_TABLE.c.gameId
        ).join(
            config.USER_TABLE,
            config.USER_TABLE.c.id == config.STATS_TABLE.c.userId
        )
    ).where(
        and_(
            config.STATS_TABLE.c.endTime == None,
            ~config.STATS_TABLE.c.userId.in_(user_blacklist),
        )
    ).execute().fetchall()
    for result in results:
        if result['name'] not in stats:
            stats[result['name']] = []
        stats[result['name']].append(result['username'])
    return stats


@discord_charting.route('/global/top_active_time_of_day', methods=['GET'])
def top_active_time_of_day():
    results = select([
        config.STATS_TABLE.c.userId,
        config.STATS_TABLE.c.startTime,
        config.STATS_TABLE.c.endTime,
    ]).where(
        and_(
            config.STATS_TABLE.c.endTime != None,
            ~config.STATS_TABLE.c.userId.in_(user_blacklist),
        )
    ).execute().fetchall()

    # HourEachDay -> [userId]
    hour_map = {}
    for result in results:
        current_time = result['startTime'].replace(minute=0, second=0, microsecond=0)
        end_time = result['endTime'].replace(minute=0, second=0, microsecond=0)

        # loop from start time to end time so we get a data point for each hour someone played a game
        while current_time <= end_time:
            if hour_map.get(current_time) is None:
                hour_map[current_time] = []
            # We don't want to count the same user in the same hour so make
            # sure they haven't already been accounted for in our map
            if result['userId'] not in hour_map[current_time]:
                hour_map[current_time].append(result['userId'])

            current_time += timedelta(hours=1)

    # We want to capture the number of people/hour AND the number of samples so that we
    # can compute the average number of players for that hour
    # Hour -> (# People, # Samples)
    stats = [(0, 0)] * 24
    for hour, users in hour_map.items():
        stats[hour.hour] = (stats[hour.hour][0] + len(users), stats[hour.hour][1] + 1)

    # convert stats for highcharts
    final_stats = []
    for hour in range(0, 24):
        if hour < 13:
            h = hour
            tod = 'AM'
        else:
            h = hour - 12
            tod = 'PM'
        final_stats.append({
            'name': str(h) + ':00' + tod,
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
        and_(
            config.STATS_TABLE.c.endTime != None,
            ~config.STATS_TABLE.c.userId.in_(user_blacklist),
        )
    ).execute().fetchall()

    # We want to capture the number of unique players per game per hour
    # Hour -> (Game -> [Players])
    hour_map = {}
    for result in results:
        current_time = result['startTime'].replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = result['endTime'].replace(hour=0, minute=0, second=0, microsecond=0)

        # loop from start time to end time so we get a data point for each hour someone played a game
        while current_time <= end_time:
            if not hour_map.get(current_time):
                hour_map[current_time] = {}
            if result['gameName'] not in hour_map[current_time]:
                hour_map[current_time][result['gameName']] = []
            if result['userId'] not in hour_map[current_time][result['gameName']]:
                hour_map[current_time][result['gameName']].append(result['userId'])

            current_time += timedelta(days=1)

    known_games = select([
        config.GAMES_TABLE.c.name
    ]).execute().fetchall()

    # sort the times so that the resulting chart is a nice timeline
    times = sorted(list(hour_map.keys()))
    formatted_times = []

    games = {}
    for time in times:
        formatted_times.append(time.strftime('%Y-%m-%d'))

        # we want a metric for every game even if it hasn't been played within our timeframe
        # so we loop over all known games here
        for game_row in known_games:
            game_name = game_row['name']
            if games.get(game_name) is None:
                games[game_name] = []
            # if there were no players, we make sure to default to 0
            games[game_name].append(len(hour_map[time].get(game_name, [])))
    game_series = []
    for game, data in games.items():
        # make sure all lines are set to invisible since we presumably have a ton of
        # games to display and we don't want to crowd the graph
        # TODO: Set the Top X games to be visible
        game_series.append({'name': game, 'data': data, 'visible': False})

    stats = {'times': formatted_times, 'games': game_series}
    return Response(json.dumps(stats), mimetype='application/json')


@discord_charting.route('/global/total_games_played', methods=['GET'])
def total_games_played():
    # get all of the stats, get the earliest game time seen, and chart from then in 1 day increments
    game_stats = {}
    user_stats = {}
    times = []
    total = 0

    results = select([
        config.GAMES_TABLE.c.name,
        config.GAMES_TABLE.c.firstSeen,
    ]).where(
        ~config.GAMES_TABLE.c.firstUser.in_(user_blacklist),
    ).order_by(
        asc(
            config.GAMES_TABLE.c.firstSeen
        )
    ).execute().fetchall()

    for result in results:
        start = result['firstSeen'].strftime('%Y-%m-%d')
        if start not in game_stats:
            game_stats[start] = total
            times.append(start)
        game_stats[start] += 1
        total += 1

    results = select([
        config.USER_TABLE.c.username,
        config.USER_TABLE.c.firstSeen,
    ]).order_by(
        asc(
            config.USER_TABLE.c.firstSeen
        )
    ).execute().fetchall()

    total = 0
    for result in results:
        start = result['firstSeen'].strftime('%Y-%m-%d')
        if start not in user_stats:
            user_stats[start] = total
            times.append(start)
        user_stats[start] += 1
        total += 1

    # convert stats for highcharts
    final_stats = {
        'games': [{
            'name': 'Unique games',
            'data': sorted(list(game_stats.values()))
        }, {
            'name': 'Unique users',
            'data': sorted(list(user_stats.values()))
        }],
        'times': times,
    }

    return Response(json.dumps(final_stats), mimetype='application/json')


@discord_charting.route('/global/top_active_users', methods=['GET'])
def top_active_users():
    # Get the top 5 most active users and the percent of time that they account for
    results = select([
        config.USER_TABLE.c.username,
        func.sec_to_time(
            func.sum(
                func.timediff(
                    config.STATS_TABLE.c.endTime,
                    config.STATS_TABLE.c.startTime
                )
            )
        ).label('time_played')
    ]).select_from(
        config.USER_TABLE.join(
            config.STATS_TABLE,
            config.USER_TABLE.c.id == config.STATS_TABLE.c.userId
        )
    ).where(
        ~config.STATS_TABLE.c.userId.in_(user_blacklist),
    ).group_by(
        config.USER_TABLE.c.username
    ).order_by(
        desc(
            'time_played'
        )
    ).limit(
        5
    ).execute().fetchall()

    # Get the total game time
    total_time = float(select([
        func.sum(
            func.timediff(
                config.STATS_TABLE.c.endTime,
                config.STATS_TABLE.c.startTime
            )
        )
    ]).execute().first()[0])

    time_played = {}
    stats = []
    for result in results:
        time_played[result['username']] = result['time_played'].total_seconds()

    allotted_time = 0
    for user, play_time in time_played.items():
        stats.append({
            'name': user,
            'y': (play_time / total_time) * 100
        })
        allotted_time += play_time
    stats.append({
        'name': 'Other',
        'y': (total_time - allotted_time) / total_time * 100
    })

    return Response(json.dumps(stats), mimetype='application/json')


@discord_charting.route('/global/user_contribution_to_total_game_time', methods=['GET'])
def user_contribution_to_total_game_time():
    # Get the users game time and the percent of time that they account for
    results = select([
        config.USER_TABLE.c.username,
        func.sec_to_time(
            func.sum(
                func.timediff(
                    config.STATS_TABLE.c.endTime,
                    config.STATS_TABLE.c.startTime
                )
            )
        ).label('time_played')
    ]).select_from(
        config.USER_TABLE.join(
            config.STATS_TABLE,
            config.USER_TABLE.c.id == config.STATS_TABLE.c.userId
        )
    ).where(
        ~config.STATS_TABLE.c.userId.in_(user_blacklist),
    ).group_by(
        config.USER_TABLE.c.username
    ).order_by(
        desc(
            'time_played'
        )
    ).limit(
        20
    ).execute().fetchall()

    # Get the total game time
    total_time = float(select([
        func.sum(
            func.timediff(
                config.STATS_TABLE.c.endTime,
                config.STATS_TABLE.c.startTime
            )
        )
    ]).execute().first()[0])

    time_played = {}
    stats = []
    for result in results:
        time_played[result['username']] = result['time_played'].total_seconds()

    allotted_time = 0
    for user, play_time in time_played.items():
        stats.append({
            'name': user,
            'y': (play_time / total_time) * 100
        })
        allotted_time += play_time
    stats.append({
        'name': 'Other',
        'y': (total_time - allotted_time) / total_time * 100
    })

    return Response(json.dumps(stats), mimetype='application/json')


@discord_charting.route('/user/game_time_breakdown', methods=['GET'])
@discord_charting.route('/user/game_time_breakdown/<string:user>', methods=['GET'])
def game_time_breakdown(user=None):
    if not user:
        return 'You must include a user', 404
    user_id = select([
        config.USER_TABLE.c.id,
    ]).where(
        config.USER_TABLE.c.username == user
    ).execute().fetchone()

    if not user_id:
        return 'User not found (case matters!)', 404
    else:
        user_id = user_id['id']

    results = select([
        config.GAMES_TABLE.c.name,
        func.sec_to_time(
            func.sum(
                func.timediff(
                    config.STATS_TABLE.c.endTime,
                    config.STATS_TABLE.c.startTime
                )
            )
        ).label('time_played'),
    ]).select_from(
        config.STATS_TABLE.join(
            config.GAMES_TABLE,
            config.GAMES_TABLE.c.id == config.STATS_TABLE.c.gameId
        )
    ).where(
        and_(
            config.STATS_TABLE.c.userId == user_id,
            ~config.STATS_TABLE.c.userId.in_(user_blacklist),
        )
    ).group_by(
        config.STATS_TABLE.c.gameId
    ).execute().fetchall()

    time_played = {}
    stats = []
    total_time = 0
    for result in results:
        time_played[result['name']] = result['time_played'].total_seconds()
        total_time += result['time_played'].total_seconds()

    for game, play_time in time_played.items():
        stats.append({
            'name': game,
            'y': play_time / total_time * 100
        })

    return Response(json.dumps(stats), mimetype='application/json')


@discord_charting.route('/user/activity_breakdown', methods=['GET'])
@discord_charting.route('/user/activity_breakdown/<string:user>', methods=['GET'])
def user_activity_breakdown(user=None):
    return user


@discord_charting.route('/game/time_breakdown_by_user', methods=['GET'])
@discord_charting.route('/game/time_breakdown_by_user/<string:game>', methods=['GET'])
def game_breakdown_by_user(game=None):
    if not game:
        return 'You must include a game', 404
    game_id = select([
        config.GAMES_TABLE.c.id,
    ]).where(
        config.GAMES_TABLE.c.name == game
    ).execute().fetchone()

    if not game_id:
        return 'Game not found (case matters!)', 404
    else:
        game_id = game_id['id']

    results = select([
        config.USER_TABLE.c.username,
        func.sec_to_time(
            func.sum(
                func.timediff(
                    config.STATS_TABLE.c.endTime,
                    config.STATS_TABLE.c.startTime
                )
            )
        ).label('time_played'),
    ]).select_from(
        config.STATS_TABLE.join(
            config.USER_TABLE,
            config.USER_TABLE.c.id == config.STATS_TABLE.c.userId
        )
    ).where(
        and_(
            config.STATS_TABLE.c.gameId == game_id,
            ~config.STATS_TABLE.c.userId.in_(user_blacklist),
        )
    ).group_by(
        config.STATS_TABLE.c.userId
    ).execute().fetchall()

    time_played = {}
    stats = []
    total_time = 0
    for result in results:
        time_played[result['username']] = result['time_played'].total_seconds()
        total_time += result['time_played'].total_seconds()

    for game, play_time in time_played.items():
        stats.append({
            'name': game,
            'y': play_time / total_time * 100
        })

    return Response(json.dumps(stats), mimetype='application/json')


@discord_charting.route('/typeahead', methods=['GET'])
def typeahead():
    user = request.args.get('user', None)
    game = request.args.get('game', None)
    if user is not None:
        results = select([
            config.USER_TABLE.c.username,
            config.USER_TABLE.c.id,
        ]).where(
            config.USER_TABLE.c.username.like(
                '%' + user + '%'
            )
        ).execute().fetchall()
        # Convert the data into typeahead format
        json_results = []
        for result in results:
            json_results.append({
                'name': result['username'],
                'value': result['id']
            })
        return Response(json.dumps(json_results), mimetype='application/json')
    elif game is not None:
        results = select([
            config.GAMES_TABLE.c.name,
            config.GAMES_TABLE.c.id,
        ]).where(
            config.GAMES_TABLE.c.name.like(
                '%' + game + '%'
            )
        ).execute().fetchall()
        # Convert the data into typeahead format
        json_results = []
        for result in results:
            json_results.append({
                'name': result['name'],
                'value': result['id']
            })
        return Response(json.dumps(json_results), mimetype='application/json')
    else:
        return 'You must include a parameter to typeahead on', 400
