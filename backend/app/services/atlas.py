"""健康可视化页面使用的人体系统科普数据。"""

from __future__ import annotations

from app.models import (
    AtlasBodyRegion,
    AtlasModelProfile,
    AtlasOrgan,
    AtlasSymptomOption,
    AtlasSystem,
    BodyAtlasResponse,
)


_SYMPTOMS = {
    "generic": [
        ("pain", "疼痛", "这个部位疼痛"),
        ("swelling", "肿胀", "这个部位肿胀"),
        ("numbness", "麻木或刺痛", "这个部位麻木或刺痛"),
        ("rash", "发红、皮疹或瘙痒", "这个部位发红、起疹或瘙痒"),
        ("injury", "碰伤或外伤", "这个部位有碰伤或外伤"),
    ],
    "head": [
        ("pain", "疼痛", "头面部局部疼痛"),
        ("pressure", "发紧或胀痛", "头面部局部发紧或胀痛"),
        ("numbness", "麻木或感觉异常", "头面部局部麻木或感觉异常"),
        ("swelling", "肿胀或包块", "头面部局部肿胀或摸到包块"),
        ("injury", "碰伤", "头面部局部受到碰撞"),
    ],
    "eye": [
        ("pain", "眼周或眼球痛", "眼周或眼球疼痛"),
        ("redness", "眼红或分泌物", "眼红或有异常分泌物"),
        ("vision", "看不清或重影", "视物模糊或出现重影"),
        ("light", "怕光", "眼睛怕光"),
        ("swelling", "眼皮肿", "眼睑或眼周肿胀"),
    ],
    "ear": [
        ("pain", "耳朵痛", "耳部疼痛"),
        ("tinnitus", "耳鸣", "耳内出现鸣响"),
        ("hearing", "听不清", "听力下降"),
        ("discharge", "流液或流脓", "耳部流液或流脓"),
        ("swelling", "耳周肿胀", "耳廓或耳周肿胀"),
    ],
    "mouth": [
        ("pain", "疼痛", "口唇、口腔或下颌疼痛"),
        ("ulcer", "破溃或溃疡", "口唇或口腔出现破溃"),
        ("swelling", "肿胀", "口唇、口腔或下颌肿胀"),
        ("swallow", "吞咽不舒服", "吞咽时不适"),
        ("movement", "张口受限", "张口或咀嚼受限"),
    ],
    "neck": [
        ("pain", "颈部疼痛", "颈部疼痛"),
        ("stiff", "僵硬或转头困难", "颈部僵硬或活动受限"),
        ("lump", "摸到肿块", "颈部摸到肿块"),
        ("swallow", "吞咽不适", "颈部伴吞咽不适"),
        ("injury", "扭伤或外伤", "颈部扭伤或受到外伤"),
    ],
    "chest": [
        ("pain", "疼痛", "胸部疼痛"),
        ("tightness", "发闷或压迫感", "胸部发闷或有压迫感"),
        ("breathing", "呼吸时不舒服", "胸部不适与呼吸有关"),
        ("palpitation", "心慌或心跳异常", "伴有心慌或心跳感觉异常"),
        ("swelling", "肿胀或包块", "胸壁或乳房区域肿胀或摸到包块"),
    ],
    "abdomen": [
        ("pain", "疼痛", "腹部局部疼痛"),
        ("bloating", "发胀", "腹部发胀"),
        ("nausea", "恶心或呕吐", "伴恶心或呕吐"),
        ("diarrhea", "拉肚子", "伴腹泻"),
        ("constipation", "排便困难", "伴便秘或排便困难"),
        ("lump", "摸到包块", "腹部摸到包块"),
    ],
    "back": [
        ("pain", "疼痛", "背部或腰部疼痛"),
        ("stiff", "僵硬", "背部或腰部僵硬"),
        ("numbness", "麻木或放射痛", "背部不适伴麻木或向其他部位放射"),
        ("movement", "活动时加重", "背部不适在活动时加重"),
        ("injury", "扭伤或外伤", "背部或腰部扭伤或受到外伤"),
    ],
    "perineal": [
        ("pain", "疼痛", "会阴或肛周疼痛"),
        ("itch", "瘙痒", "会阴或肛周瘙痒"),
        ("bleeding", "出血", "会阴或肛周出血"),
        ("swelling", "肿胀或包块", "会阴或肛周肿胀或摸到包块"),
        ("discharge", "异常分泌物", "会阴部出现异常分泌物"),
    ],
    "limb": [
        ("pain", "疼痛", "肢体局部疼痛"),
        ("swelling", "肿胀", "肢体局部肿胀"),
        ("numbness", "麻木或刺痛", "肢体局部麻木或刺痛"),
        ("weakness", "无力", "肢体感觉无力"),
        ("movement", "活动受限", "肢体活动受限"),
        ("injury", "扭伤或外伤", "肢体局部扭伤或受到外伤"),
    ],
    "joint": [
        ("pain", "关节痛", "关节疼痛"),
        ("swelling", "关节肿", "关节肿胀"),
        ("redness", "发红或发热", "关节局部发红或发热"),
        ("sound", "弹响或卡住", "关节活动时弹响或卡住"),
        ("movement", "活动受限", "关节活动受限"),
        ("injury", "扭伤或外伤", "关节扭伤或受到外伤"),
    ],
}


