import threading
from typing import List

import pytest

from qrl.crypto.xmss import XMSS


def test_concurrent_signatures_unique_and_index_advances():
    xmss = XMSS(height=6)  # max_signatures = 64
    n = 20

    lock = threading.Lock()
    signatures: List[str] = []
    errors: List[BaseException] = []

    def worker(i: int):
        try:
            sig = xmss.sign(b"payload")
            with lock:
                signatures.append(sig)
        except BaseException as e:
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Unexpected errors during concurrent signing: {errors}"
    assert len(signatures) == n
    assert len(set(signatures)) == n, "Signatures should be unique due to OTS index consumption"
    # Index should have advanced by n
    assert xmss.index >= n


def test_concurrent_oversubscription_raises_after_max():
    xmss = XMSS(height=4)  # max_signatures = 16
    total_attempts = 20

    lock = threading.Lock()
    successes = 0
    failures = 0

    def worker():
        nonlocal successes, failures
        try:
            xmss.sign(b"payload")
            with lock:
                successes += 1
        except ValueError:
            with lock:
                failures += 1

    threads = [threading.Thread(target=worker) for _ in range(total_attempts)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert successes == xmss.max_signatures, "Should succeed exactly max_signatures times"
    assert failures == total_attempts - xmss.max_signatures, "Excess attempts should fail"
