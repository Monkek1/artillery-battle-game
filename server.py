'''
'''
import socket
import threading
import random
import math
from common import send_msg, recv_msg

HOST = '0.0.0.0'
PORT = 50007

#Объект игрока, который хранит в себе данные
class Player:
    def __init__(self, socket, address, nickname):
        self.sock = socket
        self.addr = address
        self.nickname = nickname
        self.id = None
        self.ready = False
        self.hp = 100
        self.alive = True
        self.x = 0
        self.y = 0
        self.room = None

#Объект комнаты, в которую заходят игроки и в которой находится игровая логика
class Room:
    def __init__(self, name):
        self.name = name
        self.players = []
        self.lock = threading.Lock()
        self.game_started = False
        self.current_player_index = 0
        self.map_width = 800
        self.map_height = 400
        self.heights = [] #карта реализуется в виде массива высот

    #добавление игрока в комнату
    def add_player(self, player):
        with self.lock:
            #айди игрока назначается в зависимости от его порядка в списке игроков
            player.id = len(self.players)
            player.room = self
            self.players.append(player)
            self.broadcast_lobby_state()

    #удаление игрока из комнаты
    def remove_player(self, player):
        with self.lock:
            if player in self.players:
                self.players.remove(player)
                #если уже началась игра то меняем данные
                if self.game_started:
                    player.alive = False
                    self.broadcast({
                        "type": "PLAYER_LEFT",
                        "id": player.id,
                        "nickname": player.nickname
                    })
                    #и проверяем а не закончится ли игра после его удаления
                    self.check_game_over()
                else:
                    self.broadcast_lobby_state()

    #функция для определения готовности игрока
    def toggle_ready(self, player, ready):
        with self.lock:
            player.ready = ready
            self.broadcast_lobby_state()
            #пытаемся запустить игру если вдруг уже все готовы
            self.try_start_game()

    #вид сообщения о состоянии комнаты
    def lobby_state_msg(self):
        return {
            "type": "LOBBY_STATE",
            "room": self.name,
            "players": [
                {"id": player.id, "nickname": player.nickname, "ready": player.ready}
                for player in self.players
            ]
        }

    #функция отправки сообщения клиентам о состоянии комнаты в которой они
    def broadcast_lobby_state(self):
        self.broadcast(self.lobby_state_msg())

    #общая функция отправки сообщений по сокету
    def broadcast(self, msg):
        for player in list(self.players):
            try:
                #send_msg из common.py
                send_msg(player.sock, msg)
            except OSError:
                pass

    #функция попытки начать игру
    #для отдельной проверки можно ли это делать
    def try_start_game(self):
        if self.game_started:
            return
        if len(self.players) < 2:
            return
        if not all(player.ready for player in self.players):
            return
        self.start_game()

    #функция начала игры
    def start_game(self):
        self.game_started = True
        #генерируем карту
        '''
        создаем список из n высот. По сути, карта будет разбита на n участков и представлять из себя
        физически набор прямоугольников, на которых стоят игроки и черезW которые летят снаряды.
        Чтобы позже вычислить какая высота y в определенной точке x, мы находим в каком из этих n отрезков
        находится точка x. Для этого используется определнная формула col = x / map_width * (cols - 1).
        Col = индекс столбца в списке высот.
        '''
        cols = 80

        self.heights = [random.randint(180, 200) for _ in range(cols)]
        #шаг черех который ставим игроков
        step = self.map_width // (len(self.players) + 1)
        #ставим игроков на карте
        for i, p in enumerate(self.players):
            p.hp = 100
            p.alive = True
            x = (i + 1) * step
            col = int(x / self.map_width * (cols - 1))
            # координаты в tkninter сверху вниз, поэтому тут учитываем это
            ground_y = self.map_height - self.heights[col]
            p.x = x
            p.y = ground_y - 10  # чуть выше земли

        self.current_player_index = 0

        # рассылаем всем сообщения что игра началась
        # тут данные игроков, данные карты чтобы ее рисовать и айди того кто щас ходит
        for p in self.players:
            msg = {
                "type": "GAME_START",
                "your_id": p.id,
                "map": {
                    "width": self.map_width,
                    "height": self.map_height,
                    "heights": self.heights,
                },
                "players": [
                    {
                        "id": pl.id,
                        "nickname": pl.nickname,
                        "hp": pl.hp,
                        "x": pl.x,
                        "y": pl.y,
                        "alive": pl.alive
                    }
                    for pl in self.players
                ],
                "current_player_id": self.players[self.current_player_index].id
            }
            try:
                send_msg(p.sock, msg)
            except OSError:
                pass

        self.broadcast_game_state()

    #определение игрока, который сейчас ходит
    def current_player(self):
        if not self.players:
            return None
        #получение остатка из деления нужно чтобы получать нужного игрока, даже если 
        #self.current_player_index > len(self.players)
        return self.players[self.current_player_index % len(self.players)]

    def next_turn(self):
        # ищем следующего живого
        for _ in range(len(self.players)):
            #ставим индексом текущего игрока индекс следующего игрока
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            #если он живой, то больше не ищем
            if self.players[self.current_player_index].alive:
                break
        self.broadcast_game_state()

    #вспомогательная функция для рассылки данных клиентам, которая определяет
    #что мы отсылаем данные игроков
    def broadcast_game_state(self):
        msg = {
            "type": "GAME_STATE",
            "players": [
                {
                    "id": p.id,
                    "nickname": p.nickname,
                    "hp": p.hp,
                    "x": p.x,
                    "y": p.y,
                    "alive": p.alive
                }
                for p in self.players
            ],
            "current_player_id": self.current_player().id if self.current_player() else None
        }
        self.broadcast(msg)

    #обработка выстрела игрока
    def handle_fire(self, player: Player, angle_deg: float, power: float):
        #проверка началась ли игра, жив ли игрок, ходит ли игрок сейчас
        if not self.game_started or not player.alive:
            return
        if player != self.current_player():
            return

        # симулируем выстрел и получаем куда и в кого попало
        hit_player, hit_x, hit_y = self.simulate_shot(player, angle_deg, power)

        # если существует задетый игрок, меняем данные так как это ссылка на объект
        if hit_player:
            hit_player.hp -= 40
            if hit_player.hp <= 0:
                hit_player.hp = 0
                hit_player.alive = False

        # всем сообщаем результат выстрела
        self.broadcast({
            "type": "SHOT_RESULT",
            "from_id": player.id,
            "hit_id": hit_player.id if hit_player else None,
            "hit_x": hit_x,
            "hit_y": hit_y
        })

        #проверяем не закончилась ли игра после попадания
        self.check_game_over()
        if not self.game_started:
            return  # игра закончилась
        self.broadcast_game_state()
        self.next_turn()

    #функция для симуляции выстрела
    def simulate_shot(self, player: Player, angle_deg: float, power: float):
        #угол и направление выстрела
        angle = math.radians(angle_deg)
        vx = power * math.cos(angle)
        vy = -power * math.sin(angle)  # координаты на карте идут сверху вниз, поэтому игрок с минусом
        #начальная позиция снаряда в точке откуда игрок стреляет
        x = player.x
        y = player.y
        #ускорение снаряда и скорость
        g = 9.8 * 5
        dt = 0.1
        #узнаем сколько высот на карте
        cols = len(self.heights)

        # цикл полёта снаряда
        while 0 <= x < self.map_width and 0 <= y < self.map_height:
            # итерация полёта
            x += vx * dt
            vy += g * dt
            y += vy * dt

            #узнаем в какой из n секций при высоте на карте снаряд по формуле
            col = int(x / self.map_width * (cols - 1))
            #координаты в игре идут сверху вниз, поэтому считаем от верха экрана сколько до земли
            ground_y = self.map_height - self.heights[col]

            # если снаряд от верха экрана прошел больше, чем до земли, то он попадает в землю
            if y >= ground_y:
                hit_x, hit_y = x, ground_y
                break
        else:
            # вылетело за экран
            hit_x, hit_y = x, y

        # проверим игроков по радиусу попадания
        radius = 30
        hit_player = None
        #считаем дистанцию всех игроков до места попадания
        for p in self.players:
            if not p.alive:
                continue
            #считаем расстояние
            dist = math.hypot(p.x - hit_x, p.y - hit_y)
            #если игрок задет то назначем его тем, по кому попали
            if dist <= radius:
                hit_player = p
                break

        return hit_player, hit_x, hit_y

    #проверка закончена ли игра 
    #если в живых 1 игрок или меньше то назначаем его победителем если есть и говорим всем
    def check_game_over(self):
        alive_players = [p for p in self.players if p.alive]
        if len(alive_players) <= 1 and self.game_started:
            winner_id = alive_players[0].id if alive_players else None
            self.broadcast({
                "type": "GAME_OVER",
                "winner_id": winner_id
            })
            self.game_started = False


