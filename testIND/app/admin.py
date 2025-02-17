from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import F
from django.core.exceptions import ValidationError
from django import forms
from .models import CustomUser, StockProduct


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('phone_number', 'address', 'date_of_birth', 'pincode', 'in_gujarat')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('phone_number', 'address', 'date_of_birth', 'email', 'first_name', 'last_name', 'pincode', 'in_gujarat')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'date_of_birth', 'is_staff', 'pincode', 'in_gujarat')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'pincode', 'in_gujarat')


class StockProductAdminForm(forms.ModelForm):
    add_in_stock = forms.IntegerField(required=True, min_value=1, label="Add Stock")

    class Meta:
        model = StockProduct
        fields = []  # No editable fields except add_in_stock

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        self.fields['add_in_stock'].widget.attrs.update({'placeholder': 'Enter quantity to add'})


@admin.register(StockProduct)
class StockProductAdmin(admin.ModelAdmin):
    form = StockProductAdminForm
    list_display = ('id', 'catalog_number', 'product_type', 'description', 'catalog_heading', 'catalog_subheading', 'in_stock')
    ordering = ('id',)
    readonly_fields = ('in_stock',)  # Make in_stock non-editable
    fields = ('in_stock', 'add_in_stock')  # Show in_stock but only allow adding stock

    search_fields = ('catalog_number', 'description', 'product_type',)
    list_filter = ('catalog_heading', 'catalog_subheading')

    def save_model(self, request, obj, form, change):
        """Allow stock managers to add stock but not modify any other field."""
        if change and form.cleaned_data.get('add_in_stock'):
            try:
                # Fetch existing stock product
                product = StockProduct.objects.get(id=obj.id)

                # Update in_stock by adding add_in_stock
                product.in_stock = product.in_stock + form.cleaned_data['add_in_stock']

                # Save only the in_stock field
                product.save(update_fields=['in_stock'])

                # Ensure admin displays updated in_stock value
                obj.in_stock = product.in_stock

            except StockProduct.DoesNotExist:
                raise ValidationError("StockProduct does not exist.")
        else:
            raise ValidationError("Stock managers can only add stock.")


from django.contrib import admin
from import_export.admin import ExportMixin, ImportExportModelAdmin
from import_export import resources
from .models import Product  # Ensure correct import
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Product
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from django.core.exceptions import ValidationError
from .models import Product, CatalogHeading, CatalogSubHeading


class ProductResource(resources.ModelResource):
    # Ensure correct values are exported instead of IDs
    catalog_heading = fields.Field(
        column_name='catalog_heading',
        attribute='catalog_heading',
        widget=ForeignKeyWidget(CatalogHeading, 'name')  # Ensure correct lookup
    )

    catalog_subheading = fields.Field(
        column_name='catalog_subheading',
        attribute='catalog_subheading',
        widget=ForeignKeyWidget(CatalogSubHeading, 'name')  # Ensure correct lookup
    )

    class Meta:
        model = Product
        fields = ('id','catalog_number', 'product_type', 'description', 'catalog_heading', 'catalog_subheading', 'warranty', 'in_stock', 'original_price', 'discounted_price')
        export_order = ('id','catalog_number', 'product_type', 'description', 'catalog_heading', 'catalog_subheading', 'warranty', 'in_stock', 'original_price', 'discounted_price')

    def dehydrate_catalog_heading(self, product):
        """Export actual value of catalog_heading instead of ID"""
        return product.catalog_heading.name if product.catalog_heading else ""

    def dehydrate_catalog_subheading(self, product):
        """Export actual value of catalog_subheading instead of ID"""
        return product.catalog_subheading.name if product.catalog_subheading else ""

    def before_import_row(self, row, **kwargs):
        """Convert catalog_heading and catalog_subheading to their respective instances"""
        if int(row.get("in_stock", 0)) < 0:
            raise ValidationError("Stock cannot be negative.")

        # Get or create catalog heading
        row["catalog_heading"], _ = CatalogHeading.objects.get_or_create(name=row["catalog_heading"])

        # Get or create catalog subheading
        row["catalog_subheading"], _ = CatalogSubHeading.objects.get_or_create(name=row["catalog_subheading"])

# Extend ImportExportModelAdmin
from import_export.admin import ImportExportModelAdmin
from import_export.formats.base_formats import XLS, XLSX
from .models import Product

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ('id','catalog_number', 'product_type', 'description', 'catalog_heading', 'catalog_subheading', 'warranty', 'in_stock', 'original_price', 'discounted_price')
    search_fields = ('catalog_number', 'description')
    list_filter = ('catalog_heading', 'catalog_subheading')
    ordering = ('id',)

    # Enable import/export for Excel
    def get_export_formats(self):
        return [XLS, XLSX]

    def get_import_formats(self):
        return [XLS, XLSX]