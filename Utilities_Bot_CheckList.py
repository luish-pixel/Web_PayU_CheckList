#Utilities_Bot_CheckList.py

# ==========================================================
# LIBRERIAS
# ==========================================================

# 🔹 Standard library
import asyncio
import sys
import time
import os
import random
import sqlite3
import urllib.parse
import unicodedata
import html
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional

# 🔹 UI
import tkinter as tk
from tkinter import messagebox

# 🔹 Third-party
import pandas as pd
from playwright.async_api import async_playwright

# 🔹 ReportLab
from reportlab.platypus import ( SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether )
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 🔹 Local
import config

# ==========================================================
# GET BROWSER AND PAGE INSTANCE
# ==========================================================
async def get_browser_and_page(playwright, SF_Pass, SF_User, browser=None, page=None):

    if browser is None or page is None:

        browser = await playwright.chromium.launch(
            channel="chrome",
            headless=False
        )
        
        page = await browser.new_page()

        result = await access_SF_website(page, SF_Pass, SF_User)

        # 🔥 Manejo correcto
        if isinstance(result, tuple):
            status, message = result

            if not status:
                return False, browser, page, message
            else:
                return True, browser, page

        else:
            if result:
                return True, browser, page
            else:
                return False, browser, page

    else:
        return True, browser, page

# ==========================================================
# ACCESS SALESFORCE WEBSITE AND LOGIN
# ==========================================================
async def access_SF_website(page, SF_Pass, SF_User):

    try:
            #https://payu.lightning.force.com/lightning/r/Report/00OSl00000FOo1RMAT/view
        await page.goto(
            "https://payu.lightning.force.com/lightning/page/chatter",
            timeout=15000
        )

    except Exception:

        print("❌ Salesforce URL could not be accessed. Check VPN.")
        sys.exit(0)           
    
    try:

        # 🔥 NUEVO: botón Google
        google_btn = page.locator(
            "button:has-text('Google Prod (Rapyd)')"
        )

        okta_btn = page.locator(
            "#idp_section_buttons button",
            has_text="OKTA Production"
        )

        identifier_input = page.locator('input[name="identifier"]')

        MAX_ATTEMPTS = 3
        TIMEOUT_UI = 5000

        for attempt in range(1, MAX_ATTEMPTS + 1):

            await asyncio.sleep(random.uniform(3, 10))
            
            print(f"🔄 Attempt {attempt}/{MAX_ATTEMPTS}")

            await page.wait_for_load_state("domcontentloaded")

            try:

                await page.wait_for_function(
                    """() =>
                    document.querySelector('#idp_section_buttons button') ||
                    document.querySelector('input[name="identifier"]')
                    """,
                    timeout=TIMEOUT_UI
                )

            except:
                pass

            # =====================================================
            # 🔥 GOOGLE LOGIN (PRIORIDAD)
            # =====================================================
            if await google_btn.count() > 0:

                print("🔐 Google (Rapyd) detected")

                await google_btn.wait_for(state="visible", timeout=15000)
                await google_btn.click(force=True)

                # ⚠️ Manejo de nueva pestaña
                context = page.context
                try:
                    new_page = await context.wait_for_event("page", timeout=10000)
                    await new_page.wait_for_load_state()
                    page = new_page
                    print("🆕 Switched to Google login tab")
                except:
                    print("➡️ Google opened in same tab")

                # =========================
                # EMAIL
                # =========================
                try:
                    email_input = page.locator("#identifierId")

                    await email_input.wait_for(state="visible", timeout=20000)
                    await email_input.fill(SF_User)

                    next_btn = page.locator("#identifierNext")
                    await next_btn.click()

                except Exception as e:
                    print(f"❌ Error in Google email step: {e}")
                    await page.screenshot(path="error_google_email.png")
                    return False

                # =====================================================
                # 🔥 VALIDACIÓN EMAIL INVÁLIDO (Try again)
                # =====================================================
                try:
                    error_btn = page.locator("#next")

                    await error_btn.wait_for(state="visible", timeout=3000)

                    print("❌ Invalid email detected (Google Try again)")
                    return False, "email invalido"

                except:
                    pass  # ✅ No apareció error → flujo normal
                
                
                # =========================
                # PASSWORD
                # =========================
                try:
                    password_input = page.locator('input[name="Passwd"]')

                    await password_input.wait_for(state="visible", timeout=20000)
                    await password_input.fill(SF_Pass)

                    next_btn = page.locator("#passwordNext")
                    await next_btn.click()
                    
                    

                except Exception as e:
                    print(f"❌ Error in Google password step: {e}")
                    await page.screenshot(path="error_google_password.png")
                    return False

                # =====================================================
                # 🔥 VALIDACIÓN PASSWORD INVÁLIDO
                # =====================================================
                try:
                    error_pass = page.locator('input[name="Passwd"][aria-invalid="true"]')

                    await error_pass.wait_for(state="visible", timeout=3000)

                    print("❌ Invalid password detected")
                    return  False, "password invalido"

                except:
                    pass  # ✅ Password correcto → sigue flujo
                
                break

            # =====================================================
            # OKTA LOGIN (SE MANTIENE)
            # =====================================================
            if await okta_btn.count() > 0:

                print("🔐 OKTA detected")

                await okta_btn.wait_for(state="visible", timeout=15000)
                await okta_btn.click(force=True)

                await identifier_input.wait_for(timeout=15000)
                await page.fill('input[name="identifier"]', SF_User)
                await page.keyboard.press("Enter")

                await page.locator(
                    'input[name="credentials.passcode"]'
                ).wait_for(timeout=15000)

                await page.fill(
                    'input[name="credentials.passcode"]',
                    SF_Pass
                )

                await page.keyboard.press("Enter")
                
                break

            # =====================================================
            # DIRECT LOGIN (SE MANTIENE)
            # =====================================================
            if await identifier_input.count() > 0:

                print("👤 Direct login detected")

                await identifier_input.wait_for(timeout=15000)
                await page.fill('input[name="identifier"]', SF_User)

                await page.keyboard.press("Enter")

                await page.locator(
                    'input[name="credentials.passcode"]'
                ).wait_for(timeout=15000)

                await page.fill(
                    'input[name="credentials.passcode"]',
                    SF_Pass
                )

                await page.keyboard.press("Enter")

                break

            print("⏳ Interface not ready yet...")

        else:

            print("❌ Salesforce login interface not recognized")
            await page.screenshot(path="error_login_salesforce.png")
            return False

        # =====================================================
        # 2FA (SIN CAMBIOS)
        # =====================================================
        result = await authentication_flow(page)

        if result == "accept":

            selector = 'span.slds-truncate[title="Operations Service Console"]'

            try:
                # 1. Esperar que el iframe esté presente
                await page.wait_for_selector("iframe.reportsReportBuilder", timeout=20000)

                # 2. Acceder al frame
                frame = page.frame_locator("iframe.reportsReportBuilder")

                # 3. Localizar el botón "More Actions - Edit"
                button = frame.locator("button.more-actions-button")

                # 4. Esperar que el botón sea visible
                await button.wait_for(state="visible", timeout=30000)

                # (Opcional) pequeña espera para estabilidad
                await asyncio.sleep(10)

                print("✅ Salesforce interface loaded (More Actions detected)")
                return True

            except Exception as e:
                print(f"❌ Salesforce interface not detected: {e}")
                return False
            

        else:

            return False

    except Exception as e:

        print(f"❌ Error in Salesforce login: {e}")
        return False
# ==========================================================
# VALIDATE 2FA AUTHENTICATION
# ==========================================================
async def authentication_flow(page):

    await asyncio.sleep(2)

    possible_verify_selectors = [

        'span[data-se="o-form-input-credentials.passcode"] input[name="credentials.passcode"]',
        'input[name="credentials.passcode"][type="text"]',
        'span.o-form-input-name-credentials\\.passcode input[type="text"]',

    ]

    cycles = 4

    for cycle in range(cycles):

        print(f"\n🔁 Authentication cycle {cycle + 1}/{cycles}")

        for selector in possible_verify_selectors:

            locator = page.locator(selector)

            if await locator.is_visible():

                print("✓ Verification field detected")

                password_new_input = page.locator('input[name="credentials.passcode"]')
                password_confirm_input = page.locator('input[name="confirmPassword"]')
                password_form = page.locator("form.password-authenticator")

                if (
                    await password_form.count() > 0
                    or (
                        await password_new_input.count() > 0
                        and await password_confirm_input.count() > 0
                    )
                ):

                    print("⚠️ Password reset / expiration detected (Okta)")

                    return False
                
                
                result = show_notification()

                await search_and_click_verify_button(page)

                return result

        print("⚠ Verification field not visible")

        selector_factor = 'a[data-se="button"].button.select-factor.link-button'

        try:

            await page.wait_for_selector(
                selector_factor,
                state="visible",
                timeout=1500
            )

            elements = await page.locator(selector_factor).all()

            if len(elements) >= 2:

                await elements[1].click()
                return show_notification()

            elif len(elements) == 1:

                await elements[0].click()
                return show_notification()

        except:

            print("No factor selection found")

        await asyncio.sleep(1)

    print("❌ Authentication flow failed")

    return False

# ==========================================================
# SHOW 2FA POPUP
# ==========================================================
def show_notification():

    try:

        root = tk.Tk()
        root.withdraw()

        response = messagebox.askquestion(

            "Notification Confirmation",

            "Do you accept the notification?",

            icon='question',

            detail="Please accept the authentication notification on your phone and press YES.",

            type='yesno'
        )

        if response == "yes":

            print("✅ User accepted notification")
            time.sleep(5)
            return "accept"

        else:

            print("❌ User rejected notification")
            return "reject"

    except Exception as e:

        print(f"❌ Notification error: {e}")
        return "reject"

# ==========================================================
# CLICK VERIFY BUTTON
# ==========================================================
async def search_and_click_verify_button(page):

    try:

        verify_button = page.locator(
            'input[type="submit"][value="Verificar"]'
        )

        await verify_button.wait_for(state="visible", timeout=1000)

        if await verify_button.is_visible():

            await verify_button.click()
            return True

    except:

        pass

    try:

        verify_button = page.locator(
            'input[type="submit"][value="Verify"]'
        )

        await verify_button.wait_for(state="visible", timeout=1000)

        if await verify_button.is_visible():

            await verify_button.click()
            return True

    except:

        pass

    print("Verify button not found")

    return False

# ==========================================================
# TEST ADMIN CREDENTIALS
# ==========================================================
async def test_credentials(admin_user, password):

    playwright = None
    browser = None
    context = None
    page = None

    try:

        playwright = await async_playwright().start()

        browser = await playwright.chromium.launch(headless=False)

        context = await browser.new_context()

        page = await context.new_page()

        page.set_default_timeout(5000)

        await page.goto("https://admin.payulatam.com//", timeout=20000)

        await asegurar_idioma_espanol(page)

        await page.wait_for_selector(
            'input[name="j_username"]',
            state="visible"
        )

        await page.fill(
            'input[name="j_username"]',
            admin_user
        )

        await page.fill(
            'input[name="j_password"]',
            password
        )

        await page.keyboard.press("Enter")

        await page.wait_for_selector(
            '.ItemsAqui[title="Merchants"]',
            state="visible",
            timeout=20000
        )

        print("✅ Admin login successful")

        return True

    except Exception as e:

        print(f"❌ Admin login failed: {e}")

        return False

    finally:

        if context:
            await context.close()

        if browser:
            await browser.close()

        if playwright:
            await playwright.stop()

# ==========================================================
# ENSURE SPANISH LANGUAGE
# ==========================================================
async def asegurar_idioma_espanol(page):

    try:

        boton_idioma = page.locator("button.z-menu-btn")

        await boton_idioma.wait_for(state="visible", timeout=5000)

        texto = (await boton_idioma.inner_text()).strip().lower()

        if "español" in texto:

            print("🌐 Language already Spanish")

            return

        await boton_idioma.click()

        await page.wait_for_selector(
            "ul.z-menu-popup-cnt",
            state="visible"
        )

        opcion = page.locator(
            "ul.z-menu-popup-cnt li.z-menu-item >> text=Español"
        )

        await opcion.click()

        await page.wait_for_timeout(1000)

        print("✅ Language switched to Spanish")

    except Exception as e:

        print(f"❌ Language switch error: {e}")

# ==========================================================
# OPEN ADMIN WEBSITE
# ==========================================================
async def open_admin_portal(page):

    try:

        await page.goto(
            "https://admin.payulatam.com//",
            timeout=15000
        )

        await asegurar_idioma_espanol(page)

    except Exception:

        print("❌ Admin site not accessible")
        sys.exit(0)
        
# ==========================================================
# ADMIN LOGIN
# ==========================================================
async def admin_login(page, username, password):

    try:

        await page.wait_for_selector(
            'input[name="j_username"]',
            state="visible"
        )

        await page.fill(
            'input[name="j_username"]',
            username
        )

        await page.fill(
            'input[name="j_password"]',
            password
        )

        await page.keyboard.press("Enter")

        await page.wait_for_selector(
            '.ItemsAqui[title="Merchants"]',
            state="visible",
            timeout=10000
        )

        print("✅ Admin interface loaded")

    except Exception as e:

        raise Exception(f"Admin login failed: {e}")
        sys.exit(1)
          
# Navegacion SF hacia la descarga, disparando la nueva ventana
async def Navegacion_SF(page):

    try:
        print("🔹 [1] Esperando iframe...")
        await page.wait_for_selector("iframe.reportsReportBuilder", timeout=20000)
        frame = page.frame_locator("iframe.reportsReportBuilder")

        print("🔹 [2] Click More Actions...")
        button = frame.locator("button.more-actions-button")
        await button.wait_for(state="visible", timeout=10000)
        await button.click()

        print("🔹 [3] Dropdown...")
        dropdown = frame.locator("ul.dropdown__list[role='menu']")
        await dropdown.wait_for(state="visible", timeout=10000)

        print("🔹 [4] Click Export...")
        await dropdown.get_by_role("menuitem", name="Export").click()

        print("🔹 [5] Details Only...")
        await page.wait_for_timeout(3000)
        details_only = page.locator(
            'span.slds-text-heading_small.visual-picker-header:has-text("Details Only")'
        )
        await details_only.wait_for(state="visible", timeout=10000)
        await details_only.click()

        print("🔹 [6] Formato XLSX...")
        await page.select_option('select.slds-select', value='xlsx')

        print("🔹 [7] Click Export final...")
        boton = page.locator("button:has-text('Export')")

        await boton.wait_for(state="visible", timeout=15000)
        await boton.scroll_into_view_if_needed()

        # 🔥 CLICK ROBUSTO (clave para Salesforce)
        await boton.click(force=True)

        print("🚀 Export ejecutado")

    except Exception as e:
        print(f"❌ Error during Navegacion_SF: {e}")



