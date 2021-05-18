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
        #self.eyes = pygame.image.load("eyes_right.png")
        self.eyes = [pygame.image.load("eyes_right.png"),pygame.image.load("eyes_up.png"),pygame.image.load("eyes_left.png"),pygame.image.load("eyes_down.png")]
        #self.eyes[1] = pygame.image.load("eyes_up.png")
        #self.eyes[2] = pygame.image.load("eyes_left.png")
        #self.eyes[3] = pygame.image.load("eyes_down.png")

        #self.hands[0] = pygame.image.load("arm_idle.png")
        #self.hands[1] = pygame.image.load("arm_punched.png")
        #self.hands[2] = pygame.image.load("arm_punching.png")
        self.hands = [pygame.image.load("arm_idle.png",),  pygame.image.load("arm_punching.png"), pygame.image.load("arm_punched.png"), pygame.image.load("arm_idle.png",), pygame.image.load("arm_block.png",)]
        self.handIndexL = 0
        self.handIndexR = 0
        center1 = 100
        center2 = 200
        self.center = [center1, center2]
        self.centereyes = [center1+35, center2+30]
        self.centerRightArm = [center1+60 , center2+45]
        self.centerLeftArm = [center1+60 , center2+35]
        self.health = 100


    def move(self, x, y):
        self.center[0] += x
        self.centereyes[0] += x
        self.center[1] += y
        self.centereyes[1] += y

        self.centerLeftArm[0] += x
        self.centerLeftArm[1] += y

        self.centerRightArm[0] += x
        self.centerRightArm[1] += y

    def draw(self, surf):
        #surf.blit(self.eyes, self.centereyes)
        #surf.blit(self.eyes, self.centereyes)
        surf.blit(self.hands[self.handIndexL], self.centerLeftArm)
        surf.blit(self.image, self.center)
        surf.blit(self.eyes[0], self.centereyes)
        surf.blit(self.hands[self.handIndexR], self.centerRightArm)



    def hit(self):
        self.health = self.health - 10

    def punchLeft(self):
        for i in range(2):
            self.handIndexL +=1
        self.handIndexL = 0
    def punchRight(self):
        for i in range(2):
            self.handIndexR +=1
        self.handIndexR = 0
    #def block(self):



class BurgerEnemy(object):
    def __init__(self):
        self.image = pygame.image.load("burgrer.png")
        self.eyes = pygame.image.load("eyes_left.png")
        center1 = 1000
        center2 = 500
        self.center = [center1, center2]
        self.centereyes = [center1+35, center2+30]
        self.health = 100

    def move(self, x, y):
        self.center[0] += x
        self.centereyes[1] += x
        self.center[1] += y
        self.centereyes[1] += y

    def draw(self, surf):
        surf.blit(self.image, self.center)
        surf.blit(self.eyes, self.centereyes)


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

        self.last = pygame.time.get_ticks()
        self.cooldown = 300



    def draw(self, surf):
        surf.blit(self.bg, self.center)
    def col_check(x,y,w,h,x2,y2,w2,h2):
        if (x < (x2 + w2) and (x + w) > x2 and y < (y2 + h2) and (h + y) > y2):
            return True

    def drawHealth(self, surf):
        BLACK = (0,0,0)
        pygame.draw.rect(self.screen,BLACK,(40,30,520,60))
        pygame.draw.rect(self.screen,RED,(50,40,500,40))

        pygame.draw.rect(self.screen,GREEN,(50,40,self.player.health*5,40))
        pygame.draw.rect(self.screen,BLACK,(640,30,520,60))
        pygame.draw.rect(self.screen,RED,(650,40,500,40))
        pygame.draw.rect(self.screen,GREEN,(650,40,500,40))

    def run(self):

        #hitSound = pygame.mixer.Sound("hit.wav")
        switch = 0
        pygame.init()
        punchSound = [pygame.mixer.Sound("low_punch.wav"), pygame.mixer.Sound("normal_punch.wav"), pygame.mixer.Sound("high_punch.wav")]
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

            if event.type == pygame.MOUSEBUTTONDOWN:
                print(event.button)
                if event.button == 1:
                    punchSound[0].play()
                    #for i in range(2):
                    self.player.handIndexL += 1

                    if self.player.handIndexL == 3:
                        self.player.handIndexL = 0

                if event.button == 2:
                    #self.player.block()
                    punchSound[1].play()
                    if switch == 1:
                        switch = switch - 1
                        self.player.handIndexR = 0

                    else:
                        self.player.handIndexR = 4
                        switch = switch + 1



                if event.button == 3:
                    punchSound[2].play()
                    if self.player.handIndexR == 4:
                        self.player.handIndexR = 0
                    self.player.handIndexR += 1

                    if self.player.handIndexR == 3:
                        self.player.handIndexR = 0

            #while(self.col_check() and (self.player.handIndexL != 0 or self.player.handIndexR !=0)):


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
