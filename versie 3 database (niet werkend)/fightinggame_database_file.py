import pickle
import mysql.connector
import logging
import os
import hashlib
import re
import time
from typing import Dict, Any, Optional, Tuple

class GameDatabase:
    def __init__(self, db_type="mysql", db_path="fightinggame_database"):
        """
        Args:
        :param db_type (str): "sqlite" or "mysql"
        :param db_path (str): Path to the SQLite database file
        :param mysql_config(dict): MySQL connection parameters
        """

        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s [DATABASE]%(message)s',
                            datefmt='%H:%M:%S')
        self.logger = logging.getLogger('GameDatabase')

        self.db_type = db_type
        self.db_path = db_path

        self.mysqlconfig = {
            'host' : 'localhost',
            'user' : 'root',
            'password' : '',
            'database': 'fightinggame_database',
            'connect_timeout': 3000
        }

        self.connection = None
        self.initialize_database()
        self.login_popup = None

        try:
            self.connect()
            if self.connection:
                self.cursor = self.connection.cursor()

                if self.db_type == 'mysql':
                    self.cursor.execute(''' SELECT * FROM pygame ''')

                self.connection.commit()
        except Exception as e:
            self.logger.error(f'Error selecting information: {str(e)}')
        finally:
            self.disconnect()

    def initialize_database(self):
        try:
            self.connect()
            if self.connection:
                self.cursor = self.connection.cursor()

                if self.db_type == 'mysql':
                    self.cursor.execute(''' CREATE TABLE IF NOT EXISTS pygame (
                    GameID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Winner INTEGER, 
                    Loser INTEGER, 
                    Player1_character TEXT, 
                    Player2_character TEXT, 
                    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)
                    ''')

                    self.cursor.execute(''' CREATE TABLE IF NOT EXISTS users (
                    accountID INTEGER FOREIGN KEY REFERENCE GameID NOT NULL AUTO_INCREMENT, 
                    account_name VARCHAR(255) NOT NULL, 
                    account_password VARCHAR(255) NOT NULL, 
                    win_count INTEGER default 0
                    loss_count INTEGER default 0''')

                self.connection.commit()
                self.logger.info('Database initialized succesfully')
            else:
                self.logger.error('Failed to establish database connection')
        except Exception as e:
            self.logger.error(f'Error initializing database: {str(e)}')
        finally:
            self.disconnect()

    def connect(self):
        try:
            if self.db_type == 'mysql':
                self.connection = mysql.connector.connect(**self.mysqlconfig)
                return True
        except Exception as e:
            self.logger.error(f'Error connection to database: {str(e)}')
            return False

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def hash_password(selfself, password: str) -> str:
        "hash password using SHA_256"
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username: str, password:str) -> Dict[str, Any]:
        result = {'success': False, 'message': '', "user_id": None}

        if not re.match(r'^[a-zA-Z0-9_]{3, 20}$', username):
            result["message"]= "Username must be 3-20 characters and contain only letters, numbers, and underscores"
            return result

        if len(password) < 6:
            result['message'] = 'Password must be at least 6 characters long'
            return result
        try:
            self.connect()
            if self.connection:
                cursor = self.connection.cursor()
                cursor.execute("SELECT accountID FROM users WHERE Username = %s", (username,))
                if cursor.fetchone():
                    result['message'] = 'username already exists'
                    return result

                password_hash = self.hash_password(password)

                cursor.execute(
                    'INSERT INTO users (account_name, account_password) VALUES (%s, %s)',
                    (username, password_hash)
                )
                self.connection.commit()

                accountID = cursor.lastrowid
                result['success'] = True
                result['message'] = "Registration successful"
                result['accountID'] = accountID

                self.logger.info(f"New user registered: {username} (ID: {accountID})")
                return result

        except Exception as e:
            self.logger.error(f'Error registering new user: {str(e)}')
            result['message'] = 'Database error during registration'

        finally:
            self.disconnect()
        return result

    def login_user(self, username: str, password: str) -> Dict[str, Any]:
        result = {"success": False, 'message': '', 'user_data': None}
        try:
            self.connect()
            if self.connection:
                cursor = self.connection.cursor(dictionary=True)

                password_hash = self.hash_password(password)

                cursor.execute(
                    'SELECT accountID, account_name, win_count, loss_count FROM users WHERE account_name = %s AND account_password= %s',
                    (username, password_hash)
                )
                user_data = cursor.fetchone()

                if not user_data:
                    result['message'] = 'Invalid username or password'
                    return result

                self.connection.commit()

                result['success'] = True
                result['message'] = 'login successful'
                result['user_data'] = user_data

                self.logger.info(f'User logged in {username} (ID: {user_data['accountID']}')
                return result
        except Exception as e:
            self.logger.error(f'Error during login: {str(e)}')
            result['message'] = 'Database error during login'
        finally:
            self.disconnect()
        return result

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        stats = {
            'win_count': 0,
            'loss_count': 0,
            'win_rate': 0.0,
            'favorite_character': None
        }

        try:
            self.connect()
            if self.connection:
                cursor = self.connection.cursor(dictionary=True)
                cursor.execute(
                    'SELECT win_count, loss_count FROM users WHERE accountID = %s',
                    (user_id,)
                )
                user_data = cursor.fetchone()

                if not user_data:
                    return stats
                stats["wins"] = user_data["win_count"]
                if stats["total_games"] > 0:
                    stats["win_rate"] = (stats["wins"] / stats["total_games"]) * 100

                cursor.execute("""
                                    SELECT Player1_character as character, COUNT(*) as count 
                                    FROM pygame 
                                    WHERE UserID = %s 
                                    GROUP BY Player1_character 
                                    ORDER BY count DESC 
                                    LIMIT 1
                                """, (user_id,))
                favorite = cursor.fetchone()

                if favorite:
                    stats["favorite_character"] = favorite["character"]

                cursor.execute("""
                                    SELECT GameID, Winner, Loser, Player1_character, Player2_character, Timestamp
                                    FROM pygame
                                    WHERE UserID = %s
                                    ORDER BY Timestamp DESC
                                    LIMIT 5
                                """, (user_id,))
                stats["recent_games"] = cursor.fetchall()

                return stats

        except Exception as e:
            self.logger.error(f"Error getting user stats: {str(e)}")
        finally:
            self.disconnect()
        return stats

    def save_player_selection(self, player1_character, player2_character):
        try:
            self.connect()
            if self.connection:
                cursor = self.connection.cursor()
                if self.db_type == 'mysql':
                    cursor.execute("INSERT INTO pygame (Player1_character, player2_character) VALUES (%s, %s)",
                                   (player1_character, player2_character))
                self.connection.commit()
                result = True
                return result
            return False
        except Exception as e:
            self.logger.error(f"Error saving player selection: {str(e)}")
            result = False
        finally:
            self.disconnect()
        return result

    def record_game_result(self, winner: int, loser: int, player1_character: str, player2_character: str, user_id: int = None) -> bool:
        """Records the result of a game in the database

            Args:
                winner (int): The player number who won (1 or 2)
                loser (int): The player number who lost (1 or 2)
                player1_character (str, optional): Character used by player 1
                player2_character (str, optional): Character used by player 2

            Returns:
                bool: True if successful, False otherwise
            """
        try:
            self.connect()
            if self.connection:
                cursor = self.connection.cursor()
                if self.db_type == 'mysql':
                    if player1_character and player2_character:
                        cursor.execute('''
                                            INSERT INTO pygame (Winner, Loser, Player1_character, player2_character)
                                            VALUES (%s, %s, %s, %s)
                                        ''', (winner, loser, player1_character, player2_character))

                    if user_id:
                        if winner == 1:
                            cursor.execute("UPDATE users set win_count = win_count + 1 WHERE accountID = %s", (user_id,))
                        else:
                            cursor.execute("UPDATE users set loss_count = loss_count + 1 WHERE accountID = %s", (user_id,))
                    else:
                        cursor.execute('INSERT INTO pygame (Winner, Loser) VALUES (%s, %s)',
                                       (winner, loser))

                self.connection.commit()
                return True
            return False
        except Exception as e:
            self.logger.error(f'Error recording game result: {str(e)}')
            return False
        finally:
            self.disconnect()

    def get_character_stats(self, character_name: str) -> Dict[str, Any]:
        """
        Args:
        :param character_name (str): Name of the character
        Returns:
        dict: Character statistics
        """
        stats = {
            'total_games': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0
        }
        try:
            self.connect()
            cursor = self.connection.cursor()

            cursor.execute('''
            SELECT COUNT(*) FROM pygame
            WHERE Player1_character = %s
            ''', (character_name,))

            player1_count = cursor.fetchone()[0]

            cursor.execute('''
            SELECT COUNT(*) FROM pygame
            WHERE player2_character = %s
            ''', (character_name,))

            player2_count = cursor.fetchone()[0]

            cursor.execute('''
            SELECT COUNT(*) FROM pygame
            WHERE (Winner = 1 AND Player1_character = %s) 
            or (Winner = 2 AND player2_character = %s''',
            (character_name, character_name))
            wins = cursor.fetchone()[0]

            total_games = player1_count + player2_count
            stats['total_games'] = total_games
            stats['wins'] = wins
            stats['losses'] = total_games - wins
            stats['win_rate'] = (wins / total_games * 100) if total_games > 0 else 0
            return stats
        except Exception as e:
            self.logger.error(f"Error getting character stats: {str(e)}")
            return stats
        finally:
            self.disconnect()

    def get_recent_games(self, limit: int = 10, user_id: int = None) -> list:
        """
        Args:
        :param limit (int): Maximum number of games to return
        :return:
        list: Recent games data
        """
        games = []
        try:
            self.connect()
            cursor = self.connection.cursor(dictionary=True)

            if user_id:
                cursor.execute('''
                SELECT GameID, Winner, Loser, Player1_character, player2_character, Timestamp, accountID
                FROM pygame, users
                WHERE accountID = %s
                ORDER BY Timestamp DESC
                LIMIT %s''',
                               (user_id, limit))
            else:
                cursor.execute('''
                SELECT GameID, Winner, Loser, Player1_character, player2_character, Timestamp
                FROM pygame
                ORDER BY Timestamp DESC
                LIMIT %s''',
                               (limit,))

            games = cursor.fetchall()
            return games

        except Exception as e:
            self.logger.error(f'Error getting recent games: {str(e)}')
            return games
        finally:
            self.disconnect()

