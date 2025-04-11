import threading
import argparse
import socket
import signal
import os
import io
from contextlib import redirect_stdout
from enum import Enum

from netools import recv_cstring


class client:
    # ******************** TYPES *********************

    # *

    # * @brief Return codes for the protocol methods

    class RC(Enum):
        OK = 0
        ERROR = 1
        USER_ERROR = 2

    # ****************** ATTRIBUTES ******************
    _server = None
    _port = -1
    _listen_thread = None
    _listen_port = None
    _listen_socket = None
    _current_user_connected = None
    # ******************** METHODS *******************

    @staticmethod
    def register(user):
        if len(user) < 0 or len(user) > 255:
            print("Error: Invalid username length")
            return client.RC.USER_ERROR

        sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sck.connect((client._server, client._port))

        try:
            sck.sendall("REGISTER\0".encode())
            username = user + "\0"
            sck.sendall(username.encode())

            # Una vez enviado el nombre de usuario, se espera la respuesta del servidor
            # Recibimos el primer byte de la respuesta, codificado en formato de red
            response = int.from_bytes(sck.recv(1), byteorder='big')
            if response == 0:
                print("c> REGISTER OK")
                sck.close()
                return client.RC.OK
            elif response == 1:
                print("c> USERNAME IN USE")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 2:
                print("c> REGISTER FAIL")
            else:
                print("UNKNOWN RESPONSE FROM SERVER: ", response)
        except Exception as e:
            print("c> REGISTER CLIENT ERROR - ", str(e))

        sck.close()
        return client.RC.ERROR
    @staticmethod
    def unregister(user):
        if len(user) < 0 or len(user) > 255:
            print("Error: Invalid username length")
            return client.RC.USER_ERROR

        sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sck.connect((client._server, client._port))

        try:
            sck.sendall("UNREGISTER\0".encode())
            username = user + "\0"
            sck.sendall(username.encode())

            # Una vez enviado el nombre de usuario, se espera la respuesta del servidor
            response = int.from_bytes(sck.recv(1), byteorder='big')
            if response == 0:
                if user == client._current_user_connected:
                    client._current_user_connected = None
                print("c> UNREGISTER OK")
                sck.close()
                return client.RC.OK
            elif response == 1:
                print("c> USER DOES NOT EXIST")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 2:
                print("c> UNREGISTER FAIL")
            else:
                print("c> UNKNOWN RESPONSE FROM SERVER: ", response)
        except Exception as e:
            print("c> UNREGISTER CLIENT ERROR - ", str(e))

        return client.RC.ERROR

    @staticmethod
    def connect(user):
        if len(user) < 0 or len(user) > 255:
            print("Error: Invalid username length")
            return client.RC.USER_ERROR

        sck = None
        success = False
        try:
            # Antes de mandar nada al servidor, vamos a crear el socket de escucha
            client._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client._listen_socket.bind(('', 0))  # Lo bindeamos al primer puerto que esté libre
            client._listen_socket.listen(10)

            # Obtenemos el puerto asignado
            client._listen_port = client._listen_socket.getsockname()[1]

            # Ahora que tenemos el socket de escucha, desplegamos el hilo que permitirá conexiones
            # entrantes de otros clientes
            client._listen_thread = threading.Thread(target=client._downloads_handler, daemon=True)
            client._listen_thread.start()

            # AHORA ya podemos enviar cosas al servidor
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.connect((client._server, client._port))

            sck.sendall("CONNECT\0".encode())
            username = user + "\0"
            sck.sendall(username.encode())
            listen_port = str(client._listen_port) + "\0"
            sck.sendall(listen_port.encode())

            response = int.from_bytes(sck.recv(1), byteorder='big')
            if response == 0:
                print("c> CONNECT OK")
                success = True
                client._current_user_connected = user
                sck.close()
                return client.RC.OK
            elif response == 1:
                print("c> CONNECT FAIL, USER DOES NOT EXIST")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 2:
                print("c> USER ALREADY CONNECTED")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 3:
                print("c> CONNECT FAIL")
                sck.close()
                return client.RC.ERROR
            else:
                print("c> UNKNOWN RESPONSE FROM SERVER: ", response)
        except Exception as e:
            print("c> CONNECT CLIENT ERROR - ", str(e))
        finally:
            if sck:
                sck.close()
            # Cerrar el socket de escucha si se produce un error
            if not success and client._listen_socket:
                client._listen_socket.close()
                client._listen_socket = None
                client._listen_port = None
                client._listen_thread = None

        return client.RC.ERROR

    @staticmethod
    def disconnect(user):
        if len(user) < 0 or len(user) > 255:
            print("Error: Invalid username length")
            return client.RC.USER_ERROR

        sck = None
        try:
            # Ahora, tenemos primero que mandar el mensaje al servidor. En caso de
            # que el servidor no esté disponible, no podremos cerrar el socket de escucha
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.connect((client._server, client._port))
            sck.sendall("DISCONNECT\0".encode())
            username = user + "\0"
            sck.sendall(username.encode())

            # Una vez enviado el nombre de usuario, se espera la respuesta del servidor
            response = int.from_bytes(sck.recv(1), byteorder='big')
            if response == 0:
                sck.close()

                # Si ha salido bien, ahora cerramos el socket de escucha
                if client._listen_socket:
                    client._listen_socket.close()
                    client._listen_socket = None
                    client._listen_port = None

                # y matamos al hilo
                if client._listen_thread:
                    client._listen_thread = None

                client._current_user_connected = None
                print("c> DISCONNECT OK")
                return client.RC.OK
            elif response == 1:
                print("c> DISCONNECT FAIL , USER DOES NOT EXIST")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 2:
                print("c> DISCONNECT FAIL , USER NOT CONNECTED")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 3:
                print("c> DISCONNECT FAIL")
                sck.close()
                return client.RC.ERROR
            else:
                print("c> UNKNOWN RESPONSE FROM SERVER: ", response)

        except Exception as e:
            print("c> DISCONNECT CLIENT ERROR - ", str(e))
        finally:
            if sck:
                sck.close()

        return client.RC.ERROR

    @staticmethod
    def publish(fileName, description):
        if len(fileName) < 0 or len(fileName) > 255:
            print("Error: Invalid filename length")
            return client.RC.USER_ERROR

        # Comprobamos que el path no tenga espacios en blanco
        if " " in fileName:
            print("Error: Invalid filename, blank spaces not allowed")
            return client.RC.USER_ERROR

        # Comprobamos que el fichero exista
        if not os.path.isfile(fileName):
            print("Error: File does not exist")
            return client.RC.USER_ERROR

        # Verificamos que el path sea absoluto y en caso de que no lo sea, lo convertimos
        if not os.path.isabs(fileName):
            fileName = os.path.abspath(fileName)
            if len(fileName) < 0 or len(fileName) > 255:
                print("Error: Invalid filename length while converting to absolute path")
                return client.RC.USER_ERROR

        if len(description) < 0 or len(description) > 255:
            print("Error: Invalid description length")
            return client.RC.USER_ERROR

        if client._current_user_connected is None:
            print("c> PUBLISH FAIL, USER NOT CONNECTED")
            return client.RC.USER_ERROR

        sck = None
        try:
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.connect((client._server, client._port))
            sck.sendall("PUBLISH\0".encode())
            username = client._current_user_connected + "\0"
            sck.sendall(username.encode())

            # Ahora enviamos el path
            fileName = fileName + "\0"
            sck.sendall(fileName.encode())
            # Y ahora la descripción
            description = description + "\0"
            sck.sendall(description.encode())

            response = int.from_bytes(sck.recv(1), byteorder='big')
            if response == 0:
                print("c> PUBLISH OK")
                sck.close()
                return client.RC.OK
            elif response == 1:
                print("c> PUBLISH FAIL, USER DOES NOT EXIST")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 2:
                print("c> PUBLISH FAIL, USER NOT CONNECTED")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 3:
                print("c> PUBLISH FAIL, CONTENT ALREADY PUBLISHED")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 4:
                print("c> PUBLISH FAIL")
                sck.close()
                return client.RC.USER_ERROR
            else:
                print("c> UNKNOWN RESPONSE FROM SERVER: ", response)
        except Exception as e:
            print("c> PUBLISH CLIENT ERROR - ", str(e))
        finally:
            if sck:
                sck.close()

        return client.RC.ERROR

    @staticmethod
    def delete(fileName):
        if len(fileName) < 0 or len(fileName) > 255:
            print("Error: Invalid filename length")
            return client.RC.USER_ERROR

        # Comprobamos que el path no tenga espacios en blanco
        if " " in fileName:
            print("Error: Invalid filename, blank spaces not allowed")
            return client.RC.USER_ERROR

        # Comprobamos que el fichero exista
        if not os.path.isfile(fileName):
            print("Error: File does not exist")
            return client.RC.USER_ERROR

        # Verificamos que el path sea absoluto y en caso de que no lo sea, lo convertimos
        if not os.path.isabs(fileName):
            fileName = os.path.abspath(fileName)
            if len(fileName) < 0 or len(fileName) > 255:
                print("Error: Invalid filename length while converting to absolute path")
                return client.RC.USER_ERROR

        if client._current_user_connected is None:
            print("c> DELETE FAIL, USER NOT CONNECTED")
            return client.RC.USER_ERROR

        sck = None
        try:
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.connect((client._server, client._port))
            sck.sendall("DELETE\0".encode())
            username = client._current_user_connected + "\0"
            sck.sendall(username.encode())

            # Ahora enviamos el path
            fileName = fileName + "\0"
            sck.sendall(fileName.encode())

            response = int.from_bytes(sck.recv(1), byteorder='big')
            if response == 0:
                print("c> DELETE OK")
                sck.close()
                return client.RC.OK
            elif response == 1:
                print("c> DELETE FAIL, USER DOES NOT EXIST")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 2:
                print("c> DELETE FAIL, USER NOT CONNECTED")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 3:
                print("c> DELETE FAIL, CONTENT NOT PUBLISHED")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 4:
                print("c> DELETE FAIL")
                sck.close()
                return client.RC.USER_ERROR
            else:
                print("c> UNKNOWN RESPONSE FROM SERVER: ", response)
        except Exception as e:
            print("c> DELETE CLIENT ERROR - ", str(e))
        finally:
            if sck:
                sck.close()

        return client.RC.ERROR

    @staticmethod
    def listusers():
        if client._current_user_connected is None:
            print("c> LIST_USERS FAIL, USER NOT CONNECTED")
            return client.RC.USER_ERROR

        sck = None
        try:
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.connect((client._server, client._port))
            sck.sendall("LIST_USERS\0".encode())
            username = client._current_user_connected + "\0"
            sck.sendall(username.encode())

            response = int.from_bytes(sck.recv(1), byteorder='big')
            if response == 0:
                # Éxito
                print("c> LIST_USERS OK")

                num_users_str = recv_cstring(sck)
                try:
                    num_users = int(num_users_str)
                except ValueError:
                    print("c> LIST_USERS CLIENT ERROR - invalid num_users: ", num_users_str)
                    return client.RC.ERROR

                # Leemos los datos de cada usuario: name, ip, port (3 C-strings por usuario)
                users = []
                for _ in range(num_users):
                    username = recv_cstring(sck)
                    ip_str = recv_cstring(sck)
                    port = recv_cstring(sck)
                    users.append((username, ip_str, port))

                max_user_len = max(len(u[0]) for u in users) if users else 0
                max_ip_len = max(len(u[1]) for u in users) if users else 0

                for i, (username, ip_str, port) in enumerate(users):
                    print(f"\tUSER{i}: {username.ljust(max_user_len)}\t{ip_str.ljust(max_ip_len)}\t{port}")
                return client.RC.OK

            elif response == 1:
                print("c> LIST_USERS FAIL, USER DOES NOT EXIST")
                return client.RC.USER_ERROR

            elif response == 2:
                print("c> LIST_USERS FAIL, USER NOT CONNECTED")
                return client.RC.USER_ERROR

            elif response == 3:
                print("c> LIST_USERS FAIL")
                return client.RC.USER_ERROR

            else:
                print("c> UNKNOWN RESPONSE FROM SERVER:", response)
                return client.RC.ERROR

        except Exception as e:
            print("c> LIST_USERS CLIENT ERROR -", str(e))
            return client.RC.ERROR
        finally:
            if sck:
                sck.close()

        return client.RC.ERROR

    @staticmethod
    def listcontent(user):
        if len(user) < 0 or len(user) > 255:
            print("Error: Invalid username length")
            return client.RC.USER_ERROR

        if client._current_user_connected is None:
            print("c> LIST_CONTENT FAIL, USER NOT CONNECTED")
            return client.RC.USER_ERROR

        sck = None
        try:
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.connect((client._server, client._port))
            sck.sendall("LIST_CONTENT\0".encode())
            username = client._current_user_connected + "\0"
            sck.sendall(username.encode())

            # Enviamos el nombre de usuario del que queremos listar el contenido
            username = user + "\0"
            sck.sendall(username.encode())

            response = int.from_bytes(sck.recv(1), byteorder='big')
            if response == 0:
                # Éxito
                print("c> LIST_CONTENT OK")

                num_files_str = recv_cstring(sck)
                try:
                    num_files = int(num_files_str)
                except ValueError:
                    print("c> LIST_CONTENT CLIENT ERROR - invalid num_files: ", num_files_str)
                    return client.RC.ERROR

                # Leemos los datos de cada fichero: name, description (2 C-strings por fichero)
                files = []
                for _ in range(num_files):
                    filename = recv_cstring(sck)
                    files.append(filename)

                max_file_len = max(len(f[0]) for f in files) if files else 0

                for i, filename in enumerate(files):
                    print(f"\tFILE{i}: {filename.ljust(max_file_len)}")
                return client.RC.OK

            elif response == 1:
                print("c> LIST_CONTENT FAIL, USER DOES NOT EXIST")
                return client.RC.USER_ERROR

            elif response == 2:
                print("c> LIST_CONTENT FAIL, USER NOT CONNECTED")
                return client.RC.USER_ERROR

            elif response == 3:
                print("c> LIST_CONTENT FAIL, REMOTE USER DOES NOT EXIST")
                return client.RC.USER_ERROR

            elif response == 4:
                print("c> LIST_CONTENT FAIL")
                return client.RC.USER_ERROR

            else:
                print("c> UNKNOWN RESPONSE FROM SERVER:", response)
                return client.RC.ERROR

        except Exception as e:
            print("c> LIST_CONTENT CLIENT ERROR -", str(e))
        finally:
            if sck:
                sck.close()

        return client.RC.ERROR

    @staticmethod
    def getfile(user, remote_FileName, local_FileName):

        #  Write your code here

        return client.RC.ERROR

    @staticmethod
    def _downloads_handler():
        """
        Hilo que escucha conexiones entrantes de otros clientes.
        """
        #print("[DOWNLOAD THREAD] Hilo de escucha iniciado.")
        while True:
            try:
                conn, addr = client._listen_socket.accept()
                print(f"[DOWNLOAD THREAD] Conexión entrante de {addr}")
                conn.close()
            except Exception as e: # Se produce cuando el socket de escucha se cierra
                break

        #print("[DOWNLOAD THREAD] Socket de escucha cerrado. Saliendo del hilo.")

    # *

    # **

    # * @brief Command interpreter for the client. It calls the protocol functions.

    @staticmethod
    def shell():

        while (True):

            try:

                command = input("c> ")

                line = command.split(" ")
                if (len(line) > 0):
                    line[0] = line[0].upper()
                    if (line[0] == "REGISTER"):
                        if (len(line) == 2):
                            client.register(line[1])
                        else:
                            print("Syntax error. Usage: REGISTER <userName>")

                    elif (line[0] == "UNREGISTER"):
                        if (len(line) == 2):
                            client.unregister(line[1])
                        else:
                            print("Syntax error. Usage: UNREGISTER <userName>")

                    elif (line[0] == "CONNECT"):
                        if (len(line) == 2):
                            client.connect(line[1])
                        else:
                            print("Syntax error. Usage: CONNECT <userName>")

                    elif (line[0] == "PUBLISH"):
                        if (len(line) >= 3):
                            #  Remove first two words
                            description = ' '.join(line[2:])
                            client.publish(line[1], description)
                        else:
                            print("Syntax error. Usage: PUBLISH <fileName> <description>")


                    elif (line[0] == "DELETE"):
                        if (len(line) == 2):
                            client.delete(line[1])
                        else:
                            print("Syntax error. Usage: DELETE <fileName>")

                    elif (line[0] == "LIST_USERS"):
                        if (len(line) == 1):
                            client.listusers()
                        else:
                            print("Syntax error. Use: LIST_USERS")

                    elif (line[0] == "LIST_CONTENT"):
                        if (len(line) == 2):
                            client.listcontent(line[1])
                        else:
                            print("Syntax error. Usage: LIST_CONTENT <userName>")



                    elif (line[0] == "DISCONNECT"):
                        if (len(line) == 2):
                            client.disconnect(line[1])
                        else:
                            print("Syntax error. Usage: DISCONNECT <userName>")



                    elif (line[0] == "GET_FILE"):
                        if (len(line) == 4):
                            client.getfile(line[1], line[2], line[3])
                        else:
                            print("Syntax error. Usage: GET_FILE <userName> <remote_fileName> <local_fileName>")



                    elif (line[0] == "QUIT"):
                        if (len(line) == 1):
                            break
                        else:
                            print("Syntax error. Use: QUIT")
                    else:
                        print("Error: command " + line[0] + " not valid.")

            except Exception as e:

                print("Exception: " + str(e))

    # *

    # * @brief Prints program usage

    @staticmethod
    def usage():

        print("Usage: python3 client.py -s <server> -p <port>")

    # *

    # * @brief Parses program execution arguments

    @staticmethod
    def parseArguments(argv):

        parser = argparse.ArgumentParser()

        parser.add_argument('-s', type=str, required=True, help='Server IP')

        parser.add_argument('-p', type=int, required=True, help='Server Port')

        args = parser.parse_args()

        if (args.s is None):
            parser.error("Usage: python3 client.py -s <server> -p <port>")

            return False

        if ((args.p < 1024) or (args.p > 65535)):
            parser.error("Error: Port must be in the range 1024 <= port <= 65535");

            return False;

        client._server = args.s

        client._port = args.p

        return True

    @staticmethod
    def handle_exit_signal(signum, frame):
        # Si el cliente estaba conectado y no se ha desconectado, lo hacemos
        # pero capturando la salida estándar para que no se vea en la consola
        if client._current_user_connected is not None:
            with io.StringIO() as buf, redirect_stdout(buf):
                client.disconnect(client._current_user_connected)
                output = buf.getvalue()
                if output:
                    print(output)
                else:
                    print("No output from disconnect command")
        print()
        print("+++ FINISHED +++")
        exit(0)

    # ******************** MAIN *********************

    @staticmethod
    def main(argv):

        if (not client.parseArguments(argv)):
            client.usage()

            return

        signal.signal(signal.SIGINT, client.handle_exit_signal)
        signal.signal(signal.SIGTERM, client.handle_exit_signal)

        client.shell()
        client.handle_exit_signal(None, None)



if __name__ == "__main__":
    client.main([])
