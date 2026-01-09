from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response,session,flash,abort
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime, date, timedelta
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
from cloudinary.utils import cloudinary_url
# --- END NEW IMPORTS ---

from fpdf import FPDF
import csv
from io import StringIO
from decimal import Decimal
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


# In app.py
from cloudinary.utils import cloudinary_url
app.jinja_env.globals.update(cloudinary_url=cloudinary_url)



def safe_date_format(date_obj, format='%d-%m-%Y', default='N/A'):
    """Safely formats a date object, returning default if None."""
    if date_obj:
        return date_obj.strftime(format)
    return default

# --- TIMEZONE HELPERS ---
def get_ist_now():
    """Returns current time in IST (UTC + 5:30)"""
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

def parse_date_input(date_str):
    """Converts dd-mm-yyyy to yyyy-mm-dd for MySQL"""
    try:
        return datetime.strptime(date_str, '%d-%m-%Y').strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        # Return as-is if it fails (might already be correct or None)
        return date_str

# --- VIEW EVENING SETTLEMENT DETAILS ---
@app.route('/evening/view/<int:settle_id>')
def view_evening_settlement(settle_id):
    if "loggedin" not in session: return redirect(url_for("login"))
    
    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Fetch Header Info
    # Added 'due_note' and used 'e.phone'
    cursor.execute("""
        SELECT es.*, 
               IFNULL(es.total_amount, 0) as total_amount,
               IFNULL(es.cash_money, 0) as cash_money,
               IFNULL(es.online_money, 0) as online_money,
               IFNULL(es.discount, 0) as discount,
               IFNULL(es.emp_credit_amount, 0) as emp_credit_amount,
               IFNULL(es.emp_debit_amount, 0) as emp_debit_amount,
               IFNULL(es.due_note, '') as due_note,
               e.name as emp_name, e.image as emp_image, e.phone as emp_mobile
        FROM evening_settle es
        JOIN employees e ON es.employee_id = e.id
        WHERE es.id = %s
    """, (settle_id,))
    settlement = cursor.fetchone()
    
    if not settlement:
        flash("Record not found.", "danger")
        return redirect(url_for('admin_evening_master'))
        
    # Process Header Data
    if settlement['emp_image']:
        if not settlement['emp_image'].startswith('http'):
             settlement['emp_image'] = url_for('static', filename='uploads/' + settlement['emp_image'])
    else:
        settlement['emp_image'] = url_for('static', filename='img/default-user.png')
        
    if isinstance(settlement['date'], (date, datetime)):
        settlement['formatted_date'] = settlement['date'].strftime('%d-%m-%Y')
    else:
        settlement['formatted_date'] = str(settlement['date'])

    # Calculate Due Amount safely
    total = float(settlement['total_amount'])
    paid = float(settlement['cash_money']) + float(settlement['online_money']) + float(settlement['discount'])
    settlement['due_amount'] = total - paid

    # 2. Fetch Product Items
    cursor.execute("""
        SELECT ei.*, p.name as product_name, p.image 
        FROM evening_item ei
        JOIN products p ON ei.product_id = p.id
        WHERE ei.settle_id = %s
    """, (settle_id,))
    items = cursor.fetchall()
    
    # Process Item Images
    for item in items:
        if item['image']:
            if not item['image'].startswith('http'):
                 item['image'] = url_for('static', filename='uploads/' + item['image'])
        else:
            item['image'] = url_for('static', filename='img/default-product.png')

    return render_template('admin/view_evening.html', settlement=settlement, items=items)




import pytz # Recommended: pip install pytz

# Helper to get current IST time
def get_ist_now():
    # If pytz is available
    try:
        ist = pytz.timezone('Asia/Kolkata')
        return datetime.now(ist)
    except:
        # Fallback manual calculation
        return datetime.utcnow() + timedelta(hours=5, minutes=30)

# Helper to parse dd-mm-yyyy to yyyy-mm-dd for MySQL
def parse_date_input(date_str):
    try:
        # Tries to parse dd-mm-yyyy
        return datetime.strptime(date_str, '%d-%m-%Y').strftime('%Y-%m-%d')
    except ValueError:
        # If it fails, maybe it's already yyyy-mm-dd or invalid
        return date_str 

