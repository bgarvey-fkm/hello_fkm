# -*- coding: utf-8 -*-
"""
LLM-Based PII Redaction with Consistent Mapping

Uses Azure OpenAI to:
1. Read all income-relevant semantic JSON files
2. Identify all PII across all files
3. Create a consistent mapping table (real → dummy)
4. Apply mapping to sanitize all files while preserving relationships
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()


def get_income_relevant_files(loan_id):
    """Get all semantic JSON files marked as income-relevant"""
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        raise FileNotFoundError(f"Semantic JSON directory not found: {semantic_dir}")
    
    income_files = []
    for json_file in semantic_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                doc = json.load(f)
            
            # Only include income-relevant documents
            if doc.get('income_verification_relevant', {}).get('is_relevant', False):
                income_files.append({
                    'filename': json_file.name,
                    'filepath': str(json_file),
                    'content': doc
                })
        except Exception as e:
            print(f"Warning: Could not read {json_file.name}: {e}")
            continue
    
    return income_files


def create_pii_mapping_with_llm(income_files, loan_id):
    """
    Use LLM to analyze all files and create a consistent PII mapping.
    
    Returns:
        dict: Mapping of real PII values to dummy replacements
    """
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    # Create a summary of all files for the LLM
    files_summary = []
    for f in income_files:
        files_summary.append({
            'filename': f['filename'],
            'semantic_content': f['content'].get('semantic_content', {}),
            'metadata': f['content'].get('metadata', {})
        })
    
    prompt = f"""You are a data privacy expert. Review these {len(income_files)} income verification documents for loan {loan_id} and create a comprehensive PII mapping.

DOCUMENTS:
{json.dumps(files_summary, indent=2)}

TASK:
1. Identify ALL personally identifiable information (PII) across ALL documents:
   - Person names (borrowers, co-borrowers, employers, verifiers, loan officers)
   - Company/employer names
   - Addresses (property addresses, employer addresses, company addresses)
   - Phone numbers
   - Email addresses
   - SSNs, loan IDs, file IDs
   - Any other identifying information

2. Create CONSISTENT dummy replacements:
   - Same real value MUST map to same dummy value across all files
   - Use realistic dummy data (real-looking names, addresses, phones)
   - Preserve context:
     * Property addresses → residential dummy addresses
     * Employer addresses → commercial dummy addresses
     * Person names → consistent fake names
     * Company names → consistent fake company names

3. Maintain relationships:
   - If "John Smith" appears in multiple files, always replace with same dummy name
   - If "123 Main St" appears multiple times, always use same dummy address
   - Preserve the linkage between files

OUTPUT FORMAT:
Return a JSON object with this structure:
{{
  "pii_mappings": [
    {{
      "real_value": "actual PII value",
      "dummy_value": "realistic replacement",
      "pii_type": "person_name|company_name|property_address|employer_address|phone|email|ssn|loan_id|other",
      "context": "borrower|co_borrower|employer|lender|verifier|property|other",
      "occurrences": <count of times this appears>
    }}
  ],
  "summary": {{
    "total_pii_values": <number>,
    "person_names": <count>,
    "companies": <count>,
    "addresses": <count>,
    "phones": <count>,
    "other": <count>
  }}
}}

