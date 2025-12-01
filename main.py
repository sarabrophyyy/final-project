# main game file - Once Upon a Platform
import pygame
import sys
from pathlib import Path

pygame.init()
pygame.mixer.init()  # for sounds/music

# basic settings
WIDTH, HEIGHT = 1000, 600
FPS = 60
GRAVITY = 0.8
PLAYER_SPEED = 5
PLAYER_JUMP_POWER = -15
FONT_NAME = pygame.font.get_default_font()
ASSETS_DIR = Path("assets")


def load_image(name, size=None):
    p = ASSETS_DIR / name
    if p.exists():
        img = pygame.image.load(p).convert_alpha()
        if size: img = pygame.transform.scale(img, size)
        return img
    # simple colored surface for now as placeholder for assets
    surf = pygame.Surface(size if size else (40, 40), pygame.SRCALPHA)
    surf.fill((200, 100, 255, 255))
    return surf

def load_sound(name):
    p = ASSETS_DIR / name
    if p.exists():
        return pygame.mixer.Sound(p)
    return None

def load_music(name):
    p = ASSETS_DIR / name
    if p.exists():
        pygame.mixer.music.load(p)
        return True
    return False

# game window
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Once Upon a Platform")
clock = pygame.time.Clock()

# fonts
def get_font(size=24):
    return pygame.font.Font(FONT_NAME, size)

# objects in game
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill((60, 150, 60))  # green-ish
        self.rect = self.image.get_rect(topleft=(x, y))

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = load_image("coin.png", (24, 24))
        # fallback: find image for coin
        if getattr(self.image, "get_alpha", None) and self.image.get_at((0,0))[3] == 255 and self.image.get_size() == (24,24):
            pass
        self.rect = self.image.get_rect(center=(x, y))

class Goal(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = load_image("flag.png", (48, 64))
        self.rect = self.image.get_rect(midbottom=(x, y))

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, patrol_left, patrol_right, speed=2):
        super().__init__()
        self.image = load_image("enemy.png", (40, 40))
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.speed = speed
        self.left_bound = patrol_left
        self.right_bound = patrol_right
        self.vx = speed

    def update(self, platforms):
        self.rect.x += self.vx
        # reverse at bounds
        if self.rect.left < self.left_bound:
            self.rect.left = self.left_bound
            self.vx *= -1
        if self.rect.right > self.right_bound:
            self.rect.right = self.right_bound
            self.vx *= -1
        # gravity so enemy stays on platform if needed
        self.rect.y += 5
        # drop until on a platform
        collided = pygame.sprite.spritecollideany(self, platforms)
        if collided:
            self.rect.bottom = collided.rect.top

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # use drawings for character animation (square to fall back on)
        self.images_right = [load_image("player_idle.png", (40, 56))]
        self.images_left = [pygame.transform.flip(img, True, False) for img in self.images_right]
        # square fallback here
        if not self.images_right[0]:
            surf = pygame.Surface((40, 56))
            surf.fill((120, 180, 255))
            self.images_right = [surf]
            self.images_left = [pygame.transform.flip(surf, True, False)]
        self.image = self.images_right[0]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.facing_right = True
        self.anim_timer = 0
        self.score = 0
        self.lives = 3

    def handle_input(self):
        keys = pygame.key.get_pressed()
        self.vx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx = -PLAYER_SPEED
            self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = PLAYER_SPEED
            self.facing_right = True
        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.vy = PLAYER_JUMP_POWER
            self.on_ground = False
            if jump_snd: jump_snd.play()

    def apply_gravity(self):
        self.vy += GRAVITY
        if self.vy > 20:
            self.vy = 20

    def update(self, platforms, coins, enemies, goal):
        self.handle_input()
        # hoirzontal movement
        self.rect.x += self.vx
        collided = pygame.sprite.spritecollide(self, platforms, False)
        for plat in collided:
            if self.vx > 0:
                self.rect.right = plat.rect.left
            elif self.vx < 0:
                self.rect.left = plat.rect.right

        # vertical movement
        self.apply_gravity()
        self.rect.y += self.vy
        self.on_ground = False
        collided = pygame.sprite.spritecollide(self, platforms, False)
        for plat in collided:
            # falling
            if self.vy > 0:
                self.rect.bottom = plat.rect.top
                self.vy = 0
                self.on_ground = True
            elif self.vy < 0:
                self.rect.top = plat.rect.bottom
                self.vy = 0

        # coin collection
        coin_hit = pygame.sprite.spritecollide(self, coins, True)
        if coin_hit:
            self.score += len(coin_hit)
            if coin_snd: coin_snd.play()

        # enemy collisions
        enemy_hit = pygame.sprite.spritecollide(self, enemies, False)
        for e in enemy_hit:
            # player jumps and hits enemy from above -> stomp
            if self.vy > 0 and (self.rect.bottom - e.rect.top) < 15:
                # kill enemy
                try:
                    enemies.remove(e)
                except Exception:
                    pass
                self.vy = PLAYER_JUMP_POWER / 2  # bounce a little bit
                if stomp_snd: stomp_snd.play()
                self.score += 1
            else:
                # hit by enemy -> lose life and respawn
                if hit_snd: hit_snd.play()
                self.lives -= 1
                return "HIT_ENEMY"

        # check the goal
        if pygame.sprite.collide_rect(self, goal):
            if win_snd: win_snd.play()
            return "WIN"

        return None

    def draw(self, surf, offset_x):
        # simple draw with facing flip
        img = self.images_right[0] if self.facing_right else self.images_left[0]
        surf.blit(img, (self.rect.x + offset_x, self.rect.y))

