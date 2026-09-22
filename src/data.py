# -*- coding: utf-8 -*-
"""
Content of the page. Edit this file, then run `python src/build.py`.

Structure follows the two overview boards (「3DGS 研究方向与技术关联」 and
「3DGS 研究方向与代表工作」):

  MODULES -> sections (the boxes on the overview map)
          -> groups   (sub-headings; the representative works, in board order)
          -> extra    (further reading, folded by default, sorted by date)

Every work:
  W(name, date, venue, text, arxiv=..., url=..., code=..., star=..., tag=..., aka=..., img=...)
    date   "2024.03" — month of the first arXiv version (or release month)
    venue  where it was published; "arXiv" if not (yet) published
    text   one plain-language sentence or two
    star   True for milestones
    tag    where a number comes from: 作者自评 / 厂商声明
    img    teaser image URL; normally filled from figures.json by src/teasers.py
Arxiv ids, titles and venues were checked on 2026-09-17 against arxiv.org,
openaccess.thecvf.com, ecva.net and the projects' GitHub pages.
"""

UPDATED = "2026-09-17"


def W(name, date, venue, text, arxiv=None, url=None, code=None, star=False, tag=None, aka=None, img=None):
    return dict(name=name, date=date, venue=venue, text=text, arxiv=arxiv, url=url, code=code,
                star=star, tag=tag, aka=aka, img=img)


def S(id, name, tagline, icon, groups, hub, extra=(), note=None):
    """A section = one box on the overview map. groups: [(heading or None, [works])]."""
    return dict(id=id, name=name, tagline=tagline, icon=icon, groups=list(groups), hub=list(hub),
                extra=list(extra), note=note)


# ---------------------------------------------------------------------------
# 模块一 · 高效重建
# ---------------------------------------------------------------------------

