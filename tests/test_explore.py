import pytest
from app import app


def test_explore_page_renders():
    client = app.test_client()
    resp = client.get('/explore')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Check for core market sections
    assert 'Market Movers' in html
    assert 'Popular Stocks' in html
    assert 'Market Summary' in html