"""Adapters are controlled plugins and must not bypass JINX-Core."""

from jinx.adapters.framework import AdapterGate, AdapterManifest

__all__ = ["AdapterGate", "AdapterManifest"]
