#include <arpa/inet.h>
#include <errno.h>
#include <pthread.h>
#include <rpc/rpc.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "../logger/logger.h"
#include "claves.h"
#include "lines.h"
#include "stdbool.h"

#define MAX_MSG_SIZE 2048
#define MAX_DATETIME_SIZE 64
#define MAX_OP_MSG_SIZE 64
#define MAX_USER_MSG_SIZE 255
#define MAX_FILE_PATH_SIZE 256
#define MAX_FILE_DESC_SIZE 256

pthread_mutex_t req_lock = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t req_cond = PTHREAD_COND_INITIALIZER;
bool req_ready = false;

// Variables globales
int server_sock;
user_t *usuarios = NULL;
CLIENT *clnt = NULL;

// Cabeceras
void handle_register(int socket, char *user, char *datetime);
void handle_unregister(int socket, char *user, char *datetime);
void handle_connect(int socket, char *user, char *datetime);
void handle_disconnect(int socket, char *user, char *datetime);
void handle_publish(int socket, char *user, char *datetime);
void handle_delete(int socket, char *user, char *datetime);
void handle_list_users(int socket, char *user, char *datetime);
void handle_list_files(int socket, char *user, char *datetime);
// Funciones Extra
void handle_getmultifile(int socket, char *user, char *datetime);

void handle_poweroff() {
  close(server_sock);
  destroy(&usuarios);
  printf("\nSaliendo del servidor...\n");
  exit(EXIT_SUCCESS);
}

/*
 * Función auxiliar para enviar un valor entero al cliente en formato ascii + \0
 */
int send_ret_value(int socket, uint8_t ret) {
  // NO HACE FALTA TRANSFORMAR EL VALOR A FORMATO DE RED PORQUE, AL SER UN ÚNICO BYTE,
  // NO HAY PROBLEMAS DE ENDIANESS
  ssize_t bytes_sent = send_message(socket, (char *) &ret, sizeof(ret));
  if (bytes_sent < 0) {
    return -1;
  }
  return 0;
}

/*
 * Función auxiliar que compara si la terminación del path de dos ficheros es igual
 */
bool is_same_file(const char *file1, const char *file2) {
  // Buscar la última ocurrencia de '/' y '\' en file1
  const char *slash1 = strrchr(file1, '/');
  const char *backslash1 = strrchr(file1, '\\');
  const char *name1 = file1;

  if (slash1 && backslash1)
    name1 = (slash1 > backslash1) ? slash1 + 1 : backslash1 + 1;
  else if (slash1)
    name1 = slash1 + 1;
  else if (backslash1)
    name1 = backslash1 + 1;

  // Repetir para file2
  const char *slash2 = strrchr(file2, '/');
  const char *backslash2 = strrchr(file2, '\\');
  const char *name2 = file2;

  if (slash2 && backslash2)
    name2 = (slash2 > backslash2) ? slash2 + 1 : backslash2 + 1;
  else if (slash2)
    name2 = slash2 + 1;
  else if (backslash2)
    name2 = backslash2 + 1;

  return strcmp(name1, name2) == 0;
}

int get_ip_address(char *ip) {
  char *ip_local = getenv("LOG_RPC_IP");
  if (!ip_local) {
    return -1;
  }
  strcpy(ip, ip_local);
  return 0;
}

/*
 * Función auxiliar que crea un cliente RPC para el logger
 */
static CLIENT *get_rpc_client() {
  char rpc_server_ip[16] = {0};
  if (get_ip_address(rpc_server_ip) != 0) {
    fprintf(stderr, "s> error getting RPC server IP from env variable\n");
    return NULL;
  }
  CLIENT *client = clnt_create(rpc_server_ip, LOGGER_PROG, LOGGER_VERS, "udp");
  if (client == NULL) {
    clnt_pcreateerror(rpc_server_ip);
    return NULL;
  }
  return client;
}

/*
 * Función auxiliar que loggea la operación
 */
int log_operation(char *user, char *operation, char *datetime, char *filename) {
  if (clnt == NULL) {
    clnt = get_rpc_client();
    if (clnt == NULL) {
      return -1;
    }
  }

  log_entry entry;
  entry.username = user;
  entry.operation = operation;
  entry.timestamp = datetime;

  if (filename != NULL) {
    entry.filename = filename;
  } else {
    entry.filename = "";
  }

  // Llamada RPC
  if (log_op_1(&entry, clnt) == NULL) {
    clnt_perror(clnt, "s> error calling RPC. Try again.");
    clnt_destroy(clnt);
    clnt = NULL;
    return -1;
  }
  return 0;
}

