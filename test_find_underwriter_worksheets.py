"""
Test Script: Find Underwriter Income Calculation Worksheets

Uses LLM to intelligently scan semantic_json files to identify:
1. Income calculation worksheets created by underwriters
2. Underwriter comments and analysis
3. DU/LP/AUS findings that show calculated income
4. VOE (Verification of Employment) with income verification
5. Any other underwriter work products showing income calculations

Usage:
    python test_find_underwriter_worksheets.py <loan_id>
    
Example:
    python test_find_underwriter_worksheets.py 1000175957
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from openai import AzureOpenAI
from dotenv import load_dotenv
import os
import asyncio
from datetime import datetime

# Fix console encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

client = AzureOpenAI(
    api_key=subscription_key,
    api_version=api_version,
    azure_endpoint=endpoint
)


async def classify_document_as_uw_artifact(file_path: Path, file_data: dict) -> Dict[str, Any]:
    """
    Send a single semantic JSON file to LLM to determine if it's an underwriter artifact.
    
    Returns classification with details.
    """
    
    metadata = file_data.get('metadata', {})
    semantic_content = file_data.get('semantic_content', {})
    
    prompt = f"""You are analyzing a loan document to determine if it is an UNDERWRITER WORK PRODUCT.

**DOCUMENT FILE:** {file_path.name}

**DOCUMENT METADATA:**
{json.dumps(metadata, indent=2)}

**SEMANTIC CONTENT:**
{json.dumps(semantic_content, indent=2)}

**YOUR TASK:**

Analyze this document and determine if it is an **underwriter-created artifact** or analysis. We are specifically looking for:

1. **Income Calculation Worksheets** - Where underwriter calculated qualifying monthly income
2. **Underwriter Comments/Notes** - Written analysis, conditions, or findings
3. **AUS Findings** (Desktop Underwriter/Loan Prospector) - Automated underwriting results
4. **VOE/VOD** (Verification of Employment/Deposit) - Income/employment verification
5. **Underwriting Conditions** - Requirements set by underwriter
6. **Analysis Spreadsheets** - Any calculations or analysis done by underwriter

**IMPORTANT DISTINCTIONS:**

- **YES** = Document created BY underwriter or contains underwriter analysis/calculations
- **NO** = Primary source documents FROM borrower (paystubs, W2s, bank statements, tax returns)
- **NO** = Form 1003 (application filled out by borrower/loan officer)
- **NO** = Appraisals, title docs, insurance policies (third-party documents)

**WHAT WE CARE ABOUT:**

If this IS an underwriter artifact, extract:
- Type of artifact (income worksheet, condition, comment, AUS finding, etc.)
- Any calculated income amounts mentioned
- Underwriter comments or analysis text
- Conditions or requirements stated
- Date/version information

**RESPONSE FORMAT:**

Return JSON with this structure:

{{
  "is_underwriter_artifact": true/false,
  "artifact_type": "income_worksheet" | "uw_comment" | "aus_finding" | "voe" | "condition" | "analysis" | "not_applicable",
  "confidence": "high" | "medium" | "low",
  "contains_income_calculation": true/false,
  "calculated_income_amount": null or number (monthly income if mentioned),
  "underwriter_comments": "extracted comments" or null,
  "conditions_stated": ["condition 1", "condition 2"] or [],
  "key_findings": "brief summary of what underwriter analyzed/concluded",
  "reason": "why this is/isn't an underwriter artifact"
}}

