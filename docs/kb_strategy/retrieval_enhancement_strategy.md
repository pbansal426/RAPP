# Retrieval Enhancement Strategy

## Current Retrieval Pipeline

### Existing Flow
```
User Query → Metadata Filter → Vector Search (ChromaDB) → Top-k Results
```

### Limitations
- Single retrieval method (pure semantic)
- No query optimization
- No result re-ranking
- Limited metadata utilization
- No diversity promotion
- No safety-critical prioritization

## Enhanced Retrieval Architecture

### Complete Pipeline
```
User Query
    ↓
Query Understanding
    ├→ Intent Classification (diagnosis/repair/parts/specs)
    ├→ Entity Extraction (components, symptoms, OBD codes)
    ├→ Query Expansion (synonyms, related terms)
    └→ Query Rewriting (technical terminology normalization)
    ↓
Parallel Retrieval
    ├→ Semantic Search (vector embeddings)
    ├→ Keyword Search (BM25/TF-IDF)
    ├→ Metadata Filter (exact match)
    └→ Structured Query (specifications lookup)
    ↓
Result Fusion
    ├→ Weighted combination (semantic: 0.6, keyword: 0.3, structured: 0.1)
    ├→ Deduplication
    ├→ Diversity promotion
    └→ Initial ranking (top 50)
    ↓
Re-ranking
    ├→ Cross-encoder scoring
    ├→ Metadata boosting (quality, recency, authority)
    ├→ Safety-critical prioritization
    ├→ Difficulty matching
    └→ Final ranking (top 10)
    ↓
Result Enrichment
    ├→ Related procedures
    ├→ Required parts
    ├→ Tool recommendations
    └→ Safety warnings
    ↓
Result Return
```

## Query Understanding Layer

### Intent Classification
```python
class QueryIntent(Enum):
    DIAGNOSIS = "diagnosis"          # "Why is my car making this noise?"
    REPAIR = "repair"                # "How to replace brake pads"
    PARTS = "parts"                  # "What part number for alternator?"
    SPECS = "specs"                  # "Torque specs for cylinder head"
    SYMPTOM = "symptom"              # "Grinding noise when braking"
    CODE = "code"                    # "P0300 code meaning"
```

### Entity Extraction
```python
class QueryEntities:
    components: List[str]           # ["brake caliper", "brake pads"]
    symptoms: List[str]             # ["grinding noise", "vibration"]
    obd_codes: List[str]            # ["P0300", "C1234"]
    vehicle_spec: Dict[str, Any]    # {"engine": "2ZR-FE", "year": 2010}
    actions: List[str]              # ["replace", "adjust", "diagnose"]
    measurements: List[str]          # ["120 ft-lbs", "5W-30"]
```

### Query Expansion Strategies

#### 1. Synonym Expansion
```python
automotive_synonyms = {
    "alternator": ["charging system", "generator", "battery charging"],
    "brake pads": ["brake shoes", "friction material"],
    "spark plug": ["ignition plug", "firing plug"],
    "oil filter": ["lubrication filter", "engine oil filter"]
}
```

#### 2. OBD Code Expansion
```python
obd_code_expansions = {
    "P0300": ["random misfire", "cylinder misfire", "engine misfire", "misfire detected"],
    "P0420": ["catalyst efficiency", "catalytic converter", "o2 sensor", "emissions"],
    "C1234": ["abs code", "brake system", "wheel speed sensor"]
}
```

#### 3. Component Hierarchy Expansion
```python
component_hierarchy = {
    "brake system": ["brake pads", "brake rotors", "brake calipers", "brake lines"],
    "engine": ["pistons", "crankshaft", "valves", "timing belt"],
    "suspension": ["shocks", "struts", "control arms", "ball joints"]
}
```

#### 4. Symptom-Procedure Mapping
```python
symptom_to_procedure = {
    "grinding noise": ["brake pad replacement", "rotor resurfacing", "wheel bearing"],
    "overheating": ["coolant system check", "thermostat replacement", "radiator flush"],
    "rough idle": ["spark plug replacement", "fuel injector cleaning", "vacuum leak check"]
}
```

## Parallel Retrieval Strategies

### 1. Semantic Search (Vector Embeddings)
**Implementation:** OpenAI text-embedding-3-large
**Weight:** 0.6
**Strengths:** Semantic understanding, synonym handling
**Weaknesses:** Misses exact matches, technical terms

