"""
Token counting to prevent token limit errors.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class TokenCounter:
    """Fast token estimation."""
    
    def __init__(self):
        self._truncation_count = 0
        logger.info("TokenCounter initialized")
    
    def count_tokens_fast(self, content: Any) -> int:
        """Fast token counting (4 chars ≈ 1 token)."""
        text = str(content) if not isinstance(content, str) else content
        return len(text) // 4
    
    def truncate_to_limit(self, data: List[Dict], max_tokens: int) -> List[Dict]:
        """Truncate list to stay under token limit."""
        if not data:
            return data
        
        truncated = []
        total_tokens = 0
        
        for item in data:
            item_tokens = self.count_tokens_fast(item)
            
            if total_tokens + item_tokens > max_tokens:
                self._truncation_count += 1
                logger.warning(
                    f"✂️ Truncated at {len(truncated)}/{len(data)} items "
                    f"(~{total_tokens:,} tokens, limit: {max_tokens:,})"
                )
                break
            
            truncated.append(item)
            total_tokens += item_tokens
        
        return truncated
    
    def get_stats(self):
        """Get token counter statistics."""
        return {
            "total_truncations": self._truncation_count
        }


# Global singleton
token_counter = TokenCounter()
