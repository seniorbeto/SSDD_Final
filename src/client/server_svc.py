import os.path
import threading
import socket

from netools import recv_cstring


class ServerThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(ServerThread, self).__init__(*args, **kwargs)
        self.__stop_event = threading.Event()
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.bind(('', 0))  # Lo bindeamos al primer puerto libre
        self.__socket.listen(10)
        # Establecemos un timeout para evitar bloqueos indefinidos en accept()
        self.__socket.settimeout(0.2)
        self._port = self.__socket.getsockname()[1]

    def run(self):
        while not self.__stop_event.is_set():
            try:
                client, addr = self.__socket.accept()
                # Creamos un nuevo hilo para manejar la conexión
                client_thread = threading.Thread(target=self.handle_connection, args=(client,))
                client_thread.daemon = True
                client_thread.start()
            except socket.timeout:
                # Timeout: no hay conexiones, continuamos comprobando el evento de parada
                continue
            except OSError as e:
                # OSError: es probable que se deba al cierre del socket
                break
            except Exception as e:
                pass
            finally:
                pass

    def get_port(self):
        return self._port

    def kill(self):
        self.__socket.close()
        self.__stop_event.set()
        self.join()

    def handle_connection(self, client):
        try:
            # Primero recibimos la operación y la ruta del fichero
            operation = recv_cstring(client)
            file_path = recv_cstring(client)
        except Exception as e:
            client.close()
            return

        # Verificamos que la operación sea "GET_FILE"
        if operation != "GET_FILE" and operation != "GET_MULTIFILE":
            client.send(b'\x02')
            client.close()
            return

        # Comprobamos si el fichero existe en la máquina local
        if not os.path.isfile(file_path):
            client.send(b'\x01')
            client.close()
            return

        # Si el fichero existe, lo enviamos al cliente
        if operation == "GET_FILE":
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

        elif operation == "GET_MULTIFILE":
            try:
                # Recibir seeder id y total de seeders (Necesario para saber qué fragmento del fichero tenemos que
                # enviar)
                seeder_id_str = recv_cstring(client)
                total_seeders_str = recv_cstring(client)
                seeder_id = int(seeder_id_str)
                total_seeders = int(total_seeders_str)
            except Exception as e:
                client.send(b'\x02')
                client.close()
                return

            # Obtener el tamaño total del fichero
            file_size = os.path.getsize(file_path)
            part_size = file_size // total_seeders
            offset = seeder_id * part_size
            if seeder_id == total_seeders - 1:
                length = file_size - offset  # El último seeder toma el resto
            else:
                length = part_size

            # Enviar confirmación
            client.send(b'\x00')
            try:
                with open(file_path, "rb") as f:
                    f.seek(offset)
                    bytes_sent = 0
                    while bytes_sent < length:
                        chunk = f.read(min(1024, length - bytes_sent))
                        if not chunk:
                            break
                        client.send(chunk)
                        bytes_sent += len(chunk)
            except Exception as e:
                client.send(b'\x02')
            finally:
                client.close()
