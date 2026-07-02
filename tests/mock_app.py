import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

def get_flags():
    return {
        "FAULTY_VIN_DECODING": os.getenv("FAULTY_VIN_DECODING", "false").lower() == "true",
        "MISSING_WARNINGS": os.getenv("MISSING_WARNINGS", "false").lower() == "true",
        "BYPASS_PAYWALL_GATE": os.getenv("BYPASS_PAYWALL_GATE", "false").lower() == "true",
        "SMALL_TOUCH_TARGETS": os.getenv("SMALL_TOUCH_TARGETS", "false").lower() == "true",
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    flags = get_flags()
    btn_height = "30px" if flags["SMALL_TOUCH_TARGETS"] else "48px"
    faulty_vin = "true" if flags["FAULTY_VIN_DECODING"] else "false"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Mock RAPP</title>
    <style>
        .dark {{
            background-color: #0f172a; /* bg-slate-900 */
            color: #f8fafc;
        }}
    </style>
</head>
<body class="dark bg-slate-900">
    <div style="padding: 20px;">
        <h1>Frictionless VIN Ingestion</h1>
        <div>
            <input data-testid="vin-input" id="vin-input" type="text" placeholder="Enter VIN" style="display: block; margin-bottom: 10px; font-size: 16px; padding: 8px;" />
            <button data-testid="scan-barcode-btn" id="scan-barcode-btn" style="display: block; margin-bottom: 10px; height: {btn_height};">Scan Barcode</button>
            <button data-testid="submit-vin-btn" id="submit-vin-btn" style="display: block; height: {btn_height};">Submit VIN</button>
        </div>
        <hr style="margin: 20px 0; border: 1px solid #334155;" />
        <h2>Or Select Vehicle Manually</h2>
        <div>
            <select data-testid="select-year" id="select-year" style="display: block; margin-bottom: 10px; padding: 8px; font-size: 16px;">
                <option value="">Select Year</option>
                <option value="2015">2015</option>
                <option value="2023">2023</option>
                <option value="2026">2026</option>
            </select>
            <select data-testid="select-make" id="select-make" style="display: block; margin-bottom: 10px; padding: 8px; font-size: 16px;" disabled>
                <option value="">Select Make</option>
                <option value="HONDA">HONDA</option>
                <option value="TOYOTA">TOYOTA</option>
                <option value="FORD">FORD</option>
                <option value="LEXUS">LEXUS</option>
                <option value="CHEVROLET">CHEVROLET</option>
            </select>
            <select data-testid="select-model" id="select-model" style="display: block; margin-bottom: 10px; padding: 8px; font-size: 16px;" disabled>
                <option value="">Select Model</option>
            </select>
            <button data-testid="submit-ymm-btn" id="submit-ymm-btn" style="display: block; height: {btn_height};" disabled>Confirm Vehicle</button>
        </div>
    </div>
    <script>
        document.getElementById('submit-vin-btn').addEventListener('click', () => {{
            const vinVal = document.getElementById('vin-input').value;
            localStorage.setItem('rapp_vin', vinVal);
            if ({faulty_vin}) {{
                console.log("Faulty VIN decoding enabled, not transitioning.");
            }} else {{
                window.location.href = '/diagnose';
            }}
        }});

        const yearSel = document.getElementById('select-year');
        const makeSel = document.getElementById('select-make');
        const modelSel = document.getElementById('select-model');
        const ymmBtn = document.getElementById('submit-ymm-btn');

        const modelsPerMake = {{
            HONDA: ['CIVIC', 'ACCORD'],
            TOYOTA: ['CAMRY', 'COROLLA'],
            FORD: ['F-150'],
            LEXUS: ['RX350'],
            CHEVROLET: ['SILVERADO']
        }};

        yearSel.addEventListener('change', () => {{
            if (yearSel.value) {{
                makeSel.disabled = false;
            }} else {{
                makeSel.disabled = true;
                makeSel.value = '';
                modelSel.disabled = true;
                modelSel.value = '';
            }}
            updateBtn();
        }});

        makeSel.addEventListener('change', () => {{
            if (makeSel.value) {{
                modelSel.disabled = false;
                modelSel.innerHTML = '<option value="">Select Model</option>';
                modelsPerMake[makeSel.value].forEach(mod => {{
                    const opt = document.createElement('option');
                    opt.value = mod;
                    opt.textContent = mod;
                    modelSel.appendChild(opt);
                }});
            }} else {{
                modelSel.disabled = true;
                modelSel.value = '';
            }}
            updateBtn();
        }});

        modelSel.addEventListener('change', () => {{
            updateBtn();
        }});

        function updateBtn() {{
            ymmBtn.disabled = !(yearSel.value && makeSel.value && modelSel.value);
        }}

        ymmBtn.addEventListener('click', () => {{
            const yy = yearSel.value.slice(-2);
            const makeCodes = {{ HONDA: 'HONDA', TOYOTA: 'TOYOT', FORD: 'FORDX', LEXUS: 'LEXUS', CHEVROLET: 'CHEVR' }};
            const modelCodes = {{ CIVIC: 'CIVICXX', ACCORD: 'ACCORDX', 'F-150': 'F150XXX', CAMRY: 'CAMRYXX', COROLLA: 'COROLLA', RX350: 'RX350XX', SILVERADO: 'SILVERA' }};
            const vinVal = "SYN" + yy + makeCodes[makeSel.value] + modelCodes[modelSel.value];
            localStorage.setItem('rapp_vin', vinVal);
            if ({faulty_vin}) {{
                console.log("Faulty VIN decoding enabled, not transitioning.");
            }} else {{
                window.location.href = '/diagnose';
            }}
        }});
    </script>
</body>
</html>
"""
    return html

@app.get("/diagnose", response_class=HTMLResponse)
async def diagnose():
    flags = get_flags()
    btn_height = "30px" if flags["SMALL_TOUCH_TARGETS"] else "48px"
    label_height = "30px" if flags["SMALL_TOUCH_TARGETS"] else "48px"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Mock RAPP - Diagnose</title>
    <style>
        .dark {{
            background-color: #0f172a;
            color: #f8fafc;
        }}
    </style>
</head>
<body class="dark bg-slate-900">
    <div style="padding: 20px;">
        <button data-testid="back-to-home-btn" id="back-to-home-btn" style="display: block; margin-bottom: 10px; height: {btn_height};">Back to Home</button>
        <h1>Diagnostic Input</h1>
        <textarea data-testid="symptoms-input" id="symptoms-input" placeholder="Describe symptoms" style="width: 100%; height: 100px; margin-bottom: 10px; padding: 8px;"></textarea>
        
        <div style="margin-bottom: 20px;">
            <label for="tool-hand-tools" style="display: block; height: {label_height}; font-size: 18px; margin-bottom: 5px;">
                <input type="checkbox" id="tool-hand-tools" data-testid="tool-hand-tools" /> Basic Hand Tools
            </label>
            <label for="tool-jack-stands" style="display: block; height: {label_height}; font-size: 18px; margin-bottom: 5px;">
                <input type="checkbox" id="tool-jack-stands" data-testid="tool-jack-stands" /> Jack Stands
            </label>
            <label for="tool-multimeter" style="display: block; height: {label_height}; font-size: 18px; margin-bottom: 5px;">
                <input type="checkbox" id="tool-multimeter" data-testid="tool-multimeter" /> Multimeter
            </label>
        </div>
        
        <button data-testid="submit-diagnose-btn" id="submit-diagnose-btn" style="height: {btn_height};">Submit</button>
    </div>
    <script>
        document.getElementById('back-to-home-btn').addEventListener('click', () => {{
            window.location.href = '/';
        }});
        document.getElementById('submit-diagnose-btn').addEventListener('click', () => {{
            const symptomsVal = document.getElementById('symptoms-input').value;
            localStorage.setItem('rapp_symptoms', symptomsVal);
            window.location.href = '/results';
        }});
    </script>
</body>
</html>
"""
    return html

@app.get("/results", response_class=HTMLResponse)
async def results():
    flags = get_flags()
    btn_height = "30px" if flags["SMALL_TOUCH_TARGETS"] else "48px"
    
    bypass_paywall = flags["BYPASS_PAYWALL_GATE"]
    locked_display = "block" if bypass_paywall else "none"
    cta_display = "none" if bypass_paywall else "block"
    missing_warnings = "true" if flags["MISSING_WARNINGS"] else "false"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Mock RAPP - Results</title>
    <style>
        .dark {{
            background-color: #0f172a;
            color: #f8fafc;
        }}
        .border-orange-500 {{ border: 2px solid #f97316; }}
        .bg-orange-950 {{ background-color: #431407; }}
        .text-orange-500 {{ color: #f97316; }}
    </style>
</head>
<body class="dark bg-slate-900">
    <div style="padding: 20px;">
        <div id="warning-container"></div>
        <h1>Diagnostic Results</h1>
        <div data-testid="free-diagnosis-summary" style="margin-bottom: 20px;">
            Free Diagnosis Summary: Misfire or other symptom detected.
        </div>
        
        <div id="locked-repair-steps" data-testid="locked-repair-steps" style="display: {locked_display}; margin-bottom: 20px;">
            <h3>Locked Repair Steps</h3>
            <p>Please unlock to view steps.</p>
        </div>
        
        <button data-testid="payment-cta-btn" id="payment-cta-btn" style="display: {cta_display}; height: {btn_height};">
            Unlock Repair Steps
        </button>
    </div>
    <script>
        const symptoms = localStorage.getItem('rapp_symptoms') || '';
        const isAirbag = symptoms.toLowerCase().includes('airbag');
        const missingWarnings = {missing_warnings};
        if (isAirbag && !missingWarnings) {{
            const banner = document.createElement('div');
            banner.setAttribute('data-testid', 'safety-warning-banner');
            banner.className = 'border-orange-500 bg-orange-950 text-orange-500 p-4 mb-4';
            banner.innerText = 'DANGER: SRS / Airbag systems are explosive and safety-critical. Professional service is highly recommended.';
            document.getElementById('warning-container').appendChild(banner);
        }}
        
        const payBtn = document.getElementById('payment-cta-btn');
        if (payBtn) {{
            payBtn.addEventListener('click', () => {{
                const vin = localStorage.getItem('rapp_vin');
                if (!vin) {{
                    alert("Error: No VIN found in state.");
                    return;
                }}
                window.location.href = '/repair/success?session_id=cs_test_123&vin=' + vin;
            }});
        }}
    </script>
</body>
</html>
"""
    return html

@app.get("/repair/success", response_class=HTMLResponse)
async def repair_success():
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Mock RAPP - Success</title>
</head>
<body>
    <script>
        const urlParams = new URLSearchParams(window.location.search);
        const vin = urlParams.get('vin');
        const sessionId = urlParams.get('session_id');
        if (vin && sessionId) {
            localStorage.setItem('rapp_unlocked_' + vin, sessionId);
        }
        window.location.href = '/repair';
    </script>
</body>
</html>
"""
    return html

@app.get("/repair", response_class=HTMLResponse)
async def repair():
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Mock RAPP - Repair Steps</title>
    <style>
        .dark {
            background-color: #0f172a;
            color: #f8fafc;
        }
    </style>
</head>
<body class="dark bg-slate-900">
    <div style="padding: 20px;">
        <h1>Repair Steps</h1>
        
        <div id="detailed-repair-steps" data-testid="detailed-repair-steps" style="display: none; margin-bottom: 20px;">
            <h3>Detailed Repair Steps</h3>
            <p>1. Disconnect negative battery terminal.</p>
            <p>2. Replace ignition coil.</p>
        </div>
        
        <div id="rag-citation" data-testid="rag-citation" style="display: none;">
            Honda Civic ESM 2016-2021 Section 12-4
        </div>
    </div>
    <script>
        const vin = localStorage.getItem('rapp_vin');
        if (!vin) {
            console.error("No VIN in state");
        } else {
            const isUnlocked = localStorage.getItem('rapp_unlocked_' + vin);
            if (isUnlocked) {
                document.getElementById('detailed-repair-steps').style.display = 'block';
                document.getElementById('rag-citation').style.display = 'block';
            }
        }
    </script>
</body>
</html>
"""
    return html

if __name__ == "__main__":
    import os
    port = int(os.getenv("MOCK_PORT", "3099"))
    uvicorn.run(app, host="127.0.0.1", port=port)

