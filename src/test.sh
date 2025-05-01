#!/bin/bash

SERVER_IP='localhost'
SERVER_PORT=4444
RPC_SERVICE_IP='localhost'

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p test_files/output/logs
rm -f test_files/output/logs/*.log

run_test() {
  local test_name=$1
  local input_file=$2
  local expected_file=$3
  local output_file="test_files/output/${test_name}.output"

  echo -e -n "${BLUE}Running test '$test_name'...${NC} "

  # Ejecutar el cliente, redirigiendo entrada desde $input_file y guardando salida
  python3 client/client.py -s $SERVER_IP -p $SERVER_PORT < "$input_file" > "$output_file" 2>/dev/null

  # Comparar resultado con lo esperado
  if diff -b -B -q <(sed -E 's/[0-9]{4,5}/PORT/g' "$output_file") \
                <(sed -E 's/[0-9]{4,5}/PORT/g' "$expected_file") >/dev/null; then
      echo -e "${GREEN}OK.${NC}"
    else
      echo -e "${RED}Fail.${NC}"
    fi
}


# LOGGER (servicio rpc)
./logger/cmake-build-release/logger > test_files/output/logs/logger.log 2>&1 &
LOGGER_PID=$!

# SERVER
export LOG_RPC_IP=$RPC_SERVICE_IP
./server/cmake-build-release/server $SERVER_PORT > test_files/output/logs/server.log 2>&1 &
SERVER_PID=$!

# WEB SERVICE
python3 web_server/web_server.py > test_files/output/logs/web_service.log 2>&1 &
WEB_SERVICE_PID=$!

# tests
run_test "quit" "test_files/input/quit.txt" "test_files/expected/quit_expected.txt"
run_test "register_1" "test_files/input/register_1.txt" "test_files/expected/register_1_expected.txt"
run_test "register_2" "test_files/input/register_2.txt" "test_files/expected/register_2_expected.txt"

kill $SERVER_PID 2>/dev/null
kill $LOGGER_PID 2>/dev/null
kill $WEB_SERVICE_PID 2>/dev/null