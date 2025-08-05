import pytest
from scripts.web_app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_index_no_input(client):
    resp = client.post('/', data={})
    assert resp.status_code == 200
    assert b'No input provided' in resp.data


def test_success_flow(client, monkeypatch, tmp_path):
    def fake_run_pipeline(inputs, shapes, base_iri, ontologies=None, model='gpt-4', repair=False, reason=False):
        ttl_path = tmp_path / 'out.ttl'
        ttl_path.write_text('@prefix : <http://example.com/> .')
        return {
            'sentences': ['s1'],
            'owl_snippets': ['a b c'],
            'reasoner': 'ok',
            'shacl_conforms': True,
            'shacl_report': 'report',
            'combined_ttl': str(ttl_path),
        }
    monkeypatch.setattr('scripts.web_app.run_pipeline', fake_run_pipeline)

    data = {
        'text': 'Requirement',
        'model': 'gpt-4',
        'reason': 'on',
        'repair': 'on',
    }
    resp = client.post('/', data=data)
    assert resp.status_code == 200
    assert b'Preprocessed Sentences' in resp.data

