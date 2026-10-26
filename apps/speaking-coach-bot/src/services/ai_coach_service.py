import json
import logging
import random
from typing import Dict, Any, List, Optional

try:
    from pydantic import BaseModel, Field, model_validator
except ImportError:
    from dataclasses import dataclass, field

    def Field(*args, **kwargs):
        default_factory = kwargs.get("default_factory")
        if default_factory is not None:
            return field(default_factory=default_factory)
        return field(default=kwargs.get("default"))

    @dataclass
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = logging.getLogger(__name__)


class GrammarSlip(BaseModel):
    """Specific grammatical or phrasing mistake identified in speech."""

    original: str = Field(description="Phrase spoken by the user")
    correction: str = Field(description="Native, correct phrasing")
    explanation: str = Field(default="", description="Quick pedagogical reason")


class SpeakingFeedback(BaseModel):
    """Structured evaluation feedback from AI Speaking Coach."""

    transcript: str = Field(description="Exact verbatim transcription of what the user said")
    fluency_score: int = Field(default=80, description="Fluency score between 1 and 100")
    cefr_level: str = Field(default="B1", description="Estimated CEFR level: A1, A2, B1, B2, C1, or C2")
    ielts_band: float = Field(default=6.0, description="Estimated IELTS Speaking Band between 4.0 and 9.0")
    grammar_slips: List[GrammarSlip] = Field(
        default_factory=list,
        description="List of identified grammar slips with corrections",
    )
    vocabulary_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions for higher-level or idiomatic vocabulary",
    )
    pronunciation_notes: List[str] = Field(
        default_factory=list,
        description="Tips on clarity, tricky consonant clusters, or syllable stress",
    )
    conversational_reply: str = Field(
        description="Spoken in-character response replying to the user and asking a follow-up question"
    )


class ShadowingFeedback(BaseModel):
    """Evaluation result for Shadowing Mode (pronunciation & rhythm matching)."""

    match_score: int = Field(default=85, description="Pronunciation and wording accuracy percentage (0-100)")
    transcribed_text: str = Field(description="Verbatim transcription of user's shadowing attempt")
    mispronounced_words: List[str] = Field(
        default_factory=list,
        description="List of words where pronunciation or stress was off",
    )
    cadence_feedback: str = Field(
        default="Good natural rhythm.",
        description="Notes on pacing, pauses, and speech linking",
    )
    praise_message: str = Field(
        default="Great attempt!",
        description="Encouraging feedback for the learner",
    )


class IELTSMockFeedback(BaseModel):
    """Official 4-criteria IELTS Speaking Mock Exam Scorecard."""

    overall_band: float = Field(default=6.5, description="Official Overall Band Score (0.0 - 9.0, half-band increments)")
    fluency_coherence: float = Field(default=6.5, description="Band score for Fluency and Coherence (FC)")
    lexical_resource: float = Field(default=6.5, description="Band score for Lexical Resource (LR)")
    grammar_accuracy: float = Field(default=6.0, description="Band score for Grammatical Range and Accuracy (GRA)")
    pronunciation: float = Field(default=7.0, description="Band score for Pronunciation (PR)")
    strengths: List[str] = Field(default_factory=list, description="Candidate key speaking strengths observed")
    weaknesses: List[str] = Field(default_factory=list, description="Identified linguistic weaknesses and hesitations")
    key_recommendations_for_band_plus: str = Field(
        default="Work on complex compound sentences and idiom usage.",
        description="Concrete, actionable advice to leap to the next +1.0 Band",
    )
    examiner_summary: str = Field(
        default="A competent performance with good communicative efficacy.",
        description="Official examiner comprehensive summary",
    )


class PhonemeFeedback(BaseModel):
    """Evaluation result for Phoneme & Minimal Pairs practice."""

    accuracy_score: int = Field(default=85, description="Acoustic accuracy percentage (0-100)")
    detected_words: str = Field(description="Transcription of the target words/phrases detected")
    target_ipa: str = Field(description="Target IPA phonetic transcription, e.g. /θɪŋk/ vs /sɪŋk/")
    detected_ipa: str = Field(description="Detected IPA phonetic transcription produced by candidate")
    is_distinction_clear: bool = Field(default=True, description="Whether the phoneme distinction was acoustically distinct")
    mouth_position_tip: str = Field(
        default="Place tongue tip between teeth for /θ/. Do not let air hiss like /s/.",
        description="Physical anatomical instructions for tongue, teeth, lips, or airflow",
    )
    coaching_summary: str = Field(
        default="Good phonetic distinction!",
        description="Encouraging actionable coaching comment",
    )


class TenseEvaluationFeedback(BaseModel):
    """Evaluation feedback for a specific targeted English Tense drill."""

    transcribed_text: str = Field(default="", description="Exact transcript of what the learner said")
    target_tense: str = Field(default="", description="Name of the target tense practiced")
    accuracy_score: int = Field(default=85, description="Tense structure accuracy score between 0 and 100")
    is_target_tense_used: bool = Field(default=True, description="Whether the learner successfully applied the target tense")
    verb_form_analysis: str = Field(default="", description="Analysis of verbs and auxiliary verbs used")
    grammar_corrections: List[GrammarSlip] = Field(default_factory=list, description="Any identified slips or mistakes")
    coaching_tip: str = Field(default="", description="Concise pedagogical tip for mastering this tense")
    conversational_reply: str = Field(default="", description="Natural spoken conversational follow-up reply in context")

    @model_validator(mode="before")
    @classmethod
    def remap_legacy_or_alias_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "user_transcript" in values and "transcribed_text" not in values:
                values["transcribed_text"] = values["user_transcript"]
            if "tense_accuracy" in values and "accuracy_score" not in values:
                values["accuracy_score"] = values["tense_accuracy"]
            if "is_correct_tense" in values and "is_target_tense_used" not in values:
                values["is_target_tense_used"] = values["is_correct_tense"]
            if "corrected_sentence" in values and "verb_form_analysis" not in values:
                values["verb_form_analysis"] = values["corrected_sentence"]
            if "explanation" in values and "coaching_tip" not in values:
                values["coaching_tip"] = values["explanation"]
            if "coaching_comment" in values and "conversational_reply" not in values:
                values["conversational_reply"] = values["coaching_comment"]
            if "target_tense_used" in values and "target_tense" not in values:
                values["target_tense"] = values["target_tense_used"]
        return values

    @property
    def user_transcript(self) -> str:
        return self.transcribed_text

    @property
    def tense_accuracy(self) -> int:
        return self.accuracy_score

    @property
    def is_correct_tense(self) -> bool:
        return self.is_target_tense_used

    @property
    def target_tense_used(self) -> str:
        return self.target_tense

    @property
    def corrected_sentence(self) -> str:
        return self.verb_form_analysis

    @property
    def explanation(self) -> str:
        return self.coaching_tip

    @property
    def coaching_comment(self) -> str:
        return self.conversational_reply


