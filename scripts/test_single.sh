#!/bin/bash

set -uo pipefail

fail_testcase() {
    echo -e "\t> ${1}"
    printf '\n'
    exit 72
}

DRIVER="$1"
TO_ASSEMBLE="${DRIVER%_driver.c}.c"
LOG_PATH="${TO_ASSEMBLE#compiler_tests/}"
LOG_PATH="./bin/output/${LOG_PATH%.c}"
BASE_NAME="$(basename "${LOG_PATH}")"
LOG_FILE_BASE="${LOG_PATH}/${BASE_NAME}"
rm -rf "${LOG_PATH}"
mkdir -p "${LOG_PATH}"

OUT="${LOG_FILE_BASE}"

set -e
make --silent
set +e

ASAN_OPTIONS=exitcode=0 timeout --foreground 15s \
    ./bin/c_compiler \
    -S "${TO_ASSEMBLE}" \
    -o "${OUT}.s" \
    2>"${LOG_FILE_BASE}.compiler.stderr.log" \
    >"${LOG_FILE_BASE}.compiler.stdout.log"
if [ $? -ne 0 ]; then
    fail_testcase "Failed to compile testcase: \n\t ${LOG_FILE_BASE}.compiler.stderr.log \n\t ${LOG_FILE_BASE}.compiler.stdout.log \n\t ${OUT}.s \n\t ${OUT}.s.printed"
fi

timeout --foreground 15s \
    riscv64-unknown-elf-gcc \
    -march=rv32imfd \
    -mabi=ilp32d \
    -o "${OUT}.o" \
    -c "${OUT}.s" \
    2>"${LOG_FILE_BASE}.assembler.stderr.log" \
    >"${LOG_FILE_BASE}.assembler.stdout.log"
if [ $? -ne 0 ]; then
    fail_testcase "Failed to assemble: \n\t ${LOG_FILE_BASE}.compiler.stderr.log \n\t ${LOG_FILE_BASE}.compiler.stdout.log \n\t ${LOG_FILE_BASE}.assembler.stderr.log \n\t ${LOG_FILE_BASE}.assembler.stdout.log \n\t ${OUT}.s \n\t ${OUT}.s.printed"
fi

timeout --foreground 15s riscv64-unknown-elf-gcc \
    -march=rv32imfd \
    -mabi=ilp32d \
    -static \
    -o "${OUT}" \
    "${OUT}.o" "${DRIVER}" \
    2>"${LOG_FILE_BASE}.linker.stderr.log" \
    >"${LOG_FILE_BASE}.linker.stdout.log"
if [ $? -ne 0 ]; then
    fail_testcase "Failed to link driver: \n\t ${LOG_FILE_BASE}.compiler.stderr.log \n\t ${LOG_FILE_BASE}.compiler.stdout.log \n\t ${LOG_FILE_BASE}.linker.stderr.log \n\t ${LOG_FILE_BASE}.linker.stdout.log \n\t ${OUT}.s \n\t ${OUT}.s.printed"
fi

timeout --foreground 15s \
    spike pk "${OUT}" \
    >"${LOG_FILE_BASE}.simulation.log"
if [ $? -ne 0 ]; then
    fail_testcase "Failed to simulate: simulation did not exit with code 0: \n\t ${LOG_FILE_BASE}.compiler.stderr.log \n\t ${LOG_FILE_BASE}.compiler.stdout.log \n\t ${LOG_FILE_BASE}.simulation.log \n\t ${OUT}.s \n\t ${OUT}.s.printed"
else
    echo -e "\t> Pass\n"
    exit 0
fi
