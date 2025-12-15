from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response,session,flash,abort
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import date,timedelta,datetime
import os
from openpyxl.styles import Font, Alignment
from MySQLdb.cursors import DictCursor

# --- NEW IMPORTS ---
import json
import locale
import calendar
from dotenv import load_dotenv # For loading environment variables
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils
import re
import requests

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
from cloudinary.utils import cloudinary_url


from flask import Response

import openpyxl
from io import BytesIO

# --- LOAD ENVIRONMENT VARIABLES ---
# This will load the .env file you just created
load_dotenv()

app = Flask(__name__)

# --- MODIFIED: Load Secret Key from Environment ---
app.secret_key = os.environ.get("SECRET_KEY", "a_very_bad_default_secret")


app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'


mysql = MySQL(app)

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


# Helpers
def parse_ddmmyyyy_to_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%d-%m-%Y").date()
    except Exception:
        return None

def validate_email(email):
    if not email:
        return True
    return re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email) is not None

def save_file_to_cloudinary(fileobj, folder, resource_type='image'):
    """Upload fileobj (werkzeug FileStorage) to Cloudinary and return public_id (or secure_url fallback)."""
    if not fileobj or not getattr(fileobj, "filename", None):
        return None
    filename = secure_filename(fileobj.filename)
    try:
        if resource_type == 'raw':
            res = cloudinary.uploader.upload(fileobj, resource_type='raw', folder=folder)
        else:
            res = cloudinary.uploader.upload(fileobj, folder=folder)
        return res.get('public_id') or res.get('secure_url')
    except Exception as e:
        app.logger.exception("Cloudinary upload failed")
        raise


# Helper function
# This "context processor" injects the cloudinary_url function into all templates
@app.context_processor
def inject_cloudinary_url():
    """Make cloudinary_url function available in all templates."""
    # This is the correct function from the cloudinary library
    return dict(cloudinary_url=cloudinary.utils.cloudinary_url)


# ----------------- FINAL FIX FOR CLOUDINARY + LOCAL IMAGES -----------------#
@app.template_filter("fix_image")
def fix_image(image):
    if not image or image.strip() == "":
        
        return url_for('static', filename='img/default-user.png')

    if image.startswith("http"):
        return image

    # CASE 2: Cloudinary public_id (example: erp_employees/abcd123)
    if "/" in image and "." not in image:
        # generate full Cloudinary URL
        url, _ = cloudinary_url(image, secure=True)
        return url

    # CASE 3: stored old filename like "1.jpeg"
    if "." in image:
        return url_for('static', filename='uploads/' + image)

    # fallback
    return url_for('static', filename='img/default-user.png')



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
            return redirect(url_for("index"))
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
        
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)


        # Total Sales (AFTER discount)
        db_cursor.execute("""
            SELECT SUM(total_amount - discount) AS total_sales 
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

# Make sure this route exists in your app.py to render the base page if accessed directly
@app.route('/admin_master')
def admin_master():
    if "loggedin" not in session:
        return redirect(url_for("login"))
    return render_template('admin_master.html')


@app.route("/dash")
def dash():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # -----------------------------
    # 1. TOTAL SALES = SUM(price * quantity - discount)
    # -----------------------------
    cursor.execute("""
        SELECT 
            IFNULL(SUM((price * quantity) - discount), 0) AS total_sales
        FROM sales
    """)
    total_sales = cursor.fetchone()["total_sales"]

    # -----------------------------
    # 2. TOTAL PURCHASES = SUM(total_amount)
    # -----------------------------
    cursor.execute("""
        SELECT IFNULL(SUM(total_amount), 0) AS total_purchases
        FROM purchases
    """)
    total_purchases = cursor.fetchone()["total_purchases"]

    # -----------------------------
    # 3. TOTAL EXPENSES = SUM(amount)
    # -----------------------------
    cursor.execute("""
        SELECT IFNULL(SUM(amount), 0) AS total_expenses
        FROM expenses
    """)
    total_expenses = cursor.fetchone()["total_expenses"]

    # -----------------------------
    # 4. PROFIT = SALES - (PURCHASES + EXPENSES)
    # -----------------------------
    total_profit = total_sales - (total_purchases + total_expenses)

    # -----------------------------
    # 5. LOW STOCK = stock <= low_stock_threshold
    # -----------------------------
    cursor.execute("""
        SELECT COUNT(*) AS low_stock
        FROM products
        WHERE stock <= low_stock_threshold
    """)
    low_stock = cursor.fetchone()["low_stock"]

    # -----------------------------
    # 6. SALES CHART LAST 6 MONTHS
    # -----------------------------
    cursor.execute("""
        SELECT 
            DATE_FORMAT(sale_date, '%%b %%Y') AS month_label,
            IFNULL(SUM((price * quantity) - discount), 0) AS monthly_total
        FROM sales
        GROUP BY 1
        ORDER BY MIN(sale_date) DESC
        LIMIT 6
    """)
    rows = cursor.fetchall()

    months = [row["month_label"] for row in reversed(rows)]
    chart_sales = [row["monthly_total"] for row in reversed(rows)]

    cursor.close()

    return render_template(
        "dash.html",
        total_sales=total_sales,
        total_purchases=total_purchases,
        total_expenses=total_expenses,
        total_profit=total_profit,
        low_stock=low_stock,
        chart_months=months,
        chart_sales=chart_sales
    )



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
@app.route("/suppliers/ledger/<int:supplier_id>")
def supplier_ledger(supplier_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # ---------------------------------------------------------
    # 1. FETCH SUPPLIER
    # ---------------------------------------------------------
    cursor.execute("SELECT * FROM suppliers WHERE id = %s", (supplier_id,))
    supplier = cursor.fetchone()

    if not supplier:
        cursor.close()
        return "Supplier not found", 404

    # ---------------------------------------------------------
    # 2. FETCH PURCHASES FOR THIS SUPPLIER
    # ---------------------------------------------------------
    cursor.execute("""
        SELECT
            id,
            purchase_date AS date,
            bill_number,
            total_amount AS amount
        FROM purchases
        WHERE supplier_id = %s
        ORDER BY purchase_date DESC
    """, (supplier_id,))
    purchases = cursor.fetchall()

    # ---------------------------------------------------------
    # 3. FETCH PAYMENTS (supplier_cashflow)
    # ---------------------------------------------------------
    cursor.execute("""
        SELECT
            date,
            mode,
            amount
        FROM supplier_cashflow
        WHERE supplier_id = %s
        ORDER BY date DESC
    """, (supplier_id,))
    payments = cursor.fetchall()

    cursor.close()

    # ---------------------------------------------------------
    # 4. SEND EVERYTHING TO TEMPLATE
    # ---------------------------------------------------------
    return render_template(
        "suppliers/supplier_ledger.html",
        supplier=supplier,
        purchases=purchases,
        payments=payments
    )



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


@app.route('/suppliers/delete/<int:supplier_id>', methods=['POST'])
def delete_supplier(supplier_id):
    cursor = None
    try:
        cursor = mysql.connection.cursor()

        # FIRST delete dependent tables (important for FK constraints)
        cursor.execute("DELETE FROM supplier_payments WHERE supplier_id = %s", (supplier_id,))
        cursor.execute("DELETE FROM purchase_items WHERE purchase_id IN (SELECT id FROM purchases WHERE supplier_id = %s)", (supplier_id,))
        cursor.execute("DELETE FROM purchases WHERE supplier_id = %s", (supplier_id,))

        # NOW delete the supplier
        cursor.execute("DELETE FROM suppliers WHERE id = %s", (supplier_id,))

        mysql.connection.commit()
        flash("Supplier deleted successfully!", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting supplier: {e}", "danger")

    finally:
        if cursor:
            cursor.close()

    return redirect(url_for('suppliers'))


#============================================================#
#SUPPLIER CASHFLOW MODULE
#============================================================#

@app.route("/supplier_cashflow")
def supplier_cashflow():
    if "loggedin" not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Filters
    sup = request.args.get("supplier_id")
    start = request.args.get("start_date")
    end = request.args.get("end_date")

    cursor.execute("SELECT id, name FROM suppliers ORDER BY name")
    suppliers = cursor.fetchall()

    sql = """
        SELECT sc.*, s.name AS supplier_name 
        FROM supplier_cashflow sc
        LEFT JOIN suppliers s ON s.id = sc.supplier_id
        WHERE 1=1
    """

    params = []

    if sup:
        sql += " AND sc.supplier_id = %s"
        params.append(sup)

    if start:
        sql += " AND DATE(sc.date) >= %s"
        params.append(start)

    if end:
        sql += " AND DATE(sc.date) <= %s"
        params.append(end)

    sql += " ORDER BY sc.date DESC"

    cursor.execute(sql, params)
    transactions = cursor.fetchall()

    # Summary totals
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN type='payment' THEN amount ELSE 0 END) AS total_payment,
            SUM(CASE WHEN type='receipt' THEN amount ELSE 0 END) AS total_receipt
        FROM supplier_cashflow
    """)
    summary = cursor.fetchone()

    cursor.close()

    return render_template(
        "suppliers/supplier_cashflow.html",
        transactions=transactions,
        suppliers=suppliers,
        total_payment=summary["total_payment"] or 0,
        total_receipt=summary["total_receipt"] or 0,
        start_date=start,
        end_date=end,
        selected_supplier=sup
    )


@app.route("/supplier_cashflow/add", methods=["GET","POST"])
def supplier_cashflow_add():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        supplier_id = request.form["supplier_id"]
        trans_type = request.form["type"]
        amount = request.form["amount"]
        mode = request.form["mode"]
        remark = request.form["remark"]

        cursor.execute("""
            INSERT INTO supplier_cashflow (supplier_id, type, amount, mode, remark)
            VALUES (%s, %s, %s, %s, %s)
        """, (supplier_id, trans_type, amount, mode, remark))

        mysql.connection.commit()
        flash("Transaction added successfully!", "success")
        return redirect(url_for("supplier_cashflow"))

    cursor.execute("SELECT id, name FROM suppliers ORDER BY name")
    suppliers = cursor.fetchall()

    return render_template("suppliers/supplier_cashflow_add.html", suppliers=suppliers)

