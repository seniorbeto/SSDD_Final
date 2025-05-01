#include "logger.h"
#include <stdio.h>

void *
log_op_1_svc(log_entry *entry, struct svc_req *rqstp)
{
  static char res;
  printf("[%s] %s: %s %s\n",
          entry->timestamp,
          entry->username,
          entry->operation,
         entry->filename);

  // Devolvemos un valor cualquiera para indicar que la operación se ha realizado correctamente
  return (void *) &res;
}