#Объект сервера
class GameServer:
    #при создании назначаем порт, хост, список комнат для игроков,
    #сокет сервера IPv4 TCP, назначем ему порт и хост и пусть он начинает слушать соединения с макс очередью 8
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.rooms = {"default": Room("default")}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(8)
        print(f"Server listening on {self.host}:{self.port}")

    #функция запуска сервера
    def start(self):
        #бесконечный цикл слушания новых подключений
        while True:
            #accept нужен для ожидания подключения
            client_sock, addr = self.sock.accept()
            print("New connection from", addr)
            #запускаем функцию работы с клиентом в фоновом потоке
            t = threading.Thread(target=self.handle_client, args=(client_sock, addr), daemon=True)
            t.start()

    #функция работы с клиентом
    def handle_client(self, client_sock, addr):
        player = None
        room = None
        try:
            # ждём HELLO
            msg = recv_msg(client_sock)
            if not msg or msg.get("type") != "HELLO":
                client_sock.close()
                return
            nickname = msg.get("nickname", "Anon")
            player = Player(client_sock, addr, nickname)

            # ждём JOIN_ROOM
            msg = recv_msg(client_sock)
            if not msg or msg.get("type") != "JOIN_ROOM":
                client_sock.close()
                return
            room_name = msg.get("room", "default")
            room = self.rooms.get(room_name)
            if not room:
                room = Room(room_name)
                self.rooms[room_name] = room
            room.add_player(player)

            # Основной цикл приема сообщений
            while True:
                msg = recv_msg(client_sock)
                if msg is None:
                    print(f"Client {addr} disconnected")
                    break
                mtype = msg.get("type")
                if mtype == "SET_READY":
                    ready = bool(msg.get("ready", False))
                    room.toggle_ready(player, ready)
                elif mtype == "FIRE":
                    angle = float(msg.get("angle", 45))
                    power = float(msg.get("power", 50))
                    room.handle_fire(player, angle, power)
                elif mtype == "LEAVE":
                    break
        except Exception as e:
            print("Error with client", addr, e)
        finally:
            # аккуратное удаление
            try:
                client_sock.close()
            except OSError:
                pass
            if room and player:
                room.remove_player(player)

#запускаем сервер при старте программы
if __name__ == "__main__":
    GameServer(HOST, PORT).start()
