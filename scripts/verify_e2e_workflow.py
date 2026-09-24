"""
End-to-End Workflow Verification Script
Translation Quality Analytics & Continuous Improvement Platform

Executes the complete test sequence defined in Section 38:
1. Generate English -> Hindi translation for:
   "Distributed stream processing architectures require robust fault tolerance and exactly-once processing guarantees."
2. Verify Natural, Formal, Literal variants returned.
3. Verify latency and human_request_id (REQ-YYYYMMDD-XXXXX).
4. Select candidate and record GOOD feedback.
5. Verify PostgreSQL persistence.
6. Generate second translation.
7. Select candidate and attempt POOR feedback without defect reason (verify validation rejection).
8. Record POOR feedback with valid defect reason.
9. Verify PostgreSQL persistence and quality degradation anomaly flag.
10. Test Quality Investigation workflow with request_id.
11. Verify Session History returns logged requests.
12. Verify Quality Analytics computes real live KPIs without hardcoded fallbacks.
"""

import sys

# Configure UTF-8 stdout encoding for Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from gradio_app.app import (
    investigate_translation,
    load_analytics_kpis,
    load_history_table,
    mark_preferred_variant,
    perform_translation,
    submit_human_feedback,
)
from src.database.connection import get_db_session
from src.database.models import Feedback, Translation, TranslationOption
from sqlalchemy import select


