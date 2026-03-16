#!/bin/bash

# NOTE: This script runs inside the Rocky builder container

set -e
set -u

NAME="usbmon-exporter"
RPMROOT="/build"
VERSION="0.2.0"

test -d ${RPMROOT}/SOURCES || mkdir -p ${RPMROOT}/SOURCES

tar -czf "${RPMROOT}/SOURCES/${NAME}-${VERSION}.tar.gz" \
    --exclude="${NAME}.spec" \
    --exclude="SOURCES" \
    --exclude="SPECS" \
    --exclude="RPMS" \
    --exclude="SRPMS" \
    --exclude="BUILD" \
    --exclude=".git" \
    --exclude=".mypy_cache" \
    --exclude="dist" \
    --exclude="todo" \
    --exclude="BUILD" \
    --exclude="BUILDROOT" \
    --transform "s!^\./!${NAME}-${VERSION}/!" \
    -C /src .

rpmbuild \
    --ba \
    --define "_topdir ${RPMROOT}" \
    --define "_sourcedir ${RPMROOT}/SOURCES" \
    "${NAME}.spec"

if command -v rpmlint >/dev/null 2>&1; then
    # Find RPM files to check
    rpm_files=()
    while IFS= read -r -d '' file; do
        rpm_files+=("$file")
    done < <(find "$RPMROOT/RPMS" -name '*.rpm' -print0)

    if [[ ${#rpm_files[@]} -gt 0 ]]; then
        echo "Running rpmlint on RPMs..."
        # rpmlint 1.x (Rocky 8) doesn't support --strict or config files well
        # rpmlint 2.x+ (Rocky 9) supports --strict but we don't use it for vendored packages
        # The warnings for vendored packages are expected and safe to ignore
        rpmlint "${rpm_files[@]}" || true
    fi
fi

find "$RPMROOT/RPMS" \
    -name '*.rpm' \
    -exec cp {} /build/dist/ \;
