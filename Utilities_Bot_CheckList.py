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

        country = strip_accents(
            str(
                merchant_row.get("Country", "") or ""
            ).strip().lower()
        )

        if "colombia" in country:
            return "colombia"

        if "peru" in country:
            return "peru"

        return "unknown"

    def detect_crp_country(crp_row):

        text = strip_accents(
            str(
                crp_row.get(
                    "Company city (Registry data)",
                    ""
                ) or ""
            ).strip().lower()
        )

        # =========================================
        # COUNTRY DIRECT DETECTION
        # =========================================

        if "colombia" in text:
            return "colombia"

        if "peru" in text:
            return "peru"

        # =========================================
        # CITY DETECTION
        # =========================================

        if any(city in text for city in COLOMBIAN_CITIES):
            return "colombia"

        if any(city in text for city in PERU_CITIES):
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
        # MERCHANT GEMINI PROCESSES
        # =========================
        merchant_name = normalize_missing(row.get("Company name (Registry data)"))
        merchant_name_status = "pending" if merchant_name != "missing data" else "missing data"

        expected["Merchant_Name"]        = merchant_name_status
        expected["Merchant_Name_String"] = merchant_name_status

        merchant_email = normalize_missing(row.get("Firm Email"))
        merchant_email_status = "pending" if (merchant_email != "missing data" and "@" in str(merchant_email)) else "missing data"

        expected["Merchant_Email"]        = merchant_email_status
        expected["Merchant_Email_String"] = merchant_email_status

        # =========================
        # CRP GEMINI PROCESSES
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

            expected[f"{crp_number}"]        = crp_base_status
            expected[f"{crp_number}_String"] = crp_base_status

            procuraduria_key = f"Google_PROCURADURIA_{crp_number}"
            if crp_country == "colombia":
                expected[procuraduria_key] = "missing data" if personal_id == "missing data" else "pending"
            else:
                expected[procuraduria_key] = "not applicable: CRP is not from Colombia"

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
            "Country",
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

        
        df_merch.loc[0, "Country"] = normalize_missing(
            df_merch.loc[0, "Country"]
        )
        
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

        browser_admin  = None
        browser_google = None

        try:

            if data_to_use.empty:
                print("⚠️ No records to process")
                return

            print(f"🚀 Starting Evidence Collection - Partition {partition_number}")

            page_admin   = None
            page_google  = None
            admin_session_active = False


            row = data_to_use.iloc[0]

            case_number     = row["Case Number"]
            business_name   = row["Company name (Registry data)"]
            tax_id          = row["Tax Identification Number"]
            email           = row["Firm Email"]
            website         = row["Website"]
            billing_address = data_to_use["Billing Address"].dropna().unique()[0]

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
                if process.startswith("ADM") and process_type in ("ALL", "ADMIN"):

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
                # CRP / MERCHANT GEMINI SEARCH
                # ==========================================
                elif (
                    process.startswith("CRP") or
                    process.startswith("Merchant_Name") or
                    process.startswith("Merchant_Email")
                ) and process_type in ("ALL", "CRP", "MERCHANT", "GEMINI"):
                
                    print(f"🔍 [GEMINI] First Gemini process detected: {process}")
                    print("🌐 Launching dual tab Gemini session...")
                
                    # Put the current process back to pending so the tab workers pick it up
                    update_process_status(sqlite_path, process, "pending")
                
                    # Run both tabs in parallel — they will consume all pending
                    # CRP/Merchant processes from SQLite until none are left
                    await run_gemini_dual_tab_session(
                        playwright           = playwright,
                        sqlite_path          = sqlite_path,
                        prompt_general_path  = config.PROMPT_GENERAL_PATH,
                        prompt_specific_path = config.PROMPT_SPECIFIC_PATH,
                        crp_dict             = crp_dict,
                        business_name        = business_name,
                        email                = email
                    )
                    
                    print("🔥 GEMINI SESSION COMPLETED")
                    print("✅ Gemini dual tab session completed")
                
                    # After session ends, break the while loop for this worker
                    # since all Gemini processes have been handled
                    break

                # ==========================================
                # GOOGLE URL
                # ==========================================
                elif process == "Google_URL" and process_type in ("ALL", "GOOGLE"):

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
                # PROCURADURIA (COLOMBIA ONLY)
                # ==========================================
                elif process.startswith("Google_PROCURADURIA_") and process_type in ("ALL", "PROCURADURIA"):

                    print("⚖ Procuraduria validation")

                    if not page_google:
                        browser_google, page_google = await initialize_google_browser(playwright)

                    async def run_proc():
                        crp = process.replace("Google_PROCURADURIA_", "").strip()
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
                elif process == "Google_RUES" and process_type in ("ALL", "GOOGLE"):

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
                elif process == "Google_SUNAT" and process_type in ("ALL", "GOOGLE"):

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
                elif process == "Google_MAPS" and process_type in ("ALL", "GOOGLE"):

                    print("🗺 Processing Google Maps")

                    if not page_google:
                        browser_google, page_google = await initialize_google_browser(playwright)

                    async def run_maps():
                        await Busqueda_google_maps(
                            billing_address,
                            page_google,
                            sqlite_path,
                            case_number,
                            process
                        )

                    await process_with_retries_async(sqlite_path, process, run_maps)

        except Exception as e:
            print(f"❌ Critical error: {e}")

        finally:

            if browser_admin:
                await browser_admin.close()

            if browser_google:
                await browser_google.close()

            


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


