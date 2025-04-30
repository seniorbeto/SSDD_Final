#include "logger.h"
#include <stdio.h>

void *
log_op_1_svc(log_entry *entry, struct svc_req *rqstp)
{
  printf("[%s] %s: %s\n",
          entry->timestamp,
          entry->username,
          entry->operation);

  return NULL;
}
