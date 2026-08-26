import React from "react";
import { Product } from "../../types";
import { Star, Truck, ShoppingCart, CheckCircle2 } from "lucide-react";

interface ProductCardProps {
  product: Product;
  onBuy: (product: Product) => void;
  highlight?: boolean;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product, onBuy, highlight = false }) => {
  return (
    <div
      className={`rounded-xl border transition-all overflow-hidden flex flex-col justify-between ${
        highlight
          ? "bg-indigo-950/40 border-indigo-500/50 shadow-xl shadow-indigo-500/10"
          : "bg-slate-900/90 border-slate-800 hover:border-slate-700"
      }`}
    >
      <div>
        {product.image_url && (
          <div className="h-40 w-full overflow-hidden relative">
            <img
              src={product.image_url}
              alt={product.name}
              className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
            />
            <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-slate-950/80 backdrop-blur text-[11px] font-semibold text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" />
              {product.inventory} in stock
            </div>
          </div>
        )}

        <div className="p-4">
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              {product.category.replace("_", " ")}
            </span>
            <div className="flex items-center gap-1 text-xs text-amber-400 font-semibold">
              <Star className="h-3.5 w-3.5 fill-amber-400" />
              <span>{product.rating}</span>
              <span className="text-slate-500">({product.review_count})</span>
            </div>
          </div>

          <h3 className="font-semibold text-sm text-white line-clamp-2 mb-1.5">
            {product.name}
          </h3>

          <p className="text-xs text-slate-400 line-clamp-2 mb-3">
            {product.description}
          </p>

          {/* Specs tags */}
          <div className="flex flex-wrap gap-1 mb-3">
            {Object.entries(product.specs).slice(0, 2).map(([key, val]) => (
              <span key={key} className="text-[10px] px-1.5 py-0.5 bg-slate-800/80 text-slate-400 rounded">
                {String(val)}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="px-4 pb-4 pt-2 border-t border-slate-800/60 flex items-center justify-between">
        <div>
          <div className="text-xs text-slate-400">Price</div>
          <div className="text-base font-bold text-white">
            ₹{product.price.toLocaleString("en-IN")}
          </div>
        </div>

        <button
          onClick={() => onBuy(product)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition"
        >
          <ShoppingCart className="h-3.5 w-3.5" />
          Buy Now
        </button>
      </div>
    </div>
  );
};
