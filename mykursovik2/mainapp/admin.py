import os
from datetime import timedelta

from django.conf import settings
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils import timezone

from .models import ActionLog, BackupLog, BackupSettings


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action_colored', 'model_verbose', 'object_id', 'object_repr', 'ip_address', 'has_details')
    list_filter = ('action', 'model_name', 'user', 'timestamp')
    search_fields = ('object_repr', 'user__username', 'ip_address')
    readonly_fields = ('user', 'action', 'model_name', 'object_id', 'object_repr', 'ip_address', 'timestamp', 'details_display')
    fields = ('timestamp', 'user', 'action', 'model_name', 'object_id', 'object_repr', 'ip_address', 'details_display')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    list_per_page = 50

    MODEL_VERBOSE = {
        'Client': 'Клиент',
        'ClientCar': 'Автомобиль',
        'Order': 'Заказ',
        'CarMake': 'Марка авто',
        'CarModel': 'Модель авто',
        'ServiceType': 'Тип услуги',
        'Service': 'Услуга',
        'Brand': 'Бренд',
        'Supplier': 'Поставщик',
        'Part': 'Запчасть',
        'StorageLocation': 'Локация',
        'PurchaseOrder': 'Закупка',
        'SupplyDocument': 'Поставка',
        'StockEntry': 'Остаток склада',
        'Employee': 'Сотрудник',
        'WriteOff': 'Списание',
    }

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description='', boolean=False)
    def has_details(self, obj):
        from django.utils.html import format_html
        if obj.details:
            return format_html('<span style="color:#2563eb;font-size:16px;" title="Есть подробности">●</span>')
        return ''

    EVENT_LABELS = {
        'order_created': 'Создан заказ',
        'service_added': 'Добавлена услуга',
        'service_updated': 'Изменена услуга',
        'service_removed': 'Удалена услуга',
        'employee_assigned': 'Назначен исполнитель',
        'employee_removed': 'Снят исполнитель',
        'part_added': 'Добавлена запчасть',
        'part_updated': 'Изменена запчасть',
        'part_changed': 'Изменена запчасть',
        'part_removed': 'Удалена запчасть',
        'purchase_created': 'Создана закупка',
        'status_changed': 'Изменён статус',
        'item_ordered': 'Позиция заказана',
        'item_updated': 'Позиция обновлена',
        'supply_created': 'Создана поставка',
        'received': 'Получено на склад',
        'order_deleted': 'Удалён заказ',
        'min_qty_changed': 'Изменён мин. остаток',
        'write_off_created': 'Создано списание',
        'written_off': 'Списано со склада',
    }

    FIELD_LABELS = {
        'client': 'Клиент', 'car': 'Автомобиль', 'plate': 'Госномер',
        'vin': 'VIN', 'status': 'Статус', 'supplier': 'Поставщик',
        'order': 'Заказ', 'service': 'Услуга', 'hours': 'Часы',
        'complexity': 'Коэф. сложности', 'factor': 'Коэф. сложности', 'price': 'Цена',
        'employee': 'Исполнитель', 'article': 'Артикул',
        'part_name': 'Запчасть', 'quantity': 'Количество', 'qty': 'Количество',
        'markup': 'Наценка (%)',
        'packages': 'Упаковок', 'pkg_qty': 'Штук в упаковке', 'units_total': 'Итого штук',
        'sale_price': 'Цена продажи', 'purchase_price': 'Цена закупки',
        'location': 'Место хранения',
        # supply item — PO link
        'ordered_qty': 'Заказано', 'remaining_before': 'Остаток до (устар.)',
        'po_ordered': 'Заказано у поставщика',
        'po_remaining_before': 'Остаток до приёмки',
        'po_remaining_after': 'Остаток после приёмки',
        'purchase_order': 'Заказ поставки',
        # order deletion snapshot
        'cost': 'Стоимость', 'services': 'Услуги', 'parts': 'Запчасти',
        'comment': 'Примечание',
    }

    @admin.display(description='Подробности')
    def details_display(self, obj):
        from django.utils.html import escape, mark_safe
        if not obj.details:
            return '—'
        d = obj.details
        rows = []

        def _change_row(field, frm, to):
            return (
                f'<tr>'
                f'<td style="color:#64748b;padding:4px 10px;white-space:nowrap;">{escape(field)}</td>'
                f'<td style="padding:4px 10px;">'
                f'<span style="color:#dc2626;">{escape(str(frm))}</span>'
                f' → '
                f'<span style="color:#16a34a;">{escape(str(to))}</span>'
                f'</td></tr>'
            )

        def _kv_row(key, val):
            label = self.FIELD_LABELS.get(key, key)
            return (
                f'<tr>'
                f'<td style="color:#64748b;padding:4px 10px 4px 18px;white-space:nowrap;">{escape(label)}</td>'
                f'<td style="padding:4px 10px;">{escape(str(val))}</td>'
                f'</tr>'
            )

        def _section_hdr(text, bg='#f1f5f9'):
            return (
                f'<tr><td colspan="2" style="background:{bg};font-weight:600;'
                f'padding:6px 10px;border-top:2px solid #e2e8f0;">'
                f'{escape(text)}</td></tr>'
            )

        # ── New structure: {field_changes, events} ──────────────────────────
        field_changes = d.get('field_changes', [])
        events = d.get('events', [])

        if field_changes:
            rows.append(_section_hdr('Изменения полей'))
            for ch in field_changes:
                rows.append(_change_row(ch.get('field', ''), ch.get('from', '—'), ch.get('to', '—')))

        for ev in events:
            if not ev:
                continue
            ev_key = ev.get('event', '')
            ev_label = self.EVENT_LABELS.get(ev_key, ev_key or 'Событие')
            rows.append(_section_hdr(ev_label, bg='#f0f9ff'))

            # If event has nested changes (e.g. part_changed)
            inner_changes = ev.get('changes')
            if inner_changes:
                for ch in inner_changes:
                    rows.append(_change_row(ch.get('field', ''), ch.get('from', '—'), ch.get('to', '—')))
            for key, val in ev.items():
                if key in ('event', 'changes'):
                    continue
                rows.append(_kv_row(key, val))

        # ── Legacy flat structure (old log entries) ──────────────────────────
        if not field_changes and not events:
            old_changes = d.get('changes')
            if old_changes:
                rows.append(_section_hdr('Изменения'))
                for ch in old_changes:
                    rows.append(_change_row(ch.get('field', ''), ch.get('from', '—'), ch.get('to', '—')))
            else:
                ev_key = d.get('event', '')
                if ev_key:
                    rows.append(_section_hdr(self.EVENT_LABELS.get(ev_key, ev_key)))
                for key, val in d.items():
                    if key in ('event', 'changes'):
                        continue
                    rows.append(_kv_row(key, val))

        if not rows:
            return '—'

        table = (
            '<table style="border-collapse:collapse;min-width:340px;font-size:13px;">'
            + ''.join(rows)
            + '</table>'
        )
        return mark_safe(table)

    @admin.display(description='Действие')
    def action_colored(self, obj):
        from django.utils.html import format_html
        colors = {'create': '#16a34a', 'update': '#2563eb', 'delete': '#dc2626'}
        labels = {'create': 'Создание', 'update': 'Изменение', 'delete': 'Удаление'}
        color = colors.get(obj.action, '#64748b')
        label = labels.get(obj.action, obj.action)
        return format_html('<span style="color:{};font-weight:600;">{}</span>', color, label)

    @admin.display(description='Модель')
    def model_verbose(self, obj):
        return self.MODEL_VERBOSE.get(obj.model_name, obj.model_name)


