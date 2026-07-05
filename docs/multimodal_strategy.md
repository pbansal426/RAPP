# Multimodal Knowledge Base Strategy

## Current State

### Existing Capabilities
- Text-only processing (TSB PDFs, repair procedures)
- No image processing
- No diagram understanding
- No visual symptom analysis

### User Input Types
- VIN text
- OBD error codes (text)
- Symptoms description (text)
- **Photos of car issues** (not yet processed)
- **Diagrams from manuals** (not yet processed)

## Multimodal Use Cases

### 1. User Photo Analysis
**Input:** User-uploaded photos of car issues
**Examples:**
- Leaking fluid identification
- Damage assessment
- Component identification
- Wear pattern analysis
- Warning light dashboard photos

### 2. Manual Diagram Processing
**Input:** OEM manual diagrams and illustrations
**Examples:**
- Component location diagrams
- Exploded view diagrams
- Wiring diagrams
- Flow charts
- Torque sequence diagrams

### 3. Visual Procedure Guidance
**Input:** Step-by-step visual procedures
**Examples:**
- Photo-illustrated repair steps
- Video frame extraction
- Before/after comparisons
- Tool usage demonstrations

## Technical Architecture

### Image Processing Pipeline
```
User Image Upload
    ↓
Image Preprocessing
    ├→ Quality assessment (blur, lighting, resolution)
    ├→ Standardization (resize, normalize)
    └→ Region of interest detection
    ↓
Feature Extraction
    ├→ Object detection (components, tools, damage)
    ├→ Text extraction (OCR)
    ├→ Diagram analysis (wiring, exploded views)
    └→ Visual similarity search
    ↓
Multimodal Retrieval
    ├→ Image-to-image search
    ├→ Image-to-text search
    ├→ Text-to-image search
    └→ Cross-modal ranking
    ↓
Result Generation
    ├→ Component identification
    ├→ Issue diagnosis
    ├→ Procedure matching
    └→ Visual guidance
```

## Image Understanding Models

### Option 1: Gemini Vision (Recommended for Production)
**Pros:**
- State-of-the-art visual understanding
- Strong automotive component recognition
- Excellent OCR capabilities
- Easy integration (already using Gemini for LLM)
- Multimodal reasoning
- Cost-effective pricing

**Cons:**
- API dependency
- Rate limits

**Best for:** Production with budget for API costs

### Option 2: Claude 3 Vision (Alternative)
**Pros:**
- Excellent visual understanding
- Strong technical diagram analysis
- Competitive pricing
- Good OCR capabilities

**Cons:**
- API dependency
- Rate limits

**Best for:** Alternative to Gemini Vision

### Option 3: Open Source - CLIP + YOLO (Cost-Effective)
**Pros:**
- Free and open source
- Self-hosted
- No API dependency
- Customizable

**Cons:**
- Requires training/fine-tuning for automotive
- Infrastructure overhead
- Lower accuracy than commercial models

**Best for:** Cost-sensitive scaling, privacy requirements

### Option 4: Specialized Automotive Models
**Pros:**
- Optimized for automotive components
- Better damage detection
- Specialized diagram understanding

**Cons:**
- Limited availability
- May require custom development
- Higher cost

**Best for:** Long-term optimization with large dataset

## Implementation Strategy

### Phase 1: Basic Image Analysis (Week 1-2)
**Goal:** Enable user photo analysis for component identification

**Actions:**
1. Integrate Gemini Vision API
2. Implement image preprocessing
3. Add component detection
4. Create image-to-text mapping
5. Basic visual similarity search

**Expected Outcomes:**
- Users can upload photos of issues
- System identifies components in photos
- Visual similarity to manual diagrams

### Phase 2: Diagram Processing (Week 3-4)
**Goal:** Process and index manual diagrams

**Actions:**
1. Extract diagrams from OEM manuals
2. Classify diagram types (exploded view, wiring, location)
3. Add diagram metadata to vector store
4. Implement diagram-to-procedure linking
5. Create visual search capability

**Expected Outcomes:**
- Diagrams indexed and searchable
- Users can search by visual similarity
- Diagrams linked to relevant procedures

### Phase 3: Visual Procedure Guidance (Month 2)
**Goal:** Add visual step-by-step guidance

**Actions:**
1. Extract photo sequences from manuals
2. Create visual procedure chunks
3. Link visual steps to text instructions
4. Implement before/after comparisons
5. Add tool usage visualization