#Funtion procces in SF an Download the report
async def SF_Download_Report(SF_Pass, SF_User):

    try:
        from config import OUTPUT_FOLDER
        from datetime import datetime
        import os
        from playwright.async_api import async_playwright

        async with async_playwright() as playwright:

            browser = None
            page = None     

            print("🔐 Iniciando login...")
            response = await get_browser_and_page(
                playwright, SF_Pass, SF_User, browser, page
            )

            # 🔥 Manejo flexible de respuesta
            if len(response) == 4:
                resultado, browser, page, message = response
            else:
                resultado, browser, page = response
                message = None

            
            if resultado:

                print("✅ Login OK")

                # 🔥 CLAVE: esperar descarga (timeout largo)
                async with page.expect_download(timeout=120000) as download_info:
                    await Navegacion_SF(page)

                download = await download_info.value

                print("📥 Descarga detectada")

                path = await download.path()
                print(f"📁 Ruta temporal: {path}")

                # ✅ Validación
                if not path or os.path.getsize(path) == 0:
                    raise Exception("❌ Archivo vacío o inválido")

                # Nombre final
                fecha = datetime.now().strftime("%d_%m_%Y")
                ruta_archivo = OUTPUT_FOLDER / f"reporteSF-{fecha}.xlsx"

                await download.save_as(str(ruta_archivo))

                print(f"🟩 Guardado en: {ruta_archivo}")

                return ruta_archivo

            else:

                print("🟥 Salesforce login failed")

                if message:
                    print(f"⚠️ Motivo: {message}")
                    return message  # 🔥 DEVUELVES EL MOTIVO REAL

                return None


    except Exception as e:
        print(f"❌ Error during SF_Download_Report: {e}")
        return None


 
async def procesar_ACI(output_ACI_path, ProcessName, SF_Pass, SF_User):

    """
    Valida si el ACI existe.
    Si no existe, descarga el reporte desde Salesforce.
    Devuelve (True, mensaje) si todo fue bien, (False, mensaje) si hubo error.
    """

    ruta_reporte = None

    # ==========================================================
    # 1️⃣ VALIDAR SI YA EXISTE EL ACI
    # ==========================================================

    if os.path.exists(output_ACI_path):

        mensaje = f"🆗 El ACI ya existe: {output_ACI_path}"
        return True, mensaje


    print("El ACI NO existe → se intentará descargar el reporte desde Salesforce")

    # ==========================================================
    # 2️⃣ INTENTAR DESCARGAR REPORTE
    # ==========================================================

    max_intentos = 3

    for intento in range(1, max_intentos + 1):

        try:

            print(f"Intento {intento} de {max_intentos}...")

            ruta_reporte = await SF_Download_Report(SF_Pass, SF_User)

            if ruta_reporte:

                print(f"Reporte descargado en: {ruta_reporte}")

                return True, f"Reporte descargado correctamente: {ruta_reporte}"

            else:

                print("No se obtuvo ruta del reporte. Reintentando...")

        except Exception as e:

            print(f"Error en el intento {intento}: {e}")

    # ==========================================================
    # 3️⃣ SI FALLÓ TODO
    # ==========================================================

    mensaje = "❌ No se pudo descargar el reporte desde Salesforce."

    return False, mensaje       
        
def normalizar_columnas(df):
    df.columns = [normalizar(col) for col in df.columns]
    return df

def normalizar(texto: Optional[str]) -> str:
    if texto is None:
        return ""
    s = str(texto)
    # convertir entidades HTML (&nbsp;, &amp;, etc.) a su forma textual
    s = html.unescape(s)
    # reemplazar non-breaking spaces por espacios normales
    s = s.replace('\xa0', ' ')
    # colapsar cualquier whitespace (tabs, múltiples espacios, saltos de línea) a un solo espacio
    s = re.sub(r'\s+', ' ', s)
    s = s.strip().lower()
    # quitar acentos/diacríticos
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return s
              
async def get_case_dataframev1(case_number, sf_user, sf_pass):

    """
    Returns the DataFrame for the requested Case Number.
    - If SQLite exists → load and return
    - If not → download Salesforce report → extract case → create SQLite
    """

    try:

        table_name = "aci_data"

        # ==========================================================
        # 1️⃣ SQLITE PATH
        # ==========================================================

        sqlite_path = config.OUTPUT_FOLDER / f"ACI_{case_number}.db"

        # ==========================================================
        # 2️⃣ LOAD EXISTING SQLITE
        # ==========================================================

        if os.path.exists(sqlite_path):

            print(f"🆗 SQLite already exists: {sqlite_path}")

            conn = sqlite3.connect(sqlite_path)

            df = pd.read_sql(f"SELECT * FROM {table_name}", conn)

            # 🔎 verificar si existe la tabla de status
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                AND name='aci_status'
            """)

            status_exists = cursor.fetchone()

            if not status_exists:
                print("🟡 Status table not found → creating")
                create_status_table(conn, df)
            else:
                print("✅ Using existing status table")
                # 🔄 Reset de procesos en 'processing' → 'pending'
                cursor.execute("""
                    UPDATE aci_status
                    SET status = 'pending'
                    WHERE status = 'processing'
                """)

                conn.commit()

                print("🔄 Reset 'processing' → 'pending'")

            conn.close()

            return True, df, sqlite_path 
        

        print("SQLite does not exist → downloading Salesforce report")

        # ==========================================================
        # 3️⃣ DOWNLOAD REPORT
        # ==========================================================

        ruta_reporte = await SF_Download_Report(sf_pass, sf_user)

        if not ruta_reporte:
            print("❌ Salesforce report download failed")
            return False, None, None

        print(f"Report downloaded: {ruta_reporte}")

        # ==========================================================
        # 4️⃣ READ EXCEL
        # ==========================================================

        df = pd.read_excel(ruta_reporte)

        if "Case Number" not in df.columns:
            print("❌ 'Case Number' column not found in report")
            return False, None, None

        df["Case Number"] = df["Case Number"].astype(str)

        case_number = str(case_number)

        df_case = df[df["Case Number"] == case_number]

        if df_case.empty:
            print(f"❌ Case {case_number} not found in report")
            return False, None, None

        print(f"✅ Case {case_number} found in report")

        # ==========================================================
        # 6️⃣CREATE SQLITE
        # ==========================================================

        conn = sqlite3.connect(sqlite_path)

        df_case.to_sql(
            table_name,
            conn,
            if_exists="replace",
            index=False
        )
        
        # ==========================================================
        # CREATE STATUS TABLE
        # ==========================================================

        create_status_table(conn, df_case)

        conn.close()

        print(f"🟩 SQLite created: {sqlite_path}")

        # ==========================================================
        # 7️⃣ RETURN DATAFRAME
        # ==========================================================

        return True, df_case, sqlite_path

    except Exception as e:

        print(f"❌ Error in get_case_dataframe: {e}")

        return False, None, None      

def build_sqlite_from_template(ruta_excel):
    import os
    import re
    import sqlite3
    import unicodedata
    import pandas as pd
    import config

    def clean_text(value):
        if pd.isna(value):
            return None
        value = str(value).strip()
        if value == "" or value.lower() == "nan":
            return None
        return value

    def normalize_dataframe(df):
        df.columns = [str(c).strip() for c in df.columns]
        for col in df.columns:
            df[col] = df[col].apply(clean_text)
        return df

    def is_missing_or_invalid(value):
        txt = str(value).strip().lower()
        return (
            value is None
            or txt == ""
            or txt == "nan"
            or txt == "none"
            or txt == "missing data"
            or txt.startswith("invalid format")
        )

    def normalize_missing(value):
        return "missing data" if is_missing_or_invalid(value) else str(value).strip()

    def normalize_tax_id(value):
        value = clean_text(value)
        if value is None:
            return "missing data"

        value_str = str(value).strip()
        if not value_str.isdigit():
            return "invalid format: tax ID must be numeric"

        return value_str

    def normalize_website(value):
        value = clean_text(value)
        if value is None:
            return "missing data"

        value_str = str(value).strip()
        if not value_str.lower().startswith(("http://", "https://")):
            return "invalid format: website must start with http"

        return value_str

    def normalize_email(value):
        value = clean_text(value)
        if value is None:
            return "missing data"

        value_str = str(value).strip()
        if "@" not in value_str:
            return "invalid format: email format incorrect"

        return value_str

    def strip_accents(text):
        text = str(text)
        return "".join(
            c for c in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(c)
        )

    def detect_merchant_country(merchant_row):
        fields = [
            merchant_row.get("Billing Address", ""),
            merchant_row.get("Company address (Registry data)", ""),
            merchant_row.get("Website", ""),
            merchant_row.get("Company name (Registry data)", ""),
        ]

        text = strip_accents(
            " | ".join([str(x) for x in fields if x is not None]).lower()
        )

        if any(city in text for city in COLOMBIAN_CITIES) or ".com.co" in text or ".co/" in text:
            return "colombia"

        if any(city in text for city in PERU_CITIES) or ".com.pe" in text or ".pe/" in text:
            return "peru"

        return "unknown"

    def detect_crp_country(crp_row):
        city = strip_accents(
            str(crp_row.get("Company city (Registry data)", "") or "").strip().lower()
        )

        if city in COLOMBIAN_CITIES:
            return "colombia"

        if city in PERU_CITIES:
            return "peru"

        return "unknown"
    
    def build_expected_status_map(df_case):
        expected = {}

        if df_case.empty:
            return expected

        row = df_case.iloc[0]
        merchant_country = detect_merchant_country(row)

        def base_status_from_value(value):
            if is_missing_or_invalid(value):
                return "missing data"
            return "pending"

        # =========================
        # ADMIN / MERCHANT
        # =========================
        expected["ADM_DOC"]       = base_status_from_value(row.get("Billing Address"))
        expected["ADM_MERCH_NAME"]= base_status_from_value(row.get("Company name (Registry data)"))
        expected["ADM_EMAIL"]     = base_status_from_value(row.get("Firm Email"))
        expected["ADM_WEB"]       = base_status_from_value(row.get("Website"))
        expected["Google_URL"]    = base_status_from_value(row.get("Website"))
        expected["Google_MAPS"]   = base_status_from_value(row.get("Billing Address"))

        tax_id_value = row.get("Tax Identification Number")

        if merchant_country == "colombia":
            expected["Google_RUES"]  = base_status_from_value(tax_id_value)
            expected["Google_SUNAT"] = "not applicable: merchant is not from Peru"

        elif merchant_country == "peru":
            expected["Google_SUNAT"] = base_status_from_value(tax_id_value)
            expected["Google_RUES"]  = "not applicable: merchant is not from Colombia"

        else:
            if is_missing_or_invalid(tax_id_value):
                expected["Google_RUES"]  = "missing data"
                expected["Google_SUNAT"] = "missing data"
            else:
                expected["Google_RUES"]  = "not applicable: merchant country could not be identified"
                expected["Google_SUNAT"] = "not applicable: merchant country could not be identified"

        # =========================
        # PROCESOS COMERCIO
        # =========================
        m_name = normalize_missing(row.get("Company name (Registry data)"))
        mn_status = "pending" if m_name != "missing data" else "missing data"

        expected["Merchant_Name"]          = mn_status
        expected["Merchant_Name_String"]   = mn_status
        expected["Merchant_Name_AI"]       = mn_status
        expected["Merchant_Name_String_AI"]= mn_status

        m_email = normalize_missing(row.get("Firm Email"))
        me_status = "pending" if (m_email != "missing data" and "@" in str(m_email)) else "missing data"

        expected["Merchant_Email"]          = me_status
        expected["Merchant_Email_String"]   = me_status
        expected["Merchant_Email_AI"]       = me_status
        expected["Merchant_Email_String_AI"]= me_status

        # =========================
        # CRP (4 procesos + Procuraduría)
        # =========================
        unique_crps = df_case.drop_duplicates(subset=["CRP number"])

        for _, crp_row in unique_crps.iterrows():
            crp_number  = normalize_missing(crp_row.get("CRP number"))
            crp_name    = normalize_missing(crp_row.get("Name"))
            personal_id = normalize_missing(crp_row.get("Personal ID number"))
            crp_country = detect_crp_country(crp_row)

            crp_base_status = "pending"
            if crp_number == "missing data" or crp_name == "missing data":
                crp_base_status = "missing data"

            expected[f"{crp_number}"]           = crp_base_status
            expected[f"{crp_number}_String"]    = crp_base_status
            expected[f"{crp_number}_AI"]        = crp_base_status
            expected[f"{crp_number}_String_AI"] = crp_base_status

            proc_key = f"Google_PROCURADURIA_{crp_number}"
            if crp_country == "colombia":
                expected[proc_key] = "missing data" if personal_id == "missing data" else "pending"
            else:
                expected[proc_key] = "not applicable: CRP is not from Colombia"

        return expected
    
    def sync_status_table(conn, df_case):
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aci_status (
                process TEXT PRIMARY KEY,
                status TEXT
            )
        """)

        # 🔄 Reset procesos atascados en 'processing' → 'pending'
        cursor.execute("""
            UPDATE aci_status
            SET status = 'pending'
            WHERE status = 'processing'
        """)
        conn.commit()
        print("♻ Stuck 'processing' processes reset to 'pending'")
        
        
        cursor.execute("SELECT process, status FROM aci_status")
        existing_rows = cursor.fetchall()
        existing_status = {
            str(process).strip(): str(status).strip()
            for process, status in existing_rows
        }

        expected_status = build_expected_status_map(df_case)

        for process, new_status in expected_status.items():
            current_status = existing_status.get(process)

            if current_status is None:
                cursor.execute(
                    "INSERT INTO aci_status (process, status) VALUES (?, ?)",
                    (process, new_status)
                )
                continue

            current_status_norm = str(current_status).strip().lower()
            new_status_norm = str(new_status).strip().lower()

            # preservar procesos ya completados
            preserve_statuses = {
                "completed",
                "done",
                "success",
                "ok"
            }

            if current_status_norm in preserve_statuses:
                continue

            # si estaba pending y ahora corresponde comment/missing data, actualizar
            if current_status_norm != new_status_norm:
                cursor.execute(
                    "UPDATE aci_status SET status = ? WHERE process = ?",
                    (new_status, process)
                )

        conn.commit()

    try:
        print(f"📖 Reading Excel template: {ruta_excel}")

        xl = pd.ExcelFile(ruta_excel)

        if "Merchant_Info" not in xl.sheet_names:
            return False, "❌ Sheet 'Merchant_Info' not found", None

        if "CRP" not in xl.sheet_names:
            return False, "❌ Sheet 'CRP' not found", None

        df_merch = xl.parse("Merchant_Info")
        df_crp = xl.parse("CRP")

        df_merch = normalize_dataframe(df_merch)
        df_crp = normalize_dataframe(df_crp)

        if df_merch.empty:
            return False, "❌ Merchant_Info is empty", None

        if len(df_merch) != 1:
            return False, "❌ Merchant_Info must contain exactly 1 row", None

        if "Case Number" not in df_merch.columns:
            return False, "❌ 'Case Number' column not found in Merchant_Info", None

        case_number = clean_text(df_merch.loc[0, "Case Number"])

        if case_number is None:
            return False, "❌ Case Number is required", None

        case_number = str(case_number).strip()

        if not case_number.isdigit():
            return False, f"❌ Invalid format: Case Number '{case_number}' must be numeric", None

        # =========================
        # NORMALIZACION MERCHANT
        # =========================
        merchant_required_fields = [
            "MCC code: MCC",
            "MCC Description",
            "Tax Identification Number",
            "Website",
            "Firm Email",
            "Contact Name: Full Name",
            "Company name (Registry data)",
            "Account Name",
            "Billing Address",
            "Company address (Registry data)",
        ]

        for col in merchant_required_fields:
            if col not in df_merch.columns:
                df_merch[col] = None

        df_merch.loc[0, "MCC code: MCC"] = normalize_missing(df_merch.loc[0, "MCC code: MCC"])
        df_merch.loc[0, "MCC Description"] = normalize_missing(df_merch.loc[0, "MCC Description"])
        df_merch.loc[0, "Tax Identification Number"] = normalize_tax_id(df_merch.loc[0, "Tax Identification Number"])
        df_merch.loc[0, "Website"] = normalize_website(df_merch.loc[0, "Website"])
        df_merch.loc[0, "Firm Email"] = normalize_email(df_merch.loc[0, "Firm Email"])
        df_merch.loc[0, "Contact Name: Full Name"] = normalize_missing(df_merch.loc[0, "Contact Name: Full Name"])
        df_merch.loc[0, "Company name (Registry data)"] = normalize_missing(df_merch.loc[0, "Company name (Registry data)"])
        df_merch.loc[0, "Account Name"] = normalize_missing(df_merch.loc[0, "Account Name"])
        df_merch.loc[0, "Billing Address"] = normalize_missing(df_merch.loc[0, "Billing Address"])
        df_merch.loc[0, "Company address (Registry data)"] = normalize_missing(df_merch.loc[0, "Company address (Registry data)"])

        # =========================
        # NORMALIZACION CRP
        # =========================
        crp_required_fields = [
            "CRP number",
            "Name",
            "Status",
            "Role type",
            "Date/Time Opened",
            "Company city (Registry data)",
            "Company zip code (Registry data)",
            "Personal ID number",
            "Service: Service",
        ]

        for col in crp_required_fields:
            if col not in df_crp.columns:
                df_crp[col] = None

        for idx in df_crp.index:
            df_crp.loc[idx, "CRP number"] = normalize_missing(df_crp.loc[idx, "CRP number"])
            df_crp.loc[idx, "Name"] = normalize_missing(df_crp.loc[idx, "Name"])
            df_crp.loc[idx, "Status"] = normalize_missing(df_crp.loc[idx, "Status"])
            df_crp.loc[idx, "Role type"] = normalize_missing(df_crp.loc[idx, "Role type"])
            df_crp.loc[idx, "Date/Time Opened"] = normalize_missing(df_crp.loc[idx, "Date/Time Opened"])
            df_crp.loc[idx, "Company city (Registry data)"] = normalize_missing(df_crp.loc[idx, "Company city (Registry data)"])
            df_crp.loc[idx, "Company zip code (Registry data)"] = normalize_missing(df_crp.loc[idx, "Company zip code (Registry data)"])
            df_crp.loc[idx, "Personal ID number"] = normalize_missing(df_crp.loc[idx, "Personal ID number"])
            df_crp.loc[idx, "Service: Service"] = normalize_missing(df_crp.loc[idx, "Service: Service"])

        # =========================
        # CROSS JOIN
        # =========================
        df_merch["_tmp_key"] = 1
        df_crp["_tmp_key"] = 1
        df_case = pd.merge(df_merch, df_crp, on="_tmp_key").drop(columns=["_tmp_key"])

        # columnas de compatibilidad
        if "Gambling Registry check" not in df_case.columns:
            df_case["Gambling Registry check"] = None

        if "Blacklisted CRP" not in df_case.columns:
            df_case["Blacklisted CRP"] = None

        db_path = os.path.join(config.OUTPUT_FOLDER, f"ACI_{case_number}.db")
        db_exists = os.path.exists(db_path)

        conn = sqlite3.connect(db_path)

        # siempre actualiza aci_data, pero NO reinicia aci_status
        df_case.to_sql("aci_data", conn, if_exists="replace", index=False)

        # sync sin perder el progreso previo
        sync_status_table(conn, df_case)

        conn.close()

        if db_exists:
            print(f"♻ Existing DB reused: {db_path}")
        else:
            print(f"✅ New DB created: {db_path}")

        return True, df_case, db_path

    except Exception as e:
        print(f"❌ Error in build_sqlite_from_template: {e}")
        return False, str(e), None

