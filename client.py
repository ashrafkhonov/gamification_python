
import tkinter as tk
import tkinter.messagebox
import socket
import threading
import time
import sys

HOST_ADDR = ""
HOST_PORT = 0

class ClientInterface(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.container = tk.Frame(self)
        self.resizable(width=False, height=False)
        self.title(string="Клиент")
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(5, weight=1)
        self.container.grid_columnconfigure(5, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.quit())

        self.frames = {}
        for nig in (StartPage, Launcher,  Game, Faq, TheEnd):
            page_name = nig.__name__
            frame = nig(parent=self.container, controller=self)
            self.frames[page_name] = frame

            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("StartPage")

    def quit_me(self):
        self.quit()
        self.destroy()

    def show_frame(self, page_name, switch=True):
        if page_name == "Launcher":
            self.refresh("Launcher", switch)
        frame = self.frames[page_name]
        frame.tkraise()

    def refresh(self, pageType, switch=True):
        self.frames[pageType].destroy()
        for v in (Launcher, Game):
            if v.__name__ == pageType:
                frame = v(controller=self, parent=self.container, switch=switch)
        self.frames[pageType] = frame
        frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("StartPage")

    def activateEnd(self, data):
        self.frames["Game"].client.close()
        self.refresh("Game")

        self.frames["TheEnd"].destroy()
        self.frames["TheEnd"] = TheEnd(controller=self, parent=self.container)

        self.frames["TheEnd"].tkDisplay.config(state=tk.NORMAL)
        for i in range(1, int(data[0]) + 1):
            self.frames["TheEnd"].tkDisplay.insert(tk.END, data[i])
        self.frames["TheEnd"].tkDisplay.config(state=tk.DISABLED)
        self.frames["TheEnd"].grid(row=0, column=0, sticky="nsew")
        self.show_frame("TheEnd")

class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        button1 = tk.Button(self, text="Начать игру", width=20,
                            command=lambda: self.controller.show_frame("Launcher"))
        button2 = tk.Button(self, text="Присоединиться", width=20,
                            command=lambda: self.controller.show_frame("Launcher", switch=False))
        button3 = tk.Button(self, text="Справка", width=20,
                            command=lambda: self.controller.show_frame("Faq"))

        button1.pack(padx=20, expand=1)
        button2.pack(padx=20, expand=1)
        button3.pack(padx=20, expand=1)

class Launcher(tk.Frame):
    def __init__(self, parent, controller, switch=True):
        if switch:
            suggestion = "Создать игру"
        else:
            suggestion = "Подключиться"

        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self, text="Введите идентификатор игры")
        label.pack(side="top", fill="x", pady=10)

        self.topFrame = tk.Frame(self)
        self.entName = tk.Entry(self.topFrame)
        self.entName.pack(side=tk.LEFT, padx=10)
        self.btnConnect = tk.Button(self.topFrame, text=suggestion, command=lambda: self.launch(switch))
        self.btnConnect.pack(side=tk.RIGHT, padx=10)
        self.topFrame.pack(side=tk.TOP)

        self.toMenu = tk.Button(self, text="Назад в меню", command=lambda: self.controller.show_frame("StartPage"))
        self.toMenu.pack(pady=20)

    def launch(self, switch):
        success = ClientBackend.connect(self.controller.frames["Game"], switch)
        if success:
            self.controller.show_frame("Game")
            self.entName.delete(0, tk.END)

