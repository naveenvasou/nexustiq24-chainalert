"""
Data loading and tabular normalization pipeline for ChainAlert supply chain network.
Loads supplier registries, multi-tier BOM structures, facility inventories, and active transit shipments.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd


class SupplyChainDataset:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.suppliers_raw: List[Dict[str, Any]] = []
        self.inventory_raw: Dict[str, Any] = {}
        self.sample_notices: List[Dict[str, Any]] = []

        # Pandas DataFrames for tabular aggregations and metrics
        self.suppliers_df: Optional[pd.DataFrame] = None
        self.inventory_df: Optional[pd.DataFrame] = None
        self.products_df: Optional[pd.DataFrame] = None
        self.plants_df: Optional[pd.DataFrame] = None
        self.shipments_df: Optional[pd.DataFrame] = None

        self._load_all()

    def _load_all(self):
        suppliers_file = self.data_dir / "suppliers.json"
        if suppliers_file.exists():
            with open(suppliers_file, "r", encoding="utf-8") as f:
                self.suppliers_raw = json.load(f)
            self.suppliers_df = pd.DataFrame(self.suppliers_raw)

        inv_file = self.data_dir / "inventory_and_routes.json"
        if inv_file.exists():
            with open(inv_file, "r", encoding="utf-8") as f:
                self.inventory_raw = json.load(f)

            if "inventory" in self.inventory_raw:
                self.inventory_df = pd.DataFrame(self.inventory_raw["inventory"])
                if not self.inventory_df.empty:
                    self.inventory_df["runway_days"] = (
                        self.inventory_df["on_hand"] / self.inventory_df["daily_burn"]
                    ).round(1)
                    self.inventory_df["safety_buffer_ratio"] = (
                        self.inventory_df["on_hand"] / self.inventory_df["safety_stock"]
                    ).round(2)

            if "products" in self.inventory_raw:
                self.products_df = pd.DataFrame(self.inventory_raw["products"])

            if "assembly_plants" in self.inventory_raw:
                self.plants_df = pd.DataFrame(self.inventory_raw["assembly_plants"])

            if "in_transit_shipments" in self.inventory_raw:
                self.shipments_df = pd.DataFrame(self.inventory_raw["in_transit_shipments"])

        notices_file = self.data_dir / "sample_notices.json"
        if notices_file.exists():
            with open(notices_file, "r", encoding="utf-8") as f:
                self.sample_notices = json.load(f)

    def get_supplier_by_id(self, supplier_id: str) -> Optional[Dict[str, Any]]:
        for sup in self.suppliers_raw:
            if sup.get("id") == supplier_id:
                return sup
        return None

    def get_suppliers_for_part(self, part_id: str) -> List[Dict[str, Any]]:
        matched = []
        for sup in self.suppliers_raw:
            for p in sup.get("parts_supplied", []):
                if p.get("part_id") == part_id:
                    matched.append(sup)
        return matched

    def get_inventory_for_part(self, part_id: str) -> Optional[Dict[str, Any]]:
        for item in self.inventory_raw.get("inventory", []):
            if item.get("part_id") == part_id:
                return item
        return None

    def get_products_using_part(self, part_id: str) -> List[Dict[str, Any]]:
        matched = []
        for prod in self.inventory_raw.get("products", []):
            if part_id in prod.get("bom_parts", []):
                matched.append(prod)
        return matched

    def get_shipments_by_port(self, port_keyword: str) -> List[Dict[str, Any]]:
        port_kw = port_keyword.lower()
        matched = []
        for ship in self.inventory_raw.get("in_transit_shipments", []):
            origin = ship.get("origin_port", "").lower()
            dest = ship.get("destination_hub", "").lower()
            lane = ship.get("transit_lane", "").lower()
            carrier = ship.get("carrier", "").lower()
            if port_kw in origin or port_kw in dest or port_kw in lane or port_kw in carrier:
                matched.append(ship)
        return matched

    def get_summary_metrics(self) -> Dict[str, Any]:
        total_suppliers = len(self.suppliers_raw)
        total_products = len(self.inventory_raw.get("products", []))
        total_inventory_items = len(self.inventory_raw.get("inventory", []))
        active_shipments = len(self.inventory_raw.get("in_transit_shipments", []))

        # Calculate average inventory runway
        avg_runway = 0.0
        if self.inventory_df is not None and not self.inventory_df.empty:
            avg_runway = float(self.inventory_df["runway_days"].mean())

        return {
            "total_suppliers": total_suppliers,
            "total_products": total_products,
            "total_inventory_items": total_inventory_items,
            "active_in_transit_shipments": active_shipments,
            "average_runway_days": round(avg_runway, 1),
        }


def load_supply_chain_data(data_dir: str = "data") -> SupplyChainDataset:
    return SupplyChainDataset(data_dir=data_dir)
