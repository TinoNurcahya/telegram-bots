import json
import re
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from src.config import settings

logger = logging.getLogger(__name__)

# Comprehensive 15+ analytical/investigative categories for Master Detective Siesta
SIESTA_CATEGORIES = {
    "Dark Psychology & Mind Anomalies": {
        "description": "Subconscious human vulnerabilities, cognitive biases, dark psychology tricks, and optical mind traps.",
        "angles": [
            "The Gaslighting Effect and Subconscious Vulnerability",
            "The Paradox of Choice that Paralyzes the Human Brain",
            "Subconscious Cues That Involuntarily Expose Lies",
            "The Bystander Effect: Why Crowds Paralyze Action",
            "The Dark Triad Personality Traits Hidden in Ordinary Behavior"
        ]
    },
    "Dark Secrets & Classified Enigmas": {
        "description": "Redacted historical files, hidden underground facilities, ancient sealed vaults, and government black projects.",
        "angles": [
            "The Sealed Secret Vault B of Padmanabhaswamy Temple",
            "Declassified Operations of Project MKUltra Mind Control",
            "The Subterranean Secrets of the Cheyenne Mountain Complex",
            "Unopened Chambers of the Great Pyramid of Giza",
            "The Silent Svalbard Global Seed Vault Deep in Permafrost"
        ]
    },
    "Unsolved Historical Mysteries": {
        "description": "Unexplained vanishings, baffling historical records, and enigmatic events without forensic resolution.",
        "angles": [
            "The Disappearance of the Flannan Isles Lighthouse Keepers",
            "The Ghost Crew of the Mary Celeste Ship",
            "The Unsolved Identity of the Somerton Man",
            "The Bizarre Dancing Plague of Strasbourg in 1518",
            "The Vanishing of the Roanoke Colony Without a Trace"
        ]
    },
    "What If? Catastrophes & Scenarios": {
        "description": "Extreme scientific thought experiments, planetary disruptions, and catastrophic domino effects.",
        "angles": [
            "What If the Earth Stopped Spinning for Exactly One Second",
            "What If Oxygen Vanished from Earth for Just Five Seconds",
            "What If All Ocean Salt Disappeared Overnight",
            "What If the Sun Vanished from the Solar System for Seven Days",
            "What If the Entire Global Internet Permanently Collapsed"
        ]
    },
    "Cosmic Paradoxes & Space Wonders": {
        "description": "Deep universe anomalies, black hole physics, the Fermi paradox, and rogue celestial threats.",
        "angles": [
            "The Fermi Paradox: Where Is Everybody in the Infinite Cosmos?",
            "Rogue Planets: Frozen Giants Wandering Interstellar Space",
            "False Vacuum Decay: The Instant Annihilation of All Physics",
            "The Boötes Void: A Terrifying Chasm in the Fabric of Space",
            "Gravitational Time Dilation Near Supermassive Black Holes"
        ]
    },
    "Abyssal Ocean & Deep Nature Anomalies": {
        "description": "Unexplored marine trenches, biological impossibilities, and abyssal organisms.",
        "angles": [
            "Anomalies Lurking in the Absolute Depths of the Mariana Trench",
            "The Biological Immortality Paradox of Turritopsis dohrnii",
            "The Bloop and Unexplained Ultra-Low Frequency Deep Sea Acoustics",
            "Ophiocordyceps: Zombie Fungi That Hijack Neural Networks",
            "The Macropinna Microstoma: Fish with a Completely Transparent Head"
        ]
    },
    "Forensic Deduction & Impossible Crimes": {
        "description": "Locked-room logic, microscopic trace evidence, and criminal psychology deductions.",
        "angles": [
            "The Mathematical Deduction Behind Flawless Locked-Room Mysteries",
            "How Microscopic Pollen Dust Cracked an Impossible Cold Case",
            "Micro-Expressions: The Split-Second Involuntary Tells of Truth",
            "The Forensic Flaw That Inevitably Destroys Perfect Alibis",
            "Locard's Exchange Principle: Every Contact Leaves a Trace"
        ]
    },
    "Glitches in Reality & Simulation Oddities": {
        "description": "Collective false memories, neurological glitches, quantum measurement paradoxes, and reality illusions.",
        "angles": [
            "The Neurological Science Explaining the Illusion of Déjà Vu",
            "The Quantum Eraser Experiment: Can the Future Rewrite the Past?",
            "The Mandela Effect: Collective False Memory or Reality Glitch?",
            "The Taos Hum: The Unexplainable Acoustic Frequency Felt Worldwide",
            "Quantum Superposition: Matter Existing in All States Simultaneously"
        ]
    },
    "Forbidden & Dangerous Earth Terrains": {
        "description": "Deadly restricted territories, extreme quarantine zones, and islands where visitors never return.",
        "angles": [
            "Ilha da Queimada Grande: The Deadly Snake Island Forbidden to Humans",
            "North Sentinel Island: The Isolated Enclave from the Stone Age",
            "The Pripyat Red Forest: Nature Mutating Inside the Chernobyl Zone",
            "The Danakil Depression: The Hottest and Most Toxic Place on Earth",
            "Poveglia Island: The Quarantined Plague Island in the Venetian Lagoon"
        ]
    },
    "Lost Civilizations & Ooparts": {
        "description": "Out-of-place artifacts, enigmatic ancient engineering, and forgotten technological feats.",
        "angles": [
            "The 2,000-Year-Old Analog Computer of Antikythera",
            "The Lost Metallurgical Secret of Damascus Steel",
            "Göbekli Tepe: Megalithic Temples Built Before Human Agriculture",
            "The Precision Stone Cuts of Puma Punku in the Bolivian Andes",
            "The Ancient Baghdad Battery and Forgotten Electrochemistry"
        ]
    },
    "Mind-Bending Science & Quantum Paradoxes": {
        "description": "Physics counter-intuitions, quantum entanglement, antimatter, and strange matter.",
        "angles": [
            "Quantum Entanglement: Einstein's 'Spooky Action at a Distance'",
            "Strange Quark Stars: Matter That Consumes Everything It Touches",
            "The Mpemba Effect: Why Boiling Water Freezes Faster Than Cold Water",
            "Antimatter: The Most Expensive and Volatile Material in the Universe",
            "Neutron Stars: Where One Teaspoon Weighs Billions of Tons"
        ]
    },
    "Counter-Intuitive Truths & Bizarre Facts": {
        "description": "Facts that sound completely fabricated but are scientifically and empirically proven.",
        "angles": [
            "Sharks Are Older Than Trees and the Rings of Saturn",
            "The Mycelium Wood Wide Web: Underground Tree Communication",
            "Cleopatra Lived Closer in Time to the Moon Landing Than to the Great Pyramid",
            "Water Can Boil and Freeze at the Exact Same Time (The Triple Point)",
            "Bananas Are Slightly Radioactive Due to Potassium-40 Isotopes"
        ]
    },
    "Human Brain Curiosities & Rare Syndromes": {
        "description": "Phantom limbs, split-brain experiments, synesthesia, and hyperthymesia.",
        "angles": [
            "The Split-Brain Experiments: Two Distinct Conscious Minds in One Head",
            "Synesthesia: The Neurological Cross-Wiring of Senses",
            "Cotard's Syndrome: Patients Genuinely Convinced They Are Deceased",
            "Hyperthymesia: The Inability to Forget Any Day of One's Life",
            "Foreign Accent Syndrome: Waking Up With a Completely Different Accent"
        ]
    },
    "Time & Dimensional Paradoxes": {
        "description": "Temporal mechanics, the grandfather paradox, bootstrap paradoxes, and relativity.",
        "angles": [
            "The Bootstrap Paradox: An Information Loop With No Origin",
            "Gravitational Time Dilation: Why Time Runs Slower at Sea Level",
            "The Grandfather Paradox and the Many-Worlds Interpretation",
            "The Speed of Light Limitation and Why Looking at Stars Is Looking into the Past",
            "The Closed Timelike Curves Allowed by Einstein's Equations"
        ]
    },
    "Cryptic Codes & Unsolved Ciphers": {
        "description": "Historical undeciphered texts, modern cryptographic riddles, and secret cipherstones.",
        "angles": [
            "The Bizarre Botanical Cipher of the Voynich Manuscript",
            "Kryptos Section 4: The CIA Sculpture Code That Has Stood for Decades",
            "The Beale Ciphers and the Legend of Hidden Gold",
            "The Dorabella Cipher: A Secret Musical Code That Stumped Historians",
            "The Linear A Script: The Undeciphered Language of Minoan Crete"
        ]
    }
}