RECON = dict(
    id="recon", no="模块一", name="高效重建", sub="重建 × 提速", color="blue",
    question="从拍照到能看，要等多久？",
    problem="原版 3DGS 要先用 COLMAP 求相机位姿，再在一张 RTX A6000 上训练 3 万步，Mip-NeRF 360 数据集平均 41 分钟。生产里的真实耗时是「求位姿 + 训练 + 清理」三段相加，其中求位姿往往最慢、也最容易失败；城市级场景还会超出单卡显存。",
    ideas=[
        ("跳过 SfM", "用几何基础模型或前馈网络，一次前向给出位姿、深度，甚至直接给出高斯。"),
        ("算得更快、用得更少", "改写反向传播、优化器和排序，并给高斯数量设预算。"),
        ("分而治之", "大场景切块并行训练，再无缝拼接。"),
        ("生成式补全", "照片不够、或者走到离拍摄点很远的视角时，用图像 / 视频扩散模型修掉伪影、补上没拍到的区域，再蒸馏回 3D。"),
    ],
    advice="底座选 gsplat（Apache-2.0）并打开 MCMC 预算；用前馈模型给出位姿和初始高斯，再做短时精修；把 Faster-GS 当作「哪些技巧真有效」的清单，逐项移植、自己测。",
    sections=[
        S("recon-ff", "前馈重建与初始化", "未标定图像 → 位姿 / 深度 / 高斯", "ff",
          hub=["AnySplat", "InstantSplat", "WorldMirror 2.0"],
          groups=[
              ("少视图 / 前馈重建", [
                  W("pixelSplat", "2023.12", "CVPR 2024 Oral · 最佳论文亚军", "从一对图像直接「预测」出高斯，不需要逐场景训练，开了前馈 3DGS 的头。它处理的是两图之间的窄基线插值，适合读脉络，不适合当生产重建器。",
                    arxiv="2312.12337", code="https://github.com/dcharatan/pixelsplat", star=True),
                  W("MVSplat", "2024.03", "ECCV 2024 Oral", "用多视角代价体（cost volume）来定位高斯的中心，比 pixelSplat 模型更小、推理更快。",
                    arxiv="2403.14627", code="https://github.com/donydchen/mvsplat"),
                  W("latentSplat", "2024.03", "ECCV 2024", "高斯里存的是可变分的特征，再用轻量解码器出图，能更好地处理视角外推时看不清的区域。",
                    arxiv="2403.16292", code="https://github.com/Chrixtar/latentsplat"),
                  W("Splatt3R", "2024.08", "arXiv", "不需要相机参数：在几何基础模型 MASt3R 上补预测高斯属性，从两张未标定照片直接得到高斯。",
                    arxiv="2408.13912", code="https://github.com/btsmart/splatt3r"),
                  W("AnySplat", "2025.05", "SIGGRAPH Asia 2025 · TOG", "从未标定的照片集合一次前向输出高斯、深度和相机位姿，并用可微体素化把重复的逐像素高斯合并。代码为 MIT 许可。",
                    arxiv="2505.23716", code="https://github.com/InternRobotics/AnySplat"),
                  W("WorldMirror 2.0", "2026.04", "HY-World 2.0 技术报告", "腾讯混元世界模型 2.0 中的重建模型（约 1.2B 参数）：多视图或视频一次前向输出点云、深度、法线、相机和 3DGS，推理代码与权重已开源（腾讯社区许可）。",
                    arxiv="2604.14268", code="https://github.com/Tencent-Hunyuan/HY-World-2.0", aka="HY-World 2.0"),
              ]),
              ("初始化与几何基础", [
                  W("InstantSplat", "2024.03", "arXiv", "用 DUSt3R / MASt3R 这类模型给出初始点云和位姿，再短时联合优化，稀疏视角下几十秒就能出结果。属于「初始化后再优化」的思路。",
                    arxiv="2403.20309", code="https://github.com/NVlabs/InstantSplat"),
                  W("DUSt3R", "2023.12", "CVPR 2024", "从两张未标定的照片直接回归出逐像素的 3D 点图，开启了「用几何基础模型替代 SfM」这条路。",
                    arxiv="2312.14132", code="https://github.com/naver/dust3r", star=True),
                  W("MASt3R", "2024.06", "ECCV 2024", "在 DUSt3R 的基础上加入稠密特征匹配，位姿和匹配都更准。",
                    arxiv="2406.09756", code="https://github.com/naver/mast3r"),
                  W("VGGT", "2025.03", "CVPR 2025 最佳论文", "一个前馈 Transformer 一次性输出相机参数、深度图、点图和点跟踪，速度远快于传统 SfM 流程，常被用来给 3DGS 提供位姿和初始化。",
                    arxiv="2503.11651", code="https://github.com/facebookresearch/vggt", star=True),
              ]),
          ],
          extra=[
              W("CF-3DGS", "2023.12", "CVPR 2024", "利用视频帧之间的连续性，边估计相机位姿边训练高斯，不再依赖 COLMAP。",
                arxiv="2312.07504", aka="COLMAP-Free 3DGS"),
              W("GS-LRM", "2024.04", "ECCV 2024", "大型 Transformer 重建模型：输入少量带位姿的图像，一次前向预测出逐像素的高斯。",
                arxiv="2404.19702"),
              W("Long-LRM", "2024.10", "ICCV 2025", "一次读入 32 张 960×540 的图像，前馈重建大范围的 360° 场景；作者报告在单张 A100 上约 1 秒完成。",
                arxiv="2410.12781", tag="作者自评"),
              W("DepthSplat", "2024.10", "CVPR 2025", "把单目深度模型和多视角匹配结合起来，前馈高斯和深度估计互相促进。",
                arxiv="2410.13862", code="https://github.com/cvg/depthsplat"),
              W("NoPoSplat", "2024.10", "ICLR 2025 Oral", "输入不需要相机位姿，直接在一个规范坐标系里预测高斯。",
                arxiv="2410.24207", code="https://github.com/cvg/NoPoSplat"),
              W("WorldMirror", "2025.10", "ICML 2026", "WorldMirror 的第一版：可以选择性地输入位姿、内参、深度等先验，一次前向同时输出点云、深度、法线、相机参数和 3DGS。",
                arxiv="2510.10726", code="https://github.com/Tencent-Hunyuan/HunyuanWorld-Mirror"),
              W("ARTDECO", "2025.10", "arXiv", "面向「边拍边建」（on-the-fly）的重建，用结构化的场景表示兼顾效率和画质。",
                arxiv="2510.08551"),
              W("Depth Anything 3", "2025.11", "arXiv", "用一个朴素的 Transformer，从任意数量的视图（有无位姿均可）预测空间一致的几何；官方代码还提供直接预测 3D 高斯、用于新视角合成的输出头。",
                arxiv="2511.10647", code="https://github.com/ByteDance-Seed/Depth-Anything-3"),
          ]),
        S("recon-train", "训练与采样优化", "预算致密化 / 高效反传 / MCMC", "train",
          hub=["Taming 3DGS", "Faster-GS", "3DGS-MCMC"],
          groups=[
              (None, [
                  W("Taming 3DGS", "2024.06", "SIGGRAPH Asia 2024", "把「最终用多少个高斯」变成事先定好的预算，再配合逐 splat 反向传播、稀疏 Adam 等工程改写来提速；这些改写后来成了很多加速工作的公共零件。",
                    arxiv="2406.15643", code="https://github.com/humansensinglab/taming-3dgs", star=True),
                  W("FastGS", "2025.11", "CVPR 2026 Highlight", "依据多视角一致性来决定在哪里加、删高斯，严格控制训练中的高斯数量；作者报告在 Deep Blending 上比原版快约 15 倍，论文标题即「100 秒训练 3DGS」。",
                    arxiv="2511.04283", code="https://github.com/fastgs/FastGS", tag="作者自评"),
                  W("Faster-GS", "2026.02", "CVPR 2026", "把「实现层面的提速」和「算法改动」拆开评测，合并前人真正通用、有效的技巧，并研究数值稳定性、高斯截断和梯度近似；作者报告训练最高提速约 5 倍且画质不降。适合当作一份 trick 清单来读。",
                    arxiv="2602.09999", tag="作者自评"),
                  W("DashGaussian", "2025.03", "CVPR 2025", "训练前期用低分辨率、之后逐步提高分辨率，并让高斯数量同步增长；论文标题就是「200 秒内完成优化」。",
                    arxiv="2503.18402", tag="作者自评"),
                  W("LiteGS", "2025.03", "arXiv", "从底层光栅化、中层数据组织（按 Morton 码做空间排序）到上层算法，三层一起优化训练流程；仓库自称「50 秒训练 3DGS」。",
                    arxiv="2503.01199", code="https://github.com/MooreThreads/LiteGS", tag="作者自评"),
                  W("Mini-Splatting2", "2024.11", "arXiv", "激进致密化：训练早期就把高斯一次铺够，几分钟内建好 360° 场景。arXiv 上的现题名为 Efficient Scene Modeling via Structure-Aware and Region-Prioritized 3D Gaussians。",
                    arxiv="2411.12788", code="https://github.com/fatPeter/mini-splatting2"),
                  W("3DGS-MCMC", "2024.04", "NeurIPS 2024 Spotlight", "把高斯看成从场景分布中抽出的样本，用「重定位」代替手工设计的克隆/分裂规则，天然带数量上限；gsplat 已内置这一策略。",
                    arxiv="2404.09591", code="https://github.com/ubc-vision/3dgs-mcmc", star=True),
              ]),
          ],
          extra=[
              W("gsplat", "2024.09", "JMLR（MLOSS）", "Nerfstudio 团队维护的开源 CUDA 光栅化库，比原版实现更省显存、更快，并内置 MCMC 致密化、抗锯齿、3DGUT、压缩等功能。Apache-2.0 许可，是最常用的可商用底座。",
                arxiv="2409.06765", code="https://github.com/nerfstudio-project/gsplat"),
              W("Revising Densification", "2024.04", "ECCV 2024", "用像素误差而不是位置梯度来决定在哪里加高斯，并修正了克隆时不透明度的偏差。",
                arxiv="2404.06109"),
              W("AbsGS", "2024.04", "ACM MM 2024", "大高斯内部各处的梯度方向相反、相互抵消，导致它迟迟不分裂、画面发糊；改用梯度的绝对值来累积，找回细节。",
                arxiv="2404.10484"),
              W("Grendel", "2024.06", "ICLR 2025 Oral", "把一个场景的训练拆到多张 GPU 上并行，从而能用上更多高斯、更高的分辨率。论文题为 On Scaling Up 3D Gaussian Splatting Training。",
                arxiv="2406.18533", code="https://github.com/nyu-systems/Grendel-GS"),
              W("3DGS-LM", "2024.09", "ICCV 2025", "把优化器从 Adam 换成二阶的 Levenberg–Marquardt，在画质相当的前提下缩短优化时间。",
                arxiv="2409.12892"),
              W("CLM", "2025.11", "ASPLOS 2026", "把暂时看不到的高斯卸载到 CPU 内存、需要时再换回，让一张消费级显卡也能训练超大场景。",
                arxiv="2511.04951", code="https://github.com/nyu-systems/CLM-GS"),
          ]),
        S("recon-large", "大场景分块重建", "空间分块 / 并行训练", "blocks",
          hub=["VastGaussian", "CityGaussian"],
          groups=[
              (None, [
                  W("VastGaussian", "2024.02", "CVPR 2024", "大场景先分区训练、再无缝合并，并用外观解耦处理不同照片之间的光照差异。",
                    arxiv="2402.17427"),
                  W("CityGaussian", "2024.04", "ECCV 2024", "分而治之的训练加上 LoD 策略，实现城市级场景的实时渲染。",
                    arxiv="2404.01133", code="https://github.com/DekuLiuTesla/CityGaussian"),
              ]),
          ],
          extra=[
              W("Horizon-GS", "2024.12", "CVPR 2025", "把航拍和地面街景放进同一个模型里重建，兼顾大尺度俯瞰与近景细节。",
                arxiv="2412.01745", code="https://github.com/InternRobotics/HorizonGS"),
          ]),
        S("recon-fix", "生成式修复与补全", "扩散 / 视频先验修伪影、补空洞", "fix",
          hub=["Difix3D+", "3DGS-Enhancer", "FixAnything"],
          note="两张总览图没有单列这一组。照片太少、或者走到离拍摄点很远的视角时，3DGS 会出现漂浮物、模糊和空洞；这一组借助图像 / 视频生成模型把这些地方「修」好，再蒸馏回 3D。修出来的内容是模型想象的，不是真实拍到的。删掉物体后的补洞见「组织、编辑与 LoD」里的 InFusion。本组于 2026-09-22 核对。",
          groups=[
              ("渲染修复：训练一个「修图器」", [
                  W("3DGS-Enhancer", "2024.10", "NeurIPS 2024 Spotlight", "把稀疏视角下渲染出的一串新视角当成一段视频，用视频扩散模型整体修复，借视频的时间一致性换来多视角一致，再用修好的画面微调 3DGS。",
                    arxiv="2410.16266", url="https://xiliu8006.github.io/3DGS-Enhancer-project", code="https://github.com/xiliu8006/3DGS-Enhancer"),
                  W("Difix3D+", "2025.03", "CVPR 2025 Oral · 最佳论文候选", "把单步图像扩散模型微调成「修图器」Difix：重建时修复从当前 3D 渲染出的伪训练视角、逐步蒸馏回 3D；渲染时再实时修一遍。NeRF 和 3DGS 都适用。",
                    arxiv="2503.01774", code="https://github.com/nv-tlabs/Difix3D", star=True),
                  W("GSFixer", "2025.08", "ICML 2026", "在「带伪影的渲染 / 干净画面」配对数据上训练 DiT 视频修复模型，并把输入视角的 2D 语义特征和 3D 几何特征当作参考条件，修出来的内容不偏离真实拍到的东西。",
                    arxiv="2508.09667", code="https://github.com/GVCLab/GSFixer"),
                  W("GSFix3D", "2025.08", "3DV 2026", "微调出的修复扩散模型同时以网格和 3DGS 的渲染为条件，去掉新视角里的伪影、补上缺失区域，再蒸馏回高斯场景。",
                    arxiv="2508.14717", url="https://gsfix3d.github.io/", code="https://github.com/GSFix3D/GSFix3D"),
                  W("FixAnything", "2026.08", "ECCV 2026", "把预训练视频生成模型（Wan2.1）用 LoRA 轻量微调成通用修复器，3DGS、NeRF、网格乃至稀疏点云的渲染伪影都能修；再以「修完后相机位姿能否被准确恢复」作为偏好信号继续优化，保证 3D 一致。",
                    arxiv="2608.23549", url="https://fix-anything.github.io", code="https://github.com/kvuong2711/fix-anything"),
              ]),
              ("免微调：直接借用现成的扩散模型", [
                  W("FixingGS", "2025.09", "arXiv", "不训练扩散模型：在 3DGS 优化全程持续做分数蒸馏，并按区域可靠程度逐步增强，修掉稀疏视角下的伪影、补上缺失内容。",
                    arxiv="2509.18759"),
                  W("FreeFix", "2026.01", "3DV 2026", "同样不微调扩散模型：2D 修图和 3D 更新交替进行，用逐像素置信度决定哪里该听生成模型的，重点改善外推视角。",
                    arxiv="2601.20857", url="https://xdimlab.github.io/freefix", code="https://github.com/hyzhou404/FreeFix"),
              ]),
              ("先生成更多视角，再重建", [
                  W("CAT3D", "2024.05", "NeurIPS 2024 Oral", "用多视角扩散模型从一张到几张照片生成大量一致的新视角，再重建成 Zip-NeRF 或 3DGS，是「先生成、再重建」这条路的代表。",
                    arxiv="2405.10314", url="https://cat3d.github.io"),
                  W("ReconX", "2024.08", "TIP 2026", "把稀疏视角重建改写成视频生成：先用输入视角建全局点云，以它为条件生成时间一致的补全视频，再用置信度感知的 3DGS 优化恢复场景。",
                    arxiv="2408.16767", url="https://liuff19.github.io/ReconX", code="https://github.com/THU-SI/ReconX"),
                  W("ViewCrafter", "2024.09", "TPAMI 2025", "以点云渲染为条件驱动视频扩散模型，沿相机轨迹生成新视角、边生成边扩充点云，最后训练 3DGS。",
                    arxiv="2409.02048", url="https://drexubery.github.io/ViewCrafter/", code="https://github.com/Drexubery/ViewCrafter"),
                  W("GenFusion", "2025.03", "CVPR 2025", "训练一个以带伪影的 RGB-D 渲染为条件的视频扩散模型，把修好的帧不断加回训练集，重建和生成循环迭代，逐步把场景补全。",
                    arxiv="2503.21219", url="https://genfusion.sibowu.com", code="https://github.com/Inception3D/GenFusion"),
                  W("FlowR", "2025.04", "ICCV 2025 Highlight", "不从噪声开始生成，而是用多视角流匹配模型把稀疏重建渲染出的新视角直接「流向」密集重建应有的样子，再用它们增强 3DGS。",
                    arxiv="2504.01647", url="https://tobiasfshr.github.io/pub/flowr", code="https://github.com/tobiasfshr/flowr"),
              ]),
          ],
          extra=[
              W("SplatFormer", "2024.11", "ICLR 2025 Spotlight", "不用扩散模型：训练一个点云 Transformer 直接修正高斯参数，让偏离训练视角很远（OOD）时的渲染不崩。",
                arxiv="2411.06390", code="https://github.com/ChenYutongTHU/SplatFormer"),
              W("MVSplat360", "2024.11", "NeurIPS 2024", "前馈模型先给出粗高斯，再用视频扩散模型把渲染结果补成完整画面，只用少量照片做 360° 新视角合成。",
                arxiv="2411.04924", code="https://github.com/donydchen/mvsplat360"),
              W("GSCompleter", "2026.04", "arXiv", "把「修复再蒸馏」换成「生成再注册」：生成参考图后直接抬升成带度量尺度的高斯、并入原场景，免去反复蒸馏；作者称几秒内完成补全。",
                arxiv="2604.20155"),
              W("ConFixGS", "2026.05", "arXiv", "面向驾驶场景里的前馈 3DGS：先生成扩散增强的伪目标，再用重投影交叉验证得到置信度，只采信可靠的细节；作者报告在 Waymo 等数据集上 PSNR 最多提升 3.68 dB。",
                arxiv="2605.09688"),
              W("VidSplat", "2026.05", "SIGGRAPH 2026", "免训练的生成式重建：用视频扩散模型迭代合成新视角来补足覆盖，面向少视角下的完整表面重建。",
                arxiv="2605.11424", url="https://tangjm24.github.io/VidSplat", code="https://github.com/tangjm24/VidSplat"),
          ]),
        S("recon-input", "不完美的输入", "模糊 / 曝光变化 / 视角太少", "blur",
          hub=[], groups=[],
          note="两张总览图没有单列这一组，这里作为延伸阅读：输入照片不理想时，重建质量靠这些方法兜底。",
          extra=[
              W("FSGS", "2023.12", "ECCV 2024", "只有三五张照片时，让新高斯在已有点之间「长出来」，并用单目深度约束几何，避免过拟合。",
                arxiv="2312.00451", code="https://github.com/VITA-Group/FSGS"),
              W("Deblurring 3DGS", "2024.01", "ECCV 2024", "用一个小 MLP 调整每个高斯来模拟模糊，从运动或失焦模糊的照片中重建出清晰场景。",
                arxiv="2401.00834"),
              W("DNGaussian", "2024.03", "CVPR 2024", "稀疏视角下，用全局—局部深度归一化来约束几何。",
                arxiv="2403.06912"),
              W("BAD-Gaussians", "2024.03", "ECCV 2024", "显式建模快门打开期间的相机运动轨迹，与高斯一起优化，去掉运动模糊。",
                arxiv="2403.11831", code="https://github.com/WU-CVGL/BAD-Gaussians"),
              W("Bilateral Guided Processing", "2024.06", "SIGGRAPH 2024 · TOG", "用双边网格拟合每张照片各自的相机处理（ISP）与曝光差异，去掉由此产生的漂浮色斑。",
                arxiv="2406.00448", code="https://github.com/yuehaowang/bilarf", aka="Bilateral Guided Radiance Field Processing"),
              W("WildGaussians", "2024.07", "NeurIPS 2024", "借助 DINO 特征和每张图的外观嵌入，处理网上照片里的光照差异和行人等遮挡物。",
                arxiv="2407.08447", code="https://github.com/jkulhanek/wild-gaussians"),
          ]),
    ],
)

