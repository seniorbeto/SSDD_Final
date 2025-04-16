import os.path
import threading
import socket

from netools import recv_cstring

class ServerThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(ServerThread, self).__init__(*args, **kwargs)
        self.__stop_event = threading.Event()
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.bind(('', 0))  # Lo bindeamos al primer puerto que esté libre
        self.__socket.listen(10)

        self._port = self.__socket.getsockname()[1]

    def run(self):
        while not self.__stop_event.is_set():
            """
            Aquí hay que tener cuidado ya que la función accept es bloqueante, lo que quiere decir 
            que como tratemos de matar al hilo, no se podrá cerrar el socket, ya que el hilo
            sigue esperando a que alguien se conecte. Por eso es necesario el timeout, para que haga otra
            iteración del bucle y así pueda salir del mismo.
            """
            self.__socket.settimeout(0.2)
            try:
                client, addr = self.__socket.accept()
                # Generamos un nuevo hilo detached para manejar la conexión
                client_thread = threading.Thread(target=self.handle_connection, args=(client,))
                client_thread.daemon = True
                client_thread.start()
            except socket.timeout:
                pass
            except OSError as e:
                pass
            except Exception as e:
                print(f"Error: {e}")
            finally:
                pass

    def get_port(self):
        return self._port

    def kill(self):
        self.__socket.close()
        self.__stop_event.set()
        self.join()

    def handle_connection(self, client):
        # Primero, tenemos que recibir la cadena GET_FILE
        operation = recv_cstring(client)
        file_path = recv_cstring(client)

        if operation != "GET_FILE":
            client.send(b'\x02')
            client.close()
            return

        # Comprobamos ahora si el fichero existe en nuesta máquina
        if not os.path.isfile(file_path):
            client.send(b'\x01')
            client.close()
            return

        # Si el fichero existe, lo enviamos al cliente
        client.send(b'\x00')
        try:
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(1)
                    if not data:
                        break
                    client.send(data)
        except Exception as e:
            client.send(b'\x02')
        finally:
            client.close()

