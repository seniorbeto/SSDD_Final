#include "claves.h"
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


// Variables globales
static pthread_rwlock_t lock = PTHREAD_RWLOCK_INITIALIZER;
/*
 * Esta variable se utiliza para llevar la cuenta de los usuarios conectados, de
 * esta manera, podemos reservar memoria para la cantidad de usuarios exacta por ejemplo,
 * cuando la función list_users devuelve la lista de usuarios conectados, junto con su ip y puerto.
 */
u_int32_t users_connected = 0;

static int find_user_internal(user_t *head, const char *name, user_t **out_user) {
  if (!out_user || !name) {
    return 2;
  }
  while (head) {
    if (strcmp(head->name, name) == 0) {
      *out_user = head;
      return 0; // Encontrado
    }
    head = head->next;
  }
  *out_user = NULL;
  return 1; // No encontrado
}

int add_user(user_t **head, const char *name) {
  if (!head || !name) {
    return 2; // Error en parámetros
  }

  pthread_rwlock_wrlock(&lock);

  user_t *temp = *head;
  while (temp) {
    if (strcmp(temp->name, name) == 0) {
      pthread_rwlock_unlock(&lock);
      return 1; // Usuario ya existe
    }
    temp = temp->next;
  }

  user_t *new_user = (user_t *) malloc(sizeof(user_t));
  if (!new_user) {
    pthread_rwlock_unlock(&lock);
    return 2; // Fallo de reserva
  }
  memset(new_user, 0, sizeof(user_t));
  strncpy(new_user->name, name, sizeof(new_user->name) - 1);

  new_user->connected = false;
  new_user->files = NULL;
  new_user->next = *head;
  *head = new_user;

  pthread_rwlock_unlock(&lock);
  return 0; // Éxito
}

int remove_user(user_t **head, const char *name) {
  if (!head || !*head || !name) {
    return 2;
  }

  pthread_rwlock_wrlock(&lock);

  user_t *curr = *head;
  user_t *prev = NULL;

  while (curr) {
    if (strcmp(curr->name, name) == 0) {
      if (!prev) {
        *head = curr->next;
      } else {
        prev->next = curr->next;
      }
      file_t *f = curr->files;
      while (f) {
        file_t *aux = f;
        f = f->next;
        free(aux);
      }
      // Si lo hemos encontrado y está conectado  hay que tenerlo en cuenta
      if (curr->connected) {
        users_connected--;
      }
      free(curr);
      pthread_rwlock_unlock(&lock);
      return 0; // Éxito
    }
    prev = curr;
    curr = curr->next;
  }

  pthread_rwlock_unlock(&lock);
  return 1; // Usuario no encontrado
}

int find_user(user_t *head, const char *name, user_t **out_user) {
  pthread_rwlock_rdlock(&lock);
  int ret = find_user_internal(head, name, out_user);
  pthread_rwlock_unlock(&lock);
  return ret;
}

int connect_user(user_t **head, const char *name, const char *ip, int port) {
  if (!head || !name || !ip) {
    return 3;
  }
  if (port < 1024 || port > 65535) {
    return 3; // Puerto no válido
  }

  pthread_rwlock_wrlock(&lock);

  user_t *usr = NULL;
  int ret = find_user_internal(*head, name, &usr);
  if (ret == 0 && usr) {
    if (usr->connected) {
      pthread_rwlock_unlock(&lock);
      return 2; // Ya conectado
    }
    usr->connected = true;
    usr->port = port;
    strncpy(usr->ip, ip, sizeof(usr->ip) - 1);
    users_connected++;

    pthread_rwlock_unlock(&lock);
    return 0;
  }

  pthread_rwlock_unlock(&lock);
  return (ret == 1) ? 1 : 3;
}

int disconnect_user(user_t **head, const char *name) {
  if (!head || !name) {
    return 3;
  }

  pthread_rwlock_wrlock(&lock);

  user_t *usr = NULL;
  int ret = find_user_internal(*head, name, &usr);
  if (ret == 0 && usr) {
    if (!usr->connected) {
      pthread_rwlock_unlock(&lock);
      return 2; // No estaba conectado
    }
    usr->connected = false;
    usr->port = 0;
    memset(usr->ip, 0, sizeof(usr->ip));
    users_connected--;
    pthread_rwlock_unlock(&lock);
    return 0;
  }

  pthread_rwlock_unlock(&lock);
  return (ret == 1) ? 1 : 3;
}

