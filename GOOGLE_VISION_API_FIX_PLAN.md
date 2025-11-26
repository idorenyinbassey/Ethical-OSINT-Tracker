# Google Vision API 400 Error - Root Cause Analysis & Fix Plan

## Error Details
```
Google Vision API error: Client error '400 Bad Request' 
for url 'https://vision.googleapis.com/v1/images:annotate?key=9694e52164e9130a2d8b3f20086d363dcb7543da'
```

## Root Cause Analysis

### Problem #1: Invalid API Key Format
**Current Issue**: The API key in settings (`9694e52164e9130a2d8b3f20086d363dcb7543da`) appears to be a placeholder/test key, not a valid Google Cloud API key.

**Valid Google Cloud API Key Format**:
- Pattern: `AIza` prefix followed by 35 characters
- Example: `AIzaSyDaGmWKa4JsXZ-HjGbvB0123456789ABCD`
- Length: 39 characters total
- Source: Google Cloud Console → APIs & Services → Credentials

**Current Key Issues**:
- ❌ No `AIza` prefix
- ❌ Wrong length (40 chars instead of 39)
- ❌ Looks like a random hex string, not a Google API key

### Problem #2: Incorrect API Endpoint
**Current Implementation**:
```python
endpoint = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
```

**Issues**:
- ❌ API key should be in header, not URL query parameter (security best practice)
- ❌ Missing version-specific endpoint path
- ⚠️ Works but exposes key in logs/URLs

**Correct Implementation Options**:

**Option A: API Key in Header (Recommended)**
```python
endpoint = "https://vision.googleapis.com/v1/images:annotate"
headers = {
    "Content-Type": "application/json",
    "X-goog-api-key": api_key  # or use Authorization header
}
```

**Option B: Query Parameter (Current, but less secure)**
```python
endpoint = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
```

### Problem #3: Missing API Key Validation
**Current Flow**:
```python
cfg = get_by_service("ImageRecognition")
if cfg and cfg.is_enabled and cfg.api_key:
    # Directly uses API key without validation
    api_key = cfg.api_key
```

**Issues**:
- ❌ No format validation before API call
- ❌ No helpful error message for invalid keys
- ❌ Users don't know if their key is valid until API call fails

### Problem #4: Poor Error Handling
**Current Implementation**:
```python
except Exception as e:
    result["exif"]["api_error"] = f"Google Vision API error: {str(e)}"
```

**Issues**:
- ❌ Generic exception catch hides specific HTTP errors
- ❌ No differentiation between 400 (bad request), 401 (invalid key), 403 (quota exceeded)
- ❌ No actionable guidance for users

## Comprehensive Fix Plan

### Phase 1: Immediate Fixes (Critical - 15 minutes)

#### Fix 1.1: Add API Key Validation
**File**: `app/services/image_client.py`
**Location**: Before API call (line ~215)

```python
def validate_google_vision_key(api_key: str) -> tuple[bool, str]:
    """Validate Google Cloud Vision API key format.
    
    Returns:
        (is_valid, error_message)
    """
    if not api_key:
        return False, "API key is empty"
    
    # Google Cloud API keys start with "AIza" and are 39 chars
    if not api_key.startswith("AIza"):
        return False, "Invalid format: Google Cloud API keys must start with 'AIza'"
    
    if len(api_key) != 39:
        return False, f"Invalid length: Expected 39 characters, got {len(api_key)}"
    
    # Check for valid characters (alphanumeric, _, -)
    import re
    if not re.match(r'^[A-Za-z0-9_-]+$', api_key):
        return False, "Invalid characters: API key contains invalid characters"
    
    return True, ""
```

**Integration Point**:
```python
# Before making API call
is_valid, error_msg = validate_google_vision_key(api_key)
if not is_valid:
    result["exif"]["api_error"] = f"Configuration Error: {error_msg}"
    result["identified_person"] = "API key validation failed"
    result["confidence"] = "N/A"
    return result
```

#### Fix 1.2: Improve Error Handling
**File**: `app/services/image_client.py`
**Location**: Exception handler (line ~318)

