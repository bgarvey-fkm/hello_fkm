"""
Underwriting Primitives Timeline Agent

Tracks key underwriting metrics (FICO, CLTV, DTI) as they evolve throughout the loan process.
Shows only information that would have been available at each point in time.

Key Primitives Tracked:
- FICO Score (Credit)
- Monthly Income (for DTI)
- Loan Amount (Second Lien/HELOC)
- First Lien Amount
- Property Value (for CLTV)

Derived Metrics:
- CLTV = (First Lien + Second Lien) / Property Value × 100
- DTI = Total Monthly Debt Payments / Monthly Income × 100

Usage:
    python agents/underwriting_primitives_timeline_agent.py <loan_id>

Example:
    python agents/underwriting_primitives_timeline_agent.py 1000182005
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")


def load_semantic_json_files(loan_id: str) -> list[dict]:
    """Load all semantic JSON files for the loan."""
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"❌ Semantic JSON directory not found: {semantic_dir}")
        return []
    
    json_files = list(semantic_dir.glob("*.json"))
    
    if not json_files:
        print(f"❌ No semantic JSON files found in {semantic_dir}")
        return []
    
    print(f"\n📂 Loading {len(json_files)} semantic JSON files...")
    
    documents = []
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['source_filename'] = json_file.name
                documents.append(data)
        except Exception as e:
            print(f"   ✗ Error loading {json_file.name}: {e}")
    
    print(f"✓ Loaded {len(documents)} semantic documents")
    return documents


def analyze_primitives_timeline(loan_id: str, documents: list[dict]) -> dict:
    """Use LLM to extract underwriting primitives at each point in the timeline."""
    
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION
    )
    
    system_prompt = """You are an expert mortgage underwriter analyzing loan file evolution.

Your task is to track key underwriting primitives as they become available throughout the loan process.

KEY PRIMITIVES TO TRACK:
1. FICO Score - Credit score (lowest of all borrowers)
2. Monthly Qualifying Income - Total monthly gross income
3. Second Lien Amount - HELOC/Second mortgage amount
4. First Lien Balance - Existing first mortgage balance
5. Property Value - Appraised or estimated property value
6. Total Monthly Debt - All monthly debt payments (for DTI)

DERIVED METRICS:
- CLTV = (First Lien + Second Lien) / Property Value × 100
- DTI = Total Monthly Debt / Monthly Income × 100

TIMELINE RULES:
- August 18 (Application): Only use information from 1003 application
  * Self-reported FICO, income, property value (estimate), first lien balance
  * Second lien amount (loan request)
- August 20-22 (Post-Application): Same as application + any disclosures
- August 25 (Valuation): Add actual property value from AVM/Appraisal
- August 22+ (VOE): Add verified income from VOE/paystubs
- September 24 (Credit Pull): Add actual FICO scores from credit report
- September 8+ (Underwriting): Add final verified amounts

For each date/milestone, extract:
- What information was NEWLY available at that point
- What the primitive values were (estimated vs verified)
- Source of information (1003, credit report, appraisal, VOE, etc.)
- Whether it's self-reported, estimated, or verified

Return a timeline showing how each primitive evolved from application to closing."""

    # Prepare document summary
    doc_summaries = []
    for i, doc in enumerate(documents[:60]):  # Analyze up to 60 docs
        doc_summaries.append({
            "index": i,
            "filename": doc.get('source_filename', 'unknown'),
            "document_type": doc.get('document_type', 'unknown'),
            "summary": doc.get('summary', 'No summary')[:500],
            "key_entities": doc.get('key_entities', [])[:15]
        })
    
    user_prompt = f"""Analyze the underwriting primitives timeline for loan {loan_id}.

Extract the evolution of key underwriting metrics throughout the loan process.

Documents:
{json.dumps(doc_summaries, indent=2)}

