# Local auto-rig + text-to-motion pipeline (M5, 24 GB)

Research checked 2026-11-07 against the GitHub API, READMEs, source and Hugging Face file listings.

## Recommended stack

| Stage | Pick | Why | Mac status |
|---|---|---|---|
| Auto-rig | **SkinTokens** ([VAST-AI-Research/SkinTokens](https://github.com/VAST-AI-Research/SkinTokens), MIT, 616★, successor to UniRig) run through **[localai-org/skin-tokens.cpp](https://github.com/localai-org/skin-tokens.cpp)** (Apache-2.0, GGML) | Best published skeleton + skin quality; arbitrary topology | The C++ port runs on **Metal** (`--device auto`); Metal fix merged in PR #3. The upstream PyTorch version needs CUDA ≥ 12.1 and flash-attn |
| Auto-rig fallback | `blender/autorig.py` (this repo) | No model weights; heat-diffusion skinning | Works today, about 1 s |
| Text → motion | **NVIDIA Kimodo** ([nv-tlabs/kimodo](https://github.com/nv-tlabs/kimodo), Apache-2.0 code, 4.1k★, active) with **Kimodo-SOMA-RP-v1.2** weights | Arbitrary text, multi-prompt sequencing, constraints, SOMA skeleton with fingers; NVIDIA Open Model License **allows commercial use** | PyTorch; the code picks `cuda` or `cpu` only (see the MPS patch below) |
| Retarget + export | `blender/retarget.py` (this repo) | Works on any humanoid rig: SOMA names, Mixamo/VRM/SMPL aliases, or **topology matching for `bone_N` rigs** (SkinTokens output) | Works today |

AssetFurnace ([Bingeljell/image-to-3dlab](https://github.com/Bingeljell/image-to-3dlab), Apache-2.0, 1.1k★, pushed yesterday) is this same pairing, SkinTokens plus Kimodo, packaged as an app. Note that its "21 moves" are **presets pre-generated with Kimodo**. It does not do live text-to-motion. Its `scripts/patch_skintokens_portable.py` is the reference for running PyTorch SkinTokens on MPS.

### Others evaluated

| Project | Verdict |
|---|---|
| **HY-Motion 1.0** ([Tencent-Hunyuan/HY-Motion-1.0](https://github.com/Tencent-Hunyuan/HY-Motion-1.0), 2.6k★) | Highest-quality open text-to-motion (1.0B / 0.46B DiT). However, the README lists 26 / 24 GB minimum VRAM, the text encoder is **Qwen3-8B (~16 GB bf16)**, and `t2m_runtime.py` only selects CUDA, falling back to **CPU** (no MPS path). The licence is the Tencent Community License: **it excludes the EU, UK and South Korea** and requires a separate licence above 1M MAU. Use it as a second engine, not the default, on 24 GB. |
| MotionGPT ([OpenMotionLab](https://github.com/OpenMotionLab/MotionGPT), MIT) | Last push July 2025. HumanML3D/SMPL (AMASS data is non-commercial). Light, but older quality. |
| MDM ([GuyTevet/motion-diffusion-model](https://github.com/GuyTevet/motion-diffusion-model), MIT) | The 2022 baseline. Small (CLIP + about 20M parameters), but it needs registered SMPL files and is slow (1000 diffusion steps). |
| MoMask ([EricGuo5513/momask-codes](https://github.com/EricGuo5513/momask-codes), MIT) | Inactive since September 2024. Good quality for its size; HumanML3D licensing caveats apply. |
| ARDY ([nv-tlabs/ardy](https://github.com/nv-tlabs/ardy)) | NVIDIA's real-time autoregressive successor. A macOS/MPS PR is open, not merged; it needs gated Llama-3-8B. |
| UniRig ([VAST-AI-Research/UniRig](https://github.com/VAST-AI-Research/UniRig), MIT) | Superseded by SkinTokens and needs spconv/CUDA. |
| kimodo.cpp ([localai-org/kimodo.cpp](https://github.com/localai-org/kimodo.cpp)) | CPU/Vulkan only. **The Mac support issue (#4) is open.** Its Q4_K text encoder (4.4 GB) is the long-term answer to Kimodo's memory cost. |

## Hardware fit (24 GB unified memory)

| Component | Weights on disk | Peak memory (estimate) | Device |
|---|---|---|---|
| SkinTokens GGUF F16 | 1.25 GB | ~2–4 GB (KV cache grows with `--beams`) | Metal |
| Kimodo SOMA-RP v1.2 motion model | 1.13 GB | <3 GB | MPS (patched) or CPU |
| Kimodo text encoder: Llama-3-8B-Instruct + LLM2Vec | ~16 GB bf16 (**gated**: request access on HF) | ~16 GB | **The bottleneck.** It fits, but close heavy apps. `TEXT_ENCODER_DEVICE=cpu` keeps the motion model on the GPU |
| HY-Motion-1.0-Lite + Qwen3-8B + CLIP | 1.8 + 16 + 0.5 GB | ~20 GB | CPU (no MPS code path) |

Run the stages one after another, never at the same time; the pipeline already works this way. The peak is about 17 GB, set by Kimodo's text encoder.

## Install

```bash
# 0. prerequisites
brew install cmake ninja git-lfs && xcode-select --install   # Blender 5.x already in /Applications
cd projects/rig-motion-poc && mkdir -p vendor

# 1. proof of concept (no weights): works now
uv run --no-project --with numpy python pipeline.py \
  --input samples/khronos/CesiumMan.glb --strip \
  --prompt "Make this character walk forward, jump and perform a backflip" \
  --out out/cesium --preview

# 2. SkinTokens on Metal (~1.25 GB of weights)
git clone https://github.com/localai-org/skin-tokens.cpp vendor/skin-tokens.cpp
cd vendor/skin-tokens.cpp
cmake -S . -B build/release -G Ninja -DCMAKE_BUILD_TYPE=Release -DSKINTOKENS_ENABLE_VULKAN=OFF
cmake --build build/release -j
uvx --from huggingface_hub hf download LocalAI-io/SkinTokens-GGUF --include "F16/*" --local-dir models/SkinTokens-GGUF
cd ../..
#   then: pipeline.py ... --rigger skintokens --strip

# 3. Kimodo (motion model 1.13 GB + gated Llama-3-8B ~16 GB)
#    first accept https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct and run `hf auth login`
uv venv vendor/kimodo-venv --python 3.11 && source vendor/kimodo-venv/bin/activate
uv pip install torch && uv pip install "git+https://github.com/nv-tlabs/kimodo.git"
#    MPS patch: the script hard-codes cuda/cpu
sed -i '' 's/"cuda:0" if torch.cuda.is_available() else "cpu"/"cuda:0" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")/' \
  "$(python -c 'import kimodo.scripts.generate as g; print(g.__file__)')"
PYTORCH_ENABLE_MPS_FALLBACK=1 kimodo_gen "A person walks forward." --duration 3 --output /tmp/k_test
deactivate
#   then: PATH=vendor/kimodo-venv/bin:$PATH pipeline.py ... --motion kimodo
```

Steps 2 and 3 are **not run yet**. They download weights and need your OK.

## Pipeline design

```
IN.glb/fbx/obj ──rig──▶ rigged.glb ──┐
   heuristic | skintokens | none     ├─retarget (Blender)─▶ animated.glb + preview.mp4
prompt ──plan()──▶ ["A person walks forward." 3s, ...] ──motion──▶ motion.npz (SOMA-77)
                          kimodo (real) | clips (offline stand-in)
```

* `rigmotion/motion.py` `plan()` splits free text into Kimodo-style prompts with durations. Kimodo's guidance is one or two behaviours per prompt, each starting with "A person…". Kimodo then blends the segments natively.
* `motion.npz` is the interchange format: world rotations relative to the T-pose, plus a hips track. Any future engine (HY-Motion, MoMask) only needs a converter into it.
* `blender/retarget.py`: W_b = A·G_j·Aᵀ·C_b, where C_b straightens A-pose limbs into SOMA's T-pose. The basis is Rᵀ·W_parentᵀ·W_b·R. Hips travel is scaled by hip height.

## Proof-of-concept results (`out/`)

* `out/cesium/`: CesiumMan (CC-BY 4.0, Khronos) with its rig **stripped**. It was auto-rigged (22 bones, all 3,273 vertices weighted), then given walk → jump → backflip. 200 frames, whole pipeline about 8 s.
* `out/cesium_origrig/`: the same motion on CesiumMan's **original** rig, with names it had never seen (`leg_joint_L_1`...). The topology matcher mapped 19 bones with the correct left and right.
* Motion here comes from real Kimodo outputs (AssetFurnace's pre-generated clips). **The backflip is synthesised** from the jump clip as a placeholder, because no flip clip exists offline. With `--motion kimodo` the model generates every segment from text.

## Known limits

* The heuristic rigger assumes a standing biped in T- or A-pose facing ±Y. It has no fingers, and its stylised proportions are measured from the geometry. Use SkinTokens for anything else.
* The topology mapper is tested on CesiumMan's rig only, **not yet on real SkinTokens output**.
* Hips translation assumes the hips' ancestors stay at rest (true for SOMA-named, Mixamo and SkinTokens rigs).