int add_file(user_t **head, const char *username, const char *path, const char *description) {
  if (!head || !username || !path || !description) {
    return 4;
  }

  pthread_rwlock_wrlock(&lock);

  user_t *usr = NULL;
  int ret_user = find_user_internal(*head, username, &usr);
  if (ret_user != 0 || !usr) {
    pthread_rwlock_unlock(&lock);
    return 1; // No existe
  }

  if (!usr->connected) {
    pthread_rwlock_unlock(&lock);
    return 2; // No conectado
  }

  file_t *temp = usr->files;
  while (temp) {
    if (strcmp(temp->path, path) == 0) {
      pthread_rwlock_unlock(&lock);
      return 3; // Fichero ya publicado
    }
    temp = temp->next;
  }

  file_t *new_file = (file_t *) malloc(sizeof(file_t));
  if (!new_file) {
    pthread_rwlock_unlock(&lock);
    return 4; // Error de memoria
  }
  memset(new_file, 0, sizeof(file_t));
  strncpy(new_file->path, path, sizeof(new_file->path) - 1);
  strncpy(new_file->description, description, sizeof(new_file->description) - 1);
  new_file->next = usr->files;
  usr->files = new_file;

  pthread_rwlock_unlock(&lock);
  return 0;
}

int remove_file(user_t **head, const char *username, const char *path) {
  if (!head || !username || !path) {
    return 4;
  }

  pthread_rwlock_wrlock(&lock);

  user_t *usr = NULL;
  int ret_user = find_user_internal(*head, username, &usr);
  if (ret_user != 0 || !usr) {
    pthread_rwlock_unlock(&lock);
    return 1; // usuario no existe
  }

  if (!usr->connected) {
    pthread_rwlock_unlock(&lock);
    return 2; // no conectado
  }

  file_t *curr = usr->files;
  file_t *prev = NULL;
  while (curr) {
    if (strcmp(curr->path, path) == 0) {
      if (!prev) {
        usr->files = curr->next;
      } else {
        prev->next = curr->next;
      }
      free(curr);
      pthread_rwlock_unlock(&lock);
      return 0;
    }
    prev = curr;
    curr = curr->next;
  }

  pthread_rwlock_unlock(&lock);
  return 3; // no se encontró
}

int find_file(user_t *head, const char *username, const char *path, file_t **out_file) {
  if (!head || !username || !path || !out_file) {
    return 3;
  }

  pthread_rwlock_rdlock(&lock);

  user_t *usr = NULL;
  int ret_user = find_user_internal(head, username, &usr);
  if (ret_user != 0 || !usr) {
    *out_file = NULL;
    pthread_rwlock_unlock(&lock);
    return 1;
  }

  file_t *temp = usr->files;
  while (temp) {
    if (strcmp(temp->path, path) == 0) {
      *out_file = temp;
      pthread_rwlock_unlock(&lock);
      return 0;
    }
    temp = temp->next;
  }
  *out_file = NULL;

  pthread_rwlock_unlock(&lock);
  return 2;
}

int get_connected_users(user_t **head, const char *username, connected_user_t **array, uint32_t *size) {
  if (!head || !array) {
    return 3;
  }

  pthread_rwlock_rdlock(&lock);

  // Si no hay usuarios conectados, devolvemos un código de error 3
  if (users_connected <= 0) {
    pthread_rwlock_unlock(&lock);
    return 3; // No hay usuarios conectados
  }

  user_t *usr = NULL;
  int ret_user = find_user_internal(*head, username, &usr);
  if (ret_user != 0 || !usr) {
    pthread_rwlock_unlock(&lock);
    return 1; // No existe
  }

  // comprobamos que el usuario está conectado
  if (!usr->connected) {
    pthread_rwlock_unlock(&lock);
    return 2; // No conectado
  }

  // Primero, reservamos memoria para el array en función de la
  // cantidad de usuarios conectados que haya por el momento.
  // OJO: LIBERAR ESTA MEMORIA ES RESPONSABILIDAD DEL CALLER
  *array = (connected_user_t *) malloc(users_connected * sizeof(connected_user_t));
  if (!*array) {
    pthread_rwlock_unlock(&lock);
    return 3; // Error de memoria
  }

  *size = users_connected;

  size_t count = 0;
  for (user_t *u = *head; u != NULL; u = u->next) {
    if (u->connected) {
      strncpy((*array)[count].name, u->name, sizeof((*array)[count].name) - 1);
      (*array)[count].name[sizeof((*array)[count].name) - 1] = '\0';

      strncpy((*array)[count].ip, u->ip, sizeof((*array)[count].ip) - 1);
      (*array)[count].ip[sizeof((*array)[count].ip) - 1] = '\0';

      (*array)[count].port = u->port;
      count++;
    }
  }
  pthread_rwlock_unlock(&lock);

  return 0; // Éxito
}

void destroy(user_t **head) {
  pthread_rwlock_wrlock(&lock);

  if (!head) {
    pthread_rwlock_unlock(&lock);
    return;
  }

  user_t *curr_user = *head;
  while (curr_user) {
    user_t *tmp_user = curr_user;
    curr_user = curr_user->next;

    file_t *curr_file = tmp_user->files;
    while (curr_file) {
      file_t *tmp_file = curr_file;
      curr_file = curr_file->next;
      free(tmp_file);
    }
    free(tmp_user);
  }
  *head = NULL;

  pthread_rwlock_unlock(&lock);
}
