# Future Architecture: Multi-Provider & Multi-Key Rotation

**Status**: Future Enhancement (Post V2.1)  
**Priority**: MEDIUM-HIGH (enables scaling free tier usage)  
**Complexity**: HIGH (requires significant orchestration changes)

---

## 🎯 Vision: Distributed Rate Limit Management

### The Problem We're Solving

**Current Limitation**:
- Single Groq API key → 30K TPM (tokens per minute)
- Long video (30K words) × 10 patterns = 400K tokens needed
- Result: Rate limit failures, slow processing

**The Solution**:
- **Multiple API keys** from same provider (Groq)
- **Multiple providers** with same model families (Groq, Together, Fireworks)
- **Intelligent rotation** to distribute load
- **Stay on free tiers** while achieving higher throughput

### The Math: Why This Works

**Scenario 1: Single Groq Key**
- Rate limit: 30K TPM
- Video needs: 400K tokens
- Time: ~13 minutes (sequential with waits)
- Failures: ~50% on burst patterns

**Scenario 2: 4 Groq Keys (Rotation)**
- Combined rate limit: 120K TPM (4 × 30K)
- Video needs: 400K tokens  
- Time: ~3-4 minutes (4x faster)
- Failures: Near 0% (distributed load)

**Scenario 3: Mixed Providers (Groq + Together + Fireworks)**
- Groq: 30K TPM (llama-4-scout)
- Together: 60K TPM (llama-3.1-8b-instruct-turbo, free tier)
- Fireworks: 60K TPM (llama-v3p1-8b-instruct, free tier)
- **Combined**: 150K TPM
- **Time**: ~2-3 minutes
- **Redundancy**: If one provider down, others work

---

## 🏗️ Architecture Design

### Phase 1: Multi-Key Support (Same Provider)

**Configuration Structure** (`config.yaml`):

```yaml
providers:
  groq:
    enabled: true
    model: llama-4-scout
    rate_limits:
      tokens_per_minute: 30000
      requests_per_minute: 30
    
    # Multiple API keys for rotation
    api_keys:
      - key: "gsk_key1..."
        name: "groq-account-1"
        priority: 1
        enabled: true
      
      - key: "gsk_key2..."
        name: "groq-account-2"
        priority: 1
        enabled: true
      
      - key: "gsk_key3..."
        name: "groq-backup"
        priority: 2  # Use as fallback
        enabled: true
    
    rotation_strategy: "round_robin"  # or "least_recently_used" or "random"
```

**Key Rotation Logic**:

```python
class APIKeyRotator:
    """Rotates API keys to distribute rate limits."""
    
    def __init__(self, provider_config: dict):
        self.keys = [k for k in provider_config['api_keys'] if k['enabled']]
        self.strategy = provider_config['rotation_strategy']
        self.current_index = 0
        self.key_usage = {k['name']: {'calls': 0, 'last_used': None} for k in self.keys}
    
    def get_next_key(self) -> str:
        """Get next API key based on rotation strategy."""
        if self.strategy == "round_robin":
            key = self.keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.keys)
            return key['key']
        
        elif self.strategy == "least_recently_used":
            # Find key with oldest last_used timestamp
            sorted_keys = sorted(
                self.keys, 
                key=lambda k: self.key_usage[k['name']]['last_used'] or 0
            )
            return sorted_keys[0]['key']
        
        elif self.strategy == "random":
            import random
            return random.choice(self.keys)['key']
    
    def mark_key_used(self, key_name: str):
        """Update usage tracking."""
        self.key_usage[key_name]['calls'] += 1
        self.key_usage[key_name]['last_used'] = time.time()
    
    def mark_key_rate_limited(self, key_name: str, retry_after: int):
        """Temporarily disable rate-limited key."""
        # Find key and disable for retry_after seconds
        for key in self.keys:
            if key['name'] == key_name:
                key['enabled'] = False
                # Schedule re-enable after retry_after
                threading.Timer(retry_after, self._re_enable_key, [key_name]).start()
    
    def _re_enable_key(self, key_name: str):
        """Re-enable key after rate limit cooldown."""
        for key in self.keys:
            if key['name'] == key_name:
                key['enabled'] = True
```

---

### Phase 2: Multi-Provider Support (Different Services)

**Extended Configuration**:

