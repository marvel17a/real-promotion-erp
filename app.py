from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response,session,flash,abort
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import date,timedelta,datetime
import os
from openpyxl.styles import Font, Alignment

# --- NEW IMPORTS ---
import json
import locale
import calendar
from dotenv import load_dotenv # For loading environment variables
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils
# --- END NEW IMPORTS ---

from fpdf import FPDF
import csv
from io import StringIO
from decimal import Decimal
import datetime
import io 
from flask import send_file
import uuid
from werkzeug.utils import secure_filename
import MySQLdb 
from flask_mysqldb import MySQL
from flask import Flask,jsonify,request

from flask import Response

import openpyxl
from io import BytesIO

# --- LOAD ENVIRONMENT VARIABLES ---
# This will load the .env file you just created
load_dotenv()

app = Flask(__name__)

# --- MODIFIED: Load Secret Key from Environment ---
app.secret_key = os.environ.get("SECRET_KEY", "a_very_bad_default_secret")

# --- MODIFIED: Load Database Config from Environment ---
# This will read from your .env file locally, and from
# Render's dashboard when deployed.
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# NOTE: We have removed the complex SSL configuration
# to make it compatible with more free database hosts.

mysql = MySQL(app)

# --- NEW: Cloudinary Configuration ---
# This will read the keys from your .env file
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)
app.logger.info(f"Cloudinary configured with cloud name: {os.environ.get('CLOUDINARY_CLOUD_NAME')}")


# --- FILE UPLOAD LOGIC ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_DOC_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Check if uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#==============================================
# --- ALL YOUR ROUTES ---
# (Copied from your file, with modifications
#  only to routes that save files)
#==============================================

# Helper function
# This "context processor" injects the cloudinary_url function into all templates
@app.context_processor
def inject_cloudinary_url():
    """Make cloudinary_url function available in all templates."""
    # This is the correct function from the cloudinary library
    return dict(cloudinary_url=cloudinary.utils.cloudinary_url)

@app.route("/")
def index1():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        cursor.close()

        if user:
            session["loggedin"] = True
            session["username"] = user["username"]
            return redirect(url_for("inventory"))
        else:
            flash("Invalid username or password", "error")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route('/index')
def index():
    return render_template('index.html')

# ADD THIS NEW, FIXED FUNCTION
@app.route("/dashboard")
def dashboard():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    report_date = date.today().isoformat()
    summary_data = {
        "total_sales": 0,
        "total_expenses": 0,
        "net_cash_flow": 0
    }

    try:
        # We must use the lowercase table names for Linux
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Total Sales
        db_cursor.execute("""
            SELECT SUM(total_amount) AS total_sales 
            FROM evening_settle 
            WHERE date = %s
        """, (report_date,))
        sales_result = db_cursor.fetchone()
        summary_data["total_sales"] = sales_result["total_sales"] or 0

        # Total Expenses
        db_cursor.execute("""
            SELECT SUM(amount) AS total_expenses 
            FROM expenses 
            WHERE expense_date = %s
        """, (report_date,))
        expenses_result = db_cursor.fetchone()
        summary_data["total_expenses"] = expenses_result["total_expenses"] or 0

        # Net Cash Flow
        summary_data["net_cash_flow"] = (
            summary_data["total_sales"] - summary_data["total_expenses"]
        )

        db_cursor.close()

    except Exception as e:
        flash(f"Error loading dashboard: {e}", "danger")

    report_date_obj = date.fromisoformat(report_date)
    report_date_str = report_date_obj.strftime('%d %B, %Y')

    #
    # THE FIX IS HERE:
    # We use **summary_data to unpack the dictionary into separate variables
    # for the template.
    #
    return render_template("dashboard.html",
        report_date=report_date,
        report_date_str=report_date_str,
        **summary_data
    )


#==============================================ADMIN PAGE=======================================
@app.context_processor
def inject_kpis():
    db_cursor = None
    try:
        if 'mysql' not in app.extensions:
            return dict(kpis={"sales_today": 0, "supplier_dues": 0, "mtd_expenses": 0, "stock_value": 0, "total_employees": 0, "total_products": 0})
            
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        db_cursor.execute("SELECT SUM(total_amount) as total FROM evening_settle WHERE date = CURDATE()")
        sales_today = db_cursor.fetchone()['total'] or 0

        db_cursor.execute("SELECT SUM(current_due) as total FROM suppliers")
        supplier_dues = db_cursor.fetchone()['total'] or 0
        
        db_cursor.execute("SELECT SUM(amount) as total FROM expenses WHERE MONTH(expense_date) = MONTH(CURDATE()) AND YEAR(expense_date) = YEAR(CURDATE())")
        mtd_expenses = db_cursor.fetchone()['total'] or 0

        db_cursor.execute("SELECT SUM(stock * purchase_price) as total FROM products")
        stock_value = db_cursor.fetchone()['total'] or 0
        
        db_cursor.execute("SELECT COUNT(id) as total FROM employees")
        total_employees = db_cursor.fetchone()['total'] or 0
        
        db_cursor.execute("SELECT COUNT(id) as total FROM products")
        total_products = db_cursor.fetchone()['total'] or 0

        kpis = {
            "sales_today": float(sales_today),
            "supplier_dues": float(supplier_dues),
            "mtd_expenses": float(mtd_expenses),
            "stock_value": float(stock_value),
            "total_employees": total_employees,
            "total_products": total_products
        }
        
        return dict(kpis=kpis)
    except Exception as e:
        app.logger.error(f"CRITICAL ERROR in context processor: {e}")
        return dict(kpis={"sales_today": 0, "supplier_dues": 0, "mtd_expenses": 0, "stock_value": 0, "total_employees": 0, "total_products": 0})
    finally:
        if db_cursor:
            db_cursor.close()

# --- API ROUTE FOR DASHBOARD CHARTS ---
@app.route('/api/dashboard-charts')
def api_dashboard_charts():
    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        db_cursor.execute("""
            SELECT 
                DATE(date) as sale_date, 
                SUM(total_amount) as total_sales
            FROM evening_settle
            WHERE date >= CURDATE() - INTERVAL 7 DAY
            GROUP BY DATE(date)
            ORDER BY sale_date ASC;
        """)
        sales_data = db_cursor.fetchall()
        
        db_cursor.execute("""
            SELECT 
                DATE(expense_date) as exp_date, 
                SUM(amount) as total_expenses
            FROM expenses
            WHERE expense_date >= CURDATE() - INTERVAL 7 DAY
            GROUP BY DATE(expense_date)
            ORDER BY exp_date ASC;
        """)
        expense_data = db_cursor.fetchall()

        sales_labels = [row['sale_date'].strftime('%b %d') for row in sales_data]
        sales_values = [float(row['total_sales']) for row in sales_data]
        
        expense_labels = [row['exp_date'].strftime('%b %d') for row in expense_data]
        expense_values = [float(row['total_expenses']) for row in expense_data]

        db_cursor.close()
        return jsonify({
            "sales": {"labels": sales_labels, "values": sales_values},
            "expenses": {"labels": expense_labels, "values": expense_values}
        })
    except Exception as e:
        app.logger.error(f"Chart API Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db_cursor:
            db_cursor.close()

@app.route('/admin_master')
def admin_master():
    return render_template('admin_master.html')

@app.route('/dash')
def dash():
    return render_template('dash.html')

# =====================================================================
# SUPPLIER MANAGEMENT ROUTES
# =====================================================================

@app.route('/suppliers')
def suppliers():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM suppliers ORDER BY name")
    all_suppliers = cur.fetchall()
    cur.close()
    return render_template('suppliers/suppliers.html', suppliers=all_suppliers)

@app.route('/suppliers/add', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        gstin = request.form.get('gstin')

        if not name:
            flash("Supplier name is required.", "danger")
            return render_template('suppliers/add_supplier.html')

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO suppliers (name, phone, address, gstin) VALUES (%s, %s, %s, %s)",
            (name, phone, address, gstin)
        )
        mysql.connection.commit()
        cur.close()
        flash('Supplier added successfully!', 'success')
        return redirect(url_for('suppliers'))
    
    return render_template('suppliers/add_supplier.html')

@app.route('/suppliers/edit/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM suppliers WHERE id = %s", (supplier_id,))
    supplier = cur.fetchone()
    
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for('suppliers'))

    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        gstin = request.form.get('gstin')

        if not name:
            flash("Supplier name is required.", "danger")
            return render_template('suppliers/edit_supplier.html', supplier=supplier)

        cur.execute("""
            UPDATE suppliers SET name=%s, phone=%s, address=%s, gstin=%s 
            WHERE id=%s
        """, (name, phone, address, gstin, supplier_id))
        mysql.connection.commit()
        cur.close()
        flash('Supplier updated successfully!', 'success')
        return redirect(url_for('suppliers'))

    cur.close()
    return render_template('suppliers/edit_supplier.html', supplier=supplier)

# =====================================================================
# SUPPLIER LEDGER & PAYMENT ROUTES
# =====================================================================

@app.route('/suppliers/ledger/<int:supplier_id>')
def supplier_ledger(supplier_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cur.execute("SELECT * FROM suppliers WHERE id = %s", (supplier_id,))
    supplier = cur.fetchone()
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for('suppliers'))

    cur.execute("SELECT * FROM purchases WHERE supplier_id = %s ORDER BY purchase_date DESC", (supplier_id,))
    purchases = cur.fetchall()

    cur.execute("SELECT * FROM supplier_payments WHERE supplier_id = %s ORDER BY payment_date DESC", (supplier_id,))
    payments = cur.fetchall()
    
    cur.close()
    return render_template('suppliers/supplier_ledger.html', supplier=supplier, purchases=purchases, payments=payments)


@app.route('/suppliers/<int:supplier_id>/payment/new', methods=['GET', 'POST'])
def record_payment(supplier_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, name FROM suppliers WHERE id = %s", (supplier_id,))
    supplier = cur.fetchone()
    cur.close()

    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for('suppliers'))

    if request.method == 'POST':
        amount_paid = request.form.get('amount_paid')
        payment_date = request.form.get('payment_date')
        payment_mode = request.form.get('payment_mode')
        notes = request.form.get('notes')

        if not amount_paid or not payment_date:
            flash("Payment amount and date are required.", "danger")
            return render_template('suppliers/new_payment.html', supplier=supplier, today_date=date.today().isoformat())
        
        db_cursor = None
        try:
            db_cursor = mysql.connection.cursor()
            db_cursor.execute("""
                INSERT INTO supplier_payments (supplier_id, amount_paid, payment_date, payment_mode, notes)
                VALUES (%s, %s, %s, %s, %s)
            """, (supplier_id, amount_paid, payment_date, payment_mode, notes))

            db_cursor.execute("""
                UPDATE suppliers SET current_due = current_due - %s WHERE id = %s
            """, (amount_paid, supplier_id))
            
            mysql.connection.commit()
            flash('Payment recorded successfully!', 'success')
            return redirect(url_for('supplier_ledger', supplier_id=supplier_id))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred: {e}", "danger")
        finally:
            if db_cursor:
                db_cursor.close()

    return render_template('suppliers/new_payment.html', supplier=supplier, today_date=date.today().isoformat())


# =====================================================================
# PURCHASE MANAGEMENT ROUTES
# =====================================================================

@app.route('/purchases')
def purchases():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT p.*, s.name as supplier_name, COUNT(pi.id) as item_count
        FROM purchases p
        JOIN suppliers s ON p.supplier_id = s.id
        LEFT JOIN purchase_items pi ON p.id = pi.purchase_id
        GROUP BY p.id
        ORDER BY p.purchase_date DESC
    """)
    all_purchases = cur.fetchall()
    cur.close()
    return render_template('purchases/purchases.html', purchases=all_purchases)

@app.route('/purchases/new', methods=['GET', 'POST'])
def new_purchase():
    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        if request.method == 'POST':
            supplier_id = request.form.get('supplier_id')
            purchase_date = request.form.get('purchase_date')
            bill_number = request.form.get('bill_number')
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            purchase_prices = request.form.getlist('purchase_price[]')
            
            if not all([supplier_id, purchase_date, product_ids, quantities, purchase_prices]):
                flash("Supplier, Date, and at least one full product row are required.", "danger")
                return redirect(url_for('new_purchase'))

            total_amount = sum([float(qty) * float(price) for qty, price in zip(quantities, purchase_prices)])

            db_cursor.execute("INSERT INTO purchases (supplier_id, purchase_date, bill_number, total_amount) VALUES (%s, %s, %s, %s)",
                              (supplier_id, purchase_date, bill_number, total_amount))
            purchase_id = db_cursor.lastrowid

            item_sql = "INSERT INTO purchase_items (purchase_id, product_id, quantity, purchase_price) VALUES (%s, %s, %s, %s)"
            stock_update_sql = "UPDATE products SET stock = stock + %s, purchase_price = %s WHERE id = %s"

            for i, product_id_val in enumerate(product_ids):
                if product_id_val.startswith('new--'):
                    new_product_name = product_id_val.split('--', 1)[1]
                    db_cursor.execute("INSERT INTO products (name, stock, price, purchase_price) VALUES (%s, %s, %s, %s)",
                                      (new_product_name, quantities[i], 0, purchase_prices[i]))
                    product_id = db_cursor.lastrowid
                else:
                    product_id = int(product_id_val)
                    db_cursor.execute(stock_update_sql, (quantities[i], purchase_prices[i], product_id))
                
                db_cursor.execute(item_sql, (purchase_id, product_id, quantities[i], purchase_prices[i]))

            db_cursor.execute("UPDATE suppliers SET current_due = current_due + %s WHERE id = %s", (total_amount, supplier_id))

            mysql.connection.commit()
            flash('Purchase recorded successfully and stock updated!', 'success')
            return redirect(url_for('purchases'))

        db_cursor.execute("SELECT id, name FROM suppliers WHERE is_active = TRUE ORDER BY name")
        suppliers = db_cursor.fetchall()
        db_cursor.execute("SELECT id, name, purchase_price FROM products ORDER BY name")
        products = db_cursor.fetchall()
        
        return render_template('purchases/new_purchase.html', suppliers=suppliers, products=products, today_date=date.today().isoformat())
        
    except Exception as e:
        if db_cursor:
            mysql.connection.rollback()
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('new_purchase'))
    finally:
        if db_cursor:
            db_cursor.close()


@app.route('/purchases/view/<int:purchase_id>')
def view_purchase(purchase_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT p.*, s.name as supplier_name, s.address as supplier_address, s.phone as supplier_phone
        FROM purchases p JOIN suppliers s ON p.supplier_id = s.id WHERE p.id = %s
    """, (purchase_id,))
    purchase = cur.fetchone()
    cur.execute("""
        SELECT pi.*, pr.name as product_name 
        FROM purchase_items pi JOIN products pr ON pi.product_id = pr.id WHERE pi.purchase_id = %s
    """, (purchase_id,))
    items = cur.fetchall()
    cur.close()
    if not purchase:
        flash("Purchase not found.", "danger")
        return redirect(url_for('purchases'))
    return render_template('purchases/view_purchase.html', purchase=purchase, items=items)

