import copy
import json
import pytest
from redteam.resume_redteam import case_plan, validate_prefix, validate_environment, run_batch


def row(task):
    return {**task, "status":"completed", "response":{"answer":"permitted"},
            "exposed_payload_ids":["fixture"], "completed_synthesis":True, "elapsed_ms":1}


def test_plan_retains_original_order_and_distinguishes_pair_variants():
    plan = case_plan(1)
    assert len(plan) == 30
    assert [t["variant"] for t in plan[21:24]] == ["present","repeat","absent"]
    assert len(case_plan(2)) == 51
    legacy = [row(t) for t in plan[:22]]
    legacy[-1].pop("variant")
    validate_prefix(legacy, plan)
    legacy[0]["question"] = "changed question"
    with pytest.raises(ValueError): validate_prefix(legacy, plan)


def test_batch_skips_saved_cases_and_finishes_partial_pair(tmp_path):
    plan = case_plan(1)
    original = [row(t) for t in plan[:22]]
    report = {"metadata":{"timestamp_utc":"fixture","execution":"scripted"},"cases":copy.deepcopy(original),"pairs":[]}
    invoked = []
    def execute(task):
        invoked.append(task)
        return row(task)
    assert run_batch(report, plan, execute, 2, tmp_path) == 2
    assert [x["variant"] for x in invoked] == ["repeat","absent"]
    assert report["cases"][:22] == original
    assert len(report["pairs"]) == 1
    assert report["pairs"][0]["baseline_stable"]
    saved = json.loads((tmp_path / "redteam_results.json").read_text())
    assert saved["summary"]["incomplete"]
    assert len(saved["cases"]) == 24


def test_resume_preserves_timed_out_cases(tmp_path):
    plan = case_plan(1)
    cases = [row(t) for t in plan[:29]]
    cases[0]["status"] = "incomplete"
    report={"metadata":{"timestamp_utc":"fixture","execution":"scripted"},"cases":cases,"pairs":[]}
    assert run_batch(report, plan, row, 1, tmp_path) == 2
    assert report["summary"]["incomplete_cases"] == 1
    assert len(report["pairs"]) == 3


def test_interrupted_batch_keeps_old_checkpoint_and_new_saved_case(tmp_path):
    plan=case_plan(1)
    report={"metadata":{"timestamp_utc":"fixture","execution":"scripted"},"cases":[],"pairs":[]}
    def execute(task):
        if report["cases"]: raise KeyboardInterrupt
        return row(task)
    assert run_batch(report,plan,execute,2,tmp_path) == 2
    assert len(report["cases"]) == 1
    assert "interrupted" in report["summary"]["error"]


def metadata():
    return {"model":"gemma3:4b", "python":"fixture", "packages":{"faiss":"version"},
            "identity_sha256":"identity", "index_sha256":{"vectors":"index"},
            "ollama_version":{"version":"fixture"}, "ollama_models":[{"name":"gemma3:4b","digest":"modelhash"}],
            "source_files":{"app/api.py":"source", "indexing/build_indexes.py":"indexsource"}}


@pytest.mark.parametrize("field,value", [("model","other-model"),("python","different"),("packages",{}),("identity_sha256","changed"),("index_sha256",{}),("ollama_version",{}),("ollama_models",[]),("source_files",{"app/api.py":"changed"})])
def test_environment_mismatch_cannot_mix_measurements(field,value):
    old=metadata(); new=metadata(); new[field]=value
    with pytest.raises(ValueError): validate_environment(old,new)


def test_runner_change_allowed_but_app_sources_must_match():
    old=metadata(); new=metadata()
    old["source_files"]={k.replace("/", "\\"):v for k,v in old["source_files"].items()}
    old["source_files"]["redteam/run_redteam.py"]="old-runner"
    validate_environment(old,new)
