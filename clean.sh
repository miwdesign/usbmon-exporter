#!/usr/bin/env bash

# clean.sh - Clean generated build artifacts
# Usage: ./clean.sh [--all] [--images] [--rpms] [--build-dirs]

set -e

NAME="usbmon-exporter"
THIS_DIR=$(dirname "$(readlink -f "$0" 2> /dev/null || echo "$0")")

CLEAN_IMAGES=false
CLEAN_RPMS=false
CLEAN_BUILD_DIRS=false
CLEAN_ALL=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --all)
            CLEAN_ALL=true
            shift
            ;;
        --images)
            CLEAN_IMAGES=true
            shift
            ;;
        --rpms)
            CLEAN_RPMS=true
            shift
            ;;
        --build-dirs)
            CLEAN_BUILD_DIRS=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--all] [--images] [--rpms] [--build-dirs]"
            echo ""
            echo "Clean generated build artifacts."
            echo ""
            echo "Options:"
            echo "  --all        Clean everything"
            echo "  --images     Clean builder container images"
            echo "  --rpms       Clean built RPMs from dist/"
            echo "  --build-dirs Clean RPM build directories"
            echo "  --help       Show this help message"
            echo ""
            echo "Default: Clean images and RPMs"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Default action if no specific options given
if [[ "$CLEAN_ALL" == "false" && "$CLEAN_IMAGES" == "false" && "$CLEAN_RPMS" == "false" && "$CLEAN_BUILD_DIRS" == "false" ]]; then
    CLEAN_IMAGES=true
    CLEAN_RPMS=true
elif [[ "$CLEAN_ALL" == "true" ]]; then
    CLEAN_IMAGES=true
    CLEAN_RPMS=true
    CLEAN_BUILD_DIRS=true
fi

if [[ "$CLEAN_IMAGES" == "true" ]]; then
    echo "Removing builder container images..."
    for rhel_version in 8 9; do
        for arch in amd64 aarch64; do
            IMAGE_NAME="${NAME}-builder:rocky${rhel_version}-${arch}"
            if podman image exists "localhost/$IMAGE_NAME" 2>/dev/null; then
                # shellcheck disable=SC2015
                podman rmi "localhost/$IMAGE_NAME" 2>/dev/null && echo "  Removed: $IMAGE_NAME" || true
            fi
        done
    done
fi

if [[ "$CLEAN_RPMS" == "true" ]]; then
    echo "Removing built RPMs..."
    if [[ -d "$THIS_DIR/dist" ]]; then
        find "$THIS_DIR/dist" -name '*.rpm' -delete && echo "  Removed: dist/*.rpm"
    fi
fi

if [[ "$CLEAN_BUILD_DIRS" == "true" ]]; then
    echo "Removing RPM build directories..."
    for dir in BUILDROOT RPMS SOURCES SPECS SRPMS; do
        if [[ -d "$THIS_DIR/$dir" ]]; then
            rm -rf "${THIS_DIR:?}/$dir" && echo "  Removed: $dir/"
        fi
    done
fi
