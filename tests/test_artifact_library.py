"""
Regression tests for Artifact History, Persistence, and Downloads.
Includes both:
1. Fast mocked unit tests (API endpoints, ownership validation, download headers, CSP/sandboxing).
2. Real PostgreSQL database integration tests (multi-artifact retention, deduplication, isolation).
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db, SessionLocal
from app import crud, models
from app.validator import secure_artifact_html

client = TestClient(app)


# ===========================================================================
# 1. MOCKED UNIT TESTS
# ===========================================================================

class TestMockedArtifactEndpoints:
    """Mocked unit tests for Artifact Library API endpoints."""

    def test_list_artifacts_session_not_found(self):
        """Listing artifacts for a non-existent session returns 404."""
        mock_db = MagicMock()
        with patch("app.main.get_db", return_value=mock_db), \
             patch("app.crud.get_session", return_value=None):
            app.dependency_overrides[get_db] = lambda: mock_db
            try:
                res = client.get(f"/api/v1/sessions/{uuid.uuid4()}/artifacts")
                assert res.status_code == 404
                assert "Session not found" in res.json().get("detail", "")
            finally:
                app.dependency_overrides.clear()

    def test_list_artifacts_success(self):
        """Listing artifacts returns serialized summaries in order."""
        sess_id = uuid.uuid4()
        art_id1 = uuid.uuid4()
        art_id2 = uuid.uuid4()

        mock_sess = MagicMock(id=sess_id)
        mock_art1 = MagicMock(
            id=art_id1,
            session_id=sess_id,
            artifact_type="html",
            title="Landing Page",
            created_at=datetime.now(timezone.utc)
        )
        mock_art2 = MagicMock(
            id=art_id2,
            session_id=sess_id,
            artifact_type="markdown",
            title="Growth Essay",
            created_at=datetime.now(timezone.utc)
        )

        mock_db = MagicMock()
        with patch("app.main.get_db", return_value=mock_db), \
             patch("app.crud.get_session", return_value=mock_sess), \
             patch("app.crud.get_session_artifacts", return_value=[mock_art1, mock_art2]):
            app.dependency_overrides[get_db] = lambda: mock_db
            try:
                res = client.get(f"/api/v1/sessions/{sess_id}/artifacts")
                assert res.status_code == 200
                data = res.json()
                assert len(data) == 2
                assert data[0]["title"] == "Landing Page"
                assert data[0]["artifact_type"] == "html"
                assert data[1]["title"] == "Growth Essay"
                assert data[1]["artifact_type"] == "markdown"
            finally:
                app.dependency_overrides.clear()

    def test_get_artifact_not_found(self):
        """Requesting a missing artifact ID returns 404."""
        mock_db = MagicMock()
        with patch("app.main.get_db", return_value=mock_db), \
             patch("app.crud.get_artifact", return_value=None):
            app.dependency_overrides[get_db] = lambda: mock_db
            try:
                res = client.get(f"/api/v1/artifacts/{uuid.uuid4()}")
                assert res.status_code == 404
                assert "Artifact not found" in res.json().get("detail", "")
            finally:
                app.dependency_overrides.clear()

    def test_get_artifact_cross_session_forbidden(self):
        """Requesting an artifact from a different session returns 403 Forbidden."""
        mock_db = MagicMock()
        target_art_id = uuid.uuid4()
        other_sess_id = uuid.uuid4()

        # Artifact exists globally, but crud.get_artifact with session_id returns None
        mock_other = MagicMock(id=target_art_id, session_id=uuid.uuid4())

        def mock_get_art(db, art_id, session_id=None):
            if session_id:
                return None
            return mock_other

        with patch("app.main.get_db", return_value=mock_db), \
             patch("app.crud.get_artifact", side_effect=mock_get_art):
            app.dependency_overrides[get_db] = lambda: mock_db
            try:
                res = client.get(f"/api/v1/artifacts/{target_art_id}?session_id={other_sess_id}")
                assert res.status_code == 403
                assert "Access denied" in res.json().get("detail", "")
            finally:
                app.dependency_overrides.clear()

    def test_get_artifact_success(self):
        """Requesting an artifact with valid ownership returns full content."""
        sess_id = uuid.uuid4()
        art_id = uuid.uuid4()
        mock_art = MagicMock(
            id=art_id,
            session_id=sess_id,
            artifact_type="html",
            title="Retention Dashboard",
            content="<div class='dash'>Active</div>",
            created_at=datetime.now(timezone.utc)
        )

        mock_db = MagicMock()
        with patch("app.main.get_db", return_value=mock_db), \
             patch("app.crud.get_artifact", return_value=mock_art):
            app.dependency_overrides[get_db] = lambda: mock_db
            try:
                res = client.get(f"/api/v1/artifacts/{art_id}?session_id={sess_id}")
                assert res.status_code == 200
                data = res.json()
                assert data["id"] == str(art_id)
                assert data["title"] == "Retention Dashboard"
                assert data["content"] == "<div class='dash'>Active</div>"
            finally:
                app.dependency_overrides.clear()

    def test_download_html_artifact_headers(self):
        """Downloading an HTML artifact sets .html extension and text/html MIME type."""
        art_id = uuid.uuid4()
        sess_id = uuid.uuid4()
        mock_art = MagicMock(
            id=art_id,
            session_id=sess_id,
            artifact_type="html",
            title="Pricing Calculator v2!",
            content="<!DOCTYPE html><html><body>Calculator</body></html>",
            created_at=datetime.now(timezone.utc)
        )

        mock_db = MagicMock()
        with patch("app.main.get_db", return_value=mock_db), \
             patch("app.crud.get_artifact", return_value=mock_art):
            app.dependency_overrides[get_db] = lambda: mock_db
            try:
                res = client.get(f"/api/v1/artifacts/{art_id}/download?session_id={sess_id}")
                assert res.status_code == 200
                assert "text/html" in res.headers["content-type"]
                assert 'attachment; filename="pricing_calculator_v2.html"' == res.headers["content-disposition"]
                assert res.text == "<!DOCTYPE html><html><body>Calculator</body></html>"
            finally:
                app.dependency_overrides.clear()

    def test_download_markdown_artifact_headers(self):
        """Downloading a Markdown artifact sets .md extension and text/markdown MIME type."""
        art_id = uuid.uuid4()
        sess_id = uuid.uuid4()
        mock_art = MagicMock(
            id=art_id,
            session_id=sess_id,
            artifact_type="markdown",
            title="Ship 30 Essay: Retention",
            content="# The Retention Playbook\n\nBy Lenny",
            created_at=datetime.now(timezone.utc)
        )

        mock_db = MagicMock()
        with patch("app.main.get_db", return_value=mock_db), \
             patch("app.crud.get_artifact", return_value=mock_art):
            app.dependency_overrides[get_db] = lambda: mock_db
            try:
                res = client.get(f"/api/v1/artifacts/{art_id}/download?session_id={sess_id}")
                assert res.status_code == 200
                assert "text/markdown" in res.headers["content-type"]
                assert 'attachment; filename="ship_30_essay_retention.md"' == res.headers["content-disposition"]
                assert res.text == "# The Retention Playbook\n\nBy Lenny"
            finally:
                app.dependency_overrides.clear()

    def test_download_cross_session_forbidden(self):
        """Cross-session artifact download returns 403 Forbidden."""
        mock_db = MagicMock()
        target_art_id = uuid.uuid4()
        other_sess_id = uuid.uuid4()
        mock_other = MagicMock(id=target_art_id, session_id=uuid.uuid4())

        def mock_get_art(db, art_id, session_id=None):
            if session_id:
                return None
            return mock_other

        with patch("app.main.get_db", return_value=mock_db), \
             patch("app.crud.get_artifact", side_effect=mock_get_art):
            app.dependency_overrides[get_db] = lambda: mock_db
            try:
                res = client.get(f"/api/v1/artifacts/{target_art_id}/download?session_id={other_sess_id}")
                assert res.status_code == 403
                assert "Access denied" in res.json().get("detail", "")
            finally:
                app.dependency_overrides.clear()

    def test_chat_endpoint_returns_persisted_artifact_metadata(self):
        """When an artifact is generated via chat, artifact_id and artifact_title are returned."""
        saved_art_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_sess = MagicMock(id=uuid.uuid4())
        mock_art = MagicMock(id=saved_art_id, title="Landing Page Mockup")

        with patch("app.main.get_db", return_value=mock_db), \
             patch("app.crud.create_session", return_value=mock_sess), \
             patch("app.crud.get_session_messages", return_value=[]), \
             patch("app.main.retrieve_context", return_value=("Context", [])), \
             patch("app.main.call_pi_agent", return_value=("Here is the page", "<html><head><title>Landing Page Mockup</title></head><body>Welcome</body></html>", {})), \
             patch("app.crud.create_artifact", return_value=mock_art), \
             patch("app.crud.save_message_pair"):
            app.dependency_overrides[get_db] = lambda: mock_db
            try:
                res = client.post("/api/v1/chat", json={
                    "question": "Build an html landing page for growth loops",
                    "provider": "ollama",
                    "model": "qwen2.5:3b"
                })
                assert res.status_code == 200
                data = res.json()
                assert data["artifact"] is not None
                assert data["artifact_id"] == str(saved_art_id)
                assert data["artifact_title"] == "Landing Page Mockup"
            finally:
                app.dependency_overrides.clear()

    def test_chat_endpoint_returns_persisted_markdown_artifact(self):
        """When a markdown artifact is generated, artifact_type='markdown' and title are returned."""
        saved_art_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_sess = MagicMock(id=uuid.uuid4())
        mock_art = MagicMock(id=saved_art_id, title="User Activation Checklist", artifact_type="markdown")

        with patch("app.main.get_db", return_value=mock_db), \
             patch("app.crud.create_session", return_value=mock_sess), \
             patch("app.crud.get_session_messages", return_value=[]), \
             patch("app.main.retrieve_context", return_value=("Context", [])), \
             patch("app.main.call_pi_agent", return_value=("Here is the checklist", "# User Activation Checklist\n\n- [ ] Step 1", {})), \
             patch("app.crud.create_artifact", return_value=mock_art), \
             patch("app.crud.save_message_pair"):
            app.dependency_overrides[get_db] = lambda: mock_db
            try:
                res = client.post("/api/v1/chat", json={
                    "question": "Create a Markdown document titled 'User Activation Checklist'",
                    "provider": "ollama",
                    "model": "qwen2.5:3b"
                })
                assert res.status_code == 200
                data = res.json()
                assert data["artifact"] is not None
                assert data["artifact_type"] == "markdown"
                assert data["artifact_id"] == str(saved_art_id)
                assert data["artifact_title"] == "User Activation Checklist"
            finally:
                app.dependency_overrides.clear()

    def test_csp_and_sandbox_security_preservation(self):
        """Artifact HTML undergoes strict CSP injection and does not allow unsafe script escape."""
        raw_html = "<html><body><h1>Dashboard</h1><script>alert(1)</script></body></html>"
        secured = secure_artifact_html(raw_html)
        assert "Content-Security-Policy" in secured
        assert "default-src 'none'" in secured
        assert "style-src 'unsafe-inline'" in secured


# ===========================================================================
# 2. REAL DATABASE INTEGRATION TESTS
# ===========================================================================

@pytest.fixture(scope="function")
def real_db_session():
    """Provides a real database session from the configured PostgreSQL engine."""
    db = SessionLocal()
    created_sessions = []
    try:
        yield db, created_sessions
    finally:
        for s_id in created_sessions:
            try:
                sess = db.query(models.Session).filter(models.Session.id == s_id).first()
                if sess:
                    db.delete(sess)
                    db.commit()
            except Exception:
                db.rollback()
        db.close()


class TestRealDatabaseArtifactIntegration:
    """Real PostgreSQL database integration tests for Artifact persistence and isolation."""

    def test_real_db_multi_artifact_persistence_retains_all(self, real_db_session):
        """Generating multiple artifacts in a session retains all without overwriting earlier ones."""
        db, cleanup_list = real_db_session

        # 1. Create a real session
        session = crud.create_session(db)
        cleanup_list.append(session.id)

        # 2. Persist artifact 1 (HTML)
        art1 = crud.create_artifact(
            db=db,
            session_id=session.id,
            artifact_type="html",
            title="Artifact 1: Pricing Page",
            content="<html><body>Pricing $10</body></html>"
        )
        assert art1.id is not None

        # 3. Persist artifact 2 (Markdown)
        art2 = crud.create_artifact(
            db=db,
            session_id=session.id,
            artifact_type="markdown",
            title="Artifact 2: Strategy Essay",
            content="# Growth Loops\n\nStep 1: Viral hook"
        )
        assert art2.id is not None
        assert art1.id != art2.id

        # 4. Persist artifact 3 (HTML)
        art3 = crud.create_artifact(
            db=db,
            session_id=session.id,
            artifact_type="html",
            title="Artifact 3: Onboarding Modal",
            content="<html><body>Welcome modal</body></html>"
        )
        assert art3.id is not None

        # 5. Fetch all session artifacts
        all_artifacts = crud.get_session_artifacts(db, session.id)
        assert len(all_artifacts) == 3

        # Confirm all 3 artifacts remain intact with exact contents and timestamps
        titles = [a.title for a in all_artifacts]
        assert "Artifact 3: Onboarding Modal" in titles
        assert "Artifact 2: Strategy Essay" in titles
        assert "Artifact 1: Pricing Page" in titles

        retrieved1 = crud.get_artifact(db, art1.id, session_id=session.id)
        assert retrieved1.content == "<html><body>Pricing $10</body></html>"
        assert retrieved1.artifact_type == "html"

        retrieved2 = crud.get_artifact(db, art2.id, session_id=session.id)
        assert retrieved2.content == "# Growth Loops\n\nStep 1: Viral hook"
        assert retrieved2.artifact_type == "markdown"

    def test_real_db_deduplication_prevents_identical_clones(self, real_db_session):
        """Submitting identical artifact content in the same session reuses the existing record."""
        db, cleanup_list = real_db_session

        session = crud.create_session(db)
        cleanup_list.append(session.id)

        content = "<html><body>Standard template</body></html>"
        art_first = crud.create_artifact(
            db=db,
            session_id=session.id,
            artifact_type="html",
            title="Template",
            content=content
        )

        art_second = crud.create_artifact(
            db=db,
            session_id=session.id,
            artifact_type="html",
            title="Template (Retry)",
            content=content
        )

        # Same record returned, no duplicate created
        assert art_first.id == art_second.id
        all_artifacts = crud.get_session_artifacts(db, session.id)
        assert len(all_artifacts) == 1

    def test_real_db_session_ownership_isolation(self, real_db_session):
        """Session A cannot access or list Session B's artifacts."""
        db, cleanup_list = real_db_session

        session_a = crud.create_session(db)
        session_b = crud.create_session(db)
        cleanup_list.extend([session_a.id, session_b.id])

        art_a = crud.create_artifact(
            db=db,
            session_id=session_a.id,
            artifact_type="html",
            title="Confidential Strategy A",
            content="<html><body>Session A Secret</body></html>"
        )

        art_b = crud.create_artifact(
            db=db,
            session_id=session_b.id,
            artifact_type="markdown",
            title="Confidential Essay B",
            content="# Session B Secret"
        )

        # Listing for Session A must only show Session A
        list_a = crud.get_session_artifacts(db, session_a.id)
        assert len(list_a) == 1
        assert list_a[0].id == art_a.id

        # Listing for Session B must only show Session B
        list_b = crud.get_session_artifacts(db, session_b.id)
        assert len(list_b) == 1
        assert list_b[0].id == art_b.id

        # Querying art_a with session_b must return None (isolated)
        forbidden_query = crud.get_artifact(db, art_a.id, session_id=session_b.id)
        assert forbidden_query is None

        # Querying art_b with session_a must return None (isolated)
        forbidden_query2 = crud.get_artifact(db, art_b.id, session_id=session_a.id)
        assert forbidden_query2 is None

        # Querying art_a with its own session_a succeeds
        allowed_query = crud.get_artifact(db, art_a.id, session_id=session_a.id)
        assert allowed_query is not None
        assert allowed_query.id == art_a.id

    def test_real_db_markdown_document_full_lifecycle(self, real_db_session):
        """A Markdown document request persists as markdown, appears in history, reopens, and downloads as .md."""
        db, cleanup_list = real_db_session
        session = crud.create_session(db)
        cleanup_list.append(session.id)

        md_content = "# User Activation Checklist\n\n## Introduction\nEffective user onboarding is crucial.\n\n- [ ] Step 1: Collect Early Feedback\n- [ ] Step 2: Implement Curiosity Loop"

        # 1. Persist markdown artifact
        art = crud.create_artifact(
            db=db,
            session_id=session.id,
            artifact_type="markdown",
            title="User Activation Checklist",
            content=md_content
        )
        assert art.id is not None
        assert art.artifact_type == "markdown"
        assert art.title == "User Activation Checklist"

        # 2. Verify listing in session history
        history_items = crud.get_session_artifacts(db, session.id)
        assert len(history_items) == 1
        assert history_items[0].id == art.id
        assert history_items[0].artifact_type == "markdown"
        assert history_items[0].title == "User Activation Checklist"

        # 3. Verify reopening from API without LLM
        res_detail = client.get(f"/api/v1/artifacts/{art.id}?session_id={session.id}")
        assert res_detail.status_code == 200
        detail_json = res_detail.json()
        assert detail_json["artifact_type"] == "markdown"
        assert detail_json["title"] == "User Activation Checklist"
        assert detail_json["content"] == md_content

        # 4. Verify downloading as .md
        res_dl = client.get(f"/api/v1/artifacts/{art.id}/download?session_id={session.id}")
        assert res_dl.status_code == 200
        assert "text/markdown" in res_dl.headers["content-type"]
        assert 'attachment; filename="user_activation_checklist.md"' == res_dl.headers["content-disposition"]
        assert res_dl.text == md_content
