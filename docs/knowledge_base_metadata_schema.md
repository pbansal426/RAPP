# Enhanced Knowledge Base Metadata Schema

## Current Schema
```json
{
  "year": 2010,
  "make": "TOYOTA", 
  "model": "COROLLA",
  "type": "tsb"
}
```

## Proposed Enhanced Schema

### Vehicle Metadata (Existing + Enhanced)
```json
{
  "year": 2010,
  "make": "TOYOTA",
  "model": "COROLLA", 
  "trim": "LE",
  "engine": "1.8L 2ZR-FE",
  "engine_code": "2ZR-FE",
  "transmission": "Automatic",
  "drive_type": "FWD",
  "body_style": "Sedan",
  "vin_pattern": "1NXBU4EE*"
}
```

### Component Metadata (New)
```json
{
  "component_category": "Brake System",
  "component_name": "Brake Caliper",
  "component_location": "Front Left",
  "affected_systems": ["brakes", "safety"],
  "related_components": ["brake rotor", "brake pads", "brake line"]
}
```

### Procedure Metadata (New)
```json
{
  "procedure_type": "repair",
  "difficulty_level": "intermediate",
  "estimated_time_minutes": 120,
  "required_tools": ["socket set", "torque wrench", "brake caliper tool"],
  "required_parts": ["brake pads", "brake caliper bolts"],
  "safety_warnings": ["brake dust hazard", "torque specifications critical"],
  "prerequisite_procedures": ["wheel removal"],
  "skill_level": "DIY-capable"
}
```

### Symptom & Diagnostic Metadata (New)
```json
{
  "symptom_category": "noise",
  "symptom_description": "grinding noise when braking",
  "obd_codes": ["C1234", "P0300"],
  "diagnostic_confidence": 0.85,
  "common_causes": ["worn brake pads", "stuck caliper"],
  "frequency": "common"
}
```

### Source & Quality Metadata (New)
```json
{
  "source_type": "oem_manual",
  "source_authority": "official",
  "source_date": "2024-01-15",
  "quality_score": 0.95,
  "verification_status": "verified",
  "last_updated": "2024-06-01",
  "citation_url": "https://...",
  "document_id": "TSB-2024-001"
}
```

### Parts Metadata (New)
```json
{
  "part_number": "04465-02070",
  "oem_part_number": "04465-02070",
  "aftermarket_equivalents": ["Raybestos PGD770", "Centric 120.44070"],
  "part_category": "Brake Pads",
  "compatibility_notes": "Fits 2009-2013 Corolla",
  "average_cost_usd": 45.00,
  "availability": "common"
}
```

### Specification Metadata (New)
```json
{
  "spec_type": "torque",
  "spec_value": "76 ft-lbs",
  "spec_unit": "ft-lbs",
  "spec_range": "74-78 ft-lbs",
  "critical_tolerance": true,
  "measurement_point": "caliper bracket bolts"
}
```

## Metadata Indexing Strategy

### Primary Filters (Fast Pre-filter)
- year, make, model, engine, component_category
- These should be indexed for exact match filtering

### Secondary Filters (Semantic Search)
- symptom_description, procedure_type, component_name
- These should be embedded for semantic search

### Tertiary Filters (Post-retrieval Ranking)
- difficulty_level, quality_score, diagnostic_confidence
- These should be used for re-ranking retrieved results

## Implementation Priority

### Phase 1 (Immediate)
1. Add component metadata to existing TSB chunks
2. Add source quality metadata
3. Add procedure type metadata

### Phase 2 (Short-term)
4. Implement parts metadata structure
5. Add symptom/diagnostic metadata
6. Add specification metadata

### Phase 3 (Long-term)
7. Add tool requirements metadata
8. Add safety warnings metadata
9. Add prerequisite procedure linking