### 2. Keyword Search (BM25)
**Implementation:** Elasticsearch or Whoosh
**Weight:** 0.3
**Strengths:** Exact term matching, technical precision
**Weaknesses:** No semantic understanding

### 3. Structured Query (Metadata)
**Implementation:** ChromaDB metadata filters
**Weight:** 0.1
**Strengths:** Exact vehicle matching, component filtering
**Weaknesses:** Limited to indexed fields

### 4. Specification Lookup
**Implementation:** Dedicated specs database
**Weight:** 0.1
**Strengths:** Precise values (torque, capacity)
**Weaknesses:** Limited to structured data

## Result Fusion Strategy

### Weighted Fusion Algorithm
```python
def fuse_results(
    semantic_results: List[Result],
    keyword_results: List[Result],
    metadata_results: List[Result],
    spec_results: List[Result]
) -> List[Result]:
    # Combine with weights
    combined = {}
    
    for result in semantic_results:
        combined[result.id] = {
            'result': result,
            'score': result.score * 0.6,
            'sources': ['semantic']
        }
    
    for result in keyword_results:
        if result.id in combined:
            combined[result.id]['score'] += result.score * 0.3
            combined[result.id]['sources'].append('keyword')
        else:
            combined[result.id] = {
                'result': result,
                'score': result.score * 0.3,
                'sources': ['keyword']
            }
    
    # Similar for metadata and spec results...
    
    # Sort by combined score
    sorted_results = sorted(
        combined.values(),
        key=lambda x: x['score'],
        reverse=True
    )
    
    return [item['result'] for item in sorted_results[:50]]
```

### Deduplication Strategy
- Document ID deduplication
- Content similarity deduplication (cosine similarity > 0.95)
- Source deduplication (same TSB from different sources)

### Diversity Promotion
```python
def promote_diversity(results: List[Result], k: int) -> List[Result]:
    diverse = []
    seen_sources = set()
    seen_components = set()
    
    for result in results:
        source = result.metadata.get('source_type')
        component = result.metadata.get('component_name')
        
        # Prioritize unseen sources and components
        if source not in seen_sources or component not in seen_components:
            diverse.append(result)
            seen_sources.add(source)
            seen_components.add(component)
        
        if len(diverse) >= k:
            break
    
    # Fill remaining slots
    for result in results:
        if result not in diverse:
            diverse.append(result)
            if len(diverse) >= k:
                break
    
    return diverse
```

## Re-ranking Strategy

### Cross-Encoder Re-ranking
```python
def rerank_results(
    query: str,
    candidates: List[Result],
    reranker: CrossEncoder
) -> List[Result]:
    # Score each candidate
    pairs = [(query, result.text) for result in candidates]
    scores = reranker.predict(pairs)
    
    # Add scores to results
    for result, score in zip(candidates, scores):
        result.rerank_score = score
    
    # Sort by rerank score
    return sorted(candidates, key=lambda x: x.rerank_score, reverse=True)
```

### Metadata Boosting
```python
def apply_metadata_boosts(result: Result) -> float:
    base_score = result.rerank_score
    
    # Quality score boost
    quality = result.metadata.get('quality_score', 0.5)
    quality_boost = 1.0 + (quality * 0.5)
    
    # Recency boost
    doc_date = result.metadata.get('source_date')
    if doc_date:
        days_old = (datetime.now() - doc_date).days
        recency_boost = max(0.5, 1.0 - (days_old / 3650))
    else:
        recency_boost = 1.0
    
    # Authority boost
    authority = result.metadata.get('source_authority', 'community')
    authority_boosts = {
        'official': 1.3,
        'professional': 1.2,
        'community_verified': 1.1,
        'community': 1.0
    }
    authority_boost = authority_boosts.get(authority, 1.0)
    
    # Apply boosts
    final_score = base_score * quality_boost * recency_boost * authority_boost
    
    return final_score
```

### Safety-Critical Prioritization
```python
def prioritize_safety_critical(results: List[Result]) -> List[Result]:
    safety_critical = [
        r for r in results 
        if r.metadata.get('safety_critical', False)
    ]
    non_critical = [
        r for r in results 
        if not r.metadata.get('safety_critical', False)
    ]
    
    # Safety-critical results get 2x boost
    for result in safety_critical:
        result.final_score *= 2.0
    
    # Re-sort
    combined = safety_critical + non_critical
    return sorted(combined, key=lambda x: x.final_score, reverse=True)
```

