from flask import Flask, request, render_template_string
import os
import sys
from werkzeug.utils import secure_filename

# Ensure both the scripts folder and project root are importable
current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, ".."))
for path in (current_dir, project_root):
    if path not in sys.path:
        sys.path.insert(0, path)

from main import run_pipeline

app = Flask(__name__)

FORM_HTML = """<!doctype html>
<html>
<head>
  <title>Ontology Pipeline</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    form textarea { width: 100%; }
    .section { border: 1px solid #ddd; padding: 10px 15px; margin-top: 20px; border-radius: 4px; }
    pre { background: #f8f8f8; padding: 10px; overflow-x: auto; }
  </style>
</head>
<body>
  <h1>Ontology Pipeline</h1>
  <form method="post" enctype="multipart/form-data">
    <label>Text:</label><br>
    <textarea name="text" rows="6"></textarea><br><br>
    <label>File:</label> <input type="file" name="file"><br><br>
    <label>Ontologies:</label> <input type="file" name="ontologies" multiple><br><br>
    <input type="submit" value="Run Pipeline">
  </form>

  {% if result %}
    <div class="section">
      <h2>Preprocessed Sentences</h2>
      <ul>
        {% for s in result.sentences %}
          <li>{{ s }}</li>
        {% endfor %}
      </ul>
    </div>

    <div class="section">
      <h2>LLM Generated OWL</h2>
      {% for snippet in result.owl_snippets %}
        <pre>{{ snippet }}</pre>
      {% endfor %}
    </div>

    <div class="section">
      <h2>Reasoner</h2>
      <p>{{ result.reasoner }}</p>
    </div>

    <div class="section">
      <h2>SHACL Validation</h2>
      <p>Conforms: {{ result.shacl_conforms }}</p>
      <pre>{{ result.shacl_report }}</pre>
    </div>

    <div class="section">
      <h2>Final Ontology</h2>
      <pre>{{ ontology }}</pre>
    </div>
  {% endif %}
</body>
</html>"""


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        inputs = []
        ontology_files = []
        os.makedirs("uploads", exist_ok=True)
        text = request.form.get("text", "").strip()
        if text:
            text_path = os.path.join("uploads", "input.txt")
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(text)
            inputs.append(text_path)
        uploaded = request.files.get("file")
        if uploaded and uploaded.filename:
            filename = secure_filename(uploaded.filename)
            file_path = os.path.join("uploads", filename)
            uploaded.save(file_path)
            inputs.append(file_path)
        for onto in request.files.getlist("ontologies"):
            if onto and onto.filename:
                ofile = secure_filename(onto.filename)
                o_path = os.path.join("uploads", ofile)
                onto.save(o_path)
                ontology_files.append(o_path)
        if not inputs:
            return "No input provided", 400
        result = run_pipeline(
            inputs,
            "shapes.ttl",
            "http://example.com/atm#",
            ontologies=ontology_files,
            repair=True,
            reason=True,
        )
        ontology_path = result.get("repaired_ttl", result.get("combined_ttl"))
        with open(ontology_path, "r", encoding="utf-8") as f:
            ontology_data = f.read()
        return render_template_string(FORM_HTML, result=result, ontology=ontology_data)
    return render_template_string(FORM_HTML, result=None, ontology=None)


if __name__ == "__main__":
    app.run(debug=True, port=8000)
