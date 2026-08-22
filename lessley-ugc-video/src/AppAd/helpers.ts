// Mirrors formatAmount() in lessley-frontend/src/lib/formatters.ts so the
// mockups show money exactly the way the real app does.
const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "ILS",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export const ils = (value: number) => currencyFormatter.format(value);

const wholeFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "ILS",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

export const ilsWhole = (value: number) => wholeFormatter.format(Math.round(value));

/** Reveals `text` one character at a time, starting at `startFrame`. */
export const typed = (
  text: string,
  frame: number,
  startFrame: number,
  charsPerFrame: number,
) => {
  const revealed = Math.floor((frame - startFrame) * charsPerFrame);
  if (revealed <= 0) return "";
  return text.slice(0, Math.min(text.length, revealed));
};