SCENARIO_PROMPTS = {
    "Free Conversation": "You are a warm, encouraging English conversation partner. Discuss everyday topics naturally.",
    "Job Interview": "You are a senior hiring manager conducting a job interview. Act in-character, ask professional behavioral and situational questions.",
    "Cafe & Dining": "You are a friendly barista at a specialty coffee shop. Greet the customer, take orders, and discuss menu choices.",
    "Airport Immigration": "You are an international border control officer. Ask about travel itinerary, purpose of visit, and accommodation.",
    "Tech Standup": "You are an engineering manager in an agile daily standup. Ask about yesterday's deliverables, today's plans, and blockers.",
}

TOPICS_BY_LEVEL = {
    "Beginner": [
        "Tell me about your favorite food and how often you eat it.",
        "Describe what you usually do on a typical Sunday morning.",
        "What is your favorite hobby and why do you enjoy it?",
        "Describe your hometown: is it crowded, quiet, modern, or traditional?",
        "Talk about a movie or series you recently watched.",
    ],
    "Intermediate": [
        "If you could travel anywhere in the world tomorrow with all expenses paid, where would you go and why?",
        "Do you prefer working remotely from home or working in an office? Explain your reasons.",
        "What is a skill you have always wanted to master, and what has stopped you so far?",
        "How has technology changed the way you communicate with family and friends?",
        "Describe a challenge you faced recently and how you resolved it.",
    ],
    "Advanced": [
        "To what extent do you think artificial intelligence will transform the future job market over the next decade?",
        "Discuss the balance between economic development and environmental conservation in developing nations.",
        "Is privacy a fundamental human right in the modern digital era, or is it an illusion?",
        "Analyze the impact of social media algorithms on public discourse and polarization.",
        "How should education systems adapt to cultivate critical thinking rather than rote memorization?",
    ],
}

SHADOWING_TARGET_BANK = {
    "Beginner": [
        "Have a wonderful and productive day ahead!",
        "Could you please tell me where the nearest train station is?",
        "I really enjoy listening to calm acoustic music in the evening.",
        "What time does the supermarket close on weekends?",
        "It's a pleasure to meet you and learn about your projects.",
    ],
    "Intermediate": [
        "I would've called you earlier, but I completely lost track of time.",
        "To be honest, adapting to remote work required significant discipline.",
        "Could you walk me through the key takeaways from yesterday's meeting?",
        "If everything goes according to schedule, we should wrap up by Friday.",
        "It's essential to strike a healthy balance between ambition and well-being.",
    ],
    "Advanced": [
        "The technological breakthrough substantially accelerated their developmental trajectory.",
        "Navigating ambiguity with strategic resilience is paramount in leadership.",
        "Such inadvertent discrepancies often precipitate unforeseen organizational complications.",
        "We must meticulously corroborate the underlying hypotheses prior to deployment.",
        "Her articulate discourse seamlessly synthesized complex macroeconomic principles.",
    ],
}

IELTS_QUESTION_PACKS = [
    {
        "topic": "Technology, Daily Life & Digital Habits",
        "part1": [
            "Do you use technology a lot in your daily work or study routine?",
            "What kind of mobile apps or digital tools do you find most useful, and why?",
            "Do you think people spend too much time on their smartphones nowadays?",
        ],
        "part2": {
            "title": "A digital device or app that changed how you live or work",
            "prompt": "Describe a digital device or software application that has greatly helped you in your daily life.",
            "bullet_points": [
                "What device or app it is",
                "When and how you first started using it",
                "What you primarily use it for",
                "And explain why this tool has been so impactful or important to you.",
            ],
        },
        "part3": [
            "In what ways has the internet altered human communication compared to past decades?",
            "Do you think artificial intelligence will replace jobs, or will it create new opportunities for workers?",
        ],
    },
    {
        "topic": "Travel, Tourism & Cross-Cultural Experiences",
        "part1": [
            "Do you enjoy traveling to unfamiliar places, and why?",
            "Which destination in your country would you recommend to foreign tourists?",
            "Do you prefer traveling alone or in a group with friends or family?",
        ],
        "part2": {
            "title": "A memorable trip or journey you took in the past",
            "prompt": "Describe a memorable journey or trip that left a strong impression on you.",
            "bullet_points": [
                "Where you traveled to",
                "Who you went with",
                "What memorable activities you did there",
                "And explain why this journey was so unforgettable for you.",
            ],
        },
        "part3": [
            "What are the main economic benefits and environmental drawbacks of international tourism?",
            "How can travelers respect local traditions and cultural norms when visiting a foreign country?",
        ],
    },
    {
        "topic": "Career, Education & Personal Ambition",
        "part1": [
            "What do you find most fulfilling about your current studies or profession?",
            "Did you have a favorite subject at school when you were younger?",
            "Is it easy for young graduates to find suitable employment in your country today?",
        ],
        "part2": {
            "title": "An important ambition or life goal you hope to achieve",
            "prompt": "Describe an ambitious goal or career milestone you are currently working towards.",
            "bullet_points": [
                "What the goal or ambition is",
                "When you first decided to pursue it",
                "What steps or sacrifices are needed to reach it",
                "And explain why reaching this milestone matters so much to you.",
            ],
        },
        "part3": [
            "Should universities focus more on practical vocational skills or abstract theoretical knowledge?",
            "What qualities define an effective leader in a modern globalized workplace?",
        ],
    },
]

