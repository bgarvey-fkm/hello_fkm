"""
Find Underwriter Income Analysis - Two-Pass Approach
Pass 1: Classify each file individually (send complete file content)
Pass 2: Extract income from identified worksheets
"""
import os
import json
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Load environment and create client
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_KEY")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=api_key,
)

def load_all_semantic_json(loan_id):
    """Load all semantic JSON files for a loan"""
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"❌ No semantic JSON directory found for loan {loan_id}")
        return []
    
    files = []
    for json_file in semantic_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                files.append(data)  # Send complete file
        except Exception as e:
            print(f"⚠️  Error loading {json_file.name}: {e}")
    
    return files

def classify_single_file(file_data, filename):
    """Send COMPLETE file to LLM to determine if it's an underwriter income worksheet"""
    
    prompt = f"""Analyze this COMPLETE document to determine if it is an underwriter income calculation or worksheet.

COMPLETE DOCUMENT DATA:
{json.dumps(file_data, indent=2)}

Is this document an underwriter income worksheet, income calculation, or similar work product created by an underwriter to calculate qualifying monthly income?

Look for:
- Income worksheets (Excel files with calculations)
- Underwriter notes about income
- Income calculation forms
- DTI calculation worksheets
- Documents showing how monthly income was derived

RESPOND IN JSON:
{{
  "is_underwriter_income_worksheet": true/false,
  "confidence": "high/medium/low",
  "reason": "brief explanation"
}}
"""
    
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are an expert at identifying underwriter income worksheets. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=500
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        return {"is_underwriter_income_worksheet": False, "confidence": "low", "reason": f"Error: {str(e)[:100]}"}


def analyze_underwriter_worksheets(loan_id, worksheet_files):
    """Send all COMPLETE identified worksheets to LLM to extract income calculations"""
    
    prompt = f"""Analyze these {len(worksheet_files)} COMPLETE underwriter income worksheets for loan {loan_id}.

Extract:
1. The monthly gross qualifying income calculated by the underwriter
2. Detailed explanation of how they calculated it
3. Any underwriter comments or notes
4. Income breakdown if available

COMPLETE WORKSHEET FILES:
{json.dumps(worksheet_files, indent=2)}

RESPOND IN JSON:
{{
  "monthly_gross_income": <dollar amount or null>,
  "calculation_method": "detailed step-by-step explanation",
  "underwriter_comments": "any notes found",
  "income_breakdown": {{
    "base_income": <amount or null>,
    "overtime": <amount or null>,
    "bonus": <amount or null>,
    "commission": <amount or null>,
    "other": <amount or null>
  }},
  "source_documents": ["filename1", "filename2"]
}}
"""
    
    print(f"\n🔍 Step 2: Extracting income from {len(worksheet_files)} worksheet(s)...")
    
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are an expert at analyzing underwriter income calculations. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=4000
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        print(f"❌ Error analyzing worksheets: {e}")
        return None


def find_underwriter_income(loan_id, semantic_files):
    """Two-pass analysis: 1) Classify each COMPLETE file, 2) Extract income from worksheets"""
    
    print(f"\n" + "="*80)
    print(f"🔍 PASS 1: CLASSIFYING {len(semantic_files)} FILES")
    print("="*80)
    
    # Pass 1: Classify each complete file individually
    underwriter_worksheets = []
    for i, file in enumerate(semantic_files, 1):
        filename = file.get('metadata', {}).get('FileName', f'file_{i}')
        print(f"[{i}/{len(semantic_files)}] {filename[:70]:<70} ", end='')
        
        classification = classify_single_file(file, filename)
        
        if classification['is_underwriter_income_worksheet']:
            print(f"✅ WORKSHEET ({classification['confidence']})")
            underwriter_worksheets.append(file)
        else:
            print(f"❌")
    
    if not underwriter_worksheets:
        print("\n❌ No underwriter income worksheets found")
        return {
            "underwriter_artifacts_found": False,
            "summary": "No underwriter income worksheets identified in any files"
        }
    
    print(f"\n✅ Found {len(underwriter_worksheets)} underwriter worksheet(s)")
    
    # Pass 2: Analyze all complete worksheets together to extract income
    print(f"\n" + "="*80)
    print(f"🔍 PASS 2: ANALYZING WORKSHEETS")
    print("="*80)
    
    result = analyze_underwriter_worksheets(loan_id, underwriter_worksheets)
    
    if result:
        result['underwriter_artifacts_found'] = True
        result['num_worksheets_found'] = len(underwriter_worksheets)
        result['worksheet_filenames'] = [f.get('metadata', {}).get('FileName', 'unknown') for f in underwriter_worksheets]
    
    return result


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python find_underwriter_income.py <loan_id>")
        print("Example: python find_underwriter_income.py 1000178434")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    
    print("=" * 80)
    print("🔍 UNDERWRITER INCOME FINDER (TWO-PASS)")
    print("=" * 80)
    print(f"\nLoan ID: {loan_id}")
    print("Pass 1: Send each COMPLETE file to LLM for classification")
    print("Pass 2: Send all identified worksheets to extract income\n")
    
    # Load all complete semantic JSON files
    print("📁 Loading complete semantic JSON files...")
    semantic_files = load_all_semantic_json(loan_id)
    print(f"   Loaded {len(semantic_files)} complete files")
    
    if not semantic_files:
        print("❌ No files to analyze")
        return
    
    # Two-pass analysis
    result = find_underwriter_income(loan_id, semantic_files)
    
    if not result:
        print("❌ Analysis failed")
        return
    
    # Display results
    print("\n" + "=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)
    
    print(f"\nUnderwriter artifacts found: {'✅ YES' if result.get('underwriter_artifacts_found') else '❌ NO'}")
    
    if result.get('num_worksheets_found'):
        print(f"Number of worksheets: {result['num_worksheets_found']}")
        print(f"Worksheet files:")
        for filename in result.get('worksheet_filenames', []):
            print(f"  - {filename}")
    
    if result.get('monthly_gross_income'):
        print(f"\n💰 Monthly Gross Income: ${result['monthly_gross_income']:,.2f}")
    
    if result.get('calculation_method'):
        print(f"\n📝 Calculation Method:\n{result['calculation_method']}")
    
    if result.get('underwriter_comments'):
        print(f"\n💬 Underwriter Comments:\n{result['underwriter_comments']}")
    
    if result.get('income_breakdown'):
        breakdown = result['income_breakdown']
        print(f"\n📊 Income Breakdown:")
        for key, value in breakdown.items():
            if value:
                print(f"  {key}: ${value:,.2f}")
    
    # Save results
    output_dir = Path(f"loan_docs/{loan_id}/income_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "underwriter_income_finder.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
