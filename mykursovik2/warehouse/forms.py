from django import forms
from .models import (
    Brand, Supplier, Part, StorageLocation, StockEntry,
    SupplyDocument, SupplyItem,
    PurchaseOrder, PurchaseOrderItem,
    WorkOrderPart, WorkOrderService, WorkshopSettings,
    Employee, WriteOff, WriteOffItem,
)


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'contact', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}
        labels = {
            'name': 'Название',
            'phone': 'Телефон',
            'contact': 'Контактное лицо',
            'notes': 'Примечания',
        }

    def clean_phone(self):
        import re
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            if not re.match(r'^\+7\s\(\d{3}\)\s\d{3}-\d{2}-\d{2}$', phone):
                raise forms.ValidationError(
                    'Введите номер в формате +7 (999) 999-99-99.'
                )
        return phone


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
        widgets = {'part': forms.HiddenInput()}
        labels = {
            'part': 'Деталь',
            'quantity': 'Количество',
            'markup': 'Наценка (%)',
        }


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
        fields = ['hourly_rate']
        labels = {'hourly_rate': 'Стоимость нормо-часа (руб.)'}


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
