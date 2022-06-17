import pygame
import math
import socket
import select
import threading
import random
import os
import time
import binascii

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


WALL = pygame.transform.smoothscale(pygame.image.load(r'Game/media/crateMetal.png'), (60, 60))
pygame.font.init()
font = pygame.font.SysFont('Sans Serif', 60)
smallfont = pygame.font.SysFont('Sans Serif', 30)
#endregion game files

#region setup config

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#host_port = ("127.0.0.1", 5378)
#host_port = ("192.168.178.89", 5378) 
host_port = ("77.173.106.197", 5378)
sock.connect(host_port)

pygame.display.set_caption("Tank game :)")

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

score = 0
#endregion setup config

#region classes

class dummyPlayer(pygame.sprite.Sprite):
    def __init__(self, playerid, x, y, angle):
        super(dummyPlayer, self).__init__()
        self.og_surf = pygame.transform.smoothscale(TANKS[playerid % 8].convert_alpha(), (50, 50))
        self.surf = self.og_surf
        self.rect = self.surf.get_rect()
        self.rect.center = (int(x), int(y)) 
        self.playerid = playerid
        self.angle = angle

    
    def rotate(self):
        self.surf = pygame.transform.rotate(self.og_surf, self.angle)
        self.direction = pygame.Vector2(math.sin(math.radians(self.angle)), math.cos(math.radians(self.angle)))
        self.rect = self.surf.get_rect(center=self.rect.center)


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, playerid):
        super(Bullet, self).__init__()
        self.surf = pygame.transform.rotate(BULLETS[playerid % 8], angle + 180)
        self.rect = self.surf.get_rect()

        self.direction = pygame.Vector2(math.sin(math.radians(angle)), math.cos(math.radians(angle))) 
        self.rect.center = (x, y) + self.direction * 20
        self.center = pygame.Vector2(self.rect.center)        
        self.speed = 10

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
                Bullet.kill(self)

def spawn_bullet(pos, angle, playerid):
    bullet = Bullet(pos[0] + 0.5*pos[2], pos[1] + 0.5*pos[3], angle, playerid)
    all_sprites.add(bullet)
    all_bullets.add(bullet)

#class for wall objects
class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super(Wall, self).__init__()
        self.surf = WALL
        self.rect = self.surf.get_rect()
        self.rect.center = (x * 60 + 30, y * 60 + 30)

#endregion classes

#region initialize game
#initialize game
pygame.init()

#set up clock for constant framerate
clock = pygame.time.Clock()

#set up the game window size
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

#create sprite groups
all_sprites = pygame.sprite.Group()
all_players = pygame.sprite.Group()
all_bullets = pygame.sprite.Group()
all_walls = pygame.sprite.Group()

#endregion initialize game

#region timeout
lastMessageTime = 0
#regionend timeout

#region lerp
playerlist = []
#endregion lerp


#region game
player_alive = True
win = False
recent_seqs = []
print("sending handshake")
sock.sendall(b'HELLO')
id = 0

def createWalls(layout):
    for y in range(0,18):
        layout[y] = layout[y].replace("[", "")
        layout[y] = layout[y].replace("]", "")
        layout[y] = layout[y].replace(" ", "")
        layout[y] = layout[y].replace("'", "")
        print(layout[y])
        for x in range(0, 32):
            if layout[y][x] == "1":
                tempwall = Wall(x,y)
                all_sprites.add(tempwall)
                all_walls.add(tempwall)

def movethread(player, x, y, angle):

    endPostition = pygame.Vector2(int(x), int(y))
    endAngle = int(angle)
    InterpolateSpeed = 0.1
    lerpPoint = InterpolateSpeed
    currentPositionString = player.rect.center
    currentPosition = pygame.Vector2(int(currentPositionString[0]), int(currentPositionString[1]))
    currentAngle = int(player.angle)
    if currentPosition == endPostition:
        if currentAngle < 10 and endAngle > 300:
                currentAngle = 360
        while lerpPoint <= 1:    
            nextAngle = currentAngle * (1 - lerpPoint) + endAngle * lerpPoint

            player.angle = int(nextAngle)
            player.rotate()
            lerpPoint += InterpolateSpeed
            time.sleep(0.025)

    elif currentAngle == endAngle:
        while lerpPoint <= 1:
            nextPosition = pygame.math.Vector2.lerp(currentPosition, endPostition, lerpPoint)
            player.rect.center = (int(nextPosition[0]), int(nextPosition[1]))
            
            lerpPoint += InterpolateSpeed
            time.sleep(0.025)

    else:
        if currentAngle < 10 and endAngle > 300:
                currentAngle = 360
        while lerpPoint <= 1:
            nextAngle = currentAngle * (1 - lerpPoint) + endAngle * lerpPoint
            nextPosition = pygame.math.Vector2.lerp(currentPosition, endPostition, lerpPoint)
            player.rect.center = (int(nextPosition[0]), int(nextPosition[1]))
            player.angle = int(nextAngle)
            player.rotate()

            lerpPoint += InterpolateSpeed
            time.sleep(0.025)

    
