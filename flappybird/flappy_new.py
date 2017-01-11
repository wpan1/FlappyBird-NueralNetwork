from itertools import cycle
import random
import sys

import pygame
from pygame.locals import *


FPS = 30
SCREENWIDTH  = 288
SCREENHEIGHT = 512
# amount by which base can maximum shift to left
PIPEGAPSIZE  = 100 # gap between upper and lower part of pipe
BASEY        = SCREENHEIGHT * 0.79
# image, sound and hitmask  dicts
IMAGES, SOUNDS, HITMASKS = {}, {}, {}

# list of all possible players (tuple of 3 positions of flap)
PLAYERS_LIST = (
    # red bird
    (
        'flappybird/assets/sprites/redbird-upflap.png',
        'flappybird/assets/sprites/redbird-midflap.png',
        'flappybird/assets/sprites/redbird-downflap.png',
    ),
    # blue bird
    (
        # amount by which base can maximum shift to left
        'flappybird/assets/sprites/bluebird-upflap.png',
        'flappybird/assets/sprites/bluebird-midflap.png',
        'flappybird/assets/sprites/bluebird-downflap.png',
    ),
    # yellow bird
    (
        'flappybird/assets/sprites/yellowbird-upflap.png',
        'flappybird/assets/sprites/yellowbird-midflap.png',
        'flappybird/assets/sprites/yellowbird-downflap.png',
    ),
)

# list of backgrounds
BACKGROUNDS_LIST = (
    'flappybird/assets/sprites/background-black.png',
    'flappybird/assets/sprites/background-day.png',
    'flappybird/assets/sprites/background-night.png',
)

# list of pipes
PIPES_LIST = (
    'flappybird/assets/sprites/pipe-green.png',
    'flappybird/assets/sprites/pipe-red.png',
)

