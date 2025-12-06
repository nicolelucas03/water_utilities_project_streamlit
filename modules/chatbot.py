# modules/smart_assistant.py

import os
import json
import toml
import pandas as pd
from typing import Dict, Any, List

from groq import Groq
from .semantic_index import SemanticIndex

CONFIG = toml.load("secrets.toml")
GROQ_API_KEY = CONFIG["GROQ_API_KEY"]
client = Groq(api_key=GROQ_API_KEY)

DATASETS: Dict[str, Dict[str, Any]] = {
    "production_daily": {
        "path": "data/production.csv",
        "description": (
            "Daily water production volumes and operating hours for multiple countries. "
            "Each row includes production_m3, service_hours, date, and the country."
        ),
        "column_notes": """
- country: Country name (cameroon, uganda, malawi, lesotho)
- source: Water production source or facility name
- date_YYMMDD: Calendar date (YYYY/MM/DD)
- production_m3: Volume of water produced that day (m³)
- service_hours: Number of hours the production system operated that day
"""
    },

    "billing_customers": {
        "path": "data/billing.csv",
        "description": (
            "Customer-level monthly billing and payment records across multiple countries. "
            "Includes billed consumption, payments, and monthly billing dates."
        ),
        "column_notes": """
- country: Country name
- customer_id: Customer identifier
- date_MMYY: Billing month/year
- consumption_m3: Billed consumption (m³)
- billed: Amount billed
- paid: Amount paid
- source: Data source (may be empty)
- date_YYMMDD: Optional date field
"""
    },

    "all_fin_service": {
        "path":  "data/all_fin_service.csv",
        "description": (
            "City-level sanitation and water financial/service indicators across multiple countries. "
            "Includes sewer network length, complaints, revenue, staffing, and operational metrics."
        ),
        "column_notes": """
- country: Country name
- city: City name
- date_MMYY: Month/year
- sewer_length: Length of sewer network (km)
- complaints, resolved: Complaint volumes and resolutions
- blocks: Number of sewer blockages
- sewer_billed, sewer_revenue: Billed amounts and revenue collected
- opex: Operating expenditure
- san_staff, w_staff: Sanitation and water staff counts
- propoor_popn: Population covered by pro-poor programs
"""
    },

    "all_national": {
        "path": "data/all_national.csv",
        "description": (
            "National-level annual WASH budgets, staffing, water treatment plant data, and "
            "service provider indicators for multiple countries."
        ),
        "column_notes": """
- country: Country name
- date_YY: Year
- budget_allocated, san_allocation, wat_allocation: WASH budget values
- staff_cost: Staff expenditure
- water_resources: Water resource expenditures
- trained_staff: Number of trained staff
- complaint_resolution: Complaints resolved (indicator)
- registered_wtps, inspected_wtps: Water treatment plants
- total_service_providers, licensed_service_providers: Provider counts
- asset_health: Asset condition indicator
- staff_training_budget: Training allocated budget
"""
    },

    "s_access": {
        "path": "data/s_access.csv",
        "description": (
            "Sanitation access data by zone and year across multiple countries, following "
            "the JMP service ladder (safely managed, basic, limited, etc.)."
        ),
        "column_notes": """
- country: Country name
- zone: Administrative zone
- date_YY: Year
- safely_managed, basic, limited, unimproved, open_def: Population counts by sanitation service level
- *_pct: Percentage of population in each service level
- other_pct: Other/unspecified sanitation access
- popn_total: Total population
- households: Number of households
"""
    },

    "s_service": {
        "path": "data/s_service.csv",
        "description": (
            "Sanitation service delivery by zone and month across multiple countries. "
            "Includes sewer connections, sludge collection, wastewater treatment, and reuse."
        ),
        "column_notes": """
- country: Country name
- zone: Administrative zone
- date_MMYY: Month/year
- households: Number of households
- sewer_connections: Sewer connections
- public_toilets: Number of public toilets
- workforce, f_workforce: Total and female sanitation workforce
- ww_collected, ww_treated, ww_reused: Wastewater collected/treated/reused
- w_supplied: Water supplied (m³)
- hh_emptied: Households emptied
- fs_treated, fs_reused: Fecal sludge treated/reused
"""
    },

    "water_access": {
        "path": "data/water_access.csv",
        "description": (
            "Water access levels by zone across multiple countries, including safely managed, "
            "basic, limited and unimproved service levels, plus households and population totals."
        ),
        "column_notes": """
- country: Country name
- zone: Administrative zone
- safely_managed, basic, limited, unimproved, surface_water: Population by water service level
- *_pct: Percentage of population for each service level
- popn_total: Total population
- households: Number of households
- municipal_coverage: Municipal water supply coverage
"""
    },

    "water_service": {
        "path": "data/water_service.csv",
        "description": (
            "Water service quality and supply indicators by zone and month across multiple countries. "
            "Includes quality tests (chlorine/E. coli), water supplied, consumption, and capacity."
        ),
        "column_notes": """
- country: Country name
- zone: Administrative zone
- date_MMYY: Month/year
- tests_chlorine, tests_ecoli: Number of requested tests
- tests_conducted_chlorine, test_conducted_ecoli: Tests conducted
- test_passed_chlorine, tests_passed_ecoli: Tests that passed
- w_supplied: Water supplied (m³)
- total_consumption: Total water consumption (m³)
- metered: Metered consumption or metered connections
- ww_capacity: Wastewater treatment capacity
"""
    },
}



