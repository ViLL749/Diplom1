import threading
from datetime import timedelta
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.utils import timezone

_locals = threading.local()

SIMPLE_MODELS = {
    'Client', 'ClientCar', 'CarMake', 'CarModel',
    'ServiceType', 'Service', 'Part', 'Brand', 'Supplier',
    'StorageLocation', 'Employee',
}

ORDER_FIELDS = {'status': 'Статус', 'cost': 'Стоимость', 'comment': 'Комментарий'}

MERGE_WINDOW_SECONDS = 300  # 5 minutes


def _is_suppressed():
    return getattr(_locals, 'suppress_signals', False)


# Pairs that cancel each other out when merging within the time window
_OPPOSITE_EVENT = {
    'service_added':   'service_removed',
    'service_removed': 'service_added',
    'part_added':      'part_removed',
    'part_removed':    'part_added',
    'employee_assigned': 'employee_removed',
    'employee_removed':  'employee_assigned',
}


def _event_identity(ev):
    """Return a hashable key that identifies 'which thing' an event refers to."""
    t = ev.get('event', '')
    if t in ('service_added', 'service_removed'):
        return ('service', ev.get('service', ''))
    if t in ('part_added', 'part_removed'):
        return ('part', ev.get('article', ''))
    if t in ('employee_assigned', 'employee_removed'):
        return ('employee', ev.get('employee', ''), ev.get('service', ''))
    return None


def _merge_events(stored_events, new_events):
    """Merge new_events into stored_events; opposite pairs cancel each other out."""
    result = list(stored_events)
    for new_ev in new_events:
        opposite = _OPPOSITE_EVENT.get(new_ev.get('event', ''))
        if opposite:
            key = _event_identity(new_ev)
            if key:
                cancel_idx = next(
                    (i for i, e in enumerate(result)
                     if e.get('event') == opposite and _event_identity(e) == key),
                    None,
                )
                if cancel_idx is not None:
                    result.pop(cancel_idx)
                    continue  # drop new_ev too — net effect is zero
        result.append(new_ev)
    return result


def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return xff.split(',')[0].strip() or request.META.get('REMOTE_ADDR') or None


def _merge_into_log(existing, action, object_repr, new_details):
    stored = existing.details or {'field_changes': [], 'events': []}

    if new_details:
        if 'field_changes' in new_details or 'events' in new_details:
            # Structured format {field_changes, events} from order_commit
            fc_by_field = {c['field']: c for c in stored.get('field_changes', [])}
            for ch in new_details.get('field_changes', []):
                field = ch['field']
                if field in fc_by_field:
                    fc_by_field[field] = {'field': field, 'from': fc_by_field[field]['from'], 'to': ch['to']}
                else:
                    fc_by_field[field] = ch
            stored['field_changes'] = list(fc_by_field.values())
            stored['events'] = _merge_events(stored.get('events', []), new_details.get('events', []))
        elif 'changes' in new_details:
            # Legacy: field-change list
            fc_by_field = {c['field']: c for c in stored.get('field_changes', [])}
            for ch in new_details['changes']:
                field = ch['field']
                if field in fc_by_field:
                    fc_by_field[field] = {
                        'field': field,
                        'from': fc_by_field[field]['from'],
                        'to': ch['to'],
                    }
                else:
                    fc_by_field[field] = ch
            stored['field_changes'] = list(fc_by_field.values())
        else:
            stored['events'] = _merge_events(stored.get('events', []), [new_details])

    if action == 'delete':
        existing.action = 'delete'

    existing.details = stored
    existing.object_repr = str(object_repr)[:500]
    existing.timestamp = timezone.now()
    existing.save(update_fields=['details', 'object_repr', 'timestamp', 'action'])