async def capture_process_screenshot(page, sqlite_path, case_number, process, custom_name=None):
    screenshots_dir = Path(sqlite_path).parent / "screenshots" / str(case_number)
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    process_name = custom_name if custom_name else process

    # 📋 CONFIGURACIÓN: Procesos que SÍ necesitan scroll completo (case-sensitive)
    SCROLL_PROCESSES = [
        "Merchant_Name",
        "Merchant_Email",
        "Google_URL",
        "Google_RUES_LEGAL",
        "LEGAL"
    ]

    needs_scroll = any(p in process_name for p in SCROLL_PROCESSES)

    # =====================================================
    # 📸 MODO SINGLE (ADMIN, MAPS, URL, ETC)
    # =====================================================
    if not needs_scroll:
        file_path = screenshots_dir / f"{process_name}_part_0.png"

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
        file_path = screenshots_dir / f"{process_name}_part_{part}.png"

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
        
        cursor.execute("INSERT INTO aci_status VALUES (?, ?)", (f"{crp_id}", name_status))
        cursor.execute("INSERT INTO aci_status VALUES (?, ?)", (f"{crp_id}_String", name_status))

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


    
   
       
def get_next_process(sqlite_path, process_type="ALL"):

    conn = sqlite3.connect(sqlite_path, timeout=30)
    cursor = conn.cursor()

    print("\n-----------------------------")
    print("GET NEXT PROCESS CALLED")
    print("process_type:", process_type)

    try:

        conn.execute("BEGIN IMMEDIATE")

        print("📊 Current pending status:")
        cursor.execute("SELECT process FROM aci_status WHERE status='pending'")
        rows_debug = cursor.fetchall()
        print("➡ Pending:", [r[0] for r in rows_debug][:10])

        if process_type == "ADMIN":
            filter_clause = "process LIKE 'ADM%'"

        elif process_type == "CRP":
            filter_clause = """(
                process LIKE 'CRP%'
                OR process LIKE 'Merchant_Name%'
                OR process LIKE 'Merchant_Email%'
            )"""

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

        print(f"🔍 DEBUG SQL query: {query}")
        cursor.execute(query)
        row = cursor.fetchone()

        print("SQL RESULT:", row)

        if row is None:
            print("⚠️ No processes available for this worker")
            conn.commit()
            conn.close()
            return None

        process = row[0]
        print(f"🎯 SELECTED PROCESS: {process}")

        cursor.execute("""
            UPDATE aci_status
            SET status='processing'
            WHERE process=?
        """, (process,))

        conn.commit()
        conn.close()

        print(f"🎯 PROCESS LOCKED: {process}")
        return process

    except Exception as e:

        print("❌ get_next_process error:", e)
        conn.rollback()
        conn.close()
        return None



    
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


