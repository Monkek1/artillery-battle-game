# client.py
import math
import socket
import threading
import queue
import tkinter as tk
from tkinter import messagebox
from common import send_msg, recv_msg

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 50007


class ClientApp:
    #root - главное окно tkninter
    def __init__(self, root):
        self.root = root
        self.root.title("Артиллерийская битва")

        '''
        создаем 
        клиентский сокет
        поток который позже в фоне будет принимать сообщения
        и очередь в которую сначала будем класть сообщения из потока, а потом
        передавать их в интерфейс пользователя, так как ткинтер не рассчитан
        на работу с потоком кроме главного
        '''
        self.sock = None
        self.recv_thread = None
        self.msg_queue = queue.Queue()

        #данные которые будет присылать сервер на клиент
        self.player_id = None
        self.players = []
        self.map_width = 800
        self.map_height = 400
        self.map_heights = []
        self.current_player_id = None
        self.nickname = ""

        #экраны которые будут переключаться
        self.frame_login = tk.Frame(root)
        self.frame_lobby = tk.Frame(root)
        self.frame_game = tk.Frame(root)
        self.frame_result = tk.Frame(root)

        self.build_login_frame()
        self.build_lobby_frame()
        self.build_game_frame()
        self.build_result_frame()

        #первым делом показывает окно логина
        self.show_frame(self.frame_login)

        #постоянно обрабатываем сообщения
        self.root.after(50, self.process_messages)

    #переключает экран на другой и показывает выбранный на все окно
    def show_frame(self, frame):
        for f in (self.frame_login, self.frame_lobby, self.frame_game, self.frame_result):
            f.pack_forget()
        #fill растягивает экран на все окно, а экспанд распрдееляет свободное место в пользу
        #этого окна
        frame.pack(fill="both", expand=True)

    #создание окна логина
    def build_login_frame(self):
        #создаем текст введите ник с отступом 5 сверху, создаем поле для ввода ника
        #вставляем в него стандартное значение игрок и делаем отступ сверху 5
        tk.Label(self.frame_login, text="Введите ник:").pack(pady=5)
        self.entry_nick = tk.Entry(self.frame_login)
        self.entry_nick.insert(0, "Игрок")
        self.entry_nick.pack(pady=5)

        #создаем текст комната и поле для ввода в какую комнату хотим с отступом 5 сверху
        tk.Label(self.frame_login, text="Комната:").pack(pady=5)
        self.entry_room = tk.Entry(self.frame_login)
        self.entry_room.insert(0, "Комната")
        self.entry_room.pack(pady=5)

        #кнопка подключиться которая вызывает функцию при подключении с отступом 10 сверху
        tk.Button(self.frame_login, text="Подключиться", command=self.on_connect).pack(pady=10)

    #функция при подключении
    def on_connect(self):
        #получаем из полей ввода данные без пробелов или на стандартные их заменяаем если ничего нет
        nickname = self.entry_nick.get().strip() or "Игрок"
        room_name = self.entry_room.get().strip() or "Комната"
        #назначем объекту клиентского приложения ник который введен
        self.nickname = nickname

        #пробуем создать клиентский IPv4 TCP сокет и подключиться по хосту и порту
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((SERVER_HOST, SERVER_PORT))
        except OSError as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")
            return

        #говорим серверу что подключаемся
        send_msg(self.sock, {"type": "HELLO", "nickname": nickname})
        send_msg(self.sock, {"type": "JOIN_ROOM", "room": room_name})

        #запускаем фоновый поток который слушает сообщения
        self.recv_thread = threading.Thread(target=self.recv_loop, daemon=True)
        self.recv_thread.start()

        #переключаем экран на лобби
        self.show_frame(self.frame_lobby)

    #создание экрана лобби
    def build_lobby_frame(self):
        #текст лобби с отстуом 5 сверху, показывает
        #список игроков в виде виджета со строками шириной 40
        tk.Label(self.frame_lobby, text="Лобби").pack(pady=5)
        self.listbox_players = tk.Listbox(self.frame_lobby, width=40)
        self.listbox_players.pack(pady=5)

        #переменная готовности, кнопка для галочки готов
        self.ready_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self.frame_lobby, text="Готов", variable=self.ready_var,
            #кнопка запускает функцию при готовности
            command=self.on_ready_toggle
        ).pack(pady=5)

    #функция при готовности которая говорит серверу что игрок готов и отсылаем
    #переменную готовности чтобы кнопку можно было обратно туда сюда переключать
    #и сервер знал готов или не готов игрок
    def on_ready_toggle(self):
        send_msg(self.sock, {
            "type": "SET_READY",
            "ready": self.ready_var.get()
        })

    #функция обновления лобби которая будет запускаться при полученнии lobby_state
    #от сервера для отрисовки лобби
    def update_lobby(self, msg):
        #чистим полностью наш список игроков нарисованный от 0 до последнего элемента, 
        self.listbox_players.delete(0, tk.END)
        # из сообщения от сервера получаем список игроков и проходимся по нему и 
        # каждого игрока вставляем с конца строки с игроками и их готовностью
        for player in msg["players"]:
            if player['ready']:
                self.listbox_players.insert(tk.END, f"{player['nickname']} Готов")
            else:
                self.listbox_players.insert(tk.END, f"{player['nickname']} ...")

    #создание окна с игровым процессом
    def build_game_frame(self):
        #верхняя панель управления растянутая по ширине приклеенная к верху
        top = tk.Frame(self.frame_game)
        top.pack(side="top", fill="x")

        #кладем в нее текст в котором инфа основная
        self.label_turn = tk.Label(top, text="Ход: -")
        self.label_turn.pack(side="left", padx=5)

        tk.Label(top, text="Угол:").pack(side="left")
        self.entry_angle = tk.Entry(top, width=5)
        self.entry_angle.insert(0, "45")
        self.entry_angle.pack(side="left", padx=2)

        tk.Label(top, text="Сила:").pack(side="left")
        self.entry_power = tk.Entry(top, width=5)
        self.entry_power.insert(0, "50")
        self.entry_power.pack(side="left", padx=2)

        #при отпускании клавиши в полях ввода угла и силы вызываем перерисовку игры
        #для того чтобы предпросматривать примерную траекторию полета
        self.entry_angle.bind("<KeyRelease>", lambda e: self.redraw_game())
        self.entry_power.bind("<KeyRelease>", lambda e: self.redraw_game())

        #кнопка выстрела которая вызывает команду при выстреле и изначально выключена чтобы
        #не стреляли те не чей ход
        self.btn_fire = tk.Button(top, text="Огонь!", command=self.on_fire, state="disabled")
        self.btn_fire.pack(side="left", padx=5)

        #рисуем полотно неба которое заполняет всё окно и светло синее
        self.canvas = tk.Canvas(self.frame_game, width=800, height=400, bg="lightblue")
        self.canvas.pack(fill="both", expand=True)

    #команда при выстреле
    def on_fire(self):
        #получаем данные выстрела и говорим серверу что сделали выстрел
        try:
            angle = float(self.entry_angle.get())
            power = float(self.entry_power.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректный угол или сила")
            return
        send_msg(self.sock, {
            "type": "FIRE",
            "angle": angle,
            "power": power
        })
        #выключаем кнопку выстрела до следующего хода
        self.btn_fire.config(state="disabled")

    #функция старта игры, которая принимате сообщение от сервера и берет из него все данные
    def start_game(self, msg):
        self.player_id = msg["your_id"]
        self.map_width = msg["map"]["width"]
        self.map_height = msg["map"]["height"]
        self.map_heights = msg["map"]["heights"]
        self.players = msg["players"]
        self.current_player_id = msg["current_player_id"]

        #показывает окно игрового процесса и перерисовываем графику сразу
        self.show_frame(self.frame_game)
        self.redraw_game()

    #функция обновления состояния игры которая получает сообщения от сервера
    #узнает состояние игроков, получает и назначает нового текущего игрока
    #и перерисоывает графику
    def update_game_state(self, msg):
        self.players = msg["players"]
        self.current_player_id = msg["current_player_id"]
        self.redraw_game()

    #фунция которая отрисовывает/перерисовывает землю и игроков
    def redraw_game(self):
        #сначала стираем всю землю и игроков
        self.canvas.delete("all")

        #рисуем землю
        w = self.map_width
        h = self.map_height
        cols = len(self.map_heights)
        points = []
        #циклом проходимся по высотам и получает значение и индекс в каждой итерации
        #получаем список с x, y для каждой высоты на карте
        for i, height in enumerate(self.map_heights):
            x = i * w / (cols - 1)
            y = h - height
            points.append((x, y))
            
        #Добавляем в конец и в начало точки в нижних углах экрана чтобы земля нарисовалась под точками
        points = [(0, h)] + points + [(w, h)]
        #и превращаем этот список из списка чисел по два в список чисел по одному
        pointsSingleElements = []
        for x, y in points:
            pointsSingleElements.extend([x, y])
        #отправляем распакованный в позиционные аргументы список точек в фукнцию
        #и рисуем один большой полигон земли зеленого цвета с черным контуром
        self.canvas.create_polygon(*pointsSingleElements, fill="green", outline="black")

        # рисуем пушки для каждого игрока
        for player in self.players:
            #если игрок не живой то не рисуем
            if not player["alive"]:
                continue
            r = 8
            #обозначаем границы круга от координат игрока по радиусу
            self.canvas.create_oval(
                player["x"] - r, player["y"] - r, player["x"] + r, player["y"] + r,
                fill="red" if player["id"] == self.player_id else "black"
            )
            self.canvas.create_text(player["x"], player["y"] - 15,
                                    text=f"{player['nickname']} ({player['hp']})",
                                    anchor="s")

        # определяем чей ход
        # если того игрока которого запущенное приложение то включаем ему кнопку выстрела
        # и пишем ему в окне что его ход
        if self.current_player_id == self.player_id:
            self.label_turn.config(text="Ваш ход")
            self.btn_fire.config(state="normal")
        # если не его ход, то
        else:
            # узнаем имя игрока которого ход, пишем что его ход и выключаем конкретному игроку кнопку
            name = next((player["nickname"] for player in self.players if player["id"] == self.current_player_id), "?")
            self.label_turn.config(text=f"Ход: {name}")
            self.btn_fire.config(state="disabled")

        #если игрок = текущий игрок то рисуем траекторию выстрела
        if self.current_player_id == self.player_id:
            self.draw_trajectory_preview(float(self.entry_angle.get()), float(self.entry_power.get()))

    #TODO: траектория выстрелов
    def draw_trajectory_preview(self, angle, power):
        #берем код из simulate_shot с файла сервера
        angle_rad = math.radians(angle)
        vx = power * math.cos(angle_rad)
        vy = -power * math.sin(angle_rad)

        player = self.players[self.player_id]

        x = player["x"]
        y = player["y"]

        g = 9.8 * 5
        dt = 0.1
        cols = len(self.map_heights)

        max_len = 200
        drawn_len = 0
        points = [(x, y)]

        while drawn_len < max_len and 0 <= x < self.map_width and 0 <= y < self.map_height:
            x += vx * dt
            vy += g * dt
            y += vy * dt

            col = int(x / self.map_width * (cols - 1))
            ground_y = self.map_height - self.map_heights[col]
            if y >= ground_y:
                y = ground_y
                points.append((x, y))
                break

            last_x, last_y = points[-1]
            step_len = math.hypot(x - last_x, y - last_y)
            if drawn_len + step_len > max_len:
                # обрезаем сегмент так, чтобы суммарно было ровно max_len
                ratio = (max_len - drawn_len) / step_len
                x = last_x + (x - last_x) * ratio
                y = last_y + (y - last_y) * ratio
                points.append((x, y))
                break
            else:
                drawn_len += step_len
                points.append((x, y))

        if len(points) >= 2:
            flat = [coord for pt in points for coord in pt]
            self.canvas.create_line(*flat, fill="orange", width=2, dash=(3, 2))    


    #создание окна с результатами
    def build_result_frame(self):
        self.label_result = tk.Label(self.frame_result, text="Результат")
        self.label_result.pack(pady=10)
        #кнопка для возвращения в лобби
        tk.Button(self.frame_result, text="Вернуться к выбору лобби", command=self.back_to_lobby).pack(pady=10)

    #функция показа результата которая от сервера получает айди победителя
    def show_result(self, winner_id):
        if winner_id is None:
            self.label_result.config(text="Ничья или все вышли")
        elif winner_id == self.player_id:
            self.label_result.config(text="Вы победили!")
        else:
            name = next((player["nickname"] for player in self.players if player["id"] == winner_id), "?")
            self.label_result.config(text=f"Победил игрок: {name}")
        self.show_frame(self.frame_result)

    #функция выхода в лобби, перезапускаем клиента
    def back_to_lobby(self):
        self.root.destroy()

    #функция цикла для принятия сообщений
    def recv_loop(self):
        #получаем сообщение из сокета и кладем его в очередь
        try:
            while True:
                msg = recv_msg(self.sock)
                self.msg_queue.put(msg)
        except Exception as e:
            print("recv_loop error:", e)
        finally:
            #все равно закрываем подключение в конце
            try:
                self.sock.close()
            except OSError:
                pass

    #функция обработки сообщений из очереди
    #при включении работает постоянно и не блокируется, чтобы окно ткинтера не висло
    def process_messages(self):
        while True:
            try:
                #берем из очереди сообщение без ожидания чтобы выходить из цикла
                #если сообщений нет сразу
                msg = self.msg_queue.get_nowait()
            except queue.Empty:
                break
            #как достали из очереди то вызываем функцию работы с сообщениями
            self.handle_message(msg)
        #через 50мс по новой проверяем очередь на сообщения
        self.root.after(50, self.process_messages)

    #функция работы с сообщениями
    def handle_message(self, msg):
        mtype = msg.get("type")
        if mtype == "LOBBY_STATE":
            self.update_lobby(msg)
        elif mtype == "GAME_START":
            self.start_game(msg)
        elif mtype == "GAME_STATE":
            self.update_game_state(msg)
        elif mtype == "SHOT_RESULT":
            pass
        elif mtype == "GAME_OVER":
            self.show_result(msg.get("winner_id"))
        elif mtype == "PLAYER_LEFT":
            print("Player left:", msg.get("nickname"))
        elif mtype == "__DISCONNECTED__":
            messagebox.showwarning("Отключено", "Связь с сервером потеряна.")
            self.show_frame(self.frame_login)

# создаем окно ткинтера, передаем его в созданный объект приложения и 
# запускаем главный цикл работы окна чтобы оно реагировало на события
def main():
    root = tk.Tk()
    app = ClientApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