def _symptom_options(category: str) -> list[AtlasSymptomOption]:
    """把部位类别转换为可多选的通俗症状选项。

    Args:
        category: 头面部、胸部、腹部或肢体等症状模板类别。

    Returns:
        适合普通用户理解和勾选的症状选项。
    """

    return [
        AtlasSymptomOption(id=item[0], label=item[1], query_text=item[2])
        for item in _SYMPTOMS.get(category, _SYMPTOMS["generic"])
    ]


def _organ(
    organ_id: str,
    name: str,
    summary: str,
    observation: str,
    mesh_aliases: list[str],
    category: str,
    available_models: list[str] | None = None,
) -> AtlasOrgan:
    """创建可由内部三维网格点击并加入问诊的器官数据。

    Args:
        organ_id: 稳定器官标识。
        name: 面向普通用户的中文器官名称。
        summary: 器官功能与位置简介。
        observation: 需要注意的症状线索。
        mesh_aliases: 用于匹配 GLB 节点名称的英文别名。
        category: 快捷症状模板类别。
        available_models: 可展示该器官的解剖模型；为空时表示男女模型均可用。

    Returns:
        包含网格别名和快捷症状的器官数据。
    """

    return AtlasOrgan(
        id=organ_id,
        name=name,
        summary=summary,
        observation=observation,
        mesh_aliases=mesh_aliases,
        symptom_options=_symptom_options(category),
        available_models=available_models or ["male", "female"],
    )


def _region(
    region_id: str,
    name: str,
    english_name: str,
    group: str,
    side: str,
    location: str,
    summary: str,
    mesh_aliases: list[str],
    category: str,
) -> AtlasBodyRegion:
    """创建一条可与三维网格匹配的身体部位说明。

    Args:
        region_id: 稳定的身体部位标识。
        name: 面向普通用户的中文名称。
        english_name: 医学解剖英文名称。
        group: 页面分组名称。
        side: 左、右、中线或双侧标识。
        location: 帮助用户确认位置的通俗描述。
        summary: 该位置包含的主要结构说明。
        mesh_aliases: 可匹配 Three.js 模型节点的英文别名。
        category: 决定症状选项集合的模板类别。

    Returns:
        完整的细分身体区域数据。
    """

    return AtlasBodyRegion(
        id=region_id,
        name=name,
        english_name=english_name,
        group=group,
        side=side,
        location=location,
        summary=summary,
        mesh_aliases=mesh_aliases,
        symptom_options=_symptom_options(category),
    )


def _paired_regions(
    region_id: str,
    name: str,
    english_name: str,
    group: str,
    location: str,
    summary: str,
    aliases: list[str],
    category: str,
) -> list[AtlasBodyRegion]:
    """生成左右两侧独立可选的身体区域。

    Args:
        region_id: 不含左右前缀的基础标识。
        name: 不含左右描述的中文部位名称。
        english_name: 三维模型使用的英文结构名称。
        group: 页面分组名称。
        location: 通俗位置描述。
        summary: 主要解剖结构说明。
        aliases: 不含侧别后缀的模型节点别名。
        category: 症状选项模板类别。

    Returns:
        分别对应人体左侧和右侧的两条区域数据。
    """

    side_names = {"left": ("左侧", "l"), "right": ("右侧", "r")}
    return [
        _region(
            f"{side}-{region_id}",
            f"{label}{name}",
            english_name,
            group,
            side,
            f"人体{label}{location}",
            summary,
            [f"{alias}.{suffix}" for alias in aliases],
            category,
        )
        for side, (label, suffix) in side_names.items()
    ]