Return ONLY valid JSON."""

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert mortgage underwriter who can identify underwriter work products and analysis."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=2000
        )
        
        classification = json.loads(response.choices[0].message.content)
        classification['file_name'] = file_path.name
        classification['file_path'] = str(file_path)
        
        return classification
        
    except Exception as e:
        print(f"  ⚠️  Error classifying {file_path.name}: {e}")
        return {
            'file_name': file_path.name,
            'file_path': str(file_path),
            'is_underwriter_artifact': False,
            'artifact_type': 'error',
            'confidence': 'low',
            'error': str(e)
        }


async def scan_for_underwriter_artifacts(loan_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Scan semantic_json files using LLM to identify underwriter artifacts.
    
    Returns:
        Dictionary with categories of underwriter work products
    """
    
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"❌ Semantic JSON directory not found: {semantic_dir}")
        return {}
    
    print(f"\n{'='*80}")
    print(f"🔍 SCANNING FOR UNDERWRITER WORK PRODUCTS (LLM ANALYSIS)")
    print(f"{'='*80}\n")
    print(f"📁 Directory: {semantic_dir}")
    
    all_files = list(semantic_dir.glob("*.json"))
    print(f"📋 Total semantic JSON files: {len(all_files)}\n")
    print(f"🤖 Sending each file to LLM for intelligent classification...")
    print(f"   Model: {deployment}")
    print(f"   This may take a few minutes...\n")
    
    # Categories to collect results
    categories = {
        'income_worksheets': [],
        'underwriter_comments': [],
        'aus_findings': [],
        'voe_vod': [],
        'conditions': [],
        'analysis_documents': [],
        'other_uw_artifacts': []
    }
    
    # Process files in batches to avoid rate limits
    batch_size = 5
    all_classifications = []
    
    for i in range(0, len(all_files), batch_size):
        batch = all_files[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1} ({len(batch)} files)...")
        
        tasks = []
        for json_file in batch:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                tasks.append(classify_document_as_uw_artifact(json_file, data))
            except Exception as e:
                print(f"  ⚠️  Error reading {json_file.name}: {e}")
                continue
        
        # Process batch concurrently
        batch_results = await asyncio.gather(*tasks)
        all_classifications.extend(batch_results)
        
        # Small delay between batches to be nice to API
        if i + batch_size < len(all_files):
            await asyncio.sleep(1)
    
    print(f"\n✅ Completed LLM classification of all files\n")
    print(f"{'='*80}")
    print("📊 CLASSIFICATION RESULTS")
    print(f"{'='*80}\n")
    
    # Categorize results
    for classification in all_classifications:
        if not classification.get('is_underwriter_artifact', False):
            continue
        
        artifact_type = classification.get('artifact_type', 'other')
        
        # Print findings
        print(f"  ✓ {classification['file_name']}")
        print(f"    Type: {artifact_type} ({classification.get('confidence', 'unknown')} confidence)")
        
        if classification.get('contains_income_calculation'):
            income = classification.get('calculated_income_amount')
            if income:
                print(f"    💰 Income Found: ${income:,.2f}/month")
            else:
                print(f"    💰 Contains income calculation")
        
        if classification.get('underwriter_comments'):
            comment = classification['underwriter_comments'][:100]
            print(f"    💬 Comment: {comment}...")
        
        if classification.get('key_findings'):
            finding = classification['key_findings'][:100]
            print(f"    📝 Finding: {finding}...")
        
        print()
        
        # Categorize
        if 'income' in artifact_type.lower() and 'worksheet' in artifact_type.lower():
            categories['income_worksheets'].append(classification)
        elif artifact_type == 'uw_comment':
            categories['underwriter_comments'].append(classification)
        elif artifact_type == 'aus_finding':
            categories['aus_findings'].append(classification)
        elif artifact_type == 'voe':
            categories['voe_vod'].append(classification)
        elif artifact_type == 'condition':
            categories['conditions'].append(classification)
        elif artifact_type == 'analysis':
            categories['analysis_documents'].append(classification)
        else:
            categories['other_uw_artifacts'].append(classification)
    
    return categories


