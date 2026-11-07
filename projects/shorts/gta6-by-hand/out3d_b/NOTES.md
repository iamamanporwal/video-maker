# Agent B: 3D shots (characters, rig, animation, bugs)

Build: `blender -b -P scene.py -- $PWD/scene.blend` (NOCAR=1 uses a procedural box car).
Render: `.venv/bin/python render_b.py stills --scale 40 [--only ...]` then `render_b.py full --scale 100`.
Sets are separate scenes (NPCS, RIGSET, ANIM, STREET, CLEAN, ROOM). STREET holds three shots on time offsets:
cycles frames 1-90, fallthrough 201-296, bugs 401-472. cycles 3.0-5.3 s comes from the CLEAN scene (frames 91-159).
EEVEE 14 samples, AgX Punchy, motion blur OFF (camera cuts are keyed jumps; blur smeared them).

## Gotchas found
- `bounds()` must update the view layer after `mesh.transform()`, or bound boxes are stale (desk PC was 3x).
- Mixamo Hips has 3 children: pick Spine as the bone-viz child or the hips bone is metres long.
- Poly Haven image textures on a 320 m road plane gave radial streaks at grazing angles; the road, ground and
  sidewalk use a procedural noise material now.
- Xbot clips retargeted onto Michelle gave a broken arm pose, so the street hero is an Xbot painted orange/navy
  (native walk/run clips). Michelle is used as the X-ray rig girl, the floating T-pose NPC and the spiky NPC.
- Crowd bakes need NLA blend_in = 0, or the first frames bake half T-pose.
- The Sketchfab glb CDN was very slow (about 20 KB/s, truncated twice); curl -C - resume loop.

## Scores (look-check stills)
- npcs 8/10: one grey Xbot duplicates into a row (0.6), then about 470 instanced, varied-pose mannequins (by 1.6);
  camera cranes up; a radial colour wave from 2.4. Weak spot: small coat sparkles on some instances.
- rig 7/10: Michelle in X-ray with glowing orange bones and teal joints. At 1.4 the forearm folds flat back over
  the upper arm (175° twist plus a squashed bone), wobbles, then snaps to a clean flex at 2.6. Reads as a bad fold,
  but it is not a true candy-wrapper mesh crumple. Framing was re-centred after the last look check.
- animate 8/10: stepped pose-to-pose until 1.55 s (crouch, jump, land, ta-da) with teal/orange/pink onion ghosts,
  then smooth to a tired hunch and a face-down collapse with a foot twitch.
- cycles 7/10: painted Xbot walk, then run, trip and faceplant, then the Fairheaven car bonks him into a
  spinning tumble. At 3.0 it cuts to a grey viewport: an X-ray tumble pose with bones, re-posed in 3 stepped
  "cleanup" keys, on an orbit camera. Weak spot: the hit cut is wide, so the flying body is small.
- fallthrough 8/10: chase cam behind the car, then at 1.4 it sinks through the road. The camera drops under the
  map: flat grey-blue underside ceiling, blue void, and the car tumbling away.
- bugs 7/10: the half-sunk car pops back with a squash, then three glitches at 1.0 with a shake: a giant
  T-posing NPC in the sky, an NPC exploding into noise spikes, and a car jammed nose-up into a palm.
  The glitches are smallish on a phone.
- lonely 8/10: Eric at the gaming desk in a dark blue room, monitor glow on his face, slow push-in.
