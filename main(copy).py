import socket
import threading
import tkinter as tk
from ui.auth_window import AuthWindow
from ui.contact_list import ContactListWindow
from ui.chat_window import ChatWindow
import sys

# Глобальные переменные для связи
client_socket = None

def start_app():
    print("[LOG] Приложение запущено")
    session = {"username": None}

    def login_callback(user):
        print(f"[LOG] Успешный логин в окне: {user}")
        session["username"] = user

    def open_chat_handler(contact_name):
        print(f"[LOG] Открываем чат с {contact_name}")
        def send_msg_to_net(name,message):
            if client_socket:
                full_msg = f"{session['username']}:{message}"
                client_socket.send(full_msg.encode('utf-8'))
                def listen_server():
                    while True:
                        try:
                            data = client_socket.recv(1024).decode('utf-8')
                            if data:
                               print(f"\n[СЕРВЕР ПРИСЛАЛ]: {data}")
                            #    Тут позже будет логика вывода текста в окно чата
                        except:
                            print("Связь с сервером потеряна")
                            break
        # Запускаем "ухо" в отдельном потоке, чтобы окно не висло
        threading.Thread(target=listen_server, daemon=True).start()

        ChatWindow(contact_name, send_msg_to_net)

    # 1. Запуск окна авторизации
    print("[LOG] Открываем AuthWindow...")
    AuthWindow(login_callback)

    # 2. Этот код выполнится ТОЛЬКО после того, как AuthWindow закроется (через destroy)
    print(f"[LOG] AuthWindow закрыто. Текущая сессия: {session['username']}")

    if session["username"]:
        global client_socket
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(('127.0.0.1', 5555))
            client_socket.send(session["username"].encode('utf-8'))
            print("[LOG] Подключено к серверу!")
        except Exception as e:
            print(f"[ERROR] Сервер не ответил: {e}")

        print("[LOG] Запускаем Список Контактов...")

        ContactListWindow(session["username"], open_chat_handler)
    else:
        print("[LOG] Вход не был выполнен. Завершение.")
        sys.exit()

if __name__ == "__main__":
    start_app()


class MessengerApp:
    def __init__(self):
        self.server_ip = '127.0.0.1' # ТВОЙ IP ИЗ RADMIN VPN
        self.port = 5555
        self.client_socket = None
        self.username = None
        
        # Хранилище открытых окон чатов: { "ИмяДруга": объект_окна }
        self.open_chats = {}

        # Запускаем авторизацию
        AuthWindow(self.login_success)

    def login_success(self, username):
        self.username = username
        print(f"[NET] Попытка подключения к серверу {self.server_ip}...")
        
        try:
            # Настройка сокета
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_ip, self.port))
            print("[LOG] Соединение установлено!")
        except Exception as e:
            print(f"[CRITICAL] Ошибка подключения: {e}") 
            
            # Отправляем никнейм серверу (первое сообщение)
            self.client_socket.send(self.username.encode('utf-8'))
            
            # Запускаем поток прослушивания сервера
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
            # Открываем список контактов
            self.contact_list = ContactListWindow(self.username, self.start_chat_callback)
            
        except Exception as e:
            print(f"[ERROR] Не удалось подключиться к серверу: {e}")
            tk.messagebox.showerror("Ошибка сети", "Сервер недоступен. Проверь Radmin и запущен ли server.py")

    def receive_messages(self):
        """Фоновая функция, которая ждет сообщения от сервера"""
        while True:
            try:
                data = self.client_socket.recv(1024).decode('utf-8')
                if not data: break
                
                # Простейший протокол: "Отправитель:Сообщение"
                if ":" in data:
                    sender, message = data.split(":", 1)
                    
                    # Если окно чата с этим человеком открыто — пишем туда
                    if sender in self.open_chats:
                        self.open_chats[sender].display_message(sender, message)
                    else:
                        print(f"Новое сообщение от {sender}: {message} (Окно чата закрыто)")
                else:
                    print(f"[SERVER]: {data}")
                    
            except:
                print("[NET] Соединение разорвано")
                break

    def start_chat_callback(self, contact_name):
        """Вызывается при двойном клике в списке контактов"""
        if contact_name not in self.open_chats:
            # Создаем окно чата и передаем функцию отправки
            new_chat = ChatWindow(contact_name, self.send_to_server)
            self.open_chats[contact_name] = new_chat
            # При закрытии окна удаляем его из списка открытых
            new_chat.window.protocol("WM_DELETE_WINDOW", lambda: self.on_chat_close(contact_name))

    def send_to_server(self, contact_name, message):
        """Отправка сообщения через сокет"""
        if self.client_socket:
            # Формат для сервера: "Кому:Сообщение" (упростим пока до общей рассылки)
            full_message = f"{self.username}:{message}"
            self.client_socket.send(full_message.encode('utf-8'))

    def on_chat_close(self, contact_name):
        if contact_name in self.open_chats:
            self.open_chats[contact_name].window.destroy()
            del self.open_chats[contact_name]

if __name__ == "__main__":
    app = MessengerApp()