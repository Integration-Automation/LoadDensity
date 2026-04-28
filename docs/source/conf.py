# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath('.'))
# Reach the repo root so ``import je_load_density`` works inside autodoc.
sys.path.insert(0, os.path.abspath(os.path.join(os.pardir, os.pardir)))

# -- Project information -----------------------------------------------------

project = 'LoadDensity'
project_copyright = '2022 ~ 2025, JE-Chen'
author = 'JE-Chen'
release = '0.0.65'

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.napoleon",
    "sphinxcontrib.mermaid",
]

# Autosummary writes per-module reference pages on every build.
autosummary_generate = True
# autosectionlabel collides on common section titles repeated across
# language manuals; prefix every label with the document path so
# duplicates become unique.
autosectionlabel_prefix_document = True
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}
# Autodoc imports the modules it documents; some carry soft deps
# that aren't installed in the docs build environment, so silence them.
autodoc_mock_imports = [
    "locust",
    "gevent",
    "PySide6",
    "qt_material",
    "defusedxml",
    "websocket",
    "grpc",
    "paho",
    "prometheus_client",
    "opentelemetry",
    "faker",
    "mcp",
]

mermaid_version = "10.9.0"

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'titles_only': False,
}
