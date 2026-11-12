from __future__ import annotations


def test_imports_all_scaffold_modules() -> None:
    import task_bundle
    import task_bundle.bundle
    import task_bundle.cli
    import task_bundle.container
    import task_bundle.errors
    import task_bundle.grader
    import task_bundle.orchestrator
    import task_bundle.parser
    import task_bundle.solver
    import task_bundle.staging
    import task_bundle.store

    assert task_bundle.__version__