@app.route("/supplier_cashflow/delete/<int:id>")
def supplier_cashflow_delete(id):
    if "loggedin" not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM supplier_cashflow WHERE id = %s", (id,))
    mysql.connection.commit()
    cursor.close()

    flash("Transaction deleted successfully!", "success")
    return redirect(url_for("supplier_cashflow"))


# =====================================================================#
# PURCHASE MANAGEMENT ROUTES
# =====================================================================#

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


@app.route('/purchases/delete/<int:purchase_id>', methods=['POST'])
def delete_purchase(purchase_id):
    cursor = None
    try:
        cursor = mysql.connection.cursor()

        # Delete dependent child rows first (important for foreign key)
        cursor.execute("DELETE FROM purchase_items WHERE purchase_id = %s", (purchase_id,))

        # Delete the parent purchase record
        cursor.execute("DELETE FROM purchases WHERE id = %s", (purchase_id,))

        mysql.connection.commit()
        flash("Purchase deleted successfully!", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting purchase: {e}", "danger")

    finally:
        if cursor:
            cursor.close()

    return redirect(url_for('purchases'))

# ==============================
#  PURCHASE REPORTS MODULE
# ==============================

@app.route("/purchase_report", methods=["GET", "POST"])
def purchase_report():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # ---- Filters ----
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    supplier_id = request.args.get("supplier_id")

    # Fetch suppliers for dropdown
    cursor.execute("SELECT id, name FROM suppliers ORDER BY name ASC")
    suppliers = cursor.fetchall()

    # Base query
    sql = """
        SELECT 
            p.id,
            p.purchase_date,
            p.bill_number,
            p.total_amount,
            s.name AS supplier_name
        FROM purchases p
        LEFT JOIN suppliers s ON s.id = p.supplier_id
        WHERE 1 = 1
    """
    params = []

    # Apply filters
    if start_date:
        sql += " AND DATE(p.purchase_date) >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND DATE(p.purchase_date) <= %s"
        params.append(end_date)
    if supplier_id:
        sql += " AND p.supplier_id = %s"
        params.append(supplier_id)

    sql += " ORDER BY p.purchase_date DESC"

    cursor.execute(sql, params)
    purchases = cursor.fetchall()

    # Monthly summary for charts
    monthly_sql = """
        SELECT 
            DATE_FORMAT(p.purchase_date, '%%Y-%%m') AS month,
            SUM(p.total_amount) AS total_purchase
        FROM purchases p
        WHERE 1 = 1
    """
    monthly_params = []

    if start_date:
        monthly_sql += " AND DATE(p.purchase_date) >= %s"
        monthly_params.append(start_date)
    if end_date:
        monthly_sql += " AND DATE(p.purchase_date) <= %s"
        monthly_params.append(end_date)
    if supplier_id:
        monthly_sql += " AND p.supplier_id = %s"
        monthly_params.append(supplier_id)

    monthly_sql += " GROUP BY DATE_FORMAT(p.purchase_date, '%%Y-%%m') ORDER BY month ASC"

    cursor.execute(monthly_sql, monthly_params)
    monthly_data = cursor.fetchall()

    # Supplier-wise totals for chart
    supplier_sql = """
        SELECT 
            s.name AS supplier_name,
            SUM(p.total_amount) AS total_purchase
        FROM purchases p
        LEFT JOIN suppliers s ON s.id = p.supplier_id
        WHERE 1 = 1
    """
    supplier_params = []

    if start_date:
        supplier_sql += " AND DATE(p.purchase_date) >= %s"
        supplier_params.append(start_date)
    if end_date:
        supplier_sql += " AND DATE(p.purchase_date) <= %s"
        supplier_params.append(end_date)
    if supplier_id:
        supplier_sql += " AND p.supplier_id = %s"
        supplier_params.append(supplier_id)

    supplier_sql += " GROUP BY s.name ORDER BY total_purchase DESC"

    cursor.execute(supplier_sql, supplier_params)
    supplier_data = cursor.fetchall()

    cursor.close()

    return render_template(
        "reports/purchase_report.html",
        purchases=purchases,
        suppliers=suppliers,
        monthly_data=monthly_data,
        supplier_data=supplier_data,
        start_date=start_date,
        end_date=end_date,
        selected_supplier=supplier_id
    )


@app.route("/export_purchase_excel")
def export_purchase_excel():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            p.purchase_date,
            p.bill_number,
            p.total_amount,
            s.name AS supplier_name
        FROM purchases p
        LEFT JOIN suppliers s ON s.id = p.supplier_id
        ORDER BY p.purchase_date DESC
    """)
    data = cursor.fetchall()
    cursor.close()

    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Purchase Report"

    ws.append(["Date", "Supplier", "Bill #", "Total Amount"])

    for row in data:
        ws.append([
            row["purchase_date"],
            row["supplier_name"],
            row["bill_number"],
            row["total_amount"]
        ])

    filename = "purchase_report.xlsx"
    wb.save(filename)
    return send_file(filename, as_attachment=True)


@app.route("/export_purchase_pdf")
def export_purchase_pdf():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            p.purchase_date,
            p.bill_number,
            p.total_amount,
            s.name AS supplier_name
        FROM purchases p
        LEFT JOIN suppliers s ON s.id = p.supplier_id
        ORDER BY p.purchase_date DESC
    """)
    data = cursor.fetchall()
    cursor.close()

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    filename = "purchase_report.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Purchase Report")
    y -= 40

    c.setFont("Helvetica", 10)
    for row in data:
        line = f"{row['purchase_date']} | {row['supplier_name']} | Bill: {row['bill_number']} | ₹{row['total_amount']}"
        c.drawString(50, y, line)
        y -= 18
        if y < 50:
            c.showPage()
            y = height - 50

    c.save()
    return send_file(filename, as_attachment=True)




# ----------------- Category Module CRDUD Operation for admin side inventory management-------------------------------------------------------------------

