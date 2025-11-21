import math
import random
import pickle

rooms = {}
next_player_id = 1

#объект игрока который хранит его данные
class Player:
    def __init__(self, player_id, name, client_connection):
        self.player_id = player_id
        self.name = name
        self.client_connection = client_connection
        self.ready = False
        self.alive = True
        self.hp = 100
        self.x = 0
        self.y = 0

    #превращаем данные игрока в словарь для пересылки позже
    def serialize_player_data(self):
        return {
            "player_id": self.player_id,
            "name": self.name,
            "ready": self.ready,
            "alive": self.alive,
            "hp": self.hp,
            "x": self.x,
            "y": self.y
        }
    
#Объект комнаты в которую входят игроки и которой принадлежит объект
#игровой логкики
class Room:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players = []
        self.started = False
        self.game = None

    def add_player(self, player):
        if self.started:
            return False
        if len(self.players) >= 4:
            return False
        self.players.append(player)
        return True
    
    def remove_player(self, player):
        self.players.remove(player)

    def all_ready(self):
        if not (2 <= len(self.players) <= 4):
            return False
        return all(player.ready for player in self.players)
    
    #рассылка сообщений клиентам
    def broadcast(self, message):
        data = pickle.dumps(message)
        for player in list(self.players):
            try:
                player.client_connection.sendall(data)
            except Exception as e:
                player.alive = False

#Объект игровой логики, который будет создаваться для каждой комнаты
class Game:
    #TODO: ходы, выстрелы
    def __init__(self, room):
        self.room = room
        self.current_turn_index = 0
        self.width = 800
        self.height = 600
        self.current_player = self.room.players[0]
        self.terrain = []

    def start(self):
        self.generate_terrain()
        self.place_players()

    #карта генерируется в виде одномерного массива высот
    def generate_terrain(self):
        self.terrain = []

        #выбираем рамки для линии примерно по центру экрана
        current_height = self.height // 3
        min_height = self.height // 6
        max_height = self.height // 2

        for i in range(self.width):
            #каждую итерацию цикла рисуем линию и выбираем случайно пойти вверх или вниз
            #при этом линия не выходит за рамки
            current_height = max(min_height, min(max_height, current_height + random.choice([-1, 0, 1])))
            self.terrain.append(current_height)

    #расставляем игроков по карте
    def place_players(self):
        #игроки расставляются от 20 до (width - 20) каждые ~200 точек
        #высота находится по горизонатнльйо координате из массива с линией
        current_x = 20
        for player in self.room.players:
            player.x = current_x
            player.y = self.terrain[player.x]
            current_x = min(self.width - 20, current_x + 200 + random.randint(-50, 50))

    def broadcast(self):
        pass