# ==========================================
# CAPTCHA CUSTOM EXCEPTION
# ==========================================
class CaptchaExhaustedError(Exception):
    """Se lanza cuando Google CAPTCHA agota todos los intentos internos."""
    pass

# ==========================================
# MAIN PROCESS FUNCTION (UPDATED)
# ==========================================
async def evidence_collection_process(
    data_to_use,
    sqlite_path,
    admin_user,
    password,
    partition_number,
    process_type="ALL"
):

    async with async_playwright() as playwright:

        browser_admin = None
        browser_google = None

        try:

            if data_to_use.empty:
                print("⚠️ No records to process")
                return

            print(f"🚀 Starting Evidence Collection - Partition {partition_number}")

            page_admin = None
            page_google = None
            page_AI = None
            browser_ai = None
            admin_session_active = False

            row = data_to_use.iloc[0]

            case_number = row["Case Number"]
            business_name = row["Company name (Registry data)"]
            tax_id = row["Tax Identification Number"]
            email = row["Firm Email"]
            website = row["Website"]
            Personal_ID = row["Personal ID number"]
            Billing_Address = data_to_use["Billing Address"].dropna().unique()[0]
            
            crp_dict = build_crp_dictionary(data_to_use)

            print("\nCRP DICTIONARY SIZE:", len(crp_dict))
            print("CRP KEYS:", list(crp_dict.keys())[:5])

            while True:

                await asyncio.sleep(random.uniform(2, 8))
                print("\nWorker:", partition_number)
                print("Worker type:", process_type)
                print("Requesting next process...")

                process = get_next_process(sqlite_path, process_type)

                print("Process received:", process)

                if process is None:
                    print("✅ All processes completed")
                    break

                print(f"➡ Processing: {process}")

                # ==========================================
                # ADMIN VALIDATIONS
                # ==========================================
                if process.startswith("ADM") and process_type in ("ALL","ADMIN"):

                    if not admin_session_active:

                        print("🔐 Opening Admin session")

                        if not page_admin:
                            browser_admin, page_admin = await initialize_admin_browser(playwright)

                        await open_admin_portal(page_admin)
                        await admin_login(page_admin, admin_user, password)

                        admin_session_active = True

                    async def run_admin():
                        await admin_validation_process(
                            process,
                            page_admin,
                            tax_id,
                            email,
                            website,
                            business_name,
                            sqlite_path,
                            case_number
                        )

                        await capture_process_screenshot(
                            page_admin,
                            sqlite_path,
                            case_number,
                            process
                        )

                    await process_with_retries_async(sqlite_path, process, run_admin)

                # ==========================================
                # CRP GOOGLE SEARCH
                # ==========================================
                elif process.startswith("CRP") and process_type in ("ALL","CRP"):

                    if not page_google:
                        browser_google, page_google = await initialize_google_browser(playwright)

                    print("CRP PROCESS ENTERED:", process)

                    async def run_crp():
                        nonlocal page_google, browser_google

                        page_google, browser_google, search_ok = await google_search_process(
                            process,
                            crp_dict,
                            page_google,
                            browser_google,
                            playwright
                        )

                        if not search_ok:
                            # 🔥 No marcar completed, dejar en processing para reintento de ronda
                            raise CaptchaExhaustedError(f"CAPTCHA exhausted for: {process}")

                        await capture_process_screenshot(
                            page_google,
                            sqlite_path,
                            case_number,
                            process
                        )
                        
                        
                    await process_with_retries_async(sqlite_path, process, run_crp)

                # ==========================================
                # MERCHANT NAME / EMAIL GOOGLE SEARCH
                # ==========================================
                elif (
                    process.startswith("Merchant_Name") or 
                    process.startswith("Merchant_Email")
                ) and process_type in ("ALL", "CRP", "MERCHANT"):

                    if not page_google:
                        browser_google, page_google = await initialize_google_browser(playwright)

                    print(f"🏪 MERCHANT PROCESS ENTERED: {process}")

                    # Determinar qué valor buscar
                    if process.startswith("Merchant_Name"):
                        search_value = str(business_name).strip()
                    else:
                        search_value = str(email).strip()

                    # Determinar si es búsqueda con string (keywords de riesgo)
                    use_string = "_String" in process and not process.endswith("_AI")

                    async def run_merchant():
                        nonlocal page_google, browser_google

                        page_google, browser_google, search_ok = await google_search_process(
                            process,
                            {process.split("_")[0] + "_" + process.split("_")[1]: search_value},
                            page_google,
                            browser_google,
                            playwright
                        )

                        if not search_ok:
                            raise CaptchaExhaustedError(f"CAPTCHA exhausted for: {process}")

                        await capture_process_screenshot(
                            page_google,
                            sqlite_path,
                            case_number,
                            process
                        )
                    
                    
                    await process_with_retries_async(sqlite_path, process, run_merchant)
                
                # ==========================================
                # GOOGLE URL
                # ==========================================
                elif process == "Google_URL" and process_type in ("ALL","GOOGLE"):

                    print("🌐 Processing Google URL")

                    if not page_google:
                        browser_google, page_google = await initialize_google_browser(playwright)

                    async def run_url():
                        await Buscar_URL_Google(
                            website,
                            page_google,
                            sqlite_path,
                            case_number,
                            process
                        )

                    await process_with_retries_async(sqlite_path, process, run_url)

                # ==========================================
                # PROCURADURIA (UPDATED - DYNAMIC) (COLOMBIA ONLY)
                # ==========================================
                elif process.startswith("Google_PROCURADURIA_") and process_type in ("ALL","PROCURADURIA"):

                    print("⚖ Procuraduria validation")

                    if not page_google:
                        browser_google, page_google = await initialize_google_browser(playwright)

                    async def run_proc():

                        # Extract CRP from process name
                        crp = process.replace("Google_PROCURADURIA_", "").strip()

                        # Find matching row
                        row_match = data_to_use[
                            data_to_use["CRP number"].astype(str).str.strip() == crp
                        ]

                        if row_match.empty:
                            print(f"⚠ No row found for CRP: {crp}")
                            return

                        personal_id = row_match.iloc[0]["Personal ID number"]

                        print(f"📄 CRP: {crp} → Personal ID: {personal_id}")

                        await Busqueda_procuraduria(
                            personal_id,
                            page_google,
                            sqlite_path,
                            case_number,
                            process
                        )

                    await process_with_retries_async(sqlite_path, process, run_proc)

                # ==========================================
                # RUES SEARCH (COLOMBIA ONLY)
                # ==========================================
                elif process == "Google_RUES" and process_type in ("ALL","GOOGLE"):

                    print("🏛 Processing RUES search")

                    if not page_google:
                        browser_google, page_google = await initialize_google_browser(playwright)

                    async def run_rues():

                        await search_RUES(
                            tax_id,
                            page_google,
                            sqlite_path,
                            case_number,
                            process
                        )

                    await process_with_retries_async(sqlite_path, process, run_rues)
                
                # ==========================================
                # SUNAT SEARCH (PERU ONLY)
                # ==========================================
                elif process == "Google_SUNAT" and process_type in ("ALL","GOOGLE"):

                    print("🇵🇪 Processing SUNAT search")

                    if not page_google:
                        browser_google, page_google = await initialize_google_browser(playwright)

                    async def run_sunat():

                        await search_SUNAT(
                            tax_id,
                            page_google,
                            sqlite_path,
                            case_number,
                            process
                        )

                    await process_with_retries_async(sqlite_path, process, run_sunat)
                
                # ==========================================
                # GOOGLE MAPS
                # ==========================================
                elif process == "Google_MAPS" and process_type in ("ALL","GOOGLE"):

                    print("🗺 Processing Google Maps")

                    if not page_google:
                        browser_google, page_google = await initialize_google_browser(playwright)

                    async def run_maps():

                        await Busqueda_google_maps(
                            Billing_Address,   # o lo que quieras buscar
                            page_google,
                            sqlite_path,
                            case_number,
                            process
                        )

                    await process_with_retries_async(sqlite_path, process, run_maps)

                # ==========================================
                # AI PROCESS
                # ==========================================
                elif process.endswith("_AI") and process_type in ("ALL", "AI"):

                    print(f"🤖 [AI WORKER {partition_number}] ejecutando: {process}")

                    # 🔥 inicializar browser UNA VEZ
                    if not page_AI:
                        browser_ai, page_AI = await initialize_ai_browser(playwright)

                        # 🔐 login con reintentos
                        MAX_LOGIN_RETRIES = 3
                        login_ok = False

                        for login_attempt in range(1, MAX_LOGIN_RETRIES + 1):
                            print(f"🔐 Login attempt {login_attempt}/{MAX_LOGIN_RETRIES}...")
                            login_ok = await login_abacus_ai(
                                page_AI,
                                email="hurtadogarzon@gmail.com",
                                password="Letsgo12**"
                            )
                            if login_ok:
                                break
                            print(f"⚠ Login failed on attempt {login_attempt}, retrying...")
                            await asyncio.sleep(5)
                            try:
                                await browser_ai.close()
                            except:
                                pass
                            browser_ai, page_AI = await initialize_ai_browser(playwright)

                        if not login_ok:
                            print("🚨 Login failed after all retries → worker exits gracefully")
                            # 🔥 NO hacer return → dejar que el while continúe con el siguiente proceso
                            continue

                    async def run_ai():

                        nonlocal browser_ai, page_AI  # 🔥 IMPORTANTE para poder reasignar

                        MAX_AI_RETRIES = 3

                        for intento in range(1, MAX_AI_RETRIES + 1):

                            try:
                                print(f"\n🤖 AI attempt {intento} for: {process}")

                                # 🚀 USAR SIEMPRE EL MISMO PAGE (NO CREAR NUEVO)
                                result = await run_ai_worker(
                                    page_AI,
                                    process,
                                    sqlite_path,
                                    case_number,
                                    config.OUTPUT_FOLDER,
                                    config.PROMPT_PATH
                                )

                                # 🔥 VALIDAR RESULTADO
                                if result:
                                    print(f"✅ AI succeeded on attempt {intento}")
                                    return

                                else:
                                    print(f"⚠ AI failed on attempt {intento}")
                                    raise Exception("AI returned False")

                            except Exception as e:
                                print(f"❌ AI crash on attempt {intento}: {e}")

                                # 🚨 REINICIAR SOLO SI FALLA
                                try:
                                    if browser_ai:
                                        print("💥 Closing broken browser...")
                                        await browser_ai.close()
                                except:
                                    pass

                                print("🚀 Recreating browser after failure...")
                                browser_ai, page_AI = await initialize_ai_browser(playwright)

                                print("🔐 Re-login after failure...")
                                login_ok = await login_abacus_ai(
                                    page_AI,
                                    email="hurtadogarzon@gmail.com",
                                    password="Letsgo12**"
                                )

                                if not login_ok:
                                    print("🚨 Login failed after crash → siguiente intento")
                                    continue

                            # 🔁 retry delay
                            if intento < MAX_AI_RETRIES:
                                print("🔁 Retrying AI...")
                                await asyncio.sleep(3)

                        # 🚨 si falla todo
                        print(f"🚨 AI FAILED AFTER {MAX_AI_RETRIES} ATTEMPTS: {process}")
                    
                    await process_with_retries_async(
                        sqlite_path,
                        process,
                        run_ai
                    )







        except Exception as e:
            print(f"❌ Critical error: {e}")

        finally:

            if browser_admin:
                await browser_admin.close()

            if browser_google:
                await browser_google.close()

            if browser_ai:
                await browser_ai.close()