# --- ROUTE: OFFICE SALES FORM ---
@app.route('/office_sales', methods=['GET', 'POST'])
def office_sales():
    if "loggedin" not in session: return redirect(url_for("login"))
    
    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        try:
            # 1. Customer & Header Info
            c_name = request.form.get('customer_name')
            c_mobile = request.form.get('customer_mobile')
            c_addr = request.form.get('customer_address')
            sales_person = request.form.get('sales_person')
            
            # Date Handling
            b_date_str = request.form.get('bill_date')
            try:
                if b_date_str:
                    bill_date = datetime.strptime(b_date_str, '%d-%m-%Y').strftime('%Y-%m-%d')
                else:
                    bill_date = date.today()
            except ValueError:
                bill_date = date.today()

            # 2. Financials
            discount = float(request.form.get('discount') or 0)
            online_amt = float(request.form.get('online') or 0)
            cash_amt = float(request.form.get('cash') or 0)
            due_note = request.form.get('due_note')
            
            # 3. Products
            p_ids = request.form.getlist('product_id[]')
            qtys = request.form.getlist('qty[]')
            prices = request.form.getlist('price[]')
            
            total_amt = 0
            
            # Insert Header
            cursor.execute("""
                INSERT INTO office_sales 
                (customer_name, customer_mobile, customer_address, sales_person, sale_date, discount, online_amount, cash_amount, due_note)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (c_name, c_mobile, c_addr, sales_person, bill_date, discount, online_amt, cash_amt, due_note))
            sale_id = cursor.lastrowid
            
            # Process Items
            for i, pid in enumerate(p_ids):
                qty = int(qtys[i])
                price = float(prices[i])
                
                # Check Stock
                cursor.execute("SELECT stock, name FROM products WHERE id=%s", (pid,))
                prod = cursor.fetchone()
                if prod and prod['stock'] < qty:
                    raise Exception(f"Insufficient stock for {prod['name']}")

                # Deduct Stock
                cursor.execute("UPDATE products SET stock = stock - %s WHERE id=%s", (qty, pid))
                
                # Calculate Item Total
                item_total = qty * price

                cursor.execute("""
                    INSERT INTO office_sale_items (sale_id, product_id, qty, unit_price, total_price)
                    VALUES (%s, %s, %s, %s, %s)
                """, (sale_id, pid, qty, price, item_total))
                
                total_amt += item_total
            
            # Final Update
            final_amt = total_amt - discount
            cursor.execute("""
                UPDATE office_sales 
                SET sub_total=%s, final_amount=%s 
                WHERE id=%s
            """, (total_amt, final_amt, sale_id))
            
            conn.commit()
            
            return redirect(url_for('download_office_bill', sale_id=sale_id))
            
        except Exception as e:
            conn.rollback()
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('office_sales'))

    # GET: Fetch Products
    cursor.execute("SELECT id, name, price, stock, image FROM products ORDER BY name")
    products = cursor.fetchall()
    
    for p in products:
        if p['image'] and not p['image'].startswith('http'):
            p['image'] = url_for('static', filename='uploads/' + p['image'])
        elif not p['image']:
            p['image'] = url_for('static', filename='img/default-product.png')

    return render_template('office_sales.html', products=products, today=date.today().strftime('%d-%m-%Y'))


# ... (Previous imports and setup code) ...

# --- PDF GENERATOR CLASS (INTERNAL) ---
class PDFGenerator(FPDF):
    def __init__(self, title_type="Morning"):
        super().__init__()
        self.title_type = title_type
        self.company_name = "REAL PROMOTION"
        self.slogan = "SINCE 2005"
        self.address_lines = [
            "Real Promotion, G/12, Tulsimangalam Complex,",
            "B/h. Trimurti Complex, Ghodiya Bazar,",
            "Nadiad-387001, Gujarat, India"
        ]
        self.contact = "+91 96623 22476 | help@realpromotion.in"
        self.gst_no = "GSTIN: " # Add GST if available

    def header(self):
        # ... (Existing header logic for Morning/Evening) ...
        # Only print default header if NOT generating office bill (which handles its own header)
        # OR we can make generate_office_bill call a different header method.
        # For simplicity, let's keep generate_office_bill independent or handle the flag.
        if self.title_type in ["Morning", "Evening"]:
             # Company Header
            self.set_font('Arial', 'B', 24)
            self.set_text_color(26, 35, 126) # Dark Blue
            self.cell(0, 10, self.company_name, 0, 1, 'C')
            
            self.set_font('Arial', 'B', 10)
            self.set_text_color(100, 100, 100) # Grey
            self.cell(0, 5, self.slogan, 0, 1, 'C')
            self.ln(2)
            
            self.set_font('Arial', '', 9)
            self.set_text_color(50, 50, 50)
            for line in self.address_lines:
                self.cell(0, 4, line, 0, 1, 'C')
            self.cell(0, 4, self.contact, 0, 1, 'C')
            self.set_font('Arial', 'B', 9)
            self.cell(0, 4, self.gst_no, 0, 1, 'C')
            self.ln(5)
            
            # Divider
            self.set_draw_color(200, 200, 200)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(5)

            # Title
            self.set_font('Arial', 'B', 16)
            self.set_text_color(0, 0, 0)
            if self.title_type == "Morning":
                title = "DAILY STOCK ALLOCATION CHALLAN"
            else:
                title = "EVENING SETTLEMENT RECEIPT"
            self.cell(0, 10, title, 0, 1, 'C')
            self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def add_info_section(self, emp_name, emp_mobile, date_str, time_str):
        # ... (Existing logic) ...
        self.set_font('Arial', '', 10)
        self.set_text_color(0, 0, 0)
        start_y = self.get_y()
        self.set_xy(10, start_y)
        self.cell(35, 6, "Employee Name:", 0, 0)
        self.set_font('Arial', 'B', 10)
        self.cell(70, 6, str(emp_name).upper(), 0, 1)
        self.set_font('Arial', '', 10)
        self.cell(35, 6, "Mobile No:", 0, 0)
        self.set_font('Arial', 'B', 10)
        self.cell(70, 6, str(emp_mobile) if emp_mobile else "N/A", 0, 1)
        self.set_xy(140, start_y)
        self.set_font('Arial', '', 10)
        self.cell(20, 6, "Date:", 0, 0)
        self.set_font('Arial', 'B', 10)
        self.cell(40, 6, str(date_str), 0, 1)
        self.set_xy(140, start_y + 6)
        self.set_font('Arial', '', 10)
        self.cell(20, 6, "Time:", 0, 0)
        self.set_font('Arial', 'B', 10)
        self.cell(40, 6, str(time_str), 0, 1)
        self.ln(10)

    def add_table_header(self, columns, widths):
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(26, 35, 126) 
        self.set_text_color(255, 255, 255)
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.3)
        for i, col in enumerate(columns):
            self.cell(widths[i], 8, col, 1, 0, 'C', True)
        self.ln()

    def add_signature_section(self):
        if self.get_y() > 220: self.add_page()
        self.ln(15) 
        y_pos = self.get_y()
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 0, 0)
        
        # Use absolute path if possible or relative to app root
        # We need 'app' context or pass path. Assuming 'app' is global or path passed.
        # But here inside class we don't have 'app'. 
        # The caller usually handles path or we hardcode based on static folder structure relative to script.
        # Let's assume standard static/img/signature.png
        sig_path = "static/img/signature.png" 
        if os.path.exists(sig_path):
            self.image(sig_path, x=20, y=y_pos, w=40) 
            
        self.line(15, y_pos + 25, 75, y_pos + 25)
        self.set_xy(15, y_pos + 27)
        self.cell(60, 5, "Authorized Signature", 0, 0, 'C')
        self.line(135, y_pos + 25, 195, y_pos + 25)
        self.set_xy(135, y_pos + 27)
        self.cell(60, 5, "Employee Signature", 0, 1, 'C')
        self.ln(10)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, "This is a computer generated document.", 0, 1, 'C')

    # --- NEW METHOD FOR OFFICE BILL ---
    def generate_office_bill(self, data, output_buffer, owner_sig_path=None):
        self.alias_nb_pages()
        self.add_page()
        
        # 1. Custom Header for Bill
        self.set_font('Arial', 'B', 20)
        self.set_text_color(26, 35, 126)
        self.cell(0, 10, self.company_name, 0, 1, 'C')
        
        self.set_font('Arial', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, self.slogan, 0, 1, 'C')
        
        self.ln(2)
        self.set_font('Arial', '', 9)
        self.set_text_color(50, 50, 50)
        for line in self.address_lines:
            self.cell(0, 4, line, 0, 1, 'C')
        self.cell(0, 4, self.contact, 0, 1, 'C')
        self.set_font('Arial', 'B', 9)
        self.cell(0, 4, self.gst_no, 0, 1, 'C')
        
        self.ln(5)
        self.set_draw_color(0, 0, 0)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)
        
        # 2. Bill Title
        self.set_font('Arial', 'B', 16)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, "BILL OF SUPPLY", 0, 1, 'C')
        self.ln(5)
        
        # 3. Customer Info Grid
        start_y = self.get_y()
        self.set_font('Arial', 'B', 10)
        self.cell(25, 6, "Bill No:", 0, 0)
        self.set_font('Arial', '', 10)
        self.cell(60, 6, str(data['id']), 0, 1)
        
        self.set_font('Arial', 'B', 10)
        self.cell(25, 6, "Date:", 0, 0)
        self.set_font('Arial', '', 10)
        self.cell(60, 6, str(data['date']), 0, 1)
        
        self.set_font('Arial', 'B', 10)
        self.cell(25, 6, "Sales Person:", 0, 0)
        self.set_font('Arial', '', 10)
        self.cell(60, 6, str(data['sales_person']), 0, 1)
        
        # Right Column
        self.set_xy(110, start_y)
        self.set_font('Arial', 'B', 10)
        self.cell(30, 6, "Customer:", 0, 0)
        self.set_font('Arial', '', 10)
        self.cell(60, 6, str(data['customer_name']), 0, 1)
        
        self.set_xy(110, start_y + 6)
        self.set_font('Arial', 'B', 10)
        self.cell(30, 6, "Mobile:", 0, 0)
        self.set_font('Arial', '', 10)
        self.cell(60, 6, str(data['customer_mobile']), 0, 1)
        
        self.set_xy(110, start_y + 12)
        self.set_font('Arial', 'B', 10)
        self.cell(30, 6, "Address:", 0, 0)
        self.set_font('Arial', '', 10)
        self.multi_cell(60, 6, str(data['customer_address']), 0, 'L')
        
        self.ln(10)
        
        # 4. Product Table
        cols = ["#", "Product Name", "Qty", "Price", "Amount"]
        widths = [15, 85, 20, 30, 40]
        
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(0, 0, 0)
        for i, col in enumerate(cols):
            self.cell(widths[i], 8, col, 1, 0, 'C', True)
        self.ln()
        
        self.set_font('Arial', '', 10)
        for i, item in enumerate(data['items']):
            self.cell(widths[0], 8, str(i+1), 1, 0, 'C')
            self.cell(widths[1], 8, str(item['name']), 1, 0, 'L')
            self.cell(widths[2], 8, str(item['qty']), 1, 0, 'C')
            self.cell(widths[3], 8, f"{float(item['price']):.2f}", 1, 0, 'R')
            self.cell(widths[4], 8, f"{float(item['total']):.2f}", 1, 1, 'R')
            
        # 5. Totals
        self.ln(2)
        x_start = 130
        
        self.set_x(x_start)
        self.cell(30, 8, "Sub Total:", 0, 0, 'R')
        self.cell(40, 8, f"{float(data['total_amount']):.2f}", 1, 1, 'R')
        
        self.set_x(x_start)
        self.cell(30, 8, "Discount (-):", 0, 0, 'R')
        self.cell(40, 8, f"{float(data['discount']):.2f}", 1, 1, 'R')
        
        self.set_x(x_start)
        self.set_font('Arial', 'B', 11)
        self.cell(30, 10, "GRAND TOTAL:", 0, 0, 'R')
        self.cell(40, 10, f"{float(data['final_amount']):.2f}", 1, 1, 'R')
        
        self.ln(10)
        
        # 6. Terms & Signature
        y_sig = self.get_y()
        
        self.set_font('Arial', 'B', 9)
        self.cell(0, 5, "Terms & Conditions:", 0, 1)
        self.set_font('Arial', '', 8)
        self.cell(0, 4, "1. Goods once sold will not be taken back.", 0, 1)
        self.cell(0, 4, "2. Warranty as per manufacturer policy.", 0, 1)
        self.cell(0, 4, "3. Subject to Nadiad jurisdiction.", 0, 1)
        
        # Owner Sig
        if owner_sig_path and os.path.exists(owner_sig_path):
            self.image(owner_sig_path, x=150, y=y_sig, w=30)
            
        self.set_xy(140, y_sig + 20)
        self.set_font('Arial', 'B', 9)
        self.cell(50, 5, "For, REAL PROMOTION", 0, 1, 'C')
        self.set_xy(140, y_sig + 25)
        self.cell(50, 5, "(Authorized Signatory)", 0, 1, 'C')
        
        # Output logic for buffer (Standard FPDF 1.7 doesn't support writing to buffer directly via output() args smoothly without dest='S')
        # We return the string data
        return self.output(dest='S').encode('latin-1')

# ... (Previous routes) ...

# --- ROUTE: DOWNLOAD BILL PDF ---
@app.route('/office_sales/print/<int:sale_id>')
def download_office_bill(sale_id):
    if "loggedin" not in session: return redirect(url_for("login"))
    
    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute("SELECT * FROM office_sales WHERE id=%s", (sale_id,))
    sale = cursor.fetchone()
    
    if not sale: return "Bill not found"
    
    cursor.execute("""
        SELECT i.*, p.name 
        FROM office_sale_items i 
        JOIN products p ON i.product_id = p.id 
        WHERE i.sale_id=%s
    """, (sale_id,))
    items = cursor.fetchall()
    
    # Prepare Data
    pdf_data = {
        'id': sale['id'],
        'date': str(sale['bill_date']),
        'customer_name': sale['customer_name'],
        'customer_mobile': sale['customer_mobile'],
        'customer_address': sale['customer_address'],
        'sales_person': sale['sales_person'],
        'total_amount': sale['total_amount'],
        'discount': sale['discount'],
        'final_amount': sale['final_amount'],
        'items': [{'name': i['name'], 'qty': i['qty'], 'price': i['unit_price'], 'total': i['total_price']} for i in items]
    }
    
    # Instantiate Generator with specific title type "Office" to avoid default header
    pdf = PDFGenerator("Office") 
    
    # Output
    buffer = io.BytesIO()
    
    # Get signature path
    sig_path = os.path.join(app.root_path, 'static', 'img', 'signature.png')
    
    # Call the NEW method which now returns bytes directly
    pdf_bytes = pdf.generate_office_bill(pdf_data, buffer, owner_sig_path=sig_path)
    
    buffer.write(pdf_bytes)
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f"Bill_{sale_id}.pdf", mimetype='application/pdf')



@app.route('/supplier/payment/delete/<int:payment_id>', methods=['POST'])
def delete_supplier_payment(payment_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Get payment details to know amount and supplier
    cur.execute("SELECT * FROM supplier_payments WHERE id = %s", (payment_id,))
    payment = cur.fetchone()
    
    if payment:
        amount = payment['amount_paid']
        supplier_id = payment['supplier_id']
        
        # 2. Delete the payment record
        cur.execute("DELETE FROM supplier_payments WHERE id = %s", (payment_id,))
        
        # 3. Reverse the deduction (Add amount back to current_due)
        cur.execute("UPDATE suppliers SET current_due = current_due + %s WHERE id = %s", (amount, supplier_id))
        
        mysql.connection.commit()
        flash('Payment deleted and due amount reversed.', 'warning')
        cur.close()
        return redirect(url_for('supplier_ledger', supplier_id=supplier_id))
        
    cur.close()
    flash('Payment not found.', 'danger')
    return redirect(url_for('suppliers'))


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



# Morning pdf generation route:


# ---------------------------------------------------------
# 4. NEW: GENERATE PDF (Professional Morning Receipt)
# ---------------------------------------------------------
@app.route('/morning/pdf/<int:alloc_id>')
def generate_morning_pdf(alloc_id):
    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Header Info
        db_cursor.execute("""
            SELECT ma.*, e.name as emp_name, e.phone 
            FROM morning_allocations ma
            JOIN employees e ON ma.employee_id = e.id
            WHERE ma.id = %s
        """, (alloc_id,))
        header = db_cursor.fetchone()
        
        if not header: return "Not Found", 404

        # Items (Aggregated)
        db_cursor.execute("""
            SELECT p.name, SUM(mai.opening_qty + mai.given_qty) as total_qty, mai.unit_price
            FROM morning_allocation_items mai
            JOIN products p ON mai.product_id = p.id
            WHERE mai.allocation_id = %s
            GROUP BY p.id
        """, (alloc_id,))
        items = db_cursor.fetchall()

        # PDF Generation
        pdf = FPDF()
        pdf.add_page()
        
        # Logo/Title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "REAL PROMOTION", 0, 1, 'C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, "Daily Stock Allocation Challan", 0, 1, 'C')
        pdf.ln(10)

        # Info Block
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(100, 8, f"Employee: {header['emp_name']}", 0, 0)
        pdf.cell(0, 8, f"Date: {header['date']}", 0, 1, 'R')
        pdf.cell(100, 8, f"Phone: {header['phone']}", 0, 1)
        pdf.ln(5)

        # Table Header
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(10, 8, "#", 1, 0, 'C', 1)
        pdf.cell(100, 8, "Product Name", 1, 0, 'L', 1)
        pdf.cell(30, 8, "Quantity", 1, 0, 'C', 1)
        pdf.cell(30, 8, "Price", 1, 0, 'R', 1)
        pdf.cell(0, 8, "", 0, 1) # End line

        # Table Rows
        pdf.set_font("Arial", '', 10)
        i = 1
        grand_qty = 0
        for item in items:
            pdf.cell(10, 8, str(i), 1, 0, 'C')
            pdf.cell(100, 8, str(item['name']), 1, 0, 'L')
            pdf.cell(30, 8, str(item['total_qty']), 1, 0, 'C')
            pdf.cell(30, 8, f"{item['unit_price']:.2f}", 1, 0, 'R')
            pdf.ln()
            i += 1
            grand_qty += item['total_qty']

        # Total
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(110, 10, "Total Items:", 0, 0, 'R')
        pdf.cell(30, 10, str(grand_qty), 0, 1, 'C')

        # Signatures
        pdf.ln(20)
        pdf.cell(90, 10, "___________________", 0, 0, 'C')
        pdf.cell(90, 10, "___________________", 0, 1, 'C')
        pdf.cell(90, 5, "Store Manager", 0, 0, 'C')
        pdf.cell(90, 5, "Receiver (Employee)", 0, 1, 'C')

        response = make_response(pdf.output(dest='S').encode('latin1'))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Alloc_{alloc_id}.pdf'
        return response

    except Exception as e:
        app.logger.error(f"PDF Error: {e}")
        return str(e), 500
    finally:
        if db_cursor: db_cursor.close()



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


# Admin Page 
@app.route('/admin_master')
def admin_master():
    if "loggedin" not in session: 
        return redirect(url_for("login"))
    # Redirect dashboard page 
    return redirect(url_for('dash'))



# --- HELPER FUNCTION: Find correct column name automatically ---
def get_db_column(cursor, table_name, candidates):
    """Finds which column name actually exists in the table."""
    try:
        cursor.execute(f"SHOW COLUMNS FROM {table_name}")
        existing_columns = [row['Field'] for row in cursor.fetchall()]
        for cand in candidates:
            if cand in existing_columns: return cand
        return candidates[0]
    except:
        return candidates[0]



@app.route("/dash")
def dash():
    """Admin Analytics Dashboard (Premium)"""
    if "loggedin" not in session: return redirect(url_for("login"))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    today = date.today()
    current_year = today.year
    
    # --- DYNAMIC COLUMN DETECTION ---
    sales_col = get_db_column(cursor, 'sales', ['total_amount', 'amount', 'total', 'grand_total', 'final_total'])
    purch_col = get_db_column(cursor, 'purchases', ['total_amount', 'amount', 'total'])
    exp_col   = get_db_column(cursor, 'expenses', ['amount', 'cost', 'total'])
    stock_col = get_db_column(cursor, 'products', ['quantity', 'qty', 'stock'])

    # --- 1. Sales Today ---
    try:
        cursor.execute(f"SELECT SUM({sales_col}) as total FROM sales WHERE date = %s", (today,))
        sales_today = cursor.fetchone()['total'] or 0
    except: sales_today = 0

    # --- 2. Sales This Month ---
    try:
        start_m = date(today.year, today.month, 1)
        if today.month == 12: end_m = date(today.year + 1, 1, 1) - timedelta(days=1)
        else: end_m = date(today.year, today.month + 1, 1) - timedelta(days=1)
        
        cursor.execute(f"SELECT SUM({sales_col}) as total FROM sales WHERE date BETWEEN %s AND %s", (start_m, end_m))
        sales_this_month = cursor.fetchone()['total'] or 0
    except: sales_this_month = 0

    # --- 3. Yearly Sales ---
    try:
        cursor.execute(f"SELECT SUM({sales_col}) as total FROM sales WHERE YEAR(date) = %s", (current_year,))
        yearly_sales = cursor.fetchone()['total'] or 0
    except: yearly_sales = 0

    # --- 4. Yearly Expenses ---
    try:
        cursor.execute(f"SELECT SUM({exp_col}) as total FROM expenses WHERE YEAR(date) = %s", (current_year,))
        yearly_expenses = cursor.fetchone()['total'] or 0
    except: yearly_expenses = 0
    
    # --- 5. Low Stock ---
    try:
        cursor.execute(f"SELECT COUNT(*) as cnt FROM products WHERE {stock_col} < 10")
        low_stock = cursor.fetchone()['cnt'] or 0
    except: low_stock = 0
    
    # --- 6. Supplier Dues (FIXED LOGIC: Opening + Purchases + Adjustments - Payments) ---
    try:
        # A. Total Opening Balance
        cursor.execute("SELECT SUM(opening_balance) as total_ob FROM suppliers")
        total_ob = float(cursor.fetchone()['total_ob'] or 0)
        
        # B. Total Purchases
        cursor.execute(f"SELECT SUM(total_amount) as total_pur FROM purchases")
        total_pur = float(cursor.fetchone()['total_pur'] or 0)
        
        # C. Total Manual Adjustments (Others)
        try:
            cursor.execute("SELECT SUM(amount) as total_adj FROM supplier_adjustments")
            total_adj = float(cursor.fetchone()['total_adj'] or 0)
        except: total_adj = 0.0

        # D. Total Payments (from supplier_payments table)
        try:
            cursor.execute("SELECT SUM(amount_paid) as total_paid FROM supplier_payments")
            total_paid = float(cursor.fetchone()['total_paid'] or 0)
        except: total_paid = 0.0
            
        supplier_dues = (total_ob + total_pur + total_adj) - total_paid
    except Exception as e:
        print(f"Dues Calc Error: {e}")
        supplier_dues = 0
    
    # --- 7. CHART DATA ---
    chart_months = []
    chart_sales = []
    chart_expenses = []
    
    for m in range(1, 13):
        month_name = calendar.month_abbr[m]
        chart_months.append(month_name)
        
        start_date = date(current_year, m, 1)
        if m == 12: end_date = date(current_year + 1, 1, 1) - timedelta(days=1)
        else: end_date = date(current_year, m + 1, 1) - timedelta(days=1)
            
        try:
            cursor.execute(f"SELECT SUM({sales_col}) as s FROM sales WHERE date BETWEEN %s AND %s", (start_date, end_date))
            chart_sales.append(float(cursor.fetchone()['s'] or 0))
        except: chart_sales.append(0.0)
        
        try:
            cursor.execute(f"SELECT SUM({exp_col}) as e FROM expenses WHERE date BETWEEN %s AND %s", (start_date, end_date))
            chart_expenses.append(float(cursor.fetchone()['e'] or 0))
        except: chart_expenses.append(0.0)

    # --- 8. TOP PRODUCTS ---
    top_prod_names, top_prod_qty = [], []
    try:
        cursor.execute("""
            SELECT p.name, SUM(s.quantity) as qty 
            FROM sales s
            JOIN products p ON s.product_id = p.id
            GROUP BY p.name ORDER BY qty DESC LIMIT 5
        """)
        for row in cursor.fetchall():
            top_prod_names.append(row['name'])
            top_prod_qty.append(int(row['qty']))
    except: pass

    cursor.close()
    
    return render_template(
        "dash.html",
        sales_today=sales_today,
        sales_this_month=sales_this_month,
        yearly_sales=yearly_sales,
        yearly_expenses=yearly_expenses,
        low_stock=low_stock,
        supplier_dues=supplier_dues, # Updated
        chart_months=chart_months,
        chart_sales=chart_sales,
        chart_expenses=chart_expenses,
        top_prod_names=top_prod_names,
        top_prod_qty=top_prod_qty,
        date=date,
        current_year=current_year
    )

# ... (rest of your app.py remains unchanged) ...


# =====================================================================
# SUPPLIER MANAGEMENT ROUTES
# =====================================================================
@app.route('/suppliers')
def suppliers():
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # FETCH SUPPLIERS WITH DYNAMIC DUE CALCULATION
    # Formula: Opening + Purchases + Adjustments - Payments
    # Ordered by ID ASC
    query = """
        SELECT s.*, 
            (
                s.opening_balance + 
                COALESCE((SELECT SUM(total_amount) FROM purchases WHERE supplier_id = s.id), 0) +
                COALESCE((SELECT SUM(amount) FROM supplier_adjustments WHERE supplier_id = s.id), 0) -
                COALESCE((SELECT SUM(amount_paid) FROM supplier_payments WHERE supplier_id = s.id), 0)
            ) as calculated_due
        FROM suppliers s
        ORDER BY s.id ASC
    """
    cursor.execute(query)
    suppliers = cursor.fetchall()
    
    cursor.close()
    return render_template('suppliers/suppliers.html', suppliers=suppliers)



@app.route('/suppliers/add', methods=['GET', 'POST'])
def add_supplier():
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        gstin = request.form.get('gstim', '')
        address = request.form.get('address', '')
        
        # New Fields
        opening_balance = request.form.get('opening_balance', 0.0)
        payment_terms = request.form.get('payment_terms', 60)
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            INSERT INTO suppliers (name, phone, email, gstin, address, opening_balance, payment_terms) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (name, phone, email, gstin, address, opening_balance, payment_terms))
        
        mysql.connection.commit()
        cursor.close()
        flash('Supplier added successfully!', 'success')
        return redirect(url_for('suppliers'))
        
    return render_template('suppliers/add_supplier.html')

@app.route('/suppliers/edit/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        gstin = request.form.get('gstin', '')
        address = request.form.get('address', '')
        opening_balance = request.form.get('opening_balance', 0.0)
        
        cursor.execute("""
            UPDATE suppliers 
            SET name=%s, phone=%s, email=%s, gstin=%s, address=%s, opening_balance=%s
            WHERE id=%s
        """, (name, phone, email, gstin, address, opening_balance, supplier_id))
        
        mysql.connection.commit()
        flash('Supplier updated successfully!', 'success')
        return redirect(url_for('suppliers'))
    
    cursor.execute("SELECT * FROM suppliers WHERE id=%s", (supplier_id,))
    supplier = cursor.fetchone()
    cursor.close()
    
    return render_template('suppliers/edit_supplier.html', supplier=supplier)

# =====================================================================
# SUPPLIER LEDGER & PAYMENT ROUTES
# ===================================================



@app.route('/supplier_ledger/<int:supplier_id>')
def supplier_ledger(supplier_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Fetch Supplier Info
    cursor.execute("SELECT * FROM suppliers WHERE id=%s", (supplier_id,))
    supplier = cursor.fetchone()
    
    if not supplier:
        flash("Supplier not found!", "danger")
        return redirect(url_for('suppliers'))

    # 2. Fetch Records (Purchases, Payments, Adjustments)
    cursor.execute("SELECT * FROM purchases WHERE supplier_id=%s ORDER BY purchase_date DESC", (supplier_id,))
    purchases = cursor.fetchall()
    
    try:
        cursor.execute("SELECT * FROM supplier_payments WHERE supplier_id=%s ORDER BY payment_date DESC", (supplier_id,))
        payments = cursor.fetchall()
    except: payments = []
    
    try:
        cursor.execute("SELECT * FROM supplier_adjustments WHERE supplier_id=%s ORDER BY adjustment_date DESC", (supplier_id,))
        adjustments = cursor.fetchall()
    except: adjustments = []
    
    # 3. Calculate Totals (Using COALESCE for safety)
    
    # Purchases Total
    cursor.execute("SELECT SUM(COALESCE(total_amount, 0)) as total FROM purchases WHERE supplier_id=%s", (supplier_id,))
    total_purchases = float(cursor.fetchone()['total'] or 0)
    
    # Payments Total
    try:
        cursor.execute("SELECT SUM(COALESCE(amount_paid, 0)) as total FROM supplier_payments WHERE supplier_id=%s", (supplier_id,))
        total_paid = float(cursor.fetchone()['total'] or 0)
    except:
        total_paid = 0.0
        
    # Adjustments (Other Dues) Total
    try:
        cursor.execute("SELECT SUM(COALESCE(amount, 0)) as total FROM supplier_adjustments WHERE supplier_id=%s", (supplier_id,))
        total_adjustments = float(cursor.fetchone()['total'] or 0)
    except:
        total_adjustments = 0.0
    
    # Opening Balance
    opening_bal = float(supplier.get('opening_balance', 0.0))
    
    # --- FORMULA ---
    # Total Outstanding = (Opening + Purchases + Adjustments) - Payments
    total_outstanding_amount = (opening_bal + total_purchases + total_adjustments) - total_paid
    
    cursor.close()
    
    return render_template('suppliers/supplier_ledger.html', 
                         supplier=supplier, 
                         purchases=purchases, 
                         payments=payments, 
                         adjustments=adjustments,
                         total_outstanding_amount=total_outstanding_amount, # Main Figure
                         opening_balance=opening_bal,
                         total_purchases=total_purchases,
                         total_adjustments=total_adjustments,
                         total_paid=total_paid)


# Route to Add Manual Due (Other Reason)
@app.route('/suppliers/add_due/<int:supplier_id>', methods=['GET', 'POST'])
def supplier_add_due(supplier_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM suppliers WHERE id = %s", (supplier_id,))
    supplier = cursor.fetchone()
    
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for('suppliers'))
        
    if request.method == 'POST':
        amount = request.form.get('amount')
        date_val = request.form.get('date')
        notes = request.form.get('notes')
        
        try:
            cursor.execute("""
                INSERT INTO supplier_adjustments (supplier_id, amount, adjustment_date, notes)
                VALUES (%s, %s, %s, %s)
            """, (supplier_id, amount, date_val, notes))
            
            # Update current_due in suppliers table (Increase Debt)
            cursor.execute("""
                UPDATE suppliers SET current_due = current_due + %s WHERE id = %s
            """, (amount, supplier_id))
            
            mysql.connection.commit()
            flash("Manual due added successfully.", "success")
            return redirect(url_for('supplier_ledger', supplier_id=supplier_id))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {e}", "danger")
            
    cursor.close()
    return render_template('suppliers/add_manual_due.html', supplier=supplier, today_date=date.today().isoformat())



@app.route('/suppliers/delete_adjustment/<int:adjustment_id>', methods=['POST'])
def delete_supplier_adjustment(adjustment_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get supplier ID first to redirect back
    cursor.execute("SELECT supplier_id, amount FROM supplier_adjustments WHERE id=%s", (adjustment_id,))
    adj = cursor.fetchone()
    
    if adj:
        supplier_id = adj['supplier_id']
        amount = adj['amount']
        
        try:
            # Delete adjustment
            cursor.execute("DELETE FROM supplier_adjustments WHERE id=%s", (adjustment_id,))
            
            # Update supplier current_due (Decrease debt)
            cursor.execute("UPDATE suppliers SET current_due = current_due - %s WHERE id=%s", (amount, supplier_id))
            
            mysql.connection.commit()
            flash("Adjustment deleted successfully.", "success")
            return redirect(url_for('supplier_ledger', supplier_id=supplier_id))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error deleting adjustment: {e}", "danger")
            return redirect(url_for('suppliers')) # Fallback
            
    cursor.close()
    return redirect(url_for('suppliers'))


@app.route('/suppliers/<int:supplier_id>/payment/new', methods=['GET', 'POST'])
def record_payment(supplier_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch Supplier
    cursor.execute("SELECT * FROM suppliers WHERE id = %s", (supplier_id,))
    supplier = cursor.fetchone()
    
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for('suppliers'))

    # Calculate Current Due Dynamically for Display
    cursor.execute("SELECT SUM(total_amount) as total FROM purchases WHERE supplier_id=%s", (supplier_id,))
    total_purchases = float(cursor.fetchone()['total'] or 0)
    
    try:
        cursor.execute("SELECT SUM(amount_paid) as total FROM supplier_payments WHERE supplier_id=%s", (supplier_id,))
        total_paid = float(cursor.fetchone()['total'] or 0)
    except: total_paid = 0.0
    
    try:
        cursor.execute("SELECT SUM(amount) as total FROM supplier_adjustments WHERE supplier_id=%s", (supplier_id,))
        total_adj = float(cursor.fetchone()['total'] or 0)
    except: total_adj = 0.0
    
    opening_bal = float(supplier.get('opening_balance', 0.0))
    
    # Net Payable
    current_due_display = (opening_bal + total_purchases + total_adj) - total_paid

    if request.method == 'POST':
        amount_paid = request.form.get('amount_paid')
        payment_date = request.form.get('payment_date')
        payment_mode = request.form.get('payment_mode')
        notes = request.form.get('notes')

        if not amount_paid or not payment_date:
            flash("Payment amount and date are required.", "danger")
            return render_template('suppliers/new_payment.html', supplier=supplier, current_due=current_due_display, today_date=date.today().isoformat())
        
        try:
            # Insert into supplier_payments
            cursor.execute("""
                INSERT INTO supplier_payments (supplier_id, amount_paid, payment_date, payment_mode, notes)
                VALUES (%s, %s, %s, %s, %s)
            """, (supplier_id, amount_paid, payment_date, payment_mode, notes))

            # Update 'current_due' in suppliers table (Optional sync, but good practice)
            cursor.execute("""
                UPDATE suppliers SET current_due = current_due - %s WHERE id = %s
            """, (amount_paid, supplier_id))
            
            mysql.connection.commit()
            flash('Payment recorded successfully!', 'success')
            return redirect(url_for('supplier_ledger', supplier_id=supplier_id))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred: {e}", "danger")
    
    cursor.close()
    
    # Pass 'current_due_display' to template
    return render_template('suppliers/new_payment.html', supplier=supplier, current_due=current_due_display, today_date=date.today().isoformat())





@app.route('/suppliers/delete/<int:supplier_id>', methods=['POST'])
def delete_supplier(supplier_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # 1. Delete Supplier Payments (Purchase Order Payments)
        # We try this, but if table doesn't exist or is empty, we continue
        try:
            cursor.execute("DELETE FROM supplier_payments WHERE supplier_id = %s", (supplier_id,))
        except Exception:
            pass # Table might not exist or other issue
            
        # 2. Delete Purchases (and items)
        # Get purchase IDs to manually delete items if CASCADE is missing
        cursor.execute("SELECT id FROM purchases WHERE supplier_id = %s", (supplier_id,))
        purchase_ids = [p['id'] for p in cursor.fetchall()]
        
        if purchase_ids:
            if len(purchase_ids) == 1:
                ids_tuple = f"({purchase_ids[0]})"
            else:
                ids_tuple = str(tuple(purchase_ids))
                
            cursor.execute(f"DELETE FROM purchase_items WHERE purchase_id IN {ids_tuple}")
            cursor.execute("DELETE FROM purchases WHERE supplier_id=%s", (supplier_id,))

        # 3. Delete Manual Adjustments (if any)
        try:
            cursor.execute("DELETE FROM supplier_adjustments WHERE supplier_id = %s", (supplier_id,))
        except:
            pass

        # NOTE: Removed 'supplier_cashflow' deletion as per instruction ("module removed")

        # 4. Finally, Delete the Supplier
        cursor.execute("DELETE FROM suppliers WHERE id=%s", (supplier_id,))
        
        mysql.connection.commit()
        flash('Supplier and related records deleted successfully.', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        # Check for specific FK error (1451) to give better message
        if "1451" in str(e):
             flash("Cannot delete supplier: They still have linked records (possibly in Cashflow/Archive) that must be removed first.", "danger")
        else:
             flash(f"Error deleting supplier: {str(e)}", "danger")
        
    finally:
        cursor.close()
        
    return redirect(url_for('suppliers'))



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


@app.route('/new_purchase', methods=['GET', 'POST'])
def new_purchase():
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        try:
            # 1. Master Data
            supplier_id = request.form['supplier_id']
            purchase_date = request.form['purchase_date']
            bill_number = request.form.get('bill_number', '')
            
            # 2. Item Arrays
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            prices = request.form.getlist('price[]')
            
            # Calculate Grand Total
            total_amount = 0.0
            valid_items = []
            
            for i in range(len(product_ids)):
                if product_ids[i]: 
                    # --- FIX 1: Safe Float Conversion (Prevents "could not convert string to float") ---
                    try:
                        raw_qty = quantities[i]
                        # Convert to float, default to 0.0 if empty string
                        qty = float(raw_qty) if raw_qty and str(raw_qty).strip() else 0.0
                    except ValueError:
                        qty = 0.0

                    try:
                        raw_price = prices[i]
                        # Convert to float, default to 0.0 if empty string
                        price = float(raw_price) if raw_price and str(raw_price).strip() else 0.0
                    except ValueError:
                        price = 0.0
                    # ---------------------------------------------------------------------------------

                    total_amount += (qty * price)
                    valid_items.append({'p_id': product_ids[i], 'qty': qty, 'price': price})
            
            # 3. Insert Master Purchase Record
            cursor.execute("""
                INSERT INTO purchases (supplier_id, purchase_date, bill_number, total_amount)
                VALUES (%s, %s, %s, %s)
            """, (supplier_id, purchase_date, bill_number, total_amount))
            
            purchase_id = cursor.lastrowid
            
            # 4. Insert Items & Update Stock
            
            # Dynamic Column Detection for Stock
            stock_col = 'quantity' # default
            cursor.execute("SHOW COLUMNS FROM products")
            columns = [row['Field'] for row in cursor.fetchall()]
            if 'stock_quantity' in columns: stock_col = 'stock_quantity'
            elif 'stock' in columns: stock_col = 'stock'
            elif 'qty' in columns: stock_col = 'qty'
            
            for item in valid_items:
                p_id = item['p_id']
                new_qty = item['qty']
                new_price = item['price']

                # --- Fetch CURRENT stock and price ---
                cursor.execute(f"SELECT {stock_col}, price FROM products WHERE id = %s", (p_id,))
                current_product = cursor.fetchone()
                
                if current_product:
                    try:
                        old_qty = float(current_product[stock_col] or 0)
                    except: old_qty = 0.0
                    
                    try:
                        old_price = float(current_product['price'] or 0)
                    except: old_price = 0.0
                    
                    # Calculate New Total Quantity
                    final_total_qty = old_qty + new_qty
                    
                    # --- FIX 2: Logic for Price Update ---
                    if new_price > 0:
                        # SCENARIO A: Paid Purchase -> Calculate Weighted Average
                        total_old_value = old_qty * old_price
                        total_new_value = new_qty * new_price
                        final_total_value = total_old_value + total_new_value
                        
                        if final_total_qty > 0:
                            new_avg_price = final_total_value / final_total_qty
                        else:
                            new_avg_price = 0.0
                    else:
                        # SCENARIO B: Zero Price (Free/Bonus) -> KEEP OLD PRICE
                        # The user specifically requested NOT to update price if new price is missing/zero.
                        new_avg_price = old_price

                    # E. Insert Item
                    cursor.execute("""
                        INSERT INTO purchase_items (purchase_id, product_id, quantity, purchase_price)
                        VALUES (%s, %s, %s, %s)
                    """, (purchase_id, p_id, new_qty, new_price))
                    
                    # F. Update Product with Calculated Price and New Quantity
                    update_query = f"UPDATE products SET {stock_col} = %s, price = %s WHERE id = %s"
                    cursor.execute(update_query, (final_total_qty, new_avg_price, p_id))
            
            # 5. Update Supplier Dues (Add to debt)
            cursor.execute("""
                UPDATE suppliers SET current_due = current_due + %s WHERE id = %s
            """, (total_amount, supplier_id))
            
            mysql.connection.commit()
            flash(f"Purchase Order #{purchase_id} created successfully!", "success")
            return redirect(url_for('purchases'))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error creating purchase: {str(e)}", "danger")
            # Log error to console for debugging
            print(f"Purchase Error: {e}") 
            return redirect(url_for('purchases'))
            
    # GET: Load data
    cursor.execute("SELECT id, name FROM suppliers ORDER BY name")
    suppliers = cursor.fetchall()
    
    cursor.execute("SELECT * FROM products ORDER BY name")
    products = cursor.fetchall()
    
    cursor.close()
    return render_template('purchases/new_purchase.html', suppliers=suppliers, products=products)




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


@app.route('/purchases/edit/<int:purchase_id>', methods=['GET'])
def edit_purchase(purchase_id):
    # ... (auth check) ...
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Fetch Purchase
    cursor.execute("SELECT * FROM purchases WHERE id = %s", (purchase_id,))
    purchase = cursor.fetchone()
    
    # 2. Fetch Suppliers (for dropdown)
    cursor.execute("SELECT id, name FROM suppliers ORDER BY name")
    suppliers = cursor.fetchall()
    
    # 3. Fetch Products (for JS dropdown)
    cursor.execute("SELECT * FROM products ORDER BY name")
    products = cursor.fetchall()
    
    # 4. Fetch Existing Items (to populate rows)
    cursor.execute("SELECT * FROM purchase_items WHERE purchase_id = %s", (purchase_id,))
    items = cursor.fetchall()
    
    cursor.close()
    return render_template('purchases/edit_purchase.html', 
                         purchase=purchase, 
                         suppliers=suppliers, 
                         products=products, 
                         items=items)


@app.route('/purchases/update/<int:purchase_id>', methods=['POST'])
def update_purchase(purchase_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # 1. Fetch OLD Purchase Data (to reverse stock and dues)
        cursor.execute("SELECT * FROM purchases WHERE id = %s", (purchase_id,))
        old_purchase = cursor.fetchone()
        
        if not old_purchase:
            flash("Purchase not found.", "danger")
            return redirect(url_for('purchases'))
            
        old_total = float(old_purchase['total_amount'])
        old_supplier_id = old_purchase['supplier_id']
        
        # 2. Fetch OLD Items (to reverse stock)
        cursor.execute("SELECT * FROM purchase_items WHERE purchase_id = %s", (purchase_id,))
        old_items = cursor.fetchall()
        
        # Reverse Stock: Subtract old quantities
        # Logic: Purchase added stock, so editing/removing means subtracting that addition first
        stock_col = 'quantity' # dynamic check logic omitted for brevity, assuming 'quantity' or 'stock_quantity'
        # Check column name quickly
        cursor.execute("SHOW COLUMNS FROM products")
        cols = [r['Field'] for r in cursor.fetchall()]
        if 'stock_quantity' in cols: stock_col = 'stock_quantity'
        elif 'stock' in cols: stock_col = 'stock'
        
        for item in old_items:
            cursor.execute(f"UPDATE products SET {stock_col} = {stock_col} - %s WHERE id = %s", 
                           (item['quantity'], item['product_id']))
            
        # 3. Get NEW Form Data
        new_supplier_id = request.form['supplier_id']
        new_date = request.form['purchase_date']
        new_bill = request.form.get('bill_number', '')
        
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        prices = request.form.getlist('price[]')
        
        # 4. Delete Old Items
        cursor.execute("DELETE FROM purchase_items WHERE purchase_id = %s", (purchase_id,))
        
        # 5. Insert NEW Items & Update Stock & Calculate New Total
        new_total = 0.0
        
        for i in range(len(product_ids)):
            if product_ids[i]:
                p_id = product_ids[i]
                qty = float(quantities[i])
                price = float(prices[i])
                line_total = qty * price
                new_total += line_total
                
                # Insert Item (Using 'total_amount' based on your DB schema)
                cursor.execute("""
                    INSERT INTO purchase_items (purchase_id, product_id, quantity, purchase_price, total_amount)
                    VALUES (%s, %s, %s, %s, %s)
                """, (purchase_id, p_id, qty, price, line_total))
                
                # Update Stock (Add new quantity)
                cursor.execute(f"UPDATE products SET {stock_col} = {stock_col} + %s, price = %s WHERE id = %s", 
                               (qty, price, p_id))

        # 6. Update Master Record
        cursor.execute("""
            UPDATE purchases 
            SET supplier_id=%s, purchase_date=%s, bill_number=%s, total_amount=%s 
            WHERE id=%s
        """, (new_supplier_id, new_date, new_bill, new_total, purchase_id))
        
        # 7. Update Supplier Dues
        # Logic: Subtract Old Total, Add New Total
        # If supplier changed, handle separately (Complex, assuming same supplier for simplicity or simple adjustment)
        if str(old_supplier_id) == str(new_supplier_id):
            diff = new_total - old_total
            cursor.execute("UPDATE suppliers SET current_due = current_due + %s WHERE id = %s", (diff, old_supplier_id))
        else:
            # Revert old supplier
            cursor.execute("UPDATE suppliers SET current_due = current_due - %s WHERE id = %s", (old_total, old_supplier_id))
            # Add to new supplier
            cursor.execute("UPDATE suppliers SET current_due = current_due + %s WHERE id = %s", (new_total, new_supplier_id))
        
        mysql.connection.commit()
        flash(f"Purchase Order #{purchase_id} updated successfully.", "success")
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error updating purchase: {str(e)}", "danger")
        print(f"Update Error: {e}")
        
    finally:
        cursor.close()
        
    return redirect(url_for('purchases'))




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


# --- HELPER: Safe Date Formatter ---
def safe_date_format(date_obj, format='%d-%m-%Y', default='N/A'):
    """Safely formats a date object, returning default if None."""
    if date_obj:
        return date_obj.strftime(format)
    return default



@app.route('/purchases/pdf/<int:purchase_id>')
def purchase_pdf(purchase_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch Purchase & Supplier
    # FIX: Changed s.gst_number to s.gstin based on schema inference
    cursor.execute("""
        SELECT p.*, s.name as supplier_name, s.address as supplier_address, s.phone as supplier_phone, s.gstin as supplier_gst
        FROM purchases p 
        LEFT JOIN suppliers s ON p.supplier_id = s.id 
        WHERE p.id = %s
    """, (purchase_id,))
    purchase = cursor.fetchone()
    
    if not purchase:
        flash("Purchase not found", "danger")
        return redirect(url_for('purchases'))
        
    # Fetch Items
    cursor.execute("""
        SELECT pi.*, pr.name as product_name 
        FROM purchase_items pi 
        LEFT JOIN products pr ON pi.product_id = pr.id 
        WHERE pi.purchase_id = %s
    """, (purchase_id,))
    items = cursor.fetchall()
    
    cursor.close()
    
    # Generate PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Purchase Order #{purchase['id']}", 0, 1, 'C')
    pdf.ln(10)
    
    # Supplier Info
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Supplier Details:", 0, 1)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"Name: {purchase['supplier_name']}", 0, 1)
    pdf.cell(0, 6, f"Address: {purchase['supplier_address'] or 'N/A'}", 0, 1)
    pdf.cell(0, 6, f"Phone: {purchase['supplier_phone'] or 'N/A'}", 0, 1)
    if purchase.get('supplier_gst'):
        pdf.cell(0, 6, f"GSTIN: {purchase['supplier_gst']}", 0, 1)
    
    # Purchase Info (FIXED DATE HERE)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Order Details:", 0, 1)
    pdf.set_font("Arial", '', 10)
    
    # Use helper or inline check
    p_date = safe_date_format(purchase['purchase_date'])
    pdf.cell(0, 6, f"Date: {p_date}", 0, 1)
    pdf.cell(0, 6, f"Bill No: {purchase['bill_number'] or 'N/A'}", 0, 1)
    pdf.ln(10)
    
    # Items Table Header
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(10, 10, "#", 1, 0, 'C', 1)
    pdf.cell(80, 10, "Product", 1, 0, 'L', 1)
    pdf.cell(25, 10, "Qty", 1, 0, 'C', 1)
    pdf.cell(35, 10, "Price", 1, 0, 'R', 1)
    pdf.cell(40, 10, "Total", 1, 1, 'R', 1)
    
    # Items Rows
    pdf.set_font("Arial", '', 10)
    total_calc = 0
    for i, item in enumerate(items):
        item_total = float(item['quantity']) * float(item['purchase_price'])
        total_calc += item_total
        
        pdf.cell(10, 10, str(i+1), 1, 0, 'C')
        pdf.cell(80, 10, str(item['product_name']), 1, 0, 'L')
        pdf.cell(25, 10, str(item['quantity']), 1, 0, 'C')
        pdf.cell(35, 10, f"{float(item['purchase_price']):.2f}", 1, 0, 'R')
        pdf.cell(40, 10, f"{item_total:.2f}", 1, 1, 'R')
    
    # Grand Total
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(150, 10, "Grand Total", 1, 0, 'R')
    # Use stored total_amount or calculated one
    final_total = purchase['total_amount'] if purchase['total_amount'] else total_calc
    pdf.cell(40, 10, f"{float(final_total):.2f}", 1, 1, 'R')
    
    # Output
    response = make_response(pdf.output(dest='S').encode('latin1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=PO_{purchase_id}.pdf'
    return response



@app.route('/purchases/delete/<int:purchase_id>', methods=['POST'])
def delete_purchase(purchase_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # 1. Fetch Purchase Details (to reverse Supplier Dues)
        cursor.execute("SELECT supplier_id, total_amount FROM purchases WHERE id = %s", (purchase_id,))
        purchase = cursor.fetchone()
        
        if not purchase:
            flash("Purchase not found.", "danger")
            return redirect(url_for('purchases'))
            
        supplier_id = purchase['supplier_id']
        total_amount = purchase['total_amount']

        # 2. Fetch Purchase Items (to reverse Stock)
        cursor.execute("SELECT product_id, quantity FROM purchase_items WHERE purchase_id = %s", (purchase_id,))
        items = cursor.fetchall()
        
        # 3. Dynamic Column Detection for Stock
        stock_col = 'quantity' # default
        cursor.execute("SHOW COLUMNS FROM products")
        columns = [row['Field'] for row in cursor.fetchall()]
        if 'stock_quantity' in columns: stock_col = 'stock_quantity'
        elif 'stock' in columns: stock_col = 'stock'
        elif 'qty' in columns: stock_col = 'qty'
        
        # 4. Reverse Stock (Subtract quantity)
        for item in items:
            p_id = item['product_id']
            qty = float(item['quantity'])
            
            # Subtract the quantity back
            query = f"UPDATE products SET {stock_col} = {stock_col} - %s WHERE id = %s"
            cursor.execute(query, (qty, p_id))
            
        # 5. Reverse Supplier Dues (Subtract amount)
        cursor.execute("""
            UPDATE suppliers SET current_due = current_due - %s WHERE id = %s
        """, (total_amount, supplier_id))
        
        # 6. Delete the Purchase Record
        # (purchase_items will be deleted automatically if ON DELETE CASCADE is set, otherwise delete them first)
        cursor.execute("DELETE FROM purchases WHERE id = %s", (purchase_id,))
        
        mysql.connection.commit()
        flash(f"Purchase #{purchase_id} deleted and stock reversed.", "success")
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting purchase: {str(e)}", "danger")
        print(f"Delete Error: {e}")
        
    finally:
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

# ---------- ADMIN SIDE: DEPARTMENT MASTER ----------#############################################################################################################
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



# Add employee route#
@app.route("/add_employee", methods=["GET", "POST"])
def add_employee():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == "POST":
        d = request.form
        
        # 1. Get Files
        img_file = request.files.get("image")
        doc_file = request.files.get("document")
        
        img_url = None
        doc_url = None
        
        try:
            # 2. Upload Image
            if img_file and allowed_file(img_file.filename):
                res = cloudinary.uploader.upload(img_file, folder="erp_employees")
                img_url = res.get('secure_url')
            
            # 3. Upload Document
            if doc_file and doc_file.filename != '':
                res = cloudinary.uploader.upload(doc_file, folder="erp_employee_docs", resource_type="auto")
                doc_url = res.get('secure_url')
        except Exception as e:
            app.logger.error(f"Upload error: {e}")
            flash(f"Upload warning: {e}", "warning")

        # 4. Insert (UPDATED QUERY)
        try:
            cur.execute("""
                INSERT INTO employees (
                    name, email, phone, aadhar_no, emergency_contact, emergency_contact_person, 
                    dob, position_id, department_id, address_line1, address_line2, 
                    pincode, city, district, state, image, document, status
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active')
            """, (
                d.get("name"), 
                d.get("email"), 
                d.get("phone"), 
                d.get("aadhar_no"), 
                d.get("emergency_contact"),
                d.get("emergency_contact_person"), # NEW FIELD
                d.get("dob") if d.get("dob") else None,
                d.get("position_id"), 
                d.get("department_id"), 
                d.get("address_line1"), 
                d.get("address_line2"), 
                d.get("pincode"), 
                d.get("city"), 
                d.get("district"), 
                d.get("state"), 
                img_url, 
                doc_url
            ))
            mysql.connection.commit()
            flash("Employee Added Successfully!", "success")
            return redirect(url_for("employees"))
        except Exception as e:
            mysql.connection.rollback()
            app.logger.error(f"DB Error: {e}")
            flash(f"Error adding employee: {e}", "danger")
        finally:
            cur.close()

    cur.execute("SELECT * FROM employee_positions")
    pos = cur.fetchall()
    cur.execute("SELECT * FROM employee_departments")
    dept = cur.fetchall()
    cur.close()
    return render_template("employees/add_employee.html", positions=pos, departments=dept)


# =========================================================
#  EMPLOYEE Document route 
# =========================================================

@app.route("/employee_document/<int:id>")
def employee_document(id):
    if "loggedin" not in session: return redirect(url_for("login"))
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cur.execute("SELECT document FROM employees WHERE id=%s", (id,))
        row = cur.fetchone()
    finally:
        cur.close()

    if not row or not row.get("document"):
        flash("No document attached.", "warning")
        return redirect(request.referrer or url_for('employees'))
        
    doc_val = row["document"]

    # 1. Full URL
    if doc_val.startswith("http"):
        # Fix for PDF 404s (Append .pdf if missing in docs folder)
        if "erp_employee_docs" in doc_val and not any(doc_val.lower().endswith(x) for x in ['.pdf', '.jpg', '.png', '.jpeg', '.doc', '.docx']):
            return redirect(doc_val + ".pdf")
        return redirect(doc_val)

    # 2. Cloudinary Public ID
    try:
        # Heuristic: Force PDF format if likely a doc without extension
        if "erp_employee_docs" in doc_val and not any(doc_val.lower().endswith(x) for x in ['.pdf', '.jpg', '.png', '.jpeg']):
             url, _ = cloudinary.utils.cloudinary_url(doc_val, secure=True, format="pdf")
             return redirect(url)
        
        url, _ = cloudinary.utils.cloudinary_url(doc_val, secure=True)
        return redirect(url)
    except Exception as e:
        app.logger.error(f"Doc URL Error: {e}")
        return "Error opening document", 500


# ---------- ADMIN SIDE: EDIT EMPLOYEE (admin_master.html) ----------

@app.route("/edit_employee/<int:id>", methods=["GET", "POST"])
def edit_employee(id):
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        form = request.form
        
        # Basic Info
        name = form.get("name", "").strip()
        email = form.get("email", "").strip()
        phone = form.get("phone", "").strip()
        
        # Dates
        dob = form.get("dob") or None 
        joining_date = form.get("join_date") or None # Fixed field name match

        # IDs
        position_id = form.get("position_id") or None
        department_id = form.get("department_id") or None
        
        # Status (Added Logic)
        status = form.get("status", "active").lower() # Default to active if missing

        # Extra Info
        emergency_contact = form.get("emergency_contact", "").strip()
        emergency_contact_person = form.get("emergency_contact_person", "").strip()
        aadhar_no = form.get("aadhar_no", "").strip()

        # Address Info
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
                res = cloudinary.uploader.upload(image_file, folder="erp_employees")
                image_public_id = res.get('secure_url')
            
            if doc_file and doc_file.filename:
                res = cloudinary.uploader.upload(doc_file, folder="erp_employee_docs", resource_type='auto')
                doc_public_id = res.get('secure_url')

            # Dynamic Update Query
            fields = [
                ("name", name),
                ("email", email or None),
                ("phone", phone or None),
                ("dob", dob),
                ("joining_date", joining_date),
                ("status", status), # Include status in update
                ("position_id", position_id),
                ("department_id", department_id),
                ("emergency_contact", emergency_contact or None),
                ("emergency_contact_person", emergency_contact_person or None),
                ("aadhar_no", aadhar_no or None),
                ("pincode", pincode or None),
                ("city", city or None),
                ("district", district or None),
                ("state", state or None),
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
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cursor = None
    try:
        # We need a cursor. Since your app uses DictCursor globally, we handle results as dicts.
        cursor = mysql.connection.cursor()

        # =========================================================
        # STEP 1: Delete Blocking 'Evening Settle' Records
        # =========================================================
        # Evening settlements are linked to Morning Allocations AND Employees.
        # We must find all Allocations belonging to this employee first.
        
        cursor.execute("SELECT id FROM morning_allocations WHERE employee_id = %s", (id,))
        allocations = cursor.fetchall()
        allocation_ids = [row['id'] for row in allocations]

        # A. Delete Settlements linked to this Employee's Allocations
        if allocation_ids:
            # Convert list to string for SQL IN clause (safe way)
            placeholders = ', '.join(['%s'] * len(allocation_ids))
            sql = f"DELETE FROM evening_settle WHERE allocation_id IN ({placeholders})"
            cursor.execute(sql, tuple(allocation_ids))

        # B. Delete Settlements linked directly to the Employee ID
        # (This catches any settlements that might not have a matching allocation link)
        cursor.execute("DELETE FROM evening_settle WHERE employee_id = %s", (id,))

        # =========================================================
        # STEP 2: Delete Morning Allocations
        # =========================================================
        # Now that evening settlements are gone, we can delete allocations.
        # (This will auto-delete morning_allocation_items if you have CASCADE, but we do it manually to be safe)
        cursor.execute("DELETE FROM morning_allocations WHERE employee_id = %s", (id,))

        # =========================================================
        # STEP 3: Delete Other Dependencies
        # =========================================================
        cursor.execute("DELETE FROM product_returns WHERE employee_id = %s", (id,))
        cursor.execute("DELETE FROM employee_transactions WHERE employee_id = %s", (id,))
        cursor.execute("DELETE FROM employee_attendance WHERE employee_id = %s", (id,))

        # =========================================================
        # STEP 4: Delete the Employee
        # =========================================================
        cursor.execute("DELETE FROM employees WHERE id = %s", (id,))

        mysql.connection.commit()
        flash("Employee and all associated records deleted successfully!", "success")

    except Exception as e:
        mysql.connection.rollback()
        # Log the specific error to help debugging
        app.logger.error(f"Delete Employee Failed: {e}")
        
        # User friendly error message
        if "foreign key" in str(e).lower():
            flash("Cannot delete employee: There are still linked records (like Settlements) preventing deletion.", "danger")
        else:
            flash(f"An error occurred: {e}", "danger")

    finally:
        if cursor:
            cursor.close()

    return redirect(url_for("employee_master"))

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
        FROM expenses e
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
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        form_type = request.form['form_type']
        
        if form_type == 'main_category':
            cat_name = request.form['category_name']
            cur.execute("INSERT INTO expensecategories (category_name) VALUES (%s)", [cat_name])
            flash('Category Added!', 'success')
            
        elif form_type == 'subcategory':
            parent_id = request.form['parent_category_id']
            sub_name = request.form['subcategory_name']
            cur.execute("INSERT INTO expensesubcategories (category_id, subcategory_name) VALUES (%s, %s)", (parent_id, sub_name))
            flash('Subcategory Added!', 'success')
            
        mysql.connection.commit()
        return redirect(url_for('category_man'))

    # GET Request: Fetch Hierarchy
    cur.execute("SELECT * FROM expensecategories ORDER BY category_name")
    main_cats = cur.fetchall()
    
    cur.execute("SELECT * FROM expensesubcategories ORDER BY subcategory_name")
    sub_cats = cur.fetchall()
    
    # Merge for Template
    categories = []
    for mc in main_cats:
        mc_dict = dict(mc)
        mc_dict['subcategories'] = [sc for sc in sub_cats if sc['category_id'] == mc['category_id']]
        categories.append(mc_dict)
        
    cur.close()
    return render_template('expenses/category_man.html', categories=categories)


# ==========================================
# ROBUST DELETE ROUTES FOR EXPENSES
# ==========================================
@app.route('/delete_category/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    try:
        # 1. First, delete all EXPENSES linked to any SUBCATEGORY of this Main Category
        # We need to find all subcategory_ids belonging to this category_id
        # FIXED: Corrected table name to 'expensesubcategories' (no underscore)
        cur.execute("SELECT subcategory_id FROM expensesubcategories WHERE category_id = %s", [category_id])
        subcats = cur.fetchall()
        
        for sc in subcats:
            # Delete expenses for each subcategory
            cur.execute("DELETE FROM expenses WHERE subcategory_id = %s", [sc[0]])
            
        # REMOVED: The invalid query 'DELETE FROM expenses WHERE category_id...' 
        # because the 'expenses' table does not have a 'category_id' column.

        # 3. Now it is safe to delete the Subcategories
        # FIXED: Corrected table name to 'expensesubcategories'
        cur.execute("DELETE FROM expensesubcategories WHERE category_id = %s", [category_id])
        
        # 4. Finally, delete the Main Category
        # FIXED: Corrected table name to 'expensecategories'
        cur.execute("DELETE FROM expensecategories WHERE category_id = %s", [category_id])
        
        mysql.connection.commit()
        flash('Category and all related expenses deleted successfully.', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        # Log the actual error for debugging
        print(f"Delete Category Error: {e}")
        flash(f'Error deleting category: {e}', 'danger')
        
    finally:
        cur.close()
        
    return redirect(url_for('category_man'))


@app.route('/delete_subcategory/<int:subcategory_id>', methods=['POST'])
def delete_subcategory(subcategory_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    try:
        # 1. First, delete all EXPENSES that use this specific subcategory
        cur.execute("DELETE FROM expenses WHERE subcategory_id = %s", [subcategory_id])
        
        # 2. Now it is safe to delete the Subcategory itself
        cur.execute("DELETE FROM expensesubcategories WHERE subcategory_id = %s", [subcategory_id])
        
        mysql.connection.commit()
        flash('Subcategory and associated expenses deleted successfully.', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        print(f"Delete Subcategory Error: {e}")
        flash(f'Error deleting subcategory: {e}', 'danger')
        
    finally:
        cur.close()
        
    return redirect(url_for('category_man'))

# REPLACE THIS ROUTE IN YOUR app.py
@app.route("/exp_report", methods=["GET"])
def exp_report():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # --------------------------
    # GET FILTERS (Fixed datetime usage)
    # --------------------------
    report_type = request.args.get("type", "monthly_summary")

    # FIX: Use datetime.now() directly, NOT datetime.datetime.now()
    current_year = datetime.now().year
    current_month = datetime.now().month

    filters = {
        "year": request.args.get("year", current_year),
        "month": request.args.get("month", f"{current_month:02d}"),
        "start_date": request.args.get("start_date", ""),
        "end_date": request.args.get("end_date", "")
    }

    # --------------------------
    # MONTH LIST
    # --------------------------
    months = [
        ("01", "January"), ("02", "February"), ("03", "March"),
        ("04", "April"), ("05", "May"), ("06", "June"),
        ("07", "July"), ("08", "August"), ("09", "September"),
        ("10", "October"), ("11", "November"), ("12", "December")
    ]

    # --------------------------
    # REPORT DATA
    # --------------------------
    chart_data = {"labels": [], "data": []}
    report_rows = []

    try:
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
                LEFT JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id
                LEFT JOIN expensecategories c ON sc.category_id = c.category_id
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
                LEFT JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id
                LEFT JOIN expensecategories c ON sc.category_id = c.category_id
                WHERE e.expense_date BETWEEN %s AND %s
                ORDER BY e.expense_date DESC
            """, (filters["start_date"], filters["end_date"]))
            report_rows = cursor.fetchall()

        # 3. CATEGORY-WISE REPORT
        elif report_type == "category_wise":
            cursor.execute("""
                SELECT c.category_name as category, SUM(e.amount) AS total
                FROM expenses e
                LEFT JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id
                LEFT JOIN expensecategories c ON sc.category_id = c.category_id
                WHERE YEAR(e.expense_date) = %s
                GROUP BY c.category_name
                ORDER BY total DESC
            """, (filters["year"],))
            rows = cursor.fetchall()
            report_rows = rows
            chart_data["labels"] = [r["category"] for r in rows]
            chart_data["data"] = [float(r["total"]) for r in rows]

        # 4. SUBCATEGORY-WISE REPORT
        elif report_type == "subcategory_wise":
            cursor.execute("""
                SELECT sc.subcategory_name as subcategory, SUM(e.amount) AS total
                FROM expenses e
                LEFT JOIN expensesubcategories sc ON e.subcategory_id = sc.subcategory_id
                WHERE YEAR(e.expense_date) = %s
                GROUP BY sc.subcategory_name
                ORDER BY total DESC
            """, (filters["year"],))
            rows = cursor.fetchall()
            report_rows = rows
            chart_data["labels"] = [r["subcategory"] for r in rows]
            chart_data["data"] = [float(r["total"]) for r in rows]

        # 5. MOM COMPARISON
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

    except Exception as e:
        app.logger.error(f"Expense Report Error: {e}")
        # Optionally flash an error message to the user
        
    finally:
        cursor.close()

    # --- CALCULATE SUMMARY DATA (Fix for UndefinedError) ---
    total_amount = sum(float(r['amount']) for r in report_rows if 'amount' in r) if report_rows else 0
    # For category/subcategory/mom types, the column is often named 'total' instead of 'amount'
    if not total_amount and report_rows and 'total' in report_rows[0]:
         total_amount = sum(float(r['total']) for r in report_rows)

    month_name = "Unknown"
    for m_num, m_name in months:
        if m_num == str(filters["month"]):
            month_name = m_name
            break
            
    report_data = {
        "month_name": month_name,
        "year": filters["year"],
        "summary": {
            "total": total_amount,
            "count": len(report_rows)
        }
    }
    # -------------------------------------------------------

    return render_template(
        "reports/exp_report.html",
        report_type=report_type,
        filters=filters,
        months=months,
        report_rows=report_rows,
        chart_data=chart_data,
        report_data=report_data # <--- Passing the variable with 'summary'
    )



# --- PDF GENERATOR CLASS (INTERNAL) ---
class PDFGenerator(FPDF):
    def __init__(self, title_type="Morning"):
        super().__init__()
        self.title_type = title_type
        self.company_name = "REAL PROMOTION"
        self.slogan = "SINCE 2005"
        self.address_lines = [
            "Real Promotion, G/12, Tulsimangalam Complex,",
            "B/h. Trimurti Complex, Ghodiya Bazar,",
            "Nadiad-387001, Gujarat, India"
        ]
        self.contact = "+91 96623 22476 | help@realpromotion.in"
        self.gst_no = "GSTIN: " # Add GST if available

    def header(self):
        # Company Header
        self.set_font('Arial', 'B', 24)
        self.set_text_color(26, 35, 126) # Dark Blue
        self.cell(0, 10, self.company_name, 0, 1, 'C')
        
        self.set_font('Arial', 'B', 10)
        self.set_text_color(100, 100, 100) # Grey
        self.cell(0, 5, self.slogan, 0, 1, 'C')
        self.ln(2)
        
        self.set_font('Arial', '', 9)
        self.set_text_color(50, 50, 50)
        for line in self.address_lines:
            self.cell(0, 4, line, 0, 1, 'C')
        self.cell(0, 4, self.contact, 0, 1, 'C')
        self.set_font('Arial', 'B', 9)
        self.cell(0, 4, self.gst_no, 0, 1, 'C')
        self.ln(5)
        
        # Divider
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

        # Title
        self.set_font('Arial', 'B', 16)
        self.set_text_color(0, 0, 0)
        if self.title_type == "Morning":
            title = "DAILY STOCK ALLOCATION CHALLAN"
        else:
            title = "EVENING SETTLEMENT RECEIPT"
        self.cell(0, 10, title, 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def add_info_section(self, emp_name, emp_mobile, date_str, time_str):
        self.set_font('Arial', '', 10)
        self.set_text_color(0, 0, 0)
        start_y = self.get_y()
        
        # Left: Employee
        self.set_xy(10, start_y)
        self.cell(35, 6, "Employee Name:", 0, 0)
        self.set_font('Arial', 'B', 10)
        self.cell(70, 6, str(emp_name).upper(), 0, 1)
        
        self.set_font('Arial', '', 10)
        self.cell(35, 6, "Mobile No:", 0, 0)
        self.set_font('Arial', 'B', 10)
        self.cell(70, 6, str(emp_mobile) if emp_mobile else "N/A", 0, 1)

        # Right: Date/Time
        self.set_xy(140, start_y)
        self.set_font('Arial', '', 10)
        self.cell(20, 6, "Date:", 0, 0)
        self.set_font('Arial', 'B', 10)
        self.cell(40, 6, str(date_str), 0, 1)

        self.set_xy(140, start_y + 6)
        self.set_font('Arial', '', 10)
        self.cell(20, 6, "Time:", 0, 0)
        self.set_font('Arial', 'B', 10)
        self.cell(40, 6, str(time_str), 0, 1)
        self.ln(10)

    def add_table_header(self, columns, widths):
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(26, 35, 126) 
        self.set_text_color(255, 255, 255)
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.3)
        for i, col in enumerate(columns):
            self.cell(widths[i], 8, col, 1, 0, 'C', True)
        self.ln()

    def add_signature_section(self):
        if self.get_y() > 220: self.add_page()
        self.ln(15) 
        y_pos = self.get_y()
        
        # Owner Signature
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 0, 0)
        
        sig_path = os.path.join(app.root_path, 'static', 'img', 'signature.png')
        
        if os.path.exists(sig_path):
            self.image(sig_path, x=20, y=y_pos, w=40) 
        else:
            self.set_xy(20, y_pos)
            self.set_font('Arial', 'I', 8)
            self.cell(40, 10, "", 0, 0)

        self.line(15, y_pos + 25, 75, y_pos + 25)
        self.set_xy(15, y_pos + 27)
        self.cell(60, 5, "Authorized Signature", 0, 0, 'C')
        
        # Employee Signature
        self.line(135, y_pos + 25, 195, y_pos + 25)
        self.set_xy(135, y_pos + 27)
        self.cell(60, 5, "Employee Signature", 0, 1, 'C')
        
        self.ln(10)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, "This is a computer generated document.", 0, 1, 'C')


