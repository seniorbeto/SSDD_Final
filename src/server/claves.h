#ifndef CLAVES_H
#define CLAVES_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

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
  char name[255]; /**< Nombre del usuario (máx. 31 caracteres) */
  char ip[16]; /**< Dirección IP del usuario (máx. 15 caracteres) */
  int port; /**< Puerto asociado al usuario */
  bool connected; /**< Indica si el usuario está conectado o no */
  file_t *files; /**< Lista de ficheros publicados por el usuario */
  user_t *next; /**< Puntero al siguiente usuario en la lista enlazada */
};

/*
 * La siguiente estructura es lo que se devuelve cuando se ejecuta la función
 * get_connected_users, que devuelve una lista de usuarios conectados.
 */
typedef struct connected_user_s {
  char name[256];
  char ip[17];
  int port;
} connected_user_t;

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
 *   - 2 si el usuario no está conectado.
 *   - 3 si el fichero no existe.
 *   - 4 si ocurre otro error (parámetros nulos).
 */
int remove_file(user_t **head, const char *username, const char *path);

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
 * @brief Devuelve un array de usuarios conectados. OJO: la responsabilidad
 * de liberar la memoria del array es del caller, ya que esta función reserva memoria
 * en función del número de usuarios conectados.
 *
 * @param[in]  head       Cabeza de la lista de usuarios.
 * @param[in]  username   Nombre del usuario que solicita la lista.
 * @param[out] array      Array donde se almacenarán los usuarios conectados.
 * @param[out] size       Tamaño del array (número de usuarios conectados).
 *
 * @return int:
 *   - 0 si se obtiene correctamente el array.
 *   - 1 si el usuario no está registrado.
 *   - 2 si el usuario no está conectado.
 *   - 3 en cualquier otro caso (parámetros nulos o fallo en malloc).
 */
int get_connected_users(user_t **head, const char *username, connected_user_t **array, uint32_t *size);

/**
 * @brief Devuelve un array de ficheros publicados por el usuario 'username'.
 * OJO: la responsabilidad de liberar la memoria del array es del caller, ya que
 * esta función reserva memoria en función del número de ficheros publicados.
 *
 * @param[in]  head       Cabeza de la lista de usuarios.
 * @param[in]  username   Nombre del usuario que solicita la lista.
 * @param[in]  usertocheck Nombre del usuario cuyos ficheros se quieren obtener.
 * @param[out] array      Array donde se almacenarán los ficheros publicados.
 * @param[out] size       Tamaño del array (número de ficheros publicados).
 *
 * @return int:
 *   - 0 si se obtiene correctamente el array.
 *   - 1 si el usuario no existe.
 *   - 2 si el usuario que realiza la operación no está conectado.
 *   - 3 si el usuario del que se quieren obtener los ficheros no existe.
 *   - 4 en cualquier otro caso (parámetros nulos o fallo en malloc).
 */
int get_user_files(user_t **head, const char *username, const char *usertocheck, file_t **array, uint32_t *size);

/**
 * @brief Libera toda la memoria asociada a la lista de usuarios y sus ficheros.
 *
 * @param[in,out] head Doble puntero a la cabeza de la lista.
 */
void destroy(user_t **head);

#endif // CLAVES_H
