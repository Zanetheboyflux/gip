import pygame
import pygame_menu
import os
import sys
from stadium_fightinggame import Stadium


class GameMenu:
    def __init__(self):
        pygame.init()
        self.res = (900, 900)
        self.screen = pygame.display.set_mode(self.res)
        pygame.display.set_caption("Character Selection Menu")

        self.player1_character = None
        self.player2_character = None

    def start_the_game(self):
        if self.player1_character and self.player2_character:
            print(f"Starting game with Player 1: {self.player1_character}, Player 2: {self.player2_character}")

            stadium = Stadium(self.player1_character, self.player2_character)
            stadium.run()
        else:
            print("Please select characters for both players!")

    def set_character_p1(self, selected_value, _):
        self.player1_character = selected_value[0][0]
        print(f'Player 1 character selected: {self.player1_character}')

    def set_character_p2(self, selected_value, _):
        self.player2_character = selected_value[0][0]
        print(f'Player 2 character selected: {self.player2_character}')

    def add_baseimage(self, image_path, scale=(50, 50)):
        """Load and scale an image, with error handling"""
        try:
            # Check if file exists
            if not os.path.exists(image_path):
                print(f"Image file not found: {image_path}")
                # Return a colored rectangle as fallback
                surface = pygame.Surface(scale)
                surface.fill((255, 0, 0))  # Red rectangle as placeholder
                return pygame_menu.BaseImage(surface)

                # Load and convert the image
                image = pygame.image.load(image_path).convert_alpha()
                # Scale the image
                scaled_image = pygame.transform.scale(image, scale)
                # Create surface and blit the image
                surface = pygame.Surface(scale, pygame.SRCALPHA)
                surface.blit(scaled_image, (0, 0))

                return pygame_menu.BaseImage(surface)
        except Exception as e:
            print(f"Error loading image {image_path}: {str(e)}")
            # Return a colored rectangle as fallback
            surface = pygame.Surface(scale)
            surface.fill((255, 0, 0))  # Red rectangle as placeholder
            return pygame_menu.BaseImage(surface)

    def run(self):
        # Create menu theme
        mytheme = pygame_menu.themes.THEME_DARK.copy()
        mytheme.widget_font_size = 20

        # Create the menu
        menu = pygame_menu.Menu(
            'Character Selection',
            650, 400,
            theme=mytheme
        )

        try:
            # Load character images
            characters = [
                ('Lucario', self.add_baseimage("sprites/lucario_sprite.png")),
                ('Cinderace', self.add_baseimage("sprites/cinderace_sprite.png")),
                ('Zeraora', self.add_baseimage("sprites/zeraora_sprite.png")),
                ('Mewtwo', self.add_baseimage("sprites/mewtwo_sprite.png"))
            ]

            # Add widgets to the menu
            menu.add.label('Player 1')
            menu.add.selector(
                'choose character:',
                [(char[0], char[1]) for char in characters],
                onchange=self.set_character_p1
            )

            menu.add.vertical_margin(30)

            menu.add.label('Player 2')
            menu.add.selector(
                'Choose character:',
                [(char[0], char[1]) for char in characters],
                onchange=self.set_character_p2
            )

            menu.add.vertical_margin(30)
            menu.add.button('Play', self.start_the_game)
            menu.add.button('Quit', pygame_menu.events.EXIT)

            menu.mainloop(self.screen)

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            pygame.quit()
            sys.exit()


if __name__ == '__main__':
    game = GameMenu()
    game.run()