def print_summary(categories: Dict[str, List[Dict[str, Any]]]):
    """Print a summary of findings."""
    
    print(f"\n{'='*80}")
    print(f"� SUMMARY OF UNDERWRITER ARTIFACTS FOUND")
    print(f"{'='*80}\n")
    
    total_artifacts = sum(len(items) for items in categories.values())
    
    if total_artifacts == 0:
        print("❌ No underwriter artifacts found")
        return
    
    print(f"✅ Found {total_artifacts} underwriter artifacts:\n")
    
    for category, items in categories.items():
        if items:
            category_label = category.replace('_', ' ').title()
            print(f"  • {category_label}: {len(items)} file(s)")
    
    print(f"\n{'='*80}")
    print("� DETAILED FINDINGS")
    print(f"{'='*80}\n")
    
    # Show detailed info for most relevant categories
    if categories['income_worksheets']:
        print("💰 INCOME WORKSHEETS:")
        print("-" * 80)
        for item in categories['income_worksheets']:
            print(f"\n  📄 {item['file_name']}")
            print(f"     Confidence: {item.get('confidence', 'unknown')}")
            if item.get('calculated_income_amount'):
                print(f"     💵 Calculated Income: ${item['calculated_income_amount']:,.2f}/month")
            if item.get('underwriter_comments'):
                print(f"     💬 UW Comments: {item['underwriter_comments'][:200]}")
            if item.get('key_findings'):
                print(f"     📝 Key Findings: {item['key_findings'][:200]}")
        print()
    
    if categories['underwriter_comments']:
        print("💬 UNDERWRITER COMMENTS:")
        print("-" * 80)
        for item in categories['underwriter_comments']:
            print(f"\n  � {item['file_name']}")
            print(f"     Confidence: {item.get('confidence', 'unknown')}")
            if item.get('underwriter_comments'):
                print(f"     💬 Comment: {item['underwriter_comments'][:200]}")
            if item.get('key_findings'):
                print(f"     📝 Finding: {item['key_findings'][:200]}")
        print()
    
    if categories['aus_findings']:
        print("🤖 AUTOMATED UNDERWRITING SYSTEM (DU/LP) FINDINGS:")
        print("-" * 80)
        for item in categories['aus_findings']:
            print(f"\n  📄 {item['file_name']}")
            print(f"     Confidence: {item.get('confidence', 'unknown')}")
            if item.get('key_findings'):
                print(f"     📝 Findings: {item['key_findings'][:200]}")
        print()
    
    if categories['voe_vod']:
        print("✅ VERIFICATION OF EMPLOYMENT/DEPOSIT:")
        print("-" * 80)
        for item in categories['voe_vod']:
            print(f"\n  📄 {item['file_name']}")
            print(f"     Confidence: {item.get('confidence', 'unknown')}")
            if item.get('calculated_income_amount'):
                print(f"     💵 Verified Income: ${item['calculated_income_amount']:,.2f}/month")
            if item.get('key_findings'):
                print(f"     📝 Findings: {item['key_findings'][:200]}")
        print()
    
    if categories['conditions']:
        print("� UNDERWRITER CONDITIONS:")
        print("-" * 80)
        for item in categories['conditions']:
            print(f"\n  📄 {item['file_name']}")
            print(f"     Confidence: {item.get('confidence', 'unknown')}")
            if item.get('conditions_stated'):
                print(f"     📋 Conditions:")
                for cond in item['conditions_stated'][:3]:  # Show first 3
                    print(f"        - {cond}")
            if item.get('key_findings'):
                print(f"     📝 Finding: {item['key_findings'][:200]}")
        print()


def save_results(loan_id: str, categories: Dict[str, List[Dict[str, Any]]]):
    """Save results to JSON file."""
    
    output_dir = Path(f"loan_docs/{loan_id}/income_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "underwriter_artifacts_scan.json"
    
    # Convert Path objects to strings for JSON serialization
    serializable_categories = {}
    for category, items in categories.items():
        serializable_categories[category] = items
    
    result = {
        'loan_id': loan_id,
        'scan_date': str(Path.cwd()),  # Just as placeholder
        'total_artifacts': sum(len(items) for items in categories.values()),
        'categories': serializable_categories
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"💾 Results saved to: {output_file}")
    print(f"{'='*80}\n")


def main():
    """Main execution function."""
    
    if len(sys.argv) < 2:
        print("Usage: python test_find_underwriter_worksheets.py <loan_id>")
        print("Example: python test_find_underwriter_worksheets.py 1000175957")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    
    print(f"\n{'='*80}")
    print(f"🔍 UNDERWRITER ARTIFACTS SCANNER (LLM-POWERED)")
    print(f"{'='*80}")
    print(f"\nLoan ID: {loan_id}")
    
    # Scan for artifacts using LLM
    categories = asyncio.run(scan_for_underwriter_artifacts(loan_id))
    
    if not categories:
        print("\n❌ No artifacts found or directory doesn't exist")
        sys.exit(1)
    
    # Print summary
    print_summary(categories)
    
    # Save results
    save_results(loan_id, categories)
    
    print("\n✅ SCAN COMPLETE!\n")


if __name__ == "__main__":
    main()
