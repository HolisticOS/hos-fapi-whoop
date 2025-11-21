# WHOOP Health Insights API (Gemini-powered)

AI-powered health insights generated from WHOOP data using Google's Gemini 2.5 Flash model.

## Features

✅ **7-Day Data Analysis** - Analyzes recovery, sleep, cycle, and workout data
✅ **AI-Powered Insights** - Uses Gemini 2.5 Flash for fast, intelligent analysis
✅ **Trend Detection** - Identifies improving/declining/stable patterns
✅ **Actionable Recommendations** - Specific advice based on your data
✅ **Smart Caching** - 1-hour cache reduces API costs
✅ **Data Quality Assessment** - Validates sufficient data before analysis

## Quick Start

### 1. Get Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key (free tier available)
3. Copy the key

### 2. Configure Environment

Add to your `.env` file:

```env
# Google Gemini API Settings
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TEMPERATURE=0.7
GEMINI_MAX_OUTPUT_TOKENS=2048
CACHE_TTL_INSIGHTS=3600
```

### 3. Test the API

```bash
# Set your JWT token in .env
TEST_JWT_TOKEN=your_supabase_jwt_token

# Run the test script
./venv-whoop/Scripts/python.exe test_insights.py

# Or run quick test
./venv-whoop/Scripts/python.exe test_insights.py --quick

# Test with custom days
./venv-whoop/Scripts/python.exe test_insights.py --days 14
```

## API Endpoint

### GET `/api/v1/data/insights`

Generate AI-powered health insights from WHOOP data.

**Query Parameters:**
- `days_back` (optional): Number of days to analyze (1-30, default: 7)

**Headers:**
- `Authorization: Bearer <supabase_jwt_token>` (required)

**Example Request:**

```bash
curl -H "Authorization: Bearer <your_jwt_token>" \
     "http://localhost:8001/api/v1/data/insights?days_back=7"
```

**Example Response:**

```json
{
  "user_id": "a57f70b4-d0a4-4aef-b721-a4b526f64869",
  "date_range": {
    "start": "2025-11-14",
    "end": "2025-11-21",
    "days": 7
  },
  "insights": [
    "Your recovery scores are consistently above 70%, indicating strong adaptation to training load",
    "Sleep efficiency has improved from 85% to 92% over the past week",
    "HRV shows a positive upward trend, suggesting reduced stress and improved recovery"
  ],
  "summary": "Overall health metrics are trending positively with strong recovery scores and improving sleep quality. Your body is adapting well to the current training load.",
  "recommendations": [
    "Maintain current sleep schedule - consistency is paying off",
    "Consider a deload week if strain remains above 15 for more than 3 consecutive days",
    "Focus on maintaining HRV above 60ms through stress management techniques"
  ],
  "trends": {
    "recovery": "improving",
    "sleep": "improving",
    "strain": "stable",
    "overall": "Positive trajectory with strong recovery adaptation"
  },
  "generated_at": "2025-11-21T15:30:00Z",
  "data_quality": "excellent",
  "model": "gemini-2.5-flash"
}
```

## Response Schema

### `WhoopInsightsResponse`

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string | User's UUID |
| `date_range` | object | Analysis date range |
| `insights` | array[string] | Key insights from data analysis |
| `summary` | string | 2-3 sentence health overview |
| `recommendations` | array[string] | Actionable improvement suggestions |
| `trends` | object | Trend analysis for each metric |
| `generated_at` | string | ISO timestamp when generated |
| `data_quality` | string | excellent/good/fair/limited/insufficient |
| `model` | string | AI model used (gemini-2.5-flash) |

### Data Quality Levels

- **excellent**: 20+ data records across all metrics
- **good**: 15-19 data records
- **fair**: 10-14 data records
- **limited**: 3-9 data records
- **insufficient**: <3 data records (cannot generate insights)

## Cost Estimation

Based on Gemini 2.5 Flash pricing:

| Metric | Value |
|--------|-------|
| Model cost | $0.53 per million tokens |
| Avg tokens/request | ~1,000 tokens |
| Cost per insight | ~$0.0005 |
| Daily cost (cached) | ~$0.012/user |
| Monthly cost | ~$0.36/user |

**With 1-hour caching:** Maximum 24 requests/day per user

## Integration

### Flutter Integration

Add to `whoop_service.dart`:

