#!/bin/bash

# NOTE: This script runs inside the Rocky builder container

set -e
set -u

NAME="usbmon-exporter"
RPMROOT="/build"

rpmbuild \
    --bb \
    --define "_topdir ${RPMROOT}" \
    --define "_sourcedir /src" \
    "/src/${NAME}.spec"

if command -v rpmlint >/dev/null 2>&1; then
    rpm_files=()
    while IFS= read -r -d '' file; do
        rpm_files+=("$file")
    done < <(find "$RPMROOT/RPMS" -name '*.rpm' -print0)

    if [[ ${#rpm_files[@]} -gt 0 ]]; then
        echo "Running rpmlint on RPMs..."
        RPMLINTRC="/src/${NAME}.rpmlintrc"
        if [[ -f "$RPMLINTRC" ]]; then
            rpmlint -f "$RPMLINTRC" "${rpm_files[@]}"
        else
            rpmlint "${rpm_files[@]}"
        fi
    fi
fi

find "$RPMROOT/RPMS" \
    -name '*.rpm' \
    -exec cp {} /build/dist/ \;
