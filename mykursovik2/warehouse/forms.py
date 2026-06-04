from django import forms
from .models import (
    Brand, Supplier, Part, StorageLocation, StockEntry,
    SupplyDocument, SupplyItem,
    PurchaseOrder, PurchaseOrderItem,
    WorkOrderPart, WorkOrderService, WorkshopSettings,
    Employee, WriteOff, WriteOffItem,
)


# ── Validators for Russian registration numbers ──────────────

def _validate_inn_ip(inn: str) -> str | None:
    """ИНН ИП — 12 цифр, две контрольные цифры."""
    if not inn.isdigit():
        return 'ИНН должен содержать только цифры.'
    if len(inn) != 12:
        return 'Для ИП ИНН должен содержать ровно 12 цифр.'
    d = [int(c) for c in inn]
    c1 = (d[0]*7 + d[1]*2 + d[2]*4 + d[3]*10 + d[4]*3 + d[5]*5 +
          d[6]*9 + d[7]*4 + d[8]*6 + d[9]*8) % 11 % 10
    c2 = (d[0]*3 + d[1]*7 + d[2]*2 + d[3]*4 + d[4]*10 + d[5]*3 +
          d[6]*5 + d[7]*9 + d[8]*4 + d[9]*6 + d[10]*8) % 11 % 10
    if d[10] != c1 or d[11] != c2:
        return 'ИНН не прошёл проверку контрольной суммы — возможно, введён с ошибкой.'
    return None


def _validate_inn_org(inn: str) -> str | None:
    """ИНН организации — 10 цифр, одна контрольная цифра."""
    if not inn.isdigit():
        return 'ИНН должен содержать только цифры.'
    if len(inn) != 10:
        return 'Для организаций ИНН должен содержать ровно 10 цифр.'
    d = [int(c) for c in inn]
    c = (d[0]*2 + d[1]*4 + d[2]*10 + d[3]*3 + d[4]*5 +
         d[5]*9 + d[6]*4 + d[7]*6 + d[8]*8) % 11 % 10
    if d[9] != c:
        return 'ИНН не прошёл проверку контрольной суммы — возможно, введён с ошибкой.'
    return None


def _validate_ogrn(ogrn: str) -> str | None:
    """ОГРН — 13 цифр, контрольная цифра = остаток от деления первых 12 на 11, взятый mod 10."""
    if not ogrn.isdigit():
        return 'ОГРН должен содержать только цифры.'
    if len(ogrn) != 13:
        return 'ОГРН должен содержать ровно 13 цифр.'
    if ogrn[0] not in ('1', '5'):
        return 'ОГРН должен начинаться с цифры 1 или 5.'
    if int(ogrn[-1]) != int(ogrn[:-1]) % 11 % 10:
        return 'ОГРН не прошёл проверку контрольной суммы — возможно, введён с ошибкой.'
    return None


def _validate_ogrnip(ogrnip: str) -> str | None:
    """ОГРНИП — 15 цифр, контрольная цифра = остаток от деления первых 14 на 13, взятый mod 10."""
    if not ogrnip.isdigit():
        return 'ОГРНИП должен содержать только цифры.'
    if len(ogrnip) != 15:
        return 'ОГРНИП должен содержать ровно 15 цифр.'
    if ogrnip[0] != '3':
        return 'ОГРНИП должен начинаться с цифры 3.'
    if int(ogrnip[-1]) != int(ogrnip[:-1]) % 13 % 10:
        return 'ОГРНИП не прошёл проверку контрольной суммы — возможно, введён с ошибкой.'
    return None


def _validate_kpp(kpp: str) -> str | None:
    """КПП — 9 цифр."""
    if not kpp.isdigit():
        return 'КПП должен содержать только цифры.'
    if len(kpp) != 9:
        return 'КПП должен содержать ровно 9 цифр.'
    return None


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone_country', 'phone', 'contact', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
            'phone_country': forms.Select(attrs={
                'id': 'id_phone_country',
                'style': 'width:auto;flex-shrink:0;',
            }),
        }
        labels = {
            'name': 'Название',
            'phone_country': 'Страна',
            'phone': 'Телефон',
            'contact': 'Контактное лицо',
            'notes': 'Примечания',
        }

    def clean(self):
        cleaned = super().clean()
        phone = cleaned.get('phone', '').strip()
        country = cleaned.get('phone_country', 'RU') or 'RU'
        if phone:
            from mainapp.validators import validate_phone
            ok, result = validate_phone(phone, country)
            if not ok:
                self.add_error('phone', result)
            else:
                cleaned['phone'] = result
        return cleaned


