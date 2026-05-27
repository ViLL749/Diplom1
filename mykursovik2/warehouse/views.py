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
    WorkOrderServiceForm, WorkOrderServiceUpdateForm, WorkshopSettingsForm,
    EmployeeForm, WriteOffForm, WriteOffItemFormSet,
)
from .models import (
    Brand, Supplier, Part, StorageLocation, StockEntry,
    SupplyDocument, SupplyItem,
    PurchaseOrder, PurchaseOrderItem,
    WorkOrderPart, WorkOrderService, WorkshopSettings,
    Employee, WorkOrderServiceEmployee, WriteOff, WriteOffItem,
)


# ──────────────────────────────────────────────────────────────
# AJAX API
# ──────────────────────────────────────────────────────────────

def _in_stock_batches(part, available_only=False):
    """Return supply batches with remaining stock, per-unit prices and remaining qty.

    Uses per-location FIFO: for each StockEntry we consult only the SupplyItems
    at that location to find which batches are still physically present and how many
    are available (unreserved).

    available_only=True  → only unreserved units (use for pricing / reservation)
    available_only=False → all physical units (use for display)
    """
    from decimal import Decimal

    result = []
    entries = StockEntry.objects.filter(part=part).select_related('location')

    for entry in entries:
        units_to_show = entry.available_qty if available_only else entry.total_qty
        if units_to_show <= 0:
            continue

        # SupplyItems at this location in FIFO order (oldest batch first)
        supply_items = list(
            SupplyItem.objects.filter(part=part, location=entry.location)
            .select_related('document')
            .order_by('document__created_at', 'id')
        )

        total_received = sum(si.quantity for si in supply_items)
        # Units physically removed (sold / written off) from this location
        consumed = max(0, total_received - entry.total_qty)

        remaining_to_show = units_to_show
        consumed_skipped = 0  # how many consumed units we've accounted for

        for si in supply_items:
            if remaining_to_show <= 0:
                break

            # Skip units consumed from this batch (FIFO within location)
            if consumed_skipped + si.quantity <= consumed:
                consumed_skipped += si.quantity
                continue

            already_consumed_from_si = max(0, consumed - consumed_skipped)
            physical_in_si = si.quantity - already_consumed_from_si
            consumed_skipped = consumed  # all consumed units now accounted for

            show = min(physical_in_si, remaining_to_show)
            if show <= 0:
                continue

            pkg = si.pkg_qty or 1
            price_pkg = (part.package_qty or 1) if pkg == 1 and (part.package_qty or 1) > 1 else pkg
            result.append({
                'price_per_pkg':  si.purchase_price,
                'price_per_unit': si.purchase_price / Decimal(price_pkg),
                'pkg_qty':   pkg,
                'remaining': show,
                'doc_id':    si.document_id,
                'date':      si.document.created_at,
                'location':  entry.location,
            })
            remaining_to_show -= show

    return result


def _min_stock_price(part, quantity=1):
    """Return total purchase cost for `quantity` units using cheapest available batches.

    Uses cheapest available (unreserved) batches first.
    If quantity exceeds total available, prices only what's available.
    Returns total cost (not per-unit average) to avoid rounding errors on sale_price.
    """
    from decimal import Decimal
    batches = _in_stock_batches(part, available_only=True)
    if not batches:
        return None

    # cheapest first — give the best possible price
    by_price = sorted(batches, key=lambda b: b['price_per_unit'])

    remaining = quantity
    total_cost = Decimal('0')
    total_used = 0
    for b in by_price:
        if remaining <= 0:
            break
        use = min(b['remaining'], remaining)
        total_cost += b['price_per_unit'] * Decimal(use)
        total_used += use
        remaining -= use

    if not total_used:
        return None
    return total_cost  # total purchase cost for all units used


def _reserve_cheapest_first(part, quantity):
    """Reserve `quantity` units picking cheapest available batches first.

    Returns (shortage, reserved_entries) where:
      shortage        = units that could not be reserved (0 = fully reserved)
      reserved_entries = [{'entry_id': id, 'qty': n}, ...] — exact entries touched,
                         in cheapest-first order (used for deterministic issue/unreserve).
    """
    avail_batches = _in_stock_batches(part, available_only=True)
    if not avail_batches:
        return quantity, []
    by_price = sorted(avail_batches, key=lambda b: b['price_per_unit'])
    remaining = quantity
    reserved_entries = []
    for batch in by_price:
        if remaining <= 0:
            break
        entry = StockEntry.objects.filter(part=part, location=batch['location']).first()
        if not entry:
            continue
        use = min(entry.available_qty, batch['remaining'], remaining)
        if use <= 0:
            continue
        entry.reserved_qty += use
        entry.save()
        reserved_entries.append({'entry_id': entry.id, 'qty': use})
        remaining -= use
    return remaining, reserved_entries


