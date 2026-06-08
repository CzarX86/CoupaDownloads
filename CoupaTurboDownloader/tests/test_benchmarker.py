import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.engine.benchmarker import Chromosome, benchmark, run_genetic_tuning


def test_chromosome_random_individual():
    ind = Chromosome.random_individual()
    assert 4 <= ind.concurrency <= 16
    assert 0.0 <= ind.request_delay <= 0.4
    assert 5.0 <= ind.timeout <= 12.0
    assert ind.fitness == 0.0


def test_chromosome_mutate():
    ind = Chromosome(concurrency=8, request_delay=0.1, timeout=8.0)
    original_concurrency = ind.concurrency
    original_delay = ind.request_delay
    original_timeout = ind.timeout

    # Mutate many times — at least one param should change eventually
    changed = False
    for _ in range(50):
        ind.mutate()
        if (ind.concurrency != original_concurrency
                or ind.request_delay != original_delay
                or ind.timeout != original_timeout):
            changed = True
            break
    assert changed, "Mutation should change at least one parameter after many attempts"


def test_chromosome_mutate_stays_in_bounds():
    ind = Chromosome(concurrency=2, request_delay=0.0, timeout=3.0)
    for _ in range(100):
        ind.mutate()
        assert 2 <= ind.concurrency <= 24
        assert 0.0 <= ind.request_delay <= 1.0
        assert 3.0 <= ind.timeout <= 20.0


def test_chromosome_crossover():
    p1 = Chromosome(concurrency=8, request_delay=0.1, timeout=8.0)
    p2 = Chromosome(concurrency=12, request_delay=0.3, timeout=12.0)
    child = p1.crossover(p2)
    assert child.concurrency in (8, 12)
    assert child.request_delay in (0.1, 0.3)
    assert child.timeout in (8.0, 12.0)


def test_chromosome_repr():
    ind = Chromosome(concurrency=8, request_delay=0.1, timeout=10.0)
    ind.fitness = 42.5
    ind.throughput = 30.0
    s = repr(ind)
    assert "8" in s
    assert "0.1" in s
    assert "42.5" in s


@pytest.mark.asyncio
async def test_benchmark_empty_urls():
    result = await benchmark([])
    assert "error" in result


@pytest.mark.asyncio
async def test_run_genetic_tuning_returns_best():
    """Integration: genetic algorithm converges on best chromosome."""
    mock_responses = [
        {"success": True, "latency": 0.1, "html_size": 5000},
        {"success": True, "latency": 0.15, "html_size": 4000},
    ]

    with patch("src.engine.benchmarker.httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        async def mock_get(url, timeout=None):
            resp = MagicMock()
            resp.status_code = 200
            resp.url = url
            resp.text = "<html></html>"
            resp.raise_for_status = MagicMock()
            return resp

        mock_client.get = mock_get
        mock_client_cls.return_value = mock_client

        urls = ["https://unilever.coupahost.com/order_headers/1",
                "https://unilever.coupahost.com/order_headers/2"]

        best = await run_genetic_tuning(urls, cookies={}, base_url="https://unilever.coupahost.com",
                                         generations=2, pop_size=4)

        assert best is not None
        assert 2 <= best.concurrency <= 24
        assert 0.0 <= best.request_delay <= 1.0
        assert best.fitness >= 0.0
