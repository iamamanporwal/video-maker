"""python vo.py: Hindi (desi gaali) narration, ElevenLabs direct API (premade Brian, eleven_v3) → out/words.json.

TTS gets Devanagari (clean Hindi pronunciation); captions show the 1:1 Hinglish tokens. Each line is tied to the
English beat it replaces (`en` = that beat's time in the English learn-blender cut, `at` = which Hinglish word
lands on it), so scene.py can warp every English key time onto the Hindi VO. The gaalis are for Blender (and the
"maarchod" is praise for Vi3W), never aimed at a real person.
"""
import json, os, sys
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / "src"))
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))
from reelforge.shorts import tts  # noqa: E402

VOICE = {"id": "nPczCjzI2devNBz1zQrb", "model": "eleven_v3", "stability": 0.5}      # Brian (premade)

# (english beat s, word index that lands on it, Hinglish caption, Devanagari spoken; same word count, tags excluded)
LINES = [
    (0.05, 0, "Socho, agar tum aaj Blender seekhne baitho toh?", "सोचो, अगर तुम आज Blender सीखने बैठो तो?"),
    (2.47, 0, "Pehla din. Blender khola, aur saamne ek bhosdiwala grey cube ghoor raha hai.",
     "पहला दिन। Blender खोला, और सामने एक भोसड़ीवाला ग्रे क्यूब घूर रहा है।"),
    (6.82, 0, "300 buttons.", "तीन-सौ बटन।"),
    (8.12, 0, "Idea? Zero.", "आइडिया? ज़ीरो।"),
    (9.62, 0, "Toh tumne woh famous donut tutorial lagaya.", "तो तुमने वो फ़ेमस डोनट ट्यूटोरियल लगाया।"),
    (12.45, 0, "4 ghante baad...", "चार घंटे बाद..."),
    (13.58, 0, "donut nahi, behenchod truck ka tyre ban gaya.", "[laughs] डोनट नहीं, बहनचोद ट्रक का टायर बन गया।"),
    (15.26, 0, "Din 30.", "तीसवाँ दिन।"),
    (17.05, 1, "Roz 19 ghante.", "रोज़ उन्नीस घंटे।"),
    (18.74, 0, "Na dhoop, na dost.", "ना धूप, ना दोस्त।"),
    (21.02, 0, "Bas tum aur yeh saale shortcuts.", "बस तुम और ये साले शॉर्टकट्स।"),
    (22.88, 0, "Aakhir mein render dabaya.", "आख़िर में रेंडर दबाया।"),
    (24.26, 0, "Time dikha raha hai: 9 ghante.", "टाइम दिखा रहा है: नौ घंटे।"),
    (26.80, 0, "Toh baith ke wait kiya.", "तो बैठ के वेट किया।"),
    (28.42, 1, "Ek burger khaya.", "एक बर्गर खाया।"),
    (29.25, 0, "Phir doosra.", "फिर दूसरा।"),
    (30.46, 1, "Phir 14 aur.", "फिर चौदह और।"),
    (32.29, 0, "20 kilo chadh gaye.", "बीस किलो चढ़ गए।"),
    (33.87, 0, "Aur 99 percent pe...", "और निन्यानवे परसेंट पे..."),
    (36.06, 0, "Blender crash. Behenchod!", "[shouting] Blender क्रैश। बहनचोद!"),
    (38.27, 0, "Save kiya tha? Nahi. Maa chud gayi.", "सेव किया था? नहीं। माँ चुद गई।"),
    (39.55, 0, "Chhe mahine. Ek kursi.", "छह महीने। एक कुर्सी।"),
    (41.61, 0, "Model? Zero. Behenchod Blender.", "मॉडल? ज़ीरो। बहनचोद Blender।"),
    (42.99, 0, "Ya phir... bas sketch banao.", "[excited] या फिर... बस स्केच बनाओ।"),
    (45.87, 0, "Vi3W pe kuch bhi draw karo,", "व्यू पे कुछ भी ड्रॉ करो,"),
    (47.74, 0, "aur woh 3D model ban jaata hai,", "और वो थ्री-डी मॉडल बन जाता है,"),
    (50.18, 1, "sirf 30 second mein!", "सिर्फ़ तीस सेकंड में!"),
    (51.49, 0, "Na cube,", "ना क्यूब,"),
    (52.66, 0, "na crash,", "ना क्रैश,"),
    (53.89, 0, "na burger.", "ना बर्गर।"),
    (None, 0, "Vi3W maarchod hai bhai, maza aa gaya!", "[laughs] व्यू मारचोद है भाई, मज़ा आ गया!"),
]

if __name__ == "__main__":
    pub = D / "out"
    deva = " ".join(d for *_, d in LINES)
    mp3, words, dur = tts(D, pub, VOICE, deva, {})
    roman = [t for *_, r, _ in LINES for t in r.split()]
    assert len(words) == len(roman), (len(words), len(roman))
    words = [(a, b, r) for (a, b, _), r in zip(words, roman)]
    anchors, i = [], 0
    for en, at, r, _ in LINES:
        if en is not None:
            anchors.append((en, words[i + at][0]))
        i += len(r.split())
    anchors.append((55.5, words[-1][1] + 0.7))                          # English story end ↔ Hindi story end
    (pub / "words.json").write_text(json.dumps({"mp3": str(pub / mp3), "dur": dur, "words": words,
                                                "anchors": anchors}, ensure_ascii=False))
    print(f"{dur:.1f}s, {len(words)} words → {mp3}; story end {anchors[-1][1]:.2f}s")
