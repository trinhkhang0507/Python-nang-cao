from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['DEBUG'] = True
app.secret_key = 'your_secret_key' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:123456@localhost/banphim'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Khởi tạo SQLAlchemy
db = SQLAlchemy(app)

# Định nghĩa model cho người dùng
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
 
# Định nghĩa model cho sản phẩm
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(50), nullable=False) 


# Định nghĩa model cho đơn hàng
class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    order_date = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Quan hệ với OrderItem
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)


# Tạo bảng trong database nếu chưa tồn tại
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    products = Product.query.all()  # Lấy tất cả sản phẩm từ cơ sở dữ liệu
    return render_template('index.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash("Username đã tồn tại!", 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Đăng ký thành công!", 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash("Đăng nhập thành công!", 'success')
            return redirect(url_for('home'))
        else:
            flash("Tên đăng nhập hoặc mật khẩu không đúng!", 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash("Đăng xuất thành công!", 'info')
    return redirect(url_for('login'))

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []

    product = Product.query.get(product_id)

    if not product:
        flash("Sản phẩm không tồn tại.", 'danger')
        return redirect(url_for('home'))

    found = False
    for item in session['cart']:
        if item['id'] == product.id:
            item['quantity'] += 1
            found = True
            break

    if not found:
        session['cart'].append({
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'image_url': product.image_url,
            'quantity': 1
        })

    flash(f"{product.name} đã được thêm vào giỏ hàng.", 'success')
    return redirect(url_for('home'))

@app.route('/cart')
def cart():
    # Kiểm tra nếu session giỏ hàng trống
    if 'cart' not in session or not session['cart']:
        flash('Giỏ hàng của bạn đang trống.', 'info')
        return redirect(url_for('home'))

    # Tính tổng giá
    total_price = sum(float(item['price'] * item['quantity']) for item in session['cart'])
    return render_template('cart.html', cart=session['cart'], total_price=total_price)

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['id'] != product_id]
        flash("Sản phẩm đã được xóa khỏi giỏ hàng.", 'success')

    return redirect(url_for('cart'))

@app.route('/checkout')
def checkout():
    # Sample cart data; replace with data from your database
    cart = session.get('cart', [])
    total_price = sum(item['price'] * item['quantity'] for item in cart)
    return render_template('checkout.html', cart=cart, total_price=total_price)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    # Get form data
    name = request.form['name']
    address = request.form['address']
    phone = request.form['phone']
    payment_method = request.form['payment_method']
    
    # Calculate total price
    cart = session.get('cart', [])
    total_price = sum(item['price'] * item['quantity'] for item in cart)

    # Create Order object and save it
    new_order = Order(
        user_id=session.get('user_id'),  # Optional, if user is logged in
        name=name,
        address=address,
        phone=phone,
        payment_method=payment_method,
        total_price=total_price
    )
    db.session.add(new_order)
    db.session.flush()  # Flush to get order ID for order items

    # Create OrderItem objects and associate them with the order
    for item in cart:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item['id'],
            product_name=item['name'],
            price=item['price'],
            quantity=item['quantity']
        )
        db.session.add(order_item)

    # Commit all changes to the database
    db.session.commit()

    # Clear the cart after successful payment
    session['cart'] = []
    flash('Thanh toán thành công! Đơn hàng của bạn sẽ được xử lý.', 'success')
    return redirect(url_for('home'))

@app.route('/category/<category_name>')
def category(category_name):
    products = Product.query.filter_by(category=category_name).all()
    return render_template('category.html', products=products, category_name=category_name)


if __name__ == '__main__':
    app.run(debug=True)
