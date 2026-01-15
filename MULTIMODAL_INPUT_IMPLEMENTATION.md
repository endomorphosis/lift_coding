# Multimodal Input Placeholder Implementation

## Summary
This PR adds placeholder support for camera snapshot/image input to the command API with strict privacy enforcement. Mobile/wearable devices can now send image inputs alongside audio/text, and the backend will accept them according to the configured privacy mode.

## Key Features

### 1. OpenAPI Schema Updates
- Added `ImageInput` schema with required `type` and `uri` fields
- Added optional `content_type` field for MIME type specification
- Extended `CommandInput` union type to support text, audio, and image inputs
- Updated discriminator mapping for proper type routing
- **Backward compatible**: Existing clients continue to work without changes

### 2. Privacy Mode Enforcement

#### Strict Mode (Default)
- **Behavior**: Rejects image inputs with error
- **Response**: HTTP 200 with error status
- **Intent**: `error.image_not_supported`
- **Spoken Text**: "Image input is not supported in strict privacy mode."
- **Logging**: Rejection logged without URI (unless debug mode with redaction)

#### Balanced Mode
- **Behavior**: Accepts image inputs but doesn't process them
- **Response**: HTTP 200 with ok status
- **Intent**: `image.placeholder`
- **Spoken Text**: "Image received but cannot be processed yet. Please describe what you need help with."
- **Logging**: Acceptance logged without URI (unless debug mode with redaction)

#### Debug Mode
- **Behavior**: Same as balanced mode + additional debug information
- **Debug Info**: Includes stub message about image not being processed
- **Tool Calls**: Contains note about OCR/vision not yet implemented

### 3. Security & Privacy Guarantees

✅ **No image data fetched**: Image URIs are metadata only - no bytes downloaded  
✅ **No image data stored**: No image content persisted to database or filesystem  
✅ **URI privacy**: Image URIs never appear in spoken_text in any mode  
✅ **Logging privacy**: URIs only logged in debug mode with redaction applied  
✅ **Strict by default**: Default privacy mode rejects images entirely  
✅ **No external dependencies**: No vision/OCR services called  

### 4. Test Coverage

Created comprehensive test suite (`tests/test_image_input.py`) with 12 tests:

**Privacy Enforcement Tests**
- Strict mode rejection (default and explicit)
- Balanced mode acceptance with stub response
- Debug mode acceptance with debug info
- Content type handling (with and without)

**Schema Validation Tests**
- OpenAPI schema accepts ImageInput
- Pydantic model validation
- Required field enforcement

**Logging & Security Tests**
- URI never in spoken_text (all modes)
- Logging behavior verification
- Secret redaction integration

**Backward Compatibility Tests**
- Text input continues to work
- Audio input continues to work

### 5. Implementation Details

**Models (`src/handsfree/models.py`)**
```python
class ImageInput(BaseModel):
    """Image input schema for camera snapshots."""
    type: Literal["image"] = "image"
    uri: str  # Not fetched or processed yet
    content_type: str | None = None
```

**API Handling (`src/handsfree/api.py`)**
- Added `ImageInput` to imports
- Implemented privacy mode checks before processing
- Returns appropriate error or stub response
- Logs with privacy-safe redaction
- Stores command with `input_type="image"`

**OpenAPI Spec (`spec/openapi.yaml`)**
```yaml
ImageInput:
  type: object
  required: [type, uri]
  properties:
    type:
      type: string
      enum: [image]
    uri:
      type: string
      description: URI to the image/camera snapshot
    content_type:
      type: string
      description: MIME type of the image
```

## Validation Results

All required checks pass:

```bash
✅ make fmt-check      # Code formatting verified
✅ make lint           # No lint errors
✅ make test           # 12 new tests passing, 908 total passing
✅ make openapi-validate  # OpenAPI spec valid
```

## Behavioral Changes

### New Input Type Support
- API now accepts `input.type: "image"` in command requests
- Input types: `text`, `audio`, `image`

### Privacy Mode Behavior
- **Strict** (default): Rejects images → no change for existing clients
- **Balanced**: Accepts images with stub response
- **Debug**: Accepts images with stub response + debug info

### No Breaking Changes
- Existing text and audio inputs work identically
- Default privacy mode (strict) maintains existing behavior
- New field is optional and has sensible defaults

## Future Work

This PR provides the foundation for future multimodal capabilities:

1. **OCR/Vision Processing**: Add image analysis in balanced/debug modes
2. **Multiple Images**: Support arrays of images in single request
3. **Image Validation**: Content-type verification, size limits
4. **Vision Models**: Integration with GPT-4 Vision, Claude Vision, or similar
5. **Context Awareness**: Use image content to enhance command understanding

## Migration Guide

### For Mobile/Wearable Clients

**To send an image input:**
```json
{
  "input": {
    "type": "image",
    "uri": "https://example.com/snapshot.jpg",
    "content_type": "image/jpeg"
  },
  "profile": "default",
  "client_context": {
    "device": "ios",
    "locale": "en-US",
    "timezone": "America/Los_Angeles",
    "app_version": "0.1.0",
    "privacy_mode": "balanced"  // Required to accept images
  }
}
```

**Expected responses:**

Strict mode (default):
```json
{
  "status": "error",
  "intent": {"name": "error.image_not_supported", "confidence": 1.0},
  "spoken_text": "Image input is not supported in strict privacy mode."
}
```

Balanced/debug mode:
```json
{
  "status": "ok",
  "intent": {"name": "image.placeholder", "confidence": 1.0},
  "spoken_text": "Image received but cannot be processed yet. Please describe what you need help with."
}
```

### For Backend Integration

No changes required for existing integrations. Image input support is opt-in via privacy mode.

## Testing

Run image input tests:
```bash
pytest tests/test_image_input.py -v
```

Run privacy mode integration tests:
```bash
pytest tests/test_privacy_mode_integration.py -v
```

Run full test suite:
```bash
make test
```

## Files Changed

1. **spec/openapi.yaml** - Added ImageInput schema, updated CommandInput union
2. **src/handsfree/models.py** - Added ImageInput Pydantic model
3. **src/handsfree/api.py** - Added image input handling with privacy enforcement
4. **tests/test_image_input.py** - Comprehensive test coverage (new file)
5. **PRIVACY_MODES_IMPLEMENTATION.md** - Updated documentation

## Constraints Satisfied

✅ No external vision/OCR dependencies  
✅ No image bytes fetched or stored  
✅ Privacy enforcement in strict mode  
✅ Stub response in balanced/debug modes  
✅ URI privacy guaranteed  
✅ OpenAPI schema validation passes  
✅ All tests pass  
✅ Backward compatible  

## Review Checklist

- [x] OpenAPI schema accepts image input
- [x] Strict mode rejects images
- [x] Balanced/debug modes accept images with stub response
- [x] Image URIs never in spoken_text
- [x] Logging respects privacy modes
- [x] No image data fetched or stored
- [x] Tests comprehensive and passing
- [x] Documentation updated
- [x] Code formatted and linted
- [x] Backward compatible
