
#include "lines.h"
#include <errno.h>
#include <unistd.h>

int send_message(int socket, char *buffer, size_t len) {
  ssize_t r;
  ssize_t l = (ssize_t) len;

  do {
    r = write(socket, buffer, (size_t) l);
    l = l - r;
    buffer = buffer + r;
  } while ((l > 0) && (r >= 0));

  if (r < 0) {
    return (-1); /* fallo */
  } else {
    return (0); /* full length has been sent */
  }
}

int recv_message(int socket, char *buffer, size_t len) {
  ssize_t r;
  ssize_t l = (ssize_t) len;


  do {
    r = read(socket, buffer, (size_t) l);
    l = l - r;
    buffer = buffer + r;
  } while ((l > 0) && (r >= 0));

  if (r < 0) {
    return (-1); /* fallo */
  } else {
    return (0);
  } /* full length has been receive */
}

ssize_t read_line(int fd, void *buffer, size_t n) {
  ssize_t numRead; /* num of bytes fetched by last read() */
  size_t totRead; /* total bytes read so far */
  char *buf;
  char ch;


  if (n <= 0 || buffer == NULL) {
    errno = EINVAL;
    return -1;
  }

  buf = buffer;
  totRead = 0;

  for (;;) {
    numRead = read(fd, &ch, 1); /* read a byte */

    if (numRead == -1) {
      if (errno == EINTR) /* interrupted -> restart read() */
        continue;
      else
        return -1; /* some other error */
    } else if (numRead == 0) { /* EOF */
      if (totRead == 0) /* no byres read; return 0 */
        return 0;
      else
        break;
    } else { /* numRead must be 1 if we get here*/
      if (ch == '\n')
        break;
      if (ch == '\0')
        break;
      if (totRead < n - 1) { /* discard > (n-1) bytes */
        totRead++;
        *buf++ = ch;
      }
    }
  }

  *buf = '\0';
  return (ssize_t)totRead;
}
