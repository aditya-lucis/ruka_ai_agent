# -*- coding: utf-8 -*-
"""RUKA Ambient Sensors — Temporal, Geolocation, Weather & Currency Real-Time Engine.

Menyediakan persepsi real-time bagi nalar kognisi Ruka:
1. Temporal Awareness: Hari, tanggal, jam, menit, zona waktu lokal (WIB/WITA/WIT).
2. Geolocation Awareness: GPS koordinat (lat, lon), kota, provinsi, negara via IP geolocation.
3. Weather Awareness: Suhu, kondisi cuaca, kelembaban, angin real-time via wttr.in/Open-Meteo.
4. Currency Rates: Kurs valas terkini (USD, EUR, SGD, JPY, GBP, MYR ke IDR) via live exchange rates.
"""
from __future__ import annotations

import datetime
import json
import logging
import time
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger("ruka.tools.ambient_sensors")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 RukaCompanion/1.0"
    ),
    "Accept": "application/json, text/plain, */*",
}

_HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
_BULAN_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

# Cache in-memory sederhana untuk menghemat latency dan bandwith
_geo_cache: dict[str, Any] = {"data": None, "ts": 0.0}
_rate_cache: dict[str, Any] = {"data": None, "ts": 0.0}
_weather_cache: dict[str, Any] = {}


def get_current_time() -> dict[str, Any]:
    """Mendapatkan informasi waktu lokal real-time presisi tinggi."""
    now = datetime.datetime.now().astimezone()
    hari = _HARI_ID[now.weekday()]
    bulan = _BULAN_ID[now.month - 1]
    tz_name = now.tzname() or "WIB"
    
    # Deteksi periode waktu (pagi, siang, sore, malam)
    jam = now.hour
    if 4 <= jam < 11:
        periode = "Pagi"
    elif 11 <= jam < 15:
        periode = "Siang"
    elif 15 <= jam < 18:
        periode = "Sore"
    else:
        periode = "Malam"

    date_str = f"{now.day} {bulan} {now.year}"
    formatted = f"{hari}, {date_str} | Pukul {now.strftime('%H:%M:%S')} {tz_name}"
    return {
        "formatted": formatted,
        "day_name": hari,
        "day": now.day,
        "month_name": bulan,
        "month": now.month,
        "year": now.year,
        "date": date_str,
        "time": now.strftime("%H:%M:%S"),
        "timezone": tz_name,
        "timezone_name": tz_name,
        "period": periode.lower(),
        "greeting_period": periode,
        "timestamp": now.timestamp(),
        "iso_timestamp": now.isoformat(),
        "greeting_suggestion": f"Selamat {periode.lower()}, Young Lord",
    }