**Expected Outcomes:**
- Visual procedure steps available
- Photo-enhanced repair instructions
- Tool usage demonstrations

### Phase 4: Advanced Visual Analysis (Month 3)
**Goal:** Advanced damage and wear analysis

**Actions:**
1. Implement damage detection
2. Add wear pattern analysis
3. Create fluid leak identification
4. Implement warning light recognition
5. Add visual diagnostic confidence scoring

**Expected Outcomes:**
- Automated damage assessment
- Fluid leak identification
- Dashboard warning light recognition

## Multimodal Retrieval

### Image-to-Image Search
```python
def search_similar_images(
    query_image: Image,
    k: int = 5
) -> List[ImageResult]:
    # Extract image embeddings
    image_embedding = vision_model.encode(query_image)
    
    # Search image vector store
    similar_images = image_store.search(
        embedding=image_embedding,
        k=k
    )
    
    return similar_images
```

### Image-to-Text Search
```python
def search_text_from_image(
    query_image: Image,
    k: int = 5
) -> List[TextResult]:
    # Extract image features
    image_description = vision_model.describe(query_image)
    components = vision_model.detect_components(query_image)
    
    # Search text vector store
    text_results = text_store.search(
        query=image_description,
        metadata_filter={"components": components}
    )
    
    return text_results
```

### Text-to-Image Search
```python
def search_images_from_text(
    query_text: str,
    k: int = 5
) -> List[ImageResult]:
    # Generate image embedding from text
    text_embedding = clip_model.encode_text(query_text)
    
    # Search image vector store
    image_results = image_store.search(
        embedding=text_embedding,
        k=k
    )
    
    return image_results
```

### Cross-Modal Ranking
```python
def rank_multimodal_results(
    query: str,
    query_image: Image,
    text_results: List[TextResult],
    image_results: List[ImageResult]
) -> List[MultimodalResult]:
    # Score cross-modal relevance
    scored_results = []
    
    for text_result in text_results:
        # Text relevance
        text_score = semantic_similarity(query, text_result.text)
        
        # Image relevance (if available)
        if text_result.related_images:
            image_score = image_similarity(query_image, text_result.related_images)
        else:
            image_score = 0
        
        # Combined score
        combined_score = 0.7 * text_score + 0.3 * image_score
        
        scored_results.append({
            'type': 'text',
            'data': text_result,
            'score': combined_score
        })
    
    for image_result in image_results:
        # Image relevance
        image_score = image_similarity(query_image, image_result.image)
        
        # Text relevance (if available)
        if image_result.related_text:
            text_score = semantic_similarity(query, image_result.related_text)
        else:
            text_score = 0
        
        # Combined score
        combined_score = 0.7 * image_score + 0.3 * text_score
        
        scored_results.append({
            'type': 'image',
            'data': image_result,
            'score': combined_score
        })
    
    # Sort and return
    return sorted(scored_results, key=lambda x: x['score'], reverse=True)[:10]
```

## Metadata for Visual Content

### Image Metadata Schema
```json
{
  "image_type": "component_photo",
  "component_category": "Brake System",
  "component_name": "Brake Caliper",
  "view_angle": "front",
  "condition": "worn",
  "quality_score": 0.85,
  "resolution": "1920x1080",
  "source_type": "user_upload",
  "detection_confidence": 0.92,
  "detected_objects": ["brake caliper", "brake rotor", "brake pads"],
  "text_content": ["caliper bolt", "torque spec"],
  "related_procedures": ["brake caliper replacement"],
  "diagram_type": null,
  "visual_features": ["metallic", "corrosion", "wear_pattern"]
}
```

### Diagram Metadata Schema
```json
{
  "image_type": "diagram",
  "diagram_type": "exploded_view",
  "component_category": "Engine",
  "component_name": "Timing Belt System",
  "view_angle": "exploded",
  "quality_score": 0.95,
  "resolution": "3000x2000",
  "source_type": "oem_manual",
  "labeled_components": ["crankshaft", "camshaft", "timing belt", "tensioner"],
  "part_numbers": ["13568-09010", "13568-09011"],
  "torque_specs": ["76 ft-lbs"],
  "related_procedures": ["timing belt replacement"],
  "visual_features": ["schematic", "labeled", "exploded"]
}
```

## Storage Architecture

### Image Storage Options

