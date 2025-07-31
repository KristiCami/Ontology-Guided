from rdflib import Graph

class OntologyBuilder:
    """
    Φορτώνει Turtle snippets σε RDF Graph με δυνατότητα debug,
    προσθέτοντας δηλώσεις prefix ώστε να υποστηρίζονται τα 'atm:' namespaces.
    """
    def __init__(self, base_iri: str):
        # Ensure base ends with '#'
        if not base_iri.endswith('#'):
            base_iri += '#'
        self.base_iri = base_iri

        # Header declares 'atm:' prefix for base IRI and standard prefixes
        self.header = (
            f"@prefix atm: <{self.base_iri}> .\n"
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
        )
        self.graph = Graph()

    def parse_turtle(self, turtle_str: str):
        """
        Process Turtle string:
         - Remove existing @prefix lines and empty lines
         - Prepend header with 'atm:' and standard prefixes
         - Debug-print the final Turtle
         - Parse into the graph
        """
        # Filter out @prefix and blank lines
        lines = [line for line in turtle_str.splitlines() 
                 if line.strip() and not line.strip().startswith('@prefix')]
        cleaned = "\n".join(lines)

        # Combine header and cleaned Turtle
        data = self.header + "\n" + cleaned

        # Debug: show what's being parsed
        print("=== Turtle input to rdflib.parse ===")
        print(data)
        print("=== End of Turtle ===")

        # Parse the combined Turtle
        self.graph.parse(data=data, format='turtle')

    def save(self, file_path: str, fmt: str = 'turtle'):
        """
        Serialize the RDF graph to a file.
        fmt: 'turtle' or 'xml' (OWL/XML)
        """
        self.graph.serialize(destination=file_path, format=fmt)

# Standalone test
if __name__ == '__main__':
    import os
    BASE_IRI = 'http://example.com/atm#'
    os.makedirs('results', exist_ok=True)
    with open('results/llm_output.ttl', 'r', encoding='utf-8') as f:
        ttl = f.read()
    ob = OntologyBuilder(BASE_IRI)
    ob.parse_turtle(ttl)
    ob.save('results/combined.ttl', fmt='turtle')
    ob.save('results/combined.owl', fmt='xml')
    print('Saved results/combined.ttl and results/combined.owl')
