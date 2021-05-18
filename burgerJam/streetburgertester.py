import pygame, sys
from pygame.locals import *

def burger(x,y):
    gameDisplay.blit(burgrer, (x,y))


burgerX = 100
burgerY = 50
display_width = 1200
display_height = 600
pygame.init()
burgrer= pygame.image.load("burgrer.png")
bg = pygame.image.load("bcg.png")
gameDisplay = pygame.display.set_mode((display_width,display_height))
gameDisplay.blit(bg, (0,0))
    #DISPLAY=pygame.display.set_mode((1200,600),0,32)
pygame.display.set_caption('Burger, Fight! ')
WHITE=(255,255,255)
BLUE=(0,0,255)
RED=(255,0,0)
GREEN=(0,255,0)

    #DISPLAY.

    #pygame.draw.rect(DISPLAY,RED,(200,150,100,50))
pygame.draw.rect(gameDisplay,RED,(50,40,500,40))
pygame.draw.rect(gameDisplay,GREEN,(50,40,500,40))

pygame.draw.rect(gameDisplay,RED,(650,40,500,40))
pygame.draw.rect(gameDisplay,GREEN,(650,40,500,40))
    #pygame.draw.rect(DISPLAY,GREEN,(50,40,500,40))



while True:
    for event in pygame.event.get():

        burger(burgerX,burgerY)

        if event.type==QUIT:
            pygame.quit()
            sys.exit()
    pygame.display.update()
