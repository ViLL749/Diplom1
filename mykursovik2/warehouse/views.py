from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect

from .forms import (
    BrandForm, SupplierForm, PartForm, StorageLocationForm, StockEntryMinQtyForm,
    SupplyDocumentForm, SupplyItemFormSet,
    PurchaseOrderForm, PurchaseOrderItemFormSet, PurchaseOrderStatusForm,
    WorkOrderPartForm, WorkOrderPartStatusForm,
    WorkOrderServiceForm, WorkshopSettingsForm,
)
from .models import (
    Brand, Supplier, Part, StorageLocation, StockEntry,
    SupplyDocument, SupplyItem,
    PurchaseOrder, PurchaseOrderItem,
    WorkOrderPart, WorkOrderService, WorkshopSettings,
)


# ──────────────────────────────────────────────────────────────
# AJAX API
# ──────────────────────────────────────────────────────────────

@login_required
def api_parts(request):
    search = request.GET.get('search', '')
    po_id  = request.GET.get('po_id', '')
    page   = int(request.GET.get('page', 1))
    parts  = Part.objects.all()

    if po_id:
        # Restrict to parts that still have remaining items in this PO
        remaining_part_ids = [
            poi.part_id
            for poi in PurchaseOrderItem.objects.filter(purchase_order_id=po_id)
            if poi.remaining_qty > 0
        ]
        parts = parts.filter(id__in=remaining_part_ids)

    if search:
        parts = parts.filter(
            Q(article__icontains=search) | Q(name__icontains=search) | Q(brand__icontains=search)
        )
    parts = parts.order_by('article')
    paginator = Paginator(parts, 10)
    page_obj = paginator.get_page(page)
    return JsonResponse({
        'parts': [
            {'id': p.id, 'article': p.article, 'name': p.name,
             'brand': p.brand, 'package_qty': p.package_qty}
            for p in page_obj
        ],
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })


@login_required
def api_suppliers(request):
    search = request.GET.get('search', '')
    suppliers = Supplier.objects.all()
    if search:
        suppliers = suppliers.filter(Q(name__icontains=search) | Q(contact__icontains=search))
    return JsonResponse({
        'suppliers': [
            {'id': s.id, 'name': s.name, 'phone': s.phone, 'contact': s.contact}
            for s in suppliers[:30]
        ]
    })


@login_required
def api_po_items(request):
    """Return remaining (not fully received) items for a PurchaseOrder."""
    po_id = request.GET.get('po_id')
    if not po_id:
        return JsonResponse({'items': []})
    items = PurchaseOrderItem.objects.filter(
        purchase_order_id=po_id
    ).select_related('part')
    result = []
    for item in items:
        if item.remaining_qty > 0:
            result.append({
                'id': item.id,
                'article': item.part.article,
                'name': item.part.name,
                'part_id': item.part.id,
                'quantity': item.quantity,
                'received_qty': item.received_qty,
                'remaining_qty': item.remaining_qty,
                'package_qty': item.part.package_qty,
            })
    return JsonResponse({'items': result})


@login_required
def api_brands(request):
    search = request.GET.get('search', '')
    brands = Brand.objects.all()
    if search:
        brands = brands.filter(name__icontains=search)
    return JsonResponse({
        'brands': [{'id': b.id, 'name': b.name} for b in brands[:50]]
    })


@login_required
def api_work_orders(request):
    from mainapp.models import Order
    search = request.GET.get('search', '')
    orders = Order.objects.exclude(status='Завершён').order_by('-id')
    if search:
        orders = orders.filter(
            Q(id__icontains=search) |
            Q(client__fio__icontains=search) |
            Q(car_details_static__icontains=search)
        )
    return JsonResponse({
        'orders': [
            {
                'id': o.id,
                'client': o.client_fio_static or '—',
                'car': o.car_details_static or '—',
                'status': o.status,
            }
            for o in orders[:30]
        ]
    })


# ──────────────────────────────────────────────────────────────
# Brands
# ──────────────────────────────────────────────────────────────

