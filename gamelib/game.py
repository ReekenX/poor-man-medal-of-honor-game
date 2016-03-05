# core
import os
import sys
import math
import random
import math

# 3rd party
import pygame as pg

# local
import settings


TRANSPARENT = (0, 0, 0, 0)
COLOR_KEY = (255, 0, 255)
HALF_WIDTH = 640 / 2
HALF_HEIGHT = 480 / 2

DIRECT_DICT = {pg.K_a  : (-1, 0),
               pg.K_d : (1, 0),
               pg.K_w    : (0, -1),
               pg.K_s  : (0, 1)}


class Player(pg.sprite.Sprite):
    def __init__(self, rect, speed, direction=pg.K_d):
        pg.sprite.Sprite.__init__(self)
        self.rect = pg.Rect(rect)
        self.remainder = [0, 0]  #Adjust rect in integers; save remainders.
        self.mask = self.make_mask()
        self.speed = speed  #Pixels per second; not pixels per frame.
        self.direction = direction
        self.old_direction = None  #The Players previous direction every frame.
        self.direction_stack = []  #Held keys in the order they were pressed.
        self.redraw = False  #Force redraw if needed.
        self.image = None
        self.angle = -math.radians(135)
        self.lifes = 6

        self.sprites = pg.image.load(settings.IMG_DIR + "/player.png").convert_alpha()
        #  self.sprites.set_colorkey(COLOR_KEY)

        self.frame  = 0
        self.frames = self.get_frames()
        self.animate_timer = 0.0
        self.animate_fps = 7.0
        self.walkframes = []
        self.adjust_images()

    def make_mask(self):
        mask_surface = pg.Surface(self.rect.size).convert_alpha()
        mask_surface.fill(TRANSPARENT)
        mask_surface.fill(pg.Color("white"), (5,5,40,40))
        mask = pg.mask.from_surface(mask_surface)
        return mask

    def get_frames(self):
        indices = [[0,0], [1,0], [2,0], [3,0]]
        return get_images(self.sprites, indices, self.rect.size)

    def adjust_images(self):
        if self.direction != self.old_direction:
            self.walkframes = [self.frames[0], self.frames[1], self.frames[2], self.frames[3]]
            self.old_direction = self.direction
            self.redraw = True
        self.make_image()

    def make_image(self):
        now = pg.time.get_ticks()
        if self.redraw or now-self.animate_timer > 1000/self.animate_fps:
            self.frame = (self.frame+1)%len(self.walkframes)
            self.image = self.walkframes[self.frame]
            self.animate_timer = now
        if not self.image:
            self.image = self.walkframes[self.frame]
        self.redraw = False

    def add_direction(self, key):
        if key in DIRECT_DICT:
            if key in self.direction_stack:
                self.direction_stack.remove(key)
            self.direction_stack.append(key)
            self.direction = self.direction_stack[-1]

    def pop_direction(self, key):
        if key in DIRECT_DICT:
            if key in self.direction_stack:
                self.direction_stack.remove(key)
            if self.direction_stack:
                self.direction = self.direction_stack[-1]

    def update(self, obstacles, dt, camera):
        vector = [0, 0]
        for key in self.direction_stack:
            vector[0] += DIRECT_DICT[key][0]
            vector[1] += DIRECT_DICT[key][1]
        factor = (math.sqrt(2)/2 if all(vector) else 1)
        frame_speed = self.speed*factor*dt
        self.remainder[0] += vector[0]*frame_speed
        self.remainder[1] += vector[1]*frame_speed
        vector[0], self.remainder[0] = divfmod(self.remainder[0], 1)
        vector[1], self.remainder[1] = divfmod(self.remainder[1], 1)
        if vector != [0, 0]:
            self.adjust_images()
            self.movement(obstacles, vector[0], 0)
            self.movement(obstacles, vector[1], 1)

            camera.update(self)

    def movement(self, obstacles, offset, i):
        self.rect[i] += offset
        collisions = pg.sprite.spritecollide(self, obstacles, False)
        callback = pg.sprite.collide_mask
        while pg.sprite.spritecollideany(self, collisions, callback):
            self.rect[i] += (1 if offset<0 else -1)
            self.remainder[i] = 0

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def collides_with_enemy(self, enemy, camera):
        rect = camera.apply_rect(self.rect)
        return self.rect.colliderect(enemy)

    def collides_with_star(self, star, camera):
        rect = camera.apply_rect(self.rect)
        return self.rect.colliderect(star)