void handle_register(int socket, char *user, char *datetime) {
  // En la operación register, solo hace falta el código de operación y el nombre de usuario
  int res = add_user(&usuarios, user);
  if (send_ret_value(socket, (uint8_t) res) != 0) {
    printf("s> error sending return value to %s", user);
  }
  if (log_operation(user, "REGISTER", datetime, NULL) != 0) {
    printf("s> error logging operation\n");
  }
}

void handle_unregister(int socket, char *user, char *datetime) {
  // En la operación unregister, solo hace falta el código de operación y el nombre de usuario
  int res = remove_user(&usuarios, user);
  if (send_ret_value(socket, (uint8_t) res) != 0) {
    printf("s> error sending return value to %s", user);
  }
  if (log_operation(user, "UNREGISTER", datetime, NULL) != 0) {
    printf("s> error logging operation\n");
  }
}

void handle_connect(int socket, char *user, char *datetime) {
  // En este caso, todavía nos falta por llegar el puerto del cliente
  char port_str[16] = {0};
  ssize_t bytes_read = read_line(socket, port_str, sizeof(port_str));
  port_str[sizeof(port_str) - 1] = '\0';
  if (bytes_read <= 0) {
    perror("s> error reading port");
    close(socket);
    return;
  }
  int port = atoi(port_str);
  if (port < 1024 || port > 65535) {
    perror("s> invalid port");
    close(socket);
    return;
  }
  // Ahora, obtenemos la dirección IP del cliente
  struct sockaddr_in client_addr;
  socklen_t client_addr_len = sizeof(client_addr);
  if (getpeername(socket, (struct sockaddr *) &client_addr, &client_addr_len) == -1) {
    perror("s> error getting client address");
    close(socket);
    return;
  }

  int res = connect_user(&usuarios, user, inet_ntoa(client_addr.sin_addr), port);
  if (send_ret_value(socket, (uint8_t) res) != 0) {
    printf("s> error sending return value to %s", user);
  }
  if (log_operation(user, "CONNECT", datetime, NULL) != 0) {
    printf("s> error logging operation\n");
  }
}

void handle_disconnect(int socket, char *user, char *datetime) {
  // En la operación disconnect, solo hace falta el código de operación y el nombre de usuario
  int res = disconnect_user(&usuarios, user);
  if (send_ret_value(socket, (uint8_t) res) != 0) {
    printf("s> error sending return value to %s", user);
  }
  if (log_operation(user, "DISCONNECT", datetime, NULL) != 0) {
    printf("s> error logging operation\n");
  }
}

void handle_publish(int socket, char *user, char *datetime) {
  // Aquí, todavía nos falta por llegar la ruta del fichero y su descripcción,
  // ambos valores como más de 256 caracteres
  char file_path[MAX_FILE_PATH_SIZE] = {0};
  ssize_t bytes_read = read_line(socket, file_path, sizeof(file_path));
  file_path[sizeof(file_path) - 1] = '\0'; // Por si acaso
  if (bytes_read <= 0) {
    perror("s> error reading file path");
    close(socket);
    return;
  }

  char file_desc[MAX_FILE_DESC_SIZE] = {0};
  bytes_read = read_line(socket, file_desc, sizeof(file_desc));
  file_desc[sizeof(file_desc) - 1] = '\0'; // Por si acaso
  if (bytes_read <= 0) {
    perror("s> error reading file description");
    close(socket);
    return;
  }

  int res = add_file(&usuarios, user, file_path, file_desc);
  if (send_ret_value(socket, (uint8_t) res) != 0) {
    printf("s> error sending return value to %s", user);
  }
  if (log_operation(user, "PUBLISH", datetime, file_path) != 0) {
    printf("s> error logging operation\n");
  }
}

void handle_delete(int socket, char *user, char *datetime) {
  char file_path[MAX_FILE_PATH_SIZE] = {0};
  ssize_t bytes_read = read_line(socket, file_path, sizeof(file_path));
  file_path[sizeof(file_path) - 1] = '\0'; // Por si acaso
  if (bytes_read <= 0) {
    perror("s> error reading file path");
    close(socket);
    return;
  }

  int res = remove_file(&usuarios, user, file_path);
  if (send_ret_value(socket, (uint8_t) res) != 0) {
    printf("s> error sending return value to %s", user);
  }
  if (log_operation(user, "DELETE", datetime, file_path) != 0) {
    printf("s> error logging operation\n");
  }
}