def generar_reporte_pdf(case_number,sqlite_path,admin_user, case_summary=None,underwriting_link=None,ruta_imagen=None):

    print("🔥 STARTING PDF GENERATION")
    print(f"📄 Case Number: {case_number}")

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

        FUENTE_BASE   = "AmpleSoft"
        FUENTE_BOLD   = "AmpleSoft-Bold"
        FUENTE_ITALIC = "AmpleSoft"
    except Exception as e:
        print("⚠ No se pudo cargar AmpleSoft, usando Helvetica")
        print("❌ ERROR REAL:", e)
        FUENTE_BASE   = "Helvetica"
        FUENTE_BOLD   = "Helvetica-Bold"
        FUENTE_ITALIC = "Helvetica-Oblique"

    def P(texto, bold=False, color="black", size=11):
        font = FUENTE_BOLD if bold else FUENTE_BASE
        return Paragraph(
            f'<font name="{font}" color="{color}" size="{size}">{texto}</font>',
            styles["Normal"]
        )

    screenshots_dir = Path(sqlite_path).parent / "screenshots" / str(case_number)
    output_pdf      = Path(sqlite_path).parent / f"CASE_{case_number}_evidence.pdf"

    styles = getSampleStyleSheet()

    styles["Normal"].fontName  = FUENTE_BASE
    styles["Normal"].fontSize  = 11
    styles["Normal"].alignment = TA_JUSTIFY

    styles["Title"].fontName   = FUENTE_BOLD
    styles["Title"].fontSize   = 12
    styles["Title"].alignment  = TA_LEFT

    styles["Heading2"].fontName  = FUENTE_BOLD
    styles["Heading2"].fontSize  = 12
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

    link_style = ParagraphStyle(
        name="LinkStyle",
        parent=styles["Normal"],
        fontName=FUENTE_BASE,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#777777"),
        spaceAfter=4,
    )

    # =====================================================
    # HEADER + FOOTER
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

        BASE_DIR  = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
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
    # SQLITE DATA
    # =====================================================
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM aci_data LIMIT 1')
    row = cursor.fetchone()

    company_name = row["Company name (Registry data)"] if row else "N/A"
    mcc_code     = row["MCC code: MCC"] if row else ""
    mcc_desc     = row["MCC Description"] if row else ""
    mcc_text     = f"{int(mcc_code)} - {mcc_desc}" if mcc_code else "N/A"

    conn.close()

    # =====================================================
    # HEADER TABLE
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
    # TITLE
    # =====================================================
    elementos.append(Paragraph(f"Case Evidence Report: {case_number}", styles["Title"]))
    elementos.append(Spacer(1, 20))

    # =====================================================
    # CHECKLIST STATUS TABLE (GROUPED)
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

                data = [["Process", "Status", "Remediation or justification"]]

                for process_name, status_value in sorted(grouped[group_name]):
                    data.append([
                        Paragraph(process_name, styles["Normal"]),
                        Paragraph(status_value, styles["Normal"]),
                        Paragraph("", styles["Normal"]),
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
    # BUSINESS MODEL
    # =====================================================

    if case_summary or underwriting_link:

        elementos.append(Paragraph("Business Model", titulo_style))
        elementos.append(Spacer(1, 10))

        elementos.append(Paragraph(
            "General summary and analysis of the merchant; the underwriting must be attached ",
            nota_style
        ))

        elementos.append(Spacer(1, 10))

        # ==========================================
        # SUMMARY MODE
        # ==========================================

        if case_summary and case_summary.strip():

            clean_summary = case_summary.replace("\n", "<br/>")

            elementos.append(
                Paragraph(clean_summary, styles["Normal"])
            )

        # ==========================================
        # LINK MODE
        # ==========================================

        elif underwriting_link and underwriting_link.strip():

            safe_link = (
                underwriting_link
                .strip()
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

            link_html = f'''
            <b>Open Link →</b><br/>
            <a href="{safe_link}">
                {safe_link}
            </a>
            '''

            elementos.append(
                Paragraph(link_html, styles["Normal"])
            )

        elementos.append(Spacer(1, 20))
    
    # =====================================================
    # DOCUMENT IMAGE
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
        bloque_doc.append(Spacer(1, 10))

        img_reader = ImageReader(ruta_imagen)
        w, h      = img_reader.getSize()
        scale     = min(456 / w, 500 / h, 1)

        img        = Image(ruta_imagen, width=w * scale, height=h * scale)
        img.hAlign = "CENTER"

        bloque_doc.append(img)
        bloque_doc.append(Spacer(1, 25))
        elementos.append(KeepTogether(bloque_doc))

    # =====================================================
    # CRP VALIDATION TITLE
    # =====================================================
    elementos.append(Paragraph("CRP Validation", titulo_style))
    elementos.append(Spacer(1, 10))
    elementos.append(Spacer(1, 10))

    # =====================================================
    # CRP TABLE FROM aci_data
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

        data = [["CRP number", "Name", "Status", "Role type", "Personal ID number"]]

        for r in rows:
            data.append([
                Paragraph(str(r["CRP number"])       if r["CRP number"]       else "", styles["Normal"]),
                Paragraph(str(r["Name"])              if r["Name"]              else "", styles["Normal"]),
                Paragraph(str(r["Status"])            if r["Status"]            else "", styles["Normal"]),
                Paragraph(str(r["Role type"])         if r["Role type"]         else "", styles["Normal"]),
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
    # LOAD STATUS DICT
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
    # HELPER — render Gemini txt content
    # Lines starting with http → grey link style
    # Lines starting with === → skip (redundant header)
    # All other lines → normal text
    # =====================================================
    def render_gemini_content(text: str) -> list:
        """
        Parse Gemini result text and return a list of Paragraph elements.
        URLs rendered in grey (#777777), header lines (===) skipped.
        """
        paragraphs = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                paragraphs.append(Spacer(1, 4))
                continue
            # Skip === header line — already shown as bold title above
            if line.startswith("===") and line.endswith("==="):
                continue
            # URL line → grey
            if line.startswith("http://") or line.startswith("https://"):
                safe_url = line.replace("&", "&amp;")
                paragraphs.append(Paragraph(
                    f'<font color="#777777">{safe_url}</font>',
                    link_style
                ))
            else:
                # Escape special XML chars
                safe_line = (
                    line
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                paragraphs.append(Paragraph(safe_line, styles["Normal"]))
        return paragraphs

    # =====================================================
    # IMAGES — screenshot-based processes
    # =====================================================
    imagenes = sorted(screenshots_dir.glob("*.png"))

    procesos_dict = defaultdict(lambda: defaultdict(dict))

    for img_path in imagenes:
        nombre      = img_path.stem
        is_before   = "_BEFORE" in nombre
        nombre_clean = nombre.replace("_BEFORE", "")

        match     = re.search(r"_part_(\d+)", nombre_clean)
        part      = int(match.group(1)) if match else 0
        base_name = re.sub(r"_part_\d+", "", nombre_clean)

        if is_before:
            procesos_dict[base_name][part]["before"] = img_path
        else:
            procesos_dict[base_name][part]["after"] = img_path

    max_width_half   = 220
    max_width_single = 456
    max_height       = 500

    def preparar_imagen(img_path, max_width, max_height):
        reader = ImageReader(str(img_path))
        w, h   = reader.getSize()
        scale  = min(max_width / w, max_height / h, 1)
        return Image(str(img_path), width=w * scale, height=h * scale), h * scale

    admin_header_shown        = False
    blacklist_header_shown    = False
    procuraduria_header_shown = False
    rues_header_shown         = False
    merchant_header_shown     = False
    crp_header_shown          = False

    # =====================================================
    # PROCESS ORDER
    # Google_MAPS is last (99) so Gemini results come before it
    # =====================================================
    def get_process_order(proceso):
        p = proceso.upper()
        if p.startswith("ADM"):            return 1
        elif "RUES" in p or "SUNAT" in p:  return 2
        elif "PROCURADURIA" in p:          return 3
        elif p == "GOOGLE_URL":            return 4
        elif p == "GOOGLE_MAPS":           return 99
        else:                              return 50

    # Split screenshot processes into two groups:
    # before_maps  → ADM, RUES, SUNAT, PROCURADURIA, Google_URL
    # after_gemini → Google_MAPS (rendered after Gemini block)
    procesos_ordenados = sorted(
        procesos_dict.items(),
        key=lambda x: (get_process_order(x[0]), x[0])
    )

    procesos_before_maps = [
        (p, parts) for p, parts in procesos_ordenados
        if get_process_order(p) < 99
    ]

    procesos_maps = [
        (p, parts) for p, parts in procesos_ordenados
        if get_process_order(p) == 99
    ]

    # =====================================================
    # SCREENSHOT LOOP HELPER
    # =====================================================
    def render_screenshot_proceso(proceso, partes):

        nonlocal admin_header_shown, blacklist_header_shown
        nonlocal procuraduria_header_shown, rues_header_shown

        process_status = get_pdf_process_status(proceso)
        if process_status == "missing data":
            print(f"⏭ Skipping PDF section for {proceso} (missing data)")
            return

        if not blacklist_header_shown and not proceso.upper().startswith("ADM"):
            blacklist_header_shown = True
            elementos.append(Spacer(1, 10))
            elementos.append(Paragraph(
                'Blacklist Verification in Salesforce (If the status is "Not Passed" / "Failed," '
                'a search is performed by name and ID in the blacklist).',
                titulo_style
            ))
            elementos.append(Spacer(1, 10))
            elementos.append(Spacer(1, 10))
            elementos.append(Spacer(1, 10))

        first = True

        for part in sorted(partes.keys()):
            imgs   = partes[part]
            bloque = []

            if first:

                if proceso.upper().startswith("ADM"):
                    if not admin_header_shown:
                        bloque.append(Paragraph(
                            "Admin Whitelist Verification (Search in Admin using name, "
                            "identification number, website, and email)",
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

                
                elif ("RUES" in proceso or "SUNAT" in proceso):
                    if not rues_header_shown:
                        bloque.append(Paragraph(
                            "<b>RUES (Merchant Identification and Verification)</b>",
                            titulo_style
                        ))
                        bloque.append(Paragraph(
                            "For other LATAM countries refer to Prevalidation documents file<br/>"
                            "and upload the relevant supporting evidence within the case or opportunity<br/>",
                            nota_style
                        ))
                        bloque.append(Spacer(1, 10))
                        rues_header_shown = True
                    bloque.append(Paragraph(f"<b>{proceso}</b>", titulo_style))

                elif proceso == "Google_URL":
                    bloque.append(Paragraph("<b>Economic Activity Identification</b>", titulo_style))
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
                        "If the address is not found in Google Maps, validate it using "
                        "Facebook, Instagram, or LinkedIn.",
                        nota_style
                    ))

                else:
                    titulo = PROCESS_NAMES.get(proceso, proceso)
                    bloque.append(Paragraph(f"<b>{titulo}</b>", titulo_style))

                bloque.append(Spacer(1, 10))
                first = False

            if "before" in imgs and "after" in imgs:
                img_before, _ = preparar_imagen(imgs["before"], max_width_half, max_height)
                img_after, _  = preparar_imagen(imgs["after"],  max_width_half, max_height)
                table = Table(
                    [["Before Search", "After Search"], [img_before, img_after]],
                    colWidths=[max_width_half, max_width_half]
                )
                bloque.append(table)
                bloque.append(Spacer(1, 25))

            elif "after" in imgs:
                img, _     = preparar_imagen(imgs["after"], max_width_single, max_height)
                img.hAlign = "CENTER"
                bloque.append(img)
                bloque.append(Spacer(1, 25))

            elif "before" in imgs:
                img, _     = preparar_imagen(imgs["before"], max_width_single, max_height)
                img.hAlign = "CENTER"
                bloque.append(img)
                bloque.append(Spacer(1, 25))

            elementos.append(KeepTogether(bloque))

    # =====================================================
    # RENDER ADM / RUES / SUNAT / PROCURADURIA / Google_URL
    # =====================================================
    for proceso, partes in procesos_before_maps:
        render_screenshot_proceso(proceso, partes)

    # =====================================================
    # GEMINI RESULTS — Merchant Name, Merchant Email, CRP
    # Rendered BEFORE Google Maps
    # =====================================================
    ai_results_dir = (
        Path(sqlite_path).parent
        / "ai_results"
        / str(case_number)
    )

    if ai_results_dir.exists():

        def get_gemini_order(filename):
            name = filename.stem.replace("Resultado_AI_", "")
            if name.startswith("Merchant_Name"):  return (1, name)
            if name.startswith("Merchant_Email"): return (2, name)
            if name.startswith("CRP"):            return (3, name)
            return (99, name)

        ai_txt_files = sorted(
            ai_results_dir.glob("Resultado_AI_*.txt"),
            key=get_gemini_order
        )

        for ai_file in ai_txt_files:

            process_name = ai_file.stem.replace("Resultado_AI_", "")

            # Only Gemini processes
            if not (
                process_name.startswith("CRP") or
                process_name.startswith("Merchant_Name") or
                process_name.startswith("Merchant_Email")
            ):
                continue

            # Skip missing data
            process_status = status_dict.get(process_name, "")
            if process_status == "missing data":
                print(f"⏭ Skipping Gemini PDF section for {process_name} (missing data)")
                continue

            # Read content
            try:
                with open(ai_file, "r", encoding="utf-8") as f:
                    ai_text = f.read().strip()
            except Exception as e:
                print(f"⚠ Error reading {ai_file}: {e}")
                continue

            if not ai_text:
                continue

            bloque = []

            # Section header — shown once for the entire Merchant + CRP block
            if (
                process_name.startswith("Merchant_") or process_name.startswith("CRP")
            ) and not merchant_header_shown and not crp_header_shown:
                bloque.append(Spacer(1, 10))
                bloque.append(Paragraph(
                    "Open-Source Search for News or Findings Related to the Merchant",
                    titulo_style
                ))
                bloque.append(Paragraph(
                    "Search using: legal name (without legal suffix), trade name, and email "
                    "(with and without risk string), and related parties.<br/>"
                    "If negative news is found, a deeper investigation must be conducted.<br/>"
                    "Related companies must be manually added in Salesforce for screening.<br/><br/>"
                    "Best practice (optional): review LinkedIn profiles and search related IDs in Google.",
                    nota_style
                ))
                bloque.append(Spacer(1, 10))
                merchant_header_shown = True
                crp_header_shown = True

            # Process title
            bloque.append(Paragraph(f"<b>{process_name}</b>", titulo_style))
            bloque.append(Spacer(1, 6))

            # Content — URLs in grey, === headers skipped
            bloque.extend(render_gemini_content(ai_text))
            bloque.append(Spacer(1, 15))

            elementos.append(KeepTogether(bloque))

    # =====================================================
    # GOOGLE MAPS — rendered AFTER Gemini results
    # =====================================================
    for proceso, partes in procesos_maps:
        render_screenshot_proceso(proceso, partes)

    # =====================================================
    # BUILD PDF
    # =====================================================
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=letter,
        topMargin=80
    )

    print("🔥 BUILDING PDF DOCUMENT")
    print(f"📦 Total elementos: {len(elementos)}")
    
    doc.build(
        elementos,
        onFirstPage=draw_header,
        onLaterPages=draw_header
    )

    print(f"📄 PDF report created: {output_pdf}")
    print("🔥 PDF BUILD COMPLETED")


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
                    process,
                    custom_name=f"{process}_RESULT"
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
async def search_SUNAT( tax_id, page_google, sqlite_path, case_number, process ): 

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
                page_google,
                sqlite_path,
                case_number,
                process,
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
                        page_google,
                        sqlite_path,
                        case_number,
                        process,
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
            page_google,
            sqlite_path,
            case_number,
            process,
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




import subprocess
import requests
import time

# ==========================================================
# CONFIGURATION
# ==========================================================

CDP_URL    = "http://localhost:9222"
TARGET_URL = "https://gemini.google.com/app"

SPINNER          = "div.bard-avatar.thinking"
STOP_BUTTON      = "div.blue-circle.stop-icon"
TEXTAREA         = "div.ql-editor[contenteditable='true']"
SEND_BUTTON      = "button.send-button.submit"
RESPONSE_BLOCK   = "div.presented-response-container"
RESPONSE_CONTENT = "div[id^='model-response-message-content']"

MAX_GEMINI_RETRIES = 3

# ==========================================================
# CHROME CDP
# ==========================================================

def wait_for_chrome(timeout=15):
    """Wait until Chrome exposes the remote debugging port."""
    for i in range(timeout):
        try:
            requests.get(CDP_URL, timeout=1)
            print(f"[Chrome] ✅ Chrome ready after {i+1}s.")
            return
        except Exception:
            print(f"  ... attempt {i+1}/{timeout}")
            time.sleep(1)
    raise TimeoutError("❌ Chrome did not expose port 9222 in time.")


def launch_chrome_if_needed():
    """Launch Chrome with remote debugging if it is not already running."""
    try:
        requests.get(CDP_URL, timeout=2)
        print("[Chrome] ✅ Chrome with remote debugging is already running.")
    except Exception:
        print("[Chrome] ⚠️ Chrome not running, attempting to launch...")

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            rf"C:\Users\{os.environ.get('USERNAME', '')}\AppData\Local\Google\Chrome\Application\chrome.exe",
        ]

        chrome_executable = next((p for p in chrome_paths if os.path.exists(p)), None)

        if not chrome_executable:
            raise FileNotFoundError("❌ Chrome executable not found in any known path.")

        user_data_dir = rf"C:\Users\{os.environ.get('USERNAME', 'default')}\AppData\Local\Temp\chrome-debug"

        subprocess.Popen([
            chrome_executable,
            "--remote-debugging-port=9222",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check"
        ])

        wait_for_chrome(timeout=15)


# ==========================================================
# PROMPT LOADER
# ==========================================================

def load_prompt(filepath: str, entity: str) -> str:
    """Read prompt file and replace the placeholder with the target entity."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return content.replace("[ENTIDAD]", f"{entity}")


# ==========================================================
# HELPERS
# ==========================================================

async def element_exists(page, selector: str) -> bool:
    """Return True if the selector matches at least one element on the page."""
    try:
        return await page.locator(selector).count() > 0
    except Exception:
        return False


async def clear_and_send_prompt(page, prompt: str) -> None:
    """Clear the Gemini textarea, paste the prompt, and submit it."""
    textarea = page.locator(TEXTAREA)
    await textarea.click()
    await asyncio.sleep(0.5)
    await textarea.press("Control+a")
    await textarea.press("Delete")
    await asyncio.sleep(0.3)

    await page.evaluate("""async (text) => {
        await navigator.clipboard.writeText(text);
    }""", prompt)

    await textarea.press("Control+v")
    await asyncio.sleep(2)
    await textarea.press("Enter")
    print("✅ Prompt submitted")


async def scroll_page(page) -> None:
    """Scroll the page to simulate human activity while Gemini processes."""
    for _ in range(3):
        await page.mouse.wheel(0, 500)
        await asyncio.sleep(random.uniform(0.8, 1.5))
        if await element_exists(page, SPINNER):
            return
        await page.mouse.wheel(0, 500)
        await asyncio.sleep(random.uniform(0.8, 1.5))
        if await element_exists(page, SPINNER):
            return
        await page.mouse.wheel(0, -500)
        await asyncio.sleep(random.uniform(0.8, 1.5))
        if await element_exists(page, SPINNER):
            return
        await page.mouse.wheel(0, -500)
        await asyncio.sleep(random.uniform(0.8, 1.5))
        if await element_exists(page, SPINNER):
            return


async def extract_response(page) -> str | None:
    """Extract the last response text from the Gemini chat."""
    try:
        last_block  = page.locator(RESPONSE_BLOCK).last
        content_div = last_block.locator(RESPONSE_CONTENT)
        await content_div.wait_for(state="visible", timeout=15_000)
        text = await content_div.inner_text()
        return text.strip() or None
    except Exception as e:
        print(f"⚠️ Error extracting response: {e}")
        return None


# ==========================================================
# GEMINI RESPONSE MONITOR
# ==========================================================

async def monitor_spinner(page) -> bool:
    """Wait until the thinking spinner disappears."""
    for attempt in range(1, 6):
        if not await element_exists(page, SPINNER):
            print(f"[Spinner {attempt}/5] ✅ Spinner gone")
            return True

        print(f"[Spinner {attempt}/5] 🔄 Processing...")

        if attempt < 5:
            for _ in range(60):
                await asyncio.sleep(1)
                if not await element_exists(page, SPINNER):
                    return True
        else:
            print("⛔ Spinner persisted after 5 attempts")
            return False


async def monitor_stop_button(page):
    """
    Wait until the stop button disappears (response finished).
    Returns True on success, False on timeout, None if spinner reappeared.
    """
    for attempt in range(1, 6):
        if not await element_exists(page, STOP_BUTTON):
            print(f"[Stop {attempt}/5] ✅ Response complete")
            return True

        print(f"[Stop {attempt}/5] 🔄 Response in progress...")

        if attempt < 5:
            for _ in range(60):
                await asyncio.sleep(1)
                if not await element_exists(page, STOP_BUTTON):
                    return True

            if await element_exists(page, SPINNER):
                print("🔁 Spinner reappeared → restarting cycle")
                return None
        else:
            print("⛔ Stop button persisted after 5 attempts")
            return False


async def monitor_gemini(page) -> tuple[bool, str | None]:
    """Orchestrate spinner + stop button monitoring and extract the response."""
    await asyncio.sleep(5)

    while True:
        spinner_ok = await monitor_spinner(page)
        if not spinner_ok:
            return False, None

        stop_result = await monitor_stop_button(page)

        if stop_result is True:
            text = await extract_response(page)
            return (True, text) if text else (False, None)
        elif stop_result is False:
            return False, None
        elif stop_result is None:
            continue


# ==========================================================
# SHOW MANUAL LOGIN POPUP
# ==========================================================

def show_gemini_login_popup() -> bool:
    """
    Show a popup asking the user to log in to Gemini manually.
    Returns True if user clicked Yes, False if No.
    """
    try:
        root = tk.Tk()
        root.withdraw()

        response = messagebox.askquestion(
            "Gemini Login Required",
            "Gemini is not logged in.\n\nPlease sign in manually in the Chrome window and then click YES.",
            icon="warning",
            type="yesno"
        )

        root.destroy()
        return response == "yes"

    except Exception as e:
        print(f"❌ Error showing login popup: {e}")
        return False


# ==========================================================
# OPEN A SINGLE GEMINI TAB
# ==========================================================

async def open_single_gemini_tab(context, tab_id: int):
    """
    Open one Gemini tab inside an existing CDP context.
    Applies a random delay before navigating to mitigate bot detection.
    Returns the page object.
    """
    page = await context.new_page()

    nav_delay = random.uniform(3, 5)
    print(f"[Tab {tab_id}] ⏳ Waiting {nav_delay:.1f}s before navigating...")
    await asyncio.sleep(nav_delay)

    await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=90_000)
    print(f"[Tab {tab_id}] ✅ Gemini loaded")

    # Dismiss popup if present
    try:
        popup = page.get_by_role("button", name="Got it")
        await popup.wait_for(state="visible", timeout=5_000)
        await popup.click()
    except Exception:
        pass

    return page


# ==========================================================
# CHECK LOGIN AND HANDLE SIGN IN
# Only called on Tab 1 during initialization
# ==========================================================

async def check_gemini_login(page) -> bool:

    LOGIN_SELECTOR = 'a[href*="ServiceLogin"]'

    while True:

        try:

            # ==========================================
            # DETECT LOGIN
            # ==========================================

            login_detected = await element_exists(
                page,
                LOGIN_SELECTOR
            )

            # ==========================================
            # DETECT PROFILE PICKER
            # ==========================================

            profile_picker_detected = (
                "profile-picker" in page.url.lower()
            )

            # ==========================================
            # VALIDATED
            # ==========================================

            if (
                not login_detected
                and not profile_picker_detected
            ):

                print(
                    "✅ [Gemini] "
                    "Login/profile validated"
                )

                return True

            # ==========================================
            # LOGS
            # ==========================================

            if login_detected:

                print(
                    "⚠️ [Gemini] "
                    "Google login detected"
                )

            if profile_picker_detected:

                print(
                    "⚠️ [Gemini] "
                    "Chrome profile picker detected"
                )

            # ==========================================
            # SHOW POPUP
            # ==========================================

            user_confirmed = show_gemini_login_popup()

            if not user_confirmed:

                print(
                    "❌ User cancelled "
                    "Gemini validation"
                )

                return False

            # ==========================================
            # WAIT BEFORE REVALIDATION
            # ==========================================

            print(
                "🔄 Revalidating "
                "Gemini state..."
            )

            await asyncio.sleep(3)

            # ==========================================
            # RELOAD GEMINI
            # ==========================================

            await page.goto(
                TARGET_URL,
                wait_until="domcontentloaded",
                timeout=90_000
            )

            await asyncio.sleep(3)

        except Exception as e:

            print(
                f"❌ Gemini validation error: {e}"
            )

            await asyncio.sleep(3)


# ==========================================================
# RECREATE A SINGLE FAILED TAB
# ==========================================================

async def recreate_gemini_tab(context, tab_id: int, failed_page=None):
    """
    Close the failed tab and open a new one in its place.
    Applies the same random delay before navigating.
    Returns the new page object.
    """
    if failed_page:
        try:
            await failed_page.close()
        except Exception:
            pass

    print(f"[Tab {tab_id}] 🔄 Recreating tab after failure...")
    new_page = await open_single_gemini_tab(context, tab_id=tab_id)
    return new_page


# ==========================================================
# SEND PROMPT AND GET RESPONSE ON A GIVEN PAGE
# ==========================================================
async def run_gemini_on_page(page, prompt: str, tab_id: int) -> str | None:
    """
    Send a prompt to an already-open Gemini tab and return the response text.
    Does NOT open or close the browser — reuses the existing page.
    """

    try:

        # ==========================================
        # VALIDATE GEMINI TEXTAREA
        # ==========================================

        textarea_exists = True

        try:

            await page.wait_for_selector(
                'div[contenteditable="true"][role="textbox"]',
                state="visible",
                timeout=5000
            )

        except Exception:

            textarea_exists = False

        if not textarea_exists:

            print(
                f"[Tab {tab_id}] ⚠️ "
                f"Gemini textarea not detected"
            )

            root = tk.Tk()

            root.withdraw()

            messagebox.showinfo(
                "Gemini Interface Issue",
                (
                    "Gemini input area was not detected.\n\n"
                    "Please verify the page manually.\n\n"
                    "Press OK when Gemini is ready."
                )
            )

            root.destroy()

            await page.wait_for_selector(
                'div[contenteditable="true"][role="textbox"]',
                state="visible",
                timeout=5000
            )

            print(
                f"[Tab {tab_id}] ✅ "
                f"Textarea detected again"
            )
        
        
        await clear_and_send_prompt(page, prompt)

        await asyncio.sleep(3)

        # ==========================================
        # KEEP ORIGINAL SCROLL
        # ==========================================

        await scroll_page(page)

        # ==========================================
        # WAIT GEMINI STARTS RESPONDING
        # ==========================================

        try:

            print(f"[Tab {tab_id}] ⏳ Waiting Gemini generation start...")

            await page.wait_for_selector(
                STOP_BUTTON,
                state="visible",
                timeout=15000
            )

            print(f"[Tab {tab_id}] 🤖 Gemini generation detected")

        except Exception:

            print(f"[Tab {tab_id}] ⚠️ Stop button not detected")

        # ==========================================
        # WAIT GEMINI FINISHES
        # ==========================================

        print(f"[Tab {tab_id}] ⏳ Waiting Gemini completion...")

        gemini_completed = False

        # ==========================================
        # FIRST TRY: SEND BUTTON
        # ==========================================

        try:

            await page.wait_for_selector(
                SEND_BUTTON,
                state="visible",
                timeout=30000
            )

            print(
                f"[Tab {tab_id}] ✅ "
                f"Send button detected"
            )

            gemini_completed = True

        except Exception:

            print(
                f"[Tab {tab_id}] ⚠️ "
                f"Send button not detected"
            )

        # ==========================================
        # SECOND TRY: MICROPHONE BUTTON
        # ==========================================

        if not gemini_completed:

            try:

                await page.wait_for_selector(
                    'button[aria-label="Microphone"]',
                    state="visible",
                    timeout=30000
                )

                print(
                    f"[Tab {tab_id}] 🎤 "
                    f"Microphone detected"
                )

                gemini_completed = True

            except Exception:

                print(
                    f"[Tab {tab_id}] ❌ "
                    f"Microphone not detected"
                )

        # ==========================================
        # FINAL VALIDATION
        # ==========================================

        if not gemini_completed:

            raise Exception(
                "Gemini completion not detected"
            )

        print(
            f"[Tab {tab_id}] ✅ "
            f"Gemini completed response"
        )

        await asyncio.sleep(2)

        # ==========================================
        # KEEP ORIGINAL SCROLL
        # ==========================================

        await scroll_page(page)

        success, text = await monitor_gemini(page)

        if success and text:
            return text

        print(f"[Tab {tab_id}] ⚠️ No response obtained")

        return None

    except Exception as e:

        print(f"[Tab {tab_id}] ❌ Error during search: {e}")

        return None




# ==========================================================
# GEMINI TAB WORKER
# Each tab runs independently in parallel.
# Both tabs compete for processes from the same SQLite.
# ==========================================================

async def run_gemini_tab_worker(
    tab_id: int,
    context,
    page,
    sqlite_path: str,
    prompt_general_path: str,
    prompt_specific_path: str,
    crp_dict: dict,
    business_name: str,
    email: str
):
    """
    Independent worker for one Gemini tab.
    Keeps pulling processes from SQLite and executing them
    until no more pending processes are available.
    Recreates the tab on failure and retries up to MAX_GEMINI_RETRIES times.
    """

    print(f"[Tab {tab_id}] 🚀 Worker started")

    while True:

        # Pull next available process for this tab
        process = get_next_process(sqlite_path, "CRP")

        if process is None:
            print(f"[Tab {tab_id}] ✅ No more processes — worker done")
            break

        print(f"[Tab {tab_id}] ➡ Process: {process}")

        # Determine search value
        if process.startswith("CRP"):
            crp_base     = process.replace("_String", "")
            search_value = crp_dict.get(crp_base)
            if not search_value:
                print(f"[Tab {tab_id}] ⚠ Name not found for {crp_base}")
                update_process_status(sqlite_path, process, "issue: CRP name not found")
                continue

        elif "Merchant_Name" in process:
            search_value = str(business_name).strip()

        elif "Merchant_Email" in process:
            search_value = str(email).strip()

        else:
            print(f"[Tab {tab_id}] ⚠ Unknown process type: {process}")
            update_process_status(sqlite_path, process, "issue: unknown process type")
            continue

        # Select prompt
        is_string_search = process.endswith("_String")
        prompt_path      = prompt_specific_path if is_string_search else prompt_general_path
        search_type      = "SPECIFIC" if is_string_search else "GENERAL"
        print(f"[Tab {tab_id}] {'🎯' if is_string_search else '🔍'} Using {search_type} prompt")

        prompt = load_prompt(str(prompt_path), search_value)

        # Execute with retries — each retry recreates the tab
        success = False

        for attempt in range(1, MAX_GEMINI_RETRIES + 1):
            print(f"[Tab {tab_id}] 🔄 Attempt {attempt}/{MAX_GEMINI_RETRIES} for: {process}")

            try:
                # Navigate to Gemini with random delay before each attempt
                nav_delay = random.uniform(3, 5)
                print(f"[Tab {tab_id}] ⏳ Navigating (delay {nav_delay:.1f}s)...")
                await asyncio.sleep(nav_delay)
                await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=90_000)
                await asyncio.sleep(2)
                

            except Exception as nav_error:
                print(f"[Tab {tab_id}] ❌ Navigation failed: {nav_error} → recreating tab")
                page = await recreate_gemini_tab(context, tab_id, failed_page=page)
                continue

            response = await run_gemini_on_page(page, prompt, tab_id)

            if response:
                # Save result
                file_content   = f"=== {process} ===\n{response}"
                case_number = Path(sqlite_path).stem.replace("ACI_", "")

                ai_results_dir = (
                    Path(sqlite_path).parent
                    / "ai_results"
                    / case_number
                )

                ai_results_dir.mkdir(parents=True, exist_ok=True)

                output_file = ai_results_dir / f"Resultado_AI_{process}.txt"

                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(file_content)

                print(f"[Tab {tab_id}] ✅ Saved: {output_file}")
                update_process_status(sqlite_path, process, "completed")
                success = True
                break

            # Response failed — recreate tab and retry
            print(f"[Tab {tab_id}] ⚠️ Attempt {attempt} failed → recreating tab")
            page = await recreate_gemini_tab(context, tab_id, failed_page=page)

        if not success:
            print(f"[Tab {tab_id}] 🚨 Process {process} failed after {MAX_GEMINI_RETRIES} attempts")
            update_process_status(
                sqlite_path,
                process,
                f"issue: after {MAX_GEMINI_RETRIES} attempts gemini did not respond"
            )

    # ==========================================
    # CLOSE TAB
    # ==========================================

    try:
        if page and not page.is_closed():
            await page.close()
            print(f"[Tab {tab_id}] 🛑 Gemini tab closed")
    except Exception as e:
        print(f"[Tab {tab_id}] ⚠ Error closing tab: {e}")

    print(f"[Tab {tab_id}] 🏁 Worker finished")

    return None


# ==========================================================
# INITIALIZE BOTH GEMINI TABS AND RUN PARALLEL WORKERS
# ==========================================================

async def run_gemini_dual_tab_session(
    playwright,
    sqlite_path: str,
    prompt_general_path: str,
    prompt_specific_path: str,
    crp_dict: dict,
    business_name: str,
    email: str
):
    """
    Initialize both Gemini tabs with delay between them,
    then run both tab workers in parallel via asyncio.gather.
    Tab 1 starts immediately after opening.
    Tab 2 starts after a 5-10s delay from Tab 1.
    """

    launch_chrome_if_needed()

    print("[CDP] Connecting to Chrome via CDP...")
    browser = await playwright.chromium.connect_over_cdp(CDP_URL)
    context = browser.contexts[0]

    try:

        # ── Open Tab 1 ──
        print("[Gemini] Opening Tab 1...")
        page_tab1 = await open_single_gemini_tab(context, tab_id=1)

        # ── Verify login on Tab 1 only ──
        login_ok = await check_gemini_login(page_tab1)
        if not login_ok:
            raise Exception("Gemini login failed or was cancelled")

        # ── Open Tab 2 with delay — Tab 1 starts working immediately after ──
        # We launch both workers with gather, but Tab 2 worker has a built-in
        # startup delay so Tab 1 gets a head start while Tab 2 is still opening.

        async def tab1_worker():
            return await run_gemini_tab_worker(
                tab_id               = 1,
                context              = context,
                page                 = page_tab1,
                sqlite_path          = sqlite_path,
                prompt_general_path  = prompt_general_path,
                prompt_specific_path = prompt_specific_path,
                crp_dict             = crp_dict,
                business_name        = business_name,
                email                = email
            )

        async def tab2_worker():
            # Delay + open Tab 2 before starting work
            inter_tab_delay = random.uniform(3, 5)
            print(f"[Gemini] ⏳ Waiting {inter_tab_delay:.1f}s before opening Tab 2...")
            await asyncio.sleep(inter_tab_delay)

            print("[Gemini] Opening Tab 2...")
            page_tab2 = await open_single_gemini_tab(context, tab_id=2)

            return await run_gemini_tab_worker(
                tab_id               = 2,
                context              = context,
                page                 = page_tab2,
                sqlite_path          = sqlite_path,
                prompt_general_path  = prompt_general_path,
                prompt_specific_path = prompt_specific_path,
                crp_dict             = crp_dict,
                business_name        = business_name,
                email                = email
            )

        # ── Run both workers in parallel ──
        print("🚀 Launching both Gemini tab workers in parallel...")
        await asyncio.gather(tab1_worker(), tab2_worker())

        print("✅ Both Gemini tab workers finished")
        print("🔥 EXITING run_gemini_dual_tab_session")

    finally:
        try:
            await browser.close()
        except Exception:
            pass


async def wait_gemini_response_complete(
    page,
    tab_name="Tab",
    timeout_ms=180000
):

    try:

        # ==========================================
        # WAIT GEMINI STARTS GENERATING
        # ==========================================

        print(f"[{tab_name}] ⏳ Waiting Gemini generation start...")

        await page.wait_for_selector(
            'button[aria-label="Stop response"]',
            timeout=15000
        )

        print(f"[{tab_name}] 🤖 Gemini generation detected")

        # ==========================================
        # WAIT GEMINI FINISHES
        # ==========================================

        print(f"[{tab_name}] ⏳ Waiting Gemini response completion...")

        await page.wait_for_selector(
            'button[aria-label="Send message"]',
            timeout=timeout_ms
        )

        print(f"[{tab_name}] ✅ Gemini response completed")

        return True

    except Exception as e:

        print(f"[{tab_name}] ❌ Gemini response timeout/error: {e}")

        return False


