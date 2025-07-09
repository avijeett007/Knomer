# User Management & Credit Provisioning API

## 🎯 Overview

The Video Merger API now includes comprehensive user management and credit provisioning endpoints designed for integration with external SaaS platforms.

## 🔑 Authentication

All admin endpoints require an admin API key passed as a form parameter:

```bash
admin_api_key=your-admin-secret-key
```

**Set in environment:**
```bash
ADMIN_API_KEY=your-super-secret-admin-key
```

## 👥 User Management Endpoints

### 1. Create User with Credits

**Endpoint:** `POST /api/v1/admin/users`

**Purpose:** Create a new user with initial credits and API key (for SaaS integration)

**Parameters:**
- `email` (required): User email address
- `name` (optional): User full name
- `subscription_tier` (optional): `free`, `basic`, `premium`, `enterprise` (default: `free`)
- `initial_credits` (optional): Initial credit amount (default: 10000)
- `admin_api_key` (required): Admin authentication key

**Example Request:**
```bash
curl -X POST "https://api.yourdomain.com/api/v1/admin/users" \
  -F "email=user@example.com" \
  -F "name=John Doe" \
  -F "subscription_tier=premium" \
  -F "initial_credits=50000" \
  -F "admin_api_key=your-admin-secret-key"
```

**Example Response:**
```json
{
  "success": true,
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "subscription_tier": "premium",
  "initial_credits": 50000,
  "api_key": "vp_AbCdEf123456789...",
  "message": "User created successfully with initial credits"
}
```

### 2. Provision Monthly Credits

**Endpoint:** `POST /api/v1/admin/users/{user_id}/credits`

**Purpose:** Add credits to existing user (for monthly provisioning)

**Parameters:**
- `user_id` (path): User ID from previous creation
- `credits_amount` (required): Number of credits to add
- `description` (optional): Description for the transaction (default: "Monthly credit provision")
- `admin_api_key` (required): Admin authentication key

**Example Request:**
```bash
curl -X POST "https://api.yourdomain.com/api/v1/admin/users/123e4567-e89b-12d3-a456-426614174000/credits" \
  -F "credits_amount=25000" \
  -F "description=Monthly premium subscription credits" \
  -F "admin_api_key=your-admin-secret-key"
```

**Example Response:**
```json
{
  "success": true,
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "credits_added": 25000,
  "total_credits": 75000,
  "remaining_credits": 75000,
  "description": "Monthly premium subscription credits",
  "message": "Credits provisioned successfully"
}
```

### 3. Get User Details

**Endpoint:** `GET /api/v1/admin/users/{user_id}?admin_api_key=your-key`

**Purpose:** Retrieve user information including credits and API keys

**Example Request:**
```bash
curl -X GET "https://api.yourdomain.com/api/v1/admin/users/123e4567-e89b-12d3-a456-426614174000?admin_api_key=your-admin-secret-key"
```

**Example Response:**
```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "name": "John Doe",
    "subscription_tier": "premium",
    "is_active": true,
    "created_at": "2025-01-08T10:30:00Z"
  },
  "credits": {
    "total_credits": 75000,
    "used_credits": 0,
    "remaining_credits": 75000,
    "last_updated": "2025-01-08T10:30:00Z"
  },
  "api_keys_count": 1,
  "api_keys": [
    {
      "id": "key-123",
      "name": "Default API Key",
      "key_prefix": "vp_AbCdEf",
      "is_active": true,
      "created_at": "2025-01-08T10:30:00Z"
    }
  ]
}
```

## 🔄 Integration Examples

### Node.js/Express Integration

