#!/usr/bin/env bash
set -euo pipefail

APP_NAME="notecli"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"
BIN_DIR="${HOME}/.local/bin"
BIN_PATH="${BIN_DIR}/${APP_NAME}"

python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r "${PROJECT_DIR}/requirements.txt"

mkdir -p "${BIN_DIR}"
cat > "${BIN_PATH}" <<EOF
#!/usr/bin/env bash
exec "${VENV_DIR}/bin/python" "${PROJECT_DIR}/notecli.py" "\$@"
EOF
chmod +x "${BIN_PATH}"

echo "Installed ${APP_NAME} -> ${BIN_PATH}"
case ":${PATH}:" in
  *":${BIN_DIR}:"*) ;;
  *)
    echo "Add this to your shell profile if ${APP_NAME} is not found:"
    echo "  export PATH=\"${BIN_DIR}:\$PATH\""
    ;;
esac
