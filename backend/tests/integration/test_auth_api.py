async def test_health_check(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_register_login_me_flow(client):
    register_response = await client.post(
        "/auth/register", json={"email": "flow@example.com", "password": "s3cret123"}
    )
    assert register_response.status_code == 201
    body = register_response.json()
    assert body["email"] == "flow@example.com"
    assert body["role"] == "viewer"

    login_response = await client.post(
        "/auth/login", json={"email": "flow@example.com", "password": "s3cret123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "flow@example.com"


async def test_register_duplicate_email_returns_409(client):
    payload = {"email": "dup@example.com", "password": "s3cret123"}
    await client.post("/auth/register", json=payload)

    response = await client.post("/auth/register", json=payload)

    assert response.status_code == 409


async def test_login_wrong_password_returns_401(client):
    await client.post("/auth/register", json={"email": "wrong@example.com", "password": "right-pass"})

    response = await client.post(
        "/auth/login", json={"email": "wrong@example.com", "password": "wrong-pass"}
    )

    assert response.status_code == 401


async def test_me_without_token_returns_401(client):
    response = await client.get("/auth/me")

    assert response.status_code == 401
