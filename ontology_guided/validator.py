from rdflib.namespace import RDF, SH
from rdflib import URIRef
from pyshacl import validate
import os


class SHACLValidator:
    """Εκτελεί έλεγχο SHACL για τα παραγόμενα triples."""

    def __init__(self, data_graph_path: str, shapes_graph_path: str, inference: str = "rdfs"):
        self.data_graph_path = data_graph_path
        self.shapes_graph_path = shapes_graph_path
        self.inference = inference

    def run_validation(self):
        """Επιστρέφει αποτελέσματα επικύρωσης ως δομημένη λίστα."""
        conforms, results_graph, _ = validate(
            data_graph=self.data_graph_path,
            shacl_graph=self.shapes_graph_path,
            inference=self.inference,
            debug=False,
        )

        results = []
        if not conforms:
            for result in results_graph.subjects(RDF.type, SH.ValidationResult):
                focus = results_graph.value(result, SH.focusNode)
                path = results_graph.value(result, SH.resultPath)
                message = results_graph.value(result, SH.resultMessage)
                source_shape = results_graph.value(result, SH.sourceShape)
                severity = results_graph.value(result, SH.resultSeverity)
                component = results_graph.value(
                    result, SH.sourceConstraintComponent
                )
                expected = results_graph.value(result, URIRef(str(SH) + "expected"))
                value = results_graph.value(result, SH.value)
                results.append(
                    {
                        "focusNode": str(focus) if focus else None,
                        "resultPath": str(path) if path else None,
                        "message": str(message) if message else None,
                        "sourceShape": str(source_shape) if source_shape else None,
                        "resultSeverity": str(severity) if severity else None,
                        "sourceConstraintComponent": str(component)
                        if component
                        else None,
                        "expected": str(expected) if expected else None,
                        "value": str(value) if value else None,
                    }
                )

        return conforms, results


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
    conforms, results = validator.run_validation()
    print("Conforms:", conforms)
    print("--- Validation Report ---")
    for r in results:
        print(
            f"- focusNode: {r['focusNode']}, resultPath: {r['resultPath']}, message: {r['message']}"
        )
