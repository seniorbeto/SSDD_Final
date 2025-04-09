#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "claves.h"

user_t* add_user(user_t **head, const char *name, const char *ip, int port) {
    if (head == NULL || name == NULL || ip == NULL) {
        return NULL;
    }

    // Comprobar si el usuario ya existe
    user_t *temp = *head;
    while (temp != NULL) {
        if (strcmp(temp->name, name) == 0) {
            // El usuario ya existe
            return NULL;
        }
        temp = temp->next;
    }

    // Crear el nuevo usuario
    user_t *new_user = (user_t *)malloc(sizeof(user_t));
    if (!new_user) {
        return NULL;
    }
    memset(new_user, 0, sizeof(user_t));

    strncpy(new_user->name, name, sizeof(new_user->name) - 1);
    strncpy(new_user->ip,   ip,   sizeof(new_user->ip)   - 1);
    new_user->port  = port;
    new_user->files = NULL;
    new_user->next  = NULL;

    // Insertar al inicio de la lista
    new_user->next = *head;
    *head = new_user;

    return new_user;
}

int remove_user(user_t **head, const char *name) {
    if (head == NULL || *head == NULL || name == NULL) {
        return -1;
    }

    user_t *curr = *head;
    user_t *prev = NULL;

    // Buscar el usuario en la lista
    while (curr != NULL) {
        if (strcmp(curr->name, name) == 0) {
            // Encontrado: eliminar
            if (prev == NULL) {
                // Es el primero
                *head = curr->next;
            } else {
                prev->next = curr->next;
            }

            // Eliminar también la lista de ficheros de este usuario
            file_t *f = curr->files;
            while (f) {
                file_t *aux = f;
                f = f->next;
                free(aux);
            }

            free(curr);
            return 0;
        }
        prev = curr;
        curr = curr->next;
    }

    // No se ha encontrado
    return -1;
}

user_t* find_user(user_t *head, const char *name) {
    while (head != NULL) {
        if (strcmp(head->name, name) == 0) {
            return head;
        }
        head = head->next;
    }
    return NULL;
}

file_t* add_file(user_t *user, const char *path, size_t size, const char *description) {
    if (user == NULL || path == NULL || description == NULL) {
        return NULL;
    }

    // Comprobar si el fichero ya existe
    file_t *temp = user->files;
    while (temp != NULL) {
        if (strcmp(temp->path, path) == 0) {
            // Ya existe el fichero
            return NULL;
        }
        temp = temp->next;
    }

    // Crear nuevo fichero
    file_t *new_file = (file_t *)malloc(sizeof(file_t));
    if (!new_file) {
        return NULL;
    }
    memset(new_file, 0, sizeof(file_t));

    strncpy(new_file->path,        path,        sizeof(new_file->path)        - 1);
    strncpy(new_file->description, description, sizeof(new_file->description) - 1);
    new_file->size = size;
    new_file->next = NULL;

    // Insertar al inicio de la lista
    new_file->next = user->files;
    user->files = new_file;

    return new_file;
}


int remove_file(user_t *user, const char *path) {
    if (user == NULL || path == NULL) {
        return -1;
    }
    file_t *curr = user->files;
    file_t *prev = NULL;

    while (curr != NULL) {
        if (strcmp(curr->path, path) == 0) {
            // Encontrado: eliminar
            if (prev == NULL) {
                user->files = curr->next;
            } else {
                prev->next = curr->next;
            }
            free(curr);
            return 0;
        }
        prev = curr;
        curr = curr->next;
    }
    return -1;
}

file_t* find_file(const user_t *user, const char *path) {
    if (user == NULL || path == NULL) {
        return NULL;
    }
    file_t *temp = user->files;
    while (temp != NULL) {
        if (strcmp(temp->path, path) == 0) {
            return temp;
        }
        temp = temp->next;
    }
    return NULL;
}

void destroy(user_t **head) {
  if (head == NULL) {
    return;
  }

  user_t *curr_user = *head;
  while (curr_user != NULL) {
    user_t *tmp_user = curr_user;
    curr_user = curr_user->next;

    // Liberar la lista de ficheros de este usuario
    file_t *curr_file = tmp_user->files;
    while (curr_file != NULL) {
      file_t *tmp_file = curr_file;
      curr_file = curr_file->next;
      free(tmp_file);
    }

    // Liberar la estructura del usuario
    free(tmp_user);
  }

  *head = NULL;  // Dejamos el puntero principal en NULL
}
