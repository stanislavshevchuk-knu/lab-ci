from unittest.mock import Mock

import pytest

from shop.cart import Cart, RateProvider


def test_new_cart_is_empty(empty_cart: Cart) -> None:
    assert empty_cart.items_count() == 0
    assert empty_cart.total() == 0


def test_add_counts_all_units(cart_with_items: Cart) -> None:
    assert cart_with_items.items_count() == 6


def test_add_same_name_merges_quantity(empty_cart: Cart) -> None:
    empty_cart.add("book", price=200.0, qty=1)
    empty_cart.add("book", price=200.0, qty=2)
    assert empty_cart.items_count() == 3
    assert empty_cart.total() == 600.0


def test_remove_existing_item(cart_with_items: Cart) -> None:
    cart_with_items.remove("pen")
    assert cart_with_items.items_count() == 2
    assert cart_with_items.total() == 400.0


def test_total_without_discount(cart_with_items: Cart) -> None:
    assert cart_with_items.total() == 460.0


def test_total_with_discount(cart_with_items: Cart) -> None:
    assert cart_with_items.total(discount_percent=10) == 414.0


@pytest.mark.parametrize(
    ("discount", "expected"),
    [(0, 460.0), (10, 414.0), (50, 230.0), (100, 0.0)],
)
def test_total_discount_boundaries(cart_with_items: Cart, discount: float, expected: float) -> None:
    assert cart_with_items.total(discount_percent=discount) == expected


def test_add_negative_price_raises(empty_cart: Cart) -> None:
    with pytest.raises(ValueError, match="price"):
        empty_cart.add("book", price=-1.0)


@pytest.mark.parametrize("qty", [0, -1])
def test_add_non_positive_qty_raises(empty_cart: Cart, qty: int) -> None:
    with pytest.raises(ValueError, match="qty"):
        empty_cart.add("book", price=10.0, qty=qty)


@pytest.mark.parametrize("discount", [-1, 100.5, 101])
def test_total_invalid_discount_raises(cart_with_items: Cart, discount: float) -> None:
    with pytest.raises(ValueError, match="discount_percent"):
        cart_with_items.total(discount_percent=discount)


def test_remove_missing_item_raises(empty_cart: Cart) -> None:
    with pytest.raises(KeyError):
        empty_cart.remove("ghost")


def test_total_in_with_mock(empty_cart: Cart) -> None:
    rates = Mock(spec=RateProvider)
    rates.get_rate.return_value = 40.0  # 1 USD = 40 UAH
    empty_cart.add("book", price=400.0)

    assert empty_cart.total_in("USD", rates) == 10.0
    rates.get_rate.assert_called_once_with("USD")


class FakeRates:
    """Власна заглушка (stub): завжди повертає заданий курс."""

    def __init__(self, rate: float) -> None:
        self._rate = rate
        self.last_currency: str | None = None

    def get_rate(self, currency: str) -> float:
        self.last_currency = currency
        return self._rate


def test_total_in_with_stub(cart_with_items: Cart) -> None:
    assert cart_with_items.total_in("EUR", FakeRates(46.0)) == 10.0


@pytest.mark.parametrize("rate", [0.0, -5.0])
def test_total_in_invalid_rate_raises(cart_with_items: Cart, rate: float) -> None:
    with pytest.raises(ValueError, match="rate"):
        cart_with_items.total_in("USD", FakeRates(rate))


def test_most_expensive_empty_cart_returns_none(empty_cart: Cart) -> None:
    assert empty_cart.most_expensive() is None


def test_most_expensive_returns_item_with_highest_unit_price(cart_with_items: Cart) -> None:
    item = cart_with_items.most_expensive()

    assert item is not None
    assert item.name == "book"
    assert item.price == 200.0


def test_most_expensive_compares_unit_price_not_line_total(empty_cart: Cart) -> None:
    empty_cart.add("pen", price=15.0, qty=100)  # у сумі 1500, але одиниця дешева
    empty_cart.add("laptop", price=1000.0, qty=1)

    item = empty_cart.most_expensive()

    assert item is not None
    assert item.name == "laptop"


def test_add_same_name_with_different_price_keeps_original_price(
    empty_cart: Cart,
) -> None:
    empty_cart.add("book", price=200.0, qty=1)
    empty_cart.add("book", price=300.0, qty=1)

    item = empty_cart.most_expensive()

    assert item is not None
    assert item.name == "book"
    assert item.price == 200.0
    assert item.qty == 2
