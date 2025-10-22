"""
Property Valuation Agent

Extracts and summarizes property valuation information from semantic JSON files.
Focuses on: appraisal details, property characteristics, comparable sales,
valuation methods, and property condition.

Usage:
    python agents/property_valuation_agent.py <loan_id>
    
Example:
    python agents/property_valuation_agent.py 1000182227
"""

import os
import sys
import json
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Initialize Azure OpenAI client
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

client = AzureOpenAI(
    api_key=subscription_key,
    api_version=api_version,
    azure_endpoint=endpoint
)


def load_semantic_json(loan_id):
    """Load all semantic JSON files for a loan."""
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"❌ Semantic JSON directory not found: {semantic_dir}")
        return {}
    
    semantic_docs = {}
    for json_file in semantic_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                doc_type = data.get('document_type', 'unknown')
                # Focus on appraisal and property-related documents
                if any(keyword in doc_type.lower() or keyword in json_file.stem.lower() 
                       for keyword in ['appraisal', 'valuation', 'property', 'avm', 'bpo']):
                    semantic_docs[json_file.stem] = data
        except Exception as e:
            print(f"⚠️  Error loading {json_file.name}: {e}")
    
    return semantic_docs


def analyze_valuation(loan_id="1000182227"):
    """
    Analyze property valuation information from semantic JSON files.
    """
    
    print("=" * 80)
    print(f"Property Valuation Analysis - Loan {loan_id}")
    print("=" * 80)
    print()
    
    # Load semantic data
    print("📁 Loading valuation-related semantic JSON files...")
    semantic_docs = load_semantic_json(loan_id)
    
    if not semantic_docs:
        print("❌ No appraisal/valuation documents found!")
        print("   Looking for any semantic JSON with property data...")
        # Fallback: load all semantic docs
        semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
        for json_file in semantic_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    semantic_docs[json_file.stem] = data
            except Exception as e:
                continue
    
    print(f"✅ Loaded {len(semantic_docs)} documents")
    print()
    print("=" * 80)
    print("🔍 Analyzing property valuation...")
    print("=" * 80)
    print()
    
    # Build comprehensive prompt
    prompt = f"""You are a Chief Appraiser and Property Valuation Expert reviewing mortgage loan collateral.

SEMANTIC LOAN DOCUMENTS:
{json.dumps(semantic_docs, indent=2)}

YOUR TASK:
Extract and summarize ALL property valuation and appraisal information from the documents. Provide a comprehensive valuation analysis.

OUTPUT FORMAT (JSON only, no markdown):
{{
  "loan_number": "...",
  "property_address": {{
    "street": "...",
    "city": "...",
    "state": "...",
    "zip": "...",
    "county": "...",
    "legal_description": "..."
  }},
  "appraisal_details": {{
    "appraisal_type": "Full Interior | Desktop | Drive-by | AVM | BPO | Exterior Only",
    "valuation_method": "Sales Comparison | Cost Approach | Income Approach | AVM Algorithm",
    "appraised_value": 0,
    "appraisal_date": "...",
    "effective_date": "...",
    "appraiser_name": "...",
    "appraiser_license": "...",
    "appraiser_company": "...",
    "report_type": "URAR 1004 | 2055 Exterior | Desktop | AVM Report | etc.",
    "intended_use": "Purchase | Refinance | HELOC",
    "appraisal_ordered_by": "...",
    "review_status": "Accepted | Pending Review | Revised"
  }},
  "property_characteristics": {{
    "property_type": "Single Family | Condo | Townhouse | 2-4 Unit | PUD | etc.",
    "year_built": 0,
    "square_feet_gla": 0,
    "lot_size_sf": 0,
    "lot_size_acres": 0,
    "bedrooms": 0,
    "bathrooms": 0,
    "stories": 0,
    "garage": "None | 1-car | 2-car | 3-car | Attached | Detached",
    "basement": "None | Finished | Unfinished | Partial",
    "pool": "Yes | No",
    "condition": "Excellent | Good | Average | Fair | Poor",
    "quality": "High | Good | Average | Fair | Low",
    "construction_type": "Wood Frame | Brick | Stucco | etc.",
    "roof_type": "...",
    "heating_cooling": "...",
    "special_features": ["..."]
  }},
  "site_information": {{
    "zoning": "...",
    "flood_zone": "...",
    "utilities": ["Electric", "Gas", "Water", "Sewer", "etc."],
    "access": "Public Road | Private Road | etc.",
    "topography": "Level | Sloped | etc.",
    "view": "...",
    "location_rating": "Urban | Suburban | Rural"
  }},
  "comparable_sales": [
    {{
      "comp_number": 1,
      "address": "...",
      "distance_to_subject": "...",
      "sale_price": 0,
      "sale_date": "...",
      "square_feet": 0,
      "bedrooms": 0,
      "bathrooms": 0,
      "adjustments": {{
        "total_adjustments": 0,
        "adjusted_price": 0,
        "major_adjustments": ["..."]
      }}
    }}
  ],
  "valuation_reconciliation": {{
    "sales_comparison_value": 0,
    "cost_approach_value": 0,
    "income_approach_value": 0,
    "final_opinion_of_value": 0,
    "as_is_value": 0,
    "as_completed_value": 0,
    "approach_used": "Sales Comparison | Cost | Income | Multiple Approaches"
  }},
  "property_condition": {{
    "overall_condition": "C1 | C2 | C3 | C4 | C5 | C6",
    "condition_description": "...",
    "deferred_maintenance": "Yes | No",
    "repairs_needed": ["..."],
    "adverse_conditions": ["..."],
    "extraordinary_assumptions": ["..."],
    "hypothetical_conditions": ["..."]
  }},
  "marketability": {{
    "days_on_market": 0,
    "marketing_time": "...",
    "exposure_time": "...",
    "market_conditions": "Declining | Stable | Increasing",
    "supply_demand": "Undersupply | Balanced | Oversupply",
    "subject_marketability": "Excellent | Good | Average | Fair | Poor"
  }},
  "neighborhood_analysis": {{
    "neighborhood_name": "...",
    "predominant_occupancy": "Owner | Tenant | Vacant",
    "property_values": "Declining | Stable | Increasing",
    "demand_supply": "Shortage | In Balance | Over Supply",
    "growth_rate": "Rapid | Stable | Slow",
    "location_factor": "Urban | Suburban | Rural",
    "built_up": "Over 75% | 25-75% | Under 25%",
    "employment_stability": "Declining | Stable | Increasing"
  }},
  "valuation_strengths": [
    "List positive valuation factors..."
  ],
  "valuation_concerns": [
    "List negative valuation factors or risks..."
  ],
  "underwriting_notes": {{
    "property_meets_guidelines": true/false,
    "requires_repairs": true/false,
    "subject_to_completion": true/false,
    "appraisal_within_90_days": true/false,
    "appraiser_licensed": true/false,
    "comps_appropriate": true/false,
    "value_supportable": true/false,
    "ltv_acceptable": true/false,
    "recommendation": "Accept | Accept with Conditions | Reject | Order New Appraisal",
    "conditions": ["List any valuation-related conditions..."]
  }},
  "analyst_summary": "Comprehensive narrative summary of the property valuation, highlighting the appraisal methodology, property characteristics, comparable sales analysis, market conditions, and any concerns or extraordinary items. Include professional opinion on value supportability."
}}

Be thorough and precise. Extract ALL property and valuation details found in the documents."""

    # Call LLM
    print("⏳ Analyzing valuation data (this may take 30-45 seconds)...")
    
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system", 
                "content": "You are a Chief Appraiser and Property Valuation Expert with expertise in residential mortgage appraisals. Output only valid JSON with comprehensive valuation analysis."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=16000
    )
    
    # Parse response
    valuation_analysis = json.loads(response.choices[0].message.content)
    
    # Add metadata
    valuation_analysis['_metadata'] = {
        'analysis_date': datetime.now().isoformat(),
        'loan_id': loan_id,
        'documents_analyzed': len(semantic_docs),
        'analyzing_model': deployment,
        'agent': 'property_valuation_agent'
    }
    
    # Save output
    output_dir = Path(f"loan_docs/{loan_id}/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"valuation_analysis_{loan_id}_{timestamp}.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(valuation_analysis, f, indent=2, ensure_ascii=False)
    
    # Display results
    print()
    print("=" * 80)
    print("✅ VALUATION ANALYSIS COMPLETE!")
    print("=" * 80)
    print(f"📄 Saved to: {output_path}")
    print()
    
    # Summary
    property_address = valuation_analysis.get('property_address', {})
    print("📊 PROPERTY SUMMARY:")
    print(f"\n   📍 Address: {property_address.get('street', 'N/A')}")
    print(f"      {property_address.get('city', '')}, {property_address.get('state', '')} {property_address.get('zip', '')}")
    
    appraisal = valuation_analysis.get('appraisal_details', {})
    print(f"\n   📋 Appraisal Type: {appraisal.get('appraisal_type', 'N/A')}")
    print(f"   📅 Appraisal Date: {appraisal.get('appraisal_date', 'N/A')}")
    print(f"   💰 Appraised Value: ${appraisal.get('appraised_value', 0):,.0f}")
    
    if appraisal.get('appraiser_name'):
        print(f"   👤 Appraiser: {appraisal.get('appraiser_name')} (Lic: {appraisal.get('appraiser_license', 'N/A')})")
    
    property_chars = valuation_analysis.get('property_characteristics', {})
    print(f"\n   🏠 Property Type: {property_chars.get('property_type', 'N/A')}")
    print(f"   📐 Square Feet: {property_chars.get('square_feet_gla', 0):,}")
    print(f"   🛏️  Bedrooms: {property_chars.get('bedrooms', 0)} | 🚿 Bathrooms: {property_chars.get('bathrooms', 0)}")
    print(f"   📆 Year Built: {property_chars.get('year_built', 'N/A')}")
    print(f"   ⭐ Condition: {property_chars.get('condition', 'N/A')}")
    
    site = valuation_analysis.get('site_information', {})
    if site.get('flood_zone'):
        print(f"\n   🌊 Flood Zone: {site.get('flood_zone', 'N/A')}")
    
    comps = valuation_analysis.get('comparable_sales', [])
    if comps:
        print(f"\n   📊 Comparable Sales: {len(comps)}")
        for comp in comps[:3]:
            print(f"      Comp {comp.get('comp_number', '?')}: ${comp.get('sale_price', 0):,} | {comp.get('square_feet', 0):,} SF | {comp.get('sale_date', 'N/A')}")
    
    condition = valuation_analysis.get('property_condition', {})
    print(f"\n   🔍 Overall Condition: {condition.get('overall_condition', 'N/A')}")
    if condition.get('repairs_needed'):
        print(f"   🔧 Repairs Needed: {len(condition.get('repairs_needed', []))} items")
    
    market = valuation_analysis.get('marketability', {})
    if market.get('market_conditions'):
        print(f"\n   📈 Market Conditions: {market.get('market_conditions', 'N/A')}")
        print(f"   🎯 Marketability: {market.get('subject_marketability', 'N/A')}")
    
    uw_notes = valuation_analysis.get('underwriting_notes', {})
    print(f"\n   ✅ Value Supportable: {'Yes' if uw_notes.get('value_supportable') else 'No'}")
    print(f"   📝 Recommendation: {uw_notes.get('recommendation', 'N/A')}")
    
    # Strengths and Concerns
    strengths = valuation_analysis.get('valuation_strengths', [])
    if strengths:
        print(f"\n   ✨ Valuation Strengths ({len(strengths)}):")
        for strength in strengths[:3]:
            print(f"      • {strength}")
    
    concerns = valuation_analysis.get('valuation_concerns', [])
    if concerns:
        print(f"\n   ⚠️  Valuation Concerns ({len(concerns)}):")
        for concern in concerns[:3]:
            print(f"      • {concern}")
    
    conditions = uw_notes.get('conditions', [])
    if conditions:
        print(f"\n   📋 Conditions ({len(conditions)}):")
        for condition in conditions[:3]:
            print(f"      • {condition}")
    
    print()
    print("=" * 80)
    
    return valuation_analysis


if __name__ == "__main__":
    if len(sys.argv) > 1:
        loan_id = sys.argv[1]
    else:
        loan_id = "1000182227"
    
    analyze_valuation(loan_id)
