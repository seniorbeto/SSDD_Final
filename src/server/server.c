#include <arpa/inet.h>
#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "claves.h"
#include "lines.h"
#include "stdbool.h"

#define MAX_MSG_SIZE 2048
#define MAX_OP_MSG_SIZE 64
#define MAX_USER_MSG_SIZE 255

pthread_mutex_t req_lock = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t req_cond = PTHREAD_COND_INITIALIZER;
bool req_ready = false;

// Variables globales
int server_sock;
user_t *usuarios = NULL;

// Cabeceras
void handle_register(int socket, char *user);
void handle_unregister(int socket, char *user);
void handle_connect(int socket, char *user);
void handle_disconnect(int socket, char *user);

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

void handle_register(int socket, char *user) {
  // En la operación register, solo hace falta el código de operación y el nombre de usuario
  int res = add_user(&usuarios, user);
  if (send_ret_value(socket, (uint8_t) res) != 0) {
    printf("s> error sending return value to %s", user);
  }
}

void handle_unregister(int socket, char *user) {
  // En la operación unregister, solo hace falta el código de operación y el nombre de usuario
  int res = remove_user(&usuarios, user);
  if (send_ret_value(socket, (uint8_t) res) != 0) {
    printf("s> error sending return value to %s", user);
  }
}

void handle_connect(int socket, char *user) {
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
}

void handle_disconnect(int socket, char *user) {
  // En la operación disconnect, solo hace falta el código de operación y el nombre de usuario
  int res = disconnect_user(&usuarios, user);
  if (send_ret_value(socket, (uint8_t) res) != 0) {
    printf("s> error sending return value to %s", user);
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

  char user[MAX_USER_MSG_SIZE];
  memset(user, 0, MAX_USER_MSG_SIZE);

  const ssize_t bytes_read_user = read_line(client_sock, user, MAX_USER_MSG_SIZE);
  if (bytes_read_user <= 0) {
    perror("s> error reading user");
    close(client_sock);
    return NULL;
  }

  printf("s> OPERATION %s FROM %s\n", operation, user);

  // Aquí se realizan las operaciones
  if (strcmp(operation, "REGISTER") == 0) {
    handle_register(client_sock, user);
  } else if (strcmp(operation, "UNREGISTER") == 0) {
    handle_unregister(client_sock, user);
  } else if (strcmp(operation, "CONNECT") == 0) {
    handle_connect(client_sock, user);
  } else if (strcmp(operation, "DISCONNECT") == 0) {
    handle_disconnect(client_sock, user);
  } else {
    printf("s> unknown operation: %s\n", operation);
  }

  close(client_sock);

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
