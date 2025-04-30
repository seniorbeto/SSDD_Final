cmake_minimum_required(VERSION 3.10)
project(SSDD_Final C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED True)
add_compile_options(-Wall -Wextra -Werror -pedantic -pedantic-errors -Wconversion -Wsign-conversion -pthread -fPIC)

include_directories(/usr/include/tirpc)

add_executable(server server.c claves.c lines.c ../logger/logger_clnt.c ../logger/logger_xdr.c)
target_link_libraries(server PRIVATE pthread rt tirpc)

# Esto es para desactivar los warnings de las librerías de logger
set_source_files_properties(
        ../logger/logger_clnt.c ../logger/logger_xdr.c
        PROPERTIES COMPILE_FLAGS "-w"
)