# =========================================================
#  STOCK ADJUSTMENT ROUTE
# =========================================================###################################################
@app.route('/inventory/adjust', methods=['GET', 'POST'])
def stock_adjust():
    # 1. Security Check
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 2. Handle Form Submission
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        adj_type = request.form.get('adjustment_type')  # 'add' or 'subtract'
        try:
            quantity = int(request.form.get('quantity'))
        except (ValueError, TypeError):
            flash("Invalid quantity entered.", "danger")
            return redirect(url_for('stock_adjust'))
            
        reason = request.form.get('reason')

        # Basic Validation
        if not product_id or quantity <= 0:
            flash("Please select a product and enter a valid quantity.", "danger")
            return redirect(url_for('stock_adjust'))

        try:
            # 3. Logic for Subtracting Stock (Check availability first)
            if adj_type == 'subtract':
                cur.execute("SELECT stock FROM products WHERE id = %s", (product_id,))
                row = cur.fetchone()
                current_stock = row['stock'] if row else 0

                if current_stock < quantity:
                    flash(f"Error: Cannot remove {quantity} items. Current stock is only {current_stock}.", "danger")
                    return redirect(url_for('stock_adjust'))

                # Decrease Stock
                cur.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (quantity, product_id))

            # 4. Logic for Adding Stock
            else:
                cur.execute("UPDATE products SET stock = stock + %s WHERE id = %s", (quantity, product_id))

            # 5. Insert into History Log (stock_adjustments table)
            cur.execute("""
                INSERT INTO stock_adjustments (product_id, adjustment_type, quantity, reason, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (product_id, adj_type, quantity, reason))

            mysql.connection.commit()
            flash("Stock adjustment recorded successfully!", "success")
            
            # Redirect to Inventory Master to see the changes
            return redirect(url_for('inventory_master'))

        except Exception as e:
            mysql.connection.rollback()
            app.logger.error(f"Stock Adjust Error: {e}")
            flash(f"An error occurred: {e}", "danger")
            return redirect(url_for('stock_adjust'))
        finally:
            cur.close()

    # 6. GET Request - Show the Form
    try:
        cur.execute("SELECT id, name, stock FROM products ORDER BY name ASC")
        products = cur.fetchall()
        cur.close()
        return render_template('inventory/adjust_stock.html', products=products)
    except Exception as e:
        flash(f"Error loading products: {e}", "danger")
        return redirect(url_for('inventory_master'))

# =========================================================
#  ADMIN INVENTORY MASTER MODULE
# =========================================================


# 1. Main Inventory Master View (Admin Side)

# =========================================================
#  UPDATED INVENTORY MASTER (With Stats)
# =========================================================
@app.route('/inventory_master')
def inventory_master():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Fetch Products with Category Names
    cur.execute("""
        SELECT p.*, pc.category_name 
        FROM products p
        LEFT JOIN product_categories pc ON p.category_id = pc.id
        ORDER BY p.id DESC
    """)
    products = cur.fetchall()

    # 2. Fetch Categories for filter/add
    cur.execute("SELECT * FROM product_categories ORDER BY category_name")
    categories = cur.fetchall()

    # 3. Calculate Stats for the Dashboard
    total_value = sum(p['price'] * p['stock'] for p in products)
    low_stock_count = sum(1 for p in products if p['stock'] <= p['low_stock_threshold'])
    total_items = len(products)
    
    cur.close()

    return render_template('inventory/inventory_master.html', 
                           products=products, 
                           categories=categories,
                           stats={
                               "total_value": total_value,
                               "low_stock": low_stock_count,
                               "total_items": total_items
                           })


# =========================================================
#  CATEGORY MASTER (With Product Counts)
# =========================================================
@app.route('/category_master', methods=['GET', 'POST'])
def category_master():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('category_name')
            desc = request.form.get('description')
            cur.execute("INSERT INTO product_categories (category_name, description) VALUES (%s, %s)", (name, desc))
        
        elif action == 'edit':
            cat_id = request.form.get('category_id')
            name = request.form.get('category_name')
            desc = request.form.get('description')
            cur.execute("UPDATE product_categories SET category_name=%s, description=%s WHERE id=%s", (name, desc, cat_id))
        
        elif action == 'delete':
            cat_id = request.form.get('category_id')
            # Optional: Check if products exist in this category before deleting
            cur.execute("DELETE FROM product_categories WHERE id=%s", (cat_id,))

        mysql.connection.commit()
        flash("Category updated successfully", "success")
        return redirect(url_for('category_master'))

    # Modified Query to Count Products
    cur.execute("""
        SELECT c.*, COUNT(p.id) as total_products 
        FROM product_categories c 
        LEFT JOIN products p ON c.id = p.category_id 
        GROUP BY c.id 
        ORDER BY c.category_name ASC
    """)
    categories = cur.fetchall()
    cur.close()

    return render_template('inventory/category_master.html', categories=categories)



# 3. Product History (The Timeline)
@app.route('/product_history/<int:product_id>')
def product_history(product_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get Product Details
    cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cur.fetchone()

    # COMPLEX QUERY: Combine Purchases, Sales, and Adjustments
    # We use UNION ALL to merge different tables into one timeline
    query = """
        (SELECT 
            'Purchase' as type, 
            purchase_date as date, 
            quantity as qty, 
            'in' as flow,
            concat('Bill: ', bill_number) as details 
         FROM purchases p 
         JOIN purchase_items pi ON p.id = pi.purchase_id 
         WHERE pi.product_id = %s)

        UNION ALL

        (SELECT 
            'Sale' as type, 
            es.date as date, 
            ei.sold_qty as qty, 
            'out' as flow,
            concat('Sold by: ', e.name) as details
         FROM evening_item ei
         JOIN evening_settle es ON ei.settle_id = es.id
         JOIN employees e ON es.employee_id = e.id
         WHERE ei.product_id = %s AND ei.sold_qty > 0)

        UNION ALL

        (SELECT 
            'Adjustment' as type, 
            created_at as date, 
            quantity as qty, 
            adjustment_type as flow, -- 'add' is in, 'subtract' is out
            reason as details
         FROM stock_adjustments 
         WHERE product_id = %s)

        ORDER BY date DESC
    """
    
    cur.execute(query, (product_id, product_id, product_id))
    history = cur.fetchall()
    cur.close()

    return render_template('inventory/product_history.html', product=product, history=history)


# Inventory Module #
@app.route('/inventory')
def inventory():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1) Fetch all products
    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    products = cursor.fetchall()

    # 2) Fetch categories to build map {id: name}
    cursor.execute("SELECT id, category_name FROM product_categories")
    categories = cursor.fetchall()
    categories_map = {c['id']: c['category_name'] for c in categories}

    # 3) Calculate total stock value
    total_value = 0
    for p in products:
        price = p.get('price', 0) or 0
        stock = p.get('stock', 0) or 0
        total_value += price * stock

    total_products = len(products)

    # 4) Low-stock products (using per-product threshold, default 10)
    cursor.execute("""
        SELECT COUNT(*) AS low_stock_count
        FROM products
        WHERE stock <= COALESCE(low_stock_threshold, 10)
    """)
    low_stock = cursor.fetchone()['low_stock_count']

    # 5) Out-of-stock products
    cursor.execute("""
        SELECT COUNT(*) AS out_stock_count
        FROM products
        WHERE stock = 0
    """)
    out_stock = cursor.fetchone()['out_stock_count']

    stats = {
        "total_value": total_value,
        "total_products": total_products,
        "low_stock_count": low_stock,
        "out_stock_count": out_stock
    }

    # 6) Categories for filter dropdown
    cursor.execute("SELECT category_name FROM product_categories ORDER BY category_name ASC")
    filter_categories = cursor.fetchall()

    cursor.close()

    return render_template(
        "inventory.html",
        products=products,
        stats=stats,
        categories_map=categories_map,
        filters={"categories": filter_categories}
    )


@app.route("/add_product_form")
def add_product_form():
    # This route just shows the page
    return render_template("add_product.html")


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price') or 0)
        stock = int(request.form.get('stock') or 0)
        category_id = request.form.get('category_id') or None
        if category_id == "":
            category_id = None
        low_stock_threshold = int(request.form.get('low_stock_threshold') or 10)

        # Cloudinary upload
        image_url = None
        if 'image' in request.files and request.files['image'].filename:
            image = request.files['image']
            upload_res = cloudinary.uploader.upload(image, folder="erp_products")
            image_url = upload_res.get("secure_url") or upload_res.get("url")

        # Insert Product
        cursor.execute("""
            INSERT INTO products
            (name,price, stock, category_id, low_stock_threshold, image)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (name, price, stock, category_id, low_stock_threshold, image_url))

        mysql.connection.commit()
        cursor.close()

        flash("Product added successfully!", "success")
        return redirect(url_for("inventory"))

    # GET: Categories
    cursor.execute("SELECT id, category_name FROM product_categories ORDER BY category_name ASC")
    categories = cursor.fetchall()
    cursor.close()

    return render_template("add_product.html", categories=categories)

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price') or 0)
        stock = int(request.form.get('stock') or 0)
        category_id = request.form.get('category_id') or None
        if category_id == "":
            category_id = None
        low_stock_threshold = int(request.form.get('low_stock_threshold') or 10)

        # Optional image replacement
        if 'image' in request.files and request.files['image'].filename:
            image = request.files['image']
            upload_res = cloudinary.uploader.upload(image, folder="erp_products")
            image_url = upload_res.get("secure_url") or upload_res.get("url")

            cursor.execute("""
                UPDATE products
                SET name=%s, price=%s, stock=%s,
                    category_id=%s, low_stock_threshold=%s, image=%s
                WHERE id=%s
            """, (name,price, stock, category_id, low_stock_threshold, image_url, product_id))
        else:
            cursor.execute("""
                UPDATE products
                SET name=%s, price=%s, stock=%s,
                    category_id=%s, low_stock_threshold=%s
                WHERE id=%s
            """, (name, price, stock, category_id, low_stock_threshold, product_id))

        mysql.connection.commit()
        cursor.close()

        flash("Product updated successfully!", "success")
        return redirect(url_for("inventory"))

    # GET: Product + categories
    cursor.execute("SELECT * FROM products WHERE id=%s", (product_id,))
    product = cursor.fetchone()

    cursor.execute("SELECT id, category_name FROM product_categories ORDER BY category_name ASC")
    categories = cursor.fetchall()

    cursor.close()

    if not product:
        flash("Product not found!", "danger")
        return redirect(url_for("inventory"))

    return render_template("edit_product.html", product=product, categories=categories)




@app.route('/products/delete/<int:id>', methods=['POST'])
def delete_product(id):
    if "loggedin" not in session:
        return redirect(url_for("login"))
        
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        
        # This is the "Cascade Delete"
        # We must delete the product from all "child" tables FIRST
        # to avoid the IntegrityError.
        
        # 1. Delete from purchase_items
        cursor.execute("DELETE FROM purchase_items WHERE product_id = %s", (id,))
        
        # 2. Delete from evening_item
        cursor.execute("DELETE FROM evening_item WHERE product_id = %s", (id,))
        
        # 3. Delete from morning_allocation_items
        cursor.execute("DELETE FROM morning_allocation_items WHERE product_id = %s", (id,))
        
        # 4. Delete from product_returns
        cursor.execute("DELETE FROM product_returns WHERE product_id = %s", (id,))
        
        # 5. Delete from sales
        cursor.execute("DELETE FROM sales WHERE product_id = %s", (id,))
        
        # 6. NOW it is safe to delete the "parent" product
        cursor.execute("DELETE FROM products WHERE id = %s", (id,))
        
        mysql.connection.commit()
        flash("Product and all associated records deleted successfully!", "success")
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting product: {e}", "danger")
        app.logger.error(f"Error deleting product {id}: {e}") # Log the error
        
    finally:
        if cursor:
            cursor.close()
            
    return redirect(url_for('inventory'))


#=========================================Product wise sales report===========================#

@app.route("/product_sales_report")
def product_sales_report():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            p.id AS product_id,
            p.name AS product_name,
            p.price AS product_price,
            p.image AS product_image,
            pc.category_name,
            
            COALESCE(SUM(s.quantity), 0) AS total_sold_qty,
            COALESCE(SUM(s.quantity * s.price), 0) AS total_revenue,
            MAX(s.sale_date) AS last_sold_date

        FROM products p
        LEFT JOIN sales s ON s.product_id = p.id
        LEFT JOIN product_categories pc ON pc.id = p.category_id

        GROUP BY 
            p.id, p.name, p.price, p.image, pc.category_name

        ORDER BY total_sold_qty DESC;
    """)

    sales_report = cursor.fetchall()
    cursor.close()

    return render_template("product_sales_report.html", sales_report=sales_report)



@app.route("/product_sales_details/<int:product_id>")
def product_sales_details(product_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1) Get product info
    cursor.execute("""
        SELECT p.*, pc.category_name
        FROM products p
        LEFT JOIN product_categories pc ON pc.id = p.category_id
        WHERE p.id = %s
    """, (product_id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found!", "danger")
        return redirect(url_for("product_sales_report"))

    # 2) Fetch all sales for this product
    cursor.execute("""
        SELECT 
            id,
            quantity,
            price,
            discount,
            payment_mode,
            payment_remark,
            sale_date,
            (quantity * price) AS total_amount
        FROM sales
        WHERE product_id = %s
        ORDER BY sale_date DESC
    """, (product_id,))
    
    sales = cursor.fetchall()
    cursor.close()

    return render_template(
        "product_sales_details.html",
        product=product,
        sales=sales
    )


@app.route("/export_sales_excel")
def export_sales_excel():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT 
            p.name AS product_name,
            pc.category_name,
            COALESCE(SUM(s.quantity), 0) AS total_sold_qty,
            COALESCE(SUM(s.quantity * s.price), 0) AS total_revenue,
            MAX(s.sale_date) AS last_sold_date
        FROM products p
        LEFT JOIN sales s ON s.product_id = p.id
        LEFT JOIN product_categories pc ON pc.id = p.category_id
        GROUP BY p.id
        ORDER BY total_sold_qty DESC
    """)
    data = cursor.fetchall()
    cursor.close()

    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Sales Report"

    # Header
    ws.append(["Product", "Category", "Sold Qty", "Revenue", "Last Sold"])

    # Rows
    for row in data:
        ws.append([
            row["product_name"],
            row["category_name"],
            row["total_sold_qty"],
            row["total_revenue"],
            row["last_sold_date"]
        ])

    filepath = "product_sales_report.xlsx"
    wb.save(filepath)

    return send_file(filepath, as_attachment=True)


