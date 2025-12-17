import json
import pytest

from app import app, compute_and_cache_global_leaderboard, db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_compute_and_cache_runs():
    # Should run without raising and return True/False
    result = compute_and_cache_global_leaderboard()
    assert result in (True, False)


def test_api_leaderboard_global_logged_in(client):
    # Create a session with a user_id (may or may not exist in DB)
    with client.session_transaction() as sess:
        sess['user_id'] = 1

    resp = client.get('/api/leaderboard/global?limit=5')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'leaderboard' in data
    assert 'total' in data


def test_api_league_leaderboard_cached_or_live(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1

    # Use league id 1 for smoke test
    resp = client.get('/api/leaderboard/league/1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'leaderboard' in data
    assert isinstance(data['leaderboard'], list)
