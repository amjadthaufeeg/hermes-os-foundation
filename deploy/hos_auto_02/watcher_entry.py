"""Retry-safe R2 watcher entrypoint.

Keeps the mature watcher implementation intact while fixing two closure issues
for the current GitHub Issue ingress:

1. a failed AUTO execution must not permanently poison ``completed_tasks``;
   a new immutable issue/version with a new nonce may retry the same task id;
2. duplicate issue versions must be marked processed so they are not polled
   forever.

Exact issue versions remain single-shot. Retry requires a new source version
and nonce, preserving replay protection and immutable evidence.
"""
import time

from deploy.hos_auto_02 import watcher


RETRYABLE_EXECUTION_VERDICTS = frozenset({
    "FAIL",
    "TIMEOUT",
    "ERROR",
    "TEST_ENVIRONMENT_INVALID",
})
TRANSIENT_VERDICTS = frozenset({
    "GATED",
    "RATE_LIMITED",
    "CLAIM_FAILED",
    "SOURCE_CHANGED",
    "REPLAY",
})


def finalize_issue_outcome(result, mark_completed) -> None:
    """Persist task-level terminal/retry state after one issue attempt."""
    verdict = result.verdict
    task_id = result.task_id

    if verdict == "FAIL":
        # watcher.process_task_content already recorded this failure.
        if any("STOP: 3 identical failures" in w for w in result.warnings):
            mark_completed(task_id)
        return

    if verdict in RETRYABLE_EXECUTION_VERDICTS:
        # Non-FAIL retryable verdicts are counted here. The legacy reset is
        # suppressed during issue processing so the count survives retries.
        if watcher.persistent_record_failure(task_id):
            if "STOP: 3 identical failures" not in result.warnings:
                result.warnings.append("STOP: 3 identical failures")
            mark_completed(task_id)
        return

    if verdict in TRANSIENT_VERDICTS or verdict == "DUPLICATE":
        return

    # PASS and deterministic terminal rejections/stops become completed.
    watcher.persistent_reset_failures(task_id)
    mark_completed(task_id)


def process_issue_retry_safe(issue_number: int):
    """Process one issue without prematurely completing retryable failures."""
    original_mark_completed = watcher.persistent_mark_completed
    original_reset_failures = watcher.persistent_reset_failures
    watcher.persistent_mark_completed = lambda task_id: None
    watcher.persistent_reset_failures = lambda task_id: None
    try:
        result = watcher.process_issue_task(issue_number)
    finally:
        watcher.persistent_mark_completed = original_mark_completed
        watcher.persistent_reset_failures = original_reset_failures

    finalize_issue_outcome(result, original_mark_completed)
    return result


def _mark_current_issue_version_processed(issue_number: int) -> None:
    """Best-effort de-queue of the current immutable issue version."""
    try:
        envelope = watcher.read_issue_task(issue_number)
        if envelope:
            watcher.persistent_mark_issue_processed(
                issue_number, envelope["source_version"]
            )
    except Exception as exc:
        print(f"Issue processed-marker warning for #{issue_number}: {exc}")


def watch_loop():
    print("HOS-AUTO-02 R2 watcher started (retry-safe issue ingress)")
    while True:
        try:
            watcher.git_pull()

            # Legacy/direct file ingress keeps its existing immutable behavior.
            for filename in watcher.list_inbox_tasks():
                print(f"Processing file task: {filename}")
                result = watcher.process_file_task(filename)
                published = watcher.publish_result(result)
                if published and hasattr(result, "_source_version"):
                    watcher.persistent_mark_issue_processed(
                        result._issue_number, result._source_version
                    )
                print(f"  -> {result.status} {result.verdict}: {result.summary[:80]}")

            try:
                issues = watcher.list_issue_tasks()
            except Exception as exc:
                issues = []
                print(f"Issue ingress unavailable: {exc}")

            for issue in issues:
                number = int(issue["number"])
                print(f"Processing issue task: #{number}")
                result = process_issue_retry_safe(number)

                if result.verdict == "DUPLICATE":
                    # No duplicate result publication is needed, but the issue
                    # version must be retired from future polling.
                    _mark_current_issue_version_processed(number)
                    print(f"  -> {result.status} {result.verdict}: {result.summary[:80]}")
                    continue

                published = watcher.publish_result(result)
                if published:
                    if hasattr(result, "_issue_number"):
                        watcher.persistent_mark_issue_processed(
                            result._issue_number, result._source_version
                        )
                    else:
                        _mark_current_issue_version_processed(number)
                print(f"  -> {result.status} {result.verdict}: {result.summary[:80]}")

        except KeyboardInterrupt:
            break
        except Exception as exc:
            print(f"Watcher error: {exc}")
        time.sleep(watcher.POLL_INTERVAL)


if __name__ == "__main__":
    watch_loop()
