import os
import sys

# Ensure the Personalization root is importable so tests can `import services` / `import routers`
# the same way the application does (absolute imports), without installing the package.
sys.path.insert(0, os.path.dirname(__file__))
