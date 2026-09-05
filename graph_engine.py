"""
Multi-tier supply chain dependency graph and downstream disruption impact tracer.
Traverses relationships across suppliers, sub-tier materials, BOM parts, assembly plants,
and active transit shipments to compute days-to-stockout and financial revenue exposure.
"""

from typing import Dict, Any, List, Set, Optional
from datetime import datetime, timedelta


class DisruptionImpactTrace:
    def __init__(self):
        self.is_impacted: bool = False
        self.severity: str = "NO_IMPACT"  # NO_IMPACT, LOW, MEDIUM, HIGH, CRITICAL
        self.summary_reason: str = ""
        self.directly_affected_suppliers: List[Dict[str, Any]] = []
        self.indirectly_affected_suppliers: List[Dict[str, Any]] = []
        self.delayed_shipments: List[Dict[str, Any]] = []
        self.affected_parts: List[Dict[str, Any]] = []
        self.impacted_products: List[Dict[str, Any]] = []
        self.impacted_plants: List[Dict[str, Any]] = []
        self.total_financial_exposure_usd: float = 0.0
        self.earliest_stockout_days: Optional[float] = None
        self.max_delay_days: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_impacted": self.is_impacted,
            "severity": self.severity,
            "summary_reason": self.summary_reason,
            "directly_affected_suppliers": self.directly_affected_suppliers,
            "indirectly_affected_suppliers": self.indirectly_affected_suppliers,
            "delayed_shipments": self.delayed_shipments,
            "affected_parts": self.affected_parts,
            "impacted_products": self.impacted_products,
            "impacted_plants": self.impacted_plants,
            "total_financial_exposure_usd": round(self.total_financial_exposure_usd, 2),
            "earliest_stockout_days": self.earliest_stockout_days,
            "max_delay_days": round(self.max_delay_days, 1),
        }


