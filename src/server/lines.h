#ifndef LINES_H
#define LINES_H

#include <unistd.h>

int send_message(int socket, char * buffer, size_t len);

int recv_message(int socket, char *buffer, size_t len);

#endif //LINES_H