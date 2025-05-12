import pygame

class Character:
    def __init__(self, name, x, y):
        self.name = name
        self.x = x
        self.y = y
        self.scale = (100, 100)
        self.sprite = self.load_sprite()

        self.max_health = 100
        self.current_health = self.max_health
        self.health_bar_width = 100
        self.health_bar_height = 10

        self.velocity_y = 0
        self.velocity_x = 0
        self.is_jumping = False
        self.move_speed = 5
        self.jump_force = -15
        self.gravity = 0.8
        self.ground_y = 900
        self.on_platform = False
        self.is_dead = False
        self.death_y = 700

        self.rect = pygame.Rect(x - self.scale[0]//2, y - self.scale[1], self.scale[0], self.scale[1])

        self.last_special_attack_time = 0
        self.special_attack_cooldown = 10000
        self.basic_attack_damage = 10
        self.attack_range = 150
        self.is_attacking = False
        self.is_special_attacking = False
        self.facing_right = False

        if self.name == 'Lucario':
            self.special_attack_damage = 25
            self.attack_range = 200
        elif self.name == 'Mewtwo':
            self.special_attack_damage = 30
            self.attack_range = 300
        elif self.name == 'Zeraora':
            self.special_attack_damage = 20
            self.attack_range = 150
            self.special_attack_cooldown = 2000
        elif self.name == 'Cinderace':
            self.special_attack_damage = 22
            self.attack_range = 250

    def load_sprite(self):

        character_colors = {
            'Lucario': (0, 0, 255),
            'Mewtwo': (255, 0, 255),
            'Zeraora': (255, 255, 0),
            'Cinderace': (255, 0, 0)
        }

        try:
            sprite_path = f"sprites/{self.name.lower()}_sprite.png"
            img = pygame.image.load(sprite_path).convert_alpha()
            return pygame.transform.scale(img, self.scale)

        except Exception as e:
            print(f"Error loading sprite for {self.name}: {str(e)}")

            surface = pygame.surface.Surface(self.scale)
            color = character_colors.get(self.name, (255, 0, 0))
            surface.fill(color)
            return surface

    def check_platform_collision(self, platforms):
        self.rect.x = self.x - self.scale[0] // 2
        self.rect.y = self.y - self.scale[1]

        if self.velocity_y > 0:
            for platform in platforms:
                if self.rect.right >= platform.x and self.rect.left <= platform.x + platform.width:
                    current_bottom = self.rect.bottom

                    if abs(current_bottom - platform.y) <= abs(self.velocity_y + self.gravity) + 1:
                        self.y = platform.y
                        self.velocity_y = 0
                        self.is_jumping = False
                        self.on_platform = True
                        return True

                    elif self.velocity_y > 0 and current_bottom >= platform.y and current_bottom <= platform.y + platform.height:
                        self.y = platform.y
                        self.velocity_y = 0
                        self.is_jumping = False
                        self.on_platform = True
                        return True

        self.on_platform = False
        return False

    def draw_health_bar(self, screen):
        bar_x = self.x - self.health_bar_width // 2
        bar_y = self.y - self.scale[1] - 20

        pygame.draw.rect(screen, (255, 0, 0),
                         (bar_x, bar_y, self.health_bar_width, self.health_bar_height))

        health_width = (self.current_health / self.max_health) * self.health_bar_width
        if health_width > 0:
            pygame.draw.rect(screen, (0, 255, 0),
                             (bar_x, bar_y, health_width, self.health_bar_height))

        pygame.draw.rect(screen, (0, 0, 0),
                         (bar_x, bar_y, self.health_bar_width, self.health_bar_height), 1)

    def perform_basic_attack(self, other_character):
        if other_character and not self.is_dead and not other_character.is_dead:
            distance = abs(self.x - other_character.x)

            is_target_right = other_character.x > self.x
            if distance <= self.attack_range and self.facing_right == is_target_right:
                other_character.take_damage(self.basic_attack_damage)
                self.is_attacking = True
                return True
        return False

    def perform_special_attack(self, other_character, current_time):
        if other_character and not self.is_dead and not other_character.is_dead:
            if current_time - self.last_special_attack_time >= self.special_attack_cooldown:
                distance = abs(self.x - other_character.x)
                is_target_right = other_character.x > self.x

                if distance <= self.attack_range and self.facing_right == is_target_right:
                    damage = self.special_attack_damage
                    if self.name == 'Lucario':
                        # Aura Sphere - More damage at lower health
                        damage = self.special_attack_damage * (1+ (1 - self.current_health/self.max_health))
                    elif self.name == 'Mewtwo':
                        # Psystrike - Ignores distance penalty
                        damage = self.special_attack_damage
                    elif self.name == 'Zeraora':
                        # Plasma Fists - Chain lightning effect
                        damage = self.special_attack_damage
                        other_character.velocity_x = 10 if is_target_right else -10
                    elif self.name == 'Cinderace':
                        # Pyro Ball - More damage at longer range
                        damage = self.special_attack_damage * (1 + distance/self.attack_range)

                    other_character.take_damage(damage)
                    self.last_special_attack_time = current_time
                    self.is_special_attacking = True
                    return True
        return False

    def take_damage(self, damage):
        if not self.is_dead:
            self.current_health = max(0, self.current_health - damage)
            if self.current_health == 0:
                self.is_dead = True

    def check_death(self):
        if self.y > self.death_y:
            self.is_dead = True
            self.current_health = 0
            return True
        return False

    def move(self, keys, platforms, player_num=1):
        #forward and backward movement
        if player_num == 1:
            left_key = pygame.K_q
            right_key = pygame.K_d
            jump_key = pygame.K_z
        else:
            left_key = pygame.K_LEFT
            right_key = pygame.K_RIGHT
            jump_key = pygame.K_UP

        if keys[left_key]:
            self.x -= self.move_speed
            self.facing_right = False
        elif keys[right_key]:
            self.x += self.move_speed
            self.facing_right = True
        else:
            self.velocity_x = 0

        self.x += self.velocity_x

        #jumping
        if keys[jump_key] and not self.is_jumping:
            self.velocity_y = self.jump_force
            self.is_jumping = True
            self.on_platform = False

        #gravity
        self.velocity_y += self.gravity
        self.y += self.velocity_y

        if not self.check_platform_collision(platforms):
            if self.y >= self.ground_y:
                self.y = self.ground_y
                self.velocity_y = 0
                self.is_jumping = False
                self.on_platform = True

        #screen boundaries
        self.x = max(50, min(self.x, 950))

        self.check_death()

    def draw(self, screen):
        if self.sprite:
            screen.blit(self.sprite, (self.x - self.sprite.get_width()//2,
                                      self.y - self.sprite.get_height()))
            self.draw_health_bar(screen)


class CharacterManager:
    def __init__(self):
        self.player1 = None
        self.player2 = None

    def set_character(self, character_name, is_player1=True):
        if is_player1:
            self.player1 = Character(character_name, 300, 580)
        else:
            self.player2 = Character(character_name, 700, 580)

    def update(self, keys, platforms, current_time):

        if self.player1:
            self.player1.move(keys, platforms, 1)
            if keys[pygame.K_f]:
                self.player1.perform_basic_attack(self.player2)
            elif keys[pygame.K_g]:
                self.player1.perform_special_attack(self.player2, current_time)

        if self.player2:
            self.player2.move(keys, platforms, 2)
            if keys[pygame.K_k]:
                self.player2.perform_basic_attack(self.player1)
            elif keys[pygame.K_l]:
                self.player2.perform_special_attack(self.player1, current_time)

            # Reset attack states
        if self.player1:
            if not keys[pygame.K_f]:
                self.player1.is_attacking = False
            if not keys[pygame.K_g]:
                self.player1.is_special_attacking = False

        if self.player2:
            if not keys[pygame.K_k]:
                self.player2.is_attacking = False
            if not keys[pygame.K_l]:
                self.player2.is_special_attacking = False

    def draw(self, screen):
        if self.player1:
            self.player1.draw(screen)
        if self.player2:
            self.player2.draw(screen)