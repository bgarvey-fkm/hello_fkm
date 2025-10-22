# Income Expert - AI Income Verification System

**Branch: income-expert**

A specialized Python system for testing and developing AI-based income verification for mortgage underwriting. This project analyzes consistency and accuracy of LLM-based income calculations across multiple loan files to build a robust income verification expert system.

## 🎯 Project Goal

Develop a reliable AI system that can accurately determine qualified income from mortgage loan documentation by:
1. Processing multiple loan files to understand income calculation variance
2. Identifying different income scenarios and edge cases
3. Building pattern recognition for consistent income determination
4. Comparing AI calculations against human underwriter results

## 📊 Current Status

**Testing Phase**: Running consistency tests on income calculations
- ✅ Tested loan 1000179167: 50-run test showed 18.19% variance
- ✅ Identified 4 distinct LLM calculation methodologies
- 🔄 Next: Expand to 10 loans to identify more income scenarios

## Features

- **� Multi-Loan Pipeline**: Process 10+ loans from Harvest API
- **🧪 Consistency Testing**: Run parallel async tests (configurable iterations)
- **� Variance Analysis**: Track how LLM income calculations vary across runs
- **� HTML Reports**: Detailed methodology breakdowns with frequency analysis
- **🎯 Document Type Support**: Paystubs, W-2s, 1099-R (pension), income worksheets
- **⚡ Async Processing**: Parallel execution for speed

## Project Structure

```
hello_fkm/
├── pipeline/                         # 🔄 Core Processing Pipeline
│   ├── process_from_harvest_api.py   # Download loans from Harvest API
│   └── create_structured_json.py     # Create semantic JSON from documents
├── agents/                           # 🤖 Income Analysis Agents
│   └── income_analysis_agent.py      # Main consistency testing agent
├── loan_docs/                        # 📁 Loan documents by loan ID (gitignored)
│   └── {loan_id}/
│       ├── raw_json/                 # Initial document extraction
│       └── semantic_json/            # Structured semantic content
├── reports/                          # 📊 Analysis reports (gitignored)
│   ├── income_analysis_{loan_id}_run{N}.json
│   └── income_analysis_consistency_report_{loan_id}.html
├── loan_files_inputs/                # 📥 Harvest API input configs (gitignored)
└── requirements.txt                  # Python dependencies
```

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/bgarvey-fkm/hello_fkm.git
cd hello_fkm
git checkout income-expert
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your Azure OpenAI credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:
```env
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

## Usage

### Income Consistency Testing Workflow

**Step 1: Download Loan Documents from Harvest API**
```bash
# Create input JSON with loan IDs to process
# Place in loan_files_inputs/loans_to_process.json

python pipeline/process_from_harvest_api.py loan_files_inputs/loans_to_process.json
```

**Step 2: Create Semantic JSON from Documents**
```bash
# Process all downloaded loans
python pipeline/create_structured_json.py {loan_id}
```

**Step 3: Run Income Analysis Consistency Test**
```bash
# Run N parallel analyses on a single loan
python agents/income_analysis_agent.py {loan_id} {num_runs}

# Example: 50 parallel runs on loan 1000179167
python agents/income_analysis_agent.py 1000179167 50
```

**Output:** 
- JSON results for each run: `reports/income_analysis_{loan_id}_run{N}.json`
- HTML consistency report: `reports/income_analysis_consistency_report_{loan_id}.html`
- Summary JSON: `reports/income_analysis_consistency_{loan_id}.json`

### Batch Processing Multiple Loans

```bash
# Process 10 loans and run 20 consistency tests on each
# (Script to be created)
python run_batch_income_analysis.py --loans 10 --runs 20
```

## Income Analysis Features

### Document Types Analyzed
- **Paystubs**: Year-to-date income, pay frequency, gross pay
- **W-2 Forms**: Annual income (Box 1: taxable wages, Box 5: Medicare wages)
- **1099-R Forms**: Pension/retirement income distributions
- **Income Worksheets**: Underwriter-calculated qualified income (for comparison)

### Methodology Tracking

The system identifies different calculation approaches the LLM uses:
1. **Method 1** (Most Common): W2 Box 5 (Medicare wages) ÷ 12
2. **Method 2**: W2 Box 1 (Taxable wages) ÷ 12  
3. **Method 3**: Includes additional income components
4. **Method 4**: Paystub semi-monthly calculation

Reports show frequency distribution and variance analysis.

## Key Findings (Loan 1000179167)

**50-Run Consistency Test:**
- Average Income: $11,998.82/month
- Variance: 18.19%
- Most Frequent Result: $12,059.23 (56% of runs)
- Consistency Rating: **LOW** - Significant variation

**Impact of Adding 1099-R:**
- Variance improved from 28.04% → 18.19%
- More complete income picture reduced calculation uncertainty

## Next Steps

1. ✅ Clean up project (remove debt/DTI/timeline agents)
2. 🔄 Process 10 new loans from Harvest API
3. 🧪 Run consistency tests on all 10 loans
4. 📊 Analyze patterns across different income scenarios
5. 🎯 Build expert system rules based on findings

## Technical Details

- **Azure OpenAI**: GPT-4o-mini for income analysis
- **Async Processing**: asyncio for parallel execution
- **Document Formats**: PDF text extraction → Semantic JSON
- **Python 3.8+**: Modern async/await patterns

## Security Notes

🔒 **Protected Information (NOT in GitHub):**
- `.env` - Azure OpenAI credentials
- `loan_docs/` - All loan documents and processed data
- `reports/` - All generated analysis reports
- `loan_files_inputs/` - Harvest API configurations with loan IDs
- `archive/` - Archived documentation

✅ **Safe to Share (in GitHub):**
- Python scripts (`.py` files)
- `.env.example` - Template with no actual credentials
- `.gitignore` - Protection rules
- `README.md`, documentation files
- `requirements.txt` - Python dependencies

**Never commit sensitive data, loan information, or API keys to version control!**

## Requirements

- Python 3.8+
- Azure OpenAI API access (gpt-4o-mini or similar)
- Network access to Harvest API (for document download)

## Contributing

This is a research/development branch. For questions or collaboration:
1. Review the income analysis agent code
2. Check HTML reports for methodology insights
3. Reach out with findings or suggestions

## Branch Information

- **Main Branch**: Full underwriting system with debt/DTI/compliance agents
- **Income-Expert Branch** (this): Focused income verification testing and development

## License

[Specify your license]

## Acknowledgments

- Azure OpenAI for GPT-4o-mini capabilities
- Spring EQ underwriting guidelines for validation
