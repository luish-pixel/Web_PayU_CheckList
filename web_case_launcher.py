# web_case_launcher.py

import asyncio
import config
import random
import threading


# ==========================================
# IMPORTAR las nuevas funciones
# ==========================================
from Utilities_Bot_CheckList import (
    test_credentials,
    evidence_collection_process,
    generar_reporte_pdf,
    build_sqlite_from_template,
    google_search_process,
    get_pending_processes,
    AI_Process,
    reset_processing_to_pending,       
    has_pending_processes,             
    mark_remaining_processing_as_issue 
)

def ejecutar_busquedas(sqlite_path, case_number):
    pendientes = get_pending_processes(sqlite_path)

    procesos_busqueda = [
        p for p in pendientes
        if "GOOGLE" in p.upper() or "CRP-" in p.upper() or "MERCHANT_" in p.upper()
    ]

    if not procesos_busqueda:
        return

    num_workers = config.SEARCH_WORKERS
    chunks = [procesos_busqueda[i::num_workers] for i in range(num_workers)]

    hilos = []
    for i, chunk in enumerate(chunks):
        if not chunk:
            continue
        t = threading.Thread(
            target=google_search_process,
            args=(chunk, sqlite_path, case_number, f"Worker_{i+1}")
        )
        hilos.append(t)
        t.start()

    for t in hilos:
        t.join()    

def ejecutar_ai(sqlite_path, case_number):
    pendientes = get_pending_processes(sqlite_path)

    procesos_ai = [
        p for p in pendientes
        if p.upper().endswith("_AI") or p.upper().endswith("_STRING_AI")
    ]

    if not procesos_ai:
        print("✅ No pending AI processes")
        return

    num_workers = config.AI_WORKERS
    chunks = [procesos_ai[i::num_workers] for i in range(num_workers)]

    hilos = []
    for i, chunk in enumerate(chunks):
        if not chunk:
            continue
        t = threading.Thread(
            target=AI_Process,
            args=(chunk, sqlite_path, case_number, f"AI_Worker_{i+1}")
        )
        hilos.append(t)
        t.start()

    for t in hilos:
        t.join()

    print("✅ All AI workers finished")
    
