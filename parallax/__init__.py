"""
Init
"""

import os

__version__ = "0.38.2"

# allow multiple OpenMP instances
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
