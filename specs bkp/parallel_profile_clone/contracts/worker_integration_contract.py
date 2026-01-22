"""Re-export contract symbols from 003-parallel-profile-clone.

This file forwards imports for the Worker Integration contract so tests
and implementation can use a stable path independent of the numeric
prefix directory that contains hyphens in its name.
"""

from importlib import import_module as _import_module

_real = _import_module('specs.003-parallel-profile-clone.contracts.worker_integration_contract')

# Re-export everything needed by tests/implementation
WorkerConfig = _real.WorkerConfig
WorkerStartupResult = _real.WorkerStartupResult
ProfileAwareWorkerPoolContract = _real.ProfileAwareWorkerPoolContract
WorkerProfileEventHandler = _real.WorkerProfileEventHandler

WorkerPoolException = _real.WorkerPoolException
WorkerStartupException = _real.WorkerStartupException
WorkerNotFoundException = _real.WorkerNotFoundException
MaxWorkersExceededException = _real.MaxWorkersExceededException
WorkerPoolShutdownException = _real.WorkerPoolShutdownException

__all__ = [
    'WorkerConfig', 'WorkerStartupResult', 'ProfileAwareWorkerPoolContract',
    'WorkerProfileEventHandler', 'WorkerPoolException', 'WorkerStartupException',
    'WorkerNotFoundException', 'MaxWorkersExceededException', 'WorkerPoolShutdownException'
]