def _build_body_regions() -> list[AtlasBodyRegion]:
    """构建覆盖头面、躯干九区、背部和四肢前后侧的细分定位目录。

    Returns:
        可映射到高精度体表 GLB 网格的身体区域列表。
    """

    paired_specs = [
        ("forehead", "额头", "Frontal region", "头面部", "前额", "额骨前方的软组织区域。", ["Frontal region", "Eyebrow", "Hairs of eyebrow"], "head"),
        ("temple", "太阳穴", "Temporal region", "头面部", "头部两侧、眼睛外上方", "颞部覆盖颞骨及颞肌。", ["Temporal region"], "head"),
        ("eye", "眼睛和眼眶", "Orbital region", "头面部", "眼球及眼睛周围", "包含眼球、眼睑与骨性眼眶周围。", ["Orbital region", "Infra-orbital region", "Eyelashes"], "eye"),
        ("ear", "耳朵和耳周", "Auricular region", "头面部", "耳廓及耳朵周围", "包含耳廓、耳后和邻近软组织。", ["Auricular region", "auricle", "Helix", "Antihelix", "Antitragus", "Tragus", "Concha", "Scapha", "Intertragic incisure", "Cymba conchae", "Mastoid region", "Auricular tubercle", "Eminentia conchae", "Eminentia fossae triangularis", "Eminentia scaphae", "Fossa antihelica", "Posterior auricular groove", "Triangular fossa"], "ear"),
        ("cheek", "面颊", "Buccal region", "头面部", "鼻子和耳朵之间的脸颊", "覆盖颊肌、皮下组织及腮腺邻近区域。", ["Buccal region", "Zygomatic region", "Parotideomasseteric region"], "head"),
        ("nose", "鼻部", "Nasal region", "头面部", "面部中央的鼻及鼻旁", "包含外鼻与鼻旁软组织。", ["Nasal region", "Nasolabial sulcus"], "head"),
        ("mouth-jaw", "口周和下颌", "Oral and mental region", "头面部", "嘴唇、嘴角和下巴", "包含口唇、口角、颏部及下颌表面。", ["Oral region", "Angle of mouth", "Labial commissure", "Mental region", "Mentolabial sulcus", "Philtrum", "Tubercle of upper lip"], "mouth"),
        ("side-neck", "颈侧", "Lateral region of neck", "颈部", "耳下至锁骨之间的颈部侧面", "包含胸锁乳突肌周围、颈动脉三角等区域。", ["Lateral region of neck", "Sternocleidomastoid region", "Carotid triangle", "Muscular triangle"], "neck"),
        ("supraclavicular", "锁骨上窝", "Supraclavicular fossa", "颈部", "颈根部和锁骨上方的凹陷", "为颈部、胸廓入口和肩部相邻区域。", ["Greater supraclavicular fossa", "Lesser supraclavicular fossa"], "neck"),
        ("shoulder", "肩部", "Deltoid region", "上肢", "颈部外侧与上臂连接处", "包含三角肌覆盖区和肩关节周围。", ["Deltoid region", "Deltopectoral triangle"], "joint"),
        ("front-upper-arm", "上臂前侧", "Anterior region of arm", "上肢", "肩到肘之间的前面", "主要覆盖肱二头肌所在区域。", ["Anterior region of arm", "Medial bicipital groove", "Lateral bicipital groove"], "limb"),
        ("back-upper-arm", "上臂后侧", "Posterior region of arm", "上肢", "肩到肘之间的后面", "主要覆盖肱三头肌所在区域。", ["Posterior region of arm"], "limb"),
        ("front-elbow", "肘窝", "Cubital fossa", "上肢", "肘关节前方凹陷", "包含肘窝及其周围肌腱、血管和神经。", ["Cubital fossa", "Anterior region of elbow"], "joint"),
        ("back-elbow", "肘后", "Posterior region of elbow", "上肢", "肘尖及肘关节后侧", "覆盖尺骨鹰嘴和肘后软组织。", ["Posterior region of elbow"], "joint"),
        ("front-forearm", "前臂前侧", "Anterior region of forearm", "上肢", "肘到手腕之间、手掌同侧", "包含前臂屈肌群及腕管上游区域。", ["Anterior region of forearm", "Medial border of forearm"], "limb"),
        ("back-forearm", "前臂后侧", "Posterior region of forearm", "上肢", "肘到手腕之间、手背同侧", "包含前臂伸肌群。", ["Posterior region of forearm", "Lateral border of forearm"], "limb"),
        ("wrist", "手腕", "Wrist region", "上肢", "前臂与手掌交界处", "包含腕关节、肌腱和腕管邻近结构。", ["Anterior region of wrist", "Posterior region of wrist", "Radial foveola"], "joint"),
        ("palm", "手掌", "Palm", "上肢", "手的掌面", "包含掌骨、肌腱、神经和掌侧软组织。", ["Palm", "Palmar surfaces of digits of hand"], "limb"),
        ("back-hand", "手背和手指", "Dorsum of hand", "上肢", "手的背面和手指", "覆盖手背、手指背侧和甲周。", ["Dorsum of hand", "Dorsal surfaces of digits of hand", "Nail plate", "Perionyx"], "limb"),
        ("hip", "髋部", "Hip region", "下肢", "腰部外下方与大腿连接处", "包含髋关节周围、肌腱和软组织。", ["Hip region"], "joint"),
        ("groin", "腹股沟", "Inguinal region", "腹部与骨盆", "下腹部与大腿根部交界", "为腹壁、腹股沟管和髋前区相邻位置。", ["Inguinal region", "Femoral triangle"], "abdomen"),
        ("buttock", "臀部", "Gluteal region", "背部与骨盆", "骨盆后方的臀部", "主要覆盖臀肌和坐骨周围软组织。", ["Gluteal region", "Gluteal fold"], "back"),
        ("front-thigh", "大腿前侧", "Anterior region of thigh", "下肢", "腹股沟到膝盖之间的前面", "主要覆盖股四头肌区域。", ["Anterior region of thigh"], "limb"),
        ("back-thigh", "大腿后侧", "Posterior region of thigh", "下肢", "臀部到膝窝之间的后面", "主要覆盖腘绳肌区域。", ["Posterior region of thigh"], "limb"),
        ("front-knee", "膝盖前侧", "Anterior region of knee", "下肢", "膝关节和髌骨前方", "包含髌骨、肌腱和膝关节前侧软组织。", ["Anterior region of knee"], "joint"),
        ("back-knee", "膝窝", "Popliteal fossa", "下肢", "膝关节后方凹陷", "包含腘窝血管、神经及肌腱邻近区域。", ["Posterior region of knee", "Popliteal fossa"], "joint"),
        ("front-leg", "小腿前侧", "Anterior region of leg", "下肢", "膝盖到脚踝之间的前面", "主要覆盖胫骨前方和小腿前群肌。", ["Anterior region of leg"], "limb"),
        ("back-leg", "小腿后侧", "Posterior region of leg", "下肢", "膝窝到脚跟之间的后面", "主要覆盖小腿三头肌及跟腱上方。", ["Posterior region of leg"], "limb"),
        ("ankle", "脚踝", "Ankle region", "下肢", "小腿与脚的连接处", "包含踝关节、内外踝及周围韧带。", ["Anterior region of ankle", "Lateral malleolus", "Medial malleolus", "retromalleolar region"], "joint"),
        ("heel", "脚跟", "Heel region", "下肢", "脚的后下方、落地受力处", "包含跟骨、足底筋膜后端和跟腱止点邻近区域。", ["Heel region"], "limb"),
        ("top-foot", "脚背", "Dorsum of foot", "下肢", "脚的上表面", "覆盖跗骨、跖骨、伸肌腱和足趾背侧。", ["Dorsum of foot", "Dorsal surfaces of digits of foot", "Metatarsal region", "Nail plate (foot)", "Perionyx (foot)"], "limb"),
        ("sole", "脚底和脚趾", "Sole", "下肢", "脚的底面和脚趾掌侧", "包含足底筋膜、足弓和足趾底面。", ["Sole", "Plantar surfaces of digits of foot", "Hallucial eminence", "arch of foot", "border of foot"], "limb"),
    ]
    regions: list[AtlasBodyRegion] = []
    for spec in paired_specs:
        regions.extend(_paired_regions(*spec))

    regions.extend(
        [
            _region("back-head", "后脑勺和头皮", "Occipital region", "头面部", "middle", "头部后下方及头皮", "覆盖枕骨后方、头顶部和头皮软组织。", ["Occipital region.l", "Occipital region.r", "Parietal region.l", "Parietal region.r", "Hairs of head"], "head"),
            _region("front-neck", "颈前和咽喉", "Anterior neck triangles", "颈部", "middle", "下巴下方到胸骨上方", "包含颏下、下颌下和咽喉表面区域。", ["Submental triangle.l", "Submental triangle.r", "Submandibular triangle.l", "Submandibular triangle.r"], "neck"),
            _region("back-neck", "后颈", "Posterior region of neck", "颈部", "middle", "后脑勺下方到上背部", "覆盖颈椎后方和颈后肌群。", ["Posterior region of neck.l", "Posterior region of neck.r"], "neck"),
            _region("center-chest", "胸口正中", "Presternal region", "胸部", "middle", "两侧胸部之间、胸骨前方", "对应胸骨和前纵隔表面投影区域。", ["Presternal region.l", "Presternal region.r"], "chest"),
            _region("left-chest", "左侧胸部", "Left pectoral region", "胸部", "left", "左侧锁骨下方至肋缘上方", "覆盖左侧胸壁、胸肌和乳房区域。", ["Pectoral region.l", "Mammary region.l", "Inframammary region.l", "Infraclavicular fossa.l", "Lateral region of thorax.l"], "chest"),
            _region("right-chest", "右侧胸部", "Right pectoral region", "胸部", "right", "右侧锁骨下方至肋缘上方", "覆盖右侧胸壁、胸肌和乳房区域。", ["Pectoral region.r", "Mammary region.r", "Inframammary region.r", "Infraclavicular fossa.r", "Lateral region of thorax.r"], "chest"),
            _region("upper-middle-abdomen", "上腹正中", "Epigastric region", "腹部与骨盆", "middle", "胸骨下端与肚脐之间", "医学上称上腹部或心窝，邻近胃、胰腺和肝左叶表面投影。", ["Epigastric region.l", "Epigastric region.r"], "abdomen"),
            _region("left-upper-abdomen", "左上腹", "Left hypochondriac region", "腹部与骨盆", "left", "左侧肋骨下缘以内", "邻近胃、脾、胰尾和左肾等结构的表面投影。", ["Hypochondriac region.l"], "abdomen"),
            _region("right-upper-abdomen", "右上腹", "Right hypochondriac region", "腹部与骨盆", "right", "右侧肋骨下缘以内", "邻近肝、胆囊、十二指肠和右肾等结构的表面投影。", ["Hypochondriac region.r"], "abdomen"),
            _region("around-navel", "肚脐周围", "Umbilical region", "腹部与骨盆", "middle", "肚脐及其周围", "邻近小肠、横结肠等腹腔结构的表面投影。", ["Umbilical region.l", "Umbilical region.r", "Umbilicus.l", "Umbilicus.r"], "abdomen"),
            _region("left-side-abdomen", "左侧腹部", "Left lateral abdominal region", "腹部与骨盆", "left", "左上腹和左下腹之间的侧腹", "邻近降结肠、左肾和腹壁肌肉等结构。", ["Lateral region of abdomen.l"], "abdomen"),
            _region("right-side-abdomen", "右侧腹部", "Right lateral abdominal region", "腹部与骨盆", "right", "右上腹和右下腹之间的侧腹", "邻近升结肠、右肾和腹壁肌肉等结构。", ["Lateral region of abdomen.r"], "abdomen"),
            _region("lower-middle-abdomen", "下腹正中", "Hypogastric region", "腹部与骨盆", "middle", "肚脐下方到耻骨上方", "邻近膀胱、肠道及生殖系统部分结构的表面投影。", ["Hypogastric region.l", "Hypogastric region.r", "Urogenital region.l", "Urogenital region.r"], "abdomen"),
            _region("pubic-region", "耻骨和外阴上方", "Pubic region", "腹部与骨盆", "middle", "下腹部最下方、外生殖器上方", "覆盖耻骨联合及其表面软组织。", ["Pubic hairs"], "perineal"),
            _region("perianal-region", "肛周", "Anal region", "腹部与骨盆", "middle", "臀沟下方、肛门周围", "包含肛门周围皮肤和会阴后部软组织。", ["Anal region.l", "Anal region.r"], "perineal"),
            _region("left-shoulder-blade", "左肩胛区", "Left scapular region", "背部与骨盆", "left", "左侧上背部肩胛骨表面", "覆盖肩胛骨、肩胛周围肌群及相邻胸壁。", ["Scapular region.l", "Infrascapular region.l", "Triangle of auscultation.l"], "back"),
            _region("right-shoulder-blade", "右肩胛区", "Right scapular region", "背部与骨盆", "right", "右侧上背部肩胛骨表面", "覆盖肩胛骨、肩胛周围肌群及相邻胸壁。", ["Scapular region.r", "Infrascapular region.r", "Triangle of auscultation.r"], "back"),
            _region("upper-middle-back", "上背正中", "Interscapular region", "背部与骨盆", "middle", "两侧肩胛骨之间", "覆盖胸椎上段和肩胛间肌群。", ["Interscapular region.l", "Interscapular region.r"], "back"),
            _region("spine", "脊柱沿线", "Vertebral region", "背部与骨盆", "middle", "后颈到腰骶部的背部正中线", "对应颈椎、胸椎和腰椎后方表面区域。", ["Vertebral region.l", "Vertebral region.r"], "back"),
            _region("left-lower-back", "左侧腰部", "Left lumbar region", "背部与骨盆", "left", "左侧肋骨下缘与骨盆之间的后外侧", "覆盖腰背肌，也邻近左肾表面投影区域。", ["Lumbar region.l"], "back"),
            _region("right-lower-back", "右侧腰部", "Right lumbar region", "背部与骨盆", "right", "右侧肋骨下缘与骨盆之间的后外侧", "覆盖腰背肌，也邻近右肾表面投影区域。", ["Lumbar region.r"], "back"),
            _region("sacrum-tailbone", "骶尾部", "Sacral region", "背部与骨盆", "middle", "腰部下方、两侧臀部之间", "覆盖骶骨、尾骨和邻近软组织。", ["Sacral region.l", "Sacral region.r"], "back"),
        ]
    )
    return regions


