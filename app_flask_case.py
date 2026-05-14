# app_flask_case.py

import os
import sys
import socket
import webbrowser
import threading
from flask import Flask, render_template_string, request

# ==========================================================
# PLAYWRIGHT PATH (compatible con EXE futuro)
# ==========================================================

if getattr(sys, "frozen", False):

    base_path = os.path.dirname(sys.executable)

    # 🔥 buscar en carpeta normal
    playwright_path = os.path.join(base_path, "ms-playwright")

    # 🔥 fallback por si PyInstaller usa _internal
    if not os.path.exists(playwright_path):
        playwright_path = os.path.join(base_path, "_internal", "ms-playwright")

    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = playwright_path

    print("PLAYWRIGHT PATH:", playwright_path)

# ==========================================================
# IMPORTS
# ==========================================================

import asyncio
import config

from form_html_case import HTML_FORM
from web_case_launcher import ejecutar_proceso

app = Flask(__name__)

# ==========================================================
# DETECTAR AMBIENTE
# ==========================================================

ES_EXE = getattr(sys, "frozen", False)
AMBIENTE_GLOBAL = "PROD" if ES_EXE else "DEV"

print("Ambiente detectado:", AMBIENTE_GLOBAL)

# ==========================================================
# RUTA PRINCIPAL
# ==========================================================

@app.route("/", methods=["GET", "POST"])
def index():

    mensaje = ""

    if request.method == "POST":

        # ======================================
        # FORM DATA
        # ======================================

        num_hilos = 1

        business_mode = request.form.get(
            "business_mode",
            "summary"
        )

        case_summary = (
            request.form.get("case_summary", "")
            .strip()
        )

        underwriting_link = (
            request.form.get("underwriting_link", "")
            .strip()
        )

        imagen = request.files.get("imagen")

        # ======================================
        # DEV MODE
        # ======================================

        if AMBIENTE_GLOBAL == "DEV":

            admin_user = config.USERNAME
            admin_pass = config.PASSWORD

        # ======================================
        # PROD MODE
        # ======================================

        else:

            admin_user = request.form.get("admin_user")
            admin_pass = request.form.get("admin_pass")

            if not admin_user or not admin_pass:

                mensaje = "⚠️ All fields are required"

                return render_template_string(
                    HTML_FORM,
                    mensaje=mensaje,
                    ambiente=AMBIENTE_GLOBAL
                )

        # ======================================
        # SAVE IMAGE
        # ======================================

        ruta_imagen = None

        if imagen:

            carpeta = config.OUTPUT_FOLDER

            os.makedirs(carpeta, exist_ok=True)

            ruta_imagen = os.path.join(
                carpeta,
                imagen.filename
            )

            imagen.save(ruta_imagen)

        # ======================================
        # SAVE EXCEL
        # ======================================

        excel_file = request.files.get("excel_file")

        ruta_excel = None

        if excel_file:

            ruta_excel = os.path.join(
                config.OUTPUT_FOLDER,
                excel_file.filename
            )

            excel_file.save(ruta_excel)

        # ======================================
        # BUSINESS MODEL VALIDATION
        # ======================================

        if business_mode == "summary" and not case_summary:

            mensaje = "⚠️ Summary cannot be empty"

            return render_template_string(
                HTML_FORM,
                mensaje=mensaje,
                ambiente=AMBIENTE_GLOBAL
            )

        if business_mode == "link" and not underwriting_link:

            mensaje = "⚠️ Underwriting link cannot be empty"

            return render_template_string(
                HTML_FORM,
                mensaje=mensaje,
                ambiente=AMBIENTE_GLOBAL
            )

        # ======================================
        # EXECUTE BOT
        # ======================================

        try:

            loop = asyncio.new_event_loop()

            asyncio.set_event_loop(loop)

            mensaje = loop.run_until_complete(

                ejecutar_proceso(
                    admin_user,
                    admin_pass,
                    ruta_excel,
                    case_summary,
                    underwriting_link,
                    ruta_imagen,
                    num_hilos
                )

            )

        except Exception as e:

            mensaje = f"❌ Error:\n{str(e)}"

    return render_template_string(
        HTML_FORM,
        mensaje=mensaje,
        ambiente=AMBIENTE_GLOBAL
    )

# ==========================================================
# FIND FREE PORT
# ==========================================================

def find_free_port(start_port=5000, max_tries=20):

    for port in range(start_port, start_port + max_tries):

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port

    raise RuntimeError("No free ports available")

# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    port = find_free_port()

    def open_browser():

        webbrowser.open_new(
            f"http://127.0.0.1:{port}"
        )

    threading.Timer(1, open_browser).start()

    app.run(
        debug=(AMBIENTE_GLOBAL == "DEV"),
        use_reloader=False,
        port=port
    )