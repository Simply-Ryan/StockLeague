import os
import sys
import tempfile
import json
import pytest

# Ensure project root is on sys.path for imports when running tests directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db_manager import DatabaseManager

# Import the Flask app
import app as flask_app


def setup_test_db():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, 'test.db')
    db = DatabaseManager(db_path=db_path)
    # Ensure schema is initialized (call again to be robust in test env)
    try:
        db.init_db()
    except Exception:
        pass
    # Verify tables exist; create again if missing (robustness for test env)
    try:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        conn.close()
        if 'leagues' not in tables:
            db.init_db()
    except Exception as e:
        print('setup_test_db: exception when checking tables:', e)
    # Debug info
    try:
        print('setup_test_db: db_path=', db.db_path)
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print('setup_test_db: tables after init:', [r[0] for r in c.fetchall()])
        conn.close()
    except Exception as e:
        print('setup_test_db: exception during debug table listing:', e)
    except Exception:
        pass
    return db, db_path


def teardown_test_db(db_path):
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture()
def test_client():
    db, db_path = setup_test_db()

    # Create some users and a league
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, hash, email, cash) VALUES (?, ?, ?, ?)", ('admin', 'x', 'a@example.com', 10000))
    admin_id = cursor.lastrowid
    cursor.execute("INSERT INTO users (username, hash, email, cash) VALUES (?, ?, ?, ?)", ('member', 'x', 'm@example.com', 10000))
    member_id = cursor.lastrowid
    cursor.execute("INSERT INTO leagues (name, creator_id, league_type, starting_cash) VALUES (?, ?, ?, ?)", ('Test League', admin_id, 'private', 10000))
    league_id = cursor.lastrowid
    # Add league members
    cursor.execute("INSERT INTO league_members (league_id, user_id, is_admin) VALUES (?, ?, ?)", (league_id, admin_id, 1))
    cursor.execute("INSERT INTO league_members (league_id, user_id, is_admin) VALUES (?, ?, ?)", (league_id, member_id, 0))
    conn.commit()
    conn.close()

    # Monkeypatch DatabaseManager in app to return our test db
    flask_app.DatabaseManager = lambda *args, **kwargs: db
    flask_app.app.config['TESTING'] = True
    client = flask_app.app.test_client()

    yield client, db, league_id, admin_id, member_id

    # Teardown
    teardown_test_db(db_path)


def test_db_helpers():
    # Basic test for DB helpers
    db, db_path = setup_test_db()
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO users (username, hash) VALUES (?, ?)", ('u1', 'x'))
    u1 = c.lastrowid
    c.execute("INSERT INTO leagues (name, creator_id) VALUES (?, ?)", ('L', u1))
    lid = c.lastrowid
    c.execute("INSERT INTO league_members (league_id, user_id, is_admin) VALUES (?, ?, ?)", (lid, u1, 1))
    conn.commit()
    conn.close()

    assert db.is_user_league_admin(lid, u1) is True
    db.set_league_member_admin(lid, u1, is_admin=False)
    assert db.is_user_league_admin(lid, u1) is False

    # Test moderation
    db.set_league_moderation(lid, u1, is_muted=True, muted_until=None, is_banned=False)
    mod = db.get_league_moderation(lid, u1)
    assert mod is not None
    assert mod['is_muted'] == 1

    teardown_test_db(db_path)


def test_api_admin_actions(test_client):
    client, db, league_id, admin_id, member_id = test_client

    # Set session to admin
    with client.session_transaction() as sess:
        sess['user_id'] = admin_id
        sess['username'] = 'admin'

    # Promote member to admin
    resp = client.post(f'/leagues/{league_id}/admin/set_admin', json={'target_user_id': member_id, 'is_admin': 1})
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data.get('ok') is True
    members = db.get_league_members(league_id)
    member = next((m for m in members if m['id'] == member_id), None)
    assert member is not None and member['is_admin'] == 1

    # Mute member
    resp = client.post(f'/leagues/{league_id}/admin/mute', json={'target_user_id': member_id, 'minutes': 5})
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data.get('ok') is True
    mod = db.get_league_moderation(league_id, member_id)
    assert mod is not None and mod['is_muted'] == 1

    # Kick member
    resp = client.post(f'/leagues/{league_id}/admin/kick', json={'target_user_id': member_id})
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data.get('ok') is True
    members = db.get_league_members(league_id)
    assert all(m['id'] != member_id for m in members)