def _recalculate_order_cost(order):
    from decimal import Decimal as _D
    wos_total = sum(
        (w.final_price or _D('0')) for w in WorkOrderService.objects.filter(work_order=order)
    )
    wop_total = sum(
        (w.sale_price or _D('0')) for w in WorkOrderPart.objects.filter(work_order=order)
    )
    order.cost = wos_total + wop_total
    order.save(update_fields=['cost'])


@login_required
def api_services(request):
    """Return all services grouped by type for the order detail service modal."""
    from mainapp.models import Service, ServiceType
    result = []
    for stype in ServiceType.objects.prefetch_related('service_set').all():
        svcs = [
            {'id': s.id, 'name': s.name, 'base_hours': float(s.base_hours)}
            for s in stype.service_set.all()
        ]
        if svcs:
            result.append({'type': stype.name, 'services': svcs})
    return JsonResponse({'groups': result})


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
    page_parts = list(page_obj)
    # Build available stock map in one query
    from django.db.models import Sum
    stock_map = {}
    for row in StockEntry.objects.filter(part__in=page_parts).values('part_id').annotate(
        tot=Sum('total_qty'), res=Sum('reserved_qty')
    ):
        stock_map[row['part_id']] = (row['tot'] or 0) - (row['res'] or 0)
    price_map = {}
    for si in SupplyItem.objects.filter(part__in=page_parts).values('part_id', 'purchase_price', 'pkg_qty'):
        pkg = si['pkg_qty'] or 1
        unit = float(si['purchase_price']) / pkg
        pid = si['part_id']
        if pid not in price_map or unit < price_map[pid]:
            price_map[pid] = unit
    return JsonResponse({
        'parts': [
            {
                'id': p.id, 'article': p.article, 'name': p.name,
                'brand': p.brand, 'package_qty': p.package_qty,
                'available': stock_map.get(p.id, 0),
                'unit_price': price_map.get(p.id),
                'default_markup': float(p.default_markup) if p.default_markup else 0,
            }
            for p in page_parts
        ],
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })


@login_required
def api_part_price(request):
    """Return exact total purchase cost for a given part + quantity (uses actual stock batches).

    Supports two modes:
    - wopId: editing existing WOP — preserves cost of already-reserved units, queries
             available stock only for the EXTRA quantity above the current reservation.
    - partId: adding a new part — queries available stock for the full quantity.
    """
    qty = max(1, int(request.GET.get('qty', 1) or 1))
    wop_id = request.GET.get('wopId')

    if wop_id:
        wop = WorkOrderPart.objects.filter(pk=wop_id).first()
        if not wop:
            return JsonResponse({'error': 'WOP not found'}, status=404)
        part = wop.part
        old_qty = wop.quantity
        if wop.sale_price and old_qty:
            old_factor = 1 + wop.markup / Decimal('100')
            old_cost = wop.sale_price / old_factor  # purchase cost without markup
            if qty > old_qty:
                extra = _min_stock_price(part, qty - old_qty)
                total_cost = old_cost + (extra or Decimal('0'))
            elif qty < old_qty:
                total_cost = old_cost * Decimal(qty) / Decimal(old_qty)
            else:
                total_cost = old_cost
        else:
            total_cost = _min_stock_price(part, qty)
        extra_avail = sum(e.available_qty for e in StockEntry.objects.filter(part=part))
        return JsonResponse({
            'total_cost': float(total_cost) if total_cost is not None else None,
            'qty': qty,
            'available_qty': old_qty + extra_avail,  # already reserved + still free
        })

    part_id = request.GET.get('partId')
    if not part_id:
        return JsonResponse({'error': 'partId or wopId required'}, status=400)
    part = Part.objects.filter(pk=part_id).first()
    if not part:
        return JsonResponse({'error': 'Not found'}, status=404)
    total_cost = _min_stock_price(part, qty)
    avail = sum(e.available_qty for e in StockEntry.objects.filter(part=part))
    return JsonResponse({
        'total_cost': float(total_cost) if total_cost is not None else None,
        'qty': qty,
        'available_qty': avail,
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
# Purchase Prices (cost by part)
# ──────────────────────────────────────────────────────────────

@login_required
def purchase_prices_list(request):
    """Parts that have at least one stock entry, with total qty and reserve."""
    from django.db.models import Sum
    search = request.GET.get('search', '')
    parts = Part.objects.filter(
        stock_entries__total_qty__gt=0
    ).distinct()
    if search:
        parts = parts.filter(
            Q(article__icontains=search) | Q(name__icontains=search)
        )
    parts = parts.order_by('article')
    # Annotate totals across all locations
    parts_data = []
    for part in parts:
        entries = part.stock_entries.all()
        total = sum(e.total_qty for e in entries)
        reserved = sum(e.reserved_qty for e in entries)
        if total > 0:
            parts_data.append({'part': part, 'total': total, 'reserved': reserved, 'available': total - reserved})
    per_page = _get_per_page(request)
    paginator = Paginator(parts_data, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'warehouse/purchase_prices/list.html', {
        'page_obj': page_obj, 'per_page': per_page,
    })


@login_required
def purchase_prices_detail(request, part_pk):
    """Show only batches currently in stock with per-unit prices."""
    part = get_object_or_404(Part, pk=part_pk)
    entries = part.stock_entries.select_related('location').all()
    total_qty = sum(e.total_qty for e in entries)
    reserved_qty = sum(e.reserved_qty for e in entries)

    in_stock = _in_stock_batches(part, available_only=False)
    in_stock_avail = _in_stock_batches(part, available_only=True)

    # Map (doc_id, location_id) → available remaining (may differ from total remaining)
    avail_map = {(b['doc_id'], b['location'].id): b['remaining'] for b in in_stock_avail}
    for b in in_stock:
        b['avail_remaining'] = avail_map.get((b['doc_id'], b['location'].id), 0)

    min_price = min((b['price_per_unit'] for b in in_stock), default=None)
    min_price_available = min(
        (b['price_per_unit'] for b in in_stock_avail), default=None
    ) if in_stock_avail else None
    price_diff = (
        (min_price_available - min_price).quantize(Decimal('0.01'))
        if min_price and min_price_available and min_price_available != min_price
        else None
    )

    return render(request, 'warehouse/purchase_prices/detail.html', {
        'part': part,
        'total_qty': total_qty,
        'reserved_qty': reserved_qty,
        'available_qty': total_qty - reserved_qty,
        'in_stock': in_stock,
        'min_price': min_price,
        'min_price_available': min_price_available,
        'price_diff': price_diff,
    })


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
        # Conflict detection: another employee processed a receipt for this PO in the meantime
        if initial_po:
            po_version_sent = request.POST.get('po_version', '')
            if po_version_sent and po_version_sent != initial_po.updated_at.isoformat():
                return redirect(f"{request.path}?po={initial_po.pk}&conflict=1")

        doc_form = SupplyDocumentForm(request.POST)
        formset = SupplyItemFormSet(request.POST)
        doc_valid = doc_form.is_valid()
        formset_valid = formset.is_valid()
        if doc_valid and formset_valid:
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
                item._pkg_qty = item.part.package_qty if item.part and item.part.package_qty else 1
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
                        item.pkg_qty = pkg  # persist so FIFO can compute per-unit price
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
        'po_version': initial_po.updated_at.isoformat() if initial_po else '',
        # On POST re-render we must NOT re-run the AJAX prefill — it would wipe
        # the quantities the user already typed in.
        'prefill_fresh': request.method == 'GET',
    })


