#ifndef CLAVES_H
#define CLAVES_H

#include <stdbool.h>
#include <stddef.h>

// CABECERAS
typedef struct user user_t;
typedef struct file file_t;

/**
 * @struct file
 * @brief Estructura que representa un fichero publicado por un usuario.
 */
struct file {
  char path[256]; /**< Ruta completa del fichero (máx. 255 caracteres) */
  char description[256]; /**< Descripción asociada al fichero (máx. 255 caracteres) */
  file_t *next; /**< Puntero al siguiente fichero en la lista enlazada */
};

/**
 * @struct user
 * @brief Estructura que representa un usuario del sistema.
 */
struct user {
  char name[32]; /**< Nombre del usuario (máx. 31 caracteres) */
  char ip[16]; /**< Dirección IP del usuario (máx. 15 caracteres) */
  int port; /**< Puerto asociado al usuario */
  bool connected; /**< Indica si el usuario está conectado o no */
  file_t *files; /**< Lista de ficheros publicados por el usuario */
  user_t *next; /**< Puntero al siguiente usuario en la lista enlazada */
};

/**
 * @brief Añade un nuevo usuario a la lista.
 *
 * @param[in,out] head  Doble puntero a la cabeza de la lista de usuarios.
 * @param[in]     name  Nombre del usuario.
 * @param[in]     ip    Dirección IP del usuario.
 * @param[in]     port  Puerto del usuario.
 *
 * @return int:
 *   - 0 si se ha añadido correctamente.
 *   - 1 si el usuario ya existe.
 *   - 2 en caso de error (parámetros nulos o fallo al reservar memoria).
 */
int add_user(user_t **head, const char *name);

/**
 * @brief Elimina de la lista al usuario cuyo nombre coincide.
 *
 * @param[in,out] head  Doble puntero a la cabeza de la lista de usuarios.
 * @param[in]     name  Nombre del usuario a eliminar.
 *
 * @return int:
 *   - 0 si se elimina correctamente.
 *   - 1 si no se encuentra el usuario.
 *   - 2 en caso de error (parámetros nulos).
 */
int remove_user(user_t **head, const char *name);

/**
 * @brief Busca a un usuario por nombre y lo devuelve via parámetro 'out_user'.
 *
 * @param[in]  head       Cabeza de la lista de usuarios.
 * @param[in]  name       Nombre del usuario a buscar.
 * @param[out] out_user   Puntero que contendrá la dirección del usuario hallado.
 *
 * @return int:
 *   - 0 si se encuentra y se devuelve en out_user.
 *   - 1 si no se encuentra.
 *   - 2 en caso de error (parámetros nulos).
 */
int find_user(user_t *head, const char *name, user_t **out_user);

/**
 * @brief Marca como 'conectado' a un usuario si existe.
 *
 * @param[in] head  Cabeza de la lista de usuarios.
 * @param[in] name  Nombre del usuario a "conectar".
 *
 * @return int:
 *   - 0 si se ha conectado correctamente.
 *   - 1 si no existe.
 *   - 2 en caso de que el usuario ya esté conectado.
 *   - 3 cualquier otro caso.
 */
int connect_user(user_t **head, const char *name, const char *ip, int port);

/**
 * @brief Marca como 'desconectado' a un usuario si existe.
 *
 * @param[in] head  Cabeza de la lista de usuarios.
 * @param[in] name  Nombre del usuario a "desconectar".
 *
 * @return int:
 *   - 0 si se ha desconectado correctamente.
 *   - 1 si no existe.
 *   - 2 si el usuario no está conectado.
 *   - 3 en caso de error (parámetros nulos).
 */
int disconnect_user(user_t **head, const char *name);

/**
 * @brief Añade un fichero a la lista del usuario 'username'.
 *
 * @param[in] head         Cabeza de la lista de usuarios.
 * @param[in] username     Nombre del usuario dueño del fichero.
 * @param[in] path         Ruta del fichero.
 * @param[in] size         Tamaño del fichero en bytes.
 * @param[in] description  Descripción del fichero.
 *
 * @return int:
 *   - 0 si se añade correctamente.
 *   - 1 si el usuario no existe.
 *   - 2 si el usuario no está conectado.
 *   - 3 si el fichero ya está publicado.
 *   - 4 si ocurre otro error (parámetros nulos o fallo en malloc).
 */
int add_file(user_t **head, const char *username, const char *path, const char *description);

/**
 * @brief Elimina un fichero 'path' de la lista del usuario 'username'.
 *
 * @param[in] head       Cabeza de la lista de usuarios.
 * @param[in] username   Nombre del usuario dueño del fichero.
 * @param[in] path       Ruta del fichero a eliminar.
 *
 * @return int:
 *   - 0 si se elimina correctamente.
 *   - 1 si no existe el usuario.
 *   - 2 si el fichero no existe.
 *   - 3 en caso de error (parámetros nulos).
 */
int remove_file(user_t *head, const char *username, const char *path);

/**
 * @brief Busca un fichero 'path' dentro del usuario 'username' y, si lo halla, lo devuelve en *out_file.
 *
 * @param[in]  head       Cabeza de la lista de usuarios.
 * @param[in]  username   Nombre del usuario.
 * @param[in]  path       Ruta del fichero a buscar.
 * @param[out] out_file   Puntero al que se asignará el fichero hallado (o NULL si no se halla).
 *
 * @return int:
 *   - 0 si se encuentra.
 *   - 1 si no existe el usuario.
 *   - 2 si el fichero no existe.
 *   - 3 en caso de error (parámetros nulos).
 */
int find_file(user_t *head, const char *username, const char *path, file_t **out_file);

/**
 * @brief Libera toda la memoria asociada a la lista de usuarios y sus ficheros.
 *
 * @param[in,out] head Doble puntero a la cabeza de la lista.
 */
void destroy(user_t **head);

#endif // CLAVES_H
