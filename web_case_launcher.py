# web_case_launcher.py

import asyncio
import config
import random


# ==========================================
# IMPORTS
# ==========================================
from Utilities_Bot_CheckList import (
    test_credentials,
    evidence_collection_process,
    generar_reporte_pdf,
    build_sqlite_from_template,
    get_pending_processes,
    reset_processing_to_pending,
    has_pending_processes,
    mark_remaining_processing_as_issue
)

async def ejecutar_proceso(
    admin_user,
    admin_pass,
    ruta_excel,
    case_summary,
    underwriting_link,
    ruta_imagen,
    num_hilos
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
        # CRP + MERCHANT GEMINI SEARCH (WITH ROUNDS)
        # ======================================

        print("🔍 Running CRP / Merchant Gemini searches...")

        CRP_PREFIXES = ["CRP", "Merchant_"]

        MAX_ROUNDS = 3

        for ronda in range(1, MAX_ROUNDS + 1):

            print(f"\n🔁 === ROUND {ronda}/{MAX_ROUNDS} ===")

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

            print(f"✅ Round {ronda} finished")

            if ronda < MAX_ROUNDS:
                reseteados = reset_processing_to_pending(sqlite_path, prefixes=CRP_PREFIXES)
                if reseteados == 0:
                    print("✅ No CRP/Merchant processes stuck in processing, no next round needed")
                    break
                else:
                    print(f"🔄 {reseteados} processes reset to pending → starting round {ronda + 1}")
                    await asyncio.sleep(random.uniform(15, 30))
            else:
                mark_remaining_processing_as_issue(sqlite_path)
                print("🚨 Final round completed, remaining processes marked as issue")

        # ======================================
        # GENERATE PDF
        # ======================================

        generar_reporte_pdf(
            case_number,
            sqlite_path,
            admin_user,
            case_summary,
            underwriting_link,
            ruta_imagen
        )

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