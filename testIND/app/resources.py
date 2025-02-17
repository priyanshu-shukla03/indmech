# app/resources.py
from import_export.resources import ModelResource
from .models import Product

class ProductResource(ModelResource):
    class Meta:
        model = Product
        import_id_fields = ['catalog_number']  # Ensure catalog_number is unique
        fields = ('catalog_number', 'description', 'catalog_heading', 'catalog_subheading', 'in_stock')