class SupplyChainGraph:
    def __init__(self, dataset):
        self.dataset = dataset
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self._build_graph()

    def _build_graph(self):
        # 1. Add Suppliers
        for sup in self.dataset.suppliers_raw:
            s_id = sup["id"]
            self.nodes[s_id] = {
                "id": s_id,
                "name": sup["name"],
                "type": "Supplier",
                "tier": sup.get("tier", 1),
                "location": f"{sup.get('city', '')}, {sup.get('country', '')}",
                "port_hub": sup.get("port_hub", ""),
            }

            # Parts supplied
            for part in sup.get("parts_supplied", []):
                p_id = part["part_id"]
                if p_id not in self.nodes:
                    self.nodes[p_id] = {
                        "id": p_id,
                        "name": part.get("name", p_id),
                        "type": "Part",
                        "unit_cost": part.get("unit_cost", 0.0),
                    }
                self.edges.append({
                    "source": s_id,
                    "target": p_id,
                    "relation": "SUPPLIES",
                    "lead_time_days": part.get("standard_lead_time_days", 14),
                })

                # Sub-tier dependencies
                for sub_dep in part.get("sub_tier_dependencies", []):
                    self.edges.append({
                        "source": sub_dep,
                        "target": p_id,
                        "relation": "SUB_TIER_INPUT",
                    })

        # 2. Add Plants & Products
        for plant in self.dataset.inventory_raw.get("assembly_plants", []):
            pl_id = plant["plant_id"]
            self.nodes[pl_id] = {
                "id": pl_id,
                "name": plant["name"],
                "type": "AssemblyPlant",
                "location": plant.get("location", ""),
            }

        for prod in self.dataset.inventory_raw.get("products", []):
            pr_id = prod["product_id"]
            self.nodes[pr_id] = {
                "id": pr_id,
                "name": prod["name"],
                "type": "Product",
                "margin_usd": prod.get("margin_usd", 0.0),
            }
            # Link to Plant
            if "plant_id" in prod:
                self.edges.append({
                    "source": pr_id,
                    "target": prod["plant_id"],
                    "relation": "MANUFACTURED_AT",
                })
            # Link BOM parts
            for b_part in prod.get("bom_parts", []):
                self.edges.append({
                    "source": b_part,
                    "target": pr_id,
                    "relation": "BOM_COMPONENT",
                })

    def get_network_graph(self) -> Dict[str, Any]:
        return {
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
        }

    def trace_impact(
        self,
        affected_supplier_ids: List[str],
        affected_ports: List[str],
        affected_transit_lanes: List[str],
        duration_days: float,
        disruption_summary: str = "",
    ) -> DisruptionImpactTrace:
        trace = DisruptionImpactTrace()
        trace.max_delay_days = duration_days

        # Normalize lookups
        direct_supplier_ids: Set[str] = set()
        matched_ports = [p.lower() for p in affected_ports if p]
        matched_lanes = [l.lower() for l in affected_transit_lanes if l]

        # 1. Identify directly affected suppliers by ID or Port/Location match
        for sup in self.dataset.suppliers_raw:
            s_id = sup.get("id", "")
            s_port = sup.get("port_hub", "").lower()
            s_city = sup.get("city", "").lower()
            s_country = sup.get("country", "").lower()

            if s_id in affected_supplier_ids:
                direct_supplier_ids.add(s_id)
            else:
                for port_k in matched_ports:
                    if port_k in s_port or port_k in s_city or port_k in s_country:
                        direct_supplier_ids.add(s_id)
                        break

        # 2. Identify in-transit shipments affected
        affected_shipment_ids: Set[str] = set()
        for ship in self.dataset.inventory_raw.get("in_transit_shipments", []):
            s_orig = ship.get("origin_port", "").lower()
            s_dest = ship.get("destination_hub", "").lower()
            s_lane = ship.get("transit_lane", "").lower()
            carrier = ship.get("carrier", "").lower()

            hit = False
            for port_k in matched_ports:
                if port_k in s_orig or port_k in s_dest:
                    hit = True
                    break
            if not hit:
                for lane_k in matched_lanes:
                    if lane_k in s_lane or lane_k in carrier:
                        hit = True
                        break

            if hit:
                affected_shipment_ids.add(ship.get("shipment_id", ""))
                trace.delayed_shipments.append(ship)
                # Link shipment parts to directly affected
                for cargo_item in ship.get("cargo", []):
                    if "supplier_id" in cargo_item:
                        direct_supplier_ids.add(cargo_item["supplier_id"])

        # Record directly affected suppliers
        for s_id in direct_supplier_ids:
            s_info = self.dataset.get_supplier_by_id(s_id)
            if s_info:
                trace.directly_affected_suppliers.append(s_info)

        # 3. Sub-tier upstream propagation (e.g. Tier 3 silicon -> Tier 1 MCU)
        sub_tier_parts_disrupted: Set[str] = set()
        for s_info in trace.directly_affected_suppliers:
            for part in s_info.get("parts_supplied", []):
                sub_tier_parts_disrupted.add(part.get("part_id"))

        for sup in self.dataset.suppliers_raw:
            s_id = sup.get("id")
            if s_id in direct_supplier_ids:
                continue
            for part in sup.get("parts_supplied", []):
                for dep in part.get("sub_tier_dependencies", []):
                    if dep in sub_tier_parts_disrupted:
                        trace.indirectly_affected_suppliers.append({
                            "supplier": sup,
                            "reason": f"Dependent on upstream raw material {dep} from disrupted tier",
                        })
                        direct_supplier_ids.add(s_id)

        # If zero suppliers and zero shipments are affected -> NO IMPACT
        if not direct_supplier_ids and not trace.delayed_shipments:
            trace.is_impacted = False
            trace.severity = "NO_IMPACT"
            trace.summary_reason = (
                "No active suppliers, assembly facilities, contracted carriers, or transit shipments "
                "overlap with the geographic area, infrastructure, or commodity scope specified in the notice."
            )
            return trace

        # 4. Trace affected Parts & compare against Inventory Runway
        trace.is_impacted = True
        affected_part_ids: Set[str] = set()

        for s_id in direct_supplier_ids:
            s_info = self.dataset.get_supplier_by_id(s_id)
            if s_info:
                for part in s_info.get("parts_supplied", []):
                    p_id = part.get("part_id")
                    if p_id:
                        affected_part_ids.add(p_id)

        for ship in trace.delayed_shipments:
            for cargo_item in ship.get("cargo", []):
                p_id = cargo_item.get("part_id")
                if p_id:
                    affected_part_ids.add(p_id)

        earliest_stockout = None
        has_critical_stockout = False

        for p_id in affected_part_ids:
            inv = self.dataset.get_inventory_for_part(p_id)
            on_hand = inv.get("on_hand", 0) if inv else 0
            daily_burn = inv.get("daily_burn", 1) if inv else 1
            safety_stock = inv.get("safety_stock", 0) if inv else 0
            runway_days = round(on_hand / daily_burn, 1) if daily_burn > 0 else 999.0

            if earliest_stockout is None or runway_days < earliest_stockout:
                earliest_stockout = runway_days

            is_stockout = duration_days > runway_days
            if is_stockout:
                has_critical_stockout = True
                shortfall_days = round(duration_days - runway_days, 1)
                shortfall_units = int(shortfall_days * daily_burn)
            else:
                shortfall_days = 0.0
                shortfall_units = 0

            trace.affected_parts.append({
                "part_id": p_id,
                "on_hand": on_hand,
                "safety_stock": safety_stock,
                "daily_burn": daily_burn,
                "runway_days": runway_days,
                "disruption_duration_days": duration_days,
                "stockout_imminent": is_stockout,
                "shortfall_days": shortfall_days,
                "shortfall_units": shortfall_units,
            })

        trace.earliest_stockout_days = earliest_stockout

        # 5. Trace Downstream Products & Assembly Plants
        affected_product_ids: Set[str] = set()
        affected_plant_ids: Set[str] = set()

        total_financial_exposure = 0.0

        for part_info in trace.affected_parts:
            p_id = part_info["part_id"]
            prods = self.dataset.get_products_using_part(p_id)
            for prod in prods:
                pr_id = prod.get("product_id")
                plant_id = prod.get("plant_id")
                affected_product_ids.add(pr_id)
                if plant_id:
                    affected_plant_ids.add(plant_id)

                # Financial impact calculation
                daily_rate = prod.get("daily_build_rate", 10)
                margin = prod.get("margin_usd", 1000.0)
                sla_pen = prod.get("sla_penalty_per_day_usd", 200.0)

                if part_info["stockout_imminent"]:
                    days_halted = part_info["shortfall_days"]
                    lost_units = int(days_halted * daily_rate)
                    margin_loss = lost_units * margin
                    penalty_cost = days_halted * sla_pen
                    total_prod_risk = margin_loss + penalty_cost
                    total_financial_exposure += total_prod_risk

                    trace.impacted_products.append({
                        "product_id": pr_id,
                        "product_name": prod.get("name"),
                        "plant_id": plant_id,
                        "limiting_part": p_id,
                        "production_halt_days": days_halted,
                        "delayed_finished_units": lost_units,
                        "revenue_margin_risk_usd": round(margin_loss, 2),
                        "contract_penalty_risk_usd": round(penalty_cost, 2),
                        "total_exposure_usd": round(total_prod_risk, 2),
                    })

        # Assembly Plants impacted
        for pl_id in affected_plant_ids:
            for plant in self.dataset.inventory_raw.get("assembly_plants", []):
                if plant.get("plant_id") == pl_id:
                    trace.impacted_plants.append(plant)

        trace.total_financial_exposure_usd = total_financial_exposure

        # Determine overall Severity Level
        if has_critical_stockout and total_financial_exposure > 250000.0:
            trace.severity = "CRITICAL"
            trace.summary_reason = (
                f"Critical supply shortfall! Estimated disruption duration ({duration_days:.1f}d) exceeds "
                f"inventory runway ({earliest_stockout:.1f}d). Production halt expected at "
                f"{', '.join(affected_plant_ids)} with ${total_financial_exposure:,.0f} revenue and penalty exposure."
            )
        elif has_critical_stockout:
            trace.severity = "HIGH"
            trace.summary_reason = (
                f"High impact disruption: Disruption duration ({duration_days:.1f}d) exceeds component safety runway "
                f"({earliest_stockout:.1f}d). Downstream production line throttle required."
            )
        elif trace.delayed_shipments or trace.directly_affected_suppliers:
            trace.severity = "MEDIUM"
            trace.summary_reason = (
                f"Moderate disruption: Supplier or transit shipment affected ({duration_days:.1f}d delay), "
                f"but buffer stock ({earliest_stockout:.1f}d) is sufficient to absorb the initial window without immediate plant shutdown."
            )
        else:
            trace.severity = "LOW"
            trace.summary_reason = "Minor disruption identified; operational impact is minimal and fully buffered."

        return trace