# ---------------------------------------------------------------------------
# 模块二 · 组织、编辑与 LoD
# ---------------------------------------------------------------------------

ORGANIZE = dict(
    id="organize", no="模块二", name="组织、编辑与 LoD", sub="空间分层 ↔ 对象分组", color="green",
    question="一大团高斯，怎样选中、修改，又怎样按远近分层？",
    problem="重建出来的高斯是一大团没有结构的点：想删掉一个路人、给沙发换个颜色，得先知道哪些高斯属于哪个物体；想流畅浏览一座城市，又得知道远处该用多粗的版本。前者是「对象分组」，后者是「空间分层」，两者都是给高斯补上结构。",
    ideas=[
        ("语义选择", "把 2D 分割或语言特征蒸馏进每个高斯，按物体或按一句话选中。"),
        ("局部与多视图编辑", "用扩散模型改图，再把改动一致地落到 3D；或者直接在编辑器里框选、清理。"),
        ("空间层次", "用锚点、八叉树或层次结构组织高斯，按视点选择细节层级。"),
    ],
    advice="「实例分组 + 手工清理工具」性价比最高。生成式编辑优先看「先做多视角一致的 2D 编辑，再直接拟合 3D」这一类（DGE），比逐张换图、反复训练快得多。LoD 参考 Octree-GS 和 Hierarchical 3DGS 两种范式；A LoD of Gaussians 把训练和渲染统一进一套外存方案。",
    sections=[
        S("org-select", "对象分组与语义选择", "实例分组 / 开放词汇查询", "select",
          hub=["Gaussian Grouping", "LangSplat"],
          groups=[
              (None, [
                  W("Feature 3DGS", "2023.12", "CVPR 2024 Highlight", "把 2D 基础模型的特征蒸馏进高斯，支持语义分割和语言引导的编辑。",
                    arxiv="2312.03203"),
                  W("LangSplat", "2023.12", "CVPR 2024 Highlight", "把 CLIP 语言特征压缩后存进高斯，可以用一句话查询场景里的物体，比 NeRF 版的 LERF 快得多。",
                    arxiv="2312.16084", code="https://github.com/minghanqin/LangSplat"),
                  W("Gaussian Grouping", "2023.12", "ECCV 2024", "给每个高斯加一个「身份编码」，用 SAM 的 2D 分割结果来监督，从而可以按物体删除、替换、修复。",
                    arxiv="2312.00732", code="https://github.com/lkeab/gaussian-grouping", star=True),
              ]),
          ],
          extra=[
              W("SAGA", "2023.12", "AAAI 2025", "给出 2D 点选等提示，4 毫秒内就能在 3D 高斯中分割出对应物体；分割能力从 SAM 蒸馏而来。",
                arxiv="2312.00860", code="https://github.com/Jumpat/SegAnyGAussians", aka="Segment Any 3D Gaussians", tag="作者自评"),
          ]),
        S("org-edit", "局部与多视图编辑", "对象修改 / 多视图一致 / 交互清理", "edit",
          hub=["GaussianEditor", "DGE", "Splatshop"],
          groups=[
              (None, [
                  W("GaussianEditor", "2023.11", "CVPR 2024", "用「高斯语义追踪」锁定要编辑的区域，再用分层高斯让扩散模型的引导更稳定，支持删除、替换和文字编辑。",
                    arxiv="2311.14521", code="https://github.com/buaacyw/GaussianEditor", star=True),
                  W("DGE", "2024.04", "ECCV 2024", "先对少量视角做彼此一致的 2D 编辑，再直接拟合到 3D，比逐张换图、反复训练快得多。",
                    arxiv="2404.18929", aka="Direct Gaussian Editor"),
                  W("Splatshop", "2025", "Computer Graphics Forum 2025", "桌面端的大规模高斯编辑器，用于清理、拼装和绘制；项目说明称在 RTX 4090 上桌面端可编辑约一亿个 splat，VR 中约一千万个。",
                    url="https://diglib.eg.org/bitstream/handle/10.1111/cgf70214/cgf70214.pdf", code="https://github.com/m-schuetz/Splatshop"),
                  W("Instruct-GS2GS", "2023.10", "开源项目", "Instruct-NeRF2NeRF 的高斯版本：反复用 InstructPix2Pix 改写训练图像、再更新高斯，实现「一句话改场景」。它是项目而非论文。",
                    url="https://instruct-gs2gs.github.io/", code="https://github.com/cvachha/instruct-gs2gs"),
              ]),
          ],
          extra=[
              W("Instruct-NeRF2NeRF", "2023.03", "ICCV 2023", "NeRF 时代的开山之作：用 InstructPix2Pix 反复改写训练图像、再重新训练，实现文字编辑 3D 场景。",
                arxiv="2303.12789"),
              W("GaussianEditor（同名）", "2023.11", "CVPR 2024", "华为等机构的同名工作，侧重按文字指令精细地编辑局部区域；引用时请按 arXiv 编号区分两篇。",
                arxiv="2311.16037", aka="Editing 3D Gaussians Delicately with Text Instructions"),
              W("GaussCtrl", "2024.03", "ECCV 2024", "所有视角一起编辑（深度条件 + 注意力对齐），保证改完以后多视角一致。",
                arxiv="2403.08733"),
              W("InFusion", "2024.04", "arXiv", "用扩散模型补全深度，修补删掉物体后留下的空洞。",
                arxiv="2404.11613"),
              W("SuperSplat", "2024", "开源工具", "PlayCanvas 出品的浏览器高斯编辑器：框选、删除、变换、合并，可导出压缩格式；MIT 许可。",
                code="https://github.com/playcanvas/supersplat"),
          ]),
        S("org-lod", "空间层次与 LoD", "分块 / 分层 / 按视点选级", "lod",
          hub=["Octree-GS", "Hierarchical 3DGS"],
          groups=[
              ("结构化表示", [
                  W("Scaffold-GS", "2023.11", "CVPR 2024 Highlight", "不再直接存高斯，而是存稀疏的「锚点」，由小 MLP 按视角实时生成周围的高斯。结构化以后更省空间，对视角变化也更稳；Octree-GS、HAC 都建立在它之上。",
                    arxiv="2312.00109", code="https://github.com/city-super/Scaffold-GS", star=True),
              ]),
              ("层次 LoD", [
                  W("Octree-GS", "2024.03", "TPAMI 2025", "用八叉树组织锚点、按距离选择细节层级，远近切换时画质和帧率都更稳定。",
                    arxiv="2403.17898", code="https://github.com/city-super/Octree-GS", star=True),
                  W("Hierarchical 3DGS", "2024.06", "SIGGRAPH 2024 · TOG", "为超大规模采集建立高斯层次结构：分块训练，层级之间平滑过渡，实时浏览数万张照片量级的大场景。",
                    arxiv="2406.12080", code="https://github.com/graphdeco-inria/hierarchical-3d-gaussians", star=True),
                  W("A LoD of Gaussians", "2025.07", "SIGGRAPH 2026", "不分块：把整个场景放在外存（如 CPU 内存）里，直接训练一个 LoD 表示，在单张消费级显卡上训练和渲染超大场景。",
                    arxiv="2507.01110"),
              ]),
          ]),
    ],
)

# ---------------------------------------------------------------------------
# 模块三 · 压缩与高效渲染
# ---------------------------------------------------------------------------

