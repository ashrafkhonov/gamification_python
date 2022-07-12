
import tkinter as tk
import socket
import threading
import os
import time
import sys
import subprocess

HOST_ADDR = "localhost"
HOST_PORT = int(os.environ.get("PORT", 8989))

class ServerInterface(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.server = None
        self.container = tk.Frame(self)
        self.resizable(width=False, height=False)
        self.title(string="Состояние сервера")
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(5, weight=1)
        self.container.grid_columnconfigure(5, weight=1)
        self.mainframe = MainFrame(controller=self, parent=self.container)
        self.mainframe.grid(row=0, column=0, sticky="nsew")
        self.protocol("WM_DELETE_WINDOW", self.serverQuit())

        ServerBackend.start_server(self.mainframe)
        self.mainframe.tkraise()

    def serverQuit(self):
        if self.server != None:
            self.server.shutdown(socket.SHUT_RDWR)
            self.server.close()

    def refresh(self):
        for crutch, client in self.mainframe.clients.items():
            client.connection.close()
        self.mainframe.clients = {}
        self.mainframe.storage = ""
        self.mainframe.storedInput = ""
        self.mainframe.destroy()
        self.mainframe = MainFrame(controller=self, parent=self.container)
        self.mainframe.grid(row=0, column=0, sticky="nsew")

class MainFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.clients = {}
        self.storage = ""
        self.storedInput = ""

        self.headerFrame = tk.Frame(self)
        self.header = tk.Label(self.headerFrame, text="Игроки", font=("Helvetica, 16"))
        self.header.pack(side=tk.LEFT, pady=10)
        self.headerFrame.pack(side=tk.TOP, fill=tk.X)

        self.infoFrame = tk.Frame(self)
        self.scrollBar = tk.Scrollbar(self.infoFrame)
        self.scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tkDisplay = tk.Text(self.infoFrame, height=15, width=45)
        self.tkDisplay.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
        self.scrollBar.config(command=self.tkDisplay.yview)
        self.tkDisplay.config(yscrollcommand=self.scrollBar.set, background="#F4F6F7", highlightbackground="grey",
                         state="disabled")
        self.infoFrame.pack(side=tk.TOP, pady=(5, 10))

        self.idFrame = tk.Frame(self)
        self.premise = tk.Label(self.idFrame,
                                   text="Идентификатор сервера: ")
        self.premise.pack(side=tk.LEFT, pady=30, fill=tk.X)
        self.identifier = tk.Label(self.idFrame, foreground="blue",
                                   text=HOST_ADDR + ':' + str(HOST_PORT))
        self.identifier.pack(side=tk.LEFT, pady=30, fill=tk.X)
        self.idFrame.pack(side=tk.TOP)

    def update_client_names_display(self):
        self.tkDisplay.config(state=tk.NORMAL)
        self.tkDisplay.delete('1.0', tk.END)

        for c in self.clients.keys():
            self.tkDisplay.insert(tk.END, c + "\n")
        self.tkDisplay.config(state=tk.DISABLED)

class Client:
    def __init__(self, connection, score=0):
        self.connection = connection
        self.score = score

class ServerBackend:
    @staticmethod
    def start_server(interface):
        global HOST_ADDR, HOST_PORT

        interface.controller.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        interface.controller.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        interface.controller.server.bind((HOST_ADDR, HOST_PORT))
        interface.controller.server.listen(10)
        threading._start_new_thread(ServerBackend.accept_clients, (interface, ""))

    @staticmethod
    def accept_clients(interface, crutch):
        clientCount = 0
        while len(interface.clients) > -1:
            client, addr = interface.controller.server.accept()
            clientCount += 1

            doRun = ServerBackend.addClient(interface.controller.mainframe, client, "Player"+str(clientCount))
            if len(interface.controller.mainframe.clients) == 1 and doRun:
                time.sleep(1)
                threading._start_new_thread(ServerBackend.takeTurns,
                                            (interface.controller.mainframe, ""))
            if not doRun:
                client.close()

    @staticmethod
    def addClient(interface, client_connection, client_name):
        request = client_connection.recv(4096).decode()
        determinant, crutch = ServerBackend.switchQuery(interface, Client(client_connection, 0), request)

        if determinant:
            interface.clients[client_name] = Client(client_connection, 0)
            interface.update_client_names_display()

            client_connection.send(("/countstr" + str(len(interface.storage))).encode())
            time.sleep(1)
            client_connection.recv(4096)
            time.sleep(1)
            client_connection.send(interface.storage.encode())
            time.sleep(1)
            client_connection.recv(4096)
            return True
        else:
            client_connection.send("".encode())
            client_connection.shutdown(socket.SHUT_RDWR)
            client_connection.close()
            return False

    @staticmethod
    def send_receive_client_message(interface, client_name, client_connection):
        try:
            container = client_connection.connection.recv(4096).decode()
        except Exception as e:
            ServerBackend.removeClient(interface.controller, client_name)
        if container == "":
            client_connection.connection.close()
            raise ConnectionRefusedError('Something wrong...')
        query, client_msg, clientScore = ServerBackend.processData(container)
        interface.storage += client_msg

        sendMsg, response = ServerBackend.switchQuery(interface, client_name, query)

        if sendMsg:
            for cKey, cVal in interface.clients.items():
                    if cVal != client_connection:
                        try:
                            cVal.connection.send(("/showcode" + client_msg).encode())
                        except Exception as e:
                            mistake = "mist"
            ServerBackend.processCode(interface, client_name)
            client_connection.score += clientScore
        else:
            for cKey, cVal in interface.clients.items():
                if cVal != client_connection:
                    try:
                        cVal.connection.send(("/infohash" + response).encode())
                    except Exception as e:
                        mistake = "mist"

    @staticmethod
    def switchQuery(interface, client, query):
        if query == "/exitgame":
            threading._start_new_thread(ServerBackend.removeClient, (interface.controller, client))
            return False, "#Один из игроков покинул игру\n"
        if query == "/skipmove":
            return False, "#Игрок пропустил ход\n"
        if query == "/stopgame":
            ServerBackend.endGame(interface)
        if query == "/anewgame":
            if(len(interface.clients) == 0):
                return True, ""
            else:
                return False, ""
        if query == "/joingame":
            if (len(interface.clients) == 0):
                return False, ""
            else:
                return True, ""
        return True, ""

    @staticmethod
    def processCode(interface, client_name):
        interface.clients[client_name].connection.send("/sendinpt#Определите ввод для своих строк кода, или нажмите на \"Пропуск хода\"\n".encode())
        container = interface.clients[client_name].connection.recv(4096).decode()
        query, data, crutch = ServerBackend.processData(container)
        sendMsg, response = ServerBackend.switchQuery(interface, client_name, query)

        interface.storedInput += data
        try:
            result = subprocess.run([sys.executable, "-c", interface.storage],
                                    capture_output=True, text=True, timeout=5, input=interface.storedInput)
        except Exception as e:
            ServerBackend.endGame(interface, client_name
                                  + " допустил ошибку: " + str(e))
        if result.stderr != "":
            ServerBackend.endGame(interface, client_name
                                  + " допустил ошибку: " + result.stderr)

    @staticmethod
    def endGame(interface, fault = ""):
        for cName, cVal in interface.clients.items():
            if fault != "":
                result = "/enddgame" + str(len(interface.clients) + 1) + '&' + fault
            else:
                result = "/enddgame" + str(len(interface.clients))
            for cName2, cVal2 in interface.clients.items():
                if cName != cName2:
                    result += "&\n" + cName2 + " - строчек кода: " + str(cVal2.score)
                else:
                    result += "&\nВы(" + cName + ") - строчек кода: " + str(cVal2.score)
            cVal.connection.send(result.encode())
        interface.controller.refresh()

    @staticmethod
    def removeClient(interface, client_name):
        if len(interface.mainframe.clients) == 0 and interface.mainframe.storage != "":
            interface.refresh()
            return
        interface.mainframe.clients[client_name].connection.close()
        del interface.mainframe.clients[client_name]
        interface.mainframe.update_client_names_display()

    @staticmethod
    def processData(msg):
        query = msg[0:9]
        if len(msg) > 9:
            data = msg[9: len(msg)].strip("\n ")
            return query, data + '\n', data.count('\n') + 1
        else:
            data = ""
            return query, data, 0

    @staticmethod
    def takeTurns(interface, crutch):
        log = ""
        while len(interface.clients) >= 1:
            try:
                for cName, cVal in interface.clients.items():
                    log = cName
                    cVal.connection.send(("/taketurn").encode())
                    ServerBackend.send_receive_client_message(interface, cName, cVal)
                    time.sleep(1)
            except Exception as e:
                if str(e.__str__()) != "dictionary changed size during iteration" \
                        and str(e.__str__()) != "dictionary keys changed during iteration":
                     ServerBackend.removeClient(interface.controller, log)
                continue
        interface.controller.refresh()

app = ServerInterface()
app.mainloop()