DEFAULT_TOPICS = [
    angle
    for cat in SIESTA_CATEGORIES.values()
    for angle in cat["angles"]
]

INVESTIGATIVE_LENSES = [
    "Ancient Mediterranean, Middle Eastern, or Mesopotamian archaeological records",
    "Cold War era declassified scientific or intelligence anomalies (1947–1991)",
    "Deep-sea oceanographic expeditions and abyssal trench discoveries",
    "East Asian, Japanese, or Himalayan historical and geographical enigmas",
    "19th and early 20th century forensic, maritime, or expedition mysteries",
    "Astrophysics, deep-space telescope observations, and relativistic paradoxes",
    "Neuroscience, extreme human perception experiments, and rare cognitive phenomena",
    "South American, Mesoamerican, or remote island anthropological mysteries",
    "Quantum mechanics, particle physics, and thermodynamic counter-intuitions",
    "Cryptography, undeciphered manuscripts, and mathematical anomalies",
    "Extreme terrestrial environments, subterranean caverns, and polar expeditions",
    "Bioluminescent, parasitic, or extremophile biological adaptations",
]

class Scene(BaseModel):
    scene_number: int = Field(description="Sequential scene number starting at 1")
    voiceover_text: str = Field(
        description="Spoken English narration in a natural, compelling, intelligent female documentary narrator voice. 1-2 punchy sentences."
    )
    subtitle_text: str = Field(
        description="Exact identical English text as voiceover_text for on-screen kinetic subtitle display."
    )
    visual_prompt: str = Field(
        description="Detailed cinematic anime art prompt for AI image generator. Include style, lighting, camera angle, vertical 9:16 aspect."
    )
    keywords: List[str] = Field(description="2-4 English keywords for stock video B-roll search")
    character_emotion: str = Field(
        default="concentration",
        description="Narrator's emotional reaction matching scene: concentration, contempt, confusion, anticipation, pride, surprise, fear, sadness, happiness, anxiety, boredom, relief, disappointment, disgust, embarrassment, anger, jealousy"
    )