COMPRESS = dict(
    id="compress", no="模块三", name="压缩与高效渲染", sub="减点 / 码率 / 渲染分别优化", color="purple",
    question="几百 MB 的模型，怎样存得下、传得动、跑得快？",
    problem="原版每个高斯要存 59 个浮点数，其中 48 个是球谐颜色系数；原论文在 Mip-NeRF 360 数据集上平均占 734 MB。运行时显存、下载体积、每帧渲染速度和缩放时的画质，是需要分别优化的几个目标。",
    ideas=[
        ("减点", "剪掉贡献小的高斯，直接降低显存和排序开销。"),
        ("编码", "降低球谐阶数、向量量化、熵编码，减小文件体积。"),
        ("渲染加速与抗锯齿", "从 GPU 系统层面提速；用滤波让缩放时不出锯齿。"),
        ("跨端部署", "压缩格式加按需加载，让网页和手机也能打开。"),
    ],
    advice="先把目标拆开：运行时显存靠减点，下载体积靠码率，大场景靠 LoD（见模块二）。「锚点 + MLP 解码」这类方法（Scaffold-GS → HAC → HAC++）渲染时要跑网络，更适合作传输/存档格式，进引擎前一般要烘焙回显式高斯；引擎和网页侧更友好的是 SOGS、SPZ 这类「显式高斯 + 压缩」格式。Mip-Splatting 的两个滤波器几乎是标配。",
    sections=[
        S("cmp-code", "减点与编码", "高斯数量 / 存储码率", "codec",
          hub=["LightGaussian", "MaskGaussian", "HAC++"],
          groups=[
              ("减点与紧凑表示", [
                  W("LightGaussian", "2023.11", "NeurIPS 2024 Spotlight", "三步走：剪掉不重要的高斯，把高阶球谐蒸馏成低阶，再做向量量化。论文标题即「压缩 15 倍、200+ FPS」。",
                    arxiv="2311.17245", code="https://github.com/VITA-Group/LightGaussian", star=True, tag="作者自评"),
                  W("Mini-Splatting", "2024.03", "ECCV 2024", "指出高斯在空间里分布不均，才是模型臃肿的根源；用更少的高斯达到相近画质。「分布低效」这个结论对速度和压缩同样有用。",
                    arxiv="2403.14166", code="https://github.com/fatPeter/mini-splatting"),
                  W("MaskGaussian", "2024.12", "CVPR 2025", "把「这个高斯留不留」建模成可采样的概率掩码，训练过程中就学会剪枝。",
                    arxiv="2412.20522", code="https://github.com/kaikai23/MaskGaussian"),
              ]),
              ("编码与存储", [
                  W("Compressed 3DGS", "2023.11", "arXiv", "对方向颜色和高斯参数做考虑敏感度的向量聚类，并配合量化感知训练；作者报告在真实场景上最高压缩约 31 倍，渲染也更快。",
                    arxiv="2401.02436", url="https://keksboter.github.io/c3dgs/", code="https://github.com/KeKsBoTer/c3dgs", tag="作者自评",
                    aka="Compressed 3D Gaussian Splatting for Accelerated Novel View Synthesis"),
                  W("HAC", "2024.03", "ECCV 2024", "在 Scaffold-GS 的基础上，用哈希网格建模锚点属性之间的空间相关性，据此做熵编码。",
                    arxiv="2403.14530", code="https://github.com/YihangChen-ee/HAC"),
                  W("HAC++", "2025.01", "TPAMI 2025", "HAC 的期刊扩展，加入锚点内部的上下文与自适应量化；作者报告相对原版 3DGS 平均压缩超过 100 倍，相对 Scaffold-GS 超过 20 倍。",
                    arxiv="2501.12255", code="https://github.com/YihangChen-ee/HAC-plus", star=True, tag="作者自评",
                    aka="HAC++: Towards 100X Compression of 3D Gaussian Splatting"),
                  W("Self-Organizing Gaussians", "2023.12", "ECCV 2024", "把高斯参数排进规整的 2D 网格，并在训练中让相邻格子保持平滑，从而大幅压缩（作者报告 17–42 倍）。PlayCanvas 于 2025 年 5 月采用的 SOGS 压缩格式即基于这一方法。",
                    arxiv="2312.13299", code="https://github.com/fraunhoferhhi/Self-Organizing-Gaussians", aka="SOG", tag="作者自评"),
                  W("PCGS", "2025.03", "AAAI 2026 Oral", "渐进式压缩：从数量（逐步加入锚点）和质量（逐步细化量化）两个方向分级，码流可以按需加载，先看到粗略版本，再逐步变清晰。",
                    arxiv="2503.08511", url="https://yihangchen-ee.github.io/project_pcgs/", code="https://github.com/YihangChen-ee/PCGS"),
              ]),
              ("压缩综述", [
                  W("3DGS.zip", "2024.06", "CGF 2025 · 综述", "3DGS 压缩方法的综述：把方法分成「减小文件」和「减少高斯数」两类，统一对比框架，并维护一个持续更新的对比网站。挑压缩方法前先看这里。",
                    arxiv="2407.09510", url="https://w-m.github.io/3dgs-compression-survey/"),
              ]),
          ],
          extra=[
              W("Compact 3DGS", "2023.11", "CVPR 2024 Highlight", "学一个掩码删掉用处不大的高斯，用网格化的神经场代替逐点颜色，并用码本量化几何属性。",
                arxiv="2311.13681", code="https://github.com/maincold2/Compact-3DGS", aka="Compact 3D Gaussian Representation for Radiance Field"),
              W("CompGS", "2023.11", "ECCV 2024", "对高斯属性做 K-means 向量量化，只存码本编号，从而大幅缩小体积。早期版本题为 Compact3D。",
                arxiv="2311.18159", code="https://github.com/UCDvision/compact3d"),
              W("EAGLES", "2023.12", "ECCV 2024", "用量化的隐式属性表示高斯，并配合渐进式训练，同时降低存储和显存。",
                arxiv="2312.04564"),
              W("GaussianImage", "2024.03", "ECCV 2024", "用 2D 高斯表示和压缩图像，解码可达每秒上千帧。本页原理第四步的小实验就属于这类思路。",
                arxiv="2403.08551", code="https://github.com/Xinjie-Q/GaussianImage"),
              W("ContextGS", "2024.05", "NeurIPS 2024", "把锚点分成层级，用已经解码的粗层去预测细层，做自回归式的上下文编码。",
                arxiv="2405.20721", code="https://github.com/wyf0912/ContextGS"),
              W("PUP 3D-GS", "2024.06", "CVPR 2025", "训练完成后，用基于 Hessian 的敏感度给每个高斯打分，一次剪掉大部分，再微调恢复画质。",
                arxiv="2406.10219"),
              W("NanoGS", "2026.03", "ECCV 2026", "免训练的高斯简化：不需要原始照片，直接在现成模型上合并、精简高斯，同时尽量保住外观和几何。代码为 CC BY-NC 4.0（非商用）。",
                arxiv="2603.16103", code="https://github.com/RongLiu-Leo/NanoGS"),
          ]),
        S("cmp-render", "渲染加速与抗锯齿", "GPU 优化 / 多尺度滤波", "render",
          hub=["FlashGS", "Mip-Splatting"],
          groups=[
              (None, [
                  W("FlashGS", "2024.08", "CVPR 2025", "纯系统层面的光栅化加速：消除冗余计算，优化流水线、调度和显存访问，和算法层面的改进互不冲突，主要面向大场景、高分辨率；作者报告在消费级 GPU 上平均提速约 4 倍。",
                    arxiv="2408.07967", code="https://github.com/InternLandMark/FlashGS", tag="作者自评"),
                  W("Mip-Splatting", "2023.11", "CVPR 2024 最佳学生论文", "用 3D 平滑滤波限制每个高斯的最高频率，再用 2D Mip 滤波替代屏幕空间的膨胀操作，拉远拉近都不再出现锯齿或「变粗」。",
                    arxiv="2311.16493", code="https://github.com/autonomousvision/mip-splatting", star=True),
                  W("Multi-Scale 3DGS", "2023.11", "CVPR 2024", "为不同分辨率准备不同尺度的高斯，缓解拉远时的锯齿。",
                    arxiv="2311.17089"),
              ]),
          ],
          extra=[
              W("StopThePop", "2024.02", "SIGGRAPH 2024 · TOG", "逐像素做分层排序，消除转动视角时颜色突然跳变的 popping。",
                arxiv="2402.00525", code="https://github.com/r4dl/StopThePop"),
              W("Analytic-Splatting", "2024.03", "ECCV 2024 Oral", "对高斯在整个像素面积上的积分做解析近似，而不是只采样像素中心。",
                arxiv="2403.11056", code="https://github.com/lzhnb/Analytic-Splatting"),
              W("EVER", "2024.10", "ICCV 2025", "用密度恒定的椭球做精确的体渲染，从原理上避开排序近似带来的 popping。",
                arxiv="2410.01804"),
              W("Sort-free GS", "2024.10", "ICLR 2025", "用加权求和代替「先排序再 α 混合」，省掉排序开销，更适合手机等移动端。",
                arxiv="2410.18931"),
              W("Speedy-Splat", "2024.11", "CVPR 2025", "更精确地定位每个高斯在画面上的覆盖范围，并在训练中加入剪枝；作者报告平均渲染提速 6.71 倍，模型体积和训练时间也随之下降。",
                arxiv="2412.00578", tag="作者自评"),
          ]),
        S("cmp-deploy", "跨端与流式部署", "按需加载 / 浏览器 / 引擎", "deploy",
          hub=["Spark", "SOGS", "SPZ"],
          note="这一组是工具与格式，不是论文。",
          groups=[
              (None, [
                  W("Spark", "2025.05", "开源库 · World Labs", "World Labs 出品的 three.js 高斯渲染库，能把高斯和普通网格放进同一个场景；目标覆盖 98% 以上支持 WebGL2 的设备，低功耗手机上也能流畅渲染。MIT 许可。",
                    url="https://sparkjs.dev/", code="https://github.com/sparkjsdev/spark", tag="厂商声明"),
                  W("WebDGS", "2025.12", "个人开源项目", "完全在浏览器里用 WebGPU 训练和查看 3DGS：分块渲染、反向传播、Adam 和增删都在 GPU 上跑。仓库未声明许可证，适合当教学和原型参考。",
                    url="https://krispy-kenay.github.io/WebDGS/", code="https://github.com/krispy-kenay/WebDGS"),
                  W("SOGS", "2025.05", "PlayCanvas Engine 2.7.5", "PlayCanvas 采用的 Self-Organizing Gaussians 压缩格式，把高斯属性组织成 2D 图像存储；官方称可把 3DGS 数据缩小 20 倍以上。",
                    url="https://blog.playcanvas.com/playcanvas-adopts-sogs-for-20x-3dgs-compression/", tag="厂商声明"),
                  W("SPZ", "2024", "开源格式 · Niantic", "Niantic 开源的高斯压缩文件格式，官方说明约为同等 PLY 文件的 1/10 大小；MIT 许可。",
                    code="https://github.com/nianticlabs/spz", tag="厂商声明"),
              ]),
          ],
          extra=[
              W("KHR_gaussian_splatting", "2026.02", "Khronos glTF 扩展", "glTF 的高斯泼溅扩展，2026 年 2 月发布候选版；截至 2026 年 9 月，Khronos 官方仓库里的状态已是 Complete, Ratified（已批准）。SPZ、L-GSC 等压缩扩展仍在提案阶段。",
                url="https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_gaussian_splatting"),
          ]),
    ],
)

# ---------------------------------------------------------------------------
# 模块四 · 几何与 Mesh + GS
# ---------------------------------------------------------------------------

