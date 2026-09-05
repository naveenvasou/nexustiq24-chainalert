"""
ChainAlert: Autonomous Supply Chain Disruption Response Engine
FastAPI application providing REST endpoints and a responsive operations dashboard.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# Supply chain subsystem imports
from data_loader import load_supply_chain_data
from graph_engine import SupplyChainGraph
from retrieval import SupplyChainRetriever
from disruption_analyzer import DisruptionAnalyzer

app = FastAPI(
    title="ChainAlert - Supply Chain Disruption Response Engine",
    description="Track 8: Supply Chain Disruption Response System",
    version="1.0.0",
)

# Initialize dataset, graph, retriever, and analyzer
dataset = load_supply_chain_data("data")
graph = SupplyChainGraph(dataset)
retriever = SupplyChainRetriever(dataset)
analyzer = DisruptionAnalyzer(dataset, graph, retriever)


class AnalyzeRequest(BaseModel):
    notice_text: Optional[str] = None
    sample_id: Optional[str] = None


@app.get("/api/status")
async def get_status():
    metrics = dataset.get_summary_metrics()
    return {
        "status": "OPERATIONAL",
        "track": 8,
        "system_name": "ChainAlert",
        "gemini_api_configured": bool(os.getenv("GEMINI_API_KEY")),
        "metrics": metrics,
    }


@app.get("/api/samples")
async def get_samples():
    return {
        "samples": dataset.sample_notices,
    }


@app.get("/api/network")
async def get_network():
    return graph.get_network_graph()


@app.post("/api/analyze")
async def analyze_notice(req: AnalyzeRequest):
    text_to_analyze = req.notice_text

    if not text_to_analyze and req.sample_id:
        for sample in dataset.sample_notices:
            if sample.get("id") == req.sample_id:
                text_to_analyze = sample.get("raw_text")
                break

    if not text_to_analyze or not text_to_analyze.strip():
        raise HTTPException(status_code=400, detail="Notice text or valid sample_id must be provided")

    result = analyzer.analyze_disruption(text_to_analyze)
    return JSONResponse(content=result)


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    metrics = dataset.get_summary_metrics()
    sample_options = "".join([
        f'<button onclick="loadSample(\'{s["id"]}\')" class="sample-btn text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-indigo-600 hover:border-indigo-500 text-slate-300 hover:text-white transition shadow-sm">{s["title"][:38]}...</button>'
        for s in dataset.sample_notices
    ])

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChainAlert - Supply Chain Disruption Response Engine (Track 8)</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        brand: {{
                            50: '#eef2ff',
                            500: '#6366f1',
                            600: '#4f46e5',
                            700: '#4338ca',
                            900: '#312e81',
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body {{ font-family: 'Inter', sans-serif; }}
        .badge-CRITICAL {{ background-color: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }}
        .badge-HIGH {{ background-color: rgba(249, 115, 22, 0.2); color: #fb923c; border: 1px solid rgba(249, 115, 22, 0.4); }}
        .badge-MEDIUM {{ background-color: rgba(234, 179, 8, 0.2); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.4); }}
        .badge-LOW {{ background-color: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }}
        .badge-NO_IMPACT {{ background-color: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen antialiased flex flex-col">
    <!-- Navbar -->
    <header class="border-b border-slate-800 bg-slate-900/70 backdrop-blur sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-400 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
                    CA
                </div>
                <div>
                    <h1 class="text-base font-bold tracking-tight text-white flex items-center gap-2">
                        ChainAlert
                        <span class="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Track 8: Supply Chain</span>
                    </h1>
                    <p class="text-xs text-slate-400">Autonomous Disruption Response & Trade-Off Engine</p>
                </div>
            </div>
            <div class="flex items-center space-x-4">
                <div class="flex items-center space-x-2 text-xs text-slate-300 bg-slate-800/80 px-3 py-1.5 rounded-full border border-slate-700/60">
                    <span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span>System Ready</span>
                </div>
            </div>
        </div>
    </header>

    <!-- Key Metrics Strip -->
    <div class="border-b border-slate-800 bg-slate-900/30">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div class="flex items-center space-x-3">
                <div class="p-2 bg-slate-800 rounded-lg text-indigo-400">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path></svg>
                </div>
                <div>
                    <p class="text-[11px] uppercase tracking-wider text-slate-400 font-medium">Multi-Tier Suppliers</p>
                    <p class="text-sm font-semibold text-white">{metrics['total_suppliers']} Global Nodes</p>
                </div>
            </div>
            <div class="flex items-center space-x-3">
                <div class="p-2 bg-slate-800 rounded-lg text-emerald-400">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"></path></svg>
                </div>
                <div>
                    <p class="text-[11px] uppercase tracking-wider text-slate-400 font-medium">Finished Products</p>
                    <p class="text-sm font-semibold text-white">{metrics['total_products']} Active Lines</p>
                </div>
            </div>
            <div class="flex items-center space-x-3">
                <div class="p-2 bg-slate-800 rounded-lg text-cyan-400">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                </div>
                <div>
                    <p class="text-[11px] uppercase tracking-wider text-slate-400 font-medium">Average Buffer Runway</p>
                    <p class="text-sm font-semibold text-white">{metrics['average_runway_days']} Days Stock</p>
                </div>
            </div>
            <div class="flex items-center space-x-3">
                <div class="p-2 bg-slate-800 rounded-lg text-amber-400">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                </div>
                <div>
                    <p class="text-[11px] uppercase tracking-wider text-slate-400 font-medium">In-Transit Freight</p>
                    <p class="text-sm font-semibold text-white">{metrics['active_in_transit_shipments']} Active POs</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Content -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        <!-- Left: Input & Notice Intake (5 cols) -->
        <section class="lg:col-span-5 flex flex-col space-y-4">
            <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl">
                <div class="flex items-center justify-between mb-3">
                    <h2 class="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
                        <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                        Disruption Notice Intake
                    </h2>
                    <span class="text-[11px] text-slate-400">Natural Language / Prose</span>
                </div>

                <!-- Sample Presets -->
                <div class="mb-3">
                    <label class="block text-[11px] font-medium text-slate-400 mb-1.5 uppercase">Test Scenarios (1-Click Load):</label>
                    <div class="flex flex-wrap gap-1.5">
                        {sample_options}
                    </div>
                </div>

                <!-- Textarea -->
                <div class="mb-4">
                    <label for="noticeInput" class="block text-xs font-medium text-slate-300 mb-1">Advisory Text or Supplier Email:</label>
                    <textarea id="noticeInput" rows="10" placeholder="Paste unstructured supplier email, weather alert, carrier notice, or port advisory..." class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono leading-relaxed resize-none"></textarea>
                </div>

                <!-- Actions -->
                <div class="flex items-center space-x-3">
                    <button id="analyzeBtn" onclick="submitAnalysis()" class="flex-1 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white font-medium py-2.5 px-4 rounded-xl text-xs transition shadow-lg shadow-indigo-600/30 flex items-center justify-center space-x-2">
                        <span id="btnText">Analyze Disruption & Generate Plans</span>
                        <svg id="spinner" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white hidden" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                        </svg>
                    </button>
                    <button onclick="clearForm()" class="px-3 py-2.5 rounded-xl border border-slate-800 bg-slate-800/60 hover:bg-slate-800 text-xs text-slate-400 hover:text-slate-200 transition">
                        Clear
                    </button>
                </div>
            </div>

            <!-- Supply Chain Network Legend -->
            <div class="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 text-xs text-slate-400">
                <h3 class="font-medium text-slate-300 mb-2 uppercase text-[11px] tracking-wider">Monitored Facilities & Hubs</h3>
                <ul class="space-y-1.5 font-mono text-[11px]">
                    <li class="flex items-center justify-between">
                        <span class="text-slate-300">Austin Advanced Robotics Plant (USA)</span>
                        <span class="text-indigo-400">40 units/day</span>
                    </li>
                    <li class="flex items-center justify-between">
                        <span class="text-slate-300">Bavaria Healthcare Center (Munich, DE)</span>
                        <span class="text-indigo-400">20 units/day</span>
                    </li>
                    <li class="flex items-center justify-between">
                        <span class="text-slate-300">Kaohsiung & Taoyuan Corridor (TW)</span>
                        <span class="text-cyan-400">Tier-1 Microcontrollers</span>
                    </li>
                    <li class="flex items-center justify-between">
                        <span class="text-slate-300">Rotterdam / Rhine Inland Waterway</span>
                        <span class="text-amber-400">Tier-2 Titanium Alloys</span>
                    </li>
                </ul>
            </div>
        </section>

        <!-- Right: Results & Ranked Mitigation Plans (7 cols) -->
        <section class="lg:col-span-7 flex flex-col space-y-4">
            <!-- Empty State Placeholder -->
            <div id="emptyState" class="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center flex flex-col items-center justify-center min-h-[420px]">
                <div class="h-16 w-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4">
                    <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                </div>
                <h3 class="text-base font-semibold text-white mb-1">Awaiting Disruption Input</h3>
                <p class="text-xs text-slate-400 max-w-md mb-6">Select one of the sample disruption scenarios on the left or paste an unstructured supplier email or carrier notice to trigger graph impact tracing.</p>
                <div class="flex gap-2 text-xs">
                    <button onclick="loadSample('NOTICE-001')" class="px-3 py-1.5 bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 rounded-lg border border-indigo-500/30 transition">Test Typhoon Kaemi (Critical)</button>
                    <button onclick="loadSample('NOTICE-005')" class="px-3 py-1.5 bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 rounded-lg border border-emerald-500/30 transition">Test Rotterdam Flowers (No Impact)</button>
                </div>
            </div>

            <!-- Analysis Output Container -->
            <div id="resultsContainer" class="hidden flex flex-col space-y-4">
                <!-- Summary Card -->
                <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl">
                    <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
                        <div class="flex items-center space-x-3">
                            <span id="severityBadge" class="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full"></span>
                            <h3 id="incidentTitle" class="text-base font-bold text-white"></h3>
                        </div>
                        <div class="text-xs text-slate-400">
                            Confidence: <span id="confidenceScore" class="font-mono text-emerald-400 font-semibold">95%</span>
                        </div>
                    </div>

                    <div class="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl mb-4 font-mono text-xs text-slate-300 leading-relaxed" id="executiveSummary">
                    </div>

                    <!-- Impact Metrics Bar -->
                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <div class="p-3 bg-slate-950/50 border border-slate-800/80 rounded-xl">
                            <p class="text-[10px] uppercase tracking-wider text-slate-400">Disruption Window</p>
                            <p id="delayDays" class="text-sm font-semibold text-amber-400 mt-0.5">0.0 Days</p>
                        </div>
                        <div class="p-3 bg-slate-950/50 border border-slate-800/80 rounded-xl">
                            <p class="text-[10px] uppercase tracking-wider text-slate-400">Earliest Stockout</p>
                            <p id="stockoutDays" class="text-sm font-semibold text-rose-400 mt-0.5">None</p>
                        </div>
                        <div class="p-3 bg-slate-950/50 border border-slate-800/80 rounded-xl">
                            <p class="text-[10px] uppercase tracking-wider text-slate-400">Affected Facilities</p>
                            <p id="affectedFacilities" class="text-sm font-semibold text-slate-200 mt-0.5">0</p>
                        </div>
                        <div class="p-3 bg-slate-950/50 border border-slate-800/80 rounded-xl">
                            <p class="text-[10px] uppercase tracking-wider text-slate-400">Financial Exposure</p>
                            <p id="financialExposure" class="text-sm font-semibold text-rose-400 mt-0.5">$0</p>
                        </div>
                    </div>
                </div>

                <!-- Mitigation Plans Section -->
                <div id="mitigationSection">
                    <div class="flex items-center justify-between mb-2">
                        <h3 class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                            <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"></path></svg>
                            Ranked Response Plans & Operational Trade-Offs
                        </h3>
                    </div>

                    <div id="plansList" class="space-y-3">
                        <!-- Populated by JavaScript -->
                    </div>
                </div>
            </div>
        </section>
    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-800 py-4 bg-slate-900/40 text-center text-xs text-slate-500">
        ChainAlert &bull; Track 8: Supply Chain Disruption Response &bull; Autonomous Hackathon Submission
    </footer>

    <script>
        let samplesCache = [];

        async function init() {{
            try {{
                const res = await fetch('/api/samples');
                const data = await res.json();
                samplesCache = data.samples || [];
            }} catch (e) {{
                console.error("Failed to load samples", e);
            }}
        }}
        init();

        function loadSample(sampleId) {{
            const sample = samplesCache.find(s => s.id === sampleId);
            if (sample) {{
                document.getElementById('noticeInput').value = sample.raw_text;
                submitAnalysis();
            }}
        }}

        function clearForm() {{
            document.getElementById('noticeInput').value = '';
            document.getElementById('resultsContainer').classList.add('hidden');
            document.getElementById('emptyState').classList.remove('hidden');
        }}

        async function submitAnalysis() {{
            const text = document.getElementById('noticeInput').value;
            if (!text.trim()) {{
                alert("Please enter a disruption notice or select a sample scenario.");
                return;
            }}

            const btnText = document.getElementById('btnText');
            const spinner = document.getElementById('spinner');
            const analyzeBtn = document.getElementById('analyzeBtn');

            btnText.textContent = "Analyzing Disruption...";
            spinner.classList.remove('hidden');
            analyzeBtn.disabled = true;

            try {{
                const res = await fetch('/api/analyze', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ notice_text: text }})
                }});
                const result = await res.json();
                renderResults(result);
            }} catch (e) {{
                alert("Error analyzing disruption: " + e.message);
            }} finally {{
                btnText.textContent = "Analyze Disruption & Generate Plans";
                spinner.classList.add('hidden');
                analyzeBtn.disabled = false;
            }}
        }}

        function renderResults(res) {{
            document.getElementById('emptyState').classList.add('hidden');
            const container = document.getElementById('resultsContainer');
            container.classList.remove('hidden');

            const parsed = res.parsed_notice || {{}};
            const trace = res.impact_trace || {{}};
            const plans = res.mitigation_plans || [];

            // Severity Badge
            const badge = document.getElementById('severityBadge');
            badge.className = "text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full badge-" + res.impact_status;
            badge.textContent = res.impact_status.replace('_', ' ');

            // Title & Executive Summary
            document.getElementById('incidentTitle').textContent = parsed.incident_title || "Disruption Incident";
            document.getElementById('executiveSummary').innerText = res.executive_summary || "";
            document.getElementById('confidenceScore').textContent = Math.round((parsed.confidence_score || 0.9) * 100) + "%";

            // Metrics
            document.getElementById('delayDays').textContent = (trace.max_delay_days || 0).toFixed(1) + " Days";
            document.getElementById('stockoutDays').textContent = trace.earliest_stockout_days ? trace.earliest_stockout_days.toFixed(1) + " Days" : "Safe";
            document.getElementById('affectedFacilities').textContent = (trace.impacted_plants ? trace.impacted_plants.length : 0) + " Plants";
            document.getElementById('financialExposure').textContent = "$" + (trace.total_financial_exposure_usd || 0).toLocaleString();

            // Render Mitigation Plans
            const plansContainer = document.getElementById('plansList');
            plansContainer.innerHTML = "";

            if (!plans || plans.length === 0) {{
                if (res.impact_status === "NO_IMPACT") {{
                    plansContainer.innerHTML = `
                        <div class="bg-emerald-950/20 border border-emerald-500/30 rounded-2xl p-6 text-center">
                            <div class="h-10 w-10 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto mb-3">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                            </div>
                            <h4 class="text-sm font-bold text-emerald-400 mb-1">No Response Action Necessary</h4>
                            <p class="text-xs text-slate-300 max-w-lg mx-auto">This incident is outside company component and carrier lanes. All existing buffer allocations and manufacturing schedules proceed normally.</p>
                        </div>
                    `;
                }} else {{
                    plansContainer.innerHTML = `<p class="text-xs text-slate-400 italic">No plans generated.</p>`;
                }}
                return;
            }}

            plans.forEach(plan => {{
                const prosList = (plan.trade_offs?.pros || []).map(p => `<li class="flex items-start gap-1.5"><span class="text-emerald-400 font-bold">&check;</span><span>${{p}}</span></li>`).join('');
                const consList = (plan.trade_offs?.cons || []).map(c => `<li class="flex items-start gap-1.5"><span class="text-rose-400 font-bold">&times;</span><span>${{c}}</span></li>`).join('');
                const stepsList = (plan.action_steps || []).map((s, idx) => `<li class="flex items-start gap-2"><span class="text-indigo-400 font-mono text-[10px] px-1.5 py-0.5 bg-slate-900 rounded">${{idx + 1}}</span><span>${{s}}</span></li>`).join('');

                const card = document.createElement('div');
                card.className = "bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden";
                card.innerHTML = `
                    <div class="flex items-start justify-between gap-3 mb-3">
                        <div class="flex items-center space-x-2">
                            <span class="h-6 w-6 rounded-lg bg-indigo-600 text-white font-bold text-xs flex items-center justify-center shadow-md">
                                #${{plan.rank}}
                            </span>
                            <h4 class="text-sm font-bold text-white">${{plan.strategy_name}}</h4>
                        </div>
                        <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                            ${{plan.strategy_type || 'STRATEGY'}}
                        </span>
                    </div>

                    <!-- Metrics Grid -->
                    <div class="grid grid-cols-3 gap-2 mb-3 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80 text-xs">
                        <div>
                            <span class="text-[10px] text-slate-400 block uppercase">Cost Delta</span>
                            <span class="font-semibold text-slate-200">+$${{(plan.cost_delta_usd || 0).toLocaleString()}}</span>
                        </div>
                        <div>
                            <span class="text-[10px] text-slate-400 block uppercase">Lead Time Saved</span>
                            <span class="font-semibold text-emerald-400">${{plan.lead_time_saved_days || 0}} Days</span>
                        </div>
                        <div>
                            <span class="text-[10px] text-slate-400 block uppercase">Residual SLA Risk</span>
                            <span class="font-semibold ${{plan.residual_sla_risk === 'Low' ? 'text-emerald-400' : (plan.residual_sla_risk === 'Medium' ? 'text-amber-400' : 'text-rose-400')}}">${{plan.residual_sla_risk}}</span>
                        </div>
                    </div>

                    <!-- Action Steps -->
                    <div class="mb-3">
                        <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Action Plan Steps:</p>
                        <ul class="text-xs text-slate-300 space-y-1">
                            ${{stepsList}}
                        </ul>
                    </div>

                    <!-- Trade-offs Grid -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3 text-xs bg-slate-950/40 p-3 rounded-xl border border-slate-800/60">
                        <div>
                            <p class="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider mb-1">Advantages / Pros:</p>
                            <ul class="text-slate-300 space-y-1">${{prosList}}</ul>
                        </div>
                        <div>
                            <p class="text-[10px] font-semibold text-rose-400 uppercase tracking-wider mb-1">Trade-Offs / Cons:</p>
                            <ul class="text-slate-300 space-y-1">${{consList}}</ul>
                        </div>
                    </div>

                    <div class="text-[11px] text-slate-400 italic">
                        <span class="font-semibold text-slate-300">Recommendation Rationale:</span> ${{plan.recommendation_rationale}}
                    </div>
                `;
                plansContainer.appendChild(card);
            }});
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
