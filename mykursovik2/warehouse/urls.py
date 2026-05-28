from django.urls import path
from . import views

urlpatterns = [
    # AJAX API
    path('api/employees/', views.api_employees, name='api_employees'),
    path('api/wos/<int:wos_pk>/assign/', views.api_assign_employee, name='api_assign_employee'),
    path('api/wos/<int:wos_pk>/unassign/<int:emp_pk>/', views.api_unassign_employee, name='api_unassign_employee'),
    path('api/parts/', views.api_parts, name='api_parts'),
    path('api/part-price/', views.api_part_price, name='api_part_price'),
    path('api/suppliers/', views.api_suppliers, name='api_suppliers'),
    path('api/po-items/', views.api_po_items, name='api_po_items'),
    path('api/brands/', views.api_brands, name='api_brands'),
    path('api/work-orders/', views.api_work_orders, name='api_work_orders'),
    path('api/services/', views.api_services, name='api_services'),
    path('api/part-stock/', views.api_part_stock, name='api_part_stock'),
    path('api/part-locations/', views.api_part_locations, name='api_part_locations'),

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

    # Purchase prices
    path('purchase-prices/', views.purchase_prices_list, name='purchase_prices_list'),
    path('purchase-prices/<int:part_pk>/', views.purchase_prices_detail, name='purchase_prices_detail'),

    # Supply Documents
    path('supply/', views.supply_list, name='supply_list'),
    path('supply/create/', views.supply_create, name='supply_create'),
    path('supply/<int:pk>/', views.supply_detail, name='supply_detail'),

    # Purchase Orders
    path('purchase/', views.purchase_list, name='purchase_list'),
    path('purchase/create/', views.purchase_create, name='purchase_create'),
    path('purchase/<int:pk>/', views.purchase_detail, name='purchase_detail'),
    path('purchase/<int:pk>/update/', views.purchase_update, name='purchase_update'),
    path('purchase/<int:pk>/edit/', views.purchase_edit, name='purchase_edit'),
    path('purchase/<int:pk>/delete/', views.purchase_delete, name='purchase_delete'),

    # Work Order Parts
    path('orders/<int:order_pk>/parts/add/', views.workorderpart_create, name='workorderpart_create'),
    path('workorderpart/<int:pk>/update/', views.workorderpart_update, name='workorderpart_update'),
    path('workorderpart/<int:pk>/delete/', views.workorderpart_delete, name='workorderpart_delete'),

    # Work Order Services
    path('orders/<int:order_pk>/services/add-bulk/', views.workorderservice_create_bulk, name='workorderservice_create_bulk'),
    path('orders/<int:order_pk>/services/add/', views.workorderservice_create, name='workorderservice_create'),
    path('workorderservice/<int:pk>/update/', views.workorderservice_update, name='workorderservice_update'),
    path('workorderservice/<int:pk>/delete/', views.workorderservice_delete, name='workorderservice_delete'),

    # Picking list
    path('orders/<int:order_pk>/picking/', views.picking_list, name='picking_list'),

    # Write-Off (Списание)
    path('write-off/', views.write_off_list, name='write_off_list'),
    path('write-off/create/', views.write_off_create, name='write_off_create'),
    path('write-off/<int:pk>/', views.write_off_detail, name='write_off_detail'),

    # Settings
    path('settings/', views.settings_view, name='warehouse_settings'),

    # Employees
    path('employees/', views.employees_list, name='employees_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/report/', views.employees_report_all, name='employees_report_all'),
    path('employees/<int:pk>/update/', views.employee_update, name='employee_update'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('employees/<int:pk>/report/', views.employee_report, name='employee_report'),
]
