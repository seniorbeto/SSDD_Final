import os.path
import threading
import socket
import logging

from netools import recv_cstring

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename="server.log",
    filemode="w"
)

try:
    import miniupnpc
except ImportError:
    logging.warning("miniupnpc no está instalado. No se podrá realizar el port forwarding.")

class ServerThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(ServerThread, self).__init__(*args, **kwargs)
        self.__stop_event = threading.Event()
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.bind(('', 0))  # Lo bindeamos al primer puerto libre
        self.__socket.listen(10)
        self._port = self.__socket.getsockname()[1]
        logging.info(f"ServerThread inicializado en el puerto {self._port}")

        """
        El siguiente fragmento de código estará mejor explicado en la memoria del proyecto.
        Resumidamente, se intenta realizar un port forwarding mediante UPnP, ya que si no 
        se hace, el cliente no podrá conectarse al servidor si está detrás de un NAT.
        
        PARA QUE ESTO FUNCIONE, EL ROUTER DEBE TENER HABILITADO EL UPnP Y EL FIREWALL DEBE PERMITIR
        EL ACCESO AL PUERTO DEL SERVIDOR.
        """
        self.upnp = None
        try:
            self.upnp = miniupnpc.UPnP()
            self.upnp.discoverdelay = 200
            ndevices = self.upnp.discover()
            logging.info(f"Dispositivos UPnP encontrados: {ndevices}")
            self.upnp.selectigd()  # Seleccionar el router
            external_ip = self.upnp.externalipaddress()
            logging.info(f"IP externa detectada: {external_ip}")
            # Se intenta crear el mapeo: usamos el mismo puerto para la conexión interna y externa
            success = self.upnp.addportmapping(
                self._port,         # Puerto externo
                'TCP',                      # Protocolo
                self.upnp.lanaddr,          # IP interna
                self._port,                 # Puerto interno
                'ServerThread mapping',  # Descripción
                ''
            )
            if success:
                logging.info(f"Mapping UPnP exitoso: {external_ip}:{self._port} => {self.upnp.lanaddr}:{self._port}")
            else:
                logging.warning("Error: el mapeo UPnP no se ha podido establecer.")
        except Exception as e:
            logging.exception("Error en configuración UPnP:")

    def run(self):
        logging.info("ServerThread iniciado, esperando conexiones.")
        while not self.__stop_event.is_set():
            # Establecemos un timeout para evitar bloqueos indefinidos en accept()
            self.__socket.settimeout(0.2)
            try:
                client, addr = self.__socket.accept()
                logging.info(f"Conexión aceptada de {addr}")
                # Creamos un nuevo hilo para manejar la conexión
                client_thread = threading.Thread(target=self.handle_connection, args=(client,))
                client_thread.daemon = True
                client_thread.start()
            except socket.timeout:
                # Timeout: no hay conexiones, continuamos comprobando el evento de parada
                continue
            except OSError as e:
                # OSError: es probable que se deba al cierre del socket
                logging.debug(f"OSError en accept: {e}")
                break
            except Exception as e:
                logging.exception("Error inesperado en accept:")
            finally:
                pass
        logging.info("ServerThread finalizado.")

    def get_port(self):
        return self._port

    def kill(self):
        logging.info("Se solicita cerrar ServerThread...")
        if self.upnp:
            try:
                removed = self.upnp.deleteportmapping(self._port, 'TCP')
                if removed:
                    logging.info(f"Mapping UPnP eliminado: puerto {self._port}")
                else:
                    logging.warning(f"No se pudo eliminar el mapping UPnP en el puerto {self._port}")
            except Exception as e:
                logging.exception("Error al eliminar mapping UPnP:")
        self.__socket.close()
        self.__stop_event.set()
        self.join()
        logging.info("ServerThread cerrado correctamente.")

    def handle_connection(self, client):
        try:
            # Primero recibimos la operación y la ruta del fichero
            operation = recv_cstring(client)
            file_path = recv_cstring(client)
            logging.info(f"Solicitud: {operation} para el fichero {file_path}")
        except Exception as e:
            logging.exception("Error al recibir datos de la conexión")
            client.close()
            return

        # Verificamos que la operación sea "GET_FILE"
        if operation != "GET_FILE" and operation != "GET_MULTIFILE":
            client.send(b'\x02')
            client.close()
            logging.warning("Operación no válida recibida. Se cierra la conexión.")
            return

        # Comprobamos si el fichero existe en la máquina local
        if not os.path.isfile(file_path):
            client.send(b'\x01')
            client.close()
            logging.warning(f"Archivo no encontrado: {file_path}")
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
                logging.info(f"Archivo enviado correctamente: {file_path}")
            except Exception as e:
                client.send(b'\x02')
                logging.exception("Error durante el envío del archivo:")
            finally:
                client.close()
                logging.info("Conexión cerrada tras manejo de solicitud.")

        elif operation == "GET_MULTIFILE":
            try:
                # Recibir seeder id y total de seeders (Necesario para saber qué fragmento del fichero tenemos que
                # enviar)
                seeder_id_str = recv_cstring(client)
                total_seeders_str = recv_cstring(client)
                seeder_id = int(seeder_id_str)
                total_seeders = int(total_seeders_str)
                logging.info(f"GET_MULTIFILE: seeder_id={seeder_id}, total_seeders={total_seeders}")
            except Exception as e:
                logging.exception("Error al recibir parámetros de GET_MULTIFILE")
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
                logging.info(f"Envío completado de la porción del fichero {file_path} (offset: {offset}, longitud: {length})")
            except Exception as e:
                client.send(b'\x02')
                logging.exception("Error durante el envío del fragmento:")
            finally:
                client.close()
                logging.info("Conexión cerrada tras manejo de GET_MULTIFILE.")
