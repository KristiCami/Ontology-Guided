from pathlib import Path
import sys
import os
from tempfile import NamedTemporaryFile
import subprocess

# Ensure project root is on sys.path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rdflib import Graph, Namespace, RDFS


def run_unsats(path: str) -> int:
    code = (
        "from ontology_guided.reasoner import run_reasoner;import sys;"
        "u=run_reasoner(sys.argv[1])[2];"
        "print(len([x for x in u if x != 'http://www.w3.org/2002/07/owl#Nothing']))"
    )
    result = subprocess.run([sys.executable, "-c", code, path], capture_output=True, text=True, check=True)
    return int(result.stdout.strip())


def main() -> None:
    base = Path(__file__).resolve().parent
    ttl_path = base / "reasoning_example.ttl"

    unsats = run_unsats(str(ttl_path))
    print(f"unsats={unsats}")

    graph = Graph()
    graph.parse(ttl_path, format="turtle")
    ex = Namespace("http://example.com/")
    graph.remove((ex.VIPCustomer, RDFS.subClassOf, ex.NonCustomer))

    with NamedTemporaryFile("w", suffix=".ttl", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        graph.serialize(destination=tmp_path, format="turtle")
        unsats = run_unsats(tmp_path)
        print(f"unsats={unsats}")
    finally:
        os.remove(tmp_path)


if __name__ == "__main__":
    main()
