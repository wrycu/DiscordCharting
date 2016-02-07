from sqlalchemy import select, func, and_


class ChartingDao:
    def __init__(self, meta_data):
        """
        Abstracts SQL calls away from the stat tracking logic
        :param meta_data:
            SQLAlchemy MetaData object which contains all tables
        :return:
        """
        self.members_table = meta_data.tables['users']
        self.games_table = meta_data.tables['games']
        self.stats_table = meta_data.tables['statistics']

    def get_members(self):
        """
        Retrieve a list of all members
        :return:
            A list of all member IDs
        """
        return select([
            self.members_table.c.id,
        ]).execute().fetchall()

    def member_exists(self, user_id):
        """
        Checks if a member exists in the DB
        :param user_id:
            ID of the member to check on
        :return:
            Bool indicating if the user exists
        """
        if len(
            select([
                self.members_table.c.id
            ]).where(
                self.members_table.c.id == user_id
            ).execute().fetchall()
        ) == 0:
            return False
        else:
            return True

    def create_member(self, user_id, username, first_seen, realname=None):
        """
        Inserts a new member into the DB
        :param user_id:
            ID of the member.  This should be the member's discord ID
        :param username:
            Username of the member
        :param first_seen:
            Datetime object representing when the user was first seen
        :param realname:
            The person's IRL name.  Optional - not really used anywhere at the moment
        :return:
        """
        self.members_table.insert({
            'id': user_id,
            'username': username,
            'firstSeen': first_seen,
            'realname': realname,
        }).execute()

    def get_games(self):
        """
        Retrieve a list of all known games
        :return:
            All known game IDs and names
        """
        return select([
            self.games_table.c.id,
            self.games_table.c.name,
        ]).execute().fetchall()

    def get_game_id(self, game_name):
        """
        Lookup the ID of a given game
        :param game_name:
            Name of the game to look up
        :return:
            ID of the game, if it exists
            False if it does not
        """
        return select([
            self.games_table.c.id
        ]).where(
            self.games_table.c.name == game_name
        ).execute().fetchone()

    def create_game(self, name, first_user, first_seen):
        """
        Creates a new game for tracking stats against
        :param name:
            Name of the game.  Note that this is currently expected to be lowercase
        :param first_user:
            The ID of the user who was first seen playing this game
        :param first_seen:
            The datetime at which this game was first seen being played
        :return:
            ID of the game after it's created
        """
        return self.games_table.insert({
            'name': name,
            'firstUser': first_user,
            'firstSeen': first_seen,
        }).execute().inserted_primary_key

    def get_stats(self, user_id):
        """
        Returns all currently open entries for a given user
        :param user_id:
            ID of the user you want to look up
        :return:
            A list of tuples containing the gameID and entry ID that are currently in progress
        """
        return select([
            self.stats_table.c.gameId,
            self.stats_table.c.id,
        ]).where(
            and_(
                self.stats_table.c.userId == user_id,
                self.stats_table.c.endTime == None,
            )
        ).execute().fetchall()

    def close_stat(self, stat_id, end_time):
        """
        Adds an endtime to a given entry, marking that game as no longer being played
        Note that you can invoke "close_stats" to close all entries for a given user
        :param stat_id:
            Entry ID to close out
        :param end_time:
            Datetime at which this game was finished being played
        :return:
            N/A
        """
        self.stats_table.update(
            self.stats_table.c.id == stat_id,
            {'endTime': end_time}
        ).execute()

    def close_stats(self, user_id, end_time):
        """
        Adds an endtime to all games a user is playing, marking that game as no longer being played
        Note that you can invoke "close_stat" to close a single entry
        :param user_id:
            ID of the user you want to close stats for
        :param end_time:
            Datetime at which this game was finished being played
        :return:
            N/A
        """
        stat_ids = self.get_stats(
            user_id,
        )
        for stat_id in stat_ids:
            self.stats_table.update(
                self.stats_table.c.id == stat_id,
                {
                    'endTime': end_time,
                }
            ).execute()

    def create_stat(self, user_id, game_name, start_time):
        """
        Inserts a new entry for a user playing a game
        Note that this function will automatically close any other entries for that user
        :param user_id:
            ID of the user playing the game
        :param game_name:
            ID of the game the user is playing
        :param start_time:
            The time at which this user started playing this game
        :return:
            N/A
        """
        entries = self.get_stats(user_id)
        if len(entries) > 0:
            for entry in entries:
                self.close_stat(entry[1], start_time)

        game_id = self.get_game_id(game_name)
        if not game_id:
            game_id = self.create_game(game_name, user_id, start_time)
        else:
            game_id = game_id[0]
        self.stats_table.insert({
            'gameId': game_id,
            'userId': user_id,
            'startTime': start_time,
        }).execute()
