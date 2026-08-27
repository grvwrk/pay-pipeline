import uuid
from typing import List, Optional, Dict, Any
from backend.app.models.catalog import Product, ProductFilter
from backend.app.models.cart import BundleOffer, Cart, CartItem
from backend.app.database.repositories import product_repo, cart_repo, order_repo, payment_repo
from backend.app.tools.discount_engine import discount_engine
from backend.app.tools.dispatcher import tool_dispatcher, ToolRiskLevel


class ReadAndDecisionTools:
    """
    Read & Decision Tools (Class A - Low to Medium Risk).
    Provides structured, authoritative catalog, inventory, pricing,
    cart operations, and discount computation. Connected directly to SQLite persistence.
    """

    @property
    def catalog(self) -> List[Product]:
        return product_repo.get_all()

    def reload_catalog(self):
        pass

    def catalog_lookup(self, filter_params: ProductFilter) -> List[Product]:
        return product_repo.filter_products(filter_params)

    def search_products(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        max_price: Optional[float] = None,
        in_stock_only: bool = True
    ) -> List[Product]:
        return product_repo.filter_products(ProductFilter(
            query=query,
            category=category,
            max_price=max_price,
            in_stock_only=in_stock_only
        ))

    def get_product(self, product_id: str) -> Optional[Product]:
        return product_repo.get_by_id(product_id)

    def get_inventory(self, product_id: str) -> int:
        p = product_repo.get_by_id(product_id)
        return p.inventory if p else 0

    def get_price(self, product_id: str) -> Optional[float]:
        p = product_repo.get_by_id(product_id)
        return p.price if p else None

    def build_cart(
        self, 
        user_id: str, 
        items: List[Dict[str, Any]], 
        promo_code: Optional[str] = None,
        include_bundle: bool = False
    ) -> Cart:
        if not user_id:
            raise ValueError("user_id is required to build a cart.")

        cart_id = f"cart_{uuid.uuid4().hex[:12]}"
        cart = Cart(cart_id=cart_id, user_id=user_id)

        should_include_bundle = include_bundle

        for item_data in items:
            prod_id = item_data.get("product_id") or item_data.get("id") or item_data.get("sku")
            qty = int(item_data.get("quantity", 1))
            
            if item_data.get("include_bundle"):
                should_include_bundle = True

            prod = self.get_product(prod_id)
            if prod:
                cart.items.append(CartItem(
                    product_id=prod.id,
                    name=prod.name,
                    price=prod.price,
                    quantity=qty,
                    subtotal=prod.price * qty,
                    category=prod.category
                ))

        if len(cart.items) == 1 and should_include_bundle:
            bundle = self.calculate_upsell_bundle(cart.items[0].product_id)
            if bundle:
                companion = self.get_product(bundle.complementary_product_id)
                if companion:
                    cart.items.append(CartItem(
                        product_id=companion.id,
                        name=companion.name,
                        price=companion.price,
                        quantity=1,
                        subtotal=companion.price,
                        category=companion.category
                    ))
                    cart.applied_bundle = bundle

        return self.calculate_cart_total(cart, promo_code=promo_code)

    def add_to_cart(self, cart_id: str, product_id: str, quantity: int = 1, user_id: Optional[str] = None) -> Cart:
        cart = cart_repo.get_cart(cart_id)
        if not cart:
            if not user_id:
                raise ValueError("user_id required to initialize a new cart.")
            cart = Cart(cart_id=cart_id, user_id=user_id)

        prod = self.get_product(product_id)
        if not prod:
            raise ValueError(f"Product '{product_id}' not found in catalog")

        existing = next((i for i in cart.items if i.product_id == product_id), None)
        if existing:
            existing.quantity += quantity
            existing.subtotal = existing.price * existing.quantity
        else:
            cart.items.append(CartItem(
                product_id=prod.id,
                name=prod.name,
                price=prod.price,
                quantity=quantity,
                subtotal=prod.price * quantity,
                category=prod.category
            ))

        return self.calculate_cart_total(cart)

    def remove_from_cart(self, cart_id: str, product_id: str) -> Cart:
        cart = cart_repo.get_cart(cart_id)
        if not cart:
            raise ValueError(f"Cart '{cart_id}' not found")

        cart.items = [i for i in cart.items if i.product_id != product_id]
        
        if cart.applied_bundle:
            bundle_prod_ids = {cart.applied_bundle.primary_product_id, cart.applied_bundle.complementary_product_id}
            cart_prod_ids = {i.product_id for i in cart.items}
            if not bundle_prod_ids.issubset(cart_prod_ids):
                cart.applied_bundle = None

        return self.calculate_cart_total(cart)

    def calculate_cart_total(self, cart: Cart, promo_code: Optional[str] = None) -> Cart:
        cart.subtotal_amount = sum(i.subtotal for i in cart.items)
        calc = discount_engine.calculate_discount(
            subtotal=cart.subtotal_amount, 
            bundle=cart.applied_bundle, 
            promo_code=promo_code
        )
        cart.discount_amount = calc.final_discount
        cart.total_amount = calc.final_total
        return cart_repo.save_cart(cart)

    def calculate_discount(self, subtotal: float, bundle_id: Optional[str] = None, promo_code: Optional[str] = None) -> Dict[str, Any]:
        bundle = self.calculate_upsell_bundle(bundle_id) if bundle_id else None
        calc = discount_engine.calculate_discount(subtotal, bundle=bundle, promo_code=promo_code)
        return calc.model_dump()

    def calculate_upsell_bundle(self, primary_product_id: str) -> Optional[BundleOffer]:
        primary = self.get_product(primary_product_id)
        if not primary or not primary.complementary_product_ids:
            return None

        comp_id = primary.complementary_product_ids[0]
        comp = self.get_product(comp_id)
        if not comp:
            return None

        bundle_subtotal = primary.price + comp.price
        discount_rate = discount_engine.BUNDLE_DISCOUNT_RATE
        discount_amount = round(comp.price * discount_rate, 2)
        bundle_total = round(bundle_subtotal - discount_amount, 2)

        return BundleOffer(
            primary_product_id=primary.id,
            primary_product_name=primary.name,
            complementary_product_id=comp.id,
            complementary_product_name=comp.name,
            original_combined_price=bundle_subtotal,
            discounted_bundle_price=bundle_total,
            savings_amount=discount_amount,
            discount_percentage=discount_rate * 100.0,
            rationale=f"Pairing {primary.name} with {comp.name} unlocks an authorized {discount_rate * 100:.0f}% accessory bundle discount."
        )

    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        order = order_repo.get_order(order_id)
        return order.model_dump() if order else None

    def get_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        payment = payment_repo.get_payment(payment_id)
        return payment.model_dump() if payment else None


