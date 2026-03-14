"""
Aureus Smart Script Engine v3.0
================================
Scripts are STRICTLY written for 15-20 second videos:
  - Exactly 3 sentences
  - ~55-65 words total
  - Calm speaking pace = 15-20 seconds of audio

THREE content buckets, randomly chosen each run:
  🔴 NEWS     (40%) — real RSS headlines from BBC/TechCrunch/Guardian/NASA
  💚 SOCIAL   (35%) — 25+ awareness causes (mental health, climate, etc.)
  🧠 KNOWLEDGE(25%) — 25+ fascinating fact domains (science, history, etc.)

Script chain: Groq LLaMA-3.3 → OpenAI → built-in fallback
RSS fetched with stdlib urllib — no extra libraries needed.
"""

import logging, json, random, os, re, xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from typing import Optional

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Timing constants — single source of truth for the whole pipeline
# ----------------------------------------------------------------------------
TARGET_DURATION_S  = 18     # target video duration in seconds
SENTENCES_PER_CLIP = 3      # exactly 3 sentences per script
WORDS_PER_SENTENCE = 20     # ~20 words × 3 = ~60 words ≈ 18s at calm pace
SCENES_COUNT       = 3      # one scene per sentence

BUCKET_WEIGHTS = {"news": 0.40, "social": 0.35, "knowledge": 0.25}

# ----------------------------------------------------------------------------
# SOCIAL AWARENESS pool (25+ causes)
# ----------------------------------------------------------------------------
SOCIAL_TOPICS = [
    ("Mental health affects 1 in 4 people every year",
     "mental health awareness, breaking the stigma around therapy and emotions"),
    ("The loneliness epidemic is now a global health crisis",
     "loneliness, social isolation, and the importance of human connection"),
    ("Burnout is not a badge of honour — it is a warning sign",
     "workplace burnout, rest, and sustainable productivity"),
    ("Only 3% of Earth's water is drinkable — and we are wasting it",
     "water conservation, global water scarcity crisis and solutions"),
    ("A million species face extinction in the next decade",
     "biodiversity loss, wildlife conservation and habitat protection"),
    ("Fast fashion is the world's second most polluting industry",
     "sustainable fashion, overconsumption, and clothing waste crisis"),
    ("Air pollution kills 7 million people every year",
     "air quality, clean energy transition, pollution awareness"),
    ("A single act of kindness can change someone's entire day",
     "random acts of kindness, community, human connection"),
    ("826 million people go to bed hungry every night",
     "world hunger, food waste, food donation and local food banks"),
    ("The average person spends 7 hours a day looking at screens",
     "screen time, digital detox, mindful technology use"),
    ("Social media comparison is triggering a teen mental health crisis",
     "social media and mental health, teen wellbeing, digital literacy"),
    ("1 in 7 people on earth lives with a disability",
     "disability inclusion, accessibility, breaking barriers"),
    ("258 million children have never been to school",
     "education inequality, child literacy, right to education"),
    ("Sitting for more than 8 hours a day is as dangerous as smoking",
     "sedentary lifestyle, movement breaks, physical health"),
    ("Donating blood costs you nothing and saves up to 3 lives",
     "blood donation awareness, organ donation, life-saving action"),
    ("40 million people worldwide are trapped in modern slavery",
     "human trafficking awareness, modern slavery, how to help"),
    ("Deforestation destroys a football pitch of forest every second",
     "deforestation, Amazon rainforest, reforestation and climate"),
    ("Talking about suicide saves lives",
     "suicide prevention, mental health first aid, reaching out"),
    ("Cyberbullying affects 1 in 3 young people online",
     "cyberbullying awareness, online kindness, digital safety"),
    ("Women still earn 82 cents for every dollar a man earns",
     "gender pay gap, women's empowerment, workplace equality"),
]

