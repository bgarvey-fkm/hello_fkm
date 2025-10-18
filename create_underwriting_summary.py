import os
import json
import asyncio
from pathlib import Path
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")


async def process_loan_document(file_path, client):
    """
    Process a single loan document and return structured JSON
    """
    
    # Read the document content
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"Processing: {file_path.name}...")
    
    # Check if this is a base64 image file
    is_base64 = "_base64" in file_path.name
    
    if is_base64:
        # For base64 images, use vision capabilities
        response = await client.chat.completions.create(     
            messages=[         
                {
                    "role": "system",
                    "content": """You are a Mortgage Loan Origination Document Processor. Your job is to analyze mortgage loan documents and extract all relevant information into a structured JSON format.

For each document you receive:
1. Identify what type of document it is (paystub, W-2, credit report, appraisal, mortgage statement, bank statement, etc.)
2. Extract ALL relevant data fields specific to that document type
3. Return a well-structured JSON object with appropriate schema for that document type
4. Include a "document_type" field at the top level
5. Include a "document_date" field if a date is present
6. Be thorough - capture all financial figures, dates, names, addresses, and other relevant information

Return ONLY valid JSON, no explanations or markdown."""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please analyze this document image and extract all relevant information into a structured JSON format. Return ONLY the JSON object, no other text."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{content}"
                            }
                        }
                    ]
                }    
            ],
            max_completion_tokens=16384, 
            model=deployment
        )
    else:
        # For text files, use standard text processing
        response = await client.chat.completions.create(     
            messages=[         
                {
                    "role": "system",
                    "content": """You are a Mortgage Loan Origination Document Processor. Your job is to analyze mortgage loan documents and extract all relevant information into a structured JSON format.

For each document you receive:
1. Identify what type of document it is (paystub, W-2, credit report, appraisal, mortgage statement, bank statement, etc.)
2. Extract ALL relevant data fields specific to that document type
3. Return a well-structured JSON object with appropriate schema for that document type
4. Include a "document_type" field at the top level
5. Include a "document_date" field if a date is present
6. Be thorough - capture all financial figures, dates, names, addresses, and other relevant information

Return ONLY valid JSON, no explanations or markdown."""
                },
                {
                    "role": "user",
                    "content": f"""Please analyze this document and extract all relevant information into a structured JSON format.

DOCUMENT CONTENT:
{content}

Remember: Return ONLY the JSON object, no other text."""
                }    
            ],
            max_completion_tokens=16384, 
            model=deployment
        )
    
    json_response = response.choices[0].message.content
    
    # Try to parse to validate it's proper JSON
    try:
        parsed_json = json.loads(json_response)
        return parsed_json
    except json.JSONDecodeError as e:
        print(f"Warning: Response for {file_path.name} may not be valid JSON: {e}")
        return {"error": "Invalid JSON response", "raw_response": json_response}


async def create_document_json_files():
    """
    Process each document in loan_docs_inputs and create individual JSON files in parallel
    """
    
    input_dir = Path("loan_docs_inputs")
    output_dir = Path("loan_docs_json")
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    if not input_dir.exists():
        print(f"Error: {input_dir} directory not found!")
        return
    
    # Get ALL text files (both text extractions and base64)
    all_files = list(input_dir.glob("*.txt"))
    
    if not all_files:
        print("No files found in loan_docs_inputs/")
        return
    
    print(f"Found {len(all_files)} documents to process")
    print("="*60)
    
    # Initialize Azure OpenAI async client
    client = AsyncAzureOpenAI(
        api_version=api_version, 
        azure_endpoint=endpoint, 
        api_key=subscription_key
    )
    
    # Create tasks for all documents to process in parallel
    async def process_and_save(file):
        try:
            # Process the document
            json_data = await process_loan_document(file, client)
            
            # Create output filename (remove _text or _base64 suffix)
            output_filename = file.stem.replace("_text", "").replace("_base64", "") + ".json"
            output_path = output_dir / output_filename
            
            # Save JSON file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2)
            
            print(f"✓ Saved: {output_filename}")
            return True
            
        except Exception as e:
            print(f"✗ Error processing {file.name}: {e}")
            return False
    
    # Run all processing tasks in parallel
    results = await asyncio.gather(*[process_and_save(file) for file in all_files])
    
    print("="*60)
    print(f"Processing complete! JSON files saved to: {output_dir}/")
    print(f"Total files processed: {len(all_files)}")
    print(f"Successful: {sum(results)}, Failed: {len(results) - sum(results)}")


if __name__ == "__main__":
    asyncio.run(create_document_json_files())