```dart
/// Get AI-powered health insights
Future<Map<String, dynamic>> getHealthInsights({
  required String userId,
  int daysBack = 7,
}) async {
  if (!isEnabled) {
    throw Exception('WHOOP integration is disabled');
  }

  try {
    final url = Uri.parse(
      '${AppConfig.whoopApiBaseUrl}/data/insights',
    ).replace(queryParameters: {
      'days_back': daysBack.toString(),
    });

    final response = await _client.get(
      url,
      headers: _headers,  // Includes JWT auth
    );

    if (response.statusCode == 200) {
      return json.decode(response.body) as Map<String, dynamic>;
    } else if (response.statusCode == 403) {
      throw Exception('WHOOP_NOT_ACTIVE');
    } else {
      throw Exception('Failed to get insights: ${response.statusCode}');
    }
  } catch (e) {
    throw Exception('Error fetching health insights: $e');
  }
}
```

### Display in UI

```dart
// Fetch insights
final insights = await WhoopService().getHealthInsights(
  userId: _userId,
  daysBack: 7,
);

// Display summary
Text(insights['summary']),

// Display insights
...insights['insights'].map((insight) =>
  ListTile(
    leading: Icon(Icons.lightbulb),
    title: Text(insight),
  )
),

// Display recommendations
...insights['recommendations'].map((rec) =>
  ListTile(
    leading: Icon(Icons.recommend),
    title: Text(rec),
  )
),
```

## Troubleshooting

### Error: "GEMINI_API_KEY not configured"

**Solution:** Add `GEMINI_API_KEY` to your `.env` file

```env
GEMINI_API_KEY=your_actual_api_key_here
```

### Error: "Insufficient data available"

**Cause:** User has less than 3 days of WHOOP data

**Solution:**
- Sync more WHOOP data
- Reduce `days_back` parameter
- Ensure WHOOP device is connected and syncing

### Error: "Unauthorized" (401)

**Cause:** JWT token is invalid or expired

**Solution:** Get a fresh JWT token from Supabase:

```dart
final token = Supabase.instance.client.auth.currentSession?.accessToken;
print('JWT Token: $token');
```

### Error: "Forbidden" (403)

**Cause:** WHOOP connection is not active (`is_active=false`)

**Solution:** Reconnect WHOOP account through the app

### Slow response times

**Cause:** First request generates insights (not cached)

**Solution:**
- Normal behavior - first request takes 3-10 seconds
- Subsequent requests are cached (< 1 second)
- Cache expires after 1 hour

## Technical Details

### Architecture

```
User Request (JWT auth)
    ↓
API Endpoint (/data/insights)
    ↓
WhoopInsightsService
    ↓ (check cache)
    ↓
WhoopDataService (fetch 7 days of raw data)
    ↓
Format data for Gemini
    ↓
Gemini 2.5 Flash API (generate insights)
    ↓
Cache result (1 hour)
    ↓
Return structured response
```

### Data Processing

1. **Fetch Raw Data:** Recovery, Sleep, Cycle, Workout tables
2. **Format Data:** Structured markdown summary with key metrics
3. **AI Analysis:** Gemini identifies patterns, trends, correlations
4. **Structure Response:** JSON with insights, recommendations, trends
5. **Cache:** 1-hour TTL to reduce costs

### Model Selection: Gemini 2.5 Flash

**Why Gemini 2.5 Flash?**
- **Speed:** 163.6 tokens/second (1.5x faster than 2.0)
- **Cost:** 13x cheaper than Gemini Pro
- **Context:** 1M token window (perfect for 7 days of data)
- **Proven:** Used in production for health data analysis

**Alternatives:**
- **Gemini 2.5 Pro:** Better reasoning but 13x more expensive
- **Gemini 2.5 Flash-Lite:** Faster but less capable

## Files

| File | Purpose |
|------|---------|
| `app/services/insights_service.py` | Core insights generation service |
| `app/api/internal.py` | API endpoint definition |
| `app/models/schemas.py` | Pydantic response models |
| `test_insights.py` | Comprehensive test suite |
| `.env.example` | Configuration template |

## Development

### Run Tests

```bash
# Full test suite
./venv-whoop/Scripts/python.exe test_insights.py

# Quick test (insights only)
./venv-whoop/Scripts/python.exe test_insights.py --quick

# Custom days
./venv-whoop/Scripts/python.exe test_insights.py --days 14

# Show help
./venv-whoop/Scripts/python.exe test_insights.py --help
```

### Clear Cache

The cache clears automatically after 1 hour, or you can restart the server:

```bash
# Restart server (clears cache)
./venv-whoop/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Monitor Costs

View usage at [Google AI Studio](https://aistudio.google.com/app/apikey)

## Support

- **Gemini Documentation:** https://ai.google.dev/gemini-api/docs
- **API Reference:** http://localhost:8001/docs
- **WHOOP API:** https://developer.whoop.com/docs

## License

Part of the HolisticOS WHOOP integration service.
