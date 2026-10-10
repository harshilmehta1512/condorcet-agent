from streamlit.testing.v1 import AppTest

from ui.data import ROOT, TITLES


def test_all_reports_render_and_guided_review_persists():
    app = AppTest.from_file(str(ROOT / "ui/app.py"), default_timeout=30).run()
    assert not app.exception
    for name in TITLES:
        app.session_state["selected_report"] = name
        app.run()
        assert not app.exception, name
    app.session_state["selected_report"] = "ev_market"
    app.run()
    for label in ["Saved human review", "Real models · evidence slices", "Real models · full evidence"]:
        app.selectbox[0].set_value(label).run()
        assert not app.exception, label
    app.session_state["selected_report"] = "agi_timelines"
    app.run()
    app.toggle[1].set_value(True).run()
    app.button(key="evidence_agi_timelines").click().run()
    assert "Evidence" in app.session_state["review_steps"]["agi_timelines"]
    assert not app.exception


def test_human_submission_updates_state_without_losing_initial():
    app = AppTest.from_file(str(ROOT / "ui/app.py"), default_timeout=30).run()
    app.radio[0].set_value("Confirmed")
    app.text_area[0].set_value("Geely annual report: 1.49 million new-energy vehicles.")
    app.button(key="FormSubmitter:human_form_ev_market-Update decision").click().run()
    assert not app.exception
    after = app.session_state["review_results"]["ev_market"]
    assert after["before"]["action"] == "ESCALATE"
    assert after["action"] != "APPROVE"
