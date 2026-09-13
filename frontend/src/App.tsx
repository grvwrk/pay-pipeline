import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useAsync } from "./lib/useAsync";
import { api } from "./lib/api";
import { useSession } from "./state/session";
import { Badge } from "./components/ui";

import Chat from "./pages/Chat";
import Catalog from "./pages/Catalog";
import CartPage from "./pages/Cart";
import Orders from "./pages/Orders";
import Guardrails from "./pages/Guardrails";
import Audit from "./pages/Audit";
import Merchant from "./pages/Merchant";
import Scenarios from "./pages/Scenarios";

const NAV = [
  { to: "/chat", label: "Agent console", group: "Buyer" },
  { to: "/catalog", label: "Catalog", group: "Buyer" },
  { to: "/cart", label: "Cart & checkout", group: "Buyer" },
  { to: "/orders", label: "Orders & refunds", group: "Buyer" },
  { to: "/guardrails", label: "Guardrails", group: "Trusted layer" },
  { to: "/audit", label: "Audit chain", group: "Trusted layer" },
  { to: "/merchant", label: "Merchant growth", group: "Merchant" },
  { to: "/scenarios", label: "Demo scenarios", group: "Merchant" },
];

function Sidebar() {
  const { userId, setUserId, cart } = useSession();
  const { data: health } = useAsync(() => api.health(), []);
  const groups = [...new Set(NAV.map((n) => n.group))];

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-ink-800 bg-ink-900">
      <div className="border-b border-ink-800 px-5 py-5">
        <h1 className="text-sm font-semibold tracking-tight">pay-pipeline</h1>
        <p className="mt-1 text-xs leading-relaxed text-ink-400">
          Agentic commerce with a deterministic policy diode.
        </p>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {groups.map((group) => (
          <div key={group} className="mb-5">
            <p className="label px-2 pb-2">{group}</p>
            <ul className="space-y-0.5">
              {NAV.filter((n) => n.group === group).map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    className={({ isActive }) =>
                      `flex items-center justify-between rounded-lg px-2.5 py-2 text-sm transition-colors ${
                        isActive
                          ? "bg-ink-800 text-ink-100"
                          : "text-ink-300 hover:bg-ink-850 hover:text-ink-100"
                      }`
                    }
                  >
                    {item.label}
                    {item.to === "/cart" && cart && cart.items.length > 0 && (
                      <span className="mono rounded bg-ink-700 px-1.5 py-0.5 text-ink-100">
                        {cart.items.length}
                      </span>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="space-y-3 border-t border-ink-800 px-4 py-4">
        <div>
          <label className="label" htmlFor="buyer-id">Acting as</label>
          <input
            id="buyer-id"
            className="field mono mt-1.5"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            spellCheck={false}
          />
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {health ? (
            <>
              <Badge tone="good">api up</Badge>
              <Badge tone="neutral">{health.payment_mode}</Badge>
              <Badge tone="neutral">{health.llm_provider}</Badge>
            </>
          ) : (
            <Badge tone="bad">api unreachable</Badge>
          )}
        </div>
      </div>
    </aside>
  );
}

export default function App() {
  return (
    <div className="flex h-full">
      <Sidebar />
      <main className="min-w-0 flex-1 overflow-y-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/guardrails" element={<Guardrails />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="/merchant" element={<Merchant />} />
          <Route path="/scenarios" element={<Scenarios />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </main>
    </div>
  );
}