class GameState:
    def  __init__(self):
        global SCREEN, FPSCLOCK
        pygame.init()
        FPSCLOCK = pygame.time.Clock()
        SCREEN = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT))
        pygame.display.set_caption('Flappy Bird')

        # numbers sprites for score display
        IMAGES['numbers'] = (
            pygame.image.load('flappybird/assets/sprites/0.png').convert_alpha(),
            pygame.image.load('flappybird/assets/sprites/1.png').convert_alpha(),
            pygame.image.load('flappybird/assets/sprites/2.png').convert_alpha(),
            pygame.image.load('flappybird/assets/sprites/3.png').convert_alpha(),
            pygame.image.load('flappybird/assets/sprites/4.png').convert_alpha(),
            pygame.image.load('flappybird/assets/sprites/5.png').convert_alpha(),
            pygame.image.load('flappybird/assets/sprites/6.png').convert_alpha(),
            pygame.image.load('flappybird/assets/sprites/7.png').convert_alpha(),
            pygame.image.load('flappybird/assets/sprites/8.png').convert_alpha(),
            pygame.image.load('flappybird/assets/sprites/9.png').convert_alpha()
        )

        # game over sprite
        IMAGES['gameover'] = pygame.image.load('flappybird/assets/sprites/gameover.png').convert_alpha()
        # message sprite for welcome screen
        IMAGES['message'] = pygame.image.load('flappybird/assets/sprites/message.png').convert_alpha()
        # base (ground) sprite
        IMAGES['base'] = pygame.image.load('flappybird/assets/sprites/base.png').convert_alpha()

        # sounds
        if 'win' in sys.platform:
            soundExt = '.wav'
        else:
            soundExt = '.ogg'

        SOUNDS['die']    = pygame.mixer.Sound('flappybird/assets/audio/die' + soundExt)
        SOUNDS['hit']    = pygame.mixer.Sound('flappybird/assets/audio/hit' + soundExt)
        SOUNDS['point']  = pygame.mixer.Sound('flappybird/assets/audio/point' + soundExt)
        SOUNDS['swoosh'] = pygame.mixer.Sound('flappybird/assets/audio/swoosh' + soundExt)
        SOUNDS['wing']   = pygame.mixer.Sound('flappybird/assets/audio/wing' + soundExt)

        # select random background sprites
        # randBg = random.randint(0, len(BACKGROUNDS_LIST) - 1)
        randBg = 0
        IMAGES['background'] = pygame.image.load(BACKGROUNDS_LIST[randBg]).convert()

        # select random player sprites
        # randPlayer = random.randint(0, len(PLAYERS_LIST) - 1)
        randPlayer = 0
        IMAGES['player'] = (
            pygame.image.load(PLAYERS_LIST[randPlayer][0]).convert_alpha(),
            pygame.image.load(PLAYERS_LIST[randPlayer][1]).convert_alpha(),
            pygame.image.load(PLAYERS_LIST[randPlayer][2]).convert_alpha(),
        )

        # select random pipe sprites
        # pipeindex = random.randint(0, len(PIPES_LIST) - 1)
        pipeindex = 0
        IMAGES['pipe'] = (
            pygame.transform.rotate(
                pygame.image.load(PIPES_LIST[pipeindex]).convert_alpha(), 180),
            pygame.image.load(PIPES_LIST[pipeindex]).convert_alpha(),
        )

        # hismask for pipes
        HITMASKS['pipe'] = (
            self.getHitmask(IMAGES['pipe'][0]),
            self.getHitmask(IMAGES['pipe'][1]),
        )

        # hitmask for player
        HITMASKS['player'] = (
            self.getHitmask(IMAGES['player'][0]),
            self.getHitmask(IMAGES['player'][1]),
            self.getHitmask(IMAGES['player'][2]),
        )

        self.score = self.playerIndex = self.loopIter = self.distance = self.tick = 0
        self.playerIndexGen = cycle([0, 1, 2, 1])

        self.playerx = int(SCREENWIDTH * 0.2)
        self.playery = int((SCREENHEIGHT - IMAGES['player'][0].get_height()) / 2)

        self.basex = 0
        self.baseShift = IMAGES['base'].get_width() - IMAGES['background'].get_width()

        # get 2 new pipes to add to upperPipes lowerPipes list
        newPipe1 = self.getRandomPipe()
        newPipe2 = self.getRandomPipe()

        # list of upper pipes
        self.upperPipes = [
            {'x': SCREENWIDTH + 200, 'y': newPipe1[0]['y']},
            {'x': SCREENWIDTH + 200 + (SCREENWIDTH / 2), 'y': newPipe2[0]['y']},
        ]

        # list of lowerpipe
        self.lowerPipes = [
            {'x': SCREENWIDTH + 200, 'y': newPipe1[1]['y']},
            {'x': SCREENWIDTH + 200 + (SCREENWIDTH / 2), 'y': newPipe2[1]['y']},
        ]

        self.pipeVelX = -4

        # player velocity, max velocity, downward accleration, accleration on flap
        self.playerVelY    =  -9   # player's velocity along Y, default same as playerFlapped
        self.playerMaxVelY =  10   # max vel along Y, max descend speed
        self.playerMinVelY =  -8   # min vel along Y, max ascend speed
        self.playerAccY    =   1   # players downward accleration
        self.playerFlapAcc =  -9   # players speed on flapping
        self.playerFlapped = False # True when player flaps

    def reInit(self):
        self.score = self.playerIndex = self.loopIter = 0
        self.playerIndexGen = cycle([0, 1, 2, 1])

        self.playerx = int(SCREENWIDTH * 0.2)
        self.playery = int((SCREENHEIGHT - IMAGES['player'][0].get_height()) / 2)

        self.basex = 0
        self.baseShift = IMAGES['base'].get_width() - IMAGES['background'].get_width()

        # get 2 new pipes to add to upperPipes lowerPipes list
        newPipe1 = self.getRandomPipe()
        newPipe2 = self.getRandomPipe()

        # list of upper pipes
        self.upperPipes = [
            {'x': SCREENWIDTH + 200, 'y': newPipe1[0]['y']},
            {'x': SCREENWIDTH + 200 + (SCREENWIDTH / 2), 'y': newPipe2[0]['y']},
        ]

        # list of lowerpipe
        self.lowerPipes = [
            {'x': SCREENWIDTH + 200, 'y': newPipe1[1]['y']},
            {'x': SCREENWIDTH + 200 + (SCREENWIDTH / 2), 'y': newPipe2[1]['y']},
        ]

        self.pipeVelX = -4

        # player velocity, max velocity, downward accleration, accleration on flap
        self.playerVelY    =  -9   # player's velocity along Y, default same as playerFlapped
        self.playerMaxVelY =  10   # max vel along Y, max descend speed
        self.playerMinVelY =  -8   # min vel along Y, max ascend speed
        self.playerAccY    =   1   # players downward accleration
        self.playerFlapAcc =  -9   # players speed on flapping
        self.playerFlapped = False # True when player flaps
        
        self.frame_step([1,0])

    def frame_step(self, key_input):

        # Ignore events so pygame doesn't freeze
        for event in pygame.event.get():
            None

        reward = 0
        endgame = False

        if (key_input[1] == 1):
            if self.playery > -2 * IMAGES['player'][0].get_height():
                self.playerVelY = self.playerFlapAcc
                self.playerFlapped = True
                SOUNDS['wing'].play()

        # check for score
        playerMidPos = self.playerx + IMAGES['player'][0].get_width() / 2
        for pipe in self.upperPipes:
            pipeMidPos = pipe['x'] + IMAGES['pipe'][0].get_width() / 2
            if pipeMidPos <= playerMidPos < pipeMidPos + 4:
                self.score += 1
                reward = 1
                SOUNDS['point'].play()

        # playerIndex basex change
        if (self.loopIter + 1) % 3 == 0:
            self.playerIndex = next(self.playerIndexGen)
        self.loopIter = (self.loopIter + 1) % 30
        self.basex = -((-self.basex + 100) % self.baseShift)

        # player's movement
        if self.playerVelY < self.playerMaxVelY and not self.playerFlapped:
            self.playerVelY += self.playerAccY
        if self.playerFlapped:
            self.playerFlapped = False
        self.playerHeight = IMAGES['player'][self.playerIndex].get_height()
        self.playery += min(self.playerVelY, BASEY - self.playery - self.playerHeight)

        # move pipes to left
        for uPipe, lPipe in zip(self.upperPipes, self.lowerPipes):
            uPipe['x'] += self.pipeVelX
            lPipe['x'] += self.pipeVelX

        # add new pipe when first pipe is about to touch left of screen
        if 0 < self.upperPipes[0]['x'] < 5:
            newPipe = self.getRandomPipe()
            self.upperPipes.append(newPipe[0])
            self.lowerPipes.append(newPipe[1])

        # remove first pipe if its out of the screen
        if self.upperPipes[0]['x'] < -IMAGES['pipe'][0].get_width():
            self.upperPipes.pop(0)
            self.lowerPipes.pop(0)

        # check for crash here
        crashTest = self.checkCrash({'x': self.playerx, 'y': self.playery, 'index': self.playerIndex},
                               self.upperPipes, self.lowerPipes)
        if crashTest[0]:
            self.reInit()
            image_data = pygame.surfarray.array3d(pygame.display.get_surface())
            endgame = True
            reward = -1

        # draw sprites
        SCREEN.blit(IMAGES['background'], (0,0))

        for uPipe, lPipe in zip(self.upperPipes, self.lowerPipes):
            SCREEN.blit(IMAGES['pipe'][0], (uPipe['x'], uPipe['y']))
            SCREEN.blit(IMAGES['pipe'][1], (lPipe['x'], lPipe['y']))

        SCREEN.blit(IMAGES['base'], (self.basex, BASEY))
        # print score so player overlaps the score
        # self.showScore(self.score)
        SCREEN.blit(IMAGES['player'][self.playerIndex], (self.playerx, self.playery))


        image_data = pygame.surfarray.array3d(pygame.display.get_surface())

        pygame.display.update()
        FPSCLOCK.tick(FPS)

        return image_data, reward, endgame

    def playerShm(self, playerShm):
        """oscillates the value of playerShm['val'] between 8 and -8"""
        if abs(playerShm['val']) == 8:
            playerShm['dir'] *= -1

        if playerShm['dir'] == 1:
             playerShm['val'] += 1
        else:
            playerShm['val'] -= 1


    def getRandomPipe(self):
        """returns a randomly generated pipe"""
        # y of gap between upper and lower pipe
        gapY = random.randrange(0, int(BASEY * 0.6 - PIPEGAPSIZE))
        gapY += int(BASEY * 0.2)
        pipeHeight = IMAGES['pipe'][0].get_height()
        pipeX = SCREENWIDTH + 10

        return [
            {'x': pipeX, 'y': gapY - pipeHeight},  # upper pipe
            {'x': pipeX, 'y': gapY + PIPEGAPSIZE}, # lower pipe
        ]


    def showScore(self, score):
        """displays score in center of screen"""
        scoreDigits = [int(x) for x in list(str(score))]
        totalWidth = 0 # total width of all numbers to be printed

        for digit in scoreDigits:
            totalWidth += IMAGES['numbers'][digit].get_width()

        Xoffset = (SCREENWIDTH - totalWidth) / 2

        for digit in scoreDigits:
            SCREEN.blit(IMAGES['numbers'][digit], (Xoffset, SCREENHEIGHT * 0.1))
            Xoffset += IMAGES['numbers'][digit].get_width()


    def checkCrash(self, player, upperPipes, lowerPipes):
        """returns True if player collders with base or pipes."""
        pi = player['index']
        player['w'] = IMAGES['player'][0].get_width()
        player['h'] = IMAGES['player'][0].get_height()

        # if player crashes into ground
        if player['y'] + player['h'] >= BASEY - 1:
            return [True, True]
        else:

            playerRect = pygame.Rect(player['x'], player['y'],
                          player['w'], player['h'])
            pipeW = IMAGES['pipe'][0].get_width()
            pipeH = IMAGES['pipe'][0].get_height()

            for uPipe, lPipe in zip(upperPipes, lowerPipes):
                # upper and lower pipe rects
                uPipeRect = pygame.Rect(uPipe['x'], uPipe['y'], pipeW, pipeH)
                lPipeRect = pygame.Rect(lPipe['x'], lPipe['y'], pipeW, pipeH)

                # player and upper/lower pipe hitmasks
                pHitMask = HITMASKS['player'][pi]
                uHitmask = HITMASKS['pipe'][0]
                lHitmask = HITMASKS['pipe'][1]

                # if bird collided with upipe or lpipe
                uCollide = self.pixelCollision(playerRect, uPipeRect, pHitMask, uHitmask)
                lCollide = self.pixelCollision(playerRect, lPipeRect, pHitMask, lHitmask)

                if uCollide or lCollide:
                    return [True, False]

        return [False, False]

    def pixelCollision(self, rect1, rect2, hitmask1, hitmask2):
        """Checks if two objects collide and not just their rects"""
        rect = rect1.clip(rect2)

        if rect.width == 0 or rect.height == 0:
            return False

        x1, y1 = rect.x - rect1.x, rect.y - rect1.y
        x2, y2 = rect.x - rect2.x, rect.y - rect2.y

        for x in range(rect.width):
            for y in range(rect.height):
                if hitmask1[x1+x][y1+y] and hitmask2[x2+x][y2+y]:
                    return True
        return False

    def getHitmask(self, image):
        """returns a hitmask using an image's alpha."""
        mask = []
        for x in range(image.get_width()):
            mask.append([])
            for y in range(image.get_height()):
                mask[x].append(bool(image.get_at((x,y))[3]))
        return mask
