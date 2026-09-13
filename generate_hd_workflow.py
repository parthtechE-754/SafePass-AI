import os
import subprocess

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SafePass Maps Architecture Mindmap HD</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }
  body {
    background: #FFFFFF;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #1F2937;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 30px;
    width: 820px;
    margin: 0 auto;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
  
  .diagram {
    width: 760px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  /* Root Node */
  .node-root {
    background: #1F2937;
    color: #FFFFFF;
    font-size: 13.5px;
    font-weight: 700;
    padding: 9px 36px;
    border-radius: 6px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.12);
    text-align: center;
    letter-spacing: 0.2px;
  }

  /* Top 2 Columns */
  .col-container {
    width: 100%;
    display: grid;
    grid-template-columns: 350px 350px;
    column-gap: 60px;
  }

  .col {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  /* Column Headers */
  .hdr-btn {
    width: 100%;
    border-radius: 6px;
    padding: 10px 16px;
    font-size: 13.5px;
    font-weight: 700;
    color: #FFFFFF;
    text-align: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
  }
  .hdr-btn.green {
    background: #15803D;
  }
  .hdr-btn.blue {
    background: #1D4ED8;
  }

  /* Card */
  .card {
    width: 100%;
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    padding: 9px 12px;
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    min-height: 52px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }
  .card-title {
    font-size: 13px;
    font-weight: 700;
    color: #1F2937;
    line-height: 1.25;
  }
  .card-sub {
    font-size: 10.5px;
    color: #4B5563;
    font-weight: 500;
    margin-top: 3px;
    line-height: 1.2;
  }

  /* Pill Badges - Fixed to top-right corner */
  .badge {
    position: absolute;
    top: -6px;
    right: 12px;
    font-size: 9px;
    font-weight: 700;
    color: #FFFFFF;
    padding: 2px 8px;
    border-radius: 4px;
    letter-spacing: 0.3px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.15);
  }
  .badge.frontend {
    background: #6366F1;
  }
  .badge.backend {
    background: #EA580C;
  }
  .badge.response {
    background: #8B5CF6;
  }
  .badge.database {
    background: #0D9488;
  }

  /* AI Engine (Center Orange) */
  .ai-box {
    width: 100%;
    background: #EA580C;
    border-radius: 8px;
    padding: 13px 20px;
    color: #FFFFFF;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    box-shadow: 0 3px 10px rgba(234, 88, 12, 0.25);
  }
  .ai-box .ai-title {
    font-size: 14.5px;
    font-weight: 800;
    letter-spacing: 0.2px;
  }
  .ai-box .ai-sub {
    font-size: 11px;
    font-weight: 600;
    color: #FFEDD5;
    margin-top: 3px;
  }

  /* Database Box (Teal) */
  .db-box {
    width: 100%;
    background: #CCFBF1;
    border: 1px solid #99F6E4;
    border-radius: 8px;
    padding: 11px 20px;
    position: relative;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    box-shadow: 0 1px 4px rgba(13, 148, 136, 0.1);
  }
  .db-box .db-title {
    font-size: 13.5px;
    font-weight: 700;
    color: #1F2937;
  }
  .db-box .db-sub {
    font-size: 11px;
    color: #4B5563;
    font-weight: 500;
    margin-top: 3px;
  }

  /* Bottom Cards */
  .bottom-card {
    width: 100%;
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    padding: 9px 12px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 52px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }
  .bottom-card .b-title {
    font-size: 13px;
    font-weight: 700;
    color: #1F2937;
  }
  .bottom-card .b-sub {
    font-size: 10.5px;
    color: #4B5563;
    font-weight: 500;
    margin-top: 3px;
  }

  /* Footer */
  .footer {
    margin-top: 18px;
    text-align: center;
  }
  .footer-title {
    font-size: 14px;
    font-weight: 800;
    color: #1F2937;
    letter-spacing: 0.2px;
  }
  .footer-sub {
    font-size: 11.5px;
    font-style: italic;
    color: #4B5563;
    margin-top: 3px;
  }

  /* Clean Connector SVG */
  .connector-svg {
    display: block;
    width: 100%;
  }
  .vert-arrow {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 18px;
  }
</style>
</head>
<body>

<div class="diagram">

  <!-- 1. ROOT -->
  <div class="node-root">Open SafePass Maps</div>

  <!-- SPLIT ARROWS -->
  <!-- Width: 760, Col1 center = 175, Col2 center = 585, Mid = 380 -->
  <svg class="connector-svg" width="760" height="26" viewBox="0 0 760 26">
    <defs>
      <marker id="m1" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 1 2 L 7 5 L 1 8 z" fill="#4B5563" />
      </marker>
    </defs>
    <line x1="380" y1="2" x2="175" y2="24" stroke="#4B5563" stroke-width="1.5" marker-end="url(#m1)" />
    <line x1="380" y1="2" x2="585" y2="24" stroke="#4B5563" stroke-width="1.5" marker-end="url(#m1)" />
  </svg>

  <!-- 2. TOP COLUMNS: PLAN A ROUTE & REPORT A HAZARD -->
  <div class="col-container">
    
    <!-- LEFT: Plan a Route -->
    <div class="col">
      <div class="hdr-btn green">Plan a Route</div>

      <div class="vert-arrow">
        <svg width="12" height="18" viewBox="0 0 12 18">
          <line x1="6" y1="0" x2="6" y2="13" stroke="#4B5563" stroke-width="1.5" />
          <polygon points="2,12 6,17 10,12" fill="#4B5563" />
        </svg>
      </div>

      <div class="card">
        <span class="badge frontend">Frontend</span>
        <div class="card-title">Search Origin &amp; Destination</div>
        <div class="card-sub">MapLibre GL JS map UI</div>
      </div>

      <div class="vert-arrow">
        <svg width="12" height="18" viewBox="0 0 12 18">
          <line x1="6" y1="0" x2="6" y2="13" stroke="#4B5563" stroke-width="1.5" />
          <polygon points="2,12 6,17 10,12" fill="#4B5563" />
        </svg>
      </div>

      <div class="card">
        <span class="badge frontend">Frontend</span>
        <div class="card-title">Select Mode &amp; Corridor</div>
        <div class="card-sub">Car / Bike / Truck</div>
      </div>

      <div class="vert-arrow">
        <svg width="12" height="18" viewBox="0 0 12 18">
          <line x1="6" y1="0" x2="6" y2="13" stroke="#4B5563" stroke-width="1.5" />
          <polygon points="2,12 6,17 10,12" fill="#4B5563" />
        </svg>
      </div>

      <div class="card">
        <span class="badge backend">Backend</span>
        <div class="card-title">Request Route Alternatives</div>
        <div class="card-sub">REST API call to routing engine</div>
      </div>
    </div>

    <!-- RIGHT: Report a Hazard -->
    <div class="col">
      <div class="hdr-btn blue">Report a Hazard</div>

      <div class="vert-arrow">
        <svg width="12" height="18" viewBox="0 0 12 18">
          <line x1="6" y1="0" x2="6" y2="13" stroke="#4B5563" stroke-width="1.5" />
          <polygon points="2,12 6,17 10,12" fill="#4B5563" />
        </svg>
      </div>

      <div class="card">
        <span class="badge frontend">Frontend</span>
        <div class="card-title">Fill Hazard Form</div>
        <div class="card-sub">Category, severity, location</div>
      </div>

      <div class="vert-arrow">
        <svg width="12" height="18" viewBox="0 0 12 18">
          <line x1="6" y1="0" x2="6" y2="13" stroke="#4B5563" stroke-width="1.5" />
          <polygon points="2,12 6,17 10,12" fill="#4B5563" />
        </svg>
      </div>

      <div class="card">
        <span class="badge frontend">Frontend</span>
        <div class="card-title">Capture GPS Location</div>
        <div class="card-sub">Live coordinates auto-filled</div>
      </div>

      <div class="vert-arrow">
        <svg width="12" height="18" viewBox="0 0 12 18">
          <line x1="6" y1="0" x2="6" y2="13" stroke="#4B5563" stroke-width="1.5" />
          <polygon points="2,12 6,17 10,12" fill="#4B5563" />
        </svg>
      </div>

      <div class="card">
        <span class="badge backend">Backend</span>
        <div class="card-title">Submit Report</div>
        <div class="card-sub">Triggers NLP classifier</div>
      </div>
    </div>

  </div>

  <!-- CONVERGING ARROWS TO AI ENGINE -->
  <svg class="connector-svg" width="760" height="26" viewBox="0 0 760 26">
    <line x1="175" y1="2" x2="380" y2="24" stroke="#4B5563" stroke-width="1.5" marker-end="url(#m1)" />
    <line x1="585" y1="2" x2="380" y2="24" stroke="#4B5563" stroke-width="1.5" marker-end="url(#m1)" />
  </svg>

  <!-- 3. AI/ML PROCESSING ENGINE -->
  <div class="ai-box">
    <div class="ai-title">AI/ML Processing Engine</div>
    <div class="ai-sub">GradientBoostingRegressor + SHAP (scikit-learn)</div>
  </div>

  <!-- DIVERGING ARROWS TO RESPONSE CARDS -->
  <svg class="connector-svg" width="760" height="26" viewBox="0 0 760 26">
    <line x1="380" y1="2" x2="175" y2="24" stroke="#4B5563" stroke-width="1.5" marker-end="url(#m1)" />
    <line x1="380" y1="2" x2="585" y2="24" stroke="#4B5563" stroke-width="1.5" marker-end="url(#m1)" />
  </svg>

  <!-- 4. POST-AI COLUMNS -->
  <div class="col-container">

    <!-- LEFT: Route Safety & SHAP -->
    <div class="col">
      <div class="card">
        <span class="badge response">Response</span>
        <div class="card-title">Corridor Safety Scores</div>
        <div class="card-sub">0–10 score, CRI index</div>
      </div>

      <div class="vert-arrow">
        <svg width="12" height="18" viewBox="0 0 12 18">
          <line x1="6" y1="0" x2="6" y2="13" stroke="#4B5563" stroke-width="1.5" />
          <polygon points="2,12 6,17 10,12" fill="#4B5563" />
        </svg>
      </div>

      <div class="card">
        <span class="badge response">Response</span>
        <div class="card-title">SHAP Factor Breakdown</div>
        <div class="card-sub">Ranked risk contributors</div>
      </div>
    </div>

    <!-- RIGHT: Hazard Tag & Cloud Publish -->
    <div class="col">
      <div class="card">
        <span class="badge response">Response</span>
        <div class="card-title">Severity &amp; Category Tag</div>
        <div class="card-sub">AI-suggested, citizen-confirmed</div>
      </div>

      <div class="vert-arrow">
        <svg width="12" height="18" viewBox="0 0 12 18">
          <line x1="6" y1="0" x2="6" y2="13" stroke="#4B5563" stroke-width="1.5" />
          <polygon points="2,12 6,17 10,12" fill="#4B5563" />
        </svg>
      </div>

      <div class="card">
        <span class="badge backend">Backend</span>
        <div class="card-title">Publish to Cloud Network</div>
        <div class="card-sub">Hazard pin added to live map</div>
      </div>
    </div>

  </div>

  <!-- CONVERGING ARROWS TO DATABASE -->
  <svg class="connector-svg" width="760" height="26" viewBox="0 0 760 26">
    <line x1="175" y1="2" x2="380" y2="24" stroke="#4B5563" stroke-width="1.5" marker-end="url(#m1)" />
    <line x1="585" y1="2" x2="380" y2="24" stroke="#4B5563" stroke-width="1.5" marker-end="url(#m1)" />
  </svg>

  <!-- 5. DATABASE -->
  <div class="db-box">
    <span class="badge database">Database</span>
    <div class="db-title">Supabase Cloud Database</div>
    <div class="db-sub">PostgreSQL · routes, hazards, trips</div>
  </div>

  <!-- DIVERGING ARROWS TO BOTTOM CARDS -->
  <svg class="connector-svg" width="760" height="26" viewBox="0 0 760 26">
    <line x1="380" y1="2" x2="175" y2="24" stroke="#4B5563" stroke-width="1.5" marker-end="url(#m1)" />
    <line x1="380" y1="2" x2="585" y2="24" stroke="#4B5563" stroke-width="1.5" marker-end="url(#m1)" />
  </svg>

  <!-- 6. BOTTOM ROW -->
  <div class="col-container">
    <div class="bottom-card">
      <div class="b-title">Live Navigation Mode</div>
      <div class="b-sub">GPS, voice alerts, proximity warnings</div>
    </div>

    <div class="bottom-card">
      <div class="b-title">SOS &amp; Emergency Assist</div>
      <div class="b-sub">Tel 112/1033/108, WhatsApp SOS</div>
    </div>
  </div>

  <!-- 7. FOOTER -->
  <div class="footer">
    <div class="footer-title">SafePass Maps Platform</div>
    <div class="footer-sub">Predictive Routing. Explainable Risk. Real-Time Safety.</div>
  </div>

</div>

</body>
</html>
"""

html_path = "/Users/parthsonkusare1340/Hack2026ps1/mindmap_hd.html"
with open(html_path, "w") as f:
    f.write(html_content)

print("Generated HD HTML template at", html_path)