GEOMETRY = dict(
    id="geometry", no="模块四", name="几何与 Mesh + GS", sub="几何提取 / 网格绑定 / 混合渲染", color="teal",
    question="能碰撞、能投影、能和网格一起进引擎吗？",
    problem="3DGS 本身没有「表面」：法线和深度都不可靠，游戏引擎需要的碰撞、阴影、物理无从谈起。进了引擎还要回答高斯和普通网格怎么一起渲染：谁挡住谁，谁照亮谁。",
    ideas=[
        ("把高斯压成面片", "法线天然有定义，深度也更准（2DGS、PGSR 一系）。"),
        ("从高斯场里取表面", "定义不透明度场或深度，再抽取等值面得到网格（GOF、RaDe-GS）；MILo 更进一步，训练时就带着网格。"),
        ("网格绑定", "把高斯绑到网格上，网格一动，高斯跟着动。"),
        ("统一光路或换掉高斯", "用光线追踪把高斯和网格放进同一套光路（3DGRT / 3DGUT）；或者干脆直接优化三角形。"),
    ],
    advice="用 PGSR 或 MILo 出代理网格，负责碰撞、阴影和间接光；引擎里先把「深度合成 + 代理网格投影」做稳，光追混合作为高端路径。注意：MILo 等仓库依赖 Inria 系光栅器，PGSR 代码也是非商用许可，商用前逐个核对。",
    sections=[
        S("geo-mesh", "网格提取", "几何约束 / 深度法线 / 表面提取", "mesh",
          hub=["2DGS", "PGSR", "RaDe-GS", "MILo"],
          groups=[
              (None, [
                  W("2DGS", "2024.03", "SIGGRAPH 2024", "把 3D 椭球压扁成 2D 圆盘（面元），用光线与面元求交来渲染，几何和法线天然准确，是后续几何方法最常用的基线。",
                    arxiv="2403.17888", code="https://github.com/hbb1/2d-gaussian-splatting", star=True, aka="2D Gaussian Splatting"),
                  W("Gaussian Surfels", "2024.04", "SIGGRAPH 2024", "同期的相近思路：把高斯的一个轴压到零，得到带法线的面元，用于高质量表面重建。",
                    arxiv="2404.17774"),
                  W("GOF", "2024.04", "SIGGRAPH Asia 2024 · TOG", "直接从高斯定义不透明度场，能在无界场景里自适应地提取网格。",
                    arxiv="2404.10772", code="https://github.com/autonomousvision/gaussian-opacity-fields", aka="Gaussian Opacity Fields"),
                  W("PGSR", "2024.06", "TVCG 2024", "把高斯压成平面，配合无偏深度和单/多视角几何一致性约束，精度与速度兼顾。",
                    arxiv="2406.06521", code="https://github.com/zju3dv/PGSR"),
                  W("RaDe-GS", "2024.06", "ACM TOG", "用光栅化的方式算出高斯的深度和法线，几何精度高、速度快；也是 MILo 默认使用的光栅器。",
                    arxiv="2406.01467", code="https://github.com/BaowenZ/RaDe-GS"),
                  W("MILo", "2025.06", "SIGGRAPH Asia 2025 · TOG", "训练的每一步都从高斯可微地提取网格（顶点位置和连接关系都来自高斯），让网格上的误差回传给高斯；得到的网格顶点数少一个数量级。",
                    arxiv="2506.24096", code="https://github.com/Anttwo/MILo", star=True),
              ]),
          ],
          extra=[
              W("DN-Splatter", "2024.03", "WACV 2025", "加入深度和法线先验的监督，室内场景提取出的网格更平整。",
                arxiv="2403.17822", code="https://github.com/maturk/dn-splatter"),
          ]),
        S("geo-bind", "网格绑定编辑", "网格驱动高斯形变", "bind",
          hub=["SuGaR", "Gaussian Frosting"],
          groups=[
              (None, [
                  W("SuGaR", "2023.11", "CVPR 2024", "用正则项把高斯拉平、贴到物体表面上，再用泊松重建提取网格，还能把高斯绑到网格上跟着编辑。",
                    arxiv="2311.12775", code="https://github.com/Anttwo/SuGaR", star=True),
                  W("Gaussian Frosting", "2024.03", "ECCV 2024 Oral", "在网格外面包一层厚度可变的高斯「糖霜」：网格负责结构，高斯负责毛发这类模糊细节，还能跟着网格做动画。",
                    arxiv="2403.14554", code="https://github.com/Anttwo/Frosting"),
              ]),
          ]),
        S("geo-hybrid", "Mesh / GS 共渲染", "光栅化 / 光追 / 深度与遮挡", "hybrid",
          hub=["3DGRT", "3DGUT", "3DGRUT"],
          groups=[
              (None, [
                  W("3DGRT", "2024.07", "SIGGRAPH Asia 2024 · TOG", "用光线追踪代替光栅化来渲染高斯，能做反射、折射、阴影等次级光线效果，也支持鱼眼等畸变相机；需要光追硬件，速度慢于光栅化。",
                    arxiv="2407.07090", star=True, aka="3D Gaussian Ray Tracing"),
                  W("3DGUT", "2024.12", "CVPR 2025", "用无迹变换（Unscented Transform）来投影高斯，让光栅化也能处理畸变相机和卷帘快门，并能与 3DGRT 混合：主光线光栅化，次级光线追踪。gsplat 已集成。",
                    arxiv="2412.12507"),
                  W("3DGRUT", "2025", "NVIDIA 开源代码（工程实现）", "3DGRT 与 3DGUT 的官方实现（Apache-2.0）。其 Playground 可以把带 PBR 材质的网格插进高斯场景，渲染反射、折射和景深，适合当「正确答案」参考。",
                    code="https://github.com/nv-tlabs/3dgrut"),
              ]),
          ],
          extra=[
              W("XScene-UEPlugin", "2023", "开源插件", "XVERSE 的 UE5 高斯渲染插件（原 XV3DGS），基于 Niagara，支持与 UE 资产混合渲染和多种动态光源；Apache-2.0。据第三方报道，UE 至今没有第一方的高斯模块。",
                code="https://github.com/xverse-engine/XScene-UEPlugin"),
          ]),
        S("geo-tri", "三角形替代表示", "以三角形或网格替代高斯", "tri",
          hub=["Triangle Splatting+", "MeshSplatting"],
          groups=[
              (None, [
                  W("Triangle Splatting+", "2025.09", "arXiv", "让三角形共享顶点、并在训练中逼成不透明，产出无需后处理即可放进标准图形引擎的半连通网格，可用于物理仿真和交互漫游。植被、毛发这类高斯擅长的内容上画质损失多少，建议用自己的数据验证。",
                    arxiv="2509.25122"),
                  W("MeshSplatting", "2025.12", "CVPR 2026", "用可微渲染联合优化网格的几何与外观，用受限 Delaunay 三角化保证连通性，产出能在实时 3D 引擎里高效渲染的网格；作者报告在 Mip-NeRF 360 上比 MILo 高 0.69 dB，训练快一倍。",
                    arxiv="2512.06818", tag="作者自评"),
              ]),
          ],
          extra=[
              W("3D Convex Splatting", "2024.11", "CVPR 2025 Highlight", "用可微的平滑凸体代替高斯，硬边和平面更锐利，需要的图元更少。",
                arxiv="2411.14974"),
              W("Deformable Beta Splatting", "2025.01", "SIGGRAPH 2025", "用形状可调的 Beta 核代替高斯核，用更少的参数表达更锐利的边界。",
                arxiv="2501.18630"),
              W("3D Student Splatting and Scooping", "2025.03", "CVPR 2025 · 最佳论文荣誉提名", "用学生 t 分布作为基元，并允许负密度把多余的部分「挖掉」，同等画质下图元更少。",
                arxiv="2503.10148", code="https://github.com/realcrane/3D-student-splating-and-scooping"),
              W("Triangle Splatting", "2025.05", "3DV 2026", "把每个三角形当作可微的「软」图元来优化，让三角形重新成为场景表示；三角形天然兼容标准图形管线，作者用现成的网格渲染器在 1280×720 下跑出 2400+ FPS。",
                arxiv="2505.19175", code="https://github.com/trianglesplatting/triangle-splatting", tag="作者自评"),
          ]),
    ],
)

# ---------------------------------------------------------------------------
# 模块五 · 材质分解与重光照
# ---------------------------------------------------------------------------

