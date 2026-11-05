import json
import pytest
from app import app, db, User, Product, scheme_for

@pytest.fixture()
def client(tmp_path):
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///"+str(tmp_path/"test.db"),
                      WTF_CSRF_ENABLED=False, SECRET_KEY="test")
    with app.app_context():
        db.drop_all()
        db.create_all()
        from app import seed
        seed()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

def login(client, username, password):
    return client.post("/login", data={"username":username,"password":password}, follow_redirects=True)

def test_health(client):
    assert client.get("/health").json["status"] == "ok"

def test_retailer_login_and_catalogue(client):
    response=login(client,"retailer","retail123")
    assert response.status_code == 200
    assert b"Products for your store" in response.data

def test_scheme_buy_get(client):
    with app.app_context():
        p=Product.query.filter_by(sku="SKU-BS-075").first()
        free,total,discount=scheme_for(p,20)
        assert free == 2
        assert total == 15552.0
        assert discount == 0

def test_order_placement(client):
    login(client,"retailer","retail123")
    with app.app_context():
        pid=Product.query.filter_by(sku="SKU-BS-075").first().id
    response=client.post("/place-order",data={"cart":json.dumps([{"product_id":pid,"quantity":10}])},follow_redirects=True)
    assert b"Order #" in response.data

def test_role_protection(client):
    login(client,"retailer","retail123")
    response=client.get("/desk",follow_redirects=True)
    assert b"Products for your store" in response.data
