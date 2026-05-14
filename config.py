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

# Number of workers for parallel searches (1 = sequential, 2 = parallel)
SEARCH_WORKERS = 1

# ==========================================================
# BASE PATH
# ==========================================================

if IS_EXE:
    # Running as .exe (PyInstaller)
    BASE_DIR = Path(sys._MEIPASS)
else:
    # Running as script
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
# PROMPT PATHS
# ==========================================================

if not IS_EXE:
    PROMPT_GENERAL_PATH = Path(
        r"G:\My Drive\Doc-Operacion\Web_PayU_CheckList\Templates\Prompts_AI\Promt_AI_General.txt"
    )
    PROMPT_SPECIFIC_PATH = Path(
        r"G:\My Drive\Doc-Operacion\Web_PayU_CheckList\Templates\Prompts_AI\Promt_AI_Especifico.txt"
    )
else:
    PROMPT_GENERAL_PATH  = BASE_DIR / "Prompts_AI" / "Promt_AI_General.txt"
    PROMPT_SPECIFIC_PATH = BASE_DIR / "Prompts_AI" / "Promt_AI_Especifico.txt"

print(f"🧠 PROMPT_GENERAL_PATH: {PROMPT_GENERAL_PATH}")
print(f"🧠 PROMPT_SPECIFIC_PATH: {PROMPT_SPECIFIC_PATH}")

# ==========================================================
# DEV CREDENTIALS (DEV only)
# ==========================================================

USERNAME = "luis.hurtado.adminpayu"
PASSWORD = "WzF@yvB3$4pFh$"