def _create_log(action, model_name, object_id, object_repr, details=None):
    from .middleware import get_current_request
    from .models import ActionLog
    request = get_current_request()
    user = request.user if (request and hasattr(request, 'user') and request.user.is_authenticated) else None
    ip = _get_ip(request) if request else None

    # Try to merge into a recent log entry for the same user + object
    if user and action != 'delete' and object_id is not None:
        cutoff = timezone.now() - timedelta(seconds=MERGE_WINDOW_SECONDS)
        existing = ActionLog.objects.filter(
            user=user, model_name=model_name, object_id=object_id,
            timestamp__gte=cutoff
        ).order_by('-timestamp').first()
        if existing and existing.action != 'delete':
            _merge_into_log(existing, action, object_repr, details)
            return

    # Build structured details for a new entry
    if details:
        if 'field_changes' in details or 'events' in details:
            built = {
                'field_changes': details.get('field_changes') or [],
                'events': details.get('events') or [],
            }
        elif 'changes' in details:
            built = {'field_changes': details['changes'], 'events': []}
        else:
            built = {'field_changes': [], 'events': [details]}
    else:
        built = None

    ActionLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        object_repr=str(object_repr)[:500],
        ip_address=ip,
        details=built,
    )


# ─── pre_save: сохраняем старые значения ──────────────────────────────────────

@receiver(pre_save)
def on_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        return
    name = sender.__name__

    if name == 'Order':
        try:
            old = sender.objects.get(pk=instance.pk)
            _locals.order_old = {
                'status': old.status,
                'cost': str(old.cost) if old.cost is not None else None,
                'comment': (old.comment or '')[:100],
            }
        except sender.DoesNotExist:
            pass

    elif name == 'PurchaseOrder':
        try:
            old = sender.objects.get(pk=instance.pk)
            _locals.po_old_status = old.status
        except sender.DoesNotExist:
            pass

    elif name == 'WorkOrderPart':
        try:
            old = sender.objects.get(pk=instance.pk)
            _locals.wop_old = {'qty': old.quantity, 'status': old.status}
        except sender.DoesNotExist:
            pass

    elif name == 'PurchaseOrderItem':
        try:
            old = sender.objects.get(pk=instance.pk)
            _locals.poi_old = {'qty': old.quantity, 'received': old.received_qty}
        except sender.DoesNotExist:
            pass


# ─── Order ────────────────────────────────────────────────────────────────────

@receiver(post_save)
def on_order_save(sender, instance, created, **kwargs):
    if sender.__name__ != 'Order':
        return
    if _is_suppressed():
        return

    details = {}

    if created:
        details['event'] = 'order_created'
        details['status'] = instance.status
        if instance.client_car:
            try:
                details['client'] = instance.client_car.client.fio
                details['car'] = f"{instance.client_car.make.name} {instance.client_car.model.name}"
                details['plate'] = instance.client_car.license_plate or '—'
                if instance.client_car.vin:
                    details['vin'] = instance.client_car.vin
            except Exception:
                pass
    else:
        old = getattr(_locals, 'order_old', None)
        if old:
            changes = []
            new_vals = {
                'status': instance.status,
                'cost': str(instance.cost) if instance.cost is not None else None,
                'comment': (instance.comment or '')[:100],
            }
            for field, label in ORDER_FIELDS.items():
                if old.get(field) != new_vals.get(field):
                    changes.append({
                        'field': label,
                        'from': old.get(field) or '—',
                        'to': new_vals.get(field) or '—',
                    })
            if changes:
                details['changes'] = changes
        _locals.order_old = None

    _create_log('create' if created else 'update', 'Order', instance.pk, instance, details or None)


@receiver(pre_delete)
def on_order_pre_delete(sender, instance, **kwargs):
    if sender.__name__ != 'Order':
        return
    try:
        services = []
        for wos in instance.work_order_services.select_related('service').prefetch_related('assignments__employee'):
            svc_name = wos.service_name_snapshot or (wos.service.name if wos.service else '—')
            employees = [a.employee.name for a in wos.assignments.all() if a.employee]
            entry = f"{svc_name} ({wos.hours_applied}ч"
            if wos.final_price:
                entry += f", {wos.final_price} руб."
            entry += ")"
            if employees:
                entry += f" [{', '.join(employees)}]"
            services.append(entry)
        parts = []
        for wop in instance.work_order_parts.select_related('part'):
            part_name = wop.part.name if wop.part else '—'
            article = wop.part.article if wop.part else '—'
            parts.append(f"{article} {part_name} ×{wop.quantity} ({wop.get_status_display()})")
        _locals.order_delete_snapshot = {
            'client': instance.client_fio_static or '—',
            'car': instance.car_details_static or '—',
            'status': instance.status,
            'cost': str(instance.cost) if instance.cost else '—',
            'services': services,
            'parts': parts,
        }
    except Exception:
        _locals.order_delete_snapshot = None