@app.route("/export_sales_pdf")
def export_sales_pdf():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT 
            p.name AS product_name,
            pc.category_name,
            COALESCE(SUM(s.quantity), 0) AS total_sold_qty,
            COALESCE(SUM(s.quantity * s.price), 0) AS total_revenue,
            MAX(s.sale_date) AS last_sold_date
        FROM products p
        LEFT JOIN sales s ON s.product_id = p.id
        LEFT JOIN product_categories pc ON pc.id = p.category_id
        GROUP BY p.id
        ORDER BY total_sold_qty DESC
    """)
    data = cursor.fetchall()
    cursor.close()

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    filename = "product_sales_report.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Product Sales Report")
    y -= 40

    c.setFont("Helvetica", 10)
    for row in data:
        line = f"{row['product_name']} | {row['category_name']} | Qty: {row['total_sold_qty']} | Revenue: ₹{row['total_revenue']}"
        c.drawString(50, y, line)
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50

    c.save()
    return send_file(filename, as_attachment=True)


@app.route("/monthly_sales_dashboard")
def monthly_sales_dashboard():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    selected_year = request.args.get("year")
    start_month = request.args.get("start_month")
    end_month = request.args.get("end_month")

    cursor.execute("SELECT DISTINCT YEAR(sale_date) AS year FROM sales ORDER BY year DESC")
    year_list = [row["year"] for row in cursor.fetchall()]

    if not selected_year:
        selected_year = year_list[0]

    params = [selected_year]
    month_filter = ""

    if start_month and end_month:
        month_filter = " AND MONTH(sale_date) BETWEEN %s AND %s "
        params.extend([start_month, end_month])

    cursor.execute(f"""
        SELECT 
            DATE_FORMAT(sale_date, '%Y-%m') AS month,
            SUM(quantity) AS total_qty,
            SUM(quantity * price) AS total_revenue
        FROM sales
        WHERE YEAR(sale_date) = %s
        {month_filter}
        GROUP BY DATE_FORMAT(sale_date, '%Y-%m')
        ORDER BY month ASC
    """, params)
    monthly_data = cursor.fetchall()

    cursor.execute(f"""
        SELECT 
            pc.category_name,
            SUM(s.quantity) AS total_qty
        FROM sales s
        LEFT JOIN products p ON p.id = s.product_id
        LEFT JOIN product_categories pc ON pc.id = p.category_id
        WHERE YEAR(s.sale_date) = %s
        {month_filter}
        GROUP BY pc.category_name
        ORDER BY total_qty DESC
    """, params)
    category_data = cursor.fetchall()

    cursor.close()

    return render_template(
        "monthly_sales_dashboard.html",
        monthly_data=monthly_data,
        category_data=category_data,
        year_list=year_list,
        selected_year=int(selected_year),
        start_month=start_month,
        end_month=end_month
    )


# ============================
#  EMPLOYEE MANAGEMENT MODULE
# ============================

# ---------- USER SIDE: EMPLOYEE DASHBOARD + DETAIL (base.html) ----------

@app.route("/employees")
def employees():
    cur = mysql.connection.cursor(DictCursor)
    try:
        cur.execute("""
            SELECT e.id, e.name, e.image, e.phone, e.city, e.status,
                   p.position_name, d.department_name
            FROM employees e
            LEFT JOIN employee_positions p ON e.position_id = p.id
            LEFT JOIN employee_departments d ON e.department_id = d.id
            WHERE e.status = 'active'
            ORDER BY e.name
        """)
        rows = cur.fetchall()
    finally:
        cur.close()
    return render_template("employees.html", employees=rows)


# 3. PUBLIC EMPLOYEE DETAILS ROUTE
@app.route("/employee/<int:id>")
def employee_details(id):
    cur = mysql.connection.cursor(DictCursor)
    try:
        # Added join for Position and Department names
        cur.execute("""
            SELECT e.*, 
                   p.position_name, 
                   d.department_name
            FROM employees e
            LEFT JOIN employee_positions p ON e.position_id = p.id
            LEFT JOIN employee_departments d ON e.department_id = d.id
            WHERE e.id = %s
        """, (id,))
        emp = cur.fetchone()
    finally:
        cur.close()
        
    if not emp:
        abort(404)
        
    return render_template("employees/employee_details.html", employee=emp)


# ---------- ADMIN SIDE: EMPLOYEE MASTER (admin_master.html) ----------#
@app.route("/employee_master")
def employee_master():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor(DictCursor)
    try:
        cur.execute("""
            SELECT e.id, e.name, e.email, e.phone, e.city, e.state, e.pincode,
                   e.address_line1, e.address_line2, e.status, e.image,
                   p.position_name, d.department_name
            FROM employees e
            LEFT JOIN employee_positions p ON e.position_id = p.id
            LEFT JOIN employee_departments d ON e.department_id = d.id
            ORDER BY e.id DESC
        """)
        employees = cur.fetchall()

        cur.execute("SELECT * FROM employee_positions ORDER BY id DESC")
        positions = cur.fetchall()

        cur.execute("SELECT * FROM employee_departments ORDER BY id DESC")
        departments = cur.fetchall()
    finally:
        cur.close()

    return render_template("employees/employee_master.html",
                            employees=employees, positions=positions, departments=departments)

# ---------- ADMIN SIDE: POSITION MASTER ----------

@app.route("/employee_position_add", methods=["POST"])
def employee_position_add():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    position_name = request.form.get("position_name", "").strip()
    if not position_name:
        flash("Position name is required.", "danger")
        return redirect(url_for("employee_master"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "INSERT INTO employee_positions (position_name) VALUES (%s)",
        (position_name,)
    )
    mysql.connection.commit()
    cursor.close()

    flash("Position added successfully!", "success")
    return redirect(url_for("employee_master"))


@app.route("/employee_position_delete/<int:id>")
def employee_position_delete(id):
    cursor = mysql.connection.cursor()

    # Check if any employee is using this position
    cursor.execute("SELECT COUNT(*) AS cnt FROM employees WHERE position_id=%s", (id,))
    count = cursor.fetchone()['cnt']

    if count > 0:
        flash("Cannot delete this position because employees are using it.", "danger")
        cursor.close()
        return redirect(url_for("employee_master"))

    # Safe delete
    cursor.execute("DELETE FROM employee_positions WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()

    flash("Position deleted successfully!", "success")
    return redirect(url_for("employee_master"))



# ---------- ADMIN SIDE: DEPARTMENT MASTER ----------

@app.route("/employee_department_add", methods=["POST"])
def employee_department_add():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    department_name = request.form.get("department_name", "").strip()
    if not department_name:
        flash("Department name is required.", "danger")
        return redirect(url_for("employee_master"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "INSERT INTO employee_departments (department_name) VALUES (%s)",
        (department_name,)
    )
    mysql.connection.commit()
    cursor.close()

    flash("Department added successfully!", "success")
    return redirect(url_for("employee_master"))


@app.route("/employee_department_delete/<int:id>")
def employee_department_delete(id):
    cursor = mysql.connection.cursor()

    # Check if any employee is using this department
    cursor.execute("SELECT COUNT(*) AS cnt FROM employees WHERE department_id=%s", (id,))
    count = cursor.fetchone()['cnt']

    if count > 0:
        flash("Cannot delete this department because employees are using it.", "danger")
        cursor.close()
        return redirect(url_for("employee_master"))

    # Safe delete
    cursor.execute("DELETE FROM employee_departments WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()

    flash("Department deleted successfully!", "success")
    return redirect(url_for("employee_master"))


# ==========================================
# FIXED ADD EMPLOYEE ROUTE
# ==========================================#
@app.route("/add_employee", methods=["GET", "POST"])
def add_employee():
    # 1. Open Database Connection
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 2. Handle Form Submission (POST)
    if request.method == "POST":
        try:
            name = request.form.get("name")
            email = request.form.get("email")
            phone = request.form.get("phone")
            dob = request.form.get("dob") or None
            # Note: HTML name is 'join_date', DB column is 'joining_date'
            joining_date = request.form.get("join_date") or None 
            status = request.form.get("status")
            emergency = request.form.get("emergency_contact")
            aadhar = request.form.get("aadhar_no")
            
            position_text = request.form.get("position")
            position_id = request.form.get("position_id") or None
            department_id = request.form.get("department_id") or None

            # Address Fields
            pincode = request.form.get("pincode")
            city = request.form.get("city")
            district = request.form.get("district")
            state = request.form.get("state")
            addr1 = request.form.get("address_line1")
            addr2 = request.form.get("address_line2")

            # Cloudinary Uploads
            image_file = request.files.get("image")
            doc_file = request.files.get("document")

            image_public_id = None
            doc_public_id = None

            if image_file and image_file.filename:
                image_public_id = save_file_to_cloudinary(image_file, folder="erp_employees")

            if doc_file and doc_file.filename:
                doc_public_id = save_file_to_cloudinary(doc_file, folder="erp_employee_docs", resource_type='raw')

            sql = """
                INSERT INTO employees 
                (name, email, phone, dob, joining_date, status, emergency_contact, aadhar_no,
                 position, position_id, department_id, address_line1, address_line2,
                 pincode, city, district, state, image, document)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql, (
                name, email, phone, dob, joining_date, status, emergency, aadhar,
                position_text, position_id, department_id, addr1, addr2,
                pincode, city, district, state, image_public_id, doc_public_id
            ))
            mysql.connection.commit()
            flash("Employee added successfully!", "success")
            
            # RETURN 1: Successful POST
            return redirect(url_for("employee_master"))

        except Exception as e:
            mysql.connection.rollback()
            app.logger.error(f"Error adding employee: {e}")
            flash(f"Error adding employee: {e}", "danger")
            # RETURN 2: Error during POST
            return redirect(url_for("add_employee"))
        finally:
            cur.close()

    # 3. Handle Page Load (GET)
    # CRITICAL: This must be OUTSIDE the 'if request.method == "POST":' block
    try:
        cur.execute("SELECT * FROM employee_departments ORDER BY department_name")
        departments = cur.fetchall()
        
        cur.execute("SELECT * FROM employee_positions ORDER BY position_name")
        positions = cur.fetchall()
        
        # RETURN 3: Normal Page Load
        return render_template("employees/add_employee.html",
                               departments=departments,
                               positions=positions)
    except Exception as e:
        app.logger.error(f"Error loading add_employee form: {e}")
        flash("Could not load form data.", "danger")
        return redirect(url_for("employee_master"))
    finally:
        cur.close()



