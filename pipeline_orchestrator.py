"""
Loan Processing Pipeline Orchestrator (Subprocess Version)
===========================================================
Single entry point that orchestrates existing pipeline scripts.

Usage:
    # Process single loan
    python pipeline_orchestrator.py 1000178625
    
    # Process multiple loans
    python pipeline_orchestrator.py 1000178625 1000178635 1000178636
    
    # Resume from failures (skip completed steps)
    python pipeline_orchestrator.py 1000178625 --resume
    
    # Custom number of analysis runs
    python pipeline_orchestrator.py 1000178625 --runs 5

Pipeline Steps:
    1. harvest_ocr: Download from Harvest API + Document Intelligence OCR
    2. semantic: Convert to semantic JSON
    3. classify: Classify income-relevant documents
    4. form1003: Extract Form 1003 timeline
    5. employment: Generate employment history
    6. analysis: Run income analysis (default 3 runs)
"""

import subprocess
import sys
import argparse
from pathlib import Path
from typing import List, Optional


class PipelineOrchestrator:
    """Orchestrates loan processing by calling existing pipeline scripts."""
    
    def __init__(self, python_exe: str = None):
        """Initialize orchestrator with Python executable path."""
        self.python_exe = python_exe or sys.executable
    
    def _check_completed(self, loan_id: str, step: str) -> bool:
        """Check if a pipeline step has already been completed."""
        checks = {
            'harvest_ocr': lambda: self._check_path(f"loan_docs/{loan_id}/raw_json", min_files=1),
            'semantic': lambda: self._check_path(f"loan_docs/{loan_id}/semantic_json", min_files=1),
            'classify': lambda: self._check_classification(loan_id),
            'form1003': lambda: self._check_file(f"loan_docs/{loan_id}/income_analysis/form_1003_income_timeline.json"),
            'employment': lambda: self._check_file(f"loan_docs/{loan_id}/employment_history/employment_history.json"),
            'analysis': lambda: self._check_path(f"loan_docs/{loan_id}/income_analysis", pattern="consistency_summary_*.json")
        }
        
        return checks.get(step, lambda: False)()
    
    def _check_path(self, path: str, min_files: int = 0, pattern: str = "*.json") -> bool:
        """Check if path exists and has minimum number of files."""
        p = Path(path)
        if not p.exists():
            return False
        if min_files > 0:
            return len(list(p.glob(pattern))) >= min_files
        return True
    
    def _check_file(self, filepath: str) -> bool:
        """Check if file exists."""
        return Path(filepath).exists()
    
    def _check_classification(self, loan_id: str) -> bool:
        """Check if income classification has been done."""
        import json
        semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
        if not semantic_dir.exists():
            return False
        
        # Check if any semantic files have the income_verification_relevant flag
        for file in semantic_dir.glob("*.json"):
            try:
                with open(file, encoding='utf-8') as f:
                    data = json.load(f)
                    if 'income_verification_relevant' in data:
                        return True
            except:
                continue
        return False
    
    def _run_command(self, description: str, command: List[str], allow_failure: bool = False) -> bool:
        """Run a subprocess command and report status."""
        print(f"\n  🔄 {description}")
        print(f"     Command: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode != 0:
                print(f"  ❌ Failed with exit code {result.returncode}")
                if result.stderr:
                    print(f"     Error: {result.stderr[:500]}")
                return False
            
            print(f"  ✅ {description} - Completed")
            return True
            
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            return False
    
    def process_loan(self, loan_id: str, resume: bool = False, num_runs: int = 3) -> bool:
        """Process a single loan through the complete pipeline."""
        print(f"\n{'='*80}")
        print(f"PROCESSING LOAN {loan_id}")
        print(f"{'='*80}")
        
        metadata_file = f"loan_files_inputs/loan_{loan_id}_tree.json"
        if not Path(metadata_file).exists():
            print(f"❌ Metadata file not found: {metadata_file}")
            return False
        
        # Define pipeline steps
        steps = [
            {
                'name': 'harvest_ocr',
                'description': 'Download PDFs and run Document Intelligence OCR',
                'command': [self.python_exe, 'pipeline/process_from_harvest_api.py', metadata_file, loan_id]
            },
            {
                'name': 'semantic',
                'description': 'Convert to semantic JSON',
                'command': [self.python_exe, 'pipeline/process_semantic_compression.py', loan_id]
            },
            {
                'name': 'classify',
                'description': 'Classify income-relevant documents',
                'command': [self.python_exe, 'pipeline/classify_income_documents.py', loan_id]
            },
            {
                'name': 'form1003',
                'description': 'Extract Form 1003 income timeline',
                'command': [self.python_exe, 'agents/form_1003_income_tracker.py', loan_id]
            },
            {
                'name': 'employment',
                'description': 'Generate employment history',
                'command': [self.python_exe, 'agents/employment_history_agent.py', loan_id]
            },
            {
                'name': 'analysis',
                'description': f'Run income analysis ({num_runs} runs)',
                'command': [self.python_exe, 'agents/income_analysis_agent.py', loan_id, str(num_runs)]
            }
        ]
        
        # Execute each step
        for i, step in enumerate(steps, 1):
            step_name = step['name']
            
            # Check if already completed
            if resume and self._check_completed(loan_id, step_name):
                print(f"\n  ✅ Step {i}/6 [{step_name}]: Already completed, skipping")
                continue
            
            # Run the step
            print(f"\n  [{i}/6] {step_name.upper()}")
            success = self._run_command(step['description'], step['command'])
            
            if not success:
                print(f"\n❌ Pipeline failed at step: {step_name}")
                return False
        
        print(f"\n{'='*80}")
        print(f"✅ LOAN {loan_id} COMPLETED SUCCESSFULLY")
        print(f"{'='*80}\n")
        return True
    
    def process_multiple_loans(self, loan_ids: List[str], **kwargs) -> dict:
        """Process multiple loans through the pipeline."""
        print(f"\n{'='*80}")
        print(f"BATCH PROCESSING {len(loan_ids)} LOANS")
        print(f"{'='*80}")
        print(f"Loans: {', '.join(loan_ids)}")
        print(f"{'='*80}\n")
        
        results = {}
        for loan_id in loan_ids:
            results[loan_id] = self.process_loan(loan_id, **kwargs)
        
        # Summary
        print(f"\n{'='*80}")
        print("BATCH PROCESSING SUMMARY")
        print(f"{'='*80}")
        successful = sum(1 for v in results.values() if v)
        print(f"Successful: {successful}/{len(loan_ids)}")
        for loan_id, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"  {loan_id}: {status}")
        print(f"{'='*80}\n")
        
        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Loan Processing Pipeline Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single loan
  python pipeline_orchestrator.py 1000178625
  
  # Process multiple loans
  python pipeline_orchestrator.py 1000178625 1000178635 1000178636
  
  # Resume from failures (skip completed steps)
  python pipeline_orchestrator.py 1000178625 --resume
  
  # Custom number of analysis runs
  python pipeline_orchestrator.py 1000178625 --runs 5
        """
    )
    
    parser.add_argument('loan_ids', nargs='+', help='Loan IDs to process')
    parser.add_argument('--resume', action='store_true', 
                       help='Skip steps that are already completed')
    parser.add_argument('--runs', type=int, default=3, 
                       help='Number of income analysis runs (default: 3)')
    
    args = parser.parse_args()
    
    orchestrator = PipelineOrchestrator()
    
    if len(args.loan_ids) == 1:
        success = orchestrator.process_loan(args.loan_ids[0], resume=args.resume, num_runs=args.runs)
        sys.exit(0 if success else 1)
    else:
        results = orchestrator.process_multiple_loans(args.loan_ids, resume=args.resume, num_runs=args.runs)
        all_success = all(results.values())
        sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
