"""
ai_comment_worker.py - Background worker for AI comment generation with retry.

Provides a queue-based worker that processes AI comment requests one at a time,
with exponential backoff retry for transient failures.
"""
import logging
import queue
import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3        # Total attempts = 1 initial + 3 retries
BASE_DELAY = 3.0       # Initial retry delay in seconds
MAX_DELAY = 30.0       # Cap on retry delay


class AiCommentWorker(QObject):
    """Queue-based background worker for AI comment generation.

    Usage:
        worker = AiCommentWorker(api_client)
        worker.ai_succeeded.connect(on_success)
        worker.ai_failed.connect(on_failure)
        worker.submit(step_id)   # non-blocking
        ...
        worker.stop()            # on shutdown
    """

    ai_started = pyqtSignal(int)            # step_id
    ai_succeeded = pyqtSignal(int)          # step_id
    ai_failed = pyqtSignal(int, str)        # step_id, error message
    ai_retrying = pyqtSignal(int, int, int) # step_id, attempt (1-based), max_retries

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self._api = api_client
        self._queue = queue.Queue()
        self._running = False
        self._thread = None

    def submit(self, step_id):
        """Enqueue a step for AI comment generation. Non-blocking."""
        self._queue.put(step_id)
        self._ensure_thread()

    def stop(self):
        """Signal the worker thread to stop and wait briefly."""
        self._running = False
        self._queue.put(None)  # sentinel to unblock queue.get()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _ensure_thread(self):
        """Start the worker thread if not already running."""
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def _worker_loop(self):
        """Main loop: pull step_ids from queue and process them."""
        while self._running:
            try:
                step_id = self._queue.get(timeout=5)
            except queue.Empty:
                # No work for a while; keep looping to check _running flag
                continue

            if step_id is None:
                # Sentinel: time to exit
                break

            self._process_one(step_id)

        self._running = False

    def _process_one(self, step_id):
        """Attempt AI comment generation with exponential backoff retry."""
        self.ai_started.emit(step_id)

        last_error = ''
        for attempt in range(MAX_RETRIES + 1):
            if not self._running:
                return

            try:
                self._api.trigger_ai_comment(step_id)
                self.ai_succeeded.emit(step_id)
                logger.info('AI comment generated for step %s', step_id)
                return
            except ConnectionError as e:
                # Network issue - always retryable
                last_error = str(e)
            except RuntimeError as e:
                last_error = str(e)
                if not self._is_retryable(e):
                    # Permanent error (HTTP 4xx) - no point retrying
                    self.ai_failed.emit(step_id, last_error)
                    logger.warning('AI comment permanently failed for step %s: %s',
                                   step_id, last_error)
                    return
            except Exception as e:
                last_error = str(e)

            # Retry with exponential backoff
            if attempt < MAX_RETRIES:
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                self.ai_retrying.emit(step_id, attempt + 1, MAX_RETRIES)
                logger.info('AI comment retry %d/%d for step %s in %.0fs',
                            attempt + 1, MAX_RETRIES, step_id, delay)
                # Sleep in small increments so stop() can interrupt
                deadline = time.time() + delay
                while time.time() < deadline and self._running:
                    time.sleep(0.5)

        # All retries exhausted
        self.ai_failed.emit(step_id, last_error)
        logger.warning('AI comment failed after %d retries for step %s: %s',
                        MAX_RETRIES, step_id, last_error)

    @staticmethod
    def _is_retryable(error):
        """Determine if a RuntimeError from the API client is retryable."""
        msg = str(error)
        # HTTP 4xx errors are permanent (bad request, no API key, etc.)
        if 'HTTP 4' in msg:
            return False
        # HTTP 5xx and other errors are transient
        return True
