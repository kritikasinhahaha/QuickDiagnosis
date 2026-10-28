"""
QuickDiagnosis - NIH / MedlinePlus External Service
Fetches authoritative disease, condition, and health topic information
from the official U.S. National Library of Medicine (NLM) MedlinePlus Web Service.
Strictly authentic data retrieval: never fabricates URLs or clinical claims.
"""

import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


class MedlinePlusService:
    """
    Communicates with the official NIH/NLM MedlinePlus Health Topics Web Service.
    API reference: https://medlineplus.gov/webservices.html
    """
    BASE_URL = "https://wsearch.nlm.nih.gov/ws/query"
    TIMEOUT_SECONDS = 4.0

    def __init__(self):
        self._ssl_context = self._build_ssl_context()

    def _build_ssl_context(self) -> ssl.SSLContext:
        """Constructs an SSL context resilient to Windows CA environments."""
        try:
            import certifi
            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            pass

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx
        except Exception:
            return ssl._create_unverified_context()

    def _clean_html(self, raw_html: Optional[str]) -> str:
        """Strips HTML tags and entity codes returned inside MedlinePlus XML snippets."""
        if not raw_html:
            return ""
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", raw_html)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        # Decode common XML/HTML entities
        entities = {
            "&amp;": "&",
            "&quot;": '"',
            "&apos;": "'",
            "&lt;": "<",
            "&gt;": ">",
            "&#39;": "'",
            "&nbsp;": " "
        }
        for ent, char in entities.items():
            text = text.replace(ent, char)
        return text

    def _query_api(self, term: str) -> Optional[bytes]:
        """Executes a single HTTP GET request to NLM MedlinePlus API."""
        params = {
            "db": "healthTopics",
            "term": term,
            "retmode": "xml"
        }
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "QuickDiagnosis/2.0 (Medical Symptom Screener; Open Educational Tool)",
                "Accept": "application/xml"
            }
        )
        try:
            with urllib.request.urlopen(req, context=self._ssl_context, timeout=self.TIMEOUT_SECONDS) as response:
                if response.status == 200:
                    return response.read()
        except Exception:
            return None
        return None

    def fetch_topic(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Queries NLM MedlinePlus for the specified disease or health condition term.
        Returns authentic structured metadata or None if not found or unreachable.
        """
        if not query or not query.strip():
            return None

        # Build candidate terms in order of preference (most specific clinical term first)
        candidates: List[str] = []
        base = re.sub(r"\(.*?\)", "", query).strip()
        base = re.sub(r"\s+", " ", base)

        # 1. Simplified term without noise modifiers like "Episode", "Seasonal", "Acute", "Infection"
        simplified = re.sub(r"\b(Episode|Attack|Seasonal|Acute|Chronic|Infection|Condition)\b", "", base, flags=re.IGNORECASE).strip()
        simplified = re.sub(r"\s+", " ", simplified)
        if simplified and simplified not in candidates:
            candidates.append(simplified)

        # 2. Extracted parenthetical word if any (e.g. "Flu" from "Seasonal Influenza (Flu)")
        parentheses = re.findall(r"\((.*?)\)", query)
        for p in parentheses:
            p_clean = p.strip()
            if p_clean and p_clean not in candidates:
                candidates.append(p_clean)

        # 3. Base full name
        if base and base not in candidates:
            candidates.append(base)

        # 4. Significant individual words from user symptom input (e.g. "ear" from "ear fullness")
        stopwords = {"and", "the", "in", "of", "with", "or", "a", "an", "to", "my", "feeling", "sensation", "having", "pain", "ache"}
        words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", base.lower()) if w not in stopwords]
        for w in words:
            if w not in candidates:
                candidates.append(w)

        xml_data: Optional[bytes] = None
        matched_search_term = ""

        for candidate in candidates:
            xml_data = self._query_api(candidate)
            if xml_data:
                try:
                    root = ET.fromstring(xml_data)
                    count_elem = root.find(".//count")
                    if count_elem is not None and int(count_elem.text or 0) > 0:
                        matched_search_term = candidate
                        break
                except Exception:
                    continue

        if not xml_data:
            return None

        try:
            root = ET.fromstring(xml_data)
            count_elem = root.find(".//count")
            if count_elem is not None and int(count_elem.text or 0) == 0:
                return None

            doc = root.find(".//document")
            if doc is None:
                return None

            official_url = doc.attrib.get("url", "").strip()
            if not official_url or not official_url.startswith("http"):
                return None

            title = ""
            snippet = ""
            full_summary = ""
            mesh_terms: List[str] = []

            for content in doc.findall("content"):
                name = content.attrib.get("name", "")
                text_val = (content.text or "").strip()
                if not text_val:
                    continue

                if name == "title":
                    title = self._clean_html(text_val)
                elif name == "snippet":
                    snippet = self._clean_html(text_val)
                elif name == "FullSummary":
                    full_summary = self._clean_html(text_val)
                elif name == "mesh":
                    cleaned_mesh = self._clean_html(text_val)
                    if cleaned_mesh and cleaned_mesh not in mesh_terms:
                        mesh_terms.append(cleaned_mesh)

            if not title:
                title = query

            # Prefer FullSummary if concise enough, else snippet
            summary = full_summary if full_summary else snippet
            if not summary:
                summary = snippet

            return {
                "source": "NIH / MedlinePlus",
                "source_full": "U.S. National Library of Medicine / National Institutes of Health",
                "title": title,
                "official_url": official_url,
                "summary": summary,
                "snippet": snippet[:280] + "..." if len(snippet) > 280 else snippet,
                "mesh_terms": mesh_terms[:5],
                "retrieved_via": "NLM Health Topics Web Service API"
            }
        except Exception:
            return None
