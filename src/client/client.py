import threading
import argparse
import socket
import signal
import os
import io
from contextlib import redirect_stdout
from enum import Enum
from zeep import Client

from netools import recv_cstring
from server_svc import ServerThread

def download_range(ip, port, remote_filepath, seeder_id, total_seeders):
    """Descarga la porción asignada de un seeder y la guarda en un fichero temporal."""
    temp_filename = f"{seeder_id}.temp"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, int(port)))
        # Enviar comando GET_MULTIFILE
        s.sendall("GET_MULTIFILE\0".encode())
        s.sendall((remote_filepath + "\0").encode())
        # Envío de parámetros: seeder id y total de seeders
        s.sendall((str(seeder_id) + "\0").encode())
        s.sendall((str(total_seeders) + "\0").encode())

        # Esperamos confirmación del seeder (0 indica OK)
        response = int.from_bytes(s.recv(1), byteorder='big')
        if response != 0:
            s.close()
            return False

        # Descargamos hasta que se cierre la conexión
        with open(temp_filename, "wb") as ftemp:
            while True:
                chunk = s.recv(1024)
                if not chunk:
                    break
                ftemp.write(chunk)
        s.close()
        return True
    except Exception as e:
        return False


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
    _listen_thread: ServerThread = None
    _current_user_connected = None
    # El web service siempre se conecta al localhost
    _ws_client = Client(wsdl="http://127.0.0.1:8000/?wsdl")
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
            sck.sendall((client._ws_client.service.get_datetime("") + "\0").encode())
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
            sck.sendall((client._ws_client.service.get_datetime("") + "\0").encode())
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
            client._listen_thread = ServerThread()
            client._listen_thread.start()
            port = client._listen_thread.get_port()

            # AHORA ya podemos enviar cosas al servidor
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.connect((client._server, client._port))

            sck.sendall("CONNECT\0".encode())
            sck.sendall((client._ws_client.service.get_datetime("") + "\0").encode())
            username = user + "\0"
            sck.sendall(username.encode())
            listen_port = str(port) + "\0"
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
            if not success and client._listen_thread:
                client._listen_thread.kill()
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
            sck.sendall((client._ws_client.service.get_datetime("") + "\0").encode())
            username = user + "\0"
            sck.sendall(username.encode())

            # Una vez enviado el nombre de usuario, se espera la respuesta del servidor
            response = int.from_bytes(sck.recv(1), byteorder='big')
            if response == 0:
                sck.close()
                # y matamos al hilo
                if client._listen_thread:
                    client._listen_thread.kill()
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
            sck.sendall((client._ws_client.service.get_datetime("") + "\0").encode())
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
            sck.sendall((client._ws_client.service.get_datetime("") + "\0").encode())
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
            sck.sendall((client._ws_client.service.get_datetime("") + "\0").encode())
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
            sck.sendall((client._ws_client.service.get_datetime("") + "\0").encode())
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
        if client._current_user_connected is None:
            print("c> GET_FILE FAIL, USER NOT CONNECTED")
            return client.RC.USER_ERROR


        # El siguiente fragmento de código sirve para redirigir la salida estándar a un buffer
        # para capturar la salida de la funcón listusers(). De esta manera, no se visualiza por terminal
        with io.StringIO() as buf, redirect_stdout(buf):
            client.listusers()
            output = buf.getvalue()

        if "LIST_USERS OK" not in output:
            print("c> GET_FILE FAIL, LIST_USERS ERROR")
            return client.RC.ERROR

        # Ahora, obtenemos el puerto y la ip del cliente "user"
        lines = output.splitlines()
        for line in lines:
            parts = line.split()
            if parts[1] == user:
                ip = parts[2]
                port = int(parts[3])
                break
        else:
            print(f"c> GET_FILE FAIL, USER {user} NOT FOUND")
            return client.RC.USER_ERROR

        sck = None
        try:
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.connect((ip, port))
            sck.sendall("GET_FILE\0".encode())
            sck.sendall(remote_FileName.encode() + b"\0")

            response = int.from_bytes(sck.recv(1), byteorder='big')
            if response == 0:
                # Ahora, recibimos el fichero
                with open(local_FileName, 'wb') as f:
                    while True:
                        data = sck.recv(1)
                        if not data:
                            break
                        f.write(data)
                print("c> GET_FILE OK")
                sck.close()
                return client.RC.OK
            elif response == 1:
                print("c> GET_FILE FAIL, FILE DOES NOT EXIST")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 2:
                print("c> GET_FILE FAIL")
                sck.close()
                return client.RC.USER_ERROR
            else:
                print("c> UNKNOWN RESPONSE FROM SERVER:", response)
        except Exception as e:
            print("c> GET_FILE CLIENT ERROR -", str(e))
            return client.RC.ERROR
        finally:
            if sck:
                sck.close()

        return client.RC.ERROR

    @staticmethod
    def getmultifile(remote_FileName, local_FileName):
        """
        Esta función no está en el enunciado de la práctica. Se trata de recibir un fichero
        desde varios usuarios al mismo tiempo y guardarlo en el directorio local, desplegando un
        hilo por cada usuario.
        :param remote_FileName:
        :param local_FileName:
        :return:
        """
        if client._current_user_connected is None:
            print("c> GET_MULTIFILE FAIL, USER NOT CONNECTED")
            return client.RC.USER_ERROR

        sck = None
        try:
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.connect((client._server, client._port))
            sck.sendall("GET_MULTIFILE\0".encode())
            sck.sendall((client._ws_client.service.get_datetime("") + "\0").encode())
            username = client._current_user_connected + "\0"
            sck.sendall(username.encode())

            # Ahora enviamos el path
            remote_FileName = remote_FileName + "\0"
            sck.sendall(remote_FileName.encode())

            response = int.from_bytes(sck.recv(1), byteorder='big')
            if response == 0:
                # Primero recibimos el número de usuarios que tienen el fichero
                num_users = int.from_bytes(sck.recv(1), byteorder='big')

                print("recibido: ", num_users)
                # Por cada usuario, recibimos su ip y su puerto
                users = []
                for _ in range(num_users):
                    ip = recv_cstring(sck)
                    port = recv_cstring(sck)
                    file_path = recv_cstring(sck)
                    users.append((ip, port, file_path))

                # A partir de aquí, ya sabemos cuántos usuarios tienen el fichero y quiénes son exactamente
                # por lo que procederemos a decir a cada usuario qué parte del fichero nos tienen que enviar
                # para que lo ensamblemos según la porción que le corresponda a cada uno.
                threads = []
                # Lanzamos un hilo por cada seeder
                for seeder_id, (ip, port, file_path) in enumerate(users):
                    t = threading.Thread(target=download_range,
                                         args=(ip, port, file_path.strip("\0"), seeder_id, num_users))
                    threads.append(t)
                    t.start()

                for t in threads:
                    t.join()

                # Una vez descargados todos los fragmentos, concatenarlos en el fichero final.
                with open(local_FileName, "wb") as fout:
                    for seeder_id in range(num_users):
                        temp_filename = f"{seeder_id}.temp"
                        if os.path.exists(temp_filename):
                            with open(temp_filename, "rb") as fin:
                                fout.write(fin.read())
                            os.remove(temp_filename)
                        else:
                            print(f"Error: Fichero temporal '{temp_filename}' no encontrado.")
                            return client.RC.ERROR

                print(f"c> GET_MULTIFILE OK")

                return client.RC.OK
            elif response == 1:
                print("c> GET_MULTIFILE FAIL, NO USER CONNECTED HAVE FILE")
                sck.close()
                return client.RC.USER_ERROR
            elif response == 2:
                print("c> GET_MULTIFILE FAIL")
                sck.close()
                return client.RC.USER_ERROR
            else:
                print("c> UNKNOWN RESPONSE FROM SERVER:", response)
        except Exception as e:
            print("c> GET_MULTIFILE CLIENT ERROR -", str(e))
        finally:
            if sck:
                sck.close()

        return client.RC.ERROR

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

                    elif (line[0] == "GET_MULTIFILE"):
                        if (len(line) == 3):
                            client.getmultifile(line[1], line[2])
                        else:
                            print("Syntax error. Usage: GET_MULTIFILE <remote_fileName> <local_fileName>")

                    elif (line[0] == "QUIT"):
                        if (len(line) == 1):
                            break
                        else:
                            print("Syntax error. Use: QUIT")

                    elif (line[0] == "HELP"):
                        print("Commands:")
                        print("\tREGISTER <userName>")
                        print("\tUNREGISTER <userName>")
                        print("\tCONNECT <userName>")
                        print("\tDISCONNECT <userName>")
                        print("\tPUBLISH <fileName> <description>")
                        print("\tDELETE <fileName>")
                        print("\tLIST_USERS")
                        print("\tLIST_CONTENT <userName>")
                        print("\tGET_FILE <userName> <remote_fileName> <local_fileName>")
                        print("\tGET_MULTIFILE <remote_fileName> <local_fileName>")
                        print("\tQUIT")

                    elif (line[0] == "SET1"): # DEBUF. QUITAR MÁS ADELANTE
                        client.register("pepe")
                        client.connect("pepe")
                        client.publish("testo.txt", "test")
                    elif (line[0] == "SET2"): # DEBUF. QUITAR MÁS ADELANTE
                        client.register("popo")
                        client.connect("popo")
                        client.publish("testo.txt", "yo también lo tengo")
                        client.publish("client.py", "el código fuente")
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
