#!/bin/bash

rm -rf cmake-build-release

cmake -S ./ -B cmake-build-release -DCMAKE_BUILD_TYPE=Release
cmake --build cmake-build-release
make -C cmake-build-release