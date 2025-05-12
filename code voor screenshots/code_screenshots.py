def record_game_result(self, winner: int, loser: int, Player1_character: str, Player2_character: str) -> bool:
    try:
        self.connect()
        cursor = self.connection.cursor()

        query = '''
        INSERT INTO fightinggame_database (Winner, Loser, Player1_character, Player2_character)
        VALUES (?, ?, ?, ?)
        '''
        if self.db_type == "mysql":
            query = query.replace('?', '%s')

        cursor.execute(query, (winner, loser, Player1_character, Player2_character))
        self.connection.commit()

        self.logger.info(
            f'Game recorded: Winner={winner}, Loser={loser}, P1={Player1_character}, P2={Player2_character}')
        return True
    except Exception as e:
        self.logger.error(f'Error recording game result: {str(e)}')
        return False
    finally:
        self.disconnect()