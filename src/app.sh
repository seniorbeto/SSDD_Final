#!/usr/bin/env bash
set -euo pipefail

#
# manage.sh — Orquesta build & clean de SSDD_P3 con colores y mensajes llamativos
#
# Uso:
#   ./manage.sh -b    Build all C components (logger y server)
#   ./manage.sh -c    Clean all build artifacts
#   ./manage.sh -h    Show this help
#

# Colores ANSI
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # Sin color

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Función para imprimir ayuda en color
usage() {
  echo -e "${BLUE}Usage:${NC} $0 [options]"
  echo
  echo -e "  ${YELLOW}-b${NC}   Build all C components (logger y server)"
  echo -e "  ${YELLOW}-c${NC}   Clear all build artifacts"
  echo -e "  ${YELLOW}-h${NC}   Show this help"
  echo
  exit 1
}

# Descripción de ejecución de cada componente
run_usage() {
  echo -e "${BLUE}Execute services this way:${NC}"
  echo -e "  ${GREEN}logger:${NC}      ./logger/cmake-build-release/logger"
  echo -e "  ${GREEN}server:${NC}      env LOG_RPC_IP=<${YELLOW}rpc_service_ip${NC}> ./server/cmake-build-release/server -p <${YELLOW}port${NC}>"
  echo -e "  ${GREEN}web_service:${NC} python3 web_server/web_server.py"
  echo -e "  ${GREEN}client:${NC}      python3 client/client.py -s <${YELLOW}server_ip${NC} > -p <${YELLOW}port${NC}>"
  echo
  exit 1
}

# Función de ayuda para ejecutar un paso de build en silencio con log
# args: 1=Descripción, 2=Logfile, 3...=comando y args
run_build_step() {
  local desc="$1"; shift
  local logfile="$1"; shift
  local cmd=( "$@" )

  echo -e "${BLUE}=== ${desc} ===${NC}"
  if "${cmd[@]}" >"$logfile" 2>&1; then
    echo -e "${GREEN}✔ ${desc}: success${NC}"
    rm -f "$logfile"
  else
    echo -e "${RED}✖ ${desc}: FAILED! See ${logfile}${NC}"
    exit 1
  fi
  echo
}

build() {
  echo -e "${BLUE}--- Building components ---${NC}"

  # Logger
  pushd "$ROOT/logger" >/dev/null
    run_build_step "Generating RPC stubs (logger)" gen_rpc.log rpcgen logger.x
    run_build_step "Building logger" logger_build.log ./compile.sh
  popd >/dev/null

  # Server
  pushd "$ROOT/server" >/dev/null
    run_build_step "Building server" server_build.log ./compile.sh
  popd >/dev/null

  echo -e "${GREEN}=== Build complete ===${NC}\n"
  run_usage
}

clean() {
  echo -e "${BLUE}--- Cleaning build artifacts ---${NC}"

  # Logger
  pushd "$ROOT/logger" >/dev/null
    rm -rf cmake-build-release
    rm -f logger.h logger_clnt.c logger_svc.c logger_xdr.c gen_rpc.log logger_build.log
  popd >/dev/null

  # Server
  pushd "$ROOT/server" >/dev/null
    rm -rf cmake-build-release
    rm -f server_build.log
  popd >/dev/null

  # All __pycache__ folders
  find "$ROOT" -type d -name "__pycache__" -exec rm -rf {} +

  echo -e "${GREEN}=== Clean complete ===${NC}"
}

# --- Main CLI parsing ---
if [ $# -eq 0 ]; then
  usage
fi

BUILD=false
CLEAR=false

while getopts "bch" opt; do
  case "${opt}" in
    b) BUILD=true ;;
    c) CLEAR=true ;;
    h|*) usage ;;
  esac
done

$BUILD && build
$CLEAR && clean