```python
except httpx.HTTPStatusError as e:
    # Specific HTTP error handling
    status_code = e.response.status_code
    
    if status_code == 400:
        error_detail = "Invalid request format or parameters"
        try:
            error_data = e.response.json()
            if "error" in error_data:
                error_detail = error_data["error"].get("message", error_detail)
        except:
            pass
        result["exif"]["api_error"] = f"Bad Request (400): {error_detail}"
        
    elif status_code == 401:
        result["exif"]["api_error"] = "Authentication Failed (401): Invalid API key. Get key from Google Cloud Console."
        
    elif status_code == 403:
        result["exif"]["api_error"] = "Access Denied (403): API key lacks permissions or quota exceeded. Check Cloud Console."
        
    elif status_code == 429:
        result["exif"]["api_error"] = "Rate Limit Exceeded (429): Too many requests. Wait before retrying."
        
    else:
        result["exif"]["api_error"] = f"HTTP Error ({status_code}): {str(e)}"
        
except httpx.RequestError as e:
    result["exif"]["api_error"] = f"Network Error: {str(e)}"
    
except Exception as e:
    result["exif"]["api_error"] = f"Unexpected Error: {str(e)}"
```

#### Fix 1.3: Update Settings Page with Better Instructions
**File**: `app/pages/settings.py`
**Location**: `google_vision_setup_instructions()` function

Add these critical warnings:
```python
# Warning about API key format
rx.el.div(
    rx.icon("alert-triangle", size=16, class_name="text-red-500"),
    rx.el.span(
        "API Key Format: Must start with 'AIza' and be exactly 39 characters",
        class_name="text-sm text-red-700 font-semibold ml-2"
    ),
    class_name="flex items-center p-3 bg-red-50 rounded-lg border border-red-200 mb-3"
)

# Example key format
rx.el.div(
    rx.el.span("Example: ", class_name="text-xs text-gray-500"),
    rx.el.code(
        "AIzaSyDaGmWKa4JsXZ-HjGbvB0123456789ABCD",
        class_name="text-xs bg-gray-100 px-2 py-1 rounded"
    ),
    class_name="mb-3"
)
```

### Phase 2: Enhanced Features (High Priority - 20 minutes)

#### Fix 2.1: API Key Test Button
**File**: `app/states/settings_state.py`
**New Method**:

```python
@rx.event
async def test_api_connection(self):
    """Test Google Vision API connection with current key."""
    self.is_testing_api = True
    self.api_test_result = None
    yield
    
    from app.services.image_client import validate_google_vision_key
    import httpx
    
    # Get ImageRecognition config
    from app.repositories.api_config_repository import get_by_service
    cfg = get_by_service("ImageRecognition")
    
    if not cfg or not cfg.api_key:
        self.api_test_result = "❌ No API key configured"
        self.is_testing_api = False
        return
    
    # Validate format first
    is_valid, error_msg = validate_google_vision_key(cfg.api_key)
    if not is_valid:
        self.api_test_result = f"❌ Invalid Key Format: {error_msg}"
        self.is_testing_api = False
        return
    
    # Test with minimal request
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Use a tiny 1x1 pixel test image
            import base64
            # 1x1 red pixel PNG
            test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
            
            request_body = {
                "requests": [{
                    "image": {"content": test_image},
                    "features": [{"type": "LABEL_DETECTION", "maxResults": 1}]
                }]
            }
            
            endpoint = f"https://vision.googleapis.com/v1/images:annotate?key={cfg.api_key}"
            headers = {"Content-Type": "application/json"}
            
            response = await client.post(endpoint, headers=headers, json=request_body)
            response.raise_for_status()
            
            self.api_test_result = "✅ Connection Successful! API key is valid."
            
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status == 401:
            self.api_test_result = "❌ Invalid API Key (401)"
        elif status == 403:
            self.api_test_result = "❌ API Not Enabled or Quota Exceeded (403)"
        else:
            self.api_test_result = f"❌ HTTP Error {status}"
    except Exception as e:
        self.api_test_result = f"❌ Error: {str(e)[:100]}"
    
    self.is_testing_api = False
```

**UI Addition** (in `api_config_form()`):
```python
rx.cond(
    SettingsState.selected_service == "ImageRecognition",
    rx.el.div(
        rx.el.button(
            rx.cond(
                SettingsState.is_testing_api,
                rx.spinner(size="3"),
                "Test API Connection"
            ),
            on_click=SettingsState.test_api_connection,
            disabled=SettingsState.is_testing_api,
            class_name="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        ),
        rx.cond(
            SettingsState.api_test_result,
            rx.el.div(
                SettingsState.api_test_result,
                class_name="mt-2 p-3 rounded-lg bg-gray-50 text-sm"
            )
        ),
        class_name="mt-4"
    )
)
```