RELIGHT = dict(
    id="relight", no="模块五", name="材质分解与重光照", sub="材质 / 光照 / 可见性", color="orange",
    question="换个时间、加一盏灯，画面还对吗？",
    problem="3DGS 用球谐函数把「这个点从这个方向看是什么颜色」直接记了下来，光照被烘死在颜色里。想重新打光，就得先拆出几何（法线）、材质（反照率、粗糙度、金属度）、光照和遮挡；而高斯恰恰缺可靠的法线，也缺高效的光线求交。",
    ideas=[
        ("材质与光照分解", "给高斯加法线和简化的 BRDF，先把反光物体做对。"),
        ("光追算可见性", "用光线追踪计算阴影和互反射，物理上更正确。"),
        ("可控着色", "延迟着色、预计算辐射传输，或让神经渲染器补上真实感。"),
    ],
    advice="纯 PBR 逆渲染的上限被几何质量卡住，所以重光照必须和模块四一起做。游戏侧较可行的路线是：2DGS / PGSR 类几何 → 用本征先验约束反照率、法线和粗糙度 → 引擎延迟着色，阴影交给代理网格。研究线可以并行跟踪 IRGS → EAG-PT → TRON。",
    sections=[
        S("rl-decomp", "材质与光照分解", "几何 / 材质 / 光照 / 可见性", "decomp",
          hub=["GaussianShader", "GS-IR"],
          groups=[
              (None, [
                  W("GaussianShader", "2023.11", "CVPR 2024", "给高斯加上简化的着色函数和法线估计，反光物体的渲染明显改善。",
                    arxiv="2311.17977"),
                  W("GS-IR", "2023.11", "CVPR 2024", "从渲染深度推出法线、把遮挡信息烘焙下来，完成高斯的逆渲染（分解出材质与光照）。",
                    arxiv="2311.16473", code="https://github.com/lzhnb/GS-IR"),
              ]),
          ]),
        S("rl-trace", "光追与间接光", "遮挡 / 互反射 / 多跳光传输", "trace",
          hub=["R3DG", "IRGS", "EAG-PT"],
          groups=[
              (None, [
                  W("R3DG", "2023.11", "ECCV 2024", "给每个高斯加上法线和 BRDF 参数，并用基于 BVH 的点光线追踪计算可见性，从而支持重光照。",
                    arxiv="2311.16043", code="https://github.com/NJU-3DV/Relightable3DGaussian", star=True, aka="Relightable 3D Gaussians"),
                  W("IRGS", "2024.12", "CVPR 2025", "不再简化渲染方程，而是用可微的 2D 高斯光线追踪在线计算入射光，能捕捉物体之间的互反射；它的第一阶段直接依赖 Ref-Gaussian。",
                    arxiv="2412.15867", code="https://github.com/fudan-zvg/IRGS"),
                  W("EAG-PT", "2026.01", "SIGGRAPH 2026", "发光感知的高斯加路径追踪，面向室内漫反射场景的重建与编辑，走的是「高斯 + 光线追踪」的物理正确路线。",
                    arxiv="2601.23065"),
              ]),
          ]),
        S("rl-shade", "可控着色与重光照", "延迟着色 / 预计算 / 神经渲染", "shade",
          hub=["GI-GS", "PRTGS", "TRON"],
          groups=[
              ("着色 / 预计算", [
                  W("Ref-Gaussian", "2024.12", "ICLR 2025", "面向强反射物体的高斯渲染与分解。论文题为 Reflective Gaussian Splatting。",
                    arxiv="2412.19282", code="https://github.com/fudan-zvg/ref-gaussian"),
                  W("GI-GS", "2024.10", "ICLR 2025", "延迟着色框架：先渲染 G-buffer，只对直接光做 PBR，再用轻量的路径追踪计算间接光（全局光照）。",
                    arxiv="2410.02619", code="https://github.com/stopaimme/GI-GS"),
                  W("RTR-GS", "2025.07", "arXiv", "混合渲染：正向渲染负责辐射传输，延迟渲染负责反射，能稳健处理任意反射率的物体，分解出 BRDF 与光照并重新打光。",
                    arxiv="2507.07733", code="https://github.com/ZyyZyy06/RTR-GS"),
                  W("PRTGS", "2024.08", "arXiv", "借助预计算辐射传输（PRT）做实时重光照，包括次级光照效果，运行时开销低。",
                    arxiv="2408.03538"),
                  W("3DGS-DR", "2024.04", "SIGGRAPH 2024", "延迟反射：先渲染法线等缓冲，再逐像素计算反射，镜面效果更准，是反射着色的常用基础。",
                    arxiv="2404.18454", aka="3D Gaussian Splatting with Deferred Reflection"),
              ]),
              ("物理与神经渲染结合", [
                  W("TRON", "2026.06", "arXiv 预印本 · NVIDIA", "出发点是纯 PBR 高斯受几何、材质和光传输估计误差所限，重光照不够真实。做法是用逆渲染模型的本征先验约束高斯材质，让光追器只提供辐射度引导，再由轻量神经渲染器补足真实感（基于 3DGRT 管线）。",
                    arxiv="2606.11314", url="https://research.nvidia.com/labs/sil/projects/tron"),
                  W("DiffusionRenderer", "2025.01", "CVPR 2025 Oral", "外部支撑方法：用视频扩散模型从真实视频中估计几何和材质（G-buffer），再在新光照下正向合成图像。",
                    arxiv="2501.18590", code="https://github.com/nv-tlabs/diffusion-renderer", star=True),
              ]),
          ],
          extra=[
              W("Spec-Gaussian", "2024.02", "NeurIPS 2024", "用各向异性球面高斯代替球谐函数，更好地表现高光和镜面反射。",
                arxiv="2402.15870", code="https://github.com/ingra14m/Spec-Gaussian"),
              W("3DGS 逆渲染 + 近似全局光照", "2025.04", "arXiv", "用光栅化的 G-buffer 加屏幕空间光追，为高斯近似一次反弹的间接光。插入外部物体时，先把物体渲染成 G-buffer，再按深度与场景的 G-buffer 合成，物体既被正确照亮、又参与间接光（地面上能看到它的反射）。这几乎就是引擎延迟管线里网格与高斯共存的原型。",
                arxiv="2504.01358", aka="3D Gaussian Inverse Rendering with Approximated Global Illumination"),
              W("LumiGauss", "2024.08", "WACV 2025", "从网络照片集重建户外场景，并建模环境光照和阴影，使其可以重新打光。",
                arxiv="2408.04474"),
              W("GS³", "2024.10", "SIGGRAPH Asia 2024", "在灯光阵列这类受控采集条件下，用三组高斯分别负责外观、阴影和残差，实现高效重光照。",
                arxiv="2410.11419", aka="Triple Gaussian Splatting"),
              W("GaRe", "2025.07", "ICCV 2025", "面向户外、光照不受控的照片集的可重光照高斯。",
                arxiv="2507.20512"),
              W("ROSGS", "2025.09", "arXiv", "户外场景的可重光照高斯重建。",
                arxiv="2509.11275"),
          ]),
    ],
)

# ---------------------------------------------------------------------------
# 模块六 · 动态与交互
# ---------------------------------------------------------------------------

DYNAMIC = dict(
    id="dynamic", no="模块六", name="动态与交互", sub="时序 / 骨骼 / 物理", color="indigo",
    question="怎样让高斯动起来：随时间变化、跟着骨骼走、受力会变形？",
    problem="静态 3DGS 只描述一个瞬间。要表现会动的场景，需要给高斯加上时间维或形变场；要做数字人，需要把高斯绑到人体或头部模板上，由骨骼和表情驱动；要做交互，还得让高斯服从物理规律。",
    ideas=[
        ("时空表示", "规范空间加形变场，或者直接用带时间维的高斯。"),
        ("模板绑定", "把高斯挂到 SMPL、FLAME 这类参数化模型上，由骨骼和表情驱动。"),
        ("物理仿真", "把高斯当作仿真粒子，赋予材料属性，实时响应交互。"),
    ],
    advice="除非要做角色或动态资产，这个模块读摘要即可。做数字人，头部先看 GaussianAvatars，全身先看 GART 和 GauHuman。",
    sections=[
        S("dyn-4d", "动态场景 / 4D", "时序跟踪 / 形变场 / 时空高斯", "motion",
          hub=["4D-GS", "SC-GS", "STG"],
          groups=[
              (None, [
                  W("Dynamic 3D Gaussians", "2023.08", "3DV 2024", "让高斯随时间移动、身份保持不变，重建动态场景的同时顺带得到逐点跟踪。",
                    arxiv="2308.09713", star=True),
                  W("Deformable 3DGS", "2023.09", "CVPR 2024", "规范空间里的高斯加一个形变 MLP，重建单目拍摄的动态场景。",
                    arxiv="2309.13101", code="https://github.com/ingra14m/Deformable-3D-Gaussians"),
                  W("4D-GS", "2023.10", "CVPR 2024", "用多分辨率的 4D 特征平面编码形变，实时渲染动态场景。",
                    arxiv="2310.08528", code="https://github.com/hustvl/4DGaussians", aka="4D Gaussian Splatting for Real-Time Dynamic Scene Rendering"),
                  W("SC-GS", "2023.12", "CVPR 2024", "用少量控制点学习 6 自由度变换，再按学到的权重插值出每个高斯的运动（与骨骼蒙皮同一思路），拖动控制点就能编辑动作，最接近 TA 熟悉的蒙皮工作流。",
                    arxiv="2312.14937", code="https://github.com/yihua7/SC-GS"),
                  W("STG", "2023.12", "CVPR 2024", "时空高斯：给高斯加上随时间变化的不透明度和参数化的运动、旋转，并用神经特征代替球谐；作者报告轻量版在 RTX 4090 上以 60 FPS 渲染 8K 动态视频。",
                    arxiv="2312.16812", code="https://github.com/oppo-us-research/SpacetimeGaussians", tag="作者自评", aka="Spacetime Gaussian Feature Splatting"),
              ]),
          ],
          extra=[
              W("4D Gaussian", "2023.10", "ICLR 2024", "直接用带时间维度的 4D 高斯表示时空。",
                arxiv="2310.10642", code="https://github.com/fudan-zvg/4d-gaussian-splatting"),
          ]),
        S("dyn-avatar", "数字人 / 头像", "模板绑定 / 骨骼与表情驱动", "avatar",
          hub=["GaussianAvatars", "GauHuman", "GART"],
          groups=[
              (None, [
                  W("GaussianAvatars", "2023.12", "CVPR 2024 Highlight", "把高斯绑定到参数化头部网格（FLAME）上，由表情参数驱动的逼真头像。",
                    arxiv="2312.02069", code="https://github.com/ShenhanQian/GaussianAvatars"),
                  W("Gaussian Head Avatar", "2023.12", "CVPR 2024", "用可控的 3D 高斯表示头部外观，并与 MLP 形变场联合优化，兼顾表情准确和细节；arXiv 现题名 HHAvatar，扩展到了动态头发。",
                    arxiv="2312.03029", code="https://github.com/YuelangX/Gaussian-Head-Avatar", aka="HHAvatar: Gaussian Head Avatar with Dynamic Hairs"),
                  W("GauHuman", "2023.12", "CVPR 2024", "从单目人体视频学习可驱动的高斯人体：在规范空间建模，用线性混合蒙皮变换到各个姿态；作者报告训练 1–2 分钟、渲染最高 189 FPS。",
                    arxiv="2312.02973", code="https://github.com/skhu101/GauHuman", tag="作者自评"),
                  W("GART", "2023.11", "CVPR 2024", "高斯铰接模板：借助 SMPL、SMAL 等类别模板和可学习的蒙皮，从单目视频在几秒到几分钟内重建可驱动的人体或动物，新姿态下渲染超过 150 FPS。",
                    arxiv="2311.16099", code="https://github.com/JiahuiLei/GART", tag="作者自评"),
                  W("Animatable Gaussians", "2023.11", "CVPR 2024", "把高斯排在正反两张「高斯贴图」上，用 2D CNN 学出随姿态变化的衣物细节；arXiv 现题名 Animatable and Relightable Gaussians，扩展到了重光照。",
                    arxiv="2311.16096", code="https://github.com/lizhe00/AnimatableGaussians"),
              ]),
          ],
          extra=[
              W("Relightable Gaussian Codec Avatars", "2023.12", "CVPR 2024 Oral", "可重光照的高保真头像：头发、皮肤的细节在新光照下依然真实。",
                arxiv="2312.03704"),
          ]),
        S("dyn-phys", "物理仿真与交互", "材料属性 / 力学求解 / 实时交互", "physics",
          hub=["PhysGaussian", "VR-GS"],
          groups=[
              (None, [
                  W("PhysGaussian", "2023.11", "CVPR 2024 Highlight", "把高斯直接当作物质点法（MPM）的粒子来仿真，「看到的就是仿真的」，不需要另建网格。",
                    arxiv="2311.12198", star=True),
                  W("VR-GS", "2024.01", "arXiv", "在 VR 里对高斯场景做实时的、带物理的交互编辑。",
                    arxiv="2401.16663"),
              ]),
          ],
          extra=[
              W("PhysDreamer", "2024.04", "ECCV 2024", "从视频生成模型里「学到」物体的材质参数，让高斯物体对戳、拉等交互做出合理的动态响应。",
                arxiv="2404.13026"),
          ]),
    ],
)

MODULES = [RECON, ORGANIZE, COMPRESS, GEOMETRY, RELIGHT, DYNAMIC]

