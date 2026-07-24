"""Integration tests for PipelineRunner in launcher.py.

These tests verify the pipeline orchestrator correctly:
- Executes all 4 steps in order
- Stops on user interrupt
- Reports errors via queue when a step fails
- Does NOT silently skip steps (regression test for v1.2.1 bug)
"""
import queue
import sys
from types import MethodType
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _bind(fn, instance):
    """Bind a function as a method on an instance (bypass descriptor protocol)."""
    return MethodType(fn, instance)


class TestPipelineRunnerIntegration:
    """Verify PipelineRunner executes all steps and handles failures."""

    def test_all_four_steps_execute_in_order(self):
        """Pipeline must call _collect -> _enrich -> _classify -> _apply.

        This is the regression test for the v1.2.1 bug where missing
        return True caused the pipeline to stop after enrich.
        """
        from launcher import PipelineRunner

        executed = []

        def _collect(self):
            executed.append("collect")

        def _enrich(self):
            executed.append("enrich")

        def _classify(self):
            executed.append("classify")

        def _apply(self):
            executed.append("apply")

        def _check_stop(self):
            return False

        q = queue.Queue()
        runner = PipelineRunner(q, lambda *a: None)
        runner._collect = _bind(_collect, runner)
        runner._enrich = _bind(_enrich, runner)
        runner._classify = _bind(_classify, runner)
        runner._apply = _bind(_apply, runner)
        runner._check_stop = _bind(_check_stop, runner)

        runner.run()

        assert executed == ["collect", "enrich", "classify", "apply"], (
            f"Pipeline did not execute all steps. Executed: {executed}"
        )

    def test_stops_after_collect_if_user_interrupts(self):
        """Pipeline should stop if _check_stop returns True after collect."""
        from launcher import PipelineRunner

        executed = []
        stop_after_collect = True

        def _collect(self):
            executed.append("collect")

        def _enrich(self):
            executed.append("enrich")

        def _classify(self):
            executed.append("classify")

        def _apply(self):
            executed.append("apply")

        def _check_stop(self):
            nonlocal stop_after_collect
            if stop_after_collect:
                stop_after_collect = False
                return True
            return False

        q = queue.Queue()
        runner = PipelineRunner(q, lambda *a: None)
        runner._collect = _bind(_collect, runner)
        runner._enrich = _bind(_enrich, runner)
        runner._classify = _bind(_classify, runner)
        runner._apply = _bind(_apply, runner)
        runner._check_stop = _bind(_check_stop, runner)

        runner.run()

        assert executed == ["collect"], (
            f"Pipeline should have stopped after collect. Executed: {executed}"
        )

    def test_enrich_error_is_queued_and_pipeline_continues(self):
        """When _enrich calls _done('error'), the error is queued for GUI.

        The pipeline continues executing (by design); the GUI picks up
        the error from the queue and displays it to the user.
        """
        from launcher import PipelineRunner

        executed = []

        def _collect(self):
            executed.append("collect")

        def _enrich(self):
            executed.append("enrich")
            self.log("test error message")
            self._done("error")

        def _classify(self):
            executed.append("classify")

        def _apply(self):
            executed.append("apply")

        def _check_stop(self):
            return False

        q = queue.Queue()
        runner = PipelineRunner(q, lambda *a: None)
        runner._collect = _bind(_collect, runner)
        runner._enrich = _bind(_enrich, runner)
        runner._classify = _bind(_classify, runner)
        runner._apply = _bind(_apply, runner)
        runner._check_stop = _bind(_check_stop, runner)

        runner.run()

        # All steps execute; error is reported via queue
        assert executed == ["collect", "enrich", "classify", "apply"]
        # Verify the error was queued for the GUI
        queued = []
        while not q.empty():
            queued.append(q.get_nowait())
        assert any(mtype == "done" and mval == "error" for mtype, mval in queued), (
            f"Expected 'done' with 'error' in queue, got: {queued}"
        )

    def test_classify_and_apply_reach_end(self):
        """_classify and _apply must both reach their end (return naturally).

        This catches the v1.2.1 regression where missing `return True`
        caused `if not self._classify()` to treat None as False.
        """
        from launcher import PipelineRunner

        executed = []

        def _collect(self):
            executed.append("collect")

        def _enrich(self):
            executed.append("enrich")

        def _classify(self):
            executed.append("classify")
            # Method runs to end naturally (no early return)

        def _apply(self):
            executed.append("apply")
            # Method runs to end naturally (no early return)

        def _check_stop(self):
            return False

        q = queue.Queue()
        runner = PipelineRunner(q, lambda *a: None)
        runner._collect = _bind(_collect, runner)
        runner._enrich = _bind(_enrich, runner)
        runner._classify = _bind(_classify, runner)
        runner._apply = _bind(_apply, runner)
        runner._check_stop = _bind(_check_stop, runner)

        runner.run()

        assert "collect" in executed, "collect step was never reached"
        assert "enrich" in executed, "enrich step was never reached"
        assert "classify" in executed, "classify step was never reached"
        assert "apply" in executed, "apply step was never reached after classify"