```javascript
const axios = require('axios');

class VideoMergerUserManager {
  constructor(apiUrl, adminApiKey) {
    this.apiUrl = apiUrl;
    this.adminApiKey = adminApiKey;
  }

  async createUser(email, name, subscriptionTier = 'free', initialCredits = 10000) {
    const formData = new FormData();
    formData.append('email', email);
    formData.append('name', name);
    formData.append('subscription_tier', subscriptionTier);
    formData.append('initial_credits', initialCredits);
    formData.append('admin_api_key', this.adminApiKey);

    try {
      const response = await axios.post(`${this.apiUrl}/api/v1/admin/users`, formData);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to create user: ${error.response?.data?.detail || error.message}`);
    }
  }

  async provisionMonthlyCredits(userId, creditsAmount, description = 'Monthly credit provision') {
    const formData = new FormData();
    formData.append('credits_amount', creditsAmount);
    formData.append('description', description);
    formData.append('admin_api_key', this.adminApiKey);

    try {
      const response = await axios.post(`${this.apiUrl}/api/v1/admin/users/${userId}/credits`, formData);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to provision credits: ${error.response?.data?.detail || error.message}`);
    }
  }

  async getUserDetails(userId) {
    try {
      const response = await axios.get(`${this.apiUrl}/api/v1/admin/users/${userId}?admin_api_key=${this.adminApiKey}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get user details: ${error.response?.data?.detail || error.message}`);
    }
  }
}

// Usage example
const userManager = new VideoMergerUserManager('https://api.yourdomain.com', 'your-admin-secret-key');

// Create user when they subscribe
app.post('/webhook/user-subscribed', async (req, res) => {
  const { email, name, plan } = req.body;
  
  const subscriptionTier = plan === 'pro' ? 'premium' : 'basic';
  const initialCredits = plan === 'pro' ? 50000 : 20000;
  
  try {
    const result = await userManager.createUser(email, name, subscriptionTier, initialCredits);
    
    // Store the user_id and api_key in your database
    await saveUserToDatabase({
      email,
      video_merger_user_id: result.user_id,
      video_merger_api_key: result.api_key,
      subscription_tier: subscriptionTier
    });
    
    res.json({ success: true, user_id: result.user_id });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Monthly credit provisioning
app.post('/cron/provision-monthly-credits', async (req, res) => {
  const activeUsers = await getActiveSubscribers();
  
  for (const user of activeUsers) {
    const creditsAmount = user.plan === 'pro' ? 50000 : 20000;
    
    try {
      await userManager.provisionMonthlyCredits(
        user.video_merger_user_id,
        creditsAmount,
        `Monthly ${user.plan} subscription credits`
      );
    } catch (error) {
      console.error(`Failed to provision credits for user ${user.email}:`, error.message);
    }
  }
  
  res.json({ success: true });
});
```

### Python/Django Integration

```python
import requests
from django.conf import settings

class VideoMergerUserManager:
    def __init__(self):
        self.api_url = settings.VIDEO_MERGER_API_URL
        self.admin_api_key = settings.VIDEO_MERGER_ADMIN_KEY
    
    def create_user(self, email, name, subscription_tier='free', initial_credits=10000):
        data = {
            'email': email,
            'name': name,
            'subscription_tier': subscription_tier,
            'initial_credits': initial_credits,
            'admin_api_key': self.admin_api_key
        }
        
        response = requests.post(f'{self.api_url}/api/v1/admin/users', data=data)
        response.raise_for_status()
        return response.json()
    
    def provision_monthly_credits(self, user_id, credits_amount, description='Monthly credit provision'):
        data = {
            'credits_amount': credits_amount,
            'description': description,
            'admin_api_key': self.admin_api_key
        }
        
        response = requests.post(f'{self.api_url}/api/v1/admin/users/{user_id}/credits', data=data)
        response.raise_for_status()
        return response.json()

# Usage in Django views
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def handle_subscription_webhook(request):
    data = json.loads(request.body)
    
    user_manager = VideoMergerUserManager()
    
    if data['event'] == 'user.subscribed':
        result = user_manager.create_user(
            email=data['user']['email'],
            name=data['user']['name'],
            subscription_tier='premium' if data['plan'] == 'pro' else 'basic',
            initial_credits=50000 if data['plan'] == 'pro' else 20000
        )
        
        # Save to your database
        UserProfile.objects.filter(email=data['user']['email']).update(
            video_merger_user_id=result['user_id'],
            video_merger_api_key=result['api_key']
        )
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Unknown event'})
```

## 📊 Credit Tiers & Pricing

**Recommended Credit Allocation:**

| Tier | Monthly Credits | Video Processing Capacity |
|------|----------------|---------------------------|
| **Free** | 10,000 | ~166 minutes basic processing |
| **Basic** | 25,000 | ~416 minutes basic processing |
| **Premium** | 50,000 | ~833 minutes basic processing |
| **Enterprise** | 100,000+ | ~1,666+ minutes basic processing |

**Credit Costs:**
- Basic operations: 1 credit per second
- Premium AI processing: 100 credits per minute
- Logo overlay: +10% of base cost
- Transitions: +20% of base cost

## 🔒 Security Considerations

1. **Admin API Key**: Store securely, rotate regularly
2. **User API Keys**: Provide to users securely, support rotation
3. **Rate Limiting**: Built into API key system
4. **Audit Trail**: All credit transactions logged
5. **User Isolation**: Users can only access their own data

## 🎯 Ready for SaaS Integration!

The user management system is now ready for integration with your existing SaaS platform. You can:

✅ **Create users** when they subscribe
✅ **Provision credits** monthly or on-demand  
✅ **Monitor usage** through the admin endpoints
✅ **Scale automatically** with your user base
✅ **Maintain security** with proper API key management
