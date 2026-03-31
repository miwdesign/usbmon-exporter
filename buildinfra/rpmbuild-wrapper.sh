#!/bin/bash

# NOTE: This script runs inside the Rocky builder container

set -e
set -u

NAME="usbmon-exporter"
RPMROOT="/build"
VERSION="0.2.0"

test -d ${RPMROOT}/SOURCES || mkdir -p ${RPMROOT}/SOURCES

# FIXME: The long list of manual exclusions is clunky; there must be a better
#        way to manage this.
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