class Game(tk.Frame):
    def __init__(self, parent, controller, switch=True):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.parent = parent

        self.message = ""
        self.client = None

        self.topFrame = tk.Frame(self)
        self.lblName = tk.Label(self.topFrame, text="Общий код", font=("Helvetica, 16"))
        self.lblName.pack(side=tk.LEFT, padx=20, pady=20, fill=tk.X)
        self.backToMenu = tk.Button(self.topFrame, text="Назад в меню",
                                    command=lambda: ClientBackend.send_message_to_server(self, "/exitgame", True))
        self.backToMenu.pack(side=tk.RIGHT, fill=tk.X)
        self.topFrame.pack(side=tk.TOP, expand = 1, fill=tk.X)

        self.displayFrame = tk.Frame(self)
        self.scrollBar = tk.Scrollbar(self.displayFrame)
        self.scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tkDisplay = tk.Text(self.displayFrame, height=20, width=55)
        self.tkDisplay.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
        self.tkDisplay.tag_config("tag_your_message", foreground="blue")
        self.tkDisplay.tag_config("system_info", foreground="green")
        self.scrollBar.config(command=self.tkDisplay.yview)
        self.tkDisplay.config(yscrollcommand=self.scrollBar.set, background="#F4F6F7", highlightbackground="grey",
                         state="disabled")
        self.displayFrame.pack(side=tk.TOP)

        self.controlFrame = tk.Frame(self)
        self.tkSend = tk.Button(self.controlFrame, text="Добавить", height=2, width=10,
                                   command=lambda: ClientBackend.getChatMessage(self, self.tkMessage.get("1.0", tk.END)))
        self.tkSend.pack(side=tk.LEFT, padx=5, pady=10)
        self.tkSend.config(state=tk.DISABLED)
        self.tkSkip = tk.Button(self.controlFrame, text="Пропуск\nхода", height=2, width=10,
                                command=lambda: ClientBackend.send_message_to_server(self, "/skipmove", True))
        self.tkSkip.pack(side=tk.LEFT, padx=5, pady=10)
        self.tkSkip.config(state=tk.DISABLED)
        self.tkStop = tk.Button(self.controlFrame, text="Конец игры", height=2, width=10,
                                command=lambda: ClientBackend.send_message_to_server(self, "/stopgame", True))
        self.tkStop.pack(side=tk.LEFT, padx=5, pady=10)
        self.tkStop.config(state=tk.DISABLED)
        self.controlFrame.pack(fill=tk.X)

        self.bottomFrame = tk.LabelFrame(self)
        self.tkMessage = tk.Text(self.bottomFrame, height=2, width=55)
        self.tkMessage.pack(side=tk.LEFT, padx=(5, 13), pady=(5, 10))
        self.tkMessage.config(highlightbackground="grey", state="disabled")
        self.bottomFrame.pack(side=tk.BOTTOM)

