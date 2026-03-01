from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from core.config import Settings
from Websites.BaseScraper import BaseScraper


class HotScraper(BaseScraper):
    def __init__(self, settings: Settings):
        super().__init__(club_name="Hot", base_url="https://www.hot.co.il", settings=settings)
        self.api_url = "https://api.hot.co.il/api/website/2.0/getAllBenefits/"
        self.details_api_url = "https://api.hot.co.il/api/website/2.0/getDetailedBenefitByIdForWeb/"

    async def initialize_session(self) -> None:
        print(f"[{self.club_name}] Initializing session and XSRF token...")
        self.client.headers.update(
            {
                "origin": self.base_url,
                "referer": f"{self.base_url}/",
            }
        )
        await self.client.get(self.base_url)
        token = self.client.cookies.get("XSRF-TOKEN")
        if not token:
            for cookie in self.client.cookies.jar:
                if cookie.name.lower() in {"xsrf-token", "csrf-token"}:
                    token = cookie.value
                    break

        if token:
            self.client.headers.update(
                {
                    "x-xsrf-token": token,
                }
            )
            print(f"[{self.club_name}] XSRF token acquired.")
        else:
            # HOT detail endpoint may still require an x-xsrf-token header even
            # when the cookie is absent. Browser traffic commonly sends "1".
            self.client.headers.update({"x-xsrf-token": "1"})
            print(
                f"[{self.club_name}] No XSRF cookie detected. "
                "Continuing without token (endpoint usually works without it)."
            )

    async def fetch_benefits(self, page_num: int) -> dict[str, Any] | None:
        payload = {
            "radius": "0",
            "page": str(page_num),
            "platform": "web",
            "size": "50",
        }

        try:
            response = await self.client.post(self.api_url, data=payload)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            print(f"[{self.club_name}] Error fetching page {page_num}: {exc}")
            return None

    async def fetch_benefit_details(
        self, benefit_id: int | str, is_commerce: int | str = 0
    ) -> dict[str, Any] | None:
        payload = {
            "benefitId": str(benefit_id),
            "isCommerce": str(is_commerce),
        }

        try:
            response = await self.client.post(
                self.details_api_url,
                # Browser sends multipart/form-data for this endpoint.
                files={k: (None, v) for k, v in payload.items()},
                headers={"accept": "application/json, text/plain, */*"},
            )
            body: dict[str, Any]
            try:
                body = response.json()
            except Exception:
                body = {"raw_body": response.text}

            if response.status_code >= 400:
                return {
                    "http_status": response.status_code,
                    "request_payload": payload,
                    "response": body,
                }

            return body
        except Exception as exc:
            print(f"[{self.club_name}] Error fetching details for benefitId={benefit_id}: {exc}")
            return None

    async def iter_offers(self) -> AsyncIterator[dict[str, Any]]:
        for page_num in range(self.settings.page_start, self.settings.page_start + self.settings.max_pages):
            data = await self.fetch_benefits(page_num)
            if not data:
                break

            records = data.get("data", {}).get("records", [])
            if not records:
                print(f"[{self.club_name}] No more records after page {page_num}.")
                break

            for record in records:
                yield record

            await self.throttle()

    def normalize_item(self, record: dict[str, Any]) -> dict[str, Any]:
        external_id = str(record.get("id") or "")
        source = self.club_name.lower()
        benefit_type = self._normalize_benefit_type(record)
        value = self._normalize_value(record)
        categories = self._normalize_categories(record)
        images = self._normalize_images(record)
        pricing = self._normalize_pricing(record)
        expiry_date = self._normalize_expiry_date(record)
        is_expired = self._is_expired(expiry_date)
        redemption_url = self._normalize_redemption_url(record, external_id)
        generic_id = f"{source}:{external_id}" if external_id else f"{source}:{record.get('slug') or ''}"

        item: dict[str, Any] = {
            # GenericBenefit schema
            "id": generic_id,
            "externalId": external_id,
            "source": source,
            "title": record.get("title") or record.get("item_name") or "",
            "brandName": record.get("item_brand") or record.get("brand_name") or "",
            "description": record.get("description") or "",
            "shortDescription": record.get("small_text") or "",
            "category": categories,
            "benefitType": benefit_type,
            "value": value,
            "images": images,
            "expiryDate": expiry_date,
            "redemptionUrl": redemption_url,
            "isActive": bool(record.get("is_active", True)),
            "isExpired": is_expired,
            "updatedAt": self._utc_now_iso(),
            "rawSourceData": record,
            # Backward-compatible fields currently used in the pipeline/repository
            "source_club": self.club_name,
            "external_id": external_id,
            "business_name": record.get("item_brand"),
            "category_legacy": record.get("item_category"),
            "benefit_value": record.get("value"),
            "benefit_type": record.get("small_text"),
            "link": f"{self.base_url}/benefit/{external_id}" if external_id else None,
            "raw": record,
            "scraped_at": self._utc_now_iso(),
        }

        logo_url = record.get("logo") or record.get("logo_url")
        if isinstance(logo_url, str) and logo_url.strip():
            item["logoUrl"] = self._to_absolute_url(logo_url.strip())

        locations = self._normalize_locations(record)
        if locations:
            item["locations"] = locations

        if pricing:
            item["pricing"] = pricing

        return item

    def normalize_offer(self, record: dict[str, Any]) -> dict[str, Any]:
        return self.normalize_item(record)

    def _normalize_categories(self, record: dict[str, Any]) -> list[str]:
        raw_categories = record.get("item_category") or record.get("category") or record.get("categories")
        if isinstance(raw_categories, str):
            parts = [p.strip() for p in re.split(r"[>|/,]", raw_categories) if p.strip()]
            return parts
        if isinstance(raw_categories, list):
            return [str(c).strip() for c in raw_categories if str(c).strip()]
        return []

    def _normalize_benefit_type(self, record: dict[str, Any]) -> str:
        text = " ".join(
            str(v or "")
            for v in (
                record.get("small_text"),
                record.get("value"),
                record.get("title"),
                record.get("description"),
            )
        ).lower()
        if any(token in text for token in ("cashback", "money back", "refund")):
            return "cashback"
        if any(token in text for token in ("voucher", "gift card", "giftcard")):
            return "voucher"
        if any(token in text for token in ("coupon", "promo code", "code")):
            return "coupon"
        return "discount_at_billing"

    def _normalize_value(self, record: dict[str, Any]) -> dict[str, Any]:
        raw_value = str(record.get("value") or record.get("small_text") or "").strip()
        percentage_match = re.search(r"(\d+(?:\.\d+)?)\s*%", raw_value)
        if percentage_match:
            return {
                "type": "percentage",
                "amount": float(percentage_match.group(1)),
                "displayValue": raw_value,
            }
        numeric_match = re.search(r"(\d+(?:\.\d+)?)", raw_value.replace(",", ""))
        if numeric_match:
            return {
                "type": "fixed",
                "amount": float(numeric_match.group(1)),
                "displayValue": raw_value,
            }
        return {
            "type": "text",
            "amount": None,
            "displayValue": raw_value,
        }

    def _normalize_pricing(self, record: dict[str, Any]) -> dict[str, Any] | None:
        original_price = self._to_float(
            record.get("original_price") or record.get("originalPrice") or record.get("price_before")
        )
        discounted_price = self._to_float(
            record.get("discounted_price") or record.get("discountedPrice") or record.get("price_after")
        )
        if original_price is None and discounted_price is None:
            return None
        return {
            "originalPrice": original_price,
            "discountedPrice": discounted_price,
            "currency": str(record.get("currency") or "ILS"),
        }

    def _normalize_images(self, record: dict[str, Any]) -> list[str]:
        candidates = []
        for key in ("images", "gallery", "item_images", "image", "item_image", "picture", "thumbnail"):
            value = record.get(key)
            if isinstance(value, str):
                candidates.append(value)
            elif isinstance(value, list):
                candidates.extend(str(v) for v in value if isinstance(v, (str, int, float)))
        seen: set[str] = set()
        images: list[str] = []
        for candidate in candidates:
            normalized = self._to_absolute_url(str(candidate).strip())
            if normalized and normalized not in seen:
                seen.add(normalized)
                images.append(normalized)
        return images

    def _normalize_expiry_date(self, record: dict[str, Any]) -> str | None:
        for key in ("expiry_date", "expiryDate", "valid_to", "validUntil", "end_date", "date_to"):
            raw = record.get(key)
            if raw is None:
                continue
            if isinstance(raw, (int, float)) and raw > 0:
                try:
                    return datetime.fromtimestamp(float(raw), tz=timezone.utc).isoformat()
                except Exception:
                    continue
            if isinstance(raw, str):
                parsed = self._parse_date_text(raw.strip())
                if parsed:
                    return parsed
        return None

    def _normalize_redemption_url(self, record: dict[str, Any], external_id: str) -> str | None:
        for key in ("redemption_url", "redeem_url", "benefit_url", "url", "link", "website"):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return self._to_absolute_url(value.strip())
        return f"{self.base_url}/benefit/{external_id}" if external_id else None

    def _normalize_locations(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        raw_locations = record.get("locations") or record.get("branches")
        if not isinstance(raw_locations, list):
            return []
        normalized: list[dict[str, Any]] = []
        for location in raw_locations:
            if not isinstance(location, dict):
                continue
            city = str(location.get("city") or "").strip()
            address = str(location.get("address") or location.get("street") or "").strip()
            if not city and not address:
                continue
            item: dict[str, Any] = {"city": city, "address": address}
            lat = self._to_float(location.get("lat") or location.get("latitude"))
            lng = self._to_float(location.get("lng") or location.get("longitude"))
            if lat is not None:
                item["lat"] = lat
            if lng is not None:
                item["lng"] = lng
            phone = location.get("phone")
            if isinstance(phone, str) and phone.strip():
                item["phone"] = phone.strip()
            normalized.append(item)
        return normalized

    def _is_expired(self, expiry_date: str | None) -> bool:
        if not expiry_date:
            return False
        try:
            parsed = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed < datetime.now(timezone.utc)
        except Exception:
            return False

    def _parse_date_text(self, value: str) -> str | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.isoformat()
        except Exception:
            pass
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
                return parsed.isoformat()
            except Exception:
                continue
        return None

    def _to_absolute_url(self, url: str) -> str:
        if not url:
            return ""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("/"):
            return f"{self.base_url}{url}"
        return f"{self.base_url}/{url}"

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        try:
            return float(text)
        except Exception:
            return None

