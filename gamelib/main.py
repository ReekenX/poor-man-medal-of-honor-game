# core
import os
import sys

# 3rd party
import pygame as pg

# local
import settings
from gamelib.game import Game


def main():
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    pg.init()
    pg.display.set_caption(settings.SCREEN_TITLE)
    pg.display.set_mode(settings.SCREEN_SIZE)

    Game().main_loop()

    pg.quit()
    sys.exit()
