"""SQLite run ledger, artifact registry, and query surface."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from task_bundle.errors import StoreNotFoundError


SCHEMA_VERSION = 1
PARSER_VERSION = "pytest-junit-xunit2-v1"


class StoreSchemaError(Exception):
    """The SQLite schema version does not match this package."""


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    verb: str
    task_id: str
    started_at: str
    finished_at: str | None
    terminal_state: str | None
    taxonomy_code: str | None
    verdict: str | None
    failure_class: str | None
    exit_code: int | None
    error_message: str | None
    bundle_hash: str
    image_tag: str
    image_digest: str | None
    base_commit: str
    instance_commit: str
    repo_language: str
    parser_version: str
    apply_ladder_winner: str | None
    apply_partial: int | None
    reserved_path_collisions_json: str | None
    host_info_json: str | None
    isolation_snapshot_json: str | None


@dataclass(frozen=True)
class TestOutcomeRow:
    run_id: str
    phase: str
    test_id: str
    expected: str
    actual_status: str
    satisfied: bool | None
    duration_ms: int


TestOutcomeRow.__test__ = False


@dataclass(frozen=True)
class EventRecord:
    run_id: str
    ts: float
    kind: str
    payload_json: str

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self.payload_json)


@dataclass(frozen=True)
class ArtifactRef:
    run_id: str
    kind: str
    path: str
    sha256: str
    bytes: int


@dataclass(frozen=True)
class FullRunReport:
    run: RunRecord
    test_outcomes: tuple[TestOutcomeRow, ...]
    events: tuple[EventRecord, ...]
    artifacts: tuple[ArtifactRef, ...]
    in_flight: bool


class Store:
    """Context-managed SQLite store with short explicit transactions."""

    def __init__(self, db_path: Path | str | None = None, artifact_root: Path | str | None = None) -> None:
        self.db_path = Path(
            db_path
            or os.environ.get("TASK_BUNDLE_DB")
            or (Path.home() / ".swe-task" / "runs.db")
        )
        self.artifact_base = Path(
            artifact_root
            or os.environ.get("TASK_BUNDLE_ARTIFACTS")
            or (Path.home() / ".swe-task" / "artifacts")
        )
        self._conn: sqlite3.Connection | None = None

    def __enter__(self) -> "Store":
        self.open()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Store is not open")
        return self._conn

    def open(self) -> None:
        if self._conn is not None:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        if version == 0:
            self._apply_schema(conn)
        elif version != SCHEMA_VERSION:
            conn.close()
            raise StoreSchemaError(f"Store schema version mismatch: expected {SCHEMA_VERSION}, found {version}")
        self._conn = conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def artifact_dir(self, run_id: str) -> Path:
        path = self.artifact_base / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def create_run(
        self,
        run_id: str,
        verb: str,
        task_id: str,
        bundle_hash: str,
        image_tag: str,
        base_commit: str,
        instance_commit: str,
        repo_language: str,
        parser_version: str = PARSER_VERSION,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO runs (
              run_id, verb, task_id, started_at, bundle_hash, image_tag,
              base_commit, instance_commit, repo_language, parser_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                verb,
                task_id,
                _now_iso(),
                bundle_hash,
                image_tag,
                base_commit,
                instance_commit,
                repo_language,
                parser_version,
            ),
        )
        self.conn.commit()

    def append_event(self, run_id: str, kind: str, payload: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO events (run_id, ts, kind, payload_json) VALUES (?, ?, ?, ?)",
            (run_id, time.time(), kind, json.dumps(payload, sort_keys=True)),
        )
        self.conn.commit()

    def record_test_outcomes(
        self,
        run_id: str,
        phase: str,
        outcomes: Iterable[TestOutcomeRow],
    ) -> None:
        rows = [
            (
                run_id,
                phase,
                outcome.test_id,
                outcome.expected,
                outcome.actual_status,
                _bool_to_db(outcome.satisfied),
                outcome.duration_ms,
            )
            for outcome in outcomes
        ]
        self.conn.executemany(
            """
            INSERT INTO test_outcomes (
              run_id, phase, test_id, expected, actual_status, satisfied, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def record_artifact(self, run_id: str, kind: str, path: str, sha256: str, bytes: int) -> None:
        self.conn.execute(
            "INSERT INTO artifacts (run_id, kind, path, sha256, bytes) VALUES (?, ?, ?, ?, ?)",
            (run_id, kind, path, sha256, bytes),
        )
        self.conn.commit()

    def finalize_run(
        self,
        run_id: str,
        finished_at: str | None,
        terminal_state: str | None,
        taxonomy_code: str | None,
        verdict: str | None,
        failure_class: str | None,
        exit_code: int | None,
        error_message: str | None,
        apply_ladder_winner: str | None,
        apply_partial: int | None,
        reserved_path_collisions_json: str | None,
        host_info_json: str | None,
        isolation_snapshot_json: str | None,
        image_digest: str | None,
    ) -> None:
        cursor = self.conn.execute(
            """
            UPDATE runs
            SET finished_at = ?,
                terminal_state = ?,
                taxonomy_code = ?,
                verdict = ?,
                failure_class = ?,
                exit_code = ?,
                error_message = ?,
                apply_ladder_winner = ?,
                apply_partial = ?,
                reserved_path_collisions_json = ?,
                host_info_json = ?,
                isolation_snapshot_json = ?,
                image_digest = ?
            WHERE run_id = ?
            """,
            (
                finished_at,
                terminal_state,
                taxonomy_code,
                verdict,
                failure_class,
                exit_code,
                error_message,
                apply_ladder_winner,
                apply_partial,
                reserved_path_collisions_json,
                host_info_json,
                isolation_snapshot_json,
                image_digest,
                run_id,
            ),
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            raise StoreNotFoundError(f"run not found: {run_id}")

    def get_run(self, run_id: str) -> RunRecord | None:
        row = self.conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return _run_from_row(row) if row else None

    def get_test_outcomes(self, run_id: str, phase: str | None = None) -> tuple[TestOutcomeRow, ...]:
        if phase is None:
            rows = self.conn.execute(
                "SELECT * FROM test_outcomes WHERE run_id = ? ORDER BY rowid",
                (run_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM test_outcomes WHERE run_id = ? AND phase = ? ORDER BY rowid",
                (run_id, phase),
            ).fetchall()
        return tuple(_test_outcome_from_row(row) for row in rows)

    def get_events(self, run_id: str, since_ts: float | None = None) -> tuple[EventRecord, ...]:
        if since_ts is None:
            rows = self.conn.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY ts",
                (run_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM events WHERE run_id = ? AND ts >= ? ORDER BY ts",
                (run_id, since_ts),
            ).fetchall()
        return tuple(_event_from_row(row) for row in rows)

    def get_artifacts(self, run_id: str, kind: str | None = None) -> tuple[ArtifactRef, ...]:
        if kind is None:
            rows = self.conn.execute(
                "SELECT * FROM artifacts WHERE run_id = ? ORDER BY rowid",
                (run_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM artifacts WHERE run_id = ? AND kind = ? ORDER BY rowid",
                (run_id, kind),
            ).fetchall()
        return tuple(_artifact_from_row(row) for row in rows)

    def list_runs(
        self,
        task_id: str | None = None,
        verdict: str | None = None,
        verb: str | None = None,
        limit: int = 50,
    ) -> tuple[RunRecord, ...]:
        clauses = []
        args: list[Any] = []
        if task_id is not None:
            clauses.append("task_id = ?")
            args.append(task_id)
        if verdict is not None:
            clauses.append("verdict = ?")
            args.append(verdict)
        if verb is not None:
            clauses.append("verb = ?")
            args.append(verb)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        args.append(limit)
        rows = self.conn.execute(
            f"SELECT * FROM runs {where} ORDER BY started_at DESC LIMIT ?",
            args,
        ).fetchall()
        return tuple(_run_from_row(row) for row in rows)

    def get_run_full(self, run_id: str) -> FullRunReport:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            run = self.get_run(run_id)
            if run is None:
                raise StoreNotFoundError(f"run not found: {run_id}")
            outcomes = self.get_test_outcomes(run_id)
            events = self.get_events(run_id)
            artifacts = self.get_artifacts(run_id)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return FullRunReport(
            run=run,
            test_outcomes=outcomes,
            events=events,
            artifacts=artifacts,
            in_flight=run.finished_at is None,
        )

    def _apply_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
              run_id TEXT PRIMARY KEY,
              verb TEXT NOT NULL,
              task_id TEXT NOT NULL,
              started_at TEXT NOT NULL,
              finished_at TEXT NULL,
              terminal_state TEXT NULL,
              taxonomy_code TEXT NULL,
              verdict TEXT NULL,
              failure_class TEXT NULL,
              exit_code INTEGER NULL,
              error_message TEXT NULL,
              bundle_hash TEXT NOT NULL,
              image_tag TEXT NOT NULL,
              image_digest TEXT NULL,
              base_commit TEXT NOT NULL,
              instance_commit TEXT NOT NULL,
              repo_language TEXT NOT NULL,
              parser_version TEXT NOT NULL,
              apply_ladder_winner TEXT NULL,
              apply_partial INTEGER NULL,
              reserved_path_collisions_json TEXT NULL,
              host_info_json TEXT NULL,
              isolation_snapshot_json TEXT NULL
            );

            CREATE TABLE IF NOT EXISTS test_outcomes (
              run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
              phase TEXT NOT NULL,
              test_id TEXT NOT NULL,
              expected TEXT NOT NULL,
              actual_status TEXT NOT NULL,
              satisfied INTEGER NULL,
              duration_ms INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_test_outcomes_run_id ON test_outcomes(run_id);
            CREATE INDEX IF NOT EXISTS idx_test_outcomes_run_phase ON test_outcomes(run_id, phase);
            CREATE INDEX IF NOT EXISTS idx_test_outcomes_test_id ON test_outcomes(test_id);

            CREATE TABLE IF NOT EXISTS events (
              run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
              ts REAL NOT NULL,
              kind TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_run_ts ON events(run_id, ts);

            CREATE TABLE IF NOT EXISTS artifacts (
              run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
              kind TEXT NOT NULL,
              path TEXT NOT NULL,
              sha256 TEXT NOT NULL,
              bytes INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_artifacts_run_kind ON artifacts(run_id, kind);

            PRAGMA user_version = 1;
            """
        )
        conn.commit()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _bool_to_db(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


def _db_to_bool(value: int | None) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _run_from_row(row: sqlite3.Row) -> RunRecord:
    return RunRecord(**{key: row[key] for key in row.keys()})


def _test_outcome_from_row(row: sqlite3.Row) -> TestOutcomeRow:
    return TestOutcomeRow(
        run_id=row["run_id"],
        phase=row["phase"],
        test_id=row["test_id"],
        expected=row["expected"],
        actual_status=row["actual_status"],
        satisfied=_db_to_bool(row["satisfied"]),
        duration_ms=row["duration_ms"],
    )


def _event_from_row(row: sqlite3.Row) -> EventRecord:
    return EventRecord(
        run_id=row["run_id"],
        ts=row["ts"],
        kind=row["kind"],
        payload_json=row["payload_json"],
    )


def _artifact_from_row(row: sqlite3.Row) -> ArtifactRef:
    return ArtifactRef(
        run_id=row["run_id"],
        kind=row["kind"],
        path=row["path"],
        sha256=row["sha256"],
        bytes=row["bytes"],
    )
