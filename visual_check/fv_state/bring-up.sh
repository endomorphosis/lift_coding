#!/usr/bin/env bash
# Functional-verification stack bring-up (idempotent; loopback only).
# Launches: ipfs_accelerate upstream :9000, kit adapter :8014,
# datasets adapter :3002, accelerate adapter :3003, vite desktop :3001.
# Logs and pidfiles land in visual_check/fv_state/ (workspace-persistent).
set -u
ROOT=/home/hatch/workspace/lift_coding
SK=$ROOT/swissknife
STATE=$ROOT/visual_check/fv_state
PY=$ROOT/.venv/bin/python
mkdir -p "$STATE"
export no_proxy=localhost,127.0.0.1 NO_PROXY=localhost,127.0.0.1

alive() { curl -s -m 3 -o /dev/null "http://127.0.0.1:$1/" ; }
port_up() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && exec 3>&- 3<&-; }

launch() { # name, workdir, logfile, cmd...
  local name=$1 wd=$2 log=$3; shift 3
  ( cd "$wd" && setsid nohup "$@" > "$STATE/$log" 2>&1 < /dev/null & echo $! > "$STATE/$name.pid" )
  echo "launched $name"
}

port_up 9000 || launch fv-accel-upstream "$ROOT" accel-upstream.log \
  env PYTHONPATH=$ROOT/external/ipfs_accelerate "$PY" -m ipfs_accelerate_py.mcp_server \
  --port 9000 --host 127.0.0.1 --fastapi
sleep 6
port_up 8014 || launch fv-kit-adapter "$SK" kit-adapter.log \
  env PYTHON=$PY node scripts/start-ipfs-kit-mcp-compat.cjs
port_up 3002 || launch fv-datasets-adapter "$SK" datasets-adapter.log \
  env IPFS_DATASETS_PY_ROOT=$ROOT/external/ipfs_datasets node scripts/start-ipfs-datasets-mcp-compat.cjs
port_up 3003 || launch fv-accel-adapter "$SK" accel-adapter.log \
  node scripts/start-ipfs-accelerate-mcp-compat.cjs
sleep 10
port_up 3001 || launch fv-vite "$SK" vite.log \
  ./node_modules/.bin/vite dev --config vite.web.config.ts --port 3001 --host 127.0.0.1
sleep 20
echo "--- port state ---"
for p in 9000 8014 3002 3003 3001; do
  if port_up $p; then echo "$p UP"; else echo "$p DOWN"; fi
done