```yaml
providers:
  groq:
    enabled: true
    model: llama-4-scout
    rate_limits:
      tokens_per_minute: 30000
      requests_per_minute: 30
    api_keys:
      - key: "gsk_..."
        name: "groq-1"
    priority: 1  # Try first
  
  together:
    enabled: true
    model: meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
    rate_limits:
      tokens_per_minute: 60000
      requests_per_minute: 60
    api_keys:
      - key: "together_..."
        name: "together-1"
    priority: 2  # Try second
  
  fireworks:
    enabled: true
    model: accounts/fireworks/models/llama-v3p1-8b-instruct
    rate_limits:
      tokens_per_minute: 60000
      requests_per_minute: 60
    api_keys:
      - key: "fw_..."
        name: "fireworks-1"
    priority: 3  # Try third

# Global rotation strategy
provider_rotation:
  strategy: "priority_weighted"  # Prefer higher priority, fallback to others
  enable_fallback: true           # If primary fails, try others
  distribute_load: true           # Spread calls across all providers
```

**Provider Manager**:

```python
class ProviderManager:
    """Manages multiple providers with intelligent routing."""
    
    def __init__(self, config: dict):
        self.providers = self._initialize_providers(config)
        self.strategy = config['provider_rotation']['strategy']
        self.enable_fallback = config['provider_rotation']['enable_fallback']
        self.distribute_load = config['provider_rotation']['distribute_load']
    
    def _initialize_providers(self, config: dict):
        """Create provider instances with key rotators."""
        providers = []
        for name, pconfig in config['providers'].items():
            if pconfig['enabled']:
                providers.append({
                    'name': name,
                    'model': pconfig['model'],
                    'rate_limits': pconfig['rate_limits'],
                    'key_rotator': APIKeyRotator(pconfig),
                    'priority': pconfig.get('priority', 999),
                    'client': self._create_client(name, pconfig)
                })
        return sorted(providers, key=lambda p: p['priority'])
    
    def get_provider_for_request(self, token_estimate: int) -> dict:
        """Select optimal provider for request."""
        
        if self.strategy == "priority_weighted":
            # Try providers in priority order
            for provider in self.providers:
                if self._can_handle_request(provider, token_estimate):
                    return provider
            
            # Fallback to any available
            if self.enable_fallback:
                return self.providers[0]
        
        elif self.strategy == "load_balanced":
            # Distribute across all providers
            least_loaded = min(
                self.providers,
                key=lambda p: p['key_rotator'].get_total_usage()
            )
            return least_loaded
        
        elif self.strategy == "cheapest_first":
            # Use free tier providers first, paid as backup
            free_providers = [p for p in self.providers if p.get('cost') == 0]
            return free_providers[0] if free_providers else self.providers[0]
    
    def _can_handle_request(self, provider: dict, tokens: int) -> bool:
        """Check if provider has capacity."""
        rotator = provider['key_rotator']
        
        # Check if any keys available (not rate limited)
        available_keys = [k for k in rotator.keys if k['enabled']]
        if not available_keys:
            return False
        
        # Check token limit
        tpm_limit = provider['rate_limits']['tokens_per_minute']
        recent_usage = rotator.get_recent_usage(window=60)
        
        return (recent_usage + tokens) < tpm_limit
    
    def execute_with_failover(self, pattern: str, input_data: str, 
                               model: str = None) -> dict:
        """Execute pattern with automatic provider failover."""
        
        token_estimate = estimate_tokens(input_data)
        
        # Try providers in order
        for provider in self.providers:
            try:
                # Get API key from rotator
                api_key = provider['key_rotator'].get_next_key()
                
                # Execute request
                result = self._execute_request(
                    provider=provider,
                    api_key=api_key,
                    pattern=pattern,
                    input_data=input_data,
                    model=model or provider['model']
                )
                
                # Success! Track usage
                provider['key_rotator'].mark_key_used(api_key)
                return result
            
            except RateLimitError as e:
                # Mark key as rate limited
                provider['key_rotator'].mark_key_rate_limited(
                    api_key, 
                    retry_after=e.retry_after
                )
                
                # Try next provider if fallback enabled
                if self.enable_fallback:
                    continue
                else:
                    raise
            
            except Exception as e:
                # Other errors, try next provider
                if self.enable_fallback:
                    continue
                else:
                    raise
        
        # All providers failed
        raise Exception("All providers exhausted or rate limited")
```

---

### Phase 3: Parallel Execution with Multi-Provider

**Goal**: Process multiple chunks simultaneously across providers