class PartForm(forms.ModelForm):
    # Display-only input for brand — filled via modal, value goes into brand CharField
    brand_display = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'placeholder': 'Нажмите «Выбрать»',
            'id': 'brand-display-input',
        }),
        label='Производитель'
    )

    class Meta:
        model = Part
        fields = ['article', 'name', 'brand', 'category', 'package_qty', 'default_markup', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'brand': forms.HiddenInput(attrs={'id': 'brand-hidden-input'}),
        }
        labels = {
            'article': 'Артикул',
            'name': 'Название',
            'brand': 'Производитель',
            'category': 'Категория',
            'package_qty': 'Штук в упаковке',
            'default_markup': 'Наценка по умолчанию (%)',
            'notes': 'Примечания',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate display input from existing instance or POST data
        if self.instance and self.instance.brand:
            self.fields['brand_display'].initial = self.instance.brand
        elif self.data.get('brand'):
            self.fields['brand_display'].initial = self.data.get('brand')

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        qs = Part.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Деталь с таким названием уже существует.')
        return name


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name']
        labels = {'name': 'Название производителя'}


class StorageLocationForm(forms.ModelForm):
    class Meta:
        model = StorageLocation
        fields = ['rack', 'shelf', 'cell']
        labels = {'rack': 'Стеллаж', 'shelf': 'Полка', 'cell': 'Ячейка'}

    def validate_unique(self):
        # Uniqueness is checked manually in clean() with a user-friendly message;
        # suppress Django's auto-generated unique_together error to avoid duplicates.
        pass

    def clean(self):
        cleaned = super().clean()
        rack = cleaned.get('rack', '').strip()
        shelf = cleaned.get('shelf', '').strip()
        cell = cleaned.get('cell', '').strip()
        if rack and shelf and cell:
            qs = StorageLocation.objects.filter(rack=rack, shelf=shelf, cell=cell)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'Место хранения {rack}-{shelf}-{cell} уже существует.'
                )
        return cleaned


class StockEntryMinQtyForm(forms.ModelForm):
    class Meta:
        model = StockEntry
        fields = ['min_qty']
        labels = {'min_qty': 'Минимальный остаток'}


# ── Purchase Orders ──────────────────────────────────────────

class PurchaseOrderForm(forms.ModelForm):
    supplier_display = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'placeholder': 'Нажмите «Выбрать»',
            'id': 'supplier-display-input',
        }),
        label='Поставщик'
    )

    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'status', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 2}),
            'supplier': forms.HiddenInput(attrs={'id': 'id_supplier'}),
        }
        labels = {
            'supplier': 'Поставщик',
            'status': 'Статус',
            'comment': 'Примечание',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].queryset = Supplier.objects.all().order_by('name')
        self.fields['supplier'].required = False
        # Forbid setting received/partial manually — they are set automatically
        self.fields['status'].choices = [
            ('draft', 'Черновик'),
            ('ordered', 'Заказано'),
            ('in_transit', 'В пути'),
        ]
        # Pre-populate display fields from instance or POST data
        if self.instance and self.instance.pk:
            if self.instance.supplier:
                self.fields['supplier_display'].initial = self.instance.supplier.name
        elif self.data.get('supplier'):
            try:
                s = Supplier.objects.get(pk=self.data['supplier'])
                self.fields['supplier_display'].initial = s.name
            except Supplier.DoesNotExist:
                pass

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('supplier'):
            self.add_error('supplier', 'Укажите поставщика.')
        return cleaned


