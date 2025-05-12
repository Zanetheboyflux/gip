import socket
import pickle
import threading
import time
import logging
import argparse
import fightinggame_database_file as db_handler

def parse_arguments():
    parser = argparse.ArgumentParser(description='Pokemon Fighting Game Server')
    parser.add_argument('--port', '-p', type=int, default=5555,
                        help='Port to listen on')
    return parser.parse_args()

class GameServer:
    def __init__(self, host='0.0.0.0', port=5555):
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s [SERVER] %(message)s',
                            datefmt='%H:%M:%S')
        self.logger = logging.getLogger('GameServer')

        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
        self.logger.info(f'Clients: {self.clients}')
        self.client_characters = {}
        self.game_state = {
            'players': {},
            'ready': 0
        }

        self.match_started = False
        self.platforms = []
        self.init_platforms()
        self.logger.info(f'Initializing server on {host}:{port}')

        self.db_handler = db_handler.ServerDatabaseHandler()

        #self.authenticate_users = {}
        #self.require_authentication = True
        #self.authenticated_users = None

    def init_platforms(self):
        self.platforms = [
            {'x': 200, 'y': 600, 'width': 600, 'height': 20},
            {'x': 400, 'y': 300, 'width': 100, 'height': 20},
            {'x': 600, 'y': 450, 'width': 100, 'height': 20}
        ]
        self.game_state['platforms'] = self.platforms

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(2)
            self.logger.info(f'Server started, listening on {self.host}:{self.port}')
            update_thread = threading.Thread(target=self.update_game_state)
            update_thread.daemon = True
            update_thread.start()

            #while True:
            client_socket, address = self.server_socket.accept()
            if len(self.clients)>= 2:
                self.logger.info(f'Rejected connection from {address} - server full')
                client_socket.send(pickle.dumps({'status': "error", "message": "Server full"}))
                client_socket.close()
                #continue
            self.logger.info(f'Connection from {address} has been established')

            player_num = len(self.clients) + 1
            self.logger.info(f'Player num: {player_num}')
            self.clients[player_num] = client_socket
            self.logger.info(f'client_socket: {client_socket}')

            # self.game_state[player_num]= client_socket
            self.game_state['players'][player_num] = {
                'connected': True,
                'character': None,
                'x': 300 if player_num == 1 else 700,
                'y': 580,
                'health': 100,
                'is_dead': False,
                'is_attacking': False,
                'is_special_attacking': False,
                'facing_right': True if player_num == 2 else False
            }

            client_socket.send(pickle.dumps({'status':'connected', 'player_num': player_num}))
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, player_num))
            client_thread.daemon = True
            client_thread.start()

        except Exception as e:
            self.logger.error(f'Error starting server: {str(e)}')
        finally:
            self.close_server()

    def handle_client(self, client_socket, player_num):

        heartbeat_thread = threading.Thread(target=self.send_heartbeats, args=(client_socket, player_num))
        heartbeat_thread.daemon = True
        heartbeat_thread.start()
        self.logger.info(f'Client socket: {client_socket}')

        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                client_data = pickle.loads(data)
                self.logger.info(f'client data: {client_data}')

                #if 'action' in client_data:
                    #if client_data['action'] == 'login':
                        #username = client_data.get('username')
                        #password = client_data.get('password')
                        #self.logger.info(f'username: {username}')
                        #self.logger.info(f'password: {password}')
                        #login_result = self.db_handler.authenticate_user(username, password)
                        #self.logger.info(f'login result: {login_result}')

                        #client_socket.send(pickle.dumps({
                            #'status': 'success' if login_result['success'] else 'error',
                            #'message': login_result['message'],
                            #'user_data': login_result.get('user_data')
                        #}))
                        #if login_result['success']:
                            #self.authenticated_users[player_num] = login_result['user_data']
                        #continue

                    #elif client_data['action'] == 'register':
                        #username = client_data.get('username')
                        #password = client_data.get('password')
                        #self.logger.info(f'username: {username}')
                        #self.logger.info(f'password: {password}')

                        #register_result = self.db_handler.register_new_user(username, password)
                        #self.logger.info(f'register result: {register_result}')

                        #client_socket(pickle.dumps({
                            #'status': 'success' if register_result['success'] else 'error',
                            #'message': register_result['message']
                        #}))
                        #self.logger.info('einde register')
                        #continue

                if 'player_action' in client_data:
                    action = client_data['player_action']
                    self.process_action(player_num, action)

                    if 'attack' in action and action['attack']:
                        self.handle_attack(player_num, action)

                if 'player1_character' in client_data or 'player2_character' in client_data:
                    character = None
                    if 'player1_character' in client_data and player_num == 1:
                        character = client_data['player1_character']
                    elif 'player2_character' in client_data and player_num == 2:
                        character = client_data['player2_character']

                    if character:
                        self.game_state['players'][player_num]['character'] = character
                        self.logger.info(f'Player {player_num} selected character: {character}')

                    self.broadcast_game_state()

                if 'ready' in client_data and client_data['ready']:
                    self.game_state['ready'] += 1
                    self.logger.info(f"Player {player_num} is ready. Ready count: {self.game_state['ready']}")

                if 'player_action' in client_data:
                    action = client_data['player_action']
                    player = self.game_state['players'][player_num]

                if 'player_died' in client_data and client_data['player_died']:
                    self.game_state['players'][player_num]['is_dead'] = True
                    self.logger.info(f'Player {player_num} died!')


        except Exception as e:
            self.logger.info(f'Error handling client {player_num}:{str(e)}')
            try:
                error_msg = {'status': 'server_error', 'message': f'Server error: {str(e)}'}
                client_socket.send(pickle.dumps(error_msg))
            except:
                pass
        finally:
            self.handle_disconnect(player_num)

    def send_heartbeats(self, client_socket, player_num):
        while player_num in self.clients:
            self.logger.info(f'self.clients: {self.clients}')
            try:
                client_socket.send(pickle.dumps({'status': 'heartbeat'}))
                self.logger.info(f'client socket: {client_socket}')
                time.sleep(1)
            except Exception as e:
                self.logger.info(f'Heartbeat failed for player{player_num}: {str(e)}')
                break

    def handle_attack(self, attacker_num, action):
        if not self.match_started:
            return

        attacker = self.game_state['players'][attacker_num]
        defender_num = 1 if attacker_num == 2 else 2

        if defender_num in self.game_state['players']:
            defender = self.game_state['players'][defender_num]

            distance = abs(attacker['x'] - defender['x'])
            if distance <= action.get('attack_range', 100):
                damage = action.get('damage', 10)
                defender['health'] = max(0, defender['health'] - damage)

                if defender['health'] <= 0:
                    defender['is_dead'] = True
                    self.logger.info(f'Player {defender_num} defeated!')

    def process_action(self, player_num, action):
        player = self.game_state['players'][player_num]

        #if player_num not in self.authenticate_users and self.require_authentication:
            #self.logger.warning(f'Player {player_num} attempted action without authentication')

        if 'x' in action:
            player['x'] = action['x']
        if 'y' in action:
            player['y'] = action['y']

        if 'facing_right' in action:
            player['facing_right'] = action['facing_right']
        if 'is_attacking' in action:
            player['is_attacking'] = action['is_attacking']
        if 'is_special_attacking' in action:
            player['is_special_attacking'] = action['is_special_attacking']

    def broadcast_game_state(self):
        game_state_data = pickle.dumps({"status": "game_state_update", "game_state": self.game_state})
        for client_socket in self.clients.values():
            try:
                client_socket.send(game_state_data)
            except Exception as e:
                self.logger.error(f'Error sending game state: {str(e)}')


    def handle_disconnect(self, player_num):
        self.logger.info(f'Player {player_num} disconnected')
        if player_num in self.clients:
            try:
                self.clients[player_num].send(pickle.dumps({
                    'status': 'server_error',
                    'message': 'Server disconnection occurred'
                }))
                self.clients[player_num].close()
            except Exception:
                pass
            del self.clients[player_num]

        if player_num in self.game_state['players']:
            self.game_state['players'][player_num]['connected'] = False

        other_player = 1 if player_num == 2 else 2
        if other_player in self.clients:
            try:
                self.clients[other_player].send(pickle.dumps({
                    'status': 'server_error',
                    'message': f'Player {player_num} disconnected'
                }))
            except Exception:
                pass

        if self.match_started:
            self.match_started = False
            self.game_state['ready'] = 0
            self.logger.info('Match ended due to player disconnect')

    def update_game_state(self):
        while True:
            if not self.match_started and self.game_state['ready'] >= 2:
                self.logger.info('Both players ready, starting match!')
                self.match_started = True

                player1_character = self.game_state['players'][1].get('character')
                player2_character = self.game_state['players'][2].get('character')

                if player1_character and player2_character:
                    success = self.db_handler.save_character_selection(player1_character, player2_character)
                    self.logger.info(f'Character selection saved to database: {success}')

                if 1 in self.game_state['players'] and 2 in self.game_state['players']:
                    player1_character = self.game_state['players'][1].get('character')
                    player2_character = self.game_state['players'][2].get('character')

                    if player1_character:
                        self.db_handler.db.save_player_selection(player1_character, player2_character)

                for client_socket in self.clients.values():
                    client_socket.send(pickle.dumps({
                        "status": "match_start",
                        "game_state": self.game_state
                    }))

            if self.match_started:
                self.broadcast_game_state()
                game_over = False
                winner = None

                for player_num, player_data in self.game_state['players'].items():
                    if player_data['is_dead']:
                        game_over = True
                        winner = 1 if player_num == 2 else 2
                        break

                if game_over:
                    self.logger.info(f'Game_over! Player {winner} wins!')
                    player1_character = self.game_state['players'][1].get('character')
                    player2_character = self.game_state['players'][2].get('character')

                    winner_num = winner
                    loser_num = 1 if winner == 2 else 2

                    self.db_handler.handle_game_over(self.game_state, winner)

                    for client_socket in self.clients.values():
                        client_socket.send(pickle.dumps({
                            "status": 'game_over',
                            'winner': winner,
                            'game_state': self.game_state
                        }))

                    self.match_started = False
                    self.game_state['ready'] = 0

                    for player_num, player in self.game_state['players'].items():
                        player_x = 300 if player_num == 1 else 700
                        player.update({'health': 100, 'is_dead': False, 'x': player_x, 'y': 580})
                    self.logger.info('Game reset for new match')

            time.sleep(0.05)

    def close_server(self):
        self.logger.info('Closing server')
        for client_socket in self.clients.values():
            try:
                client_socket.close()
            except Exception:
                pass
        self.server_socket.close()

