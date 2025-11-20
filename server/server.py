import socket
import threading
import pickle #сериализация и десереализация сообщений
import server.gamelogic

#адрес и порт на котором слушаются подключения
HOST = "127.0.0.1"
PORT = 50000

class MESSAGE_TYPES:
    JOIN = "JOIN"
    READY = "READY"
    DISCONNECT = "DISCONNECT"
    GAME_STATE = "GAME_STATE"
    CHAT = "CHAT"
    SHOT = "SHOT"
    ERROR = "ERROR"

#работа с клиентами
def handle_clinet(client_connection, client_address):
    print(f"Клиент подключился")
    try:
        # запускаем бесконечный цикл принятия сообщений от клиента
        while True:
            data = client_connection.recv(4096)
            if not data:
                break

            # с помощью пикла превращаем принятые байты в словарь
            try:
                message_from_client = pickle.loads(data)
            except Exception as e:
                print(f"Ошибка десериализации: {client_address}: {e}")
        

            #узнаем из словаря какой тип сообщения
            message_type = message_from_client.get("type")

            #в зависимости от типа сообщения выбираем что делать с ним
            if message_type == MESSAGE_TYPES.JOIN:
                message_to_client = {
                    "type": MESSAGE_TYPES.CHAT,
                    "payload": {"message": "Вы подключились в лобби"}
                }

            elif message_type == MESSAGE_TYPES.CHAT:
                message_to_client = {
                    "type": MESSAGE_TYPES.CHAT,
                    "payload": {"original": message_from_client.get("payload")}
                }
            
            else:
                message_to_client = {
                    "type": MESSAGE_TYPES.ERROR,
                    "payload": {"message": f"Ошибка {message_from_client.get("type")}"}
                }

            #после принятия сообщения от клиента, обновляем данные у всех
            #клиентов
            try:
                client_connection.sendall(pickle.dumps(message_to_client))
            except Exception as e:
                print(f"Ошибка отправки {e}")
                break
            
    #в любом случае отключаемся независимо от результата
    finally:
        print(f"Клиент отключился: {client_address}")
        client_connection.close()

#точка запуска сервера
def main():
    '''
    Создаем серверный сокет IPv4 TCP, делаем возможным переиспользование
    адреса чтобы не было ошибки, привязываем к нашим портам и хосту и
    переводим в режим слушания новых подключений
    '''
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    '''
    '''
    while True:
        #ждем подключения через accept
        client_connection, client_address = server_socket.accept()
        #создаем фоновый поток с подключением клиента
        thread = threading.Thread(
            target=handle_clinet,
            args=(client_connection, client_address),
            daemon=True,
            )
        thread.start()
    
if __name__ == "__main__":
    main()