class Bullet(pg.sprite.Sprite):
    def __init__(self, location, angle):
        pg.sprite.Sprite.__init__(self)
        bullet_image = pg.image.load(settings.IMG_DIR + "/bullet.png").convert()
        bullet_image.set_colorkey(COLOR_KEY)
        self.original_bullet = bullet_image.subsurface((0,0,13,13))
        self.angle = -math.radians(angle-135)
        self.image = pg.transform.rotate(self.original_bullet, angle)
        self.rect = self.image.get_rect(center=location)
        self.move = [self.rect.x, self.rect.y]
        self.speed_magnitude = 15
        self.mask = self.make_mask()
        self.speed = (self.speed_magnitude*math.cos(self.angle),
                      self.speed_magnitude*math.sin(self.angle))
        self.done = False

    def make_mask(self):
        mask_surface = pg.Surface(self.rect.size).convert_alpha()
        mask_surface.fill(TRANSPARENT)
        mask_surface.fill(pg.Color("white"), (0,0,20,20))
        mask = pg.mask.from_surface(mask_surface)
        return mask

    def update(self, screen_rect):
        self.move[0] += self.speed[0]
        self.move[1] += self.speed[1]
        self.rect.topleft = self.move

    def check_collision(self, obstacles, camera):
        rect = camera.apply_rect(self.rect)
        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                self.kill()

                if type(obstacle) is Enemy:
                    obstacle.killed = True

                if type(obstacle) is Player:
                    obstacle.lifes -= 1


class Block(pg.sprite.Sprite):
    def __init__(self, location):
        pg.sprite.Sprite.__init__(self)
        self.image = self.make_image()
        self.rect = self.image.get_rect(topleft=location)
        self.mask = pg.mask.from_surface(self.image)

    def make_image(self):
        image = pg.image.load(settings.IMG_DIR + "/block.png").convert_alpha()
        image.set_colorkey(COLOR_KEY)
        image.blit(image, (0,0))
        return image

class Star(pg.sprite.Sprite):
    def __init__(self, location):
        pg.sprite.Sprite.__init__(self)
        self.image = self.make_image()
        self.rect = self.image.get_rect(topleft=location)
        self.mask = pg.mask.from_surface(self.image)

    def make_image(self):
        image = pg.image.load(settings.IMG_DIR + "/star.png").convert_alpha()
        image.blit(image, (0,0))
        return image

class Ground(pg.sprite.Sprite):
    def __init__(self, location):
        pg.sprite.Sprite.__init__(self)
        self.image = self.make_image()
        self.rect = self.image.get_rect(topleft=location)
        self.mask = pg.mask.from_surface(self.image)

    def make_image(self):
        image = pg.image.load(settings.IMG_DIR + "/ground" + str(random.randint(1, 6)) + ".png").convert_alpha()
        image.blit(image, (0,0))
        return image