class PurchaseOrderItemForm(forms.ModelForm):
    # Display fields populated by modal
    part_display = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'placeholder': 'Нажмите «Выбрать»'}),
        label='Деталь'
    )

    class Meta:
        model = PurchaseOrderItem
        fields = ['part', 'quantity']
        widgets = {
            'part': forms.HiddenInput(),
            'quantity': forms.NumberInput(attrs={'min': 1}),
        }
        labels = {'part': 'Деталь', 'quantity': 'Количество'}

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is None:
            raise forms.ValidationError('Укажите количество.')
        if qty < 1:
            raise forms.ValidationError('Количество должно быть не меньше 1.')
        return qty


PurchaseOrderItemFormSet = forms.inlineformset_factory(
    PurchaseOrder, PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class PurchaseOrderStatusForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['status']
        labels = {'status': 'Статус'}

    def __init__(self, *args, current_status=None, **kwargs):
        super().__init__(*args, **kwargs)
        if current_status == 'partial':
            self.fields['status'].choices = [
                ('partial_cancelled', 'Частично получено / Отменено'),
            ]
        else:
            self.fields['status'].choices = [
                ('draft', 'Черновик'),
                ('ordered', 'Заказано'),
                ('in_transit', 'В пути'),
                ('cancelled', 'Отменено'),
            ]


# ── Supply Documents ─────────────────────────────────────────

class SupplyDocumentForm(forms.ModelForm):
    supplier_display = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'placeholder': 'Нажмите «Выбрать»',
            'id': 'supply-supplier-display',
        }),
        label='Поставщик',
    )

    class Meta:
        model = SupplyDocument
        fields = ['supplier', 'purchase_order', 'comment', 'created_at']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 2}),
            'created_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
            'supplier': forms.HiddenInput(attrs={'id': 'supply-supplier-id'}),
            'purchase_order': forms.HiddenInput(),
        }
        labels = {
            'supplier': 'Поставщик',
            'purchase_order': 'Заказ поставщику',
            'comment': 'Примечание',
            'created_at': 'Дата приёмки',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].queryset = Supplier.objects.all().order_by('name')
        self.fields['supplier'].required = False
        self.fields['purchase_order'].queryset = PurchaseOrder.objects.filter(
            status__in=['ordered', 'in_transit', 'partial']
        ).order_by('-created_at')
        self.fields['purchase_order'].required = False
        # Pre-populate supplier display text
        if self.instance and self.instance.pk and self.instance.supplier:
            self.fields['supplier_display'].initial = self.instance.supplier.name
        elif self.data.get('supplier'):
            try:
                s = Supplier.objects.get(pk=self.data['supplier'])
                self.fields['supplier_display'].initial = s.name
            except Supplier.DoesNotExist:
                pass

class SupplyItemForm(forms.ModelForm):
    part_display = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'placeholder': 'Нажмите «Выбрать»'}),
        label='Деталь'
    )
    # Not stored in the model — used to pass "packages entered" to the view,
    # which multiplies by this before writing to StockEntry.
    package_qty = forms.IntegerField(
        required=False, initial=1, widget=forms.HiddenInput()
    )

    class Meta:
        model = SupplyItem
        fields = ['po_item', 'part', 'location', 'quantity', 'purchase_price']
        widgets = {
            'part': forms.HiddenInput(),
            'po_item': forms.HiddenInput(),
            'quantity': forms.NumberInput(attrs={'min': 1}),
        }
        labels = {
            'part': 'Деталь',
            'location': 'Место хранения',
            'quantity': 'Количество',
            'purchase_price': 'Цена закупки',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].queryset = StorageLocation.objects.all().order_by('rack', 'shelf', 'cell')
        # Rows without a location are simply skipped on save — allow partial receipts
        self.fields['location'].required = False
        self.fields['purchase_price'].required = False
        self.fields['part'].required = False
        self.fields['quantity'].required = False
        self.fields['po_item'].required = False

    def clean(self):
        cleaned = super().clean()
        part = cleaned.get('part')
        location = cleaned.get('location')
        quantity = cleaned.get('quantity')
        price = cleaned.get('purchase_price')
        # Row is considered "touched" if the user filled any field.
        # An empty row (nothing filled) is silently skipped in the view.
        # A touched row must be fully valid.
        row_touched = any([part, location, quantity, price])
        if row_touched:
            if not part:
                self.add_error('part', 'Укажите деталь.')
            if not location:
                self.add_error('location', 'Укажите место хранения.')
            if quantity is None or quantity < 1:
                self.add_error('quantity', 'Укажите количество (мин. 1).')
            if not price:
                self.add_error('purchase_price', 'Укажите цену закупки.')
        return cleaned