MINIMAL_PAIRS_CATALOG = {
    "th_vs_s": {
        "title": "👅 /θ/ vs /s/ (Dental vs Alveolar Fricative)",
        "description": "Membedakan bunyi 'th' desis lidah (/θ/) dengan 's' biasa (/s/). Masalah umum yang sering membuat 'think' terdengar seperti 'sink'.",
        "pairs": [
            {
                "id": "th_s_think_sink",
                "label": "think vs sink",
                "word_a": "think",
                "ipa_a": "/θɪŋk/",
                "word_b": "sink",
                "ipa_b": "/sɪŋk/",
                "sentence": "I think the heavy boat will sink.",
                "mouth_tip": "Untuk /θ/ (think): Tempatkan ujung lidah di antara gigi seri atas & bawah, lalu tiupkan udara lembut. Untuk /s/ (sink): Rapatkan gigi dan lidah berada di belakang gigi atas.",
            },
            {
                "id": "th_s_thick_sick",
                "label": "thick vs sick",
                "word_a": "thick",
                "ipa_a": "/θɪk/",
                "word_b": "sick",
                "ipa_b": "/sɪk/",
                "sentence": "The thick fog made him feel sick.",
                "mouth_tip": "Jangan biarkan lidah bersembunyi saat mengucapkan 'thick'. Biarkan ujung lidah menyentuh tepi gigi atas.",
            },
            {
                "id": "th_s_mouth_mouse",
                "label": "mouth vs mouse",
                "word_a": "mouth",
                "ipa_a": "/maʊθ/",
                "word_b": "mouth",
                "ipa_b": "/maʊs/",
                "sentence": "The cat opened its mouth and caught a mouse.",
                "mouth_tip": "Di akhir kata 'mouth', keluarkan ujung lidah sedikit. Pada 'mouse', tutup gigi dan buat bunyi mendesis 'ss'.",
            },
        ],
    },
    "v_vs_b": {
        "title": "👄 /v/ vs /b/ (Labiodental vs Bilabial)",
        "description": "Membedakan getaran gigi-bibir (/v/) dengan letupan dua bibir (/b/). Sering tertukar menjadi 'berry' atau 'ban'.",
        "pairs": [
            {
                "id": "v_b_very_berry",
                "label": "very vs berry",
                "word_a": "very",
                "ipa_a": "/ˈvɛri/",
                "word_b": "berry",
                "ipa_b": "/ˈbɛri/",
                "sentence": "This sweet berry is very delicious.",
                "mouth_tip": "Untuk /v/ (very): Sentuhkan gigi seri atas ke bibir bawah bagian dalam, rasakan getaran pita suara. Untuk /b/ (berry): Rapatkan kedua bibir lalu lepaskan dengan letupan udara.",
            },
            {
                "id": "v_b_van_ban",
                "label": "van vs ban",
                "word_a": "van",
                "ipa_a": "/væn/",
                "word_b": "ban",
                "ipa_b": "/bæn/",
                "sentence": "The city decided to ban that old delivery van.",
                "mouth_tip": "Pastikan gigi atas menggigit lembut bibir bawah saat memulai 'van'.",
            },
            {
                "id": "v_b_vote_boat",
                "label": "vote vs boat",
                "word_a": "vote",
                "ipa_a": "/voʊt/",
                "word_b": "boat",
                "ipa_b": "/boʊt/",
                "sentence": "We will vote while traveling on the boat.",
                "mouth_tip": "'Vote' dimulai dengan gesekan gigi-bibir, sedangkan 'boat' dimulai dengan kedua bibir tertutup rapat.",
            },
        ],
    },
    "l_vs_r": {
        "title": "👅 /l/ vs /r/ (Lateral vs Approximant)",
        "description": "Membedakan lidah menempel di langit-langit (/l/) dengan lidah ditarik melengkung ke belakang tanpa menyentuh langit-langit (/r/).",
        "pairs": [
            {
                "id": "l_r_light_right",
                "label": "light vs right",
                "word_a": "light",
                "ipa_a": "/laɪt/",
                "word_b": "right",
                "ipa_b": "/raɪt/",
                "sentence": "Turn right at the green traffic light.",
                "mouth_tip": "Untuk /l/ (light): Tempelkan ujung lidah kuat-kuat ke gusi belakang gigi atas. Untuk /r/ (right): Tarik lidah ke belakang mulut melengkung tanpa menyentuh atap mulut sama sekali.",
            },
            {
                "id": "l_r_collect_correct",
                "label": "collect vs correct",
                "word_a": "collect",
                "ipa_a": "/kəˈlɛkt/",
                "word_b": "correct",
                "ipa_b": "/kəˈrɛkt/",
                "sentence": "Make sure you collect the correct answers.",
                "mouth_tip": "Pada 'collect', biarkan udara lewat di samping lidah yang menempel. Pada 'correct', bentuk bibir sedikit membulat seperti huruf O.",
            },
            {
                "id": "l_r_glass_grass",
                "label": "glass vs grass",
                "word_a": "glass",
                "ipa_a": "/ɡlæs/",
                "word_b": "grass",
                "ipa_b": "/ɡræs/",
                "sentence": "He dropped a glass bottle on the green grass.",
                "mouth_tip": "Setelah bunyi /g/, segera tempelkan lidah untuk 'glass', atau gulung lidah ke belakang untuk 'grass'.",
            },
        ],
    },
    "sh_vs_s": {
        "title": "🌬️ /ʃ/ vs /s/ (Postalveolar vs Alveolar)",
        "description": "Membedakan desisan 'sh' tebal (/ʃ/) dengan 's' tajam (/s/). Contoh klasik: 'sheet' vs 'seat'.",
        "pairs": [
            {
                "id": "sh_s_sheet_seat",
                "label": "sheet vs seat",
                "word_a": "sheet",
                "ipa_a": "/ʃiːt/",
                "word_b": "seat",
                "ipa_b": "/siːt/",
                "sentence": "Please take a seat and take a clean sheet of paper.",
                "mouth_tip": "Untuk /ʃ/ (sheet): Majukan bibir membulat (seperti menyuruh orang diam 'shhh'). Untuk /s/ (seat): Tarik sudut bibir ke samping seperti tersenyum tipis.",
            },
            {
                "id": "sh_s_sheep_ship",
                "label": "sheep vs ship",
                "word_a": "sheep",
                "ipa_a": "/ʃiːp/",
                "word_b": "ship",
                "ipa_b": "/ʃɪp/",
                "sentence": "We saw white sheep standing on the cargo ship.",
                "mouth_tip": "Ini melatih vokal panjang /iː/ (sheep) vs vokal rileks pendek /ɪ/ (ship) dengan awalan /ʃ/ yang tebal.",
            },
            {
                "id": "sh_s_shine_sign",
                "label": "shine vs sign",
                "word_a": "shine",
                "ipa_a": "/ʃaɪn/",
                "word_b": "sign",
                "ipa_b": "/saɪn/",
                "sentence": "The bright lights shine on the highway sign.",
                "mouth_tip": "Jangan biarkan lidah mendatar pada 'shine'. Angkat badan lidah mendekati langit-langit keras.",
            },
        ],
    },
    "ae_vs_e": {
        "title": "🗣️ /æ/ vs /e/ (Open Front vs Mid Front)",
        "description": "Membedakan vokal 'a' lebar rahang terbuka (/æ/) dengan vokal 'e' rileks (/e/). Menghindari salah arti antara 'bad' dan 'bed'.",
        "pairs": [
            {
                "id": "ae_e_bad_bed",
                "label": "bad vs bed",
                "word_a": "bad",
                "ipa_a": "/bæd/",
                "word_b": "bed",
                "ipa_b": "/bɛd/",
                "sentence": "Sleeping on a bad mattress makes me miss my bed.",
                "mouth_tip": "Untuk /æ/ (bad): Buka rahang mulut ke bawah selebar dua jari. Untuk /e/ (bed): Buka mulut secukupnya, rahang lebih rileks dan lidah di tengah.",
            },
            {
                "id": "ae_e_man_men",
                "label": "man vs men",
                "word_a": "man",
                "ipa_a": "/mæn/",
                "word_b": "men",
                "ipa_b": "/mɛn/",
                "sentence": "One tall man met five other men.",
                "mouth_tip": "'Man' (tunggal) butuh bukaan rahang ke bawah yang lebih lebar daripada 'men' (jamak).",
            },
            {
                "id": "ae_e_pan_pen",
                "label": "pan vs pen",
                "word_a": "pan",
                "ipa_a": "/pæn/",
                "word_b": "pen",
                "ipa_b": "/pɛn/",
                "sentence": "He put the frying pan down and grabbed a ballpoint pen.",
                "mouth_tip": "Turunkan rahang bawah saat membunyikan 'pan'.",
            },
        ],
    },
    "p_vs_f": {
        "title": "💨 /p/ vs /f/ (Bilabial Plosive vs Labiodental Fricative)",
        "description": "Membedakan letupan dua bibir (/p/) dengan desisan gigi-bibir (/f/). Sangat umum terjadi pada penutur dialek nusantara.",
        "pairs": [
            {
                "id": "p_f_pan_fan",
                "label": "pan vs fan",
                "word_a": "pan",
                "ipa_a": "/pæn/",
                "word_b": "fan",
                "ipa_b": "/fæn/",
                "sentence": "She used a handheld fan while watching the frying pan.",
                "mouth_tip": "Untuk /p/ (pan): Rapatkan bibir atas & bawah, tahan nafas sejenak, lalu lepaskan 'pop'. Untuk /f/ (fan): Gigi atas menyentuh bibir bawah, tiupkan udara terus menerus tanpa letupan.",
            },
            {
                "id": "p_f_copy_coffee",
                "label": "copy vs coffee",
                "word_a": "copy",
                "ipa_a": "/ˈkɑːpi/",
                "word_b": "coffee",
                "ipa_b": "/ˈkɔːfi/",
                "sentence": "Please copy this document before having your morning coffee.",
                "mouth_tip": "Bunyi tengah pada 'copy' adalah letupan bibir /p/, sedangkan pada 'coffee' adalah desisan gigi-bibir /f/.",
            },
            {
                "id": "p_f_pull_full",
                "label": "pull vs full",
                "word_a": "pull",
                "ipa_a": "/pʊl/",
                "word_b": "full",
                "ipa_b": "/fʊl/",
                "sentence": "Do not pull the rope when the cart is completely full.",
                "mouth_tip": "Bibir harus menutup sempurna sebelum meletupkan 'pull'. Jangan biarkan udara bocor seperti 'full'.",
            },
        ],
    },
}


