import os
import sys

# Ensure project root is on sys.path so tests can import 'src' package
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "src")
PIPELINES_DIR = os.path.join(ROOT, "pipelines")

# Ensure 'src' and 'pipelines' are on sys.path
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if PIPELINES_DIR not in sys.path:
    sys.path.insert(0, PIPELINES_DIR)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def pytest_configure(config):
    # Keep pytest default rootdir behavior; we only ensure sys.path contains project root above.
    # This avoids assigning to the read-only `config.rootdir` property which raises in newer pytest.
    return
