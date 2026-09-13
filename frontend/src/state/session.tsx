import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import type { Cart } from "../lib/types";

/**
 * Session state shared across pages: which buyer we act as, the server-side cart
 * we're building, and the approval token the policy engine last handed back.
 * The cart itself always lives on the backend; we only hold its id.
 */
interface SessionValue {
  userId: string;
  setUserId: (id: string) => void;
  cart: Cart | null;
  cartLoading: boolean;
  addToCart: (productId: string, quantity?: number, includeBundle?: boolean) => Promise<Cart>;
  removeFromCart: (productId: string) => Promise<void>;
  refreshCart: () => Promise<void>;
  clearCart: () => void;
  setCart: (cart: Cart | null) => void;
  approvalToken: string | null;
  setApprovalToken: (token: string | null) => void;
}

const SessionContext = createContext<SessionValue | null>(null);

const USER_KEY = "pp.user_id";
const CART_KEY = "pp.cart_id";

const read = (key: string) => {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
};
const write = (key: string, value: string | null) => {
  try {
    value === null ? localStorage.removeItem(key) : localStorage.setItem(key, value);
  } catch {
    /* private mode or blocked storage: session just won't survive a reload */
  }
};

export function SessionProvider({ children }: { children: ReactNode }) {
  const [userId, setUserIdState] = useState(() => read(USER_KEY) ?? "user_default_buyer");
  const [cart, setCart] = useState<Cart | null>(null);
  const [cartLoading, setCartLoading] = useState(false);
  const [approvalToken, setApprovalToken] = useState<string | null>(null);

  const setUserId = useCallback((id: string) => {
    setUserIdState(id);
    write(USER_KEY, id);
  }, []);

  // Re-attach to the cart from a previous visit, if the backend still has it.
  useEffect(() => {
    const cartId = read(CART_KEY);
    if (!cartId) return;
    let cancelled = false;
    api
      .getCart(cartId)
      .then((c) => !cancelled && setCart(c))
      .catch(() => write(CART_KEY, null));
    return () => {
      cancelled = true;
    };
  }, []);

  const addToCart = useCallback(
    async (productId: string, quantity = 1, includeBundle = false) => {
      setCartLoading(true);
      try {
        // No cart yet: create one server-side so discounts/bundles are priced by the backend.
        const next = cart
          ? await api.addCartItem(cart.cart_id, { product_id: productId, quantity })
          : await api.createCart({
              user_id: userId,
              items: [{ product_id: productId, quantity, include_bundle: includeBundle }],
            });
        setCart(next);
        write(CART_KEY, next.cart_id);
        return next;
      } finally {
        setCartLoading(false);
      }
    },
    [cart, userId],
  );

  const removeFromCart = useCallback(
    async (productId: string) => {
      if (!cart) return;
      setCartLoading(true);
      try {
        const next = await api.removeCartItem(cart.cart_id, productId);
        setCart(next);
      } finally {
        setCartLoading(false);
      }
    },
    [cart],
  );

  const refreshCart = useCallback(async () => {
    if (!cart) return;
    const next = await api.getCart(cart.cart_id).catch(() => null);
    setCart(next);
    if (!next) write(CART_KEY, null);
  }, [cart]);

  const clearCart = useCallback(() => {
    setCart(null);
    setApprovalToken(null);
    write(CART_KEY, null);
  }, []);

  const applyCart = useCallback((next: Cart | null) => {
    setCart(next);
    write(CART_KEY, next?.cart_id ?? null);
  }, []);

  const value = useMemo<SessionValue>(
    () => ({
      userId, setUserId, cart, cartLoading, addToCart, removeFromCart,
      refreshCart, clearCart, setCart: applyCart, approvalToken, setApprovalToken,
    }),
    [userId, setUserId, cart, cartLoading, addToCart, removeFromCart, refreshCart, clearCart, applyCart, approvalToken],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used inside <SessionProvider>");
  return ctx;
}