def movethread2(id):
    print(f"Movethread2 has started for player {id}")
    while 1:
        try:
            int(playerlist[id][0])
        except:
            print(f"movethread closed playerlist error {id}")
            break
        endPostition = pygame.Vector2(int(playerlist[id][0]), int(playerlist[id][1]))
        endAngle = int(playerlist[id][2])
        InterpolateSpeed = 0.1
        lerpPoint = InterpolateSpeed
        playerUsed = ""
        for player in all_players:
            if player.playerid == id:
                playerUsed = player
                continue
        if playerUsed == "":
            print(f"movethread closed playerused empty  {id}")
            break
        currentPositionString = playerUsed.rect.center
        currentPosition = pygame.Vector2(int(currentPositionString[0]), int(currentPositionString[1]))
        currentAngle = int(playerUsed.angle)
        if currentPosition == endPostition:
            if currentAngle > 540:
                currentAngle = currentAngle % 360
                endAngle = endAngle % 360
            if currentAngle > 180 and endAngle == 0:
                endAngle = 360
            if abs(currentAngle - endAngle) > 180:
                currentAngle = 360 + currentAngle
            if abs(currentAngle - endAngle) > 360:
                if currentAngle > endAngle:
                    currentAngle = currentAngle % 360
                else:
                    endAngle = endAngle % 360
            if currentAngle < 10 and endAngle > 300:
                    currentAngle = 360
            while lerpPoint <= 1:    
                nextAngle = currentAngle * (1 - lerpPoint) + endAngle * lerpPoint

                playerUsed.angle = int(nextAngle)
                playerUsed.rotate()
                lerpPoint += InterpolateSpeed
                time.sleep(0.025)

        elif currentAngle == endAngle:
            while lerpPoint <= 1:
                nextPosition = pygame.math.Vector2.lerp(currentPosition, endPostition, lerpPoint)
                playerUsed.rect.center = (int(nextPosition[0]), int(nextPosition[1]))
                
                lerpPoint += InterpolateSpeed
                time.sleep(0.025)
        else:
            if currentAngle > 540:
                currentAngle = currentAngle % 360
                endAngle = endAngle % 360
            if currentAngle > 180 and endAngle == 0:
                endAngle = 360
            if abs(currentAngle - endAngle) > 180:
                currentAngle = 360 + currentAngle
            if abs(currentAngle - endAngle) > 360:
                if currentAngle > endAngle:
                    currentAngle = currentAngle % 360
                else:
                    endAngle = endAngle % 360
            if currentAngle < 10 and endAngle > 300:
                    currentAngle = 360
            while lerpPoint <= 1:
                nextAngle = currentAngle * (1 - lerpPoint) + endAngle * lerpPoint
                nextPosition = pygame.math.Vector2.lerp(currentPosition, endPostition, lerpPoint)
                playerUsed.rect.center = (int(nextPosition[0]), int(nextPosition[1]))
                playerUsed.angle = int(nextAngle)
                playerUsed.rotate()

                lerpPoint += InterpolateSpeed
                time.sleep(0.025)

lastusedseq = 0
outstanding_acks = []

def safesend(message):
    global lastusedseq
    outstanding_acks.append(lastusedseq)
    print(f"safesending {message} to server")
    sock.sendall(f"{message} {lastusedseq}".encode("utf-8"))
    time.sleep(0.5)
    while lastusedseq in outstanding_acks:
        sock.sendall(f"{message} {lastusedseq}".encode("utf-8"))
        time.sleep(0.5)
    lastusedseq += 1

