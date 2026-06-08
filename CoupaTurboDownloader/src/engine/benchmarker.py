import asyncio
import random
import time
from typing import List, Dict, Any, Optional

import httpx

from src.engine.crawler import CoupaCrawler, RateLimitError, AuthError


class Chromosome:
    """Hyperparameter set for crawler tuning."""

    def __init__(self, concurrency: int, request_delay: float, timeout: float):
        self.concurrency = concurrency
        self.request_delay = request_delay
        self.timeout = timeout
        self.fitness = 0.0
        self.throughput = 0.0
        self.success_rate = 0.0
        self.avg_latency = 0.0
        self.errors: List[str] = []

    @classmethod
    def random_individual(cls) -> "Chromosome":
        return cls(
            concurrency=random.randint(4, 16),
            request_delay=round(random.uniform(0.0, 0.4), 2),
            timeout=round(random.uniform(5.0, 12.0), 1),
        )

    def mutate(self) -> None:
        if random.random() < 0.3:
            self.concurrency = max(2, min(24, self.concurrency + random.choice([-2, -1, 1, 2])))
        if random.random() < 0.3:
            self.request_delay = max(0.0, min(1.0, round(self.request_delay + random.choice([-0.05, -0.02, 0.02, 0.05]), 2)))
        if random.random() < 0.3:
            self.timeout = max(3.0, min(20.0, round(self.timeout + random.choice([-2.0, -1.0, 1.0, 2.0]), 1)))

    def crossover(self, other: "Chromosome") -> "Chromosome":
        return Chromosome(
            concurrency=random.choice([self.concurrency, other.concurrency]),
            request_delay=random.choice([self.request_delay, other.request_delay]),
            timeout=random.choice([self.timeout, other.timeout]),
        )

    def __repr__(self) -> str:
        return (
            f"Chromosome(concurrency={self.concurrency}, delay={self.request_delay}s, "
            f"timeout={self.timeout}s | Fitness={self.fitness:.2f}, Throughput={self.throughput:.1f} PO/m)"
        )


async def _evaluate_individual(
    ind: Chromosome,
    sample_urls: List[str],
    cookies: Dict[str, str],
    base_url: str,
) -> float:
    """Benchmark one chromosome against sample URLs. Returns fitness score."""
    limits = httpx.Limits(max_keepalive_connections=ind.concurrency, max_connections=ind.concurrency * 2)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    semaphore = asyncio.Semaphore(ind.concurrency)

    async def fetch_one(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
        async with semaphore:
            if ind.request_delay > 0:
                await asyncio.sleep(ind.request_delay)
            start = time.time()
            try:
                resp = await client.get(url, timeout=ind.timeout)
                latency = time.time() - start
                if resp.status_code == 429:
                    return {"success": False, "error": "RATE_LIMIT_429", "latency": latency}
                resp.raise_for_status()
                if "sessions/login" in str(resp.url):
                    return {"success": False, "error": "AUTH_FAILED", "latency": latency}
                return {"success": True, "latency": latency, "html_size": len(resp.text)}
            except Exception as e:
                return {"success": False, "error": type(e).__name__, "latency": time.time() - start}

    start_time = time.time()
    async with httpx.AsyncClient(
        cookies=cookies, headers=headers, limits=limits, follow_redirects=True
    ) as client:
        results = await asyncio.gather(*[fetch_one(client, url) for url in sample_urls])
    elapsed = time.time() - start_time

    success_count = sum(1 for r in results if r.get("success"))
    throughput = (len(results) / elapsed) * 60.0 if elapsed > 0 else 0.0
    success_rate = success_count / len(results) if results else 0.0
    latencies = [r["latency"] for r in results if "latency" in r]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    errors = [r.get("error") for r in results if not r.get("success")]
    rate_limits = sum(1 for e in errors if e == "RATE_LIMIT_429")
    auth_failures = sum(1 for e in errors if e == "AUTH_FAILED")

    base_fitness = throughput * (success_rate ** 2)
    penalty = 0.0
    if rate_limits > 0:
        penalty += rate_limits * 15.0
    if auth_failures > 0:
        penalty += auth_failures * 25.0
    if success_rate < 0.8:
        penalty += 50.0

    ind.fitness = max(0.0, base_fitness - penalty)
    ind.throughput = throughput
    ind.success_rate = success_rate
    ind.avg_latency = avg_latency
    ind.errors = list(set(errors))
    return ind.fitness


async def run_genetic_tuning(
    urls: List[str],
    cookies: Dict[str, str],
    base_url: str = "https://unilever.coupahost.com",
    generations: int = 3,
    pop_size: int = 4,
) -> Chromosome:
    """Evolve optimal crawler parameters using genetic algorithm."""
    population = [Chromosome.random_individual() for _ in range(pop_size)]
    best_overall: Chromosome = population[0]

    for gen in range(generations):
        for ind in population:
            await _evaluate_individual(ind, urls, cookies, base_url)

        population = sorted(population, key=lambda x: x.fitness, reverse=True)
        if population[0].fitness > best_overall.fitness:
            best_overall = population[0]

        # Elitism + crossover/mutation
        next_pop = [population[0]]
        while len(next_pop) < pop_size:
            p1, p2 = random.sample(population[:2], 2)
            child = p1.crossover(p2)
            child.mutate()
            next_pop.append(child)
        population = next_pop

    return best_overall


async def benchmark(
    urls: List[str],
    cookies: Optional[Dict[str, str]] = None,
    base_url: str = "https://unilever.coupahost.com",
) -> Dict[str, Any]:
    """
    Run network benchmark against Coupa endpoints.
    Returns optimal concurrency, delay, timeout, and throughput estimate.
    """
    if not urls:
        return {"error": "No URLs provided for benchmark"}

    best = await run_genetic_tuning(urls, cookies or {}, base_url)
    return {
        "concurrency": best.concurrency,
        "request_delay": best.request_delay,
        "timeout": best.timeout,
        "throughput": best.throughput,
        "success_rate": best.success_rate,
        "avg_latency": best.avg_latency,
        "fitness": best.fitness,
    }