# ----------------------------------------------------------------------------
# KNOWLEDGE FACTS pool (25+ domains)
# ----------------------------------------------------------------------------
KNOWLEDGE_TOPICS = [
    ("Your brain physically changes every time you learn something",
     "neuroplasticity — how the brain forms new synaptic connections through learning"),
    ("Trees in a forest communicate underground through fungal networks",
     "mycorrhizal networks — the Wood Wide Web and how forests share nutrients"),
    ("There are more stars in the universe than grains of sand on Earth",
     "the scale of the observable universe and what it means for life"),
    ("A day on Venus is longer than a year on Venus",
     "Venus's slow retrograde rotation and its thick atmosphere"),
    ("The Library of Alexandria held the knowledge of the ancient world",
     "history of Alexandria — what was lost and why it still matters"),
    ("Octopuses have three hearts, blue blood, and can solve puzzles",
     "cephalopod intelligence — how octopuses think and display consciousness"),
    ("The Black Death killed half of Europe and rewrote civilisation",
     "the bubonic plague of 1347 — causes, scale, and lasting social impact"),
    ("Ancient Romans had fast food restaurants on every street",
     "thermopolia in Pompeii — how Romans ate and lived daily life"),
    ("A teaspoon of soil has more organisms than people on Earth",
     "soil microbiome — the invisible world beneath our feet"),
    ("The tardigrade is the most indestructible animal on Earth",
     "water bears — surviving space, radiation, and extreme pressure"),
    ("Sleep cleans your brain of toxins while you rest",
     "the glymphatic system — cerebrospinal fluid flushes waste during sleep"),
    ("Compound interest built every great fortune in history",
     "the mathematics of compounding — why time is the most valuable asset"),
    ("The Silk Road connected China to Rome 2,000 years ago",
     "ancient Silk Road — trade, culture, ideas and disease across continents"),
    ("Music gives you goosebumps through a dopamine spike in the brain",
     "the science of frisson — musical chills and emotional peak experiences"),
    ("Quantum computers could break all internet encryption within a decade",
     "quantum computing threat to cybersecurity and post-quantum cryptography"),
    ("The internet generates 2.5 quintillion bytes of data every day",
     "big data, digital footprints, and who owns the information you create"),
    ("Plato said democracy would always collapse into tyranny",
     "Plato's Republic — the cycle of governments and democracy's weaknesses"),
    ("Stoics had a 2,000-year-old solution to modern anxiety",
     "Stoic philosophy — Marcus Aurelius and practising control over thoughts"),
    ("Black holes don't suck — the truth about gravity in space",
     "misconceptions about black holes, event horizons, and how gravity works"),
    ("The James Webb telescope is showing us the first light of the universe",
     "JWST discoveries — earliest galaxies and cosmic origins"),
]

