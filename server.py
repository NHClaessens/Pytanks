print("started server")
import pygame
import socket
import select
from _thread import *
import threading
import math
import random
import os
from _thread import *
import time
import binascii


#connect socket and start listening
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#server.bind(("127.0.0.1", 5378))
server.bind(("0.0.0.0", 5378))

#keep track of playercount, connections and their last positions
playercount = 0
playerlist = []
scorelist = []
inputtimer = []

#create sprite groups
all_sprites = pygame.sprite.Group()
all_players = pygame.sprite.Group()
all_bullets = pygame.sprite.Group()
all_walls = pygame.sprite.Group()

#region game files
BLUE_TANK = pygame.transform.rotate(pygame.image.load(r'Game/media/tank_blue.png'), 0)
RED_TANK = pygame.transform.rotate(pygame.image.load(r'Game/media/tank_red.png'), 0)
GREEN_TANK = pygame.transform.rotate(pygame.image.load(r'Game/media/tank_green.png'), 0)
DARK_TANK = pygame.transform.rotate(pygame.image.load(r'Game/media/tank_dark.png'), 0)
SAND_TANK = pygame.transform.rotate(pygame.image.load(r'Game/media/tank_sand.png'), 0)
CYAN_TANK = pygame.transform.rotate(pygame.image.load(r'Game/media/tank_cyan.png'), 0)
LIME_TANK = pygame.transform.rotate(pygame.image.load(r'Game/media/tank_lime.png'), 0)
YELLOW_TANK = pygame.transform.rotate(pygame.image.load(r'Game/media/tank_yellow.png'), 0)
TANKS = [BLUE_TANK, RED_TANK, GREEN_TANK, DARK_TANK, SAND_TANK, CYAN_TANK, LIME_TANK, YELLOW_TANK]

BLUE_BULLET = pygame.transform.smoothscale(pygame.image.load(r'Game/media/bulletBlue1_outline.png'), (20, 20))
RED_BULLET = pygame.transform.smoothscale(pygame.image.load(r'Game/media/bulletRed1_outline.png'), (20, 20))
GREEN_BULLET = pygame.transform.smoothscale(pygame.image.load(r'Game/media/bulletGreen1_outline.png'), (20, 20))
DARK_BULLET = pygame.transform.smoothscale(pygame.image.load(r'Game/media/bulletDark1_outline.png'), (20, 20))
SAND_BULLET = pygame.transform.smoothscale(pygame.image.load(r'Game/media/bulletSand1_outline.png'), (20, 20))
CYAN_BULLET = pygame.transform.smoothscale(pygame.image.load(r'Game/media/bulletCyan1_outline.png'), (20, 20))
LIME_BULLET = pygame.transform.smoothscale(pygame.image.load(r'Game/media/bulletLime1_outline.png'), (20, 20))
YELLOW_BULLET = pygame.transform.smoothscale(pygame.image.load(r'Game/media/bulletYellow1_outline.png'), (20, 20))
BULLETS = [BLUE_BULLET, RED_BULLET, GREEN_BULLET, DARK_BULLET, SAND_BULLET, CYAN_BULLET, LIME_BULLET, YELLOW_BULLET]

pygame.mixer.init()

#FIRE_SOUND = pygame.mixer.Sound(r'Game/media/fire.mp3')
#BOOM_SOUND = pygame.mixer.Sound(r'Game/media/boom.mp3')

WALL = pygame.transform.smoothscale(pygame.image.load(r'Game/media/crateMetal.png'), (60, 60))

pygame.font.init()
font = pygame.font.SysFont('Sans Serif', 20)
#endregion game files

#region setup config

pygame.display.set_caption("server view")
from pygame.locals import(
    K_UP,
    K_DOWN,
    K_LEFT,
    K_RIGHT,
    K_ESCAPE,
    K_SPACE,
    K_r,
    KEYDOWN,
)

#setup screen size
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

#set of possible spawn locations for new players and respawned players
SPAWN_LOCATIONS = [(100, 100), (1820, 980), (100, 980), (1820, 100), (935, 515)]