def build_body_atlas() -> BodyAtlasResponse:
    """构建不包含个体诊断结论的人体系统认知数据。

    Returns:
        可供前端交互式人体图谱展示的系统与器官说明。
    """

    body_regions = _build_body_regions()
    systems = [
        AtlasSystem(
            id="regional",
            name="体表精细定位",
            english_name="REGIONAL ANATOMY",
            color="#67e8d5",
            summary=(
                "按头面、颈、胸腹九区、背部及四肢前后侧定位。"
                "可直接点击三维体表区域，不需要先知道专业名称。"
            ),
            organs=[],
            available_models=["male"],
        ),
        AtlasSystem(
            id="nervous",
            name="神经系统",
            english_name="NERVOUS SYSTEM",
            color="#7dd3fc",
            summary="负责感觉、运动、认知与自主调节，是全身信息处理网络。",
            organs=[
                _organ("brain", "大脑", "位于颅腔内，整合感觉、认知与运动控制。", "持续意识改变、突发言语或肢体异常需要及时评估。", ["brain", "cerebr", "cortex", "gyrus", "sulcus", "cerebell", "thalam", "amygdaloid", "caudate nucleus", "corpus callosum"], "head"),
                _organ("spinal", "脊髓与周围神经", "脊髓连接大脑与全身周围神经。", "新发肢体无力或大小便功能异常属于重要信号。", ["spinal cord", "spinal nerve", "cauda equina", "nerve", "plexus", "tract", "fasciculus"], "back"),
            ],
            available_models=["male"],
        ),
        AtlasSystem(
            id="circulatory",
            name="循环系统",
            english_name="CIRCULATORY SYSTEM",
            color="#fb7185",
            summary="由心脏与血管组成，维持氧、营养和代谢物运输。",
            organs=[
                _organ("heart", "心脏", "位于胸腔中央偏左，通过节律性收缩推动血液循环。", "胸痛伴呼吸困难、大汗或晕厥需要急症评估。", ["heart", "ventricle", "atrium", "coronary", "papillary muscle", "valve"], "chest"),
                _organ("vessels", "血管", "动脉和静脉连接心脏与全身组织。", "肢体突然苍白、发凉、明显肿胀或神经功能异常需要及时评估。", ["artery", "aorta", "vein", "venous", "sinus", "vascular", "trunk"], "limb"),
            ],
        ),
        AtlasSystem(
            id="respiratory",
            name="呼吸系统",
            english_name="RESPIRATORY SYSTEM",
            color="#5eead4",
            summary="完成空气传导和肺泡气体交换，维持氧合与酸碱平衡。",
            organs=[
                _organ("lungs", "肺和胸膜", "位于左右胸腔，完成氧气与二氧化碳交换。", "明显气促、口唇发紫或咯血应尽快线下评估。", ["lobe of", "lung", "pleura"], "chest"),
                _organ("airway", "气管和支气管", "从咽喉向左右肺输送空气。", "喘鸣和气道阻塞表现需结合发作速度与诱因判断。", ["trachea", "bronchus", "bronchi"], "chest"),
            ],
            available_models=["male"],
        ),
        AtlasSystem(
            id="digestive",
            name="消化系统",
            english_name="DIGESTIVE SYSTEM",
            color="#fbbf24",
            summary="完成食物消化、营养吸收、代谢处理与废物排出。",
            organs=[
                _organ("mouth-pharynx", "口腔与咽部", "完成咀嚼、味觉并启动吞咽。", "吞咽困难、明显流涎或呼吸受影响需要及时评估。", ["tooth", "incisor", "canine", "molar", "premolar", "gingiva", "tongue", "pharynx", "uvula", "salivary", "parotid", "sublingual", "submandibular"], "mouth"),
                _organ("esophagus", "食管", "连接咽部与胃，将食物送入胃内。", "进行性吞咽困难、吞咽疼痛或呕血需要及时评估。", ["oesophagus", "esophagus", "epiglottis"], "chest"),
                _organ("stomach", "胃", "位于上腹部，储存并初步消化食物。", "疼痛与空腹或进食的关系是消化道问诊的重要线索。", ["stomach"], "abdomen"),
                _organ("liver", "肝脏", "主要位于右上腹，参与代谢、合成与解毒。", "黄疸、深色尿或明显右上腹不适需要结合检查评估。", ["liver"], "abdomen"),
                _organ("gallbladder", "胆囊和胆管", "位于肝脏下方，储存胆汁并输送至肠道。", "右上腹剧痛伴发热、黄疸或持续呕吐需要及时评估。", ["gallbladder", "bile duct"], "abdomen"),
                _organ("pancreas", "胰腺", "位于上腹深部，参与消化和血糖调节。", "持续剧烈上腹痛并向背部放射需要及时评估。", ["pancreas", "pancreatic"], "abdomen"),
                _organ("small-intestine", "小肠", "包括十二指肠和空肠等，主要负责营养吸收。", "持续呕吐、明显腹胀或严重腹痛需要及时评估。", ["duodenum", "jejunum", "ileum"], "abdomen"),
                _organ("large-intestine", "大肠和阑尾", "吸收水分并形成粪便，包括结肠和阑尾。", "便血、停止排气排便或进行性右下腹痛需要及时评估。", ["colon", "taenia", "appendix"], "abdomen"),
                _organ("anorectal", "直肠和肛门", "消化道末端，负责储存并排出粪便。", "大量便血、黑便或肛周剧痛伴发热需要及时评估。", ["anal sphincter", "rectum", "anus"], "perineal"),
            ],
        ),
        AtlasSystem(
            id="urinary",
            name="泌尿系统",
            english_name="URINARY SYSTEM",
            color="#a78bfa",
            summary="调节体液、电解质与代谢废物排出。",
            organs=[
                _organ("kidney", "肾脏和肾盂", "位于左右腰背深部，过滤血液并调节水盐平衡。", "尿量骤减、肉眼血尿或腰痛伴发热需要及时评估。", ["kidney", "renal pelvis"], "back"),
                _organ("ureter", "输尿管", "连接肾脏与膀胱，输送尿液。", "腰腹绞痛、肉眼血尿或伴发热需要及时评估。", ["ureter"], "abdomen"),
                _organ("bladder", "膀胱", "位于下腹和骨盆内，储存尿液。", "尿频尿急等表现需结合疼痛、发热和持续时间。", ["urinary bladder"], "abdomen"),
                _organ("urethra", "尿道", "将膀胱内尿液排出体外。", "完全无法排尿、明显血尿或剧烈疼痛需要及时评估。", ["urethra"], "perineal"),
            ],
        ),
        AtlasSystem(
            id="musculoskeletal",
            name="运动系统",
            english_name="MUSCULOSKELETAL SYSTEM",
            color="#94a3b8",
            summary="骨骼、关节与肌肉共同完成支撑、保护和运动。",
            organs=[
                _organ("spine-bones", "脊柱与躯干骨骼", "支撑躯干并保护脊髓和胸腹器官。", "创伤后明显脊柱疼痛、肢体无力或大小便异常需要及时评估。", ["vertebra", "sternum", "rib", "sacrum", "coccyx", "intervertebral disc"], "back"),
                _organ("upper-limb-bones", "上肢骨骼与关节", "包括肩、上臂、肘、前臂、腕和手部骨骼。", "创伤后畸形、手部发凉发白或感觉异常需要及时处理。", ["clavicle", "scapula", "humerus", "radius", "ulna", "carpal", "metacarpal", "finger of hand"], "joint", ["male"]),
                _organ("lower-limb-bones", "下肢骨骼与关节", "包括骨盆、髋、大腿、膝、小腿、踝和足部骨骼。", "创伤后不能负重、明显畸形或足部发凉发白需要及时处理。", ["hip bone", "femur", "patella", "tibia", "fibula", "tarsal", "metatarsal", "finger of foot", "calcaneus"], "joint", ["male"]),
                _organ("muscles", "肌肉与肌腱", "产生运动、稳定关节并维持姿势。", "明显无力、肌肉剧痛或外伤后功能丧失需要结合检查评估。", ["muscle", "tendon", "ligament"], "limb", ["male"]),
            ],
        ),
        AtlasSystem(
            id="integumentary",
            name="乳房精细结构",
            english_name="INTEGUMENTARY SYSTEM",
            color="#f0a6ca",
            summary="展示女性乳房、乳头乳晕、乳腺叶和乳管等结构，用于精细定位而非影像诊断。",
            organs=[
                _organ(
                    "breast-left",
                    "左侧乳房",
                    "位于左侧前胸壁，包含乳腺、乳头乳晕及周围软组织。",
                    "新发包块、皮肤凹陷、血性溢液或明显红肿发热需要线下评估。",
                    ["fat_L", "mammary_lobes_L", "nipple_L", "areola_L", "lactiferous_ducts_L", "lactiferous_sinuses_L", "suspensory_ligaments_L"],
                    "chest",
                    ["female"],
                ),
                _organ(
                    "breast-right",
                    "右侧乳房",
                    "位于右侧前胸壁，包含乳腺、乳头乳晕及周围软组织。",
                    "新发包块、皮肤凹陷、血性溢液或明显红肿发热需要线下评估。",
                    ["fat_R", "mammary_lobes_R", "nipple_R", "areola_R", "lactiferous_ducts_R", "lactiferous_sinuses_R", "suspensory_ligaments_R"],
                    "chest",
                    ["female"],
                ),
            ],
            available_models=["female"],
        ),
        AtlasSystem(
            id="lymphatic",
            name="脾脏",
            english_name="LYMPHATIC SYSTEM",
            color="#9ee493",
            summary="当前女性参考图层仅包含脾脏及其表面结构，不包含全身淋巴结和淋巴管。",
            organs=[
                _organ(
                    "spleen",
                    "脾脏",
                    "位于左上腹，参与免疫、血细胞过滤和血液储备。",
                    "外伤后左上腹痛、肩部牵涉痛、头晕或晕厥需要急症评估。",
                    ["spleen", "surface_of_spleen", "hilum_of_spleen"],
                    "abdomen",
                    ["female"],
                ),
            ],
            available_models=["female"],
        ),
        AtlasSystem(
            id="reproductive",
            name="女性生殖系统",
            english_name="FEMALE REPRODUCTIVE SYSTEM",
            color="#f472b6",
            summary="展示子宫、宫颈、卵巢、输卵管和阴道等女性盆腔结构。",
            organs=[
                _organ("uterus", "子宫", "位于盆腔中央，孕育胚胎并参与月经周期。", "异常阴道出血、妊娠相关腹痛或大量出血需要及时评估。", ["uterus", "uterine", "endometrium", "myometrium"], "abdomen", ["female"]),
                _organ("cervix", "宫颈", "位于子宫下端并连接阴道。", "接触性出血、异常分泌物或筛查异常需要妇科评估。", ["cervix", "cervical canal"], "perineal", ["female"]),
                _organ("ovaries", "卵巢", "位于子宫两侧，产生卵细胞并分泌激素。", "突发单侧下腹剧痛、晕厥或妊娠可能时需尽快评估。", ["left_ovary", "right_ovary", "ovarian"], "abdomen", ["female"]),
                _organ("uterine-tubes", "输卵管", "连接卵巢附近与子宫腔，是受精过程相关结构。", "停经后腹痛、出血或晕厥需要排除异位妊娠等急症。", ["uterine tube", "fallopian", "oviduct"], "abdomen", ["female"]),
                _organ("vagina", "阴道", "连接宫颈与外阴，是女性生殖道的一部分。", "大量出血、剧痛、恶臭分泌物或伴发热需要及时评估。", ["vagina", "vaginal"], "perineal", ["female"]),
            ],
            available_models=["female"],
        ),
    ]
    return BodyAtlasResponse(
        title="人体系统交互图谱",
        description=(
            "先在三维人体上指出哪里不舒服，再选择疼痛、肿胀、麻木等具体表现；"
            "支持多部位一起带入智能问诊。"
        ),
        systems=systems,
        body_regions=body_regions,
        models=[
            AtlasModelProfile(
                id="male",
                name="男性全身参考",
                english_name="MALE WHOLE BODY",
                description="用于全身体表、神经、呼吸、循环、消化、泌尿和骨骼结构定位。",
                coverage="头部至足部的全身参考模型",
                structure_count=256,
                available_system_ids=[
                    "regional", "nervous", "respiratory", "circulatory",
                    "digestive", "urinary", "musculoskeletal",
                ],
            ),
            AtlasModelProfile(
                id="female",
                name="女性腹盆躯干参考",
                english_name="FEMALE TRUNK",
                description="突出乳房、盆腔和女性生殖结构；当前数据覆盖躯干，不代表完整女性全身。",
                coverage="胸、腹、盆腔躯干参考模型",
                structure_count=264,
                available_system_ids=[
                    "circulatory", "digestive", "integumentary", "lymphatic",
                    "urinary", "reproductive", "musculoskeletal",
                ],
            ),
        ],
        default_model="male",
        disclaimer="该图谱用于健康科普与检索导航，不展示个体检测结果，不构成诊断。",
    )