def _do_backup():
    """Экспортирует все данные через dumpdata в JSON и создаёт BackupLog."""
    from io import StringIO
    from django.core.management import call_command

    backup_dir = settings.BASE_DIR / 'backups'
    backup_dir.mkdir(exist_ok=True)
    ts = timezone.now().strftime('%Y%m%d_%H%M%S')
    file_name = f'backup_{ts}.json'
    dest = backup_dir / file_name

    out = StringIO()
    call_command(
        'dumpdata',
        '--natural-foreign', '--natural-primary',
        '--exclude=contenttypes', '--exclude=auth.permission',
        '--indent=2',
        stdout=out,
    )
    dest.write_text(out.getvalue(), encoding='utf-8')
    size_kb = max(1, os.path.getsize(dest) // 1024)
    return BackupLog.objects.create(file_name=file_name, size_kb=size_kb)


@admin.register(BackupSettings)
class BackupSettingsAdmin(admin.ModelAdmin):
    fields = ('timezone', 'interval_days')

    def has_add_permission(self, request):
        return not BackupSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = BackupSettings.load()
        return HttpResponseRedirect(
            reverse('admin:mainapp_backupsettings_change', args=[obj.pk])
        )


@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'file_name', 'size_kb')
    readonly_fields = ('created_at', 'file_name', 'size_kb')
    change_list_template = 'admin/mainapp/backuplog/change_list.html'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                'create-now/',
                self.admin_site.admin_view(self.create_now_view),
                name='mainapp_backuplog_create_now',
            ),
        ]
        return extra + urls

    def create_now_view(self, request):
        log = _do_backup()
        self.message_user(request, f'Резервная копия создана: {log.file_name} ({log.size_kb} КБ).', messages.SUCCESS)
        return HttpResponseRedirect(reverse('admin:mainapp_backuplog_changelist'))

    def changelist_view(self, request, extra_context=None):
        cfg = BackupSettings.load()
        last = BackupLog.objects.first()
        auto_created = None

        if last is None or (timezone.now() - last.created_at) >= timedelta(days=cfg.interval_days):
            log = _do_backup()
            auto_created = log.file_name
            last = log

        extra_context = extra_context or {}
        extra_context['backup_interval'] = cfg.interval_days
        extra_context['last_backup'] = last
        extra_context['auto_backup_created'] = auto_created
        extra_context['backup_dir'] = str(settings.BASE_DIR / 'backups')
        return super().changelist_view(request, extra_context=extra_context)
