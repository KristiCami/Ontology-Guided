import os
import sys

# Allow importing main from the same folder when executed directly
sys.path.append(os.path.dirname(__file__))
from main import run_pipeline

if __name__ == "__main__":
    run_pipeline(["demo.txt"], "shapes.ttl", "http://example.com/atm#")
