"""
Create Interactive HTML Timeline Visualization

Generates a visual timeline showing both:
1. Underwriting Process Timeline (when documents were created/collected)
2. Historical Data Timeline (dates within documents - credit history, income history, etc.)
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
from collections import defaultdict

def load_all_loan_json_files(loan_id: str) -> Dict[str, Dict]:
    """Load all JSON files for a given loan."""
    json_dir = Path(f"loan_docs/{loan_id}/json")
    
    if not json_dir.exists():
        print(f"JSON directory not found: {json_dir}")
        return {}
    
    json_files = {}
    for json_file in json_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                json_files[json_file.stem] = data
        except Exception as e:
            print(f"Error loading {json_file.name}: {e}")
    
    return json_files


def extract_all_dates(json_data: Dict[str, Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Extract dates from JSON files and categorize them as:
    1. Process dates (document creation, underwriting events)
    2. Historical dates (data within documents)
    """
    
    process_events = []
    historical_events = []
    
    # Keywords that indicate process/underwriting timeline
    process_keywords = [
        'document_date', 'report_date', 'created_date', 'application_date',
        'appraisal_date', 'closing_date', 'signature_date', 'signed_date',
        'lock_date', 'order_date', 'effective_date', 'issue_date',
        'statement_date', 'pay_date', 'verification_date'
    ]
    
    # Keywords that indicate historical/data timeline
    historical_keywords = [
        'opened_date', 'date_opened', 'purchase_date', 'origination_date',
        'first_payment_date', 'last_activity', 'opening_date',
        'tax_year', 'pay_period_start', 'pay_period_end'
    ]
    
    for doc_name, doc_data in json_data.items():
        doc_type = doc_data.get('document_type', 'Unknown')
        
        # Extract process dates
        for key in process_keywords:
            if key in doc_data:
                date_str = doc_data[key]
                try:
                    if isinstance(date_str, str):
                        # Try multiple date formats
                        date_obj = None
                        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d', '%m-%d-%Y']:
                            try:
                                date_obj = datetime.strptime(date_str, fmt)
                                break
                            except:
                                continue
                        
                        if date_obj:
                            process_events.append({
                                'date': date_obj,
                                'date_str': date_str,
                                'event': f"{doc_type} - {key.replace('_', ' ').title()}",
                                'document': doc_name,
                                'category': 'Process'
                            })
                except Exception as e:
                    pass
        
        # Extract historical dates from specific document types
        
        # Credit report trade lines
        if 'trade_lines' in doc_data:
            for trade_line in doc_data['trade_lines']:
                if isinstance(trade_line, dict):
                    for key in ['date_opened', 'opened_date', 'opening_date']:
                        if key in trade_line:
                            date_str = trade_line[key]
                            try:
                                if isinstance(date_str, str):
                                    date_obj = None
                                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d', '%m-%d-%Y']:
                                        try:
                                            date_obj = datetime.strptime(date_str, fmt)
                                            break
                                        except:
                                            continue
                                    
                                    if date_obj:
                                        creditor = trade_line.get('creditor_name', 'Unknown')
                                        historical_events.append({
                                            'date': date_obj,
                                            'date_str': date_str,
                                            'event': f"Credit Account Opened: {creditor}",
                                            'document': doc_name,
                                            'category': 'Credit History'
                                        })
                            except Exception as e:
                                pass
        
        # W-2 tax years
        if 'tax_year' in doc_data:
            try:
                tax_year = doc_data['tax_year']
                if isinstance(tax_year, (int, str)):
                    date_obj = datetime(int(tax_year), 12, 31)
                    employer = doc_data.get('employer_name', 'Unknown')
                    historical_events.append({
                        'date': date_obj,
                        'date_str': str(tax_year),
                        'event': f"W-2 Tax Year: {employer}",
                        'document': doc_name,
                        'category': 'Income History'
                    })
            except Exception as e:
                pass
        
        # Property purchase/deed dates
        if doc_type == 'Appraisal' or 'appraisal' in doc_name.lower():
            for key in ['purchase_date', 'prior_sale_date', 'deed_date']:
                if key in doc_data:
                    date_str = doc_data[key]
                    try:
                        if isinstance(date_str, str):
                            date_obj = None
                            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d', '%m-%d-%Y']:
                                try:
                                    date_obj = datetime.strptime(date_str, fmt)
                                    break
                                except:
                                    continue
                            
                            if date_obj:
                                historical_events.append({
                                    'date': date_obj,
                                    'date_str': date_str,
                                    'event': f"Property {key.replace('_', ' ').title()}",
                                    'document': doc_name,
                                    'category': 'Property History'
                                })
                    except Exception as e:
                        pass
    
    # Sort by date
    process_events.sort(key=lambda x: x['date'])
    historical_events.sort(key=lambda x: x['date'])
    
    return process_events, historical_events