@login_required
def brands_list(request):
    brands = Brand.objects.all()
    search = request.GET.get('search', '')
    if search:
        brands = brands.filter(name__icontains=search)
    per_page = _get_per_page(request)
    paginator = Paginator(brands, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'warehouse/brands/list.html', {
        'page_obj': page_obj, 'per_page': per_page
    })


@login_required
def brand_create(request):
    if request.method == 'POST':
        form = BrandForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Производитель добавлен.')
            return redirect('brands_list')
    else:
        form = BrandForm()
    return render(request, 'warehouse/brands/create.html', {'form': form})


@login_required
def brand_update(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, 'Производитель обновлён.')
            return redirect('brands_list')
    else:
        form = BrandForm(instance=brand)
    return render(request, 'warehouse/brands/update.html', {'form': form, 'brand': brand})


@login_required
def brand_delete(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        brand.delete()
        messages.success(request, 'Производитель удалён.')
        return redirect('brands_list')
    return render(request, 'warehouse/brands/delete.html', {'brand': brand})


# ──────────────────────────────────────────────────────────────
# Suppliers
# ──────────────────────────────────────────────────────────────

@login_required
def suppliers_list(request):
    suppliers = Supplier.objects.all()
    search = request.GET.get('search', '')
    if search:
        suppliers = suppliers.filter(
            Q(name__icontains=search) | Q(contact__icontains=search)
        )
    per_page = _get_per_page(request)
    paginator = Paginator(suppliers, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'warehouse/suppliers/list.html', {
        'page_obj': page_obj, 'per_page': per_page
    })


@login_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Поставщик добавлен.')
            return redirect('suppliers_list')
    else:
        form = SupplierForm()
    return render(request, 'warehouse/suppliers/create.html', {'form': form})


@login_required
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Поставщик обновлён.')
            return redirect('suppliers_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'warehouse/suppliers/update.html', {'form': form, 'supplier': supplier})


@login_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        supplier.delete()
        messages.success(request, 'Поставщик удалён.')
        return redirect('suppliers_list')
    return render(request, 'warehouse/suppliers/delete.html', {'supplier': supplier})


# ──────────────────────────────────────────────────────────────
# Parts
# ──────────────────────────────────────────────────────────────

@login_required
def parts_list(request):
    parts = Part.objects.all()
    search = request.GET.get('search', '')
    column = request.GET.get('column', 'article')
    if search:
        mapping = {
            'article': 'article__icontains',
            'name': 'name__icontains',
            'brand': 'brand__icontains',
            'category': 'category__icontains',
        }
        parts = parts.filter(**{mapping.get(column, 'article__icontains'): search})

    sort = request.GET.get('sort', 'article')
    direction = request.GET.get('direction', 'asc')
    if sort not in ['article', 'name', 'brand', 'category']:
        sort = 'article'
    parts = parts.order_by(f'-{sort}' if direction == 'desc' else sort)

    per_page = _get_per_page(request)
    paginator = Paginator(parts, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'warehouse/parts/list.html', {'page_obj': page_obj, 'per_page': per_page})


def _save_part_form(form):
    """Save part form; auto-create Brand entry when brand name is new."""
    part = form.save(commit=False)
    if part.brand:
        Brand.objects.get_or_create(name=part.brand)
    part.save()
    return part


@login_required
def part_create(request):
    if request.method == 'POST':
        form = PartForm(request.POST)
        if form.is_valid():
            _save_part_form(form)
            messages.success(request, 'Деталь добавлена.')
            return redirect('parts_list')
    else:
        form = PartForm()
    return render(request, 'warehouse/parts/create.html', {'form': form})


@login_required
def part_detail(request, pk):
    part = get_object_or_404(Part, pk=pk)
    stock_entries = part.stock_entries.select_related('location').all()
    return render(request, 'warehouse/parts/detail.html', {'part': part, 'stock_entries': stock_entries})


@login_required
def part_update(request, pk):
    part = get_object_or_404(Part, pk=pk)
    if request.method == 'POST':
        form = PartForm(request.POST, instance=part)
        if form.is_valid():
            _save_part_form(form)
            messages.success(request, 'Деталь обновлена.')
            return redirect('part_detail', pk=pk)
    else:
        form = PartForm(instance=part)
    return render(request, 'warehouse/parts/update.html', {'form': form, 'part': part})


@login_required
def part_delete(request, pk):
    part = get_object_or_404(Part, pk=pk)
    if request.method == 'POST':
        part.delete()
        messages.success(request, 'Деталь удалена.')
        return redirect('parts_list')
    return render(request, 'warehouse/parts/delete.html', {'part': part})


# ──────────────────────────────────────────────────────────────
# Storage Locations
# ──────────────────────────────────────────────────────────────

@login_required
def locations_list(request):
    import json as _json
    locations = StorageLocation.objects.all()
    search = request.GET.get('search', '')
    if search:
        locations = locations.filter(label__icontains=search)
    sort = request.GET.get('sort', 'rack')
    direction = request.GET.get('direction', 'asc')
    if sort not in ['rack', 'shelf', 'cell', 'label']:
        sort = 'rack'
    locations = locations.order_by(f'-{sort}' if direction == 'desc' else sort)
    per_page = _get_per_page(request)
    paginator = Paginator(locations, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    # Build map data — all locations (not paginated), grouped rack→shelf→cells
    all_locs = StorageLocation.objects.prefetch_related(
        'stock_entries__part'
    ).order_by('rack', 'shelf', 'cell')
    map_racks = {}  # rack → {shelf → [cell_info]}
    for loc in all_locs:
        entries = list(loc.stock_entries.all())
        total = sum(e.total_qty for e in entries)
        reserved = sum(e.reserved_qty for e in entries)
        low = any(e.total_qty > 0 and e.total_qty <= e.min_qty for e in entries)
        parts = [
            {'article': e.part.article, 'name': e.part.name,
             'qty': e.total_qty, 'reserved': e.reserved_qty,
             'pkg': e.part.package_qty}
            for e in entries
        ]
        cell_info = {
            'id': loc.id, 'cell': loc.cell, 'label': loc.label,
            'total': total, 'reserved': reserved, 'low': low,
            'empty': total == 0, 'parts': parts,
        }
        map_racks.setdefault(loc.rack, {}).setdefault(loc.shelf, []).append(cell_info)

    return render(request, 'warehouse/locations/list.html', {
        'page_obj': page_obj,
        'per_page': per_page,
        'map_data_json': _json.dumps(map_racks, ensure_ascii=False),
    })


@login_required
def location_create(request):
    if request.method == 'POST':
        form = StorageLocationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Место хранения добавлено.')
            return redirect('locations_list')
    else:
        form = StorageLocationForm()
    return render(request, 'warehouse/locations/create.html', {'form': form})


@login_required
def location_detail(request, pk):
    location = get_object_or_404(StorageLocation, pk=pk)
    stock_entries = location.stock_entries.select_related('part').all()
    return render(request, 'warehouse/locations/detail.html', {'location': location, 'stock_entries': stock_entries})


@login_required
def location_update(request, pk):
    location = get_object_or_404(StorageLocation, pk=pk)
    if request.method == 'POST':
        form = StorageLocationForm(request.POST, instance=location)
        if form.is_valid():
            form.save()
            messages.success(request, 'Место хранения обновлено.')
            return redirect('location_detail', pk=pk)
    else:
        form = StorageLocationForm(instance=location)
    return render(request, 'warehouse/locations/update.html', {'form': form, 'location': location})


@login_required
def location_delete(request, pk):
    location = get_object_or_404(StorageLocation, pk=pk)
    if request.method == 'POST':
        location.delete()
        messages.success(request, 'Место хранения удалено.')
        return redirect('locations_list')
    return render(request, 'warehouse/locations/delete.html', {'location': location})


# ──────────────────────────────────────────────────────────────
# Stock
# ──────────────────────────────────────────────────────────────

@login_required
def stock_list(request):
    entries = StockEntry.objects.select_related('part', 'location').all()
    search = request.GET.get('search', '')
    column = request.GET.get('column', 'article')
    if search:
        if column == 'article':
            entries = entries.filter(part__article__icontains=search)
        elif column == 'name':
            entries = entries.filter(part__name__icontains=search)
        elif column == 'location':
            entries = entries.filter(location__label__icontains=search)

    sort = request.GET.get('sort', 'part__article')
    direction = request.GET.get('direction', 'asc')
    if sort not in ['part__article', 'part__name', 'location__label', 'total_qty', 'reserved_qty']:
        sort = 'part__article'
    entries = entries.order_by(f'-{sort}' if direction == 'desc' else sort)

    per_page = _get_per_page(request)
    paginator = Paginator(entries, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'warehouse/stock/list.html', {'page_obj': page_obj, 'per_page': per_page})


@login_required
def stock_update_min(request, pk):
    entry = get_object_or_404(StockEntry, pk=pk)
    if request.method == 'POST':
        form = StockEntryMinQtyForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, 'Минимальный остаток обновлён.')
            return redirect('stock_list')
    else:
        form = StockEntryMinQtyForm(instance=entry)
    return render(request, 'warehouse/stock/update_min.html', {'form': form, 'entry': entry})


# ──────────────────────────────────────────────────────────────
# Supply Documents
# ──────────────────────────────────────────────────────────────

@login_required
def supply_list(request):
    docs = SupplyDocument.objects.select_related('supplier', 'purchase_order').all()
    search = request.GET.get('search', '')
    if search:
        docs = docs.filter(supplier__name__icontains=search)
    per_page = _get_per_page(request)
    paginator = Paginator(docs, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'warehouse/supply/list.html', {'page_obj': page_obj, 'per_page': per_page})


@login_required
@transaction.atomic
def supply_create(request):
    # Pre-select PO if passed in GET
    po_id = request.GET.get('po')
    initial_po = None
    po_items = []
    if po_id:
        initial_po = PurchaseOrder.objects.filter(pk=po_id).first()
        if initial_po:
            po_items = list(
                PurchaseOrderItem.objects.filter(purchase_order=initial_po)
                .select_related('part')
                .filter(received_qty__lt=models_remaining_filter())
            )
            # filter items that still have remaining qty
            po_items = [i for i in PurchaseOrderItem.objects.filter(
                purchase_order=initial_po
            ).select_related('part') if i.remaining_qty > 0]

    if request.method == 'POST':
        doc_form = SupplyDocumentForm(request.POST)
        formset = SupplyItemFormSet(request.POST)
        if doc_form.is_valid() and formset.is_valid():
            # Iterate forms manually to read the non-model package_qty field.
            # Quantities stay in "packages" (what the user entered) until AFTER
            # the overrun check — the PO was also created in the same unit.
            valid_items = []
            for form in formset:
                cd = form.cleaned_data
                if not cd or cd.get('DELETE'):
                    continue
                # Skip completely empty rows (no field filled)
                if not any([cd.get('part'), cd.get('location'),
                            cd.get('quantity'), cd.get('purchase_price')]):
                    continue
                # Rows that have errors (missing fields) are caught by formset.is_valid()
                item = form.save(commit=False)
                item._pkg_qty = max(1, int(cd.get('package_qty') or 1))
                valid_items.append(item)

            if not valid_items:
                messages.error(request, 'Укажите место хранения хотя бы для одной позиции.')
            else:
                # Auto-link manually added rows to PO items when the supply is tied to a PO.
                # If the user picks a part that exists in the linked PO, bind it automatically
                # so received_qty is updated and overrun checks apply.
                linked_po = doc_form.cleaned_data.get('purchase_order')
                if linked_po:
                    poi_by_part = {
                        poi.part_id: poi
                        for poi in PurchaseOrderItem.objects.filter(purchase_order=linked_po)
                    }
                    for item in valid_items:
                        if not item.po_item_id and item.part_id in poi_by_part:
                            item.po_item = poi_by_part[item.part_id]

                # Server-side guard: total received per PO item must not exceed remaining_qty
                overrun_errors = _check_po_overrun(valid_items)
                for err in overrun_errors:
                    messages.error(request, err)

                if not overrun_errors:
                    # Multiply package count → unit count before writing to stock.
                    # Overrun check already passed using package-level quantities.
                    for item in valid_items:
                        pkg = getattr(item, '_pkg_qty', 1)
                        if item.quantity and pkg > 1:
                            item.quantity *= pkg

                    doc = doc_form.save()

                    # {po_item_id: total qty received in this document}
                    po_item_received: dict[int, int] = {}

                    for item in valid_items:
                        item.document = doc
                        item.save()

                        # Update or create stock entry
                        entry, _ = StockEntry.objects.get_or_create(
                            part=item.part,
                            location=item.location,
                            defaults={'total_qty': 0, 'reserved_qty': 0, 'min_qty': 1},
                        )
                        entry.total_qty += item.quantity
                        entry.save()

                        if item.po_item_id:
                            pkg = getattr(item, '_pkg_qty', 1)
                            pkg_count = item.quantity // pkg if pkg > 1 else item.quantity
                            po_item_received[item.po_item_id] = (
                                po_item_received.get(item.po_item_id, 0) + pkg_count
                            )

                    # Atomic increment — handles multiple rows referencing the same PO item
                    for po_item_id, qty in po_item_received.items():
                        PurchaseOrderItem.objects.filter(pk=po_item_id).update(
                            received_qty=F('received_qty') + qty
                        )

                    # Update PO status (re-fetch to get updated received_qty)
                    po = doc.purchase_order
                    if po:
                        all_po_items = list(po.items.all())
                        if all(i.remaining_qty == 0 for i in all_po_items):
                            po.status = 'received'
                        elif any(i.received_qty > 0 for i in all_po_items):
                            po.status = 'partial'
                        po.save()

                        # Auto-reserve parts for linked work order when fully received
                        if po.status == 'received' and po.work_order:
                            for po_item in all_po_items:
                                for entry in StockEntry.objects.filter(part=po_item.part):
                                    if entry.available_qty >= po_item.quantity:
                                        entry.reserved_qty += po_item.quantity
                                        entry.save()
                                        if not WorkOrderPart.objects.filter(
                                            work_order=po.work_order, part=po_item.part
                                        ).exists():
                                            WorkOrderPart.objects.create(
                                                work_order=po.work_order,
                                                part=po_item.part,
                                                quantity=po_item.quantity,
                                                status='reserved',
                                            )
                                        break

                    messages.success(request, f'Приход №{doc.id} создан.')
                    return redirect('supply_detail', pk=doc.pk)
    else:
        initial = {}
        if initial_po:
            initial['purchase_order'] = initial_po
            if initial_po.supplier:
                initial['supplier'] = initial_po.supplier
        doc_form = SupplyDocumentForm(initial=initial)
        formset = SupplyItemFormSet()

    return render(request, 'warehouse/supply/create.html', {
        'doc_form': doc_form,
        'formset': formset,
        'initial_po': initial_po,
        'po_items': po_items,
        # On POST re-render we must NOT re-run the AJAX prefill — it would wipe
        # the quantities the user already typed in.
        'prefill_fresh': request.method == 'GET',
    })


@login_required
def supply_detail(request, pk):
    doc = get_object_or_404(SupplyDocument, pk=pk)
    items = doc.items.select_related('part', 'location', 'po_item').all()
    return render(request, 'warehouse/supply/detail.html', {'doc': doc, 'items': items})


# ──────────────────────────────────────────────────────────────
# Purchase Orders
# ──────────────────────────────────────────────────────────────

@login_required
def purchase_list(request):
    orders = PurchaseOrder.objects.select_related('supplier', 'work_order').all()
    search = request.GET.get('search', '')
    if search:
        orders = orders.filter(
            Q(supplier__name__icontains=search) |
            Q(items__part__article__icontains=search) |
            Q(items__part__name__icontains=search)
        ).distinct()

    sort = request.GET.get('sort', 'created_at')
    direction = request.GET.get('direction', 'desc')
    if sort not in ['created_at', 'status', 'supplier__name']:
        sort = 'created_at'
    orders = orders.order_by(f'-{sort}' if direction == 'desc' else sort)

    per_page = _get_per_page(request)
    paginator = Paginator(orders, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'warehouse/purchase/list.html', {'page_obj': page_obj, 'per_page': per_page})


@login_required
@transaction.atomic
def purchase_create(request):
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            po = form.save()
            items = formset.save(commit=False)
            for item in items:
                item.purchase_order = po
                item.save()
            messages.success(request, f'Заказ поставщику №{po.id} создан.')
            return redirect('purchase_detail', pk=po.pk)
    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet()
    return render(request, 'warehouse/purchase/create.html', {'form': form, 'formset': formset})


@login_required
def purchase_detail(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    items = po.items.select_related('part').all()
    supply_docs = po.supply_documents.all()
    return render(request, 'warehouse/purchase/detail.html', {
        'po': po, 'items': items, 'supply_docs': supply_docs
    })


@login_required
def purchase_update(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if po.status == 'received':
        messages.error(request, 'Нельзя изменить статус полностью полученного заказа.')
        return redirect('purchase_detail', pk=pk)
    if request.method == 'POST':
        form = PurchaseOrderStatusForm(request.POST, instance=po)
        if form.is_valid():
            new_status = form.cleaned_data['status']
            if new_status == 'received':
                messages.error(request, 'Статус «Получено» проставляется автоматически при оформлении прихода товара.')
                return redirect('purchase_detail', pk=pk)
            form.save()
            messages.success(request, 'Статус обновлён.')
            return redirect('purchase_detail', pk=pk)
    else:
        form = PurchaseOrderStatusForm(instance=po)
    return render(request, 'warehouse/purchase/update.html', {'form': form, 'po': po})


# ──────────────────────────────────────────────────────────────
# Work Order Parts
# ──────────────────────────────────────────────────────────────

@login_required
def workorderpart_create(request, order_pk):
    from mainapp.models import Order
    order = get_object_or_404(Order, pk=order_pk)
    if request.method == 'POST':
        form = WorkOrderPartForm(request.POST)
        if form.is_valid():
            wop = form.save(commit=False)
            wop.work_order = order
            last_item = SupplyItem.objects.filter(part=wop.part).order_by('-document__created_at').first()
            if last_item:
                markup = wop.markup / Decimal('100')
                wop.sale_price = last_item.purchase_price * (1 + markup)
            wop.save()
            # Reserve from stock
            remaining = wop.quantity
            for entry in StockEntry.objects.filter(part=wop.part).order_by('location__rack', 'location__shelf'):
                if remaining <= 0:
                    break
                can = min(entry.available_qty, remaining)
                if can > 0:
                    entry.reserved_qty += can
                    entry.save()
                    remaining -= can
            if remaining > 0:
                messages.warning(request, f'Частичный резерв. Не хватает {remaining} шт.')
            else:
                messages.success(request, 'Деталь добавлена и зарезервирована.')
            return redirect('order_detail', pk=order_pk)
    else:
        form = WorkOrderPartForm()
    return render(request, 'warehouse/workorderpart/create.html', {'form': form, 'order': order})


@login_required
def workorderpart_update(request, pk):
    wop = get_object_or_404(WorkOrderPart, pk=pk)
    order_pk = wop.work_order.pk
    if request.method == 'POST':
        form = WorkOrderPartStatusForm(request.POST, instance=wop)
        if form.is_valid():
            form.save()
            messages.success(request, 'Статус детали обновлён.')
            return redirect('order_detail', pk=order_pk)
    else:
        form = WorkOrderPartStatusForm(instance=wop)
    return render(request, 'warehouse/workorderpart/update.html', {'form': form, 'wop': wop})


@login_required
def workorderpart_delete(request, pk):
    wop = get_object_or_404(WorkOrderPart, pk=pk)
    order_pk = wop.work_order.pk
    if request.method == 'POST':
        if wop.status == 'reserved':
            remaining = wop.quantity
            for entry in StockEntry.objects.filter(part=wop.part):
                if remaining <= 0:
                    break
                release = min(entry.reserved_qty, remaining)
                entry.reserved_qty -= release
                entry.save()
                remaining -= release
        wop.delete()
        messages.success(request, 'Деталь удалена.')
        return redirect('order_detail', pk=order_pk)
    return render(request, 'warehouse/workorderpart/delete.html', {'wop': wop})


# ──────────────────────────────────────────────────────────────
# Work Order Services
# ──────────────────────────────────────────────────────────────

@login_required
def workorderservice_create(request, order_pk):
    from mainapp.models import Order
    order = get_object_or_404(Order, pk=order_pk)
    if request.method == 'POST':
        form = WorkOrderServiceForm(request.POST)
        if form.is_valid():
            wos = form.save(commit=False)
            wos.work_order = order
            wos.save()
            messages.success(request, 'Услуга добавлена.')
            return redirect('order_detail', pk=order_pk)
    else:
        form = WorkOrderServiceForm()
    settings = WorkshopSettings.objects.first()
    return render(request, 'warehouse/workorderservice/create.html', {
        'form': form, 'order': order,
        'hourly_rate': settings.hourly_rate if settings else 0,
    })


@login_required
def workorderservice_update(request, pk):
    wos = get_object_or_404(WorkOrderService, pk=pk)
    order_pk = wos.work_order.pk
    if request.method == 'POST':
        form = WorkOrderServiceForm(request.POST, instance=wos)
        if form.is_valid():
            form.save()
            messages.success(request, 'Услуга обновлена.')
            return redirect('order_detail', pk=order_pk)
    else:
        form = WorkOrderServiceForm(instance=wos)
    settings = WorkshopSettings.objects.first()
    return render(request, 'warehouse/workorderservice/update.html', {
        'form': form, 'wos': wos,
        'hourly_rate': settings.hourly_rate if settings else 0,
    })


@login_required
def workorderservice_delete(request, pk):
    wos = get_object_or_404(WorkOrderService, pk=pk)
    order_pk = wos.work_order.pk
    if request.method == 'POST':
        wos.delete()
        messages.success(request, 'Услуга удалена.')
        return redirect('order_detail', pk=order_pk)
    return render(request, 'warehouse/workorderservice/delete.html', {'wos': wos})


# ──────────────────────────────────────────────────────────────
# Picking List
# ──────────────────────────────────────────────────────────────

@login_required
def picking_list(request, order_pk):
    from mainapp.models import Order
    order = get_object_or_404(Order, pk=order_pk)
    parts = WorkOrderPart.objects.filter(work_order=order).select_related('part').prefetch_related(
        'part__stock_entries__location'
    )
    return render(request, 'warehouse/picking_list.html', {'order': order, 'parts': parts})


# ──────────────────────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────────────────────

@login_required
def settings_view(request):
    settings, _ = WorkshopSettings.objects.get_or_create(pk=1)
    if request.method == 'POST':
        form = WorkshopSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки сохранены.')
            return redirect('warehouse_settings')
    else:
        form = WorkshopSettingsForm(instance=settings)
    return render(request, 'warehouse/settings.html', {'form': form})


# ──────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────

def _get_per_page(request):
    try:
        per_page = int(request.GET.get('per_page', 10))
        return per_page if per_page in [5, 10, 20] else 10
    except (ValueError, TypeError):
        return 10


def models_remaining_filter():
    """Placeholder — not used, filtering done in Python."""
    return 0


def _check_po_overrun(valid_items):
    """Return list of error strings if any PO item would be over-received."""
    proposed: dict[int, int] = {}
    pkg_map: dict[int, int] = {}
    for item in valid_items:
        if item.po_item_id:
            proposed[item.po_item_id] = proposed.get(item.po_item_id, 0) + (item.quantity or 0)
            pkg_map[item.po_item_id] = getattr(item, '_pkg_qty', 1)

    errors = []
    for poi_id, qty in proposed.items():
        try:
            poi = PurchaseOrderItem.objects.select_related('part').get(pk=poi_id)
            if qty > poi.remaining_qty:
                unit = 'упак.' if pkg_map.get(poi_id, 1) > 1 else 'шт.'
                errors.append(
                    f'«{poi.part.article} {poi.part.name}»: хотите принять {qty} {unit}, '
                    f'а по заказу осталось {poi.remaining_qty} {unit}.'
                )
        except PurchaseOrderItem.DoesNotExist:
            pass
    return errors