# --- MORNING PDF ROUTE ---
@app.route('/download_morning_pdf/<int:allocation_id>')
def download_morning_pdf(allocation_id):
    if "loggedin" not in session: return redirect(url_for("login"))
    
    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Header (Removed e.mobile)
    cursor.execute("""
        SELECT ma.date, ma.created_at, e.name as emp_name
        FROM morning_allocations ma
        JOIN employees e ON ma.employee_id = e.id
        WHERE ma.id = %s
    """, (allocation_id,))
    header = cursor.fetchone()
    
    if not header:
        flash("Allocation not found", "danger")
        return redirect(url_for('allocation_list'))
        
    # 2. Items
    cursor.execute("""
        SELECT p.name, mai.opening_qty, mai.given_qty, mai.unit_price
        FROM morning_allocation_items mai
        JOIN products p ON mai.product_id = p.id
        WHERE mai.allocation_id = %s
    """, (allocation_id,))
    items = cursor.fetchall()
    
    # 3. Generate
    pdf = PDFGenerator("Morning")
    pdf.alias_nb_pages()
    pdf.add_page()
    
    d_val = header['date'].strftime('%d-%m-%Y') if header['date'] else ""
    t_val = str(header['created_at']) if header['created_at'] else "N/A"
    
    pdf.add_info_section(header['emp_name'], "", d_val, t_val)
    
    cols = ["#", "Product Name", "Opening", "Given", "Total", "Price", "Amount"]
    widths = [10, 70, 20, 20, 20, 20, 30]
    pdf.add_table_header(cols, widths)
    
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(245, 245, 245)
    
    total_qty_sum = 0
    total_amount_sum = 0
    fill = False
    
    for i, item in enumerate(items):
        pdf.cell(widths[0], 7, str(i+1), 1, 0, 'C', fill)
        pdf.cell(widths[1], 7, str(item['name']), 1, 0, 'L', fill)
        pdf.cell(widths[2], 7, str(item['opening_qty']), 1, 0, 'C', fill)
        pdf.cell(widths[3], 7, str(item['given_qty']), 1, 0, 'C', fill)
        
        t_qty = int(item['opening_qty']) + int(item['given_qty'])
        pdf.cell(widths[4], 7, str(t_qty), 1, 0, 'C', fill)
        
        pdf.cell(widths[5], 7, f"{float(item['unit_price']):.2f}", 1, 0, 'R', fill)
        
        amt = t_qty * float(item['unit_price'])
        pdf.cell(widths[6], 7, f"{amt:.2f}", 1, 1, 'R', fill)
        
        total_qty_sum += t_qty
        total_amount_sum += amt
        fill = not fill 
        
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(sum(widths[:4]), 8, "GRAND TOTAL", 1, 0, 'R', True)
    pdf.cell(widths[4], 8, str(total_qty_sum), 1, 0, 'C', True)
    pdf.cell(widths[5], 8, "", 1, 0, 'C', True)
    pdf.cell(widths[6], 8, f"{total_amount_sum:.2f}", 1, 1, 'R', True)
    
    pdf.add_signature_section()
    
    # Return PDF string as byte stream
    pdf_string = pdf.output(dest='S').encode('latin-1')
    buffer = io.BytesIO(pdf_string)
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f"Morning_Alloc_{allocation_id}.pdf", mimetype='application/pdf')


