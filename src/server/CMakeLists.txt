cmake_minimum_required(VERSION 3.10)
project(SSDD_Final C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED True)
add_compile_options(-Wall -Wextra -Werror -pedantic -pedantic-errors -Wconversion -Wsign-conversion -pthread -fPIC)


add_executable(server server.c claves.c lines.c)