"""
Core Application Infrastructure Module.

This package encapsulates low-level cross-cutting concerns that sit between
the network layer and the business domain:
1. `middleware.py`:
   - Configures Cross-Origin Resource Sharing (CORS) policies to allow safe browser access.
   - Provides transparent route rewrites for frontend clients communicating via `/api/*`.
2. `exceptions.py`:
   - Centralizes global exception handling so unhandled Python exceptions,
     Pydantic validation errors, and HTTP status codes return uniform, CORS-safe JSON envelopes.
"""

__all__ = ["middleware", "exceptions"]