# --- PDF Class ---
# We must define this class before it's used
class PDF(FPDF):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_family = 'Arial' # Default
        font_path_regular = os.path.join(app.static_folder, 'fonts', 'DejaVuSans.ttf')
        font_path_bold = os.path.join(app.static_folder, 'fonts', 'DejaVuSans-Bold.ttf')

        # Check if font files exist
        # You MUST add DejaVuSans.ttf and DejaVuSans-Bold.ttf to your static/fonts/ folder
        if os.path.exists(font_path_regular) and os.path.exists(font_path_bold):
            try:
                self.add_font('DejaVu', '', font_path_regular, uni=True)
                self.add_font('DejaVu', 'B', font_path_bold, uni=True)
                self.font_family = 'DejaVu'
                app.logger.info("DejaVu font loaded for PDF.")
            except Exception as e:
                app.logger.warning(f"Could not load DejaVu font, falling back to Arial. Error: {e}")
        else:
             app.logger.warning("DejaVu font files not found in static/fonts/. Falling back to Arial.")

    def header(self):
        self.set_font(self.font_family, 'B', 16)
        self.cell(0, 10, 'Purchase Order', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_family, 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def safe_text(self, text):
        """Encodes text to latin-1 safely for FPDF if not using Unicode font."""
        text_str = str(text or '') # Ensure it's a string, handle None
        if self.font_family == 'DejaVu':
            return text_str # DejaVu handles Unicode
        # Fallback for Arial: encode non-Latin characters
        return text_str.encode('latin-1', 'replace').decode('latin-1')

@app.route('/purchases/pdf/<int:purchase_id>')
def purchase_pdf(purchase_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT p.*, s.name as s_name, s.address as s_addr FROM purchases p JOIN suppliers s ON p.supplier_id = s.id WHERE p.id = %s", (purchase_id,))
    purchase = cur.fetchone()
    cur.execute("SELECT pi.*, pr.name as p_name FROM purchase_items pi JOIN products pr ON pi.product_id = pr.id WHERE pi.purchase_id = %s", (purchase_id,))
    items = cur.fetchall()
    cur.close()
    if not purchase: return "Not Found", 404
    
    pdf = PDF()
    pdf.add_page()
    pdf.set_font(pdf.font_family, '', 12)
    pdf.cell(0, 10, f"Date: {purchase['purchase_date'].strftime('%d-%m-%Y')}", 0, 1)
    pdf.cell(0, 10, f"Bill No: {purchase['bill_number']}", 0, 1)
    pdf.cell(0, 10, pdf.safe_text(f"Supplier: {purchase['s_name']}"), 0, 1)
    pdf.ln(10)

    pdf.set_font(pdf.font_family, 'B', 12)
    pdf.cell(100, 10, 'Product', 1)
    pdf.cell(30, 10, 'Quantity', 1)
    pdf.cell(30, 10, 'Price', 1)
    pdf.cell(30, 10, 'Amount', 1, 1)

    pdf.set_font(pdf.font_family, '', 12)
    for item in items:
        pdf.cell(100, 10, pdf.safe_text(item['p_name']), 1)
        pdf.cell(30, 10, str(item['quantity']), 1)
        pdf.cell(30, 10, f"{item['purchase_price']:.2f}", 1)
        pdf.cell(30, 10, f"{item['quantity'] * item['purchase_price']:.2f}", 1, 1)
    
    pdf.set_font(pdf.font_family, 'B', 12)
    pdf.cell(160, 10, 'Grand Total', 1)
    pdf.cell(30, 10, f"{purchase['total_amount']:.2f}", 1, 1)

    # Use 'S' to output as string, then encode
    pdf_output = pdf.output(dest='S').encode('latin1')
    response = make_response(pdf_output)
    response.headers.set('Content-Type', 'application/pdf')
    response.headers.set('Content-Disposition', 'attachment', filename=f'Purchase_{purchase_id}.pdf')
    return response


#-------Product--------------------------------------------------------------------------------

@app.route('/products')
def products():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    cur.close()
    return render_template('products.html', products=products)


@app.route("/add_product")
def add_product():
    return render_template("add_product.html")


# --- MODIFIED: `add_product_action` ---
@app.route("/add_product_form", methods=["POST"])
def add_product_form():
    if request.method == "POST":
        name = request.form.get("name")
        category = request.form.get("category")
        price = request.form.get("price")
        stock = int(request.form.get("stock") or 0)
        image_file = request.files.get("image")
        
        image_url = None # Will hold the URL from Cloudinary

        if image_file and allowed_file(image_file.filename):
            try:
                # Upload to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    image_file, 
                    folder="erp_products" # Creates a folder in Cloudinary
                )
                image_url = upload_result.get('secure_url') # Get the HTTPS URL
                app.logger.info(f"Image uploaded to Cloudinary: {image_url}")
            except Exception as e:
                app.logger.error(f"Cloudinary upload failed: {e}")
                flash(f"Image upload failed: {e}", "danger")
                return redirect(url_for("add_product_form"))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            "SELECT id, stock FROM products WHERE name=%s AND category=%s",
            (name, category)
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing product
            if image_url: # Only update image if a new one was uploaded
                cursor.execute("""
                    UPDATE products SET stock=%s, price=%s, image=%s
                    WHERE id=%s
                """, (existing['stock'] + stock, price, image_url, existing['id']))
            else: # No new image, just update stock/price
                cursor.execute("""
                    UPDATE products SET stock=%s, price=%s
                    WHERE id=%s
                """, (existing['stock'] + stock, price, existing['id']))
        else:
            # Insert new product
            cursor.execute("""
                INSERT INTO products (name, category, price, stock, image)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, category, price, stock, image_url))

        mysql.connection.commit()
        cursor.close()
        flash("✅ Product added/updated successfully!", "success")
        return redirect(url_for("inventory"))

    return redirect(url_for("add_product_form"))


# --- MODIFIED: `edit_product` ---
@app.route('/products/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM products WHERE id=%s", (id,))
    product = cur.fetchone()
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('inventory'))

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = request.form['price']
        stock = request.form['stock']
        image_file = request.files.get('image')

        # Start with the existing image URL
        image_url = product['image'] 

        if image_file and allowed_file(image_file.filename):
            try:
                # Upload the NEW image to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    image_file, 
                    folder="erp_products"
                )
                image_url = upload_result.get('secure_url') # Get the new URL
                app.logger.info(f"Image updated in Cloudinary: {image_url}")
            except Exception as e:
                app.logger.error(f"Cloudinary upload failed: {e}")
                flash(f"Image upload failed: {e}", "danger")
                return render_template("edit_product.html", product=product)

        # Update the database with the new (or old) image URL
        cur.execute("""
            UPDATE products 
            SET name=%s, category=%s, price=%s, stock=%s, image=%s 
            WHERE id=%s
        """, (name, category, price, stock, image_url, id))
        
        mysql.connection.commit()
        cur.close()
        flash("Product updated successfully!", "success")
        return redirect(url_for('inventory'))

    cur.close()
    return render_template("edit_product.html", product=product)


@app.route('/products/delete/<int:id>', methods=['POST'])
def delete_product(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (id,))
    mysql.connection.commit()
    cursor.close()

    flash("Product deleted successfully!", "success")
    return redirect(url_for('inventory'))


#=========================================================================================================
# ------------------ EMPLOYEES ----------------------------------------------------------------------
@app.route('/api/check-employee')
def api_check_employee():
    field = request.args.get('field', '').strip().lower()
    value = request.args.get('value', '').strip()
    exclude_id = request.args.get('exclude_id')

    allowed = {'name', 'email', 'phone'}
    if field not in allowed or not value:
        return {'ok': False, 'exists': False, 'error': 'Invalid request'}, 400

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if exclude_id:
        cur.execute(f"SELECT id FROM employees WHERE {field}=%s AND id<>%s LIMIT 1", (value, exclude_id))
    else:
        cur.execute(f"SELECT id FROM employees WHERE {field}=%s LIMIT 1", (value,))
    row = cur.fetchone()
    cur.close()

    return {'ok': True, 'exists': bool(row)}


# --- MODIFIED: `add_employee` ---
@app.route("/add_employee", methods=["GET", "POST"])
def add_employee():
    if request.method == "POST":
        name = request.form["name"]
        position = request.form["position"]
        email = request.form["email"]
        phone = request.form["phone"]
        status = request.form["status"]
        city = request.form["city"]
        
        image_file = request.files.get("image")
        document_file = request.files.get("document")

        image_url = None
        document_url = None

        try:
            # Upload image
            if image_file and allowed_file(image_file.filename):
                img_res = cloudinary.uploader.upload(image_file, folder="erp_employees")
                image_url = img_res.get('secure_url')
                app.logger.info("Employee image uploaded.")

            # Upload document
            if document_file and document_file.filename != '':
                doc_res = cloudinary.uploader.upload(
                    document_file, 
                    folder="erp_documents",
                    resource_type="auto" # Tell Cloudinary to handle non-image files
                )
                document_url = doc_res.get('secure_url')
                app.logger.info("Employee document uploaded.")

        except Exception as e:
            app.logger.error(f"Cloudinary upload failed: {e}")
            flash(f"File upload failed: {e}", "danger")
            return render_template("add_employee.html")

        # Insert into DB
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO employees (name, position, email, phone, status, city, image, document)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, position, email, phone, status, city, image_url, document_url))
        mysql.connection.commit()
        cursor.close()

        flash(" Employee Added Successfully!", "success")
        return redirect(url_for("employees"))

    return render_template("add_employee.html")


@app.route("/employees")
def employees():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM employees")
    data = cursor.fetchall()
    cursor.close()
    return render_template("employees.html", employees=data)


# --- MODIFIED: `edit_employee` ---
@app.route("/edit_employee/<int:id>", methods=["GET", "POST"])
def edit_employee(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM employees WHERE id=%s", (id,))
    employee = cursor.fetchone()
    if not employee:
        flash("Employee not found.", "danger")
        return redirect(url_for('employees'))

    if request.method == "POST":
        name = request.form["name"]
        position = request.form["position"]
        email = request.form["email"]
        phone = request.form["phone"]
        status = request.form["status"]
        city = request.form["city"]

        image_file = request.files.get("image")
        document_file = request.files.get("document")

        # Start with existing URLs
        image_url = employee["image"]
        document_url = employee["document"]

        try:
            # Upload new image if provided
            if image_file and allowed_file(image_file.filename):
                img_res = cloudinary.uploader.upload(image_file, folder="erp_employees")
                image_url = img_res.get('secure_url')
                app.logger.info("Employee image updated.")
            
            # Upload new document if provided
            if document_file and document_file.filename != '':
                doc_res = cloudinary.uploader.upload(
                    document_file, 
                    folder="erp_documents",
                    resource_type="auto"
                )
                document_url = doc_res.get('secure_url')
                app.logger.info("Employee document updated.")
                
        except Exception as e:
            app.logger.error(f"Cloudinary upload failed: {e}")
            flash(f"File upload failed: {e}", "danger")
            return render_template("edit_employee.html", employee=employee)

        cursor.execute("""
            UPDATE employees SET name=%s, position=%s, email=%s, phone=%s, 
            status=%s, city=%s, image=%s, document=%s WHERE id=%s
        """, (name, position, email, phone, status, city, image_url, document_url, id))
        mysql.connection.commit()
        cursor.close()

        flash(" Employee Updated Successfully!", "info")
        return redirect(url_for("employees"))

    cursor.close()
    return render_template("edit_employee.html", employee=employee)


@app.route("/delete_employee/<int:id>", methods=["POST"])
def delete_employee(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM employees WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash(" Employee Deleted Successfully!", "danger")
    return redirect(url_for("employees"))

#----------------------------------------INVENTORY-----------------------------------------------------------
@app.route("/inventory")
def inventory():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.close()
    return render_template("inventory.html", products=products)


#=============================================EXPENSES================================================
@app.route('/expenses_list', methods=['GET', 'POST'])
def expenses_list():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        expense_date = request.form['expense_date']
        amount = request.form['amount']
        subcategory_id = request.form['subcategory_id']
        description = request.form.get('description')
        payment_method = request.form.get('payment_method')
        cur.execute("""
            INSERT INTO expenses (expense_date, amount, subcategory_id, description, payment_method)
            VALUES (%s, %s, %s, %s, %s)
        """, (expense_date, amount, subcategory_id, description, payment_method))
        mysql.connection.commit()
        flash('Expense Added Successfully!', 'success')
        return redirect(url_for('expenses_list'))
    cur.execute("SELECT * FROM expensecategories ORDER BY category_name")
    categories = cur.fetchall()
    cur.execute("SELECT * FROM expensesubcategories")
    subcategories = cur.fetchall()
    cur.execute("""
        SELECT e.*, sc.subcategory_name, c.category_name
        FROM expenses e
        JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id
        JOIN expensecategories c ON sc.category_id = c.category_id
        ORDER BY e.expense_date DESC, e.expense_id DESC
    """)
    expenses = cur.fetchall()
    cur.close()
    return render_template('expenses/expenses_list.html',
                           expenses=expenses,
                           categories=categories,
                           subcategories_for_js=subcategories)


@app.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        expense_date = request.form['expense_date']
        amount = request.form['amount']
        subcategory_id = request.form['subcategory_id']
        description = request.form.get('description')
        payment_method = request.form.get('payment_method')
        cur.execute("""
            UPDATE expenses
            SET expense_date = %s, amount = %s, subcategory_id = %s, description = %s, payment_method = %s
            WHERE expense_id = %s
        """, (expense_date, amount, subcategory_id, description, payment_method, expense_id))
        mysql.connection.commit()
        flash('Expense Updated Successfully!', 'success')
        return redirect(url_for('expenses_list'))

    cur.execute("""
        SELECT e.*, sc.category_id
        FROM Expenses e
        JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id
        WHERE e.expense_id = %s
    """, (expense_id,))
    expense = cur.fetchone()
    if not expense:
        flash('Expense not found!', 'danger')
        return redirect(url_for('expenses_list'))
    cur.execute("SELECT * FROM expensecategories ORDER BY category_name")
    all_categories = cur.fetchall()
    cur.execute("SELECT * FROM expensesubcategories")
    all_subcategories = cur.fetchall()
    cur.close()
    return render_template('expenses/edit_expense.html', 
                           expense=expense,
                           categories=all_categories, 
                           subcategories_for_js=all_subcategories)


@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("DELETE FROM expenses WHERE expense_id = %s", (expense_id,))
    mysql.connection.commit()
    flash('Expense Deleted Successfully!', 'danger')
    return redirect(url_for('expenses_list'))

@app.route('/expense_dash')
def expense_dash():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT SUM(amount) AS total FROM expenses WHERE MONTH(expense_date) = MONTH(CURDATE()) AND YEAR(expense_date) = YEAR(CURDATE())")
    this_month_result = cur.fetchone()
    this_month_spend = this_month_result['total'] if this_month_result and this_month_result['total'] else 0
    cur.execute("SELECT SUM(amount) AS total FROM expenses WHERE MONTH(expense_date) = MONTH(CURDATE() - INTERVAL 1 MONTH) AND YEAR(expense_date) = YEAR(CURDATE() - INTERVAL 1 MONTH)")
    last_month_result = cur.fetchone()
    last_month_spend = last_month_result['total'] if last_month_result and last_month_result['total'] else 0
    cur.execute("SELECT SUM(amount) AS total FROM expenses WHERE YEAR(expense_date) = YEAR(CURDATE())")
    ytd_result = cur.fetchone()
    ytd_spend = ytd_result['total'] if ytd_result and ytd_result['total'] else 0
    cur.execute("""
        SELECT c.category_name, SUM(e.amount) as total_amount
        FROM expenses e
        JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id
        JOIN expensecategories c ON sc.category_id = c.category_id
        WHERE MONTH(e.expense_date) = MONTH(CURDATE()) AND YEAR(e.expense_date) = YEAR(CURDATE())
        GROUP BY c.category_name ORDER BY total_amount DESC LIMIT 1
    """)
    top_category = cur.fetchone()
    kpi_data = {
        'this_month': this_month_spend,
        'last_month': last_month_spend,
        'ytd_spend': ytd_spend,
        'top_category_name': top_category['category_name'] if top_category else 'N/A',
        'top_category_amount': top_category['total_amount'] if top_category else 0
    }
    cur.execute("""
        SELECT e.amount, sc.subcategory_name
        FROM expenses e
        JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id
        WHERE MONTH(e.expense_date) = MONTH(CURDATE()) AND YEAR(e.expense_date) = YEAR(CURDATE())
        ORDER BY e.amount DESC
        LIMIT 3
    """)
    top_3_expenses = cur.fetchall()
    cur.execute("""
        SELECT c.category_name, SUM(e.amount) as total_amount
        FROM expenses e JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id JOIN ExpenseCategories c ON sc.category_id = c.category_id
        GROUP BY c.category_name ORDER BY total_amount DESC
    """)
    category_results = cur.fetchall()
    category_data = {
        'labels': [row['category_name'] for row in category_results],
        'data': [float(row['total_amount'] or 0) for row in category_results]
    }
    cur.execute("""
        SELECT DATE_FORMAT(expense_date, '%%b %%Y') AS month, SUM(amount) AS total_amount
        FROM expenses WHERE expense_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(expense_date, '%%b %%Y') ORDER BY MIN(expense_date) ASC
    """)
    monthly_results = cur.fetchall()
    monthly_data = {
        'labels': [row['month'] for row in monthly_results],
        'data': [float(row['total_amount'] or 0) for row in monthly_results]
    }
    cur.close()
    return render_template('expenses/expense_dash.html',
                           kpi_data=kpi_data,
                           top_3_expenses=top_3_expenses,
                           category_data=category_data,
                           monthly_data=monthly_data)

@app.route('/category_man', methods=['GET', 'POST'])
def category_man():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'main_category':
            category_name = request.form.get('category_name')
            if category_name:
                cur.execute("INSERT INTO expensecategories (category_name) VALUES (%s)", (category_name,))
                mysql.connection.commit()
                flash('Main Category added successfully!', 'success')
        elif form_type == 'subcategory':
            parent_id = request.form.get('parent_category_id')
            subcategory_name = request.form.get('subcategory_name')
            if parent_id and subcategory_name:
                cur.execute("INSERT INTO expensesubcategories (category_id, subcategory_name) VALUES (%s, %s)", (parent_id, subcategory_name))
                mysql.connection.commit()
                flash('Subcategory added successfully!', 'success')
        return redirect(url_for('category_man'))

    cur.execute("SELECT * FROM expensecategories ORDER BY category_name")
    categories = cur.fetchall()
    cur.execute("SELECT * FROM expensesubcategories ORDER BY subcategory_name")
    subcategories = cur.fetchall()
    cur.close()
    for category in categories:
        category['subcategories'] = [sub for sub in subcategories if sub['category_id'] == category['category_id']]
    return render_template('expenses/category_man.html', categories=categories)


@app.route('/delete_category/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("DELETE FROM expensesubcategories WHERE category_id = %s", (category_id,))
    cur.execute("DELETE FROM expensecategories WHERE category_id = %s", (category_id,))
    mysql.connection.commit()
    flash('Main Category and its subcategories have been deleted.', 'danger')
    return redirect(url_for('category_man'))


@app.route('/delete_subcategory/<int:subcategory_id>', methods=['POST'])
def delete_subcategory(subcategory_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("DELETE FROM expensesubcategories WHERE subcategory_id = %s", (subcategory_id,))
    mysql.connection.commit()
    flash('Subcategory has been deleted.', 'danger')
    return redirect(url_for('category_man'))                                 

# =====================================================================
# MORNING ALLOCATION ROUTES
# =====================================================================

@app.route('/morning', methods=['GET', 'POST'])
def morning():
    if request.method == 'POST':
        return save_allocation_data()
    data = get_template_data()
    return render_template('morning.html', **data)


@app.route('/api/fetch_stock')
def api_fetch_stock():
    employee_id = request.args.get('employee_id')
    date_str    = request.args.get('date')
    if not employee_id or not date_str:
        return jsonify({"error": "Employee and date are required."}), 400
    try:
        current_date = date.fromisoformat(date_str)
        previous_day = current_date - timedelta(days=1)
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("""
            SELECT 
              ei.product_id,
              ei.remaining_qty  AS remaining,
              ei.unit_price     AS price
            FROM evening_item ei
            JOIN evening_settle es ON ei.settle_id = es.id
            WHERE es.employee_id = %s
              AND es.date        = %s
              AND ei.remaining_qty > 0
        """, (employee_id, previous_day))
        rows = cur.fetchall()
        cur.close()
        out = {
            str(r['product_id']): {
                'remaining': int(r['remaining']),
                'price'    : float(r['price'])
            }
            for r in rows
        }
        return jsonify(out)
    except Exception as e:
        app.logger.error("fetch_stock error: %s", e)
        return jsonify({"error": "Internal server error."}), 500


@app.route('/api/fetch_morning_allocation')
def api_fetch_morning_allocation():
    employee_id = request.args.get('employee_id')
    date_str    = request.args.get('date')
    if not employee_id or not date_str:
        return jsonify({"error": "Employee and date are required."}), 400
    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(
            "SELECT id FROM morning_allocations WHERE employee_id=%s AND date=%s",
            (employee_id, date_str)
        )
        alloc = cur.fetchone()
        if not alloc:
            cur.close()
            return jsonify({"error": "No allocation found."}), 404
        alloc_id = alloc['id']
        cur.execute("""
            SELECT 
              mai.product_id,
              p.name       AS product_name,
              mai.opening_qty,
              mai.given_qty,
              mai.total_qty,
              mai.unit_price
            FROM morning_allocation_items mai
            JOIN products p ON mai.product_id = p.id
            WHERE mai.allocation_id = %s
        """, (alloc_id,))
        items = cur.fetchall()
        cur.close()
        for i in items:
            i['opening_qty'] = int(i['opening_qty'])
            i['given_qty']   = int(i['given_qty'])
            i['total_qty']   = int(i['total_qty'])
            i['unit_price']  = float(i['unit_price'])
        return jsonify({"allocation_id": alloc_id, "items": items})
    except Exception as e:
        app.logger.error("fetch_morning_allocation error: %s", e)
        return jsonify({"error": "Internal server error."}), 500


def get_template_data():
    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT id, name FROM employees ORDER BY name")
        employees = cur.fetchall()
        cur.execute("SELECT id, name, price FROM products ORDER BY name")
        raw = cur.fetchall()
        cur.close()
        products = [
            {'id': p['id'], 'name': p['name'], 'price': float(p['price'])}
            for p in raw
        ]
        productOptions = ''.join(
            f'<option value="{pr["id"]}">{pr["name"]}</option>'
            for pr in products
        )
        return {
            'employees'     : employees,
            'products'      : products,
            'productOptions': productOptions,
            'today_date'    : date.today().isoformat()
        }
    except Exception as e:
        app.logger.error("get_template_data error: %s", e)
        flash("Database error loading form.", "danger")
        return {
            'employees'     : [],
            'products'      : [],
            'productOptions': '',
            'today_date'    : date.today().isoformat()
        }


def save_allocation_data():
    try:
        employee_id  = request.form.get('employee_id')
        date_str     = request.form.get('date')
        product_ids  = request.form.getlist('product_id[]')
        opening_list = request.form.getlist('opening[]')
        given_list   = request.form.getlist('given[]')
        price_list   = request.form.getlist('price[]')

        if not (employee_id and date_str and product_ids):
            flash("All fields are required.", "danger")
            return redirect(url_for('morning'))

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT id FROM morning_allocations WHERE employee_id=%s AND date=%s",
            (employee_id, date_str)
        )
        if cur.fetchone():
            cur.close()
            flash("Allocation already exists for this date.", "warning")
            return redirect(url_for('morning'))
        cur.execute(
            "INSERT INTO morning_allocations (employee_id, date) VALUES (%s, %s)",
            (employee_id, date_str)
        )
        alloc_id = cur.lastrowid
        insert_sql = """
          INSERT INTO morning_allocation_items
            (allocation_id, product_id, opening_qty, given_qty, unit_price)
          VALUES (%s, %s, %s, %s, %s)
        """
        for idx, pid in enumerate(product_ids):
            if not pid:
                continue
            open_q = int(opening_list[idx] or 0)
            giv_q  = int(given_list[idx]   or 0)
            price  = float(price_list[idx] or 0.0)
            cur.execute(insert_sql,
                        (alloc_id, pid, open_q, giv_q, price))
        mysql.connection.commit()
        cur.close()
        flash("Morning allocation saved successfully.", "success")
        return redirect(url_for('morning'))
    except Exception as e:
        app.logger.error("save_allocation_data error: %s", e)
        flash("Error saving allocation.", "danger")
        return redirect(url_for('morning'))

# -------------------------------
# EVENING SETTLEMENT ROUTE
# ----------------------------------------------------------------------------------------------------------
@app.route('/evening', methods=['GET', 'POST'])
def evening():
    if request.method == 'POST':
        db_cursor = None
        try:
            allocation_id = request.form.get('allocation_id')
            employee_id = request.form.get('h_employee')
            date_str = request.form.get('h_date')
            total_amount = request.form.get('totalAmount')
            online_received = request.form.get('online')
            cash_received = request.form.get('cash')
            discount = request.form.get('discount')
            product_ids = request.form.getlist('product_id[]')
            total_qtys = request.form.getlist('total_qty[]')
            sold_qtys = request.form.getlist('sold[]')
            return_qtys = request.form.getlist('return[]')
            unit_prices = request.form.getlist('price[]')

            if not allocation_id:
                flash("Error: Morning Allocation ID missing. Please fetch data again.", "danger")
                return redirect(url_for('evening'))

            db_cursor = mysql.connection.cursor()
            db_cursor.execute("""
                INSERT INTO evening_settle (allocation_id, employee_id, date, total_amount, online_money, cash_money, discount)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (allocation_id, employee_id, date_str, total_amount, online_received, cash_received, discount))
            settle_id = db_cursor.lastrowid
            item_sql = """
                INSERT INTO evening_item (settle_id, product_id, total_qty, sold_qty, return_qty, unit_price)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            inventory_update_list = []
            for i, product_id in enumerate(product_ids):
                if not product_id:
                    continue
                sold_qty = int(sold_qtys[i] or 0)
                return_qty = int(return_qtys[i] or 0)
                db_cursor.execute(item_sql, (settle_id, product_id, total_qtys[i], sold_qty, return_qty, unit_prices[i]))
                if sold_qty > 0 or return_qty > 0:
                    inventory_update_list.append({'id': product_id, 'sold': sold_qty, 'returned': return_qty})

            if inventory_update_list:
                for item in inventory_update_list:
                    db_cursor.execute("UPDATE products SET stock = stock - %s + %s WHERE id = %s", 
                                      (item['sold'], item['returned'], item['id']))
            mysql.connection.commit()
            return redirect(url_for('evening', last_settle_id=settle_id))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred: {e}", "danger")
            return redirect(url_for('evening'))
        finally:
            if db_cursor:
                db_cursor.close()

    # GET request
    last_settle_id = request.args.get('last_settle_id', None)
    db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    db_cursor.execute("SELECT id, name FROM employees ORDER BY name")
    employees = db_cursor.fetchall()
    db_cursor.close()
    today_date = date.today().isoformat()
    return render_template('evening.html', employees=employees, today=today_date, last_settle_id=last_settle_id)




@app.route('/evening/pdf/<int:settle_id>')
def generate_pdf(settle_id):
    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        db_cursor.execute("""
            SELECT es.*, e.name as employee_name
            FROM evening_settle es
            JOIN employees e ON es.employee_id = e.id
            WHERE es.id = %s
        """, (settle_id,))
        settlement = db_cursor.fetchone()
        if not settlement:
            return "Settlement not found", 404
        db_cursor.execute("""
            SELECT ei.*, p.name as product_name
            FROM evening_item ei
            JOIN products p ON ei.product_id = p.id
            WHERE ei.settle_id = %s
        """, (settle_id,))
        items = db_cursor.fetchall()

        pdf = PDF() 
        pdf.add_page()
        pdf.set_font(pdf.font_family, 'B', 12)
        pdf.cell(0, 10, pdf.safe_text(f"Employee: {settlement['employee_name']}"), 0, 0, 'L')
        pdf.cell(0, 10, f"Date: {settlement['date'].strftime('%d-%m-%Y')}", 0, 1, 'R')
        pdf.ln(5)
        pdf.set_font(pdf.font_family, 'B', 10)
        pdf.set_fill_color(230, 230, 230)
        headers = [('#', 10), ('Product', 60), ('Total', 15), ('Sold', 15),
                   ('Return', 15), ('Remaining', 20), ('Price', 20), ('Amount', 25)]
        for header, width in headers:
            pdf.cell(width, 8, header, 1, 0, 'C' if header != 'Product' else 'L', 1)
        pdf.ln()
        pdf.set_font(pdf.font_family, '', 10)
        for i, item in enumerate(items):
            amount = (item.get('sold_qty') or 0) * (item.get('unit_price') or 0)
            remaining = (item.get('total_qty', 0) - item.get('sold_qty', 0))
            pdf.cell(10, 8, str(i + 1), 1, 0, 'C')
            pdf.cell(60, 8, pdf.safe_text(item.get('product_name', '')), 1, 0, 'L')
            pdf.cell(15, 8, str(item.get('total_qty', 0)), 1, 0, 'C')
            pdf.cell(15, 8, str(item.get('sold_qty', 0)), 1, 0, 'C')
            pdf.cell(15, 8, str(item.get('return_qty', 0)), 1, 0, 'C')
            pdf.cell(20, 8, str(remaining), 1, 0, 'C')
            pdf.cell(20, 8, f"{float(item.get('unit_price', 0)):.2f}", 1, 0, 'R')
            pdf.cell(25, 8, f"{float(amount):.2f}", 1, 1, 'R')
        pdf.ln(10)
        pdf.set_font(pdf.font_family, 'B', 12)
        pdf.cell(0, 10, 'Financial Summary', 0, 1, 'L')
        pdf.set_font(pdf.font_family, '', 10)
        total_amount = settlement.get('total_amount', 0)
        online_money = settlement.get('online_money', 0)
        cash_money = settlement.get('cash_money', 0)
        discount = settlement.get('discount', 0)
        due_amount = total_amount - (online_money + cash_money + discount)
        summary_data = [
            ("Total Sales Amount:", total_amount),
            ("Online Received:", online_money),
            ("Cash Received:", cash_money),
            ("Discount Given:", discount),
        ]
        for label, value in summary_data:
            pdf.cell(50, 8, label, 0, 0, 'R')
            pdf.cell(30, 8, f"{float(value):.2f}", 0, 1, 'R')
        pdf.set_font(pdf.font_family, 'B', 10)
        pdf.cell(50, 8, 'Balance Due:', 0, 0, 'R')
        pdf.cell(30, 8, f"{float(due_amount):.2f}", 0, 1, 'R')
        pdf_output = pdf.output(dest='S').encode('latin1')
        filename = f"Settlement_{settlement['employee_name']}_{settlement['date']}.pdf"
        response = make_response(pdf_output)
        response.headers.set('Content-Type', 'application/pdf')
        response.headers.set('Content-Disposition', 'attachment', filename=filename)
        return response
    except Exception as e:
        app.logger.error(f"!!! PDF GENERATION FAILED: {type(e).__name__}: {e} !!!")
        flash(f"Could not generate PDF. Server error: {e}", "danger")
        return redirect(url_for('evening'))
    finally:
        if db_cursor:
            db_cursor.close()

# --- ALL OTHER ROUTES (REPORTS, EMPLOYEE FINANCE, etc.) ---
# (Pasting the rest of your routes)

@app.route('/sales', methods=['GET', 'POST'])
def sales():
    db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    db_cursor.execute("SELECT id, name FROM employees ORDER BY name")
    employees = db_cursor.fetchall()
    db_cursor.execute("SELECT id, name FROM products ORDER BY name")
    products = db_cursor.fetchall()
    report_data = None
    totals = None
    filters = {
        'start_date': request.form.get('start_date', date.today().isoformat()),
        'end_date': request.form.get('end_date', date.today().isoformat()),
        'employee_id': request.form.get('employee_id', 'all'),
        'product_id': request.form.get('product_id', 'all')
    }
    if request.method == 'POST':
        query = """
            SELECT 
                es.date,
                e.name AS employee_name,
                p.name AS product_name,
                ei.sold_qty AS units_sold,
                ei.unit_price,
                (ei.sold_qty * ei.unit_price) AS total_amount
            FROM evening_item ei
            JOIN evening_settle es ON ei.settle_id = es.id
            JOIN employees e ON es.employee_id = e.id
            JOIN products p ON ei.product_id = p.id
            WHERE es.date BETWEEN %s AND %s
        """
        params = [filters['start_date'], filters['end_date']]
        if filters['employee_id'] != 'all':
            query += " AND es.employee_id = %s"
            params.append(filters['employee_id'])
        if filters['product_id'] != 'all':
            query += " AND ei.product_id = %s"
            params.append(filters['product_id'])
        query += " ORDER BY es.date, e.name"
        db_cursor.execute(query, tuple(params))
        report_data = db_cursor.fetchall()
        total_units = sum(row['units_sold'] for row in report_data)
        total_sales = sum(row['total_amount'] for row in report_data)
        totals = {'total_units': total_units, 'total_sales': total_sales}
    db_cursor.close()
    return render_template('sales.html',
                           employees=employees,
                           products=products,
                           today=date.today().isoformat(),
                           report_data=report_data,
                           totals=totals,
                           filters=filters)


@app.route('/saless', methods=['POST'])
def sales_export():
    try:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        employee_id = request.form.get('employee_id')
        product_id = request.form.get('product_id')
        query = """
            SELECT es.date, e.name, p.name, ei.sold_qty, ei.unit_price, (ei.sold_qty * ei.unit_price)
            FROM evening_item ei
            JOIN evening_settle es ON ei.settle_id = es.id
            JOIN employees e ON es.employee_id = e.id
            JOIN products p ON ei.product_id = p.id
            WHERE es.date BETWEEN %s AND %s
        """
        params = [start_date, end_date]
        if employee_id != 'all':
            query += " AND es.employee_id = %s"
            params.append(employee_id)
        if product_id != 'all':
            query += " AND ei.product_id = %s"
            params.append(product_id)
        db_cursor = mysql.connection.cursor()
        db_cursor.execute(query, tuple(params))
        report_data = db_cursor.fetchall()
        db_cursor.close()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Employee', 'Product', 'Units Sold', 'Unit Price', 'Total Amount'])
        for row in report_data:
            writer.writerow(row)
        output.seek(0)
        return Response(output,
                        mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment;filename=sales_report_{start_date}_to_{end_date}.csv"})
    except Exception as e:
        flash(f"Error exporting report: {e}", "danger")
        return redirect(url_for('sales'))


@app.route('/summary')
def summary():
    selected_date = request.args.get('date', date.today().isoformat())
    db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    db_cursor.execute("""
        SELECT ma.id, e.name as employee_name, 
               (SELECT COUNT(id) FROM evening_settle WHERE allocation_id = ma.id) as evening_submitted
        FROM morning_allocations ma
        JOIN employees e ON ma.employee_id = e.id
        WHERE ma.date = %s ORDER BY e.name
    """, (selected_date,))
    morning_forms_raw = db_cursor.fetchall()
    morning_forms = []
    for form in morning_forms_raw:
        form['is_editable'] = form['evening_submitted'] == 0
        morning_forms.append(form)
    db_cursor.execute("""
        SELECT es.id, e.name as employee_name, es.total_amount
        FROM evening_settle es
        JOIN employees e ON es.employee_id = e.id
        WHERE es.date = %s ORDER BY e.name
    """, (selected_date,))
    evening_forms = db_cursor.fetchall()
    db_cursor.close()
    return render_template('daily_summary.html', 
                           morning_forms=morning_forms, 
                           evening_forms=evening_forms, 
                           selected_date=selected_date)


@app.route('/reports')
def reports():
    return render_template("/reports.html")

@app.route('/exp_report')
def exp_report():
    return render_template("/exp_report.html")


@app.route('/reports/daily_summary', methods=['GET', 'POST'])
def daily_summary():
    report_date = date.today().isoformat()
    summary_data = None
    if request.method == 'POST':
        report_date = request.form.get('report_date')
        try:
            db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            db_cursor.execute("SELECT SUM(total_amount) as total_sales FROM evening_settle WHERE date = %s", (report_date,))
            sales_result = db_cursor.fetchone()
            total_sales = sales_result['total_sales'] or 0
            db_cursor.execute("SELECT SUM(amount) as total_expenses FROM expenses WHERE expense_date = %s", (report_date,))
            expenses_result = db_cursor.fetchone()
            total_expenses = expenses_result['total_expenses'] or 0
            db_cursor.close()
            summary_data = {
                "total_sales": total_sales,
                "total_expenses": total_expenses,
                "net_cash_flow": total_sales - total_expenses
            }
        except Exception as e:
            flash(f"An error occurred while generating the report: {e}", "danger")
    
    report_date_obj = date.fromisoformat(report_date)
    report_date_str = report_date_obj.strftime('%d %B, %Y')
    return render_template('reports/daily_summary.html', 
                           report_date=report_date, 
                           report_date_str=report_date_str,
                           summary_data=summary_data)


@app.route('/reports/daily_summary/pdf/<report_date>')
def report_daily_summary_pdf(report_date):
    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        db_cursor.execute("SELECT SUM(total_amount) as total_sales FROM evening_settle WHERE date = %s", (report_date,))
        sales_result = db_cursor.fetchone()
        total_sales = sales_result['total_sales'] or 0
        db_cursor.execute("SELECT SUM(amount) as total_expenses FROM expenses WHERE expense_date = %s", (report_date,))
        expenses_result = db_cursor.fetchone()
        total_expenses = expenses_result['total_expenses'] or 0
        db_cursor.close()
        
        net_cash_flow = total_sales - total_expenses
        report_date_obj = date.fromisoformat(report_date)
        report_date_str = report_date_obj.strftime('%d %B, %Y')

        pdf = PDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font(pdf.font_family, 'B', 14)
        pdf.cell(0, 10, f'Daily Financial Summary: {report_date_str}', 0, 1, 'C')
        pdf.ln(15)
        pdf.set_font(pdf.font_family, '', 12)
        pdf.cell(0, 10, 'Total Sales', 1, 0, 'L')
        pdf.cell(0, 10, f'Rs. {total_sales:.2f}', 0, 1, 'R')
        pdf.ln(2)
        pdf.cell(0, 10, 'Total Expenses', 1, 0, 'L')
        pdf.cell(0, 10, f'Rs. {total_expenses:.2f}', 0, 1, 'R')
        pdf.ln(2)
        pdf.set_font(pdf.font_family, 'B', 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, 'Net Cash Flow', 1, 0, 'L', 1)
        pdf.cell(0, 10, f'Rs. {net_cash_flow:.2f}', 0, 1, 'R')

        pdf_output = pdf.output(dest='S').encode('latin1')
        response = make_response(pdf_output)
        response.headers.set('Content-Type', 'application/pdf')
        response.headers.set('Content-Disposition', 'attachment', filename=f'Daily_Summary_{report_date}.pdf')
        return response
    except Exception as e:
        app.logger.error(f"PDF Generation Error: {e}")
        flash("Could not generate PDF due to a server error.", "danger")
        return redirect(url_for('daily_summary'))
    finally:
        if db_cursor:
            db_cursor.close()


@app.route('/reports/daily_sales', methods=['GET', 'POST'])
def daily_sales():
    report_date = date.today().isoformat()
    sales_data = []
    grand_total = 0

    if request.method == 'POST':
        report_date = request.form.get('report_date')
        db_cursor = None
        try:
            db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            sql = """
                SELECT 
                    p.name AS product_name,
                    e.name AS employee_name,
                    ei.sold_qty,
                    ei.unit_price,
                    (ei.sold_qty * ei.unit_price) AS total_amount
                FROM evening_item ei
                JOIN evening_settle es ON ei.settle_id = es.id
                JOIN products p ON ei.product_id = p.id
                JOIN employees e ON es.employee_id = e.id
                WHERE es.date = %s AND ei.sold_qty > 0
                ORDER BY e.name, p.name
            """
            db_cursor.execute(sql, (report_date,))
            sales_data = db_cursor.fetchall()
        except Exception as e:
            flash(f"An error occurred while generating the report: {e}", "danger")
        finally:
            if db_cursor:
                db_cursor.close()

    if sales_data:
        grand_total = sum(item['total_amount'] for item in sales_data)
    report_date_obj = date.fromisoformat(report_date)
    report_date_str = report_date_obj.strftime('%d %B, %Y')
    return render_template('reports/daily_sales.html', 
                           report_date=report_date, 
                           report_date_str=report_date_str,
                           sales_data=sales_data,
                           grand_total=grand_total)


@app.route('/reports/daily_sales/pdf/<report_date>')
def report_daily_sales_pdf(report_date):
    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        sql = """
            SELECT p.name AS product_name, e.name AS employee_name, ei.sold_qty, ei.unit_price, (ei.sold_qty * ei.unit_price) AS total_amount
            FROM evening_item ei
            JOIN evening_settle es ON ei.settle_id = es.id
            JOIN products p ON ei.product_id = p.id
            JOIN employees e ON es.employee_id = e.id
            WHERE es.date = %s AND ei.sold_qty > 0
            ORDER BY e.name, p.name
        """
        db_cursor.execute(sql, (report_date,))
        sales_data = db_cursor.fetchall()
        
        grand_total = sum(item['total_amount'] for item in sales_data) if sales_data else 0
        report_date_obj = date.fromisoformat(report_date)
        report_date_str = report_date_obj.strftime('%d %B, %Y')

        pdf = PDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font(pdf.font_family, 'B', 14)
        pdf.cell(0, 10, f'Detailed Daily Sales Report: {report_date_str}', 0, 1, 'C')
        pdf.ln(10)
        pdf.set_font(pdf.font_family, 'B', 10)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(10, 8, '#', 1, 0, 'C', 1)
        pdf.cell(65, 8, 'Product', 1, 0, 'L', 1)
        pdf.cell(45, 8, 'Sold By', 1, 0, 'L', 1)
        pdf.cell(20, 8, 'Qty', 1, 0, 'C', 1)
        pdf.cell(25, 8, 'Unit Price', 1, 0, 'R', 1)
        pdf.cell(25, 8, 'Total', 1, 1, 'R', 1)
        pdf.set_font(pdf.font_family, '', 9)
        if not sales_data:
            pdf.cell(190, 10, 'No sales data found for this date.', 1, 1, 'C')
        else:
            for i, item in enumerate(sales_data):
                pdf.cell(10, 7, str(i + 1), 1)
                pdf.cell(65, 7, pdf.safe_text(item['product_name']), 1)
                pdf.cell(45, 7, pdf.safe_text(item['employee_name']), 1)
                pdf.cell(20, 7, str(item['sold_qty']), 1, 0, 'C')
                pdf.cell(25, 7, f"{item['unit_price']:.2f}", 1, 0, 'R')
                pdf.cell(25, 7, f"{item['total_amount']:.2f}", 1, 1, 'R')
            pdf.set_font(pdf.font_family, 'B', 10)
            pdf.cell(165, 8, 'Grand Total', 1, 0, 'R')
            pdf.cell(25, 8, f"{grand_total:.2f}", 1, 1, 'R')
        
        pdf_output = pdf.output(dest='S').encode('latin1')
        response = make_response(pdf_output)
        response.headers.set('Content-Type', 'application/pdf')
        response.headers.set('Content-Disposition', 'attachment', filename=f'Daily_Sales_Detail_{report_date}.pdf')
        return response
    except Exception as e:
        app.logger.error(f"PDF Generation Error: {e}")
        flash("Could not generate PDF due to a server error.", "danger")
        return redirect(url_for('daily_sales')) # Corrected route
    finally:
        if db_cursor:
            db_cursor.close()


@app.route('/reports/employee_performance', methods=['GET', 'POST'])
def employee_performance():
    end_date = date.today()
    start_date = end_date - timedelta(days=29)
    performance_data = []
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
        
        db_cursor = None
        try:
            db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            sql = """
                SELECT
                    e.name AS employee_name,
                    SUM(ei.sold_qty) AS total_units_sold,
                    SUM(ei.sold_qty * ei.unit_price) AS total_sales_amount
                FROM evening_item ei
                JOIN evening_settle es ON ei.settle_id = es.id
                JOIN employees e ON es.employee_id = e.id
                WHERE es.date BETWEEN %s AND %s
                GROUP BY e.id, e.name
                ORDER BY total_sales_amount DESC
            """
            db_cursor.execute(sql, (start_date, end_date))
            performance_data = db_cursor.fetchall()
        except Exception as e:
            flash(f"An error occurred while generating the report: {e}", "danger")
        finally:
            if db_cursor:
                db_cursor.close()

    start_date_str = start_date.strftime('%d %b, %Y')
    end_date_str = end_date.strftime('%d %b, %Y')
    return render_template('reports/employee_performance.html', 
                           start_date=start_date.isoformat(), 
                           end_date=end_date.isoformat(),
                           start_date_str=start_date_str,
                           end_date_str=end_date_str,
                           performance_data=performance_data)


@app.route('/reports/employee_performance/pdf/<start_date>/<end_date>')
def report_employee_performance_pdf(start_date, end_date):
    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        sql = """
            SELECT e.name AS employee_name, SUM(ei.sold_qty) AS total_units_sold, SUM(ei.sold_qty * ei.unit_price) AS total_sales_amount
            FROM evening_item ei
            JOIN evening_settle es ON ei.settle_id = es.id
            JOIN employees e ON es.employee_id = e.id
            WHERE es.date BETWEEN %s AND %s
            GROUP BY e.id, e.name
            ORDER BY total_sales_amount DESC
        """
        db_cursor.execute(sql, (start_date, end_date))
        performance_data = db_cursor.fetchall()
        
        start_date_obj = date.fromisoformat(start_date)
        end_date_obj = date.fromisoformat(end_date)
        date_range_str = f"{start_date_obj.strftime('%d %b %Y')} to {end_date_obj.strftime('%d %b %Y')}"

        pdf = PDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font(pdf.font_family, 'B', 14)
        pdf.cell(0, 10, 'Employee Performance Report', 0, 1, 'C')
        pdf.set_font(pdf.font_family, '', 10)
        pdf.cell(0, 10, date_range_str, 0, 1, 'C')
        pdf.ln(10)
        pdf.set_font(pdf.font_family, 'B', 10)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(15, 8, 'Rank', 1, 0, 'C', 1)
        pdf.cell(85, 8, 'Employee Name', 1, 0, 'L', 1)
        pdf.cell(40, 8, 'Total Units Sold', 1, 0, 'C', 1)
        pdf.cell(50, 8, 'Total Sales Amount', 1, 1, 'R', 1)
        pdf.set_font(pdf.font_family, '', 9)
        if not performance_data:
            pdf.cell(190, 10, 'No sales data found for this period.', 1, 1, 'C')
        else:
            for i, emp in enumerate(performance_data):
                pdf.cell(15, 7, str(i + 1), 1, 0, 'C')
                pdf.cell(85, 7, pdf.safe_text(emp['employee_name']), 1)
                pdf.cell(40, 7, str(emp['total_units_sold']), 1, 0, 'C')
                pdf.cell(50, 7, f"{emp['total_sales_amount']:.2f}", 1, 1, 'R')
        
        pdf_output = pdf.output(dest='S').encode('latin1')
        response = make_response(pdf_output)
        response.headers.set('Content-Type', 'application/pdf')
        response.headers.set('Content-Disposition', 'attachment', filename=f'Employee_Performance_{start_date}_to_{end_date}.pdf')
        return response
    except Exception as e:
        app.logger.error(f"PDF Generation Error: {e}")
        flash("Could not generate PDF due to a server error.", "danger")
        return redirect(url_for('employee_performance')) # Corrected route
    finally:
        if db_cursor:
            db_cursor.close()

# ... (rest of your routes) ...
@app.route('/reports/product_perfrm', methods=['GET', 'POST'])
def product_perfrm():
    end_date = date.today()
    start_date = end_date - timedelta(days=29)
    product_data = []
    sort_by = 'revenue' 
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        sort_by = request.form.get('sort_by', 'revenue')
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
        db_cursor = None
        try:
            db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            order_clause = "ORDER BY total_revenue DESC"
            if sort_by == 'quantity':
                order_clause = "ORDER BY total_units_sold DESC"
            sql = f"""
                SELECT
                    p.name AS product_name,
                    SUM(ei.sold_qty) AS total_units_sold,
                    SUM(ei.sold_qty * ei.unit_price) AS total_revenue
                FROM evening_item ei
                JOIN evening_settle es ON ei.settle_id = es.id
                JOIN products p ON ei.product_id = p.id
                WHERE es.date BETWEEN %s AND %s AND ei.sold_qty > 0
                GROUP BY p.id, p.name
                {order_clause}
            """
            db_cursor.execute(sql, (start_date, end_date))
            product_data = db_cursor.fetchall()
        except Exception as e:
            flash(f"An error occurred while generating the report: {e}", "danger")
        finally:
            if db_cursor:
                db_cursor.close()
    start_date_str = start_date.strftime('%d %b, %Y')
    end_date_str = end_date.strftime('%d %b, %Y')
    return render_template('reports/product_perfrm.html', 
                           start_date=start_date.isoformat(), 
                           end_date=end_date.isoformat(),
                           start_date_str=start_date_str,
                           end_date_str=end_date_str,
                           sort_by=sort_by,
                           product_data=product_data)

# ... (rest of your routes) ...
@app.route('/reports/profitability_reprt', methods=['GET', 'POST'])
def profitability_report():
    today = date.today()
    start_date = today.replace(day=1)
    end_date = today
    report_data = {
        "total_revenue": 0,
        "total_cogs": 0,
        "total_expenses": 0,
        "net_profit": 0
    }
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
        db_cursor = None
        try:
            db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            rev_sql = "SELECT SUM(ei.sold_qty * ei.unit_price) AS total_revenue FROM evening_item ei JOIN evening_settle es ON ei.settle_id = es.id WHERE es.date BETWEEN %s AND %s"
            db_cursor.execute(rev_sql, (start_date, end_date))
            revenue_result = db_cursor.fetchone()
            total_revenue = revenue_result['total_revenue'] or 0
            cogs_sql = "SELECT SUM(ei.sold_qty * p.purchase_price) AS total_cogs FROM evening_item ei JOIN evening_settle es ON ei.settle_id = es.id JOIN products p ON ei.product_id = p.id WHERE es.date BETWEEN %s AND %s"
            db_cursor.execute(cogs_sql, (start_date, end_date))
            cogs_result = db_cursor.fetchone()
            total_cogs = cogs_result['total_cogs'] or 0
            exp_sql = "SELECT SUM(amount) AS total_expenses FROM expenses WHERE expense_date BETWEEN %s AND %s"
            db_cursor.execute(exp_sql, (start_date, end_date))
            expense_result = db_cursor.fetchone()
            total_expenses = expense_result['total_expenses'] or 0
            net_profit = (total_revenue - total_cogs) - total_expenses
            report_data = {
                "total_revenue": float(total_revenue),
                "total_cogs": float(total_cogs),
                "total_expenses": float(total_expenses),
                "net_profit": float(net_profit)
            }
        except Exception as e:
            flash(f"An error occurred while generating the report: {e}", "danger")
        finally:
            if db_cursor:
                db_cursor.close()
    return render_template('reports/profitability_report.html', 
                           start_date=start_date.isoformat(), 
                           end_date=end_date.isoformat(),
                           start_date_str=start_date.strftime('%d %b, %Y'),
                           end_date_str=end_date.strftime('%d %b, %Y'),
                           **report_data
                           )

# ... (all other routes) ...
@app.route('/emp_list')
def emp_list():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, name, position, email FROM employees WHERE status = 'active' ORDER BY name ASC")
    employees = cur.fetchall()
    cur.close()
    return render_template('emp_list.html', employees=employees)

@app.route('/employee-ledger/<int:employee_id>')
def emp_ledger(employee_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, name, position, email, image FROM employees WHERE id = %s", [employee_id])
    employee = cur.fetchone()
    if not employee:
        flash('Employee not found!', 'danger')
        return redirect(url_for('emp_list'))
    cur.execute("""
        SELECT id, transaction_date, type, amount, description, created_at 
        FROM employee_transactions 
        WHERE employee_id = %s 
        ORDER BY transaction_date ASC, id ASC
    """, [employee_id])
    transactions_from_db = cur.fetchall()
    cur.close()
    balance = 0.0
    transactions = []
    for t in transactions_from_db:
        amount = float(t['amount'])
        if t['type'] == 'debit':
            balance += amount
        else:
            balance -= amount
        processed_t = dict(t)
        processed_t['balance'] = balance
        transactions.append(processed_t)
    return render_template('emp_ledger.html', employee=employee, transactions=transactions, final_balance=balance)

@app.route('/add-transaction/<int:employee_id>', methods=['GET', 'POST'])
def add_transaction(employee_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        trans_date = request.form['transaction_date']
        trans_type = request.form['type'] 
        amount = request.form['amount']
        description = request.form['description']
        cur.execute("""
            INSERT INTO employee_transactions (employee_id, transaction_date, type, amount, description)
            VALUES (%s, %s, %s, %s, %s)
        """, (employee_id, trans_date, trans_type, amount, description))
        mysql.connection.commit()
        cur.close()
        flash('Transaction Added Successfully!', 'success')
        return redirect(url_for('emp_ledger', employee_id=employee_id))
    cur.execute("SELECT id, name FROM employees WHERE id = %s", [employee_id])
    employee = cur.fetchone()
    cur.close()
    return render_template('add_transaction.html', employee=employee)

@app.route('/edit-transaction/<int:transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        trans_date = request.form['transaction_date']
        trans_type = request.form['type']
        amount = request.form['amount']
        description = request.form['description']
        cur.execute("UPDATE employee_transactions SET transaction_date=%s, type=%s, amount=%s, description=%s WHERE id=%s", (trans_date, trans_type, amount, description, transaction_id))
        mysql.connection.commit()
        cur.execute("SELECT employee_id FROM employee_transactions WHERE id = %s", [transaction_id])
        transaction_info = cur.fetchone()
        cur.close()
        flash('Transaction Updated Successfully!', 'info')
        return redirect(url_for('emp_ledger', employee_id=transaction_info['employee_id']))
    cur.execute("SELECT et.*, e.name FROM employee_transactions et JOIN employees e ON et.employee_id = e.id WHERE et.id = %s", [transaction_id])
    transaction = cur.fetchone()
    cur.close()
    return render_template('edit_transaction.html', transaction=transaction)

@app.route('/delete-transaction/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT employee_id FROM employee_transactions WHERE id = %s", [transaction_id])
    result = cur.fetchone()
    if result:
        employee_id = result['employee_id']
        cur.execute("DELETE FROM employee_transactions WHERE id = %s", [transaction_id])
        mysql.connection.commit()
        flash('Transaction Deleted!', 'danger')
        cur.close()
        return redirect(url_for('emp_ledger', employee_id=employee_id))
    cur.close()
    flash('Transaction not found.', 'warning')
    return redirect(url_for('emp_list'))

#============================================= Employees transaction Reports module========================  

# --- HELPER FUNCTION (Define this BEFORE the routes that use it) ---
def _fetch_transaction_data(filters):
    """
    A private helper function to query the database based on a dictionary of filters.
    Returns a list of transactions.
    """
    cur = mysql.connection.cursor()
    
    where_clauses = []
    params = []

    # Date filtering
    period = filters.get('period')
    if period == 'today':
        where_clauses.append("t.transaction_date = CURDATE()")
    elif period == 'this_week':
        where_clauses.append("YEARWEEK(t.transaction_date, 1) = YEARWEEK(CURDATE(), 1)")
    elif period == 'this_month':
        where_clauses.append("YEAR(t.transaction_date) = YEAR(CURDATE()) AND MONTH(t.transaction_date) = MONTH(CURDATE())")
    elif period == 'this_year':
        where_clauses.append("YEAR(t.transaction_date) = YEAR(CURDATE())")
    elif period == 'custom' and filters.get('start_date') and filters.get('end_date'):
        where_clauses.append("t.transaction_date BETWEEN %s AND %s")
        params.extend([filters.get('start_date'), filters.get('end_date')])

    # Employee filtering
    employee_id = filters.get('employee_id')
    if employee_id and employee_id != 'all':
        where_clauses.append("t.employee_id = %s")
        params.append(employee_id)

    # Build and execute the final query
    sql = """
        SELECT t.transaction_date, t.type, t.amount, t.description, e.name as employee_name
        FROM employee_transactions t
        JOIN employees e ON t.employee_id = e.id
    """
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    sql += " ORDER BY t.transaction_date DESC, t.id DESC"

    cur.execute(sql, tuple(params))
    transactions = cur.fetchall()
    cur.close()
    return transactions




@app.route('/transaction-report', methods=['GET', 'POST'])
def transaction_report():
    """Renders the interactive transaction analysis page."""
    # This function's logic is correct and does not need to change.
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name FROM employees WHERE status = 'active' ORDER BY name ASC")
    employees = cur.fetchall()
    cur.close()
    filters = {'period': 'this_month', 'employee_id': 'all', 'start_date': '', 'end_date': ''}
    if request.method == 'POST':
        filters['period'] = request.form.get('period')
        filters['employee_id'] = request.form.get('employee_id')
        filters['start_date'] = request.form.get('start_date')
        filters['end_date'] = request.form.get('end_date')
    transactions = _fetch_transaction_data(filters)
    total_debit = sum(t['amount'] for t in transactions if t['type'] == 'debit')
    total_credit = sum(t['amount'] for t in transactions if t['type'] == 'credit')
    net_flow = total_debit - total_credit
    return render_template('reports/transaction_report.html',
                           employees=employees,
                           transactions=transactions,
                           total_transactions=len(transactions),
                           total_debit=total_debit,
                           total_credit=total_credit,
                           net_flow=net_flow,
                           filters=filters)



@app.route('/download-transaction-report')
def download_transaction_report():
    """
    Generates and downloads a highly structured PDF or a fixed Excel file.
    This version includes robust error handling for fonts.
    """
    # Get filters from URL query parameters (no changes here)
    filters = {
        'period': request.args.get('period'),
        'employee_id': request.args.get('employee_id'),
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date')
    }
    report_format = request.args.get('format')
    transactions = _fetch_transaction_data(filters)
    
    # --- PDF GENERATION (Completely Redesigned and Bulletproof) ---
    if report_format == 'pdf':
        try:
            class PDF(FPDF):
                def header(self):
                    # Set up fonts
                    self.add_font('DejaVu', 'B', 'static/fonts/DejaVuSans-Bold.ttf')
                    self.add_font('DejaVu', '', 'static/fonts/DejaVuSans.ttf')
                    
                    # Header Title
                    self.set_font('DejaVu', 'B', 16)
                    self.cell(0, 10, 'Employee Transaction Report', 0, 1, 'C')
                    
                    # Header Subtitle
                    self.set_font('DejaVu', '', 10)
                    period_text = f"Period: {filters.get('start_date', 'N/A')} to {filters.get('end_date', 'N/A')}"
                    if filters.get('period') != 'custom':
                        period_text = f"Period: {filters.get('period').replace('_', ' ').title()}"
                    self.cell(0, 8, period_text, 0, 1, 'C')
                    self.ln(8) # Line break

                def footer(self):
                    self.set_y(-15)
                    self.set_font('DejaVu', '', 8)
                    self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
                    # Use a fixed date for the footer to avoid errors
                    self.cell(0, 10, "Generated on: " + date.today().strftime('%d-%m-%Y'), 0, 0, 'R')

                def styled_table(self, header, data):
                    # Colors, line width and bold font
                    self.set_fill_color(230, 230, 230)
                    self.set_text_color(0)
                    self.set_draw_color(220, 220, 220)
                    self.set_line_width(0.3)
                    self.set_font('DejaVu', 'B', 10)
                    
                    # Column widths
                    col_widths = [25, 55, 100, 35, 35]
                    # Header
                    for i, col in enumerate(header):
                        self.cell(col_widths[i], 10, str(col), 1, 0, 'C', 1)
                    self.ln()

                    # Data rows with zebra-striping
                    self.set_font('DejaVu', '', 9)
                    fill = False
                    for row in data:
                        # Ensure all cell data is converted to string to prevent errors
                        self.cell(col_widths[0], 8, str(row[0]), 'LR', 0, 'L', fill)
                        self.cell(col_widths[1], 8, str(row[1]), 'LR', 0, 'L', fill)
                        self.cell(col_widths[2], 8, str(row[2]), 'LR', 0, 'L', fill)
                        self.cell(col_widths[3], 8, str(row[3]), 'LR', 0, 'R', fill)
                        self.cell(col_widths[4], 8, str(row[4]), 'LR', 0, 'R', fill)
                        self.ln()
                        fill = not fill
                    self.cell(sum(col_widths), 0, '', 'T')

            pdf = PDF(orientation='L', unit='mm', format='A4')
            
            # --- CRITICAL FIX: This adds the fonts before they are used ---
            pdf.add_font('DejaVu', '', 'static/fonts/DejaVuSans.ttf')
            pdf.add_font('DejaVu', 'B', 'static/fonts/DejaVuSans-Bold.ttf')

            pdf.add_page()
            
            # Check for data
            if not transactions:
                pdf.set_font('DejaVu', '', 12)
                pdf.cell(0, 20, 'No transactions found for the selected criteria.', 0, 1, 'C')
            else:
                header = ['Date', 'Employee', 'Description', 'Debit (₹)', 'Credit (₹)']
                data = []
                for t in transactions:
                    data.append([
                        t['transaction_date'].strftime('%d-%m-%Y'),
                        t['employee_name'],
                        t['description'] or '',
                        f"{t['amount']:,.2f}" if t['type'] == 'debit' else '',
                        f"{t['amount']:,.2f}" if t['type'] == 'credit' else ''
                    ])
                pdf.styled_table(header, data)
            
            # --- FINAL FIX: This correctly outputs the PDF bytes ---
            pdf_output = pdf.output()

            return Response(pdf_output, mimetype='application/pdf', headers={'Content-Disposition': 'attachment;filename=transaction_report.pdf'})
        
        # --- CRITICAL FIX: Gracefully handle the error if font files are missing ---
        except FileNotFoundError:
            flash("PDF generation failed: Font files not found. Please ensure 'DejaVuSans.ttf' and 'DejaVuSans-Bold.ttf' are in the 'fonts' directory.", "danger")
            return redirect(url_for('transaction_report'))

    # --- EXCEL GENERATION (Unchanged but confirmed working) ---
    elif report_format == 'excel':
        # Your existing, working Excel code
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transaction Report"
        ws.append(['Date', 'Employee', 'Description', 'Debit (₹)', 'Credit (₹)'])
        for cell in ws[1]: cell.font = Font(bold=True)
        if not transactions:
            ws.append(['No transactions found for the selected criteria.'])
            ws.merge_cells('A2:E2')
            ws['A2'].alignment = Alignment(horizontal='center')
        else:
            for t in transactions:
                ws.append([t['transaction_date'], t['employee_name'], t['description'], t['amount'] if t['type'] == 'debit' else None, t['amount'] if t['type'] == 'credit' else None])
        for col_letter in ['D', 'E']:
            for cell in ws[col_letter]: cell.number_format = '"₹" #,##,##0.00'
        for col in ws.columns:
            max_length = 0
            for cell in col:
                try: 
                    if len(str(cell.value)) > max_length: max_length = len(str(cell.value))
                except: pass
            ws.column_dimensions[col[0].column_letter].width = max_length + 2
        virtual_workbook = io.BytesIO()
        wb.save(virtual_workbook)
        virtual_workbook.seek(0)
        return Response(virtual_workbook, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': 'attachment;filename=transaction_report.xlsx'})

    return redirect(url_for('transaction_report'))

# This new route lists all submitted allocations
@app.route('/morning_list')
def morning_list():
    if "loggedin" not in session:
        return redirect(url_for("morning"))

    filter_date_str = request.args.get('filter_date', date.today().isoformat())
    filter_employee = request.args.get('filter_employee', 'all')
    
    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Get employees for the filter dropdown
        db_cursor.execute("SELECT id, name FROM employees ORDER BY name")
        employees = db_cursor.fetchall()
        
        # Base query
        query = """
            SELECT ma.id, ma.date, e.name as employee_name, 
                   (SELECT COUNT(id) FROM evening_settle WHERE allocation_id = ma.id) as evening_submitted
            FROM morning_allocations ma
            JOIN employees e ON ma.employee_id = e.id
            WHERE ma.date = %s
        """
        params = [filter_date_str]
        
        # Add employee filter if selected
        if filter_employee != 'all':
            query += " AND ma.employee_id = %s"
            params.append(filter_employee)
            
        query += " ORDER BY e.name"
        
        db_cursor.execute(query, tuple(params))
        allocations = db_cursor.fetchall()
        
        return render_template('morning_list.html',
                               allocations=allocations,
                               employees=employees,
                               filter_date=filter_date_str,
                               filter_employee=filter_employee)
    except Exception as e:
        flash(f"Error loading allocations: {e}", "danger")
        return redirect(url_for('morning_list')) # Or another safe page
    finally:
        if db_cursor:
            db_cursor.close()


# This new route handles GET (showing the form) and POST (saving changes)
@app.route('/morning/edit/<int:allocation_id>', methods=['GET', 'POST'])
def morning_edit(allocation_id):
    if "loggedin" not in session:
        return redirect(url_for("morning_edit"))

    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Check if evening form is submitted, if so, block editing
        db_cursor.execute("SELECT COUNT(id) as count FROM evening_settle WHERE allocation_id = %s", (allocation_id,))
        if db_cursor.fetchone()['count'] > 0:
            flash("Cannot edit this allocation as the evening settlement has already been submitted.", "warning")
            return redirect(url_for('morning'))

        # Handle POST request (saving the data)
        if request.method == 'POST':
            product_ids = request.form.getlist('product_id[]')
            item_ids = request.form.getlist('item_id[]') # 0 for new, ID for existing
            opening_list = request.form.getlist('opening[]')
            given_list = request.form.getlist('given[]')
            price_list = request.form.getlist('price[]')

            # We need to get all *existing* item IDs for this allocation to find which ones were deleted
            db_cursor.execute("SELECT id FROM morning_allocation_items WHERE allocation_id = %s", (allocation_id,))
            existing_db_ids = {str(row['id']) for row in db_cursor.fetchall()}
            
            submitted_item_ids = set()

            for i, product_id in enumerate(product_ids):
                item_id = item_ids[i]
                open_q = int(opening_list[i] or 0)
                giv_q = int(given_list[i] or 0)
                price = float(price_list[i] or 0.0)

                if item_id == '0': # This is a new item, INSERT it
                    db_cursor.execute("""
                        INSERT INTO morning_allocation_items
                        (allocation_id, product_id, opening_qty, given_qty, unit_price)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (allocation_id, product_id, open_q, giv_q, price))
                else: # This is an existing item, UPDATE it
                    submitted_item_ids.add(item_id)
                    db_cursor.execute("""
                        UPDATE morning_allocation_items
                        SET product_id = %s, opening_qty = %s, given_qty = %s, unit_price = %s
                        WHERE id = %s AND allocation_id = %s
                    """, (product_id, open_q, giv_q, price, item_id, allocation_id))
            
            # Find which items were deleted (in DB but not in submission)
            ids_to_delete = existing_db_ids - submitted_item_ids
            if ids_to_delete:
                # Use a format string to safely create the list for the IN clause
                delete_query = "DELETE FROM morning_allocation_items WHERE id IN ({})".format(
                    ",".join(["%s"] * len(ids_to_delete))
                )
                db_cursor.execute(delete_query, tuple(ids_to_delete))

            mysql.connection.commit()
            flash("Allocation updated successfully!", "success")
            return redirect(url_for('morning_edit'))

        # Handle GET request (showing the form)
        
        # 1. Get allocation details
        db_cursor.execute("""
            SELECT ma.*, e.name as employee_name 
            FROM morning_allocations ma
            JOIN employees e ON ma.employee_id = e.id
            WHERE ma.id = %s
        """, (allocation_id,))
        allocation = db_cursor.fetchone()
        if not allocation:
            flash("Allocation not found.", "danger")
            return redirect(url_for('morning_list'))

        # 2. Get items for this allocation
        db_cursor.execute("""
            SELECT * FROM morning_allocation_items 
            WHERE allocation_id = %s 
            ORDER BY id ASC
        """, (allocation_id,))
        items = db_cursor.fetchall()

        # 3. Get all products for dropdowns (same as 'morning' route)
        db_cursor.execute("SELECT id, name, price FROM products ORDER BY name")
        products = db_cursor.fetchall()
        productOptions = ''.join(
            f'<option value="{pr["id"]}">{pr["name"]}</option>'
            for pr in products
        )
        
        return render_template('morning_edit.html',
                               allocation=allocation,
                               items=items,
                               products=products,
                               productOptions=productOptions)

    except Exception as e:
        mysql.connection.rollback()
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('morning_list'))
    finally:
        if db_cursor:
            db_cursor.close()