def get_phoneme_categories() -> List[Dict[str, Any]]:
    """Return all available phoneme categories for menu selection."""
    return [
        {
            "id": cat_id,
            "title": data["title"],
            "description": data["description"],
            "pairs_count": len(data["pairs"]),
        }
        for cat_id, data in MINIMAL_PAIRS_CATALOG.items()
    ]


def get_phoneme_pairs_by_category(category_id: str) -> List[Dict[str, Any]]:
    """Return list of minimal pairs under a specific category."""
    cat = MINIMAL_PAIRS_CATALOG.get(category_id)
    if not cat:
        return []
    return cat["pairs"]


def get_phoneme_pair(pair_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve details for a specific minimal pair drill by ID."""
    for cat_id, cat_data in MINIMAL_PAIRS_CATALOG.items():
        for pair in cat_data["pairs"]:
            if pair["id"] == pair_id:
                p = dict(pair)
                p["category_id"] = cat_id
                p["category_title"] = cat_data["title"]
                return p
    return None


def get_random_phoneme_pair() -> Dict[str, Any]:
    """Retrieve a random minimal pair across all categories."""
    all_pairs = []
    for cat_id, cat_data in MINIMAL_PAIRS_CATALOG.items():
        for pair in cat_data["pairs"]:
            p = dict(pair)
            p["category_id"] = cat_id
            p["category_title"] = cat_data["title"]
            all_pairs.append(p)
    return random.choice(all_pairs)




class AICoachService:
    """Service handling audio evaluation via Gemini Multimodal Audio."""

    def __init__(self, api_key: str, model_name: str = "gemini-3.1-flash-lite"):
        self.api_key = api_key
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key) if (genai and api_key) else None

    def get_speaking_topic(self, level: str = "Intermediate") -> str:
        """Return a random speaking prompt suited to the learner's proficiency level."""
        topics = TOPICS_BY_LEVEL.get(level, TOPICS_BY_LEVEL["Intermediate"])
        return random.choice(topics)

    def get_shadowing_target(self, level: str = "Intermediate") -> str:
        """Return a curated target sentence for Shadowing mode."""
        sentences = SHADOWING_TARGET_BANK.get(level, SHADOWING_TARGET_BANK["Intermediate"])
        return random.choice(sentences)

    def get_available_scenarios(self) -> List[str]:
        """Return list of supported roleplay scenarios."""
        return list(SCENARIO_PROMPTS.keys())

    async def evaluate_audio(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/ogg",
        target_level: str = "Intermediate",
        scenario: str = "Free Conversation",
        dialogue_history: Optional[List[Dict[str, str]]] = None,
    ) -> SpeakingFeedback:
        """Analyze audio using Gemini, estimating CEFR, IELTS band, grammar slips, and conversational reply."""
        if not self.client:
            raise RuntimeError("Gemini Client is not initialized. Ensure GEMINI_API_KEY is configured.")

        scenario_context = SCENARIO_PROMPTS.get(scenario, SCENARIO_PROMPTS["Free Conversation"])

        history_text = ""
        if dialogue_history:
            history_lines = []
            for turn in dialogue_history:
                speaker = "Learner" if turn.get("role") == "user" else "AI Partner"
                content = turn.get("content", "").strip()
                if content:
                    history_lines.append(f"- {speaker}: \"{content}\"")
            if history_lines:
                history_text = (
                    "\n--- Recent Conversation Context in this Scenario (Past Turns) ---\n"
                    + "\n".join(history_lines)
                    + "\n------------------------------------------------------------------\n"
                    "Instructions: The learner's audio input is the next response in this dialogue. "
                    "Ensure your 'conversational_reply' naturally references, follows up on, or develops "
                    "the ongoing topic and context established above.\n"
                )

        prompt = f"""
You are an expert English Speech Evaluator and Roleplay Partner.
Current Scenario Context: {scenario_context}
Learner Target Level: {target_level}
{history_text}
Listen carefully to the audio voice note.
Analyze the user's speech and return a strictly valid JSON response adhering to this schema:
{{
  "transcript": "Exact transcription of user speech",
  "fluency_score": 85,
  "cefr_level": "B2",
  "ielts_band": 6.5,
  "grammar_slips": [
    {{
      "original": "I am agree with that",
      "correction": "I agree with that",
      "explanation": "Use 'agree' as a verb directly without 'am'"
    }}
  ],
  "vocabulary_suggestions": [
    "Instead of 'good idea', try 'compelling proposal' or 'ingenious approach'"
  ],
  "pronunciation_notes": [
    "Ensure the final /t/ in 'restaurant' and syllable stress on the first syllable: RES-tau-rant"
  ],
  "conversational_reply": "In-character reply answering what they said, keeping the conversation engaging with 1 question."
}}

Criteria for CEFR / IELTS:
- A1/A2 (IELTS 3.5-4.5): Basic disjointed sentences, frequent pauses.
- B1 (IELTS 5.0-5.5): Able to maintain flow on familiar topics, minor grammar slips.
- B2 (IELTS 6.0-6.5): Effective operational proficiency, good range of vocabulary.
- C1/C2 (IELTS 7.0-8.5): Fluent, spontaneous, complex grammar with idiomatic ease.

Return ONLY raw JSON, with no markdown code fences or backticks.
"""

        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[audio_part, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )

            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            data = json.loads(raw_text.strip())

            # Convert grammar_slips dicts to GrammarSlip models if present
            slips = []
            for item in data.get("grammar_slips", []):
                if isinstance(item, dict):
                    slips.append(GrammarSlip(**item))
                elif isinstance(item, str):
                    slips.append(GrammarSlip(original=item, correction=item))
            data["grammar_slips"] = slips

            return SpeakingFeedback(**data)

        except Exception as err:
            logger.error("Error evaluating audio with Gemini: %s", err)
            raise

    async def evaluate_shadowing_attempt(
        self,
        audio_bytes: bytes,
        target_text: str,
        mime_type: str = "audio/ogg",
    ) -> ShadowingFeedback:
        """Evaluate how accurately the user mimicked the target sentence in Shadowing mode."""
        if not self.client:
            raise RuntimeError("Gemini Client is not initialized.")

        prompt = f"""
You are an expert English Pronunciation and Shadowing Coach.
The learner was instructed to repeat/shadow this EXACT target sentence:
TARGET SENTENCE: "{target_text}"

Listen carefully to their voice note.
Compare their spoken audio with the TARGET SENTENCE.
Return a strictly valid JSON response adhering to this schema:
{{
  "match_score": 92,
  "transcribed_text": "Exact words spoken by the learner in the audio",
  "mispronounced_words": ["words", "that", "were", "mispronounced"],
  "cadence_feedback": "Notes on whether the rhythm, pauses, and intonation sounded natural or robotic",
  "praise_message": "Warm, encouraging 1-sentence compliment highlighting their effort"
}}

Scoring Guidelines for match_score (0 - 100):
- 90 - 100: Flawless wording, accurate pronunciation, native-like cadence.
- 75 - 89: Minor slips in rhythm or 1-2 words slightly muffled, but clearly recognizable.
- 50 - 74: Noticeable omissions, dropped words, or heavy foreign accent impeding comprehension.
- Below 50: Completely different sentence or incomprehensible.

Return ONLY raw JSON, with no backticks or markdown fences.
"""

        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[audio_part, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )

            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            data = json.loads(raw_text.strip())
            return ShadowingFeedback(**data)
        except Exception as err:
            logger.error("Error evaluating shadowing attempt with Gemini: %s", err)
            raise

    def build_ielts_questions(self, exam_type: str = "express") -> List[Dict[str, Any]]:
        """Construct a structured sequence of IELTS exam questions."""
        pack = random.choice(IELTS_QUESTION_PACKS)
        questions: List[Dict[str, Any]] = []

        if exam_type == "express":
            # 1 Question Part 1, 1 Cue Card Part 2, 1 Question Part 3 (Total: 3)
            questions.append({
                "step_index": 0,
                "part": 1,
                "part_title": "Part 1: Introduction & Interview",
                "type": "interview",
                "text": pack["part1"][0],
                "cue_card": None,
            })
            questions.append({
                "step_index": 1,
                "part": 2,
                "part_title": "Part 2: The Long Turn (Cue Card)",
                "type": "cue_card",
                "text": pack["part2"]["prompt"],
                "cue_card": pack["part2"],
            })
            questions.append({
                "step_index": 2,
                "part": 3,
                "part_title": "Part 3: Two-way Discussion",
                "type": "discussion",
                "text": pack["part3"][0],
                "cue_card": None,
            })
        else:
            # Full Simulation: 3 Questions Part 1, 1 Cue Card Part 2, 2 Questions Part 3 (Total: 6)
            for idx, q_text in enumerate(pack["part1"]):
                questions.append({
                    "step_index": len(questions),
                    "part": 1,
                    "part_title": f"Part 1: Introduction (Q{idx+1}/3)",
                    "type": "interview",
                    "text": q_text,
                    "cue_card": None,
                })
            questions.append({
                "step_index": len(questions),
                "part": 2,
                "part_title": "Part 2: The Long Turn (Cue Card)",
                "type": "cue_card",
                "text": pack["part2"]["prompt"],
                "cue_card": pack["part2"],
            })
            for idx, q_text in enumerate(pack["part3"]):
                questions.append({
                    "step_index": len(questions),
                    "part": 3,
                    "part_title": f"Part 3: Two-way Discussion (Q{idx+1}/2)",
                    "type": "discussion",
                    "text": q_text,
                    "cue_card": None,
                })

        return questions

    async def transcribe_voice_note(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/ogg",
    ) -> str:
        """Quickly transcribe speech verbatim using Gemini Multimodal Audio."""
        if not self.client:
            return "Sample transcribed answer from candidate."

        prompt = (
            "Transcribe verbatim everything spoken in this audio voice note into plain English text. "
            "Do not add any preamble, greeting, markdown formatting, or explanations. "
            "Only return the exact spoken English text. If silence or non-English, describe briefly."
        )

        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[audio_part, prompt],
                config=types.GenerateContentConfig(temperature=0.1),
            )
            return response.text.strip()
        except Exception as err:
            logger.error("Error transcribing voice note with Gemini: %s", err)
            return "(Transcription failed due to audio clarity or network)"

    async def evaluate_ielts_mock_exam(
        self,
        exam_type: str,
        questions: List[Dict[str, Any]],
        responses: List[Dict[str, Any]],
    ) -> IELTSMockFeedback:
        """Evaluate complete IELTS Speaking interview responses against Cambridge/IDP rubrics."""
        if not self.client:
            return IELTSMockFeedback(
                overall_band=6.5,
                fluency_coherence=6.5,
                lexical_resource=6.5,
                grammar_accuracy=6.0,
                pronunciation=7.0,
                strengths=["Good natural pacing", "Clear task achievement on Cue Card"],
                weaknesses=["Occasional hesitation searching for academic vocabulary"],
                key_recommendations_for_band_plus="Incorporate idiomatic collocations and complex clause connectors (e.g. 'provided that', 'in spite of').",
                examiner_summary="The candidate communicated effectively with coherent structure and good general intelligibility.",
            )

        # Build transcript of the entire exam
        dialogue_transcript = []
        for idx, q in enumerate(questions):
            q_part = q.get("part_title", f"Part {q.get('part', 1)}")
            q_text = q.get("text", "")
            ans_text = responses[idx].get("transcript", "(No answer recorded)") if idx < len(responses) else "(Skipped)"
            dialogue_transcript.append(f"[{q_part}]\nExaminer: {q_text}\nCandidate: {ans_text}\n")

        full_exam_text = "\n".join(dialogue_transcript)

        prompt = f"""
You are an Official Senior IELTS Speaking Examiner accredited by Cambridge Assessment English and British Council.
You have just concluded an official IELTS Speaking Interview ({exam_type.upper()} format).

Here is the complete dialogue transcript of the exam:
=== BEGIN EXAM TRANSCRIPT ===
{full_exam_text}
=== END EXAM TRANSCRIPT ===

Evaluate the candidate strictly in accordance with the official IELTS 9-band Speaking Assessment Criteria:
1. Fluency and Coherence (FC) [0.0 - 9.0]
2. Lexical Resource (LR) [0.0 - 9.0]
3. Grammatical Range and Accuracy (GRA) [0.0 - 9.0]
4. Pronunciation (PR) [0.0 - 9.0]

Overall Band Score Calculation:
- Compute the arithmetic average of the 4 sub-scores.
- Round to the nearest official IELTS half-band (e.g., 6.25 -> 6.5, 6.75 -> 7.0, 6.125 -> 6.0).

Return a strictly valid JSON object adhering to this schema:
{{
  "overall_band": 6.5,
  "fluency_coherence": 6.5,
  "lexical_resource": 6.5,
  "grammar_accuracy": 6.0,
  "pronunciation": 7.0,
  "strengths": ["Clear articulation", "Direct answers without long pauses"],
  "weaknesses": ["Repetitive simple conjunctions ('and', 'because')", "Minor subject-verb agreement slips"],
  "key_recommendations_for_band_plus": "Specific actionable guidance on what the candidate must do to reach the next +1.0 Band.",
  "examiner_summary": "Comprehensive 2-3 sentence official examiner evaluation summarizing their overall communicative competence."
}}

Return ONLY raw JSON, with no backticks or markdown fences.
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )

            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            data = json.loads(raw_text.strip())
            return IELTSMockFeedback(**data)
        except Exception as err:
            logger.error("Error evaluating IELTS mock exam with Gemini: %s", err)
            raise

    async def evaluate_phoneme_attempt(
        self,
        audio_bytes: bytes,
        target_drill: Dict[str, Any],
        mime_type: str = "audio/ogg",
    ) -> PhonemeFeedback:
        """Evaluate acoustic distinction and pronunciation for a minimal pair drill."""
        if not self.client:
            raise RuntimeError("Gemini Client is not initialized.")

        word_a = target_drill.get("word_a", "")
        ipa_a = target_drill.get("ipa_a", "")
        word_b = target_drill.get("word_b", "")
        ipa_b = target_drill.get("ipa_b", "")
        sentence = target_drill.get("sentence", "")
        mouth_tip = target_drill.get("mouth_tip", "")

        prompt = f"""
