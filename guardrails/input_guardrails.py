"""
Input guardrails for the Slack bot to prevent abuse and ensure appropriate usage.
"""

from typing import Optional, List, Dict, Any
import re
import os


class GuardrailResult:
    """Result from a guardrail check."""
    
    def __init__(self, passed: bool, reason: Optional[str] = None, severity: str = "info"):
        self.passed = passed
        self.reason = reason
        self.severity = severity  # info, warning, critical


class InputGuardrails:
    """
    Validates user input before processing by the AI agent.
    Prevents jailbreaking, spam, and off-topic requests.
    """
    
    # Keywords that suggest jailbreak attempts
    JAILBREAK_PATTERNS = [
        r"ignore\s+(previous|all|above)\s+instructions?",
        r"forget\s+(everything|all|previous)",
        r"you\s+are\s+now",
        r"new\s+instructions?",
        r"disregard\s+(previous|all|above)",
        r"system\s+prompt",
        r"act\s+as\s+(?!.*assistant)",  # "act as X" unless it's "assistant"
        r"pretend\s+to\s+be",
        r"roleplay\s+as",
    ]
    
    # Spam/abuse patterns
    SPAM_PATTERNS = [
        r"(.)\1{20,}",  # Repeated character 20+ times
        r"^[\W_]+$",  # Only special characters
    ]
    
    @staticmethod
    def check_input(message: str) -> GuardrailResult:
        """
        Run all guardrail checks on user input.
        
        Args:
            message: The user's input message
            
        Returns:
            GuardrailResult indicating if input passed checks
        """
        # Check for jailbreak attempts
        jailbreak_result = InputGuardrails._check_jailbreak(message)
        if not jailbreak_result.passed:
            return jailbreak_result
        
        # Check for spam
        spam_result = InputGuardrails._check_spam(message)
        if not spam_result.passed:
            return spam_result
        
        # Check message length
        length_result = InputGuardrails._check_length(message)
        if not length_result.passed:
            return length_result
        
        return GuardrailResult(passed=True)
    
    @staticmethod
    def _check_jailbreak(message: str) -> GuardrailResult:
        """Check for jailbreak attempt patterns."""
        message_lower = message.lower()
        
        for pattern in InputGuardrails.JAILBREAK_PATTERNS:
            if re.search(pattern, message_lower):
                return GuardrailResult(
                    passed=False,
                    reason="Your message contains patterns that attempt to override the bot's instructions. Please rephrase your question.",
                    severity="critical"
                )
        
        return GuardrailResult(passed=True)
    
    @staticmethod
    def _check_spam(message: str) -> GuardrailResult:
        """Check for spam patterns."""
        for pattern in InputGuardrails.SPAM_PATTERNS:
            if re.search(pattern, message):
                return GuardrailResult(
                    passed=False,
                    reason="Your message appears to be spam or contains invalid content.",
                    severity="warning"
                )
        
        return GuardrailResult(passed=True)
    
    @staticmethod
    def _check_length(message: str, min_length: int = 1, max_length: int = 4000) -> GuardrailResult:
        """Check if message length is within acceptable bounds."""
        msg_length = len(message.strip())
        
        if msg_length < min_length:
            return GuardrailResult(
                passed=False,
                reason="Your message is too short. Please provide more detail.",
                severity="info"
            )
        
        if msg_length > max_length:
            return GuardrailResult(
                passed=False,
                reason=f"Your message is too long ({msg_length} characters). Please keep it under {max_length} characters.",
                severity="warning"
            )
        
        return GuardrailResult(passed=True)


class RateLimiter:
    """
    Simple rate limiter to prevent spam.
    Tracks requests per user over time windows.
    """
    
    def __init__(self, max_requests: Optional[int] = None, time_window: Optional[int] = None):
        """
        Args:
            max_requests: Maximum requests allowed in time window (default from env or 20)
            time_window: Time window in seconds (default from env or 60)
        """
        self.max_requests = max_requests or int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "20"))
        self.time_window = time_window or int(os.getenv("RATE_LIMIT_TIME_WINDOW", "60"))
        self.user_requests: Dict[str, List[float]] = {}
    
    def check_rate_limit(self, user_id: str, timestamp: float) -> GuardrailResult:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: Unique user identifier
            timestamp: Current timestamp (time.time())
            
        Returns:
            GuardrailResult indicating if request is allowed
        """
        # Initialize user if not seen before
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        
        # Clean old requests outside time window
        cutoff_time = timestamp - self.time_window
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if req_time > cutoff_time
        ]
        
        # Check if user exceeded limit
        request_count = len(self.user_requests[user_id])
        if request_count >= self.max_requests:
            return GuardrailResult(
                passed=False,
                reason=f"Rate limit exceeded. Please wait before sending more messages. (Limit: {self.max_requests} requests per {self.time_window}s)",
                severity="warning"
            )
        
        # Add current request
        self.user_requests[user_id].append(timestamp)
        
        return GuardrailResult(passed=True)


class TopicGuardrail:
    """
    Validates that user queries are relevant to available tools.
    Prevents the bot from answering completely unrelated questions.
    """
    
    @staticmethod
    def check_topic_relevance(message: str, available_topics: Optional[List[str]] = None) -> GuardrailResult:
        """
        Check if message is relevant to available topics.
        
        Args:
            message: User's message
            available_topics: List of topics the bot can handle (default from env or built-in list)
            
        Returns:
            GuardrailResult indicating if topic is relevant
        """
        if not available_topics:
            # Get from environment variable or use defaults
            topics_env = os.getenv("AVAILABLE_TOPICS", "")
            if topics_env:
                # Parse comma-separated topics from env
                available_topics = [topic.strip() for topic in topics_env.split(",")]
            else:
                # Default topics for your bot
                available_topics = [
                    "company", "office", "policy", "faq",
                    "math", "calculate", "add", "subtract", "multiply",
                    "crypto", "bitcoin", "ethereum", "price",
                    "help", "tools", "what can you do"
                ]
        
        message_lower = message.lower()
        
        # Check if any topic keyword is in the message
        has_relevant_keyword = any(
            topic in message_lower for topic in available_topics
        )
        
        # If no relevant keywords found, it might be off-topic
        # But don't be too strict - allow through and let the agent decide
        # This is more of a soft check
        
        return GuardrailResult(passed=True)  # Let the system prompt handle this


class GuardrailChain:
    """
    Chains multiple guardrails together and executes them in sequence.
    """
    
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter or RateLimiter()
    
    def check_all(self, message: str, user_id: str, timestamp: float) -> GuardrailResult:
        """
        Run all guardrail checks.
        
        Args:
            message: User's input message
            user_id: Unique user identifier
            timestamp: Current timestamp
            
        Returns:
            GuardrailResult with first failure or success
        """
        # Check rate limit first
        rate_result = self.rate_limiter.check_rate_limit(user_id, timestamp)
        if not rate_result.passed:
            return rate_result
        
        # Check input guardrails
        input_result = InputGuardrails.check_input(message)
        if not input_result.passed:
            return input_result
        
        # Check topic relevance (soft check)
        topic_result = TopicGuardrail.check_topic_relevance(message)
        if not topic_result.passed:
            return topic_result
        
        return GuardrailResult(passed=True)