#
# ALSO, ADD THIS MODIFICATION TO YOUR ORIGINAL 'morning' route
#
# This makes sure the API call uses the lowercase table name
#
@app.route('/api/fetch_stock')
def fetch_stock():
    employee_id = request.args.get('employee_id')
    date_str    = request.args.get('date')

    if not employee_id or not date_str:
        return jsonify({"error": "Employee and date are required."}), 400

    try:
        current_date = date.fromisoformat(date_str)
        previous_day = current_date - timedelta(days=1)

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        #
        # BUG FIX: Changed table names to lowercase
        #
        cur.execute("""
            SELECT 
              ei.product_id,
              ei.remaining_qty  AS remaining,
              ei.unit_price     AS price
            FROM evening_item ei
            JOIN evening_settle es ON ei.settle_id = es.id
            WHERE es.employee_id = %s
              AND es.date        = %s
              AND ei.remaining_qty > 0
        """, (employee_id, previous_day))
        rows = cur.fetchall()
        cur.close()

        # Build a JS‐friendly map: { product_id: { remaining, price } }
        out = {
            str(r['product_id']): {
                'remaining': int(r['remaining']),
                'price'    : float(r['price'])
            }
            for r in rows
        }
        return jsonify(out)

    except Exception as e:
        app.logger.error("fetch_stock error: %s", e)
        return jsonify({"error": "Internal server error."}), 500

# --- FINAL: Add this to the very bottom ---
# This block is for local development
# Render will use gunicorn to run the 'app' object
if __name__ == "__main__":
    app.logger.info("Starting app in debug mode...")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))



