#### Fix 2.2: Real-time Key Format Validation
**File**: `app/states/settings_state.py`
**Add Computed Var**:

```python
@rx.var
def api_key_validation_message(self) -> str:
    """Real-time validation message for API key input."""
    if not self.form_api_key:
        return ""
    
    if self.selected_service == "ImageRecognition":
        from app.services.image_client import validate_google_vision_key
        is_valid, error_msg = validate_google_vision_key(self.form_api_key)
        
        if is_valid:
            return "✅ Valid Google Cloud API key format"
        else:
            return f"⚠️ {error_msg}"
    
    return ""
```

**UI Integration**:
```python
rx.cond(
    SettingsState.api_key_validation_message != "",
    rx.el.div(
        SettingsState.api_key_validation_message,
        class_name=rx.cond(
            SettingsState.api_key_validation_message.contains("✅"),
            "text-sm text-green-600 mt-1",
            "text-sm text-orange-600 mt-1"
        )
    )
)
```

### Phase 3: Documentation & User Guidance (Medium Priority - 10 minutes)

#### Fix 3.1: Update Settings Instructions
**Add to `google_vision_setup_instructions()`**:

```python
# Common Issues Section
rx.el.div(
    rx.el.h4(
        "⚠️ Common Issues & Solutions",
        class_name="font-semibold text-gray-800 mb-2"
    ),
    rx.el.ul(
        rx.el.li(
            rx.el.strong("400 Bad Request:"),
            " Invalid API key format. Ensure key starts with 'AIza' and is 39 characters.",
            class_name="text-sm text-gray-700 mb-2"
        ),
        rx.el.li(
            rx.el.strong("401 Unauthorized:"),
            " API key is invalid or revoked. Generate a new key in Cloud Console.",
            class_name="text-sm text-gray-700 mb-2"
        ),
        rx.el.li(
            rx.el.strong("403 Forbidden:"),
            " Cloud Vision API not enabled for project, or free quota exceeded.",
            class_name="text-sm text-gray-700 mb-2"
        ),
        class_name="list-disc list-inside"
    ),
    class_name="mt-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200"
)
```

#### Fix 3.2: Add Troubleshooting Guide
**New File**: `docs/GOOGLE_VISION_TROUBLESHOOTING.md`

```markdown
# Google Cloud Vision API Troubleshooting

## Error: 400 Bad Request

### Causes:
1. Invalid API key format
2. Malformed request body
3. Image too large (>20MB)

### Solutions:
1. Verify API key starts with "AIza" and is 39 characters
2. Use the "Test API Connection" button in Settings
3. Check image size (must be <20MB, <75 megapixels)

## Error: 401 Unauthorized

### Causes:
1. API key is invalid
2. API key has been revoked
3. API key doesn't belong to your project

### Solutions:
1. Generate a new API key in Google Cloud Console
2. Ensure you copied the entire key (39 characters)
3. Verify the key is from the correct GCP project

## Error: 403 Forbidden

### Causes:
1. Cloud Vision API not enabled
2. Free tier quota exceeded (1,000 requests/month)
3. API key restricted to specific IPs/domains

### Solutions:
1. Enable API: Cloud Console → APIs & Services → Enable Cloud Vision API
2. Check quota: Cloud Console → APIs & Services → Quotas
3. Update API key restrictions if needed

## How to Get a Valid API Key

1. Go to: https://console.cloud.google.com/
2. Select or create a project
3. Navigate to: APIs & Services → Credentials
4. Click "Create Credentials" → "API Key"
5. Copy the key (starts with "AIza", 39 characters)
6. Enable Cloud Vision API for the project
7. (Optional) Set restrictions on the key

## Free Tier Limits

- 1,000 requests per month (free)
- After free tier: $1.50 per 1,000 images
- Feature-specific pricing applies

## Testing Your Setup

Use the built-in API test in Settings:
1. Navigate to Settings → API Integrations
2. Select "Google Cloud Vision AI"
3. Enter your API key
4. Click "Test API Connection"
5. Verify you see "✅ Connection Successful!"
```