def create_html_timeline(loan_id: str, process_events: List[Dict], historical_events: List[Dict]) -> str:
    """Create an interactive HTML timeline visualization."""
    
    # Get date range
    all_events = process_events + historical_events
    if not all_events:
        return "<html><body>No events found</body></html>"
    
    min_date = min(e['date'] for e in all_events)
    max_date = max(e['date'] for e in all_events)
    
    # Create HTML with embedded CSS and JavaScript
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Loan Timeline Analysis - {loan_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
        }}
        
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 16px;
            opacity: 0.9;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 3px solid #e9ecef;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .stat-card .number {{
            font-size: 36px;
            font-weight: bold;
            color: #2a5298;
            margin-bottom: 5px;
        }}
        
        .stat-card .label {{
            font-size: 14px;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .timeline-controls {{
            padding: 20px 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}
        
        .timeline-controls button {{
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        
        .timeline-controls button.active {{
            background: #2a5298;
            color: white;
        }}
        
        .timeline-controls button:not(.active) {{
            background: white;
            color: #495057;
            border: 2px solid #dee2e6;
        }}
        
        .timeline-controls button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .timeline-section {{
            padding: 40px 30px;
        }}
        
        .timeline-title {{
            font-size: 24px;
            font-weight: bold;
            color: #1e3c72;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 3px solid #2a5298;
        }}
        
        .timeline {{
            position: relative;
            padding-left: 40px;
        }}
        
        .timeline::before {{
            content: '';
            position: absolute;
            left: 20px;
            top: 0;
            bottom: 0;
            width: 3px;
            background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        }}
        
        .timeline-event {{
            position: relative;
            margin-bottom: 30px;
            padding: 20px;
            background: white;
            border-radius: 8px;
            border-left: 4px solid #2a5298;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: all 0.3s;
        }}
        
        .timeline-event:hover {{
            transform: translateX(5px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        }}
        
        .timeline-event::before {{
            content: '';
            position: absolute;
            left: -44px;
            top: 25px;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: white;
            border: 4px solid #2a5298;
            z-index: 1;
        }}
        
        .timeline-event.process {{
            border-left-color: #28a745;
        }}
        
        .timeline-event.process::before {{
            border-color: #28a745;
        }}
        
        .timeline-event.historical {{
            border-left-color: #fd7e14;
        }}
        
        .timeline-event.historical::before {{
            border-color: #fd7e14;
        }}
        
        .event-date {{
            font-size: 18px;
            font-weight: bold;
            color: #2a5298;
            margin-bottom: 8px;
        }}
        
        .event-title {{
            font-size: 16px;
            font-weight: 600;
            color: #212529;
            margin-bottom: 5px;
        }}
        
        .event-document {{
            font-size: 13px;
            color: #6c757d;
            font-style: italic;
        }}
        
        .event-category {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-top: 8px;
        }}
        
        .category-process {{
            background: #d4edda;
            color: #155724;
        }}
        
        .category-credit {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .category-income {{
            background: #d1ecf1;
            color: #0c5460;
        }}
        
        .category-property {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .hidden {{
            display: none;
        }}
        
        .legend {{
            display: flex;
            gap: 20px;
            padding: 20px 30px;
            background: #f8f9fa;
            border-top: 1px solid #dee2e6;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}
        
        .legend-label {{
            font-size: 14px;
            color: #495057;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Loan Timeline Analysis</h1>
            <p>Loan ID: {loan_id} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Date Range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="number">{len(process_events)}</div>
                <div class="label">Process Events</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(historical_events)}</div>
                <div class="label">Historical Events</div>
            </div>
            <div class="stat-card">
                <div class="number">{(max_date - min_date).days}</div>
                <div class="label">Days Span</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(set(e['document'] for e in all_events))}</div>
                <div class="label">Documents</div>
            </div>
        </div>
        
        <div class="timeline-controls">
            <button class="active" onclick="showTimeline('all')">All Events</button>
            <button onclick="showTimeline('process')">Process Timeline</button>
            <button onclick="showTimeline('historical')">Historical Data</button>
            <button onclick="showTimeline('2025')">2025 Only</button>
        </div>
        
        <div class="timeline-section">
            <div class="timeline-title">📅 Underwriting Process Timeline</div>
            <div class="timeline" id="process-timeline">
"""
    
    # Add process events
    for event in process_events:
        html += f"""
                <div class="timeline-event process" data-timeline="process" data-year="{event['date'].year}">
                    <div class="event-date">{event['date'].strftime('%B %d, %Y')}</div>
                    <div class="event-title">{event['event']}</div>
                    <div class="event-document">Document: {event['document']}</div>
                    <span class="event-category category-process">Process Event</span>
                </div>
"""
    
    html += """
            </div>
        </div>
        
        <div class="timeline-section">
            <div class="timeline-title">📚 Historical Data Timeline</div>
            <div class="timeline" id="historical-timeline">
"""
    
    # Add historical events
    for event in historical_events:
        category_class = 'credit' if 'Credit' in event['category'] else \
                        'income' if 'Income' in event['category'] else \
                        'property' if 'Property' in event['category'] else 'process'
        
        html += f"""
                <div class="timeline-event historical" data-timeline="historical" data-year="{event['date'].year}">
                    <div class="event-date">{event['date'].strftime('%B %d, %Y')}</div>
                    <div class="event-title">{event['event']}</div>
                    <div class="event-document">Source: {event['document']}</div>
                    <span class="event-category category-{category_class}">{event['category']}</span>
                </div>
"""
    
    html += """
            </div>
        </div>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background: #28a745;"></div>
                <span class="legend-label">Process Events (when documents created)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #fd7e14;"></div>
                <span class="legend-label">Historical Events (dates within documents)</span>
            </div>
        </div>
    </div>
    
    <script>
        function showTimeline(filter) {
            // Update button states
            document.querySelectorAll('.timeline-controls button').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Show/hide events
            const allEvents = document.querySelectorAll('.timeline-event');
            
            allEvents.forEach(event => {
                if (filter === 'all') {
                    event.classList.remove('hidden');
                } else if (filter === 'process') {
                    event.classList.toggle('hidden', !event.classList.contains('process'));
                } else if (filter === 'historical') {
                    event.classList.toggle('hidden', !event.classList.contains('historical'));
                } else if (filter === '2025') {
                    event.classList.toggle('hidden', event.getAttribute('data-year') !== '2025');
                }
            });
        }
    </script>
</body>
</html>
"""
    
    return html


def main():
    loan_id = "1000182227"
    
    print(f"Loading loan documents for {loan_id}...")
    json_data = load_all_loan_json_files(loan_id)
    
    if not json_data:
        print("No JSON files found!")
        return
    
    print(f"Loaded {len(json_data)} documents")
    
    print("Extracting timeline events...")
    process_events, historical_events = extract_all_dates(json_data)
    
    print(f"Found {len(process_events)} process events")
    print(f"Found {len(historical_events)} historical events")
    
    print("Creating HTML visualization...")
    html_content = create_html_timeline(loan_id, process_events, historical_events)
    
    # Save HTML file
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_file = report_dir / f"timeline_visualization_{loan_id}_{timestamp}.html"
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n{'='*80}")
    print(f"✅ Timeline visualization created!")
    print(f"📄 File: {html_file}")
    print(f"{'='*80}\n")
    print(f"Open the file in your browser to view the interactive timeline.")
    
    return html_file


if __name__ == "__main__":
    main()
