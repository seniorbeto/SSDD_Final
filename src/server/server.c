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
int handle_register(int socket);

void handle_poweroff() {
  close(server_sock);
  destroy(&usuarios);
  printf("\nSaliendo del servidor...\n");
  exit(EXIT_SUCCESS);
}

void *handle_request(void *arg) {
  int client_sock;

  pthread_mutex_lock(&req_lock);
  client_sock = *(int *) arg;
  free(arg);
  req_ready = true;
  pthread_cond_signal(&req_cond);
  pthread_mutex_unlock(&req_lock);

  //printf("[INFO (sock %d)] Cliente conectado por socket con descriptor: %d\n", client_sock, client_sock);

  // Primero, leemos la operación
  char operation[MAX_OP_MSG_SIZE];
  memset(operation, 0, MAX_OP_MSG_SIZE);

  const ssize_t bytes_read = read_line(client_sock, operation, MAX_OP_MSG_SIZE);
  if (bytes_read <= 0) {
    perror("[ERROR] al leer la operación del cliente");
    close(client_sock);
    return NULL;
  }

  char user[MAX_USER_MSG_SIZE];
  memset(user, 0, MAX_USER_MSG_SIZE);

  const ssize_t bytes_read_user = read_line(client_sock, user, MAX_USER_MSG_SIZE);
  if (bytes_read_user <= 0) {
    perror("[ERROR] al leer el usuario del cliente");
    close(client_sock);
    return NULL;
  }

  printf("s> OPERATION %s FROM %s\n", operation, user);

  // Aquí se realizan las operaciones
  if (strcmp(operation, "REGISTER") == 0) {

  } else {
    printf("[ERROR] Operación no válida: %s\n", operation);
  }

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