Return a JSON object with this structure:
{{
  "loan_id": "{loan_id}",
  "analysis_date": "{datetime.now().strftime('%Y-%m-%d')}",
  "timeline_snapshots": [
    {{
      "date": "2025-08-18",
      "milestone": "Application Submitted",
      "data_source": "1003 Application",
      "primitives": {{
        "fico_score": {{
          "value": number or null,
          "source": "Self-Reported|Credit Report|Not Available",
          "status": "Estimated|Verified|Unknown",
          "notes": "string"
        }},
        "monthly_income": {{
          "value": number or null,
          "source": "1003|Paystubs|VOE|Not Available",
          "status": "Estimated|Verified|Unknown",
          "notes": "string"
        }},
        "second_lien_amount": {{
          "value": number or null,
          "source": "1003|Loan Estimate|Final CD|Not Available",
          "status": "Requested|Final|Unknown",
          "notes": "string"
        }},
        "first_lien_balance": {{
          "value": number or null,
          "source": "1003|Mortgage Statement|Payoff|Not Available",
          "status": "Estimated|Verified|Unknown",
          "notes": "string"
        }},
        "property_value": {{
          "value": number or null,
          "source": "1003 Estimate|AVM|Appraisal|Not Available",
          "status": "Estimated|Verified|Unknown",
          "notes": "string"
        }},
        "total_monthly_debt": {{
          "value": number or null,
          "source": "1003|Credit Report|Not Available",
          "status": "Estimated|Verified|Unknown",
          "notes": "string"
        }}
      }},
      "derived_metrics": {{
        "cltv": number or null,
        "dti": number or null,
        "notes": "string"
      }},
      "changes_from_previous": ["string (what changed)"]
    }}
  ],
  "final_metrics": {{
    "fico_score": number,
    "monthly_income": number,
    "second_lien_amount": number,
    "first_lien_balance": number,
    "property_value": number,
    "total_monthly_debt": number,
    "cltv": number,
    "dti": number
  }},
  "metric_evolution_summary": {{
    "fico": {{
      "initial": number,
      "final": number,
      "change": number,
      "change_reason": "string"
    }},
    "property_value": {{
      "initial": number,
      "final": number,
      "change": number,
      "change_reason": "string"
    }},
    "cltv": {{
      "initial": number,
      "final": number,
      "change": number,
      "change_reason": "string"
    }},
    "dti": {{
      "initial": number,
      "final": number,
      "change": number,
      "change_reason": "string"
    }}
  }}
}}"""

    print(f"\n🤖 Analyzing primitives timeline with Azure OpenAI ({AZURE_OPENAI_DEPLOYMENT})...")
    
    try:
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=16000
        )
        
        analysis = json.loads(response.choices[0].message.content)
        
        # Add metadata
        analysis['metadata'] = {
            'agent': 'underwriting_primitives_timeline_agent',
            'version': '1.0',
            'model': AZURE_OPENAI_DEPLOYMENT,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error during LLM analysis: {e}")
        raise


def generate_html_timeline(loan_id: str, analysis: dict) -> str:
    """Generate interactive HTML visualization of primitives timeline."""
    
    timeline_data = []
    for snapshot in analysis.get('timeline_snapshots', []):
        prims = snapshot.get('primitives', {})
        derived = snapshot.get('derived_metrics', {})
        
        timeline_data.append({
            'date': snapshot.get('date'),
            'milestone': snapshot.get('milestone'),
            'source': snapshot.get('data_source'),
            'fico': prims.get('fico_score', {}).get('value'),
            'fico_status': prims.get('fico_score', {}).get('status'),
            'income': prims.get('monthly_income', {}).get('value'),
            'income_status': prims.get('monthly_income', {}).get('status'),
            'second_lien': prims.get('second_lien_amount', {}).get('value'),
            'first_lien': prims.get('first_lien_balance', {}).get('value'),
            'property_value': prims.get('property_value', {}).get('value'),
            'property_status': prims.get('property_value', {}).get('status'),
            'total_debt': prims.get('total_monthly_debt', {}).get('value'),
            'cltv': derived.get('cltv'),
            'dti': derived.get('dti'),
            'changes': snapshot.get('changes_from_previous', [])
        })
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Underwriting Primitives Timeline - Loan {loan_id}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
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
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            color: #667eea;
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: #666;
            font-size: 16px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .metric-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
        }}
        
        .metric-label {{
            font-size: 12px;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }}
        
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
        }}
        
        .metric-change {{
            font-size: 14px;
            padding: 4px 8px;
            border-radius: 4px;
            display: inline-block;
        }}
        
        .metric-change.positive {{
            background: #d4edda;
            color: #155724;
        }}
        
        .metric-change.negative {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .metric-change.neutral {{
            background: #d1ecf1;
            color: #0c5460;
        }}
        
        .charts-section {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }}
        
        .chart-container {{
            position: relative;
            height: 400px;
            margin-bottom: 40px;
        }}
        
        .timeline-section {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
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
            width: 2px;
            background: linear-gradient(to bottom, #667eea, #764ba2);
        }}
        
        .timeline-item {{
            position: relative;
            margin-bottom: 40px;
            padding-left: 20px;
        }}
        
        .timeline-item::before {{
            content: '';
            position: absolute;
            left: -27px;
            top: 0;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: white;
            border: 3px solid #667eea;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2);
        }}
        
        .timeline-date {{
            font-size: 14px;
            color: #667eea;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .timeline-milestone {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        
        .timeline-source {{
            font-size: 12px;
            color: #999;
            margin-bottom: 15px;
        }}
        
        .primitives-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
            font-size: 14px;
        }}
        
        .primitives-table th {{
            background: #f8f9fa;
            padding: 10px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #dee2e6;
        }}
        
        .primitives-table td {{
            padding: 10px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .status-badge {{
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .status-verified {{
            background: #d4edda;
            color: #155724;
        }}
        
        .status-estimated {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .status-unknown {{
            background: #e2e3e5;
            color: #383d41;
        }}
        
        .changes-list {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 12px;
            border-radius: 4px;
            margin-top: 10px;
        }}
        
        .changes-list li {{
            margin-left: 20px;
            margin-bottom: 5px;
            color: #666;
        }}
        
        h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 24px;
        }}
        
        .legend {{
            display: flex;
            gap: 20px;
            margin-top: 15px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Underwriting Primitives Timeline</h1>
            <p>Loan ID: <strong>{loan_id}</strong> | Analysis Date: {datetime.now().strftime('%B %d, %Y')}</p>
            <p style="margin-top: 10px; font-style: italic;">Tracking key underwriting metrics as they evolved from application to closing</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">FICO Score</div>
                <div class="metric-value">{analysis.get('final_metrics', {}).get('fico_score') or 'N/A'}</div>
                <div class="metric-change {_get_change_class(analysis.get('metric_evolution_summary', {}).get('fico', {}).get('change'))}">
                    {_format_change(analysis.get('metric_evolution_summary', {}).get('fico', {}).get('change'))} from application
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Property Value</div>
                <div class="metric-value">${analysis.get('final_metrics', {}).get('property_value') or 0:,.0f}</div>
                <div class="metric-change {_get_change_class(analysis.get('metric_evolution_summary', {}).get('property_value', {}).get('change'))}">
                    {_format_change(analysis.get('metric_evolution_summary', {}).get('property_value', {}).get('change'), is_currency=True)} from application
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">CLTV (Combined LTV)</div>
                <div class="metric-value">{(analysis.get('final_metrics', {}).get('cltv') or 0):.1f}%</div>
                <div class="metric-change {_get_change_class(analysis.get('metric_evolution_summary', {}).get('cltv', {}).get('change'))}">
                    {_format_change(analysis.get('metric_evolution_summary', {}).get('cltv', {}).get('change'), is_percent=True)} from application
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">DTI (Debt-to-Income)</div>
                <div class="metric-value">{(analysis.get('final_metrics', {}).get('dti') or 0):.1f}%</div>
                <div class="metric-change {_get_change_class(analysis.get('metric_evolution_summary', {}).get('dti', {}).get('change'))}">
                    {_format_change(analysis.get('metric_evolution_summary', {}).get('dti', {}).get('change'), is_percent=True)} from application
                </div>
            </div>
        </div>
        
        <div class="charts-section">
            <h2>📈 Metrics Evolution Over Time</h2>
            
            <div class="chart-container">
                <canvas id="cltv-dti-chart"></canvas>
            </div>
            
            <div class="chart-container">
                <canvas id="primitives-chart"></canvas>
            </div>
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #667eea;"></div>
                    <span>CLTV %</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #f093fb;"></div>
                    <span>DTI %</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #4facfe;"></div>
                    <span>FICO Score</span>
                </div>
                <div class="legend-item">
                    <span class="status-badge status-estimated">Estimated</span>
                    <span>Self-reported or preliminary data</span>
                </div>
                <div class="legend-item">
                    <span class="status-badge status-verified">Verified</span>
                    <span>Confirmed from authoritative source</span>
                </div>
            </div>
        </div>
        
        <div class="timeline-section">
            <h2>📅 Detailed Timeline</h2>
            <div class="timeline">
                {_generate_timeline_items(timeline_data)}
            </div>
        </div>
    </div>
    
    <script>
        const timelineData = {json.dumps(timeline_data)};
        
        // CLTV and DTI Chart
        const cltvDtiCtx = document.getElementById('cltv-dti-chart').getContext('2d');
        new Chart(cltvDtiCtx, {{
            type: 'line',
            data: {{
                labels: timelineData.map(d => d.date + '\\n' + d.milestone.substring(0, 20)),
                datasets: [
                    {{
                        label: 'CLTV %',
                        data: timelineData.map(d => d.cltv),
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 6,
                        pointHoverRadius: 8
                    }},
                    {{
                        label: 'DTI %',
                        data: timelineData.map(d => d.dti),
                        borderColor: '#f093fb',
                        backgroundColor: 'rgba(240, 147, 251, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 6,
                        pointHoverRadius: 8
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'CLTV and DTI Evolution',
                        font: {{ size: 18, weight: 'bold' }}
                    }},
                    legend: {{
                        display: true,
                        position: 'top'
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false,
                        callbacks: {{
                            label: function(context) {{
                                return context.dataset.label + ': ' + (context.parsed.y ? context.parsed.y.toFixed(1) + '%' : 'N/A');
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Percentage (%)'
                        }}
                    }}
                }}
            }}
        }});
        
        // Primitives Chart (FICO, Income, Values)
        const primitivesCtx = document.getElementById('primitives-chart').getContext('2d');
        new Chart(primitivesCtx, {{
            type: 'line',
            data: {{
                labels: timelineData.map(d => d.date + '\\n' + d.milestone.substring(0, 20)),
                datasets: [
                    {{
                        label: 'FICO Score',
                        data: timelineData.map(d => d.fico),
                        borderColor: '#4facfe',
                        backgroundColor: 'rgba(79, 172, 254, 0.1)',
                        borderWidth: 3,
                        yAxisID: 'y-fico',
                        tension: 0.4,
                        pointRadius: 6,
                        pointHoverRadius: 8
                    }},
                    {{
                        label: 'Monthly Income ($)',
                        data: timelineData.map(d => d.income),
                        borderColor: '#43e97b',
                        backgroundColor: 'rgba(67, 233, 123, 0.1)',
                        borderWidth: 3,
                        yAxisID: 'y-dollars',
                        tension: 0.4,
                        pointRadius: 6,
                        pointHoverRadius: 8
                    }},
                    {{
                        label: 'Property Value ($)',
                        data: timelineData.map(d => d.property_value),
                        borderColor: '#fa709a',
                        backgroundColor: 'rgba(250, 112, 154, 0.1)',
                        borderWidth: 3,
                        yAxisID: 'y-dollars',
                        tension: 0.4,
                        pointRadius: 6,
                        pointHoverRadius: 8
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Key Primitives Evolution',
                        font: {{ size: 18, weight: 'bold' }}
                    }},
                    legend: {{
                        display: true,
                        position: 'top'
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false,
                        callbacks: {{
                            label: function(context) {{
                                let label = context.dataset.label || '';
                                if (label) {{
                                    label += ': ';
                                }}
                                if (context.parsed.y !== null) {{
                                    if (label.includes('$')) {{
                                        label += '$' + context.parsed.y.toLocaleString();
                                    }} else {{
                                        label += context.parsed.y.toFixed(0);
                                    }}
                                }}
                                return label;
                            }}
                        }}
                    }}
                }},
                scales: {{
                    'y-fico': {{
                        type: 'linear',
                        position: 'left',
                        title: {{
                            display: true,
                            text: 'FICO Score'
                        }},
                        min: 600,
                        max: 850
                    }},
                    'y-dollars': {{
                        type: 'linear',
                        position: 'right',
                        title: {{
                            display: true,
                            text: 'Dollar Amount ($)'
                        }},
                        grid: {{
                            drawOnChartArea: false
                        }},
                        ticks: {{
                            callback: function(value) {{
                                return '$' + (value/1000).toFixed(0) + 'K';
                            }}
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
    
    return html_content


def _get_change_class(change):
    """Get CSS class for change indicator."""
    if change is None or change == 0:
        return 'neutral'
    return 'positive' if change > 0 else 'negative'


def _format_change(change, is_currency=False, is_percent=False):
    """Format change value with appropriate symbol."""
    if change is None:
        return 'N/A'
    if change == 0:
        return 'No change'
    
    sign = '+' if change > 0 else ''
    
    try:
        if is_currency:
            return f'{sign}${abs(change):,.0f}'
        elif is_percent:
            return f'{sign}{change:.1f}%'
        else:
            return f'{sign}{change}'
    except (TypeError, ValueError):
        return 'N/A'


def _generate_timeline_items(timeline_data):
    """Generate HTML for timeline items."""
    html = ""
    
    for item in timeline_data:
        changes_html = ""
        if item.get('changes'):
            changes_html = '<ul class="changes-list">'
            for change in item['changes']:
                changes_html += f'<li>{change}</li>'
            changes_html += '</ul>'
        
        fico_val = f"{item['fico']}" if item.get('fico') else "Not Available"
        fico_status = item.get('fico_status', 'Unknown')
        
        income_val = f"${item['income']:,.0f}" if item.get('income') else "Not Available"
        income_status = item.get('income_status', 'Unknown')
        
        property_val = f"${item['property_value']:,.0f}" if item.get('property_value') else "Not Available"
        property_status = item.get('property_status', 'Unknown')
        
        second_lien = f"${item['second_lien']:,.0f}" if item.get('second_lien') else "Not Available"
        first_lien = f"${item['first_lien']:,.0f}" if item.get('first_lien') else "Not Available"
        
        cltv_val = f"{item['cltv']:.1f}%" if item.get('cltv') else "Cannot Calculate"
        dti_val = f"{item['dti']:.1f}%" if item.get('dti') else "Cannot Calculate"
        
        html += f"""
        <div class="timeline-item">
            <div class="timeline-date">{item['date']}</div>
            <div class="timeline-milestone">{item['milestone']}</div>
            <div class="timeline-source">📄 {item['source']}</div>
            
            <table class="primitives-table">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>FICO Score</strong></td>
                        <td>{fico_val}</td>
                        <td><span class="status-badge status-{fico_status.lower()}">{fico_status}</span></td>
                    </tr>
                    <tr>
                        <td><strong>Monthly Income</strong></td>
                        <td>{income_val}</td>
                        <td><span class="status-badge status-{income_status.lower()}">{income_status}</span></td>
                    </tr>
                    <tr>
                        <td><strong>Property Value</strong></td>
                        <td>{property_val}</td>
                        <td><span class="status-badge status-{property_status.lower()}">{property_status}</span></td>
                    </tr>
                    <tr>
                        <td><strong>Second Lien (HELOC)</strong></td>
                        <td>{second_lien}</td>
                        <td><span class="status-badge status-estimated">Requested</span></td>
                    </tr>
                    <tr>
                        <td><strong>First Lien Balance</strong></td>
                        <td>{first_lien}</td>
                        <td><span class="status-badge status-estimated">Estimated</span></td>
                    </tr>
                    <tr style="background: #f8f9fa; font-weight: bold;">
                        <td><strong>CLTV</strong></td>
                        <td>{cltv_val}</td>
                        <td>—</td>
                    </tr>
                    <tr style="background: #f8f9fa; font-weight: bold;">
                        <td><strong>DTI</strong></td>
                        <td>{dti_val}</td>
                        <td>—</td>
                    </tr>
                </tbody>
            </table>
            
            {changes_html}
        </div>
        """
    
    return html


def save_reports(loan_id: str, analysis: dict) -> tuple[str, str]:
    """Save JSON and HTML reports."""
    reports_dir = Path(f"loan_docs/{loan_id}/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON
    json_path = reports_dir / f"primitives_timeline_{loan_id}_{timestamp}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2)
    
    # Save HTML
    html_path = reports_dir / f"primitives_timeline_{loan_id}_{timestamp}.html"
    html_content = generate_html_timeline(loan_id, analysis)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return str(json_path), str(html_path)


def main():
    """Main execution function."""
    if len(sys.argv) < 2:
        print("Usage: python agents/underwriting_primitives_timeline_agent.py <loan_id>")
        print("Example: python agents/underwriting_primitives_timeline_agent.py 1000182005")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    
    print(f"\n🚀 Starting Underwriting Primitives Timeline Agent for Loan {loan_id}")
    print("="*80)
    
    # Load documents
    documents = load_semantic_json_files(loan_id)
    if not documents:
        print("❌ No semantic documents found. Exiting.")
        sys.exit(1)
    
    # Analyze timeline
    try:
        analysis = analyze_primitives_timeline(loan_id, documents)
        print("✓ Primitives timeline analysis completed")
    except Exception as e:
        print(f"❌ Failed to analyze timeline: {e}")
        sys.exit(1)
    
    # Save reports
    try:
        json_path, html_path = save_reports(loan_id, analysis)
        print(f"✓ JSON report saved to: {json_path}")
        print(f"✓ HTML visualization saved to: {html_path}")
    except Exception as e:
        print(f"❌ Failed to save reports: {e}")
        sys.exit(1)
    
    # Display summary
    print("\n" + "="*80)
    print("📊 UNDERWRITING PRIMITIVES SUMMARY")
    print("="*80)
    
    final = analysis.get('final_metrics', {})
    print(f"\n✅ FINAL METRICS:")
    print(f"   FICO Score: {final.get('fico_score') or 'N/A'}")
    print(f"   Monthly Income: ${(final.get('monthly_income') or 0):,.2f}")
    print(f"   Property Value: ${(final.get('property_value') or 0):,.0f}")
    print(f"   Second Lien: ${(final.get('second_lien_amount') or 0):,.0f}")
    print(f"   First Lien: ${(final.get('first_lien_balance') or 0):,.0f}")
    print(f"   CLTV: {(final.get('cltv') or 0):.1f}%")
    print(f"   DTI: {(final.get('dti') or 0):.1f}%")
    
    print(f"\n📈 METRIC EVOLUTION:")
    evo = analysis.get('metric_evolution_summary', {})
    for metric_name, metric_data in evo.items():
        if metric_data:
            change = metric_data.get('change')
            if change is not None:
                sign = '+' if change > 0 else ''
                print(f"   {metric_name.upper()}: {metric_data.get('initial')} → {metric_data.get('final')} ({sign}{change})")
                print(f"      Reason: {metric_data.get('change_reason', 'N/A')}")
    
    print(f"\n✅ Timeline analysis completed successfully!")
    print(f"🌐 Open the HTML file in your browser to view the interactive timeline:")
    print(f"   {html_path}\n")


if __name__ == "__main__":
    main()
