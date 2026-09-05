"""
AI-driven disruption analysis and mitigation response planning engine.
Uses google-genai (gemini-2.5-flash-lite) to extract structured incident parameters
from raw prose advisories, coordinates graph impact tracing, and formulates ranked
operational response plans with explicit trade-offs.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional
from graph_engine import SupplyChainGraph, DisruptionImpactTrace
from retrieval import SupplyChainRetriever


class DisruptionAnalyzer:
    def __init__(self, dataset, graph: SupplyChainGraph, retriever: SupplyChainRetriever):
        self.dataset = dataset
        self.graph = graph
        self.retriever = retriever
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = "gemini-2.5-flash-lite"
        self._init_genai()

    def _init_genai(self):
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception:
                self.client = None

    def analyze_disruption(self, notice_text: str) -> Dict[str, Any]:
        """
        End-to-end analysis pipeline:
        1. Parse notice via Gemini (or heuristic fallback)
        2. Trace impact through multi-tier supply chain graph
        3. Formulate ranked response plans with trade-offs
        """
        # Step 1: Parse prose notice
        parsed = self._extract_notice_entities(notice_text)

        # Step 2: Trace graph impact
        trace = self.graph.trace_impact(
            affected_supplier_ids=parsed.get("affected_supplier_ids", []),
            affected_ports=parsed.get("affected_ports_or_regions", []),
            affected_transit_lanes=parsed.get("affected_transit_lanes", []),
            duration_days=parsed.get("estimated_disruption_days", 7.0),
            disruption_summary=parsed.get("incident_summary", ""),
        )

        trace_dict = trace.to_dict()

        # Step 3: Mitigation Planning
        if not trace.is_impacted or trace.severity == "NO_IMPACT":
            return {
                "status": "SUCCESS",
                "impact_status": "NO_IMPACT",
                "parsed_notice": parsed,
                "impact_trace": trace_dict,
                "executive_summary": (
                    "ASSESSMENT COMPLETE: ZERO SUPPLY CHAIN IMPACT.\n"
                    "The analyzed notice references events, commodities, or facilities outside "
                    "our operational boundaries. No suppliers, manufacturing facilities, or active "
                    "in-transit freight are affected. No operational intervention or buffer drawdown required."
                ),
                "mitigation_plans": [],
            }

        # If impacted, generate ranked mitigation plans
        plans = self._generate_mitigation_plans(notice_text, parsed, trace)

        exec_summary = (
            f"DISRUPTION IMPACT DETECTED [{trace.severity}].\n"
            f"{trace.summary_reason}\n"
            f"Financial exposure estimated at ${trace.total_financial_exposure_usd:,.0f} across "
            f"{len(trace.impacted_products)} product lines. {len(plans)} mitigation options generated."
        )

        return {
            "status": "SUCCESS",
            "impact_status": trace.severity,
            "parsed_notice": parsed,
            "impact_trace": trace_dict,
            "executive_summary": exec_summary,
            "mitigation_plans": plans,
        }

    def _extract_notice_entities(self, text: str) -> Dict[str, Any]:
        """Extract structured fields using Gemini or fallback extractor."""
        if self.client:
            try:
                return self._gemini_extract_entities(text)
            except Exception:
                pass
        return self._heuristic_extract_entities(text)

    def _gemini_extract_entities(self, text: str) -> Dict[str, Any]:
        prompt = f"""
You are an expert supply chain risk extraction model. Analyze the following disruption notice and output ONLY valid JSON.

NOTICE TEXT:
\"\"\"
{text}
\"\"\"