@receiver(post_delete)
def on_order_delete(sender, instance, **kwargs):
    if sender.__name__ != 'Order':
        return
    snapshot = getattr(_locals, 'order_delete_snapshot', None)
    _locals.order_delete_snapshot = None
    details = None
    if snapshot:
        details = {
            'event': 'order_deleted',
            'client': snapshot['client'],
            'car': snapshot['car'],
            'status': snapshot['status'],
            'cost': snapshot['cost'],
        }
        if snapshot['services']:
            details['services'] = '; '.join(snapshot['services'])
        if snapshot['parts']:
            details['parts'] = '; '.join(snapshot['parts'])
    _create_log('delete', 'Order', instance.pk, instance, details)


# ─── WorkOrderService ─────────────────────────────────────────────────────────

@receiver(post_save)
def on_wos_save(sender, instance, created, **kwargs):
    if sender.__name__ != 'WorkOrderService' or not created:
        return
    if _is_suppressed():
        return
    details = {
        'event': 'service_added',
        'service': instance.service_name_snapshot or (instance.service.name if instance.service else '—'),
        'hours': str(instance.hours_applied),
        'complexity': str(instance.complexity_factor),
        'price': str(instance.final_price) if instance.final_price is not None else '—',
    }
    _create_log('update', 'Order', instance.work_order_id, instance.work_order, details)


@receiver(post_delete)
def on_wos_delete(sender, instance, **kwargs):
    if sender.__name__ != 'WorkOrderService':
        return
    if _is_suppressed():
        return
    details = {
        'event': 'service_removed',
        'service': instance.service_name_snapshot or (instance.service.name if instance.service else '—'),
        'hours': str(instance.hours_applied),
        'price': str(instance.final_price) if instance.final_price is not None else '—',
    }
    _create_log('update', 'Order', instance.work_order_id, instance.work_order, details)


# ─── WorkOrderServiceEmployee ─────────────────────────────────────────────────

@receiver(post_save)
def on_wose_save(sender, instance, created, **kwargs):
    if sender.__name__ != 'WorkOrderServiceEmployee' or not created:
        return
    if _is_suppressed():
        return
    try:
        wos = instance.work_order_service
        details = {
            'event': 'employee_assigned',
            'employee': instance.employee.name if instance.employee else '—',
            'service': wos.service_name_snapshot or (wos.service.name if wos.service else '—'),
        }
        _create_log('update', 'Order', wos.work_order_id, wos.work_order, details)
    except Exception:
        pass


@receiver(post_delete)
def on_wose_delete(sender, instance, **kwargs):
    if sender.__name__ != 'WorkOrderServiceEmployee':
        return
    if _is_suppressed():
        return
    try:
        wos = instance.work_order_service
        details = {
            'event': 'employee_removed',
            'employee': instance.employee.name if instance.employee else '—',
            'service': wos.service_name_snapshot or (wos.service.name if wos.service else '—'),
        }
        _create_log('update', 'Order', wos.work_order_id, wos.work_order, details)
    except Exception:
        pass


# ─── WorkOrderPart ────────────────────────────────────────────────────────────

@receiver(post_save)
def on_wop_save(sender, instance, created, **kwargs):
    if sender.__name__ != 'WorkOrderPart':
        return
    if _is_suppressed():
        return
    if created:
        details = {
            'event': 'part_added',
            'article': instance.part.article if instance.part else '—',
            'part_name': instance.part.name if instance.part else '—',
            'quantity': str(instance.quantity),
            'status': instance.get_status_display(),
            'sale_price': str(instance.sale_price) if instance.sale_price else '—',
        }
        _create_log('update', 'Order', instance.work_order_id, instance.work_order, details)
    else:
        old = getattr(_locals, 'wop_old', None)
        if not old:
            return
        changes = []
        if str(old['qty']) != str(instance.quantity):
            changes.append({'field': 'Количество', 'from': str(old['qty']), 'to': str(instance.quantity)})
        if old['status'] != instance.status:
            changes.append({'field': 'Статус', 'from': old['status'], 'to': instance.status})
        _locals.wop_old = None
        if not changes:
            return
        details = {
            'event': 'part_changed',
            'article': instance.part.article if instance.part else '—',
            'part_name': instance.part.name if instance.part else '—',
            'changes': changes,
        }
        _create_log('update', 'Order', instance.work_order_id, instance.work_order, details)


