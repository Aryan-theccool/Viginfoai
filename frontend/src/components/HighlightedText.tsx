import { useMemo } from "react";

/** Renders source text with the AI's exact quote visually highlighted. */
export function HighlightedText({ text, quote }: { text: string; quote: string }) {
  const parts = useMemo(() => {
    if (!quote || !text.includes(quote)) return [{ t: text, hl: false }];
    const idx = text.indexOf(quote);
    return [
      { t: text.slice(0, idx), hl: false },
      { t: quote, hl: true },
      { t: text.slice(idx + quote.length), hl: false },
    ];
  }, [text, quote]);

  return (
    <p className="whitespace-pre-wrap leading-relaxed text-[15px] text-slate-800">
      {parts.map((p, i) =>
        p.hl ? (
          <mark key={i} className="vig-highlight">
            {p.t}
          </mark>
        ) : (
          <span key={i}>{p.t}</span>
        )
      )}
    </p>
  );
}
