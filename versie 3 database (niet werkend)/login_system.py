import pygame
import pygame_gui
import pickle
import socket
import logging
import threading
import time
from typing import Dict, Any, Optional, Tuple

class LoginSystem:
    def __init__(self, screen_width=1000, screen_height=800, client_socket=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Fighting Game - Login")

        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s [CLIENT] %(message)s',
                            datefmt='%H:%M:%S')
        self.logger = logging.getLogger('LoginSystem')

        self.manager = pygame_gui.UIManager((screen_width, screen_height))
        self.client_socket = client_socket
        self.current_user = None

        self.background = pygame.Surface((screen_width, screen_height))
        self.background.fill((50, 50, 80))

        self.create_ui()
        self.logger.info(f'client_socket: {client_socket}')

    def create_ui(self):
        panel_width, panel_height = 400, 350
        panel_rect = pygame.Rect((self.screen_width - panel_width)//2,
                                 (self.screen_height - panel_height)//2,
                                 panel_width, panel_height)
        self.panel = pygame_gui.elements.UIPanel(relative_rect=panel_rect,
                                                 manager=self.manager)

        title_rect = pygame.Rect(50, 20, 300, 30)
        self.title_label = pygame_gui.elements.UILabel(relative_rect=title_rect,
                                                       text="FIGHTING GAME - LOGIN",
                                                       manager=self.manager,
                                                       container=self.panel)

        username_label_rect = pygame.Rect(50, 70, 300, 20)
        self.username_label = pygame_gui.elements.UILabel(relative_rect=username_label_rect,
                                                          text='Username',
                                                          manager=self.manager,
                                                          container=self.panel)

        username_entry_rect = pygame.Rect(50, 95, 300, 30)
        self.username_entry = pygame_gui.elements.UITextEntryLine(relative_rect=username_entry_rect,
                                                                  manager=self.manager,
                                                                  container=self.panel)

        password_label_rect = pygame.Rect(50, 135, 300, 20)
        self.password_label = pygame_gui.elements.UILabel(relative_rect=password_label_rect,
                                                          text="Password:",
                                                          manager=self.manager,
                                                          container=self.panel)

        password_entry_rect= pygame.Rect(50, 160, 300, 30)
        self.password_entry = pygame_gui.elements.UITextEntryLine(relative_rect=password_entry_rect,
                                                          manager=self.manager,
                                                          container=self.panel)

        self.password_entry.set_text_hidden(True)

        login_button_rect = pygame.Rect(50, 215, 140, 40)
        self.login_button = pygame_gui.elements.UIButton(relative_rect=login_button_rect,
                                                         text="Login",
                                                         manager=self.manager,
                                                         container=self.panel)

        register_button_rect = pygame.Rect(210, 215, 140, 40)
        self.register_button = pygame_gui.elements.UIButton(relative_rect=register_button_rect,
                                                            text="Register",
                                                            manager=self.manager,
                                                            container=self.panel)

        status_rect = pygame.Rect(50, 280, 300, 20)
        self.status_label = pygame_gui.elements.UILabel(relative_rect=status_rect,
                                                        text="",
                                                        manager=self.manager,
                                                        container=self.panel)

    def show_message(self, message, is_error=False):
        self.status_label.set_text(message)
        if is_error:
            self.status_label.text_colour = pygame.Color('#FF3030')
        else:
            self.status_label.text_colour = pygame.Color('#30FF30')
        self.status_label.rebuild()

    def login(self, username, password):
        if not self.client_socket:
            self.show_message("No connection to server", True)
            return False

        try:
            self.client_socket.send(pickle.dumps({
                'action': 'login',
                'username': username,
                'password': password
            }))

            response = pickle.loads(self.client_socket.recv(4096))

            if response.get('status') == 'success':
                self.current_user = response.get('user_data')
                self.show_message(f'Welcome, {username}!')
                self.logger.info(f'User logged in: {username}')
                return True

            else:
                self.show_message(response.get('message', 'Login failed'), True)
                return False

        except Exception as e:
            self.logger.error(f'Error during login: {str(e)}')
            self.show_message('connection error', True)
            return False

    def register(self, username, password):
        self.logger.info(f'Username: {username}')
        self.logger.info(f'Password: {password}')
        if not self.client_socket:
            self.show_message('No connection to server', True)
            return False

        try:
            self.client_socket.send(pickle.dumps({
                'action': 'register',
                'username':username,
                'password': password
            }))

            response = pickle.loads(self.client_socket.recv(4096))

            if response.get('status')=='success':
                self.show_message('Registration succesful! You can now login.')
                return True
            else:
                self.show_message(response.get('message', 'Registration Failed'))
                return False

        except Exception as e:
            self.logger.error(f'Error during registration:{str(e)}')
            self.show_message('Connection error', True)
            return False

    def run(self):
        clock = pygame.time.Clock()
        running = True

        while running:
            time_delta = clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.login_button:
                        username = self.username_entry.get_text()
                        password = self.password_entry.get_text()

                        if not username or not password:
                            self.show_message("Please enter username and password", True)
                        else:
                            if self.login(username, password):
                                return True, self.current_user

                    elif event.ui_element == self.register_button:
                        username = self.username_entry.get_text()
                        password = self.password_entry.get_text()

                        if not username or not password:
                            self.show_message("Please enter username and password", True)
                        elif len(username) < 3 or len(username) > 20:
                            self.show_message("Username must be 3-20 characters long", True)
                        elif len(password) < 6:
                            self.show_message("Password must be at least 6 characters", True)
                        else:
                            self.register(username, password)

                self.manager.process_events(event)

            self.manager.update(time_delta)

            # Draw everything
            self.screen.blit(self.background, (0, 0))
            self.manager.draw_ui(self.screen)

            pygame.display.update()

        return False, None

