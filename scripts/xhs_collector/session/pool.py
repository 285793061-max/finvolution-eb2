from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime
import random

from .models import Session, SessionConfig


class SessionPool:
    """
    Session pool with error-score-based rotation.
    File-based JSON storage.
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        config: Optional[SessionConfig] = None,
    ):
        self.data_dir = data_dir or Path.home() / ".xhs_collector" / "session"
        self.config = config or SessionConfig()
        self._sessions: dict[str, Session] = {}
        self._load_sessions()

    def _get_sessions_path(self) -> Path:
        """Get path to sessions file."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "sessions.json"

    def _load_sessions(self) -> None:
        """Load sessions from file."""
        path = self._get_sessions_path()
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, info in data.items():
                        self._sessions[sid] = Session(
                            id=sid,
                            error_score=info.get("error_score", 0),
                            max_error_score=self.config.max_error_score,
                            created_at=info.get("created_at", datetime.now().timestamp()),
                            last_used_at=info.get("last_used_at", datetime.now().timestamp()),
                            success_count=info.get("success_count", 0),
                            failure_count=info.get("failure_count", 0),
                        )
            except Exception:
                self._sessions = {}

    def _save_sessions(self) -> None:
        """Save sessions to file."""
        path = self._get_sessions_path()
        data = {
            sid: {
                "error_score": s.error_score,
                "created_at": s.created_at,
                "last_used_at": s.last_used_at,
                "success_count": s.success_count,
                "failure_count": s.failure_count,
            }
            for sid, s in self._sessions.items()
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return hashlib.sha1(str(datetime.now().timestamp()).encode()).hexdigest()[:16]

    def get_session(self) -> Session:
        """Get the best available session using error-score rotation."""
        # Find healthy sessions, sorted by error score (lowest first)
        healthy = [s for s in self._sessions.values() if s.is_healthy]
        if healthy:
            healthy.sort(key=lambda s: (s.error_score, s.last_used_at))
            session = healthy[0]
            session.last_used_at = datetime.now().timestamp()
            self._save_sessions()
            return session

        # All sessions are unhealthy, return the one with lowest error score
        if self._sessions:
            worst = min(self._sessions.values(), key=lambda s: s.error_score)
            worst.error_score = 0  # Reset
            worst.last_used_at = datetime.now().timestamp()
            self._save_sessions()
            return worst

        # Create new session
        session = Session(
            id=self._generate_session_id(),
            max_error_score=self.config.max_error_score,
        )
        self._sessions[session.id] = session
        self._save_sessions()
        return session

    def record_success(self, session_id: str) -> None:
        """Record success for a session."""
        session = self._sessions.get(session_id)
        if session:
            session.record_success()
            self._save_sessions()

    def record_failure(self, session_id: str, weight: int = 1) -> None:
        """Record failure for a session."""
        session = self._sessions.get(session_id)
        if session:
            session.record_failure(weight)
            self._save_sessions()

    def clear(self) -> None:
        """Clear all sessions."""
        self._sessions.clear()
        self._save_sessions()