"""
Production-ready memory backends for AI chatbot
Supports multiple storage options suitable for different deployment scenarios
"""

import streamlit as st
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod


class MemoryBackend(ABC):
    """Abstract base class for memory storage backends"""
    
    @abstractmethod
    def save_conversation(self, session_id: str, messages: List[Dict]) -> bool:
        pass
    
    @abstractmethod
    def load_conversation(self, session_id: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def clear_conversation(self, session_id: str) -> bool:
        pass
    
    @abstractmethod
    def cleanup_old_conversations(self, days_old: int = 7) -> int:
        pass


class SessionStateMemory(MemoryBackend):
    """Session-based memory - ideal for single-session conversations"""
    
    def __init__(self):
        self.storage_key = "chat_conversation_memory"
        
    def save_conversation(self, session_id: str, messages: List[Dict]) -> bool:
        """Save conversation to Streamlit session state"""
        try:
            if self.storage_key not in st.session_state:
                st.session_state[self.storage_key] = {}
            
            st.session_state[self.storage_key][session_id] = {
                "messages": messages,
                "last_updated": datetime.now().isoformat(),
                "session_id": session_id
            }
            return True
        except Exception as e:
            st.error(f"Failed to save conversation: {e}")
            return False
    
    def load_conversation(self, session_id: str) -> List[Dict]:
        """Load conversation from session state"""
        try:
            if self.storage_key in st.session_state:
                session_data = st.session_state[self.storage_key].get(session_id, {})
                return session_data.get("messages", [])
            return []
        except Exception:
            return []
    
    def clear_conversation(self, session_id: str) -> bool:
        """Clear specific conversation"""
        try:
            if self.storage_key in st.session_state:
                st.session_state[self.storage_key].pop(session_id, None)
            return True
        except Exception:
            return False
    
    def cleanup_old_conversations(self, days_old: int = 7) -> int:
        """Session state doesn't need cleanup - handled automatically"""
        return 0


class DatabaseMemory(MemoryBackend):
    """Database-based memory - ideal for production with user accounts"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Create conversation table if it doesn't exist"""
        try:
            if self.db_manager and hasattr(self.db_manager, 'execute_query'):
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS chat_conversations (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    messages JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX(session_id),
                    INDEX(user_id),
                    INDEX(created_at)
                );
                """
                self.db_manager.execute_query(create_table_sql)
        except Exception as e:
            st.error(f"Failed to create conversation table: {e}")
    
    def save_conversation(self, session_id: str, messages: List[Dict]) -> bool:
        """Save conversation to database"""
        try:
            if not self.db_manager:
                return False
            
            user_id = st.session_state.get("username", "anonymous")
            
            # Upsert conversation
            upsert_sql = """
            INSERT INTO chat_conversations (session_id, user_id, messages, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (session_id) 
            DO UPDATE SET 
                messages = EXCLUDED.messages,
                updated_at = CURRENT_TIMESTAMP;
            """
            
            result = self.db_manager.execute_query(
                upsert_sql, 
                (session_id, user_id, json.dumps(messages))
            )
            return result is not None
            
        except Exception as e:
            st.error(f"Failed to save conversation to database: {e}")
            return False
    
    def load_conversation(self, session_id: str) -> List[Dict]:
        """Load conversation from database"""
        try:
            if not self.db_manager:
                return []
            
            user_id = st.session_state.get("username", "anonymous")
            
            select_sql = """
            SELECT messages FROM chat_conversations 
            WHERE session_id = %s AND user_id = %s
            ORDER BY updated_at DESC LIMIT 1;
            """
            
            result = self.db_manager.execute_query(select_sql, (session_id, user_id))
            
            if result and len(result) > 0:
                messages_json = result[0][0]
                return json.loads(messages_json) if isinstance(messages_json, str) else messages_json
            
            return []
            
        except Exception as e:
            st.error(f"Failed to load conversation from database: {e}")
            return []
    
    def clear_conversation(self, session_id: str) -> bool:
        """Clear conversation from database"""
        try:
            if not self.db_manager:
                return False
            
            user_id = st.session_state.get("username", "anonymous")
            
            delete_sql = """
            DELETE FROM chat_conversations 
            WHERE session_id = %s AND user_id = %s;
            """
            
            result = self.db_manager.execute_query(delete_sql, (session_id, user_id))
            return result is not None
            
        except Exception:
            return False
    
    def cleanup_old_conversations(self, days_old: int = 7) -> int:
        """Remove conversations older than specified days"""
        try:
            if not self.db_manager:
                return 0
            
            cleanup_sql = """
            DELETE FROM chat_conversations 
            WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
            """
            
            result = self.db_manager.execute_query(cleanup_sql, (days_old,))
            return result if result else 0
            
        except Exception:
            return 0


class RedisMemory(MemoryBackend):
    """Redis-based memory - ideal for high-scale production deployments"""
    
    def __init__(self, redis_url: str = None):
        try:
            import redis
            
            if redis_url:
                self.redis_client = redis.from_url(redis_url)
            else:
                # Try common Redis configurations
                self.redis_client = redis.Redis(
                    host=st.secrets.get("redis", {}).get("host", "localhost"),
                    port=st.secrets.get("redis", {}).get("port", 6379),
                    password=st.secrets.get("redis", {}).get("password"),
                    decode_responses=True
                )
            
            # Test connection
            self.redis_client.ping()
            self.available = True
            
        except Exception:
            self.redis_client = None
            self.available = False
    
    def _get_key(self, session_id: str) -> str:
        """Generate Redis key for conversation"""
        user_id = st.session_state.get("username", "anonymous")
        return f"chat:conversation:{user_id}:{session_id}"
    
    def save_conversation(self, session_id: str, messages: List[Dict]) -> bool:
        """Save conversation to Redis"""
        if not self.available:
            return False
        
        try:
            key = self._get_key(session_id)
            conversation_data = {
                "messages": messages,
                "last_updated": datetime.now().isoformat(),
                "session_id": session_id,
                "user_id": st.session_state.get("username", "anonymous")
            }
            
            # Save with TTL (expire after 30 days)
            self.redis_client.setex(
                key, 
                timedelta(days=30), 
                json.dumps(conversation_data)
            )
            return True
            
        except Exception as e:
            st.error(f"Failed to save to Redis: {e}")
            return False
    
    def load_conversation(self, session_id: str) -> List[Dict]:
        """Load conversation from Redis"""
        if not self.available:
            return []
        
        try:
            key = self._get_key(session_id)
            data = self.redis_client.get(key)
            
            if data:
                conversation_data = json.loads(data)
                return conversation_data.get("messages", [])
            
            return []
            
        except Exception:
            return []
    
    def clear_conversation(self, session_id: str) -> bool:
        """Clear conversation from Redis"""
        if not self.available:
            return False
        
        try:
            key = self._get_key(session_id)
            self.redis_client.delete(key)
            return True
        except Exception:
            return False
    
    def cleanup_old_conversations(self, days_old: int = 7) -> int:
        """Redis handles TTL automatically, but we can clean up manually"""
        if not self.available:
            return 0
        
        try:
            user_id = st.session_state.get("username", "anonymous")
            pattern = f"chat:conversation:{user_id}:*"
            keys = self.redis_client.keys(pattern)
            
            cleaned = 0
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            for key in keys:
                try:
                    data = self.redis_client.get(key)
                    if data:
                        conversation_data = json.loads(data)
                        last_updated = datetime.fromisoformat(
                            conversation_data.get("last_updated", "")
                        )
                        
                        if last_updated < cutoff_date:
                            self.redis_client.delete(key)
                            cleaned += 1
                except Exception:
                    continue
            
            return cleaned
            
        except Exception:
            return 0


class MemoryManagerFactory:
    """Factory to create appropriate memory backend based on deployment context"""
    
    @staticmethod
    def create_memory_backend(
        storage_type: str = "auto", 
        db_manager=None, 
        redis_url: str = None
    ) -> MemoryBackend:
        """
        Create appropriate memory backend
        
        Args:
            storage_type: "auto", "session", "database", "redis", "file"
            db_manager: Database manager instance (for database storage)
            redis_url: Redis connection URL (for Redis storage)
        """
        
        if storage_type == "auto":
            storage_type = MemoryManagerFactory._detect_best_storage(db_manager)
        
        if storage_type == "session":
            return SessionStateMemory()
        
        elif storage_type == "database":
            if db_manager:
                return DatabaseMemory(db_manager)
            else:
                st.warning("Database not available, falling back to session storage")
                return SessionStateMemory()
        
        elif storage_type == "redis":
            redis_backend = RedisMemory(redis_url)
            if redis_backend.available:
                return redis_backend
            else:
                st.warning("Redis not available, falling back to session storage")
                return SessionStateMemory()
        
        else:  # Default to session storage
            return SessionStateMemory()
    
    @staticmethod
    def _detect_best_storage(db_manager=None) -> str:
        """Auto-detect best storage option based on available resources"""
        
        # Check if Redis is available
        try:
            import redis
            # Try to connect to Redis
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            return "redis"
        except:
            pass
        
        # Check if database is available
        if db_manager and hasattr(db_manager, 'execute_query'):
            return "database"
        
        # Default to session storage
        return "session"


class EnhancedConversationMemory:
    """Enhanced conversation memory with production-ready features"""
    
    def __init__(
        self, 
        session_id: str = None, 
        memory_size: int = 10,
        storage_type: str = "auto",
        db_manager=None,
        redis_url: str = None
    ):
        self.session_id = session_id or self._generate_session_id()
        self.memory_size = memory_size
        
        # Initialize storage backend
        self.backend = MemoryManagerFactory.create_memory_backend(
            storage_type, db_manager, redis_url
        )
        
        # Load existing conversation
        self.messages = self.backend.load_conversation(self.session_id)
        
        # Ensure messages don't exceed memory size
        if len(self.messages) > self.memory_size * 2:  # 2 messages per exchange
            self.messages = self.messages[-(self.memory_size * 2):]
            self._save()
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        username = st.session_state.get("username", "anonymous")
        timestamp = datetime.now().isoformat()
        session_data = f"{username}_{timestamp}"
        return hashlib.md5(session_data.encode()).hexdigest()[:12]
    
    def add_message(self, message: str, message_type: str = "human"):
        """Add message to conversation"""
        self.messages.append({
            "type": message_type,
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Maintain memory size limit
        if len(self.messages) > self.memory_size * 2:
            self.messages = self.messages[-(self.memory_size * 2):]
        
        self._save()
    
    def get_conversation_history(self) -> List[Dict]:
        """Get full conversation history"""
        return self.messages.copy()
    
    def get_context_summary(self) -> str:
        """Generate context summary"""
        if not self.messages:
            return "No previous conversation context."
        
        # Analyze recent human messages for topics
        topics = []
        for msg in self.messages[-6:]:  # Last 6 messages
            if msg["type"] == "human":
                content = msg["content"].lower()
                if "energy" in content:
                    topics.append("energy analysis")
                elif "co2" in content or "carbon" in content:
                    topics.append("carbon emissions")
                elif "class" in content or "classification" in content:
                    topics.append("building classification")
                elif "chart" in content or "plot" in content:
                    topics.append("data visualization")
        
        if topics:
            unique_topics = list(set(topics))
            return f"Recent topics: {', '.join(unique_topics)}"
        
        return "General building analytics discussion"
    
    def clear_conversation(self):
        """Clear conversation history"""
        self.messages = []
        self.backend.clear_conversation(self.session_id)
    
    def _save(self):
        """Save conversation using backend"""
        self.backend.save_conversation(self.session_id, self.messages)
    
    def cleanup_old_conversations(self, days_old: int = 7) -> int:
        """Clean up old conversations"""
        return self.backend.cleanup_old_conversations(days_old)


def get_memory_status_info() -> Dict[str, Any]:
    """Get information about memory backend status"""
    
    # Check available backends
    backends = {
        "session": True,  # Always available
        "database": False,
        "redis": False
    }
    
    # Check database availability
    try:
        from utils.db_manager import get_database_manager
        db_manager, _, db_available = get_database_manager()
        backends["database"] = db_available and db_manager is not None
    except:
        pass
    
    # Check Redis availability
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        backends["redis"] = True
    except:
        pass
    
    # Determine recommended backend
    if backends["redis"]:
        recommended = "redis"
        reason = "High-performance caching for scalable deployments"
    elif backends["database"]:
        recommended = "database"
        reason = "Persistent storage with user account integration"
    else:
        recommended = "session"
        reason = "Simple session-based storage (not persistent)"
    
    return {
        "available_backends": backends,
        "recommended": recommended,
        "recommendation_reason": reason,
        "current_storage": recommended
    }