# --- EVENING PDF ROUTE ---
@app.route('/download_evening_pdf/<int:settle_id>')
def download_evening_pdf(settle_id):
    if "loggedin" not in session: return redirect(url_for("login"))
    
    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Header (Removed e.mobile)
    cursor.execute("""
        SELECT es.*, e.name as emp_name
        FROM evening_settle es
        JOIN employees e ON es.employee_id = e.id
        WHERE es.id = %s
    """, (settle_id,))
    data = cursor.fetchone()
    
    if not data:
        flash("Settlement not found", "danger")
        return redirect(url_for('evening_master'))
        
    # 2. Items
    cursor.execute("""
        SELECT p.name, ei.total_qty, ei.sold_qty, ei.return_qty, ei.unit_price
        FROM evening_item ei
        JOIN products p ON ei.product_id = p.id
        WHERE ei.settle_id = %s
    """, (settle_id,))
    items = cursor.fetchall()
    
    # 3. Generate
    pdf = PDFGenerator("Evening")
    pdf.alias_nb_pages()
    pdf.add_page()
    
    d_val = data['date'].strftime('%d-%m-%Y') if data['date'] else ""
    t_val = str(data['created_at']) if data.get('created_at') else "N/A"
    
    pdf.add_info_section(data['emp_name'], "", d_val, t_val)
    
    cols = ["#", "Product", "Total", "Sold", "Price", "Amount", "Return"]
    widths = [10, 60, 20, 20, 25, 30, 25]
    pdf.add_table_header(cols, widths)
    
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(245, 245, 245)
    
    tot_sold = 0
    tot_amt = 0
    tot_ret = 0
    fill = False
    
    for i, item in enumerate(items):
        pdf.cell(widths[0], 7, str(i+1), 1, 0, 'C', fill)
        pdf.cell(widths[1], 7, str(item['name']), 1, 0, 'L', fill)
        pdf.cell(widths[2], 7, str(item['total_qty']), 1, 0, 'C', fill)
        pdf.cell(widths[3], 7, str(item['sold_qty']), 1, 0, 'C', fill)
        pdf.cell(widths[4], 7, f"{float(item['unit_price']):.2f}", 1, 0, 'R', fill)
        
        amt = float(item['sold_qty']) * float(item['unit_price'])
        pdf.cell(widths[5], 7, f"{amt:.2f}", 1, 0, 'R', fill)
        
        pdf.cell(widths[6], 7, str(item['return_qty']), 1, 1, 'C', fill)
        
        tot_sold += int(item['sold_qty'])
        tot_amt += amt
        tot_ret += int(item['return_qty'])
        fill = not fill

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(sum(widths[:3]), 8, "TOTALS", 1, 0, 'R', True)
    pdf.cell(widths[3], 8, str(tot_sold), 1, 0, 'C', True)
    pdf.cell(widths[4], 8, "", 1, 0, 'C', True)
    pdf.cell(widths[5], 8, f"{tot_amt:.2f}", 1, 0, 'R', True)
    pdf.cell(widths[6], 8, str(tot_ret), 1, 1, 'C', True)
    pdf.ln(5)
    
    # Finance Summary
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(50, 50, 50)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, " FINANCE & SETTLEMENT SUMMARY ", 1, 1, 'C', True)
    
    pdf.set_text_color(0,0,0)
    pdf.set_font('Arial', '', 10)
    pdf.ln(2)
    y_start = pdf.get_y()
    
    def print_kv(label, val, x, w_label, w_val):
        pdf.set_x(x)
        pdf.set_font('Arial', '', 10)
        pdf.cell(w_label, 6, label, 0, 0)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(w_val, 6, val, 0, 1, 'R')

    print_kv("Total Sales Value:", f"{tot_amt:.2f}", 15, 40, 30)
    print_kv("Discount (-):", f"{float(data.get('discount', 0) or 0):.2f}", 15, 40, 30)
    print_kv("Online Rec. (-):", f"{float(data.get('online_money', 0) or 0):.2f}", 15, 40, 30)
    pdf.line(15, pdf.get_y(), 85, pdf.get_y())
    pdf.ln(1)
    print_kv("CASH COLLECTED:", f"{float(data.get('cash_money', 0) or 0):.2f}", 15, 40, 30)
    
    pdf.ln(15)
    net_sales = tot_amt - float(data.get('discount', 0) or 0) - float(data.get('online_money', 0) or 0)
    balance_due = net_sales - float(data.get('cash_money', 0) or 0)
    if abs(balance_due) < 0.01: balance_due = 0.0
    
    pdf.set_fill_color(220, 53, 69)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 12, f" BALANCE DUE:  {balance_due:.2f} ", 1, 1, 'C', True)
    
    pdf.add_signature_section()
    
    pdf_string = pdf.output(dest='S').encode('latin-1')
    buffer = io.BytesIO(pdf_string)
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f"Evening_Settle_{settle_id}.pdf", mimetype='application/pdf')