SupplyItemFormSet = forms.inlineformset_factory(
    SupplyDocument, SupplyItem,
    form=SupplyItemForm,
    extra=1,
    can_delete=True,
)


# ── Work Order Parts / Services ──────────────────────────────

class WorkOrderPartForm(forms.ModelForm):
    part_display = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'placeholder': 'Нажмите «Выбрать»'}),
        label='Деталь'
    )

    class Meta:
        model = WorkOrderPart
        fields = ['part', 'quantity', 'markup']
        widgets = {
            'part': forms.HiddenInput(),
            'quantity': forms.NumberInput(attrs={'min': '1'}),
            'markup': forms.NumberInput(attrs={'min': '0', 'step': '1'}),
        }
        labels = {
            'part': 'Деталь',
            'quantity': 'Количество',
            'markup': 'Наценка (%)',
        }

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is None:
            raise forms.ValidationError('Укажите количество.')
        if qty < 1:
            raise forms.ValidationError('Количество должно быть не меньше 1.')
        return qty

    def clean_markup(self):
        markup = self.cleaned_data.get('markup')
        if markup is None:
            raise forms.ValidationError('Укажите наценку.')
        if markup < 0:
            raise forms.ValidationError('Наценка не может быть отрицательной.')
        return markup


class WorkOrderPartStatusForm(forms.ModelForm):
    class Meta:
        model = WorkOrderPart
        fields = ['quantity', 'markup']
        labels = {
            'quantity': 'Количество',
            'markup': 'Наценка (%)',
        }
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': '1'}),
            'markup': forms.NumberInput(attrs={'min': '0', 'step': '1'}),
        }

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is None:
            raise forms.ValidationError('Укажите количество.')
        if qty < 1:
            raise forms.ValidationError('Количество должно быть не меньше 1.')
        return qty

    def clean_markup(self):
        markup = self.cleaned_data.get('markup')
        if markup is None:
            raise forms.ValidationError('Укажите наценку.')
        if markup < 0:
            raise forms.ValidationError('Наценка не может быть отрицательной.')
        return markup