@login_required
def supply_detail(request, pk):
    from decimal import Decimal
    doc = get_object_or_404(SupplyDocument, pk=pk)
    items = list(doc.items.select_related('part', 'location', 'po_item').all())
    grand_total = Decimal('0')
    for item in items:
        pkg = item.pkg_qty or 1
        item.computed_price_per_unit = item.purchase_price / Decimal(pkg)
        item.computed_total_cost = item.computed_price_per_unit * item.quantity
        item.computed_pkg_count = item.quantity // pkg if pkg > 1 else item.quantity
        grand_total += item.computed_total_cost
    return render(request, 'warehouse/supply/detail.html', {
        'doc': doc, 'items': items, 'grand_total': grand_total,
    })


# ──────────────────────────────────────────────────────────────
# Purchase Orders
# ──────────────────────────────────────────────────────────────

@login_required
def purchase_list(request):
    orders = PurchaseOrder.objects.select_related('supplier').all()
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
        'po': po, 'items': items, 'supply_docs': supply_docs,
        'po_version': po.updated_at.isoformat(),
        'po_status_choices': (
            [('partial_cancelled', 'Частично получено / Отменено')]
            if po.status == 'partial'
            else [(k, v) for k, v in PurchaseOrder.STATUS_CHOICES
                  if k not in ('received', 'partial', 'partial_cancelled')]
        ),
    })


