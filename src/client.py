from enum import Enum
import threading
import argparse
import socket


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
    # ******************** METHODS *******************

    @staticmethod
    def register(user: str):
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
            response = sck.recv(1).decode()
            if response == "0":
                print("c> REGISTER OK")
                sck.close()
                return client.RC.OK
            elif response == "1":
                print("c> USERNAME IN USE")
                sck.close()
                return client.RC.USER_ERROR
            elif response == "2":
                print("c> REGISTER FAIL")
            else:
                print("UNKNOWN RESPONSE FROM SERVER: ", response)
        except Exception as e:
            print("c> REGISTER FAIL")

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
            response = sck.recv(1).decode()
            if response == "0":
                print("c> UNREGISTER OK")
                sck.close()
                return client.RC.OK
            elif response == "1":
                print("c> USER DOES NOT EXIST")
                sck.close()
                return client.RC.USER_ERROR
            elif response == "2":
                print("c> UNREGISTER FAIL")
            else:
                print("c> UNKNOWN RESPONSE FROM SERVER: ", response)
        except Exception as e:
            print("c> UNREGISTER FAIL")

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

            res = sck.recv(1)
            if not res:
                print("c> CONNECT FAIL")
                sck.close()
                return client.RC.ERROR

            response = res.decode()
            if response == "0":
                print("c> CONNECT OK")
                success = True
                sck.close()
                return client.RC.OK
            elif response == "1":
                print("c> CONNECT FAIL, USER DOES NOT EXIST")
                sck.close()
                return client.RC.USER_ERROR
            elif response == "2":
                print("c> USER ALREADY CONNECTED")
                sck.close()
                return client.RC.USER_ERROR
            elif response == "3":
                print("c> CONNECT FAIL")
                sck.close()
                return client.RC.ERROR
            else:
                print("c> UNKNOWN RESPONSE FROM SERVER: ", response)
        except Exception as e:
            print("c> CONNECT FAIL")
        finally:
            if sck:
                sck.close()
            # Cerrar el socket de escucha si se produce un error
            if not success and client._listen_socket:
                client._listen_socket.close()
                client._listen_socket = None
                client._listen_port = None

        return client.RC.ERROR

    @staticmethod
    def disconnect(user):

        #  Write your code here

        return client.RC.ERROR

    @staticmethod
    def publish(fileName, description):

        #  Write your code here

        return client.RC.ERROR

    @staticmethod
    def delete(fileName):

        #  Write your code here

        return client.RC.ERROR

    @staticmethod
    def listusers():

        #  Write your code here

        return client.RC.ERROR

    @staticmethod
    def listcontent(user):

        #  Write your code here

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
        print("[DOWNLOAD THREAD] Hilo de escucha iniciado.")
        while True:
            try:
                conn, addr = client._listen_socket.accept()
                print(f"[DOWNLOAD THREAD] Conexión entrante de {addr}")
                conn.close()
            except Exception as e: # Se produce cuando el socket de escucha se cierra
                break

        print("[DOWNLOAD THREAD] Socket de escucha cerrado. Saliendo del hilo.")

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

    # ******************** MAIN *********************

    @staticmethod
    def main(argv):

        if (not client.parseArguments(argv)):
            client.usage()

            return

        #  Write code here

        client.shell()

        print("+++ FINISHED +++")


if __name__ == "__main__":
    client.main([])