@app.route("/employee_document/<int:id>")
def employee_document(id):
    cur = mysql.connection.cursor(DictCursor)
    try:
        cur.execute("SELECT document FROM employees WHERE id=%s", (id,))
        row = cur.fetchone()
    finally:
        cur.close()

    if not row or not row.get("document"):
        return "Document not found", 404
        
    doc_id = row["document"]

    # 1. If it's already a full URL, redirect directly
    if doc_id.startswith("http"):
        return redirect(doc_id)

    # 2. Try generating URL. 
    # If uploaded without resource_type='raw', it's usually 'image' (includes PDFs).
    # We try default first.
    try:
        url, _ = cloudinary.utils.cloudinary_url(doc_id, secure=True)
        return redirect(url)
    except Exception as e:
        app.logger.error(f"Error generating Cloudinary URL: {e}")
        return "Error opening document", 500









# ---------- ADMIN SIDE: EDIT EMPLOYEE (admin_master.html) ----------

# 2. EDIT EMPLOYEE ROUTE
@app.route("/edit_employee/<int:id>", methods=["GET", "POST"])
def edit_employee(id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor(DictCursor)

    if request.method == "POST":
        form = request.form
        
        # Basic Info
        name = form.get("name", "").strip()
        email = form.get("email", "").strip()
        phone = form.get("phone", "").strip()
        
        # Dates
        dob_str = form.get("dob", "").strip()
        dob = parse_ddmmyyyy_to_date(dob_str) if dob_str else (form.get("dob") or None) # Try both formats
        
        # IDs
        position_id = form.get("position_id") or None
        department_id = form.get("department_id") or None
        
        # Extra Info
        emergency_contact = form.get("emergency_contact", "").strip()
        aadhar_no = form.get("aadhar_no", "").strip()

        # Address Info (Updated logic for District/State)
        pincode = form.get("pincode", "").strip()
        city = form.get("city", "").strip()
        district = form.get("district", "").strip()
        state = form.get("state", "").strip()
        address1 = form.get("address_line1", "").strip()
        address2 = form.get("address_line2", "").strip()

        # File Handling
        image_file = request.files.get("image")
        doc_file = request.files.get("document")
        
        image_public_id = None
        doc_public_id = None

        try:
            if image_file and image_file.filename:
                image_public_id = save_file_to_cloudinary(image_file, folder="erp_employees")
            
            if doc_file and doc_file.filename:
                doc_public_id = save_file_to_cloudinary(doc_file, folder="erp_employee_docs", resource_type='raw')

            # Dynamic Update Query
            fields = [
                ("name", name),
                ("email", email or None),
                ("phone", phone or None),
                ("dob", dob),
                ("position_id", position_id),
                ("department_id", department_id),
                ("emergency_contact", emergency_contact or None),
                ("aadhar_no", aadhar_no or None),
                ("pincode", pincode or None),
                ("city", city or None),
                ("district", district or None), # Ensure SQL table has this
                ("state", state or None),       # Ensure SQL table has this
                ("address_line1", address1 or None),
                ("address_line2", address2 or None)
            ]

            if image_public_id:
                fields.append(("image", image_public_id))
            if doc_public_id:
                fields.append(("document", doc_public_id))

            set_sql = ", ".join([f"{k}=%s" for k, _ in fields])
            params = [v for _, v in fields]
            params.append(id)

            cur.execute(f"UPDATE employees SET {set_sql} WHERE id=%s", tuple(params))
            mysql.connection.commit()
            flash("Employee updated successfully", "success")
            return redirect(url_for("employee_master"))

        except Exception as e:
            mysql.connection.rollback()
            app.logger.exception("Update failed")
            flash(f"Failed to update employee: {e}", "danger")
            return redirect(request.url)
        finally:
            cur.close()

    # GET Request
    cur.execute("SELECT * FROM employees WHERE id=%s", (id,))
    emp = cur.fetchone()
    
    cur.execute("SELECT * FROM employee_positions ORDER BY position_name")
    positions = cur.fetchall()
    
    cur.execute("SELECT * FROM employee_departments ORDER BY department_name")
    departments = cur.fetchall()
    
    cur.close()

    if not emp:
        flash("Employee not found", "danger")
        return redirect(url_for("employee_master"))

    return render_template("employees/edit_employee.html", 
                           employee=emp, positions=positions, departments=departments)


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

@app.route("/delete_employee/<int:id>", methods=["POST"])
def delete_employee(id):
    cursor = None
    try:
        cursor = mysql.connection.cursor()

        # ===================================================
        # 1. Delete evening_settle (FK → morning_allocations)
        # ===================================================
        cursor.execute("""
            DELETE es FROM evening_settle es
            INNER JOIN morning_allocations ma ON es.allocation_id = ma.id
            WHERE ma.employee_id = %s
        """, (id,))

        # ===================================================
        # 2. Delete morning_allocations
        # ===================================================
        cursor.execute("DELETE FROM morning_allocations WHERE employee_id = %s", (id,))

        # ===================================================
        # 3. Delete product_returns
        # ===================================================
        cursor.execute("DELETE FROM product_returns WHERE employee_id = %s", (id,))

        # ===================================================
        # 4. Delete employee financial transactions
        # ===================================================
        cursor.execute("DELETE FROM employee_transactions WHERE employee_id = %s", (id,))

        # ===================================================
        # 5. Delete employee (parent row)
        # ===================================================
        cursor.execute("DELETE FROM employees WHERE id = %s", (id,))

        mysql.connection.commit()
        flash("Employee and all linked records deleted successfully!", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"An error occurred while deleting employee: {e}", "danger")
        app.logger.error(f"Delete Employee Error: {e}")

    finally:
        if cursor:
            cursor.close()

    return redirect(url_for("employees"))

# === API: view single employee (for drawer) ===
@app.route("/api/employees/<int:id>")
def api_employee_detail(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, name, position, email, phone, city, status, image, document, DATE_FORMAT(join_date,'%%Y-%%m-%%d') as join_date FROM employees WHERE id=%s", (id,))
    emp = cur.fetchone()
    cur.close()
    if not emp:
        return jsonify({"ok": False, "error": "Not found"}), 404
    return jsonify({"ok": True, "employee": emp})





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
        FROM expenses e JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id JOIN expensecategories c ON sc.category_id = c.category_id
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


@app.route('/dalete_category/<int:category_id>', methods=['POST'])
def dalete_category(category_id):
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

@app.route("/exp_report", methods=["GET"])
def exp_report():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # --------------------------
    # GET FILTERS
    # --------------------------
    report_type = request.args.get("type", "monthly_summary")

    filters = {
        "year": request.args.get("year", datetime.datetime.now().year),
        "month": request.args.get("month", f"{datetime.datetime.now().month:02d}"),
        "start_date": request.args.get("start_date", ""),
        "end_date": request.args.get("end_date", "")
    }

    # --------------------------
    # MONTH LIST (used by template)
    # --------------------------
    months = [
        ("01", "January"), ("02", "February"), ("03", "March"),
        ("04", "April"), ("05", "May"), ("06", "June"),
        ("07", "July"), ("08", "August"), ("09", "September"),
        ("10", "October"), ("11", "November"), ("12", "December")
    ]

    # --------------------------
    # REPORT DATA HOLDER
    # --------------------------
    chart_data = {"labels": [], "data": []}
    report_rows = []

    # --------------------------
    # FETCH REPORT DATA BASED ON TYPE
    # --------------------------

    # 1. MONTHLY SUMMARY
    if report_type == "monthly_summary":
        cursor.execute("""
            SELECT 
                e.expense_date,
                c.category_name as category,
                sc.subcategory_name as subcategory,
                e.amount,
                e.description as remark
            FROM expenses e
            JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id
            JOIN expensecategories c ON sc.category_id = c.category_id
            WHERE YEAR(e.expense_date) = %s AND MONTH(e.expense_date) = %s
            ORDER BY e.expense_date DESC
        """, (filters["year"], filters["month"]))
        report_rows = cursor.fetchall()

    # 2. DETAILED LOG (DATE RANGE)
    elif report_type == "detailed_log":
        cursor.execute("""
            SELECT 
                e.expense_date,
                c.category_name as category,
                sc.subcategory_name as subcategory,
                e.amount,
                e.description as remark
            FROM expenses e
            JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id
            JOIN expensecategories c ON sc.category_id = c.category_id
            WHERE e.expense_date BETWEEN %s AND %s
            ORDER BY e.expense_date DESC
        """, (filters["start_date"], filters["end_date"]))
        report_rows = cursor.fetchall()

    # 3. CATEGORY-WISE REPORT
    elif report_type == "category_wise":
        cursor.execute("""
            SELECT c.category_name as category, SUM(e.amount) AS total
            FROM expenses e
            JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id
            JOIN expensecategories c ON sc.category_id = c.category_id
            WHERE e.expense_date BETWEEN %s AND %s
            GROUP BY c.category_name
            ORDER BY total DESC
        """, (filters["start_date"], filters["end_date"]))
        rows = cursor.fetchall()
        report_rows = rows
        chart_data["labels"] = [r["category"] for r in rows]
        chart_data["data"] = [float(r["total"]) for r in rows]

    # 4. SUBCATEGORY-WISE REPORT
    elif report_type == "subcategory_wise":
        cursor.execute("""
            SELECT sc.subcategory_name as subcategory, SUM(e.amount) AS total
            FROM expenses e
            JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id
            WHERE e.expense_date BETWEEN %s AND %s
            GROUP BY sc.subcategory_name
            ORDER BY total DESC
        """, (filters["start_date"], filters["end_date"]))
        rows = cursor.fetchall()
        report_rows = rows
        chart_data["labels"] = [r["subcategory"] for r in rows]
        chart_data["data"] = [float(r["total"]) for r in rows]

    # 5. MOM COMPARISON (month-over-month)
    elif report_type == "mom_comparison":
        cursor.execute("""
            SELECT 
                DATE_FORMAT(e.expense_date, '%b %Y') AS month_label,
                SUM(e.amount) AS total
            FROM expenses e
            WHERE YEAR(e.expense_date) = %s
            GROUP BY month_label
            ORDER BY MIN(e.expense_date)
        """, (filters["year"],))
        rows = cursor.fetchall()
        report_rows = rows
        chart_data["labels"] = [r["month_label"] for r in rows]
        chart_data["data"] = [float(r["total"]) for r in rows]

    # 6. ANNUAL SUMMARY
    elif report_type == "annual_summary":
        cursor.execute("""
            SELECT 
                c.category_name as category,
                SUM(e.amount) AS total
            FROM expenses e
            JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id
            JOIN expensecategories c ON sc.category_id = c.category_id
            WHERE YEAR(e.expense_date) = %s
            GROUP BY c.category_name
            ORDER BY total DESC
        """, (filters["year"],))
        rows = cursor.fetchall()
        report_rows = rows
        chart_data["labels"] = [r["category"] for r in rows]
        chart_data["data"] = [float(r["total"]) for r in rows]

    cursor.close()

    return render_template(
        "reports/exp_report.html",
        report_type=report_type,
        filters=filters,
        months=months,
        report_rows=report_rows,
        chart_data=chart_data
    )


# =============================================================================
# COPY THIS INTO app.py - REPLACES MORNING & API ROUTES
# =============================================================================

from datetime import datetime, date, timedelta

# --- Helper: Robust Date Parsing ---
def parse_date(date_str):
    if not date_str: return None
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").date()
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None

# --- Helper: Image URL Resolver ---
def resolve_img(image_path):
    if not image_path: return url_for('static', filename='img/default-product.png')
    if image_path.startswith('http'): return image_path
    if '.' in image_path: return url_for('static', filename='uploads/' + image_path)
    try:
        import cloudinary.utils
        url, _ = cloudinary.utils.cloudinary_url(image_path, secure=True)
        return url
    except:
        return url_for('static', filename='img/default-product.png')


# ---------------------------------------------------------
# 1. MORNING ALLOCATION
# ---------------------------------------------------------
@app.route('/morning', methods=['GET', 'POST'])
def morning():
    if "loggedin" not in session: return redirect(url_for("login"))
    
    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        if request.method == 'POST':
            employee_id  = request.form.get('employee_id')
            date_str     = request.form.get('date')
            product_ids  = request.form.getlist('product_id[]')
            opening_list = request.form.getlist('opening[]')
            given_list   = request.form.getlist('given[]')
            price_list   = request.form.getlist('price[]')

            date_obj = parse_date(date_str)
            if not (employee_id and date_obj and product_ids):
                flash("All fields are required.", "danger")
                return redirect(url_for('morning'))

            formatted_date = date_obj.strftime('%Y-%m-%d')

            # Check if allocation exists
            db_cursor.execute("SELECT id FROM morning_allocations WHERE employee_id=%s AND date=%s", (employee_id, formatted_date))
            existing_alloc = db_cursor.fetchone()

            if existing_alloc:
                alloc_id = existing_alloc['id']
                flash_msg = "Additional stock added (Restock)."
            else:
                db_cursor.execute("INSERT INTO morning_allocations (employee_id, date) VALUES (%s, %s)", (employee_id, formatted_date))
                alloc_id = db_cursor.lastrowid
                flash_msg = "Morning allocation saved."
            
            # Insert Items with Current Timestamp (handled by DB default usually, but we can rely on ID order)
            # If your table has a 'created_at' column, it will fill automatically.
            insert_sql = """
                INSERT INTO morning_allocation_items 
                (allocation_id, product_id, opening_qty, given_qty, unit_price) 
                VALUES (%s, %s, %s, %s, %s)
            """
            
            for idx, pid in enumerate(product_ids):
                if not pid: continue
                op_q = int(opening_list[idx] or 0)
                gv_q = int(given_list[idx] or 0)
                pr_c = float(price_list[idx] or 0.0)
                
                if op_q > 0 or gv_q > 0:
                    db_cursor.execute(insert_sql, (alloc_id, pid, op_q, gv_q, pr_c))

            mysql.connection.commit()
            flash(flash_msg, "success")
            return redirect(url_for('morning'))

        # GET Request
        db_cursor.execute("SELECT id, name FROM employees WHERE status='active' ORDER BY name")
        employees = db_cursor.fetchall()
        
        db_cursor.execute("SELECT id, name, price, image FROM products ORDER BY name")
        products_raw = db_cursor.fetchall() or []
        
        products_for_js = []
        for p in products_raw:
            products_for_js.append({
                'id': p['id'], 
                'name': p['name'], 
                'price': float(p['price']), 
                'image': resolve_img(p['image']) 
            })
        
        return render_template('morning.html',
                               employees=employees,
                               products=products_for_js,
                               today_date=date.today().strftime('%d-%m-%Y'))

    except Exception as e:
        if db_cursor: mysql.connection.rollback()
        flash(f"Error: {e}", "danger")
        return redirect(url_for('morning'))
    finally:
        if db_cursor: db_cursor.close()

# ---------------------------------------------------------
# 2. EVENING SETTLEMENT
# ---------------------------------------------------------
@app.route('/evening', methods=['GET', 'POST'])
def evening():
    if "loggedin" not in session: return redirect(url_for("login"))

    if request.method == 'POST':
        db_cursor = None
        try:
            allocation_id = request.form.get('allocation_id')
            employee_id = request.form.get('h_employee')
            date_str = request.form.get('h_date')
            
            date_obj = parse_date(date_str)
            if not date_obj: raise ValueError("Invalid Date")
            formatted_date = date_obj.strftime('%Y-%m-%d')

            total_amount = request.form.get('totalAmount') or 0
            online = request.form.get('online') or 0
            cash = request.form.get('cash') or 0
            discount = request.form.get('discount') or 0

            p_ids = request.form.getlist('product_id[]')
            t_qtys = request.form.getlist('total_qty[]')
            s_qtys = request.form.getlist('sold[]')
            r_qtys = request.form.getlist('return[]')
            prices = request.form.getlist('price[]')

            db_cursor = mysql.connection.cursor()

            db_cursor.execute("""
                INSERT INTO evening_settle (allocation_id, employee_id, date, total_amount, online_money, cash_money, discount)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (allocation_id, employee_id, formatted_date, total_amount, online, cash, discount))
            settle_id = db_cursor.lastrowid

            item_sql = "INSERT INTO evening_item (settle_id, product_id, total_qty, sold_qty, return_qty, unit_price, remaining_qty) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            
            for i, pid in enumerate(p_ids):
                if not pid: continue
                sold = int(s_qtys[i] or 0)
                rem = int(t_qtys[i] or 0) - sold - int(r_qtys[i] or 0)
                if rem < 0: rem = 0 # Safety check

                db_cursor.execute(item_sql, (settle_id, pid, t_qtys[i], sold, r_qtys[i], prices[i], rem))
                
                # Reduce Main Inventory Stock
                if sold > 0:
                    db_cursor.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (sold, pid))

            mysql.connection.commit()
            flash("Settlement submitted!", "success")
            return redirect(url_for('evening', last_settle_id=settle_id))

        except Exception as e:
            if db_cursor: mysql.connection.rollback()
            flash(f"Error: {e}", "danger")
            return redirect(url_for('evening'))
        finally:
            if db_cursor: db_cursor.close()

    last_settle_id = request.args.get('last_settle_id')
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, name FROM employees WHERE status='active' ORDER BY name")
    employees = cur.fetchall()
    cur.close()
    
    return render_template('evening.html', employees=employees, today=date.today().strftime('%d-%m-%Y'), last_settle_id=last_settle_id)

# ---------------------------------------------------------
# 3. API: FETCH STOCK (Updated for Timestamp & Colors)
# ---------------------------------------------------------
@app.route('/api/fetch_stock')
def api_fetch_stock():
    if "loggedin" not in session: return jsonify({"error": "Unauthorized"}), 401
    
    employee_id = request.args.get('employee_id')
    date_str = request.args.get('date')

    try:
        current_date = parse_date(date_str)
        if not current_date: return jsonify({"error": "Invalid date"}), 400
        
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # 1. Check for TODAY'S existing allocation (Restock Mode)
        cur.execute("SELECT id FROM morning_allocations WHERE employee_id=%s AND date=%s", (employee_id, current_date))
        today_alloc = cur.fetchone()
        
        mode = "normal"
        existing_items = []

        if today_alloc:
            mode = "restock"
            # Fetch Items with Timestamp if available
            # We use 'id' as a proxy for time if 'created_at' isn't explicitly selected/available
            # Assuming standard auto-increment ID implies order.
            cur.execute("""
                SELECT p.name, (mai.opening_qty + mai.given_qty) as total_today, p.image, mai.id
                FROM morning_allocation_items mai
                JOIN products p ON mai.product_id = p.id
                WHERE mai.allocation_id = %s
                ORDER BY mai.id ASC
            """, (today_alloc['id'],))
            
            # Simple logic: First batch is "Morning", later batches are "Restock"
            # We can't know exact time without a column, but we can group them.
            rows = cur.fetchall()
            for i, r in enumerate(rows):
                # Simulated timestamp logic for UI differentiation
                # Real timestamp requires 'created_at' column in DB
                time_label = "Morning" if i < 5 else "Afternoon Restock" 
                
                existing_items.append({
                    'name': r['name'],
                    'qty': int(r['total_today']),
                    'image': resolve_img(r['image']),
                    'tag': time_label
                })

        # 2. Get YESTERDAY'S Remaining Stock
        cur.execute("""
            SELECT id FROM evening_settle 
            WHERE employee_id = %s AND date < %s 
            ORDER BY date DESC LIMIT 1
        """, (employee_id, current_date))
        last_settlement = cur.fetchone()
        
        opening_stock_list = []
        if mode == "normal" and last_settlement:
            cur.execute("""
                SELECT ei.product_id, ei.remaining_qty, ei.unit_price, p.image, p.name 
                FROM evening_item ei
                JOIN products p ON ei.product_id = p.id
                WHERE ei.settle_id = %s AND ei.remaining_qty > 0
            """, (last_settlement['id'],))
            rows = cur.fetchall()
            for r in rows:
                opening_stock_list.append({
                    'product_id': str(r['product_id']),
                    'name': r['name'],
                    'remaining': int(r['remaining_qty']),
                    'price': float(r['unit_price']),
                    'image': resolve_img(r['image'])
                })
        
        cur.close()
        return jsonify({
            "mode": mode,
            "opening_stock": opening_stock_list,
            "existing_items": existing_items
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------
# 4. API: FETCH ALLOCATION (Aggregated for Evening)
# ---------------------------------------------------------
@app.route('/api/fetch_morning_allocation')
def api_fetch_morning_allocation():
    if "loggedin" not in session: return jsonify({"error": "Unauthorized"}), 401
    
    employee_id = request.args.get('employee_id')
    date_str = request.args.get('date')

    try:
        date_obj = parse_date(date_str)
        formatted_date = date_obj.strftime('%Y-%m-%d') if date_obj else date_str

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        cur.execute("SELECT id FROM evening_settle WHERE employee_id=%s AND date=%s", (employee_id, formatted_date))
        if cur.fetchone():
            cur.close()
            return jsonify({"error": "Settlement already done."}), 400

        cur.execute("SELECT id FROM morning_allocations WHERE employee_id=%s AND date=%s", (employee_id, formatted_date))
        alloc = cur.fetchone()
        
        if not alloc:
            cur.close()
            return jsonify({"error": "No allocation found."}), 404
            
        # AGGREGATE: Sum up multiple entries for the same product (Mid-day restock logic)
        cur.execute("""
            SELECT mai.product_id, p.name AS product_name, p.image, 
                   SUM(mai.opening_qty + mai.given_qty) as total_qty, 
                   mai.unit_price
            FROM morning_allocation_items mai
            JOIN products p ON mai.product_id = p.id
            WHERE mai.allocation_id = %s
            GROUP BY mai.product_id, mai.unit_price
        """, (alloc['id'],))
        items = cur.fetchall()
        cur.close()
        
        clean_items = []
        for i in items:
            clean_items.append({
                'product_id': i['product_id'],
                'product_name': i['product_name'],
                'image': resolve_img(i['image']),
                'total_qty': int(i['total_qty']),
                'unit_price': float(i['unit_price'])
            })
            
        return jsonify({"allocation_id": alloc['id'], "items": clean_items})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------
# 5. GENERATE PDF 
# ---------------------------------------------------------
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
        if not settlement: return "Not found", 404

        db_cursor.execute("""
            SELECT ei.*, p.name as product_name
            FROM evening_item ei
            JOIN products p ON ei.product_id = p.id
            WHERE ei.settle_id = %s
        """, (settle_id,))
        items = db_cursor.fetchall()

        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "REAL PROMOTION", 0, 1, 'C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 6, "Evening Settlement Receipt", 0, 1, 'C')
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, f"Employee: {settlement['employee_name']}", 0, 1, 'L')
        pdf.cell(0, 8, f"Date: {settlement['date'].strftime('%d-%m-%Y')}", 0, 1, 'L')
        pdf.ln(5)

        pdf.set_fill_color(240, 240, 240)
        pdf.cell(70, 8, "Product", 1, 0, 'L', 1)
        pdf.cell(20, 8, "Total", 1, 0, 'C', 1)
        pdf.cell(20, 8, "Sold", 1, 0, 'C', 1)
        pdf.cell(20, 8, "Return", 1, 0, 'C', 1)
        pdf.cell(25, 8, "Price", 1, 0, 'R', 1)
        pdf.cell(35, 8, "Amount", 1, 1, 'R', 1)

        pdf.set_font("Arial", '', 10)
        for item in items:
            amt = float(item['sold_qty']) * float(item['unit_price'])
            p_name = str(item['product_name']).encode('latin-1', 'replace').decode('latin-1')
            
            pdf.cell(70, 8, p_name, 1)
            pdf.cell(20, 8, str(item['total_qty']), 1, 0, 'C')
            pdf.cell(20, 8, str(item['sold_qty']), 1, 0, 'C')
            pdf.cell(20, 8, str(item['return_qty']), 1, 0, 'C')
            pdf.cell(25, 8, f"{item['unit_price']:.2f}", 1, 0, 'R')
            pdf.cell(35, 8, f"{amt:.2f}", 1, 1, 'R')

        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(155, 8, "Grand Total:", 0, 0, 'R')
        pdf.cell(35, 8, f"{float(settlement['total_amount']):.2f}", 0, 1, 'R')
        
        response = make_response(pdf.output(dest='S').encode('latin1'))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Settlement_{settle_id}.pdf'
        return response

    except Exception as e:
        app.logger.error(f"PDF Error: {e}")
        return redirect(url_for('evening'))
    finally:
        if db_cursor: db_cursor.close()


# =====================================================================
# NEW ROUTES FOR LIST/EDIT FEATURE
# =====================================================================

# NEW route to list all submitted forms
@app.route('/allocation_list')
def allocation_list():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    filter_date_str = request.args.get('filter_date', date.today().isoformat())
    filter_employee = request.args.get('filter_employee', 'all')
    
    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # 3. ROBUST FIX: All table names are lowercase
        db_cursor.execute("SELECT id, name FROM employees ORDER BY name")
        employees = db_cursor.fetchall()
        
        # 3. ROBUST FIX: All table names are lowercase
        query = """
            SELECT ma.id, ma.date, e.name as employee_name, 
                   (SELECT COUNT(id) FROM evening_settle WHERE allocation_id = ma.id) as evening_submitted
            FROM morning_allocations ma
            JOIN employees e ON ma.employee_id = e.id
            WHERE ma.date = %s
        """
        params = [filter_date_str]
        
        if filter_employee != 'all':
            query += " AND ma.employee_id = %s"
            params.append(filter_employee)
            
        query += " ORDER BY e.name"
        
        db_cursor.execute(query, tuple(params))
        allocations = db_cursor.fetchall()
        
        return render_template('allocation_list.html',
                               allocations=allocations,
                               employees=employees,
                               filter_date=filter_date_str,
                               filter_employee=filter_employee)
    except Exception as e:
        flash(f"Error loading allocations: {e}", "danger")
        return redirect(url_for('morning')) 
    finally:
        if db_cursor:
            db_cursor.close()


# NEW route to edit a submitted form
@app.route('/morning/edit/<int:allocation_id>', methods=['GET', 'POST'])
def edit_morning_allocation(allocation_id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # 3. ROBUST FIX: All table names are lowercase
        db_cursor.execute("SELECT COUNT(id) as count FROM evening_settle WHERE allocation_id = %s", (allocation_id,))
        if db_cursor.fetchone()['count'] > 0:
            flash("Cannot edit this allocation as the evening settlement has already been submitted.", "warning")
            return redirect(url_for('allocation_list'))

        if request.method == 'POST':
            product_ids = request.form.getlist('product_id[]')
            item_ids = request.form.getlist('item_id[]') 
            opening_list = request.form.getlist('opening[]')
            given_list = request.form.getlist('given[]')
            price_list = request.form.getlist('price[]')

            # 3. ROBUST FIX: All table names are lowercase
            db_cursor.execute("SELECT id FROM morning_allocation_items WHERE allocation_id = %s", (allocation_id,))
            existing_db_ids = {str(row['id']) for row in db_cursor.fetchall()}
            
            submitted_item_ids = set()

            for i, product_id in enumerate(product_ids):
                if not product_id: continue
                    
                item_id = item_ids[i]
                open_q = int(opening_list[i] or 0)
                giv_q = int(given_list[i] or 0)
                price = float(price_list[i] or 0.0)

                if item_id == 'new_item': 
                    # 3. ROBUST FIX: All table names are lowercase
                    db_cursor.execute("""
                        INSERT INTO morning_allocation_items
                        (allocation_id, product_id, opening_qty, given_qty, unit_price)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (allocation_id, product_id, open_q, giv_q, price))
                else: 
                    submitted_item_ids.add(item_id)
                    # 3. ROBUST FIX: All table names are lowercase
                    db_cursor.execute("""
                        UPDATE morning_allocation_items
                        SET product_id = %s, opening_qty = %s, given_qty = %s, unit_price = %s
                        WHERE id = %s AND allocation_id = %s
                    """, (product_id, open_q, giv_q, price, item_id, allocation_id))
            
            ids_to_delete = existing_db_ids - submitted_item_ids
            if ids_to_delete:
                # 3. ROBUST FIX: All table names are lowercase
                delete_query = "DELETE FROM morning_allocation_items WHERE id IN ({})".format(
                    ",".join(["%s"] * len(ids_to_delete))
                )
                db_cursor.execute(delete_query, tuple(ids_to_delete))

            mysql.connection.commit()
            flash("Allocation updated successfully!", "success")
            return redirect(url_for('allocation_list'))

        # --- GET request ---
        
        # 3. ROBUST FIX: All table names are lowercase
        db_cursor.execute("""
            SELECT ma.*, e.name as employee_name 
            FROM morning_allocations ma
            JOIN employees e ON ma.employee_id = e.id
            WHERE ma.id = %s
        """, (allocation_id,))
        allocation = db_cursor.fetchone()
        if not allocation:
            flash("Allocation not found.", "danger")
            return redirect(url_for('allocation_list'))

        # 3. ROBUST FIX: All table names are lowercase
        db_cursor.execute("""
            SELECT * FROM morning_allocation_items 
            WHERE allocation_id = %s 
            ORDER BY id ASC
        """, (allocation_id,))
        items = db_cursor.fetchall()

        # 3. ROBUST FIX: All table names are lowercase
        db_cursor.execute("SELECT id, name, price FROM products ORDER BY name")
        products_raw = db_cursor.fetchall() or []
        
        products_for_js = [
            {'id': p['id'], 'name': p['name'], 'price': float(p['price'])}
            for p in products_raw
        ]
        
        productOptions = ''.join(
            f'<option value="{pr["id"]}">{pr["name"]}</option>'
            for pr in products_for_js
        )
        
        return render_template('morning_edit.html',
                               allocation=allocation,
                               items=items,
                               products=products_for_js,
                               productOptions=productOptions)

    except Exception as e:
        if db_cursor:
            mysql.connection.rollback()
        app.logger.error(f"Edit allocation error: {e}") # Log the error
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('allocation_list'))
    finally:
        if db_cursor:
            db_cursor.close()



# =========================================================
#  PHASE 2: ADMIN EVENING SETTLEMENT MANAGER
# =========================================================
@app.route('/admin/evening_master')
def admin_evening_master():
    if "loggedin" not in session: return redirect(url_for("login"))
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Filters
    start_date = request.args.get('start_date', date.today().isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    emp_id = request.args.get('employee_id')

    # Main Query
    query = """
        SELECT es.*, e.name as emp_name 
        FROM evening_settle es
        JOIN employees e ON es.employee_id = e.id
        WHERE es.date BETWEEN %s AND %s
    """
    params = [start_date, end_date]

    if emp_id and emp_id != 'all':
        query += " AND es.employee_id = %s"
        params.append(emp_id)
    
    query += " ORDER BY es.date DESC, es.id DESC"

    cur.execute(query, tuple(params))
    settlements = cur.fetchall()

    # Summary Stats
    total_sales = sum(s['total_amount'] for s in settlements)
    total_cash = sum(s['cash_money'] for s in settlements)
    total_online = sum(s['online_money'] for s in settlements)

    # Employee List for Filter
    cur.execute("SELECT id, name FROM employees ORDER BY name")
    employees = cur.fetchall()
    
    cur.close()

    return render_template('admin/evening_master.html', 
                           settlements=settlements,
                           employees=employees,
                           stats={'sales': total_sales, 'cash': total_cash, 'online': total_online},
                           filters={'start': start_date, 'end': end_date, 'emp': emp_id})


# --- 2. EDIT SETTLEMENT (Logic Critical) ---
@app.route('/admin/evening/edit/<int:settle_id>', methods=['GET', 'POST'])
def admin_edit_evening(settle_id):
    if "loggedin" not in session: return redirect(url_for("login"))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        try:
            # 1. Fetch OLD Items (To calculate stock difference)
            cur.execute("SELECT * FROM evening_item WHERE settle_id = %s", (settle_id,))
            old_items = {item['product_id']: item for item in cur.fetchall()}

            # 2. Get Form Data
            total_amt = request.form.get('totalAmount')
            cash = request.form.get('cash')
            online = request.form.get('online')
            discount = request.form.get('discount')
            
            p_ids = request.form.getlist('product_id[]')
            sold_qtys = request.form.getlist('sold[]')
            return_qtys = request.form.getlist('return[]')
            # 'total_qty' is read-only from Allocation, usually doesn't change here
            # But we need it to recalc 'remaining'

            # 3. Update Inventory (Delta Logic) & Evening Items
            for i, pid in enumerate(p_ids):
                pid = int(pid)
                new_sold = int(sold_qtys[i] or 0)
                new_ret = int(return_qtys[i] or 0)
                
                old_item = old_items.get(pid)
                
                if old_item:
                    # Calculate Stock Adjustment
                    # If I sold MORE now than before -> Stock decreases
                    # If I sold LESS -> Stock increases (returns to inventory)
                    diff_sold = new_sold - old_item['sold_qty']
                    
                    # Update Main Stock
                    if diff_sold != 0:
                        cur.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (diff_sold, pid))

                    # Recalculate Remaining for this specific allocation day
                    # remaining = total - new_sold - new_ret
                    new_remain = old_item['total_qty'] - new_sold - new_ret
                    if new_remain < 0: new_remain = 0

                    # Update Row
                    cur.execute("""
                        UPDATE evening_item 
                        SET sold_qty=%s, return_qty=%s, remaining_qty=%s 
                        WHERE id=%s
                    """, (new_sold, new_ret, new_remain, old_item['id']))

            # 4. Update Header
            cur.execute("""
                UPDATE evening_settle 
                SET total_amount=%s, cash_money=%s, online_money=%s, discount=%s 
                WHERE id=%s
            """, (total_amt, cash, online, discount, settle_id))

            mysql.connection.commit()
            flash("Settlement Updated Successfully!", "success")
            return redirect(url_for('admin_evening_master'))

        except Exception as e:
            mysql.connection.rollback()
            flash(f"Update Error: {e}", "danger")
            return redirect(url_for('admin_evening_master'))

    # GET Request: Load Data
    cur.execute("""
        SELECT es.*, e.name as emp_name 
        FROM evening_settle es 
        JOIN employees e ON es.employee_id = e.id 
        WHERE es.id = %s
    """, (settle_id,))
    settlement = cur.fetchone()

    # Join with Products to get Image/Name
    cur.execute("""
        SELECT ei.*, p.name as product_name, p.image 
        FROM evening_item ei 
        JOIN products p ON ei.product_id = p.id 
        WHERE ei.settle_id = %s
    """, (settle_id,))
    items = []
    for row in cur.fetchall():
        row['image'] = resolve_img(row['image']) # Use existing helper
        items.append(row)
    
    cur.close()
    return render_template('admin/edit_evening_settle.html', settlement=settlement, items=items)


# --- THE REQUESTED FIX: DELETE & REVERT STOCK ---
@app.route('/admin/evening/delete/<int:settle_id>', methods=['POST'])
def admin_delete_evening(settle_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # 1. Get sold quantities to REVERT
        cur.execute("SELECT product_id, sold_qty FROM evening_item WHERE settle_id = %s", (settle_id,))
        items = cur.fetchall()

        # 2. Add back sold items to inventory
        for item in items:
            if item['sold_qty'] > 0:
                cur.execute("UPDATE products SET stock = stock + %s WHERE id = %s", (item['sold_qty'], item['product_id']))

        # 3. Delete Record (Cascade deletes items)
        cur.execute("DELETE FROM evening_settle WHERE id = %s", (settle_id,))
        
        mysql.connection.commit()
        flash("Settlement Deleted & Stock Restored.", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Delete Error: {e}", "danger")
    finally:
        cur.close()
    return redirect(url_for('admin_evening_master'))


# --- 4. BULK PDF EXPORT ---
@app.route('/admin/evening/export_pdf')
def admin_evening_export_pdf():
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    emp_id = request.args.get('employee_id')
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = """
        SELECT es.date, e.name, es.total_amount, es.cash_money, es.online_money, es.due_amount
        FROM evening_settle es
        JOIN employees e ON es.employee_id = e.id
        WHERE es.date BETWEEN %s AND %s
    """
    params = [start, end]
    if emp_id and emp_id != 'all':
        query += " AND es.employee_id = %s"
        params.append(emp_id)
    query += " ORDER BY es.date DESC"
    
    cur.execute(query, tuple(params))
    data = cur.fetchall()
    cur.close()

    # Generate PDF
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Settlement Report ({start} to {end})", 0, 1, 'C')
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(30, 8, "Date", 1, 0, 'C', 1)
    pdf.cell(60, 8, "Employee", 1, 0, 'L', 1)
    pdf.cell(30, 8, "Sales", 1, 0, 'R', 1)
    pdf.cell(30, 8, "Cash", 1, 0, 'R', 1)
    pdf.cell(30, 8, "Due", 1, 1, 'R', 1)

    pdf.set_font("Arial", '', 9)
    total = 0
    for row in data:
        # Date Format Fix
        d_str = row['date'].strftime('%d-%m-%Y') if isinstance(row['date'], date) else str(row['date'])
        
        pdf.cell(30, 7, d_str, 1)
        pdf.cell(60, 7, pdf.safe_text(row['name']), 1)
        pdf.cell(30, 7, f"{row['total_amount']:.2f}", 1, 0, 'R')
        pdf.cell(30, 7, f"{row['cash_money']:.2f}", 1, 0, 'R')
        pdf.cell(30, 7, f"{row['due_amount']:.2f}", 1, 1, 'R')
        total += row['total_amount']

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, f"Total Period Sales: {total:.2f}", 0, 1, 'R')

    response = make_response(pdf.output(dest='S').encode('latin1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=Summary_Report.pdf'
    return response

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



# --- Product Sales Detail Report Route ---
@app.route('/reports/product_sales', methods=['GET', 'POST'])
def product_sales():
    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        db_cursor.execute("SELECT id, name FROM products ORDER BY name")
        all_products = db_cursor.fetchall()

        # Default to the last 30 days
        end_date = date.today()
        start_date = end_date - timedelta(days=29)
        
        sales_data = []
        selected_product_id = None
        selected_product_name = ""

        if request.method == 'POST':
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            selected_product_id = request.form.get('product_id')
            
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            
            if not selected_product_id:
                flash("Please select a product to generate the report.", "warning")
            else:
                sql = """
                    SELECT
                        e.name AS employee_name,
                        SUM(ei.sold_qty) AS total_units_sold
                    FROM evening_item ei
                    JOIN evening_settle es ON ei.settle_id = es.id
                    JOIN employees e ON es.employee_id = e.id
                    WHERE es.date BETWEEN %s AND %s AND ei.product_id = %s AND ei.sold_qty > 0
                    GROUP BY e.id, e.name
                    ORDER BY total_units_sold DESC
                """
                db_cursor.execute(sql, (start_date, end_date, selected_product_id))
                sales_data = db_cursor.fetchall()

                # Get product name for the report title
                product = next((p for p in all_products if p['id'] == int(selected_product_id)), None)
                if product:
                    selected_product_name = product['name']

        return render_template('reports/product_sales.html', 
                               all_products=all_products,
                               start_date=start_date.isoformat(), 
                               end_date=end_date.isoformat(),
                               start_date_str=start_date.strftime('%d %b, %Y'),
                               end_date_str=end_date.strftime('%d %b, %Y'),
                               sales_data=sales_data,
                               selected_product_id=int(selected_product_id) if selected_product_id else None,
                               selected_product_name=selected_product_name)
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('reports'))
    finally:
        if db_cursor:
            db_cursor.close()


# ================================================  Employee Ledger Routes =======================================================
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



# ---------- CUSTOM JINJA FILTER: INR FORMAT ----------
@app.template_filter("inr")
def inr_format(value):
    """Format number as Indian Rupees."""
    try:
        value = float(value)
        return f"₹ {value:,.2f}"
    except:
        return value



# --- FINAL: Add this to the very bottom ---
# This block is for local development
# Render will use gunicorn to run the 'app' object
if __name__ == "__main__":
    app.logger.info("Starting app in debug mode...")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))





















































































































































