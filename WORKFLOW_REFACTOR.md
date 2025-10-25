# Income Analysis Workflow Refactor

## Date: January 2025

## Problem Identified

The original workflow had a **subtle but critical architecture issue**:

### Original (Incorrect) Workflow:
```
1. income_scenario_classifier.py
   └─> Used simple keyword search ('W2', 'PAYSTUB', etc.)
   └─> May include/exclude wrong documents
   └─> Classified scenario based on potentially incorrect document set

2. income_analysis_agent.py
   └─> Properly filtered documents using LLM + Freddie Mac guidelines
   └─> But scenario was already classified with wrong context!
```

### The Issue:
- **Scenario classifier** used basic keyword matching → might classify based on wrong documents
- **Income analyzer** ran proper filtering → but too late, scenario already set
- This could lead to:
  - Wrong scenario classification (e.g., calling it "complex" when it's really "simple")
  - Incorrect decision tree path in income calculation
  - Inconsistent results across runs

## Solution Implemented

### Correct Workflow (After Refactoring):
```
1. income_scenario_classifier.py
   ├─> Checks if documents already have income_verification_relevant flags
   ├─> If NOT: Imports filter_income_documents_by_guidelines() from income_analysis_agent
   ├─> Runs LLM-based filtering using Freddie Mac guidelines
   ├─> Caches results to semantic JSON files (income_verification_relevant flag)
   ├─> Then uses ONLY the filtered documents for scenario classification
   └─> Outputs: income_scenario.json

2. income_analysis_agent.py
   ├─> Loads documents (flags already exist from step 1)
   ├─> Uses FAST PATH (cached flags, no LLM needed)
   ├─> Loads scenario.json
   ├─> Calculates income using decision tree + scenario context
   └─> Outputs: income_analysis_runX.json
```

## Changes Made

### File: `agents/income_scenario_classifier.py`

**Lines 189-238 (Refactored):**

```python
# Check if documents have been filtered yet
has_cached_flags = False
for doc_file in loan_docs_dir.glob("*.json"):
    try:
        with open(doc_file, 'r', encoding='utf-8') as f:
            doc = json.load(f)
            if 'income_verification_relevant' in doc:
                has_cached_flags = True
                break
    except:
        continue

# If no cached flags exist, run document filtering FIRST
if not has_cached_flags:
    print(f"\n>> No income_verification_relevant flags found - filtering documents first...")
    print(f">> Importing document filtering from income_analysis_agent...")
    
    # Import the filtering function
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from income_analysis_agent import filter_income_documents_by_guidelines
    
    # Run the filtering to populate the flags
    try:
        await filter_income_documents_by_guidelines(loan_id, refilter=False)
        print(f">> ✓ Document filtering complete - flags cached to semantic JSON files")
    except Exception as e:
        print(f">> ⚠️  Warning: Document filtering failed: {e}")
        print(f">> Falling back to keyword search...")

# Now load income documents using the cached flags
income_docs = []

for doc_file in loan_docs_dir.glob("*.json"):
    try:
        with open(doc_file, 'r', encoding='utf-8') as f:
            doc = json.load(f)
            
            # Check if this document has been classified
            if 'income_verification_relevant' in doc:
                if doc['income_verification_relevant'].get('is_relevant', False):
                    income_docs.append(doc)
            else:
                # Fallback to keyword search if filtering failed
                doc_type = doc.get('metadata', {}).get('DocPredictionType', '')
                spring_type = doc.get('metadata', {}).get('SpringDocType', '')
                if any(keyword in doc_type.upper() or keyword in spring_type.upper() 
                       for keyword in ['W2', 'W-2', 'PAYSTUB', 'PAY STUB', 'VOE', 'VERIFICATION OF EMPLOYMENT', '1099']):
                    income_docs.append(doc)
    except:
        continue
```

## Benefits

1. **Correct Document Set**: Scenario classification now uses the SAME filtered document set as income analysis
2. **Caching Efficiency**: Document filtering only runs once per loan, results cached for all future runs
3. **Consistency**: Both scenario and income calculation work from the same foundation
4. **Guideline Compliance**: LLM applies Freddie Mac guidelines to identify PRIMARY SOURCE documents
5. **Smart Fallback**: If filtering fails, falls back to keyword search (maintains compatibility)

## Document Flagging System

Each semantic JSON file now contains:

```json
{
  "metadata": { ... },
  "semantic_content": { ... },
  "income_verification_relevant": {
    "is_relevant": true,
    "reason": "Primary source W-2 showing wage income from employer",
    "classified_date": "1234567890.123"
  }
}
```

### What Gets Flagged as Relevant:

**INCLUDED** (is_relevant: true):
- ✅ Paystubs (recent, from employer)
- ✅ W-2 forms (IRS tax documents)
- ✅ 1099 forms (independent contractor income)
- ✅ Tax returns (when needed for self-employment)
- ✅ Pension/retirement benefit statements
- ✅ SSA benefit letters
- ✅ Bank statements (when showing deposits for income verification)

**EXCLUDED** (is_relevant: false):
- ❌ Underwriter worksheets/notes
- ❌ Loan officer internal documents
- ❌ VOE responses (verify employment, not primary source for income amount)
- ❌ Income analysis summaries
- ❌ Corporate structure explanations
- ❌ Employment verification letters (unless showing income)

## Testing Recommendations

1. **Test Fresh Loans**: Run classifier on loans without cached flags to verify filtering works
2. **Verify Consistency**: Re-run tested loans to see if scenario classifications change
3. **Check Variance**: Test if this improves consistency in income calculations (reduces variance)
4. **Compare Before/After**: Compare scenarios classified before vs after refactoring

## Next Steps

1. ✅ **Refactoring Complete**: Document filtering now runs before scenario classification
2. ⏳ **Test Workflow**: Test on fresh loans to verify end-to-end workflow
3. ⏳ **Measure Impact**: Compare variance before/after refactoring
4. ⏳ **Update Documentation**: Update README with new workflow

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    LOAN DOCUMENTS                           │
│  loan_docs/{loan_id}/semantic_json/*.json                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│         STEP 1: DOCUMENT FILTERING                          │
│  income_scenario_classifier.py                              │
│  ├─> Check for cached flags                                 │
│  ├─> If none: Import filter_income_documents_by_guidelines()│
│  ├─> LLM + Freddie Mac Guidelines                           │
│  └─> Cache income_verification_relevant flags               │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│         STEP 2: SCENARIO CLASSIFICATION                     │
│  income_scenario_classifier.py                              │
│  ├─> Load ONLY flagged documents (is_relevant: true)        │
│  ├─> Classify income scenario                               │
│  └─> Output: income_scenario.json                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│         STEP 3: INCOME CALCULATION                          │
│  income_analysis_agent.py                                   │
│  ├─> Load flagged documents (FAST PATH - cached)            │
│  ├─> Load income_scenario.json                              │
│  ├─> Apply decision tree with scenario context              │
│  └─> Output: income_analysis_runX.json                      │
└─────────────────────────────────────────────────────────────┘
```

## Key Insight

**The scenario classification is only as good as the documents it's based on.**

By ensuring the scenario classifier uses the SAME rigorously-filtered document set as the income analyzer, we create a consistent foundation for the entire income analysis workflow.

This refactoring moves us from:
- "Classify scenario based on whatever keyword search finds, then filter properly later"

To:
- "Filter properly ONCE, then both scenario and income calculation use the correct documents"

Much better architecture! 🎯