# --- ROUTE: ALLOCATION LIST (Correct Time & Status) ---
# --- ROUTE: ALLOCATION LIST (Fixed Time & Design) ---
# --- ROUTE: MORNING (Capture Live Clock Time) ---

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






# =========================================================
#  CORE LOGIC: STOCK CALCULATOR (The Chain System)
# =========================================================
def get_current_stock_state(cursor, emp_id, target_date_str):
    """
    Calculates the stock state for an employee up to a specific date.
    Logic: Last Settlement + All Unsettled Allocations (Gap) + Today's Allocations
    """
    stock_map = {} # Key: ProductID, Value: {qty, name, price, image}

    # 1. FIND LAST FINAL SETTLEMENT (Baseline)
    cursor.execute("""
        SELECT id, date FROM evening_settle 
        WHERE employee_id=%s AND date < %s AND status='final'
        ORDER BY date DESC LIMIT 1
    """, (emp_id, target_date_str))
    last_settle = cursor.fetchone()
    
    last_settle_date = last_settle['date'] if last_settle else '2000-01-01' # Fallback to ancient date
    
    if last_settle:
        cursor.execute("""
            SELECT product_id, remaining_qty, unit_price, p.name, p.image
            FROM evening_item ei
            JOIN products p ON ei.product_id = p.id
            WHERE settle_id = %s AND remaining_qty > 0
        """, (last_settle['id'],))
        
        for r in cursor.fetchall():
            pid = r['product_id']
            stock_map[pid] = {
                'product_id': pid, 'name': r['name'], 'image': resolve_img(r['image']),
                'qty': int(r['remaining_qty']), 'price': float(r['unit_price'])
            }

    # 2. FILL THE GAP (Allocations AFTER Last Settle but BEFORE/ON Today)
    # This catches holidays, missed settlements, AND today's restocks
    cursor.execute("""
        SELECT mai.product_id, SUM(mai.given_qty) as total_given, MAX(mai.unit_price) as unit_price, p.name, p.image
        FROM morning_allocations ma
        JOIN morning_allocation_items mai ON ma.id = mai.allocation_id
        JOIN products p ON mai.product_id = p.id
        WHERE ma.employee_id = %s AND ma.date > %s AND ma.date <= %s
        GROUP BY mai.product_id
    """, (emp_id, last_settle_date, target_date_str))
    
    gap_allocations = cursor.fetchall()
    
    for r in gap_allocations:
        pid = r['product_id']
        added_qty = int(r['total_given'])
        
        if pid in stock_map:
            stock_map[pid]['qty'] += added_qty
            # Update price if needed (usually keeps old price or avg, simplest is keep old)
        else:
            stock_map[pid] = {
                'product_id': pid, 'name': r['name'], 'image': resolve_img(r['image']),
                'qty': added_qty, 'price': float(r['unit_price'])
            }
            
    return list(stock_map.values())


