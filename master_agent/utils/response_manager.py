"""
Central response management with automatic token limit enforcement.
"""
import json
import logging
from typing import Any, Dict


logger = logging.getLogger(__name__)



class ResponseManager:
    """Centralized response truncation."""
    
    MAX_RESPONSE_TOKENS = 120000  # Increased for conversations
    MAX_ARRAY_ITEMS = 300
    MAX_TRANSCRIPT_TURNS = 300
    MAX_SESSION_RESULTS = 300
    
    def __init__(self):
        self._truncation_count = 0

    # ✅ BYPASS FLAG (class attribute)
    CONVERSATION_BYPASS = True  # Set False after implementing chunks

    def prepare_response(self, data: Any, tool_name: str = "unknown", max_items: int = None) -> str:
        """Token-safe response with conversation bypass."""
        
        # 🔥 BYPASS for conversation tools (INSTANT FIX)
        if self.CONVERSATION_BYPASS and (
            tool_name.startswith('df_session_') or 
            tool_name.startswith('df_conversation_')
        ):
            logger.info(f"[BYPASS] Full data allowed for {tool_name}")
            return json.dumps(data, indent=2)
        
        # Your existing truncation logic (unchanged)
        try:
            was_truncated = False
            
            # Apply truncation based on data type
            if isinstance(data, dict):
                for key, value in list(data.items()):
                    if isinstance(value, list):
                        # Determine max items based on context
                        if max_items:
                            limit = max_items
                        elif "transcript" in key.lower():
                            limit = self.MAX_TRANSCRIPT_TURNS
                        elif "session" in key.lower():
                            limit = self.MAX_SESSION_RESULTS
                        else:
                            limit = self.MAX_ARRAY_ITEMS
                        
                        if len(value) > limit:
                            original_count = len(value)
                            data[key] = value[:limit]
                            data[f"{key}_truncated"] = True
                            data[f"{key}_original_count"] = original_count
                            was_truncated = True
                            self._truncation_count += 1
                            logger.warning(
                                f"✂️ [{tool_name}] Truncated {key}: {original_count} → {limit} items"
                            )
            
            # Add truncation note if needed
            if was_truncated and isinstance(data, dict):
                data["_note"] = "⚠️ Response truncated to prevent token overflow. Use filters or query BigQuery directly for complete data."
            
            # Convert to JSON
            result = json.dumps(data, indent=2, default=str)
            
            # Final safety check
            estimated_tokens = len(result) // 4
            if estimated_tokens > self.MAX_RESPONSE_TOKENS:
                logger.error(f"❌ [{tool_name}] Response too large ({estimated_tokens:,} tokens), emergency truncation")
                return self._emergency_truncate(data, tool_name)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [{tool_name}] Response prep failed: {e}")
            return json.dumps({"error": "Response processing failed", "details": str(e)}, indent=2)
    
    def _emergency_truncate(self, data: Any, tool_name: str) -> str:
        """Last resort truncation."""
        summary = {
            "tool": tool_name,
            "status": "response_too_large",
            "note": "⚠️ Response exceeded maximum size even after truncation. Showing summary only.",
            "data_type": type(data).__name__,
        }
        
        if isinstance(data, dict):
            summary["keys"] = list(data.keys())[:10]
            summary["sample"] = {k: str(v)[:100] for k, v in list(data.items())[:3]}
        elif isinstance(data, list):
            summary["total_items"] = len(data)
        
        return json.dumps(summary, indent=2)
    
    def get_stats(self):
        """Get statistics."""
        return {
            "total_truncations": self._truncation_count,
            "limits": {
                "max_response_tokens": self.MAX_RESPONSE_TOKENS,
                "max_array_items": self.MAX_ARRAY_ITEMS,
                "max_transcript_turns": self.MAX_TRANSCRIPT_TURNS,
                "max_session_results": self.MAX_SESSION_RESULTS
            }
        }


# Global singleton
response_manager = ResponseManager()
