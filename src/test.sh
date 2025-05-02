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

start_server() {
  export LOG_RPC_IP=$RPC_SERVICE_IP
  ./server/cmake-build-release/server "$SERVER_PORT" \
      > test_files/output/logs/server.log 2>&1 &
  SERVER_PID=$!
}

restart_server() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID"
    # Espera a que termine para evitar zombies
    wait "$SERVER_PID" 2>/dev/null
  fi
  start_server
}

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
restart_server
run_test "register_2" "test_files/input/register_2.txt" "test_files/expected/register_2_expected.txt"

restart_server
run_test "unregister_1" "test_files/input/unregister_1.txt" "test_files/expected/unregister_1_expected.txt"
restart_server
run_test "unregister_2" "test_files/input/unregister_2.txt" "test_files/expected/unregister_2_expected.txt"

restart_server
run_test "connect_1" "test_files/input/connect_1.txt" "test_files/expected/connect_1_expected.txt"
restart_server
run_test "connect_2" "test_files/input/connect_2.txt" "test_files/expected/connect_2_expected.txt"
restart_server
run_test "connect_3" "test_files/input/connect_3.txt" "test_files/expected/connect_3_expected.txt"

# Atención: en las pruebas de publish, hay que tener en cuenta que la ruta de los ficheros es relativa
# al directorio desde el que se está ejecutando éste script. Éste está pensado para ejecutarse desde el
# directorio raíz del proyecto. En caso contrario, muy probablemente fallarán los test.
restart_server
run_test "publish_1" "test_files/input/publish_1.txt" "test_files/expected/publish_1_expected.txt"
restart_server
run_test "publish_2" "test_files/input/publish_2.txt" "test_files/expected/publish_2_expected.txt"
restart_server
run_test "publish_3" "test_files/input/publish_3.txt" "test_files/expected/publish_3_expected.txt"

restart_server
run_test "delete_1" "test_files/input/delete_1.txt" "test_files/expected/delete_1_expected.txt"
restart_server
run_test "delete_2" "test_files/input/delete_2.txt" "test_files/expected/delete_2_expected.txt"
restart_server
run_test "delete_3" "test_files/input/delete_3.txt" "test_files/expected/delete_3_expected.txt"

# Para las pruebas de list_users, hay que tener en cuenta que el puerto que genera cada usuario es aleatorio
# Para ello, dentro de la función run_test se sustituye el puerto por la palabra PORT y se compara.
restart_server
run_test "list_users_1" "test_files/input/list_users_1.txt" "test_files/expected/list_users_1_expected.txt"
restart_server
run_test "list_users_2" "test_files/input/list_users_2.txt" "test_files/expected/list_users_2_expected.txt"

restart_server
run_test "list_content_1" "test_files/input/list_content_1.txt" "test_files/expected/list_content_1_expected.txt"
restart_server
run_test "list_content_2" "test_files/input/list_content_2.txt" "test_files/expected/list_content_2_expected.txt"
restart_server
run_test "list_content_3" "test_files/input/list_content_3.txt" "test_files/expected/list_content_3_expected.txt"
restart_server
run_test "list_content_4" "test_files/input/list_content_4.txt" "test_files/expected/list_content_4_expected.txt"

restart_server
run_test "disconnect_1" "test_files/input/disconnect_1.txt" "test_files/expected/disconnect_1_expected.txt"
restart_server
run_test "disconnect_2" "test_files/input/disconnect_2.txt" "test_files/expected/disconnect_2_expected.txt"
restart_server
run_test "disconnect_3" "test_files/input/disconnect_3.txt" "test_files/expected/disconnect_3_expected.txt"

kill $SERVER_PID 2>/dev/null
kill $LOGGER_PID 2>/dev/null
kill $WEB_SERVICE_PID 2>/dev/null