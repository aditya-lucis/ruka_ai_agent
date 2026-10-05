# -*- coding: utf-8 -*-
"""Deterministic Text Normalizer (FR-EA-07).

Melakukan normalisasi teks di bawah 1 milidetik:
- Kapitalisasi kalimat awal.
- Deteksi kalimat tanya berdasarkan leksikon tanya Indonesia/Inggris dan pemberian tanda tanya (?).
- Inversi angka kata bahasa Indonesia ke angka digit (misal: 'dua puluh' -> '20').
"""
from __future__ import annotations

import re

QUESTION_WORDS = {
    "apa", "apakah", "siapa", "siapakah", "bagaimana", "bagaimanakah",
    "kenapa", "mengapa", "kapan", "kapankah", "di mana", "dimana", "ke mana",
    "kemana", "dari mana", "darimana", "berapa", "berapakah", "bisakah",
    "dapatkah", "adakah", "bolehkah",
    "what", "who", "where", "when", "why", "how", "can", "could", "would", "is", "are"
}

NUMBERS_MAP = {
    "nol": 0, "satu": 1, "dua": 2, "tiga": 3, "empat": 4,
    "lima": 5, "enam": 6, "tujuh": 7, "delapan": 8, "sembilan": 9,
    "sepuluh": 10, "sebelas": 11, "dua belas": 12, "tiga belas": 13,
    "empat belas": 14, "lima belas": 15, "enam belas": 16, "tujuh belas": 17,
    "delapan belas": 18, "sembilan belas": 19, "dua puluh": 20,
    "tiga puluh": 30, "empat puluh": 40, "lima puluh": 50,
    "seratus": 100, "seribu": 1000
}


def normalize_text(text: str) -> str:
    """Normalisasi cepat deterministik < 1 ms."""
    if not text or not text.strip():
        return ""

    cleaned = " ".join(text.strip().split())

    # 1. Inversi kata angka tunggal/majemuk sederhana
    words = cleaned.split()
    normalized_words = []
    i = 0
    while i < len(words):
        w_lower = words[i].lower()
        if i + 1 < len(words):
            two_words = f"{w_lower} {words[i+1].lower()}"
            if two_words in NUMBERS_MAP:
                normalized_words.append(str(NUMBERS_MAP[two_words]))
                i += 2
                continue
        if w_lower in NUMBERS_MAP:
            normalized_words.append(str(NUMBERS_MAP[w_lower]))
            i += 1
            continue
        normalized_words.append(words[i])
        i += 1

    result = " ".join(normalized_words)

    # 2. Kapitalisasi awal kalimat
    if result:
        result = result[0].upper() + result[1:]

    # 3. Deteksi pertanyaan
    first_word = result.split()[0].lower() if result else ""
    is_question = first_word in QUESTION_WORDS

    if is_question and not result.endswith(("?", "!", ".")):
        result += "?"
    elif not result.endswith(("?", "!", ".")):
        result += "."

    return result
