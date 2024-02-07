#!/bin/bash

# Author : James Nock (@Jpnock)
# Year   : 2023

set -uo pipefail
shopt -s globstar

if [ "${DONT_CLEAN:-}" != "1" ]; then
    make clean
fi

if [ "${COVERAGE:-}" == "1" ]; then
    rm -rf coverage
    set -e
    make with_coverage
    set +e
else
    set -e
    make bin/c_compiler
    set +e
fi

mkdir -p bin
mkdir -p bin/output

TOTAL=0
PASSING=0

J_UNIT_OUTPUT_FILE="./bin/junit_results.xml"
printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>' >"${J_UNIT_OUTPUT_FILE}"
printf '%s\n' '<testsuite name="Integration test">' >>"${J_UNIT_OUTPUT_FILE}"

SPECIFIC_FOLDER="${1:-**}"
printf '\n'

for DRIVER in compiler_tests/${SPECIFIC_FOLDER}/*_driver.c; do
    ((TOTAL++))

    TO_ASSEMBLE="${DRIVER%_driver.c}.c"
    echo "${TO_ASSEMBLE}"

    if ! TEST_RESULT=$(./scripts/test_single.sh "${DRIVER}"); then
        echo "${TEST_RESULT}"
        printf '%s\n' "<error type=\"error\" message=\"${TEST_RESULT}\">${TEST_RESULT}</error>" >>"${J_UNIT_OUTPUT_FILE}"
        printf '%s\n' "</testcase>" >>"${J_UNIT_OUTPUT_FILE}"
    else
        ((PASSING++))
        echo "${TEST_RESULT}"
        printf '%s\n' "</testcase>" >>"${J_UNIT_OUTPUT_FILE}"
    fi

    printf '\n'
done

if [ "${COVERAGE:-}" == "1" ]; then
    make coverage
fi

printf "\nPassing %d/%d tests\n" "${PASSING}" "${TOTAL}"
printf '%s\n' '</testsuite>' >>"${J_UNIT_OUTPUT_FILE}"
