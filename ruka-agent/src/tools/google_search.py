# -*- coding: utf-8 -*-
"""RUKA — Google Search & Web Intelligence Engine (Zero-Cost & Robust).
Menyediakan kemampuan penelusuran Google langsung, Google News RSS,
serta ground facts terverifikasi untuk nalar kognisi Ruka.
"""
from __future__ import annotations

import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from typing import Any

from lxml import html

logger = logging.getLogger("ruka.tools.google_search")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id,en-US;q=0.9,en;q=0.8",
}


@dataclass
class SearchResultItem:
    title: str
    url: str
    snippet: str
    source: str = "Google Search"


class GoogleSearchEngine:
    """Mesin penelusuran web Google mandiri dengan multi-mode fallback:
    1. Google Web Search HTML parsing (lxml).
    2. Google News RSS feed (100% terstruktur & bebas blokir).
    """

    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    def search_news(self, query: str, max_results: int = 5) -> list[SearchResultItem]:
        """Menelusuri berita terkini via Google News RSS terstruktur."""
        encoded_q = urllib.parse.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=id&gl=ID&ceid=ID:id"
        req = urllib.request.Request(rss_url, headers=DEFAULT_HEADERS)
        items: list[SearchResultItem] = []

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item")[:max_results]:
                title = item.findtext("title") or ""
                link = item.findtext("link") or ""
                pub_date = item.findtext("pubDate") or ""
                desc = item.findtext("description") or ""
                # Bersihkan tag HTML sederhana dari deskripsi RSS
                try:
                    desc_text = html.fromstring(desc).text_content().strip()
                except Exception:
                    desc_text = desc.strip()
                snippet = f"[{pub_date}] {desc_text}" if pub_date else desc_text
                if title and link:
                    items.append(
                        SearchResultItem(
                            title=title.strip(),
                            url=link.strip(),
                            snippet=snippet[:300].strip(),
                            source="Google News",
                        )
                    )
        except Exception as e:
            logger.warning(f"Google News RSS gagal ({e})")

        return items

    def search_bing(self, query: str, max_results: int = 5) -> list[SearchResultItem]:
        """Menelusuri web via Bing Search (bebas blokir DNS/ISP di Indonesia)."""
        import base64
        encoded_q = urllib.parse.quote(query)
        url = f"https://www.bing.com/search?q={encoded_q}"
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        items: list[SearchResultItem] = []

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8", errors="ignore")

            tree = html.fromstring(content)
            for li in tree.xpath('//li[contains(@class, "b_algo")]'):
                h2 = li.xpath(".//h2/a")
                snip = li.xpath('.//div[contains(@class, "b_caption")]/p') or li.xpath(".//p")
                if not h2:
                    continue

                title = h2[0].text_content().strip()
                link = h2[0].get("href", "").strip()

                # Decode Bing tracking link (u=a1<base64>...) jika ada
                if "bing.com/ck/a?" in link and "u=a1" in link:
                    try:
                        import re
                        m = re.search(r"[?&]u=a1([A-Za-z0-9_-]+)", link)
                        if m:
                            raw_b64 = m.group(1)
                            raw_b64 += "=" * ((4 - len(raw_b64) % 4) % 4)
                            decoded_url = base64.urlsafe_b64decode(raw_b64).decode("utf-8", errors="ignore")
                            if decoded_url.startswith("http"):
                                link = decoded_url
                    except Exception:
                        pass

                snippet = snip[0].text_content().strip() if snip else ""
                if title and link and not link.startswith("https://www.bing.com/search"):
                    items.append(
                        SearchResultItem(
                            title=title,
                            url=link,
                            snippet=snippet[:350],
                            source="Bing Search",
                        )
                    )
                if len(items) >= max_results:
                    break
        except Exception as e:
            logger.warning(f"Bing search error ({e})")

        return items

    def search_duckduckgo(self, query: str, max_results: int = 5) -> list[SearchResultItem]:
        """Menelusuri web via DuckDuckGo HTML (fallback jika ISP mengizinkan)."""
        encoded_q = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_q}"
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        items: list[SearchResultItem] = []

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8", errors="ignore")

            tree = html.fromstring(content)
            for r in tree.xpath('//div[contains(@class, "result__body")]'):
                title_el = r.xpath('.//a[contains(@class, "result__a")]')
                snip_el = r.xpath('.//a[contains(@class, "result__snippet")]')
                if not title_el:
                    continue

                title = title_el[0].text_content().strip()
                link = title_el[0].get("href", "")
                if link.startswith("//duckduckgo.com/l/?uddg="):
                    try:
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                        link = parsed.get("uddg", [link])[0]
                    except Exception:
                        pass

                snippet = snip_el[0].text_content().strip() if snip_el else ""
                if title and link:
                    items.append(
                        SearchResultItem(
                            title=title,
                            url=link,
                            snippet=snippet[:350],
                            source="DuckDuckGo",
                        )
                    )
                if len(items) >= max_results:
                    break
        except Exception as e:
            logger.warning(f"DuckDuckGo search error ({e})")

        return items

    def search_wikipedia(self, query: str, max_results: int = 2) -> list[SearchResultItem]:
        """Menelusuri ensiklopedia Wikipedia untuk definisi/konsep resmi."""
        import json
        encoded_q = urllib.parse.quote(query)
        url = f"https://id.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded_q}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "RukaCompanion/1.0"})
        items: list[SearchResultItem] = []

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            for r in data.get("query", {}).get("search", [])[:max_results]:
                title = r.get("title", "")
                snippet_raw = r.get("snippet", "")
                try:
                    snippet = html.fromstring(snippet_raw).text_content().strip()
                except Exception:
                    snippet = snippet_raw.strip()
                page_url = f"https://id.wikipedia.org/wiki/{urllib.parse.quote(title)}"
                items.append(
                    SearchResultItem(
                        title=title,
                        url=page_url,
                        snippet=snippet[:300],
                        source="Wikipedia",
                    )
                )
        except Exception as e:
            logger.warning(f"Wikipedia search error ({e})")

        return items

    def search(self, query: str, max_results: int = 5) -> list[SearchResultItem]:
        """Pencarian cerdas berjenjang bebas blokir:
        1. Google News RSS jika query bertema berita/terkini/hari ini
        2. Bing Web Search (andal & bebas blokir ISP)
        3. DuckDuckGo Web Search (fallback kedua)
        4. Wikipedia untuk pengetahuan ensiklopedis
        """
        clean_q = query.strip()
        is_news_query = any(
            k in clean_q.lower()
            for k in ["berita", "terbaru", "terkini", "hari ini", "terupdate", "news", "skor", "laga", "presiden"]
        )

        items: list[SearchResultItem] = []
        if is_news_query:
            news_items = self.search_news(clean_q, max_results=max_results)
            items.extend(news_items)

        if len(items) < max_results:
            bing_items = self.search_bing(clean_q, max_results=max_results - len(items))
            existing_urls = {i.url for i in items}
            for b in bing_items:
                if b.url not in existing_urls:
                    items.append(b)
                    existing_urls.add(b.url)

        if len(items) < max_results:
            ddg_items = self.search_duckduckgo(clean_q, max_results=max_results - len(items))
            existing_urls = {i.url for i in items}
            for d in ddg_items:
                if d.url not in existing_urls:
                    items.append(d)
                    existing_urls.add(d.url)

        if len(items) < max_results:
            wiki_items = self.search_wikipedia(clean_q, max_results=2)
            existing_urls = {i.url for i in items}
            for wi in wiki_items:
                if wi.url not in existing_urls:
                    items.append(wi)
                    existing_urls.add(wi.url)

        if not items and not is_news_query:
            items = self.search_news(clean_q, max_results=max_results)

        return items[:max_results]

    def search_as_dict(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        results = self.search(query, max_results=max_results)
        return [asdict(r) for r in results]

    def format_for_prompt(self, items: list[SearchResultItem]) -> str:
        """Format hasil pencarian Google agar mudah dicerna oleh nalar LLM Ruka."""
        if not items:
            return "Tidak ditemukan hasil web yang relevan."
        lines = ["HASIL PENELUSURAN GOOGLE (REAL-TIME):"]
        for idx, item in enumerate(items, 1):
            lines.append(f"{idx}. [{item.title}] ({item.url})")
            if item.snippet:
                lines.append(f"   Cuplikan: {item.snippet}")
        return "\n".join(lines)


# Singleton instance
_search_engine: GoogleSearchEngine | None = None


def get_search_engine() -> GoogleSearchEngine:
    global _search_engine
    if _search_engine is None:
        _search_engine = GoogleSearchEngine()
    return _search_engine