### Difficulty Matching
```python
def match_user_difficulty(
    results: List[Result],
    user_skill_level: str
) -> List[Result]:
    skill_levels = {
        'beginner': ['easy', 'beginner'],
        'intermediate': ['easy', 'beginner', 'intermediate'],
        'advanced': ['easy', 'beginner', 'intermediate', 'advanced', 'professional']
    }
    
    allowed_difficulties = skill_levels.get(user_skill_level, ['intermediate'])
    
    # Filter and boost matching results
    filtered = []
    for result in results:
        difficulty = result.metadata.get('difficulty_level', 'intermediate')
        if difficulty in allowed_difficulties:
            result.final_score *= 1.2
            filtered.append(result)
        else:
            filtered.append(result)
    
    return sorted(filtered, key=lambda x: x.final_score, reverse=True)
```

## Result Enrichment

### Related Procedures
```python
def get_related_procedures(
    primary_result: Result,
    all_results: List[Result]
) -> List[Result]:
    # Find procedures with same component
    component = primary_result.metadata.get('component_name')
    related = [
        r for r in all_results
        if r.metadata.get('component_name') == component
        and r.id != primary_result.id
    ]
    
    return related[:3]
```

### Required Parts
```python
def get_required_parts(result: Result) -> List[Part]:
    parts_metadata = result.metadata.get('required_parts', [])
    
    # Enrich with part numbers and pricing
    enriched_parts = []
    for part_name in parts_metadata:
        part_info = parts_catalog.lookup(
            component=result.metadata.get('component_name'),
            part_name=part_name,
            vehicle=result.metadata.get('vehicle_key')
        )
        enriched_parts.append(part_info)
    
    return enriched_parts
```

### Tool Recommendations
```python
def get_tool_recommendations(result: Result) -> List[Tool]:
    required_tools = result.metadata.get('required_tools', [])
    
    # Enrich with tool details and alternatives
    tool_info = []
    for tool in required_tools:
        details = tool_catalog.lookup(tool)
        tool_info.append(details)
    
    return tool_info
```

### Safety Warnings
```python
def get_safety_warnings(result: Result) -> List[str]:
    warnings = []
    
    # Extract from metadata
    warnings.extend(result.metadata.get('safety_warnings', []))
    
    # Add component-specific warnings
    component = result.metadata.get('component_name')
    if component in safety_critical_components:
        warnings.append(f"CRITICAL: {component} is safety-critical. Follow all procedures exactly.")
    
    # Add procedure-specific warnings
    procedure_type = result.metadata.get('procedure_type')
    if procedure_type in high_risk_procedures:
        warnings.append("WARNING: This procedure involves high-risk components.")
    
    return warnings
```

## Implementation Priority

### Phase 1: Query Understanding (Week 1)
1. Implement intent classification
2. Add entity extraction
3. Create synonym dictionary
4. Add OBD code expansion

### Phase 2: Parallel Retrieval (Week 2)
1. Integrate BM25 keyword search
2. Add structured query capability
3. Implement result fusion
4. Add deduplication

### Phase 3: Re-ranking (Week 3)
1. Integrate Cohere Rerank API
2. Implement metadata boosting
3. Add safety-critical prioritization
4. Implement difficulty matching

### Phase 4: Result Enrichment (Week 4)
1. Add related procedures
2. Implement parts lookup
3. Add tool recommendations
4. Enhance safety warnings

## Performance Optimization

### Caching Strategy
- Query expansion results cache (24h TTL)
- Frequently asked questions cache (7d TTL)
- Vehicle-specific procedure cache (30d TTL)

### Index Optimization
- Separate indexes for different content types
- Composite indexes for common query patterns
- Real-time index updates for new content

### Load Balancing
- Distribute retrieval across multiple vector stores
- Implement query queuing for high load
- Add fallback to simpler retrieval methods

## Monitoring & Evaluation

### Retrieval Quality Metrics
- **Precision@10:** 0.85 target
- **Recall@20:** 0.90 target
- **MRR:** 0.80 target
- **User satisfaction:** 4.5/5 target

### A/B Testing Framework
- Control: Current pure semantic search
- Variant A: Hybrid search without re-ranking
- Variant B: Hybrid search with re-ranking
- Variant C: Full enhanced pipeline

### Continuous Improvement
- Weekly retrieval quality audits
- Monthly model performance reviews
- Quarterly strategy optimization
- User feedback integration