async def search_merchant(
    page,
    value,
    field_name,
    sqlite_path=None,
    case_number=None,
    process=None
):

    try:

        await page.wait_for_timeout(500)

        locator = page.locator(
            "div.ItemsAqui[title='Merchants'], div.Items[title='Merchants']"
        )

        await locator.wait_for(state="visible", timeout=20000)
        await locator.click()

        await page.wait_for_timeout(800)

        await page.locator("a[title='Comercios']").click()

        await page.wait_for_timeout(800)

        selector = f'input[name="{field_name}"]'

        await page.wait_for_selector(selector, state="visible", timeout=10000)

        await page.fill(selector, "")
        await page.fill(selector, str(value))

        await page.wait_for_timeout(500)

        # 📸 BEFORE (nuevo - no rompe nada si no se envían params)
        if sqlite_path and case_number and process:
            await capture_process_screenshot(
                page,
                sqlite_path,
                case_number,
                f"{process}_BEFORE"
            )

        # 🔎 Click original
        await page.locator(
            "button.btnRound.z-button-os[title='Buscar']"
        ).click()

        print(f"🔎 Searching {field_name}: {value}")

        return True

    except Exception as e:

        print(f"⚠️ Error in search_merchant: {e}")

        return False

async def capture_process_screenshotv1(page,sqlite_path,case_number,process,custom_name=None):

    screenshots_dir = Path(sqlite_path).parent / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    await page.wait_for_timeout(800)

    # 🔥 usar nombre personalizado si existe
    process_name = custom_name if custom_name else process

    # =====================================================
    # 🔥 RUES GENERAL / ECONOMIC + PROCURADURIA → SINGLE SCREENSHOT
    # =====================================================
    if (
        "GENERAL" in process_name
        or "ECONOMIC" in process_name
        or process_name.startswith("Google_PROCURADURIA_")
    ):

        file_path = screenshots_dir / f"{case_number}_{process_name}.png"

        # 👉 Scroll down a bit to avoid header / search box
        scroll_offset = random.randint(200, 400)

        await page.evaluate(f"window.scrollTo(0, {scroll_offset})")
        await page.wait_for_timeout(600)

        await page.screenshot(
            path=str(file_path),
            full_page=False,
            animations="disabled",
            scale="device"
        )

        print(f"📸 SINGLE screenshot saved: {file_path}")
        return
        
    
    
    
    
    
    
    
    
    
    # =====================================================
    # 🔥 ADMIN → UNA SOLA IMAGEN (FULL PAGE)
    # =====================================================
    if process_name.startswith("ADM"):

        file_path = screenshots_dir / f"{case_number}_{process_name}.png"

        await page.evaluate("window.scrollTo(0,0)")
        await page.wait_for_timeout(500)

        await page.screenshot(
            path=str(file_path),
            full_page=True,
            animations="disabled",
            scale="device"
        )

        print(f"📸 ADMIN screenshot saved: {file_path}")
        return

    # =====================================================
    # 🔥 RESTO → SCROLL + PARTES
    # =====================================================
    await page.evaluate("window.scrollTo(0,0)")
    await page.wait_for_timeout(500)

    viewport_height = await page.evaluate("window.innerHeight")
    total_height = await page.evaluate("document.body.scrollHeight")

    scroll_y = 0
    part = 0

    while scroll_y < total_height:

        file_path = screenshots_dir / f"{case_number}_{process_name}_part_{part}.png"

        await page.evaluate(f"window.scrollTo(0, {scroll_y})")
        await page.wait_for_timeout(400)

        await page.screenshot(
            path=str(file_path),
            full_page=False,
            animations="disabled",
            scale="device"
        )

        print(f"📸 Screenshot saved: {file_path}")

        scroll_y += viewport_height
        part += 1

async def capture_process_screenshot(page, sqlite_path, case_number, process, custom_name=None):
    screenshots_dir = Path(sqlite_path).parent / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    process_name = custom_name if custom_name else process

    # 📋 CONFIGURACIÓN: Procesos que SÍ necesitan scroll completo (case-sensitive)
    SCROLL_PROCESSES = [
        "Merchant_Name",
        "Merchant_Email",
        "Google_URL",
        "CRP",
        "LEGAL"
    ]

    needs_scroll = any(p in process_name for p in SCROLL_PROCESSES)

    # =====================================================
    # 📸 MODO SINGLE (ADMIN, MAPS, URL, ETC)
    # =====================================================
    if not needs_scroll:
        file_path = screenshots_dir / f"{case_number}_{process_name}_part_0.png"

        # Ajuste de espera antes de la captura para que cargue la interfaz
        await page.wait_for_timeout(1000)

        await page.screenshot(
            path=str(file_path),
            full_page=False,
            scale="device"
        )
        print(f"📸 SINGLE screenshot saved: {file_path}")
        return

    # =====================================================
    # 📜 MODO SCROLL (ANTECEDENTES CRP / REGISTROS PÚBLICOS)
    # =====================================================
    print(f"📜 Starting full scroll capture for: {process_name}")

    await page.evaluate("window.scrollTo(0, 0)")
    await page.wait_for_timeout(800)

    total_height = await page.evaluate("document.body.scrollHeight")
    viewport_height = page.viewport_size['height'] if page.viewport_size else 800

    scroll_y = 0
    part = 0
    max_parts = 6 # Límite para no crear PDFs infinitos

    while scroll_y < total_height and part < max_parts:
        file_path = screenshots_dir / f"{case_number}_{process_name}_part_{part}.png"

        await page.evaluate(f"window.scrollTo(0, {scroll_y})")
        await page.wait_for_timeout(800)

        await page.screenshot(
            path=str(file_path),
            full_page=False,
            scale="device"
        )

        scroll_y += viewport_height
        part += 1

    print(f"✅ Full scroll capture finished for {process_name} ({part} parts)")


COLOMBIAN_CITIES = {
    "bogota", "medellin", "cali", "barranquilla",
    "cartagena", "bucaramanga", "pereira",
    "manizales", "cucuta", "ibague", "villavicencio"
}

PERU_CITIES = {
    "lima", "arequipa", "trujillo", "cusco",
    "piura", "chiclayo", "huancayo", "ica"
}
def create_status_table(conn, df_case):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS aci_status")
    cursor.execute("CREATE TABLE aci_status (process TEXT, status TEXT)")

    row = df_case.iloc[0]
    
    # --- PROCESOS ADMIN / MERCHANT ---
    # RUES y SUNAT dependen del Tax Identification Number
    tax_id_val = str(row.get("Tax Identification Number", "")).lower()
    rues_sunat_status = "pending"
    if "missing data" in tax_id_val or "invalid format" in tax_id_val:
        rues_sunat_status = "missing data"

    # Mapeo de procesos
    mapping = {
        "ADM_DOC": row.get("Billing Address"),
        "ADM_MERCH_NAME": row.get("Company name (Registry data)"),
        "ADM_EMAIL": row.get("Firm Email"),
        "ADM_WEB": row.get("Website"),
        "Google_URL": row.get("Website"),
        "Google_MAPS": row.get("Billing Address"), # Depende de Billing Address
        "Google_RUES": tax_id_val, 
        "Google_SUNAT": tax_id_val
    }

    for process, field_val in mapping.items():
        status = "pending"
        # Si el campo de origen ya viene marcado como error o falta
        if "missing data" in str(field_val).lower() or "invalid format" in str(field_val).lower():
            status = "missing data"
        
        # Caso especial para RUES/SUNAT: se registran según el país después en el bot, 
        # pero aquí los inicializamos según el Tax ID.
        cursor.execute("INSERT INTO aci_status VALUES (?, ?)", (process, status))

    # --- PROCESOS POR CRP ---
    unique_crps = df_case.drop_duplicates(subset=["CRP number"])
    for _, crp_row in unique_crps.iterrows():
        crp_id = crp_row["CRP number"]
        city = str(crp_row.get("Company city (Registry data)", "")).lower()
        id_num = str(crp_row.get("Personal ID number", "")).lower()
        name = str(crp_row.get("Name", "")).lower()

        # ⚖ Procuraduría: Solo si es Colombia y tiene ID
        if "bogota" in city or "colombia" in city:
            p_status = "pending"
            if id_num == "missing data": 
                p_status = "missing data"
            cursor.execute("INSERT INTO aci_status VALUES (?, ?)", (f"Google_PROCURADURIA_{crp_id}", p_status))

        # 🤖 Procesos de Nombre (String / AI)
        name_status = "pending"
        if name == "missing data" or crp_id == "missing data":
            name_status = "missing data"
        
        cursor.execute("INSERT INTO aci_status VALUES (?, ?)", (f"{crp_id}_String", name_status))
        cursor.execute("INSERT INTO aci_status VALUES (?, ?)", (f"{crp_id}_AI", name_status))

    conn.commit()
  
def get_pending_processes(sqlite_path):
   
    conn = sqlite3.connect(sqlite_path)

    df_status = pd.read_sql(
        """
        SELECT *
        FROM aci_status
        WHERE status='pending'
        """,
        conn
    )

    conn.close()

    return df_status
      

def reset_processing_to_pending(sqlite_path, prefixes=None):
    conn = sqlite3.connect(sqlite_path, timeout=30)
    cursor = conn.cursor()
    try:
        if prefixes:
            conditions = " OR ".join([f"process LIKE '{p}%'" for p in prefixes])
            query = f"UPDATE aci_status SET status = 'pending' WHERE status = 'processing' AND ({conditions})"
        else:
            query = "UPDATE aci_status SET status = 'pending' WHERE status = 'processing'"
        
        cursor.execute(query)
        affected = cursor.rowcount
        conn.commit()
        print(f"🔄 Reset {affected} processes: processing → pending")
        return affected
    except Exception as e:
        print(f"❌ Error resetting processing to pending: {e}")
        return 0
    finally:
        conn.close()
# ==========================================
# RESET processing → pending (para rondas de reintento)
# ==========================================
def reset_processing_to_pendingv1(sqlite_path):
    """
    Busca todos los procesos en estado 'processing' y los regresa a 'pending'.
    Se llama al final de cada ronda antes de reintentar.
    """
    conn = sqlite3.connect(sqlite_path, timeout=30)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE aci_status SET status = 'pending' WHERE status = 'processing'"
        )
        affected = cursor.rowcount
        conn.commit()
        print(f"🔄 Reset {affected} processes: processing → pending")
        return affected
    except Exception as e:
        print(f"❌ Error resetting processing to pending: {e}")
        return 0
    finally:
        conn.close()


def has_pending_processes(sqlite_path, prefixes=None):
    """
    Retorna True si hay procesos en pending o processing.
    Si se pasan prefixes, solo revisa procesos que empiecen con alguno de ellos.
    """
    conn = sqlite3.connect(sqlite_path, timeout=30)
    cursor = conn.cursor()
    try:
        if prefixes:
            conditions = " OR ".join([f"process LIKE '{p}%'" for p in prefixes])
            query = f"SELECT COUNT(*) FROM aci_status WHERE status IN ('pending', 'processing') AND ({conditions})"
        else:
            query = "SELECT COUNT(*) FROM aci_status WHERE status IN ('pending', 'processing')"
        
        cursor.execute(query)
        count = cursor.fetchone()[0]
        return count > 0
    finally:
        conn.close()


def mark_remaining_processing_as_issue(sqlite_path):
    """
    Después de 3 rondas, marca como issue los que siguen en processing.
    """
    conn = sqlite3.connect(sqlite_path, timeout=30)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """UPDATE aci_status 
               SET status = 'issue: captcha after 3 rounds' 
               WHERE status = 'processing'"""
        )
        affected = cursor.rowcount
        conn.commit()
        print(f"🚨 Marked {affected} processes as 'issue: captcha after 3 rounds'")
    except Exception as e:
        print(f"❌ Error marking issue: {e}")
    finally:
        conn.close()


def mark_process_completed(sqlite_path, process):

    conn = sqlite3.connect(sqlite_path)

    conn.execute(
        """
        UPDATE aci_status
        SET status='completed'
        WHERE process=?
        """,
        (process,)
    )
    
    # =====================================================
    # 🔥 ACTIVATE AI PROCESS (CRP ONLY)
    # =====================================================

    if process.startswith("CRP") and not process.endswith("_AI"):

        print(f"🧠 Activando AI para: {process}")
        if process.endswith("_String"):
            ai_process = f"{process}_AI"   # CRP-XXXX_String → CRP-XXXX_String_AI
        else:
            ai_process = f"{process}_AI"   # CRP-XXXX → CRP-XXXX_AI

        # 🔒 Solo activar si está en waiting (evita duplicados)
        conn.execute("""
            UPDATE aci_status
            SET status='pending'
            WHERE process=? AND status='waiting'
        """, (ai_process,))

        if conn.total_changes > 0:
            print(f"🚀 AI ACTIVADO → {ai_process}")
        else:
            print(f"⚠️ AI NO ACTIVADO (ya estaba activo o no estaba en waiting): {ai_process}")

    conn.commit()
    conn.close()
    
async def google_news_search(page, query_text):

    

    try:

        query = urllib.parse.quote(query_text)

        url = f"https://www.google.com/search?q={query}&tbm=nws&hl=en"

        await page.goto(
            url,
            timeout=15000,
            wait_until="domcontentloaded"
        )

        await page.wait_for_timeout(2000)

        print(f"📰 Google News search: {query_text}")

        return True

    except Exception as e:

        print(f"⚠️ Google News error: {e}")

        return False
    
def build_risk_query(name):

    keywords = """
    (LAVADO | NARCOTRAFICO | FRAUDE | CRIMEN | ACUSADO | ARRESTO |
    CORRUPCION | SOBORNO | TERRORISTA | TERRORISMO | DROGA | PANDILLA |
    TRAFICO | ARMA | VIOLACION | PORNOGRAFIA | ABUSO | SEXUAL |
    CARTEL | ESTAFA | BLANQUEO | EVASION | SECUESTRO | TESTAFERRO |
    REGIMEN | NARCO | PARAMILITAR | VIOLENCIA | ARMADO)
    """

    return f'"{name}" AND {keywords}'
        
def get_next_process(sqlite_path, process_type="ALL"):

    conn = sqlite3.connect(sqlite_path, timeout=30)
    cursor = conn.cursor()

    print("\n-----------------------------")
    print("GET NEXT PROCESS CALLED")
    print("process_type:", process_type)

    try:

        # 🔒 lock fuerte → evita doble toma en multi-worker
        conn.execute("BEGIN IMMEDIATE")
        
        print("📊 Estado actual pending:")
        cursor.execute("SELECT process FROM aci_status WHERE status='pending'")
        rows_debug = cursor.fetchall()
        print("➡ Pending:", [r[0] for r in rows_debug][:10])

        if process_type == "ADMIN":
            filter_clause = "process LIKE 'ADM%'"

        elif process_type == "CRP":
            filter_clause = """(
                (process LIKE 'CRP%' AND process NOT LIKE '%_AI')
                OR
                (process LIKE 'Merchant_%' AND process NOT LIKE '%_AI')
            )"""

        elif process_type == "MERCHANT":
            filter_clause = """(
                process LIKE 'Merchant_%' AND process NOT LIKE '%_AI'
            )"""

        elif process_type == "AI":
            filter_clause = "process LIKE '%_AI'"

        elif process_type == "GOOGLE":
            filter_clause = """process IN (
                'Google_URL', 'Google_MAPS', 'Google_RUES', 'Google_SUNAT'
            )"""

        elif process_type == "PROCURADURIA":
            filter_clause = "process LIKE 'Google_PROCURADURIA_%'"

        else:
            filter_clause = "1=1"

        query = f"""
            SELECT process
            FROM aci_status
            WHERE status='pending'
            AND {filter_clause}
            ORDER BY 
                CASE 
                    WHEN process LIKE 'ADM%' THEN 1
                    WHEN process LIKE 'CRP%' THEN 2
                    WHEN process = 'Google_URL' THEN 3
                    WHEN process LIKE 'Google_PROCURADURIA_%' THEN 4
                    WHEN process = 'Google_RUES' THEN 5
                    WHEN process = 'Google_MAPS' THEN 6
                    ELSE 7
                END,
                process
            LIMIT 1
        """

        print(f"🔍 DEBUG query SQL a ejecutar: {query}")
        cursor.execute(query)
        row = cursor.fetchone()

        print("SQL RESULT:", row)

        if row is None:
            print("⚠️ No hay procesos disponibles para este worker")
            conn.commit()
            conn.close()
            return None

        process = row[0]
        print(f"🎯 PROCESO SELECCIONADO: {process}")

        cursor.execute("""
            UPDATE aci_status
            SET status='processing'
            WHERE process=?
        """, (process,))

        conn.commit()

        print("PROCESS LOCKED:", process)

        conn.close()

        print(f"🎯 PROCESO SELECCIONADO: {process}")
        return process

    except Exception as e:

        print("❌ get_next_process error:", e)

        conn.rollback()
        conn.close()

        return None

