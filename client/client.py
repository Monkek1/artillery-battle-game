import socket
import threading
import pickle
from server.server import MESSAGE_TYPES

HOST = "127.0.0.1"
PORT = 50000


def listen_server(client_socket):
    #запускаем бесконечный цикл слушания сообщений от сервера
    while True:
        try:
            data = client_socket.recv(4096)
        except OSError:
            break

        if not data:
            print("Соединение с сервером закрыто")
            break

        try:
            message_from_server = pickle.loads(data)
        except Exception as e:
            print(f"Ошибка {e}")

        print(f"Сообщение от сервера: {message_from_server}")

def main():
    # Создаем клиентский сокет и подключаемся к хосту и порту
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    print(f"Подключился к серверу {HOST}: {PORT}")

    thread = threading.Thread(target=listen_server, args=(client_socket,), daemon=True)
    thread.start()

    client_socket.sendall(pickle.dumps({
        "type": MESSAGE_TYPES.JOIN,
        "payload": {"name", "потом"}
    }))

    print("Введите сообщение: ")
    while True:
        text_from_user = input("> ").strip()
        if text_from_user.lower() == "quit":
            break
    
        chat_message = {
            "type": MESSAGE_TYPES.CHAT,
            "payload": {"text": text_from_user}
        }

        try:
            client_socket.sendall(pickle.dumps(chat_message))
        except OSError:
            print("Соединение разорвано")
            break

if __name__ == "__main__":
    main()