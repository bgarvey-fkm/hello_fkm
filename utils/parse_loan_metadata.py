"""
Loan Document Metadata Parser

Parses loan document metadata JSON from the loan management system.
This metadata contains file paths, document types, timelines, and page ranges.

The metadata structure allows us to:
1. Access original PDF files via Harvest API
2. Understand document types and purposes
3. Reconstruct the loan timeline
4. Extract specific pages from the loan package
5. Map documents to loan stages
"""

import json
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import urllib.parse
import requests

# Harvest API configuration
HARVEST_API_BASE = "https://harvestapi.firstkeyholdings.net:60000/pdf/"


class LoanDocument:
    """Represents a single loan document with metadata."""
    
    def __init__(self, metadata: dict):
        self.file_id = metadata.get('FileId')
        self.ref_file_id = metadata.get('RefFileId')
        self.timeline = metadata.get('Timeline')
        self.doc_prediction_type = metadata.get('DocPredictionType')
        self.spring_doc_type = metadata.get('SpringDocType')
        self.spring_comment = metadata.get('SpringComment')
        self.file_upload_date = metadata.get('FileUploadDate')
        self.file_name = metadata.get('FileName')
        self.file_full_name = metadata.get('FileFullName')  # Full UNC path
        self.page_count = metadata.get('PageCount')
        self.page_start = metadata.get('PageStart')
        self.page_end = metadata.get('PageEnd')
        self.is_expandable = metadata.get('IsExpandable')
        self.order_id = metadata.get('OrderId')
        
        # Parse upload date
        if self.file_upload_date:
            try:
                self.upload_date = datetime.fromisoformat(self.file_upload_date.replace('Z', '+00:00'))
            except:
                self.upload_date = None
        else:
            self.upload_date = None
    
    def __repr__(self):
        return f"<LoanDocument {self.file_id}: {self.file_name[:50]}>"
    
    def get_harvest_url(self) -> str:
        """Get Harvest API URL for this document."""
        if not self.file_full_name:
            return None
        
        encoded_path = urllib.parse.quote(self.file_full_name, safe='')
        return f"{HARVEST_API_BASE}{encoded_path}"
    
    def fetch_pdf(self) -> Optional[bytes]:
        """Fetch PDF bytes via Harvest API."""
        url = self.get_harvest_url()
        if not url:
            return None
        
        try:
            response = requests.get(url, verify=False, timeout=30)
            if response.status_code == 200:
                return response.content
            else:
                print(f"Error fetching {self.file_name}: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching {self.file_name}: {e}")
            return None
    
    def is_loan_package(self) -> bool:
        """Check if this is the main loan package (expandable parent)."""
        return self.is_expandable and self.ref_file_id is None
    
    def is_child_document(self) -> bool:
        """Check if this is a child document (part of loan package)."""
        return self.ref_file_id is not None
    
    def get_doc_type_category(self) -> str:
        """Get unified document type category."""
        # Prefer SpringDocType, fall back to DocPredictionType
        doc_type = self.spring_doc_type or self.doc_prediction_type or "Unknown"
        
        # Normalize document types
        doc_type_lower = doc_type.lower()
        
        if 'credit' in doc_type_lower:
            return 'Credit'
        elif 'appraisal' in doc_type_lower or 'valuation' in doc_type_lower:
            return 'Appraisal'
        elif 'paystub' in doc_type_lower or 'pay statement' in doc_type_lower:
            return 'Income - Paystubs'
        elif 'w2' in doc_type_lower or 'w-2' in doc_type_lower:
            return 'Income - W2'
        elif '1099' in doc_type_lower:
            return 'Income - 1099'
        elif 'voe' in doc_type_lower or 'employment' in doc_type_lower:
            return 'Employment Verification'
        elif 'mortgage statement' in doc_type_lower:
            return 'First Mortgage'
        elif 'insurance' in doc_type_lower or 'hoi' in doc_type_lower:
            return 'Insurance'
        elif 'flood' in doc_type_lower:
            return 'Flood'
        elif 'title' in doc_type_lower:
            return 'Title'
        elif 'closing' in doc_type_lower or 'settlement' in doc_type_lower:
            return 'Closing'
        elif 'disbursement' in doc_type_lower:
            return 'Funding'
        elif 'compliance' in doc_type_lower:
            return 'Compliance'
        elif 'disclosure' in doc_type_lower:
            return 'Disclosures'
        elif 'id' in doc_type_lower or 'identification' in doc_type_lower:
            return 'Identification'
        else:
            return 'Other'