```python
class ParallelOrchestrator:
    """Process patterns in parallel across multiple providers."""
    
    def __init__(self, provider_manager: ProviderManager):
        self.provider_manager = provider_manager
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    
    def process_pattern_parallel(self, pattern: str, chunks: List[str]) -> List[dict]:
        """Process all chunks of a pattern in parallel."""
        
        # Submit all chunks to thread pool
        futures = []
        for i, chunk in enumerate(chunks):
            future = self.executor.submit(
                self._process_chunk_with_provider,
                pattern, chunk, i
            )
            futures.append(future)
        
        # Collect results as they complete
        results = []
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                # Handle failure
                results.append({"success": False, "error": str(e)})
        
        return sorted(results, key=lambda r: r['chunk_index'])
    
    def _process_chunk_with_provider(self, pattern: str, chunk: str, 
                                     chunk_index: int) -> dict:
        """Process single chunk using optimal provider."""
        
        # Provider manager handles selection and failover
        result = self.provider_manager.execute_with_failover(
            pattern=pattern,
            input_data=chunk
        )
        
        result['chunk_index'] = chunk_index
        return result
```

**Performance Example**:

```
Scenario: 10 chunks, 3 providers (Groq, Together, Fireworks)

Sequential (current):
  Chunk 1 → Groq → 8s
  Chunk 2 → Groq → 8s
  ...
  Total: 80s

Parallel with multi-provider:
  Chunk 1,2,3 → Groq (parallel) → 8s
  Chunk 4,5,6 → Together (parallel) → 8s
  Chunk 7,8,9 → Fireworks (parallel) → 8s
  Chunk 10 → Groq → 8s
  Total: ~32s (2.5x faster!)
```

---

## 🛠️ Implementation Plan

### Stage 1: Single Provider, Multiple Keys (2-3 days)
**Goal**: Rotate between multiple Groq API keys

**Tasks**:
1. Add `api_keys` array to config schema
2. Implement `APIKeyRotator` class
3. Update `RateLimitHandler` to use rotator
4. Test with 2-3 Groq keys
5. Document key rotation in README

**Expected Improvement**: 2-3x throughput

---

### Stage 2: Multi-Provider Support (3-5 days)
**Goal**: Support Groq + Together + Fireworks

**Tasks**:
1. Add provider abstraction layer
2. Implement `ProviderManager` class
3. Add provider-specific clients (Groq, Together, Fireworks)
4. Test failover between providers
5. Update config schema with provider priorities

**Expected Improvement**: 4-5x throughput, better redundancy

---

### Stage 3: Parallel Execution (3-5 days)
**Goal**: Process chunks simultaneously across providers

**Tasks**:
1. Implement `ParallelOrchestrator` class
2. Add thread pool executor
3. Ensure thread-safe key rotation
4. Test with 10-chunk video
5. Benchmark performance improvement

**Expected Improvement**: 2-3x faster on long videos

---

### Stage 4: Advanced Features (Optional, 5-7 days)
**Goal**: Smart load balancing and monitoring

**Tasks**:
1. Usage analytics per provider/key
2. Automatic key health checking
3. Cost tracking (if using paid tiers)
4. Dashboard for monitoring key usage
5. Automatic key disabling on repeated failures

---

## 📝 Configuration Examples

### Example 1: Personal Setup (Multiple Groq Accounts)

```yaml
providers:
  groq:
    enabled: true
    model: llama-4-scout
    api_keys:
      - key: "gsk_personal_..."
        name: "groq-personal"
      - key: "gsk_work_..."
        name: "groq-work"
      - key: "gsk_test_..."
        name: "groq-test"
    rotation_strategy: "round_robin"
```

### Example 2: Free Tier Maximization

```yaml
providers:
  groq:
    enabled: true
    model: llama-4-scout
    priority: 1
    api_keys:
      - key: "gsk_..."
        name: "groq-free"
  
  together:
    enabled: true
    model: meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
    priority: 2
    api_keys:
      - key: "together_..."
        name: "together-free"
  
  fireworks:
    enabled: true
    model: accounts/fireworks/models/llama-v3p1-8b-instruct
    priority: 3
    api_keys:
      - key: "fw_..."
        name: "fireworks-free"

provider_rotation:
  strategy: "priority_weighted"
  enable_fallback: true
  distribute_load: true
```

### Example 3: Enterprise Setup (Mixed Free + Paid)

