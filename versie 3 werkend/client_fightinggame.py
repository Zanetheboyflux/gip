import pygame
import socket
import pickle
import threading
import sys
import time
import logging
from pygame.locals import *

class GameClient:
    def __init__(self, host='localhost', port=5555):
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s [CLIENT] %(message)s',
                            datefmt='%H:%M:%S')
        self.logger = logging.getLogger('GameClient')
        pygame.init()

        self.host = host
        self.port = port
        self.client_socket = None
        self.player_num = None
        self.character_name = None
        self.opponent_character = None
        self.connected = False
        self.match_started = False
        self.game_over = False
        self.character = None
        self.winner = None

        self.SCREEN_WIDTH = 1000
        self.SCREEN_HEIGHT = 650
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        pygame.display.set_caption("Pokemon Fighting Game - Client")
        self.clock = pygame.time.Clock()

        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.GRAY = (100, 100, 100)
        self.BLUE = (50, 150, 255)
        self.DARK_BLUE = (30, 30, 120)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.YELLOW = (255, 255, 0)

        self.font = pygame.font.Font(None, 74)
        self.small_font = pygame.font.Font(None, 36)

        self.game_state = {
            'players':{},
            'platforms':[]
        }
        self.platforms = []
        self.ready = False

        self.available_characters = ['Lucario', 'Mewtwo', 'Zeraora', 'Cinderace']
        self.selected_character_index = 0

        self.character_sprite = None
        self.opponent_sprite = None

        self.heartbeat_thread = None
        self.last_server_response = time.time()
        self.heartbeat_timeout = 1000
        self.server_error = False
        self.error_message = None

    def connect_to_server(self):
        try:
            self.logger.info(f'Attempting to connect to server at {self.host}:{self.port}')
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5)
            self.client_socket.connect((self.host, self.port))
            self.client_socket.settimeout(None)

            data = self.client_socket.recv(4096)
            response = pickle.loads(data)

            if response['status'] == 'connected':
                self.player_num = response['player_num']
                self.connected = True
                self.logger.info(f'Connected to server as Player {self.player_num}')

                self.heartbeat_thread = threading.Thread(target=self.check_server_heartbeat)
                self.heartbeat_thread.daemon = True
                self.heartbeat_thread.start()

                receive_thread = threading.Thread(target=self.receive_data)
                receive_thread.daemon = True
                receive_thread.start()
                return True
            else:
                self.logger.info(f'Failed to connect: {response.get('message', 'Unknown error')}')
                self.server_error = True
                self.error_message = response.get("message", "Failed to connect to server")
                return False

        except socket.timeout:
            self.logger.info("Connection timeout: Server not responding")
            self.server_error = True
            self.error_message = "Connection timeout: Server not responding"
            return False

        except socket.error as e:
            err_code = e.args[0]
            if err_code == 10061:  # Connection refused
                self.logger.info(
                    f"Connection refused by {self.host}:{self.port} - Make sure the server is running and the port is open")
                self.server_error = True
                self.error_message = f"Connection refused by {self.host}:{self.port}. Make sure the server is running and the port is open in the firewall."
            else:
                self.logger.info(f'Socket error connecting to server: {str(e)}')
                self.server_error = True
                self.error_message = f"Error connecting to server: {str(e)}"
            return False

        except Exception as e:
            self.logger.info(f'Error connection to server: {str(e)}')
            self.server_error = True
            self.error_message = f"Connection error: {str(e)}"
            return False

    def check_server_heartbeat(self):
        while self.connected:
            if time.time() - self.last_server_response > self.heartbeat_timeout:
                self.logger.info("Server heartbeat timeout - no response")
                self.server_error = True
                self.error_message = "Server connection lost: No response"
                self.connected = False
            time.sleep(1)

    def receive_data(self):
        buffer_size = 8192

        while self.connected:
            try:
                data = self.client_socket.recv(buffer_size)

                if not data:
                    self.logger.info("Empty data received from server - disconnected")
                    self.server_error = True
                    self.error_message = "Server disconnected"
                    self.connected = False
                    break

                self.last_server_response = time.time()

                try:
                    response = pickle.loads(data)

                    if 'status' in response:
                        if response['status'] == 'match_start':
                            self.match_started = True
                            self.game_state = response['game_state']
                            self.init_platforms()
                        elif response['status'] == 'game_over':
                            self.logger.info(f'Game over received with winner: {response.get('winner')}')
                            self.game_over = True
                            self.winner = response.get('winner')
                            if 'game_state' in response:
                                self.game_state = response['game_state']
                        elif response['status'] == 'server_error':
                            self.server_error = True
                            self.error_message = response.get('message', "Server reported an error")
                            self.logger.info(f'Server error: {self.error_message}')
                        elif response['status'] == 'heartbeat':
                            continue
                    else:
                        if 'players' in response:
                            for player_num, player_data in response['players'].items():
                                if player_num in self.game_state.get('players', {}):
                                    self.game_state['players'][player_num].update(player_data)
                                else:
                                    if 'players' not in self.game_state:
                                        self.game_state['players'] = {}
                                    self.game_state['players'][player_num] = player_data

                        if 'platforms' in response and response['platforms'] != self.game_state.get('platforms'):
                            self.game_state['platforms'] = response['platforms']
                            self.init_platforms()

                    players = self.game_state.get('players', {})
                    if isinstance(players, dict):
                        for player_num, player_data in players.items():
                            if isinstance(player_data, dict) and player_data.get('is_dead', False):
                                opponent_num = 1 if int(player_num) == 2 else 2
                                if not self.game_over:
                                    self.game_over = True
                                    self.winner = opponent_num
                                    self.logger.info(f'Detected game over state! Winner: {self.winner}')

                    opponent_num = 2 if self.player_num == 1 else 1
                    if (isinstance(self.game_state.get('players', {}), dict) and
                            opponent_num in self.game_state['players'] and
                            self.game_state['players'][opponent_num].get('character') and
                            not self.opponent_character):
                        self.opponent_character = self.game_state['players'][opponent_num]['character']
                        self.opponent_sprite = self.create_character_sprite(self.opponent_character)

                except pickle.UnpicklingError as e:
                    self.logger.info(f'Error unpickling data: {str(e)}')
                    continue

            except (socket.error, ConnectionResetError, ConnectionAbortedError) as e:
                self.logger.info(f'socket connection error: {str(e)}')
                self.server_error = True
                self.error_message = f'Server connection lost: {str(e)}'
                self.connected = False
                break

            except Exception as e:
                self.logger.info(f'Error receiving data: {str(e)}')
                self.server_error = True
                self.error_message = f'Error processing server data: {str(e)}'
                self.connected = False
                break

    def send_data(self, data):
        try:
            if self.client_socket and self.connected:
                self.client_socket.send(pickle.dumps(data))
        except Exception as e:
            self.logger.info(f'Error sending data: {str(e)}')
            self.server_error = True
            self.error_message = f'Cannot send data to server: {str(e)}'
            self.connected = False

    def draw_error_popup(self):
        overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        overlay.fill(self.BLACK)
        overlay.set_alpha(180)
        self.screen.blit(overlay, (0, 0))

        popup_width, popup_height = 700, 300
        popup_x = (self.SCREEN_WIDTH - popup_width) // 2
        popup_y = (self.SCREEN_HEIGHT - popup_height) // 2

        pygame.draw.rect(self.screen, self.DARK_BLUE,
                         (popup_x, popup_y, popup_width, popup_height))
        pygame.draw.rect(self.screen, self.RED,
                         (popup_x, popup_y, popup_width, popup_height), 4)

        title_text = self.font.render("SERVER ERROR", True, self.RED)
        title_rect = title_text.get_rect(center=(self.SCREEN_WIDTH //2, popup_y + 60))
        self.screen.blit(title_text, title_rect)

        error_lines = []
        words = self.error_message.split()
        line = ""
        for word in words:
            test_line = line + " " + word if line else word
            if self.small_font.size(test_line)[0] <= popup_width - 40:
                line = test_line
            else:
                error_lines.append(line)
                line = word
        if line:
            error_lines.append(line)

        for i, line in enumerate(error_lines):
            msg_text = self.small_font.render(line, True, self.WHITE)
            msg_rect = msg_text.get_rect(center=(self.SCREEN_WIDTH // 2, popup_y + 120 + i * 30))
            self.screen.blit(msg_text, msg_rect)

        exit_text = self.small_font.render("Press ESC to exit", True, self.YELLOW)
        exit_rect = exit_text.get_rect(center=(self.SCREEN_WIDTH // 2, popup_y + popup_height - 50))
        self.screen.blit(exit_text, exit_rect)

    def select_character(self):
        selecting = True

        while selecting and self.connected:
            self.screen.fill(self.BLACK)

            title_text = self.font.render(f'Player {self.player_num} - Select Character', True, self.WHITE)
            title_rect = title_text.get_rect(center=(self.SCREEN_WIDTH/2, 100))
            self.screen.blit(title_text, title_rect)

            for i, char_name in enumerate(self.available_characters):
                color = self.GREEN if i == self.selected_character_index else self.WHITE
                char_text = self.small_font.render(char_name, True, color)
                char_rect = char_text.get_rect(center=(self.SCREEN_WIDTH/2, 300 + i*50))
                self.screen.blit(char_text, char_rect)
            instr_text = self.small_font.render('Press UP/DOWN to select, ENTER to confirm', True, self.WHITE)
            instr_rect = instr_text.get_rect(center=(self.SCREEN_WIDTH/2, 600))
            self.screen.blit(instr_text, instr_rect)

            if self.server_error:
                self.draw_error_popup()

            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == KEYDOWN:
                    if event.key == K_UP:
                        self.selected_character_index = (self.selected_character_index - 1) % len(self.available_characters)
                    elif event.key == K_DOWN:
                        self.selected_character_index = (self.selected_character_index + 1) % len(self.available_characters)
                    elif event.key == K_RETURN:
                        self.character = self.available_characters[self.selected_character_index]
                        self.send_data({'character_select': self.character})
                        selecting = False
            pygame.display.flip()
            self.clock.tick(60)

    def wait_for_match(self):
        waiting = True
        while waiting and self.connected and not self.match_started:
            self.screen.fill(self.BLACK)
            wait_text = self.font.render('Waiting for opponent...', True, (self.WHITE))
            wait_rect = wait_text.get_rect(center=(self.SCREEN_WIDTH/2, 300))
            self.screen.blit(wait_text, wait_rect)

            char_text = self.small_font.render(f'Your character: {self.character}', True, self.GREEN)
            char_rect = char_text.get_rect(center=(self.SCREEN_WIDTH/2, 400))
            self.screen.blit(char_text, char_rect)

            if not self.ready:
                ready_text = self.small_font.render('Press SPACE to ready up', True, self.WHITE)
                ready_rect = ready_text.get_rect(center=(self.SCREEN_WIDTH/2, 500))
                self.screen.blit(ready_text, ready_rect)
            else:
                ready_text = self.small_font.render('You are READY!', True, self.GREEN)
                ready_rect = ready_text.get_rect(center=(self.SCREEN_WIDTH/2, 500))
                self.screen.blit(ready_text, ready_rect)

            if self.server_error:
                self.draw_error_popup()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == K_ESCAPE and self.server_error:
                        pygame.quit()
                        sys.exit()
                    if event.key == K_SPACE and not self.ready and not self.server_error:
                        self.ready = True
                        self.send_data({'ready': True})

            pygame.display.flip()
            self.clock.tick(60)

    def draw_background(self):
        for y in range(self.SCREEN_HEIGHT):
            color = (
                self.DARK_BLUE[0] + (self.BLUE[0] - self.DARK_BLUE[0]) * y // self.SCREEN_HEIGHT,
                self.DARK_BLUE[1] + (self.BLUE[1] - self.DARK_BLUE[1]) * y // self.SCREEN_HEIGHT,
                self.DARK_BLUE[2] + (self.BLUE[2] - self.DARK_BLUE[2]) * y // self.SCREEN_HEIGHT
            )
            pygame.draw.line(self.screen, color, (0, y), (self.SCREEN_WIDTH, y))

        pygame.draw.polygon(self.screen, self.GRAY, [(0, self.SCREEN_HEIGHT), (300, 500), (500, self.SCREEN_HEIGHT)])
        pygame.draw.polygon(self.screen, self.GRAY, [(500, self.SCREEN_HEIGHT), (700, 400), (900, self.SCREEN_HEIGHT)])

    def init_platforms(self):
        self.platforms = []
        for platform_data in self.game_state['platforms']:
            platform = type('Platform', (), platform_data)
            self.platforms.append(platform)

    def draw_platforms(self):
        for platform in self.platforms:
            pygame.draw.rect(self.screen, self.DARK_BLUE, (platform.x, platform.y, platform.width, platform.height))
            pygame.draw.rect(self.screen, self.WHITE, (platform.x, platform.y, platform.width, 5))

    def create_character_sprite(self, character_name):
        character_colors = {
            'Lucario': (0, 0, 255),
            'Mewtwo': (255, 0, 255),
            'Zeraora': (255, 255, 0),
            'Cinderace': (255, 0, 0)
        }

        try:
            sprite = f"sprites/{character_name.lower()}_sprite.png"
            img = pygame.image.load(sprite).convert_alpha()
            return pygame.transform.scale(img, (100, 100))

        except Exception as e:
            self.logger.info(f"Error loading sprite for {character_name}: {str(e)}")

            surface = pygame.surface.Surface((100, 100))
            color = character_colors.get(character_name, (255, 0, 0))
            surface.fill(color)
            return surface

    def draw_character(self, player_data, sprite):
        if not player_data:
            return

        # Draw the character sprite
        self.screen.blit(sprite, (player_data['x'] - sprite.get_width() // 2,
                                  player_data['y'] - sprite.get_height()))

        # Draw health bar
        bar_width = 100
        bar_height = 10
        bar_x = player_data['x'] - bar_width // 2
        bar_y = player_data['y'] - sprite.get_height() - 20

        pygame.draw.rect(self.screen, self.RED, (bar_x, bar_y, bar_width, bar_height))
        health_width = (player_data['health'] / 100) * bar_width
        if health_width > 0:
            pygame.draw.rect(self.screen, self.GREEN, (bar_x, bar_y, health_width, bar_height))
        pygame.draw.rect(self.screen, self.BLACK, (bar_x, bar_y, bar_width, bar_height), 1)

    def draw_game_over_screen(self):
        overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        overlay.fill(self.BLACK)
        overlay.set_alpha(180)
        self.screen.blit(overlay, (0, 0))

        winner_color = self.GREEN if self.winner == int(self.player_num) else self.RED

        border_width, border_height = 600, 300
        border_x = (self.SCREEN_WIDTH - border_width) // 2
        border_y = (self.SCREEN_HEIGHT - border_height) // 2
        pygame.draw.rect(self.screen, self.DARK_BLUE,
                         (border_x, border_y, border_width, border_height))
        pygame.draw.rect(self.screen, winner_color,
                         (border_x, border_y, border_width, border_height), 6)

        game_over_text = self.font.render("GAME OVER", True, self.WHITE)
        game_over_rect = game_over_text.get_rect(center=(self.SCREEN_WIDTH / 2, self.SCREEN_HEIGHT / 2 - 70))
        self.screen.blit(game_over_text, game_over_rect)

        if self.winner:
            if self.winner == int(self.player_num):
                winner_text = "YOU WIN!"
            else:
                winner_text = 'YOU LOSE!'

            text = self.font.render(winner_text, True, winner_color)
            text_rect = text.get_rect(center=(self.SCREEN_WIDTH / 2, self.SCREEN_HEIGHT / 2))
            self.screen.blit(text, text_rect)

        exit_text = self.small_font.render("Press ESC to exit", True, self.WHITE)
        exit_rect = exit_text.get_rect(center=(self.SCREEN_WIDTH / 2, self.SCREEN_HEIGHT / 2 + 60))
        self.screen.blit(exit_text, exit_rect)

    def check_on_platform(self, player_x, player_y, feet_offset):
        if len(self.platforms) == 0:
            self.logger.info('Warning: No platform available')
            return True, None

        player_width = 50
        player_feet_y = player_y + feet_offset
        player_velocity_y = self.game_state['players'][self.player_num].get('velocity_y', 0) if self.player_num in self.game_state['players'] else 0

        player_prev_feet_y = player_feet_y - player_velocity_y

        steps = max(3, int(abs(player_velocity_y) / 5))

        if player_prev_feet_y > player_feet_y:
            start_y, end_y = player_feet_y, player_prev_feet_y
        else:
            start_y, end_y = player_prev_feet_y, player_feet_y
        step_size = (end_y - start_y) / steps if steps > 0 else 0

        for i in range(steps + 1):
            check_y = start_y + step_size * i

            for platform in self.platforms:
                if (player_x + player_width > platform.x and
                player_x - player_width < platform.x + platform.width):
                    if platform.y - 20 <= check_y <= platform.y + 20:
                        return True, platform.y
        return False, None

    def check_death(self, player_y):
        if len(self.platforms) == 0:
            return False
        lowest_platform_y = max(platform.y for platform in self.platforms)
        return player_y > lowest_platform_y + 100

    def run_game(self):
        current_time = pygame.time.get_ticks()

        if not self.character_sprite and self.character:
            self.character_sprite = self.create_character_sprite(self.character)
            self.logger.info(f'Character: {self.character}')

        if not self.opponent_sprite:
            self.opponent_sprite = pygame.Surface((100, 100))
            self.opponent_sprite.fill((255, 0, 0))

        opponent_num = 2 if self.player_num == 1 else 1
        if opponent_num in self.game_state['players'] and self.game_state['players'][opponent_num].get('character'):
            opponent_character = self.game_state['players'][opponent_num]['character']
            self.logger.info(f'Opponent character: {opponent_character}')
            if not self.opponent_character or self.opponent_character != opponent_character:
                self.opponent_character = opponent_character
                self.opponent_sprite = self.create_character_sprite(opponent_character)

        running = True
        last_attack_time = 0
        last_special_attack_time = 0
        special_attack_cooldown = 3000
        is_jumping = False
        jump_velocity = 0
        gravity = 0.8
        jump_strength = 18
        player_width = 50
        player_feet_offset = 10
        player_data = None
        last_action_time = time.time()
        action_throttle = 0.02

        predicted_player_state = None
        last_input_sequence = 0
        input_sequence_number = 0
        pending_inputs = []

        last_opponent_state = None
        current_opponent_state = None
        opponent_lerp_factor = 0.3

        while running:
            frame_start_time = time.time()

            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                    pygame.quit()
                    sys.exit()
                if event.type == KEYDOWN and event.key == K_ESCAPE:
                    if self.server_error or self.game_over:
                        running = False
                        pygame.quit()
                        sys.exit()

            self.screen.fill(self.BLACK)
            self.draw_background()
            self.draw_platforms()

            if self.player_num in self.game_state['players']:
                server_player_state = self.game_state['players'][self.player_num]
                if predicted_player_state is None:
                    predicted_player_state = server_player_state.copy()
                self.logger.info(f'player state: {predicted_player_state}')

                if 'x' in server_player_state and 'x' in predicted_player_state:
                    if abs(server_player_state['x'] - predicted_player_state['x']) > 15:
                        predicted_player_state['x'] = server_player_state['x']
                if 'y' in server_player_state and 'y' in predicted_player_state:
                    if abs(server_player_state['y'] - predicted_player_state['y']) > 15:
                        predicted_player_state['y'] = server_player_state['y']
                        predicted_player_state['velocity_y'] = server_player_state.get('velocity_y', 0)
                if 'health' in server_player_state:
                    predicted_player_state['health'] = server_player_state['health']

                self.draw_character(predicted_player_state, self.character_sprite)


            if opponent_num in self.game_state['players']:
                opponent_state = self.game_state['players'][opponent_num]

                if current_opponent_state is None:
                    current_opponent_state = opponent_state.copy()

                else:
                    if 'x' in opponent_state and 'x' in current_opponent_state:
                        current_opponent_state['x'] += (opponent_state['x'] - current_opponent_state['x']) * opponent_lerp_factor
                    if 'y' in opponent_state and 'y' in current_opponent_state:
                        current_opponent_state['y'] += (opponent_state['y'] - current_opponent_state['y']) * opponent_lerp_factor

                    if 'health' in opponent_state:
                        current_opponent_state['health'] = opponent_state['health']
                    if 'is_attacking' in opponent_state:
                        current_opponent_state['is_attacking'] = opponent_state['is_attacking']
                    if 'is_special_attacking' in opponent_state:
                        current_opponent_state['is_special_attacking'] = opponent_state['is_special_attacking']
                    if 'facing_right' in opponent_state:
                        current_opponent_state['facing_right'] = opponent_state['facing_right']

                self.logger.info(f'opponent state: {current_opponent_state}')

                self.draw_character(current_opponent_state, self.opponent_sprite)

                if self.server_error:
                    self.draw_error_popup()
                elif self.game_over:
                    self.draw_game_over_screen()
                elif self.match_started and self.connected:
                    current_time = pygame.time.get_ticks()
                    keys = pygame.key.get_pressed()

                    if self.player_num not in self.game_state['players']:
                        pygame.display.flip()
                        self.clock.tick(60)
                        continue

                    if time.time() - last_action_time >= action_throttle:
                        action = {}
                        action_taken = False

                        if self.player_num == 1:
                            left_key = K_q
                            right_key = K_d
                            jump_key = K_z
                            attack_key = K_a
                            special_attack_key = K_e
                        else:
                            left_key = K_LEFT
                            right_key = K_RIGHT
                            jump_key = K_UP
                            attack_key = K_k
                            special_attack_key = K_l

                        if keys[left_key]:
                            if 'x' in predicted_player_state:
                                predicted_player_state['x'] = max(50, predicted_player_state['x'] - 5)
                                action['x'] = predicted_player_state['x']
                                action['facing_right'] = False
                                predicted_player_state['facing_right'] = False
                                action_taken = True

                        elif keys[right_key]:
                            if 'x' in predicted_player_state:
                                predicted_player_state['x'] = min(950, predicted_player_state['x'] + 5)
                                action['x'] = predicted_player_state['x']
                                action['facing_right'] = True
                                predicted_player_state['facing_right'] = True
                                action_taken = True

                        on_platform, platform_y = self.check_on_platform(
                            predicted_player_state.get('x', 0),
                            predicted_player_state.get('y', 0),
                            player_feet_offset
                        )

                        if keys[jump_key] and on_platform and not is_jumping:
                            is_jumping = True
                            predicted_player_state['velocity_y'] = -jump_strength
                            jump_velocity = -jump_strength
                            action['is_jumping'] = True
                            action['velocity_y'] = predicted_player_state['velocity_y']
                            action_taken = True

                        if is_jumping or not on_platform:
                            predicted_player_state['y'] += jump_velocity
                            jump_velocity += gravity
                            predicted_player_state['velocity_y'] = jump_velocity
                            action['y'] = predicted_player_state['y']
                            action['velocity_y'] = predicted_player_state['velocity_y']
                            action_taken = True

                        on_platform_now, landing_y = self.check_on_platform(
                            predicted_player_state.get('x', 0),
                            predicted_player_state.get('y', 0),
                            player_feet_offset
                        )

                        if not on_platform:
                            predicted_player_state['y'] += gravity
                            predicted_player_state['velocity_y'] += gravity
                            action['velocity_y'] = predicted_player_state['velocity_y']
                            action_taken = True

                        if on_platform_now and jump_velocity > 0:
                            is_jumping = False
                            jump_velocity = 0
                            predicted_player_state['velocity_y'] = 0
                            predicted_player_state['y'] = landing_y
                            action['y'] = landing_y
                            action['is_jumping'] = False
                            action['velocity_y'] = 0
                            action_taken = True

                        if self.check_death(predicted_player_state.get('y', 0)):
                            action['died'] = True
                            predicted_player_state['is_dead'] = True
                            self.send_data({'player_died': True})
                            action_taken = True

                        if keys[attack_key] and current_time - last_attack_time > 500:
                            action['is_attacking'] = True
                            predicted_player_state['is_attacking'] = True
                            action['attack'] = True
                            action['damage'] = 10
                            action['attack_range'] = 150
                            last_attack_time = current_time
                            action_taken = True

                        if keys[
                            special_attack_key] and current_time - last_special_attack_time > special_attack_cooldown:
                            action['is_special_attacking'] = True
                            predicted_player_state['is_special_attacking'] = True
                            action['attack'] = True

                            if self.character == 'Lucario':
                                health_percent = predicted_player_state.get('health', 100) / 100
                                action['damage'] = 25 * (1 + (1 - health_percent))
                                action['attack_range'] = 200
                            elif self.character == 'Mewtwo':
                                action['damage'] = 30
                                action['attack_range'] = 300
                            elif self.character == 'Zeraora':
                                action['damage'] = 20
                                action['attack_range'] = 150
                            elif self.character == 'Cinderace':
                                opponent_data = current_opponent_state
                                if opponent_data:
                                    distance = abs(predicted_player_state.get('x', 0) - opponent_data.get('x', 0))
                                    action['damage'] = 22 * (1 + distance / 250)
                                    action['attack_range'] = 250

                            last_special_attack_time = current_time
                            action_taken = True
                        if action and action_taken and self.connected:
                            self.send_data({'player_action': action})
                            last_action_time = time.time()

            pygame.display.flip()
            self.clock.tick(60)

    def run(self):
        if self.connect_to_server():
            self.select_character()
            self.wait_for_match()
            self.run_game()

            if self.client_socket:
                self.client_socket.close()
        else:
            self.logger.info('Failed to connect to server')
            self.server_error = True
            self.error_message = 'Failed to connect to server'

            running = True
            while running:
                self.screen.fill(self.BLACK)
                self.draw_error_popup()

                for event in pygame.event.get():
                    if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                        running = False
                pygame.display.flip()
                self.clock.tick(60)

            pygame.quit()
            sys.exit()

if __name__ == '__main__':
    import sys
    host = 'localhost'
    port = 5555
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()
        server_ip = simpledialog.askstring("Server IP",
                                           "Enter server IP address:\n(leave empty for localhost)")

        if server_ip and server_ip.strip():
            host = server_ip.strip()

    print(f"Connecting to server at {host}:{port}")

    client = GameClient(host=host, port=port)
    client.run()