@login_required
def purchase_update(request, pk):
    from django.http import JsonResponse as _JR
    po = get_object_or_404(PurchaseOrder, pk=pk)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if po.is_final:
        if is_ajax:
            return _JR({'error': 'Нельзя изменить статус завершённого или отменённого заказа.'}, status=400)
        messages.error(request, 'Нельзя изменить статус завершённого или отменённого заказа.')
        return redirect('purchase_detail', pk=pk)

    if request.method == 'POST':
        client_version = request.POST.get('client_version', '')
        if client_version and client_version != po.updated_at.isoformat():
            if is_ajax:
                return _JR({
                    'conflict': True,
                    'message': 'Заказ поставщику был изменён другим сотрудником. Страница будет обновлена.',
                })
            messages.warning(request, 'Заказ поставщику был изменён другим сотрудником. Страница обновлена.')
            return redirect('purchase_detail', pk=pk)

        form = PurchaseOrderStatusForm(request.POST, instance=po, current_status=po.status)
        if form.is_valid():
            new_status = form.cleaned_data['status']
            if new_status in ('received', 'partial'):
                if is_ajax:
                    return _JR({'error': 'Этот статус проставляется автоматически.'}, status=400)
                messages.error(request, 'Этот статус проставляется автоматически.')
                return redirect('purchase_detail', pk=pk)
            form.save()
            if is_ajax:
                return _JR({'success': True})
            messages.success(request, 'Статус обновлён.')
            return redirect('purchase_detail', pk=pk)
        else:
            if is_ajax:
                return _JR({'error': 'Ошибка формы.'}, status=400)
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
            # Weighted average price across the requested quantity of available batches
            cost_total = _min_stock_price(wop.part, wop.quantity)
            if cost_total is not None:
                markup = wop.markup / Decimal('100')
                wop.sale_price = (cost_total * (1 + markup)).quantize(Decimal('0.01'))
            # Optional link to a WorkOrderService
            wos_pk = request.POST.get('work_order_service') or ''
            if wos_pk.strip():
                wos = WorkOrderService.objects.filter(pk=wos_pk, work_order=order).first()
                wop.work_order_service = wos
            wop.save()
            # Reserve from cheapest batches first (matches _min_stock_price ordering)
            shortage = _reserve_cheapest_first(wop.part, wop.quantity)
            if shortage > 0:
                messages.warning(request, f'Частичный резерв: не хватает {shortage} шт.')
            else:
                messages.success(request, 'Деталь добавлена и зарезервирована.')
            _recalculate_order_cost(order)
            return redirect('order_detail', pk=order_pk)
    else:
        form = WorkOrderPartForm()
    wos_list = WorkOrderService.objects.filter(work_order=order).select_related('service')
    return render(request, 'warehouse/workorderpart/create.html', {
        'form': form, 'order': order, 'wos_list': wos_list,
    })


@login_required
def workorderpart_update(request, pk):
    wop = get_object_or_404(WorkOrderPart, pk=pk)
    order_pk = wop.work_order.pk
    if request.method == 'POST':
        old_qty = wop.quantity
        old_markup = wop.markup
        old_sale_price = wop.sale_price
        form = WorkOrderPartStatusForm(request.POST, instance=wop)
        if form.is_valid():
            new_qty = form.cleaned_data['quantity']
            new_markup = form.cleaned_data['markup']
            delta = new_qty - old_qty

            # Recalculate sale_price when qty or markup changed.
            # sale_price stores TOTAL (all qty). Preserve cost of already-reserved units;
            # for extra qty, query actual available stock batches.
            if (new_qty != old_qty or new_markup != old_markup) and old_sale_price and old_qty:
                old_factor = 1 + old_markup / Decimal('100')
                old_cost = old_sale_price / old_factor  # total purchase cost without markup
                if new_qty > old_qty:
                    # _min_stock_price returns cost for min(delta, available) units,
                    # so sale_price is already correct even when shortage occurs later.
                    extra_cost = _min_stock_price(wop.part, new_qty - old_qty) or Decimal('0')
                    total_cost = old_cost + extra_cost
                elif new_qty < old_qty:
                    total_cost = old_cost * Decimal(new_qty) / Decimal(old_qty)
                else:
                    total_cost = old_cost
                form.instance.sale_price = (
                    total_cost * (1 + new_markup / Decimal('100'))
                ).quantize(Decimal('0.01'))

            if delta != 0 and wop.status == 'reserved':
                if delta > 0:
                    shortage, new_res = _reserve_cheapest_first(wop.part, delta)
                    if shortage > 0:
                        actually_reserved = delta - shortage
                        new_qty -= shortage
                        form.instance.quantity = new_qty
                        # sale_price was already computed using _min_stock_price(part, delta)
                        # which prices min(delta, available) = actually_reserved units — no adjustment needed.
                        messages.warning(request, f'Не удалось зарезервировать {shortage} шт. — сохранено {old_qty + actually_reserved} шт.')
                    # Merge new reservations into tracked list
                    existing = list(wop.reserved_entries or [])
                    for nr in new_res:
                        merged = False
                        for ex in existing:
                            if ex['entry_id'] == nr['entry_id']:
                                ex['qty'] += nr['qty']
                                merged = True
                                break
                        if not merged:
                            existing.append(nr)
                    form.instance.reserved_entries = existing
                else:
                    # Release excess — remove from most-expensive end (last in list = highest price)
                    to_release = -delta
                    tracked = list(wop.reserved_entries or [])
                    from warehouse.models import StockEntry as _SE
                    new_tracked = []
                    for item in reversed(tracked):
                        if to_release <= 0:
                            new_tracked.insert(0, item)
                            continue
                        entry = _SE.objects.filter(id=item['entry_id']).first()
                        release = min(item['qty'], to_release)
                        if entry and release > 0:
                            entry.reserved_qty -= release
                            entry.save()
                        to_release -= release
                        remaining_in_item = item['qty'] - release
                        if remaining_in_item > 0:
                            new_tracked.insert(0, {'entry_id': item['entry_id'], 'qty': remaining_in_item})
                    form.instance.reserved_entries = new_tracked

            form.save()
            _recalculate_order_cost(wop.work_order)
            messages.success(request, 'Деталь обновлена.')
            return redirect('order_detail', pk=order_pk)
    else:
        form = WorkOrderPartStatusForm(instance=wop)
    base_price = None
    if wop.sale_price is not None and wop.markup is not None and wop.quantity:
        factor = 1 + wop.markup / Decimal('100')
        if factor:
            base_price = (wop.sale_price / factor / wop.quantity).quantize(Decimal('0.01'))
    return render(request, 'warehouse/workorderpart/update.html', {
        'form': form, 'wop': wop, 'base_price': base_price,
    })