class WorkOrderServiceForm(forms.ModelForm):
    class Meta:
        model = WorkOrderService
        fields = ['service', 'hours_applied', 'complexity_factor']
        labels = {
            'service': 'Услуга',
            'hours_applied': 'Часы',
            'complexity_factor': 'Коэффициент сложности',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from mainapp.models import Service
        self.fields['service'].queryset = Service.objects.all().order_by('name')


class WorkOrderServiceUpdateForm(forms.ModelForm):
    """Update form for an existing WOS — service field is read-only (shown as text in template)."""
    class Meta:
        model = WorkOrderService
        fields = ['hours_applied', 'complexity_factor']
        labels = {
            'hours_applied': 'Часы',
            'complexity_factor': 'Коэффициент сложности',
        }


class WorkshopSettingsForm(forms.ModelForm):
    class Meta:
        model = WorkshopSettings
        fields = [
            'hourly_rate',
            'org_type', 'org_name', 'inn', 'kpp', 'ogrn', 'ogrnip',
            'org_address', 'org_phone', 'org_email', 'warranty_days',
        ]
        labels = {
            'hourly_rate': 'Стоимость нормо-часа (руб.)',
            'org_type': 'Форма организации',
            'org_name': 'Название / ФИО ИП',
            'inn': 'ИНН',
            'kpp': 'КПП',
            'ogrn': 'ОГРН',
            'ogrnip': 'ОГРНИП',
            'org_address': 'Адрес',
            'org_phone': 'Телефон',
            'org_email': 'Email',
            'warranty_days': 'Срок гарантии (дней)',
        }
        widgets = {
            'org_address': forms.Textarea(attrs={'rows': 2}),
        }

    _ORG_TYPES = ('ООО', 'АО', 'ПАО', 'ЗАО')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.warnings = []

    def clean(self):
        cleaned = super().clean()
        self.warnings = []

        org_type = cleaned.get('org_type', '')
        org_name = (cleaned.get('org_name') or '').strip()
        inn      = (cleaned.get('inn') or '').strip()
        kpp      = (cleaned.get('kpp') or '').strip()
        ogrn     = (cleaned.get('ogrn') or '').strip()
        ogrnip   = (cleaned.get('ogrnip') or '').strip()
        phone    = (cleaned.get('org_phone') or '').strip()
        address  = (cleaned.get('org_address') or '').strip()
        email    = (cleaned.get('org_email') or '').strip()

        is_ip  = (org_type == 'ИП')
        is_org = (org_type in self._ORG_TYPES)

        # ── ИП ───────────────────────────────────────────────
        if is_ip:
            if not org_name:
                self.add_error('org_name', 'Укажите ФИО индивидуального предпринимателя.')

            # ИНН обязателен, 12 цифр + контрольная сумма
            if not inn:
                self.add_error('inn', 'ИНН обязателен для ИП.')
            else:
                err = _validate_inn_ip(inn)
                if err:
                    self.add_error('inn', err)

            # ОГРНИП обязателен, 15 цифр + контрольная сумма
            if not ogrnip:
                self.add_error('ogrnip', 'ОГРНИП обязателен для ИП.')
            else:
                err = _validate_ogrnip(ogrnip)
                if err:
                    self.add_error('ogrnip', err)

            # Запрещённые поля
            if kpp:
                self.add_error('kpp', 'У ИП нет КПП — это реквизит только юридических лиц.')
            if ogrn:
                self.add_error('ogrn', 'У ИП нет ОГРН — используйте поле ОГРНИП.')

        # ── ООО / АО / ПАО / ЗАО ─────────────────────────────
        elif is_org:
            if not org_name:
                self.add_error('org_name', 'Укажите полное наименование организации.')

            # ИНН обязателен, 10 цифр + контрольная сумма
            if not inn:
                self.add_error('inn', 'ИНН обязателен для организации.')
            else:
                err = _validate_inn_org(inn)
                if err:
                    self.add_error('inn', err)

            # КПП обязателен, 9 цифр (без контрольной суммы)
            if not kpp:
                self.add_error('kpp', 'КПП обязателен для организации.')
            else:
                err = _validate_kpp(kpp)
                if err:
                    self.add_error('kpp', err)

            # ОГРН обязателен, 13 цифр + контрольная сумма
            if not ogrn:
                self.add_error('ogrn', 'ОГРН обязателен для организации.')
            else:
                err = _validate_ogrn(ogrn)
                if err:
                    self.add_error('ogrn', err)

            # Запрещённое поле
            if ogrnip:
                self.add_error('ogrnip', 'У организации нет ОГРНИП — используйте поле ОГРН.')

        # ── Мягкие предупреждения (не блокируют сохранение) ──
        if org_type and not phone:
            self.warnings.append('Телефон не указан — он не попадёт в документы для клиентов.')
        if org_type and not address:
            self.warnings.append('Адрес не указан — он не попадёт в документы для клиентов.')
        if org_type and not email:
            self.warnings.append('Email не указан — он не попадёт в документы для клиентов.')

        return cleaned


# ── Write-Off ────────────────────────────────────────────────

class WriteOffForm(forms.ModelForm):
    class Meta:
        model = WriteOff
        fields = ['reason', 'comment', 'created_at']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 2}),
            'created_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
        }
        labels = {
            'reason': 'Причина списания',
            'comment': 'Примечание',
            'created_at': 'Дата списания',
        }


