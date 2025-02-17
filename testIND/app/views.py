import uuid
from django.shortcuts import render, redirect, get_object_or_404
from .models import CatalogHeading, CatalogSubHeading, Order, Product, CartItem, CustomUser
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import smtplib, random, string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404
from .models import CartItem
from datetime import datetime
from django.db import transaction
from .models import OrderSerial  # Import the OrderSerial model


html_file_path = "app/templates/mail.html"  # Replace with the path to your HTML file

# Login view
def user_login(request):
    if request.method == "POST":
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(request, username=email, password=password)
        if user is not None:
            # Log the user in
            login(request, user)         
            request.session['name'] = user.first_name  + " " +user.last_name 
            request.session['email'] = user.email
            return redirect('home')
        else:
            # If invalid, return an error message
            return render(request, 'login.html', {'error': 'Invalid username or password'})
    
    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    request.session.clear()
    return redirect('user_login')  

def home(request):
    return render(request, 'base.html')

def products(request):
    return render(request, 'products.html')

def products_view(request):
    catalog_headings = CatalogHeading.objects.all()
    catalog_subheadings = CatalogSubHeading.objects.all()
    products = Product.objects.all()
    
    context = {
        'catalog_headings': catalog_headings,
        'catalog_subheadings': catalog_subheadings,
        'products': products,
    }
    
    return render(request, 'products.html', context)

# Add to cart function
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Product, CartItem

def add_to_cart(request, product_id):
    user = request.user
    product = Product.objects.get(id=product_id)
    cart_item, created = CartItem.objects.get_or_create(product=product, user_id=user)
    if not created:
        cart_item.quantity += 1
    cart_item.save()
    return redirect('cart')

# Cart view function
def generate_order_number():
    today_date = datetime.now().date()  # Get today's date (YYYY-MM-DD)
    formatted_date = today_date.strftime('%d%m%Y')  # Format as DD/MM/YYYY
    
    # Wrap in a transaction to ensure thread safety
    with transaction.atomic():
        # Check if there is an entry for today's date
        order_serial, created = OrderSerial.objects.get_or_create(date=today_date)

        if created:
            # If no entry exists, start serial from 1
            serial_number = 1
        else:
            # Increment the last serial number
            serial_number = order_serial.last_serial + 1

        # Update the last serial number in the database
        order_serial.last_serial = serial_number
        order_serial.save()

    # Format the serial number as a 4-digit zero-padded string
    serial_number_str = f"{serial_number:04d}"

    # Combine all parts into the final order number
    order_number = f"OR{formatted_date}{serial_number_str}"
    return order_number


def cart(request):
    user = request.user
    cart_items = CartItem.objects.filter(user_id=user)
    total_price = sum(item.total_price for item in cart_items)

    if request.method == "POST":
        delete_item_id = request.POST.get('delete_item', None)
        if delete_item_id:
            CartItem.objects.filter(id=delete_item_id, user_id=user).delete()
        else:
            customer_name = request.session.get('name', '')  
            customer_email = request.session.get('email', '')  

            if not customer_name or not customer_email:
                customer_name = f"{user.first_name} {user.last_name}"
                customer_email = user.email
            if customer_name and customer_email:
                order_number = generate_order_number()
                for item in cart_items:
                    order = Order(
                        product=item.product,
                        order_number=order_number,  # Use the formatted order number
                        order_date=timezone.now(),
                        order_quanity=item.quantity,  # Quantity from cart item
                        user=user,
                        status='pending',  # Default status can be 'pending'
                        delivery_estimate='1 week',  # You can update this if needed
                        
                    )
                    order.save()

                CartItem.objects.filter(user_id=user).delete()

                send_email(
                    order_number = order_number,
                    to_email=customer_email, 
                    subject="Order Requested",
                    customer_name=customer_name,  # Full name of the customer
                    html_file_path=html_file_path, 
                    request=request
                )

                return redirect("order_history")
            else:
                return redirect('login')  # Redirect to login page or show an error message

    return render(request, 'cart.html', {'cart_items': cart_items, 'total_price': total_price})


from django.contrib import messages
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        quantity = request.POST.get('quantity')

        if action == 'increment':
            item.quantity += 1
        elif action == 'decrement' and item.quantity > 1:
            item.quantity -= 1
        elif action == 'remove':
            item.delete()
            messages.success(request, "Item removed from cart.")
            return redirect('cart')

        # Handling manual input
        elif action == 'update' and quantity:
            try:
                new_quantity = int(quantity)
                if new_quantity >= 1:
                    item.quantity = new_quantity
            except ValueError:
                messages.error(request, "Invalid quantity input.")
        
        item.save()
        messages.success(request, "Cart updated successfully.")
    
    return redirect('cart')

# User checkout code
def send_email(to_email, order_number, subject, html_file_path, customer_name, request):
    sender_email = "ai@natrajinfo.in"
    sender_password = "zfpzwtcthqlldqwy"
    total_price = 0
    final_price = 0

    try:
        from .models import Order
        orders = Order.objects.filter(order_number=order_number)

        if not orders.exists():
            print(f"No orders found with order_number {order_number}")
            return None

        table_rows = ""

        for order in orders:
            total_price = round(float(order.product.original_price) * float(order.order_quanity))
            final_price += total_price
            table_rows += f"""
            <tr class="total-row">
                <td>{str(order.order_date)[0:10]}</td>
                <td>{order.order_number}</td>
                <td>{order.product.catalog_number}</td>
                <td>{order.product.description}</td>
                <td>{order.order_quanity}</td>
                <td>{order.product.original_price}</td>
                <td>{str(total_price)}</td>
                <td>{order.discount}</td>
            </tr>
            """

        server = smtplib.SMTP("smtp.outlook.office365.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)

        with open(html_file_path, "r", encoding="utf-8") as file:
            html_template = file.read()

        html_body = (
            html_template
            .replace("{{customer_name}}", customer_name)
            .replace("{{table_rows}}", table_rows)
            .replace("{{total_price}}", str(final_price))
            .replace("{{order_status}}", str(order.status))
        )

        msg = MIMEMultipart("alternative")
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["CC"] = "ai@natrajinfo.in"  # Add the CC recipient here
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        # Combine TO and CC for sending
        recipients = [to_email] + ["ai@natrajinfo.in"]
        server.sendmail(sender_email, recipients, msg.as_string())

        print(f"Email sent to {to_email} and CC'd to ai@natrajinfo.in")
        return render(request, "order_history.html")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return redirect("order_history")
    finally:
        server.quit()
        return redirect("order_history")

def order_history(request):
    user = request.user
    or_hist = Order.objects.filter(user_id = user)

    for i in or_hist:
        print(i)
    return render(request,"order_history.html", {"data":or_hist})


@login_required
def order_history(request):
    # Fetch orders for the logged-in user
    orders = Order.objects.filter(user=request.user).select_related('product')
    return render(request, "order_history.html", {"orders": orders})


def order_list(request):
    orders = Order.objects.all()
    return render(request, 'order_history.html', {'orders': orders})

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

from django.http import JsonResponse

def confirm_order(request, order_id):
    order = Order.objects.get(id=order_id)

    if order.product.in_stock >= order.order_quanity:
        order.status = "Confirm"
        order.save()

        order.product.reduce_stock(order.order_quanity)

        return JsonResponse({"success": True, "new_stock": order.product.in_stock})
    else:
        return JsonResponse({"success": False, "message": "Not enough stock available!"})