async def ejecutar_proceso(
    admin_user, admin_pass,
    ruta_excel,
    case_summary,
    ruta_imagen, num_hilos
):

    try:

        print("\n==============================")
        print("RPA BOT - CASE MANAGER")
        print("==============================")

        # ======================================
        # VALIDATE ADMIN CREDENTIALS
        # ======================================

        print("🔐 Validating admin credentials...")

        credenciales_validas = await test_credentials(admin_user, admin_pass)

        if not credenciales_validas:
            return "❌ Invalid admin credentials."

        print("✅ Admin credentials validated")

        # ======================================
        # PREPARE CASE DATA
        # ======================================

        success, df_case, sqlite_path = build_sqlite_from_template(ruta_excel)
        
        if not success:
            return "❌ Could not process Excel template."

        case_number = df_case["Case Number"].iloc[0]

        print("📊 Case data ready")
        print("📂 SQLite:", sqlite_path)

        # ======================================
        # CRP WORKER CALCULATION
        # ======================================

        crp_count = df_case["CRP number"].dropna().nunique()
        num_hilos = min(config.SEARCH_WORKERS, crp_count) if crp_count > 0 else 1

        print(f"🧠 CRP detected: {crp_count}")
        print(f"🧵 CRP workers: {num_hilos}")

        # ======================================
        # ADMIN (1 WORKER)
        # ======================================

        print("🔧 Running Admin validations...")

        await evidence_collection_process(
            df_case,
            sqlite_path,
            admin_user,
            admin_pass,
            1,
            "ADMIN"
        )

        # ======================================
        # GOOGLE URL (1 WORKER)
        # ======================================

        print("🌐 Running Google URL validation...")

        await evidence_collection_process(
            df_case,
            sqlite_path,
            admin_user,
            admin_pass,
            2,
            "GOOGLE"
        )

        # ======================================
        # PROCURADURIA WORKERS
        # ======================================

        print("⚖ Running Procuraduria searches...")

        df_pending = get_pending_processes(sqlite_path)

        proc_count = df_pending[
            df_pending["process"].str.startswith("Google_PROCURADURIA_")
        ].shape[0]

        num_proc_workers = min(config.SEARCH_WORKERS, proc_count) if proc_count > 0 else 1

        print(f"⚖ Procuraduria processes: {proc_count}")
        print(f"⚖ Procuraduria workers: {num_proc_workers}")

        tareas_proc = []

        for i in range(num_proc_workers):

            task = asyncio.create_task(
                evidence_collection_process(
                    df_case,
                    sqlite_path,
                    admin_user,
                    admin_pass,
                    i + 5,
                    "PROCURADURIA"
                )
            )

            tareas_proc.append(task)

            if i < num_proc_workers - 1:
                delay = random.randint(4, 8)
                print(f"⏳ Delay before next Procuraduria worker: {delay}s")
                await asyncio.sleep(delay)

        await asyncio.gather(*tareas_proc)

        # ======================================
        # CRP + MERCHANT GOOGLE SEARCH (CON RONDAS)
        # ======================================

        print("🔎 Running CRP searches...")

        # 🔥 Solo revisar procesos CRP y Merchant en las rondas
        CRP_PREFIXES = ["CRP", "Merchant_"]

        MAX_ROUNDS = 3

        for ronda in range(1, MAX_ROUNDS + 1):

            print(f"\n🔁 === RONDA {ronda}/{MAX_ROUNDS} ===")

            # Verificar si hay CRP/Merchant pendientes antes de lanzar workers
            if not has_pending_processes(sqlite_path, prefixes=CRP_PREFIXES):
                print("✅ No pending CRP/Merchant processes, skipping round")
                break

            tareas = []

            for i in range(num_hilos):
                task = asyncio.create_task(
                    evidence_collection_process(
                        df_case,
                        sqlite_path,
                        admin_user,
                        admin_pass,
                        i + 8,
                        "CRP"
                    )
                )
                tareas.append(task)

            await asyncio.gather(*tareas, return_exceptions=True)

            print(f"✅ Ronda {ronda} terminada")

            if ronda < MAX_ROUNDS:
                # 🔥 Solo resetear CRP/Merchant, no tocar ADMIN, AI, etc.
                print(f"🔍 DEBUG reset llamado con sqlite_path={sqlite_path}, prefixes={CRP_PREFIXES}")
                reseteados = reset_processing_to_pending(sqlite_path, prefixes=CRP_PREFIXES)
                if reseteados == 0:
                    print("✅ No quedaron procesos CRP/Merchant en processing, no se necesita otra ronda")
                    break
                else:
                    print(f"🔄 {reseteados} procesos reseteados a pending → iniciando ronda {ronda + 1}")
                    await asyncio.sleep(random.uniform(15, 30))
            else:
                # Última ronda → marcar los que siguen en processing como issue
                mark_remaining_processing_as_issue(sqlite_path)
                print("🚨 Ronda final completada, procesos restantes marcados como issue")

        # ======================================
        # AI WORKERS
        # ======================================

        print("🤖 Running AI processes...")

        print("📊 Snapshot antes de AI:")
        df_debug = get_pending_processes(sqlite_path)
        print(df_debug.head(20))

        df_pending_ai = get_pending_processes(sqlite_path)

        ai_count = df_pending_ai[
            df_pending_ai["process"].str.endswith("_AI")
        ].shape[0]

        num_ai_workers = min(config.AI_WORKERS, ai_count) if ai_count > 0 else 1

        print(f"🤖 AI processes: {ai_count}")
        print(f"🤖 AI workers: {num_ai_workers}")

        tareas_ai = []

        for i in range(num_ai_workers):

            task = asyncio.create_task(
                evidence_collection_process(
                    df_case,
                    sqlite_path,
                    admin_user,
                    admin_pass,
                    i + 20,
                    "AI"
                )
            )

            tareas_ai.append(task)

            if i < num_ai_workers - 1:
                delay = random.randint(3, 6)
                print(f"⏳ Delay before next AI worker: {delay}s")
                await asyncio.sleep(delay)

        await asyncio.gather(*tareas_ai)

        # ======================================
        # GENERATE PDF
        # ======================================

        generar_reporte_pdf(case_number, sqlite_path, admin_user, case_summary, ruta_imagen)

        # ======================================
        # FINAL RESULT
        # ======================================

        print(f"🔍 DEBUG case_number: {case_number}")
        print(f"🔍 DEBUG sqlite_path: {sqlite_path}")
        print(f"🔍 DEBUG num_hilos: {num_hilos}")
        print(f"🔍 DEBUG num_proc_workers: {num_proc_workers}")

        return f"""
✅ PROCESS COMPLETED

📄 Case: {case_number}
📂 SQLite: {sqlite_path}
🧵 CRP Workers: {num_hilos}
⚖ Procuraduria Workers: {num_proc_workers}
"""

    except Exception as e:

        return f"❌ Error during execution:\n{str(e)}"