class WriteOffItemForm(forms.ModelForm):
    part_display = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'placeholder': 'Нажмите «Выбрать»'}),
        label='Деталь'
    )

    class Meta:
        model = WriteOffItem
        fields = ['part', 'location', 'quantity']
        widgets = {
            'part': forms.HiddenInput(),
            'quantity': forms.NumberInput(attrs={'min': 1}),
        }
        labels = {
            'part': 'Деталь',
            'location': 'Место хранения',
            'quantity': 'Количество',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].queryset = StorageLocation.objects.all().order_by('rack', 'shelf', 'cell')
        self.fields['location'].required = False
        self.fields['part'].required = False
        self.fields['quantity'].required = False

    def clean(self):
        cleaned = super().clean()
        part = cleaned.get('part')
        location = cleaned.get('location')
        quantity = cleaned.get('quantity')
        row_touched = any([part, location, quantity])
        if row_touched:
            if not part:
                self.add_error('part', 'Укажите деталь.')
            if not location:
                self.add_error('location', 'Укажите место хранения.')
            if quantity is None or quantity < 1:
                self.add_error('quantity', 'Укажите количество (мин. 1).')
            if part and location and quantity and quantity >= 1:
                try:
                    entry = StockEntry.objects.get(part=part, location=location)
                    if quantity > entry.available_qty:
                        self.add_error(
                            'quantity',
                            f'Нельзя списать больше доступного остатка ({entry.available_qty} шт.).'
                        )
                except StockEntry.DoesNotExist:
                    self.add_error('part', 'Этой детали нет на выбранном месте хранения.')
        return cleaned


WriteOffItemFormSet = forms.inlineformset_factory(
    WriteOff, WriteOffItem,
    form=WriteOffItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['name', 'phone_country', 'phone', 'position', 'salary_coefficient', 'is_active']
        labels = {
            'name': 'ФИО',
            'phone_country': 'Страна',
            'phone': 'Телефон',
            'position': 'Должность',
            'salary_coefficient': 'Коэффициент ЗП',
            'is_active': 'Активен',
        }
        widgets = {
            'salary_coefficient': forms.NumberInput(attrs={'min': '0.01', 'max': '9.99', 'step': '0.01'}),
            'phone_country': forms.Select(attrs={
                'id': 'id_phone_country',
                'style': 'width:auto;flex-shrink:0;',
            }),
        }

    def clean_salary_coefficient(self):
        from decimal import Decimal
        coeff = self.cleaned_data.get('salary_coefficient')
        if coeff is None:
            raise forms.ValidationError('Укажите коэффициент ЗП.')
        if coeff < Decimal('0.01'):
            raise forms.ValidationError('Коэффициент ЗП должен быть не менее 0.01.')
        if coeff > Decimal('9.99'):
            raise forms.ValidationError('Коэффициент ЗП не может превышать 9.99.')
        return coeff

    def clean(self):
        cleaned = super().clean()
        phone = cleaned.get('phone', '').strip()
        country = cleaned.get('phone_country', 'RU') or 'RU'
        if phone:
            from mainapp.validators import validate_phone
            ok, result = validate_phone(phone, country)
            if not ok:
                self.add_error('phone', result)
            else:
                cleaned['phone'] = result
        return cleaned


# ── Перемещение запасов ───────────────────────────────────────

class StockMoveForm(forms.Form):
    part = forms.ModelChoiceField(
        queryset=Part.objects.none(),
        label='Деталь',
        empty_label='— выберите деталь —',
    )
    from_location = forms.ModelChoiceField(
        queryset=StorageLocation.objects.order_by('rack', 'shelf', 'cell'),
        label='Откуда',
        empty_label='— выберите место —',
    )
    to_location = forms.ModelChoiceField(
        queryset=StorageLocation.objects.order_by('rack', 'shelf', 'cell'),
        label='Куда',
        empty_label='— выберите место —',
    )
    quantity = forms.IntegerField(
        min_value=1,
        label='Количество',
        widget=forms.NumberInput(attrs={'min': '1'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Только детали с реальным остатком
        self.fields['part'].queryset = (
            Part.objects
            .filter(stock_entries__total_qty__gt=0)
            .distinct()
            .order_by('article')
        )