#class LoginManager:
#    def __init__(self, db: GameDatabase):
#        self.db = db
#        self.current_user = None
#        self.logger = logging.getLogger('LoginManager')
#
#    def register(self, username: str, password: str) -> Dict[str, Any]:
#        """Register a new user"""
#        return self.db.register_user(username, password)
#
#    def login(self, username:str, password:str) -> Dict[str, Any]:
#        result = self.db.login_user(username, password)
#        if result["success"]:
#            self.current_user = result["user_data"]
#        return result
#
#    def logout(self):
#        self.current_user = None
#        return {"success": True, "message": "Logged out successfully"}
#
#    def get_current_user(self)-> Optional[Dict[str, Any]]:
#        return self.current_user
#
#    def is_logged_in(self) -> bool:
#        return self.current_user is not None
#
#    def get_user_stats(self) -> Dict[str, Any]:
#        if not self.current_user:
#            return {"error": "No user logged in"}
#        return self.db.get_user_stats(self.current_user["accountID"])
#
#    def record_game_result(self, winner: int, loser:int, player_name: str, character_selected: str) -> bool:
#        user_id = self.current_user['accountID'] if self.current_user else None
#        return self.db.record_game_result(winner, loser, player_name, character_selected, user_id)

class DatabaseUpdater:
    def __init__(self, db: GameDatabase,
                 #login_manager: LoginManager= None
                 ):
        """
        args:
        :param db (GameDatabase): Database handler instance
        """
        self.db = db
        #self.login_manager = login_manager
        self.logger = logging.getLogger('DatabaseUpdater')

    def update_from_game_state(self, game_state: Dict[str, Any], winner: int) -> bool:
        """
        Update the database with information from the current game state.

        Args:
            game_state (dict): Current game state from the server
            winner (int): Player number who won (1 or 2)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if 'players' not in game_state:
                self.logger.error("Invalid game state: 'players' not found")
                return False

            players = game_state['players']

            if 1 not in players or 2 not in players:
                self.logger.error("Invalid game state: player data missing")
                return False

            player1 = players[1]
            player2 = players[2]

            if 'character' not in player1 or 'character' not in player2:
                self.logger.error("Invalid game state: character data missing")
                return False

            Winner = f"Player {winner}"
            character_winner = players[winner]['character']

            loser = 2 if winner == 1 else 1

            if self.login_manager and self.login_manager.is_logged_in():
                user_id = self.login_manager.current_user("accountID")
                return self.db.record_game_result(
                    winner=winner,
                    loser=loser,
                    player1_character=Winner,
                    player2_character= character_winner ,
                    user_id=user_id
                )

            else:
                return self.db.record_game_result(
                    winner=winner,
                    loser=loser,
                    player1_character=Winner,
                    player2_character= character_winner
                )

        except Exception as e:
            self.logger.error(f"Error updating database from game state: {str(e)}")
            return False

class ServerDatabaseHandler:
    def __init__(self, db_config=None):
        """
        Args:
         db_config (dict): Database configuration
         """
        self.db_config = db_config or {
            'db_type': 'mysql',
            'db_path': 'game_database'
        }
        self.db = GameDatabase(**self.db_config)
        self.login_manager = LoginManager(self.db)
        self.updater = DatabaseUpdater(self.db, self.login_manager)
        self.logger = logging.getLogger('ServerDatabaseHandler')

    def handle_game_over(self, game_state: Dict[str, Any], winner:int)-> bool:
        """
        Handle game over event by recording results to database

        Args:
            game_state (dict): current game state
            winner (int): Player number who won (1 or 2)

        Returns:
            bool: True if successfully recorded, False otherwise
        """
        try:
            success = self.updater.update_from_game_state(game_state, winner)
            if success:
                self.logger.info(f"Succesfully recorded game result (Winner: Player {winner}")
            else:
                self.logger.error("Failed to record game result")
        except Exception as e:
            self.logger.error(f'Error handling game over: {str(e)}')

    def save_character_selection(self, player1_character: str, player2_character: str) -> bool:
        try:
            success = self.db.save_player_selection(player1_character, player2_character)
            if success:
                self.logger.info(f"Successfully saved character selection: P1={player1_character}, P2={player2_character}")
            else:
                self.logger.error("Failed to save character selection")
            return success
        except Exception as e:
            self.logger.info(f'Error saving character selection: {str(e)}')
            return False

    def authenticate_user(self, username:str, password:str) -> Dict[str, Any]:
        return self.login_manager.login(username, password)

    def register_new_user(self, username: str, password:str) -> Dict[str, Any]:
        return self.login_manager.register(username, password)

    def get_current_user_stats(self) -> Dict[str, Any]:
        return self.login_manager.get_user_stats()

def integrate_with_server(server_instance):
    """
    args:
    :param server_instance: The game server instance
    """
    db_handler = ServerDatabaseHandler()
    original_update = server_instance.update_game_state

    def update_game_state_with_db():
        while True:
            if not server_instance.match_started and server_instance.game_state['ready'] >= 2:
                server_instance.logger.info("Both players ready, starting match!")
                server_instance.match_started = True

                player1_char = server_instance.game_state['players'][1].get('character')
                player2_char = server_instance.game_state['players'][2].get('character')
                if player1_char and player2_char:
                    db_handler.save_character_selection(player1_char, player2_char)

                for client_socket in server_instance.clients.values():
                    client_socket.send(pickle.dumps({
                        "status": "match started",
                        "game state": server_instance.game_state
                    }))

            if server_instance.match_started:
                server_instance.broadcast_game_state()
                game_over = False
                winner = None

                for player_num, player_data in server_instance.game_state['players'].items():
                    if player_data['is_dead']:
                        game_over = True
                        winner = 1 if player_num == 2 else 2

                if game_over:
                    server_instance.logger.info(f'Game over! Player {winner} wins!')
                    db_handler.handle_game_over(server_instance.game_state, winner)
                    for client_socket in server_instance.clients.values():
                        client_socket.send(pickle.dumps({
                            "status": "game_over",
                            'winner': winner,
                            'game_state': server_instance.game_state
                        }))
                    server_instance.match_started = False
                    server_instance.game_state['ready'] = 0

                    for player_num, player in server_instance.game_state['players'].items():
                        player.update({
                            'health': 100,
                            'is_dead': False,
                            'x': 300 if player_num == 1 else 700,
                            'y': 580
                        })
                        server_instance.logger.info('Game reset for new match')
                time.sleep(0.05)

            server_instance.update_game_state = update_game_state_with_db()
            return db_handler

if __name__ == "__main__":
    test_db = GameDatabase(db_type='mysql', db_path='test_game_database')
    login_manager = LoginManager(test_db)

    register_result = login_manager.register('testuser', 'password123')
    print(f'Registration result: {register_result}')

    login_result = login_manager.login("testuser", "password123")
    print(f"Login result: {login_result}")

    test_db.record_game_result(
        winner=1,
        loser=2,
        player1_character='Mewtwo',
        player2_character='Lucario',
        user_id=login_result["user_data"]["UserID"] if login_result["success"] else None
    )

    if login_manager.is_logged_in():
        user_stats = login_manager.get_user_stats()
        print(f"User stats: {user_stats}")

    lucario_stats = test_db.get_character_stats("lucario")
    print(f"Lucario stats: {lucario_stats}")

    recent_games = test_db.get_recent_games(5)
    print(f"Recent games: {recent_games}")

    print('Database test completed')