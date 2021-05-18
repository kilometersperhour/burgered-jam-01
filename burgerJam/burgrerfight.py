import pygame,sys
from pygame.locals import *
import os

WHITE=(255,255,255)
BLUE=(0,0,255)
RED=(255,0,0)
GREEN=(0,255,0)

class Burger(object):
    def __init__(self):
        self.image = pygame.image.load("burgrer.png")
        self.eyes = pygame.image.load("eyes_right.png")
        center1 = 100
        center2 = 200
        self.center = [center1, center2]
        self.centereyes = [center1+35, center2+30]
        self.health = 100

    def move(self, x, y):
        self.center[0] += x
        self.centereyes[0] += x
        self.center[1] += y
        self.centereyes[1] += y


    def draw(self, surf):
        #surf.blit(self.eyes, self.centereyes)
        surf.blit(self.image, self.center)
        surf.blit(self.eyes, self.centereyes)
    def hit(self):
        self.health = self.health - 10

class BurgerEnemy(object):
    def __init__(self):
        self.image = pygame.image.load("burgrer.png")
        self.center = [300, 200]
        self.health = 100

    def move(self, x, y):
        self.center[0] += x
        self.center[1] += y

    def draw(self, surf):
        surf.blit(self.image, self.center)


class game(object):

    def __init__(self):
        #WIDTH = 1200
        #HEIGHT = 600
        display_width = 1200
        display_height = 600
        self.health = 10
        self.bg = pygame.image.load("bcg.png")
        self.center = [0, 0]
        #gameDisplay = pygame.display.set_mode((display_width,display_height))
        self.screen = pygame.display.set_mode((display_width,display_height))
        self.clock = pygame.time.Clock()
        self.player = Burger()
        self.enemy = BurgerEnemy()

    def draw(self, surf):
        surf.blit(self.bg, self.center)

    def drawHealth(self, surf):

        pygame.draw.rect(self.screen,RED,(50,40,500,40))
        pygame.draw.rect(self.screen,GREEN,(50,40,self.player.health*5,40))
        pygame.draw.rect(self.screen,RED,(650,40,500,40))
        pygame.draw.rect(self.screen,GREEN,(650,40,500,40))

    def run(self):
        pygame.init()
        pygame.mixer.music.load('burgarena.mp3')
        pygame.mixer.music.set_volume(0.2)
        pygame.mixer.music.play(loops = -1)
        running = 1
        while running:
            self.clock.tick(60)
            event = pygame.event.poll()
            if event.type == pygame.QUIT:
                running = 0

            keys = pygame.key.get_pressed()
            move_x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
            move_y = keys[pygame.K_DOWN] - keys[pygame.K_UP]
            self.player.move(move_x * 5, move_y * 5)
            self.draw(self.screen)
            self.drawHealth(self.screen)
            #self.screen.fill([255, 255, 255])
            self.player.draw(self.screen)
            self.enemy.draw(self.screen)

            #pygame.mixer.music.load('burgarena.mp3')
            #pygame.mixer.music.set_volume(0.2)
            #pygame.mixer.music.play(loops = -1)
            pygame.display.update()


g = game()
g.run()
