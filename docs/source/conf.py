# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0
#
# Updated: 2022-06-06
#
# Configuration file for the Sphinx documentation builder.

# -- Path setup --------------------------------------------------------------

# sys.path.insert(0, os.path.abspath(pathlib.Path(__file__).parent))


# -- Project information -----------------------------------------------------

project = "conhead"
author = "Rafe Kaplan"
copyright = f"2022, {author}"

release = "0.4"
version = "0.4.0"


# -- General configuration ---------------------------------------------------

extensions = []

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

html_theme = "alabaster"
html_static_path = ["_static"]
