from tests.helpers import PASSWORD, create_user


async def test_register(client):
    response = await client.post("/auth/register", json={
        "username": "anna",
        "email": "Anna@Example.com",
        "password": PASSWORD,
    })

    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "customer"
    assert data["email"] == "anna@example.com"  # почта приводится к нижнему регистру
    assert "password" not in data
    assert "hashed_password" not in data


async def test_register_cannot_choose_role(client):
    response = await client.post("/auth/register", json={
        "username": "sneaky",
        "email": "sneaky@example.com",
        "password": PASSWORD,
        "role": "admin",
    })

    assert response.status_code == 201
    assert response.json()["role"] == "customer"


async def test_register_duplicate_email(client):
    body = {"username": "anna", "email": "anna@example.com", "password": PASSWORD}

    first = await client.post("/auth/register", json=body)
    assert first.status_code == 201

    body["username"] = "anna2"
    second = await client.post("/auth/register", json=body)
    assert second.status_code == 409


async def test_login_and_me(client):
    await create_user("anna")

    response = await client.post("/auth/login", data={"username": "anna", "password": PASSWORD})
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "anna"


async def test_login_wrong_password(client):
    await create_user("anna")

    response = await client.post("/auth/login", data={"username": "anna", "password": "wrong-password"})

    assert response.status_code == 401


async def test_login_blocked_after_five_failures(client):
    await create_user("anna")
    wrong = {"username": "anna", "password": "wrong-password"}


    for _ in range(5):
        response = await client.post("/auth/login", data=wrong)
        assert response.status_code == 401

    # шестая попытка заблокирована, даже если пароль теперь верный
    right = {"username": "anna", "password": PASSWORD}
    response = await client.post("/auth/login", data=right)
    assert response.status_code == 429