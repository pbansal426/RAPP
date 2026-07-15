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
                <option value="2010">2010</option>
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
            <select data-testid="select-trim" id="select-trim" style="display: block; margin-bottom: 10px; padding: 8px; font-size: 16px;" disabled>
                <option value="">Select Trim</option>
            </select>
            <select data-testid="select-powertrain" id="select-powertrain" style="display: block; margin-bottom: 10px; padding: 8px; font-size: 16px;" disabled>
                <option value="Gasoline">Gasoline</option>
                <option value="Diesel">Diesel</option>
                <option value="Hybrid">Hybrid</option>
                <option value="Electric (EV)">Electric (EV)</option>
            </select>
            <select data-testid="select-drive" id="select-drive" style="display: block; margin-bottom: 10px; padding: 8px; font-size: 16px;" disabled>
                <option value="">Select Drive</option>
                <option value="FWD">FWD</option>
                <option value="RWD">RWD</option>
                <option value="AWD">AWD</option>
                <option value="4WD">4WD</option>
            </select>
            <input data-testid="engine-detail" id="engine-detail" type="text" placeholder="Engine details" style="display: block; margin-bottom: 10px; padding: 8px; font-size: 16px;" disabled />
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
        const trimSel = document.getElementById('select-trim');
        const powertrainSel = document.getElementById('select-powertrain');
        const driveSel = document.getElementById('select-drive');
        const engineDetail = document.getElementById('engine-detail');
        const ymmBtn = document.getElementById('submit-ymm-btn');

        const modelsPerMake = {{
            HONDA: ['CIVIC', 'ACCORD'],
            TOYOTA: ['CAMRY', 'COROLLA', 'HIGHLANDER'],
            FORD: ['F-150'],
            LEXUS: ['RX350'],
            CHEVROLET: ['SILVERADO']
        }};

        const trimsPerModel = {{
            COROLLA: ['Base', 'S', 'LE', 'XLE'],
            HIGHLANDER: ['Base', 'LE', 'XLE', 'Limited'],
            ACCORD: ['Base', 'Sport', 'Touring'],
            CIVIC: ['Base', 'EX', 'LX'],
            CAMRY: ['Base', 'LE', 'SE'],
            'F-150': ['Base', 'XLT', 'Lariat'],
            RX350: ['Base', 'F Sport'],
            SILVERADO: ['Base', 'LT']
        }};

        yearSel.addEventListener('change', () => {{
            if (yearSel.value) {{
                makeSel.disabled = false;
            }} else {{
                makeSel.disabled = true;
                makeSel.value = '';
                modelSel.disabled = true;
                modelSel.value = '';
                trimSel.disabled = true;
                trimSel.value = '';
                powertrainSel.disabled = true;
                driveSel.disabled = true;
                driveSel.value = '';
                engineDetail.disabled = true;
                engineDetail.value = '';
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
                trimSel.disabled = true;
                trimSel.value = '';
                powertrainSel.disabled = true;
                driveSel.disabled = true;
                driveSel.value = '';
                engineDetail.disabled = true;
                engineDetail.value = '';
            }}
            updateBtn();
        }});

        modelSel.addEventListener('change', () => {{
            if (modelSel.value) {{
                trimSel.disabled = false;
                trimSel.innerHTML = '<option value="">Select Trim</option>';
                const trims = trimsPerModel[modelSel.value] || ['Base'];
                trims.forEach(tr => {{
                    const opt = document.createElement('option');
                    opt.value = tr;
                    opt.textContent = tr;
                    trimSel.appendChild(opt);
                }});
                trimSel.value = trims[0]; 

                powertrainSel.disabled = false;
                driveSel.disabled = false;
                engineDetail.disabled = false;
                
                checkAutoLock();
            }} else {{
                trimSel.disabled = true;
                trimSel.value = '';
                powertrainSel.disabled = true;
                driveSel.disabled = true;
                driveSel.value = '';
                engineDetail.disabled = true;
                engineDetail.value = '';
            }}
            updateBtn();
        }});

        trimSel.addEventListener('change', () => {{
            checkAutoLock();
            updateBtn();
        }});

        // Mirrors frontend/src/lib/vehicleSpecs.ts: entries whose specs are
        // unambiguous for a year-range/make/model(/trim) get auto-locked.
        const specTable = [
            {{ make: 'TOYOTA', model: 'COROLLA', years: [2009, 2019], powertrain: 'Gasoline', engine: '1.8L I4', drive: 'FWD' }},
            {{ make: 'TOYOTA', model: 'HIGHLANDER', trim: 'XLE', years: [2014, 2016], powertrain: 'Gasoline', engine: '3.5L V6', drive: 'AWD' }}
        ];

        function checkAutoLock() {{
            const y = Number(yearSel.value);
            const match = specTable.find(e =>
                e.make === makeSel.value && e.model === modelSel.value &&
                y >= e.years[0] && y <= e.years[1] &&
                (e.trim === undefined || e.trim === trimSel.value)
            );

            if (match) {{
                powertrainSel.value = match.powertrain;
                powertrainSel.disabled = true;
                engineDetail.value = match.engine;
                engineDetail.disabled = true;
                driveSel.value = match.drive;
                driveSel.disabled = true;
            }} else {{
                powertrainSel.disabled = false;
                engineDetail.disabled = false;
                driveSel.disabled = false;
            }}
        }}

        function updateBtn() {{
            ymmBtn.disabled = !(yearSel.value && makeSel.value && modelSel.value);
        }}

        ymmBtn.addEventListener('click', () => {{
            const yy = yearSel.value.slice(-2);
            const makeCodes = {{ HONDA: 'HONDA', TOYOTA: 'TOYOT', FORD: 'FORDX', LEXUS: 'LEXUS', CHEVROLET: 'CHEVR' }};
            const modelCodes = {{ CIVIC: 'CIVICXX', ACCORD: 'ACCORDX', 'F-150': 'F150XXX', CAMRY: 'CAMRYXX', COROLLA: 'COROLLA', HIGHLANDER: 'HIGHLAN', RX350: 'RX350XX', SILVERADO: 'SILVERA' }};
            const vinVal = "SYN" + yy + makeCodes[makeSel.value] + modelCodes[modelSel.value];
            localStorage.setItem('rapp_vin', vinVal);

            const engineVal = [powertrainSel.value, engineDetail.value.trim()].filter(Boolean).join(' · ');
            localStorage.setItem('rapp_vin_data', JSON.stringify({{
                vin: vinVal,
                year: yearSel.value,
                make: makeSel.value,
                model: modelSel.value,
                trim: trimSel.value,
                drive_type: driveSel.value,
                engine: engineVal,
                powertrain: powertrainSel.value
            }}));
            
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
        .border-red-500 {{ border: 2px solid #ef4444; }}
        .bg-red-950 {{ background-color: #450a0a; }}
        .text-red-500 {{ color: #ef4444; }}
    </style>
</head>
<body class="dark bg-slate-900">
    <div style="padding: 20px;">
        <div id="warning-container"></div>
        <h1>Diagnostic Results</h1>
        <div data-testid="free-diagnosis-summary" style="margin-bottom: 20px;">
            Free Diagnosis Summary: Misfire or other symptom detected.
        </div>

        <!-- 3-Column Price Comparison Table -->
        <table class="price-table" style="width: 100%; border-collapse: collapse; margin-bottom: 20px; border: 1px solid #ccc;">
            <thead>
                <tr style="background: #1e293b; color: #fff;">
                    <th style="padding: 10px; border: 1px solid #ccc; text-align: left;">Repair Method</th>
                    <th style="padding: 10px; border: 1px solid #ccc; text-align: left;">Estimated Cost</th>
                    <th style="padding: 10px; border: 1px solid #ccc; text-align: left;">Value & Details</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ccc;">Dealership / Pro Shop</td>
                    <td style="padding: 10px; border: 1px solid #ccc;">$450 – $900</td>
                    <td style="padding: 10px; border: 1px solid #ccc;">3-5 Days Timeframe. High labor markup.</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ccc;">Independent Auto Shop</td>
                    <td style="padding: 10px; border: 1px solid #ccc;">$200 – $400</td>
                    <td style="padding: 10px; border: 1px solid #ccc;">1-2 Days Timeframe. Variable quality.</td>
                </tr>
                <tr style="font-weight: bold; background: rgba(249,115,22,0.1);">
                    <td style="padding: 10px; border: 1px solid #ccc;">RAPP Guided DIY</td>
                    <td style="padding: 10px; border: 1px solid #ccc;">$39.00</td>
                    <td style="padding: 10px; border: 1px solid #ccc;">2-3 Hours completion. Includes $4.00 guide fee.</td>
                </tr>
            </tbody>
        </table>

        <!-- Save to My Garage & Keep Guide Forever Section -->
        <div class="card" style="border: 1px solid #f97316; padding: 15px; margin-bottom: 20px;">
            <h3>Save to My Garage & Keep Guide Forever</h3>
            <p>Create a free account to archive vehicle profile.</p>
            <div style="display: flex; flex-direction: column; gap: 8px; max-width: 300px;">
                <input class="input" type="text" placeholder="Name (optional)" />
                <input class="input" type="email" placeholder="Email" />
                <input class="input" type="password" placeholder="Password" />
                <button class="btn btn-primary" style="height: 35px;">Save to My Garage</button>
            </div>
        </div>
        
        <div id="locked-repair-steps" data-testid="locked-repair-steps" style="display: {locked_display}; margin-bottom: 20px;">
            <h3>Locked Repair Steps</h3>
            <p>Please unlock to view steps.</p>
        </div>
        
        <!-- Dual-Card UI -->
        <div style="display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap;">
            <div style="border: 2px solid yellow; padding: 15px; border-radius: 8px;">
                <h3>⭐ Annual Pass</h3>
                <p>$19.99/yr</p>
                <button data-testid="pay-annual-btn" id="pay-annual-btn" style="height: {btn_height};">Get Annual Pass</button>
            </div>
            <div style="border: 1px solid #ccc; padding: 15px; border-radius: 8px;">
                <h3>Single Unlock</h3>
                <p>$4.99</p>
                <button data-testid="payment-cta-btn" id="payment-cta-btn" style="display: {cta_display}; height: {btn_height};">
                    Unlock Single Guide
                </button>
            </div>
        </div>
    </div>
    <script>
        const symptoms = localStorage.getItem('rapp_symptoms') || '';
        const isAirbag = symptoms.toLowerCase().includes('airbag');
        const missingWarnings = {missing_warnings};
        if (isAirbag && !missingWarnings) {{
            const banner = document.createElement('div');
            banner.setAttribute('data-testid', 'safety-warning-banner');
            banner.className = 'border-red-500 bg-red-950 text-red-500 p-4 mb-4';
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
        const annualBtn = document.getElementById('pay-annual-btn');
        if (annualBtn) {{
            annualBtn.addEventListener('click', () => {{
                const vin = localStorage.getItem('rapp_vin');
                if (!vin) {{
                    alert("Error: No VIN found in state.");
                    return;
                }}
                localStorage.setItem('rapp_user_subscription_status', 'active');
                window.location.href = '/repair/success?session_id=cs_test_annual&vin=' + vin;
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
            const isSubscriber = localStorage.getItem('rapp_user_subscription_status') === 'active';
            if (isUnlocked || isSubscriber) {
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