async def google_search(page, query_text):

    try:

        query = urllib.parse.quote(query_text)

        url = f"https://www.google.com/search?q={query}&hl=en"

        await page.goto(
            url,
            timeout=15000,
            wait_until="domcontentloaded"
        )

        await page.wait_for_timeout(2000)

        print(f"🔎 Google search: {query_text}")

        return True

    except Exception as e:

        print(f"⚠️ Google search error: {e}")

        return False

import urllib.parse

async def es_captcha(page_google):
    """Verifica si la página actual tiene CAPTCHA."""
    if await page_google.locator("#recaptcha").count() > 0:
        return True
    if await page_google.locator("#recaptcha-anchor-label").count() > 0:
        return True
    if await page_google.locator("iframe[title='reCAPTCHA']").count() > 0:
        return True
    if "/sorry/" in page_google.url:
        return True
    return False

async def reiniciar_browser_google(playwright):
    """Cierra y reinicia el browser de Google limpio."""
    browser_google = await playwright.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )

    context_google = await browser_google.new_context(
        viewport={"width": 1366, "height": 768},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        locale="en-US"
    )

    await context_google.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    page_google = await context_google.new_page()

    await page_google.goto(
        "https://www.google.com",
        timeout=15000,
        wait_until="domcontentloaded"
    )

    print("✅ Google browser restarted")

    return page_google, browser_google

async def manejar_captcha_google(playwright, page_google, browser_google, query=None):

    try:
        
        # ESPERA ALEATORIA HUMANA (4 a 9 seg) para que la página cargue y simular lectura
        espera_inicial = random.uniform(4.0, 9.0)
        print(f"⏳ Waiting {espera_inicial:.2f}s before checking for search bar...")
        await page_google.wait_for_timeout(int(espera_inicial * 1000))
        
        # PANTALLAZO 1: ¿Existe textarea[name="q"]?
        textarea = page_google.locator('textarea[name="q"]')
        if await textarea.count() > 0:
            print("⌨️ Input textarea found, searching there...")
            await textarea.fill(query)
            await page_google.keyboard.press("Enter")
            await page_google.wait_for_timeout(3000)
        else:
            print("🌐 Textarea not found, using direct URL bypass...")
            url_directa = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            await page_google.goto(url_directa, timeout=15000, wait_until="domcontentloaded")
            await page_google.wait_for_timeout(3000)

        # ¿Existe CAPTCHA después de este intento?
        if not await es_captcha(page_google):
            print("✅ Bypassed CAPTCHA successfully")
            return page_google, browser_google, False

        # PANTALLAZO 2: Intentar bypass por URL directa si falló el textarea
        print("⚠️ CAPTCHA detected after search, trying direct URL...")
        url_directa = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        await page_google.goto(url_directa, timeout=15000, wait_until="domcontentloaded")
        await page_google.wait_for_timeout(3000)

        # ¿Sigue el CAPTCHA?
        if not await es_captcha(page_google):
            print("✅ Bypassed CAPTCHA after URL direct")
            return page_google, browser_google, False

        # PANTALLAZO 3: Cierre y reinicio (último recurso)
        print("⚠️ CAPTCHA persists after all attempts → closing browser")
        espera = random.randint(30, 60) + random.uniform(0.5, 3.5)
        print(f"🛑 Waiting {espera:.2f} seconds...")
        await browser_google.close()
        await asyncio.sleep(espera)
        print("🔄 Restarting Google browser...")
        page_google, browser_google = await reiniciar_browser_google(playwright)
        
        return page_google, browser_google, True

    except Exception as e:
        print(f"⚠️ CAPTCHA handler error: {e}")
        return page_google, browser_google, False


async def handle_google_captcha(playwright, page_google, browser_google, query=None):

    page_google, browser_google, captcha = await manejar_captcha_google(
        playwright,
        page_google,
        browser_google,
        query=query
    )

    return page_google, browser_google, captcha

    
PROCESS_NAMES = {

    "ADM_DOC": "Document Validation",
    "ADM_EMAIL": "Email Validation",
    "ADM_WEB": "Website Validation",
    "ADM_MERCH_NAME": "Merchant Name Validation",

    "Google_BLACKLIST": "Blacklist Search",
    "Google_POLICE": "Police Record Search",
    "Google_PROCURADURIA": "Procuraduria Search",
    "Google_URL": "Website Risk Search",
    "Google_MAPS": "Google Maps Search"
}