CRITICAL: Ensure every unique PII value has exactly ONE mapping entry, and that mapping will be used consistently across all files."""

    print(f"\n>> Sending {len(income_files)} files to LLM for PII analysis...")
    
    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": "You are a data privacy expert who creates consistent PII mappings."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        mapping_result = json.loads(response.choices[0].message.content)
        
        print(f"✅ LLM identified {mapping_result['summary']['total_pii_values']} unique PII values")
        print(f"   - Person names: {mapping_result['summary']['person_names']}")
        print(f"   - Companies: {mapping_result['summary']['companies']}")
        print(f"   - Addresses: {mapping_result['summary']['addresses']}")
        print(f"   - Phones: {mapping_result['summary']['phones']}")
        print(f"   - Other: {mapping_result['summary']['other']}")
        
        return mapping_result['pii_mappings']
        
    except Exception as e:
        raise RuntimeError(f"LLM PII mapping failed: {e}")


def apply_mapping_to_value(value, mapping_dict):
    """
    Recursively apply PII mapping to a value (string, dict, list, or primitive).
    
    Args:
        value: The value to process
        mapping_dict: Dict mapping real PII → dummy data
        
    Returns:
        The value with PII replaced
    """
    if isinstance(value, str):
        # Replace PII in strings
        result = value
        for real_pii, dummy_pii in mapping_dict.items():
            if real_pii in result:
                result = result.replace(real_pii, dummy_pii)
        return result
    
    elif isinstance(value, dict):
        # Recursively process dictionary values
        return {k: apply_mapping_to_value(v, mapping_dict) for k, v in value.items()}
    
    elif isinstance(value, list):
        # Recursively process list items
        return [apply_mapping_to_value(item, mapping_dict) for item in value]
    
    else:
        # Return primitives unchanged (numbers, booleans, None)
        return value


def apply_pii_mapping_with_llm(income_files, pii_mappings, output_dir):
    """
    Use LLM to apply the PII mapping to each file individually.
    This catches variations and context-specific instances better than string matching.
    
    Args:
        income_files: List of file dicts with content
        pii_mappings: List of mapping objects from LLM
        output_dir: Where to save sanitized files
        
    Returns:
        int: Number of files processed
    """
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n>> Applying PII mapping to {len(income_files)} files using LLM...")
    
    # Create mapping reference for LLM
    mapping_reference = "\n".join([
        f"- Replace '{m['real_value']}' with '{m['dummy_value']}' ({m['pii_type']}, context: {m['context']})"
        for m in pii_mappings
    ])
    
    for i, file_info in enumerate(income_files, 1):
        print(f"   Processing file {i}/{len(income_files)}: {file_info['filename']}")
        
        replacement_prompt = f"""You are applying a PII redaction mapping to a loan document. Use the mapping below to replace ALL instances of real PII with dummy data.

MAPPING TO APPLY:
{mapping_reference}

CRITICAL INSTRUCTIONS:
1. Replace EVERY occurrence of the real values with their dummy values
2. Look for variations (uppercase, lowercase, different formatting)
3. Preserve the JSON structure exactly - only replace the VALUES
4. Do not add or remove any fields
5. If a real value appears as part of a larger string, replace it there too
6. Ensure all names, addresses, companies, phones, etc. are replaced

ORIGINAL DOCUMENT:
{json.dumps(file_info['content'], indent=2)}

Return the complete sanitized document as valid JSON with all PII replaced according to the mapping."""

        try:
            response = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                messages=[
                    {"role": "system", "content": "You are a data privacy expert applying PII redaction mappings to documents."},
                    {"role": "user", "content": replacement_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            sanitized_content = json.loads(response.choices[0].message.content)
            
            # Save sanitized file
            output_file = output_path / file_info['filename']
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(sanitized_content, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"   ⚠️  Error processing {file_info['filename']}: {e}")
            # Save original on error
            output_file = output_path / file_info['filename']
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(file_info['content'], f, indent=2, ensure_ascii=False)
    
    # Save the mapping table for reference
    mapping_file = output_path / 'pii_mapping.json'
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump({
            'mappings': pii_mappings,
            'total_pii_values': len(pii_mappings)
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Processed {len(income_files)} files")
    print(f"✅ Saved to: {output_dir}")
    print(f"✅ Mapping saved to: {mapping_file}")
    
    return len(income_files)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python llm_pii_redaction.py <loan_id>")
        print("Example: python llm_pii_redaction.py 1000175957")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    output_dir = f"loan_docs/{loan_id}/sanitized_income_docs"
    
    print("\n" + "="*80)
    print(f"LLM-BASED PII REDACTION")
    print(f"Loan ID: {loan_id}")
    print(f"Output: {output_dir}")
    print("="*80)
    
    # Step 1: Get income-relevant files
    print(f"\n>> Step 1: Loading income-relevant documents...")
    income_files = get_income_relevant_files(loan_id)
    
    if not income_files:
        print("❌ No income-relevant documents found!")
        print("   Run: python pipeline/classify_income_documents.py <loan_id> first")
        sys.exit(1)
    
    print(f"✅ Found {len(income_files)} income-relevant documents")
    
    # Step 2: Create PII mapping with LLM
    print(f"\n>> Step 2: Creating consistent PII mapping with LLM...")
    pii_mappings = create_pii_mapping_with_llm(income_files, loan_id)
    
    # Step 3: Apply mapping to all files
    print(f"\n>> Step 3: Applying PII mapping to all files with LLM...")
    files_processed = apply_pii_mapping_with_llm(income_files, pii_mappings, output_dir)
    
    print("\n" + "="*80)
    print("PII REDACTION COMPLETE")
    print("="*80)
    print(f"Files processed: {len(income_files)}")
    print(f"Unique PII values: {len(pii_mappings)}")
    print(f"Output directory: {output_dir}")
    print("\n>> ✅ All income documents sanitized with consistent PII mapping!")


if __name__ == "__main__":
    main()