# layout/optics of the level
def build_level():
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    # ground
    platforms.add(Platform(0, HEIGHT - 40, 2500, 40))

    # some platforms (x, y, w, h)
    platform_data = [
        (300, 460, 120, 20),
        (500, 380, 120, 20),
        (700, 300, 120, 20),
        (920, 420, 120, 20),
        (1200, 360, 160, 20),
        (1450, 460, 120, 20),
        (1700, 340, 120, 20),
        (1900, 420, 120, 20),
    ]
    for x,y,w,h in platform_data:
        platforms.add(Platform(x, y, w, h))

    # coins placed above platforms
    coin_positions = [
        (340, 430), (540, 350), (740, 270), (960, 390), (1240, 330),
        (1480, 430), (1740, 310), (1940, 390)
    ]
    for cx, cy in coin_positions:
        c = Coin(cx, cy)
        coins.add(c)

    # enemies with ranges they stay between (patrol ranges)
    enemies.add(Enemy(600, HEIGHT - 40, 550, 800))
    enemies.add(Enemy(1600, 460, 1450, 1750))
    enemies.add(Enemy(1800, 420, 1750, 2000))

    # goal at the end
    goal = Goal(2200, HEIGHT - 40)

    return platforms, coins, enemies, goal

# ---------- Load sounds / music ----------
jump_snd = load_sound("jump.wav")
coin_snd = load_sound("coin.wav")
stomp_snd = load_sound("stomp.wav")
hit_snd = load_sound("hit.wav")
win_snd = load_sound("win.wav")
music_loaded = load_music("bg_music.mp3")
if music_loaded:
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)

