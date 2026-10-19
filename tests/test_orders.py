from tests.helpers import auth_headers, create_dish, create_user


async def place_order(client, user, dish) -> int:
    """Создаёт заказ из одного блюда и возвращает его id."""
    response = await client.post("/orders", headers=auth_headers(user), json={
        "items": [{"menu_item_id": dish.id, "quantity": 1}],
    })
    assert response.status_code == 201
    return response.json()["id"]


async def test_total_is_calculated_on_server(client, customer):
    borsch = await create_dish("Борщ", "350.00")
    compote = await create_dish("Компот", "80.50")

    response = await client.post("/orders", headers=auth_headers(customer), json={
        "items": [
            {"menu_item_id": borsch.id, "quantity": 2},
            {"menu_item_id": compote.id, "quantity": 1},
        ],
    })

    assert response.status_code == 201
    order = response.json()
    assert order["total"] == "780.50"
    assert order["status"] == "new"
    assert len(order["items"]) == 2


async def test_price_from_client_is_ignored(client, customer):
    borsch = await create_dish("Борщ", "350.00")

    response = await client.post("/orders", headers=auth_headers(customer), json={
        "items": [{"menu_item_id": borsch.id, "quantity": 1, "price": "0.01"}],
    })

    assert response.status_code == 201
    assert response.json()["total"] == "350.00"


async def test_order_keeps_price_from_moment_of_purchase(client, admin, customer):
    borsch = await create_dish("Борщ", "350.00")
    order_id = await place_order(client, customer, borsch)

    # после заказа цена в меню выросла
    response = await client.patch(
        f"/menu/items/{borsch.id}", headers=auth_headers(admin), json={"price": "400.00"}
    )
    assert response.status_code == 200

    response = await client.get(f"/orders/{order_id}", headers=auth_headers(customer))
    order = response.json()
    assert order["total"] == "350.00"
    assert order["items"][0]["unit_price"] == "350.00"


async def test_unavailable_dish_rejects_whole_order(client, customer):
    borsch = await create_dish("Борщ")
    sold_out = await create_dish("Окрошка", available=False)

    response = await client.post("/orders", headers=auth_headers(customer), json={
        "items": [
            {"menu_item_id": borsch.id, "quantity": 1},
            {"menu_item_id": sold_out.id, "quantity": 1},
        ],
    })
    assert response.status_code == 400

    # заказ не создался вообще, даже частично
    response = await client.get("/orders", headers=auth_headers(customer))
    assert response.json() == []


async def test_status_flow(client, admin, customer):
    order_id = await place_order(client, customer, await create_dish())
    url = f"/orders/{order_id}/status"
    headers = auth_headers(admin)

    # из "new" сразу в "served" нельзя
    response = await client.patch(url, headers=headers, json={"status": "served"})
    assert response.status_code == 400

    for status in ["cooking", "ready", "served", "paid"]:
        response = await client.patch(url, headers=headers, json={"status": status})
        assert response.status_code == 200
        assert response.json()["status"] == status

    # после оплаты заказ уже не изменить
    response = await client.patch(url, headers=headers, json={"status": "cancelled"})
    assert response.status_code == 400


async def test_customer_sees_only_own_orders(client, customer):
    other = await create_user("other")
    dish = await create_dish()
    other_order_id = await place_order(client, other, dish)
    my_order_id = await place_order(client, customer, dish)

    response = await client.get("/orders", headers=auth_headers(customer))
    assert [order["id"] for order in response.json()] == [my_order_id]

    # чужой заказ выглядит так, будто его нет
    response = await client.get(f"/orders/{other_order_id}", headers=auth_headers(customer))
    assert response.status_code == 404


async def test_customer_can_cancel_new_order(client, customer):
    order_id = await place_order(client, customer, await create_dish())

    response = await client.patch(
        f"/orders/{order_id}/status", headers=auth_headers(customer), json={"status": "cancelled"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


async def test_customer_cannot_cancel_order_in_cooking(client, admin, customer):
    order_id = await place_order(client, customer, await create_dish())
    url = f"/orders/{order_id}/status"

    # повар уже взял заказ в работу
    await client.patch(url, headers=auth_headers(admin), json={"status": "cooking"})

    response = await client.patch(url, headers=auth_headers(customer), json={"status": "cancelled"})
    assert response.status_code == 403