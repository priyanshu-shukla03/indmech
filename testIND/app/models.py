from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User, AbstractUser
from django.core.mail import send_mail
from django.utils.html import format_html
from xhtml2pdf import pisa
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from django.core.exceptions import ValidationError
from django.db.models import F


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)  # Ensure email is unique
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    pincode = models.CharField(max_length=6)

    IN_GUJARAT_CHOICES = [
        (True, 'True'),
        (False, 'False'),
    ]

    in_gujarat = models.BooleanField(
        default=True,
        choices=IN_GUJARAT_CHOICES
    )

    USERNAME_FIELD = 'email'  # Use email as the username field
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'pincode']  # Include additional fields for user creation

    def __str__(self):
        # Return full name instead of using non-existent 'name' field
        return f"{self.first_name} {self.last_name} ({self.email})"


# CatalogHeading model
class CatalogHeading(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField()

    def __str__(self):  # Fix for string representation
        return self.name


@admin.register(CatalogHeading)
class CatalogHeadingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


# CatalogSubHeading model
class CatalogSubHeading(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField()
    catalog_heading = models.ForeignKey(CatalogHeading, on_delete=models.CASCADE, related_name='subheadings')

    def __str__(self):  # Fix for string representation
        return self.name


@admin.register(CatalogSubHeading)
class CatalogSubHeadingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'catalog_heading')


# Product model
class Product(models.Model):
    id = models.AutoField(primary_key=True)
    catalog_heading = models.ForeignKey(
        CatalogHeading,
        on_delete=models.CASCADE,
        related_name='products',
        default=1  # Replace with a valid CatalogHeading ID
    )
    catalog_subheading = models.ForeignKey(
        CatalogSubHeading,
        on_delete=models.CASCADE,
        related_name='products'
    )
    catalog_number = models.TextField()
    description = models.TextField()
    in_stock = models.IntegerField()
    original_price = models.FloatField()
    discounted_price = models.FloatField(null=True, blank=True)
    product_type = models.TextField()
    in_stock = models.IntegerField()
    warranty = models.CharField(
        max_length=20,
        choices=[('1 Year', '1 Year'), ('2 Year', '2 Year'), ('3 Year', '3 Year')],
        default='1 Year'
        )

    def reduce_stock(self, quantity):
        """Reduce stock safely"""
        if self.in_stock - quantity < 0:
           raise ValidationError("Not enough stock available.")  # Prevent negative stock
        self.in_stock -= quantity
        self.save(update_fields=['in_stock'])

    def __str__(self):  # Fix for string representation
        return f"Product {self.id} in {self.catalog_heading.name} ({self.catalog_subheading.name})"

 
# Order model
class Order(models.Model):
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    order_number = models.TextField()
    order_date = models.DateTimeField()
    order_quanity = models.PositiveBigIntegerField()
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Confirm', 'Confirm'), ('Delivered', 'Delivered')],
        default='Pending'
    )
    delivery_estimate = models.CharField(
        max_length=20,
        choices=[('1 week', '1 week'), ('2 weeks', '2 weeks'), ('3 weeks', '3 weeks')],
        default='1 week'
    )
    discount = models.FloatField(null=True, blank=True)
    freight = models.FloatField(default=100)
    courier_company = models.TextField(null=True, blank=True)
    docket_number = models.IntegerField(null=True, blank=True)

    @property
    def total_price(self):
        return (self.product.discounted_price or self.product.original_price) * self.order_quanity

    def __str__(self):  # Fix for string representation
        return f"Order {self.order_number} by {self.user.first_name}"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = ('order_number', 'user', 'status', 'total_price_display', 'order_date')

    def save_model(self, request, obj, form, change):
        # Save the current order
        previous_order = Order.objects.filter(id=obj.id).first()

        super().save_model(request, obj, form, change)

        # If status is changed to 'Confirm' or 'Delivered', reduce stock
        if obj.status in ['Confirm', 'Delivered']:
            obj.product.in_stock = F('in_stock') - obj.order_quanity
            obj.product.save(update_fields=['in_stock'])

        super().save_model(request, obj, form, change)

        # Fetch all related orders with the same order_number
        related_orders = Order.objects.filter(order_number=obj.order_number)

        # Replace "OR" with "PI" in the order number for email purposes
        #modified_order_number = obj.order_number.replace("OR", "PI", 1)

        # If the freight field is updated, apply it to all related orders
        if 'freight' in form.changed_data:
            related_orders.update(freight=obj.freight)

        # Ensure all orders have the same status
        unique_statuses = related_orders.values_list('status', flat=True).distinct()

        if len(unique_statuses) == 1:  # All orders have the same status
            sender_email = "ai@natrajinfo.in"
            sender_password = "zfpzwtcthqlldqwy"

            is_in_gujarat = obj.user.in_gujarat
            cgst_rate = 9
            sgst_rate = 9
            igst_rate = 18
            total_freight = 0.0

            try:
                # Initialize grand totals
                grand_taxable_amount = 0.0
                grand_cgst_price = 0.0
                grand_sgst_price = 0.0
                grand_igst_price = 0.0
                grand_discount = 0.0
                grand_final_price = 0.0
                grand_sub_final_price = 0.0

                # Table rows for email
                table_rows = ""

                for order in related_orders:
                    order_quantity = float(order.order_quanity)
                    original_price = float(order.product.original_price)
                    discount = float(order.discount) if order.discount else 0.0
                    total_freight = float(order.freight) if order.freight else 100

                    # Calculate amounts
                    taxable_amount = order_quantity * original_price
                    discounted_price = round(taxable_amount * discount / 100)
                    after_discount_price = round(taxable_amount - discounted_price)

                    if is_in_gujarat:
                        cgst_price = round(after_discount_price * cgst_rate / 100)
                        sgst_price = round(after_discount_price * sgst_rate / 100)
                        igst_price = 0.0
                    else:
                        cgst_price = 0.0
                        sgst_price = 0.0
                        igst_price = round(after_discount_price * igst_rate / 100)

                    final_price = round(after_discount_price + cgst_price + sgst_price + igst_price)

                    # Update grand totals
                    grand_sub_final_price += final_price
                    grand_taxable_amount += taxable_amount
                    grand_cgst_price += cgst_price
                    grand_sgst_price += sgst_price
                    grand_igst_price += igst_price
                    grand_discount += discounted_price
                    grand_final_price += final_price 

                    # Add row to the email table
                    if is_in_gujarat:
                        table_rows += f"""
                        <tr>
                            <td>{order.product.catalog_number}</td>
                            <td>{order.product.description}</td>
                            <td>{order_quantity}</td>
                            <td>{original_price}</td>
                            <td>{taxable_amount}</td>
                            <td>{after_discount_price}  <br>{str(order.discount)} % off</br> </td>
                            <td>{cgst_price}</td>
                            <td>{sgst_price}</td>
                            <td>{final_price}</td>
                        </tr>
                        """
                    else:
                        table_rows += f"""
                        <tr>
                            <td>{order.product.catalog_number}</td>
                            <td>{order.product.description}</td>
                            <td>{order_quantity}</td>
                            <td>{original_price}</td>
                            <td>{taxable_amount}</td>
                            <td>{after_discount_price} <br>{str(order.discount)} % off</br> </td>
                            <td>{igst_price}</td>
                            <td>{final_price}</td>
                        </tr>
                        """

                # Generate the HTML for the email body
                if is_in_gujarat:
                    template_path = "app/templates/order_in_gujarat.html"
                else:
                    template_path = "app/templates/order_out_gujarat.html"
                with open(template_path, "r", encoding="utf-8") as file:
                    html_template = file.read()

                html_body = (
                    html_template
                    .replace("{{customer_name}}", obj.user.first_name)
                    .replace("{{table_rows}}", table_rows)
                    .replace("{{status}}", obj.status)
                    .replace("{{final_price}}", str(round(grand_final_price + total_freight, 2)))
                    .replace("{{amount_saved}}", str(round(grand_discount, 2)))
                    .replace("{{order_number}}", str(obj.order_number))
                    #.replace("{{modified_order_number}}", str(modified_order_number))
                    .replace("{{order_date}}", str(obj.order_date)[0:10])
                    .replace("{{delivery_estimate}}", str(obj.delivery_estimate))
                    .replace("{{courier_company}}", str(obj.courier_company))
                    .replace("{{docket_number}}", str(obj.docket_number) if obj.docket_number else "")
                    .replace("{{freight}}", str(obj.freight))
                    .replace("{{sub_total}}", str(grand_sub_final_price))
                )

                # Generate PDF using xhtml2pdf
                pdf_path = f"invoices/{obj.order_number}.pdf"
                os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

                with open(pdf_path, "wb") as pdf_file:
                    pisa_status = pisa.CreatePDF(html_body, dest=pdf_file)

                # Check if there were any issues with PDF generation
                if pisa_status.err:
                    self.message_user(request, "Error in generating the PDF", level="error")
                    return

                # Email setup
                server = smtplib.SMTP("smtp.outlook.office365.com", 587)
                server.starttls()
                server.login(sender_email, sender_password)

                msg = MIMEMultipart("mixed")  # Use 'mixed' to send both text/html and attachments
                msg["From"] = sender_email
                msg["To"] = obj.user.email
                msg["Subject"] = f"Order Status Update: {obj.order_number}"

                # Add HTML content to the email body
                html_part = MIMEText(html_body, "html")
                msg.attach(html_part)

                # Attach the PDF
                with open(pdf_path, "rb") as pdf_file:
                    attach = MIMEBase("application", "octet-stream")
                    attach.set_payload(pdf_file.read())
                    encoders.encode_base64(attach)
                    attach.add_header("Content-Disposition", f"attachment; filename={os.path.basename(pdf_path)}")
                    msg.attach(attach)

                server.send_message(msg)
                self.message_user(request, f"Email sent to {obj.user.email} with PDF attachment.")

            except Exception as e:
                self.message_user(request, f"Failed to send email: {e}", level="error")

            finally:
                server.quit()

    def total_price_display(self, obj):
        return format_html("<b>{}</b>", obj.total_price)

    total_price_display.short_description = "Total Price"


    def total_price_display(self, obj):
        return format_html("<b>{}</b>", obj.total_price)

    total_price_display.short_description = "Total Price"

    
class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    user_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    @property
    def total_price(self):
        # Calculate the total price based on product's price and quantity
        return (self.product.discounted_price or self.product.original_price) * self.quantity

    def __str__(self):
        return f"{self.product.catalog_number} - {self.quantity} pcs"

from django.db import models
class OrderSerial(models.Model):
    date = models.DateField(unique=True)  # Store the date
    last_serial = models.PositiveIntegerField(default=0)  # Store the last serial number for the date

    def _str_(self):
        return f"{self.date} - {self.last_serial}"

class StockProduct(Product):
    class Meta:
        proxy = True
        verbose_name = "Stock Product"
        verbose_name_plural = "Stock Products"

