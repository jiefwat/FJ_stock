#!/bin/sh
set -eu

source_path=${1:-/opt/stock-ts/data/imports/tdx_snapshots.json}
target_path=${2:-/opt/aster-market/data/market_snapshot.json}

if [ ! -f "$source_path" ]; then
  echo "snapshot source does not exist: $source_path" >&2
  exit 1
fi

mkdir -p "$(dirname "$target_path")"
temporary_path="${target_path}.link.$$"
trap 'rm -f "$temporary_path"' EXIT HUP INT TERM
ln -s "$source_path" "$temporary_path"
mv -f "$temporary_path" "$target_path"
trap - EXIT HUP INT TERM