read_tools = ReadAndDecisionTools()

# Register read tools with ToolDispatcher
tool_dispatcher.register_tool("search_products", "Search in-stock product catalog", ToolRiskLevel.LOW, read_tools.search_products)
tool_dispatcher.register_tool("get_product", "Get single product by SKU ID", ToolRiskLevel.LOW, read_tools.get_product)
tool_dispatcher.register_tool("get_inventory", "Get real-time inventory for SKU", ToolRiskLevel.LOW, read_tools.get_inventory)
tool_dispatcher.register_tool("get_price", "Get authoritative price for SKU", ToolRiskLevel.LOW, read_tools.get_price)
tool_dispatcher.register_tool("build_cart", "Build and price a shopping cart", ToolRiskLevel.MEDIUM, read_tools.build_cart)
tool_dispatcher.register_tool("add_to_cart", "Add item SKU to cart", ToolRiskLevel.MEDIUM, read_tools.add_to_cart)
tool_dispatcher.register_tool("remove_from_cart", "Remove item SKU from cart", ToolRiskLevel.MEDIUM, read_tools.remove_from_cart)
tool_dispatcher.register_tool("calculate_discount", "Calculate server-side discount", ToolRiskLevel.LOW, read_tools.calculate_discount)
tool_dispatcher.register_tool("calculate_upsell_bundle", "Compute dynamic accessory bundle offer", ToolRiskLevel.LOW, read_tools.calculate_upsell_bundle)
tool_dispatcher.register_tool("get_order_status", "Retrieve order status by order ID", ToolRiskLevel.LOW, read_tools.get_order_status)
tool_dispatcher.register_tool("get_payment_status", "Retrieve payment status by payment ID", ToolRiskLevel.LOW, read_tools.get_payment_status)