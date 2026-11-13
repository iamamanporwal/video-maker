"""Blender-first-time: GreenBroRants-style "In this town, ..." Roblox story, edgier, ends on a real Vi3W robot + outro.

LINES = (id, text) in spoken order. Text is what the captions show; SAY maps it to what the TTS says.
"""
LINES = [
    ("h1", "In this town, whatever you make in Blender comes to life."),
    ("h2", "So people here are very careful."),
    ("a1", "My neighbor tried to model a donut."),
    ("a2", "Now a lumpy flesh donut lives in his garage and calls him daddy."),
    ("a3", "The mayor sculpted himself some abs. They crawled off in the night."),
    ("m1", "And me? I'd never opened Blender in my life."),
    ("m2", "Until today."),
    ("c1", "The first thing I saw was a little grey cube. So I did what every beginner does."),
    ("c2", "I deleted it."),
    ("c3", "The whole town went silent."),
    ("c4", "Because nobody. Deletes. The cube."),
    ("n1", "That night, it came back. Pissed off. And way, way bigger."),
    ("n2", "It ate the donut. It ate the mayor's abs. And it was coming for my house."),
    ("n3", "The only way to stop it? Make something stronger."),
    ("b1", "So I opened Blender again. Extrude. Bevel. What the fuck is a normal?"),
    ("b2", "I made a horse. With six legs. And a face on its ass."),
    ("b3", "It ran straight into a wall."),
    ("v1", "So I grabbed a pencil, drew a giant robot on paper, and threw it into Vi3W."),
    ("v2", "Thirty seconds later, a real 3D robot."),
    ("v3", "It punted the cube into space."),
    ("e1", "And now? Everyone in town has a robot."),
    ("e2", "Except the mayor. He's still looking for his abs."),
]
OUTRO = ("o1", "Draw it on paper. Get it in 3D. Vi3W.in")
SAY = {"Vi3W.in": "View dot in", "Vi3W": "View", "3D": "three-D"}
GAP = 0.28                                   # silence between lines (s); punchline lines get more
GAP_AFTER = {"m1": 0.5, "c1": 0.45, "c2": 0.7, "c3": 0.45, "b2": 0.35, "v2": 0.4, "e1": 0.35}
