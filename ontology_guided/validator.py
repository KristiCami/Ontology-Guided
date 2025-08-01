from rdflib import Graph
from pyshacl import validate
import os


class SHACLValidator:
    """Εκτελεί έλεγχο SHACL για τα παραγόμενα triples."""

    def __init__(self, data_graph_path: str, shapes_graph_path: str, inference: str = "rdfs"):
        self.data_graph_path = data_graph_path
        self.shapes_graph_path = shapes_graph_path
        self.inference = inference

    def run_validation(self):
        """Επιστρέφει αποτελέσματα επικύρωσης."""
        conforms, results_graph, results_text = validate(
            data_graph=self.data_graph_path,
            shacl_graph=self.shapes_graph_path,
            inference=self.inference,
            debug=False,
        )
        return conforms, results_text, results_graph


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run SHACL validation.")
    parser.add_argument("--data", required=True, help="Path to data graph (TTL/OWL)")
    parser.add_argument("--shapes", required=True, help="Path to SHACL shapes (TTL)")
    parser.add_argument(
        "--inference",
        default="rdfs",
        choices=["none", "rdfs", "owlrl"],
        help="Inference to apply",
    )
    args = parser.parse_args()

    if not os.path.exists(args.data) or not os.path.exists(args.shapes):
        print("Error: data graph or shapes file not found.")
        exit(1)

    validator = SHACLValidator(args.data, args.shapes, inference=args.inference)
    conforms, results_text, _ = validator.run_validation()
    print("Conforms:", conforms)
    print("--- Validation Report ---")
    print(results_text)