def listenthread():
    global id
    global player_alive
    global score
    global win
    global recent_seqs
    global lastMessageTime
    global outstanding_acks

    print("started listening to server")
    while 1:
        data_available = select.select([sock], [], [], 1)
        if data_available[0]:
            try:
                incoming = sock.recv(4096)
            except:
                continue
            message = incoming.split(b' ')
            lastMessageTime = pygame.time.get_ticks()
            if message[0] == b'HELLO_THERE':
                id = int(message[1].decode("utf-8"))
                x = incoming.split(b' ', 3)[2].decode("utf-8")
                y = incoming.split(b' ', 4)[3].decode("utf-8")
                layout = incoming.split(b' ', 4)[4].decode("utf-8")
                layout = layout.split(",")
                createWalls(layout)
                print(f"this is id: {id}")
                dummyplayer = dummyPlayer(id, x, y, 0)
                all_sprites.add(dummyplayer)
                all_players.add(dummyplayer)
                if id + 1 <= len(playerlist):
                    playerlist[id] = ((x,y,0))
                    threading.Thread(target=movethread2, args=(id,)).start()
                elif id + 1 > len(playerlist):
                    for i in range(id - len(playerlist)):
                        playerlist.append("")
                    playerlist.append((x,y,0))
                    threading.Thread(target=movethread2, args=(id,)).start()
            elif message[0] == b'MOVE':
                incoming_id = int(message[1].decode("utf-8"))
                position = incoming.split(b' ', 2)[2].decode("utf-8")
                x = position.split(",")[0][1:]
                y = position.split(",")[1][1:]
                angle = position.split(",")[2][1:-1]
                for player in all_players:
                    if player.playerid == incoming_id:
                        if incoming_id + 1 <= len(playerlist):
                            playerlist[incoming_id] = ((x,y,angle))
                        elif incoming_id + 1 > len(playerlist):
                            for i in range(incoming_id - len(playerlist)):
                                playerlist.append("")
                            playerlist.append((x,y,angle))
                if not any(player.playerid == incoming_id for player in all_players):
                    print(f"creating new player with id {incoming_id}")
                    dummyplayer = dummyPlayer(incoming_id, x, y, int(angle))
                    all_sprites.add(dummyplayer)
                    all_players.add(dummyplayer)
                    dummyplayer.rotate()
                    if incoming_id + 1 <= len(playerlist):
                        playerlist[incoming_id] = ((x,y,int(angle)))
                        threading.Thread(target=movethread2, args=(incoming_id,)).start()
                    elif incoming_id + 1 > len(playerlist):
                        for i in range(incoming_id - len(playerlist)):
                            playerlist.append("")
                        playerlist.append((x,y,int(angle)))
                        threading.Thread(target=movethread2, args=(incoming_id,)).start()

                if incoming_id == id:
                    player_alive = True
            elif message[0] == b'KILL':
                message_with_seq = incoming.rsplit(b' ', 1)[0]
                seq = int(message[2].decode("utf-8"))
                if binascii.crc32(message_with_seq + b' ') != int(message[3].decode('utf-8')):
                    continue
                else:
                    sock.sendall(f"ACK {seq}".encode("utf-8"))
                    if seq not in recent_seqs:
                        recent_seqs.append(seq)
                        if len(recent_seqs) > 50:
                            recent_seqs = recent_seqs[1:]
                        incoming_id = int(message[1])
                        if incoming_id == local_id:
                            player_alive = False
                        for player in all_players:
                            if player.playerid == incoming_id:
                                dummyPlayer.kill(player)
                                try:
                                    playerlist[incoming_id] = ""
                                except:
                                    continue
            elif message[0] == b'FIRE':
                message_with_seq = incoming.rsplit(b' ', 1)[0]
                seq = int(message[7].decode("utf-8"))
                if binascii.crc32(message_with_seq + b' ') != int(message[8].decode('utf-8')):
                    continue
                else:
                    sock.sendall(f"ACK {seq}".encode("utf-8"))
                    if seq not in recent_seqs:
                        recent_seqs.append(seq)
                        if len(recent_seqs) > 50:
                            recent_seqs = recent_seqs[1:]
                        decoded = incoming.decode("utf-8")
                        position_string = decoded.split("(")[1].split(")")[0]
                        position = tuple(map(int, position_string.split(', ')))
                        angle = int(decoded.split(" ")[5])
                        incoming_id = int(decoded.split(" ")[6])
                        spawn_bullet(position, angle, incoming_id)
            elif message[0] == b'SCORE':
                message_with_seq = incoming.rsplit(b' ', 1)[0]
                seq = int(message[2].decode("utf-8"))
                if binascii.crc32(message_with_seq + b' ') != int(message[3].decode('utf-8')):
                    continue
                else:
                    sock.sendall(f"ACK {seq}".encode("utf-8"))
                    if seq not in recent_seqs:
                        recent_seqs.append(seq)
                        if len(recent_seqs) > 50:
                            recent_seqs = recent_seqs[1:]
                        score = int(message[1].decode("utf-8"))
            elif message[0] == b'WIN':
                message_with_seq = incoming.rsplit(b' ', 1)[0]
                seq = int(message[2].decode("utf-8"))
                if binascii.crc32(message_with_seq + b' ') != int(message[3].decode('utf-8')):
                    continue
                else:
                    sock.sendall(f"ACK {seq}".encode("utf-8"))
                    if seq not in recent_seqs:
                        recent_seqs.append(seq)
                        if len(recent_seqs) > 50:
                            recent_seqs = recent_seqs[1:]
                        win = int(message[1].decode("utf-8"))
            elif message[0] == b'ACK':
                seq = int(message[1].decode("utf-8"))
                outstanding_acks.remove(seq)
            elif message[0] == b'TEST':
                sock.sendall(b'SUP')

