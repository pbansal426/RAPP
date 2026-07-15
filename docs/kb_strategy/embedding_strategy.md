# Embedding Model & Strategy

## Current State Analysis

### Current Implementation
- **Vector Store:** ChromaDB with default embedding model
- **Chunking:** 1000 tokens with 200 token overlap
- **Metadata:** Basic vehicle filtering (make, model, year, engine, drive_type)
- **Retrieval:** Pure semantic search with metadata pre-filtering

### Limitations
- No control over embedding model quality
- No domain-specific fine-tuning
- No hybrid search (keyword + semantic)
- No re-ranking strategy
- No query expansion or optimization

## Recommended Embedding Model Upgrade

### Option 1: Gemini Text Embeddings (Recommended for Production)
**Pros:**
- State-of-the-art performance (768 dimensions for text-embedding-004)
- Multilingual support
- Strong technical understanding
- Easy integration (already using Gemini for LLM)
- Cost-effective pricing

**Cons:**
- API dependency
- Rate limits

**Best for:** Production with budget for API costs

### Option 2: Cohere embed-v3 (Alternative)
**Pros:**
- Excellent for technical content
- 1024 dimensions (smaller, faster)
- Good multilingual support
- Rerank API available

**Cons:**
- Cost: $0.10/1M tokens
- API dependency

**Best for:** Technical automotive content optimization

### Option 3: Open Source - BGE-M3 (Cost-Effective)
**Pros:**
- Free and open source
- Strong performance (8192 dimensions)
- Multilingual support
- Self-hosted (no API dependency)

**Cons:**
- Infrastructure overhead
- Requires GPU for optimal performance
- Maintenance burden

**Best for:** Cost-sensitive scaling, privacy requirements

### Option 4: Fine-tuned Domain Model (Long-term)
**Pros:**
- Optimized for automotive repair terminology
- Better understanding of technical procedures
- Improved OBD code interpretation

**Cons:**
- Requires fine-tuning dataset
- Ongoing maintenance
- Infrastructure complexity

**Best for:** Long-term optimization with large dataset

## Recommended Implementation Strategy

### Phase 1: Quick Win (Week 1)
**Action:** Switch to Gemini text-embedding-004
- Replace default ChromaDB embedding with Gemini embeddings
- Update vector store initialization
- Benchmark against current performance
- Expected improvement: 15-25% retrieval accuracy

### Phase 2: Hybrid Search (Week 2-3)
**Action:** Implement keyword + semantic hybrid search
- Add BM25/keyword search capability
- Combine semantic and keyword results (weighted fusion)
- Implement query expansion (synonyms, related terms)
- Expected improvement: 20-30% retrieval accuracy

### Phase 3: Re-ranking (Week 3-4)
**Action:** Add cross-encoder re-ranking
- Implement re-ranking model (Cohere Rerank or open source)
- Re-rank top 20-50 results from hybrid search
- Add relevance scoring
- Expected improvement: 10-15% retrieval accuracy

### Phase 4: Domain Optimization (Month 2-3)
**Action:** Fine-tune embedding model on automotive data
- Collect high-quality automotive repair text
- Fine-tune BGE-M3 or similar model
- A/B test against general model
- Expected improvement: 5-10% retrieval accuracy

## Hybrid Search Architecture

### Search Pipeline
```
User Query
    ↓
Query Preprocessing
    ├→ Query expansion (synonyms, related terms)
    ├→ OBD code normalization
    └→ Symptom categorization
    ↓
Parallel Search
    ├→ Semantic Search (vector embeddings)
    ├→ Keyword Search (BM25/TF-IDF)
    └→ Metadata Filter (exact match)
    ↓
Result Fusion
    ├→ Weighted combination (semantic: 0.7, keyword: 0.3)
    ├→ Deduplication
    └→ Initial ranking (top 50)
    ↓
Re-ranking
    ├→ Cross-encoder scoring
    ├→ Metadata boosting (quality, recency)
    └→ Final ranking (top 10)
    ↓
Result Return
```

### Query Expansion Strategy

#### OBD Code Expansion
```
Input: "P0300"
Expansion: ["P0300", "misfire", "cylinder misfire", "engine misfire", "random misfire"]
```

