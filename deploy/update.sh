#!/bin/bash
# Run every minute by stock-update.timer: deploy when GitHub master has a new commit.
# Wrapped in main() so bash parses it fully before `git reset` can rewrite this file.
main() {
  set -euo pipefail
  export UV_PYTHON_INSTALL_DIR=/opt/uv-python
  local marker=/var/lib/stock-deployed
  cd /opt/app
  git fetch -q origin master
  local target
  target=$(git rev-parse FETCH_HEAD)
  # compare against the last *successful* deploy, so a failed sync is retried next minute
  [ "$(cat "$marker" 2>/dev/null)" = "$target" ] && return 0
  git reset -q --hard "$target"
  uv sync --frozen --no-dev
  systemctl restart stock
  echo "$target" > "$marker"
  echo "deployed $(git rev-parse --short HEAD)"
}
main "$@"
