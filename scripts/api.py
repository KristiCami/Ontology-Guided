import os
import sys
import asyncio
import tempfile
from typing import List

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

# Ensure scripts and project root are importable
current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, ".."))
for path in (current_dir, project_root):
    if path not in sys.path:
        sys.path.insert(0, path)

from main import run_pipeline

app = FastAPI(title="Ontology Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/run-pipeline")
async def run_pipeline_endpoint(
    text: str = Form(""),
    file: UploadFile | None = File(None),
    ontologies: List[UploadFile] = File([]),
):
    inputs: List[str] = []
    ontology_files: List[str] = []
    os.makedirs("uploads", exist_ok=True)

    if text.strip():
        fd, text_path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        inputs.append(text_path)

    if file is not None:
        file_path = os.path.join("uploads", file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        inputs.append(file_path)

    for onto in ontologies:
        onto_path = os.path.join("uploads", onto.filename)
        with open(onto_path, "wb") as f:
            f.write(await onto.read())
        ontology_files.append(onto_path)

    if not inputs:
        return {"error": "No input provided"}

    result = await asyncio.to_thread(
        run_pipeline,
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
    result["ontology"] = ontology_data
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("scripts.api:app", host="0.0.0.0", port=8000, reload=True)
