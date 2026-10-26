"""
QuickDiagnosis - U.S. FDA / openFDA Service
Fetches official drug labeling, warnings, indications, and safety information
from the official openFDA API (https://open.fda.gov/apis/drug/label/).
Strictly authentic data retrieval: only queries for medications and never fabricates labels.
"""

import json
import re
import ssl
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class FDAService:
    """
    Communicates with the official openFDA Drug Labeling API.
    API reference: https://open.fda.gov/apis/drug/label/
    """
    BASE_URL = "https://api.fda.gov/drug/label.json"
    TIMEOUT_SECONDS = 4.0

    # Common clinical medications and their standardized search terms
    KNOWN_DRUGS = {
        "acetaminophen": "acetaminophen",
        "paracetamol": "acetaminophen",
        "ibuprofen": "ibuprofen",
        "oseltamivir": "oseltamivir",
        "tamiflu": "oseltamivir",
        "albuterol": "albuterol",
        "salbutamol": "albuterol",
        "amoxicillin": "amoxicillin",
        "omeprazole": "omeprazole",
        "cetirizine": "cetirizine",
        "loratadine": "loratadine",
        "sumatriptan": "sumatriptan",
        "triptan": "sumatriptan",
        "triptans": "sumatriptan",
        "aspirin": "aspirin",
        "metformin": "metformin",
        "hydrocortisone": "hydrocortisone",
        "diphenhydramine": "diphenhydramine",
        "dextromethorphan": "dextromethorphan",
        "guaifenesin": "guaifenesin",
        "pseudoephedrine": "pseudoephedrine"
    }

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

    def identify_medications(self, treatment_items: List[str]) -> List[str]:
        """
        Scans medical treatment text strings for recognized medication names.
        Returns a list of deduplicated drug keywords to query FDA.
        """
        found_drugs = []
        full_text = " ".join(treatment_items or []).lower()

        for drug_alias, canonical in self.KNOWN_DRUGS.items():
            pattern = r"\b" + re.escape(drug_alias) + r"\b"
            if re.search(pattern, full_text):
                if canonical not in found_drugs:
                    found_drugs.append(canonical)

        return found_drugs[:3]  # Limit to top 3 relevant drugs to keep requests minimal

    def fetch_drug_label(self, drug_name: str) -> Optional[Dict[str, Any]]:
        """
        Queries openFDA for official drug label, boxed warnings, indications, and precautions.
        Returns authentic structured data or None if not found or unreachable.
        """
        if not drug_name or not drug_name.strip():
            return None

        clean_name = drug_name.strip().lower()
        canonical_name = self.KNOWN_DRUGS.get(clean_name, clean_name)

        # Search openFDA by generic name or brand name
        search_query = f'openfda.generic_name:"{canonical_name}"'
        params = {
            "search": search_query,
            "limit": 1
        }
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "QuickDiagnosis/2.0 (Medical Symptom Screener; Drug Safety Module)",
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, context=self._ssl_context, timeout=self.TIMEOUT_SECONDS) as response:
                if response.status != 200:
                    return None
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            # Fallback if specific generic search failed: try brand name
            try:
                fallback_query = f'openfda.brand_name:"{canonical_name}"'
                fallback_url = f"{self.BASE_URL}?{urllib.parse.urlencode({'search': fallback_query, 'limit': 1})}"
                fallback_req = urllib.request.Request(
                    fallback_url,
                    headers={"User-Agent": "QuickDiagnosis/2.0", "Accept": "application/json"}
                )
                with urllib.request.urlopen(fallback_req, context=self._ssl_context, timeout=self.TIMEOUT_SECONDS) as response:
                    if response.status != 200:
                        return None
                    data = json.loads(response.read().decode("utf-8"))
            except Exception:
                return None

        try:
            results = data.get("results", [])
            if not results:
                return None

            record = results[0]
            openfda = record.get("openfda", {})

            brand_names = openfda.get("brand_name", [])
            generic_names = openfda.get("generic_name", [])
            display_name = (generic_names[0] if generic_names else canonical_name).title()

            # Extract warnings
            warnings = record.get("warnings") or record.get("boxed_warning") or record.get("warnings_and_cautions") or []
            warnings_text = warnings[0] if warnings else ""
            if len(warnings_text) > 350:
                warnings_text = warnings_text[:350] + "..."

            # Extract indications
            indications = record.get("indications_and_usage") or []
            indications_text = indications[0] if indications else ""
            if len(indications_text) > 300:
                indications_text = indications_text[:300] + "..."

            # Extract contraindications
            contraindications = record.get("contraindications") or []
            contraindications_text = contraindications[0] if contraindications else ""
            if len(contraindications_text) > 250:
                contraindications_text = contraindications_text[:250] + "..."

            # Official openFDA citation URL
            official_url = f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:{canonical_name}"

            return {
                "source": "U.S. FDA / openFDA",
                "source_full": "U.S. Food and Drug Administration (openFDA Drug Labeling)",
                "drug_name": display_name,
                "generic_name": canonical_name.upper(),
                "brand_names": brand_names[:4],
                "official_url": official_url,
                "warnings": warnings_text,
                "indications": indications_text,
                "contraindications": contraindications_text,
                "retrieved_via": "openFDA Drug Label API"
            }
        except Exception:
            return None
