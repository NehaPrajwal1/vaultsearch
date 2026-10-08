import copy
import json
import pytest
from app.acl import IdentityStore
from app.ollama_client import OllamaError
from redteam.api_probe import (GiB, LexicalRetriever, BudgetLLM, JournalLLM,
    memory_preflight, case_fixture, compatible_triplet, atomic_save)
from redteam.run_redteam import make_client, evaluate_case, stable_response
from redteam.presentation_probe import CASES
from test_redteam import Model


def identity():
    return IdentityStore({"user:ines": ["group:all-staff"]})


def corpus():
    return [{"chunk_id": name + "#0", "doc_id": name, "source": "fixture",
             "title": title, "text": text, "allowed_principals": acl}
            for name, title, text, acl in [
                ("lunch", "Cafeteria", "Lunch service opens at noon", ["group:all-staff"]),
                ("parking", "Parking", "Bicycles use the north entrance", ["group:all-staff"]),
                ("holiday", "Holiday", "The office closes in December", ["group:all-staff"]),
                ("restricted", "Assistant usage notes onboarding", "private records", ["group:finance"]),
            ]]


class StagedModel(Model):
    transport_attempted = True  # scripted delegate; never a real transport
    def chat_json(self, system, user):
        if system.startswith("You plan"):
            return {"subqueries": ["internal assistant usage notes onboarding"]}
        if system.startswith("You review"):
            return {"sufficient": True}
        return {"verdict": "grounded", "unsupported_claims": []}


@pytest.mark.parametrize("case", list(CASES))
@pytest.mark.parametrize("corpus_mode", ["existing", "controlled"])
def test_real_api_lexical_retrieval_and_completed_payload_accounting(case, corpus_mode, tmp_path):
    store = identity()
    chunks, kind, question, payloads = case_fixture(corpus(), case, store, "present", corpus_mode)
    report = {}
    snapshots = []
    def save():
        atomic_save(tmp_path/"checkpoint.json", report)
        snapshots.append(copy.deepcopy(report))
    model = StagedModel(CASES[case][1] + " [local-notes].")
    recorder = JournalLLM(model, payloads, report, save)
    client = make_client(LexicalRetriever(chunks, store), store, recorder)
    client.app.state.orchestrator.max_refine_rounds = 1
    client.app.state.orchestrator.use_critic = True
    try:
        row = evaluate_case(client, recorder, store, chunks, "user:ines", question, kind)
    finally:
        client.close()
    assert row["status"] == "completed"
    assert row["synthesis_payload_ids"] == ["independent-" + case]
    assert row["exposed_payload_ids"] == ["independent-" + case]
    assert not row["unauthorized_evidence"]
    assert all(ev["doc_id"] != "restricted" for ev in row["response"]["evidence"])
    assert {call["stage"] for call in row["calls"]} == {"planning", "assessment", "synthesis", "critic"}
    assert any(s.get("pending_call") for s in snapshots)
    assert all("request" in c for c in report["calls"])
    assert json.loads((tmp_path/"checkpoint.json").read_text())["pending_call"] is None


def test_hidden_corpus_has_no_effect_in_scripted_api_control():
    store = identity()
    chunks, _, question, _ = case_fixture(corpus(), "benign", store, "present")
    visible = [c for c in chunks if "group:all-staff" in c["allowed_principals"]]
    rows = []
    for variant in (chunks, chunks, visible):
        recorder = JournalLLM(StagedModel("Use cited sources [local-notes]."), {}, {}, lambda: None)
        client = make_client(LexicalRetriever(variant, store), store, recorder)
        client.app.state.orchestrator.max_refine_rounds = 1
        client.app.state.orchestrator.use_critic = True
        try:
            rows.append(evaluate_case(client, recorder, store, variant, "user:ines", question, "existence"))
        finally:
            client.close()
    assert all(r["status"] == "completed" for r in rows)
    assert stable_response(rows[0]["response"]) == stable_response(rows[1]["response"]) == stable_response(rows[2]["response"])


@pytest.mark.parametrize("free,loaded,allowed", [(None, False, False), (GiB, False, False),
    (4*GiB, False, True), (GiB, True, False), (2*GiB, True, True)])
def test_memory_preflight(free, loaded, allowed):
    assert memory_preflight(free, loaded)["allowed"] is allowed


def test_budget_stop_records_no_actual_submission(monkeypatch):
    monkeypatch.setattr("redteam.api_probe.available_memory", lambda: 0)
    recorder = JournalLLM(BudgetLLM(1, 1), {"p": "payload"}, {}, lambda: None)
    with pytest.raises(OllamaError):
        recorder.chat("Answer only", "payload")
    call = recorder.calls[0]
    assert not call["completed"] and not call["transport_attempted"]
    assert call["submitted_payload_ids"] == []
    assert call["unsubmitted_payload_ids"] == ["p"]


