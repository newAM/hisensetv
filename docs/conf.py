#!/usr/bin/env python3.8

import os
import sys
import datetime

this_directory = os.path.dirname(os.path.abspath(__file__))
module_directory = os.path.abspath(os.path.join(this_directory, ".."))
if module_directory not in sys.path:
    sys.path.append(module_directory)

# Sphinx extensions
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",  # google style docstrings
    "sphinx_autodoc_typehints",  # must be after napoleon
]


templates_path = []
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "hisensetv"
year = datetime.datetime.now().year
author = "Alex M."
copyright = f"{year}, {author}"
version = "0.0.7"
release = "0.0.7"
language = None
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", ".tox"]
pygments_style = "sphinx"
todo_include_todos = True
nitpicky = True

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

# HTML Options

html_theme = "sphinx_rtd_theme"
htmlhelp_basename = "hisensetv"
html_theme_options = {"display_version": False}
html_context = {
    "display_github": True,
    "github_user": "newAM",
    "github_repo": project,
}
