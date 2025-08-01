from flask import Flask, request, render_template_string
import os
from werkzeug.utils import secure_filename
from main import run_pipeline

app = Flask(__name__)

FORM_HTML = """
<!doctype html>
<title>Ontology Pipeline</title>
<h1>Upload requirement file or paste text</h1>
<form method=post enctype=multipart/form-data>
  <label>Text:</label><br>
  <textarea name=text rows=10 cols=80></textarea><br><br>
  <label>File:</label> <input type=file name=file><br><br>
  <input type=submit value='Run Pipeline'>
</form>
{% if result %}
<h2>Ontology Output</h2>
<pre>{{ result }}</pre>
{% endif %}
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        inputs = []
        os.makedirs('uploads', exist_ok=True)
        text = request.form.get('text', '').strip()
        if text:
            text_path = os.path.join('uploads', 'input.txt')
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text)
            inputs.append(text_path)
        uploaded = request.files.get('file')
        if uploaded and uploaded.filename:
            filename = secure_filename(uploaded.filename)
            file_path = os.path.join('uploads', filename)
            uploaded.save(file_path)
            inputs.append(file_path)
        if not inputs:
            return 'No input provided', 400
        run_pipeline(inputs, 'shapes.ttl', 'http://example.com/atm#', repair=True)
        result_path = 'results/repaired.ttl' if os.path.exists('results/repaired.ttl') else 'results/combined.ttl'
        with open(result_path, 'r', encoding='utf-8') as f:
            data = f.read()
        return render_template_string(FORM_HTML, result=data)
    return render_template_string(FORM_HTML, result=None)

if __name__ == '__main__':
    app.run(debug=True)