#!/usr/bin/env bash

set -e

NAME="usbmon-exporter"
TARGET_ARCH="amd64"
TARGET_RHEL_VERSION="8"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --arch)
            TARGET_ARCH="$2"
            shift 2
            ;;
        --rhel)
            TARGET_RHEL_VERSION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--arch amd64|aarch64] [--rhel 8|9]"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done
BUILDER_IMAGE="${NAME}-builder:rocky${TARGET_RHEL_VERSION}-${TARGET_ARCH}"
CONTAINER_FILE="${THIS_DIR}/buildinfra/Containerfile.rocky${TARGET_RHEL_VERSION}"
TARGET_PLATFORM="linux/${TARGET_ARCH}"

# See https://gist.github.com/ptc-mrucci/61772387878ed53a6c717d51a21d9371
THIS_DIR=$(dirname "$(readlink -f "$0" 2> /dev/null || echo "$0")")

test -d "$THIS_DIR/dist" || mkdir -p "$THIS_DIR/dist"

if ! command -v podman >/dev/null 2>&1; then
    echo "FATAL: podman not found!" >&2
    exit 1
fi

if ! podman image exists "localhost/$BUILDER_IMAGE"; then
    podman build \
        --tag "$BUILDER_IMAGE" \
        --platform "${TARGET_PLATFORM}" \
        --file "${CONTAINER_FILE}" \
        .
fi

podman run \
    --rm \
    --platform "${TARGET_PLATFORM}" \
    --volume "$PWD":/src:Z \
    --volume "$THIS_DIR/buildinfra/rpmbuild-wrapper.sh":/bin/build:Z \
    --volume "$THIS_DIR/dist":/build/dist:Z \
    "$BUILDER_IMAGE"

echo "Build successful. RPMs built:"
find "$THIS_DIR/dist" -name "*.rpm" -print
