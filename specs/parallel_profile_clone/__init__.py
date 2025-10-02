"""Compatibility package to expose contracts under a stable import path.

This shim allows importing:
    specs.parallel_profile_clone.contracts.profile_manager_contract

by dynamically loading the real contract from:
    specs/003-parallel-profile-clone/contracts/profile_manager_contract.py

It eases TDD by giving tests a stable module path independent of folder naming.
"""
