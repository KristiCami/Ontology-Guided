from pathlib import Path
import sys

# Ensure project root is on sys.path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ontology_guided.validator import SHACLValidator

def main() -> None:
    base = Path(__file__).resolve().parent
    shapes_path = base / "mini_shapes.ttl"

    violation_counts = []
    conform_iter = None

    for idx in range(3):
        data_path = base / f"shacl_example_iter{idx}.ttl"
        validator = SHACLValidator(str(data_path), str(shapes_path))
        conforms, _, summary = validator.run_validation()
        total = summary.get("total", 0)
        violation_counts.append(total)

        # collect per-path counts across all shapes
        path_counts = {}
        for shape_counts in summary.get("byShapePath", {}).values():
            for path, count in shape_counts.items():
                path_counts[path] = path_counts.get(path, 0) + count

        print(f"Iteration {idx}:")
        for path, count in sorted(path_counts.items()):
            print(f"  {path}: {count}")
        print(f"  Total: {total} (conforms={conforms})")
        if conforms and conform_iter is None:
            conform_iter = idx

    print("\nViolation counts (pre -> post repair):")
    for i in range(len(violation_counts) - 1):
        pre = violation_counts[i]
        post = violation_counts[i + 1]
        print(f"Iteration {i}: {pre} -> {post}")
    if conform_iter is not None:
        print(f"Conformance achieved at iteration {conform_iter}")
    else:
        print("Conformance not achieved")


if __name__ == "__main__":
    main()