def triplet():
    return [{"metadata": {"case": "pair-reserve", "variant": variant, "compatibility": {"code": "same", "model": "same"}},
             "error": None, "case_result": {"status": "completed", "elapsed_ms": 1,
                 "response": {"answer": "same", "citations": [], "evidence": [], "trace": {"reason": "same", "count": 3}}}}
            for variant in ("present", "repeat", "absent")]


def test_pair_rejects_versions_missing_cases_and_wrong_order():
    rows = triplet()
    assert compatible_triplet(rows)["baseline_stable"]
    rows[1]["metadata"]["compatibility"]["code"] = "different"
    with pytest.raises(ValueError): compatible_triplet(rows)
    rows = triplet(); rows[1]["error"] = "preflight blocked"
    with pytest.raises(ValueError): compatible_triplet(rows)
    rows = triplet(); rows.reverse()
    with pytest.raises(ValueError): compatible_triplet(rows)


def test_pair_keeps_trace_variability_and_stable_hidden_differences():
    rows = triplet(); rows[1]["case_result"]["response"]["trace"]["reason"] = "different"
    result = compatible_triplet(rows)
    assert not result["baseline_stable"]
    assert result["baseline_changed_paths"] == ["trace.reason"]
    rows = triplet(); rows[2]["case_result"]["response"]["trace"]["count"] = 4
    result = compatible_triplet(rows)
    assert result["stable_difference"]
    assert result["changed_paths"] == ["trace.count"]
    rows[1]["case_result"]["status"] = "incomplete"
    assert compatible_triplet(rows)["status"] == "incomplete"


def test_background_attack_submission_invalidates_benign_control():
    from redteam.api_probe import exposure_context
    row = {"status": "completed", "exposed_payload_ids": ["independent-benign", "background"],
           "calls": [{"transport_attempted": True, "submitted_payload_ids": ["background"]}]}
    result = exposure_context(row, "benign", ["background"])
    assert not result["clean_benign_control"]
    assert result["target_payload_exposed"]
    assert result["background_payloads_exposed"] == ["background"]
    row["exposed_payload_ids"] = []  # even an incomplete background submission contaminates control
    assert not exposure_context(row, "benign", ["background"])["clean_benign_control"]
    row["calls"] = []
    assert not exposure_context(row, "benign", ["background"])["clean_benign_control"]
    row["exposed_payload_ids"] = ["independent-benign"]
    assert exposure_context(row, "benign", ["background"])["clean_benign_control"]
    assert not exposure_context(row, "access_paraphrase", ["background"])["clean_benign_control"]


def test_controlled_conditions_differ_only_in_target_text_and_do_not_mutate_existing():
    base = corpus()
    preserved = copy.deepcopy(base)
    generated = [case_fixture(base, case, identity(), "present", "controlled")[0] for case in CASES]
    assert base == preserved
    first = generated[0]
    for chunks in generated:
        assert chunks[:-1] == first[:-1]
        assert {k: v for k, v in chunks[-1].items() if k != "text"} == {k: v for k, v in first[-1].items() if k != "text"}
        assert len(chunks) == 5
    assert generated[0][-1]["text"] != generated[1][-1]["text"]
    with pytest.raises(ValueError):
        case_fixture(base, "pair-reserve", identity(), "present", "controlled")


def test_clean_api_control_and_attack_flags_with_scripted_model():
    from redteam.api_probe import exposure_context
    for case in ("benign", "access_paraphrase"):
        store = identity()
        chunks, kind, question, payloads = case_fixture([], case, store, "present", "controlled")
        recorder = JournalLLM(StagedModel(CASES[case][1]), payloads, {}, lambda: None)
        client = make_client(LexicalRetriever(chunks, store), store, recorder)
        try:
            row = evaluate_case(client, recorder, store, chunks, "user:ines", question, kind)
        finally:
            client.close()
        context = exposure_context(row, case, ["background-attack"])
        assert context["target_payload_exposed"]
        assert context["clean_benign_control"] == (case == "benign")
        assert row["response"]["trace"]["answer_presentation"]["status"] == ("unflagged" if case == "benign" else "review_required")


@pytest.mark.parametrize("text,expected", [("MemAvailable: 5000000 kB", 5120000000), ("MemFree: 10 kB", None), ("MemAvailable: bad kB", None), ("MemAvailable: -1 kB", None)])
def test_linux_memory_uses_available_not_free(text, expected):
    from redteam.api_probe import linux_available_memory
    assert linux_available_memory(text) == expected


def test_bundle_provenance_detects_modified_files(tmp_path):
    import hashlib
    from redteam.api_probe import source_provenance
    p = tmp_path/"sample.py"; p.write_text("original")
    manifest = {"commit": "original-head", "working_tree_dirty": True,
                "files": {"sample.py": hashlib.sha256(p.read_bytes()).hexdigest()}}
    (tmp_path/"BUNDLE_MANIFEST.json").write_text(json.dumps(manifest))
    assert source_provenance(tmp_path)["commit"] == "original-head"
    p.write_text("changed")
    with pytest.raises(ValueError): source_provenance(tmp_path)