class Enemy(pg.sprite.Sprite):
    def __init__(self, rect, speed, direction=pg.K_s):
        self.rect = pg.Rect(rect)
        self.vector = [0, 1]
        self.remainder = [0, 0]
        self.mask = self.make_mask()
        self.speed = speed
        self.direction = direction
        self.old_direction = None
        self.direction_stack = []
        self.redraw = False
        self.image = None

        self.sprites = pg.image.load(settings.IMG_DIR + "/enemy" + str(random.randint(1, 3)) + ".png").convert_alpha()

        self.shooting_time = pg.time.get_ticks()

        self.frame  = 0
        self.frames = self.get_frames()
        self.animate_timer = 0.0
        self.animate_fps = 7.0
        self.walkframes = []
        self.walkframe_dict = self.make_frame_dict()
        self.adjust_images()
        self.visible = True

        self.killed = False


    def make_mask(self):
        mask_surface = pg.Surface(self.rect.size).convert_alpha()
        mask_surface.fill(TRANSPARENT)
        mask_surface.fill(pg.Color("white"), (0,0,50,50))
        mask = pg.mask.from_surface(mask_surface)
        return mask

    def make_mask_player(self):
        mask_surface = pg.Surface(self.rect.size).convert_alpha()
        mask_surface.fill(TRANSPARENT)
        mask_surface.fill(pg.Color("white"), (5,5,40,40))
        mask = pg.mask.from_surface(mask_surface)
        return mask

    def get_frames(self):
        indices = [[0,0], [1,0], [2,0], [3,0]]
        return get_images(self.sprites, indices, self.rect.size)

    def make_frame_dict(self):
        frames = {pg.K_a: [self.frames[0], self.frames[1], self.frames[2], self.frames[3]],
                  pg.K_d: [self.frames[0], self.frames[1], self.frames[2], self.frames[3]],
                  pg.K_s: [self.frames[0], self.frames[1], self.frames[2], self.frames[3]],
                  pg.K_w: [self.frames[0], self.frames[1], self.frames[2], self.frames[3]]}
        return frames

    def adjust_images(self):
        if self.direction != self.old_direction:
            self.walkframes = self.walkframe_dict[self.direction]
            self.old_direction = self.direction
            self.redraw = True
        self.make_image()

    def make_image(self):
        now = pg.time.get_ticks()
        if self.redraw or now-self.animate_timer > 1000/self.animate_fps:
            self.frame = (self.frame+1)%len(self.walkframes)
            self.image = self.walkframes[self.frame]
            self.animate_timer = now
        if not self.image:
            self.image = self.walkframes[self.frame]
        self.redraw = False

    def update(self, obstacles, dt, camera):
        vector = self.vector[:] # copy list to prevent modification for global val
        factor = (math.sqrt(2)/2 if all(vector) else 1)
        frame_speed = self.speed*factor*dt
        self.remainder[0] += vector[0]*frame_speed
        self.remainder[1] += vector[1]*frame_speed
        vector[0], self.remainder[0] = divfmod(self.remainder[0], 1)
        vector[1], self.remainder[1] = divfmod(self.remainder[1], 1)
        if vector != [0, 0]:
            self.adjust_images()
            self.movement(obstacles, vector[0], 0)
            self.movement(obstacles, vector[1], 1)

    def movement(self, obstacles, offset, i):
        self.rect[i] += offset
        collisions = pg.sprite.spritecollide(self, obstacles, False)
        callback = pg.sprite.collide_mask
        while pg.sprite.spritecollideany(self, collisions, callback):
            self.rect[i] += (1 if offset<0 else -1)
            self.remainder[i] = 0
            rand_move = random.choice([pg.K_s, pg.K_a, pg.K_w, pg.K_d])
            while rand_move == self.direction:
                rand_move = random.choice([pg.K_s, pg.K_a, pg.K_w, pg.K_d])
                pass
            self.direction = rand_move
            if self.direction == pg.K_a:
                self.direction = pg.K_a
                self.vector = [-1, 0]
            elif self.direction == pg.K_w:
                self.direction = pg.K_w
                self.vector = [0, -1]
            elif self.direction == pg.K_s:
                self.direction = pg.K_s
                self.vector = [0, 1]
            elif self.direction == pg.K_d:
                self.direction = pg.K_d
                self.vector = [1, 0]

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class Game(object):
    def __init__(self):
        self.screen = pg.display.get_surface()
        self.screen_rect = self.screen.get_rect()
        self.clock = pg.time.Clock()
        self.fps = 60.0
        self.done = False
        self.closed = False
        self.keys = pg.key.get_pressed()
        self.player = Player((0,0,50,50), 190)
        self.player.rect.center = (100, 100)
        self.angle = -math.radians(10-135)
        self.mouse = None

        self.player_bullets = pg.sprite.Group()
        self.enemy_bullets = pg.sprite.Group()
        self.elements = []
        self.obstacles = []
        self.enemies = []
        self.stars = []

        self.bullets_left = 8

        self.font = pg.font.Font(settings.FONTS_DIR + '/Flames.ttf', 14)
        self.life_bar = pg.image.load(settings.IMG_DIR + "/life_bar.png").convert_alpha()
        self.life = pg.image.load(settings.IMG_DIR + "/life.png").convert_alpha()


    def get_angle(self, mouse):
        self.mouse = mouse
        offset = (mouse[1]-(self.player.rect.centery + self.camera.state.y), mouse[0]-(self.player.rect.centerx + self.camera.state.x))
        self.angle = 135-math.degrees(math.atan2(*offset))

    def load_map(self):
        blocks = []
        elements = []
        self.enemies = []
        f = open(settings.DATA_DIR + '/map.txt', 'r')
        row = 0
        random.seed(3) # to make ground load the same, but "random"
        for line in f.readlines():
            column = 0
            for char in line:
                if char == '#':
                    blocks.append(Block((column*50, row*50)))
                    column += 1
                    continue
                elif char == 'E':
                    enemy = Enemy((0, 0, 50, 50), 100)
                    enemy.rect.center = (column*50, row*50)
                    self.enemies.append(enemy)
                elif char == 'S':
                    self.stars.append(Star((column*50+20, row*50+20)))
                elements.append(Ground((column*50, row*50)))
                column += 1
            self.camera_width = column * 50
            row += 1
        self.camera_height = row * 50
        self.obstacles = pg.sprite.Group(blocks)
        self.elements = pg.sprite.Group(elements)


        border_color = (0, 0, 0)
        for obj in self.obstacles:
            draw_top = True
            draw_right = True
            draw_left = True
            draw_bottom = True
            for obj2 in self.obstacles:
                if obj2.rect.left - 50 == obj.rect.left and obj2.rect.top == obj.rect.top:
                    draw_left = False
                if obj2.rect.right + 50 == obj.rect.right and obj2.rect.top == obj.rect.top:
                    draw_right = False
                if obj2.rect.top - 50 == obj.rect.top and obj2.rect.left == obj.rect.left:
                    draw_bottom = False
                if obj2.rect.bottom + 50 == obj.rect.bottom and obj2.rect.left == obj.rect.left:
                    draw_top = False
            if draw_right:
                pg.draw.line(obj.image, border_color, (0, 0), (0, 50))
            if draw_top:
                pg.draw.line(obj.image, border_color, (0, 0), (50, 0))
            if draw_bottom:
                pg.draw.line(obj.image, border_color, (0, 49), (50, 49))
            if draw_left:
                pg.draw.line(obj.image, border_color, (49, 0), (49, 50))


    def event_loop(self):
        for event in pg.event.get():
            self.keys = pg.key.get_pressed()
            if event.type == pg.QUIT or self.keys[pg.K_ESCAPE]:
                self.done = True
                self.closed = True
            elif event.type == pg.KEYDOWN and self.keys[pg.K_i]:
                #  import pdb
                #  pdb.set_trace()
                print 'Player at: '
                print self.player.rect
                print self.player.rect.x
                print self.player.rect.y
                print 'Camera at: '
                print self.camera.state
                print 'Painting at: '
                print  [(self.mouse[0], self.mouse[1]), (self.player.rect.centerx + abs(self.camera.state.x), self.player.rect.centery + abs(self.camera.state.y))]
                print 'Angle:'
                print self.angle
            elif event.type == pg.KEYDOWN:
                self.player.add_direction(event.key)
            elif event.type == pg.KEYUP:
                self.player.pop_direction(event.key)

            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if self.bullets_left > 0:
                    self.player_bullets.add(Bullet(self.player.rect.center, self.angle))
                    self.bullets_left -= 1
            elif event.type == pg.MOUSEMOTION:
                self.get_angle(event.pos)


    def draw(self):
        # draw ground
        i = 0
        for obj in self.elements:
            rect = self.camera.apply(obj)
            if rect.colliderect(self.screen_rect):
                self.screen.blit(obj.image, rect)

        # draw blocks
        for obj in self.obstacles:
            rect = self.camera.apply(obj)
            if rect.colliderect(self.screen_rect):
                self.screen.blit(obj.image, rect)

        # draw stars
        for obj in self.stars:
            rect = self.camera.apply(obj)
            if rect.colliderect(self.screen_rect):
                self.screen.blit(obj.image, rect)

        # draw player
        self.screen.blit(pg.transform.rotate(self.player.image, self.angle +135), self.camera.apply(self.player))

        # draw enemies
        distance = 300
        margin = 100
        for enemy in self.enemies:
            rect = self.camera.apply(enemy)
            enemy.visible = rect.colliderect(self.screen_rect)
            if enemy.visible:
                if enemy.direction == pg.K_w:
                    self.screen.blit(pg.transform.rotate(enemy.image, 0), rect)
                elif enemy.direction == pg.K_d:
                    self.screen.blit(pg.transform.rotate(enemy.image, 270), rect)
                elif enemy.direction == pg.K_s:
                    self.screen.blit(pg.transform.rotate(enemy.image, 180), rect)
                else:
                    self.screen.blit(pg.transform.rotate(enemy.image, 90), rect)

                if math.sqrt((self.player.rect.x - enemy.rect.x)**2 + (self.player.rect.y - enemy.rect.y)**2) < distance:
                    #  pg.draw.lines(self.screen, (200, 150, 150), 1, [(self.player.rect.x + self.camera.state.x, self.player.rect.y + self.camera.state.y), (enemy.rect.x + self.camera.state.x, enemy.rect.y + self.camera.state.y)])
                    if enemy.direction == pg.K_w:
                        rect = pg.Rect(
                                enemy.rect.x - margin / 2,
                                enemy.rect.y - distance,
                                margin * 2,
                                distance)
                        #  pg.draw.rect(self.screen, (200, 150, 150), self.camera.apply_rect(rect), 1)
                    elif enemy.direction == pg.K_s:
                        rect = pg.Rect(
                                enemy.rect.x - margin / 2,
                                enemy.rect.y,
                                margin * 2,
                                distance)
                        #  pg.draw.rect(self.screen, (200, 150, 150), self.camera.apply_rect(rect), 1)
                    elif enemy.direction == pg.K_d:
                        rect = pg.Rect(
                                enemy.rect.x,
                                enemy.rect.y - margin / 2,
                                distance,
                                margin * 2)
                        #  pg.draw.rect(self.screen, (200, 150, 150), self.camera.apply_rect(rect), 1)
                    elif enemy.direction == pg.K_a:
                        rect = pg.Rect(
                                enemy.rect.x - distance,
                                enemy.rect.y - margin / 2,
                                distance,
                                margin * 2)
                        #  pg.draw.rect(self.screen, (200, 150, 150), self.camera.apply_rect(rect), 1)
                    if rect.colliderect(self.player):
                        #  pg.draw.lines(self.screen, (200, 150, 150), 1, [(enemy.rect.x + self.camera.state.x, enemy.rect.y + self.camera.state.y), (enemy.rect.x + self.camera.state.x, enemy.rect.y + self.camera.state.y - distance)])
                        now = pg.time.get_ticks()
                        if now-enemy.shooting_time > 200:
                            enemy.shooting_time = now
                            dx = enemy.rect.x - self.player.rect.x
                            dy = enemy.rect.y - self.player.rect.y
                            rads = math.atan2(-dy,dx)
                            rads %= 2*math.pi
                            angle = math.degrees(rads) - 40
                            self.enemy_bullets.add(Bullet(enemy.rect.center, angle))
                    #  if enemy.direction == pg.K_s:
                        #  pg.draw.lines(self.screen, (200, 150, 150), 1, [(enemy.rect.x + self.camera.state.x, enemy.rect.y + self.camera.state.y), (enemy.rect.x + self.camera.state.x, enemy.rect.y + self.camera.state.y + distance)])
                    #  if enemy.direction == pg.K_d:
                        #  pg.draw.lines(self.screen, (200, 150, 150), 1, [(enemy.rect.x + self.camera.state.x, enemy.rect.y + self.camera.state.y), (enemy.rect.x + self.camera.state.x + distance, enemy.rect.y + self.camera.state.y)])
                    #  if enemy.direction == pg.K_a:
                        #  pg.draw.lines(self.screen, (200, 150, 150), 1, [(enemy.rect.x + self.camera.state.x, enemy.rect.y + self.camera.state.y), (enemy.rect.x + self.camera.state.x - distance, enemy.rect.y + self.camera.state.y)])

        # draw shootings
        for obj in self.player_bullets:
            rect = self.camera.apply(obj)
            if rect.colliderect(self.screen_rect):
                self.screen.blit(obj.image, rect)

        for obj in self.enemy_bullets:
            rect = self.camera.apply(obj)
            if rect.colliderect(self.screen_rect):
                self.screen.blit(obj.image, rect)

        self.screen.blit(self.font.render('Solder: John Doe', 1, (250, 250, 250)), (10, 10, 200, 50))
        #  self.screen.blit(self.font.render('Bullets: %d' % self.bullets_left, 1, (250, 250, 250)), (settings.SCREEN_SIZE[0]-140, settings.SCREEN_SIZE[1]-30, 500, 500))
        self.screen.blit(self.life_bar, (settings.SCREEN_SIZE[0] - 125 - 20, settings.SCREEN_SIZE[1] - 18 - 20, 125, 18))
        for i in range(0, self.player.lifes):
            self.screen.blit(self.life, (settings.SCREEN_SIZE[0] - 140 + i * 16 + i * 3, settings.SCREEN_SIZE[1] - 18 - 16, 125, 18))

        #  for obj in self.player_bullets:
            #  olist = obj.make_mask().outline()
            #  points = []
            #  for x, y in olist:
                #  points.append((x + obj.rect.left, y + obj.rect.top))
            #  pg.draw.lines(self.screen, (200, 150, 150), 1, points)

        #  if self.mouse:
            #  import pdb
            #  pdb.set_trace()
            #  pg.draw.lines(self.screen, (200, 150, 150), 1, [(self.mouse[0], self.mouse[1]), (self.player.rect.centerx + abs(self.camera.state.x), self.player.rect.right + abs(self.camera.state.y))])
            #  pg.draw.lines(self.screen, (200, 150, 150), 1, [(self.mouse[0], self.mouse[1]), (self.player.rect.centerx + self.camera.state.x, self.player.rect.centery + self.camera.state.y)])

    def display_fps(self):
        caption = "{} - FPS: {:.2f}".format(settings.SCREEN_TITLE, self.clock.get_fps())
        pg.display.set_caption(caption)

    def update(self, obstacles):
        for obj in self.player_bullets:
            obj.check_collision(obstacles, self.camera)
            obj.check_collision(self.enemies, self.camera)
        for obj in self.enemy_bullets:
            obj.check_collision(obstacles, self.camera)
            obj.check_collision([self.player], self.camera)
            if self.player.lifes < 1:
                self.done = True
        for enemy in self.enemies:
            if enemy.visible:
                if self.player.collides_with_enemy(enemy, self.camera):
                    self.player.kill()
                    sys.exit(0)
        for star in self.stars:
            if self.player.collides_with_star(star, self.camera):
                self.bullets_left += 8
                self.stars.remove(star)
        self.player_bullets.update(self.screen_rect)
        self.enemy_bullets.update(self.screen_rect)

    def main_loop(self):
        delta = self.clock.tick(self.fps)/1000.0

        loading_screen = True
        while loading_screen:
            block_img = pg.image.load(settings.IMG_DIR + "/ground1.png").convert_alpha()
            for i in range(0, settings.SCREEN_SIZE[0] / 50 + 1):
                for n in range(0, settings.SCREEN_SIZE[1] / 50 + 1):
                    self.screen.blit(block_img, (i * 50, n * 50, 50, 50))

            game_over_img = pg.image.load(settings.IMG_DIR + "/game_opening.png").convert_alpha()
            self.screen.blit(game_over_img, (settings.SCREEN_SIZE[0] / 2 - 528 / 2, settings.SCREEN_SIZE[1] / 2 - 294 / 2, 528, 294))
            pg.display.update()
            self.display_fps()

            for event in pg.event.get():
                self.keys = pg.key.get_pressed()
                if event.type == pg.QUIT or self.keys[pg.K_ESCAPE]:
                    sys.exit(0)
                elif event.type == pg.KEYDOWN:
                    loading_screen = False
                elif event.type == pg.MOUSEBUTTONDOWN:
                    loading_screen = False

        self.load_map()
        self.camera = Camera(complex_camera, self.camera_width, self.camera_height)

        while not self.done:
            self.event_loop()
            for enemy in self.enemies:
                if enemy.visible:
                    enemy.update(self.obstacles, delta, self.camera)
                    if enemy.killed:
                        self.enemies.remove(enemy)
            self.player.update(self.obstacles, delta, self.camera)
            self.update(self.obstacles)
            self.draw()
            pg.display.update()
            delta = self.clock.tick(self.fps)/1000.0
            self.display_fps()


        if not self.closed:
            while True:
                game_over_img = pg.image.load(settings.IMG_DIR + "/game_over.png").convert_alpha()
                self.screen.blit(game_over_img, (settings.SCREEN_SIZE[0] / 2 - 438 / 2, settings.SCREEN_SIZE[1] / 2 - 171 / 2, 438, 171))
                pg.display.update()
                self.display_fps()

                for event in pg.event.get():
                    self.keys = pg.key.get_pressed()
                    if event.type == pg.QUIT or self.keys[pg.K_ESCAPE]:
                        sys.exit(0)
                    elif event.type == pg.KEYDOWN and self.keys[pg.K_SPACE]:
                        Game().main_loop()
                        return


