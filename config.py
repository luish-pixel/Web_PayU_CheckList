#config.py
# ==========================================================
# CONFIGURATION FILE
# Handles DEV vs PROD paths
# ==========================================================

import os
import sys
from pathlib import Path

# ==========================================================
# DETECT ENVIRONMENT
# ==========================================================

IS_EXE = getattr(sys, "frozen", False)

# Número de workers para búsquedas en paralelo (1 = secuencial, 2 = paralelo)
SEARCH_WORKERS = 1

# Número de workers para procesos de IA en paralelo (1 = secuencial, 2 = paralelo)
AI_WORKERS = 2

# ==========================================================
# BASE PATH (CLAVE 🔥)
# ==========================================================

if IS_EXE:
    # Cuando corre como .exe (PyInstaller)
    BASE_DIR = Path(sys._MEIPASS)  # 🔥 correcto para archivos internos
else:
    # Cuando corre como script
    BASE_DIR = Path(__file__).resolve().parent

print(f"📁 BASE_DIR: {BASE_DIR}")

# ==========================================================
# OUTPUT FOLDER
# ==========================================================

if not IS_EXE:

    OUTPUT_FOLDER = Path(
        r"G:\My Drive\Doc-Operacion\Web_PayU_CheckList\Outputs"
    )

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    print(f"🔧 DEV MODE - Output folder: {OUTPUT_FOLDER}")

else:

    EXECUTION_PATH = Path(sys.executable).parent

    OUTPUT_FOLDER = EXECUTION_PATH / "archivos"

    OUTPUT_FOLDER.mkdir(exist_ok=True)

    print(f"🚀 PROD MODE - Output folder: {OUTPUT_FOLDER}")

# ==========================================================
# PROMPT PATH (🔥 LO NUEVO IMPORTANTE)
# ==========================================================

if not IS_EXE:
    PROMPT_PATH = Path(
        r"G:\My Drive\Doc-Operacion\Web_PayU_CheckList\Templates\Prompts_AI\Prompt_CRPs.txt"
    )
else:
    PROMPT_PATH = BASE_DIR / "Prompts_AI" / "Prompt_CRPs.txt"

print(f"🧠 PROMPT_PATH: {PROMPT_PATH}")

# ==========================================================
# THREAD CONFIGURATION
# ==========================================================

DEFAULT_THREADS = 1
MAX_THREADS = 8

# ==========================================================
# DEV CREDENTIALS (solo DEV)
# ==========================================================

USERNAME = "luis.hurtado.adminpayu"
PASSWORD = "WzF@yvB3$4pFh$"

#SF_USER = "luish@rapyd.net"
#SF_PASS = "Rapydrapyd2025*"
SF_USER = "luis.hurtado@payu.com"
SF_PASS = "Rapydrapyd2025***"