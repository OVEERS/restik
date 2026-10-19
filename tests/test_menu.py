from tests.helpers import auth_headers, create_dish


async def test_menu_shows_only_available_dishes(client):
    await create_dish("Борщ")
    await create_dish("Окрошка", available=False)

    response = await client.get("/menu")

    assert response.status_code == 200
    categories = response.json()
    assert len(categories) == 1
    assert [dish["name"] for dish in categories[0]["items"]] == ["Борщ"]


async def test_admin_can_create_category_and_dish(client, admin):
    headers = auth_headers(admin)

    response = await client.post("/menu/categories", json={"name": "Супы"}, headers=headers)
    assert response.status_code == 201
    category_id = response.json()["id"]

    response = await client.post("/menu/items", headers=headers, json={
        "category_id": category_id,
        "name": "Борщ",
        "price": "350.00",
    })
    assert response.status_code == 201
    assert response.json()["price"] == "350.00"


async def test_customer_cannot_create_category(client, customer):

    response = await client.post(
        "/menu/categories", json={"name": "Супы"}, headers=auth_headers(customer)
    )

    assert response.status_code == 403


async def test_anonymous_cannot_create_category(client):
    response = await client.post("/menu/categories", json={"name": "Супы"})

    assert response.status_code == 401