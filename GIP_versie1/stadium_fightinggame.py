import pygame
from pygame.locals import *
from Characters_fightinggame import CharacterManager
import sys

def create_sprite_surface(width, height):
    return pygame.surface.Surface((width, height), pygame.SRCALPHA)

def load_pixel_art(image_path, scale_factor=3):

    try:
        image = pygame.image.load(image_path)
        width = image.get_width() * scale_factor
        height = image.get_height() * scale_factor
        return pygame.transform.scale(image, (width, height))
    except Exception as e:
        print(f"Error loading pixel art: {str(e)}")
        return None

class Platform:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

class Stadium:
    def __init__(self, player1_character, player2_character):
        pygame.init()
        self.SCREEN_WIDTH = 1000
        self.SCREEN_HEIGHT = 1000

        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.GRAY = (100, 100, 100)
        self.BLUE = (50, 150, 255)
        self.DARK_BLUE = (30, 30, 120)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)

        self.player1_character=None
        self.player2_character=None
        self.player1 = None
        self.player2 = None

        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        pygame.display.set_caption("Fighting game stadium")
        self.clock = pygame.time.Clock()

        self.character_manager = CharacterManager()
        if player1_character:
            self.character_manager.set_character(player1_character, True)
        if player2_character:
            self.character_manager.set_character(player2_character, False)

        self.platforms = []
        self.init_platforms()

        self.font = pygame.font.Font(None, 74)
        self.small_font = pygame.font.Font(None, 36)

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

    def draw_platform(self):
        platform_width1 = 600
        platform_height = 20
        platform_x1 = (self.SCREEN_WIDTH - platform_width1) // 2
        platform_y1 = 600
        platform_width2 = 100
        platform_x2 = (self.SCREEN_WIDTH - platform_width2) // 2.25
        platform_y2 = 300
        platform_x3 = (self.SCREEN_WIDTH - platform_width2) // 1.75
        platform_y3 = 450

        #platforms of the stadium
        pygame.draw.rect(self.screen, self.DARK_BLUE, (platform_x1, platform_y1, platform_width1, platform_height))
        pygame.draw.rect(self.screen, self.WHITE, (platform_x1, platform_y1, platform_width1, 5))
        pygame.draw.rect(self.screen, self.DARK_BLUE, (platform_x2, platform_y2, platform_width2, platform_height))
        pygame.draw.rect(self.screen, self.WHITE, (platform_x2, platform_y2, platform_width2, 5))
        pygame.draw.rect(self.screen, self.DARK_BLUE, (platform_x3, platform_y3, platform_width2, platform_height))
        pygame.draw.rect(self.screen, self.WHITE, (platform_x3, platform_y3, platform_width2, 5))

    def init_platforms(self):
        platform_width1 = 600
        platform_height = 20
        platform_x1 = (self.SCREEN_WIDTH - platform_width1) //2
        platform_y1 = 600

        platform_width2 = 100
        platform_x2 = (self.SCREEN_WIDTH - platform_width2) // 2.25
        platform_y2 = 300
        platform_x3 = (self.SCREEN_WIDTH - platform_width2) // 1.75
        platform_y3 = 450

        self.platforms = [
            Platform(platform_x1, platform_y1, platform_width1, platform_height),
            Platform(platform_x2, platform_y2, platform_width2, platform_height),
            Platform(platform_x3, platform_y3, platform_width2, platform_height)
        ]
    def draw_game_over_screen(self):
        overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        overlay.fill(self.BLACK)
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))

        winner_text = ""
        if self.character_manager.player1 and self.character_manager.player2:
            if self.character_manager.player1.is_dead:
                winner_text = "PLAYER 2 WINS!"
            elif self.character_manager.player2.is_dead:
                winner_text = "PLAYER 1 WINS!"

        if winner_text:
            text = self.font.render(winner_text, True, self.GREEN)
            text_rect = text.get_rect(center=(self.SCREEN_WIDTH/2, self.SCREEN_HEIGHT/2))
            self.screen.blit(text, text_rect)

        exit_text = self.small_font.render("Press ESC to exit", True, self.WHITE)
        exit_rect = exit_text.get_rect(center=(self.SCREEN_WIDTH/2, self.SCREEN_HEIGHT/2 + 60))
        self.screen.blit(exit_text, exit_rect)

    def run(self):
        running = True
        clock = pygame.time.Clock()
        while running:
            current_time = pygame.time.get_ticks()

            pygame.display.flip()
            clock.tick(60)

            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                if event.type == KEYDOWN and event.key == K_ESCAPE:
                    running = False

            keys = pygame.key.get_pressed()
            self.character_manager.update(keys, self.platforms, current_time)

            self.screen.fill(self.BLACK)
            self.draw_background()
            self.draw_platform()

            self.character_manager.draw(self.screen)

            if (self.character_manager.player1 and self.character_manager.player1.is_dead or
                (self.character_manager.player2 and self.character_manager.player2.is_dead)):
                self.draw_game_over_screen()

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()