#!/usr/bin/env python
"""
Setup script for Chronos MCP.
This is primarily for backward compatibility.
Please use pip install -e . instead.
"""

from setuptools import setup, find_packages

setup(
    packages=find_packages(),
    package_data={
        "chronos_mcp": ["py.typed"],
    },
)