#### Option 1: Cloud Storage (Recommended)
- **AWS S3** or **Google Cloud Storage**
- Scalable, reliable, cost-effective
- CDN integration for fast delivery
- Estimated cost: $0.023/GB/month

#### Option 2: Local Storage
- On-premises storage
- Full control, no recurring costs
- Limited scalability
- Backup responsibility

#### Option 3: Hybrid Approach
- Hot data in cloud storage
- Cold data in local/archive storage
- Optimized for cost and performance

### Vector Store for Images
- **CLIP embeddings** (512 dimensions)
- **Separate collection** from text embeddings
- **Metadata filtering** for image types
- **Approximate nearest neighbor** for fast search

## Cost Analysis

### Gemini Vision API Costs
- **Gemini 1.5 Pro:** Free tier available, then $0.0025/image for standard resolution
- **Gemini 1.5 Flash:** Lower cost for faster processing
- **Assumption:** 1,000 images/day → $2.50-7.50/day → $75-225/month

### Storage Costs (AWS S3)
- **Images:** 100,000 images @ 2MB average → 200GB → $4.60/month
- **Diagrams:** 50,000 diagrams @ 5MB average → 250GB → $5.75/month
- **Total storage:** ~$10/month

### Vector Store Costs
- **Image embeddings:** 150,000 images @ 512 dims → minimal storage
- **ChromaDB:** Included in existing infrastructure

### Total Estimated Monthly Cost (Phase 4)
- **Vision API:** $75-225/month
- **Storage:** $10/month
- **Total:** $85-235/month

## Use Case Examples

### Use Case 1: Fluid Leak Identification
**User Input:** Photo of fluid under car
**Processing:**
1. Image preprocessing and quality check
2. Fluid color and location detection
3. Component identification (radiator, transmission, etc.)
4. Visual similarity to known leak patterns
5. Text search for leak diagnosis procedures

**Output:**
- "This appears to be coolant leak from radiator"
- Related procedures: radiator replacement, hose inspection
- Required parts: radiator, hoses, clamps
- Safety warnings: hot coolant hazard

### Use Case 2: Component Identification
**User Input:** Photo of unknown component
**Processing:**
1. Object detection for automotive components
2. Component classification
3. Cross-reference with vehicle specifications
4. Retrieve component information and procedures

**Output:**
- "This is the brake caliper for your 2010 Toyota Corolla"
- Component details, part numbers, related procedures
- Visual comparison to manual diagrams

### Use Case 3: Diagram Search
**User Input:** "Show me the timing belt diagram"
**Processing:**
1. Text search for "timing belt"
2. Image search for timing belt diagrams
3. Filter by vehicle specifications
4. Rank by relevance and quality

**Output:**
- Exploded view diagram of timing belt system
- Labeled components with part numbers
- Related procedures and torque specs

## Implementation Priority

### Immediate (Week 1-2)
1. **Gemini Vision Integration**
   - Add image upload endpoint
   - Implement basic image analysis
   - Create image-to-text mapping

2. **Image Storage Setup**
   - Configure cloud storage
   - Implement image preprocessing
   - Add image metadata schema

### Short-term (Week 3-4)
3. **Diagram Processing**
   - Extract diagrams from manuals
   - Classify diagram types
   - Index diagrams in vector store

4. **Visual Search**
   - Implement image-to-image search
   - Add image-to-text search
   - Create cross-modal ranking

### Medium-term (Month 2-3)
5. **Advanced Analysis**
   - Damage detection
   - Wear pattern analysis
   - Fluid leak identification

6. **Visual Procedures**
   - Extract photo sequences
   - Link visual steps to text
   - Create visual guidance

## Monitoring & Quality

### Image Quality Metrics
- **Detection accuracy:** Component identification rate
- **Classification accuracy:** Diagram type classification
- **User satisfaction:** Visual analysis helpfulness
- **Processing time:** Image analysis latency

### Continuous Improvement
- Weekly accuracy audits
- Monthly model performance reviews
- User feedback integration
- Model retraining with new data

## Privacy & Security

### User Image Handling
- **Consent:** Explicit user consent for image processing
- **Retention:** Configurable image retention policies
- **Anonymization:** Remove personal information from images
- **Access:** Role-based access to image data

### Data Protection
- **Encryption:** At-rest and in-transit encryption
- **Compliance:** GDPR, CCPA compliance
- **Audit:** Image access logging
- **Deletion:** User-controlled image deletion
