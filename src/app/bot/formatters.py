"""Formatters for Telegram messages using HTML parse mode."""

import html
from collections.abc import Sequence

from app.models.crypto import CryptoPrice


def format_prices(prices: Sequence[CryptoPrice], title: str = "قیمت‌های بازار") -> str:
    """Format a list of prices into an HTML message."""
    if not prices:
        return f"<b>{html.escape(title)}</b>\n\nاطلاعاتی موجود نیست."

    lines = [f"📊 <b>{html.escape(title)}</b>\n"]
    for p in prices:
        symbol = html.escape(p.symbol)
        name = html.escape(p.name)

        # Handle small numbers gracefully (like SHIB)
        usd = f"${p.price_usd:,.4f}" if p.price_usd < 1 else f"${p.price_usd:,.2f}"
        toman = f"{p.price_toman:,.0f} تومان"

        change = p.change_24h
        if change > 0:
            trend = f"🟢 +{change:.2f}%"
        elif change < 0:
            trend = f"🔴 {change:.2f}%"
        else:
            trend = "⚪ 0.00%"

        if p.price_toman > 0:
            lines.append(f"🔹 <b>{symbol}</b> ({name})\n💵 {usd} | 🇮🇷 {toman}\n📈 تغییر (۲۴ساعت): {trend}\n")
        else:
            lines.append(f"🔹 <b>{symbol}</b> ({name})\n💵 {usd}\n📈 تغییر (۲۴ساعت): {trend}\n")

    lines.append("\n<i>نمایش برترین نتایج. برای سایر دارایی‌ها از /price &lt;نماد&gt; استفاده کنید.</i>")

    return "\n".join(lines)