class Camera(object):
    def __init__(self, camera_func, width, height):
        self.camera_func = camera_func
        self.state = pg.Rect(0, 0, width, height)

    def apply(self, target):
        return target.rect.move(self.state.topleft)

    def apply_rect(self, rect):
        return rect.move(self.state.topleft)

    def update(self, target):
        self.state = self.camera_func(self.state, target.rect)

def simple_camera(camera, target_rect):
    l, t, _, _ = target_rect
    _, _, w, h = camera
    return pg.Rect(-l+HALF_WIDTH, -t+HALF_HEIGHT, w, h)

def complex_camera(camera, target_rect):
    l, t, _, _ = target_rect
    _, _, w, h = camera
    l, t, _, _ = -l+HALF_WIDTH, -t+HALF_HEIGHT, w, h

    l = min(0, l)                           # stop scrolling at the left edge
    l = max(-(camera.width-settings.SCREEN_SIZE[0]), l)   # stop scrolling at the right edge
    t = max(-(camera.height-settings.SCREEN_SIZE[1]), t) # stop scrolling at the bottom
    t = min(0, t)                           # stop scrolling at the top
    return pg.Rect(l, t, w, h)


def get_images(sheet, frame_indices, size):
    frames = []
    for cell in frame_indices:
        frame_rect = ((size[0]*cell[0],size[1]*cell[1]), size)
        frames.append(sheet.subsurface(frame_rect))
    return frames


def divfmod(x, y):
    fmod = math.fmod(x, y)
    div = (x-fmod)//y
    return div, fmod
