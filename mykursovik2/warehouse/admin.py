from django.contrib import admin
from .models import (
    Part, StorageLocation, StockEntry,
    SupplyDocument, SupplyItem, PurchaseOrder,
    WorkOrderPart, WorkOrderService, WorkshopSettings
)

admin.site.register(Part)
admin.site.register(StorageLocation)
admin.site.register(StockEntry)
admin.site.register(SupplyDocument)
admin.site.register(SupplyItem)
admin.site.register(PurchaseOrder)
admin.site.register(WorkOrderPart)
admin.site.register(WorkOrderService)
admin.site.register(WorkshopSettings)