#define the layout for the walls (1 = wall, 0 = no wall)
layout = [
    "00000000000000000000000000000000",
    "00000000000000000000000000000000",
    "00000111111111111111111111000000",
    "00000000000001000000000000000000",
    "00000000000001000000000000000000",
    "00000000000001000000000000011111",
    "00000000000001000000000000010000",
    "00010000000001000000000000010000",
    "00010000000000000001000000000000",
    "11110000000000000001000000000000",
    "00010000000000000001000000000000",
    "00010000000000000001000000000000",
    "00000000000000000001000000000000",
    "00000000111111111111111000000000",
    "00000000000000000000000000000000",
    "00000000000000000000000000000000",
    "00000000000001000000000000000000",
    "00000000000001000000000000000000",
]

#endregion setup config
sendprob = 101

#region classes
def sendthread(num, message):
    global playerlist
    for playernum in range(num*10, num*10+9):
        if random.randint(0,100) < sendprob:
            try:
                server.sendto(message, playerlist[playernum][0])
            except:
                continue
    return

outstanding_acks = []
lastusedseq = 0

def safesendthread(message, ip):
    global lastusedseq
    localseq = lastusedseq
    outstanding_acks.append(lastusedseq)
    message += f" {lastusedseq} "
    lastusedseq += 1
    message = message.encode("utf-8")
    message += str(binascii.crc32(message)).encode("utf-8")
    i = 0
    while i <= 5  and localseq in outstanding_acks:
        if random.randint(0,100) < sendprob:
            server.sendto(message, ip)
        i += 1
        time.sleep(0.05)
    return

def safesendthread2(num, message):
    global lastusedseq
    localseq = []
    originalmessage = message
    for playernum in range(num*10, num*10+9):
        try:
            playerlist[playernum]
        except IndexError:
            break
        if playerlist[playernum] == "": continue

        localseq.append((lastusedseq, playernum))
        outstanding_acks.append(lastusedseq)
        message = originalmessage + f" {lastusedseq} " 
        lastusedseq += 1
        message = message.encode("utf-8")
        message += str(binascii.crc32(message)).encode("utf-8")
        try:
            server.sendto(message, playerlist[playernum][0])
        except IndexError:
            pass
    time.sleep(0.05)
    i = 0
    while i < 10:
        i += 1
        for seq in localseq:
            if seq[0] in outstanding_acks:
                    try:
                        server.sendto(message, playerlist[seq[1]][0])
                    except:
                        break
        time.sleep(0.05)
    

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, playerid):
        super(Bullet, self).__init__()
        self.surf = pygame.transform.rotate(BULLETS[playerid % 8], angle + 180)
        self.rect = self.surf.get_rect()

        self.direction = pygame.Vector2(math.sin(math.radians(angle)), math.cos(math.radians(angle))) 
        self.rect.center = (x, y) + self.direction * 20
        self.center = pygame.Vector2(self.rect.center)        
        self.speed = 60

        self.playerid = playerid

    #function to update position of bullet and kill it if outside screen boundaries
    def update(self):
        self.center += self.speed * self.direction
        self.rect.center = self.center

        if self.rect.left < 0:
            Bullet.kill(self)
        if self.rect.right > SCREEN_WIDTH:
            Bullet.kill(self)
        if self.rect.top <= 0:
            Bullet.kill(self)
        if self.rect.bottom >= SCREEN_HEIGHT:
            Bullet.kill(self)
        
        if pygame.sprite.spritecollideany(self, all_walls):
            Bullet.kill(self)

        if  pygame.sprite.spritecollideany(self, all_players):
            player = pygame.sprite.spritecollideany(self, all_players)
            if player.playerid != self.playerid:
                if scorelist[player.playerid] >= 10:
                    scorelist[player.playerid] -= 10
                message = f"SCORE {scorelist[player.playerid]}"
                start_new_thread(safesendthread, (message, playerlist[player.playerid][0]))
                scorelist[self.playerid] += 10
                message = f"SCORE {scorelist[self.playerid]}"
                start_new_thread(safesendthread, (message, playerlist[self.playerid][0]))
                if scorelist[self.playerid] >= 100:
                    print("player", self.playerid, "won")
                    message = f"WIN {self.playerid}"
                    for num in range (0, math.ceil(len(playerlist) / 10)):
                        threading.Thread(target=safesendthread2, args=(num, message)).start()
                    i = 0
                    while 1:
                        if i>= 5 or len(outstanding_acks) == 0:
                            os._exit(0)
                        i += 1
                        time.sleep(1)
                Player.kill(player)
                Bullet.kill(self)
                message = f"KILL {player.playerid}"
                for num in range (0, math.ceil(len(playerlist) / 10)):
                    threading.Thread(target=safesendthread2, args=(num, message)).start()

        