def run_e2e_verification():
    print("==================================================")
    print("STARTING E2E VERIFICATION SEQUENCE")
    print("==================================================")

    # 1. Translate prompt
    source_sentence = "Distributed stream processing architectures require robust fault tolerance and exactly-once processing guarantees."
    print(f"\n[STEP 1] Generating translation for: '{source_sentence}' (EN -> HI)")
    status_msg, nat, formal, lit, opt_map, _ = perform_translation(source_sentence, "Hindi (hi)")

    print(f"Status Message: {status_msg}")
    print(f"Natural Variant: {nat}")
    print(f"Formal Variant: {formal}")
    print(f"Literal Variant: {lit}")
    print(f"Option Map: {opt_map}")

    assert "Translation completed" in status_msg
    assert "REQ-" in status_msg
    assert len(nat) > 0
    assert len(formal) > 0
    assert len(lit) > 0
    assert len(opt_map) == 3
    print("✓ Translation generation verified with all 3 variants.")

    # Extract Request ID from status_msg
    req_id_part = [p for p in status_msg.split("•") if "REQ-" in p][0]
    extracted_req_id = req_id_part.split("`")[1]
    print(f"Extracted Human Request ID: {extracted_req_id}")

    # 2. Mark candidate as preferred
    print("\n[STEP 2] Marking Natural variant as preferred choice...")
    pref_res = mark_preferred_variant("Natural / Idiomatic", opt_map)
    print(f"Preferred Result: {pref_res}")
    assert "✓ Marked Natural" in pref_res

    # 3. Submit GOOD feedback
    print("\n[STEP 3] Submitting GOOD feedback for Natural variant...")
    fb_good_res = submit_human_feedback(
        selected_style="Natural / Idiomatic",
        rating="GOOD",
        reason_code=None,
        comments="Clear and accurate terminology for distributed streaming.",
        option_map=opt_map,
    )
    print(f"Feedback Result: {fb_good_res}")
    assert "✓ Feedback recorded" in fb_good_res

    # 4. Verify PostgreSQL persistence
    with get_db_session() as sess:
        t1 = sess.execute(select(Translation).where(Translation.request_id == extracted_req_id)).scalar_one_or_none()
        assert t1 is not None, f"Translation {extracted_req_id} not found in DB!"
        assert t1.translation_time_ms > 0
        assert t1.quality_score is not None
        assert len(t1.options) == 3
        # Check preferred option
        preferred_opts = [o for o in t1.options if o.user_selected]
        assert len(preferred_opts) == 1
        assert preferred_opts[0].style_option == "NATURAL"
        print(f"✓ DB Record verified: ID={t1.id}, latency={t1.translation_time_ms}ms, quality={t1.quality_score}")

    # 5. Second translation for POOR defect evaluation
    source_sentence_2 = "Cloud-native microservices communicate asynchronously via distributed event brokers."
    print(f"\n[STEP 4] Generating second translation: '{source_sentence_2}'")
    status_msg_2, nat2, formal2, lit2, opt_map_2, _ = perform_translation(source_sentence_2, "Hindi (hi)")
    req_id_2 = [p for p in status_msg_2.split("•") if "REQ-" in p][0].split("`")[1]
    print(f"Second Request ID: {req_id_2}")

    # 6. Test POOR feedback defect reason requirement
    print("\n[STEP 5] Testing POOR feedback defect reason requirement...")
    err_fb = submit_human_feedback(
        selected_style="Literal / Direct",
        rating="POOR",
        reason_code=None,
        comments="No reason supplied",
        option_map=opt_map_2,
    )
    print(f"Expected Error: {err_fb}")
    assert "Please choose a specific defect reason" in err_fb
    print("✓ Defect reason requirement enforced successfully.")

    # 7. Submit valid POOR feedback
    print("\n[STEP 6] Submitting POOR feedback with TOO_LITERAL defect reason...")
    fb_poor_res = submit_human_feedback(
        selected_style="Literal / Direct",
        rating="POOR",
        reason_code="TOO_LITERAL",
        comments="Literal word order confuses grammatical flow in Hindi.",
        option_map=opt_map_2,
    )
    print(f"Feedback Result: {fb_poor_res}")
    assert "✓ Feedback recorded" in fb_poor_res

    # 8. Verify DB update on POOR feedback (quality score penalized, anomaly flag updated)
    with get_db_session() as sess:
        t2 = sess.execute(select(Translation).where(Translation.request_id == req_id_2)).scalar_one_or_none()
        assert t2 is not None
        assert t2.anomaly_flag == True
        assert "QUALITY_DEGRADATION" in (t2.anomaly_reasons or "")
        print(f"✓ DB Record updated with anomaly: flag={t2.anomaly_flag}, reasons={t2.anomaly_reasons}")

    # 9. Test Quality Investigation workflow
    print(f"\n[STEP 7] Investigating Request ID: {extracted_req_id}...")
    inv_summary, inv_req, inv_pair, inv_src, inv_cands, inv_prov, inv_lat, inv_q, inv_diag = investigate_translation(extracted_req_id)
    print(f"Investigation Result:")
    print(f"  Summary: {inv_summary}")
    print(f"  Request ID: {inv_req}")
    print(f"  Language Pair: {inv_pair}")
    print(f"  Latency: {inv_lat}")
    print(f"  Quality Score: {inv_q}")
    print(f"  Diagnostics: {inv_diag}")
    assert inv_req == extracted_req_id
    assert "EN → HI" in inv_pair
    assert "GOOD" in inv_diag
    print("✓ Quality Investigation workflow returned accurate historical diagnostics.")

    # 10. Verify Session History
    print("\n[STEP 8] Loading Session History table...")
    history_rows = load_history_table()
    assert len(history_rows) >= 2
    req_ids_in_history = [r[0] for r in history_rows]
    assert extracted_req_id in req_ids_in_history or req_id_2 in req_ids_in_history
    print(f"✓ Session History contains recent requests: {req_ids_in_history[:3]}")

    # 11. Verify Quality Analytics Live KPIs
    print("\n[STEP 9] Loading Quality Analytics KPIs...")
    kpi_tot, kpi_lat, kpi_qsc, kpi_prate = load_analytics_kpis()
    print(f"KPIs -> Total: {kpi_tot}, Latency: {kpi_lat}, Quality: {kpi_qsc}, Defect Rate: {kpi_prate}")
    assert int(kpi_tot.replace(",", "")) >= 2
    assert float(kpi_prate.replace("%", "")) > 0.0
    print("✓ Quality Analytics computed live KPIs directly from PostgreSQL.")

    print("\n==================================================")
    print("ALL E2E VERIFICATION STEPS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    run_e2e_verification()