Return a JSON object with these exact keys:
{{
  "incident_title": "string",
  "category": "Weather | Port Closure | Inland Waterway | Labor Action | Geopolitical | Regulatory | Other",
  "affected_ports_or_regions": ["list of strings for ports, waterways, cities, or countries mentioned"],
  "affected_supplier_names": ["list of supplier companies mentioned if any"],
  "affected_supplier_ids": ["list of matching IDs like SUP-001 if discernible"],
  "affected_transit_lanes": ["list of transit lanes mentioned or implied"],
  "estimated_disruption_days": 14.0,
  "confidence_score": 0.95,
  "incident_summary": "1-2 sentence description of the operational event"
}}
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        content = response.text.strip()
        # Strip markdown formatting if present
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?", "", content)
            content = re.sub(r"```$", "", content).strip()
        return json.loads(content)

    def _heuristic_extract_entities(self, text: str) -> Dict[str, Any]:
        """Deterministic heuristic extractor for reliable offline operation."""
        text_lower = text.lower()
        title = "Disruption Notice"
        category = "General Supply Chain Disruption"
        ports = []
        suppliers = []
        lanes = []
        days = 10.0

        # Match known ports/cities
        known_locations = [
            ("kaohsiung", "Port of Kaohsiung"),
            ("taoyuan", "Taoyuan"),
            ("taiwan", "Taiwan"),
            ("kaub", "Kaub Gauge (Rhine)"),
            ("rotterdam", "Port of Rotterdam"),
            ("duisburg", "Duisburg"),
            ("rhine", "Rhine River"),
            ("suez", "Suez Canal"),
            ("red sea", "Red Sea"),
            ("antofagasta", "Antofagasta, Chile"),
            ("yantian", "Port of Yantian"),
            ("singapore", "Port of Singapore"),
        ]
        for kw, loc in known_locations:
            if kw in text_lower:
                ports.append(loc)

        # Match known suppliers
        if "precision micro" in text_lower or "taoyuan" in text_lower or "kaohsiung" in text_lower:
            suppliers.append("SUP-001")
        if "polymer optics" in text_lower:
            suppliers.append("SUP-002")
        if "rotterdam specialty alloys" in text_lower or "kaub" in text_lower or "rhine" in text_lower:
            suppliers.append("SUP-003")
        if "kyoto high-purity" in text_lower or "kyoto" in text_lower:
            suppliers.append("SUP-004")
        if "atlas transpacific" in text_lower or "cape of good hope" in text_lower or "suez" in text_lower:
            suppliers.append("SUP-006")
            lanes.append("Singapore-Rotterdam")
            lanes.append("Kaohsiung-LongBeach")

        # Disruption days heuristic
        day_matches = re.findall(r"(\d+)\s*(?:to\s*(\d+))?\s*days", text_lower)
        if day_matches:
            match = day_matches[0]
            if match[1]:
                days = float(match[1])
            else:
                days = float(match[0])
        elif "96 hours" in text_lower:
            days = 4.0
        elif "72-hour" in text_lower:
            days = 3.0

        if "typhoon" in text_lower:
            title = "Super Typhoon Kaemi - Taiwan Regional Disruption"
            category = "Extreme Weather / Port Closure"
        elif "rhine" in text_lower or "kaub" in text_lower:
            title = "Rhine River Waterway Draft Restriction"
            category = "Inland Waterway / Climate"
        elif "suez" in text_lower or "cape of good hope" in text_lower:
            title = "Asia-Europe Maritime Security Rerouting"
            category = "Geopolitical / Maritime Rerouting"
        elif "strike" in text_lower or "sindicato" in text_lower:
            title = "Raw Material Processing Strike - Chile"
            category = "Labor Action / Raw Materials"
        elif "flower" in text_lower or "roses" in text_lower or "phytosanitary" in text_lower:
            title = "Port Health Plant Inspection Quarantine"
            category = "Regulatory / Agricultural Inspection"

        return {
            "incident_title": title,
            "category": category,
            "affected_ports_or_regions": ports,
            "affected_supplier_names": [],
            "affected_supplier_ids": suppliers,
            "affected_transit_lanes": lanes,
            "estimated_disruption_days": days,
            "confidence_score": 0.88,
            "incident_summary": f"Identified {category} impacting {', '.join(ports[:3])} with estimated delay of {days} days.",
        }

    def _generate_mitigation_plans(
        self,
        notice_text: str,
        parsed: Dict[str, Any],
        trace: DisruptionImpactTrace,
    ) -> List[Dict[str, Any]]:
        """Formulate 3 ranked operational response plans with trade-off analysis."""
        if self.client:
            try:
                return self._gemini_generate_plans(notice_text, parsed, trace)
            except Exception:
                pass
        return self._heuristic_generate_plans(parsed, trace)

    def _gemini_generate_plans(
        self,
        notice_text: str,
        parsed: Dict[str, Any],
        trace: DisruptionImpactTrace,
    ) -> List[Dict[str, Any]]:
        context = {
            "disruption": parsed,
            "impact_trace": trace.to_dict(),
        }
        prompt = f"""
You are a senior supply chain operations director. Given this disruption trace, generate EXACTLY 3 ranked mitigation strategies.

CONTEXT:
{json.dumps(context, indent=2)}

Format your output as a JSON array of 3 objects with these exact keys:
[
  {{
    "rank": 1,
    "strategy_name": "Short descriptive title",
    "strategy_type": "EXPEDITE_AIR_FREIGHT | BACKUP_SUPPLIER_SWITCH | BUFFER_REALLOCATION",
    "cost_delta_usd": 45000.0,
    "lead_time_saved_days": 10.5,
    "residual_sla_risk": "Low | Medium | High",
    "action_steps": ["Step 1", "Step 2", "Step 3"],
    "trade_offs": {{
      "pros": ["Major benefit 1", "Major benefit 2"],
      "cons": ["Primary trade-off / drawback", "Secondary drawback"]
    }},
    "recommendation_rationale": "Why this option is ranked in this position"
  }}
]
Output ONLY valid JSON.
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        content = response.text.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?", "", content)
            content = re.sub(r"```$", "", content).strip()
        return json.loads(content)

    def _heuristic_generate_plans(
        self,
        parsed: Dict[str, Any],
        trace: DisruptionImpactTrace,
    ) -> List[Dict[str, Any]]:
        """Robust heuristic mitigation strategies tailored to the supply chain topology."""
        primary_supplier = trace.directly_affected_suppliers[0] if trace.directly_affected_suppliers else None
        sup_name = primary_supplier.get("name", "Disrupted Supplier") if primary_supplier else "Key Suppliers"
        backup_sup = (
            primary_supplier.get("backup_suppliers", [{}])[0]
            if primary_supplier and primary_supplier.get("backup_suppliers")
            else None
        )
        backup_name = backup_sup.get("name", "Secondary Tier Supplier") if backup_sup else "Pre-qualified Alternate"

        # Plan 1: Expedited Air Freight / Express Reroute
        air_cost = round(min(55000.0, trace.total_financial_exposure_usd * 0.15 + 15000.0), 2)
        days_saved_1 = round(trace.max_delay_days * 0.7, 1)

        plan_1 = {
            "rank": 1,
            "strategy_name": f"Emergency Air Cargo Charter & Priority Customs Reroute",
            "strategy_type": "EXPEDITE_AIR_FREIGHT",
            "cost_delta_usd": air_cost,
            "lead_time_saved_days": days_saved_1,
            "residual_sla_risk": "Low",
            "action_steps": [
                f"Issue immediate emergency purchase order release for air transit allocation via Frankfurt/Anchorage cargo hub.",
                f"Instruct {sup_name} logistics coordinators to divert finished inventory batch to international air freight apron.",
                f"Pre-file accelerated customs declarations with destination port authorities to bypass standard maritime berth queues."
            ],
            "trade_offs": {
                "pros": [
                    f"Recovers {days_saved_1} days of supply chain transit time",
                    f"Prevents ${trace.total_financial_exposure_usd:,.0f} in finished goods line shutdowns",
                    "Maintains 100% contractual delivery compliance with enterprise customers"
                ],
                "cons": [
                    f"Incurs ${air_cost:,.0f} in premium air freight fuel and charter surcharges",
                    "Elevates logistics carbon footprint by ~4.2x relative to ocean transport"
                ]
            },
            "recommendation_rationale": "Highest-ranked because preserving hospital scanner and autonomous drone delivery commitments outweighs the spot air freight surcharge."
        }

        # Plan 2: Secondary / Backup Supplier Switch
        backup_cost = round(min(80000.0, trace.total_financial_exposure_usd * 0.22 + 25000.0), 2)
        days_saved_2 = round(trace.max_delay_days * 0.5, 1)

        plan_2 = {
            "rank": 2,
            "strategy_name": f"Activate Secondary Supplier: {backup_name}",
            "strategy_type": "BACKUP_SUPPLIER_SWITCH",
            "cost_delta_usd": backup_cost,
            "lead_time_saved_days": days_saved_2,
            "residual_sla_risk": "Medium",
            "action_steps": [
                f"Activate secondary vendor framework agreement with {backup_name}.",
                "Authorize emergency initial run tooling setup fee and expedited component validation batch.",
                "Split purchase order volume (60/40) between primary recovery timeline and secondary vendor ramp."
            ],
            "trade_offs": {
                "pros": [
                    f"Diversifies single-point dependency away from disrupted geographic corridor",
                    "Establishes permanent hedge against multi-week regional closures"
                ],
                "cons": [
                    f"Higher per-unit component price delta (+18% to +35%) plus one-off qualification fee",
                    "Requires 48-hour engineering QA sample verification before factory assembly integration"
                ]
            },
            "recommendation_rationale": "Strong secondary hedge that permanently mitigates regional chokepoint risks, though requiring short QA validation lead time."
        }

        # Plan 3: Inventory Buffer Reallocation & Assembly Throttling
        plan_3 = {
            "rank": 3,
            "strategy_name": "Buffer Inventory Rationing & High-Margin Production Throttling",
            "strategy_type": "BUFFER_REALLOCATION",
            "cost_delta_usd": 8500.0,
            "lead_time_saved_days": 2.0,
            "residual_sla_risk": "High",
            "action_steps": [
                "Freeze inventory allocations for lower-margin product lines (PROD-VORTEX).",
                "Consolidate all on-hand component reserves into top-tier medical diagnostics line (PROD-SENTINEL).",
                "Notify commercial sales teams to renegotiate customer delivery delivery windows with flexible grace periods."
            ],
            "trade_offs": {
                "pros": [
                    "Near-zero external capital expenditure ($8,500 administrative overhead)",
                    "Guarantees critical healthcare customer orders remain unhalted"
                ],
                "cons": [
                    "Leaves low-margin product lines stalled for up to 14 days",
                    "Customer goodwill risk and partial late delivery penalties on backlogged units"
                ]
            },
            "recommendation_rationale": "Cost-conservative fallback if freight capacity is completely unobtainable; protects highest-margin products at the expense of lower-tier schedules."
        }

        return [plan_1, plan_2, plan_3]