class Faq(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.displayFrame = tk.Frame(self)
        self.scrollBar = tk.Scrollbar(self.displayFrame)
        self.scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tkDisplay = tk.Text(self.displayFrame, height=20, width=55)
        self.tkDisplay.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
        self.scrollBar.config(command=self.tkDisplay.yview)
        self.tkDisplay.config(yscrollcommand=self.scrollBar.set, background="#F4F6F7",
                              highlightbackground="grey", state=tk.NORMAL)
        self.displayFrame.pack(side=tk.TOP)
        self.tkDisplay.insert(tk.END, "Обратитесь пожалуйста к документации")
        self.tkDisplay.config(state=tk.DISABLED)

        button = tk.Button(self, text="Назад в меню",
                           command=lambda: controller.show_frame("StartPage"))
        button.pack()

class TheEnd(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.header = tk.Label(self, text="Результаты", font=("Helvetica, 16"))
        self.header.pack(side=tk.TOP, padx=20, pady=20, fill=tk.X)

        self.displayFrame = tk.Frame(self)
        self.scrollBar = tk.Scrollbar(self.displayFrame)
        self.scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tkDisplay = tk.Text(self.displayFrame, height=20, width=55)
        self.tkDisplay.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
        self.scrollBar.config(command=self.tkDisplay.yview)
        self.tkDisplay.config(yscrollcommand=self.scrollBar.set, background="#F4F6F7",
                              highlightbackground="grey", state=tk.NORMAL)
        self.displayFrame.pack(side=tk.TOP)
        self.tkDisplay.config(state=tk.DISABLED)

        button = tk.Button(self, text="Назад в меню",
                           command=lambda: controller.show_frame("StartPage"))
        button.pack()

class ClientBackend:
    @staticmethod
    def connect(interface, switch):
        global HOST_ADDR, HOST_PORT
        if len(interface.controller.frames["Launcher"].entName.get()) < 1:
            tk.messagebox.showerror(title="Ошибка", message="Идентификатор должен быть введен.")
        else:
            unprocessedId = interface.controller.frames["Launcher"].entName.get()
            id = unprocessedId.split(':')
            if len(id) < 2 or not id[len(id) - 1].isnumeric():
                tk.messagebox.showerror(title="Ошибка", message="Некорректный идентификатор.")
            else:
                HOST_ADDR = unprocessedId[0:len(unprocessedId) - len(id[len(id) - 1]) - 1]
                HOST_PORT = int(id[len(id) - 1])
                return ClientBackend.connect_to_server(interface, switch)

    @staticmethod
    def connect_to_server(interface, switch):
        global HOST_ADDR, HOST_PORT
        try:
            interface.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            interface.client.settimeout(5)
            interface.client.connect((HOST_ADDR, HOST_PORT))
            interface.client.settimeout(None)
        except Exception as e:
            tk.messagebox.showerror(title="Ошибка",
                                    message="Не удается подключиться к серверу по идентификатору: " + HOST_ADDR + ":"
                                            + str(HOST_PORT) + " Сервер может быть недоступен. Попробуйте позже.")
            return False
        try:
            if switch:
                interface.client.send("/anewgame".encode())
                ClientBackend.receive_message_from_server(interface, interface.client, True)
            else:
                interface.client.send("/joingame".encode())
                ClientBackend.receive_message_from_server(interface, interface.client, True)
        except Exception as e:
            if switch:
                tk.messagebox.showerror(title="Ошибка",
                                        message="Не удается подключиться к серверу по идентификатору: " + HOST_ADDR + ":"
                                                + str(HOST_PORT) + " Игра уже запущена.")
            else:
                tk.messagebox.showerror(title="Ошибка",
                                        message="Не удается подключиться к серверу по идентификатору: " + HOST_ADDR + ":"
                                                + str(HOST_PORT) + " Игра не запущена.")
            return False

        threading._start_new_thread(ClientBackend.receive_message_from_server, (interface, interface.client))
        interface.tkMessage.config(state=tk.NORMAL)
        return True

    @staticmethod
    def receive_message_from_server(interface, sck, launching=False):
        while True:
            try:
                from_server = sck.recv(4096).decode()
            except Exception as e:
                tk.messagebox.showerror(title="Сообщение", message="Вы были отключены от сервера.")
                break
            if from_server == "":
                sck.close()
                raise Exception

            query, interface.message = ClientBackend.processData(from_server)
            isInfo = ClientBackend.switchQuery(interface, query)

            if launching:
                break
            interface.tkDisplay.config(state=tk.NORMAL)
            if isInfo:
                interface.tkDisplay.insert(tk.END, interface.message, "system_info")
            else:
                interface.tkDisplay.insert(tk.END, interface.message)
            interface.tkDisplay.config(state=tk.DISABLED)

        if not launching:
            interface.parent.master.refresh("Game")
            sck.close()

    @staticmethod
    def getChatMessage(interface, msg):
        if msg.isspace():
            tk.messagebox.showerror(title="Ошибка", message="Поле ввода не может быть пустым.")
            return

        forbidden = ["/exitgame", "/stopgame", "/skipmove", "/joingame", "/anewgame"]
        if forbidden.count(msg[0:9]):
            tk.messagebox.showerror(title="Ошибка", message="Запрещенная команда.")
            return

        interface.tkDisplay.config(state=tk.NORMAL)

        if interface.tkDisplay.compare('1.0', '==', tk.END):
            interface.tkDisplay.insert(tk.END, msg.strip("\n ") + '\n', "tag_your_message")
        else:
            interface.tkDisplay.insert(tk.END, msg.strip("\n ") + '\n', "tag_your_message")
        ClientBackend.send_message_to_server(interface, msg)

        interface.tkDisplay.config(state=tk.DISABLED)
        interface.tkSend.config(state=tk.DISABLED)
        interface.tkSkip.config(state=tk.DISABLED)
        interface.tkStop.config(state=tk.DISABLED)

    @staticmethod
    def send_message_to_server(interface, msg, switch=False):
        if switch:
            interface.client.send(msg.encode())
            ClientBackend.switchQuery(interface, msg)
        else:
            interface.client.send(("/execcode" + msg).encode())
            interface.tkMessage.delete('1.0', tk.END)

    @staticmethod
    def processData(msg):
        query = msg[0:9]
        if len(msg) > 9:
            data = msg[9:len(msg)]
        else:
            data = ""
        return query, data

    @staticmethod
    def switchQuery(interface, query):
        if query == "/exitgame":
            interface.client.close()
            interface.controller.refresh("Game")
        if query == "/skipmove":
            interface.tkDisplay.config(state=tk.NORMAL)
            interface.tkDisplay.insert(tk.END, "#Вы пропустили ход\n", "system_info")
            interface.tkDisplay.config(state=tk.DISABLED)
            interface.tkSend.config(state=tk.DISABLED)
            interface.tkSkip.config(state=tk.DISABLED)
            interface.tkStop.config(state=tk.DISABLED)
        if query == "/enddgame":
            interface.controller.activateEnd(interface.message.split('&'))
            sys.exit()
        if query == "/taketurn":
            interface.tkSend.config(state=tk.NORMAL)
            interface.tkSkip.config(state=tk.NORMAL)
            interface.tkStop.config(state=tk.NORMAL)
        if query == "/infohash":
            return True
        if query == "/countstr":
            ClientBackend.fillDisplay(interface)
            return True
        if query == "/sendinpt":
            interface.tkSend.config(state=tk.NORMAL)
            interface.tkSkip.config(state=tk.NORMAL)
            return True
        return False

    @staticmethod
    def fillDisplay(interface):
        ClientBackend.send_message_to_server(interface, "acquired", True)
        crutch = interface.client.recv(int(interface.message)).decode()
        interface.message = ""
        time.sleep(2)
        ClientBackend.send_message_to_server(interface, "acquired", True)
        interface.tkDisplay.config(state=tk.NORMAL)
        interface.tkDisplay.insert(tk.END, crutch, "system_info")
        interface.tkDisplay.config(state=tk.DISABLED)

app = ClientInterface()
app.mainloop()