listener = threading.Thread(target=listenthread)
listener.start()



running = True
while running:
    local_id = id
    if pygame.time.get_ticks() - lastMessageTime > 10000:
        print(f"attempting reconnect for id {local_id}")
        for player in all_players:
            dummyPlayer.kill(player)
        sock.sendall(f"RECONNECT {local_id}".encode("utf-8"))
        time.sleep(2)

    #handle game events
    for event in pygame.event.get():
        #handle key events
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                running = False

        elif event.type == pygame.QUIT: running = False
    sendprob = 101
    keyinput = pygame.key.get_pressed()
    if player_alive:
        if keyinput[K_UP]:
            if random.randint(0,100) < sendprob:
                sock.sendall(f"UP {local_id}".encode("utf-8"))
        if keyinput[K_RIGHT]:
            if random.randint(0,100) < sendprob:
                sock.sendall(f"RIGHT {local_id}".encode("utf-8"))
        if keyinput[K_DOWN]:
            if random.randint(0,100) < sendprob:
                sock.sendall(f"DOWN {local_id}".encode("utf-8"))
        if keyinput[K_LEFT]:
            if random.randint(0,100) < sendprob:
                sock.sendall(f"LEFT {local_id}".encode("utf-8"))
        if keyinput[K_SPACE]:
            if random.randint(0,100) < sendprob:
                sock.sendall(f"SPACE {local_id}".encode("utf-8"))
    elif keyinput[K_r]:
        threading.Thread(target=(safesend), args=(f"SPAWN {local_id}",)).start()
        time.sleep(0.5)

    screen.fill((0,0,0))
    for bullet in all_bullets:
        bullet.update()

    text_surf = font.render(str(score), False, (255,255,255))
    screen.blit(text_surf, (20,20))

    #update all sprites to the screen
    for entity in all_sprites:
        screen.blit(entity.surf, entity.rect)

    if win != False:
        bgsquare = pygame.Surface((1920,1080))
        bgsquare.set_alpha(128)
        bgsquare.fill((100, 100, 100))
        screen.blit(bgsquare, (0,0))
        text_surf = font.render(f"Player {win} won!!!", False, (255,255,255))
        screen.blit(text_surf, (SCREEN_WIDTH / 2 - text_surf.get_width() / 2,SCREEN_HEIGHT / 2 - text_surf.get_height() / 2))
        text_surf = smallfont.render(f"press ESC to quit", False, (255,255,255))
        screen.blit(text_surf, (SCREEN_WIDTH / 2 - text_surf.get_width() / 2,SCREEN_HEIGHT / 2 - text_surf.get_height() / 2 + 40))



    #update the screen
    pygame.display.update()
    clock.tick(60)

pygame.quit()
os._exit(0)
#endregion