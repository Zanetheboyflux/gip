import socket
import pickle
import threading
import time
import logging

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
        self.client_characters = {}
        self.game_state = {
            'players': {},
            'ready': 0
        }
        self.match_started = False
        self.platforms = []
        self.init_platforms()
        self.logger.info(f'Initializing server on {host}:{port}')

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

            import socket as sock
            hostname = sock.gethostname()

            try:
                import subprocess
                output = subprocess.check_output('ipconfig', shell=True).decode()
                ipv4_addresses = []
                for line in output.split('\n'):
                    if 'IPv4 Address' in line:
                        ipv4_address = line.split(':')[-1].strip()
                        ipv4_addresses.append(ipv4_address)
                if ipv4_addresses:
                    self.logger.info(f'Available IP addersses for client connections:')
                    for ip in ipv4_addresses:
                        self.logger.info(f' -{ip}')
                else:
                    self.logger.info(f'No IPv4 addresses found, clients may not be able to connect')
            except Exception as e:
                self.logger.error(f'Failed to get IPP addresses: {e}')
                self.logger.info(f'Local hostname: {hostname}')


            self.logger.info(f'Server started, listening on {self.host}:{self.port}')
            self.logger.info(f'make sure port {self.port} is allowed through your firewall')

            update_thread = threading.Thread(target=self.update_game_state)
            update_thread.daemon = True
            update_thread.start()

            while True:
                client_socket, address = self.server_socket.accept()
                if len(self.clients)>= 2:
                    self.logger.info(f'Rejected connection from {address} - server full')
                    client_socket.send(pickle.dumps({'status': "error", "message": "Server full"}))
                    client_socket.close()
                    continue
                self.logger.info(f'Connection from {address} has been established')

                player_num = len(self.clients) + 1
                self.clients[player_num] = client_socket

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
        buffer_size = 8192

        heartbeat_thread = threading.Thread(target=self.send_heartbeats, args=(client_socket, player_num))
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

        try:
            while True:
                data = client_socket.recv(buffer_size)
                if not data:
                    break
                try:
                    client_data = pickle.loads(data)

                    if 'player_action' in client_data:
                        action = client_data['player_action']
                        self.process_action(player_num, action)

                        if 'attack' in action and action['attack']:
                            self.handle_attack(player_num, action)

                    elif 'character_select' in client_data:
                        self.game_state['players'][player_num]['character']= client_data['character_select']
                        self.logger.info(f'Player {player_num} selected character: {client_data['character_select']}')

                    elif 'ready' in client_data and client_data['ready']:
                        self.game_state['ready'] += 1
                        self.logger.info(f"Player {player_num} is ready. Ready count: {self.game_state['ready']}")

                    elif 'player_died' in client_data and client_data['player_died']:
                        self.game_state['players'][player_num]['is_dead'] = True
                        self.logger.info(f'Player {player_num} died!')

                except pickle.UnpicklingError:
                    self.logger.info(f'Error unpickling data from player {player_num}')
                    continue

                if 'reset_game' in client_data and client_data['reset_game']:
                    self.reset_game()
                    self.logger.info(f"Game reset requested by player {player_num}")

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
            try:
                client_socket.send(pickle.dumps({'status': 'heartbeat'}))
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
        for player_num, client_socket in self.clients.items():
            try:
                player_specific_state = self.game_state.copy()
                player_specific_state['timestamp'] = time.time()
                client_socket.send(pickle.dumps(player_specific_state))
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
        last_broadcast_time = time.time()
        broadcast_interval = 0.016
        game_over_state = False
        game_over_time = 0

        while True:
            current_time = time.time()

            if not self.match_started and self.game_state['ready'] >= 2:
                self.logger.info('Both players ready, starting match!')
                self.match_started = True

                for client_socket in self.clients.values():
                    client_socket.send(pickle.dumps({
                        "status": "match_start",
                        "game_state": self.game_state
                    }))

            if self.match_started:
                if current_time - last_broadcast_time >= broadcast_interval:
                    self.broadcast_game_state()
                    last_broadcast_time = current_time

                game_over = False
                winner = None

                for player_num, player_data in self.game_state['players'].items():
                    if player_data['is_dead']:
                        game_over = True
                        winner = 1 if player_num == 2 else 2
                        break

                if game_over:
                    game_over_state = True
                    game_over_time = current_time
                    self.logger.info(f'Game_over! Player {winner} wins!')
                    for i in range(3):
                        for client_socket in self.clients.values():
                            try:
                                client_socket.send(pickle.dumps({
                                    "status": 'game_over',
                                    'winner': winner,
                                    'game_state': self.game_state
                                }))
                            except Exception as e:
                                self.logger.error(f'Error sending game_over: {e}')
                    time.sleep(0.1)

            if game_over_state and current_time - game_over_time >= 5:
                if self.match_started:
                    self.match_started = False
                    self.game_state['ready'] = 0
                    game_over_state = False

                for player_num, player in self.game_state['players'].items():
                    player.update({
                        'health': 100,
                        'is_dead': False,
                        'x': 300 if player_num == 1 else 700,
                        'y': 580
                    })
                self.logger.info('Game reset for new match')

            time.sleep(0.01)

    def reset_game(self):
        self.match_started = False
        self.game_state['ready'] = 0

        for player_num, player in self.game_state['players'].items():
            connected_status = player.get('connected', True)
            character = None

            self.game_state['players'][player_num] = {
                'connected': connected_status,
                'character': character,
                'x': 300 if player_num == 1 else 700,
                'y': 580,
                'health': 100,
                'is_dead': False,
                'is_attacking': False,
                'is_special_attacking': False,
                'facing_right': True if player_num == 2 else False,
                'velocity_y': 0,
                'is_jumping': False
            }
        for _ in range(3):
            for client_socket in self.clients.values():
                try:
                    client_socket.send(pickle.dumps({
                        'status': 'game_reset',
                        "game_state": self.game_state
                    }))
                except Exception as e:
                    self.logger.error(f'Error sending game reset: {e}')
            time.sleep(0.05)

        self.logger.info("Game fully reset - returning to character selection")

    def close_server(self):
        self.logger.info('Closing server')
        for client_socket in self.clients.values():
            try:
                client_socket.close()
            except Exception:
                pass
        self.server_socket.close()

if __name__ == "__main__":
    server = GameServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.logger.info('Server stopped by user')
        server.close_server()