@login_required
def workorderpart_delete(request, pk):
    wop = get_object_or_404(WorkOrderPart, pk=pk)
    order_pk = wop.work_order.pk
    if request.method == 'POST':
        if wop.status == 'reserved':
            from warehouse.models import StockEntry as _SE
            tracked = wop.reserved_entries or []
            if tracked:
                for item in tracked:
                    entry = _SE.objects.filter(id=item['entry_id']).first()
                    if entry:
                        entry.reserved_qty -= min(entry.reserved_qty, item['qty'])
                        entry.save()
            else:
                from mainapp.views import _entries_cheapest_first
                remaining = wop.quantity
                for entry in _entries_cheapest_first(wop.part):
                    if remaining <= 0:
                        break
                    release = min(entry.reserved_qty, remaining)
                    entry.reserved_qty -= release
                    entry.save()
                    remaining -= release
        order = wop.work_order
        wop.delete()
        _recalculate_order_cost(order)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'success': True})
        messages.success(request, 'Деталь удалена.')
        return redirect('order_detail', pk=order_pk)
    return render(request, 'warehouse/workorderpart/delete.html', {'wop': wop})


# ──────────────────────────────────────────────────────────────
# Work Order Services
# ──────────────────────────────────────────────────────────────

@login_required
def workorderservice_create_bulk(request, order_pk):
    from mainapp.models import Order, Service
    order = get_object_or_404(Order, pk=order_pk)
    if request.method == 'POST':
        service_ids = request.POST.getlist('service_id')
        hours_list = request.POST.getlist('hours_applied')
        factor_list = request.POST.getlist('complexity_factor')
        settings = WorkshopSettings.objects.first()
        rate_snapshot = settings.hourly_rate if settings else Decimal('0')
        created = 0
        for sid, hours, factor in zip(service_ids, hours_list, factor_list):
            try:
                service = Service.objects.get(pk=int(sid))
                WorkOrderService.objects.create(
                    work_order=order,
                    service=service,
                    service_name_snapshot=service.name,
                    hourly_rate_snapshot=rate_snapshot,
                    hours_applied=Decimal(hours),
                    complexity_factor=Decimal(factor),
                )
                created += 1
            except Exception:
                pass
        if created:
            _recalculate_order_cost(order)
            messages.success(request, f'Добавлено услуг: {created}.')
    return redirect('order_detail', pk=order_pk)


@login_required
def workorderservice_create(request, order_pk):
    from mainapp.models import Order
    order = get_object_or_404(Order, pk=order_pk)
    if request.method == 'POST':
        form = WorkOrderServiceForm(request.POST)
        if form.is_valid():
            wos = form.save(commit=False)
            wos.work_order = order
            settings = WorkshopSettings.objects.first()
            wos.service_name_snapshot = wos.service.name
            wos.hourly_rate_snapshot = settings.hourly_rate if settings else Decimal('0')
            wos.save()
            _recalculate_order_cost(order)
            messages.success(request, 'Услуга добавлена.')
            return redirect('order_detail', pk=order_pk)
    else:
        form = WorkOrderServiceForm()
    from mainapp.models import Service as _Service
    import json as _json
    settings = WorkshopSettings.objects.first()
    service_hours = {s.id: float(s.base_hours) for s in _Service.objects.all()}
    return render(request, 'warehouse/workorderservice/create.html', {
        'form': form, 'order': order,
        'hourly_rate': settings.hourly_rate if settings else 0,
        'service_hours_json': _json.dumps(service_hours),
    })


@login_required
def workorderservice_update(request, pk):
    wos = get_object_or_404(WorkOrderService, pk=pk)
    order_pk = wos.work_order.pk
    if request.method == 'POST':
        form = WorkOrderServiceUpdateForm(request.POST, instance=wos)
        if form.is_valid():
            form.save()
            _recalculate_order_cost(wos.work_order)
            messages.success(request, 'Услуга обновлена.')
            return redirect('order_detail', pk=order_pk)
    else:
        form = WorkOrderServiceUpdateForm(instance=wos)
    return render(request, 'warehouse/workorderservice/update.html', {
        'form': form, 'wos': wos,
        'hourly_rate': wos.hourly_rate_snapshot,
    })