# ----------------------------------------------------------------------------
# RSS FEEDS (free, no key)
# ----------------------------------------------------------------------------
RSS_FEEDS = [
    ("tech",     "https://feeds.feedburner.com/TechCrunch"),
    ("tech",     "https://www.theverge.com/rss/index.xml"),
    ("world",    "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("world",    "https://feeds.bbci.co.uk/news/rss.xml"),
    ("world",    "https://www.theguardian.com/world/rss"),
    ("science",  "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
    ("science",  "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
    ("health",   "https://feeds.bbci.co.uk/news/health/rss.xml"),
    ("business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
]

# ----------------------------------------------------------------------------
# The strict timing instruction injected into every prompt
# ----------------------------------------------------------------------------
_TIMING_RULE = f"""
STRICT TIMING RULE — READ CAREFULLY:
- The "script" field must be EXACTLY {SENTENCES_PER_CLIP} sentences separated by periods.
- Each sentence must be 18 to 22 words long. Count every word.
- EXAMPLE of correct length sentence (20 words): "Scientists have discovered that the human brain can form new neural connections at any age with consistent practice."
- Total script word count: {SENTENCES_PER_CLIP * WORDS_PER_SENTENCE - 5} to {SENTENCES_PER_CLIP * WORDS_PER_SENTENCE + 10} words.
- A script with fewer than 40 words total is INCORRECT and will be rejected.
"""

_JSON_SCHEMA = """{
  "topic":  "Punchy video headline — max 10 words",
  "script": "EXACTLY 3 sentences. Each sentence is 18-22 words. Total: 54-66 words. No hashtags.",
  "scenes": [
    "Scene 1 visual for sentence 1 — location, lighting, mood (detail it)",
    "Scene 2 visual for sentence 2",
    "Scene 3 powerful closing visual"
  ],
  "quote":  "A real famous quote relevant to the topic — under 15 words",
  "author": "The real person who said it"
}"""


def _prompt_news(headline, summary, category):
    return f"""You are a social video producer. Create a script about this real news story.

HEADLINE: {headline}
SUMMARY: {summary}
CATEGORY: {category}
{_TIMING_RULE}
Make viewers care. Be accurate. Be clear. A general audience must understand it.
Respond ONLY with valid JSON (no markdown, no backticks):
{_JSON_SCHEMA}"""


def _prompt_social(topic, description):
    return f"""You are a social impact video creator making an awareness video.

CAUSE: {topic}
CONTEXT: {description}
{_TIMING_RULE}
Use at least one real statistic. End with a short, positive call to action.
Respond ONLY with valid JSON (no markdown, no backticks):
{_JSON_SCHEMA}"""


def _prompt_knowledge(topic, description):
    return f"""You are a "fascinating facts" video creator.

TOPIC: {topic}
FOCUS: {description}
{_TIMING_RULE}
Open with the most surprising hook. Use real science or history. Make viewers say "I didn't know that!"
Respond ONLY with valid JSON (no markdown, no backticks):
{_JSON_SCHEMA}"""


# ----------------------------------------------------------------------------
# AI callers
# ----------------------------------------------------------------------------

def _call_groq(prompt):
    """
    Call Groq with json_object mode + word count validation.
    Retries if script is too short (Groq sometimes ignores word count instructions).
    """
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        try:
            from app.config import settings
            key = getattr(settings, "GROQ_API_KEY", "")
        except Exception:
            pass
    if not key:
        return None

    MIN_WORDS    = SENTENCES_PER_CLIP * 12   # floor — 36 words
    TARGET_WORDS = SENTENCES_PER_CLIP * WORDS_PER_SENTENCE  # goal — 60 words

    MODELS = [
        "llama-3.3-70b-versatile",
        "gemma2-9b-it",
        "mixtral-8x7b-32768",
    ]

    system_msg = (
        "You are a video script writer that outputs ONLY valid JSON. "
        "No markdown. No backticks. No preamble. "
        f"CRITICAL WORD COUNT RULE: The 'script' field MUST contain EXACTLY "
        f"{SENTENCES_PER_CLIP} sentences. EACH sentence MUST be 18-22 words. "
        f"Total word count MUST be {TARGET_WORDS - 5} to {TARGET_WORDS + 5} words. "
        "Count every word carefully. A script under 35 words is WRONG."
    )

    from groq import Groq
    client = Groq(api_key=key)

    for model in MODELS:
        for attempt in range(2):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user",   "content": prompt},
                    ],
                    temperature=0.72,
                    max_tokens=700,
                    response_format={"type": "json_object"},
                )
                raw  = resp.choices[0].message.content.strip()
                data = json.loads(raw)
                assert data.get("topic") and data.get("script") and data.get("scenes")

                word_count = len(data["script"].split())
                if word_count < MIN_WORDS:
                    logger.warning(
                        f"Groq [{model}] attempt {attempt+1}: only {word_count}w "
                        f"(need {MIN_WORDS}+) — retrying"
                    )
                    continue

                data["script"] = _enforce_sentences(data["script"])
                logger.info(
                    f"Groq [{model}] ({len(data['script'].split())}w): {data['topic']}"
                )
                return data

            except json.JSONDecodeError as e:
                logger.warning(f"Groq [{model}] bad JSON: {e}")
                break
            except Exception as e:
                logger.warning(f"Groq [{model}]: {e}")
                break

    return None


def _call_openai(prompt):
    try:
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key or key.startswith("sk-your"):
            return None
        from openai import OpenAI
        resp = OpenAI(api_key=key).chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Respond with valid JSON only. 3 sentences max in script."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.80, max_tokens=500,
        )
        raw  = resp.choices[0].message.content.strip()
        raw  = re.sub(r"^```json\s*", "", raw)
        raw  = re.sub(r"```\s*$", "", raw).strip()
        data = json.loads(raw)
        data["script"] = _enforce_sentences(data["script"])
        return data
    except Exception as e:
        logger.warning(f"OpenAI: {e}")
        return None


def _enforce_sentences(text):
    """Hard-clamp to exactly SENTENCES_PER_CLIP sentences."""
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    sents = [s.strip() for s in sents if s.strip()]
    # Take first N sentences only
    return " ".join(sents[:SENTENCES_PER_CLIP])


def _ai_generate(prompt):
    return _call_groq(prompt) or _call_openai(prompt)


# ----------------------------------------------------------------------------
# RSS fetcher
# ----------------------------------------------------------------------------

def _fetch_headlines(max_items=20):
    headlines = []
    feeds = random.sample(RSS_FEEDS, min(5, len(RSS_FEEDS)))
    for category, url in feeds:
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0 Aureus/3.0"})
            with urlopen(req, timeout=6) as resp:
                raw = resp.read()
            root  = ET.fromstring(raw)
            ns    = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall(".//item") or root.findall(".//atom:entry", ns)
            for item in items[:5]:
                title   = (item.findtext("title") or
                           item.findtext("atom:title", namespaces=ns) or "").strip()
                summary = (item.findtext("description") or
                           item.findtext("atom:summary", namespaces=ns) or "").strip()
                summary = re.sub(r"<[^>]+>", "", summary)[:300]
                if title and len(title) > 15:
                    headlines.append({"title": title, "summary": summary,
                                      "category": category})
        except Exception as e:
            logger.debug(f"RSS {url[:40]}: {e}")
    random.shuffle(headlines)
    return headlines[:max_items]


# ----------------------------------------------------------------------------
# Bucket generators
# ----------------------------------------------------------------------------

def _pick_bucket(theme):
    if theme:
        t = theme.lower()
        if any(w in t for w in ["news", "current", "trending", "today", "latest"]):
            return "news"
        if any(w in t for w in ["social", "cause", "awareness", "mental", "climate"]):
            return "social"
        if any(w in t for w in ["fact", "science", "history", "knowledge", "learn"]):
            return "knowledge"
    return random.choices(
        ["news", "social", "knowledge"],
        weights=[BUCKET_WEIGHTS["news"], BUCKET_WEIGHTS["social"], BUCKET_WEIGHTS["knowledge"]],
    )[0]


def _generate_news(theme):
    headlines = _fetch_headlines()
    if not headlines:
        return None
    if theme:
        filtered = [h for h in headlines if theme.lower() in h["title"].lower()]
        if filtered:
            headlines = filtered
    item = random.choice(headlines)
    result = _ai_generate(_prompt_news(item["title"], item["summary"], item["category"]))
    if result:
        result["bucket"] = "news"
    return result


def _generate_social(theme):
    if theme:
        matches = [(t, d) for t, d in SOCIAL_TOPICS
                   if any(w in t.lower() or w in d.lower() for w in theme.lower().split())]
        pair = random.choice(matches) if matches else random.choice(SOCIAL_TOPICS)
    else:
        pair = random.choice(SOCIAL_TOPICS)
    result = _ai_generate(_prompt_social(*pair))
    if result:
        result["bucket"] = "social"
    return result


def _generate_knowledge(theme):
    if theme:
        matches = [(t, d) for t, d in KNOWLEDGE_TOPICS
                   if any(w in t.lower() or w in d.lower() for w in theme.lower().split())]
        pair = random.choice(matches) if matches else random.choice(KNOWLEDGE_TOPICS)
    else:
        pair = random.choice(KNOWLEDGE_TOPICS)
    result = _ai_generate(_prompt_knowledge(*pair))
    if result:
        result["bucket"] = "knowledge"
    return result


# ----------------------------------------------------------------------------
# Static fallbacks (zero internet, zero API keys)
# ----------------------------------------------------------------------------
_FALLBACKS = [
    {
        "bucket": "social",
        "topic":  "One in four people experiences mental illness every year",
        "script": (
            "Mental illness affects 970 million people worldwide right now, "
            "yet most never receive any treatment because of stigma. "
            "Check on a friend today — you cannot always tell who is struggling."
        ),
        "scenes": [
            "Person sitting alone on park bench, distant look, soft autumn light",
            "Two friends embracing warmly, genuine comfort, golden afternoon",
            "Diverse group raising mental health awareness ribbons, community hope",
        ],
        "quote":  "It is okay to not be okay — as long as you do not give up.",
        "author": "Karen Salmansohn",
    },
    {
        "bucket": "social",
        "topic":  "Eight million tonnes of plastic enter our oceans every year",
        "script": (
            "Every minute, the equivalent of a rubbish truck of plastic is dumped into the ocean. "
            "By 2050 there will be more plastic in the sea than fish by weight. "
            "Refusing single-use plastic and supporting clean-ups actually works — start today."
        ),
        "scenes": [
            "Aerial view of plastic debris floating on ocean surface, sobering wide shot",
            "Community beach clean-up volunteers filling bags, teamwork, golden hour",
            "Clear blue ocean waves crashing on pristine beach, nature restored, hope",
        ],
        "quote":  "We do not inherit the earth from our ancestors — we borrow it from our children.",
        "author": "Native American Proverb",
    },
    {
        "bucket": "news",
        "topic":  "AI is replacing tasks in every major industry right now",
        "script": (
            "In the last twelve months, artificial intelligence has moved from experiment "
            "to operational reality in healthcare, finance, law and education. "
            "The greatest economic shift of our lifetime is happening — the window to adapt is narrowing."
        ),
        "scenes": [
            "Futuristic server room with blue glowing lights, data streams, cinematic wide",
            "Doctor reviewing AI-assisted diagnosis on tablet in modern hospital, focused",
            "Engineer overseeing AI robots in high-tech factory, transformation, progress",
        ],
        "quote":  "The measure of intelligence is the ability to change.",
        "author": "Albert Einstein",
    },
    {
        "bucket": "knowledge",
        "topic":  "Your brain physically rewires every time you learn something",
        "script": (
            "Every time you learn a skill, your brain forms new synaptic connections "
            "in a process called neuroplasticity. "
            "The most powerful brain-training tool is not an app — it is genuine curiosity applied consistently."
        ),
        "scenes": [
            "Glowing neural network visualization, synapses firing, science blue light",
            "Student absorbed in reading in sunlit library, deep focus, warm tones",
            "Person emerging from darkness into bright light, growth and transformation",
        ],
        "quote":  "Live as if you were to die tomorrow. Learn as if you were to live forever.",
        "author": "Mahatma Gandhi",
    },
    {
        "bucket": "knowledge",
        "topic":  "Trees in a forest communicate underground through fungal networks",
        "script": (
            "Beneath every forest floor lies a vast network of fungal threads "
            "called mycorrhizae — through which trees share nutrients and send warning signals. "
            "Forests are not just collections of trees — they are living, communicating communities."
        ),
        "scenes": [
            "Ancient forest floor close-up, visible roots and fungi, rich earth tones",
            "Time-lapse of seedling growing in dappled forest sunlight, emergence",
            "Majestic old-growth tree with sunlight filtering through canopy, awe",
        ],
        "quote":  "Look deep into nature, and then you will understand everything better.",
        "author": "Albert Einstein",
    },
]


# ----------------------------------------------------------------------------
# PUBLIC API
# ----------------------------------------------------------------------------

def generate_news_script(theme: Optional[str] = None) -> dict:
    """
    Generate a video script strictly timed for a 15-20 second video.
    Returns dict: {topic, script, scenes[3], quote, author, bucket}
    """
    bucket = _pick_bucket(theme)
    logger.info(f"Script bucket → {bucket}")

    data = None
    if bucket == "news":
        data = _generate_news(theme)
    elif bucket == "social":
        data = _generate_social(theme)
    else:
        data = _generate_knowledge(theme)

    if not data:
        logger.info("AI unavailable — using built-in fallback")
        data = _random_fallback(bucket)

    # Guarantee fields
    data.setdefault("topic",  "Today's message")
    data.setdefault("script", "")
    data.setdefault("scenes", ["Cinematic shot, golden hour light"] * SCENES_COUNT)
    data.setdefault("quote",  "Small actions create big change.")
    data.setdefault("author", "")
    data.setdefault("bucket", bucket)

    # Always enforce sentence count AFTER generation
    data["script"] = _enforce_sentences(data["script"])

    # Pad/trim scenes to exactly SCENES_COUNT
    while len(data["scenes"]) < SCENES_COUNT:
        data["scenes"].append("Cinematic wide shot, warm golden hour light")
    data["scenes"] = data["scenes"][:SCENES_COUNT]

    word_count = len(data["script"].split())
    logger.info(f"Final script: {word_count} words | {data['topic']}")
    return data


def _random_fallback(preferred_bucket):
    pool = [f for f in _FALLBACKS if f.get("bucket") == preferred_bucket]
    return random.choice(pool if pool else _FALLBACKS).copy()