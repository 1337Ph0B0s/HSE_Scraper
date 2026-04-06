# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Práctica 1 (M2.851 Tipología y ciclo de vida de los datos) — Web Scraping + Dataset (HSE Notices)'
copyright = '2026, Pablo Pazmiño Naranjo [1337Ph0B0s] & Sergio Alcudia Díaz [Alcu-D-IA]'
author = 'Pablo Pazmiño Naranjo [1337Ph0B0s] & Sergio Alcudia Díaz [Alcu-D-IA]'
release = '1.0.2026-04-06'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

extensions.append("sphinx_autodoc_typehints")

templates_path = ['_templates']
exclude_patterns = []

language = 'es'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']