def generar_reporte_pdf(case_number, sqlite_path, admin_user, case_summary=None, ruta_imagen=None):

    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    ruta_regular = os.path.join(BASE_DIR, "fonts", "AmpleSoftPro.ttf")
    ruta_bold = os.path.join(BASE_DIR, "fonts", "AmpleSoftPro-Bold.ttf")

    print("Regular:", ruta_regular, os.path.exists(ruta_regular))
    print("Bold:", ruta_bold, os.path.exists(ruta_bold))

    try:
        print("Cargando fuente regular desde:", ruta_regular)
        print("Cargando fuente bold desde:", ruta_bold)

        pdfmetrics.registerFont(TTFont("AmpleSoft", ruta_regular))
        pdfmetrics.registerFont(TTFont("AmpleSoft-Bold", ruta_bold))

        FUENTE_BASE = "AmpleSoft"
        FUENTE_BOLD = "AmpleSoft-Bold"
        FUENTE_ITALIC = "AmpleSoft"
    except Exception as e:
        print("⚠ No se pudo cargar AmpleSoft, usando Helvetica")
        print("❌ ERROR REAL:", e)
        FUENTE_BASE = "Helvetica"
        FUENTE_BOLD = "Helvetica-Bold"
        FUENTE_ITALIC = "Helvetica-Oblique"

    def P(texto, bold=False, color="black", size=11):
        font = FUENTE_BOLD if bold else FUENTE_BASE
        return Paragraph(
            f'<font name="{font}" color="{color}" size="{size}">{texto}</font>',
            styles["Normal"]
        )

    screenshots_dir = Path(sqlite_path).parent / "screenshots"
    output_pdf = Path(sqlite_path).parent / f"CASE_{case_number}_evidence.pdf"

    styles = getSampleStyleSheet()

    styles["Normal"].fontName = FUENTE_BASE
    styles["Normal"].fontSize = 11
    styles["Normal"].alignment = TA_JUSTIFY

    styles["Title"].fontName = FUENTE_BOLD
    styles["Title"].fontSize = 12
    styles["Title"].alignment = TA_LEFT

    styles["Heading2"].fontName = FUENTE_BOLD
    styles["Heading2"].fontSize = 12
    styles["Heading2"].alignment = TA_LEFT

    elementos = []

    titulo_style = ParagraphStyle(
        name="TituloCentrado",
        parent=styles["Heading2"],
        fontName=FUENTE_BOLD,
        fontSize=13,
        leading=15,
        spaceAfter=10
    )

    nota_style = ParagraphStyle(
        name="NotaStyle",
        parent=styles["Normal"],
        fontName=FUENTE_ITALIC,
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#444444"),
        spaceAfter=6,
    )

    # =====================================================
    # 🔥 HEADER + FOOTER
    # =====================================================
    def draw_header(canvas, doc):

        width, height = letter
        header_height = 40

        canvas.setFillColor(colors.HexColor("#FF007A"))
        canvas.rect(0, height - header_height, width, header_height, fill=1, stroke=0)

        texto = "Checklist CompOps - Know Your Business"
        canvas.setFillColor(colors.white)
        canvas.setFont(FUENTE_BOLD, 10)

        text_width = canvas.stringWidth(texto, FUENTE_BOLD, 10)
        canvas.drawString((width - text_width) / 2, height - header_height + 10, texto)

        BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
        logo_path = os.path.join(BASE_DIR, "static", "LogoRapyd.png")

        try:
            logo = ImageReader(logo_path)
            canvas.drawImage(logo, width - 120, height - header_height + 7, width=100, height=25, mask='auto')
        except:
            pass

        footer_y = 30

        footer_text = (
            "The total number of red flags identified in this checklist constitutes an alert criterion "
            "that requires further investigation and/or escalation to the appropriate team. "
            "This additional review process may result in the rejection of the case, provided that "
            "the decision is properly justified and supported."
        )

        footer_paragraph = Paragraph(footer_text, nota_style)
        _, h = footer_paragraph.wrap(520, 100)
        footer_paragraph.drawOn(canvas, 40, footer_y)

        canvas.setFont(FUENTE_BOLD, 8)
        canvas.drawString(40, footer_y + h + 8, "Important")

        canvas.setStrokeColor(colors.HexColor("#CCCCCC"))
        canvas.line(40, footer_y + h + 18, 550, footer_y + h + 18)

    # =====================================================
    # 🔥 SQLITE DATA
    # =====================================================
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM aci_data LIMIT 1')
    row = cursor.fetchone()

    company_name = row["Company name (Registry data)"] if row else "N/A"
    mcc_code = row["MCC code: MCC"] if row else ""
    mcc_desc = row["MCC Description"] if row else ""

    mcc_text = f"{int(mcc_code)} - {mcc_desc}" if mcc_code else "N/A"

    conn.close()

    # =====================================================
    # 🔥 HEADER TABLE
    # =====================================================
    fecha_actual = datetime.now().strftime("%B %d, %Y")

    header_data = [
        [
            P("First Review Date", bold=True, color="white", size=11),
            P("Merchant ID", bold=True, color="white", size=11),
            P("Salesforce Case", bold=True, color="white", size=11),
            P("Operational Risk Analyst", bold=True, color="white", size=10),
        ],
        [
            P(fecha_actual),
            P("N/A"),
            P(str(case_number)),
            P(admin_user),
        ],
        [
            P("MCC", bold=True, color="white"),
            Paragraph(mcc_text, styles["Normal"]),
            P("LA/FT Risk", bold=True, color="white"),
            P("Low"),
        ],
        [
            P("Merchant Name", bold=True, color="white"),
            P(company_name),
            P(""),
            P(""),
        ]
    ]

    header_table = Table(header_data, colWidths=[110, 230, 90, 130])

    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (3,0), colors.HexColor("#FF007A")),
        ("BACKGROUND", (0,2), (0,3), colors.HexColor("#FF007A")),
        ("BACKGROUND", (2,2), (2,2), colors.HexColor("#FF007A")),

        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),

        ("FONTNAME", (0,0), (-1,-1), FUENTE_BASE),
        ("FONTNAME", (0,0), (3,0), FUENTE_BOLD),
        ("FONTNAME", (0,2), (0,3), FUENTE_BOLD),
        ("FONTNAME", (2,2), (2,2), FUENTE_BOLD),

        ("TEXTCOLOR", (0,0), (3,0), colors.white),
        ("TEXTCOLOR", (0,2), (0,3), colors.white),
        ("TEXTCOLOR", (2,2), (2,2), colors.white),

        ("SPAN", (2,3), (3,3)),
    ]))

    elementos.append(header_table)
    elementos.append(Spacer(1, 20))

    # =====================================================
    # 🔥 TITLE
    # =====================================================
    elementos.append(Paragraph(f"Case Evidence Report: {case_number}", styles["Title"]))
    elementos.append(Spacer(1, 20))

    # =====================================================
    # 🔥 CHECKLIST STATUS TABLE (GROUPED) ← MOVIDO AL INICIO
    # =====================================================
    try:
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT process, status FROM aci_status")
        rows = cursor.fetchall()
        conn.close()

        if rows:
            elementos.append(Paragraph("<b>Checklists Status</b>", titulo_style))
            elementos.append(Spacer(1, 10))

            grouped = defaultdict(list)

            for r in rows:
                process_name = str(r[0])
                status_value = str(r[1]) if r[1] else ""

                p = process_name.upper()

                if p.startswith("ADM"):
                    group = "ADMIN"
                elif "GOOGLE" in p:
                    group = "GOOGLE"
                elif "PROCURADURIA" in p:
                    group = "PROCURADURIA"
                elif "CRP" in p:
                    group = "CRP"
                else:
                    group = "OTHER"

                grouped[group].append((process_name, status_value))

            ordered_groups = ["ADMIN", "GOOGLE", "PROCURADURIA", "CRP", "OTHER"]

            for group_name in ordered_groups:

                if group_name not in grouped:
                    continue

                group_block = []
                group_block.append(Paragraph(group_name, titulo_style))
                group_block.append(Spacer(1, 6))

                # ✅ NUEVA TERCERA COLUMNA: Remediation or justification
                data = [["Process", "Status", "Remediation or justification"]]

                for process_name, status_value in sorted(grouped[group_name]):
                    data.append([
                        Paragraph(process_name, styles["Normal"]),
                        Paragraph(status_value, styles["Normal"]),
                        Paragraph("", styles["Normal"]),  # columna vacía
                    ])

                table = Table(data, colWidths=[170, 130, 200])

                table.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#FF007A")),
                    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                    ("FONTNAME", (0,0), (-1,0), FUENTE_BOLD),
                    ("FONTNAME", (0,1), (-1,-1), FUENTE_BASE),
                    ("FONTSIZE", (0,0), (-1,-1), 11),
                    ("GRID", (0,0), (-1,-1), 0.5, colors.black),
                    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ]))

                group_block.append(table)
                group_block.append(Spacer(1, 15))

                elementos.append(KeepTogether(group_block))

            elementos.append(Spacer(1, 20))

    except Exception as e:
        print(f"⚠ Error loading checklist status: {e}")

    # =====================================================
    # 🔥 BUSINESS MODEL
    # =====================================================
    if case_summary:
        case_summary = case_summary.strip()

    if case_summary:
        elementos.append(Paragraph("Business Model", titulo_style))
        elementos.append(Spacer(1, 10))

        elementos.append(Paragraph(
            "General summary and analysis of the merchant; the underwriting must be attached ",
            nota_style
        ))

        #elementos.append(Spacer(1, 6))

        #elementos.append(Paragraph(
        #    "Admin whitelist validation (search in Admin using name, identification number, website, and email).",
        #    nota_style
        #))

        elementos.append(Spacer(1, 10))

        clean_summary = case_summary.replace("\n", "<​br/>")
        elementos.append(Paragraph(clean_summary, styles["Normal"]))
        elementos.append(Spacer(1, 20))

    # =====================================================
    # 🔥 DOCUMENT IMAGE
    # =====================================================
    adm_doc_status = ""

    try:
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM aci_status WHERE process = 'ADM_DOC' LIMIT 1")
        result = cursor.fetchone()
        conn.close()

        if result:
            adm_doc_status = str(result[0]).strip().lower()

    except Exception as e:
        print(f"⚠ Error reading ADM_DOC status: {e}")

    if ruta_imagen and os.path.exists(ruta_imagen) and adm_doc_status != "missing data":

        bloque_doc = []
        bloque_doc.append(Paragraph("Documents Required by Country", titulo_style))
        #bloque_doc.append(Paragraph("Applicable only for Big Onboarding", nota_style))
        bloque_doc.append(Spacer(1, 10))

        img_reader = ImageReader(ruta_imagen)
        w, h = img_reader.getSize()

        scale = min(456 / w, 500 / h, 1)

        img = Image(ruta_imagen, width=w * scale, height=h * scale)
        img.hAlign = "CENTER"

        bloque_doc.append(img)
        bloque_doc.append(Spacer(1, 25))

        elementos.append(KeepTogether(bloque_doc))

    # =====================================================
    # 🔥 CRP VALIDATION
    # =====================================================
    elementos.append(Paragraph("CRP Validation", titulo_style))
    elementos.append(Spacer(1, 10))
    elementos.append(Spacer(1, 10))

    # =====================================================
    # 🔥 CRP TABLE FROM aci_data
    # =====================================================
    try:
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                "CRP number",
                "Name",
                "Status",
                "Role type",
                "Personal ID number"
            FROM aci_data
        """)

        rows = cursor.fetchall()
        conn.close()

        data = [[
            "CRP number",
            "Name",
            "Status",
            "Role type",
            "Personal ID number"
        ]]

        for r in rows:
            data.append([
                Paragraph(str(r["CRP number"]) if r["CRP number"] else "", styles["Normal"]),
                Paragraph(str(r["Name"]) if r["Name"] else "", styles["Normal"]),
                Paragraph(str(r["Status"]) if r["Status"] else "", styles["Normal"]),
                Paragraph(str(r["Role type"]) if r["Role type"] else "", styles["Normal"]),
                Paragraph(str(r["Personal ID number"]) if r["Personal ID number"] else "", styles["Normal"])
            ])

        if not rows:
            elementos.append(Paragraph("No CRP data available", styles["Normal"]))

        table = Table(data, colWidths=[90, 150, 80, 140, 110])

        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#FF007A")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), FUENTE_BOLD),
            ("FONTNAME", (0,1), (-1,-1), FUENTE_BASE),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))

        elementos.append(table)
        elementos.append(Spacer(1, 20))

    except Exception as e:
        print(f"⚠ Error loading CRP table: {e}")

    elementos.append(Spacer(1, 20))

    # =====================================================
    # 🔥 IMAGES
    # =====================================================
    imagenes = sorted(screenshots_dir.glob(f"{case_number}_*.png"))

    procesos_dict = defaultdict(lambda: defaultdict(dict))

    for img_path in imagenes:
        nombre = img_path.stem.replace(f"{case_number}_", "")
        is_before = "_BEFORE" in nombre
        nombre_clean = nombre.replace("_BEFORE", "")

        match = re.search(r"_part_(\d+)", nombre_clean)
        part = int(match.group(1)) if match else 0

        base_name = re.sub(r"_part_\d+", "", nombre_clean)

        if is_before:
            procesos_dict[base_name][part]["before"] = img_path
        else:
            procesos_dict[base_name][part]["after"] = img_path

    max_width_half = 220
    max_width_single = 456
    max_height = 500

    def preparar_imagen(img_path, max_width, max_height):
        reader = ImageReader(str(img_path))
        w, h = reader.getSize()
        scale = min(max_width / w, max_height / h, 1)
        return Image(str(img_path), width=w * scale, height=h * scale), h * scale

    crp_header_shown = False
    procuraduria_header_shown = False
    rues_header_shown = False
    admin_header_shown = False
    blacklist_header_shown = False  # ← NUEVO FLAG

    # =====================================================
    # 🔥 ORDEN PERSONALIZADO DE PROCESOS
    # =====================================================
    def get_process_order(proceso):
        p = proceso.upper()
        if p.startswith("ADM"): return 1
        elif "RUES" in p or "SUNAT" in p: return 2
        elif "PROCURADURIA" in p: return 3
        elif p == "GOOGLE_URL": return 4
        elif "CRP-" in p: return 5
        elif "MERCHANT_NAME" in p: return 6
        elif "MERCHANT_EMAIL" in p: return 7
        elif p == "GOOGLE_MAPS": return 8
        else: return 99

    procesos_ordenados = sorted(
        procesos_dict.items(),
        key=lambda x: (get_process_order(x[0]), x[0])
    )

    # =====================================================
    # ✅ Cargar estados desde aci_status
    # =====================================================
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()
    cursor.execute("SELECT process, status FROM aci_status")
    status_rows = cursor.fetchall()
    conn.close()

    status_dict = {
        str(process).strip(): str(status).strip().lower()
        for process, status in status_rows
    }

    def get_pdf_process_status(proceso):
        proceso = str(proceso).strip()
        if proceso in status_dict:
            return status_dict[proceso]
        variants = [f"{proceso}_AI", f"{proceso}_String_AI", f"{proceso}_String"]
        for v in variants:
            if v in status_dict:
                return status_dict[v]
        return ""

    # =====================================================
    # 🔥 LOOP PRINCIPAL DE PROCESOS
    # =====================================================
    for proceso, partes in procesos_ordenados:

        process_status = get_pdf_process_status(proceso)

        if process_status == "missing data":
            print(f"⏭ Skipping PDF section for {proceso} (missing data)")
            continue

        # ✅ NUEVO: Insertar título Blacklist justo después de que termina ADMIN
        if not blacklist_header_shown and not proceso.upper().startswith("ADM"):
            blacklist_header_shown = True
            elementos.append(Spacer(1, 10))
            elementos.append(Paragraph(
                'Blacklist Verification in Salesforce (If the status is "Not Passed" / "Failed," '
                'a search is performed by name and ID in the blacklist).',
                titulo_style
            ))
            elementos.append(Spacer(1, 10))  # 3 renglones de espacio
            elementos.append(Spacer(1, 10))
            elementos.append(Spacer(1, 10))

        first = True

        for part in sorted(partes.keys()):
            imgs = partes[part]
            bloque = []

            if first:

                if proceso.upper().startswith("ADM"):

                    if not admin_header_shown:
                        bloque.append(Paragraph(
                            "Admin Whitelist Verification (Search in Admin using name, identification number, website, and email)",
                            titulo_style
                        ))
                        bloque.append(Spacer(1, 10))
                        admin_header_shown = True

                    bloque.append(Paragraph(f"<b>{proceso}</b>", titulo_style))

                elif "PROCURADURIA" in proceso.upper():

                    if not procuraduria_header_shown:
                        bloque.append(Paragraph(
                            "<b>Background Check of the Merchant and Related Parties</b>",
                            titulo_style
                        ))
                        bloque.append(Paragraph(
                            "Procuraduria: https://www.procuraduria.gov.co<br/><br/>"
                            "Applicable only for Colombia.<br/>"
                            "For other countries: N/A. Identification available in SharePoint file.",
                            nota_style
                        ))
                        bloque.append(Spacer(1, 10))
                        procuraduria_header_shown = True

                    bloque.append(Paragraph(f"<b>{proceso}</b>", titulo_style))

                elif "CRP-" in proceso:

                    if not crp_header_shown:
                        bloque.append(Paragraph(
                            "Open-Source Search for News or Findings Related to the Merchant",
                            titulo_style
                        ))
                        bloque.append(Paragraph(
                            "Search using: legal name (without legal suffix), trade name, email, and related parties (with and without string).<br/>"
                            "If negative news is found, a deeper investigation must be conducted.<br/>"
                            "Related companies must be manually added in Salesforce for screening.<br/><br/>"
                            "Best practice (optional): review LinkedIn profiles and search related IDs in Google.",
                            nota_style
                        ))
                        bloque.append(Spacer(1, 10))
                        crp_header_shown = True

                    bloque.append(Paragraph(f"<b>{proceso}</b>", titulo_style))

                    try:
                        ai_results_dir = Path(sqlite_path).parent / "ai_results"
                        ai_file = ai_results_dir / f"Resultado_AI_{proceso}.txt"

                        if ai_file.exists():
                            with open(ai_file, "r", encoding="utf-8") as f:
                                ai_text = f.read().strip()

                            if ai_text:
                                bloque.append(Spacer(1, 6))
                                ai_text_clean = ai_text.replace("\n", "<​br/>")
                                bloque.append(Paragraph(ai_text_clean, styles["Normal"]))
                                bloque.append(Spacer(1, 10))

                    except Exception as e:
                        print(f"⚠ Error loading AI text for {proceso}: {e}")

                elif "RUES" in proceso:

                    if not rues_header_shown:
                        bloque.append(Paragraph(
                            "<b>RUES (Merchant Identification and Verification)</b>",
                            titulo_style
                        ))
                        bloque.append(Paragraph(
                            
                            "For other LATAM countries refer to “Prevalidation documents file<br/>"
                            "and upload the relevant supporting evidence within the case or opportunity<br/>",
                            nota_style
                        ))
                        
                        bloque.append(Spacer(1, 10))
                        rues_header_shown = True

                    bloque.append(Paragraph(f"<b>{proceso}</b>", titulo_style))

                elif proceso == "Google_URL":

                    bloque.append(Paragraph(
                        "<b>Economic Activity Identification</b>",
                        titulo_style
                    ))
                    bloque.append(Paragraph(
                        "Home/About section must be present.<br/>"
                        "Products and services must be present.<br/>"
                        "Pricing only if applicable.<br/>"
                        "Terms and conditions only if applicable.",
                        nota_style
                    ))

                elif proceso == "Google_MAPS":

                    bloque.append(Paragraph(
                        "<b>Business Address Verification in Google Maps</b>",
                        titulo_style
                    ))
                    bloque.append(Paragraph(
                        "If the address is not found in Google Maps, validate it using Facebook, Instagram, or LinkedIn.",
                        nota_style
                    ))

                else:
                    titulo = PROCESS_NAMES.get(proceso, proceso)
                    bloque.append(Paragraph(f"<b>{titulo}</b>", titulo_style))

                    try:
                        ai_results_dir = Path(sqlite_path).parent / "ai_results"
                        ai_file = ai_results_dir / f"Resultado_AI_{proceso}.txt"

                        if ai_file.exists():
                            with open(ai_file, "r", encoding="utf-8") as f:
                                ai_text = f.read().strip()

                            if ai_text:
                                bloque.append(Spacer(1, 6))
                                ai_text_clean = ai_text.replace("\n", "<​br/>")
                                bloque.append(Paragraph(ai_text_clean, styles["Normal"]))
                                bloque.append(Spacer(1, 10))

                    except Exception as e:
                        print(f"⚠ Error loading AI text for {proceso}: {e}")

                bloque.append(Spacer(1, 10))
                first = False

            if "before" in imgs and "after" in imgs:
                img_before, _ = preparar_imagen(imgs["before"], max_width_half, max_height)
                img_after, _ = preparar_imagen(imgs["after"], max_width_half, max_height)

                table = Table([
                    ["Before Search", "After Search"],
                    [img_before, img_after]
                ], colWidths=[max_width_half, max_width_half])

                bloque.append(table)
                bloque.append(Spacer(1, 25))

            elif "after" in imgs:
                img, _ = preparar_imagen(imgs["after"], max_width_single, max_height)
                img.hAlign = "CENTER"
                bloque.append(img)
                bloque.append(Spacer(1, 25))

            elif "before" in imgs:
                img, _ = preparar_imagen(imgs["before"], max_width_single, max_height)
                img.hAlign = "CENTER"
                bloque.append(img)
                bloque.append(Spacer(1, 25))

            elementos.append(KeepTogether(bloque))

    # =====================================================
    # 🔥 BUILD PDF
    # =====================================================
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=letter,
        topMargin=80
    )

    doc.build(
        elementos,
        onFirstPage=draw_header,
        onLaterPages=draw_header
    )

    print(f"📄 PDF report created: {output_pdf}")


async def initialize_admin_browser(playwright):

    browser = await playwright.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )

    context = await browser.new_context(
        viewport={"width":1366,"height":768},
        locale="en-US"
    )

    page = await context.new_page()

    return browser, page   
    
async def initialize_google_browser(playwright):

    browser = await playwright.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )

    context = await browser.new_context(
        viewport={"width":1366,"height":768},
        locale="en-US"
    )

    await context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    page = await context.new_page()

    return browser, page  
   
def build_crp_dictionary(dataframe):

    crp_dict = {}

    if "CRP number" in dataframe.columns and "Name" in dataframe.columns:

        for _, r in dataframe.iterrows():

            crp_number = r["CRP number"]
            crp_name = r["Name"]

            if pd.notna(crp_number):

                crp_number = str(crp_number).strip()

                if pd.notna(crp_name):

                    crp_name = str(crp_name).strip()

                    if crp_name != "":
                        crp_dict[crp_number] = crp_name

    print("CRP dictionary loaded:")
    for k,v in crp_dict.items():
        print(k,"→",v)

    return crp_dict   

async def admin_validation_process(process, page_admin, tax_id, email, website, business_name, sqlite_path, case_number):

    if process == "ADM_DOC":

        print("🔎 Admin document validation")
        await search_merchant(
            page_admin,
            tax_id,
            "document",
            sqlite_path,
            case_number,
            process
        )

    elif process == "ADM_EMAIL":

        print("📧 Admin email validation")
        await search_merchant(
            page_admin,
            email,
            "contactEmail",
            sqlite_path,
            case_number,
            process
        )

    elif process == "ADM_WEB":

        print("🌐 Admin website validation")
        await search_merchant(
            page_admin,
            website,
            "url",
            sqlite_path,
            case_number,
            process
        )

    elif process == "ADM_MERCH_NAME":

        print("👤 Admin merchant name validation")
        await search_merchant(
            page_admin,
            business_name,
            "names",
            sqlite_path,
            case_number,
            process
        )
   
google_semaphore = asyncio.Semaphore(2)

async def google_search_process(process, crp_dict, page_google, browser_google, playwright):

    print("GOOGLE SEARCH FUNCTION CALLED")
    print("PROCESS:", process)

    if process.endswith("_String"):
        crp_number = process.replace("_String", "")
        search_type = "string"
    else:
        crp_number = process
        search_type = "normal"

    crp_name = crp_dict.get(crp_number)

    print(f"CRP {crp_number} → {crp_name}")

    if not crp_name:
        print(f"⚠ CRP name not found for {process}")
        return page_google, browser_google

    if search_type == "string":
        query = build_risk_query(crp_name)
    else:
        query = f'"{crp_name}"'

    max_attempts = 5

    for attempt in range(1, max_attempts + 1):

        print(f"🔎 Google attempt {attempt}/{max_attempts}")

        await asyncio.sleep(random.uniform(4, 12))

        async with google_semaphore:
            print("🌐 Entering Google semaphore...")
            await google_search(page_google, query)
            print("🌐 Leaving Google semaphore...")

        page_google, browser_google, captcha = await handle_google_captcha(
            playwright,
            page_google,
            browser_google,
            query=query
        )

        if not captcha:
            return page_google, browser_google, True  # ✅ éxito

    print(f"🚨 Max CAPTCHA attempts reached for: {process}")
    return page_google, browser_google, False  # ❌ fallo por CAPTCHA
     
async def Buscar_URL_Google(website, page_google, sqlite_path, case_number, process):

    try:

        if not website:
            print("⚠ No website available")
            return

        if not website.startswith("http"):
            website = "https://" + website

        print(f"🌐 Opening website: {website}")

        await page_google.goto(
            website,
            wait_until="domcontentloaded"
        )

        await page_google.wait_for_timeout(3000)

        await capture_process_screenshot(
            page_google,
            sqlite_path,
            case_number,
            process
        )

    except Exception as e:

        print(f"❌ Error in Buscar_URL_Google {process}: {e}")

async def Busqueda_procuraduria(numero_documento, page_google, sqlite_path, case_number, process):

    try:

        await page_google.goto(
            "https://www.procuraduria.gov.co/Pages/Consulta-de-Antecedentes.aspx",
            wait_until="domcontentloaded"
        )

        frame = page_google.frame_locator("iframe").first

        select = frame.locator("select[name='ddlTipoID']")
        await select.wait_for()

        opciones = await select.locator("option").all()

        objetivo = normalizar("Cédula de ciudadanía")

        for opcion in opciones:

            texto = normalizar(await opcion.inner_text())

            if texto == objetivo:
                valor = await opcion.get_attribute("value")
                await select.select_option(valor)
                break

        input_doc = frame.locator("input[name='txtNumID']")
        await input_doc.wait_for()
        await input_doc.fill(numero_documento)

        await frame.locator("#lblPregunta").wait_for()

        max_intentos = 6
        screenshot_taken = False

        for intento in range(max_intentos):

            pregunta = await frame.locator("#lblPregunta").inner_text()
            pregunta_norm = normalizar(pregunta)

            print(f"🧩 Captcha procuraduria: {pregunta}")

            nums = re.findall(r"\d+", pregunta_norm)
            resultado = None

            # 🔥 VALIDACIÓN DESPUÉS de nums
            if len(nums) < 2:
                print(f"⚠ Captcha inválido: {pregunta}")
                refresh_btn = frame.locator("#ImageButton1")

                if await refresh_btn.count() == 0:
                    print("❌ BOTÓN REFRESH NO ENCONTRADO")
                    continue

                pregunta_antes = pregunta

                for intento_refresh in range(3):  # 🔥 reintentos de click

                    print(f"🔄 Intento refresh #{intento_refresh + 1}")
                    
                    await refresh_btn.click(force=True)

                    await asyncio.sleep(1.5)

                    pregunta_despues = await frame.locator("#lblPregunta").inner_text()

                    print(f"🔁 Antes: {pregunta_antes}")
                    print(f"🔁 Después: {pregunta_despues}")

                    if pregunta_antes != pregunta_despues:
                        print("✅ CAPTCHA CAMBIÓ CORRECTAMENTE")
                        break
                    else:
                        print("⚠ CAPTCHA NO CAMBIÓ, reintentando...")

                else:
                    print("❌ NO SE PUDO CAMBIAR CAPTCHA DESPUÉS DE 3 INTENTOS")
                continue

            # 🔥 OPERACIONES
            if any(op in pregunta_norm for op in ["x", "*", "por", "multiplica"]):
                resultado = int(nums[0]) * int(nums[1])

            elif any(op in pregunta_norm for op in ["+", "mas"]):
                resultado = int(nums[0]) + int(nums[1])

            elif any(op in pregunta_norm for op in ["-", "menos"]):
                resultado = int(nums[0]) - int(nums[1])

            elif any(op in pregunta_norm for op in ["/", "dividido"]):
                resultado = int(nums[0]) // int(nums[1])

            if resultado is not None:

                await frame.locator(
                    "input[name='txtRespuestaPregunta']"
                ).fill(str(resultado))

                await asyncio.sleep(random.uniform(1,2))

                await frame.locator(
                    "input[name='btnConsultar']"
                ).click()

                await page_google.wait_for_load_state("networkidle")
                await asyncio.sleep(5)

                await capture_process_screenshot(
                    page_google,
                    sqlite_path,
                    case_number,
                    process
                )

                print(f"📸 Screenshot OK: {process}")

                screenshot_taken = True
                break

            else:
                print(f"⚠ No se pudo interpretar captcha: {pregunta}")
                await frame.locator("input[alt='Pregunta']").click()


        # 🔥 ESTE PRINT SOLO SI FALLÓ DE VERDAD
        if not screenshot_taken:
            print(f"❌ NO SCREENSHOT - Captcha not solved for process: {process} case_number {case_number}")


        
    except Exception as e:

        print(f"❌ Procuraduria error: {e}")

MAX_RETRIES = 3

# ==========================================
# Retry wrapper for async processes
# ==========================================
async def process_with_retries_async(sqlite_path, process, ejecutar_async):

    conn = sqlite3.connect(sqlite_path, timeout=30)
    cursor = conn.cursor()

    try:
        for intento in range(1, MAX_RETRIES + 1):
            try:
                await ejecutar_async()
                update_process_status(sqlite_path, process, "completed")
                return True

            except CaptchaExhaustedError as ce:
                # 🔥 No reintentar aquí, dejar en processing para la ronda
                print(f"⏸ [{process}] CAPTCHA exhausted → leaving in 'processing' for round retry")
                # NO actualizar status → queda en 'processing'
                return False  # salir del wrapper sin marcar completed ni error

            except Exception as e:
                print(f"⚠ [{process}] Attempt {intento}/{MAX_RETRIES} failed: {e}")
                if intento == MAX_RETRIES:
                    update_process_status(sqlite_path, process, f"issue: after {MAX_RETRIES} attempts: {str(e)[:80]}")
                    return False
                await asyncio.sleep(3)

    finally:
        conn.close()

async def Busqueda_google_maps(
    Billing_Address,
    page_google,
    sqlite_path,
    case_number,
    process
):

    try:

        if not Billing_Address:
            print("⚠ No query provided for Google Maps")
            return

        print(f"🗺 Opening Google Maps for: {Billing_Address}")

        # ==========================================
        # 🔥 GO TO GOOGLE MAPS
        # ==========================================

        await page_google.goto(
            "https://www.google.com/maps",
            wait_until="domcontentloaded"
        )

        await page_google.wait_for_timeout(3000)

        input_busqueda = page_google.locator("input[name='q']")

        await input_busqueda.wait_for()

        async with google_semaphore:
            await input_busqueda.fill(Billing_Address)
            await input_busqueda.press("Enter")

        # ⏳ esperar resultados
        await page_google.wait_for_timeout(2000)

        # ==========================================
        # 🔥 SCREENSHOT
        # ==========================================

        await capture_process_screenshot(
            page_google,
            sqlite_path,
            case_number,
            process
        )

    except Exception as e:

        print(f"❌ Error in Google Maps process {process}: {e}")

async def search_RUES( tax_id, page_google, sqlite_path, case_number, process ):

    try:

        if not tax_id:
            print("⚠ No query provided for RUES")
            return

        print(f"🏛 Opening RUES search for: {tax_id}")

        # ==========================================
        # GO TO RUES WEBSITE
        # ==========================================

        await page_google.goto(
            "https://www.rues.org.co/busqueda-avanzada",
            wait_until="domcontentloaded"
        )

        await page_google.wait_for_timeout(3000)

        print(f"Processing tax_id: {tax_id}")

        # ==========================================
        # HANDLE RATE LIMIT
        # ==========================================

        if (
            await page_google.locator("#main-frame-error").count() > 0
            or await page_google.locator("text=HTTP ERROR 429").count() > 0
        ):
            print("⚠️ RUES rate limit detected. Pausing worker...")
            await asyncio.sleep(60)
            await page_google.reload()
            await page_google.wait_for_timeout(5000)

        # ==========================================
        # VALIDATE DROPDOWN
        # ==========================================

        await page_google.wait_for_selector(
            'select#select-tipo',
            state='visible',
            timeout=5000
        )

        selected_text = await page_google.locator(
            'select#select-tipo option:checked'
        ).text_content()

        if normalizar(selected_text) != normalizar("Registro Mercantil"):

            update_process_status(
                sqlite_path,
                process,
                "issue: registro mercantil not selected"
            )

            return

        # ==========================================
        # SEARCH BY NIT
        # ==========================================

        async def cambiar_tipo_registro(tipo_value):
            await page_google.select_option('select#select-tipo', tipo_value)
            await asyncio.sleep(random.uniform(0.5, 1.0))

        async def hacer_busqueda_rues(nit_value):
            await page_google.fill('input[name="Nit"]', "")
            await asyncio.sleep(random.uniform(0.4, 1.2))
            await page_google.click('input[name="Nit"]')
            await asyncio.sleep(random.uniform(0.2, 0.8))
            await page_google.fill('input[name="Nit"]', nit_value)
            await page_google.wait_for_selector("button:has-text('Buscar')", state="visible")
            await asyncio.sleep(random.uniform(1, 2))
            await page_google.click("button:has-text('Buscar')")
            await page_google.wait_for_timeout(2000)

        tax_id_short = tax_id.strip()[:-1]
        encontrado = False

        # --- Intento 1: RM + NIT completo ---
        print(f"🔍 Intento 1: RM + NIT completo ({tax_id})")
        await cambiar_tipo_registro("RM")
        await hacer_busqueda_rues(tax_id)

        if not await no_results_found(page_google):
            print("✅ Resultado encontrado: RM + NIT completo")
            encontrado = True

        # --- Intento 2: RM + NIT sin último dígito ---
        if not encontrado:
            print(f"🔍 Intento 2: RM + NIT sin último dígito ({tax_id_short})")
            await hacer_busqueda_rues(tax_id_short)

            if not await no_results_found(page_google):
                print("✅ Resultado encontrado: RM + NIT sin último dígito")
                encontrado = True

        # --- Intento 3: ESAL + NIT completo ---
        if not encontrado:
            print(f"🔍 Intento 3: ESAL + NIT completo ({tax_id})")
            await cambiar_tipo_registro("ESAL")
            await hacer_busqueda_rues(tax_id)

            if not await no_results_found(page_google):
                print("✅ Resultado encontrado: ESAL + NIT completo")
                encontrado = True

        # --- Intento 4: ESAL + NIT sin último dígito ---
        if not encontrado:
            print(f"🔍 Intento 4: ESAL + NIT sin último dígito ({tax_id_short})")
            await hacer_busqueda_rues(tax_id_short)

            if not await no_results_found(page_google):
                print("✅ Resultado encontrado: ESAL + NIT sin último dígito")
                encontrado = True

        # --- Sin resultados en todos los intentos ---
        if not encontrado:
            print("⚠ No results found in RUES after all attempts → capturing evidence")

            await page_google.evaluate("window.scrollTo(0,0)")
            await page_google.wait_for_timeout(500)

            await capture_process_screenshot(
                page_google,
                sqlite_path,
                case_number,
                process,
                custom_name=f"{process}_NO_RESULTS"
            )

            update_process_status(
                sqlite_path,
                process,
                "issue: no results found in RUES"
            )

            return

        # ==========================================
        # ENTER DETAIL VIEW
        # ==========================================
        
        await page_google.wait_for_selector("text=Ver información", state="visible", timeout=5000)

        await page_google.locator("text=Ver información").first.click()

        await asyncio.sleep(random.uniform(2, 4))

        # ==========================================
        # GENERAL INFORMATION
        # ==========================================
        # Navigate to the "General Information" tab
        await page_google.locator('a:has-text("Información general")').wait_for(timeout=5000)
        await page_google.locator('a:has-text("Información general")').click()
        # Wait until the tab content loads
        await page_google.wait_for_selector("#detail-tabs-tabpane-pestana_general", timeout=5000)
        
        await page_google.evaluate("window.scrollTo(0, 75)")
        await asyncio.sleep(random.uniform(1,2))
        await capture_process_screenshot( page_google, sqlite_path, case_number, process, custom_name=f"{process}_GENERAL" )

        await page_google.mouse.wheel(0, random.randint(300, 800))
        await asyncio.sleep(random.uniform(1,2))

        # ==========================================
        # ECONOMIC ACTIVITY
        # ==========================================
        # Navigate to the economic activity tab
        tab_economic = page_google.locator('a:has-text("Actividad económica")')
        await tab_economic.wait_for(state="visible")
        await tab_economic.click()
        # Wait until the tab content loads
        await page_google.wait_for_selector( "#detail-tabs-tabpane-pestana_economica", timeout=5000)
        
        await page_google.evaluate("window.scrollTo(0, 50)")
        await asyncio.sleep(random.uniform(1,2))
        await capture_process_screenshot(page_google, sqlite_path, case_number, process, custom_name=f"{process}_ECONOMIC")

        await page_google.mouse.wheel(0, random.randint(300, 800))
        await asyncio.sleep(random.uniform(1,2))

        # ==========================================
        # LEGAL REPRESENTATIVE
        # ==========================================
        # Wait until the legal representative tab becomes visible
        await page_google.wait_for_selector("text=Representante legal", state="visible", timeout=5000)

        # Open the legal representative tab
        await page_google.click("text=Representante legal")
        # Wait for the container that holds the legal information
        await page_google.wait_for_selector("div.legal", timeout=5000)
        await asyncio.sleep(random.uniform(2,3))
        
        await capture_process_screenshot( page_google, sqlite_path, case_number, process, custom_name=f"{process}_LEGAL" )

        # ==========================================
        # FINAL SMALL DELAY
        # ==========================================

        await asyncio.sleep(random.uniform(1,2))

    except Exception as e:

        print(f"❌ Error in RUES process {process}: {e}")

# ==========================================================
# MAIN SUNAT FUNCTION
# ==========================================================
async def search_SUNAT(tax_id, page_google, case_number, process):

    error_screenshot = None

    try:

        if not tax_id:
            print("⚠ No query provided")
            error_screenshot = f"{process}_NO_RESULTS_SEARCH"
            return

        print(f"🏛 Searching SUNAT for: {tax_id}")

        await page_google.goto(
            "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp",
            wait_until="domcontentloaded"
        )

        await page_google.wait_for_timeout(3000)

        locator_ruc = page_google.locator("#txtRuc")
        await locator_ruc.wait_for(state="visible")

        await locator_ruc.fill(str(tax_id))
        await page_google.locator("#btnAceptar").click()

        await page_google.wait_for_load_state("networkidle")

        try:
            # ================= FIRST TABLE =================
            await page_google.locator(
                "div.list-group h4:has-text('Número de RUC:')"
            ).wait_for(timeout=15000)

            print("✅ RUC found")

            # 📸 FIRST SCREENSHOT
            await capture_process_screenshot(
                page_google, case_number, process,
                custom_name=f"{process}_RUC_GENERAL"
            )

            # ================= CLICK REPRESENTANTES =================
            await page_google.locator(".btnInfRepLeg").click()
            await page_google.wait_for_load_state("networkidle")

            try:
                # ================= SECOND TABLE =================
                panel = page_google.locator("div.panel.panel-primary")
                await panel.wait_for(state="visible", timeout=15000)

                rows = panel.locator("tbody tr")

                if await rows.count() > 0:
                    print("✅ Representatives loaded")

                    # 📸 SECOND SCREENSHOT
                    await capture_process_screenshot(
                        page_google, case_number, process,
                        custom_name=f"{process}_RUC_REPRESENTANTES_LEGALES"
                    )

                else:
                    print("⚠ No representatives found")
                    error_screenshot = f"{process}_NO_RESULTS_REPRESENTANTES"

            except Exception as e:
                print(f"❌ Error loading representatives: {e}")
                error_screenshot = f"{process}_NO_RESULTS_REPRESENTANTES"

        except Exception as e:
            print(f"❌ RUC not found: {e}")
            error_screenshot = f"{process}_NO_RESULTS_SEARCH"

    except Exception as e:
        print(f"❌ General error: {e}")
        error_screenshot = f"{process}_ERROR"

    # ================= FINAL ERROR SCREENSHOT =================
    if error_screenshot:
        await capture_process_screenshot(
            page_google, case_number, process,
            custom_name=error_screenshot
        )

# ============================================================================
# Detect "No Results Found" in RUES Portal
# ============================================================================
# Checks whether the RUES search returned no results.
# It repeatedly checks for the message within a small time window.
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

async def no_results_found(page):

    try:
        await page.wait_for_selector(
            "text=No se han encontrado resultados",
            timeout=5000
        )
        return True

    except PlaywrightTimeoutError:
        return False

def update_process_status(sqlite_path, process, message):

    print(f"📝 Updating status → {process}: {message}")

    conn = sqlite3.connect(sqlite_path, timeout=30)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM aci_status WHERE process=?",
        (process,)
    )

    if cursor.fetchone() is None:
        print(f"⚠ Process not found in DB: {process}")
    else:
        cursor.execute("""
            UPDATE aci_status
            SET status=?
            WHERE process=?
        """, (message, process))

        conn.commit()

    conn.close()

def get_process_group(process_name):

    try:
            
        if process_name.startswith("ADM"):
            return "ADMIN"

        elif process_name.startswith("CRP"):
            return "CRP"

        elif process_name.startswith("Google_PROCURADURIA_"):
            return "PROCURADURIA"

        elif process_name in ("Google_URL", "Google_MAPS", "Google_RUES"):
            return "GOOGLE"

        return "OTHER"

    except Exception as e:

            print(f"❌ Error in get_process_group: {e}")

def get_images_for_ai_process(sqlite_path, case_number, process):
    """
    Retorna la lista de imágenes correspondientes a un proceso AI.

    - CRP-XXXX_AI → solo imágenes normales
    - CRP-XXXX_String_AI → solo imágenes con _String
    """

    try:
        # =====================================================
        # 📂 UBICAR CARPETA DE SCREENSHOTS
        # =====================================================
        base_path = Path(sqlite_path).parent
        screenshots_path = base_path / "screenshots"

        if not screenshots_path.exists():
            print("⚠ Screenshots folder not found")
            return []

        # =====================================================
        # 🔥 LIMPIAR NOMBRE DEL PROCESO
        # =====================================================
        base_name = process.replace("_AI", "")  # CRP-XXXX o CRP-XXXX_String

        print(f"🔎 Searching images for: {base_name}")

        # =====================================================
        # 📸 LISTAR TODAS LAS IMÁGENES
        # =====================================================
        all_images = list(screenshots_path.glob("*.png"))

        if not all_images:
            print("⚠ No images found in folder")
            return []

        # =====================================================
        # 🔍 FILTRAR SEGÚN TIPO
        # =====================================================
        if "_String" in base_name:

            # 🟣 SOLO STRING LIMPIO
            filtered_images = [
                str(img) for img in all_images
                if base_name in img.name
                and "_part_" in img.name
            ]

        else:

            # 🔵 SOLO NORMAL (EXCLUYE STRING Y OTROS PROCESOS)
            filtered_images = [
                str(img) for img in all_images
                if base_name in img.name
                and "_part_" in img.name
                and "_String" not in img.name
                and "PROCURADURIA" not in img.name
                and "RUES" not in img.name
                and "MAPS" not in img.name
            ]

        # =====================================================
        # 🔢 ORDENAR IMÁGENES
        # =====================================================
        filtered_images.sort()

        print(f"📸 Images found: {len(filtered_images)}")

        return filtered_images

    except Exception as e:
        print(f"❌ Error getting images: {e}")
        return []

# ============================================================================
# AI WORKER
# ============================================================================
async def initialize_ai_browser(playwright):
    
    try:

        browser = await playwright.chromium.launch(
            headless=False
        )

        context = await browser.new_context(accept_downloads=True)

        page = await context.new_page()

        return browser, page

    except Exception as e:

        print(f"❌ Error in initialize_ai_browser: {e}")
        return None, None

# ============================================================================
# AI WORKER
# ============================================================================
async def run_ai_worker(page_AI, process, sqlite_path, case_number, carpeta_salida_ai, prompt_path):

    try:

        # ===============================
        # 🔍 Worker context info
        # ===============================
        print("\n🧠 ===============================")
        print("🤖 AI WORKER START")
        print(f"📌 Process: {process}")
        print(f"📂 SQLite: {sqlite_path}")
        print(f"🧾 Case: {case_number}")
        print(f"📁 Output folder: {carpeta_salida_ai}")
        print(f"📄 Prompt path: {prompt_path}")
        print("🧠 ===============================\n")

        # =====================================================
        # 🔥 GET IMAGES FOR THIS PROCESS
        # =====================================================
        imagenes = get_images_for_ai_process(
            sqlite_path,
            case_number,
            process
        )

        print(f"📸 Total images found: {len(imagenes) if imagenes else 0}")

        # 👉 No images → marcar como skipped, no como completed
        if not imagenes:
            print(f"⚠ No images found for {process} → marking as skipped")
            update_process_status(sqlite_path, process, "skipped: no screenshots found")
            return True  # True para que process_with_retries no lo marque como failed

        # =====================================================
        # 🔥 CLEAN DOCUMENT ID
        # =====================================================
        document_id = process.replace("_AI", "")
        print(f"🧾 Document ID: {document_id}")

        # =====================================================
        # 🔥 CALL AI PROCESS
        # =====================================================
        print(f"🚀 Sending process to AI: {process}")

        result = await AI_Process(
            page_AI,
            imagenes,
            carpeta_salida_ai,
            prompt_path,
            document_id
        )

        print(f"📥 Raw AI result: {result}")

        # =====================================================
        # 🔍 RESULT DEBUG
        # =====================================================
        if result and isinstance(result, tuple):
            print(f"📊 AI status: {'SUCCESS' if result[0] else 'FAIL'}")

        # =====================================================
        # 🔥 HANDLE RESULT
        # =====================================================
        if result and isinstance(result, tuple) and result[0]:
            print(f"🏁 END AI WORKER SUCCESS: {process}")
            return True
        else:
            print(f"🏁 END AI WORKER FAILED: {process}")
            return False

    except Exception as e:
        print(f"❌ Error in AI worker {process}: {e}")
        return False


# ============================================================================
# LOGIN INTO ABACUS AI
# ============================================================================
# ============================================================================
# LOGIN INTO ABACUS AI
# ============================================================================
async def login_abacus_ai(page, email, password):

    try:
        await page.goto("https://apps.abacus.ai/chatllm/?appId=99650cb1c")

        await page.fill('input[name="email"]', email)
        await page.fill('input[name="question"]', password)

        await page.click('button[type="submit"]')

        # 🔍 VALIDAR LOGIN
        textarea_selector = 'textarea[placeholder="Write something..."]'
        await page.wait_for_selector(textarea_selector, timeout=10000)

        print("✅ Login exitoso")
        return True

    except Exception as e:
        print(f"❌ Login fallido: {e}")
        return False

       
# ============================================================================
# Validate Legal Text Before AI Processing
# ============================================================================
# Ensures the extracted legal text is valid before sending it to AI.
def is_valid_legal_text(text):
    try:
        
        if not text:
            return False

        normalized = normalizar(text)

        if "informacion no disponible" in normalized:
            return False

        if len(text.strip()) < 20:
            return False

        return True 
    except Exception as e:

            print(f"❌ Error in is_valid_legal_text: {e}")
      

# ============================================================================
# MAIN AI PROCESS
# ============================================================================
async def AI_Process(page_AI, imagenes, Ruta_Resultado_AI, Ruta_prompt_txt, document_id): 

    try:

        print("\n🤖 ===== AI_PROCESS START =====")
        print(f"📄 Document ID: {document_id}")
        print(f"📂 Output path: {Ruta_Resultado_AI}")
        print(f"📄 Prompt file: {Ruta_prompt_txt}")

        # =====================================================
        # 🔹 LOAD PROMPT
        # =====================================================
        if not os.path.exists(Ruta_prompt_txt):
            print(f"❌ PROMPT FILE NOT FOUND: {Ruta_prompt_txt}")
            print("🏁 AI_PROCESS FAILED (NO PROMPT)")
            return False, None

        with open(Ruta_prompt_txt, "r", encoding="utf-8") as f:
            prompt_extractor_payu = f.read()

        if not prompt_extractor_payu.strip():
            print("❌ Prompt file is empty")
            print("🏁 AI_PROCESS FAILED (EMPTY PROMPT)")
            return False, None

        print(f"📝 Prompt loaded ({len(prompt_extractor_payu)} characters)")

        # =====================================================
        # 🔥 SEND PROMPT + IMAGES
        # =====================================================
        print("📤 Sending prompt and images to AI...")

        await imagenes_texto_en_AI(
            page_AI,
            prompt_extractor_payu,
            imagenes
        )

        # =====================================================
        # 🔥 WAIT FOR AI RESPONSE
        # =====================================================
        if await esperar_boton_normal(page_AI):

            print("⬇ Downloading AI result")

            selector_antiguo = 'svg[data-prefix="fad"][data-icon="download"]'
            selector_nuevo = '[data-id="preparingDownload"]'

            selector_boton = None

            if await page_AI.locator(selector_nuevo).count() > 0:
                selector_boton = selector_nuevo
                print("Using new selector")

            elif await page_AI.locator(selector_antiguo).count() > 0:
                selector_boton = selector_antiguo
                print("Using old selector")

            else:
                print("❌ Download button not found")
                return False, None

            # =====================================================
            # 📂 CREATE ai_results FOLDER (LIKE SCREENSHOTS)
            # =====================================================
            ai_results_dir = os.path.join(Ruta_Resultado_AI, "ai_results")

            os.makedirs(ai_results_dir, exist_ok=True)

            # =====================================================
            # 📄 FILE PATH INSIDE ai_results
            # =====================================================
            nombre_archivo = os.path.join(
                ai_results_dir,
                f"Resultado_AI_{document_id}.txt"
            )

            if await descargar_archivo(page_AI, selector_boton, nombre_archivo):
                print("🏁 AI_PROCESS SUCCESS")
                return True, nombre_archivo
            else:
                print("❌ File download failed")
                print("🏁 AI_PROCESS FAILED (DOWNLOAD)")
                return False, None

        else:
            print("❌ AI did not finish correctly")
            print("🏁 AI_PROCESS FAILED (TIMEOUT)")
            return False, None

    except Exception as e:
        print(f"❌ Error in AI_Process: {e}")
        return False, None
  
# ============================================================================
# SEND PROMPT AND IMAGES TO AI
# ============================================================================
async def imagenes_texto_en_AI(page, texto, imagenes):

    try:
        print("\n📨 === SENDING INPUT TO AI ===")

        await page.wait_for_timeout(4000)

        textarea_selector = 'textarea[placeholder="Write something..."]'

        # =====================================================
        # 📝 WRITE PROMPT
        # =====================================================
        await page.fill(textarea_selector, texto)
        print("📝 Prompt written in AI input")

        await page.wait_for_timeout(1500)

        # =====================================================
        # 📸 UPLOAD IMAGES
        # =====================================================
        if imagenes:

            print(f"📸 Uploading {len(imagenes)} images...")

            for img_path in imagenes:
                print(f"🖼️ Image: {os.path.basename(img_path)}")

            await page.locator("[data-id='paperclip']").click(force=True)

            await page.wait_for_selector("input[type='file']", timeout=10000)

            file_inputs = page.locator("input[type='file']")
            input_count = await file_inputs.count()

            print(f"🔎 File inputs detected: {input_count}")

            file_input = file_inputs.nth(input_count - 1)

            await file_input.set_input_files(imagenes)

            print("📤 Images loaded into input")

            if await esperar_subida_imagenes(page, timeout=60):

                print("✅ All images uploaded successfully")

                send_button = page.locator('[data-id="send"]')
                await send_button.wait_for(state="visible", timeout=10000)
                await send_button.click()

                print("🚀 Request sent to AI")

            else:
                print("⚠ Some images did not finish uploading")

        else:
            print("⚠ No images to upload")

        await asyncio.sleep(1)

    except Exception as e:
        print(f"❌ Error in imagenes_texto_en_AI: {e}")

async def esperar_subida_imagenes(page, timeout=60):
    try:
        """
        Espera hasta 'timeout' segundos a que desaparezcan todos los loaders de subida de imagen.
        Cuando desaparecen, espera 2 segundos y vuelve a validar.
        Devuelve True si realmente desaparecen antes del timeout, False si siguen presentes.
        """
        await page.wait_for_timeout(4000)
        loader_selector = 'svg.fa-arrows-rotate.fa-spin'
        tiempo_inicial = asyncio.get_event_loop().time()
        while True:
            loaders = await page.query_selector_all(loader_selector)
            if not loaders:
                # Espera 2 segundos y vuelve a validar
                await asyncio.sleep(3)
                print("⏳ Waiting for image upload to complete...")
                loaders = await page.query_selector_all(loader_selector)
                if not loaders:
                    return True  # Confirmado: todas las imágenes terminaron de subir
                # Si reaparecieron loaders, sigue esperando
            if asyncio.get_event_loop().time() - tiempo_inicial > timeout:
                print("⏳ Waiting for image upload to complete...")
                return False  # Timeout: aún quedan loaders
            await asyncio.sleep(0.5)
    except Exception as e:

        print(f"❌ Error in esperar_subida_imagenes: {e}")


# ============================================================================
# WAIT FOR AI RESPONSE
# ============================================================================
async def esperar_boton_normal(page, timeout=60, intentos=3):

    print("⏳ Waiting for AI response...")

    for intento in range(1, intentos + 1):

        print(f"🔄 Attempt {intento} waiting for AI...")

        try:
            await page.wait_for_selector(
                'button:has(.fa-paper-plane):not(.cursor-not-allowed)',
                state='visible',
                timeout=timeout * 1000
            )

            print("✅ AI response completed")
            return True

        except Exception:
            print("⏳ AI still processing...")

        await asyncio.sleep(2)

    print("🚨 AI did not respond in time")
    return False

# ============================================================================
# DOWNLOAD AI RESULT FILE
# ============================================================================
# Clicks the download button in the AI interface,
# waits for the file to be generated, and saves it locally.
# Returns True if the file was downloaded successfully.
async def descargar_archivo(page, selector_boton, nombre_archivo):

    try:

        await page.wait_for_timeout(5000)

        async with page.expect_download(timeout=120000) as download_info:
            await page.locator(selector_boton).last.click()

        download = await download_info.value

        await download.save_as(nombre_archivo)

        if os.path.exists(nombre_archivo) and os.path.getsize(nombre_archivo) > 0:

            print("Descarga exitosa")
            print(f"Ruta: {nombre_archivo}")

            return True

        else:

            print("No se descargó archivo")

            return False

    except Exception as e:

        print(f"Error descargando archivo: {e}")

        return False









