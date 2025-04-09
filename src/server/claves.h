#ifndef CLAVES_H
#define CLAVES_H

#include <stddef.h>

// CABECERAS
typedef struct user user_t;
typedef struct file file_t;

/**
 * @struct file
 * @brief Estructura que representa un fichero publicado por un usuario.
 */
struct file {
  char path[256];         /**< Ruta completa del fichero (máx. 255 caracteres) */
  size_t size;            /**< Tamaño del fichero en bytes */
  char description[256];  /**< Descripción asociada al fichero (máx. 255 caracteres) */
  file_t *next;    /**< Puntero al siguiente fichero en la lista enlazada */
};

/**
 * @struct user
 * @brief Estructura que representa un usuario del sistema.
 */
struct user {
  char name[32];       /**< Nombre del usuario (máx. 31 caracteres) */
  char ip[16];         /**< Dirección IP del usuario (máx. 15 caracteres) */
  int port;            /**< Puerto asociado al usuario */
  file_t *files;       /**< Lista de ficheros publicados por el usuario */
  user_t *next; /**< Puntero al siguiente usuario en la lista enlazada */
};

/**
 * @brief Añade un nuevo usuario a la lista enlazada.
 *
 * @param[in,out] head Puntero al puntero de la cabeza de la lista de usuarios.
 * @param[in] name Nombre del usuario.
 * @param[in] ip Dirección IP del usuario.
 * @param[in] port Puerto del usuario.
 *
 * @return Puntero al nuevo usuario si se ha añadido correctamente, NULL si ya existía
 *         un usuario con el mismo nombre o en caso de error.
 */
user_t* add_user(user_t **head, const char *name, const char *ip, int port);

/**
 * @brief Elimina un usuario de la lista enlazada.
 *
 * @param[in,out] head Puntero al puntero de la cabeza de la lista.
 * @param[in] name Nombre del usuario a eliminar.
 *
 * @return 0 si se eliminó correctamente, -1 si no se encontró o hubo error.
 */
int remove_user(user_t **head, const char *name);

/**
 * @brief Busca un usuario en la lista por su nombre.
 *
 * @param[in] head Puntero a la cabeza de la lista.
 * @param[in] name Nombre del usuario a buscar.
 *
 * @return Puntero al usuario encontrado, o NULL si no se encuentra.
 */
user_t* find_user(user_t *head, const char *name);

/**
 * @brief Añade un fichero a la lista de ficheros de un usuario.
 *
 * @param[in,out] user Puntero al usuario.
 * @param[in] path Ruta absoluta del fichero.
 * @param[in] size Tamaño del fichero.
 * @param[in] description Descripción del fichero.
 *
 * @return Puntero al fichero añadido, o NULL si ya existía o hubo error.
 */
file_t* add_file(user_t *user, const char *path, size_t size, const char *description);

/**
 * @brief Elimina un fichero publicado por un usuario.
 *
 * @param[in,out] user Puntero al usuario.
 * @param[in] path Ruta del fichero a eliminar.
 *
 * @return 0 si se eliminó correctamente, -1 si no se encontró o hubo error.
 */
int remove_file(user_t *user, const char *path);

/**
 * @brief Busca un fichero dentro de la lista de ficheros de un usuario.
 *
 * @param[in] user Puntero al usuario.
 * @param[in] path Ruta del fichero a buscar.
 *
 * @return Puntero al fichero encontrado, o NULL si no existe.
 */
file_t* find_file(const user_t *user, const char *path);

/**
 * @brief Libera toda la memoria asociada a la lista de usuarios y sus ficheros.
 *
 * @param[in,out] head Puntero al puntero de la cabeza de la lista de usuarios.
 */
void destroy(user_t **head);

#endif // CLAVES_H