# ==========================================
# 1. API: FETCH MORNING STOCK (Updated)
# ==========================================
@app.route('/api/fetch_stock', methods=['GET', 'POST'])
def api_fetch_stock():
    if "loggedin" not in session: return jsonify({"error": "Unauthorized"}), 401
    
    employee_id = request.values.get('employee_id')
    date_str = request.values.get('date') 

    if not employee_id or not date_str: return jsonify({"error": "Missing params"}), 400

    try:
        current_date = parse_date(date_str)
        if not current_date: return jsonify({"error": "Invalid date"}), 400
        formatted_date = current_date.strftime('%Y-%m-%d')
        
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # 1. Check Evening Lock
        cur.execute("SELECT id FROM evening_settle WHERE employee_id=%s AND date=%s AND status='final'", (employee_id, formatted_date))
        if cur.fetchone():
            cur.close()
            return jsonify({"mode": "locked", "evening_settled": True})

        # 2. Check Mode (Restock or Normal)
        cur.execute("SELECT id FROM morning_allocations WHERE employee_id=%s AND date=%s", (employee_id, formatted_date))
        today_alloc = cur.fetchone()
        
        mode = "restock" if today_alloc else "normal"
        
        # 3. CALCULATE AGGREGATED STOCK (The Magic Function)
        # This returns: Yesterday Left + Gap Allocations + Today's Given So Far
        # This satisfies "Opening me bhi dikhna chahiye"
        aggregated_stock = get_current_stock_state(cur, employee_id, formatted_date)
        
        # 4. Format for Frontend
        # If Restock Mode: We calculate specific "Already Given Today" for the history box
        existing_items = []
        if mode == 'restock':
            cur.execute("""
                SELECT p.name, p.image, mai.given_qty, mai.product_id
                FROM morning_allocation_items mai
                JOIN products p ON mai.product_id = p.id
                WHERE mai.allocation_id = %s
            """, (today_alloc['id'],))
            for r in cur.fetchall():
                existing_items.append({
                    'name': r['name'], 'image': resolve_img(r['image']),
                    'qty': int(r['given_qty']), 'product_id': r['product_id']
                })

        # Prepare Opening List (Mapped to 'remaining' key for JS compatibility)
        opening_list = []
        for item in aggregated_stock:
            opening_list.append({
                'product_id': str(item['product_id']),
                'name': item['name'],
                'image': item['image'],
                'remaining': item['qty'], # This is the AGGREGATED TOTAL
                'price': item['price']
            })

        cur.close()
        return jsonify({
            "mode": mode,
            "evening_settled": False,
            "opening_stock": opening_list, 
            "existing_items": existing_items     
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# 2. API: FETCH EVENING DATA (Updated)
# ==========================================
@app.route('/api/fetch_evening_data', methods=['POST'])
def fetch_evening_data():
    if "loggedin" not in session: return jsonify({'status': 'error', 'message': 'Unauthorized'})

    try:
        emp_id = request.form.get('employee_id')
        date_str = request.form.get('date')
        
        target_date = parse_date(date_str)
        if not target_date: return jsonify({'status': 'error', 'message': 'Invalid Date'})
        formatted_date = target_date.strftime('%Y-%m-%d')
        
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # A. Check Existing Settlement
        cur.execute("SELECT * FROM evening_settle WHERE employee_id=%s AND date=%s", (emp_id, formatted_date))
        existing = cur.fetchone()

        if existing:
            if existing['status'] == 'final':
                return jsonify({'status': 'submitted', 'message': 'Already submitted.'})
            
            # Draft Mode
            cur.execute("""
                SELECT ei.product_id, ei.total_qty, ei.sold_qty, ei.return_qty, ei.unit_price, p.name, p.image 
                FROM evening_item ei JOIN products p ON ei.product_id = p.id WHERE ei.settle_id = %s
            """, (existing['id'],))
            
            items = []
            for i in cur.fetchall():
                items.append({
                    'product_id': i['product_id'], 'name': i['name'], 'image': resolve_img(i['image']),
                    'unit_price': float(i['unit_price']), 
                    'total_qty': int(i['total_qty']),
                    'sold_qty': int(i['sold_qty']), 'return_qty': int(i['return_qty'])
                })

            return jsonify({
                'status': 'success', 'source': 'draft', 
                'allocation_id': existing.get('allocation_id') or '',
                'draft_id': existing['id'], 'draft_data': existing,
                'products': items
            })

        # B. CALCULATE FRESH DATA (Using Chain Logic)
        # This will auto-include morning allocations + any previous unsettled stock
        current_stock = get_current_stock_state(cur, emp_id, formatted_date)
        
        # Get Allocation ID for linking (if any exists for today)
        cur.execute("SELECT id FROM morning_allocations WHERE employee_id=%s AND date=%s", (emp_id, formatted_date))
        alloc_row = cur.fetchone()
        alloc_id = alloc_row['id'] if alloc_row else None

        final_items = []
        for item in current_stock:
            if item['qty'] > 0:
                final_items.append({
                    'product_id': item['product_id'], 'name': item['name'], 'image': item['image'],
                    'unit_price': item['price'], 'total_qty': item['qty'],
                    'sold_qty': 0, 'return_qty': 0
                })

        if not final_items:
            return jsonify({'status': 'error', 'message': 'No stock found for this employee.'})

        return jsonify({
            'status': 'success', 
            'source': 'fresh',
            'allocation_id': alloc_id,
            'draft_id': None, 'draft_data': None,
            'products': final_items
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        if 'cur' in locals(): cur.close()


# ==========================================
# 3. ROUTE: MORNING SUBMIT (Merge Logic)
# ==========================================
@app.route('/morning', methods=['GET', 'POST'])
def morning():
    if "loggedin" not in session: return redirect(url_for("login"))
    
    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        try:
            emp_id = request.form.get('employee_id')
            date_str = request.form.get('date')
            time_str = request.form.get('timestamp')
            
            if not time_str or time_str.strip() == "":
                ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
                time_str = ist_now.strftime('%Y-%m-%d %H:%M:%S')

            p_ids = request.form.getlist('product_id[]')
            # 'opens' here comes from the UI "Opening" column. 
            # In Restock Mode, this is actually the (Previously Held) amount.
            # But for the DB, 'opening_qty' should represent the Start-of-Day opening.
            # However, simpler logic: 'opening_qty' in DB row creates the base. 'given_qty' adds to it.
            
            opens = request.form.getlist('opening[]') 
            givens = request.form.getlist('given[]')
            prices = request.form.getlist('price[]')

            formatted_date = parse_date(date_str).strftime('%Y-%m-%d')

            # Check Existing
            cursor.execute("SELECT id FROM morning_allocations WHERE employee_id=%s AND date=%s", (emp_id, formatted_date))
            existing_alloc = cursor.fetchone()

            if existing_alloc:
                alloc_id = existing_alloc['id']
            else:
                cursor.execute("INSERT INTO morning_allocations (employee_id, date, created_at) VALUES (%s, %s, %s)", 
                               (emp_id, formatted_date, time_str))
                alloc_id = cursor.lastrowid

            cnt = 0
            for i, pid in enumerate(p_ids):
                if not pid: continue
                
                # Logic: If user enters "Given: 5", we ADD 5 to stock.
                # "Opening" in UI is for display. We don't save UI Opening to DB in Restock mode to avoid overwriting Start-Day-Opening.
                
                gv = int(givens[i] or 0)
                ui_opening = int(opens[i] or 0) # This is what user saw as 'Opening'
                pr = float(prices[i] or 0)

                # Check if item exists in this allocation
                cursor.execute("SELECT id, given_qty FROM morning_allocation_items WHERE allocation_id=%s AND product_id=%s", (alloc_id, pid))
                existing_item = cursor.fetchone()

                if existing_item:
                    # RESTOCK MERGE: Add new given to old given
                    new_total_given = int(existing_item['given_qty']) + gv
                    cursor.execute("UPDATE morning_allocation_items SET given_qty=%s, unit_price=%s WHERE id=%s", 
                                   (new_total_given, pr, existing_item['id']))
                else:
                    # NEW ITEM: Insert
                    # If this is a Restock (alloc exists), and we are adding a NEW item:
                    # The 'ui_opening' might be from Yesterday. 
                    # If we save 'ui_opening' as 'opening_qty', it correctly carries forward yesterday's stock into today's record.
                    cursor.execute("INSERT INTO morning_allocation_items (allocation_id, product_id, opening_qty, given_qty, unit_price) VALUES (%s, %s, %s, %s, %s)", 
                                   (alloc_id, pid, ui_opening, gv, pr))

                if gv > 0:
                    cursor.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (gv, pid))
                cnt += 1

            if cnt > 0:
                conn.commit()
                flash("Stock Allocation Updated/Saved.", "success")
            else:
                flash("No items saved.", "warning")
            return redirect(url_for('morning'))

        except Exception as e:
            conn.rollback()
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('morning'))

    # GET
    cursor.execute("SELECT id, name, image FROM employees WHERE status='active' ORDER BY name")
    emps = cursor.fetchall()
    for e in emps: e['image'] = resolve_img(e['image'])

    cursor.execute("SELECT id, name, price, image, stock FROM products ORDER BY name")
    prods = [{
        'id': p['id'], 'name': p['name'], 'price': float(p['price']), 
        'image': resolve_img(p['image']), 'stock': int(p['stock'] or 0)
    } for p in cursor.fetchall()]
    
    return render_template('morning.html', employees=emps, products=prods, today_date=date.today().strftime('%d-%m-%Y'))

# --- OTHER ROUTES (EVENING POST, LOGIN, ETC) REMAIN SAME AS PROVIDED PREVIOUSLY ---
@app.route('/evening', methods=['GET', 'POST'])
def evening():
    if "loggedin" not in session: return redirect(url_for("login"))
    
    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        try:
            status = request.form.get('status')
            draft_id = request.form.get('draft_id')
            alloc_id = request.form.get('allocation_id')
            emp_id = request.form.get('h_employee')
            date_val = request.form.get('h_date')
            
            ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
            time_str = ist_now.strftime('%Y-%m-%d %H:%M:%S') 
            
            cursor.execute("SELECT id FROM evening_settle WHERE employee_id=%s AND date=%s", (emp_id, date_val))
            existing_record = cursor.fetchone()

            final_alloc_id = alloc_id if alloc_id and alloc_id.strip() not in ['', '0'] else None

            total_amt = float(request.form.get('totalAmount') or 0)
            discount = float(request.form.get('discount') or 0)
            online = float(request.form.get('online') or 0)
            cash = float(request.form.get('cash') or 0)
            
            emp_c = float(request.form.get('emp_credit_amount') or 0)
            emp_c_n = request.form.get('emp_credit_note')
            emp_d = float(request.form.get('emp_debit_amount') or 0)
            emp_d_n = request.form.get('emp_debit_note')
            due_n = request.form.get('due_note')

            if existing_record:
                settle_id = existing_record['id']
                cursor.execute("""
                    UPDATE evening_settle SET total_amount=%s, cash_money=%s, online_money=%s, discount=%s, 
                    emp_credit_amount=%s, emp_credit_note=%s, emp_debit_amount=%s, emp_debit_note=%s, 
                    due_note=%s, status=%s, created_at=%s, allocation_id=%s WHERE id=%s
                """, (total_amt, cash, online, discount, emp_c, emp_c_n, emp_d, emp_d_n, due_n, status, time_str, final_alloc_id, settle_id))
                cursor.execute("DELETE FROM evening_item WHERE settle_id=%s", (settle_id,))
            else:
                cursor.execute("""
                    INSERT INTO evening_settle (allocation_id, employee_id, date, total_amount, cash_money, online_money, discount, 
                    emp_credit_amount, emp_credit_note, emp_debit_amount, emp_debit_note, due_note, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (final_alloc_id, emp_id, date_val, total_amt, cash, online, discount, emp_c, emp_c_n, emp_d, emp_d_n, due_n, status, time_str))
                settle_id = cursor.lastrowid

            p_ids = request.form.getlist('product_id[]')
            t_qtys = request.form.getlist('total_qty[]')
            s_qtys = request.form.getlist('sold[]')
            r_qtys = request.form.getlist('return[]')
            prices = request.form.getlist('price[]')

            for i, pid in enumerate(p_ids):
                if not pid: continue
                tot = int(float(t_qtys[i] or 0))
                sold = int(float(s_qtys[i] or 0))
                ret = int(float(r_qtys[i] or 0))
                pr = float(prices[i] or 0)
                rem = max(0, tot - sold - ret) 

                cursor.execute("INSERT INTO evening_item (settle_id, product_id, total_qty, sold_qty, return_qty, remaining_qty, unit_price) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                               (settle_id, pid, tot, sold, ret, rem, pr))
                
                if status == 'final' and ret > 0:
                    cursor.execute("UPDATE products SET stock = stock + %s WHERE id = %s", (ret, pid))

            if status == 'final':
                if emp_c > 0: cursor.execute("INSERT INTO employee_transactions (employee_id, transaction_date, type, amount, description, created_at) VALUES (%s, %s, 'credit', %s, %s, %s)", (emp_id, date_val, emp_c, f"Credit #{settle_id}", time_str))
                if emp_d > 0: cursor.execute("INSERT INTO employee_transactions (employee_id, transaction_date, type, amount, description, created_at) VALUES (%s, %s, 'debit', %s, %s, %s)", (emp_id, date_val, emp_d, f"Debit #{settle_id}", time_str))

            conn.commit()
            flash("Saved successfully!", "success")
            return redirect(url_for('evening'))

        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "danger")
            return redirect(url_for('evening'))

    cursor.execute("SELECT id, name, image FROM employees WHERE status='active' ORDER BY name")
    emps = cursor.fetchall()
    for e in emps: e['image'] = resolve_img(e['image'])
    return render_template('evening.html', employees=emps, today=date.today().strftime('%d-%m-%Y'))

# --- 5. ROUTE: ALLOCATION LIST (Formatted Date/Time & Status Check) ---
@app.route('/allocation_list', methods=['GET'])
def allocation_list():
    if "loggedin" not in session: return redirect(url_for("login"))

    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    date_filter = request.args.get('date')
    emp_filter = request.args.get('employee_id')
    
    query = """
        SELECT 
            ma.id, ma.date, ma.created_at, 
            e.name as emp_name, e.image as emp_image,
            (SELECT COUNT(*) FROM morning_allocation_items WHERE allocation_id = ma.id) as item_count,
            (SELECT status FROM evening_settle WHERE allocation_id = ma.id LIMIT 1) as evening_status
        FROM morning_allocations ma
        JOIN employees e ON ma.employee_id = e.id
        WHERE 1=1
    """
    params = []

    if date_filter:
        d_obj = parse_date(date_filter)
        if d_obj:
            query += " AND ma.date = %s"
            params.append(d_obj.strftime('%Y-%m-%d'))
    
    if emp_filter and emp_filter != 'all':
        query += " AND ma.employee_id = %s"
        params.append(emp_filter)

    query += " ORDER BY ma.date DESC, ma.created_at DESC"

    cursor.execute(query, tuple(params))
    allocations = cursor.fetchall()

    for a in allocations:
        a['emp_image'] = resolve_img(a['emp_image'])
        
        if isinstance(a['date'], (date, datetime)):
            a['formatted_date'] = a['date'].strftime('%d-%m-%Y')
        else:
            try: a['formatted_date'] = datetime.strptime(str(a['date']), '%Y-%m-%d').strftime('%d-%m-%Y')
            except: a['formatted_date'] = str(a['date'])

        if a.get('created_at'):
            if isinstance(a['created_at'], datetime): a['formatted_time'] = a['created_at'].strftime('%I:%M:%S %p')
            elif isinstance(a['created_at'], timedelta): a['formatted_time'] = (datetime.min + a['created_at']).strftime('%I:%M:%S %p')
            else: a['formatted_time'] = str(a['created_at'])
        else: a['formatted_time'] = "-"

        if a['evening_status'] == 'final':
            a['status_badge'] = 'Submitted'; a['status_class'] = 'bg-success'; a['is_locked'] = True
        elif a['evening_status'] == 'draft':
            a['status_badge'] = 'Draft'; a['status_class'] = 'bg-warning text-dark'; a['is_locked'] = False 
        else:
            a['status_badge'] = 'Pending'; a['status_class'] = 'bg-danger'; a['is_locked'] = False

    cursor.execute("SELECT id, name FROM employees WHERE status='active' ORDER BY name")
    employees = cursor.fetchall()

    return render_template('allocation_list.html', allocations=allocations, employees=employees, filters={'date': date_filter, 'employee_id': emp_filter})


# --- NEW ROUTE: DRAFT LIST PAGE ---
@app.route('/evening/drafts')
def draft_evening_list():
    if "loggedin" not in session: return redirect(url_for("login"))
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Check if status column exists first via try/catch in query
    try:
        cur.execute("""
            SELECT s.*, e.name as emp_name, e.image as emp_image 
            FROM evening_settle s 
            JOIN employees e ON s.employee_id = e.id 
            WHERE s.status = 'draft' 
            ORDER BY s.date DESC, s.id DESC
        """)
        drafts = cur.fetchall()
        for d in drafts: d['emp_image'] = resolve_img(d['emp_image'])
    except:
        drafts = [] # Fallback if table doesn't have status col yet
        
    cur.close()
    return render_template('draft_evening.html', drafts=drafts)




# ---------------------------------------------------------
# API: FETCH MORNING STOCK (With Holiday Logic)
# ---------------------------------------------------------
@app.route('/api/fetch_morning_allocation', methods=['GET', 'POST']) 
def fetch_morning_allocation(): 
    if "loggedin" not in session: return jsonify({'status': 'error', 'message': 'Unauthorized'})

    try:
        # Use request.values to grab from query string (GET) or body (POST)
        employee_id = request.values.get('employee_id')
        date_str = request.values.get('date') 
        
        if not employee_id or not date_str:
            return jsonify({'status': 'error', 'message': 'Missing parameters'})

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Parse Date (dd-mm-yyyy or yyyy-mm-dd)
        date_obj = parse_date(date_str)
        if not date_obj:
            return jsonify({'status': 'error', 'message': 'Invalid Date Format (Expected dd-mm-yyyy)'})

        formatted_date = date_obj.strftime('%Y-%m-%d')
        
        # HOLIDAY LOGIC: Fetch LAST Closing Stock (Opening for Today)
        
        # 1. Find the LAST COMPLETED Evening Settlement for this employee BEFORE today
        # We must ignore drafts here, only 'final' (or missing status which implies final old records)
        # Using a safer query that handles if 'status' column doesn't exist yet by ignoring it if error, 
        # but since we want robust logic:
        
        # NOTE: If you haven't added 'status' column yet, this query might fail if we add WHERE status='final'.
        # Assuming you will add it or legacy records are final.
        
        cur.execute("""
            SELECT id 
            FROM evening_settle 
            WHERE employee_id = %s AND date < %s 
            -- AND (status = 'final' OR status IS NULL) -- Uncomment after adding status column
            ORDER BY date DESC, id DESC LIMIT 1
        """, (employee_id, formatted_date))
        
        last_settle = cur.fetchone()
        
        stock_map = {}
        
        if last_settle:
            last_settle_id = last_settle['id']
            # 2. Fetch the remaining items from that settlement
            cur.execute("""
                SELECT product_id, remaining_qty 
                FROM evening_item 
                WHERE settle_id = %s
            """, (last_settle_id,))
            
            items = cur.fetchall()
            stock_map = {item['product_id']: item['remaining_qty'] for item in items}

        # --- IMPORTANT: Also fetch items allocated THIS MORNING (Today's Allocation) ---
        # So we can calculate [Total = Opening + Given Today]
        cur.execute("""
            SELECT ma.id as alloc_id, mai.product_id, mai.opening_qty, mai.given_qty, mai.unit_price, p.name, p.image
            FROM morning_allocations ma
            JOIN morning_allocation_items mai ON ma.id = mai.allocation_id
            JOIN products p ON mai.product_id = p.id
            WHERE ma.employee_id = %s AND ma.date = %s
        """, (employee_id, formatted_date))
        
        morning_items = cur.fetchall()
        
        # Prepare the final list of items for the Evening Settlement Table
        # Structure: Product ID, Name, Image, Unit Price, Total Qty (Opening + Given)
        
        final_items_list = []
        if morning_items:
            for item in morning_items:
                total_qty = int(item['opening_qty'] or 0) + int(item['given_qty'] or 0)
                if total_qty > 0:
                    final_items_list.append({
                        'product_id': item['product_id'],
                        'product_name': item['name'],
                        'image': resolve_img(item['image']),
                        'unit_price': float(item['unit_price']),
                        'total_qty': total_qty,
                        'remaining_qty': total_qty, # Initially remaining is total (before sales)
                        'sold_qty': 0,
                        'return_qty': 0
                    })
            
            # Allocation ID is needed to link the settlement later
            alloc_id = morning_items[0]['alloc_id']
        else:
            alloc_id = None
            # If no morning allocation found for today, maybe user wants to settle previous outstanding stock?
            # Or maybe they just forgot to do morning allocation. 
            # For now, let's return empty list but with success status so UI doesn't crash.
        
        return jsonify({
            'status': 'success',
            'allocation_id': alloc_id,
            'items': final_items_list,
            'allocation_date': formatted_date
        })

    except Exception as e:
        app.logger.error(f"Morning Fetch Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        if 'cur' in locals(): cur.close()




@app.route('/morning/edit/<int:allocation_id>', methods=['GET', 'POST'])
def edit_morning_allocation(allocation_id):
    if "loggedin" not in session: return redirect(url_for("login"))

    db_cursor = None
    try:
        db_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Security Check: Cannot edit if Evening Settlement is done
        db_cursor.execute("SELECT id FROM evening_settle WHERE allocation_id = %s", (allocation_id,))
        if db_cursor.fetchone():
            flash("Cannot edit: Evening settlement already submitted.", "warning")
            return redirect(url_for('allocation_list'))

        if request.method == 'POST':
            # Form Data
            item_ids = request.form.getlist('item_id[]')
            product_ids = request.form.getlist('product_id[]')
            opening_qtys = request.form.getlist('opening[]')
            given_qtys = request.form.getlist('given[]')
            prices = request.form.getlist('price[]')

            # Fetch existing IDs to detect deletions
            db_cursor.execute("SELECT id FROM morning_allocation_items WHERE allocation_id = %s", (allocation_id,))
            current_db_ids = [str(r['id']) for r in db_cursor.fetchall()]
            processed_ids = []

            for i, pid in enumerate(product_ids):
                if not pid: continue
                
                item_id = item_ids[i]
                # Safe conversions
                op_qty = int(opening_qtys[i]) if opening_qtys[i] else 0
                gv_qty = int(given_qtys[i]) if given_qtys[i] else 0
                price = float(prices[i]) if prices[i] else 0.0

                if item_id == 'new_item':
                    # Insert New Item
                    db_cursor.execute("""
                        INSERT INTO morning_allocation_items 
                        (allocation_id, product_id, opening_qty, given_qty, unit_price)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (allocation_id, pid, op_qty, gv_qty, price))
                else:
                    # Update Existing
                    processed_ids.append(item_id)
                    db_cursor.execute("""
                        UPDATE morning_allocation_items 
                        SET product_id=%s, opening_qty=%s, given_qty=%s, unit_price=%s
                        WHERE id=%s AND allocation_id=%s
                    """, (pid, op_qty, gv_qty, price, item_id, allocation_id))

            # Delete Removed Items
            for db_id in current_db_ids:
                if db_id not in processed_ids:
                    db_cursor.execute("DELETE FROM morning_allocation_items WHERE id=%s", (db_id,))

            mysql.connection.commit()
            flash("Allocation updated successfully!", "success")
            return redirect(url_for('allocation_list'))

        # GET Request
        # 1. Allocation Header
        db_cursor.execute("""
            SELECT ma.*, e.name as employee_name, e.image as emp_image 
            FROM morning_allocations ma
            JOIN employees e ON ma.employee_id = e.id
            WHERE ma.id = %s
        """, (allocation_id,))
        allocation = db_cursor.fetchone()
        
        if not allocation:
            flash("Record not found.", "danger")
            return redirect(url_for('allocation_list'))
            
        allocation['emp_image'] = resolve_img(allocation['emp_image'])

        # 2. Items
        db_cursor.execute("""
            SELECT mai.*, p.image 
            FROM morning_allocation_items mai
            JOIN products p ON mai.product_id = p.id
            WHERE mai.allocation_id = %s
        """, (allocation_id,))
        items = db_cursor.fetchall()
        for item in items: item['image'] = resolve_img(item['image'])

        # 3. Product List for Dropdown
        # FIX: Removed "WHERE status='Active'" because your products table has no status column
        db_cursor.execute("SELECT id, name, price, image FROM products ORDER BY name")
        all_products = db_cursor.fetchall()
        
        # Prepare JSON for JS
        products_js = []
        product_options = ""
        for p in all_products:
            p_img = resolve_img(p['image'])
            products_js.append({'id': p['id'], 'name': p['name'], 'price': float(p['price']), 'image': p_img})
            product_options += f'<option value="{p["id"]}">{p["name"]}</option>'

        return render_template('morning_edit.html',
                               allocation=allocation,
                               items=items,
                               products=products_js,
                               productOptions=product_options)

    except Exception as e:
        if db_cursor: mysql.connection.rollback()
        # app.logger.error(f"Edit Error: {e}")
        print(f"Edit Error: {e}")
        flash(f"Error: {e}", "danger")
        return redirect(url_for('allocation_list'))
    finally:
        if db_cursor: db_cursor.close()


# --- DELETE ALLOCATION ROUTE ---
@app.route('/morning/delete/<int:id>', methods=['POST'])
def delete_allocation(id):
    if "loggedin" not in session: return redirect(url_for("login"))
    
    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # Check Dependency
        cursor.execute("SELECT id FROM evening_settle WHERE allocation_id = %s", (id,))
        if cursor.fetchone():
            flash("Cannot delete: Linked to Evening Settlement.", "danger")
            return redirect(url_for('allocation_list'))

        # 1. Fetch Items to Reverse Stock
        cursor.execute("SELECT product_id, given_qty FROM morning_allocation_items WHERE allocation_id = %s", (id,))
        items = cursor.fetchall()

        # 2. Add Given Qty BACK to Main Stock
        for item in items:
            if item['given_qty'] > 0:
                cursor.execute("UPDATE products SET stock = stock + %s WHERE id = %s", 
                               (item['given_qty'], item['product_id']))

        # 3. Delete Records
        cursor.execute("DELETE FROM morning_allocation_items WHERE allocation_id = %s", (id,))
        cursor.execute("DELETE FROM morning_allocations WHERE id = %s", (id,))
        
        conn.commit()
        flash("Allocation deleted and stock restored.", "success")
            
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting: {str(e)}", "danger")
    finally:
        cursor.close()
        
    return redirect(url_for('allocation_list'))


# ---------------------------------------------------------
# 3. EVENING MASTER (History & Drafts) - WITH FILTERS
# ---------------------------------------------------------
# --- ADMIN EVENING MASTER ROUTE (Redesigned Stats) ---
# --- ADMIN EVENING MASTER ROUTE ---
@app.route('/evening/master')
def admin_evening_master():
    if "loggedin" not in session: return redirect(url_for("login"))
    
    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    # --- 1. Get Filter Params ---
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    emp_filter = request.args.get('employee_id')

    # --- 2. Build Query ---
    # Fetching necessary fields, including e.phone (not mobile) based on schema
    query = """
        SELECT es.id, es.date, es.created_at, 
               IFNULL(es.total_amount, 0) as total_amount, 
               IFNULL(es.cash_money, 0) as cash_money, 
               IFNULL(es.online_money, 0) as online_money, 
               IFNULL(es.discount, 0) as discount,
               e.name as emp_name, e.image as emp_image, e.phone as emp_mobile
        FROM evening_settle es
        JOIN employees e ON es.employee_id = e.id
        WHERE 1=1
    """
    params = []

    if start_date:
        try:
            # Safe check for parse_date helper
            dt = parse_date(start_date) if 'parse_date' in globals() else datetime.strptime(start_date, '%d-%m-%Y')
            query += " AND es.date >= %s"
            params.append(dt.strftime('%Y-%m-%d'))
        except ValueError: pass
    
    if end_date:
        try:
            dt = parse_date(end_date) if 'parse_date' in globals() else datetime.strptime(end_date, '%d-%m-%Y')
            query += " AND es.date <= %s"
            params.append(dt.strftime('%Y-%m-%d'))
        except ValueError: pass

    if emp_filter and emp_filter != 'all':
        query += " AND es.employee_id = %s"
        params.append(emp_filter)

    query += " ORDER BY es.date DESC, es.created_at DESC"
    
    cursor.execute(query, tuple(params))
    settlements = cursor.fetchall()
    
    # Stats Accumulators
    stats = {
        'total_sales': 0.0, 
        'net_sales': 0.0,
        'cash': 0.0,
        'online': 0.0,
        'discount': 0.0
    }
    
    for s in settlements:
        # Image Resolution Logic
        if s['emp_image']:
            # If it starts with http/https (Cloudinary), keep it. 
            # Otherwise assume local upload
            if s['emp_image'].startswith('http'):
                pass 
            else:
                s['emp_image'] = url_for('static', filename='uploads/' + s['emp_image'])
        else:
            s['emp_image'] = url_for('static', filename='img/default-user.png')

        # Date Formatting (dd-mm-yyyy)
        if isinstance(s['date'], (date, datetime)):
            s['formatted_date'] = s['date'].strftime('%d-%m-%Y')
        else:
            try:
                s['formatted_date'] = datetime.strptime(str(s['date']), '%Y-%m-%d').strftime('%d-%m-%Y')
            except ValueError:
                s['formatted_date'] = str(s['date'])

        # Time Formatting (12-hour)
        if s.get('created_at'):
             # If it's a timedelta, convert (rare but possible in some DB drivers)
            if isinstance(s['created_at'], timedelta):
                 dummy_date = datetime.min + s['created_at']
                 s['formatted_time'] = dummy_date.strftime('%I:%M %p')
            # If it's datetime
            elif isinstance(s['created_at'], datetime):
                 s['formatted_time'] = s['created_at'].strftime('%I:%M %p')
            else:
                 s['formatted_time'] = str(s['created_at'])
        else:
            s['formatted_time'] = ""

        # Numeric Safety
        t_amt = float(s['total_amount'])
        c_money = float(s['cash_money'])
        o_money = float(s['online_money'])
        disc = float(s['discount'])
        
        # Calculations
        s['net_sales'] = t_amt - disc
        
        paid = c_money + o_money + disc
        s['due_amount'] = t_amt - paid
        
        # Stats Aggregation
        stats['total_sales'] += t_amt
        stats['discount'] += disc
        stats['net_sales'] += (t_amt - disc)
        stats['cash'] += c_money
        stats['online'] += o_money

    # --- 3. Fetch Employees for Filter ---
    cursor.execute("SELECT id, name FROM employees WHERE status='active' ORDER BY name")
    employees = cursor.fetchall()

    return render_template('admin/evening_master.html', 
                           settlements=settlements, 
                           stats=stats,
                           employees=employees,
                           filters={'start': start_date, 'end': end_date, 'emp': emp_filter})



# --- 2. EDIT SETTLEMENT (Logic Critical) ---

@app.route('/admin/evening/edit/<int:settle_id>', methods=['GET', 'POST'])
def admin_edit_evening(settle_id):
    if "loggedin" not in session: return redirect(url_for("login"))
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        try:
            # Revert stock logic for old items
            cur.execute("SELECT * FROM evening_item WHERE settle_id = %s", (settle_id,))
            old_items = {item['product_id']: item for item in cur.fetchall()}
            
            total_amt = request.form.get('totalAmount')
            cash = request.form.get('cash')
            online = request.form.get('online')
            discount = request.form.get('discount')
            
            p_ids = request.form.getlist('product_id[]')
            sold_qtys = request.form.getlist('sold[]')
            return_qtys = request.form.getlist('return[]')
            # Prices might not change, but good to have
            
            for i, pid in enumerate(p_ids):
                pid = int(pid)
                new_sold = int(sold_qtys[i] or 0)
                new_ret = int(return_qtys[i] or 0)
                
                old_item = old_items.get(pid)
                if old_item:
                    diff_sold = new_sold - old_item['sold_qty']
                    if diff_sold != 0:
                        cur.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (diff_sold, pid))
                    
                    new_remain = old_item['total_qty'] - new_sold - new_ret
                    if new_remain < 0: new_remain = 0
                    
                    cur.execute("""
                        UPDATE evening_item 
                        SET sold_qty=%s, return_qty=%s, remaining_qty=%s 
                        WHERE id=%s
                    """, (new_sold, new_ret, new_remain, old_item['id']))
            
            cur.execute("UPDATE evening_settle SET total_amount=%s, cash_money=%s, online_money=%s, discount=%s WHERE id=%s", (total_amt, cash, online, discount, settle_id))
            mysql.connection.commit()
            flash("Updated", "success")
            return redirect(url_for('admin_evening_master'))
        except Exception as e:
            mysql.connection.rollback()
            return redirect(url_for('admin_evening_master'))
            
    cur.execute("SELECT es.*, e.name as emp_name FROM evening_settle es JOIN employees e ON es.employee_id = e.id WHERE es.id = %s", (settle_id,))
    settlement = cur.fetchone()
    
    cur.execute("SELECT ei.*, p.name as product_name, p.image FROM evening_item ei JOIN products p ON ei.product_id = p.id WHERE ei.settle_id = %s", (settle_id,))
    items = []
    for r in cur.fetchall():
        r['image'] = resolve_img(r['image'])
        items.append(r)
    cur.close()
    
    return render_template('admin/edit_evening_settle.html', settlement=settlement, items=items)


# --- THE REQUESTED FIX: DELETE & REVERT STOCK ---
@app.route('/admin/evening/delete/<int:settle_id>', methods=['POST'])
def admin_delete_evening(settle_id):
    if "loggedin" not in session: return redirect(url_for("login"))

    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    try:
        # 1. Fetch Items to Reverse Returns
        cursor.execute("SELECT product_id, return_qty FROM evening_item WHERE settle_id = %s", (settle_id,))
        items = cursor.fetchall()

        # 2. Subtract Returns FROM Stock (because we are undoing the return)
        for item in items:
            if item['return_qty'] > 0:
                cursor.execute("UPDATE products SET stock = stock - %s WHERE id = %s", 
                               (item['return_qty'], item['product_id']))

        # 3. Delete Record (and Ledger entries ideally, but cascading handles FK if set, otherwise manual delete)
        # Note: If your DB has FK constraints on ledger linked to settle_id, good. 
        # If not, you might have orphan ledger entries. Ideally delete those too based on description parsing or adding a link column.
        
        cursor.execute("DELETE FROM evening_settle WHERE id = %s", (settle_id,))
        
        conn.commit()
        flash("Settlement Deleted & Returns Reversed.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Delete Error: {e}", "danger")
    finally:
        cursor.close()
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
# ... existing imports ...

# ============================================================
#  EMPLOYEE FINANCE LIST ROUTE (Update this in app.py)
# ============================================================
@app.route('/emp_list')
def emp_list():
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # FETCH EMPLOYEES: Changed ORDER BY to 'id ASC'
    # Also added LEFT JOIN to ensure position_name is fetched if position ID is used
    cursor.execute("""
        SELECT e.*, p.position_name 
        FROM employees e
        LEFT JOIN employee_positions p ON e.position_id = p.id 
        WHERE e.status = 'active' 
        ORDER BY e.id ASC
    """)
    employees = cursor.fetchall()
    
    # Calculate Global Stats (Unchanged)
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN type = 'debit' THEN amount ELSE 0 END) as total_debit,
            SUM(CASE WHEN type = 'credit' THEN amount ELSE 0 END) as total_credit
        FROM employee_transactions
    """)
    stats = cursor.fetchone()
    
    total_debit = float(stats['total_debit'] or 0)
    total_credit = float(stats['total_credit'] or 0)
    net_holding = total_debit - total_credit 
    
    cursor.close()
    
    return render_template('emp_list.html', 
                           employees=employees, 
                           stats={
                               'total_debit': total_debit,
                               'total_credit': total_credit,
                               'net_holding': net_holding
                           })




# --- 1. Fix for PDF Generation (Handle None Dates) ---
@app.route('/employee/ledger/pdf/<int:employee_id>')
def employee_ledger_pdf(employee_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM employees WHERE id=%s", (employee_id,))
    emp = cur.fetchone()
    
    # Fetch transactions (Ensure created_at is selected for time)
    cur.execute("""
        SELECT * FROM employee_transactions 
        WHERE employee_id=%s 
        ORDER BY transaction_date ASC, created_at ASC
    """, (employee_id,))
    transactions = cur.fetchall()
    cur.close()
    
    if not emp: return "Employee not found", 404
    
    pdf = PDF() 
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Employee Ledger Statement", 0, 1, 'C')
    pdf.ln(5)
    
    # Info
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 6, f"Employee: {emp['name']}", 0, 1)
    # Handle missing position safely
    pos_name = emp.get('position') or emp.get('position_name') or 'N/A'
    pdf.cell(0, 6, f"Position: {pos_name}", 0, 1)
    
    # Current Time (IST)
    now_ist = datetime.now() + timedelta(hours=5, minutes=30) # Approx adjustment if server is UTC
    pdf.cell(0, 6, f"Generated: {now_ist.strftime('%d-%m-%Y %I:%M %p')}", 0, 1)
    pdf.ln(10)
    
    # Table Header
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(230, 230, 230)
    
    pdf.cell(25, 8, "Date", 1, 0, 'C', 1)
    pdf.cell(20, 8, "Time", 1, 0, 'C', 1)
    pdf.cell(65, 8, "Description", 1, 0, 'L', 1)
    pdf.cell(25, 8, "Debit", 1, 0, 'R', 1)
    pdf.cell(25, 8, "Credit", 1, 0, 'R', 1)
    pdf.cell(30, 8, "Balance", 1, 1, 'R', 1)
    
    pdf.set_font("Arial", '', 8)
    balance = 0.0
    
    for t in transactions:
        amt = float(t['amount'])
        debit = 0.0
        credit = 0.0
        
        if t['type'] == 'debit':
            debit = amt
            balance += amt
        else:
            credit = amt
            balance -= amt
            
        # --- FIX: Handle None Date ---
        if t['transaction_date']:
            d_str = t['transaction_date'].strftime('%d-%m-%Y')
        else:
            d_str = "N/A"
            
        # --- FIX: Handle Time & Convert to IST ---
        if t.get('created_at'):
            # Assuming 'created_at' from DB is UTC, add 5:30 for IST
            # If your DB is already IST, remove the timedelta
            local_time = t['created_at'] + timedelta(hours=5, minutes=30)
            t_str = local_time.strftime('%I:%M %p')
        else:
            t_str = "-"
        
        pdf.cell(25, 7, d_str, 1, 0, 'C')
        pdf.cell(20, 7, t_str, 1, 0, 'C')
        pdf.cell(65, 7, pdf.safe_text(t['description']), 1, 0, 'L')
        pdf.cell(25, 7, f"{debit:.2f}" if debit > 0 else "-", 1, 0, 'R')
        pdf.cell(25, 7, f"{credit:.2f}" if credit > 0 else "-", 1, 0, 'R')
        pdf.cell(30, 7, f"{balance:.2f}", 1, 1, 'R')
        
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    status = "Due from Employee" if balance > 0 else "Payable to Employee"
    pdf.cell(0, 10, f"Net Closing Balance: {abs(balance):.2f} ({status})", 0, 1, 'R')
    
    response = make_response(pdf.output(dest='S').encode('latin1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={emp["name"]}_Ledger.pdf'
    return response



# --- HELPER: Get Cloudinary Public ID from URL (for legacy support if needed) ---
def get_public_id_from_url(url):
    """Extracts public_id from a full Cloudinary URL if present."""
    if url and "res.cloudinary.com" in url:
        try:
            parts = url.split("/upload/")
            if len(parts) > 1:
                version_and_id = parts[1].split("/")
                if version_and_id[0].startswith("v"):
                    public_id_with_ext = "/".join(version_and_id[1:])
                else:
                    public_id_with_ext = "/".join(version_and_id)
                return public_id_with_ext.rsplit(".", 1)[0]
        except: return url
    return url 



@app.route('/employee-ledger/<int:employee_id>')
def emp_ledger(employee_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Fetch Employee
    cur.execute("SELECT id, name, position, email, phone, image FROM employees WHERE id = %s", [employee_id])
    employee = cur.fetchone()
    
    if not employee:
        flash('Employee not found!', 'danger')
        return redirect(url_for('emp_list'))
        
    # 2. Fetch Transactions
    cur.execute("""
        SELECT id, transaction_date, type, amount, description, created_at 
        FROM employee_transactions 
        WHERE employee_id = %s 
        ORDER BY transaction_date DESC, created_at DESC
    """, [employee_id])
    transactions_from_db = cur.fetchall()
    
    cur.close()
    
    # --- ROBUST TIME HANDLING ---
    # We use specific imports to avoid conflicts
    from datetime import datetime as dt_class, date as date_class, timedelta
    import pytz # Optional if installed, else manual logic below
    
    # Sort Logic: Handle None values safely
    # If transaction_date is None, use min date. Same for created_at.
    transactions_calc = sorted(
        transactions_from_db, 
        key=lambda x: (
            x['transaction_date'] or date_class.min, 
            x['created_at'] or dt_class.min
        )
    )
    
    running_balance = 0.0
    total_debit = 0.0
    total_credit = 0.0
    has_opening_balance = False
    
    processed_transactions = []
    
    for t in transactions_calc:
        amt = float(t['amount'])
        
        # Calculate Balance (Oldest first logic for math)
        if t['type'] == 'debit':
            running_balance += amt
            total_debit += amt
        else:
            running_balance -= amt
            total_credit += amt
            
        if t['description'] == 'Opening Balance':
            has_opening_balance = True
            
        t_dict = dict(t)
        t_dict['balance'] = running_balance
        
        # --- TIME FORMATTING (IST) ---
        # Converts UTC server time to IST (+5:30)
        if t.get('created_at'):
            # Manual conversion (Robust without external libs)
            local_time = t['created_at'] + timedelta(hours=5, minutes=30)
            t_dict['time_str'] = local_time.strftime('%I:%M %p')
        else:
            t_dict['time_str'] = "-"
            
        processed_transactions.append(t_dict)
        
    # Reverse to show Newest First in UI
    transactions_display = processed_transactions[::-1]

    return render_template('emp_ledger.html', 
                           employee=employee, 
                           transactions=transactions_display, 
                           final_balance=running_balance,
                           total_debit=total_debit,
                           total_credit=total_credit,
                           has_opening_balance=has_opening_balance)



@app.route('/add-opening-balance/<int:employee_id>', methods=['GET', 'POST'])
def add_opening_balance(employee_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        amount = float(request.form['amount'])
        type_ = request.form['type']
        date_ = request.form['date']
        
        cur.execute("SELECT id FROM employee_transactions WHERE employee_id=%s AND description='Opening Balance'", (employee_id,))
        exists = cur.fetchone()
        
        if exists:
            cur.execute("""
                UPDATE employee_transactions 
                SET amount=%s, type=%s, transaction_date=%s, created_at=NOW() 
                WHERE id=%s
            """, (amount, type_, date_, exists['id']))
            flash('Opening Balance Updated!', 'info')
        else:
            cur.execute("""
                INSERT INTO employee_transactions (employee_id, transaction_date, type, amount, description, created_at)
                VALUES (%s, %s, %s, %s, 'Opening Balance', NOW())
            """, (employee_id, date_, type_, amount))
            flash('Opening Balance Added!', 'success')
            
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('emp_ledger', employee_id=employee_id))
        
    cur.execute("SELECT * FROM employees WHERE id=%s", (employee_id,))
    emp = cur.fetchone()
    cur.execute("SELECT * FROM employee_transactions WHERE employee_id=%s AND description='Opening Balance'", (employee_id,))
    existing = cur.fetchone()
    cur.close()
    
    return render_template('add_opening_balance.html', employee=emp, existing=existing)

# Paste this into your app.py, replacing the existing add_transaction route


# --- 1. Add Transaction Route ---
@app.route('/add-transaction/<int:employee_id>', methods=['GET', 'POST'])
def add_transaction(employee_id):
    if 'loggedin' not in session: return redirect(url_for('login'))
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        # Get raw date from Flatpickr (dd-mm-yyyy)
        raw_date = request.form['transaction_date']
        
        # Convert to MySQL format (yyyy-mm-dd)
        trans_date = parse_date_input(raw_date)
        
        trans_type = request.form['type'] 
        amount = request.form['amount']
        description = request.form['description']
        
        # Get EXACT current time in IST
        ist_now = get_ist_now()
        
        # We store 'transaction_date' as the date selected by user
        # We store 'created_at' as the precise timestamp of entry in IST
        cur.execute("""
            INSERT INTO employee_transactions (employee_id, transaction_date, type, amount, description, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (employee_id, trans_date, trans_type, amount, description, ist_now))
        
        mysql.connection.commit()
        cur.close()
        flash('Transaction Added Successfully!', 'success')
        return redirect(url_for('emp_ledger', employee_id=employee_id))
    
    cur.execute("SELECT id, name FROM employees WHERE id = %s", [employee_id])
    employee = cur.fetchone()
    cur.close()
    
    selected_type = request.args.get('type', 'credit') 
    
    return render_template('add_transaction.html', employee=employee, selected_type=selected_type)


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














































































































