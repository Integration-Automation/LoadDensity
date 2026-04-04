# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# -- Path setup --------------------------------------------------------------
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------------
project = 'LoadDensity'
copyright = '2022, JE-Chen'
author = 'JE-Chen'

# The full version, including alpha/beta/rc tags
release = '0.0.65'

# -- General configuration ---------------------------------------------------
extensions = []

templates_path = ['_templates']

exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'

html_static_path = ['_static']

# -- Options for HTML theme --------------------------------------------------
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'titles_only': False,
}
