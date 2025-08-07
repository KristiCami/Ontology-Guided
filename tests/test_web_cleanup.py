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


def test_temporary_files_removed(monkeypatch, tmp_path):
    dummy = tmp_path / "out.ttl"
    dummy.write_text("dummy")

    def fake_run_pipeline(inputs, shapes, base_ns, ontologies=None, repair=False, reason=False):
        return _fake_result(dummy)

    monkeypatch.setattr(web_app, "run_pipeline", fake_run_pipeline)
    monkeypatch.chdir(tmp_path)
    client = web_app.app.test_client()
    data = {"text": "hi", "shacl": (BytesIO(b"data"), "shape.ttl")}
    resp = client.post("/", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert not dummy.exists()
    assert not (tmp_path / "uploads" / "input.txt").exists()
    assert not (tmp_path / "uploads" / "shape.ttl").exists()

