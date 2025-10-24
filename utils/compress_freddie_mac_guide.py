"""
Semantic Compression for Freddie Mac Guide

Takes the parsed Freddie Mac guide JSON and compresses it into a more
LLM-friendly format by extracting key rules and requirements.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

# Fix console encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()


async def compress_guide_content(content: str) -> dict:
    """
    Compress the Freddie Mac guide content by extracting key income calculation rules.
    Uses the full 400K context window - no chunking needed!
    """
    
    # Initialize Azure OpenAI client
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    subscription_key = os.getenv("AZURE_OPENAI_KEY")
    
    client = AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_key=subscription_key,
        api_version="2024-12-01-preview"
    )
    
    print(f"Processing entire guide in one LLM call...")
    print(f"  Content length: {len(content):,} characters")
    
    prompt = f"""You are analyzing the Freddie Mac Single-Family Seller/Servicer Guide sections 5300-5400 covering Income and Employment Documentation.

Extract and organize ALL income calculation rules, requirements, and guidelines from this guide.

For each rule/requirement, provide:
1. Section number (e.g., "5301.1")
2. Topic/title
3. Rule summary (concise but complete)
4. Key details (specific requirements, calculations, exceptions)
5. Examples if provided

Focus on:
- How to calculate monthly income from paystubs
- How to calculate income from W-2s
- How to handle variable income (overtime, bonus, commission)
- Income stability requirements (2-year history, continuance, etc.)
- How to handle job changes
- Documentation requirements
- Special cases (seasonal income, retirement, self-employment, etc.)

Output as a JSON array of rules:
[
  {{
    "section": "5301.1",
    "topic": "General requirements for stable monthly income",
    "rule": "Summary of the rule",
    "details": ["specific requirement 1", "specific requirement 2"],
    "examples": ["example 1 if provided"]
  }}
]

Here is the complete guide to analyze:

{content}

Return ONLY the JSON array, no other text."""

    try:
        print("  Calling LLM with full guide content...")
        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are an expert mortgage underwriting analyst extracting rules from the Freddie Mac guide."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=16000  # Increase for more comprehensive output
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Try to parse as JSON
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        
        rules = json.loads(result_text)
        
        print(f"  ✓ Extracted {len(rules)} rules from the guide")
        
        return {
            "total_rules_extracted": len(rules),
            "rules": rules
        }
        
    except Exception as e:
        print(f"  ✗ Error processing guide: {e}")
        raise


async def main():
    """Main processing function."""
    
    input_path = Path("guidelines/freddie_mac_guide_5300_5400.json")
    output_path = Path("guidelines/freddie_mac_guide_5300_5400_compressed.json")
    
    print("=" * 80)
    print("FREDDIE MAC GUIDE SEMANTIC COMPRESSION")
    print("=" * 80)
    print(f"\nInput: {input_path}")
    print(f"Output: {output_path}")
    
    if not input_path.exists():
        print(f"\n✗ Error: Input file not found at {input_path}")
        return
    
    # Load the parsed guide
    print("\nLoading parsed guide...")
    with open(input_path, 'r', encoding='utf-8') as f:
        guide_data = json.load(f)
    
    print(f"  Pages: {guide_data['page_count']}")
    print(f"  Tables: {len(guide_data['tables'])}")
    print(f"  Content: {len(guide_data['content']):,} characters")
    
    # Compress the content
    print("\nCompressing with LLM...")
    compressed = await compress_guide_content(guide_data['content'])
    
    # Combine with metadata
    output_data = {
        "source": guide_data['source'],
        "title": guide_data['title'],
        "sections": guide_data['sections'],
        "page_count": guide_data['page_count'],
        "original_content_length": len(guide_data['content']),
        "compression_stats": {
            "total_rules_extracted": compressed['total_rules_extracted'],
            "compression_ratio": f"{(len(json.dumps(compressed['rules'])) / len(guide_data['content']) * 100):.1f}%"
        },
        "rules": compressed['rules']
    }
    
    # Save compressed version
    print(f"\nSaving compressed guide to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Success!")
    print(f"  Rules extracted: {compressed['total_rules_extracted']}")
    print(f"  Original size: {len(guide_data['content']) / 1024:.1f} KB")
    print(f"  Compressed size: {len(json.dumps(compressed['rules'])) / 1024:.1f} KB")
    print(f"  Compression ratio: {output_data['compression_stats']['compression_ratio']}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
