"""
QuickDiagnosis - Medical Source Orchestration Service
Coordinates information retrieval across:
1. Official NIH / MedlinePlus (Health Topics & Clinical Summaries)
2. Official U.S. FDA / openFDA (Medication Safety, Warnings, & Labels)
3. Medical Data Cache (Local disk-backed persistence & TTL)
4. QuickDiagnosis Local Clinical Dataset (Base & Fallback)

Implements strict anti-fabrication: only authentic official data is passed forward.
"""

import os
from typing import Any, Dict, List, Optional

from services.cache_service import MedicalDataCache
from services.medlineplus_service import MedlinePlusService
from services.fda_service import FDAService


class MedicalSourceService:
    """
    Central service orchestrating authoritative medical data retrieval.
    Enforces source priority, caching, and graceful offline fallback.
    """
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        cache_path = os.path.join(data_dir, "medical_cache.json")
        self.cache = MedicalDataCache(cache_path)
        self.medlineplus = MedlinePlusService()
        self.fda = FDAService()

    def get_medlineplus_info(self, disease_id: str, disease_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves MedlinePlus info for a disease, checking cache first.
        Gracefully falls back to stale cache if offline.
        """
        cache_key = f"medlineplus:{disease_id}"
        cached = self.cache.get(cache_key, allow_stale=False)
        if cached and cached.get("data"):
            data = cached["data"]
            data["from_cache"] = True
            return data

        # Query live NIH/MedlinePlus API
        live_data = self.medlineplus.fetch_topic(disease_name)
        if live_data:
            live_data["from_cache"] = False
            self.cache.set(
                key=cache_key,
                data=live_data,
                source_name=live_data.get("source"),
                source_url=live_data.get("official_url")
            )
            return live_data

        # If live fetch failed, check for stale cache as offline fallback
        stale = self.cache.get(cache_key, allow_stale=True)
        if stale and stale.get("data"):
            data = stale["data"]
            data["from_cache"] = True
            data["offline_fallback"] = True
            return data

        return None

    def get_fda_medications(self, treatment_items: List[str]) -> List[Dict[str, Any]]:
        """
        Identifies pharmaceutical drugs in treatment items and fetches official openFDA labels.
        Only queries FDA for recognized drugs; uses cache to avoid repeated queries.
        """
        drugs = self.fda.identify_medications(treatment_items)
        results: List[Dict[str, Any]] = []

        for drug in drugs:
            cache_key = f"fda:{drug}"
            cached = self.cache.get(cache_key, allow_stale=False)
            if cached and cached.get("data"):
                data = cached["data"]
                data["from_cache"] = True
                results.append(data)
                continue

            # Query live openFDA API
            live_data = self.fda.fetch_drug_label(drug)
            if live_data:
                live_data["from_cache"] = False
                self.cache.set(
                    key=cache_key,
                    data=live_data,
                    source_name=live_data.get("source"),
                    source_url=live_data.get("official_url")
                )
                results.append(live_data)
                continue

            # Stale cache fallback if offline
            stale = self.cache.get(cache_key, allow_stale=True)
            if stale and stale.get("data"):
                data = stale["data"]
                data["from_cache"] = True
                data["offline_fallback"] = True
                results.append(data)

        return results

    def enrich_disease_detail(self, disease_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriches full disease details with NIH/MedlinePlus topic info and FDA drug labels.
        Always preserves local dataset information as foundation.
        """
        enriched = dict(disease_data)
        disease_id = enriched.get("id", "")
        disease_name = enriched.get("name", "")

        # 1. MedlinePlus Enrichment
        medline_info = self.get_medlineplus_info(disease_id, disease_name)

        # 2. FDA Medication Safety Enrichment
        cures = enriched.get("measurements_and_cures", {})
        treatments = cures.get("typical_medical_treatments", [])
        fda_meds = self.get_fda_medications(treatments)

        # 3. Assemble Authoritative Medical Sources list
        sources_list: List[Dict[str, Any]] = []

        if medline_info:
            sources_list.append({
                "authority": "NIH / MedlinePlus",
                "authority_full": medline_info.get("source_full"),
                "title": medline_info.get("title"),
                "url": medline_info.get("official_url"),
                "type": "Condition Guidance & Overview",
                "verified": True
            })
            enriched["medlineplus"] = medline_info

        if fda_meds:
            for med in fda_meds:
                sources_list.append({
                    "authority": "U.S. FDA / openFDA",
                    "authority_full": med.get("source_full"),
                    "title": f"Drug Label: {med.get('drug_name')}",
                    "url": med.get("official_url"),
                    "type": "Medication Safety & Warnings",
                    "verified": True
                })
            enriched["fda_medications"] = fda_meds

        # Always list local verified clinical baseline
        sources_list.append({
            "authority": "QuickDiagnosis Clinical Base",
            "authority_full": "Verified Clinical Symptom-Disease Knowledge Base (Local)",
            "title": f"Standard Clinical Assessment: {disease_name}",
            "url": None,
            "type": "Local Base Diagnostic Mapping",
            "verified": True
        })

        enriched["authoritative_sources"] = sources_list
        enriched["primary_source"] = (
            "NIH / MedlinePlus" if medline_info else "QuickDiagnosis Verified Clinical Dataset"
        )

        return enriched

    def enrich_candidate_cards(self, candidate_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enriches candidate result cards with verified source metadata and official links.
        """
        enriched_list = []
        for cand in candidate_list:
            c = dict(cand)
            disease_id = c.get("id", "")
            disease_name = c.get("name", "")

            # Check MedlinePlus
            medline_info = self.get_medlineplus_info(disease_id, disease_name)
            if medline_info:
                c["external_source"] = {
                    "provider": "NIH / MedlinePlus",
                    "title": medline_info.get("title"),
                    "url": medline_info.get("official_url"),
                    "snippet": medline_info.get("snippet"),
                    "verified": True
                }
            else:
                c["external_source"] = {
                    "provider": "QuickDiagnosis Clinical Base",
                    "title": disease_name,
                    "url": None,
                    "snippet": None,
                    "verified": True
                }

            enriched_list.append(c)

        return enriched_list