def main():
    args = parse_arguments()
    server = GameServer(port=args.port)
    server.start()

#def add_auth_handling_to_server(server):
#    original_handle_client = server.handle_client
#
#    def enhanced_handle_client(client_socket, player_num):
#        try:
#            data = client_socket.recv(4096)
#            if not data:
#                return
#
#            client_data = pickle.loads(data)
#
#            if 'action' in client_data and client_data['action'] == 'login':
#                username = client_data.get('username')
#                password = client_data.get('password')
#
#                login_result = server.db_handler.authenticate_user(username, password)
#
#                if login_result['success']:
#                    client_socket.send(pickle.dumps({
#                        'status': 'success',
#                        'message': 'Login successful',
#                        'user_data': login_result['user_data']
#                    }))
#                else:
#                    client_socket.send(pickle.dumps({
#                        'status': 'error',
#                        'message': login_result['message']
#                    }))
#            elif 'action' in client_data and client_data['action'] == 'register':
#                username = client_data.get('username')
#                password = client_data.get('password')
#
#                register_result = server.db_handler.register_new_user(username, password)
#
#                if register_result['success']:
#                    client_socket.send(pickle.dumps({
#                        'status': 'success',
#                        'message': 'Registration successful'
#                    }))
#                else:
#                    client_socket.send(pickle.dumps({
#                        'status': 'error',
#                        'message': register_result['message']
#                    }))
#
#            original_handle_client(client_socket, player_num)
#
#        except Exception as e:
#            server.logger.error(f"Error handling authentication: {str(e)}")
#            try:
#                client_socket.send(pickle.dumps({
#                    'status': 'error',
#                    'message': f"Server error: {str(e)}"
#                }))
#            except:
#                pass
#
#    server.handle_client = enhanced_handle_client
#    return server

if __name__ == "__main__":
    main()