@login_required
def workorderservice_delete(request, pk):
    wos = get_object_or_404(WorkOrderService, pk=pk)
    order_pk = wos.work_order.pk
    if request.method == 'POST':
        order = wos.work_order
        wos.delete()
        _recalculate_order_cost(order)
        messages.success(request, 'Услуга удалена.')
        return redirect('order_detail', pk=order_pk)
    return render(request, 'warehouse/workorderservice/delete.html', {'wos': wos})


# ──────────────────────────────────────────────────────────────
# Picking List
# ──────────────────────────────────────────────────────────────

@login_required
def picking_list(request, order_pk):
    from mainapp.models import Order
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from django.http import HttpResponse
    import io, os

    order = get_object_or_404(Order, pk=order_pk)
    parts = list(WorkOrderPart.objects.filter(work_order=order).select_related('part').prefetch_related(
        'part__stock_entries__location'
    ))

    # Register Cyrillic-capable font
    _font_candidates = [
        '/Library/Fonts/Arial Unicode.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    fn = 'Helvetica'
    for _fp in _font_candidates:
        if os.path.exists(_fp):
            try:
                pdfmetrics.registerFont(TTFont('_CyrFont', _fp))
                fn = '_CyrFont'
            except Exception:
                pass
            break

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    h1 = ParagraphStyle('h1', fontName=fn, fontSize=13, spaceAfter=4, leading=16)
    p  = ParagraphStyle('p',  fontName=fn, fontSize=10, spaceAfter=3, leading=13)

    story = []
    story.append(Paragraph(f'Лист отборки — Заказ-наряд №{order.id}', h1))
    if order.client_fio_static:
        story.append(Paragraph(f'Клиент: {order.client_fio_static}', p))
    if order.car_details_static:
        story.append(Paragraph(f'Автомобиль: {order.car_details_static}', p))
    story.append(Paragraph(f'Дата: {order.order_date.strftime("%d.%m.%Y")}', p))
    story.append(Spacer(1, 0.4*cm))

    header = ['Место хранения', 'Артикул', 'Название', 'Кол-во', 'Статус', '✓']
    rows = [header]
    for wop in parts:
        entry = wop.part.stock_entries.first()
        loc = entry.location.label if entry else '—'
        rows.append([loc, wop.part.article, wop.part.name,
                     str(wop.quantity), wop.get_status_display(), ''])
    if len(rows) == 1:
        rows.append(['Деталей нет', '', '', '', '', ''])

    col_w = [3.2*cm, 2.4*cm, 6.6*cm, 1.4*cm, 2.8*cm, 0.8*cm]
    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('FONTNAME',   (0, 0), (-1, -1), fn),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0),  colors.HexColor('#1e40af')),
        ('TEXTCOLOR',  (0, 0), (-1, 0),  colors.white),
        ('GRID',       (0, 0), (-1, -1), 0.4, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',  (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)

    doc.build(story)
    buf.seek(0)
    resp = HttpResponse(buf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="picking_{order.pk}.pdf"'
    return resp


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


# ──────────────────────────────────────────────────────────────
# Employees (Mechanics)
# ──────────────────────────────────────────────────────────────

@login_required
def employees_list(request):
    employees = Employee.objects.all()
    search = request.GET.get('search', '')
    if search:
        employees = employees.filter(name__icontains=search)
    return render(request, 'warehouse/employees/list.html', {
        'employees': employees, 'search': search,
    })


@login_required
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Сотрудник добавлен.')
            return redirect('employees_list')
    else:
        form = EmployeeForm()
    return render(request, 'warehouse/employees/create.html', {'form': form})


@login_required
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, 'Сотрудник обновлён.')
            return redirect('employees_list')
    else:
        form = EmployeeForm(instance=employee)
    return render(request, 'warehouse/employees/update.html', {'form': form, 'employee': employee})


@login_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.delete()
        messages.success(request, 'Сотрудник удалён.')
        return redirect('employees_list')
    return render(request, 'warehouse/employees/delete.html', {'employee': employee})


@login_required
def employee_report(request, pk):
    """Earnings report for a single employee. Only completed orders count."""
    from decimal import Decimal
    from datetime import date, datetime
    employee = get_object_or_404(Employee, pk=pk)

    today = date.today()
    first_of_month = today.replace(day=1)
    date_from_str = request.GET.get('date_from', '')
    date_to_str   = request.GET.get('date_to', '')
    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to   = datetime.strptime(date_to_str,   '%Y-%m-%d').date() if date_to_str   else None
    except ValueError:
        date_from = date_to = None

    qs = (
        WorkOrderServiceEmployee.objects
        .filter(employee=employee)
        .select_related('work_order_service__work_order', 'work_order_service__service')
        .order_by('-work_order_service__work_order__completion_date',
                  '-work_order_service__work_order__id')
    )
    if date_from:
        qs = qs.filter(work_order_service__work_order__completion_date__gte=date_from)
    if date_to:
        qs = qs.filter(work_order_service__work_order__completion_date__lte=date_to)

    rows = []
    total_hours = Decimal('0')
    total_earnings = Decimal('0')
    for a in qs:
        wos = a.work_order_service
        n = wos.assignments.count()
        hours_share = wos.hours_applied / Decimal(n) if n else Decimal('0')
        is_done = wos.work_order.status == 'Завершён'
        rate = wos.hourly_rate_snapshot or Decimal('0')
        coeff = a.salary_coefficient_snapshot if a.salary_coefficient_snapshot is not None \
            else (employee.salary_coefficient or Decimal('1'))
        base_share = (hours_share * rate).quantize(Decimal('0.01'))
        earnings = (base_share * coeff).quantize(Decimal('0.01')) if is_done else Decimal('0')
        if is_done:
            total_hours += hours_share
            total_earnings += earnings
        rows.append({
            'order_id': wos.work_order.id,
            'completion_date': wos.work_order.completion_date,
            'service_name': wos.service_name_snapshot or (wos.service.name if wos.service else '—'),
            'hours_share': hours_share,
            'n_employees': n,
            'rate': rate,
            'coeff': coeff,
            'base_share': base_share,
            'earnings': earnings,
            'order_status': wos.work_order.status,
            'is_done': is_done,
        })
    return render(request, 'warehouse/employees/report.html', {
        'employee': employee,
        'rows': rows,
        'total_hours': total_hours,
        'total_earnings': total_earnings,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'filtered': bool(date_from_str or date_to_str),
    })


@login_required
def employees_report_all(request):
    """Summary earnings for all employees. Only completed orders count."""
    from decimal import Decimal
    employees = Employee.objects.filter(is_active=True)
    data = []
    for emp in employees:
        total_hours = Decimal('0')
        total_earnings = Decimal('0')
        qs = (WorkOrderServiceEmployee.objects
              .filter(employee=emp, work_order_service__work_order__status='Завершён')
              .select_related('work_order_service'))
        for a in qs:
            wos = a.work_order_service
            n = wos.assignments.count()
            if n:
                hours_share = wos.hours_applied / Decimal(n)
                rate = wos.hourly_rate_snapshot or Decimal('0')
                coeff = a.salary_coefficient_snapshot if a.salary_coefficient_snapshot is not None \
                    else (emp.salary_coefficient or Decimal('1'))
                total_hours += hours_share
                total_earnings += (hours_share * rate * coeff).quantize(Decimal('0.01'))
        data.append({
            'employee': emp,
            'total_hours': total_hours,
            'total_earnings': total_earnings,
        })
    data.sort(key=lambda x: x['total_earnings'], reverse=True)
    return render(request, 'warehouse/employees/report_all.html', {'data': data})


@login_required
def api_assign_employee(request, wos_pk):
    """AJAX: assign an employee to a WorkOrderService."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    wos = get_object_or_404(WorkOrderService, pk=wos_pk)
    emp_pk = request.POST.get('employee_id')
    if not emp_pk:
        return JsonResponse({'error': 'employee_id required'}, status=400)
    employee = get_object_or_404(Employee, pk=emp_pk)
    asgn, created = WorkOrderServiceEmployee.objects.get_or_create(
        work_order_service=wos, employee=employee,
        defaults={'salary_coefficient_snapshot': employee.salary_coefficient},
    )
    if not created and asgn.salary_coefficient_snapshot is None:
        asgn.salary_coefficient_snapshot = employee.salary_coefficient
        asgn.save(update_fields=['salary_coefficient_snapshot'])
    n = wos.assignments.count()
    from decimal import Decimal
    assignments = [
        {
            'id': a.id,
            'employee_id': a.employee.id,
            'name': a.employee.name,
            'hours': str(wos.hours_applied / Decimal(n)),
            'earnings': str((wos.final_price or Decimal('0')) / Decimal(n)),
        }
        for a in wos.assignments.select_related('employee')
    ]
    return JsonResponse({'created': created, 'assignments': assignments})


@login_required
def api_unassign_employee(request, wos_pk, emp_pk):
    """AJAX: remove an employee from a WorkOrderService."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    WorkOrderServiceEmployee.objects.filter(
        work_order_service_id=wos_pk, employee_id=emp_pk
    ).delete()
    wos = get_object_or_404(WorkOrderService, pk=wos_pk)
    n = wos.assignments.count()
    from decimal import Decimal
    assignments = [
        {
            'id': a.id,
            'employee_id': a.employee.id,
            'name': a.employee.name,
            'hours': str(wos.hours_applied / Decimal(n)) if n else '0',
            'earnings': str((wos.final_price or Decimal('0')) / Decimal(n)) if n else '0',
        }
        for a in wos.assignments.select_related('employee')
    ]
    return JsonResponse({'assignments': assignments})


