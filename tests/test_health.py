async def test_health_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_503_when_db_fails(client_db_fail):
    response = await client_db_fail.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert "detail" in data
