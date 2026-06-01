# AI Assistant Memory Configuration Guide

## 🚀 Production Deployment Memory Options

The AI Assistant now supports multiple memory backends suitable for different deployment scenarios:

### 1. **Session Memory (Default)** 
- **Best for:** Single-user sessions, development, simple deployments
- **Pros:** No setup required, works instantly
- **Cons:** Memory lost on browser refresh
- **Configuration:** Automatic (no config needed)

### 2. **Database Memory (Recommended for Production)**
- **Best for:** Multi-user production with user accounts
- **Pros:** Persistent across sessions, user-specific, GDPR compliant
- **Cons:** Requires database setup
- **Configuration:** 
```python
# In your app configuration
MEMORY_STORAGE = "database"
```

### 3. **Redis Memory (Best for High-Scale)**
- **Best for:** High-traffic, multi-server deployments
- **Pros:** Fast, scalable, automatic cleanup
- **Cons:** Requires Redis server
- **Configuration:**
```python
# In secrets.toml or environment
[redis]
host = "your-redis-host"
port = 6379
password = "your-password"
```

## 📊 Memory Backend Comparison

| Feature | Session | Database | Redis |
|---------|---------|----------|-------|
| **Persistence** | Browser only | Permanent | TTL-based |
| **Multi-user** | No | Yes | Yes |
| **Performance** | Fast | Good | Very Fast |
| **Setup Complexity** | None | Medium | Medium |
| **Cost** | Free | DB costs | Redis costs |
| **Privacy** | Session-local | User-isolated | User-isolated |
| **Cleanup** | Automatic | Manual/Scheduled | Automatic TTL |

## 🛠️ Deployment Recommendations

### **Heroku/Railway (Platform-as-a-Service)**
```python
# Recommended: Database Memory
# Redis available as add-on
MEMORY_STORAGE = "auto"  # Auto-detects available options
```

### **Docker/Kubernetes**
```python
# Recommended: Redis Memory
# Easy to scale with Redis cluster
MEMORY_STORAGE = "redis"
```

### **Serverless (Vercel/Netlify)**
```python
# Required: Session Memory only
# Serverless doesn't persist files/connections
MEMORY_STORAGE = "session"
```

### **Traditional VPS/Server**
```python
# Recommended: Database Memory
# Full control over storage
MEMORY_STORAGE = "database"
```

## 🔧 Environment Variables

```bash
# Optional: Force specific memory backend
CHAT_MEMORY_BACKEND=auto|session|database|redis

# Redis configuration (if using Redis)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-password

# Database configuration (if using database)
DATABASE_URL=postgresql://user:pass@host/dbname
```

## 📋 Privacy & GDPR Compliance

### **User Data Handling:**
- All memory backends support user-specific storage
- Messages are encrypted in database/Redis
- Automatic cleanup of old conversations
- Clear user data on request

### **Data Retention:**
```python
# Automatic cleanup configuration
MEMORY_CLEANUP_DAYS = 30  # Delete conversations after 30 days
MEMORY_MAX_MESSAGES = 100  # Max messages per conversation
```

## 🚨 Security Considerations

1. **Database Memory:**
   - Use encrypted connections (SSL)
   - Implement proper user access controls
   - Regular backups

2. **Redis Memory:**
   - Use password authentication
   - Enable SSL/TLS
   - Network isolation

3. **Session Memory:**
   - No persistence = no breach risk
   - But also no user experience continuity

## 🧪 Testing Your Setup

```python
# Test memory backend functionality
from utils.memory_backends import get_memory_status_info

# Check what's available
status = get_memory_status_info()
print(f"Available backends: {status['available_backends']}")
print(f"Recommended: {status['recommended']}")
```

## 📈 Monitoring & Maintenance

### **Database Monitoring:**
```sql
-- Check conversation table size
SELECT COUNT(*) as total_conversations, 
       COUNT(DISTINCT user_id) as unique_users
FROM chat_conversations;

-- Cleanup old conversations (run weekly)
DELETE FROM chat_conversations 
WHERE created_at < NOW() - INTERVAL '30 days';
```

### **Redis Monitoring:**
```bash
# Check Redis memory usage
redis-cli info memory

# Check conversation keys
redis-cli keys "chat:conversation:*" | wc -l
```

## 🎯 Quick Start Commands

```bash
# 1. Enable database memory
echo "CHAT_MEMORY_BACKEND=database" >> .env

# 2. Enable Redis memory with Docker
docker run -d --name redis -p 6379:6379 redis:alpine
echo "CHAT_MEMORY_BACKEND=redis" >> .env

# 3. Auto-detect best option
echo "CHAT_MEMORY_BACKEND=auto" >> .env
```

## 💡 Best Practices

1. **Start Simple:** Use session memory for development
2. **Scale Gradually:** Move to database memory for production
3. **Monitor Usage:** Track conversation volume and cleanup needs
4. **Plan for Growth:** Consider Redis for high-traffic scenarios
5. **Test Failover:** Ensure graceful fallback to session memory
