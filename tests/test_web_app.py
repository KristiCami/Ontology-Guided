from scripts import web_app
from io import BytesIO


def _fake_result(path):
    return {
        "combined_ttl": str(path),
        "sentences": [],
        "owl_snippets": [],
        "reasoner": "",
        "shacl_conforms": True,
        "shacl_report": "",
    }


def test_web_app_flags(monkeypatch, tmp_path):
    dummy = tmp_path / "out.ttl"
    dummy.write_text("")
    called = {}

    def fake_run_pipeline(inputs, shapes, base_ns, ontologies=None, repair=False, reason=False):
        called["repair"] = repair
        called["reason"] = reason
        return _fake_result(dummy)

    monkeypatch.setattr(web_app, "run_pipeline", fake_run_pipeline)
    monkeypatch.chdir(tmp_path)
    client = web_app.app.test_client()
    data = {"text": "hi", "repair": "on", "reason": "on"}
    resp = client.post("/", data=data)
    assert resp.status_code == 200
    assert called["repair"] is True
    assert called["reason"] is True


def test_web_app_flags_default(monkeypatch, tmp_path):
    dummy = tmp_path / "out.ttl"
    dummy.write_text("")
    called = {}

    def fake_run_pipeline(inputs, shapes, base_ns, ontologies=None, repair=False, reason=False):
        called["repair"] = repair
        called["reason"] = reason
        return _fake_result(dummy)

    monkeypatch.setattr(web_app, "run_pipeline", fake_run_pipeline)
    monkeypatch.chdir(tmp_path)
    client = web_app.app.test_client()
    data = {"text": "hi"}
    resp = client.post("/", data=data)
    assert resp.status_code == 200
    assert called["repair"] is False
    assert called["reason"] is False


def test_web_app_custom_shacl_and_base(monkeypatch, tmp_path):
    dummy = tmp_path / "out.ttl"
    dummy.write_text("")
    called = {}

    def fake_run_pipeline(inputs, shapes, base_ns, ontologies=None, repair=False, reason=False):
        called["shapes"] = shapes
        called["base_ns"] = base_ns
        return _fake_result(dummy)

    monkeypatch.setattr(web_app, "run_pipeline", fake_run_pipeline)
    monkeypatch.chdir(tmp_path)
    client = web_app.app.test_client()
    data = {"text": "hi", "base_iri": "http://example.com/custom#", "shacl": (BytesIO(b"data"), "custom.ttl")}
    resp = client.post("/", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert called["base_ns"] == "http://example.com/custom#"
    assert called["shapes"].endswith("custom.ttl")
