from sqlalchemy import select, func, and_


class ChartingDao:
    def __init__(self, meta_data):
        self.members_table = meta_data.tables['users']
        self.games_table = meta_data.tables['games']
        self.stats_table = meta_data.tables['statistics']

    def get_known_members(self):
        return select([
            self.members_table.c.id
        ]).execute().fetchall()

    def insert_new_member(self, id, username, first_seen):
        self.members_table.insert({'id': id, 'username': username, 'firstSeen': first_seen}).execute()

    def get_known_games(self):
        return select([
            self.games_table.c.id,
            self.games_table.c.name
        ]).execute().fetchall()

    def insert_new_game_and_get_id(self, name, first_user, first_seen):
        return self.games_table.insert({
            'name': name,
            'firstUser': first_user,
            'firstSeen': first_seen
        }).execute().inserted_primary_key

    def get_count_active_stats_for_user_and_game(self, user_id, game_name):
        return select([
                    func.count(self.stats_table.c.id)
                ]).where(
                    and_(
                        self.stats_table.c.userId == user_id,
                        self.stats_table.c.gameId == select([
                            self.games_table.c.id
                        ]).where(
                            self.games_table.c.name == game_name
                        ).execute().fetchone()[0],
                        self.stats_table.c.endTime == None,  # sqlalchemy doesn't like the 'is' operator so we'll use ==
                    )
                ).execute().fetchall()

    def insert_statistic(self, user_id, game_id, start_time):
        self.stats_table.insert({
            'gameId': game_id,
            'userId': user_id,
            'startTime': start_time,
        }).execute()

    def get_active_games_for_user(self, user_id):
        return select([
            self.stats_table.c.id
        ]).where(
            and_(
                self.stats_table.c.userId == user_id,
                self.stats_table.c.endTime == None,
            )
        ).execute().fetchall()

    def update_end_time_for_stat(self, stat_id, end_time):
        self.stats_table.update(
            self.stats_table.c.id == stat_id,
            {'endTime': end_time}
        ).execute()