# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0
#
# Updated: 2022-06-07
#
# Configuration file for the Sphinx documentation builder.

import pkg_resources

# -- Path setup --------------------------------------------------------------

# sys.path.insert(0, os.path.abspath(pathlib.Path(__file__).parent))


# -- Project information -----------------------------------------------------

conhead = pkg_resources.get_distribution("conhead")

project = conhead.project_name
author = "Rafe Kaplan"
copyright = f"2022, {author}"

version = conhead.version
release = ".".join(version.split(".")[2:])

# -- General configuration ---------------------------------------------------

extensions = []

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

html_theme = "classic"
# html_static_path = ["_static"]
