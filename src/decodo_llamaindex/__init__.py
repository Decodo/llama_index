"""
decodo-llamaindex
=================

LlamaIndex integration for the Decodo Web Scraping API.

Provides:
- DecodoWebReader    — load web pages as LlamaIndex Documents
- DecodoSearchReader — load search-engine results as LlamaIndex Documents
- DecodoToolSpec     — LlamaIndex tool spec for use with agents

Quickstart::

    import os
    from decodo_llamaindex import DecodoWebReader

    reader = DecodoWebReader(api_token=os.environ["DECODO_API_TOKEN"])
    docs = reader.load_data(["https://example.com"])
"""

from decodo_llamaindex.readers import DecodoSearchReader, DecodoWebReader
from decodo_llamaindex.tools import DecodoToolSpec

__all__ = [
    "DecodoWebReader",
    "DecodoSearchReader",
    "DecodoToolSpec",
]

__version__ = "0.1.0"
