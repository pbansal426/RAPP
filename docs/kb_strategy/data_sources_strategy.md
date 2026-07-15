# Knowledge Base Data Sources Strategy

## Phase 1: Core Technical Data (High Priority)

### 1. OEM Service Manuals
**Priority:** CRITICAL  
**Coverage:** Complete repair procedures, specifications, diagrams  
**Sources:**
- AllData (API available for commercial use)
- Mitchell 1 (ProDemand API)
- Direct manufacturer APIs (Toyota TechInfo, Honda Service Express, etc.)
- Third-party aggregators (eBay Motors manuals, Tradebit)

**Ingestion Strategy:**
- PDF parsing with layout preservation (existing infrastructure)
- Table extraction for torque specs, fluid capacities
- Diagram OCR for component identification
- Metadata: source_authority=official, quality_score=0.95+

### 2. Professional Repair Databases
**Priority:** CRITICAL  
**Coverage:** Verified repair procedures, labor times, common fixes  
**Sources:**
- Identifix (Direct-Hit API)
- Alldata (Alldata Repair API)
- Mitchell 1 (ProDemand)
- ShopKey Pro

**Ingestion Strategy:**
- API integration where available
- Structured data extraction (procedures, labor times, parts)
- Real-world fix verification data
- Metadata: source_type=professional, verification_status=verified

### 3. Parts Catalogs & Cross-Reference
**Priority:** HIGH  
**Coverage:** OEM part numbers, aftermarket equivalents, pricing  
**Sources:**
- RockAuto API (parts catalog)
- PartsTech API (parts ordering)
- OEM parts databases (Toyota Parts, Honda Parts, etc.)
- Aftermarket manufacturer catalogs (Bosch, Denso, ACDelco)

**Ingestion Strategy:**
- API integration for real-time parts data
- Cross-reference mapping (OEM ↔ aftermarket)
- Compatibility matrix by VIN patterns
- Metadata: part_category, availability, average_cost

## Phase 2: Community & Real-World Data (Medium Priority)

### 4. Forum & Community Knowledge
**Priority:** HIGH  
**Coverage:** Real-world experiences, alternative fixes, common issues  
**Sources:**
- Reddit (r/MechanicAdvice, r/Toyota, r/Justrolledintotheshop)
- Brand-specific forums (Toyota Nation, Honda-Tech, Bimmerfest)
- DIY repair forums (Bob Is The Oil Guy, Garage Journal)
- Q&A sites (Stack Exchange Automotive, CarTalk)

**Ingestion Strategy:**
- API scraping (Reddit API)
- Web scraping with rate limiting
- Quality scoring based on upvotes/expert verification
- Metadata: source_type=community, quality_score=0.3-0.8

### 5. Video Content & Transcripts
**Priority:** MEDIUM  
**Coverage:** Visual procedures, step-by-step demonstrations  
**Sources:**
- YouTube repair channels (EricTheCarGuy, Scotty Kilmer, ChrisFix)
- Manufacturer tutorial videos
- Transcript extraction using YouTube API
- Timestamp linking to procedure steps

**Ingestion Strategy:**
- YouTube Data API for transcript extraction
- Video-to-text for non-captioned content
- Timestamp mapping to procedure steps
- Metadata: source_type=video, has_visual=true

### 6. Q&A & Diagnostic Databases
**Priority:** MEDIUM  
**Coverage:** Symptom-diagnosis pairs, resolution tracking  
**Sources:**
- Stack Exchange Automotive (API available)
- CarTalk community
- iFixit (automotive section)
- RepairPal Q&A

**Ingestion Strategy:**
- API integration where available
- Structured symptom → diagnosis → resolution mapping
- Success rate tracking
- Metadata: diagnostic_confidence, frequency

## Phase 3: Specialized Data (Lower Priority)

### 7. Recall & Safety Data
**Priority:** MEDIUM  
**Coverage:** Safety recalls, campaigns, NHTSA data  
**Sources:**
- NHTSA recall API (beyond TSBs)
- Manufacturer recall databases
- Safety campaign tracking

**Ingestion Strategy:**
- NHTSA API integration
- VIN pattern matching for recall applicability
- Safety warning metadata
- Metadata: safety_critical=true, source_authority=official

### 8. Specification Databases
**Priority:** MEDIUM  
**Coverage:** Fluid capacities, torque specs, tire pressures, intervals  
**Sources:**
- OEM specification databases
- Fluid capacity databases (AMS Oil, etc.)
- Tire pressure databases
- Maintenance interval databases

**Ingestion Strategy:**
- Structured data extraction
- Specification type categorization
- Critical tolerance marking
- Metadata: spec_type, critical_tolerance

### 9. Enhanced OBD-II Code Database
**Priority:** LOW  
**Coverage:** Detailed code definitions, common causes, fix patterns  
**Sources:**
- OBD-Codes.com
- Innova database
- ScannerDanner database
- Manufacturer-specific code databases

**Ingestion Strategy:**
- Code hierarchy (P, B, C, U codes)
- Common cause mapping
- Fix pattern aggregation
- Metadata: obd_codes, diagnostic_confidence

## Data Quality Framework

### Quality Scoring System
```
0.9-1.0: Official OEM documentation, verified professional sources
0.7-0.9: Professional repair databases, high-quality community content
0.5-0.7: Verified community content, video transcripts
0.3-0.5: General community content, unverified sources
0.0-0.3: Low-quality sources (use with caution)
```

### Verification Tiers
- **Tier 1 (Verified):** OEM manuals, professional databases
- **Tier 2 (Community-Verified):** High-upvote forum posts, expert-verified content
- **Tier 3 (Unverified):** General community content
- **Tier 4 (Experimental):** AI-generated or low-confidence content

### Freshness Strategy
- **Static data:** OEM manuals, specifications (update quarterly)
- **Dynamic data:** Parts pricing, availability (update daily)
- **Community data:** Forum posts, Q&A (update weekly)
- **Safety data:** Recalls, TSBs (update daily)

## API Integration Priority Matrix

| Data Source | API Available | Integration Complexity | Priority |
|-------------|---------------|----------------------|----------|
| NHTSA TSB | Yes | Low | ✅ Complete |
| NHTSA Recalls | Yes | Low | Phase 1 |
| RockAuto | Yes | Medium | Phase 1 |
| AllData | Yes | High | Phase 1 |
| Identifix | Yes | High | Phase 1 |
| Reddit | Yes | Medium | Phase 2 |
| YouTube | Yes | Medium | Phase 2 |
| Stack Exchange | Yes | Low | Phase 2 |
| Toyota TechInfo | No | High | Phase 3 |
| Mitchell 1 | Yes | High | Phase 1 |

## Estimated Data Volumes

### Current State
- TSBs: ~1,000 documents (single vehicle vertical slice)

### Target State (Phase 1 Complete)
- OEM manuals: ~50,000 documents (top 20 makes, 10 years)
- Professional repair procedures: ~100,000 documents
- Parts catalog: ~500,000 part numbers with cross-references
- Total chunks: ~1-2 million chunks

### Target State (Phase 2 Complete)
- Community content: ~200,000 high-quality posts
- Video transcripts: ~50,000 procedures
- Q&A pairs: ~100,000 symptom-diagnosis pairs
- Total chunks: ~3-5 million chunks

### Target State (Phase 3 Complete)
- Complete coverage: All major makes, 20+ years
- Total chunks: ~10-20 million chunks