# Folded block after the six modules.
APPS = dict(
    id="apps", no="延伸", name="更多应用", sub="SLAM · 自动驾驶 · 3D 生成", color="slate",
    question="同一套表示，还被用在哪里？",
    sections=[
        S("apps-all", "SLAM、自动驾驶与 3D 生成", "机器人建图 / 街景仿真 / 生成模型", "apps",
          hub=[], groups=[],
          extra=[
              W("DreamGaussian", "2023.09", "ICLR 2024 Oral", "用 2D 扩散模型的「打分」（SDS）优化高斯，几分钟内从文字或图片生成 3D 物体。",
                arxiv="2309.16653", code="https://github.com/dreamgaussian/dreamgaussian"),
              W("SplaTAM", "2023.12", "CVPR 2024", "RGB-D SLAM：边跟踪相机，边用高斯建图。",
                arxiv="2312.02126", code="https://github.com/spla-tam/SplaTAM"),
              W("Gaussian Splatting SLAM", "2023.12", "CVPR 2024 Highlight · 最佳 Demo", "只用单目相机，也能实时做高斯 SLAM。",
                arxiv="2312.06741", code="https://github.com/muskie82/MonoGS", aka="MonoGS"),
              W("DrivingGaussian", "2023.12", "CVPR 2024", "面向环视相机的动态驾驶场景重建。",
                arxiv="2312.07920"),
              W("Street Gaussians", "2024.01", "ECCV 2024", "把前景车辆和静态背景分开建模，重建自动驾驶街景。",
                arxiv="2401.01339", code="https://github.com/zju3dv/street_gaussians"),
              W("LGM", "2024.02", "ECCV 2024 Oral", "多视角扩散模型加前馈网络直接预测高斯，快速生成高分辨率 3D 物体。",
                arxiv="2402.05054", code="https://github.com/3DTopia/LGM"),
              W("TRELLIS", "2024.12", "CVPR 2025", "结构化的 3D 潜空间，同一个潜变量可以解码成高斯、辐射场或网格。",
                arxiv="2412.01506", code="https://github.com/microsoft/TRELLIS"),
              W("HunyuanWorld 1.0", "2025.07", "技术报告", "腾讯混元：从文字或图片生成可沉浸、可探索的 3D 世界。",
                arxiv="2507.21809"),
          ]),
    ],
)

# Relations drawn on the overview map (from 「3DGS 研究方向与技术关联」).
RELATIONS = [
    ("recon", "organize", "高斯场景"),
    ("organize", "compress", "LoD / 按需调度"),
    ("recon", "geometry", "几何提取"),
    ("geometry", "organize", "网格绑定"),
    ("organize", "relight", "材质编辑"),
    ("geometry", "relight", "法线 / 可见性"),
    ("dynamic", "compress", "动态呈现"),
]

# ---------------------------------------------------------------------------
# Timeline (hand-picked). mod = module id or "base".
# ---------------------------------------------------------------------------

TIMELINE = [
    ("2020", [
        dict(date="2020.03", name="NeRF", venue="ECCV 2020", mod="base", arxiv="2003.08934",
             text="用一个神经网络表示整个场景，沿光线采样、积分出图像。画质惊艳，但训练要以小时计，渲染一帧要数秒。"),
    ]),
    ("2021–2022", [
        dict(date="2021.11", name="Mip-NeRF 360", venue="CVPR 2022", mod="base", arxiv="2111.12077",
             text="把 NeRF 推到无界的 360° 真实场景，后来成了 3DGS 对比的画质标杆。"),
        dict(date="2021.12", name="Plenoxels", venue="CVPR 2022", mod="base", arxiv="2112.05131",
             text="不用神经网络，直接优化稀疏体素上的球谐系数，证明「显式表示 + 可微渲染」也行得通。"),
        dict(date="2022.01", name="Instant-NGP", venue="SIGGRAPH 2022", mod="base", arxiv="2201.05989",
             text="多分辨率哈希编码把 NeRF 训练缩短到分钟级。"),
    ]),
    ("2023", [
        dict(date="2023.08", name="3D Gaussian Splatting", venue="SIGGRAPH 2023 · TOG", mod="base", arxiv="2308.04079", star=True,
             text="用数百万个各向异性的 3D 高斯加可微光栅化，首次在 1080p 下实时渲染完整的真实场景，画质比肩 Mip-NeRF 360。"),
        dict(date="2023.08", name="Dynamic 3D Gaussians", venue="3DV 2024", mod="dynamic", arxiv="2308.09713",
             text="高斯第一次「动起来」：随时间移动，并顺带得到逐点跟踪。"),
        dict(date="2023.11", name="一个月内的密集爆发", venue="多篇", mod="base",
             text="Mip-Splatting（抗锯齿）、SuGaR（提取网格）、LightGaussian（压缩）、Scaffold-GS（结构化）、PhysGaussian（物理）、GaussianEditor（编辑）、R3DG（重光照）相继出现，几个方向几乎同时起步。"),
        dict(date="2023.12", name="DUSt3R 与 pixelSplat", venue="CVPR 2024", mod="recon",
             text="一个从两张照片直接回归 3D 点图，一个从两张照片直接预测高斯：「不跑 SfM」「不逐场景训练」两条路同时打开。"),
    ]),
    ("2024", [
        dict(date="2024.03", name="2DGS、Octree-GS、HAC、MVSplat", venue="多篇", mod="geometry",
             text="面元让几何变准，八叉树 LoD 让大场景变稳，上下文熵编码让文件变小，前馈重建变得更快更轻。"),
        dict(date="2024.04", name="3DGS-MCMC 与 GOF", venue="NeurIPS 2024 / TOG", mod="recon",
             text="致密化从手工规则走向「带预算的采样」；网格提取扩展到无界场景。"),
        dict(date="2024.06", name="Hierarchical 3DGS 与 Taming 3DGS", venue="SIGGRAPH 2024 / SIGGRAPH Asia 2024", mod="organize",
             text="原作者团队给出超大场景的层次化方案，以及「按预算训练」的工程范式。"),
        dict(date="2024.07", name="3DGRT", venue="SIGGRAPH Asia 2024", mod="geometry", arxiv="2407.07090",
             text="高斯可以被光线追踪了：反射、折射、阴影第一次有了物理上一致的路径。"),
        dict(date="2024.09", name="gsplat 论文", venue="JMLR（MLOSS）", mod="recon", arxiv="2409.06765",
             text="Apache-2.0 的开源光栅化库，逐渐成为研究和产品共用的底座。"),
        dict(date="2024.12", name="3DGUT 与 IRGS", venue="CVPR 2025", mod="relight",
             text="光栅化也能处理畸变相机和次级光线；重光照开始不再简化渲染方程。"),
    ]),
    ("2025", [
        dict(date="2025.01", name="DiffusionRenderer", venue="CVPR 2025 Oral", mod="relight", arxiv="2501.18590",
             text="用视频扩散模型做逆渲染和正向渲染，生成式方法进入重光照。"),
        dict(date="2025.03", name="VGGT", venue="CVPR 2025 最佳论文", mod="recon", arxiv="2503.11651", star=True,
             text="一次前向同时给出相机、深度和点图，「几何基础模型替代 SfM」得到最高规格的认可。"),
        dict(date="2025.03", name="Difix3D+", venue="CVPR 2025 Oral · 最佳论文候选", mod="recon", arxiv="2503.01774",
             text="单步扩散模型当「修图器」：先修新视角的伪影、再蒸馏回 3D，生成式修复成了提升重建质量的常用手段。"),
        dict(date="2025.05", name="AnySplat、Triangle Splatting 与 Spark", venue="SIGGRAPH Asia 2025 / 3DV 2026 / 开源", mod="recon",
             text="未标定照片一次前向出高斯；有人直接改用三角形向游戏引擎靠拢；World Labs 开源 three.js 高斯渲染库。"),
        dict(date="2025.05", name="PlayCanvas 采用 SOGS", venue="厂商发布", mod="compress",
             text="学术上的「自组织高斯网格」压缩进入 Web 引擎，官方称数据量可缩小 20 倍以上。"),
        dict(date="2025.06", name="MILo", venue="SIGGRAPH Asia 2025", mod="geometry", arxiv="2506.24096",
             text="网格进入训练循环：每一步都从高斯提取网格并回传误差。"),
        dict(date="2025.07", name="A LoD of Gaussians", venue="SIGGRAPH 2026", mod="organize", arxiv="2507.01110",
             text="不分块、用外存，把超大场景的训练和渲染塞进一张消费级显卡。"),
        dict(date="2025.11", name="FastGS", venue="CVPR 2026 Highlight", mod="recon", arxiv="2511.04283",
             text="逐场景训练压到百秒量级（作者自评）。"),
    ]),
    ("2026", [
        dict(date="2026.01", name="KHR_gaussian_splatting 合入 glTF 仓库", venue="Khronos", mod="compress",
             text="2 月发布候选版；截至 9 月，官方仓库中的状态为 Complete, Ratified。高斯泼溅有了开放的交换标准。"),
        dict(date="2026.02", name="Faster-GS", venue="CVPR 2026", mod="recon", arxiv="2602.09999",
             text="把各种加速技巧放到同一把尺子下重新评测，给出可复用的组合。"),
        dict(date="2026.04", name="HY-World 2.0", venue="技术报告", mod="recon", arxiv="2604.14268",
             text="WorldMirror 2.0 等模型开源，世界模型与前馈重建合流。"),
        dict(date="2026.06", name="TRON", venue="NVIDIA", mod="relight", arxiv="2606.11314",
             text="物理光追与神经渲染结合，追求「可控又真实」的重光照。"),
        dict(date="2026.08", name="FixAnything", venue="ECCV 2026", mod="recon", arxiv="2608.23549",
             text="一个视频生成模型通修 3DGS、NeRF、网格和点云的渲染伪影，修复器开始不挑表示。"),
    ]),
]

# ---------------------------------------------------------------------------
# Engineering ecosystem. Licences checked on GitHub on 2026-09-17.
# ---------------------------------------------------------------------------