class WaterSemanticAssistant:
    """
    High-level assistant:
      - no dataset/column selection by the user
      - uses RAG + planning + execution
    """

    def __init__(self, datasets_config: Dict[str, Dict[str, Any]]):
        self.datasets_config = datasets_config
        self.tables: Dict[str, pd.DataFrame] = {}

        # load all datasets as DataFrames
        for name, cfg in datasets_config.items():
            path = cfg["path"]
            if not os.path.exists(path):
                print(f"[Assistant] Missing dataset '{name}': {path}")
                continue

            df = pd.read_csv(path)
            # keep dates as strings for now
            for col in df.columns:
                if "date" in col.lower():
                    df[col] = df[col].astype(str)
            self.tables[name] = df

        if not self.tables:
            raise RuntimeError("No datasets loaded for assistant.")

        # build / load semantic index
        self.semantic_index = SemanticIndex(datasets_config)


    def _plan_query(self, question: str) -> Dict[str, Any]:
        """
        Use Groq to turn (question + retrieved docs) into an executable plan.
        """
        retrieved = self.semantic_index.retrieve(question, top_k=8)

        # make a compact context for the LLM
        context_snippets = []
        for item in retrieved:
            meta = item["metadata"]
            prefix = meta.get("kind", "")
            dataset = meta.get("dataset", "")
            col = meta.get("column", "")
            context_snippets.append(
                f"[{prefix}] dataset={dataset}, column={col}\n{item['text']}"
            )

        context_text = "\n\n---\n\n".join(context_snippets)

        system_msg = {
    "role": "system",
    "content": (
        "You are a data analysis planner for water and sanitation datasets.\n"
        "You see:\n"
        "1) A user question.\n"
        "2) Documentation about datasets and columns.\n\n"
        "You must output ONLY a JSON object describing HOW to compute the answer.\n"
        "Do NOT include any prose explanation. JSON only.\n\n"
        "Planning rules:\n"
        "- If the user asks about percentages or coverage, prefer columns whose names contain '_pct' or 'percentage'.\n"
        "- If the question compares countries (e.g., Cameroon vs Uganda), create one metric per country,\n"
        "  using a 'country' filter where appropriate.\n"
        "- If the question asks about 'over the years' or 'on average', aggregate over all available years\n"
        "  using agg='mean' on the relevant percentage column.\n"
        "- If the user asks about a **single specific year** (e.g. 'in 2020'), either:\n"
        "    * set time_scope.type = 'year' and time_scope.year = that year, OR\n"
        "    * add a filter on the appropriate date column (e.g. column='date_YY', op='==', value=2020).\n"
        "- If the user **compares two explicit years** (e.g. '2020 compared to 2022'), create **two separate metrics**:\n"
        "    * one metric with a filter for the first year (e.g. date_YY == 2020)\n"
        "    * and one metric with a filter for the second year (e.g. date_YY == 2022)\n"
        "  In that case, you can keep time_scope.type = 'all'.\n"
        "- You must use dataset and column names exactly as seen in the context snippets.\n"
        "- Use filters to restrict by country when relevant (e.g., column='country', op='==', value='Cameroon').\n"
    )
}

        user_msg = {
            "role": "user",
            "content": f"""
USER QUESTION:
{question}

AVAILABLE CONTEXT (datasets and columns):
{context_text}

TASK:
- Decide which datasets and columns to use.
- Decide what aggregations to perform (sum, mean, etc.).
- Infer a simple time_scope if the user mentions a year or range.
- For comparisons, set comparison.type appropriately.

You MUST output JSON with this exact structure:

{{
  "time_scope": {{
    "type": "all | year | range",
    "year": 2020,
    "start_year": 2018,
    "end_year": 2020
  }},
  "metrics": [
    {{
      "name": "string_unique_key",
      "dataset": "one_of_the_dataset_names",
      "agg": "sum | mean | max | min",
      "column": "one_column_name",
      "filters": [
        {{"column": "col_name", "op": ">", "value": 0}}
      ]
    }}
  ],
  "comparison": {{
    "type": "none | which_is_greater",
    "left_metric": "name_from_metrics_or_null",
    "right_metric": "name_from_metrics_or_null"
  }}
}}

Rules:
- If the question clearly asks to compare two things, use type='which_is_greater'.
- If no comparison is needed, use type='none' and set metrics accordingly.
- filters can be an empty list if no filter is needed.
- Use dataset and column names exactly as seen in the context.
- If you're unsure about exact time, use time_scope.type = "all".

"Example for a comparison question:\n"
"Question: 'Are more Cameroonians or Ugandans served safely managed water?'\n"
"Then you might produce metrics like:\n"
"  - 'cmr_safely_managed_mean' using dataset 'water_access', column 'safely_managed_pct', agg='mean', filter country=='cameroon'\n"
"  - 'uga_safely_managed_mean' using dataset 'water_access', column 'safely_managed_pct', agg='mean', filter country=='Uganda'\n"
"and comparison.type='which_is_greater' with left_metric/right_metric pointing to those names.\n\n"

""",
        }

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[system_msg, user_msg],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_completion_tokens=500,
        )

        raw = completion.choices[0].message.content.strip()
        try:
            plan = json.loads(raw)
        except json.JSONDecodeError:
            print("[Assistant] Plan JSON decode failed, raw output:", raw)
            plan = {
                "time_scope": {"type": "all"},
                "metrics": [],
                "comparison": {"type": "none", "left_metric": None, "right_metric": None},
            }
        return plan


    def _apply_time_scope(self, df: pd.DataFrame, time_scope: Dict[str, Any]) -> pd.DataFrame:
        """Very simple year-based filtering using any 'date' column."""
        ttype = time_scope.get("type", "all")
        if ttype == "all":
            return df

        date_cols = [c for c in df.columns if "date" in c.lower()]
        if not date_cols:
            return df

        col = date_cols[0]
        s = df[col].astype(str)

        if ttype == "year":
            year = str(time_scope.get("year"))
            return df[s.str.contains(year, na=False)]

        if ttype == "range":
            start_year = int(time_scope.get("start_year"))
            end_year = int(time_scope.get("end_year"))
            mask = False
            for y in range(start_year, end_year + 1):
                mask = mask | s.str.contains(str(y), na=False)
            return df[mask]

        return df

    def _apply_filters(self, df: pd.DataFrame, filters: List[Dict[str, Any]]) -> pd.DataFrame:
        res = df
        for f in filters:
            col = f.get("column")
            op = f.get("op")
            val = f.get("value")
            if col not in res.columns:
                continue
            series = res[col]

            if op == ">":
                res = res[series > val]
            elif op == ">=":
                res = res[series >= val]
            elif op == "<":
                res = res[series < val]
            elif op == "<=":
                res = res[series <= val]
            elif op == "==":
                res = res[series == val]
            elif op == "!=":
                res = res[series != val]
        return res

    def _execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        results: Dict[str, Any] = {}

        time_scope = plan.get("time_scope", {"type": "all"})
        metrics = plan.get("metrics", [])

        for m in metrics:
            name = m["name"]
            dataset = m["dataset"]
            column = m["column"]
            agg = m["agg"]
            filters = m.get("filters", [])

            if dataset not in self.tables:
                results[name] = {"error": f"Unknown dataset {dataset}"}
                continue

            df = self.tables[dataset]

            # time filter
            df = self._apply_time_scope(df, time_scope)
            # value filters
            df = self._apply_filters(df, filters)

            if column not in df.columns:
                results[name] = {"error": f"Unknown column {column} in {dataset}"}
                continue

            series = df[column]
            # ensure numeric
            series = pd.to_numeric(series, errors="coerce")
            series = series.dropna()

            if series.empty:
                results[name] = {"error": "No data after filtering"}
                continue

            if agg == "sum":
                val = float(series.sum())
            elif agg == "mean":
                val = float(series.mean())
            elif agg == "max":
                val = float(series.max())
            elif agg == "min":
                val = float(series.min())
            else:
                results[name] = {"error": f"Unknown agg {agg}"}
                continue

            results[name] = {
                "value": val,
                "dataset": dataset,
                "column": column,
                "agg": agg,
                "filters": filters,
            }

        return results


    def _summarize(self, question: str, plan: Dict[str, Any], metric_results: Dict[str, Any]) -> str:
        summary_obj = {
            "question": question,
            "plan": plan,
            "results": metric_results,
        }

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise analyst. Given a plan and computed numbers, "
                        "explain the answer in under 150 words.\n"
                        "Rules:\n"
                        "- Explicitly say which datasets and columns were used (by name).\n"
                        "- Describe how you aggregated (e.g., 'average of safely_managed_pct over all years').\n"
                        "- If comparison.type is 'which_is_greater', clearly say which side is larger.\n"
                        "- Briefly mention any limitations (e.g., missing years) as your 'double check'.\n"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(summary_obj, indent=2),
                },
            ],
            max_completion_tokens=220,
            temperature=0.3,
        )
        return completion.choices[0].message.content.strip()

    # ---------- Public entrypoint ----------

    def answer(self, question: str) -> str:
        """
        Full pipeline:
        question -> plan -> execute -> summarize
        """
        plan = self._plan_query(question)
        metric_results = self._execute_plan(plan)
        
        # DEBUG: see what the model actually planned & computed
        print("\n📌 PLAN:")
        print(json.dumps(plan, indent=2))
        print("\n📊 METRIC RESULTS:")
        print(json.dumps(metric_results, indent=2))
        
        answer_text = self._summarize(question, plan, metric_results)
        return answer_text
    
if __name__ == "__main__":

    assistant = WaterSemanticAssistant(DATASETS)

    
    test_questions = [
        "Did sewer complaints increase or decrease in Lesotho from 2020 to 2022?", 
        "Which country conducts the most E. coli tests on average per month?", 
        "What percentage of Cameroonians had safely managed water in 2020 compared to 2022?",
        "Which country has the highest average safely managed sanitation coverage from 2018-2022?",
    ]
    
    for q in test_questions:
        print("\n" + "="*70)
        print("QUESTION:", q)
        print("-"*70)
        try:
            answer = assistant.answer(q)
            print("ANSWER:", answer)
        except Exception as e:
            print("❌ ERROR:", e)
        print("="*70)
        
        
bot = WaterSemanticAssistant(DATASETS)
