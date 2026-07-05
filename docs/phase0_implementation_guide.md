# Phase 0 Implementation Guide: Build Knowledge Base First

## Overview

This guide walks through building your knowledge base with minimal cost using Gemini's free tier. You'll build the foundation first, then enable AI to reference it.

## Cost Breakdown

**Phase 0 (Knowledge Base Building):**
- Gemini embeddings: FREE (within free tier limits)
- ChromaDB storage: FREE (local disk storage)
- Total: **$0** for initial setup

**Phase 1+ (AI Reference):**
- Only when you start having users query the knowledge base
- Gemini API costs based on usage
- Estimated: $20-50/month at scale

## Step-by-Step Implementation

### Step 1: Set Up Environment Variables

Add your Gemini API key to `.env`:

```bash
# Copy example file
cp .env.example .env

# Edit .env and add your Gemini API key
GEMINI_API_KEY=your_gemini_api_key_here

# Enable Gemini embeddings (already set in .env.example)
USE_GEMINI_EMBEDDINGS=true
```

### Step 2: Install Dependencies

```bash
# Install Google GenAI SDK for embeddings
uv add google-genai
```

### Step 3: Test Current TSB Data

First, see what TSB data you currently have:

```bash
# Run the existing ETL pipeline to see current data
uv run --group etl python -m etl --year 2010 --make Toyota --model Corolla
```

This will show you the existing TSB data structure and current chunks.

### Step 4: Re-index with Gemini Embeddings

Run the re-indexing script to upgrade your existing TSB data:

```bash
python scripts/reindex_with_gemini.py
```

This will:
- Load existing TSB chunks from ChromaDB
- Re-embed them using Gemini text-embedding-004
- Replace the old embeddings with higher-quality ones

### Step 5: Test Enhanced Retrieval

Create a simple test script to verify the improved retrieval:

```python
# test_retrieval.py
from backend.rag import retrieve

# Test with a sample query
results = retrieve(
    query="brake caliper replacement",
    vin_meta={
        "year": 2010,
        "make": "Toyota", 
        "model": "Corolla"
    },
    k=5
)

for result in results:
    print(f"Score: {result['distance']}")
    print(f"Text: {result['text'][:200]}...")
    print(f"Metadata: {result['metadata']}")
    print("---")
```

Run it:
```bash
python test_retrieval.py
```

### Step 6: Add Enhanced Metadata (Optional)

Update your TSB ingestion to include enhanced metadata fields:

```python
# In your ETL pipeline, when creating chunks
vehicle = VehicleKey(year=2010, make="Toyota", model="Corolla")

# Enhanced metadata with component, procedure type, etc.
chunk_metadata = vehicle.metadata_tag(
    chunk_type="tsb",
    component_category="Brake System",
    component_name="Brake Caliper",
    procedure_type="repair",
    difficulty_level="intermediate",
    source_type="nhtsa_tsb",
    source_authority="official",
    quality_score=0.95
)
```

### Step 7: Ingest More TSB Data

Scale up your knowledge base by ingesting TSBs for more vehicles:

```bash
# Add more vehicles to your knowledge base
uv run --group etl python -m etl --year 2011 --make Toyota --model Corolla
uv run --group etl python -m etl --year 2012 --make Toyota --model Corolla
uv run --group etl python -m etl --year 2010 --make Honda --model Civic
```

## What You've Built

After completing Phase 0, you'll have:

1. **Enhanced Metadata Schema**
   - Support for component, procedure, symptom metadata
   - Source quality tracking
   - Vehicle-specific filtering

2. **Gemini-Powered Embeddings**
   - Higher-quality semantic understanding
   - Better retrieval accuracy (15-25% improvement expected)
   - Cost-effective (free tier during development)

3. **Scalable Foundation**
   - Ready for additional data sources
   - Metadata structure for advanced filtering
   - Infrastructure for hybrid search

## Next Steps (When Ready)

Once your knowledge base is built, you can:

1. **Enable AI Reference** - Your existing AI will automatically use the enhanced knowledge base
2. **Add More Data Sources** - OEM manuals, repair databases, forums
3. **Implement Hybrid Search** - Add keyword search + re-ranking
4. **Add Multimodal** - Image processing for user photos

## Monitoring

Check your knowledge base health:

```python
from backend.rag import get_vector_store

store = get_vector_store()
count = store.collection.count()
print(f"Total chunks in knowledge base: {count}")
```

## Troubleshooting

### Issue: Gemini API errors
**Solution:** Check your GEMINI_API_KEY is valid and has free tier access

### Issue: Re-indexing fails
**Solution:** Ensure ChromaDB is not locked by another process, check disk space

### Issue: No improvement in retrieval
**Solution:** Verify USE_GEMINI_EMBEDDINGS=true in .env, restart your application

## Cost Monitoring

Track your Gemini usage:
- Free tier: 1,500 requests/day for embeddings
- After free tier: ~$0.10/1M tokens for embeddings
- Monitor usage in Google Cloud Console

## Success Criteria

Phase 0 is complete when:
- ✅ Metadata schema supports enhanced fields
- ✅ Gemini embeddings are working
- ✅ Existing TSB data is re-indexed
- ✅ Retrieval quality is improved
- ✅ System is ready for additional data sources