@login_required
def api_employees(request):
    """AJAX: list active employees for assignment modal."""
    search = request.GET.get('search', '')
    emps = Employee.objects.filter(is_active=True)
    if search:
        emps = emps.filter(name__icontains=search)
    return JsonResponse({
        'employees': [{'id': e.id, 'name': e.name, 'position': e.position,
                       'salary_coefficient': str(e.salary_coefficient)} for e in emps[:50]]
    })


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


# ──────────────────────────────────────────────────────────────
# Write-Off (Списание)
# ──────────────────────────────────────────────────────────────

@login_required
def write_off_list(request):
    from django.utils import timezone as tz
    qs = WriteOff.objects.prefetch_related('items__part')
    per_page = int(request.GET.get('per_page', 10))
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'warehouse/writeoff/list.html', {
        'page_obj': page_obj,
        'per_page': per_page,
    })


@login_required
def write_off_create(request):
    from django.utils import timezone as tz
    if request.method == 'POST':
        form = WriteOffForm(request.POST)
        formset = WriteOffItemFormSet(request.POST, prefix='items')
        form_valid = form.is_valid()
        formset_valid = formset.is_valid()
        if not form_valid or not formset_valid:
            # Detect if errors are stock-related (concurrent change) vs user mistake
            stock_conflict_msgs = []
            for f in formset:
                if not f.errors:
                    continue
                for err_list in f.errors.values():
                    for err in err_list:
                        if 'остат' in err or 'не на выбранном' in err:
                            stock_conflict_msgs.append(err)
            return render(request, 'warehouse/writeoff/create.html', {
                'form': form, 'formset': formset, 'has_errors': True,
                'stock_conflict_msgs': stock_conflict_msgs,
            })
        if form_valid and formset_valid:
            valid_items = [
                f for f in formset
                if f.cleaned_data and not f.cleaned_data.get('DELETE')
                and f.cleaned_data.get('part')
                and f.cleaned_data.get('location')
                and f.cleaned_data.get('quantity')
            ]
            if not valid_items:
                messages.error(request, 'Добавьте хотя бы одну позицию для списания.')
            else:
                conflict = None
                try:
                    with transaction.atomic():
                        wo = form.save()
                        for item_form in valid_items:
                            part = item_form.cleaned_data['part']
                            location = item_form.cleaned_data['location']
                            quantity = item_form.cleaned_data['quantity']
                            # Re-check inside the lock — another user may have
                            # depleted stock between our validation and now.
                            entry = StockEntry.objects.select_for_update().get(
                                part=part, location=location
                            )
                            if quantity > entry.available_qty:
                                conflict = (
                                    f'«{part.article} {part.name}» на {location}: '
                                    f'хотите списать {quantity} шт., '
                                    f'но сейчас доступно только {entry.available_qty} шт. '
                                    f'(другой сотрудник уже произвёл списание).'
                                )
                                raise ValueError('conflict')
                            WriteOffItem.objects.create(
                                write_off=wo,
                                part=part,
                                location=location,
                                quantity=quantity,
                            )
                            entry.total_qty -= quantity
                            if entry.reserved_qty > entry.total_qty:
                                entry.reserved_qty = entry.total_qty
                            entry.save()
                except ValueError:
                    return render(request, 'warehouse/writeoff/create.html', {
                        'form': form, 'formset': formset,
                        'conflict_error': conflict,
                    })
                return redirect('write_off_detail', pk=wo.pk)
    else:
        form = WriteOffForm(initial={
            'created_at': tz.localtime(tz.now()).strftime('%Y-%m-%dT%H:%M')
        })
        formset = WriteOffItemFormSet(prefix='items')
    return render(request, 'warehouse/writeoff/create.html', {
        'form': form,
        'formset': formset,
    })


