from flask import Flask, jsonify, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import fields, ValidationError, pre_load, INCLUDE
from datetime import datetime, timedelta


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:jeweller-zipper-reck2@localhost/e_commerce_mp'
db = SQLAlchemy(app)
ma = Marshmallow(app)
migrate = Migrate(app, db)


class CustomerSchema(ma.Schema):
    name = fields.String(required=True)
    email = fields.String(required=True)
    phone = fields.String(required=True)

    class Meta:
        fields = ('name', 'email', 'phone', "id")


customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)


class CustomerAccountSchema(ma.Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)
    customer_id = fields.Int(required=True)

    class Meta:
        fields = ('username', 'password', 'customer_id', 'id')


customer_account_schema = CustomerAccountSchema()
customer_accounts_schema = CustomerAccountSchema(many=True)


class ProductSchema(ma.Schema):
    name = fields.String(required=True)
    price = fields.Float(required=True)
    stock = fields.Int(required=True)

    class Meta:
        fields = ('id', 'name', 'price', 'stock')


product_schema = ProductSchema()
products_schema = ProductSchema(many=True)


class OrderSchema(ma.Schema):
    id = fields.Int(dump_only=True)
    date = fields.Date(required=True)
    status = fields.String()
    expected_delivery_date = fields.Date()
    customer_id = fields.Int(required=True)
    product_ids = fields.List(fields.Int(), required=True)
    products = fields.Nested(ProductSchema(), many=True, dump_only=True)

    class Meta:
        unknown = INCLUDE  # This allows the schema to accept unknown fields and include them in the loaded data
        fields = ('id', 'date', 'status', 'expected_delivery_date', 'customer_id', 'product_ids', 'products')

    @pre_load
    def process_product_input(self, data, **kwargs):
        # Process 'product_ids' into 'products' for internal handling
        if 'product_ids' in data:
            data['products'] = [{'id': pid} for pid in data['product_ids']]
        return data


order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)


class Customer(db.Model):
    __tablename__ = 'Customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25), nullable=False)
    email = db.Column(db.String(320))
    phone = db.Column(db.String(15))
    orders = db.relationship('Order', backref='customer')  # results in a list of order #s


