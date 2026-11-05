import os, re, csv, io, json
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///vyapaarflow.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    retailer_name = db.Column(db.String(120))
    credit_limit = db.Column(db.Float, default=0)
    credit_used = db.Column(db.Float, default=0)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    pack_size = db.Column(db.String(60), nullable=False)
    case_units = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock_cases = db.Column(db.Integer, nullable=False)
    scheme_type = db.Column(db.String(30), default="none")
    scheme_value = db.Column(db.Float, default=0)
    scheme_text = db.Column(db.String(160), default="")

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    retailer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(30), default="Pending review")
    total = db.Column(db.Float, default=0)
    notes = db.Column(db.Text, default="")
    retailer = db.relationship("User", backref="orders")
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    free_cases = db.Column(db.Integer, default=0)
    product = db.relationship("Product")

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def role_required(role):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                flash("You do not have permission to view that page.", "error")
                return redirect(url_for("home"))
            return fn(*args, **kwargs)
        return wrapper
    return deco

def current_user():
    return db.session.get(User, session.get("user_id"))

def scheme_for(product, qty):
    free = 0
    discount = 0.0
    if product.scheme_type == "buy_get" and qty >= product.scheme_value:
        free = int(qty // product.scheme_value)
    elif product.scheme_type == "slab" and qty >= product.scheme_value:
        discount = 0.03
    subtotal = qty * product.case_units * product.price * (1 - discount)
    return free, round(subtotal, 2), discount

def seed():
    if User.query.first():
        return
    retailer = User(username="retailer", password_hash=generate_password_hash("retail123"), role="retailer",
                    retailer_name="Shree Kirana Stores", credit_limit=50000, credit_used=12500)
    desk = User(username="desk", password_hash=generate_password_hash("desk123"), role="desk")
    db.session.add_all([retailer, desk])
    products = [
        Product(sku="SKU-BS-075", name="Glucose Biscuits", category="Biscuits", pack_size="75 g · case of 96",
                case_units=96, price=8.10, stock_cases=340, scheme_type="buy_get", scheme_value=10,
                scheme_text="Buy 10 cases, get 1 case free"),
        Product(sku="SKU-DT-1KG", name="Detergent Powder", category="Home care", pack_size="1 kg · case of 20",
                case_units=20, price=101.50, stock_cases=85, scheme_type="slab", scheme_value=5,
                scheme_text="3% off on 5+ cases"),
        Product(sku="SKU-TE-250", name="Tea Leaves", category="Beverages", pack_size="250 g · case of 40",
                case_units=40, price=118.00, stock_cases=0, scheme_type="none", scheme_text="No active scheme"),
        Product(sku="SKU-SN-100", name="Salted Snack Mix", category="Snacks", pack_size="100 g · case of 60",
                case_units=60, price=22.00, stock_cases=125, scheme_type="none", scheme_text="No active scheme"),
        Product(sku="SKU-SO-500", name="Dishwash Liquid", category="Home care", pack_size="500 ml · case of 24",
                case_units=24, price=76.00, stock_cases=54, scheme_type="slab", scheme_value=5,
                scheme_text="3% off on 5+ cases"),
    ]
    db.session.add_all(products)
    db.session.commit()

def heuristic_parse(text):
    """Local fallback that processes individual order items."""
    patterns = [
        (r"\b(?:biscuits?|glucose|biskit)\b", "SKU-BS-075"),
        (r"\b(?:washing powder|detergent|surf)\b", "SKU-DT-1KG"),
        (r"\b(?:chai patti|tea|tea leaf)\b", "SKU-TE-250"),
        (r"\b(?:snack|namkeen)\b", "SKU-SN-100"),
        (r"\b(?:dishwash|dish wash)\b", "SKU-SO-500"),
    ]

    lines = []

    for segment in text.split(","):
        t = segment.lower()

        for pat, sku in patterns:
            if not re.search(pat, t):
                continue

            qmatch = re.search(
                r"\b(\d+)\s*(?:peti|case|cases|carton|cartons)\b",
                t
            )
            qty = int(qmatch.group(1)) if qmatch else None

            p = Product.query.filter_by(sku=sku).first()
            if not p:
                continue

            lines.append({
                "sku": sku,
                "product_name": p.name,
                "quantity": qty,
                "original": segment.strip(),
                "confidence": 0.78 if qty is not None else 0.45,
                "alternatives": [],
                "needs_clarification": qty is None,
                "reason": (
                    "Product matched and case quantity extracted."
                    if qty is not None else
                    "Product matched, but case quantity needs clarification."
                )
            })
            break

    return lines

def ai_parse(text):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return heuristic_parse(text), "local_fallback"
    try:
        import requests
        products = [{"sku":p.sku,"name":p.name,"pack":p.pack_size} for p in Product.query.all()]
        prompt = f"""Extract a retailer order from this message. Return ONLY JSON object {{\\"items\\":[{{\\"sku\\":string|null,\\"quantity\\":integer|null,\\"original\\":string,\\"confidence\\":number,\\"alternatives\\":[string],\\"needs_clarification\\":boolean,\\"reason\\":string}}]}}.
Use only these catalogue SKUs: {json.dumps(products)}. Quantities mean cases only if the message clearly says peti/case/carton. If unit is unclear, set needs_clarification true and quantity null. Never invent SKUs. Message: {text}"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
        response = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}],
            "generationConfig":{"responseMimeType":"application/json","temperature":0}}, timeout=18)
        response.raise_for_status()
        raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(raw)
        result = []
        for item in parsed.get("items", []):
            p = Product.query.filter_by(sku=item.get("sku")).first() if item.get("sku") else None
            result.append({**item, "product_name": p.name if p else "Needs product selection"})
        return result, "gemini"
    except Exception:
        return heuristic_parse(text), "local_fallback_after_ai_error"

@app.route("/")
def home():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return redirect(url_for("desk") if session.get("role") == "desk" else url_for("catalogue"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username","").strip()).first()
        if user and check_password_hash(user.password_hash, request.form.get("password","")):
            session.clear()
            session.update(user_id=user.id, role=user.role)
            return redirect(url_for("home"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/catalogue")
@login_required
@role_required("retailer")
def catalogue():
    products = Product.query.order_by(Product.category, Product.name).all()
    user = current_user()
    return render_template("catalogue.html", products=products, user=user)

@app.route("/place-order", methods=["POST"])
@login_required
@role_required("retailer")
def place_order():
    user = current_user()
    try:
        cart = json.loads(request.form.get("cart","[]"))
    except json.JSONDecodeError:
        cart = []
    if not cart:
        flash("Your cart is empty.", "error")
        return redirect(url_for("catalogue"))
    order = Order(retailer_id=user.id, notes="Retailer submitted from catalogue")
    db.session.add(order)
    total = 0
    for row in cart:
        p = db.session.get(Product, int(row.get("product_id",0)))
        qty = int(row.get("quantity",0))
        if not p or qty < 1 or qty > 500 or p.stock_cases < qty:
            db.session.rollback()
            flash("One or more items have invalid quantities or insufficient stock. Please review your cart.", "error")
            return redirect(url_for("catalogue"))
        free, subtotal, discount = scheme_for(p, qty)
        total += subtotal
        order.items.append(OrderItem(product=p, quantity=qty, unit_price=p.price, free_cases=free))
    order.total = round(total,2)
    if user.credit_used + order.total > user.credit_limit:
        order.status = "Credit hold"
    db.session.commit()
    flash(f"Order #{order.id} submitted. Status: {order.status}.", "success")
    return redirect(url_for("catalogue"))

@app.route("/ai-capture", methods=["GET","POST"])
@login_required
@role_required("retailer")
def ai_capture():
    parsed = None
    source = None
    raw_text = ""
    if request.method == "POST":
        raw_text = request.form.get("message","").strip()
        if raw_text:
            parsed, source = ai_parse(raw_text)
    products = Product.query.all()
    return render_template("ai_capture.html", parsed=parsed, source=source, raw_text=raw_text, products=products)

@app.route("/ai-submit", methods=["POST"])
@login_required
@role_required("retailer")
def ai_submit():
    try:
        items = json.loads(request.form.get("items","[]"))
    except json.JSONDecodeError:
        items = []
    cart = []
    for item in items:
        p = Product.query.filter_by(sku=item.get("sku")).first()
        qty = item.get("quantity")
        if p and isinstance(qty,int) and qty > 0 and not item.get("needs_clarification"):
            cart.append({"product_id":p.id,"quantity":qty})
    if not cart:
        flash("No confirmed order lines. Resolve product and quantity questions first.", "error")
        return redirect(url_for("ai_capture"))
    # Reuse the same server-side validation and scheme calculation.
    order = Order(retailer_id=current_user().id, total=0.0, notes="AI-assisted text capture; retailer reviewed before submission")
    db.session.add(order)
    for row in cart:
        p = db.session.get(Product,row["product_id"])
        qty = row["quantity"]
        if p.stock_cases < qty:
            db.session.rollback()
            flash(f"Insufficient stock for {p.name}. No order was placed.", "error")
            return redirect(url_for("ai_capture"))
        free, subtotal, discount = scheme_for(p,qty)
        order.items.append(OrderItem(product=p,quantity=qty,unit_price=p.price,free_cases=free))
        order.total += subtotal
    db.session.commit()
    flash(f"Confirmed AI-assisted order #{order.id} submitted for desk review.", "success")
    return redirect(url_for("catalogue"))

@app.route("/desk")
@login_required
@role_required("desk")
def desk():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("desk.html", orders=orders)

@app.route("/desk/order/<int:order_id>", methods=["POST"])
@login_required
@role_required("desk")
def update_order(order_id):
    order = db.session.get(Order,order_id)
    if not order:
        flash("Order not found.", "error")
    else:
        status = request.form.get("status")
        if status in ["Pending review","Approved","Credit hold","Rejected"]:
            order.status = status
            db.session.commit()
            flash(f"Order #{order.id} updated.", "success")
    return redirect(url_for("desk"))

@app.route("/export.csv")
@login_required
@role_required("desk")
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Order ID","Date UTC","Retailer","SKU","Product","Quantity Cases","Free Cases","Unit Price INR","Line Total INR","Status"])
    for order in Order.query.order_by(Order.created_at.asc()).all():
        for item in order.items:
            free, subtotal, discount = scheme_for(item.product,item.quantity)
            writer.writerow([order.id,order.created_at.isoformat(),order.retailer.retailer_name,item.product.sku,
                             item.product.name,item.quantity,item.free_cases,item.unit_price,subtotal,order.status])
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=vyapaarflow_tally_export.csv"
    return response

@app.route("/health")
def health():
    return jsonify(status="ok", app="VyapaarFlow")

with app.app_context():
    db.create_all()
    seed()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG","false").lower()=="true", host="0.0.0.0", port=int(os.getenv("PORT",5000)))
