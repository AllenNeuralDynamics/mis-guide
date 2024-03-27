"""
Module for managing package configuration and file paths.

This module defines package-level configuration variables and functions
for accessing files within the package directory.

Attributes:
    __version__ (str): The version of the package.
    package_dir (str): The directory of the package.
    image_dir (str): The directory for image files.
    ui_dir (str): The directory for UI files.

Functions:
    get_image_file(basename): Get the full path to an image file given its basename.
"""
import os
__version__ = "0.37.1"

# allow multiple OpenMP instances
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

# set package directories
package_dir = os.path.dirname(__file__)
image_dir = os.path.join(os.path.dirname(package_dir), 'img')
ui_dir = os.path.join(os.path.dirname(package_dir), 'ui')

def get_image_file(basename):
    """Get the full path to an image file given its basename."""
    return os.path.join(image_dir, basename)
