"""On-demand translation between signal source language and subscriber language.

Strategy (per approved plan): generate once in source language, translate on
demand at publish time, cache by signal_id + target_lang on disk to avoid
re-billing the LLM for the same pair.
"""
