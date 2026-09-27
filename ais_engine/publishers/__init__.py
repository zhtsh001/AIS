"""Channel-specific publishers.

Each Publisher knows how to deliver a list of ``AlphaSignal`` objects to a
list of ``Subscriber`` rows for its own channel. Tier filtering and language
translation happen in the orchestrator BEFORE the publisher is invoked, so
publishers stay focused on transport + rendering.

See ``publishers/base.py`` for the contract.
"""
