import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { money } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { Product } from "../lib/types";
import { useSession } from "../state/session";
import { PageHeader } from "../components/PageHeader";
import { Badge, Empty, ErrorNote, Panel, Spinner } from "../components/ui";

export default function Catalog() {
  const { addToCart, cartLoading } = useSession();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [inStockOnly, setInStockOnly] = useState(true);
  // Committed filters: the inputs only reach the API when the form is submitted.
  const [filters, setFilters] = useState({ query: "", category: "", max_price: "", in_stock_only: true });
  const [added, setAdded] = useState<string | null>(null);

  const { data, error, loading, reload } = useAsync(
    () =>
      api.listProducts({
        query: filters.query || undefined,
        category: filters.category || undefined,
        max_price: filters.max_price ? Number(filters.max_price) : undefined,
        in_stock_only: filters.in_stock_only,
      }),
    [filters],
  );

  const products = data ?? [];
  const categories = useMemo(() => [...new Set(products.map((p) => p.category))].sort(), [products]);

  async function add(product: Product) {
    await addToCart(product.id, 1);
    setAdded(product.id);
    setTimeout(() => setAdded((cur) => (cur === product.id ? null : cur)), 1600);
  }

  return (
    <div>
      <PageHeader
        title="Catalog"
        subtitle="Read-only discovery surface. Adding an item builds a server-side cart so pricing and bundle discounts stay authoritative."
        actions={<button className="btn-ghost" onClick={reload}>Refresh</button>}
      />

      <form
        className="flex flex-wrap items-end gap-3 border-b border-ink-800 px-8 py-5"
        onSubmit={(e) => {
          e.preventDefault();
          setFilters({ query, category, max_price: maxPrice, in_stock_only: inStockOnly });
        }}
      >
        <div className="min-w-56 flex-1">
          <label className="label" htmlFor="q">Search</label>
          <input id="q" className="field mt-1.5" placeholder="keyboard, headphones…" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <div className="w-56">
          <label className="label" htmlFor="cat">Category</label>
          <select id="cat" className="field mt-1.5" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
            ))}
          </select>
        </div>
        <div className="w-40">
          <label className="label" htmlFor="max">Max price</label>
          <input id="max" className="field mt-1.5" type="number" min={0} placeholder="5000" value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} />
        </div>
        <label className="flex h-[38px] cursor-pointer items-center gap-2 text-xs text-ink-300">
          <input type="checkbox" className="accent-flow" checked={inStockOnly} onChange={(e) => setInStockOnly(e.target.checked)} />
          In stock only
        </label>
        <button className="btn-primary h-[38px]" type="submit">Apply</button>
      </form>

      <div className="p-8">
        {loading && <Spinner label="Loading catalog…" />}
        {error && <ErrorNote error={error} onRetry={reload} />}
        {!loading && !error && products.length === 0 && (
          <Panel><Empty title="No products match these filters" hint="Widen the price ceiling or clear the search keyword." /></Panel>
        )}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {products.map((p) => (
            <article key={p.id} className="panel flex flex-col p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-sm font-semibold">{p.name}</h3>
                  <p className="mono mt-1 text-ink-400">{p.id}</p>
                </div>
                <Badge tone={p.inventory > 0 ? "good" : "bad"}>
                  {p.inventory > 0 ? `${p.inventory} in stock` : "out of stock"}
                </Badge>
              </div>

              {p.description && (
                <p className="mt-3 line-clamp-2 text-xs leading-relaxed text-ink-400">{p.description}</p>
              )}

              <dl className="mt-3 space-y-1">
                {Object.entries(p.specs).slice(0, 3).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-3 text-xs">
                    <dt className="text-ink-400">{k.replace(/_/g, " ")}</dt>
                    <dd className="truncate text-ink-300">{String(v)}</dd>
                  </div>
                ))}
              </dl>

              <div className="mt-4 flex flex-wrap gap-1.5">
                <Badge>{p.category.replace(/_/g, " ")}</Badge>
                <Badge>{p.rating}★ · {p.review_count}</Badge>
                <Badge>ships in {p.shipping_eta_hours}h</Badge>
              </div>

              <div className="mt-auto flex items-center justify-between gap-3 pt-5">
                <span className="text-lg font-semibold tabular-nums">{money(p.price)}</span>
                <button
                  className="btn-ghost text-xs"
                  disabled={p.inventory === 0 || cartLoading}
                  onClick={() => add(p)}
                >
                  {added === p.id ? "Added ✓" : "Add to cart"}
                </button>
              </div>
            </article>
          ))}
        </div>

        {products.length > 0 && (
          <p className="mt-6 text-xs text-ink-400">
            {products.length} product(s). Head to <Link className="text-flow hover:underline" to="/cart">cart and checkout</Link> to run them through the guardrails.
          </p>
        )}
      </div>
    </div>
  );
}