def spawn_bullet(pos, angle, playerid):
    bullet = Bullet(pos[0] + 0.5*pos[2], pos[1] + 0.5*pos[3], angle, playerid)
    all_sprites.add(bullet)
    all_bullets.add(bullet)

class Player(pygame.sprite.Sprite):
    def __init__(self, playerid):
        super(Player, self).__init__()
        self.og_surf = pygame.transform.smoothscale(TANKS[playerid % 8].convert_alpha(), (50, 50))
        self.surf = self.og_surf
        self.rect = self.surf.get_rect()
        self.rect.center = SPAWN_LOCATIONS[random.randint(0, 4)]
        self.angle = 0
        self.change_angle = 0
        self.center = pygame.Vector2(self.rect.center)
        self.speed = 34
        self.cooldown_tracker = 400
        self.playerid = playerid
        self.prevcenter = 0
        self.prevangle = 0
        self.prevfire = -4000
        Player.rotate(self)

    #function to rotate the visible surface by a set amount of degrees
    def rotate(self):
        self.surf = pygame.transform.rotate(self.og_surf, self.angle)
        self.angle += self.change_angle
        self.angle = self.angle % 360
        self.direction = pygame.Vector2(math.sin(math.radians(self.angle)), math.cos(math.radians(self.angle)))
        self.rect = self.surf.get_rect(center=self.rect.center)           

    #function to update the visible surface and the position of the player
    def update(self, keyinput):
        global instanceID
        fireDelay = 5000
        self.change_angle = 0
        prevcenter = self.rect.center

        if keyinput == "UP":
            self.center += self.speed * self.direction
            self.rect.center = self.center
        if keyinput == "DOWN":
            self.center -= 0.5 * self.speed * self.direction
            self.rect.center = self.center
        if keyinput == "LEFT":
            self.change_angle = 15
        if keyinput == "RIGHT":
            self.change_angle = -15
        if keyinput == "SPACE":
            spawn_bullet(self.rect, self.angle, self.playerid)
            message = f"FIRE {self.rect} {self.angle} {self.playerid}"
            for num in range (0, math.ceil(len(playerlist) / 10)):
                threading.Thread(target=safesendthread2, args=(num, message)).start()

        #handle wall collisions
        if pygame.sprite.spritecollideany(self, all_walls):
            self.rect.center = prevcenter
            self.center = self.rect.center
                    
        #Keep player on the screen
        if self.rect.left < 0:
            self.rect.left = 0
            self.center = pygame.Vector2(self.rect.center)
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH 
            self.center = pygame.Vector2(self.rect.center)
        if self.rect.top <= 0:
            self.rect.top = 0
            self.center = pygame.Vector2(self.rect.center)
        if self.rect.bottom >= SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT
            self.center = pygame.Vector2(self.rect.center)

        #rotate the player by self.changeangle degrees
        Player.rotate(self)
        return(self.rect.center[0], self.rect.center[1], self.angle)

#class for wall objects
class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super(Wall, self).__init__()
        self.surf = WALL
        self.rect = self.surf.get_rect()
        self.rect.center = (x * 60 + 30, y * 60 + 30)
        self.x = x
        self.y = y

#endregion classes

#region initialize game
#initialize game
pygame.init()

#set up clock for constant framerate
clock = pygame.time.Clock()

#set up the game window size
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

#create wall objects according to layout
for y in range(0,18):
    for x in range(0, 32):
        if layout[y][x] == "1":
            tempwall = Wall(x,y)
            all_sprites.add(tempwall)
            all_walls.add(tempwall)

#endregion initialize game

def createNewPlayer(ip):
    global playerlist
    for index, player in enumerate(playerlist):
        if player == "":
            playerlist[index] = (ip,index, 0)
            scorelist[index] = 0
            inputtimer[index] = [-1000, -1000, -1000, -1000, -1000]
            return index
    playerlist.append((ip,len(playerlist), 0))
    scorelist.append(0)
    inputtimer.append([-1000, -1000, -1000, -1000, -1000])
    return(len(playerlist) - 1)

