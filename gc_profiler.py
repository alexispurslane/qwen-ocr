"""GC profiling utilities."""

import gc
import time


class GCProfiler:
    """Profiles garbage collection activity."""

    def __init__(self):
        self.collection_count = [0, 0, 0]
        self.total_time = 0.0
        self.start_time = time.time()
        self._original_collect = None
        self._enabled = False
        self._start_stats = None

    def enable(self):
        """Enable GC profiling."""
        if self._enabled:
            return

        self._original_collect = gc.collect
        self._enabled = True
        self._start_stats = gc.get_stats()

        def profiled_collect(generation=2):
            if self._original_collect is None:
                return 0

            start = time.perf_counter()
            result = self._original_collect(generation)
            elapsed = time.perf_counter() - start

            self.total_time += elapsed
            if generation == 0:
                self.collection_count[0] += 1
            elif generation == 1:
                self.collection_count[1] += 1
            else:
                self.collection_count[2] += 1

            return result

        gc.collect = profiled_collect

    def disable(self):
        """Disable GC profiling."""
        if not self._enabled or self._original_collect is None:
            return

        gc.collect = self._original_collect
        self._enabled = False

    def get_stats(self):
        """Get GC statistics including automatic collections."""
        if not self._enabled or self._start_stats is None:
            return {
                "collections": 0,
                "collections_by_gen": (0, 0, 0),
                "total_time": 0.0,
                "elapsed_time": time.time() - self.start_time,
            }

        current_stats = gc.get_stats()
        automatic_collections = [0, 0, 0]

        for i in range(3):
            automatic_collections[i] = (
                current_stats[i]["collections"] - self._start_stats[i]["collections"]
            )

        total_collections = [
            self.collection_count[i] + automatic_collections[i] for i in range(3)
        ]

        return {
            "collections": sum(total_collections),
            "collections_by_gen": tuple(total_collections),
            "explicit_collections": tuple(self.collection_count),
            "automatic_collections": tuple(automatic_collections),
            "total_time": self.total_time,
            "elapsed_time": time.time() - self.start_time,
        }

    def reset(self):
        """Reset statistics."""
        self.collection_count = [0, 0, 0]
        self.total_time = 0.0
        self.start_time = time.time()
        self._start_stats = gc.get_stats() if self._enabled else None


gc_profiler = GCProfiler()