@login_required
def write_off_detail(request, pk):
    wo = get_object_or_404(
        WriteOff.objects.prefetch_related('items__part', 'items__location'),
        pk=pk
    )
    return render(request, 'warehouse/writeoff/detail.html', {'wo': wo})


@login_required
def api_part_stock(request):
    """AJAX: return available_qty for a given part+location combination."""
    part_id = request.GET.get('part')
    location_id = request.GET.get('location')
    if not part_id or not location_id:
        return JsonResponse({'available_qty': 0})
    try:
        entry = StockEntry.objects.get(part_id=part_id, location_id=location_id)
        return JsonResponse({'available_qty': entry.available_qty, 'total_qty': entry.total_qty})
    except StockEntry.DoesNotExist:
        return JsonResponse({'available_qty': 0, 'total_qty': 0})


@login_required
def api_part_locations(request):
    """AJAX: return locations where the given part has available stock."""
    part_id = request.GET.get('part')
    if not part_id:
        return JsonResponse({'locations': []})
    entries = (
        StockEntry.objects
        .filter(part_id=part_id)
        .select_related('location')
        .order_by('location__rack', 'location__shelf', 'location__cell')
    )
    locations = []
    for e in entries:
        avail = e.available_qty
        if avail > 0:
            locations.append({
                'id': e.location_id,
                'label': str(e.location),
                'available_qty': avail,
            })
    return JsonResponse({'locations': locations})