# title and game over screens
def title_screen():
    screen.fill((20, 24, 40))
    title_font = get_font(64)
    small = get_font(28)
    title_surf = title_font.render("ONCE UPON A PLATFORM", True, (255, 215, 0))
    subtitle = small.render("The Most Magical Game on Earth - Press ENTER to play", True, (240,240,240))
    screen.blit(title_surf, title_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 40)))
    screen.blit(subtitle, subtitle.get_rect(center=(WIDTH//2, HEIGHT//2 + 40)))
    pygame.display.flip()
    waiting = True
    while waiting:
        clock.tick(15)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    waiting = False

def game_over_screen(score):
    screen.fill((30, 10, 10))
    f1 = get_font(64)
    f2 = get_font(28)
    s1 = f1.render("GAME OVER", True, (255, 80, 80))
    s2 = f2.render(f"Score: {score}  — Press R to Restart or Q to Quit", True, (255,255,255))
    screen.blit(s1, s1.get_rect(center=(WIDTH//2, HEIGHT//2 - 40)))
    screen.blit(s2, s2.get_rect(center=(WIDTH//2, HEIGHT//2 + 30)))
    pygame.display.flip()
    waiting = True
    while waiting:
        clock.tick(15)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    waiting = False
                if event.key == pygame.K_q:
                    pygame.quit(); sys.exit()

def win_screen(score):
    screen.fill((10, 40, 20))
    f1 = get_font(64)
    f2 = get_font(28)
    s1 = f1.render("YOU WIN!", True, (255, 220, 100))
    s2 = f2.render(f"Score: {score}  — Press R to Play Again or Q to Quit", True, (255,255,255))
    screen.blit(s1, s1.get_rect(center=(WIDTH//2, HEIGHT//2 - 40)))
    screen.blit(s2, s2.get_rect(center=(WIDTH//2, HEIGHT//2 + 30)))
    pygame.display.flip()
    waiting = True
    while waiting:
        clock.tick(15)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    waiting = False
                if event.key == pygame.K_q:
                    pygame.quit(); sys.exit()

# MAIN GAME LOOP
def run_game():
    platforms, coins, enemies, goal = build_level()
    player = Player(120, HEIGHT - 200)

    all_sprites = pygame.sprite.Group()
    all_sprites.add(platforms)
    all_sprites.add(coins)
    all_sprites.add(enemies)
    all_sprites.add(goal)
    all_sprites.add(player)

    camera_x = 0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

        # update enemies
        enemies.update(platforms)

        result = player.update(platforms, coins, enemies, goal)
        if result == "HIT_ENEMY":
            if player.lives <= 0:
                return "GAME_OVER", player.score
            else:
                # respawn to start area
                player.rect.topleft = (120, HEIGHT - 200)
                player.vx = player.vy = 0
        if result == "WIN":
            return "WIN", player.score

        # camera follows player & center player a bit right of center to give look-ahead
        target_cam = -(player.rect.centerx - WIDTH // 2 + 100)
        # don't show negative far left, assuming level starts at x=0
        min_cam = -(0)
        max_cam = -(2200 - WIDTH + 200)  # allow some space to the right
        camera_x = max(max_cam, min(min_cam, target_cam))

        # draw background
        screen.fill((120, 180, 255))  # sky color
        # draw a plain castle silhouette background for theme
        pygame.draw.rect(screen, (90, 60, 180), (50 + camera_x/5, HEIGHT - 300, 400, 300))
        pygame.draw.polygon(screen, (70, 40, 140), [(300 + camera_x/5, HEIGHT - 300), (330 + camera_x/5, HEIGHT - 400), (360 + camera_x/5, HEIGHT - 300)])

        # draw platforms
        for plat in platforms:
            screen.blit(plat.image, (plat.rect.x + camera_x, plat.rect.y))

        # draw coins
        for c in coins:
            screen.blit(c.image, (c.rect.x + camera_x, c.rect.y))

        # draw enemies
        for e in enemies:
            screen.blit(e.image, (e.rect.x + camera_x, e.rect.y))

        # draw goal
        screen.blit(goal.image, (goal.rect.x + camera_x, goal.rect.y))

        # draw player
        player.draw(screen, camera_x)

        # score and lives
        score_text = get_font(24).render(f"Score: {player.score}", True, (255,255,255))
        lives_text = get_font(24).render(f"Lives: {player.lives}", True, (255,255,255))
        screen.blit(score_text, (16, 8))
        screen.blit(lives_text, (16, 36))

        pygame.display.flip()



# main function
def main():
    # show title screen
    title_screen()

    while True:
        status, score = run_game()
        if status == "GAME_OVER":
            game_over_screen(score)
        elif status == "WIN":
            win_screen(score)
        # loop continues to restart the game

if __name__ == "__main__":
    main()