class VideoScript(BaseModel):
    topic: str
    category: str = Field(default="Unsolved Mystery", description="Analytical category of this case")
    title: str = Field(description="High-CTR YouTube Shorts Title in English with emoji and hashtag")
    hook: str = Field(description="The first 3 seconds hook to captivate viewers immediately in English")
    description: str = Field(description="Short video description with engaging summary in English")
    tags: List[str] = Field(description="Relevant hashtags e.g. #shorts, #anime, #mystery, #siesta")
    scenes: List[Scene] = Field(description="List of 5 to 6 scenes making up the 45-60 second video")

class ScriptGeneratorService:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.client = genai.Client(api_key=self.api_key) if (genai and self.api_key) else None

    @staticmethod
    def _detect_wib_slot_and_day(now_wib: Optional[datetime] = None) -> tuple[int, int]:
        """
        Maps current Asia/Jakarta (UTC+7) time to one of the 5 daily schedule slots (0..4):
        Slot 0: ~13:00 WIB (< 14:30)
        Slot 1: ~16:00 WIB (14:30 - 17:29)
        Slot 2: ~19:00 WIB (17:30 - 20:14)
        Slot 3: ~21:30 WIB (20:15 - 22:29)
        Slot 4: ~23:30 WIB (>= 22:30)
        """
        wib_tz = timezone(timedelta(hours=7))
        dt = now_wib or datetime.now(wib_tz)
        day_of_year = dt.timetuple().tm_yday
        decimal_hour = dt.hour + (dt.minute / 60.0)

        if decimal_hour < 14.5:
            slot_idx = 0
        elif decimal_hour < 17.5:
            slot_idx = 1
        elif decimal_hour < 20.25:
            slot_idx = 2
        elif decimal_hour < 22.5:
            slot_idx = 3
        else:
            slot_idx = 4

        return day_of_year, slot_idx

    def get_rotated_case_prompt(
        self,
        slot_index: Optional[int] = None,
        day_of_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Deterministically rotates across the 15 categories so that all 5 daily slots
        on the same day are guaranteed to use 5 distinct categories, while pairing each
        slot with a unique investigative lens and fallback angle.
        """
        auto_day, auto_slot = self._detect_wib_slot_and_day()
        d_idx = day_of_year if day_of_year is not None else auto_day
        s_idx = slot_index if slot_index is not None else auto_slot

        categories = list(SIESTA_CATEGORIES.keys())
        cat_idx = (d_idx * 5 + s_idx) % len(categories)
        category_name = categories[cat_idx]
        cat_info = SIESTA_CATEGORIES[category_name]

        angles = cat_info["angles"]
        angle_idx = (d_idx + s_idx) % len(angles)
        lens_idx = (d_idx * 5 + s_idx * 3) % len(INVESTIGATIVE_LENSES)

        return {
            "category": category_name,
            "description": cat_info["description"],
            "angle": angles[angle_idx],
            "reference_angles": angles,
            "lens": INVESTIGATIVE_LENSES[lens_idx],
            "slot_index": s_idx,
            "day_of_year": d_idx,
        }

    def get_random_case_prompt(self) -> Dict[str, str]:
        """Picks a category and intriguing case angle using slot-aware rotation."""
        rotated = self.get_rotated_case_prompt()
        return {
            "category": rotated["category"],
            "description": rotated["description"],
            "angle": rotated["angle"]
        }

    def get_random_trending_topic(self) -> str:
        case = self.get_rotated_case_prompt()
        return case["angle"]

    async def generate_script(
        self,
        topic: Optional[str] = None,
        excluded_topics: Optional[List[str]] = None,
        slot_index: Optional[int] = None
    ) -> VideoScript:
        """
        Generates a high-retention YouTube Shorts script structured for AI video generation:
        - When topic is None, uses deterministic 5-slot daily category rotation AND instructs
          Gemini to dynamically discover a fresh, non-duplicate real-world case/anomaly.
        """
        is_dynamic_discovery = False
        reference_angles: List[str] = []
        investigative_lens = ""

        if topic and topic.strip():
            clean_topic = re.sub(r"[\r\n\t]+", " ", topic.strip())[:150].strip()
            category_name = "Investigative Case"
            target_topic = clean_topic
            category_desc = "A mysterious anomaly requiring forensic intellectual analysis."
        else:
            case = self.get_rotated_case_prompt(slot_index=slot_index)
            category_name = case["category"]
            target_topic = case["angle"]
            category_desc = case["description"]
            reference_angles = case["reference_angles"]
            investigative_lens = case["lens"]
            is_dynamic_discovery = True

        avoid_list = list(dict.fromkeys((reference_angles or []) + (excluded_topics or [])))[:35]
        avoid_block = "\n".join(f"  - {item}" for item in avoid_list) if avoid_list else "  - None"

        if is_dynamic_discovery:
            topic_directive = f"""
Topic Category: {category_name} ({category_desc})
Creative Sub-Focus / Lens for Today's Slot: {investigative_lens}

DYNAMIC CASE SELECTION (ANTI-DUPLICATE):
Instead of repeating a generic cliché, select ONE specific, real-world documented historical mystery, scientific paradox, declassified anomaly, or bizarre natural phenomenon that fits "{category_name}" (ideally intersecting with "{investigative_lens}").
DO NOT reuse or repeat any of these previously covered cases/examples:
{avoid_block}
Set the "topic" field in your JSON response to the exact name of the fresh case you selected.
"""
        else:
            topic_directive = f"""
Topic Category: {category_name} ({category_desc})
Target Case: "{target_topic}"
"""

        prompt = f"""
You are an elite female documentary & investigative narrator for viral YouTube Shorts, TikTok, and Reels (similar to the compelling, sophisticated storytelling style of Vox, Lemmino, and CuriosityStream).
Your tone is intelligent, mature, mysterious, razor-sharp, and completely natural — NO cutesy anime tropes, NO childish banter, NO theatrical anime voice acting. Just a calm, deeply intriguing, authoritative narrator presenting mind-bending facts.
{topic_directive}
CRITICAL REQUIREMENTS:
1. Voiceover Language (voiceover_text): Strictly clear, natural, engaging English written specifically for spoken auditory delivery.
   - Use short, high-impact, punchy sentences.
   - Hook the listener instantly in scene 1 with an unsettling fact, contrast, or mystery.
   - Build curiosity scene by scene, resolving with a thought-provoking conclusion.
2. Subtitle Language (subtitle_text): Identical to voiceover_text (English) for seamless on-screen kinetic subtitle synchronization.
3. Target Duration: 45 to 60 seconds when spoken aloud (around 5 to 6 scenes).
4. Visual Prompts: Cinematic, atmospheric, high-detail visual prompt. Include:
   "cinematic film still, atmospheric lighting, high detail, dramatic shadows, mysterious mood, vertical 9:16 composition" tailored to each scene.
5. Character Emotion: Choose matching reaction for each scene from:
   ["concentration", "contempt", "confusion", "anticipation", "pride", "surprise", "fear", "sadness", "happiness", "anxiety", "boredom", "relief", "disappointment", "disgust", "embarrassment", "anger", "jealousy"]
6. Title & Metadata: High-CTR English YouTube title with emojis and hashtags, compelling English description, and tags.

Return ONLY a strictly valid JSON object matching this schema:
{{
  "topic": "{target_topic}",
  "category": "{category_name}",
  "title": "The Chilling Truth About {target_topic} 🔍 #Shorts",
  "hook": "Opening 3-second hook in English...",
  "description": "Engaging description in English...",
  "tags": ["#shorts", "#mystery", "#documentary", "#facts", "#science"],
  "scenes": [
    {{
      "scene_number": 1,
      "voiceover_text": "Behind this baffling mystery lies a single contradiction that science still cannot explain.",
      "subtitle_text": "Behind this baffling mystery lies a single contradiction that science still cannot explain.",
      "visual_prompt": "cinematic film still, dramatic lighting, atmospheric mystery study, vertical 9:16 composition of ...",
      "character_emotion": "concentration",
      "keywords": ["mystery study", "dark archives"]
    }}
  ]
}}
"""

        if not self.client:
            logger.warning("Gemini Client not configured, returning mock script fallback.")
            return self._get_fallback_script(target_topic, category_name)

        models_to_try = [self.model_name]
        for fallback_m in ["gemini-flash-lite-latest", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]:
            if fallback_m not in models_to_try:
                models_to_try.append(fallback_m)

        for model_candidate in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_candidate,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7,
                    ),
                )
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]

                data = json.loads(raw_text.strip())
                return VideoScript(**data)
            except Exception as e:
                logger.warning(f"Model {model_candidate} failed: {e}. Trying next candidate...")

        logger.error(f"All Gemini models failed. Using template fallback for {target_topic}.")
        return self._get_fallback_script(target_topic, category_name)

    def _get_fallback_script(self, topic: str, category: str = "Unsolved Mystery") -> VideoScript:
        return VideoScript(
            topic=topic,
            category=category,
            title=f"The Hidden Truth of {topic} 🔍 #Shorts",
            hook=f"Did you know there is a profound enigma behind {topic}?",
            description=f"An investigative analysis of the truth behind {topic}. Subscribe for daily mind-bending stories.",
            tags=["#shorts", "#mystery", "#documentary", "#science", "#facts"],
            scenes=[
                Scene(
                    scene_number=1,
                    voiceover_text=f"Let us examine the facts. Behind {topic} lies a profound mystery that few people understand.",
                    subtitle_text=f"Let us examine the facts. Behind {topic} lies a profound mystery that few people understand.",
                    visual_prompt=f"cinematic film still, atmospheric lighting, dramatic shadows, mysterious archives, vertical 9:16 composition of {topic}",
                    character_emotion="concentration",
                    keywords=["investigation", "mystery documents"]
                ),
                Scene(
                    scene_number=2,
                    voiceover_text="When you analyze the historical evidence closely, baffling anomalies begin to emerge.",
                    subtitle_text="When you analyze the historical evidence closely, baffling anomalies begin to emerge.",
                    visual_prompt="cinematic film still, ancient library illuminated by soft moonlight, dust particles in light beam, vertical 9:16",
                    character_emotion="contempt",
                    keywords=["ancient library", "shadowy archive"]
                ),
                Scene(
                    scene_number=3,
                    voiceover_text="Connecting the recorded data reveals a startling truth that defies conventional explanation.",
                    subtitle_text="Connecting the recorded data reveals a startling truth that defies conventional explanation.",
                    visual_prompt="cinematic deep space nebula, glowing constellation lines, hyper-detailed cosmic vista, vertical 9:16",
                    character_emotion="surprise",
                    keywords=["cosmic nebula", "deep space"]
                ),
                Scene(
                    scene_number=4,
                    voiceover_text="The reality, it turns out, is far more unsettling than any fiction we could create.",
                    subtitle_text="The reality, it turns out, is far more unsettling than any fiction we could create.",
                    visual_prompt="cinematic film still, moody twilight sky over quiet European streets, dramatic mist, vertical 9:16",
                    character_emotion="relief",
                    keywords=["misty street", "cinematic twilight"]
                ),
                Scene(
                    scene_number=5,
                    voiceover_text="Did you see the hidden pattern in this mystery? Share your theory in the comments below.",
                    subtitle_text="Did you see the hidden pattern in this mystery? Share your theory in the comments below.",
                    visual_prompt="cinematic night city skyline, glistening rain reflections, glowing neon bokeh, vertical 9:16",
                    character_emotion="pride",
                    keywords=["night city", "rainy street"]
                )
            ]
        )

    async def generate_longform_script(
        self,
        topic: Optional[str] = None,
        excluded_topics: Optional[List[str]] = None
    ) -> VideoScript:
        """
        Generates a 4 to 6 minute widescreen (16:9) investigative documentary script
        structured into 3 Chapters / 15 Scenes (~750-900 words of spoken English narration)
        to build YouTube Watch Hours (4,000h AdSense threshold) and maximize Long-Form RPM.
        Uses slot_index=5 so the category never collides with the 5 daily Shorts slots (0..4).
        """
        is_dynamic_discovery = False
        reference_angles: List[str] = []
        investigative_lens = ""

        if topic and topic.strip():
            clean_topic = re.sub(r"[\r\n\t]+", " ", topic.strip())[:150].strip()
            category_name = "Deep-Dive Documentary"
            target_topic = clean_topic
            category_desc = "An in-depth forensic and historical documentary investigation."
        else:
            case = self.get_rotated_case_prompt(slot_index=5)
            category_name = case["category"]
            target_topic = case["angle"]
            category_desc = case["description"]
            reference_angles = case["reference_angles"]
            investigative_lens = case["lens"]
            is_dynamic_discovery = True

        avoid_list = list(dict.fromkeys((reference_angles or []) + (excluded_topics or [])))[:35]
        avoid_block = "\n".join(f"  - {item}" for item in avoid_list) if avoid_list else "  - None"

        if is_dynamic_discovery:
            topic_directive = f"""
Topic Category: {category_name} ({category_desc})
Creative Sub-Focus / Lens for Today's Documentary: {investigative_lens}

DYNAMIC DOCUMENTARY CASE SELECTION (ANTI-DUPLICATE):
Select ONE specific, real-world documented historical mystery, scientific paradox, declassified operation, or unexplained phenomenon that fits "{category_name}" (ideally intersecting with "{investigative_lens}") and is rich enough for a 5-minute deep-dive documentary.
DO NOT reuse or repeat any of these previously covered cases/examples:
{avoid_block}
Set the "topic" field in your JSON response to the exact name of the case you selected.
"""
        else:
            topic_directive = f"""
Topic Category: {category_name} ({category_desc})
Target Documentary Case: "{target_topic}"
"""

        prompt = f"""
You are an elite documentary narrator and investigative journalist for a high-retention widescreen YouTube Documentary channel (in the style of Lemmino, Vox, and Fern).
Your tone is intelligent, atmospheric, forensic, and completely natural.
{topic_directive}
CRITICAL REQUIREMENTS FOR 16:9 LONG-FORM DOCUMENTARY (4-6 MINUTES):
1. Structure: Exactly 15 sequential scenes (scene_number 1 through 15) divided across 3 narrative acts:
   - Scenes 1–5 (Act I: The Anomaly & Historical Context): Hook the viewer, establish the exact time, place, and baffling premise.
   - Scenes 6–10 (Act II: The Forensic Investigation & Competing Theories): Examine the documented evidence, scientific data, and failed explanations.
   - Scenes 11–15 (Act III: The Breakthrough or Unsettling Conclusion): Reveal the deepest layer of the mystery and end with a thought-provoking philosophical question.
2. Voiceover Length per Scene (voiceover_text): Write 3 to 4 rich, engaging, well-paced sentences per scene (approximately 45 to 55 words per scene, totaling ~750 words across all 15 scenes so the spoken narration lasts 4.5 to 5.5 minutes).
3. Subtitle Text (subtitle_text): Identical to voiceover_text (English).
4. Visual Prompts (visual_prompt): Widescreen 16:9 cinematic documentary imagery. Include:
   "cinematic 16:9 widescreen film still, atmospheric lighting, high detail, documentary cinematography" tailored to each scene.
5. Title & Metadata:
   - High-CTR YouTube Documentary title in English (DO NOT include #Shorts or #shorts in the title or tags!).
   - Detailed multi-paragraph YouTube SEO description in English.
   - Tags: ["#documentary", "#mystery", "#science", "#history", "#investigation"].

Return ONLY a strictly valid JSON object matching this schema:
{{
  "topic": "{target_topic}",
  "category": "{category_name}",
  "title": "The Unsolved Files: Inside {target_topic} (Full Documentary)",
  "hook": "Opening documentary hook in English...",
  "description": "Comprehensive 2-paragraph documentary overview in English...",
  "tags": ["#documentary", "#mystery", "#science", "#history", "#investigation"],
  "scenes": [
    {{
      "scene_number": 1,
      "voiceover_text": "3-4 rich sentences of documentary narration (45-55 words)...",
      "subtitle_text": "Identical 3-4 sentences of documentary narration...",
      "visual_prompt": "cinematic 16:9 widescreen film still, dramatic lighting, documentary archive of ...",
      "character_emotion": "concentration",
      "keywords": ["documentary archive", "historical mystery"]
    }}
  ]
}}
"""

        if not self.client:
            logger.warning("Gemini Client not configured, returning fallback longform script.")
            return self._get_fallback_longform_script(target_topic, category_name)

        models_to_try = [self.model_name]
        for fallback_m in ["gemini-flash-lite-latest", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]:
            if fallback_m not in models_to_try:
                models_to_try.append(fallback_m)

        for model_candidate in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_candidate,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7,
                    ),
                )
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]

                data = json.loads(raw_text.strip())
                # Strip any accidental #shorts from title/tags
                if "title" in data:
                    data["title"] = re.sub(r"(?i)#shorts\b", "", data["title"]).strip()
                if "tags" in data and isinstance(data["tags"], list):
                    data["tags"] = [t for t in data["tags"] if "short" not in t.lower()] or ["#documentary", "#mystery", "#science"]
                return VideoScript(**data)
            except Exception as e:
                logger.warning(f"Longform model {model_candidate} failed: {e}. Trying next candidate...")

        logger.error(f"All Gemini models failed for longform. Using fallback for {target_topic}.")
        return self._get_fallback_longform_script(target_topic, category_name)

    def _get_fallback_longform_script(self, topic: str, category: str = "Deep-Dive Documentary") -> VideoScript:
        emotions = [
            "concentration", "anticipation", "confusion", "surprise", "fear",
            "concentration", "contempt", "anxiety", "surprise", "sadness",
            "concentration", "discovery" if False else "anticipation", "relief", "pride", "concentration"
        ]
        scenes = []
        for idx in range(1, 16):
            narration = (
                f"In part {idx} of our investigation into {topic}, the documented historical and scientific records reveal a layer of complexity that few researchers ever anticipated. "
                f"Each piece of archival evidence points toward an extraordinary sequence of events that challenges conventional explanations. "
                f"When specialists cross-referenced these primary measurements, the resulting pattern left the scientific community searching for answers."
            )
            scenes.append(
                Scene(
                    scene_number=idx,
                    voiceover_text=narration,
                    subtitle_text=narration,
                    visual_prompt=f"cinematic 16:9 widescreen film still, atmospheric lighting, documentary investigation scene {idx} of {topic}",
                    character_emotion=emotions[(idx - 1) % len(emotions)],
                    keywords=["documentary investigation", "archival mystery"]
                )
            )
        return VideoScript(
            topic=topic,
            category=category,
            title=f"The Unsolved Files: {topic} | Full Documentary",
            hook=f"Behind the official record of {topic} lies an extraordinary mystery.",
            description=f"An in-depth widescreen documentary investigating the evidence, anomalies, and scientific mysteries surrounding {topic}.",
            tags=["#documentary", "#mystery", "#science", "#history", "#investigation"],
            scenes=scenes
        )
