"""Reconstructed subscription token generator."""
import secrets

def new_token():
    return secrets.token_urlsafe(32)