def reconnectPlayer(ip,id):
    global playerlist
    print(f"this is the id {id}")
    if  playerlist[id][2] > 2 and playerlist[id][0] == ip:
        print("reconnect accepted")
        return id
    else:
        print("reconnect failed sending new id THIS SHOULD NOT HAPPEN \n\n\n\n\n")
        for index, player in enumerate(playerlist):
            if player == "":
                playerlist[index] = (ip,index, 0)
                scorelist[index] = 0
                inputtimer[index] = [-1000, -1000, -1000, -1000, -1000]
                return index
        playerlist.append((ip,len(playerlist), 0))
        scorelist.append(0)
        inputtimer.append([-1000, -1000, -1000, -1000, -1000])
        return(len(playerlist) - 1)

def processmovement(command, message):
    incoming_id = int(message.split(b' ')[1])
    for playertomove in all_players:
        if playertomove.playerid == incoming_id:
            position = playertomove.update(command.decode("utf-8"))
            message = f"MOVE {incoming_id} {position}".encode("utf-8")
            for num in range (0, math.ceil(len(playerlist) / 10)):
                start_new_thread(sendthread, (num, message))
    

def listenthread(id):
    global playerlist
    rateLimDelay = 250
    while 1:
        if id > len(playerlist):
            print("stopping thread")
            return
        data_available = select.select([server], [], [], 1)
        if data_available[0]:
            try:
                incoming = server.recvfrom(4096)
            except:
                #print("client disconnected")
                continue
            #print(incoming)
            message = incoming[0]
            command = message.split(b' ')[0]
            ip = incoming[1]

            if message == b'HELLO':
                print("new player connected")
                start_new_thread(listenthread,(len(playerlist),))
                id = createNewPlayer(ip)
                #create new player
                newplayer = Player(id)
                all_sprites.add(newplayer)
                all_players.add(newplayer)
                server.sendto(f"HELLO_THERE {id} {newplayer.rect.center[0]} {newplayer.rect.center[1]} {layout}".encode("utf-8"), ip)
                #send all existing player positions to new player
                for player in all_players:
                    position = (player.rect.center[0], player.rect.center[1], player.angle)
                    server.sendto(f"MOVE {player.playerid} {position}".encode("utf-8"), ip)
                #send new player position to all players
                position = (newplayer.rect.center[0], newplayer.rect.center[1], newplayer.angle)
                for player in playerlist:
                    if player != "":
                        server.sendto(f"MOVE {id} {position}".encode("utf-8"), player[0])
            elif command == b'RECONNECT':
                print("player attempting reconnect")
                reconnectId = int(message.split(b' ')[1].decode("utf-8"))
                if reconnectId < len(playerlist) and playerlist[reconnectId] != "" and playerlist[reconnectId][2] > 2 and playerlist[reconnectId][0] == ip:
                    id = reconnectPlayer(ip,reconnectId)
                    for index, player in enumerate(all_players):
                        if index == id:
                            server.sendto(f"HELLO_THERE {id} {player.rect.center[0]} {player.rect.center[1]} {layout}".encode("utf-8"), ip)
                    #send all existing player positions to new player
                    for player in all_players:
                        position = (player.rect.center[0], player.rect.center[1], player.angle)
                        server.sendto(f"MOVE {player.playerid} {position}".encode("utf-8"), ip)
                else:
                    print("Reconnect failed creating new player \n\n")
                    #create new player
                    start_new_thread(listenthread,(len(playerlist),))
                    id = createNewPlayer(ip)
                    newplayer = Player(id)
                    all_sprites.add(newplayer)
                    all_players.add(newplayer)
                    server.sendto(f"HELLO_THERE {id} {newplayer.rect.center[0]} {newplayer.rect.center[1]} {layout}".encode("utf-8"), ip)
                    #send new player position to all other players
                    position = (newplayer.rect.center[0], newplayer.rect.center[1], newplayer.angle)
                    for player in playerlist:
                        if player != "":
                            server.sendto(f"MOVE {id} {position}".encode("utf-8"), player[0])
                    #send all existing player positions to new player
                    for player in all_players:
                        position = (player.rect.center[0], player.rect.center[1], player.angle)
                        server.sendto(f"MOVE {player.playerid} {position}".encode("utf-8"), ip)
            elif command == b'SUP':
                for index,player in enumerate(playerlist):
                    if player != "" and player[0] == ip:
                        #print(f"player with id {player[1]} sent SUP")
                        playerlist[index] = (player[0], player[1], 0)
            elif command == b'ACK':
                seq = message.split(b' ')[1].decode("utf-8")
                seq = int(seq)
                try:
                    outstanding_acks.remove(seq)
                except:
                    continue
            else:
                id = int(message.split(b' ')[1].decode("utf-8"))
                playerlist_index = next((i for i, v in enumerate(playerlist) if v != "" and v[0] == ip), None)
                #make sure other client doesn't try to move other players
                try:
                    if playerlist[playerlist_index][1] != id and 0:
                        continue
                except:
                    pass
            #rate limit player input
            #handle behaviour of player
            try:
                inputtimer[id][0]
            except:
                continue

            if command == b'UP':
                if pygame.time.get_ticks() - inputtimer[id][0] < rateLimDelay:
                    continue
                inputtimer[id][0] = pygame.time.get_ticks()
                processmovement(command, message)
            elif command == b'RIGHT':
                if pygame.time.get_ticks() - inputtimer[id][1] < rateLimDelay:
                    continue
                inputtimer[id][1] = pygame.time.get_ticks()
                processmovement(command, message)
            elif command == b'DOWN':
                if pygame.time.get_ticks() - inputtimer[id][2] < rateLimDelay:
                    continue
                inputtimer[id][2] = pygame.time.get_ticks()
                processmovement(command, message)
            elif command == b'LEFT':
                if pygame.time.get_ticks() - inputtimer[id][3] < rateLimDelay:
                    continue
                inputtimer[id][3] = pygame.time.get_ticks()
                processmovement(command, message)
            elif command == b'SPACE':
                if pygame.time.get_ticks() - inputtimer[id][4] < 5000:
                    continue
                inputtimer[id][4] = pygame.time.get_ticks()
                incoming_id = int(message.split(b' ')[1])
                for playertomove in all_players:
                    if playertomove.playerid == incoming_id:
                        playertomove.update(command.decode("utf-8"))
            elif command == b'SPAWN':
                incoming_id = int(message.split(b' ')[1])
                incoming_seq = int(message.split(b' ')[2])
                server.sendto(f"ACK {incoming_seq}".encode("utf-8"), ip)
                if not any(player.playerid == incoming_id for player in all_players):
                    newplayer = Player(incoming_id)
                    all_sprites.add(newplayer)
                    all_players.add(newplayer)
                    message = f"MOVE {incoming_id} ({newplayer.rect.center[0]}, {newplayer.rect.center[1]}, {newplayer.angle})".encode("utf-8")
                    for num in range (0, math.ceil(len(playerlist) / 10)):
                        start_new_thread(sendthread, (num, message))

