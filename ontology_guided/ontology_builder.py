from rdflib import Graph


class OntologyBuilder:
    """Μετατρέπει τμήματα Turtle σε ενιαία οντολογία."""

    def __init__(self, base_iri: str):
        if not base_iri.endswith("#"):
            base_iri += "#"
        self.base_iri = base_iri
        self.header = (
            f"@prefix atm: <{self.base_iri}> .\n"
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
        )
        self.graph = Graph()

    def parse_turtle(self, turtle_str: str):
        lines = [line for line in turtle_str.splitlines() if line.strip()]
        cleaned = "\n".join(lines)
        data = self.header + "\n" + cleaned
        print("=== Turtle input to rdflib.parse ===")
        print(data)
        print("=== End of Turtle ===")
        self.graph.parse(data=data, format="turtle")

    def save(self, file_path: str, fmt: str = "turtle"):
        """Αποθηκεύει την οντολογία σε αρχείο."""
        self.graph.serialize(destination=file_path, format=fmt)


if __name__ == "__main__":
    import os

    BASE_IRI = "http://example.com/atm#"
    os.makedirs("results", exist_ok=True)
    with open("results/llm_output.ttl", "r", encoding="utf-8") as f:
        ttl = f.read()
    ob = OntologyBuilder(BASE_IRI)
    ob.parse_turtle(ttl)
    ob.save("results/combined.ttl", fmt="turtle")
    ob.save("results/combined.owl", fmt="xml")
    print("Saved results/combined.ttl and results/combined.owl")
