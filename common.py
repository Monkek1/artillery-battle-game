'''
В common.py заданы универсальные функции отправки и получения сообщений

Импорты:
pickle необходим для преобразования словарей в байты и обратно
struct необходим для превращения чисел в байты и обратно
'''
import pickle 
import struct

'''
Заголовок будет испольховаться в качестве длины сообщения в байтах в начале сообщения
для обозначения начала нового сообщения в tcp соединении
'''

#размер заголовка сообщения
HEADER_SIZE = 4 

#функция отправки сообщения
#принимает сокет по которому отправит сообщение и сообщение в виде словаря
def send_msg(socket, dict):
    #превращаем словарь в байты
    data = pickle.dumps(dict)
    #создаем длину сообщения в байтах
    header = struct.pack('!I', len(data))
    #отсылаем по сокету заголовок и данные
    socket.sendall(header + data)

#функция получения сообщения   
def recv_msg(socket):
    #получаем заголовок читая из сообщения ровно столько, сколько по размерам заголовок
    header = _recv_exact(socket, HEADER_SIZE)
    if not header:
        return None
    #превращаем байты обратно в число чтобы узнать какое по длине само сообщение
    (length,) = struct.unpack('!I', header)
    #читаем само сообщение после заголовка
    body = _recv_exact(socket, length)
    if not body:
        return None
    #возвращаем прочитанное сообщение в виде словаря
    return pickle.loads(body)

#функция для чтения из сокета ровно n байт
def _recv_exact(socket, n):
    #буфер
    chunks = []
    #сколько байт уже получили
    bytes_recd = 0
    #пока не получили нужное количество байтов
    while bytes_recd < n:
        try:
            #читаем столько, сколько еще нужно из сокета
            chunk = socket.recv(n - bytes_recd)
        except OSError:
            return None
        if not chunk:
            return None
        #добавляем прочитанное в буфер и увеличиваем число сколько байт мы прочитали
        chunks.append(chunk)
        bytes_recd += len(chunk)

    #возвращаем байтовый объект, в котором все что мы прочитали и положили в буфер
    return b''.join(chunks)