You are an expert English Phonetician and Acoustic Pronunciation Coach.
The learner is practicing distinguishing this minimal pair:
- Word A: "{word_a}" ({ipa_a})
- Word B: "{word_b}" ({ipa_b})
- Practice Contrast Sentence: "{sentence}"
- Anatomical Placement Guide: "{mouth_tip}"

The learner was instructed to pronounce both words in contrast (e.g. "{word_a} ... {word_b}") and/or read the contrast sentence.

Listen carefully to the audio:
1. Did the candidate make a distinct acoustic distinction between {ipa_a} and {ipa_b}?
2. Analyze what was actually articulated (transcribe words and phonetic IPA).
3. Compute an accuracy score (0 - 100):
   - 90 - 100: Pristine phonetic contrast, clear distinction, native-like articulation.
   - 75 - 89: Recognizable difference, minor vowel reduction or slight consonant softness, but distinct.
   - 50 - 74: Blurry distinction where {word_a} sounds like {word_b} (e.g. said "sink" instead of "think").
   - Below 50: Failed to pronounce the target words or unintelligible.
4. Give a practical, physical mouth/tongue position tip in Indonesian for how to improve the sound.

Return a strictly valid JSON object adhering to this schema:
{{
  "accuracy_score": 90,
  "detected_words": "{word_a} and {word_b}",
  "target_ipa": "{ipa_a} vs {ipa_b}",
  "detected_ipa": "[{ipa_a}] vs [{ipa_b}]",
  "is_distinction_clear": true,
  "mouth_position_tip": "Tempatkan ujung lidah di antara gigi depan untuk {word_a}...",
  "coaching_summary": "Bagus sekali! Bunyi {ipa_a} terdengar jelas membedakannya dari {ipa_b}."
}}

