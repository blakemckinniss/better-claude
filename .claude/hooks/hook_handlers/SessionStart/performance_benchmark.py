"""Performance benchmark for SessionStart hook optimizations."""

import asyncio
import time
from pathlib import Path
from typing import Dict

from SessionStart.context_gatherer import (
    gather_context_comprehensive,
    gather_context_fast,
)
from SessionStart.git_operations import (
    _git_cache, run_batched_git_commands,
    run_fast_command,
)


async def benchmark_single_commands(
    project_dir: str, iterations: int = 10,
) -> Dict[str, float]:
    """Benchmark individual git commands."""
    commands = [
        ["git", "status", "--porcelain"],
        ["git", "log", "--oneline", "-5"],
        ["git", "ls-files"],
    ]

    results = {}

    for cmd in commands:
        cmd_name = " ".join(cmd)
        times = []

        for _ in range(iterations):
            start = time.perf_counter()
            await run_fast_command(cmd, cwd=project_dir)
            end = time.perf_counter()
            times.append(end - start)

        results[f"single_{cmd_name}"] = sum(times) / len(times)

    return results


async def benchmark_batched_commands(
    project_dir: str, iterations: int = 10,
) -> Dict[str, float]:
    """Benchmark batched git commands."""
    commands = [
        (["git", "status", "--porcelain"], project_dir),
        (["git", "log", "--oneline", "-5"], project_dir),
        (["git", "ls-files"], project_dir),
    ]

    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        await run_batched_git_commands(commands)
        end = time.perf_counter()
        times.append(end - start)

    return {"batched_git_commands": sum(times) / len(times)}


async def benchmark_caching_performance(
    project_dir: str, iterations: int = 20,
) -> Dict[str, float]:
    """Benchmark caching effectiveness."""
    cmd = ["git", "status", "--porcelain"]

    # Clear cache
    _git_cache.clear()

    # Measure first run (cache miss)
    cache_miss_times = []
    for _ in range(5):  # Fewer iterations for cache miss
        start = time.perf_counter()
        await run_fast_command(cmd, cwd=project_dir)
        end = time.perf_counter()
        cache_miss_times.append(end - start)
        _git_cache.clear()  # Clear after each to ensure cache miss

    # Measure subsequent runs (cache hits)
    await run_fast_command(cmd, cwd=project_dir)  # Prime cache
    cache_hit_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        await run_fast_command(cmd, cwd=project_dir)
        end = time.perf_counter()
        cache_hit_times.append(end - start)

    return {
        "cache_miss_avg": sum(cache_miss_times) / len(cache_miss_times),
        "cache_hit_avg": sum(cache_hit_times) / len(cache_hit_times),
        "cache_speedup": (sum(cache_miss_times) / len(cache_miss_times))
        / (sum(cache_hit_times) / len(cache_hit_times)),
    }


async def benchmark_context_gathering(
    project_dir: str, iterations: int = 5,
) -> Dict[str, float]:
    """Benchmark context gathering strategies."""
    fast_times = []
    comprehensive_times = []

    for _ in range(iterations):
        # Fast mode
        start = time.perf_counter()
        await gather_context_fast(project_dir)
        end = time.perf_counter()
        fast_times.append(end - start)

        # Comprehensive mode
        start = time.perf_counter()
        await gather_context_comprehensive(project_dir)
        end = time.perf_counter()
        comprehensive_times.append(end - start)

    return {
        "fast_context_avg": sum(fast_times) / len(fast_times),
        "comprehensive_context_avg": sum(comprehensive_times)
        / len(comprehensive_times),
        "fast_vs_comprehensive_speedup": (
            sum(comprehensive_times) / len(comprehensive_times)
        )
        / (sum(fast_times) / len(fast_times)),
    }


async def run_full_benchmark(project_dir: str) -> Dict[str, float]:
    """Run comprehensive performance benchmark."""
    print("🚀 Starting SessionStart performance benchmark...")

    results = {}

    print("  📊 Benchmarking single commands...")
    results.update(await benchmark_single_commands(project_dir))

    print("  📦 Benchmarking batched commands...")
    results.update(await benchmark_batched_commands(project_dir))

    print("  🎯 Benchmarking caching performance...")
    results.update(await benchmark_caching_performance(project_dir))

    print("  🏗️ Benchmarking context gathering...")
    results.update(await benchmark_context_gathering(project_dir))

    return results


def print_benchmark_results(results: Dict[str, float]) -> None:
    """Print formatted benchmark results."""
    print("\n📈 SessionStart Performance Benchmark Results")
    print("=" * 50)

    # Group results by category
    categories = {
        "Git Commands": {
            k: v for k, v in results.items() if k.startswith(("single_", "batched_"))
        },
        "Caching": {k: v for k, v in results.items() if k.startswith("cache_")},
        "Context Gathering": {
            k: v
            for k, v in results.items()
            if k.startswith(("fast_", "comprehensive_"))
        },
        "Performance Gains": {
            k: v for k, v in results.items() if k.endswith("_speedup")
        },
    }

    for category, metrics in categories.items():
        if metrics:
            print(f"\n{category}:")
            for metric, value in metrics.items():
                if "speedup" in metric:
                    print(f"  {metric}: {value:.2f}x faster")
                else:
                    print(f"  {metric}: {value*1000:.2f}ms")

    # Calculate overall improvements
    if "cache_speedup" in results:
        print(f"\n🎯 Cache Hit Speedup: {results['cache_speedup']:.1f}x")

    if "fast_vs_comprehensive_speedup" in results:
        print(
            f"⚡ Fast vs Comprehensive: {results['fast_vs_comprehensive_speedup']:.1f}x",
        )


async def main():
    """Main benchmark execution."""
    project_dir = str(Path(__file__).parent.parent.parent.parent.parent)

    try:
        results = await run_full_benchmark(project_dir)
        print_benchmark_results(results)

        # Performance recommendations
        print("\n💡 Optimization Recommendations:")

        if results.get("cache_speedup", 1) > 2:
            print("  ✅ Caching is highly effective - keep enabled")
        else:
            print("  ⚠️ Caching shows minimal benefit - consider disabling")

        if results.get("fast_vs_comprehensive_speedup", 1) > 3:
            print("  ✅ Fast mode provides significant performance gains")
        else:
            print("  ⚠️ Fast mode benefits are marginal")

        # Save results for CI/monitoring
        import json

        with open("benchmark_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print("\n📁 Results saved to benchmark_results.json")

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
