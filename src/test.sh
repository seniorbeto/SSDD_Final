#!/bin/bash

SERVER_IP='localhost'
SERVER_PORT=4444
RPC_SERVICE_IP='localhost'

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p test_files
rm -f test_files/*.log

# LOGGER (servicio rpc)
./logger/cmake-build-release/logger > test_files/logger.log 2>&1 &
LOGGER_PID=$!

# SERVER
export LOG_RPC_IP=$RPC_SERVICE_IP
./server/cmake-build-release/server $SERVER_PORT > test_files/server.log 2>&1 &
SERVER_PID=$!

# WEB SERVICE
python3 web_server/web_server.py > test_files/web_service.log 2>&1 &
WEB_SERVICE_PID=$!

# Definir el trap antes del bucle
trap 'echo -e "\n\n${RED}Stopping services...${NC}"; kill -TERM $LOGGER_PID 2>/dev/null; kill -TERM $SERVER_PID 2>/dev/null; kill -TERM $WEB_SERVICE_PID 2>/dev/null; exit' INT

# Esperar a Ctrl+C
echo -e "\n\n${YELLOW}Press Ctrl+C to stop the services...${NC}"
while true; do
  sleep 1
done