# many-to-many relationship
order_products = db.Table('OrderProducts',
    db.Column('order_id', db.Integer, db.ForeignKey('Orders.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('Products.id'), primary_key=True)
    )


class Order(db.Model):
    __tablename__ = 'Orders'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.id'))
    products = db.relationship('Product', secondary=order_products, back_populates="orders", lazy='dynamic')
    status = db.Column(db.String(50), default='Pending')
    delivery_date = db.Column(db.Date, default=None)


class CustomerAccount(db.Model):
    __tablename__ = 'CustomerAccounts'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.id'))
    customer = db.relationship('Customer', backref='customer_account', uselist=False)


class Product(db.Model):
    __tablename__ = 'Products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    orders = db.relationship('Order', secondary=order_products, back_populates="products", lazy='dynamic')


@app.route('/')
def home():
    return "Welcome to the E-Commerce Store!"


@app.route('/customers', methods=['GET'])
def get_customers():
    customers = Customer.query.all()
    return customers_schema.jsonify(customers)


@app.route('/customers/<int:id>', methods=['GET'])
def get_customer(id):
    customer = Customer.query.get_or_404(id)
    return customer_schema.jsonify(customer)


@app.route('/customers', methods=['POST'])
def add_customer():
    try:
        # Validate and deserialize input
        customer = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    new_customer = Customer(name=customer['name'], email=customer['email'], phone=customer['phone'])
    db.session.add(new_customer)
    db.session.commit()
    return jsonify({'message': 'New customer added successfully!'}), 201


@app.route('/customers/<int:id>', methods=['PUT'])
def update_customer(id):
    customer = Customer.query.get_or_404(id)
    try:
        # Validate and deserialize input
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    customer.name = customer_data['name']
    customer.email = customer_data['email']
    customer.phone = customer_data['phone']

    db.session.commit()
    return jsonify({'message': 'Customer updated successfully!'}), 200


@app.route('/customers/<int:id>', methods=['DELETE'])
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    return jsonify({'message': 'Customer removed successfully.'}), 200


# Customer Account Routes
# Create a new customer account
@app.route('/customer_accounts', methods=['POST'])
def add_customer_account():
    try:
        # Validate and deserialize input
        customer_account = customer_account_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    new_customer_account = CustomerAccount(username=customer_account['username'], password=customer_account['password'], customer_id=customer_account['customer_id'])
    db.session.add(new_customer_account)
    db.session.commit()
    return jsonify({'message': 'New customer account added successfully!'}), 201


# Get all customer accounts
@app.route('/customer_accounts', methods=['GET'])
def get_customer_accounts():
    customer_accounts = CustomerAccount.query.all()
    return customer_accounts_schema.jsonify(customer_accounts)


# Get a single customer account
@app.route('/customer_accounts/<int:id>', methods=['GET'])
def get_customer_account(id):
    customer_account = CustomerAccount.query.get_or_404(id)
    return customer_account_schema.jsonify(customer_account)


# Update a customer account
@app.route('/customer_accounts/<int:id>', methods=['PUT'])
def update_customer_account(id):
    customer_account = CustomerAccount.query.get_or_404(id)
    try:
        customer_account_data = customer_account_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    customer_account.username = customer_account_data['username']
    customer_account.password = customer_account_data['password']
    customer_account.customer_id = customer_account_data['customer_id']

    db.session.commit()
    return jsonify({'message': 'Customer account updated successfully!'}), 200


# Delete a customer account
@app.route('/customer_accounts/<int:id>', methods=['DELETE'])
def delete_customer_account(id):
    customer_account = CustomerAccount.query.get_or_404(id)
    db.session.delete(customer_account)
    db.session.commit()
    return jsonify({'message': 'Customer account removed successfully.'}), 200


# Customer Product Routs
# Create a new Product
@app.route('/products', methods=['POST'])
def add_product():
    try:
        product = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    new_product = Product(name=product['name'], price=product['price'], stock=product['stock'])
    db.session.add(new_product)
    db.session.commit()
    return jsonify({'message': 'New product account added successfully!'}), 201


# Get all Products
@app.route('/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return products_schema.jsonify(products)


# Get a single Product
@app.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    product = Product.query.get_or_404(id)
    return product_schema.jsonify(product)


# Update a Product
@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    product = Product.query.get_or_404(id)
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    product.name = product_data['name']
    product.price = product_data['price']
    product.stock = product_data['stock']

    db.session.commit()
    return jsonify({'message': 'Product updated successfully!'}), 200


# Delete a Product
@app.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({'message': 'Product removed successfully.'}), 200


@app.route('/product_stock/<int:id>', methods=['GET'])
def get_product_stock(id):
    product = Product.query.get_or_404(id)
    return jsonify({'stock': product.stock})


@app.route('/product_stock/<int:id>', methods=['PUT'])
def update_stock(id):
    product = Product.query.get_or_404(id)
    new_stock = request.json['stock']
    product.stock = new_stock
    db.session.commit()
    return jsonify({'message': 'Stock updated successfully!'}), 200


@app.route('/restock', methods=['PUT'])
def restock_product():
    products = Product.query.all()
    for product in products:
        if product.stock < 10:
            product.stock += 50
    db.session.commit()
    return jsonify({'message': 'Stock replenished successfully!'}), 200


# Order Processing Requests
# Create a new Order
@app.route('/orders', methods=['POST'])
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    products = Product.query.filter(Product.id.in_(order_data['product_ids'])).all()

    if len(products) != len(order_data['product_ids']):
        return jsonify({'message': 'One or more products not found.'}), 404

    new_order = Order(date=order_data['date'], customer_id=order_data['customer_id'], status='Processing', delivery_date=datetime.now() + timedelta(days=7))
    new_order.products = products
    db.session.add(new_order)
    db.session.commit()

    return jsonify({'message': 'New order added successfully!'}), 201


@app.route('/update_status/<int:id>', methods=['PUT'])
def update_status(id):
    order = Order.query.get_or_404(id)
    new_status = request.json['status']
    order.status = new_status
    db.session.commit()
    return jsonify({'message': 'Status updated successfully!'}), 200


@app.route('/order_details/<int:id>', methods=['GET'])
def view_order_details(id):
    order = Order.query.get_or_404(id)
    return order_schema.jsonify(order)


@app.route('/view_status/<int:id>', methods=['GET'])
def view_order_status(id):
    order = Order.query.get_or_404(id)
    return jsonify({'status': order.status}, {'expected_delivery_date': order.delivery_date})


@app.route('/order_history/<int:customer_id>', methods=['GET'])
def order_history(customer_id):
    customer = Order.query.filter_by(customer_id=customer_id).all()
    return orders_schema.dump(customer)


@app.route('/cancel_order/<int:id>', methods=['DELETE'])
def cancel_order(id):
    order = Order.query.get_or_404(id)
    if order.status != 'Shipped' and order.status != 'Complete':
        db.session.delete(order)
        db.session.commit()
        return jsonify({'message': 'Order cancelled successfully.'}), 200
    else:
        return jsonify({'message': 'Order unable to be cancelled. It is already shipped or has been completed.'}), 200


if __name__ == '__main__':
    app.run(debug=True)
