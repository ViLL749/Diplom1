"""Tests for stock movement feature."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.test import Client as TC
from django.urls import reverse

from warehouse.models import (
    Part, StorageLocation, StockEntry,
    SupplyDocument, SupplyItem,
)
from warehouse.views import _move_stock_fifo, _fifo_batches_for_move


# ─── helpers ─────────────────────────────────────────────────────────────────

def make_part(article='MV-001', name='Тест'):
    return Part.objects.create(article=article, name=name)


def make_loc(rack='A', shelf='1', cell='1'):
    return StorageLocation.objects.create(rack=rack, shelf=shelf, cell=cell)


def stock_in(part, location, qty, price='100.00', doc=None):
    """Add qty units of part to location at given price. Returns (SupplyItem, StockEntry)."""
    if doc is None:
        doc = SupplyDocument.objects.create()
    si = SupplyItem.objects.create(
        document=doc, part=part, location=location,
        quantity=qty, pkg_qty=1,
        purchase_price=Decimal(price),
    )
    entry, _ = StockEntry.objects.get_or_create(
        part=part, location=location,
        defaults={'total_qty': 0, 'reserved_qty': 0},
    )
    entry.total_qty += qty
    entry.save()
    return si, entry


def make_user():
    user = User.objects.create_user(username='testmove', password='pw')
    return user


# ─── Unit tests for _move_stock_fifo ────────────────────────────────────────

class MoveStockBasicTests(TestCase):

    def setUp(self):
        self.part = make_part()
        self.loc_a = make_loc('A', '1', '1')
        self.loc_b = make_loc('B', '2', '2')

    # T-M-01: basic move, check StockEntry totals
    def test_basic_move_updates_stock_entries(self):
        stock_in(self.part, self.loc_a, 10, '100.00')

        _move_stock_fifo(self.part, self.loc_a, self.loc_b, 4)

        entry_a = StockEntry.objects.get(part=self.part, location=self.loc_a)
        entry_b = StockEntry.objects.get(part=self.part, location=self.loc_b)
        self.assertEqual(entry_a.total_qty, 6)
        self.assertEqual(entry_b.total_qty, 4)

    # T-M-02: SupplyItem created at destination with correct price
    def test_move_creates_supply_item_at_destination(self):
        stock_in(self.part, self.loc_a, 10, '150.00')

        _move_stock_fifo(self.part, self.loc_a, self.loc_b, 3)

        dest_sis = SupplyItem.objects.filter(part=self.part, location=self.loc_b)
        self.assertEqual(dest_sis.count(), 1)
        self.assertEqual(dest_sis.first().quantity, 3)
        self.assertEqual(dest_sis.first().purchase_price, Decimal('150.00'))

    # T-M-03: source SupplyItems are NOT modified
    def test_source_supply_items_unchanged(self):
        si, _ = stock_in(self.part, self.loc_a, 10, '200.00')

        _move_stock_fifo(self.part, self.loc_a, self.loc_b, 5)

        si.refresh_from_db()
        self.assertEqual(si.quantity, 10)  # untouched

    # T-M-04: move more than available → ValueError
    def test_move_more_than_available_raises(self):
        stock_in(self.part, self.loc_a, 5)

        with self.assertRaises(ValueError):
            _move_stock_fifo(self.part, self.loc_a, self.loc_b, 6)

    # T-M-05: zero quantity → ValueError
    def test_zero_quantity_raises(self):
        stock_in(self.part, self.loc_a, 5)

        with self.assertRaises(ValueError):
            _move_stock_fifo(self.part, self.loc_a, self.loc_b, 0)

    # T-M-06: same from/to → ValueError
    def test_same_location_raises(self):
        stock_in(self.part, self.loc_a, 5)

        with self.assertRaises(ValueError):
            _move_stock_fifo(self.part, self.loc_a, self.loc_a, 3)

    # T-M-07: part not at source → ValueError
    def test_part_not_at_source_raises(self):
        with self.assertRaises(ValueError):
            _move_stock_fifo(self.part, self.loc_a, self.loc_b, 1)

    # T-M-08: move to existing location accumulates correctly
    def test_move_to_existing_location_accumulates(self):
        stock_in(self.part, self.loc_a, 10, '100.00')
        stock_in(self.part, self.loc_b, 5, '120.00')

        _move_stock_fifo(self.part, self.loc_a, self.loc_b, 3)

        entry_b = StockEntry.objects.get(part=self.part, location=self.loc_b)
        self.assertEqual(entry_b.total_qty, 8)  # 5 + 3
        # Both original and moved SupplyItems at B
        self.assertEqual(
            SupplyItem.objects.filter(part=self.part, location=self.loc_b).count(), 2
        )

    # T-M-09: move all available units
    def test_move_all_available(self):
        stock_in(self.part, self.loc_a, 7, '100.00')

        _move_stock_fifo(self.part, self.loc_a, self.loc_b, 7)

        entry_a = StockEntry.objects.get(part=self.part, location=self.loc_a)
        self.assertEqual(entry_a.total_qty, 0)
        entry_b = StockEntry.objects.get(part=self.part, location=self.loc_b)
        self.assertEqual(entry_b.total_qty, 7)

    # T-M-10: any reservation blocks the move entirely
    def test_any_reservation_blocks_move(self):
        _, entry = stock_in(self.part, self.loc_a, 10)
        entry.reserved_qty = 1  # even one reserved unit blocks
        entry.save()

        with self.assertRaises(ValueError) as ctx:
            _move_stock_fifo(self.part, self.loc_a, self.loc_b, 9)

        self.assertIn('зарезервировано', str(ctx.exception))
        # Nothing moved
        entry.refresh_from_db()
        self.assertEqual(entry.total_qty, 10)

    # T-M-11: reserved_entry_id is preserved after move (no reservations scenario)
    def test_reserved_entry_id_unchanged_after_move(self):
        _, entry_a = stock_in(self.part, self.loc_a, 10)
        original_entry_id = entry_a.id

        _move_stock_fifo(self.part, self.loc_a, self.loc_b, 7)

        entry_a.refresh_from_db()
        self.assertEqual(entry_a.id, original_entry_id)
        self.assertEqual(entry_a.total_qty, 3)


# ─── FIFO price correctness ──────────────────────────────────────────────────

class FifoBatchTests(TestCase):

    def setUp(self):
        self.part  = make_part('FIFO-001')
        self.loc_a = make_loc('C', '1', '1')
        self.loc_b = make_loc('D', '2', '2')

    # T-M-12: oldest batches move first
    def test_oldest_batch_moves_first(self):
        doc1 = SupplyDocument.objects.create()
        doc2 = SupplyDocument.objects.create()
        stock_in(self.part, self.loc_a, 5, '80.00', doc=doc1)   # older
        stock_in(self.part, self.loc_a, 5, '120.00', doc=doc2)  # newer

        batches = _fifo_batches_for_move(self.part, self.loc_a, 5)

        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]['purchase_price'], Decimal('80.00'))
        self.assertEqual(batches[0]['quantity'], 5)

    # T-M-13: move spans two batches with correct split
    def test_fifo_spans_two_batches(self):
        doc1 = SupplyDocument.objects.create()
        doc2 = SupplyDocument.objects.create()
        stock_in(self.part, self.loc_a, 3, '90.00', doc=doc1)
        stock_in(self.part, self.loc_a, 6, '110.00', doc=doc2)

        batches = _fifo_batches_for_move(self.part, self.loc_a, 7)

        self.assertEqual(len(batches), 2)
        self.assertEqual(batches[0]['quantity'], 3)
        self.assertEqual(batches[0]['purchase_price'], Decimal('90.00'))
        self.assertEqual(batches[1]['quantity'], 4)
        self.assertEqual(batches[1]['purchase_price'], Decimal('110.00'))

    # T-M-14: after move, _in_stock_batches at destination shows correct prices
    def test_destination_shows_correct_prices_after_move(self):
        from warehouse.views import _in_stock_batches
        doc1 = SupplyDocument.objects.create()
        doc2 = SupplyDocument.objects.create()
        stock_in(self.part, self.loc_a, 4, '100.00', doc=doc1)
        stock_in(self.part, self.loc_a, 4, '200.00', doc=doc2)

        _move_stock_fifo(self.part, self.loc_a, self.loc_b, 6)  # 4@100 + 2@200

        dest_batches = _in_stock_batches(self.part)
        dest = [b for b in dest_batches if b['location'] == self.loc_b]
        self.assertEqual(sum(b['remaining'] for b in dest), 6)
        prices = {b['price_per_unit'] for b in dest}
        self.assertIn(Decimal('100.00'), prices)
        self.assertIn(Decimal('200.00'), prices)

    # T-M-15: after partial move, source shows remaining prices correctly
    def test_source_remaining_prices_correct_after_move(self):
        from warehouse.views import _in_stock_batches
        doc1 = SupplyDocument.objects.create()
        doc2 = SupplyDocument.objects.create()
        stock_in(self.part, self.loc_a, 5, '50.00', doc=doc1)
        stock_in(self.part, self.loc_a, 5, '70.00', doc=doc2)

        _move_stock_fifo(self.part, self.loc_a, self.loc_b, 5)  # moves all @50

        src_batches = _in_stock_batches(self.part)
        src = [b for b in src_batches if b['location'] == self.loc_a]
        self.assertEqual(len(src), 1)
        self.assertEqual(src[0]['remaining'], 5)
        self.assertEqual(src[0]['price_per_unit'], Decimal('70.00'))


# ─── View tests ───────────────────────────────────────────────────────────────

class StockMoveViewTests(TestCase):

    def setUp(self):
        self.user  = make_user()
        self.tc    = TC()
        self.tc.login(username='testmove', password='pw')
        self.part  = make_part('VIEW-001', 'Вью деталь')
        self.loc_a = make_loc('E', '1', '1')
        self.loc_b = make_loc('F', '2', '2')
        stock_in(self.part, self.loc_a, 10, '100.00')

    # T-M-16: GET returns 200
    def test_get_returns_200(self):
        resp = self.tc.get(reverse('stock_move'))
        self.assertEqual(resp.status_code, 200)

    # T-M-17: anonymous redirected to login
    def test_anonymous_redirected(self):
        tc   = TC()
        resp = tc.get(reverse('stock_move'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])

    # T-M-18: valid POST performs move and redirects
    def test_valid_post_moves_and_redirects(self):
        resp = self.tc.post(reverse('stock_move'), {
            'part':          self.part.pk,
            'from_location': self.loc_a.pk,
            'to_location':   self.loc_b.pk,
            'quantity':      4,
        })
        self.assertRedirects(resp, reverse('stock_move'))
        self.assertEqual(
            StockEntry.objects.get(part=self.part, location=self.loc_a).total_qty, 6
        )
        self.assertEqual(
            StockEntry.objects.get(part=self.part, location=self.loc_b).total_qty, 4
        )

    # T-M-19: overmove returns 200 with error (no redirect)
    def test_overmove_shows_error(self):
        resp = self.tc.post(reverse('stock_move'), {
            'part':          self.part.pk,
            'from_location': self.loc_a.pk,
            'to_location':   self.loc_b.pk,
            'quantity':      999,
        })
        self.assertEqual(resp.status_code, 200)
        # Stock unchanged
        self.assertEqual(
            StockEntry.objects.get(part=self.part, location=self.loc_a).total_qty, 10
        )

    # T-M-20: same from/to shows form error
    def test_same_location_shows_form_error(self):
        resp = self.tc.post(reverse('stock_move'), {
            'part':          self.part.pk,
            'from_location': self.loc_a.pk,
            'to_location':   self.loc_a.pk,
            'quantity':      3,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'совпадает')

    # T-M-21: AJAX endpoint returns correct location info
    def test_api_part_move_info(self):
        resp = self.tc.get(
            reverse('api_part_move_info'),
            {'part_pk': self.part.pk},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('locations', data)
        self.assertEqual(len(data['locations']), 1)
        loc = data['locations'][0]
        self.assertEqual(loc['total_qty'], 10)
        self.assertEqual(loc['available_qty'], 10)
        self.assertEqual(loc['reserved_qty'], 0)

    # T-M-22: api returns empty list for part with no stock
    def test_api_no_stock_returns_empty(self):
        empty_part = make_part('EMPTY-001', 'Пусто')
        resp = self.tc.get(
            reverse('api_part_move_info'),
            {'part_pk': empty_part.pk},
        )
        self.assertEqual(resp.json()['locations'], [])