Return ONLY raw JSON, with no backticks or markdown fences.
"""

        contents = [prompt]
        kwargs = {}
        if types:
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            contents = [audio_part, prompt]
            kwargs["config"] = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                **kwargs,
            )

            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            data = json.loads(raw_text.strip())
            return PhonemeFeedback(**data)
        except Exception as err:
            logger.error("Error evaluating phoneme attempt with Gemini: %s", err)
            raise

    async def evaluate_tense_exercise(
        self,
        audio_bytes: bytes,
        tense_id: str,
        mime_type: str = "audio/ogg",
    ) -> TenseEvaluationFeedback:
        """Evaluate a learner's targeted English Tenses speaking exercise using Gemini 2.0."""
        if not self.client:
            raise RuntimeError("Gemini Client is not initialized. Ensure GEMINI_API_KEY is configured.")

        tense_info = get_tense_detail(tense_id)
        if not tense_info:
            tense_info = {
                "title": tense_id,
                "formula": "Standard English Tense Rules",
                "concept": "Accurate verb usage",
                "example_sentence": "I am speaking English.",
            }

        prompt = f"""
You are an expert English Language Assessor and Pedagogy Specialist evaluating an audio recording for a TARGETED TENSES PRACTICE DRILL.

TARGET TENSE: {tense_info['title']}
GRAMMAR FORMULA: {tense_info['formula']}
USAGE CONCEPT: {tense_info['concept']}
EXAMPLE: {tense_info['example_sentence']}

TASK:
1. Transcribe the user's speech verbatim.
2. Evaluate if the speaker correctly used the TARGET TENSE structure ({tense_info['title']}: {tense_info['formula']}).
3. Assign an `accuracy_score` (0-100) specifically measuring their grammatical command of this target tense.
   - 90-100: Flawless tense usage with correct auxiliary verbs and participle/verb forms.
   - 70-89: Mostly correct with minor slip in auxiliary or inflection.
   - 50-69: Struggled with verb forms or mixed up tenses.
   - Below 50: Failed to use the target tense completely or unintelligible.
4. Analyze the verb forms used (auxiliaries, suffixes, base verbs).
5. Identify any grammar slips or tense misapplications.
6. Provide a concise coaching tip in Indonesian explaining how to master this specific tense.
7. Provide a warm, conversational spoken reply in natural English that continues the topic.

Return a strictly valid JSON object adhering to this schema:
{{
  "transcribed_text": "Exact user speech...",
  "target_tense": "{tense_info['title']}",
  "accuracy_score": 90,
  "is_target_tense_used": true,
  "verb_form_analysis": "Clear usage of auxiliary and target verb forms...",
  "grammar_corrections": [
    {{
      "original": "incorrect phrase",
      "correction": "corrected phrase",
      "explanation": "quick explanation in Indonesian"
    }}
  ],
  "coaching_tip": "Untuk {tense_info['title']}, pastikan selalu...",
  "conversational_reply": "That sounds great! Keep up the momentum..."
}}

Return ONLY raw JSON, with no backticks or markdown fences.
"""

        contents = [prompt]
        kwargs = {}
        if types:
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            contents = [audio_part, prompt]
            kwargs["config"] = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                **kwargs,
            )

            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            data = json.loads(raw_text.strip())
            return TenseEvaluationFeedback(**data)
        except Exception as err:
            logger.error("Error evaluating tense attempt with Gemini: %s", err)
            raise