class GameClient:
    def __init__(self, server_host='localhost', server_port=5555):
        pygame.init()
        self.screen_width = 1000
        self.screen_height = 800
        self.screen = None

        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s [CLIENT] %(message)s',
                            datefmt='%H:%M:%S')
        self.logger = logging.getLogger('GameClient')

        self.server_host = server_host
        self.server_port = server_port
        self.client_socket = None
        self.player_num = None
        self.user_data = None

        self.connect_to_server()

        if self.client_socket:
            login_system = LoginSystem(self.screen_width, self.screen_height, self.client_socket)
            login_success, user_data = login_system.run()

            if login_success:
                self.user_data = user_data
                self.start_game()
            else:
                self.logger.info("Login cancelled or failed")
                pygame.quit()
        else:
            self.logger.error("Could not establish connection to server")
            pygame.quit()

    def connect_to_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_host, self.server_port))
            response = pickle.loads(self.client_socket.recv(4096))

            if response.get('status') == 'connected':
                self.player_num = response.get('player_num')
                self.logger.info(f'Connected to server as player {self.player_num}')

                heartbeat_thread = threading.Thread(target=self.handle_heartbeat)
                heartbeat_thread.daemon = True
                heartbeat_thread.start()

                return True

            else:
                self.logger.error(f'Connection failed: {response.get('message', 'unknown error')}')
                return False

        except Exception as e:
            self.logger.error(f'Error connecting to server: {str(e)}')

    def handle_heartbeat(self):
        while True:
            try:
                data = self.client_socket.recv(4096)

                if not data:
                    self.logger.error('Lost connection to server')
                    break

                server_message = pickle.loads(data)

                if server_message.get('status') == 'heartbeat':
                    pass
                elif server_message.get('status') == 'game_state_update':
                    pass
                elif server_message.get('status') == 'match_start':
                    pass
                elif server_message.get('status') == 'game_over':
                    pass

            except Exception as e:
                self.logger.error(f'Error in heartbeat handler= {str(e)}')
                break

    def start_game(self):
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption(f'Fighting game - Player {self.player_num}')

        self.logger.info('Starting game with user:' + self.user_data['account_name'])

        self.show_character_selection()

    def show_character_selection(self):
        pass

    def login_success_handler(self, user_data):
        self.logger.info(f'User logged in: {user_data['account_name']}')
        self.user_data = user_data
        self.start_game()


if __name__ == "__main__":
    client = GameClient()