ECOSYSTEM = [
    ("训练 · 原版", "Inria gaussian-splatting", "https://github.com/graphdeco-inria/gaussian-splatting",
     "论文参考实现与 SIBR 查看器。", "Inria 自定许可，仅限非商业研究。许多下游仓库把它的光栅器当子模块直接带着走。", "warn"),
    ("训练 · 底座", "gsplat", "https://github.com/nerfstudio-project/gsplat",
     "CUDA 光栅化库，含 MCMC、抗锯齿、3DGUT、压缩。", "Apache-2.0", "ok"),
    ("训练 · 框架", "Nerfstudio", "https://github.com/nerfstudio-project/nerfstudio",
     "模块化训练框架，高斯部分（splatfacto）基于 gsplat。", "Apache-2.0", "ok"),
    ("训练 · 跨平台", "Brush", "https://github.com/ArthurBrussee/brush",
     "Rust + WebGPU，可在多平台乃至浏览器里训练和查看。", "Apache-2.0", "ok"),
    ("训练 · 浏览器", "WebDGS", "https://github.com/krispy-kenay/WebDGS",
     "WebGPU 上的浏览器端训练与查看，个人项目。", "未声明许可证，默认保留所有权利。", "warn"),
    ("光追 / 混合", "3DGRUT", "https://github.com/nv-tlabs/3dgrut",
     "3DGRT、3DGUT 官方代码，Playground 可插入 PBR 网格。", "Apache-2.0", "ok"),
    ("编辑", "SuperSplat", "https://github.com/playcanvas/supersplat",
     "浏览器里的高斯编辑器。", "MIT", "ok"),
    ("Web 渲染", "PlayCanvas Engine", "https://github.com/playcanvas/engine",
     "WebGL / WebGPU 引擎，支持高斯与 SOGS 压缩格式。", "MIT", "ok"),
    ("Web 渲染", "Spark", "https://github.com/sparkjsdev/spark",
     "World Labs 出品的 three.js 高斯渲染库。", "MIT", "ok"),
    ("Unity", "UnityGaussianSplatting", "https://github.com/aras-p/UnityGaussianSplatting",
     "Unity 中的高斯可视化，作者自称「玩具」级实现。", "MIT", "ok"),
    ("Unreal", "XScene-UEPlugin", "https://github.com/xverse-engine/XScene-UEPlugin",
     "基于 Niagara 的 UE5 插件，支持与 UE 资产混合渲染。", "Apache-2.0", "ok"),
    ("格式", "SPZ", "https://github.com/nianticlabs/spz",
     "Niantic 的压缩格式，官方称约为 PLY 的 1/10。", "MIT", "ok"),
    ("标准", "KHR_gaussian_splatting", "https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_gaussian_splatting",
     "glTF 扩展；压缩扩展（SPZ、L-GSC 等）仍是提案。", "Khronos 规范", "ok"),
    ("前馈", "VGGT", "https://github.com/facebookresearch/vggt",
     "一次前向输出相机、深度、点图。", "自定许可（未标 SPDX），商用前核对代码与权重条款。", "warn"),
    ("前馈", "AnySplat", "https://github.com/InternRobotics/AnySplat",
     "未标定照片直接出高斯。", "MIT", "ok"),
    ("前馈", "HY-World 2.0 / WorldMirror", "https://github.com/Tencent-Hunyuan/HY-World-2.0",
     "腾讯混元的重建与世界生成模型。", "腾讯社区许可；协议写明不适用于欧盟、英国和韩国。", "warn"),
    ("几何", "PGSR", "https://github.com/zju3dv/PGSR",
     "平面化高斯表面重建。", "仅限教育、研究和非营利用途，禁止商用。", "warn"),
]

# ---------------------------------------------------------------------------
# Reading numbers
# ---------------------------------------------------------------------------

CAVEATS = [
    ("分辨率不同，PSNR 不可比",
     "同一个 Mip-NeRF 360 数据集，有的论文用 4 倍、2 倍降采样，有的用 1.6K 宽的原图。先看分辨率，再比数字。"),
    ("LPIPS 有两种骨干",
     "LPIPS 用 VGG 还是 AlexNet 算，数值差别很大，两种结果不能放在一列里比较。"),
    ("训练时间包不包含 SfM",
     "多数论文只报告优化本身的时间，不含 COLMAP 求位姿；GPU 型号（A6000、4090、A100）也会让数字差出几倍。"),
    ("FPS 在什么条件下测的",
     "分辨率、显卡、是否含排序、是否只统计测试视角，都会影响帧率。「实时」没有统一定义。"),
    ("压缩倍数相对谁",
     "「100 倍」可能相对原版 PLY，也可能相对 Scaffold-GS；解码网络和码本算不算进体积、画质是否持平，都要看清。"),
    ("前馈和逐场景优化不是一回事",
     "前馈方法常在 256×256 之类的低分辨率、两三张输入下评测，和逐场景优化的数字不能直接放在一起比。"),
    ("作者自评、厂商声明与第三方复测",
     "本页凡是来自作者自评或厂商宣传的数字都做了标注。第三方复测结果常和原文有出入，引用时注明出处。"),
]

# ---------------------------------------------------------------------------
# Glossary
# ---------------------------------------------------------------------------

GLOSSARY = [
    ("辐射场", "Radiance Field", "描述「空间中每个点、朝每个方向发出什么颜色的光」的函数。NeRF 用神经网络表示它，3DGS 用一堆高斯表示它。"),
    ("新视角合成", "Novel View Synthesis", "给定若干张照片，渲染出没拍过的视角的图像。"),
    ("SfM / COLMAP", "Structure from Motion", "从多张照片中同时求出相机位置和稀疏的三维点。COLMAP 是最常用的开源工具。"),
    ("位姿、内参、外参", "Pose / Intrinsics / Extrinsics", "外参说明相机在哪、朝哪；内参说明焦距、主点等成像参数。两者合起来，才知道一个像素对应哪条光线。"),
    ("3D 高斯", "3D Gaussian", "一个「软边的椭球」：中心决定位置，协方差决定大小和朝向，越往外越透明。"),
    ("协方差矩阵", "Covariance Σ", "描述椭球形状的 3×3 矩阵。3DGS 把它拆成缩放 S 和旋转 R：Σ = R S Sᵀ Rᵀ，保证训练中始终合法。"),
    ("四元数", "Quaternion", "用 4 个数表示三维旋转，比欧拉角更稳定，也没有万向锁。"),
    ("球谐函数", "Spherical Harmonics, SH", "定义在球面上的一组基函数，用来表示「从不同方向看颜色不同」。3 阶球谐每个颜色通道要 16 个系数，三个通道共 48 个。"),
    ("不透明度", "Opacity α", "高斯有多「实」：0 是完全透明，1 是完全不透明。"),
    ("α 混合", "Alpha Blending", "按从前到后的顺序，把半透明的颜色一层层叠起来：C = Σ cᵢ αᵢ Tᵢ。"),
    ("透光率", "Transmittance T", "光线穿过前面所有高斯后还剩多少。T 足够小时就可以提前停止。"),
    ("光栅化", "Rasterization", "把图元投影到屏幕、再逐像素填色的渲染方式，是 GPU 最擅长的事；与之相对的是光线追踪。"),
    ("图块", "Tile", "3DGS 把屏幕切成 16×16 像素的小块，每块只处理与之相交的高斯，便于在 GPU 上并行排序。"),
    ("可微渲染", "Differentiable Rendering", "渲染过程可以对参数求导，于是能用梯度下降去「拟合照片」。"),
    ("自适应密度控制", "Adaptive Density Control", "训练中按梯度克隆、分裂、剪除高斯的规则，也常叫致密化（densification）。"),
    ("漂浮物", "Floater", "空中多出来的半透明杂斑，常见原因是视角不足或致密化出错。"),
    ("锯齿", "Aliasing", "采样频率不够导致的阶梯边缘和闪烁；3DGS 在缩放时尤其明显。"),
    ("细节层级", "Level of Detail, LoD", "远处用粗模型、近处用细模型，是大场景实时渲染的基本手段。"),
    ("向量量化", "Vector Quantization", "用码本里最接近的代表向量替换原始向量，只存编号，从而压缩数据。"),
    ("熵编码", "Entropy Coding", "按出现概率分配码长的无损压缩；上下文模型把概率估得越准，文件越小。"),
    ("锚点", "Anchor", "Scaffold-GS 等方法里的稀疏控制点，由小网络据此生成周围的高斯。"),
    ("前馈重建", "Feed-forward Reconstruction", "不做逐场景优化，网络前向一次就输出三维结果。"),
    ("PSNR / SSIM / LPIPS", "Image Metrics", "三个常用画质指标：PSNR 看像素误差，SSIM 看结构相似度，这两个越高越好；LPIPS 用深度特征衡量感知差异，越低越好。"),
    ("逆渲染", "Inverse Rendering", "从图像反推几何、材质和光照，是重光照的前提。"),
    ("BRDF / PBR", "Physically Based Rendering", "BRDF 描述表面怎样反射光；PBR 是游戏和影视通用的材质体系，常用反照率、粗糙度、金属度三个参数。"),
    ("G-buffer 与延迟着色", "Deferred Shading", "先把法线、材质、深度等画进一组缓冲，再统一逐像素算光照；Unreal Engine 等引擎默认用这种管线。"),
    ("网格", "Mesh", "由顶点和三角形组成的表面，是游戏引擎的通用资产格式。"),
    ("物质点法", "MPM", "用粒子携带物质、在背景网格上求解动力学的仿真方法，擅长雪、沙和弹塑性物体。"),
    ("线性混合蒙皮", "LBS", "用若干骨骼或控制点的加权变换驱动顶点，是角色动画的标准做法。"),
    ("SDS", "Score Distillation Sampling", "借用预训练 2D 扩散模型的「打分」来优化 3D 表示，是文字生成 3D 的常用技巧。"),
]

# ---------------------------------------------------------------------------
# Corrections to the source survey, and other notes
# ---------------------------------------------------------------------------

ERRATA = [
    ("GOF 的发表处", "综述写作 NeurIPS 2024；实际发表于 ACM TOG 43(6)，即 SIGGRAPH Asia 2024 期刊轨（官方仓库亦如此标注）。",
     "https://github.com/autonomousvision/gaussian-opacity-fields"),
    ("Octree-GS 的发表处", "综述写作 NeurIPS 2024；官方仓库标注为 TPAMI 2025。",
     "https://github.com/city-super/Octree-GS"),
    ("GaussianEditor 的发表处", "综述写作 ECCV 2024；arXiv:2311.14521 实际收录于 CVPR 2024。另有同名工作 arXiv:2311.16037（同为 CVPR 2024），引用时按编号区分。",
     "https://github.com/buaacyw/GaussianEditor"),
    ("参考文献 [19]", "综述中的「Towards 100× Compression」就是 HAC++（TPAMI 2025），是 HAC 的期刊扩展，而非一篇独立的新工作。",
     "https://arxiv.org/abs/2501.12255"),
    ("KHR_gaussian_splatting 的状态（更新）", "综述写到 2026 年 2 月发布候选版为止。截至 2026-09-17，Khronos 官方 glTF 仓库中该扩展的状态已为 Complete, Ratified；压缩相关扩展（SPZ、L-GSC、EGSC 等）仍是未合并的提案。",
     "https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_gaussian_splatting"),
    ("两篇改过题名的论文", "Gaussian Head Avatar（CVPR 2024）在 arXiv 上的现题名为 HHAvatar；Animatable Gaussians（CVPR 2024）的现题名为 Animatable and Relightable Gaussians。两者都是扩展版，本页按会议版本的名称列出。",
     "https://arxiv.org/abs/2312.03029"),
]