```yaml
providers:
  groq_paid:
    enabled: true
    model: llama-70b
    priority: 1
    cost_per_1k_tokens: 0.0005
    api_keys:
      - key: "gsk_paid_..."
        name: "groq-enterprise"
  
  groq_free:
    enabled: true
    model: llama-4-scout
    priority: 2
    cost_per_1k_tokens: 0.0
    api_keys:
      - key: "gsk_free_..."
        name: "groq-backup"

provider_rotation:
  strategy: "cheapest_first"  # Use free tier first, paid as backup
  enable_fallback: true
```

---

## 🎯 Success Metrics

### Before (Single Groq Key)
- Throughput: 30K TPM
- Long video (30K words, 400K tokens): ~13 min
- Failure rate: ~50% on burst patterns
- No redundancy

### After Stage 1 (4 Groq Keys)
- Throughput: 120K TPM
- Same video: ~3-4 min (4x faster)
- Failure rate: ~10% (distributed load)
- Basic redundancy

### After Stage 2 (Multi-Provider)
- Throughput: 150K+ TPM
- Same video: ~2-3 min
- Failure rate: <5% (multiple providers)
- Full redundancy

### After Stage 3 (Parallel)
- Throughput: 150K+ TPM (same)
- Same video: ~1-2 min (parallel chunks)
- Failure rate: <5%
- Full redundancy + speed

---

## 🚧 Technical Challenges

### Challenge 1: API Key Security
**Problem**: Multiple keys in config file  
**Solutions**:
- Environment variables: `GROQ_KEY_1`, `GROQ_KEY_2`, etc.
- Encrypted config file
- Key management service (e.g., AWS Secrets Manager)

### Challenge 2: Provider API Differences
**Problem**: Each provider has different API format  
**Solutions**:
- Abstraction layer (ProviderClient interface)
- Adapter pattern for each provider
- Unified response format

### Challenge 3: Rate Limit Tracking Accuracy
**Problem**: API limits are per-minute, hard to track precisely  
**Solutions**:
- Sliding window counters
- Token bucket algorithm
- Conservative estimates (use 90% of limit)

### Challenge 4: Cost Management
**Problem**: Accidentally using paid tier when free available  
**Solutions**:
- Cost tracking per provider
- Spending limits in config
- Alerts on unexpected costs

---

## 📚 Resources

### Free Tier Providers (as of Dec 2025)

| Provider | Model | Free TPM | Free RPM | Notes |
|----------|-------|----------|----------|-------|
| Groq | llama-4-scout | 30K | ~30 | Fastest inference |
| Together | llama-3.1-8b-instruct-turbo | 60K | 60 | Good throughput |
| Fireworks | llama-v3p1-8b-instruct | 60K | 60 | Reliable |
| Cerebras | llama-3.3-70b | Unknown | Unknown | New, evaluate |
| Hyperbolic | llama-3.1-8b | Unknown | Unknown | New, evaluate |

### Provider Documentation
- Groq: https://console.groq.com/docs
- Together: https://docs.together.ai/
- Fireworks: https://docs.fireworks.ai/

---

## 🎯 Recommendation

**Priority**: Implement AFTER V2.1 (after fixing current rate limiting)

**Rationale**:
1. Fix single-key rate limiting first (V2.1)
2. Validate architecture works reliably
3. Then scale horizontally with multi-key/provider (V2.2)

**Why Not Now**:
- Current single-key approach still broken (50% failure)
- Multi-key adds complexity, harder to debug
- Better to have solid foundation first

**Timeline**:
- V2.1 (Weeks 1-2): Fix single-key rate limiting
- V2.2 (Weeks 3-4): Add multi-key rotation (Stage 1)
- V2.3 (Weeks 5-6): Add multi-provider (Stage 2)
- V2.4 (Weeks 7-8): Add parallel execution (Stage 3)

---

## ✅ Action Items

### For Current Session (Documentation)
- [x] Document multi-provider architecture vision
- [x] Design API key rotation system
- [x] Design provider manager system
- [x] Create configuration examples
- [x] Define implementation stages

### For V2.2 (Future Implementation)
- [ ] Create `lib/provider_manager.py`
- [ ] Create `lib/api_key_rotator.py`
- [ ] Update `config.yaml` schema
- [ ] Add provider abstraction layer
- [ ] Implement key rotation logic
- [ ] Add tests for rotation
- [ ] Document setup for multiple keys

---

**Document Status**: ✅ COMPLETE  
**Next Review**: After V2.1 release  
**Owner**: Future developer

---

**TL;DR**: Use multiple free API keys + multiple providers to distribute rate limits and achieve 4-5x higher throughput while staying on free tiers. Implement after V2.1 stabilizes single-key approach.
