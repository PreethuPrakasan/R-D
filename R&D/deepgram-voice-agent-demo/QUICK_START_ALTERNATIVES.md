# Quick Start: Using Cheaper LLM Alternatives

## 🚀 Fastest Way: Use Groq (Recommended)

**Groq is 10x cheaper than OpenAI and much faster!**

### Step 1: Get Groq API Key (Free Credits Available)
1. Go to https://console.groq.com
2. Sign up (free)
3. Get your API key
4. **Note:** You may need to configure this in Deepgram's dashboard (check Deepgram docs)

### Step 2: Use URL Parameters
Simply add these parameters to your URL:

```
http://localhost:3000/agent?think_provider=groq&think_model=llama-3.1-70b-versatile
```

### Available Groq Models:
- `llama-3.1-70b-versatile` - Best quality (recommended)
- `mixtral-8x7b-32768` - Faster, cheaper
- `gemma2-9b-it` - Fastest, cheapest

---

## 🎯 Other Quick Options

### Option 2: Google Gemini Flash (Cheapest Google Option)
```
http://localhost:3000/agent?think_provider=google&think_model=gemini-flash
```

### Option 3: Anthropic Claude Haiku (Cheaper Claude)
```
http://localhost:3000/agent?think_provider=anthropic&think_model=claude-haiku-3
```

### Option 4: Together.ai (Cheapest Overall)
```
http://localhost:3000/agent?think_provider=together&think_model=meta-llama/Llama-3-70b-chat-hf
```

---

## 💡 Change Default in Code

If you want to change the default provider (so you don't need URL params), edit `app/lib/constants.ts`:

```typescript
// Change this line:
const DEFAULT_LLM_PROVIDER = LLM_PROVIDERS.GROQ; // or ANTHROPIC, GOOGLE, etc.
```

---

## 📊 Cost Comparison

| Provider | Cost per 1M tokens | Speed | Quality |
|----------|-------------------|-------|---------|
| **Groq** | $0.27 | ⚡⚡⚡ Fastest | ⭐⭐⭐⭐ |
| **Gemini Flash** | $0.075 | ⚡⚡⚡ Very Fast | ⭐⭐⭐ |
| **Claude Haiku** | $0.25 | ⚡⚡ Fast | ⭐⭐⭐⭐ |
| **Together.ai** | $0.10 | ⚡ Fast | ⭐⭐⭐⭐ |
| **OpenAI GPT-4o** | $2.50 | ⚡ Medium | ⭐⭐⭐⭐⭐ |

**Groq is recommended** because it's:
- ✅ Very cheap
- ✅ Extremely fast (real-time)
- ✅ Good quality
- ✅ Easy to use

---

## 🔍 Verify Provider Support

**Important:** Check Deepgram's documentation to confirm which providers are actually supported:
- https://developers.deepgram.com/docs
- Some providers may need API keys configured on Deepgram's backend

---

## 🎉 That's It!

Just add the URL parameters and you're using a cheaper alternative! The voice agent will work exactly the same, just with a different LLM backend.