void handle_list_users(int socket, char *user, char *datetime) {
  connected_user_t *conn_users = NULL;
  uint32_t num_users = 0;

  int res = get_connected_users(&usuarios, user, &conn_users, &num_users);
  if (send_ret_value(socket, (uint8_t) res) != 0) {
    printf("s> error sending return value to %s\n", user);
    return;
  }

  if (res == 0) {
    char buffer[32] = {0};
    snprintf(buffer, sizeof(buffer), "%u", num_users);
    /*
     * Es importante especificar el tamaño del buffer, ya que el buffer es más
     * grande que el tamaño del mensaje a enviar. Si no se especifica el tamaño,
     * el mensaje se enviará completo, incluyendo toda la basura residua en el buffer.
     */
    size_t len = strlen(buffer) + 1;
    if (send_message(socket, buffer, len) != 0) {
      free(conn_users);
      return;
    }

    for (uint32_t i = 0; i < num_users; i++) {
      len = strnlen(conn_users[i].name, sizeof(conn_users[i].name)) + 1;
      if (send_message(socket, conn_users[i].name, len) != 0) {
        free(conn_users);
        return;
      }
      len = strnlen(conn_users[i].ip, sizeof(conn_users[i].ip)) + 1;
      if (send_message(socket, conn_users[i].ip, len) != 0) {
        free(conn_users);
        return;
      }
      snprintf(buffer, sizeof(buffer), "%u", conn_users[i].port);
      len = strlen(buffer) + 1;
      if (send_message(socket, buffer, len) != 0) {
        free(conn_users);
        return;
      }
    }
  }
  free(conn_users);
  if (log_operation(user, "LIST_USERS", datetime, NULL) != 0) {
    printf("s> error logging operation\n");
  }
}

void handle_list_files(int socket, char *user, char *datetime) {
  char other[MAX_USER_MSG_SIZE];
  memset(other, 0, MAX_USER_MSG_SIZE);
  ssize_t bytes_read = read_line(socket, other, sizeof(other));
  other[sizeof(other) - 1] = '\0';
  if (bytes_read <= 0) {
    perror("s> error reading other user");
    close(socket);
    return;
  }

  file_t *files = NULL;
  uint32_t num_files = 0;
  int res = get_user_files(&usuarios, user, other, &files, &num_files);
  if (send_ret_value(socket, (uint8_t) res) != 0) {
    printf("s> error sending return value to %s\n", user);
    close(socket);
    free(files);
    return;
  }

  if (res == 0) {
    char buffer[32] = {0};
    snprintf(buffer, sizeof(buffer), "%u", num_files);
    size_t len = strlen(buffer) + 1;
    if (send_message(socket, buffer, len) != 0) {
      free(files);
      close(socket);
      return;
    }

    for (uint32_t i = 0; i < num_files; i++) {
      len = strnlen(files[i].path, sizeof(files[i].path)) + 1;
      if (send_message(socket, files[i].path, len) != 0) {
        free(files);
        close(socket);
        return;
      }
    }
  }
  free(files);
  if (log_operation(user, "LIST_CONTENT", datetime, other) != 0) {
    printf("s> error logging operation\n");
  }
}