@receiver(post_delete)
def on_wop_delete(sender, instance, **kwargs):
    if sender.__name__ != 'WorkOrderPart':
        return
    if _is_suppressed():
        return
    details = {
        'event': 'part_removed',
        'article': instance.part.article if instance.part else '—',
        'part_name': instance.part.name if instance.part else '—',
        'quantity': str(instance.quantity),
    }
    _create_log('update', 'Order', instance.work_order_id, instance.work_order, details)


# ─── PurchaseOrder ────────────────────────────────────────────────────────────

@receiver(post_save)
def on_po_save(sender, instance, created, **kwargs):
    if sender.__name__ != 'PurchaseOrder':
        return
    if created:
        details = {
            'event': 'purchase_created',
            'supplier': instance.supplier.name if instance.supplier else '—',
            'status': instance.get_status_display(),
        }
        if instance.comment:
            details['comment'] = instance.comment
    else:
        old_status = getattr(_locals, 'po_old_status', None)
        _locals.po_old_status = None
        if not old_status or old_status == instance.status:
            return
        details = {
            'changes': [{
                'field': 'Статус',
                'from': dict(instance.STATUS_CHOICES).get(old_status, old_status),
                'to': instance.get_status_display(),
            }]
        }
    _create_log('create' if created else 'update', 'PurchaseOrder', instance.pk, instance, details)


@receiver(post_delete)
def on_po_delete(sender, instance, **kwargs):
    if sender.__name__ != 'PurchaseOrder':
        return
    _create_log('delete', 'PurchaseOrder', instance.pk, instance)


# ─── PurchaseOrderItem ────────────────────────────────────────────────────────

@receiver(post_save)
def on_poi_save(sender, instance, created, **kwargs):
    if sender.__name__ != 'PurchaseOrderItem':
        return
    if created:
        details = {
            'event': 'item_ordered',
            'article': instance.part.article if instance.part else '—',
            'part_name': instance.part.name if instance.part else '—',
            'quantity': str(instance.quantity),
        }
        _create_log('update', 'PurchaseOrder', instance.purchase_order_id, instance.purchase_order, details)
    else:
        old = getattr(_locals, 'poi_old', None)
        _locals.poi_old = None
        if not old:
            return
        changes = []
        if str(old['qty']) != str(instance.quantity):
            changes.append({'field': 'Заказано', 'from': str(old['qty']), 'to': str(instance.quantity)})
        if str(old['received']) != str(instance.received_qty):
            changes.append({'field': 'Получено', 'from': str(old['received']), 'to': str(instance.received_qty)})
        if not changes:
            return
        details = {
            'event': 'item_updated',
            'article': instance.part.article if instance.part else '—',
            'part_name': instance.part.name if instance.part else '—',
            'changes': changes,
        }
        _create_log('update', 'PurchaseOrder', instance.purchase_order_id, instance.purchase_order, details)


# ─── SupplyDocument ───────────────────────────────────────────────────────────

@receiver(post_save)
def on_supply_save(sender, instance, created, **kwargs):
    if sender.__name__ != 'SupplyDocument' or not created:
        return
    # Reset per-document running total used by on_supplyitem_save
    _locals.supply_received = {}
    details = {
        'event': 'supply_created',
        'supplier': instance.supplier.name if instance.supplier else '—',
    }
    if instance.purchase_order:
        details['purchase_order'] = str(instance.purchase_order)
    if instance.comment:
        details['comment'] = instance.comment
    _create_log('create', 'SupplyDocument', instance.pk, instance, details)


@receiver(post_delete)
def on_supply_delete(sender, instance, **kwargs):
    if sender.__name__ != 'SupplyDocument':
        return
    _create_log('delete', 'SupplyDocument', instance.pk, instance)


# ─── SupplyItem ───────────────────────────────────────────────────────────────

