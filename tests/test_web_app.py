import io
import os
from scripts import web_app


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
        called["shapes"] = shapes
        called["base_ns"] = base_ns
        return _fake_result(dummy)

    monkeypatch.setattr(web_app, "run_pipeline", fake_run_pipeline)
    monkeypatch.chdir(tmp_path)
    client = web_app.app.test_client()
    data = {"text": "hi"}
    resp = client.post("/", data=data)
    assert resp.status_code == 200
    assert called["repair"] is False
    assert called["reason"] is False
    assert called["shapes"] == "shapes.ttl"
    assert called["base_ns"] == "http://example.com/atm#"


def test_web_app_custom_shapes_and_base(monkeypatch, tmp_path):
    dummy = tmp_path / "out.ttl"
    dummy.write_text("")
    called = {}

    def fake_run_pipeline(inputs, shapes, base_ns, ontologies=None, repair=False, reason=False):
        called["shapes"] = shapes
        called["base_ns"] = base_ns
        called["exists"] = os.path.exists(shapes)
        return _fake_result(dummy)

    monkeypatch.setattr(web_app, "run_pipeline", fake_run_pipeline)
    monkeypatch.chdir(tmp_path)
    client = web_app.app.test_client()
    data = {
        "text": "hi",
        "base_iri": "http://test.com/base#",
        "shapes": (io.BytesIO(b"shape"), "shape.ttl"),
    }
    resp = client.post("/", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert called["base_ns"] == "http://test.com/base#"
    assert called["shapes"] == os.path.join("uploads", "shape.ttl")
    assert called["exists"] is True
