import threading
from datetime import timedelta
from django.db.models.signals import pre_save, post_save, post_delete
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
            stored.setdefault('events', []).extend(new_details.get('events', []))
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
            stored.setdefault('events', []).append(new_details)

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


@receiver(post_delete)
def on_order_delete(sender, instance, **kwargs):
    if sender.__name__ != 'Order':
        return
    _create_log('delete', 'Order', instance.pk, instance)


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
        if instance.work_order:
            details['order'] = f"Заказ №{instance.work_order_id}"
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
    details = {
        'event': 'supply_created',
        'supplier': instance.supplier.name if instance.supplier else '—',
    }
    if instance.purchase_order:
        details['purchase_order'] = str(instance.purchase_order)
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
    details = {
        'event': 'received',
        'article': instance.part.article if instance.part else '—',
        'part_name': instance.part.name if instance.part else '—',
        'quantity': str(instance.quantity),
        'purchase_price': str(instance.purchase_price),
        'location': str(instance.location) if instance.location else '—',
    }
    if instance.po_item:
        details['ordered_qty'] = str(instance.po_item.quantity)
        details['remaining_before'] = str(instance.po_item.remaining_qty + instance.quantity)
    _create_log('update', 'SupplyDocument', instance.document_id, instance.document, details)


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