def get_geolocation(force_refresh: bool = False, timeout: float = 4.0) -> dict[str, Any]:
    """Mendapatkan estimasi lokasi GPS (lat, lon, kota, negara) pengguna saat ini."""
    global _geo_cache
    now_t = time.time()
    if not force_refresh and _geo_cache["data"] and (now_t - _geo_cache["ts"] < 600.0):
        return _geo_cache["data"]

    # 1. Coba ipwho.is (sangat akurat di Indonesia)
    try:
        req = urllib.request.Request("https://ipwho.is/", headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            if d.get("success", True):
                res = {
                    "status": "success",
                    "city": d.get("city", "Jakarta"),
                    "region": d.get("region", "DKI Jakarta"),
                    "country": d.get("country", "Indonesia"),
                    "country_code": d.get("country_code", "ID"),
                    "latitude": d.get("latitude", -6.2088),
                    "longitude": d.get("longitude", 106.8456),
                    "timezone": d.get("timezone", {}).get("id", "Asia/Jakarta"),
                    "isp": d.get("connection", {}).get("isp", ""),
                    "source": "ipwho.is",
                }
                _geo_cache = {"data": res, "ts": now_t}
                return res
    except Exception as e:
        logger.warning(f"ipwho.is error: {e}")

    # 2. Fallback ipinfo.io
    try:
        req = urllib.request.Request("https://ipinfo.io/json", headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            loc = d.get("loc", "-6.2088,106.8456").split(",")
            res = {
                "status": "success",
                "city": d.get("city", "Jakarta"),
                "region": d.get("region", "DKI Jakarta"),
                "country": d.get("country", "Indonesia"),
                "country_code": d.get("country", "ID"),
                "latitude": float(loc[0]),
                "longitude": float(loc[1]),
                "timezone": d.get("timezone", "Asia/Jakarta"),
                "isp": d.get("org", ""),
                "source": "ipinfo.io",
            }
            _geo_cache = {"data": res, "ts": now_t}
            return res
    except Exception as e:
        logger.warning(f"ipinfo.io error: {e}")

    # 3. Default fallback aman
    fallback = {
        "status": "fallback",
        "city": "Jakarta",
        "region": "DKI Jakarta",
        "country": "Indonesia",
        "country_code": "ID",
        "latitude": -6.2088,
        "longitude": 106.8456,
        "timezone": "Asia/Jakarta",
        "isp": "Local Network",
        "source": "default_fallback",
    }
    _geo_cache = {"data": fallback, "ts": now_t}
    return fallback


def get_weather(location: str | None = None, timeout: float = 5.0) -> dict[str, Any]:
    """Mendapatkan cuaca real-time untuk lokasi tertentu atau lokasi GPS saat ini."""
    global _weather_cache
    geo = get_geolocation(timeout=timeout)
    target_loc = location.strip() if location and location.strip() else geo.get("city", "Jakarta")
    cache_key = target_loc.lower()
    now_t = time.time()

    if cache_key in _weather_cache and (now_t - _weather_cache[cache_key]["ts"] < 300.0):
        return _weather_cache[cache_key]["data"]

    encoded_loc = urllib.parse.quote(target_loc)
    url = f"https://wttr.in/{encoded_loc}?format=j1"
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            curr = d.get("current_condition", [{}])[0]
            nearest = d.get("nearest_area", [{}])[0]
            
            temp_c = curr.get("temp_C", "?")
            feels_c = curr.get("FeelsLikeC", temp_c)
            humidity = curr.get("humidity", "?")
            desc = curr.get("weatherDesc", [{}])[0].get("value", "Cerah/Normal")
            wind_kmh = curr.get("windspeedKmph", "?")
            precip_mm = curr.get("precipMM", "0.0")
            area_name = nearest.get("areaName", [{}])[0].get("value", target_loc)
            country = nearest.get("country", [{}])[0].get("value", "Indonesia")

            res = {
                "location": f"{area_name}, {country}",
                "temperature_c": float(temp_c) if temp_c.replace("-", "").isdigit() else temp_c,
                "feels_like_c": float(feels_c) if feels_c.replace("-", "").isdigit() else feels_c,
                "condition": desc,
                "humidity": humidity,
                "humidity_percent": f"{humidity}%",
                "wind_kmph": wind_kmh,
                "wind_speed": f"{wind_kmh} km/h",
                "precipitation_mm": f"{precip_mm} mm",
                "summary": f"Cuaca di {area_name}: {desc}, Suhu {temp_c}°C (terasa {feels_c}°C), Kelembaban {humidity}%, Angin {wind_kmh} km/h.",
            }
            _weather_cache[cache_key] = {"data": res, "ts": now_t}
            return res
    except Exception as e:
        logger.warning(f"wttr.in weather error ({e})")
        return {
            "location": target_loc,
            "temperature_c": 28.0,
            "feels_like_c": 30.0,
            "humidity": 65,
            "condition": "Informasi cuaca sementara tidak dapat dihubungi",
            "summary": f"Sensor cuaca lokal mendeteksi area {target_loc}, namun jaringan stasiun cuaca sedang sibuk ({e}).",
        }


def get_currency_rates(base: str = "USD", timeout: float = 5.0) -> dict[str, Any]:
    """Mendapatkan kurs valuta asing real-time terhadap Rupiah (IDR) dan mata uang utama dunia."""
    global _rate_cache
    now_t = time.time()
    clean_base = base.upper().strip() or "USD"

    if _rate_cache["data"] and (now_t - _rate_cache["ts"] < 300.0) and _rate_cache["data"].get("base") == clean_base:
        return _rate_cache["data"]

    url = f"https://open.er-api.com/v6/latest/{clean_base}"
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            rates = d.get("rates", {})
            idr_rate = rates.get("IDR", 1.0)
            
            # Konversi mata uang populer terhadap IDR
            major_pairs = {}
            for cur in ["USD", "EUR", "SGD", "JPY", "GBP", "AUD", "CNY", "MYR", "SAR", "IDR"]:
                if cur in rates and rates[cur] > 0:
                    val_in_idr = idr_rate / rates[cur]
                    major_pairs[cur] = round(val_in_idr, 2)

            res = {
                "base": clean_base,
                "base_currency": clean_base,
                "rates": major_pairs,
                "rates_to_idr": major_pairs,
                "last_update": d.get("time_last_update_utc", ""),
                "summary": (
                    f"Kurs Real-Time: 1 USD = Rp {major_pairs.get('USD', 0):,.2f} | "
                    f"1 EUR = Rp {major_pairs.get('EUR', 0):,.2f} | "
                    f"1 SGD = Rp {major_pairs.get('SGD', 0):,.2f} | "
                    f"1 JPY = Rp {major_pairs.get('JPY', 0):,.2f}"
                ),
            }
            _rate_cache = {"data": res, "ts": now_t}
            return res
    except Exception as e:
        logger.warning(f"open.er-api exchange error ({e})")
        return {
            "base": clean_base,
            "base_currency": clean_base,
            "rates": {"USD": 17880.0, "EUR": 20120.0, "SGD": 13970.0, "JPY": 113.0, "IDR": 1.0},
            "error": str(e),
            "summary": "Sensor kurs valuta asing sementara tidak dapat terhubung ke pasar keuangan global.",
        }

