from flask import Flask, request, render_template, flash
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

app = Flask(
    __name__,
    template_folder=os.path.join(project_root, "templates"),
    static_folder=os.path.join(project_root, "static"),
)
app.secret_key = "dev"


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
            flash("No input provided")
            return render_template("index.html")

        model = request.form.get("model", "gpt-4")
        reason = bool(request.form.get("reason"))
        repair = bool(request.form.get("repair"))

        try:
            result = run_pipeline(
                inputs,
                "shapes.ttl",
                "http://example.com/atm#",
                ontologies=ontology_files,
                model=model,
                repair=repair,
                reason=reason,
            )
        except Exception as exc:
            flash(str(exc))
            return render_template("index.html")

        ontology_path = result.get("repaired_ttl", result.get("combined_ttl"))
        with open(ontology_path, "r", encoding="utf-8") as f:
            ontology_data = f.read()
        return render_template(
            "result.html",
            result=result,
            ontology=ontology_data,
            model=model,
            reason=reason,
            repair=repair,
        )
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=8000)
