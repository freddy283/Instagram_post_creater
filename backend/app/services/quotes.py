"""
Quote generation service.
Uses OpenAI GPT to generate unique, themed motivational quotes.
Falls back to a curated static list if OPENAI_API_KEY is not set or the call fails.
"""
import random
import logging
import json

logger = logging.getLogger(__name__)

# ─── Static fallback quotes ──────────────────────────────────────────────────

FALLBACK_QUOTES = [
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("In the middle of every difficulty lies opportunity.", "Albert Einstein"),
    ("It does not matter how slowly you go as long as you do not stop.", "Confucius"),
    ("Everything you've ever wanted is on the other side of fear.", "George Addair"),
    ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
    ("The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"),
    ("I have not failed. I've just found 10,000 ways that won't work.", "Thomas Edison"),
    ("The best time to plant a tree was 20 years ago. The second best time is now.", "Chinese Proverb"),
    ("You miss 100% of the shots you don't take.", "Wayne Gretzky"),
    ("Whether you think you can or you think you can't, you're right.", "Henry Ford"),
    ("The mind is everything. What you think you become.", "Buddha"),
    ("Strive not to be a success, but rather to be of value.", "Albert Einstein"),
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("Your time is limited, so don't waste it living someone else's life.", "Steve Jobs"),
    ("Life shrinks or expands in proportion to one's courage.", "Anais Nin"),
    ("It always seems impossible until it's done.", "Nelson Mandela"),
    ("The greatest glory in living lies not in never falling, but in rising every time we fall.", "Nelson Mandela"),
    ("In the end, it's not the years in your life that count. It's the life in your years.", "Abraham Lincoln"),
    ("Life is either a daring adventure or nothing at all.", "Helen Keller"),
    ("You have brains in your head. You have feet in your shoes. You can steer yourself any direction you choose.", "Dr. Seuss"),
    ("We must be the change we wish to see in the world.", "Mahatma Gandhi"),
    ("Spread love everywhere you go. Let no one ever come to you without leaving happier.", "Mother Teresa"),
    ("When you arise in the morning, think of what a privilege it is to be alive.", "Marcus Aurelius"),
    ("Do not go where the path may lead; go instead where there is no path and leave a trail.", "Ralph Waldo Emerson"),
    ("The two most important days in your life are the day you are born and the day you find out why.", "Mark Twain"),
    ("Many of life's failures are people who did not realize how close they were to success when they gave up.", "Thomas Edison"),
    ("You will face many defeats in life, but never let yourself be defeated.", "Maya Angelou"),
    ("Either you run the day, or the day runs you.", "Jim Rohn"),
    ("Whatever the mind of man can conceive and believe, it can achieve.", "Napoleon Hill"),
    ("The most difficult thing is the decision to act; the rest is merely tenacity.", "Amelia Earhart"),
    ("Magic is believing in yourself. If you can do that, you can make anything happen.", "Johann Wolfgang von Goethe"),
    ("Don't watch the clock; do what it does. Keep going.", "Sam Levenson"),
    ("Keep your face always toward the sunshine, and shadows will fall behind you.", "Walt Whitman"),
    ("No one can make you feel inferior without your consent.", "Eleanor Roosevelt"),
    ("It is never too late to be what you might have been.", "George Eliot"),
    ("Everything has beauty, but not everyone can see.", "Confucius"),
    ("Turn your wounds into wisdom.", "Oprah Winfrey"),
    ("Act as if what you do makes a difference. It does.", "William James"),
    ("Success usually comes to those who are too busy to be looking for it.", "Henry David Thoreau"),
]

THEMES = [
    "resilience and perseverance",
    "courage and taking risks",
    "growth mindset and learning",
    "purpose and meaning",
    "kindness and compassion",
    "gratitude and mindfulness",
    "leadership and vision",
    "creativity and innovation",
    "simplicity and focus",
    "love and human connection",
]


def get_random_quote() -> tuple[str, str]:
    """Return a random (quote, author) from the fallback list."""
    return random.choice(FALLBACK_QUOTES)


def get_daily_quote(seed: int = None) -> tuple[str, str]:
    """Return a deterministic daily quote based on a seed."""
    if seed is None:
        from datetime import date
        seed = (date.today() - date(2024, 1, 1)).days
    idx = seed % len(FALLBACK_QUOTES)
    return FALLBACK_QUOTES[idx]


def generate_quote_with_openai(theme: str = None, style: str = "inspirational") -> tuple[str, str]:
    """
    Generate a unique motivational quote using OpenAI GPT.
    Returns (quote_text, author_attribution).
    Falls back to static list on any error.
    """
    from app.config import settings

    if not settings.OPENAI_API_KEY:
        logger.info("OPENAI_API_KEY not set — using fallback quote")
        return get_random_quote()

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        if not theme:
            theme = random.choice(THEMES)

        prompt = f"""Generate a single original, {style} motivational quote about the theme of "{theme}".

The quote should:
- Be profound, memorable, and genuinely uplifting
- Be 1–3 sentences maximum (suitable for an Instagram image)
- Sound like it could come from a wise, well-known thinker or leader
- NOT be a copy of any existing famous quote

Respond ONLY with a valid JSON object in this exact format, no extra text:
{{"quote": "The quote text here.", "author": "Attributed Author Name"}}

For the author, use one of: a philosopher's name, a historical leader, a modern entrepreneur, or "Unknown" — but make it feel authentic."""

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a master of inspirational wisdom. You craft quotes that move people and spark positive action. You always respond with valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.85,
            max_tokens=200,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        raw = raw.strip("```json").strip("```").strip()
        data = json.loads(raw)
        quote = data.get("quote", "").strip().strip('"')
        author = data.get("author", "Unknown").strip()

        if not quote:
            raise ValueError("Empty quote returned")

        logger.info(f"OpenAI generated quote by {author}")
        return quote, author

    except Exception as e:
        logger.warning(f"OpenAI quote generation failed ({e}), using fallback")
        return get_random_quote()


def get_openai_daily_quote(user_id: str = "", seed: int = None) -> tuple[str, str]:
    """
    Primary entry point for posting tasks.
    Tries OpenAI first, falls back to deterministic static quote.
    """
    # Pick a theme deterministically so the same user always gets
    # the same theme each day (variety across days)
    if seed is None:
        from datetime import date
        seed = (date.today() - date(2024, 1, 1)).days

    theme_idx = (seed + hash(user_id or "")) % len(THEMES)
    theme = THEMES[abs(theme_idx)]

    return generate_quote_with_openai(theme=theme)
