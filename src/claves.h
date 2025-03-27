#ifndef CLAVES_H
#define CLAVES_H

typedef struct file {
  char path[256];
  int size;
  char description[256];
} file_t;

typedef struct user {
  char name[32];
  char ip[16];
  int port;
  file_t *files; // ESTO DEBE SER LIBERADO
} user_t;

typedef struct node {
    user_t user;
    struct node *next;
} node_t;

#endif //CLAVES_H