void handle_getmultifile(int socket, char *user, char *datetime) {
  // Primero, nos ha de llegar el path del fichero
  char file_path[MAX_FILE_PATH_SIZE] = {0};
  ssize_t bytes_read = read_line(socket, file_path, sizeof(file_path));
  file_path[sizeof(file_path) - 1] = '\0'; // Por si acaso
  if (bytes_read <= 0) {
    perror("s> error reading file path");
    close(socket);
    return;
  }

  // Ahora, nos recorremos todos los ficheros de todos los usuarios para
  // comprobar quién tiene el fichero y enviárselo al cliente
  connected_user_t *conn_users = NULL;
  uint32_t num_users = 0;
  u_int32_t users_with_file = 0;

  int res_con_users = get_connected_users(&usuarios, user, &conn_users, &num_users);

  if (res_con_users != 0) {
    send_ret_value(socket, (uint8_t) res_con_users);
    close(socket);
    return;
  }

  for (u_int32_t i = 0; i < num_users; i++) {
    file_t *files = NULL;
    uint32_t num_files = 0;
    int res_get_user_files = get_user_files(&usuarios, user, conn_users[i].name, &files, &num_files);
    if (res_get_user_files == 0 && num_files > 0) {
      for (u_int32_t j = 0; j < num_files; j++) {
        if (is_same_file(files[j].path, file_path)) {
          users_with_file++;
        }
      }
    }
    free(files);
  }

  // Ahora que ya sabemos cuántos usuarios tienen el fichero, enviamos el número de usuarios que lo poseen
  if (users_with_file > 255) {
    users_with_file = 255;
  } else if (users_with_file == 0) {
    if (send_ret_value(socket, (uint8_t) 1) != 0) {
      perror("s> error sending return value to user");
      close(socket);
      free(conn_users);
      return;
    }
  }
  // Primero enviamos el código de operación de que ha ido bien
  if (send_ret_value(socket, (uint8_t) 0) != 0) {
    perror("s> error sending return value to user");
    close(socket);
    free(conn_users);
    return;
  }

  // Ahora enviamos el número de usuarios que tienen el fichero
  if (send_ret_value(socket, (uint8_t) users_with_file) != 0) {
    perror("s> error sending return value to user");
    close(socket);
    free(conn_users);
    return;
  }

  // Ahora, por cada usuario, enviamos su ip, su puerto y el ruta del fichero.
  // enviar la ruta es necesario porque un mismo fichero puede estar en dos rutas distintas.
  for (u_int32_t i = 0; i < num_users; i++) {
    file_t *files = NULL;
    uint32_t num_files = 0;
    int res_get_user_files = get_user_files(&usuarios, user, conn_users[i].name, &files, &num_files);
    if (res_get_user_files == 0 && num_files > 0) {
      for (u_int32_t j = 0; j < num_files; j++) {
        if (is_same_file(files[j].path, file_path)) {
          size_t len = strnlen(conn_users[i].ip, sizeof(conn_users[i].ip)) + 1;
          if (send_message(socket, conn_users[i].ip, len) != 0) {
            free(conn_users);
            close(socket);
            return;
          }
          char buffer[32] = {0};
          snprintf(buffer, sizeof(buffer), "%u", conn_users[i].port);
          len = strlen(buffer) + 1;
          if (send_message(socket, buffer, len) != 0) {
            free(conn_users);
            close(socket);
            return;
          }
          len = strnlen(files[j].path, sizeof(files[j].path)) + 1;
          if (send_message(socket, files[j].path, len) != 0) {
            free(conn_users);
            close(socket);
            return;
          }
        }
      }
    }
    free(files);
  }

  close(socket);
  free(conn_users);
  if (log_operation(user, "GET_MULTIFILE", datetime, file_path) != 0) {
    printf("s> error logging operation\n");
  }
}

void *handle_request(void *arg) {
  int client_sock;

  pthread_mutex_lock(&req_lock);
  client_sock = *(int *) arg;
  free(arg);
  req_ready = true;
  pthread_cond_signal(&req_cond);
  pthread_mutex_unlock(&req_lock);

  // printf("[INFO (sock %d)] Cliente conectado por socket con descriptor: %d\n", client_sock, client_sock);

  // Primero, leemos la operación
  char operation[MAX_OP_MSG_SIZE];
  memset(operation, 0, MAX_OP_MSG_SIZE);

  const ssize_t bytes_read = read_line(client_sock, operation, MAX_OP_MSG_SIZE);
  if (bytes_read <= 0) {
    perror("s> error reading operation");
    close(client_sock);
    return NULL;
  }

  // Después, leemos el datetime
  char datetime[MAX_DATETIME_SIZE];
  memset(datetime, 0, MAX_DATETIME_SIZE);

  const ssize_t bytes_read_datetime = read_line(client_sock, datetime, MAX_DATETIME_SIZE);
  if (bytes_read_datetime <= 0) {
    perror("s> error reading datetime");
    close(client_sock);
    return NULL;
  }

  // Por último, leemos el nombre de usuario
  char user[MAX_USER_MSG_SIZE];
  memset(user, 0, MAX_USER_MSG_SIZE);

  const ssize_t bytes_read_user = read_line(client_sock, user, MAX_USER_MSG_SIZE);
  if (bytes_read_user <= 0) {
    perror("s> error reading user");
    close(client_sock);
    return NULL;
  }

  printf("s> OPERATION %s FROM %s AT %s\n", operation, user, datetime);

  // Aquí se realizan las operaciones
  if (strcmp(operation, "REGISTER") == 0) {
    handle_register(client_sock, user, datetime);
  } else if (strcmp(operation, "UNREGISTER") == 0) {
    handle_unregister(client_sock, user, datetime);
  } else if (strcmp(operation, "CONNECT") == 0) {
    handle_connect(client_sock, user, datetime);
  } else if (strcmp(operation, "DISCONNECT") == 0) {
    handle_disconnect(client_sock, user, datetime);
  } else if (strcmp(operation, "PUBLISH") == 0) {
    handle_publish(client_sock, user, datetime);
  } else if (strcmp(operation, "DELETE") == 0) {
    handle_delete(client_sock, user, datetime);
  } else if (strcmp(operation, "LIST_USERS") == 0) {
    handle_list_users(client_sock, user, datetime);
  } else if (strcmp(operation, "LIST_CONTENT") == 0) {
    handle_list_files(client_sock, user, datetime);
  } else if (strcmp(operation, "GET_MULTIFILE") == 0) {
    handle_getmultifile(client_sock, user, datetime);
  } else {
    printf("s> unknown operation: %s\n", operation);
    log_operation(user, "UNKNOWN", datetime, NULL);
  }

  close(client_sock);
  fflush(stdout);

  return NULL;
}