#### Symptom Expansion
```
Input: "brake grinding noise"
Expansion: ["brake grinding", "brake noise", "grinding noise", "brake wear", "brake pads"]
```

#### Component Expansion
```
Input: "alternator"
Expansion: ["alternator", "charging system", "battery charging", "generator"]
```

### Metadata Boosting Strategy

#### Quality Score Boosting
```python
boost_factor = 1.0 + (quality_score * 0.5)
# Example: quality_score=0.9 → boost_factor=1.45
```

#### Recency Boosting
```python
days_old = (current_date - document_date).days
recency_boost = max(0.5, 1.0 - (days_old / 3650))  # 10-year decay
```

#### Source Authority Boosting
```python
authority_boosts = {
    "official": 1.3,
    "professional": 1.2,
    "community_verified": 1.1,
    "community": 1.0
}
```

## Re-ranking Strategy

### Cross-Encoder Models

#### Option 1: Cohere Rerank API (Recommended)
- State-of-the-art re-ranking
- Easy integration
- Cost: $1/1M search calls
- Supports custom top-k

#### Option 2: BGE Re-ranker (Open Source)
- Free and open source
- Good performance
- Self-hosted
- Requires GPU

#### Option 3: MonoT5 (Open Source)
- Strong performance
- Transformer-based
- Self-hosted
- Higher computational cost

### Re-ranking Features
- Query-document relevance scoring
- Metadata-aware re-ranking
- Diversity promotion (avoid similar results)
- Safety-critical content prioritization

## Implementation Recommendations

### Immediate Actions (This Week)
1. **Switch to Gemini text-embedding-004**
   - Update `backend/rag/vector_store.py` to use Gemini embeddings
   - Benchmark retrieval quality on existing TSB data
   - Cost estimate: ~$20-50/month for 1M chunks

2. **Add Query Expansion**
   - Implement synonym dictionary for automotive terms
   - Add OBD code expansion logic
   - Integrate into retriever pipeline

### Short-term Actions (Next Sprint)
3. **Implement Hybrid Search**
   - Add BM25/keyword search capability
   - Implement result fusion logic
   - A/B test against pure semantic search

4. **Add Re-ranking**
   - Integrate Cohere Rerank API
   - Implement re-ranking pipeline
   - Tune fusion weights

### Long-term Actions (Next Quarter)
5. **Fine-tune Domain Model**
   - Collect automotive repair dataset
   - Fine-tune BGE-M3 model
   - Deploy and benchmark

6. **Optimize Chunking Strategy**
   - Experiment with different chunk sizes
   - Implement semantic chunking
   - Add procedure-aware chunking

## Performance Metrics

### Retrieval Quality Metrics
- **Precision@k:** Exact match in top k results
- **Recall@k:** Coverage of relevant documents
- **MRR:** Mean Reciprocal Rank
- **NDCG:** Normalized Discounted Cumulative Gain

### Business Metrics
- **User satisfaction:** Repair success rate
- **Time to repair:** Average repair time
- **Part accuracy:** Correct part recommendation rate
- **Safety compliance:** Safety-critical content retrieval

## Cost Analysis

### Embedding Costs (Gemini text-embedding-004)
- **Current:** ~1,000 chunks → Free (within free tier)
- **Phase 1:** ~100,000 chunks → ~$10 one-time
- **Phase 2:** ~1M chunks → ~$100 one-time
- **Phase 3:** ~10M chunks → ~$1,000 one-time

### Re-ranking Costs (Cohere Rerank)
- **Assumption:** 10,000 searches/day, top-50 re-ranking
- **Cost:** $10/day → $300/month

### Total Estimated Monthly Cost (Phase 3)
- Embeddings (one-time): $1,000
- Re-ranking: $300/month
- Storage (ChromaDB): $50-100/month
- **Total:** ~$350-400/month (after initial embedding)

## Monitoring & Maintenance

### Quality Monitoring
- Daily retrieval quality sampling
- User feedback integration
- A/B testing framework
- Performance dashboards

### Model Updates
- Quarterly embedding model evaluation
- Annual re-ranking model evaluation
- Continuous query expansion optimization
- Regular metadata schema updates
