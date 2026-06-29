# MarketPulse — پلتفرم رصد بازارهای مالی

[![CI](https://github.com/mahan-vzmz/crypto-worldcup-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/mahan-vzmz/crypto-worldcup-platform/actions/workflows/ci.yml)

پلتفرم جامع، real-time و تمام‌async برای رصد قیمت لحظه‌ای بازارهای مالی — رمزارز، ارزهای فیات، فلزات گرانبها، بورس جهانی و بورس ایران — با وب داشبورد، بات تلگرام و CLI.

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
  - 🇮🇷 بورس ایران — شستا، فولاد، فملی، خودرو، سایپا و بیشتر از TSETMC CDN API
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
                /    |    |     \
  CryptoClient  FiatClient  BourseClient  IranBourseClient
   (Wallex)   (ExchangeRate)  (Yahoo)    (TSETMC CDN)
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

> **Claude Code on the web:** محیط را ویرایش کنید، **Network access** را روی
> **Custom** بگذارید و این دامنه‌ها را در **Allowed domains** اضافه کنید
> (یا سطح **Full** را انتخاب کنید). سپس یک سشن جدید باز کنید.
> راهنما: <https://code.claude.com/docs/en/claude-code-on-the-web#allow-specific-domains>
>
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

---

## اجرای محلی

```bash
crypto-wc          # CLI تعاملی
crypto-wc-api      # وب داشبورد (http://127.0.0.1:8000)
crypto-wc-bot      # بات تلگرام (نیاز به TELEGRAM_BOT_TOKEN)
```

---

## توسعه و تست

```bash
ruff check .     # lint
ruff format .    # format
mypy src         # بررسی نوع (strict)
pytest           # اجرای تست‌ها
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
  clients/             # httpx adapters: Wallex, FiatClient, Yahoo, TSETMC
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
