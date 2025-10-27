# Root Directory Cleanup Plan

## Current State: 24 Python Files in Root

### Category 1: ACTIVE PRODUCTION - Keep in Root ✅
**Main Orchestrator:**
- `pipeline_orchestrator.py` - **PRIMARY ENTRY POINT** - Single command to run full pipeline

**Harvest API Integration:**
- `batch_process_deal.py` - Fetch new loans from Harvest API and create input JSONs

**Analysis & Reporting:**
- `generate_income_comparison_csv.py` - Generate aggregate CSV from all loan results
- `generate_accuracy_histogram.py` - Visualize AI vs Form 1003 variance
- `analyze_confidence.py` - Analyze confidence score distribution

---

### Category 2: LEGACY BATCH SCRIPTS - Move to `scripts/legacy/` 🗂️
**Replaced by pipeline_orchestrator.py:**
- `batch_process_last_4_loans.py` - Superseded by orchestrator
- `batch_classify_all_loans.py` - Superseded by orchestrator with --resume
- `batch_employment_history.py` - Superseded by orchestrator
- `batch_form_1003_tracker.py` - Superseded by orchestrator
- `batch_income_analysis.py` - Superseded by orchestrator
- `batch_income_and_1003_analysis.py` - Superseded by orchestrator
- `batch_run_income_analysis.py` - Superseded by orchestrator
- `batch_test_refactored_workflow.py` - Old testing script
- `batch_income_comparison.py` - Old comparison script

---

### Category 3: UTILITY/HELPER SCRIPTS - Move to `scripts/` 📁
**Data Analysis:**
- `load_comparison_dataframe.py` - Helper to load CSV into pandas
- `generate_comparison_report.py` - Generate comparison reports
- `generate_aggregate_csv.py` - Aggregate CSV generation (check if duplicate?)

**Document Discovery:**
- `find_underwriter_income.py` - Find underwriter income worksheets
- `find_va_docs.py` - Find VA-specific documents
- `list_relevant_docs.py` - List income-relevant documents

**Cleanup:**
- `cleanup_old_analysis.py` - Clean up old analysis files
- `retry_failed_loans.py` - Retry failed loan processing

---

### Category 4: TEST FILES - Move to `tests/` 🧪
- `test_azure_openai.py` - Test Azure OpenAI connection
- `test_find_underwriter_worksheets.py` - Test worksheet finding
- `test_income_extraction.py` - Test income extraction

---

### Category 5: DUPLICATES/OBSOLETE - Archive or Delete 🗑️
Need to check if these are duplicates:
- `generate_aggregate_csv.py` vs `generate_income_comparison_csv.py`
- Multiple batch_* files that do similar things

---

## Proposed New Structure

```
hello_fkm/
├── pipeline_orchestrator.py          # MAIN ENTRY POINT
├── batch_process_deal.py             # Fetch from Harvest API
├── generate_income_comparison_csv.py # Generate aggregate CSV
├── generate_accuracy_histogram.py    # Generate visualizations
├── analyze_confidence.py             # Confidence analysis
│
├── scripts/
│   ├── legacy/                       # Old batch scripts (keep for reference)
│   │   ├── batch_process_last_4_loans.py
│   │   ├── batch_classify_all_loans.py
│   │   ├── batch_employment_history.py
│   │   ├── batch_form_1003_tracker.py
│   │   ├── batch_income_analysis.py
│   │   ├── batch_income_and_1003_analysis.py
│   │   ├── batch_run_income_analysis.py
│   │   ├── batch_test_refactored_workflow.py
│   │   └── batch_income_comparison.py
│   │
│   ├── analysis/                     # Analysis utilities
│   │   ├── load_comparison_dataframe.py
│   │   ├── generate_comparison_report.py
│   │   └── generate_aggregate_csv.py
│   │
│   ├── discovery/                    # Document discovery
│   │   ├── find_underwriter_income.py
│   │   ├── find_va_docs.py
│   │   └── list_relevant_docs.py
│   │
│   └── maintenance/                  # Cleanup & retry
│       ├── cleanup_old_analysis.py
│       └── retry_failed_loans.py
│
├── tests/                            # Test files
│   ├── test_azure_openai.py
│   ├── test_find_underwriter_worksheets.py
│   └── test_income_extraction.py
│
├── pipeline/                         # Core pipeline (existing)
├── agents/                           # Core agents (existing)
├── utils/                            # Utilities (existing)
└── ...
```

---

## Cleanup Steps

### Step 1: Create New Directories
```bash
mkdir scripts\legacy
mkdir scripts\analysis
mkdir scripts\discovery
mkdir scripts\maintenance
mkdir tests
```

### Step 2: Move Legacy Batch Scripts
```bash
# Move to scripts/legacy/
mv batch_process_last_4_loans.py scripts/legacy/
mv batch_classify_all_loans.py scripts/legacy/
mv batch_employment_history.py scripts/legacy/
mv batch_form_1003_tracker.py scripts/legacy/
mv batch_income_analysis.py scripts/legacy/
mv batch_income_and_1003_analysis.py scripts/legacy/
mv batch_run_income_analysis.py scripts/legacy/
mv batch_test_refactored_workflow.py scripts/legacy/
mv batch_income_comparison.py scripts/legacy/
```

### Step 3: Move Utility Scripts
```bash
# Analysis utilities
mv load_comparison_dataframe.py scripts/analysis/
mv generate_comparison_report.py scripts/analysis/
mv generate_aggregate_csv.py scripts/analysis/

# Discovery utilities
mv find_underwriter_income.py scripts/discovery/
mv find_va_docs.py scripts/discovery/
mv list_relevant_docs.py scripts/discovery/

# Maintenance
mv cleanup_old_analysis.py scripts/maintenance/
mv retry_failed_loans.py scripts/maintenance/
```

### Step 4: Move Test Files
```bash
mv test_*.py tests/
```

---

## Benefits

1. **Clean Root Directory**: Only 5 essential scripts visible
2. **Clear Purpose**: Obvious what each top-level file does
3. **Better Organization**: Related scripts grouped together
4. **Preserve History**: Legacy scripts kept for reference, not deleted
5. **Easy Discovery**: Tests in `tests/`, utilities in `scripts/`

---

## Verification Before Cleanup

Before moving files, check:
1. Are any legacy batch scripts still being used?
2. Is `generate_aggregate_csv.py` a duplicate of `generate_income_comparison_csv.py`?
3. Are there any imports/dependencies that reference these files by absolute path?

---

## Next Steps

1. Review this plan
2. Verify no active dependencies on legacy scripts
3. Execute cleanup (move files)
4. Update documentation (README.md, PIPELINE.md)
5. Test that main workflows still work
