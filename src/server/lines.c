
#include <unistd.h>
#include <errno.h>
#include "lines.h"

int send_message(int socket, char * buffer, size_t len) {
  ssize_t r;
  ssize_t l = (ssize_t) len;

  do {
    r = write(socket, buffer, (size_t)l);
    l = l -r;
    buffer = buffer + r;
  } while ((l>0) && (r>=0));

  if (r < 0) {
    return (-1);   /* fallo */
  } else {
    return(0);	/* full length has been sent */
  }
}

int recv_message(int socket, char *buffer, size_t len) {
  ssize_t r;
  ssize_t l = (ssize_t) len;


  do {
    r = read(socket, buffer, (size_t) l);
    l = l -r ;
    buffer = buffer + r;
  } while ((l>0) && (r>=0));

  if (r < 0) {
    return (-1);   /* fallo */
  } else {
    return(0);
  }	/* full length has been receive */
}