int main(int argc, char *argv[]) {
  if (argc != 2) {
    perror("Uso: ./servidor-sock <puerto>");
    exit(EXIT_FAILURE);
  }
  __uint16_t port = (__uint16_t) atoi(argv[1]);
  // No es necesario comprobar si el puerto es mayor que 65535 porque el tipo de dato
  // __uint16_t no puede almacenar un número mayor que 65535.
  if (port < 1024) {
    perror("El puerto debe estar entre 1024 y 65535");
    exit(EXIT_FAILURE);
  }

  struct sockaddr_in server_addr;

  if ((server_sock = socket(AF_INET, SOCK_STREAM, 0)) == -1) {
    perror("[ERROR] al crear el socket del servidor");
    exit(EXIT_FAILURE);
  }

  signal(SIGINT, handle_poweroff);
  signal(SIGTERM, handle_poweroff); // Para pararlo en CLion

  server_addr.sin_family = AF_INET;
  server_addr.sin_port = htons(port);
  server_addr.sin_addr.s_addr = INADDR_ANY;

  // El siguiente código es para evitar el error "Address already in use" y poder reutilizar el puerto
  // Esto pasa porque el puerto se queda en estado TIME_WAIT durante un tiempo después de cerrar el socket.
  int opt = 1;
  if (setsockopt(server_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
    perror("[ERROR] al establecer SO_REUSEADDR");
    close(server_sock);
    exit(EXIT_FAILURE);
  }

  // Le damos al socket una dirección
  if (bind(server_sock, (struct sockaddr *) &server_addr, sizeof(server_addr)) == -1) {
    perror("[ERROR] al enlazar el socket del servidor");
    close(server_sock);
    exit(EXIT_FAILURE);
  }

  // Marcamos al socket en modo escucha
  if (listen(server_sock, 10) == -1) {
    perror("[ERROR] al poner el servidor en modo escucha");
    close(server_sock);
    exit(EXIT_FAILURE);
  }

  printf("s> init server %s:%u\n", inet_ntoa(server_addr.sin_addr), ntohs(server_addr.sin_port));

  while (1) {
    struct sockaddr_in client_addr;
    socklen_t client_addr_len = sizeof(client_addr);
    // Para aceptar la conexión, utilizaremos un puntero a un entero para poder pasarlo al hilo.
    // La región de memoria de este entero la reservamos con calloc para asegurarnos de que está a 0.
    int *client_sock = calloc(1, sizeof(int));
    if (!client_sock) {
      perror("[ERROR] al reservar memoria para el socket del cliente");
      continue;
    }

    *client_sock = accept(server_sock, (struct sockaddr *) &client_addr, &client_addr_len);
    if (*client_sock == -1) {
      perror("[ERROR] al aceptar la conexión del cliente");
      free(client_sock);
      continue;
    }

    // Lanzamos un hilo para manejar la petición del cliente
    pthread_t tid;
    if (pthread_create(&tid, NULL, (void *(*) (void *) ) handle_request, client_sock) != 0) {
      perror("[ERROR] al crear hilo para el cliente");
      close(*client_sock);
      free(client_sock);
    } else {
      pthread_mutex_lock(&req_lock);
      while (!req_ready) {
        pthread_cond_wait(&req_cond, &req_lock);
      }
      req_ready = false;
      pthread_mutex_unlock(&req_lock);
      pthread_detach(tid);
    }
  }
  return 0;
}