def connectionthread():
    while 1:
        timeBeforeTimeout = 10
        #check if there are player and if they are still online
        if len(playerlist) > 0:
            for index,player in enumerate(playerlist):
                #remove players that do not respond for timeBeforeTimeout seconds
                if player != "" and player[2] >= timeBeforeTimeout:
                    for player in all_players:
                        if player.playerid == index:
                            Player.kill(player)
                            message = f"KILL {index}"
                            for num in range (0, math.ceil(len(playerlist) / 10)):
                                threading.Thread(target=safesendthread2, args=(num, message)).start()
                            time.sleep(0.1)
                    playerlist[index] = ""
                    scorelist[index] = 0
                    inputtimer[index] = 0
                    print(f"player with id {index} has been removed\n")

                elif player != "":
                    time.sleep(0.1)
                    #print(f"player with id {player[1]} has not responded to {player[2]} messages")
                    server.sendto(b"TEST", player[0])
                    num = player[2] + 1
                    playerlist[index] = (player[0], player[1], num)
        clock.tick(0.5)

listener = threading.Thread(target=listenthread, args=(len(playerlist),))
listener.start()
start_new_thread(connectionthread, ())

running = True
while running:

    #handle game events
    for event in pygame.event.get():
        #handle key events
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                os._exit(0)

        elif event.type == pygame.QUIT: os._exit(0)

    screen.fill((0,0,0))

    scorestring = ", ".join([str(score) for score in scorelist])
    text_surf = font.render(scorestring, False, (255,255,255))
    screen.blit(text_surf, (20,20))

    for bullet in all_bullets:
        bullet.update()

    #update all sprites to the screen
    for entity in all_sprites:
        screen.blit(entity.surf, entity.rect)

    #update the screen
    pygame.display.update()
    clock.tick(10)

pygame.quit()
os._exit(0)