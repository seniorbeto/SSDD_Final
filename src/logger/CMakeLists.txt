cmake_minimum_required(VERSION 3.10)
project(ssdd_logger C)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED True)

include_directories(/usr/include/tirpc)

add_executable(logger logger.c logger_svc.c logger_xdr.c)
target_link_libraries(logger PRIVATE pthread rt tirpc)