# MarketPulse — پلتفرم رصد بازارهای مالی

[![CI](https://github.com/mahan-vzmz/crypto-worldcup-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/mahan-vzmz/crypto-worldcup-platform/actions/workflows/ci.yml)

پلتفرم تمام‌async برای رصد قیمت بازارهای مالی — رمزارز، ارزهای فیات، فلزات گرانبها و بورس جهانی — با وب داشبورد، بات تلگرام و CLI.

**Offline-first و anti-fragile:** هر فراخوانی خارجی با TTL کش می‌شود. اگر API در دسترس نباشد، آخرین داده‌ی معتبر سرو می‌شود — نه crash.

---

## ویژگی‌ها

- **وب داشبورد** — رابط کاربری مدرن با Glassmorphism، فیلترِ بازار، جستجو و بروزرسانی خودکار هر ۳۰ ثانیه (HTMX)
- **بات تلگرام** — دستورات `/market`، `/price` (+ مخفف `/p`)، `/watchlist`، inline query، و خلاصه‌ی صبحگاهی خودکار. **برای گروه‌ها بهینه شده**: پاسخ به منشن، ریپلای، متن آزاد فارسی/انگلیسی، و خوش‌آمد خودکار هنگام افزوده‌شدن به گروه. راهنما: [`docs/telegram-bot.md`](docs/telegram-bot.md)
- **بازارهای پشتیبانی شده:**
  - 🪙 رمزارزها — لیست جهانی از CoinGecko (لوگو، ارزش بازار، حجم، رتبه، نمودار ۷ روزه) با قیمت تومانی از Wallex
  - 💵 ارزهای فیات — EUR، GBP (محاسبه‌شده از نرخ USD/تومان Wallex)
  - 🥇 فلزات — XAUT (طلا tokenized)، PAXG از Wallex
  - 📈 بورس جهانی — NVDA، AAPL، MSFT، S&P 500، NASDAQ، Dow Jones از Yahoo Finance
- **TTL caching** — داده در DB ذخیره، درخواست‌های تکراری بدون شبکه پاسخ می‌گیرند
- **Offline fallback** — در صورت قطعی API، آخرین کش معتبر با هشدار سرو می‌شود

---

## معماری

```
[ وب داشبورد ]  [ بات تلگرام ]  [ CLI ]
       \                |             /
        [ FastAPI REST API (ASGI) ]
                        |
          [ لایه‌ی سرویس (CryptoService) ]
               /       |        |        \
 MarketDataClient CryptoClient FiatClient BourseClient
    (CoinGecko)      (Wallex)  (ExchangeRate) (Yahoo)
                        |
    [ SQLAlchemy (SQLite dev / PostgreSQL prod) ]

      ( Utils & Config — در دسترس همه لایه‌ها )
```

وابستگی‌ها **فقط یک‌طرفه** جریان دارند. سرویس‌ها به *abstractionها* وابسته‌اند، نه پیاده‌سازی‌های مشخص — این معماری مهاجرت بین پیاده‌سازی‌ها را بدون بازنویسی ممکن می‌کند.

---

## تکنولوژی‌ها

| حوزه | انتخاب |
| --- | --- |
| زبان | Python 3.12+ |
| همزمانی | `asyncio` |
| HTTP Client | `httpx` (async، session reuse، retry با backoff) |
| ذخیره‌سازی | `SQLAlchemy 2.0` async + `aiosqlite` (dev) / `asyncpg` (prod) |
| وب API | `FastAPI` + `Uvicorn` (ASGI) |
| قالب‌ها | `Jinja2` + `HTMX` + TradingView Widgets |
| بات | `python-telegram-bot` (async، job queue) |
| CLI | `rich` |
| Config | `python-dotenv` + متغیرهای محیطی |
| Container | `Docker` + `Docker Compose` |
| تست | `pytest` + `pytest-asyncio` |

---

## دسترسی شبکه برای داده‌ی زنده

برای دریافت قیمت واقعی، اپ باید به این هاست‌ها دسترسی خروجی (egress) داشته باشد:

| هاست | کاربرد |
| --- | --- |
| `api.coingecko.com` | لیست کریپتو، لوگو، ارزش بازار، حجم، نمودار ۷ روزه |
| `api.wallex.ir` | قیمت تومانی، نرخ USDT، فلزات، نام‌های فارسی |
| `api.exchangerate-api.com` | نرخ یورو/پوند |
| `query1.finance.yahoo.com` | سهام و شاخص‌های بورس جهانی |

> اگر دسترسی نباشد، اپ crash نمی‌کند: آخرین داده‌ی کش‌شده سرو می‌شود و در نبود
> کش، صفحه با پیام «داده‌ای یافت نشد» نمایش داده می‌شود.

---

## راه‌اندازی با Docker (توصیه‌شده)

```bash
# ۱. Clone
git clone <repo-url>
cd crypto-worldcup-platform

# ۲. ساخت فایل env
cp .env.example .env

# ۳. پر کردن متغیرها (حداقل TELEGRAM_BOT_TOKEN)
nano .env

# ۴. اجرا
docker-compose up -d --build
```

وب داشبورد: `http://localhost:8000`

---

## راه‌اندازی محلی (توسعه)

نیاز: Python 3.12+

```bash
# ۱. محیط مجازی
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac

# ۲. نصب وابستگی‌ها
pip install -e ".[dev]"

# ۳. فایل env
cp .env.example .env
```

### متغیرهای محیطی

| متغیر | اجباری | پیش‌فرض | کاربرد |
| --- | --- | --- | --- |
| `DATABASE_URL` | خیر | SQLite | رشته‌ی اتصال (e.g. `postgresql+asyncpg://...`) |
| `DATA_DIR` | خیر | `data` | ریشه‌ی logs، settings |
| `CACHE_TTL_SECONDS` | خیر | `300` | TTL کش به ثانیه |
| `TELEGRAM_BOT_TOKEN` | بله* | — | برای اجرای بات الزامیست |
| `CRYPTO_API_KEY` | خیر | — | کلید API Wallex (اختیاری، public endpoints رایگان هستند) |
| `COINGECKO_API_KEY` | خیر | — | کلید Demo کوین‌گکو (اختیاری، سقف rate-limit را بالا می‌برد) |

---

## اجرا و تست (گام‌به‌گام)

> نیاز: **Python 3.12** (روی 3.11 حتی نصب نمی‌شود). برای داده‌ی زنده، egress
> بخش «دسترسی شبکه» باید فعال باشد؛ در غیر این صورت کش/حالت خالی نمایش داده می‌شود.

### ۰. آماده‌سازی محیط (یک‌بار)
```bash
python3.12 -m venv .venv
source .venv/bin/activate        # ویندوز: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env             # برای بات: TELEGRAM_BOT_TOKEN را پر کنید
```

### ۱. اجرای تست‌ها و کنترل کیفیت
```bash
ruff check .            # lint — انتظار: All checks passed!
ruff format --check .   # فرمت — انتظار: ... files already formatted
mypy --strict src       # نوع — انتظار: Success: no issues found
pytest -q               # تست — انتظار: 64 passed
```

### ۲. تست وب داشبورد
```bash
crypto-wc-api           # اجرا روی http://127.0.0.1:8000
```
سپس در مرورگر `http://127.0.0.1:8000` را باز کنید. باید ببینید:
- لیست کوین با لوگو، قیمت دلاری/تومانی، تغییر ۲۴س، ارزش بازار، حجم و **نمودار ۷ روزه**
- جستجو و تب‌های بازار، و مرتب‌سازی با کلیک روی سرستون‌ها
- کلیک روی نام هر کوین → صفحه‌ی جزئیات `/coin/BTC` با نمودار TradingView و تاریخچه
- بدون egress: پیام «داده‌ای یافت نشد» (طبیعی است) — مستندات API روی `http://127.0.0.1:8000/docs`

تست سریع API بدون مرورگر:
```bash
curl -s http://127.0.0.1:8000/crypto/prices | head
```

### ۳. تست بات تلگرام
```bash
# ۱) از @BotFather توکن بگیرید و در .env بگذارید: TELEGRAM_BOT_TOKEN=...
crypto-wc-bot           # انتظار در لاگ: "Bot is polling for updates..."
```
بعد در تلگرام به بات پیام دهید:
- `/start` و `/help` → راهنما
- `/price btc` یا `/p eth` → کارت قیمت با دکمه‌ی واچ‌لیست
- `btc` یا «قیمت بیتکوین» (چت خصوصی) → پاسخ مستقیم
- بات را به یک گروه اضافه کنید → پیام خوش‌آمد؛ سپس `@YourBot بیتکوین` یا ریپلای
- inline: در هر چتی `@YourBot btc` را تایپ کنید
> راهنمای کامل گروه و تنظیمات BotFather: [`docs/telegram-bot.md`](docs/telegram-bot.md)

### ۴. اجرای CLI
```bash
crypto-wc               # منوی تعاملی در ترمینال
```

---

## ساختار پروژه

```
src/app/
  main.py              # composition root: wire + start CLI
  api/                 # FastAPI routers, dependencies, lifespan
  bot/                 # handlers, inline query, jobs, formatters
  config/              # Settings (frozen dataclass, env-driven) + DI Container
  models/              # CryptoPrice dataclass + AssetType enum
  services/            # CryptoService: cache-then-fetch + offline fallback
  clients/             # httpx adapters: CoinGecko, Wallex, ExchangeRate, Yahoo
  storage/             # SQLAlchemy repository (SQLite/PostgreSQL)
  presentation/        # rich CLI renderers + menu
  templates/           # Jinja2 HTML templates
  static/              # CSS + JS
tests/                 # pytest suite (no live API, no real DB)
docs/                  # معماری، تصمیم‌ها، نقشه‌ی راه
```

---

## مجوز

MIT — نگاه کنید به [`LICENSE`](LICENSE).
