"""
Unified Loan Processing Pipeline Orchestrator
==============================================
Single entry point for processing loans from raw PDFs to income analysis.

Usage:
    # Process single loan
    python pipeline/orchestrate_loan_processing.py 1000178625
    
    # Process with specific steps
    python pipeline/orchestrate_loan_processing.py 1000178625 --steps ocr,semantic,analysis
    
    # Process multiple loans
    python pipeline/orchestrate_loan_processing.py 1000178625 1000178635 1000178636
    
    # Skip completed steps (resume from failure)
    python pipeline/orchestrate_loan_processing.py 1000178625 --resume

Pipeline Steps:
    1. harvest_ocr: Download from Harvest API + Document Intelligence OCR
    2. semantic: Convert to semantic JSON
    3. classify: Classify income-relevant documents
    4. form1003: Extract Form 1003 timeline
    5. employment: Generate employment history
    6. analysis: Run income analysis (default 3 runs)

Architecture:
    - Each step is a composable function
    - Steps check prerequisites and skip if already completed
    - Centralized error handling and logging
    - Progress tracking and resumability
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional, Set
from datetime import datetime
import argparse

# Import the actual processing functions
sys.path.append(str(Path(__file__).parent.parent))


class PipelineStep:
    """Represents a single pipeline step with dependencies and execution logic."""
    
    def __init__(self, name: str, description: str, check_completed, execute, dependencies=None):
        self.name = name
        self.description = description
        self.check_completed = check_completed
        self.execute = execute
        self.dependencies = dependencies or []
    
    async def run(self, loan_id: str, context: dict) -> bool:
        """Run this step for a loan."""
        # Check if already completed
        if self.check_completed(loan_id):
            print(f"  ✅ {self.name}: Already completed, skipping")
            return True
        
        # Execute
        print(f"  🔄 {self.name}: {self.description}")
        try:
            success = await self.execute(loan_id, context)
            if success:
                print(f"  ✅ {self.name}: Completed")
            else:
                print(f"  ❌ {self.name}: Failed")
            return success
        except Exception as e:
            print(f"  ❌ {self.name}: Error - {e}")
            return False


class LoanPipeline:
    """Orchestrates the complete loan processing pipeline."""
    
    def __init__(self):
        self.steps = self._define_steps()
    
    def _define_steps(self) -> dict:
        """Define all pipeline steps with their logic."""
        return {
            'harvest_ocr': PipelineStep(
                name='harvest_ocr',
                description='Download PDFs from Harvest API and run Document Intelligence OCR',
                check_completed=self._check_ocr_completed,
                execute=self._execute_harvest_ocr
            ),
            'semantic': PipelineStep(
                name='semantic',
                description='Convert Document Intelligence output to semantic JSON',
                check_completed=self._check_semantic_completed,
                execute=self._execute_semantic,
                dependencies=['harvest_ocr']
            ),
            'classify': PipelineStep(
                name='classify',
                description='Classify income-relevant documents',
                check_completed=self._check_classify_completed,
                execute=self._execute_classify,
                dependencies=['semantic']
            ),
            'form1003': PipelineStep(
                name='form1003',
                description='Extract Form 1003 income timeline',
                check_completed=self._check_form1003_completed,
                execute=self._execute_form1003,
                dependencies=['semantic']  # Only needs semantic, not classify
            ),
            'employment': PipelineStep(
                name='employment',
                description='Generate employment history',
                check_completed=self._check_employment_completed,
                execute=self._execute_employment,
                dependencies=['classify']
            ),
            'analysis': PipelineStep(
                name='analysis',
                description='Run income analysis (3 runs)',
                check_completed=self._check_analysis_completed,
                execute=self._execute_analysis,
                dependencies=['form1003', 'employment']
            )
        }
    
    # Completion check functions
    def _check_ocr_completed(self, loan_id: str) -> bool:
        raw_json_dir = Path(f"loan_docs/{loan_id}/raw_json")
        return raw_json_dir.exists() and len(list(raw_json_dir.glob("*.json"))) > 0
    
    def _check_semantic_completed(self, loan_id: str) -> bool:
        semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
        return semantic_dir.exists() and len(list(semantic_dir.glob("*.json"))) > 0
    
    def _check_classify_completed(self, loan_id: str) -> bool:
        # Check if any semantic files have the income_verification_relevant flag
        semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
        if not semantic_dir.exists():
            return False
        
        for file in semantic_dir.glob("*.json"):
            try:
                with open(file) as f:
                    data = json.load(f)
                    if 'income_verification_relevant' in data:
                        return True
            except:
                continue
        return False
    
    def _check_form1003_completed(self, loan_id: str) -> bool:
        timeline_file = Path(f"loan_docs/{loan_id}/income_analysis/form_1003_income_timeline.json")
        return timeline_file.exists()
    
    def _check_employment_completed(self, loan_id: str) -> bool:
        emp_file = Path(f"loan_docs/{loan_id}/employment_history/employment_history.json")
        return emp_file.exists()
    
    def _check_analysis_completed(self, loan_id: str) -> bool:
        # Check for consistency summary (indicates analysis runs completed)
        analysis_dir = Path(f"loan_docs/{loan_id}/income_analysis")
        if not analysis_dir.exists():
            return False
        return len(list(analysis_dir.glob("consistency_summary_*.json"))) > 0
    
    # Execution functions (these would call the actual processing modules)
    async def _execute_harvest_ocr(self, loan_id: str, context: dict) -> bool:
        """Execute Harvest API download + Document Intelligence OCR."""
        from pipeline.process_from_harvest_api import process_loan_from_harvest
        
        metadata_file = f"loan_files_inputs/loan_{loan_id}_tree.json"
        if not Path(metadata_file).exists():
            print(f"    ⚠️  Metadata file not found: {metadata_file}")
            return False
        
        try:
            await process_loan_from_harvest(metadata_file, loan_id)
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    async def _execute_semantic(self, loan_id: str, context: dict) -> bool:
        """Execute semantic JSON conversion."""
        from pipeline.process_semantic_compression import process_loan_semantic
        
        try:
            await process_loan_semantic(loan_id)
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    async def _execute_classify(self, loan_id: str, context: dict) -> bool:
        """Execute income document classification."""
        from pipeline.classify_income_documents import classify_loan_documents
        
        try:
            await classify_loan_documents(loan_id)
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    async def _execute_form1003(self, loan_id: str, context: dict) -> bool:
        """Execute Form 1003 timeline extraction."""
        from agents.form_1003_income_tracker import process_loan_1003
        
        try:
            await process_loan_1003(loan_id)
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    async def _execute_employment(self, loan_id: str, context: dict) -> bool:
        """Execute employment history generation."""
        from agents.employment_history_agent import process_employment_history
        
        try:
            await process_employment_history(loan_id)
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    async def _execute_analysis(self, loan_id: str, context: dict) -> bool:
        """Execute income analysis runs."""
        from agents.income_analysis_agent import run_income_analysis
        
        num_runs = context.get('num_analysis_runs', 3)
        try:
            await run_income_analysis(loan_id, num_runs)
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    async def process_loan(self, loan_id: str, steps: Optional[List[str]] = None, 
                          resume: bool = False, context: dict = None) -> bool:
        """Process a single loan through the pipeline."""
        context = context or {}
        
        print(f"\n{'='*80}")
        print(f"PROCESSING LOAN {loan_id}")
        print(f"{'='*80}")
        
        # Determine which steps to run
        if steps:
            step_list = [self.steps[s] for s in steps if s in self.steps]
        else:
            step_list = list(self.steps.values())
        
        # Execute each step
        for step in step_list:
            # Check dependencies
            for dep in step.dependencies:
                if not self.steps[dep].check_completed(loan_id):
                    print(f"  ⚠️  {step.name}: Dependency '{dep}' not completed, skipping")
                    return False
            
            # Run step
            success = await step.run(loan_id, context)
            if not success and not resume:
                print(f"\n❌ Pipeline failed at step: {step.name}")
                return False
        
        print(f"\n✅ Loan {loan_id} processing completed")
        return True
    
    async def process_multiple_loans(self, loan_ids: List[str], **kwargs) -> dict:
        """Process multiple loans through the pipeline."""
        results = {}
        
        print(f"\n{'='*80}")
        print(f"BATCH PROCESSING {len(loan_ids)} LOANS")
        print(f"{'='*80}")
        print(f"Loans: {', '.join(loan_ids)}")
        print(f"{'='*80}\n")
        
        for loan_id in loan_ids:
            results[loan_id] = await self.process_loan(loan_id, **kwargs)
        
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


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Loan Processing Pipeline Orchestrator')
    parser.add_argument('loan_ids', nargs='+', help='Loan IDs to process')
    parser.add_argument('--steps', help='Comma-separated list of steps to run (default: all)')
    parser.add_argument('--resume', action='store_true', help='Continue even if steps fail')
    parser.add_argument('--runs', type=int, default=3, help='Number of income analysis runs')
    
    args = parser.parse_args()
    
    pipeline = LoanPipeline()
    
    steps = args.steps.split(',') if args.steps else None
    context = {'num_analysis_runs': args.runs}
    
    if len(args.loan_ids) == 1:
        await pipeline.process_loan(args.loan_ids[0], steps=steps, resume=args.resume, context=context)
    else:
        await pipeline.process_multiple_loans(args.loan_ids, steps=steps, resume=args.resume, context=context)


if __name__ == "__main__":
    asyncio.run(main())
