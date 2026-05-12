from django.urls import path
from . import views

urlpatterns = [
    # AJAX API
    path('api/parts/', views.api_parts, name='api_parts'),
    path('api/suppliers/', views.api_suppliers, name='api_suppliers'),
    path('api/po-items/', views.api_po_items, name='api_po_items'),
    path('api/brands/', views.api_brands, name='api_brands'),
    path('api/work-orders/', views.api_work_orders, name='api_work_orders'),

    # Brands
    path('brands/', views.brands_list, name='brands_list'),
    path('brands/create/', views.brand_create, name='brand_create'),
    path('brands/<int:pk>/update/', views.brand_update, name='brand_update'),
    path('brands/<int:pk>/delete/', views.brand_delete, name='brand_delete'),

    # Suppliers
    path('suppliers/', views.suppliers_list, name='suppliers_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/update/', views.supplier_update, name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),

    # Parts
    path('parts/', views.parts_list, name='parts_list'),
    path('parts/create/', views.part_create, name='part_create'),
    path('parts/<int:pk>/', views.part_detail, name='part_detail'),
    path('parts/<int:pk>/update/', views.part_update, name='part_update'),
    path('parts/<int:pk>/delete/', views.part_delete, name='part_delete'),

    # Storage Locations
    path('locations/', views.locations_list, name='locations_list'),
    path('locations/create/', views.location_create, name='location_create'),
    path('locations/<int:pk>/', views.location_detail, name='location_detail'),
    path('locations/<int:pk>/update/', views.location_update, name='location_update'),
    path('locations/<int:pk>/delete/', views.location_delete, name='location_delete'),

    # Stock
    path('stock/', views.stock_list, name='stock_list'),
    path('stock/<int:pk>/min/', views.stock_update_min, name='stock_update_min'),

    # Supply Documents
    path('supply/', views.supply_list, name='supply_list'),
    path('supply/create/', views.supply_create, name='supply_create'),
    path('supply/<int:pk>/', views.supply_detail, name='supply_detail'),

    # Purchase Orders
    path('purchase/', views.purchase_list, name='purchase_list'),
    path('purchase/create/', views.purchase_create, name='purchase_create'),
    path('purchase/<int:pk>/', views.purchase_detail, name='purchase_detail'),
    path('purchase/<int:pk>/update/', views.purchase_update, name='purchase_update'),

    # Work Order Parts
    path('orders/<int:order_pk>/parts/add/', views.workorderpart_create, name='workorderpart_create'),
    path('workorderpart/<int:pk>/update/', views.workorderpart_update, name='workorderpart_update'),
    path('workorderpart/<int:pk>/delete/', views.workorderpart_delete, name='workorderpart_delete'),

    # Work Order Services
    path('orders/<int:order_pk>/services/add/', views.workorderservice_create, name='workorderservice_create'),
    path('workorderservice/<int:pk>/update/', views.workorderservice_update, name='workorderservice_update'),
    path('workorderservice/<int:pk>/delete/', views.workorderservice_delete, name='workorderservice_delete'),

    # Picking list
    path('orders/<int:order_pk>/picking/', views.picking_list, name='picking_list'),

    # Settings
    path('settings/', views.settings_view, name='warehouse_settings'),
]
