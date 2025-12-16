# =============================================================================
# TEST 2: ONLINE ALISVERIS SISTEMI
# Zorluk: ORTA | Siniflar, kalitim, metod cagrilari
# =============================================================================
# Beklenen: LLM sinif iliskilerini dogru anlamali
# Potansiyel Halusinasyon: Kalitim iliskilerini yanlis yorumlama

class Product:
    def __init__(self, name, price):
        self.name = name
        self.price = price
        self._validate_price()

    def _validate_price(self):
        if self.price < 0:
            self._handle_invalid_price()

    def _handle_invalid_price(self):
        self.price = 0

    def get_discounted_price(self, discount):
        return self._calculate_discount(discount)

    def _calculate_discount(self, discount):
        return self.price * (1 - discount)


class ShoppingCart:
    def __init__(self):
        self.items = []
        self.total = 0

    def add_item(self, product, quantity):
        self._validate_quantity(quantity)
        self.items.append((product, quantity))
        self._update_total()

    def _validate_quantity(self, quantity):
        if quantity <= 0:
            self._log_error("Invalid quantity")

    def _update_total(self):
        self.total = self._calculate_total()

    def _calculate_total(self):
        total = 0
        for product, qty in self.items:
            total += product.price * qty
        return total

    def _log_error(self, message):
        pass

    def checkout(self):
        if self._validate_cart():
            return self._process_payment()
        return False

    def _validate_cart(self):
        return len(self.items) > 0

    def _process_payment(self):
        self._send_confirmation()
        return True

    def _send_confirmation(self):
        pass


class OrderProcessor:
    def __init__(self, cart):
        self.cart = cart
        self.order_id = None

    def process_order(self):
        if self.cart.checkout():
            self.order_id = self._generate_order_id()
            self._save_order()
            self._notify_customer()
            return True
        return False

    def _generate_order_id(self):
        return "ORD-12345"

    def _save_order(self):
        self._write_to_database()

    def _write_to_database(self):
        pass

    def _notify_customer(self):
        self._send_email()
        self._send_sms()

    def _send_email(self):
        pass

    def _send_sms(self):
        pass


def create_sample_order():
    """Ornek siparis olusturur."""
    product1 = Product("Laptop", 1000)
    product2 = Product("Mouse", 50)

    cart = ShoppingCart()
    cart.add_item(product1, 1)
    cart.add_item(product2, 2)

    processor = OrderProcessor(cart)
    return processor.process_order()


# =============================================================================
# BEKLENEN CALL GRAPH:
# =============================================================================
# create_sample_order
#   --> Product.__init__ --> _validate_price --> _handle_invalid_price
#   --> ShoppingCart.__init__
#   --> ShoppingCart.add_item --> _validate_quantity --> _log_error
#                             --> _update_total --> _calculate_total
#   --> OrderProcessor.__init__
#   --> OrderProcessor.process_order
#         --> cart.checkout --> _validate_cart
#                           --> _process_payment --> _send_confirmation
#         --> _generate_order_id
#         --> _save_order --> _write_to_database
#         --> _notify_customer --> _send_email
#                              --> _send_sms
#
# Toplam Sinif: 3
# Toplam Metod: 19
# Toplam Fonksiyon: 1
# =============================================================================