### Phase 4: Advanced Enhancements (Low Priority - Optional)

#### Fix 4.1: API Key Encryption at Rest
**File**: `app/utils/crypto.py` (already exists)

Use existing encryption utilities to encrypt API keys in database.

#### Fix 4.2: Quota Tracking
Track API usage per user/globally to warn before hitting limits.

#### Fix 4.3: Fallback to Mock Data
When API fails, provide deterministic mock results instead of just error message.

## Implementation Priority

### 🔴 Critical (Do First):
1. ✅ Add API key format validation function
2. ✅ Improve error handling with specific HTTP status codes
3. ✅ Update settings page with format requirements

### 🟡 High Priority (Do Second):
4. ✅ Add "Test API Connection" button
5. ✅ Real-time key format validation in UI
6. ✅ Enhanced error messages with actionable guidance

### 🟢 Medium Priority (Do Third):
7. ✅ Add troubleshooting documentation
8. ✅ Update settings instructions with common issues
9. ✅ Add example API key format

### 🔵 Low Priority (Optional):
10. ⭕ Encrypt API keys at rest
11. ⭕ Add quota tracking/warnings
12. ⭕ Implement mock fallback for testing

## Files to Modify

1. **`app/services/image_client.py`** (Lines ~215-325)
   - Add `validate_google_vision_key()` function
   - Update error handling in `analyze_image()`
   - Import httpx exceptions specifically

2. **`app/states/settings_state.py`** (Lines ~50-150)
   - Add `is_testing_api: bool = False`
   - Add `api_test_result: Optional[str] = None`
   - Add `test_api_connection()` event
   - Add `api_key_validation_message` computed var

3. **`app/pages/settings.py`** (Lines ~114-178)
   - Enhance `google_vision_setup_instructions()`
   - Add API key format warning
   - Add common issues section
   - Add test button UI

4. **`docs/GOOGLE_VISION_TROUBLESHOOTING.md`** (New file)
   - Complete troubleshooting guide
   - Step-by-step API key setup
   - Common error solutions

## Testing Plan

### Test Case 1: Invalid Key Format
- **Input**: `9694e52164e9130a2d8b3f20086d363dcb7543da` (current key)
- **Expected**: Validation fails, shows format error before API call
- **Verify**: No network request made

### Test Case 2: Valid Key Format (Mock)
- **Input**: `AIzaSyDaGmWKa4JsXZ-HjGbvB0123456789ABCD`
- **Expected**: Format validation passes
- **Verify**: API call is attempted (will fail with 401 if key is fake)

### Test Case 3: Test Button
- **Action**: Click "Test API Connection" with invalid key
- **Expected**: Shows "❌ Invalid Key Format" message
- **Verify**: No API call made

### Test Case 4: Real-time Validation
- **Action**: Type in API key field character by character
- **Expected**: Validation message updates in real-time
- **Verify**: Green checkmark when format is valid

### Test Case 5: HTTP Error Handling
- **Scenario**: Valid format but invalid key (401)
- **Expected**: Shows "Authentication Failed: Invalid API key" with link to Console
- **Verify**: Error message is actionable

## Estimated Time

- **Phase 1 (Critical)**: 15 minutes
- **Phase 2 (High Priority)**: 20 minutes
- **Phase 3 (Medium Priority)**: 10 minutes
- **Phase 4 (Optional)**: 30 minutes

**Total Core Implementation**: ~45 minutes
**Total with Optional**: ~75 minutes

## Success Criteria

✅ Users see clear error when API key format is invalid  
✅ No API calls made with malformed keys  
✅ Specific, actionable error messages for each HTTP status  
✅ Test button allows verification without uploading images  
✅ Real-time validation helps users fix keys immediately  
✅ Documentation explains how to get a valid key  

## Next Steps

1. **Immediate**: Implement Phase 1 (critical validation & error handling)
2. **Today**: Implement Phase 2 (test button & real-time validation)
3. **This Week**: Add Phase 3 (documentation)
4. **Future**: Consider Phase 4 (encryption, quota tracking)

---

**Current Status**: Plan Complete - Ready for Implementation  
**Blocked By**: Need valid Google Cloud API key for testing  
**Workaround**: Validation will prevent bad API calls; mock testing for UI
