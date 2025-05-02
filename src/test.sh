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

  echo -e -n "${YELLOW}Running test '$test_name'...${NC} "

  # Ejecutar el cliente, redirigiendo entrada desde $input_file y guardando salida
  python3 client/client.py -s $SERVER_IP -p $SERVER_PORT < "$input_file" > "$output_file" 2>/dev/null

  normalize_output() {
    sed -E 's/[0-9]{4,5}/PORT/g' "$1" | \
    sed -E 's,(FILE).*,\1 PATH,g'
  }

  if diff -b -B -q <(normalize_output "$output_file") <(normalize_output "$expected_file") >/dev/null; then
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

echo
echo -e "${BLUE}GET FILE & GET MULTIFILE DOWNLOAD TESTS. PREPARING SCENARIOS...${NC}"
echo

FILE_PATH="$(pwd)/temp.txt"
cat > $FILE_PATH <<EOF
I met a traveller from an antique land
Who said: Two vast and trunkless legs of stone
Stand in the desert. Near them, on the sand,
Half sunk, a shattered visage lies, whose frown,
And wrinkled lip, and sneer of cold command,
Tell that its sculptor well those passions read
Which yet survive, stamped on these lifeless things,
The hand that mocked them and the heart that fed.
And on the pedestal these words appear:
"My name is Ozymandias, king of kings:
Look on my works, ye Mighty, and despair!"
Nothing beside remains. Round the decay
Of that colossal wreck, boundless and bare
The lone and level sands stretch far away
EOF

# Creamos un input dinámico para el cliente A (publicador)
cat > test_files/input/scenario_a.txt <<EOF
register user_a
connect user_a
publish $FILE_PATH fichero con descripcion
EOF

# Creamos un input dinámico para el cliente B (publicador)
cat > test_files/input/scenario_b.txt <<EOF
register user_b
connect user_b
publish $FILE_PATH fichero con descripcion 2
EOF

# Creamos un input dinámico para el cliente C (descargador)
cat > test_files/input/scenario_c.txt <<EOF
register user_c
connect user_c
get_file user_a $FILE_PATH ./temp_download.txt
get_multifile temp.txt ./temp_multidownload.txt
EOF

restart_server

# Lanzamos el cliente A con --input-file (queda colgado esperando al no tener quit)
python3 client/client.py -s $SERVER_IP -p $SERVER_PORT --input-file test_files/input/scenario_a.txt \
    > test_files/output/scenario_a.output 2>/dev/null &
CLIENT_A_PID=$!

sleep 1  # Esperamos a que A publique

# Lanzamos el cliente B con --input-file
python3 client/client.py -s $SERVER_IP -p $SERVER_PORT --input-file test_files/input/scenario_b.txt \
    > test_files/output/scenario_b.output 2>/dev/null &
CLIENT_B_PID=$!

sleep 1  # Esperamos a que B publique

# Lanzamos el cliente C con --input-file
python3 client/client.py -s $SERVER_IP -p $SERVER_PORT --input-file test_files/input/scenario_c.txt \
    > test_files/output/scenario_c.output 2>/dev/null &
CLIENT_C_PID=$!

echo -e "${YELLOW}Waiting for download to finish...${NC}"

timeout=10
elapsed=0
interval=0.5

# Esperamos que se descargue el fichero con get_file
while true; do
    if [[ -f temp_download.txt ]] && [[ -f temp.txt ]]; then
        size_orig=$(stat --format=%s temp.txt)
        size_down=$(stat --format=%s temp_download.txt)
        if [[ "$size_orig" -eq "$size_down" ]]; then
            break  # Descarga completada
        fi
    fi

    if (( $(echo "$elapsed >= $timeout" | bc -l) )); then
        echo -e "${RED}Timeout reached without completing download.${NC}"
        break
    fi

    sleep $interval
    elapsed=$(echo "$elapsed + $interval" | bc)
done

# Esperamos que se descargue el fichero con get_multifile
while true; do
    if [[ -f temp_multidownload.txt ]] && [[ -f temp.txt ]]; then
        size_orig=$(stat --format=%s temp.txt)
        size_down=$(stat --format=%s temp_multidownload.txt)
        if [[ "$size_orig" -eq "$size_down" ]]; then
            break  # Descarga completada
        fi
    fi

    if (( $(echo "$elapsed >= $timeout" | bc -l) )); then
        echo -e "${RED}Timeout reached without completing download.${NC}"
        break
    fi

    sleep $interval
    elapsed=$(echo "$elapsed + $interval" | bc)
done

kill $CLIENT_A_PID 2>/dev/null
kill $CLIENT_B_PID 2>/dev/null
kill $CLIENT_C_PID 2>/dev/null

# Comprobamos el fichero descargado con el origingal
# DE MANERA ESTRICTA
if diff -q temp.txt temp_download.txt >/dev/null; then
    echo -e "${GREEN}GET FILE OK.${NC}"
else
    echo -e "${RED}GET FILE Fail.${NC}"
fi

if diff -q temp.txt temp_multidownload.txt >/dev/null; then
    echo -e "${GREEN}GET MULTIFILE OK.${NC}"
else
    echo -e "${RED}GET MULTIFILE Fail.${NC}"
fi

# Limpiamos ficheros temporales
rm -f test_files/input/scenario_a.txt
rm -f test_files/input/scenario_b.txt
rm -f test_files/input/scenario_c.txt
rm -f temp.txt temp_download.txt temp_multidownload.txt

kill $SERVER_PID 2>/dev/null
kill $LOGGER_PID 2>/dev/null
kill $WEB_SERVICE_PID 2>/dev/null

echo
echo "Finished! All output files are available in test_files/output"
echo "Logs from server, web service and rpc-logger are available in test_files/output/logs"