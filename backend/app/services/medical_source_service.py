"""
QuickDiagnosis - Medical Sources (OOP Polymorphism & Abstraction Architecture)
Defines abstract MedicalSource base class and polymorphic implementations:
- NIHSource (MedlinePlus / NLM)
- FDASource (openFDA Drug Safety)
- LocalBaseSource (QuickDiagnosis Clinical Base)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import os

from services.cache_service import MedicalDataCache
from services.medlineplus_service import MedlinePlusService
from services.fda_service import FDAService


class MedicalSource(ABC):
    """
    Abstract Base Class defining the contract for authoritative medical knowledge sources.
    Demonstrates OOP Abstraction and Polymorphism.
    """
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Brief brand identifier for badges (e.g. 'NIH / MedlinePlus')."""
        pass

    @property
    @abstractmethod
    def authority_name(self) -> str:
        """Full government or institutional publisher title."""
        pass

    @property
    @abstractmethod
    def official_base_url(self) -> str:
        """Base website or API domain."""
        pass

    @abstractmethod
    def search(self, query: str) -> Optional[Dict[str, Any]]:
        """Searches for health topic or drug information by query term."""
        pass

    @abstractmethod
    def get_details(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Retrieves comprehensive details for a specific disease or drug identifier."""
        pass


class NIHSource(MedicalSource):
    """
    Concrete MedicalSource for the U.S. National Library of Medicine / MedlinePlus.
    Specializes in condition overviews, diagnostic criteria, and patient guidance.
    """
    def __init__(self, cache: MedicalDataCache):
        self._medline_service = MedlinePlusService()
        self._cache = cache

    @property
    def source_name(self) -> str:
        return "NIH / MedlinePlus"

    @property
    def authority_name(self) -> str:
        return "U.S. National Library of Medicine / National Institutes of Health"

    @property
    def official_base_url(self) -> str:
        return "https://medlineplus.gov"

    def search(self, query: str) -> Optional[Dict[str, Any]]:
        cache_key = f"medlineplus:{query.lower().strip()}"
        cached = self._cache.get(cache_key)
        if cached:
            data = dict(cached["data"])
            data["from_cache"] = True
            return data

        res = self._medline_service.fetch_topic(query)
        if res:
            self._cache.set(
                key=cache_key,
                data=res,
                source_name=self.source_name,
                source_url=res.get("official_url")
            )
        return res

    def get_details(self, identifier: str) -> Optional[Dict[str, Any]]:
        return self.search(identifier)


class FDASource(MedicalSource):
    """
    Concrete MedicalSource for the U.S. Food and Drug Administration (openFDA).
    Specializes in approved indications, boxed warnings, and medication safety.
    """
    def __init__(self, cache: MedicalDataCache):
        self._fda_service = FDAService()
        self._cache = cache

    @property
    def source_name(self) -> str:
        return "U.S. FDA / openFDA"

    @property
    def authority_name(self) -> str:
        return "U.S. Food and Drug Administration"

    @property
    def official_base_url(self) -> str:
        return "https://api.fda.gov"

    def search(self, query: str) -> Optional[Dict[str, Any]]:
        cache_key = f"fda:{query.lower().strip()}"
        cached = self._cache.get(cache_key)
        if cached:
            data = dict(cached["data"])
            data["from_cache"] = True
            return data

        res = self._fda_service.query_drug_label(query)
        if res:
            self._cache.set(
                key=cache_key,
                data=res,
                source_name=self.source_name,
                source_url=res.get("official_url")
            )
        return res

    def get_details(self, identifier: str) -> Optional[Dict[str, Any]]:
        return self.search(identifier)


class LocalBaseSource(MedicalSource):
    """
    Concrete MedicalSource for QuickDiagnosis local verified clinical dataset.
    Guarantees reliable baseline coverage and offline continuity.
    """
    @property
    def source_name(self) -> str:
        return "QuickDiagnosis Clinical Base"

    @property
    def authority_name(self) -> str:
        return "QuickDiagnosis Verified Clinical Dataset (Local Offline Base)"

    @property
    def official_base_url(self) -> str:
        return "local://quickdiagnosis/clinical-dataset"

    def search(self, query: str) -> Optional[Dict[str, Any]]:
        return {
            "source": self.source_name,
            "authority_full": self.authority_name,
            "title": f"Clinical Baseline: {query}",
            "official_url": None,
            "verified": True
        }

    def get_details(self, identifier: str) -> Optional[Dict[str, Any]]:
        return self.search(identifier)


class MedicalSourceCoordinator:
    """
    Orchestrates polymorphic medical sources, caching, and fallback hierarchy.
    """
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        cache_file = os.path.join(data_dir, "medical_cache.json")
        self.cache = MedicalDataCache(cache_file_path=cache_file)
        self.nih_source = NIHSource(self.cache)
        self.fda_source = FDASource(self.cache)
        self.local_source = LocalBaseSource()

    def get_disease_medline_topic(self, disease_id: str, disease_name: str) -> Optional[Dict[str, Any]]:
        # Try disease name first
        res = self.nih_source.search(disease_name)
        if res:
            return res
        return self.nih_source.search(disease_id.replace("_", " "))

    def get_fda_medication_warnings(self, treatment_items: List[str]) -> List[Dict[str, Any]]:
        results = []
        for t in treatment_items:
            # Extract common generic drugs (e.g. "Acetaminophen (Tylenol)" -> "Acetaminophen")
            tokens = [tok.strip("(),.") for tok in t.split()]
            for tok in tokens:
                if len(tok) >= 4 and tok.isalpha():
                    res = self.fda_source.search(tok)
                    if res and res.get("drug_name"):
                        if not any(r["drug_name"].lower() == res["drug_name"].lower() for r in results):
                            results.append(res)
                            break
        return results

    def enrich_disease_detail(self, disease_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enriches disease details with MedlinePlus and FDA data."""
        enriched = dict(disease_data)
        d_id = enriched.get("id", "")
        d_name = enriched.get("name", "")

        medline = self.get_disease_medline_topic(d_id, d_name)
        cures = enriched.get("measurements_and_cures", {})
        treatments = cures.get("typical_medical_treatments", [])
        fda_meds = self.get_fda_medication_warnings(treatments)

        sources_list: List[Dict[str, Any]] = []

        if medline:
            sources_list.append({
                "authority": self.nih_source.source_name,
                "authority_full": self.nih_source.authority_name,
                "title": medline.get("title"),
                "url": medline.get("official_url"),
                "type": "Condition Guidance & Overview",
                "verified": True
            })
            enriched["medlineplus"] = medline

        if fda_meds:
            for med in fda_meds:
                sources_list.append({
                    "authority": self.fda_source.source_name,
                    "authority_full": self.fda_source.authority_name,
                    "title": f"Drug Label: {med.get('drug_name')}",
                    "url": med.get("official_url"),
                    "type": "Medication Safety & Warnings",
                    "verified": True
                })
            enriched["fda_medications"] = fda_meds

        sources_list.append({
            "authority": self.local_source.source_name,
            "authority_full": self.local_source.authority_name,
            "title": f"Standard Clinical Assessment: {d_name}",
            "url": None,
            "type": "Local Base Diagnostic Mapping",
            "verified": True
        })

        enriched["authoritative_sources"] = sources_list
        enriched["primary_source"] = (
            self.nih_source.source_name if medline else self.local_source.authority_name
        )
        return enriched

    def enrich_candidate_cards(self, candidate_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched = []
        for cand in candidate_list:
            c = dict(cand)
            d_id = c.get("id", "")
            d_name = c.get("name", "")
            info = self.get_disease_medline_topic(d_id, d_name)
            if info:
                c["external_source"] = {
                    "provider": self.nih_source.source_name,
                    "title": info.get("title"),
                    "url": info.get("official_url"),
                    "snippet": info.get("snippet"),
                    "verified": True
                }
            else:
                c["external_source"] = {
                    "provider": self.local_source.source_name,
                    "title": "Local Verified Dataset",
                    "url": None,
                    "snippet": "Local clinical assessment baseline.",
                    "verified": True
                }
            enriched.append(c)
        return enriched