@receiver(post_save)
def on_supplyitem_save(sender, instance, created, **kwargs):
    if sender.__name__ != 'SupplyItem' or not created:
        return
    pkg = instance.pkg_qty or 1
    pkg_count = instance.quantity // pkg if pkg > 1 else instance.quantity
    details = {
        'event': 'received',
        'article': instance.part.article if instance.part else '—',
        'part_name': instance.part.name if instance.part else '—',
        'packages': str(pkg_count),
        'purchase_price': str(instance.purchase_price),
        'location': str(instance.location) if instance.location else '—',
    }
    if pkg > 1:
        details['pkg_qty'] = str(pkg)
        details['units_total'] = str(instance.quantity)
    if instance.po_item:
        poi = instance.po_item
        # received_qty is updated via F() after the whole item loop, so we track
        # the running total ourselves to get accurate before/after values per row.
        # PO quantities are in packages; instance.quantity is in units (already
        # multiplied by pkg_qty when pkg_qty > 1), so convert back to PO units.
        po_qty = pkg_count  # already computed above
        acc = getattr(_locals, 'supply_received', {})
        already_in_this_doc = acc.get(poi.pk, 0)
        remaining_before = poi.remaining_qty - already_in_this_doc
        remaining_after = max(0, remaining_before - po_qty)
        acc[poi.pk] = already_in_this_doc + po_qty
        _locals.supply_received = acc
        details['po_ordered'] = str(poi.quantity)
        details['po_remaining_before'] = str(remaining_before)
        details['po_remaining_after'] = str(remaining_after)
    _create_log('update', 'SupplyDocument', instance.document_id, instance.document, details)


# ─── StockEntry (только изменение мин. остатка) ───────────────────────────────

@receiver(pre_save)
def on_stock_pre_save(sender, instance, **kwargs):
    if sender.__name__ != 'StockEntry' or not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
        _locals.stock_old_min = old.min_qty
    except sender.DoesNotExist:
        pass


@receiver(post_save)
def on_stock_save(sender, instance, created, **kwargs):
    if sender.__name__ != 'StockEntry' or created:
        return
    old_min = getattr(_locals, 'stock_old_min', None)
    _locals.stock_old_min = None
    if old_min is None or old_min == instance.min_qty:
        return
    details = {
        'event': 'min_qty_changed',
        'article': instance.part.article if instance.part else '—',
        'part_name': instance.part.name if instance.part else '—',
        'location': str(instance.location) if instance.location else '—',
        'changes': [{'field': 'Мин. остаток', 'from': str(old_min), 'to': str(instance.min_qty)}],
    }
    _create_log('update', 'StockEntry', instance.pk, instance, details)


# ─── WriteOff ─────────────────────────────────────────────────────────────────

@receiver(post_save)
def on_writeoff_save(sender, instance, created, **kwargs):
    if sender.__name__ != 'WriteOff' or not created:
        return
    details = {
        'event': 'write_off_created',
        'reason': instance.reason,
    }
    if instance.comment:
        details['comment'] = instance.comment
    _create_log('create', 'WriteOff', instance.pk, instance, details)


@receiver(post_save)
def on_writeoffitem_save(sender, instance, created, **kwargs):
    if sender.__name__ != 'WriteOffItem' or not created:
        return
    details = {
        'event': 'written_off',
        'article': instance.part.article if instance.part else '—',
        'part_name': instance.part.name if instance.part else '—',
        'quantity': str(instance.quantity),
        'location': str(instance.location) if instance.location else '—',
        'reason': instance.write_off.reason if instance.write_off else '—',
    }
    _create_log('update', 'WriteOff', instance.write_off_id, instance.write_off, details)


# ─── Простые модели ───────────────────────────────────────────────────────────

@receiver(post_save)
def on_simple_save(sender, instance, created, **kwargs):
    if sender.__name__ not in SIMPLE_MODELS:
        return
    _create_log('create' if created else 'update', sender.__name__, instance.pk, instance)


@receiver(post_delete)
def on_simple_delete(sender, instance, **kwargs):
    if sender.__name__ not in SIMPLE_MODELS:
        return
    _create_log('delete', sender.__name__, instance.pk, instance)