class LoanDocumentCollection:
    """Collection of loan documents with analysis capabilities."""
    
    def __init__(self, metadata_list: List[dict]):
        self.documents = [LoanDocument(m) for m in metadata_list]
        self.loan_package = self._find_loan_package()
    
    def _find_loan_package(self) -> Optional[LoanDocument]:
        """Find the main loan package document."""
        for doc in self.documents:
            if doc.is_loan_package():
                return doc
        return None
    
    def get_by_timeline(self, timeline: str) -> List[LoanDocument]:
        """Get all documents for a specific timeline stage."""
        return [doc for doc in self.documents if doc.timeline == timeline]
    
    def get_by_doc_type(self, doc_type: str) -> List[LoanDocument]:
        """Get all documents of a specific type."""
        return [doc for doc in self.documents 
                if (doc.spring_doc_type and doc_type.lower() in doc.spring_doc_type.lower()) or
                   (doc.doc_prediction_type and doc_type.lower() in doc.doc_prediction_type.lower())]
    
    def get_timeline_stages(self) -> List[str]:
        """Get all unique timeline stages in order."""
        stages = {}
        for doc in self.documents:
            if doc.timeline and doc.timeline not in stages:
                stages[doc.timeline] = doc.order_id
        
        # Sort by order_id
        return sorted(stages.keys(), key=lambda x: stages[x])
    
    def get_doc_type_summary(self) -> Dict[str, int]:
        """Get count of documents by type category."""
        summary = {}
        for doc in self.documents:
            category = doc.get_doc_type_category()
            summary[category] = summary.get(category, 0) + 1
        return summary
    
    def get_timeline_summary(self) -> Dict[str, Dict]:
        """Get detailed timeline summary."""
        timeline_summary = {}
        
        for stage in self.get_timeline_stages():
            docs = self.get_by_timeline(stage)
            timeline_summary[stage] = {
                'count': len(docs),
                'earliest_date': min([d.upload_date for d in docs if d.upload_date], default=None),
                'latest_date': max([d.upload_date for d in docs if d.upload_date], default=None),
                'doc_types': list(set([d.get_doc_type_category() for d in docs]))
            }
        
        return timeline_summary
    
    def find_critical_documents(self) -> Dict[str, List[LoanDocument]]:
        """Find critical underwriting documents."""
        return {
            'Credit Reports': self.get_by_doc_type('credit'),
            'Appraisals': self.get_by_doc_type('appraisal'),
            'Paystubs': self.get_by_doc_type('paystub'),
            'W-2 Forms': self.get_by_doc_type('w2'),
            'VOE': self.get_by_doc_type('voe'),
            'First Mortgage': self.get_by_doc_type('mortgage'),
            'Insurance': self.get_by_doc_type('insurance'),
            'Flood': self.get_by_doc_type('flood')
        }
    
    def export_for_harvest_api(self) -> List[Dict]:
        """Export document list with Harvest API URLs."""
        return [{
            'file_id': doc.file_id,
            'file_name': doc.file_name,
            'doc_type': doc.get_doc_type_category(),
            'timeline': doc.timeline,
            'upload_date': doc.file_upload_date,
            'page_count': doc.page_count,
            'harvest_url': doc.get_harvest_url(),
            'original_path': doc.file_full_name
        } for doc in self.documents if not doc.is_loan_package()]


def analyze_loan_metadata(metadata_json):
    """Analyze loan document metadata."""
    
    if isinstance(metadata_json, str):
        metadata = json.loads(metadata_json)
    else:
        metadata = metadata_json
    
    collection = LoanDocumentCollection(metadata)
    
    print("="*80)
    print("📊 LOAN DOCUMENT METADATA ANALYSIS")
    print("="*80)
    
    print(f"\n📁 Total Documents: {len(collection.documents)}")
    
    if collection.loan_package:
        print(f"\n📦 Main Loan Package:")
        print(f"   File ID: {collection.loan_package.file_id}")
        print(f"   Pages: {collection.loan_package.page_count}")
        print(f"   Upload Date: {collection.loan_package.file_upload_date}")
        print(f"   Path: {collection.loan_package.file_full_name}")
    
    print(f"\n📋 TIMELINE STAGES:")
    timeline_summary = collection.get_timeline_summary()
    for stage, info in timeline_summary.items():
        print(f"\n   {stage} ({info['count']} documents)")
        if info['earliest_date']:
            print(f"      Date Range: {info['earliest_date'].strftime('%Y-%m-%d')} to {info['latest_date'].strftime('%Y-%m-%d')}")
        print(f"      Doc Types: {', '.join(info['doc_types'][:5])}")
    
    print(f"\n📊 DOCUMENT TYPE SUMMARY:")
    doc_type_summary = collection.get_doc_type_summary()
    for doc_type, count in sorted(doc_type_summary.items(), key=lambda x: -x[1]):
        print(f"   {doc_type}: {count}")
    
    print(f"\n🎯 CRITICAL DOCUMENTS:")
    critical = collection.find_critical_documents()
    for doc_type, docs in critical.items():
        if docs:
            print(f"   ✓ {doc_type}: {len(docs)} found")
            for doc in docs[:2]:  # Show first 2
                print(f"      - {doc.file_name[:60]}")
        else:
            print(f"   ✗ {doc_type}: Not found")
    
    print(f"\n🌐 HARVEST API ACCESS:")
    print(f"   All {len(collection.documents)} documents are accessible via Harvest API")
    print(f"   Base URL: {HARVEST_API_BASE}")
    
    print("\n" + "="*80)
    
    return collection


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python parse_loan_metadata.py <metadata.json>")
        print("   Or: python parse_loan_metadata.py 'json_string'")
        sys.exit(1)
    
    input_arg = sys.argv[1]
    
    # Check if it's a file path or JSON string
    if Path(input_arg).exists():
        with open(input_arg, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = json.loads(input_arg)
    
    collection = analyze_loan_metadata(metadata)
    
    # Export to file
    output_file = "loan_documents_harvest_urls.json"
    with open(output_file, 'w') as f:
        json.dump(collection.export_for_harvest_api(), f, indent=2)
    
    print(f"\n✅ Exported Harvest API URLs to: {output_file}")
