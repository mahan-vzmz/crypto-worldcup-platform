import json
from datetime import UTC, datetime

import pytest

from app.storage.json_repository import JSONRepository
from app.utils.exceptions import StorageError


@pytest.fixture
def repo(tmp_path):
    """
    یک فیکسچر که برای هر تست یک ریپازیتوری کاملاً ایزوله
    در یک پوشه موقت می‌سازد.
    """
    return JSONRepository(tmp_path)


def test_save_and_load_roundtrip(repo):
    """تست ۱: ذخیره و بازیابی اطلاعات باید خروجی را در یک Envelope استاندارد برگرداند."""
    payload = {"coin": "BTC", "price": 65000.0}
    repo.save("crypto_btc", payload)

    result = repo.load("crypto_btc")
    assert result is not None
    assert result["data"] == payload
    assert result["schema_version"] == 1
    assert "fetched_at" in result


def test_load_missing_key_returns_none(repo):
    """تست ۲: فراخوانی کلیدی که وجود ندارد باید None برگرداند، نه ارور."""
    assert repo.load("missing_file") is None


def test_load_corrupted_file_raises_storage_error(repo, tmp_path):
    """تست ۳: اگر فایل JSON خراب باشد، باید StorageError بگیریم."""
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{bad_json: true, missing_quotes}")

    with pytest.raises(StorageError):
        repo.load("corrupt")


def test_load_wrong_schema_version_returns_none(repo, tmp_path):
    """تست ۴: فایلی که نسخه اسکیما (schema) آن در آینده است، باید به عنوان دیتای ناموجود (None) در نظر گرفته شود."""
    future_file = tmp_path / "future_schema.json"
    future_data = {
        "fetched_at": datetime.now(UTC).isoformat(),
        "schema_version": 99,  # نسخه ناشناخته
        "data": {"feature": "unknown"},
    }
    future_file.write_text(json.dumps(future_data))

    assert repo.load("future_schema") is None


def test_delete_twice_does_not_raise(repo):
    """تست ۵: پاک کردن فایلی که وجود ندارد (یا دو بار پاک کردن) نباید باعث کرش شود."""
    repo.save("delete_me", {"temp": "data"})
    assert repo.exists("delete_me") is True

    repo.delete("delete_me")
    assert repo.exists("delete_me") is False

    # اجرای مجدد نباید ارور بدهد
    repo.delete("delete_me")


def test_invalid_key_raises_storage_error(repo):
    """تست ۶: کلیدهای خطرناک (مثل مسیرهای برگشتی به بیرون پوشه) باید مسدود شوند."""
    with pytest.raises(StorageError):
        repo.save("../escape_directory", {"hack": "fail"})
