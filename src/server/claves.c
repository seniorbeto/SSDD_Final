#include "claves.h"
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int add_user(user_t **head, const char *name) {
  if (!head || !name) {
    return 2; // Error en parámetros
  }

  // 1) Comprobar si el usuario ya existe
  user_t *temp = *head;
  while (temp) {
    if (strcmp(temp->name, name) == 0) {
      return 1; // Usuario ya existe
    }
    temp = temp->next;
  }

  // 2) Reservar memoria para el nuevo usuario
  user_t *new_user = (user_t *) malloc(sizeof(user_t));
  if (!new_user) {
    return 2; // Fallo de reserva
  }

  // 3) Rellenar y enlazar
  memset(new_user, 0, sizeof(user_t));
  strncpy(new_user->name, name, sizeof(new_user->name) - 1);
  new_user->connected = false;
  new_user->files = NULL;
  new_user->next = *head;

  *head = new_user;
  return 0; // Éxito
}

int remove_user(user_t **head, const char *name) {
  if (!head || !*head || !name) {
    return 2;
  }

  user_t *curr = *head;
  user_t *prev = NULL;

  while (curr) {
    if (strcmp(curr->name, name) == 0) {
      // 1) Reencadenar la lista
      if (!prev) {
        *head = curr->next;
      } else {
        prev->next = curr->next;
      }

      // 2) Eliminar la lista de ficheros
      file_t *f = curr->files;
      while (f) {
        file_t *aux = f;
        f = f->next;
        free(aux);
      }

      // 3) Liberar la estructura user
      free(curr);
      return 0; // Éxito
    }
    prev = curr;
    curr = curr->next;
  }

  // Usuario no encontrado
  return 1;
}

int find_user(user_t *head, const char *name, user_t **out_user) {
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

  // No encontrado
  *out_user = NULL;
  return 1;
}

/**
 * @brief Marca como 'conectado' a un usuario si existe.
 *
 * @param[in] head  Cabeza de la lista de usuarios.
 * @param[in] name  Nombre del usuario a "conectar".
 *
 * @return int:
 *   - 0 si se ha conectado correctamente.
 *   - 1 si no existe.
 *   - 2 en caso de error (parámetros nulos).
 */
int connect_user(user_t **head, const char *name, const char *ip, int port) {
  if (!head || !name || !ip) {
    return 3;
  }
  if (port < 1024 || port > 65535) {
    return 3; // Puerto no válido
  }
  user_t *usr = NULL;
  int ret = find_user(*head, name, &usr);
  if (ret == 0 && usr) {
    if (usr->connected) {
      return 2; // Ya está conectado
    }
    usr->connected = true;
    usr->port = port;
    strncpy(usr->ip, ip, sizeof(usr->ip) - 1);
    return 0;
  }
  // Si find_user() devuelve 1 => no encontrado
  return (ret == 1) ? 1 : 3;
}

int disconnect_user(user_t **head, const char *name) {
  if (!head || !name) {
    return 3;
  }

  user_t *usr = NULL;
  int ret = find_user(*head, name, &usr);
  if (ret == 0 && usr) {
    if (!usr->connected) {
      return 2; // No está conectado
    }
    usr->connected = false;
    usr->port = 0;
    memset(usr->ip, 0, sizeof(usr->ip)); // Limpiar IP
    return 0; // Éxito
  }
  // Si find_user() devuelve 1 => no encontrado
  return (ret == 1) ? 1 : 3;

}

int add_file(user_t *head, const char *username, const char *path, size_t size, const char *description) {
  if (!head || !username || !path || !description) {
    return 3;
  }

  // 1) Buscar al usuario
  user_t *usr = NULL;
  int ret_user = find_user(head, username, &usr);
  if (ret_user != 0 || !usr) {
    return 1; // no existe
  }

  // 2) Comprobar si ya existe ese fichero
  file_t *temp = usr->files;
  while (temp) {
    if (strcmp(temp->path, path) == 0) {
      return 2; // Fichero ya publicado
    }
    temp = temp->next;
  }

  // 3) Crear el nuevo file
  file_t *new_file = (file_t *) malloc(sizeof(file_t));
  if (!new_file) {
    return 3; // Error de memoria
  }
  memset(new_file, 0, sizeof(file_t));
  strncpy(new_file->path, path, sizeof(new_file->path) - 1);
  strncpy(new_file->description, description, sizeof(new_file->description) - 1);
  new_file->size = size;
  new_file->next = usr->files;

  // 4) Enlazar
  usr->files = new_file;
  return 0; // Éxito
}

int remove_file(user_t *head, const char *username, const char *path) {
  if (!head || !username || !path) {
    return 3;
  }

  // 1) Buscar usuario
  user_t *usr = NULL;
  int ret_user = find_user(head, username, &usr);
  if (ret_user != 0 || !usr) {
    return 1; // usuario no existe
  }

  // 2) Buscar y eliminar el fichero
  file_t *curr = usr->files;
  file_t *prev = NULL;

  while (curr) {
    if (strcmp(curr->path, path) == 0) {
      // encontrado: eliminar
      if (!prev) {
        usr->files = curr->next;
      } else {
        prev->next = curr->next;
      }
      free(curr);
      return 0; // Éxito
    }
    prev = curr;
    curr = curr->next;
  }

  // No se encontró el fichero
  return 2;
}

int find_file(user_t *head, const char *username, const char *path, file_t **out_file) {
  if (!head || !username || !path || !out_file) {
    return 3;
  }

  // 1) Buscar usuario
  user_t *usr = NULL;
  int ret_user = find_user(head, username, &usr);
  if (ret_user != 0 || !usr) {
    *out_file = NULL;
    return 1; // usuario no existe
  }

  // 2) Recorrer ficheros
  file_t *temp = usr->files;
  while (temp) {
    if (strcmp(temp->path, path) == 0) {
      *out_file = temp;
      return 0; // encontrado
    }
    temp = temp->next;
  }
  *out_file = NULL;
  return 2; // no se encontró el fichero
}

void destroy(user_t **head) {
  if (!head) {
    return;
  }

  user_t *curr_user = *head;
  while (curr_user) {
    user_t *tmp_user = curr_user;
    curr_user = curr_user->next;

    // 1) Liberar la lista de ficheros
    file_t *curr_file = tmp_user->files;
    while (curr_file) {
      file_t *tmp_file = curr_file;
      curr_file = curr_file->next;
      free(tmp_file);
    }

    // 2) Liberar la estructura user
    free(tmp_user);
  }

  *head = NULL; // Lista vacía
}