TENSES_CATALOG: Dict[str, Dict[str, Any]] = {
    "pres_cont": {
        "id": "pres_cont",
        "title": "Present Continuous",
        "icon": "🔄",
        "concept": "Aktivitas yang sedang berlangsung detik ini juga atau tren saat ini",
        "formula": "Subject + is/am/are + Verb-ing",
        "example_sentence": "I am practicing my English speaking skills with my AI coach right now.",
        "speaking_scenario": "Bayangkan Anda sedang duduk di kafe atau taman kota yang ramai. Ceritakan apa yang sedang Anda lakukan dan apa yang sedang orang-orang di sekeliling Anda lakukan saat ini!",
    },
    "simple_pres": {
        "id": "simple_pres",
        "title": "Simple Present",
        "icon": "⏰",
        "concept": "Kebiasaan, rutinitas harian, dan fakta umum yang tidak berubah",
        "formula": "Subject + Verb-1 (tambah s/es untuk he/she/it)",
        "example_sentence": "I usually drink a cup of coffee every morning and study English for thirty minutes.",
        "speaking_scenario": "Ceritakan rutinitas harian Anda dari bangun tidur di pagi hari hingga malam hari. Apa saja kegiatan yang selalu Anda lakukan setiap hari?",
    },
    "simple_past": {
        "id": "simple_past",
        "title": "Simple Past",
        "icon": "⏳",
        "concept": "Peristiwa atau kejadian yang terjadi dan sudah tuntas di masa lampau",
        "formula": "Subject + Verb-2 (regular -ed atau irregular verb)",
        "example_sentence": "Last year, I traveled to a beautiful beach and learned how to surf with my best friends.",
        "speaking_scenario": "Ceritakan satu momen liburan, akhir pekan, atau peristiwa berkesan yang pernah Anda alami di masa lalu. Apa saja yang Anda lakukan di sana?",
    },
    "past_cont": {
        "id": "past_cont",
        "title": "Past Continuous",
        "icon": "⚡",
        "concept": "Aktivitas yang sedang berlangsung di masa lampau ketika ada kejadian lain memotongnya",
        "formula": "Subject + was/were + Verb-ing",
        "example_sentence": "I was walking home from work yesterday when it suddenly started raining heavily.",
        "speaking_scenario": "Ceritakan peristiwa ketika Anda sedang asyik melakukan sesuatu di masa lalu (misal sedang belajar, memasak, atau bekerja), lalu tiba-tiba ada hal tak terduga yang terjadi!",
    },
    "pres_perf": {
        "id": "pres_perf",
        "title": "Present Perfect",
        "icon": "🔗",
        "concept": "Pengalaman hidup seumur hidup atau tindakan masa lalu yang hasilnya masih relevan saat ini",
        "formula": "Subject + have/has + Verb-3 (Past Participle)",
        "example_sentence": "I have visited three different countries, and I have always wanted to explore Japan.",
        "speaking_scenario": "Ceritakan pengalaman unik atau pencapaian yang sudah pernah Anda capai dalam hidup, atau hal menarik yang belum pernah Anda coba tetapi sangat ingin Anda coba!",
    },
    "future": {
        "id": "future",
        "title": "Future Tense (Will / Going to)",
        "icon": "🚀",
        "concept": "Rencana yang sudah disusun (going to) atau keputusan spontan & prediksi masa depan (will)",
        "formula": "Subject + will / be going to + Verb-1",
        "example_sentence": "Next month, I am going to take an English test, and I will prepare thoroughly.",
        "speaking_scenario": "Ceritakan target, rencana perjalanan, atau cita-cita besar yang akan Anda wujudkan dalam 6 bulan hingga 1 tahun ke depan!",
    },
    "conditionals": {
        "id": "conditionals",
        "title": "Conditionals (If Clause)",
        "icon": "🔮",
        "concept": "Pengandaian situasi nyata (If + Present, Will...) atau imajinasi masa kini (If + Past, Would...)",
        "formula": "If + Simple Present, Subject + will + V1 / If + Simple Past, Subject + would + V1",
        "example_sentence": "If I had one million dollars, I would travel around the world and support education programs.",
        "speaking_scenario": "Jika Anda mendapatkan kesempatan tinggal di negara manapun di dunia selama satu tahun penuh secara gratis, negara mana yang akan Anda pilih dan apa yang akan Anda lakukan di sana?",
    },
}


def get_tenses_catalog() -> Dict[str, Dict[str, Any]]:
    """Return the complete catalog of 7 English Tenses drills."""
    return TENSES_CATALOG


def get_tense_detail(tense_id: str) -> Optional[Dict[str, Any]]:
    """Return detailed metadata for a specific tense by ID."""
    return TENSES_CATALOG.get(tense_id)


