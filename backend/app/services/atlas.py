"""健康可视化页面使用的人体系统科普数据。"""

from __future__ import annotations

from app.models import (
    AtlasBodyRegion,
    AtlasDepartment,
    AtlasModelProfile,
    AtlasOrgan,
    AtlasSymptomOption,
    AtlasSystem,
    BodyAtlasResponse,
)


_SYMPTOMS = {
    "generic": [ # 通用症状
        ("pain", "疼痛", "这个部位疼痛"),
        ("swelling", "肿胀", "这个部位肿胀"),
        ("numbness", "麻木或刺痛", "这个部位麻木或刺痛"),
        ("rash", "发红、皮疹或瘙痒", "这个部位发红、起疹或瘙痒"),
        ("injury", "碰伤或外伤", "这个部位有碰伤或外伤"),
    ],
    "head": [ # 头部症状
        ("pain", "疼痛", "头面部局部疼痛"),
        ("pressure", "发紧或胀痛", "头面部局部发紧或胀痛"),
        ("numbness", "麻木或感觉异常", "头面部局部麻木或感觉异常"),
        ("swelling", "肿胀或包块", "头面部局部肿胀或摸到包块"),
        ("injury", "碰伤", "头面部局部受到碰撞"),
    ],
    "eye": [ # 眼部症状
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
    "dental": [ # 牙牙症状
        ("spontaneous-pain", "自发痛或跳痛", "牙齿在没有刺激时也疼痛或一跳一跳地痛"),
        ("bite-pain", "咬东西时痛", "牙齿咬合或咀嚼时疼痛"),
        ("sensitivity", "冷热酸甜敏感", "牙齿接触冷、热、酸或甜食时敏感疼痛"),
        ("gum", "牙龈肿痛或出血", "牙龈肿痛、刷牙出血或局部流脓"),
        ("loose", "牙齿松动或缺损", "牙齿松动、断裂或出现明显缺损"),
        ("face-swelling", "脸肿或张口受限", "牙痛同时出现面部肿胀或张口受限"),
    ],
    "neurologic": [
        ("pain", "头痛或神经痛", "出现头痛或沿神经分布的疼痛"),
        ("numbness", "麻木或感觉异常", "出现麻木、刺痛或感觉减退"),
        ("weakness", "无力或动作不灵", "出现肢体无力或精细动作异常"),
        ("dizziness", "眩晕或走路不稳", "出现眩晕、平衡异常或走路不稳"),
        ("consciousness", "意识、抽搐或言语异常", "出现意识改变、抽搐或言语异常"),
    ],
    "cardiac": [
        ("chest-pain", "胸痛或压迫感", "胸部疼痛或有压迫感"),
        ("palpitation", "心慌或心跳异常", "感到心慌、心跳过快过慢或不规则"),
        ("breathing", "活动后气短", "活动后出现气短或耐力下降"),
        ("syncope", "头晕或晕厥", "出现明显头晕、眼前发黑或晕厥"),
        ("edema", "下肢水肿", "脚踝或下肢出现水肿"),
    ],
    "respiratory": [
        ("cough", "咳嗽", "出现持续或反复咳嗽"),
        ("sputum", "咳痰", "咳嗽时伴有痰液"),
        ("breathing", "气促或喘鸣", "出现呼吸困难、气促或喘鸣"),
        ("hemoptysis", "痰中带血或咯血", "痰中带血或咳出血液"),
        ("chest-pain", "呼吸相关胸痛", "深呼吸或咳嗽时胸痛"),
    ],
    "vascular": [
        ("swelling", "单侧肢体肿胀", "一侧手臂或腿明显肿胀"),
        ("pain", "行走痛或静息痛", "行走后肢体疼痛或休息时也疼痛"),
        ("color", "苍白、发紫或发红", "肢体皮肤颜色出现明显改变"),
        ("temperature", "发凉或温度异常", "一侧肢体明显发凉或温度异常"),
        ("vein", "静脉曲张或皮肤溃疡", "出现静脉曲张或久不愈合的下肢创面"),
    ],
    "urinary": [
        ("pain", "腰痛或排尿痛", "出现腰部疼痛或排尿时疼痛"),
        ("frequency", "尿频、尿急或夜尿", "排尿次数增多、尿急或夜尿增多"),
        ("blood", "血尿", "尿液呈红色或检查提示血尿"),
        ("retention", "排尿困难或尿不出", "排尿费力、尿线变细或完全尿不出"),
        ("edema", "水肿或尿量异常", "出现水肿、尿量明显减少或增多"),
        ("fever", "发热伴腰痛", "发热同时出现腰痛或尿路症状"),
    ],
    "anorectal": [
        ("bleeding", "便血或纸上带血", "排便时出血或纸上带血"),
        ("pain", "肛门疼痛", "排便时或平时出现肛门疼痛"),
        ("lump", "肛门包块或脱出", "肛门周围摸到包块或排便时有组织脱出"),
        ("itch", "肛周瘙痒或潮湿", "肛门周围瘙痒、潮湿或反复刺激"),
        ("discharge", "流脓或异常分泌物", "肛周出现流脓或异常分泌物"),
        ("bowel-change", "排便习惯改变", "排便次数、形状或习惯持续改变"),
    ],
    "breast": [
        ("lump", "摸到包块", "乳房或腋下摸到新发包块"),
        ("pain", "乳房疼痛", "乳房出现局部或周期性疼痛"),
        ("discharge", "乳头溢液", "乳头出现自发性液体或血性溢液"),
        ("skin", "皮肤或乳头改变", "乳房皮肤凹陷、橘皮样改变或乳头回缩"),
        ("redness", "红肿发热", "乳房局部红肿、发热或明显压痛"),
    ],
    "gynecologic": [
        ("pain", "下腹或盆腔痛", "出现下腹部或盆腔疼痛"),
        ("bleeding", "异常阴道出血", "非月经期、性交后或绝经后阴道出血"),
        ("discharge", "分泌物异常", "阴道分泌物颜色、气味或量出现异常"),
        ("period", "月经异常", "月经周期、经量或经期明显异常"),
        ("pregnancy", "妊娠相关不适", "妊娠期出现腹痛、出血或其他异常"),
    ],
    "neck": [
        ("pain", "颈部疼痛", "颈部疼痛"),
        ("stiff", "僵硬或转头困难", "颈部僵硬或活动受限"),
        ("lump", "摸到肿块", "颈部摸到肿块"),
        ("swallow", "吞咽不适", "颈部伴吞咽不适"),
        ("injury", "扭伤或外伤", "颈部扭伤或受到外伤"),
    ],
    "chest": [ # 胸部症状
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


_CATEGORY_DEPARTMENTS = {
    "generic": ["general-practice"],
    "head": ["neurology"],
    "eye": ["ophthalmology"],
    "ear": ["ent"],
    "mouth": ["stomatology", "ent"],
    "dental": ["stomatology"],
    "neurologic": ["neurology"],
    "cardiac": ["cardiology"],
    "respiratory": ["respiratory"],
    "vascular": ["vascular-surgery", "cardiology"],
    "urinary": ["urology", "nephrology"],
    "anorectal": ["colorectal-surgery", "general-surgery", "tcm-anorectal"],
    "breast": ["breast-surgery", "gynecology"],
    "gynecologic": ["gynecology"],
    "neck": ["ent", "general-surgery"],
    "chest": ["cardiology", "respiratory"],
    "abdomen": ["gastroenterology", "general-surgery"],
    "back": ["orthopedics", "urology"],
    "perineal": ["urology", "gynecology", "general-surgery"],
    "limb": ["orthopedics"],
    "joint": ["orthopedics", "rheumatology"],
}


_SYMPTOM_DEPARTMENTS = {
    ("generic", "rash"): ["dermatology"],
    ("generic", "injury"): ["orthopedics", "general-surgery"],
    ("head", "numbness"): ["neurology"],
    ("head", "injury"): ["neurosurgery", "emergency"],
    ("eye", "vision"): ["ophthalmology", "emergency"],
    ("eye", "redness"): ["ophthalmology"],
    ("ear", "hearing"): ["ent"],
    ("ear", "discharge"): ["ent"],
    ("mouth", "ulcer"): ["oral-mucosa", "stomatology"],
    ("mouth", "movement"): ["oral-maxillofacial-surgery", "stomatology"],
    ("neck", "lump"): ["thyroid-surgery", "ent", "general-surgery"],
    ("chest", "palpitation"): ["cardiology"],
    ("chest", "breathing"): ["respiratory", "cardiology"],
    ("chest", "swelling"): ["breast-surgery", "general-surgery"],
    ("abdomen", "diarrhea"): ["gastroenterology"],
    ("abdomen", "constipation"): ["gastroenterology", "colorectal-surgery"],
    ("abdomen", "lump"): ["general-surgery", "gastroenterology"],
    ("back", "numbness"): ["orthopedics", "neurology"],
    ("back", "injury"): ["orthopedics", "emergency"],
    ("perineal", "bleeding"): ["colorectal-surgery", "gynecology", "urology"],
    ("perineal", "itch"): ["dermatology", "colorectal-surgery", "gynecology"],
    ("perineal", "discharge"): ["gynecology", "urology"],
    ("limb", "numbness"): ["neurology", "orthopedics"],
    ("limb", "weakness"): ["neurology", "orthopedics"],
    ("limb", "injury"): ["orthopedics", "emergency"],
    ("joint", "redness"): ["rheumatology", "orthopedics"],
    ("joint", "injury"): ["orthopedics", "sports-medicine"],
    ("dental", "spontaneous-pain"): ["dental-endodontics", "stomatology"],
    ("dental", "bite-pain"): ["dental-endodontics", "stomatology"],
    ("dental", "sensitivity"): ["dental-endodontics", "stomatology"],
    ("dental", "gum"): ["periodontics", "stomatology"],
    ("dental", "loose"): ["periodontics", "prosthodontics"],
    ("dental", "face-swelling"): ["oral-maxillofacial-surgery", "emergency"],
    ("neurologic", "weakness"): ["neurology", "emergency"],
    ("neurologic", "consciousness"): ["neurology", "emergency"],
    ("cardiac", "chest-pain"): ["cardiology", "emergency"],
    ("cardiac", "syncope"): ["cardiology", "emergency"],
    ("respiratory", "breathing"): ["respiratory", "emergency"],
    ("respiratory", "hemoptysis"): ["respiratory", "emergency"],
    ("vascular", "swelling"): ["vascular-surgery", "emergency"],
    ("vascular", "color"): ["vascular-surgery", "emergency"],
    ("vascular", "temperature"): ["vascular-surgery", "emergency"],
    ("urinary", "blood"): ["urology", "nephrology"],
    ("urinary", "retention"): ["urology", "emergency"],
    ("urinary", "edema"): ["nephrology"],
    ("urinary", "fever"): ["urology", "nephrology", "emergency"],
    ("anorectal", "bleeding"): ["colorectal-surgery", "general-surgery"],
    ("anorectal", "pain"): ["colorectal-surgery", "general-surgery"],
    ("anorectal", "lump"): ["colorectal-surgery", "tcm-anorectal"],
    ("anorectal", "discharge"): ["colorectal-surgery", "general-surgery"],
    ("anorectal", "bowel-change"): ["gastroenterology", "colorectal-surgery"],
    ("breast", "lump"): ["breast-surgery"],
    ("breast", "discharge"): ["breast-surgery"],
    ("breast", "skin"): ["breast-surgery"],
    ("breast", "redness"): ["breast-surgery", "general-surgery"],
    ("gynecologic", "bleeding"): ["gynecology", "obstetrics", "emergency"],
    ("gynecologic", "pregnancy"): ["obstetrics", "emergency"],
}


_REGION_DEPARTMENT_OVERRIDES = {
    "left-eye": ["ophthalmology"],
    "right-eye": ["ophthalmology"],
    "left-ear": ["ent"],
    "right-ear": ["ent"],
    "left-nose": ["ent"],
    "right-nose": ["ent"],
    "left-mouth-jaw": ["stomatology", "oral-maxillofacial-surgery", "ent"],
    "right-mouth-jaw": ["stomatology", "oral-maxillofacial-surgery", "ent"],
    "front-neck": ["ent", "thyroid-surgery", "general-surgery"],
    "pubic-region": ["urology", "gynecology", "dermatology"],
    "perianal-region": ["colorectal-surgery", "general-surgery", "tcm-anorectal"],
    "left-groin": ["general-surgery", "urology", "gynecology"],
    "right-groin": ["general-surgery", "urology", "gynecology"],
    "left-chest": ["respiratory", "cardiology", "breast-surgery"],
    "right-chest": ["respiratory", "breast-surgery"],
    "center-chest": ["cardiology", "respiratory", "thoracic-surgery"],
    "left-lower-back": ["orthopedics", "nephrology", "urology"],
    "right-lower-back": ["orthopedics", "nephrology", "urology"],
}


def _symptom_options(category: str) -> list[AtlasSymptomOption]:
    """把部位类别转换为可多选的通俗症状选项。

    Args:
        category: 头面部、胸部、腹部或肢体等症状模板类别。

    Returns:
        适合普通用户理解和勾选的症状选项。
    """

    return [
        AtlasSymptomOption(
            id=item[0],
            label=item[1],
            query_text=item[2],
            department_ids=_SYMPTOM_DEPARTMENTS.get((category, item[0]), []),
        )
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
    department_ids: list[str] | None = None,
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
        department_ids: 与该结构常见问题对应的初诊科室标识。

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
        department_ids=department_ids or _CATEGORY_DEPARTMENTS.get(
            category,
            ["general-practice"],
        ),
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
        department_ids=_REGION_DEPARTMENT_OVERRIDES.get(
            region_id,
            _CATEGORY_DEPARTMENTS.get(category, ["general-practice"]),
        ),
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
            _region("perianal-region", "肛门与肛周", "Anal region", "腹部与骨盆", "middle", "臀沟下方、肛门及其周围", "包含肛门、肛周皮肤和会阴后部软组织。", ["Anal region.l", "Anal region.r"], "anorectal"),
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


def _department(
    department_id: str,
    official_code: str,
    name: str,
    english_name: str,
    group: str,
    summary: str,
    common_reasons: list[str],
    target_system_id: str,
    target_organ_id: str | None = None,
    focus_aliases: list[str] | None = None,
    preferred_model: str | None = None,
) -> AtlasDepartment:
    """创建供普通用户定位身体结构的初诊科室导航项。

    Args:
        department_id: 前后端稳定使用的科室标识。
        official_code: 国家诊疗科目名录中的科目编码。
        name: 面向用户展示的科室名称。
        english_name: 科室英文名称。
        group: 门诊导航分组。
        summary: 科室常见诊疗范围的通俗说明。
        common_reasons: 常见就诊原因示例。
        target_system_id: 选择后需要激活的三维解剖图层。
        target_organ_id: 选择后默认打开的器官或结构标识。
        focus_aliases: 用于聚焦一个或多个三维网格的英文别名。
        preferred_model: 更适合展示该科室结构的模型标识。

    Returns:
        包含初诊说明和三维定位信息的科室导航数据。
    """

    return AtlasDepartment(
        id=department_id,
        official_code=official_code,
        name=name,
        english_name=english_name,
        group=group,
        summary=summary,
        common_reasons=common_reasons,
        target_system_id=target_system_id,
        target_organ_id=target_organ_id,
        focus_aliases=focus_aliases or [],
        preferred_model=preferred_model,
    )


def _build_departments() -> list[AtlasDepartment]:
    """构建覆盖常见医院门急诊专业的初诊科室目录。

    Returns:
        可用于科室筛选、解剖图层联动和初诊提示的科室列表。
    """

    return [
        _department("emergency", "20", "急诊医学科", "EMERGENCY MEDICINE", "急诊与综合", "处理可能危及生命或需要立即评估的急性问题。", ["胸痛伴大汗或呼吸困难", "意识改变或抽搐", "严重外伤或大量出血"], "regional"),
        _department("general-practice", "02", "全科医疗科", "GENERAL PRACTICE", "急诊与综合", "症状不明确、涉及多个系统或不知道挂什么科时的综合初诊入口。", ["乏力、发热等非特异症状", "多部位同时不适", "慢病综合评估"], "regional"),
        _department("respiratory", "03.01", "呼吸内科", "RESPIRATORY MEDICINE", "内科", "评估气道、肺与胸膜相关的内科问题。", ["咳嗽咳痰", "气促或喘鸣", "咯血或胸膜性胸痛"], "respiratory", "lungs", ["lung", "lobe of", "pleura"]),
        _department("gastroenterology", "03.02", "消化内科", "GASTROENTEROLOGY", "内科", "评估食管、胃肠、肝胆胰等消化系统内科问题。", ["腹痛腹胀", "反酸或吞咽不适", "恶心、腹泻或便血"], "digestive", "stomach", ["stomach", "duodenum"]),
        _department("neurology", "03.03", "神经内科", "NEUROLOGY", "内科", "评估脑、脊髓及周围神经相关的非手术问题。", ["头痛眩晕", "麻木或无力", "记忆、意识或运动异常"], "nervous", "brain", ["brain", "cerebr", "cortex"]),
        _department("cardiology", "03.04", "心血管内科", "CARDIOLOGY", "内科", "评估心脏节律、冠脉、心功能和血压相关问题。", ["心慌心悸", "胸闷胸痛", "活动后气短或晕厥"], "circulatory", "heart", ["heart", "ventricle", "atrium"]),
        _department("hematology", "03.05", "血液内科", "HEMATOLOGY", "内科", "评估血细胞、凝血及造血系统相关问题。", ["不明原因贫血或乏力", "反复出血或瘀斑", "血常规持续异常"], "circulatory", "vessels", ["aorta", "artery", "vein"]),
        _department("nephrology", "03.06", "肾内科", "NEPHROLOGY", "内科", "评估肾功能、蛋白尿、血尿及水盐代谢问题。", ["泡沫尿或血尿", "眼睑或下肢水肿", "肾功能检查异常"], "urinary", "kidney", ["kidney", "renal pelvis"]),
        _department("endocrinology", "03.07", "内分泌科", "ENDOCRINOLOGY", "内科", "评估糖代谢、甲状腺、肾上腺及其他激素相关问题。", ["血糖异常", "甲状腺肿大或指标异常", "体重与代谢异常"], "regional", None, ["front neck", "Anterior neck", "Submandibular"]),
        _department("rheumatology", "03.08", "风湿免疫科", "RHEUMATOLOGY", "内科", "评估炎症性关节、结缔组织及自身免疫相关问题。", ["多关节肿痛", "晨僵", "皮疹伴系统性不适"], "musculoskeletal", "spine-bones", ["joint", "vertebra"]),
        _department("allergy", "03.09", "变态反应科", "ALLERGY AND IMMUNOLOGY", "内科", "评估反复过敏、哮喘、过敏性鼻炎及可疑食物或药物过敏。", ["反复荨麻疹", "过敏性鼻炎或哮喘", "食物、药物过敏评估"], "regional"),
        _department("geriatrics", "03.10", "老年医学科", "GERIATRIC MEDICINE", "内科", "为老年人多病共存、衰弱、跌倒和多重用药提供综合评估。", ["老年人多种慢病", "反复跌倒或衰弱", "多种药物综合管理"], "regional"),
        _department("general-surgery", "04.01", "普通外科", "GENERAL SURGERY", "外科", "评估常见腹部、甲状腺、乳腺及体表肿物等可能需外科处理的问题。", ["持续或加重的局部腹痛", "体表包块", "甲状腺或乳房异常"], "digestive", "large-intestine", ["colon", "appendix"]),
        _department("thyroid-surgery", "04.01", "甲状腺外科", "THYROID SURGERY", "普外亚专科", "医院常用亚专科名称，评估甲状腺结节、肿大及需要外科判断的问题。", ["甲状腺结节", "颈前包块", "甲状腺疾病手术评估"], "regional", None, ["Anterior neck", "Submandibular triangle"]),
        _department("breast-surgery", "04.01", "乳腺外科", "BREAST SURGERY", "普外亚专科", "医院常用亚专科名称，评估乳房包块、疼痛、溢液及影像异常。", ["乳房包块", "乳头溢液", "乳腺影像检查异常"], "integumentary", "breast-left", ["mammary", "nipple", "areola", "lactiferous"], "female"),
        _department("vascular-surgery", "04.01", "血管外科", "VASCULAR SURGERY", "普外亚专科", "医院常用亚专科名称，评估动静脉狭窄、血栓、曲张及血管相关创面。", ["下肢静脉曲张", "单侧肢体突然肿胀", "肢体发凉、苍白或间歇性跛行"], "circulatory", "vessels", ["artery", "vein", "aorta"]),
        _department("hepatobiliary-surgery", "04.01", "肝胆胰外科", "HEPATOBILIARY AND PANCREATIC SURGERY", "普外亚专科", "医院常用亚专科名称，评估肝、胆道、胆囊和胰腺中可能需外科处理的问题。", ["胆囊结石或胆囊炎", "肝胆胰占位", "梗阻性黄疸"], "digestive", "gallbladder", ["liver", "gallbladder", "bile duct", "pancreas"]),
        _department("gastrointestinal-surgery", "04.01", "胃肠外科", "GASTROINTESTINAL SURGERY", "普外亚专科", "医院常用亚专科名称，评估胃、小肠和结肠中可能需要手术处理的问题。", ["胃肠道肿物", "肠梗阻可能", "阑尾或胃肠外科评估"], "digestive", "large-intestine", ["stomach", "duodenum", "jejunum", "ileum", "colon", "appendix"]),
        _department("colorectal-surgery", "04.01", "结直肠肛门外科", "COLORECTAL SURGERY", "普外亚专科", "部分医院称肛肠外科或胃肠外科，评估痔、肛裂、肛瘘及结直肠外科问题。", ["痔疮或肛门包块", "便血或肛门疼痛", "肛裂、肛瘘或肛周脓肿"], "digestive", "anorectal", ["rectum", "anus", "anal sphincter"]),
        _department("neurosurgery", "04.02", "神经外科", "NEUROSURGERY", "外科", "评估颅脑、脊髓和周围神经中可能需要手术处理的问题。", ["头部外伤", "影像发现颅脑占位", "脊髓压迫相关表现"], "nervous", "brain", ["brain", "spinal cord"]),
        _department("orthopedics", "04.03", "骨科", "ORTHOPEDICS", "外科", "评估骨骼、关节、脊柱及运动损伤。", ["骨关节疼痛", "扭伤或骨折可能", "颈肩腰腿痛"], "musculoskeletal", "spine-bones", ["vertebra", "bone", "joint"]),
        _department("urology", "04.04", "泌尿外科", "UROLOGY", "外科", "评估泌尿系结石、梗阻、肿瘤和男性泌尿生殖相关问题。", ["排尿困难", "腰腹绞痛或结石", "肉眼血尿"], "urinary", "bladder", ["urinary bladder", "ureter", "urethra"]),
        _department("thoracic-surgery", "04.05", "胸外科", "THORACIC SURGERY", "外科", "评估肺、食管、纵隔和胸壁中可能需要手术处理的问题。", ["肺结节需外科评估", "食管或纵隔占位", "胸壁结构异常"], "respiratory", "lungs", ["lung", "pleura", "oesophagus"]),
        _department("cardiac-surgery", "04.06", "心脏大血管外科", "CARDIAC SURGERY", "外科", "评估心脏瓣膜、先天性心脏病和大血管等外科问题。", ["瓣膜病需手术评估", "主动脉疾病", "先天性心脏结构异常"], "circulatory", "heart", ["heart", "aorta", "valve"]),
        _department("burns", "04.07", "烧伤科", "BURN SURGERY", "外科", "评估热力、化学、电击等烧伤及相关创面。", ["热液或火焰烧伤", "化学烧伤", "电击伤"], "regional"),
        _department("plastic-surgery", "04.08", "整形外科", "PLASTIC SURGERY", "外科", "评估先天或后天组织缺损、瘢痕、修复重建及规范医疗美容问题。", ["瘢痕或组织缺损", "创面修复", "修复重建评估"], "regional"),
        _department("gynecology", "05.01", "妇科", "GYNECOLOGY", "妇产科", "评估女性生殖系统、月经、分泌物和盆腔相关问题。", ["异常阴道出血", "盆腔或下腹痛", "外阴或分泌物异常"], "reproductive", "uterus", ["uterus", "ovary", "vagina"], "female"),
        _department("obstetrics", "05.02", "产科", "OBSTETRICS", "妇产科", "为妊娠期产检、妊娠相关不适和分娩提供专科评估。", ["孕期产检", "孕期腹痛或出血", "胎动或分娩相关问题"], "reproductive", "uterus", ["uterus", "cervix"], "female"),
        _department("reproductive-medicine", "05.04", "生殖医学与不孕症专科", "REPRODUCTIVE MEDICINE", "妇产科", "评估不孕不育、生殖内分泌及辅助生殖相关问题。", ["备孕一年未孕", "复发性流产评估", "生殖内分泌或辅助生殖咨询"], "reproductive", "uterus", ["uterus", "ovary", "uterine tube"], "female"),
        _department("pediatrics", "07", "儿科", "PEDIATRICS", "妇儿与专科", "面向儿童和青少年的综合初诊；具体年龄边界以医院规定为准。", ["儿童发热咳嗽", "喂养或生长问题", "儿童腹痛或皮疹"], "regional"),
        _department("pediatric-surgery", "09", "小儿外科", "PEDIATRIC SURGERY", "妇儿与专科", "评估儿童先天畸形、外伤及可能需要外科处理的腹部或体表问题。", ["儿童腹股沟包块", "儿童急性腹痛需外科评估", "儿童外伤或先天结构异常"], "regional"),
        _department("ophthalmology", "10", "眼科", "OPHTHALMOLOGY", "五官与皮肤", "评估眼球、眼睑、视觉和眼外伤相关问题。", ["眼红眼痛", "视力下降或重影", "眼外伤或异物"], "regional", None, ["Orbital region", "Infra-orbital region", "Eyelashes"]),
        _department("ent", "11", "耳鼻咽喉科", "OTORHINOLARYNGOLOGY", "五官与皮肤", "评估耳、鼻、咽、喉及相关头颈问题。", ["耳痛耳鸣或听力下降", "鼻塞鼻出血", "咽痛、声音嘶哑或吞咽不适"], "regional", None, ["Auricular region", "Nasal region", "Submandibular triangle"]),
        _department("stomatology", "12", "口腔科", "STOMATOLOGY", "五官与皮肤", "评估牙体牙髓、牙周、口腔黏膜及颌面部相关问题。", ["牙痛或冷热敏感", "牙龈肿痛出血", "牙齿松动、缺损或颌面肿胀"], "digestive", "upper-anterior-teeth", ["tooth", "incisor", "canine", "molar", "premolar", "gingiva"], "male"),
        _department("dental-endodontics", "12.01", "牙体牙髓病专业", "ENDODONTICS", "口腔专科", "处理龋病、牙髓炎、根尖周病和牙体缺损等牙齿内部问题。", ["自发牙痛或夜间痛", "冷热刺激痛", "咬合痛或蛀牙"], "digestive", "upper-anterior-teeth", ["tooth", "incisor", "canine", "molar", "premolar"], "male"),
        _department("periodontics", "12.02", "牙周病专业", "PERIODONTICS", "口腔专科", "评估牙龈、牙周支持组织及牙齿松动相关问题。", ["刷牙出血", "牙龈肿痛或流脓", "牙齿松动"], "digestive", "gingiva", ["gingiva", "periodont"], "male"),
        _department("oral-mucosa", "12.03", "口腔黏膜病专业", "ORAL MEDICINE", "口腔专科", "评估口腔溃疡、白斑、红斑及其他口腔黏膜异常。", ["口腔溃疡久不愈", "黏膜白斑或红斑", "口腔灼痛"], "digestive", "tongue-mucosa", ["tongue", "oral mucosa", "palate"], "male"),
        _department("pediatric-dentistry", "12.04", "儿童口腔专业", "PEDIATRIC DENTISTRY", "口腔专科", "评估儿童乳牙、恒牙萌出、龋病及口腔发育问题。", ["儿童牙痛或蛀牙", "乳牙滞留", "牙齿萌出异常"], "digestive", "upper-anterior-teeth", ["tooth", "incisor", "canine", "molar", "premolar"], "male"),
        _department("oral-maxillofacial-surgery", "12.05", "口腔颌面外科专业", "ORAL AND MAXILLOFACIAL SURGERY", "口腔专科", "评估阻生牙、颌面部感染、外伤、肿物及唾液腺外科问题。", ["智齿肿痛", "面颌部肿胀或外伤", "腮腺或颌下腺肿痛"], "digestive", "lower-posterior-teeth", ["third molar", "tooth", "parotid", "submandibular"], "male"),
        _department("prosthodontics", "12.06", "口腔修复专业", "PROSTHODONTICS", "口腔专科", "处理牙齿缺损、缺失后的冠、桥、义齿等功能修复评估。", ["牙齿缺损", "牙齿缺失", "假牙不适"], "digestive", "upper-anterior-teeth", ["tooth", "incisor", "canine", "molar", "premolar"], "male"),
        _department("orthodontics", "12.07", "口腔正畸专业", "ORTHODONTICS", "口腔专科", "评估牙列不齐、咬合异常和颌面生长发育相关问题。", ["牙齿排列不齐", "地包天或龅牙", "咬合关系异常"], "digestive", "upper-anterior-teeth", ["tooth", "incisor", "canine", "molar", "premolar"], "male"),
        _department("implant-dentistry", "12.08", "口腔种植专业", "IMPLANT DENTISTRY", "口腔专科", "评估牙齿缺失后的种植修复条件及种植体相关问题。", ["缺牙后考虑种植", "种植体周围不适", "种植修复复查"], "digestive", "upper-posterior-teeth", ["tooth", "molar", "premolar", "gingiva"], "male"),
        _department("dermatology", "13", "皮肤科", "DERMATOLOGY", "五官与皮肤", "评估皮肤、毛发、甲及常见皮肤附属器问题。", ["皮疹或瘙痒", "水疱、脱屑或色素变化", "毛发或指甲异常"], "regional"),
        _department("psychiatry", "15", "精神科／心理门诊", "PSYCHIATRY", "其他专科", "评估持续情绪、睡眠、思维、行为和成瘾相关问题；危及自身或他人时应立即求助。", ["持续抑郁或焦虑", "明显失眠伴功能受损", "幻觉、妄想或自伤想法"], "regional"),
        _department("infectious", "16", "感染性疾病科", "INFECTIOUS DISEASES", "其他专科", "评估明确或疑似感染性疾病及相关发热问题。", ["持续发热伴感染暴露", "传染病筛查异常", "复杂或反复感染"], "regional"),
        _department("oncology", "19", "肿瘤科", "ONCOLOGY", "其他专科", "对已发现或高度疑似肿瘤进行专科评估和综合治疗管理。", ["病理或影像提示肿瘤", "肿瘤治疗随访", "不明原因进行性消瘦伴占位"], "regional"),
        _department("rehabilitation", "21", "康复医学科", "REHABILITATION MEDICINE", "其他专科", "评估疾病或损伤后的功能障碍并制定康复方案。", ["术后功能恢复", "卒中后运动障碍", "慢性肌骨功能受限"], "musculoskeletal", "spine-bones", ["spine", "joint", "muscle"]),
        _department("pain", "27", "疼痛科", "PAIN MEDICINE", "其他专科", "评估持续性或复杂疼痛，尤其是常规处理效果不佳的疼痛。", ["慢性颈肩腰腿痛", "神经病理性疼痛", "原因复杂的持续疼痛"], "musculoskeletal", "spine-bones", ["spine", "nerve", "joint"]),
        _department("sports-medicine", "26", "运动医学科", "SPORTS MEDICINE", "其他专科", "评估运动相关肌肉、肌腱、韧带和关节损伤及功能恢复。", ["运动后关节疼痛", "肌腱或韧带损伤", "运动能力恢复评估"], "musculoskeletal", "upper-limb-bones", ["joint", "ligament", "tendon", "muscle"]),
        _department("tcm-anorectal", "50.11", "中医肛肠科", "TCM PROCTOLOGY", "中医专科", "国家诊疗科目中的中医肛肠专业，评估痔、肛裂、肛瘘等肛肠问题。", ["痔疮或便血", "肛门疼痛", "肛裂、肛瘘或肛周不适"], "digestive", "anorectal", ["rectum", "anus", "anal sphincter"]),
    ]


def _validate_atlas_routes(
    systems: list[AtlasSystem],
    body_regions: list[AtlasBodyRegion],
    departments: list[AtlasDepartment],
) -> None:
    """校验科室、系统、器官和症状之间的引用完整性。

    Args:
        systems: 当前人体图谱包含的解剖系统。
        body_regions: 可点击的体表精细区域。
        departments: 患者初诊科室目录。

    Raises:
        ValueError: 存在重复标识或引用了不存在的科室、系统、器官时抛出。
    """

    department_ids = [department.id for department in departments]
    if len(department_ids) != len(set(department_ids)):
        raise ValueError("初诊科室目录存在重复标识")
    known_department_ids = set(department_ids)
    systems_by_id = {system.id: system for system in systems}
    referenced_department_ids = {
        department_id
        for item in [*body_regions, *(organ for system in systems for organ in system.organs)]
        for department_id in item.department_ids
    }
    referenced_department_ids.update(
        department_id
        for system in systems
        for organ in system.organs
        for symptom in organ.symptom_options
        for department_id in symptom.department_ids
    )
    referenced_department_ids.update(
        department_id
        for region in body_regions
        for symptom in region.symptom_options
        for department_id in symptom.department_ids
    )
    unknown_department_ids = referenced_department_ids - known_department_ids
    if unknown_department_ids:
        raise ValueError(
            f"人体图谱引用了不存在的科室：{sorted(unknown_department_ids)}"
        )
    for department in departments:
        system = systems_by_id.get(department.target_system_id)
        if system is None:
            raise ValueError(f"科室 {department.id} 引用了不存在的系统")
        if department.target_organ_id and not any(
            organ.id == department.target_organ_id for organ in system.organs
        ):
            raise ValueError(f"科室 {department.id} 引用了不存在的器官")


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
                _organ("brain", "大脑", "位于颅腔内，整合感觉、认知与运动控制。", "持续意识改变、突发言语或肢体异常需要及时评估。", ["brain", "cerebr", "cortex", "gyrus", "sulcus", "cerebell", "thalam", "amygdaloid", "caudate nucleus", "corpus callosum"], "neurologic"),
                _organ("spinal", "脊髓与周围神经", "脊髓连接大脑与全身周围神经。", "新发肢体无力或大小便功能异常属于重要信号。", ["spinal cord", "spinal nerve", "cauda equina", "nerve", "plexus", "tract", "fasciculus"], "neurologic"),
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
                _organ("heart", "心脏", "位于胸腔中央偏左，通过节律性收缩推动血液循环。", "胸痛伴呼吸困难、大汗或晕厥需要急症评估。", ["heart", "ventricle", "atrium", "coronary", "papillary muscle", "valve"], "cardiac"),
                _organ("vessels", "血管", "动脉和静脉连接心脏与全身组织。", "肢体突然苍白、发凉、明显肿胀或神经功能异常需要及时评估。", ["artery", "aorta", "vein", "venous", "sinus", "vascular", "trunk"], "vascular", None, ["vascular-surgery", "cardiology"]),
            ],
        ),
        AtlasSystem(
            id="respiratory",
            name="呼吸系统",
            english_name="RESPIRATORY SYSTEM",
            color="#5eead4",
            summary="完成空气传导和肺泡气体交换，维持氧合与酸碱平衡。",
            organs=[
                _organ("lungs", "肺和胸膜", "位于左右胸腔，完成氧气与二氧化碳交换。", "明显气促、口唇发紫或咯血应尽快线下评估。", ["lobe of", "lung", "pleura"], "respiratory"),
                _organ("airway", "气管和支气管", "从咽喉向左右肺输送空气。", "喘鸣和气道阻塞表现需结合发作速度与诱因判断。", ["trachea", "bronchus", "bronchi"], "respiratory"),
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
                _organ("upper-anterior-teeth", "上前牙", "包括上颌中切牙、侧切牙和尖牙，负责切断食物并影响发音与外观。", "自发跳痛、夜间痛或面部肿胀可能提示需要尽快口腔科评估。", ["Upper medial incisor", "Upper lateral incisor", "Upper canine"], "dental", ["male"], ["stomatology", "dental-endodontics"]),
                _organ("upper-posterior-teeth", "上后牙", "包括上颌前磨牙和磨牙，主要承担研磨和咀嚼。", "咬合痛、冷热刺激后持续疼痛或牙龈局部肿包需要口腔科评估。", ["Upper first premolar", "Upper second premolar", "Upper first molar tooth", "Upper second molar tooth", "Upper third molar tooth"], "dental", ["male"], ["stomatology", "dental-endodontics"]),
                _organ("lower-anterior-teeth", "下前牙", "包括下颌中切牙、侧切牙和尖牙，参与切咬和发音。", "牙齿松动、牙龈退缩或持续咬合痛需要口腔科检查。", ["Lower medial incisor", "Lower lateral incisor", "Lower canine"], "dental", ["male"], ["stomatology", "dental-endodontics"]),
                _organ("lower-posterior-teeth", "下后牙", "包括下颌前磨牙和磨牙，是主要咀嚼牙区。", "后牙区肿痛伴张口受限、吞咽困难或发热应尽快线下就诊。", ["Lower first premolar", "Lower second premolar", "Lower first molar tooth", "Lower second molar tooth", "Lower third molar tooth"], "dental", ["male"], ["stomatology", "dental-endodontics", "oral-maxillofacial-surgery"]),
                _organ("gingiva", "牙龈与牙周", "牙龈和牙周支持组织包绕并固定牙齿。", "反复刷牙出血、牙龈肿痛、流脓或牙齿松动需要牙周评估。", ["Gingiva", "periodont"], "dental", ["male"], ["stomatology", "periodontics"]),
                _organ("tongue-mucosa", "舌与口腔黏膜", "舌参与味觉、咀嚼、吞咽和发音，黏膜覆盖口腔内表面。", "溃疡超过两周不愈、舌体迅速肿胀或影响呼吸吞咽需要及时评估。", ["tongue", "oral mucosa", "palate", "uvula"], "mouth", ["male"], ["stomatology", "oral-mucosa", "ent"]),
                _organ("salivary-glands", "唾液腺", "腮腺、颌下腺和舌下腺分泌唾液并帮助消化和保护口腔。", "进食时反复腮颌部肿痛、发热或流脓需要口腔颌面外科或耳鼻咽喉科评估。", ["salivary", "parotid", "sublingual", "submandibular"], "mouth", ["male"], ["stomatology", "oral-maxillofacial-surgery", "ent"]),
                _organ("pharynx", "咽部", "咽部连接口鼻腔与食管、喉，是吞咽和气道的共同通道。", "吞咽困难、明显流涎、声音改变或呼吸受影响需要及时评估。", ["pharynx", "epiglottis"], "mouth", ["male"], ["ent"]),
                _organ("esophagus", "食管", "连接咽部与胃，将食物送入胃内。", "进行性吞咽困难、吞咽疼痛或呕血需要及时评估。", ["oesophagus", "esophagus", "epiglottis"], "chest"),
                _organ("stomach", "胃", "位于上腹部，储存并初步消化食物。", "疼痛与空腹或进食的关系是消化道问诊的重要线索。", ["stomach"], "abdomen", None, ["gastroenterology", "gastrointestinal-surgery"]),
                _organ("liver", "肝脏", "主要位于右上腹，参与代谢、合成与解毒。", "黄疸、深色尿或明显右上腹不适需要结合检查评估。", ["liver"], "abdomen", None, ["gastroenterology", "hepatobiliary-surgery"]),
                _organ("gallbladder", "胆囊和胆管", "位于肝脏下方，储存胆汁并输送至肠道。", "右上腹剧痛伴发热、黄疸或持续呕吐需要及时评估。", ["gallbladder", "bile duct"], "abdomen", None, ["gastroenterology", "hepatobiliary-surgery"]),
                _organ("pancreas", "胰腺", "位于上腹深部，参与消化和血糖调节。", "持续剧烈上腹痛并向背部放射需要及时评估。", ["pancreas", "pancreatic"], "abdomen", None, ["gastroenterology", "hepatobiliary-surgery"]),
                _organ("small-intestine", "小肠", "包括十二指肠和空肠等，主要负责营养吸收。", "持续呕吐、明显腹胀或严重腹痛需要及时评估。", ["duodenum", "jejunum", "ileum"], "abdomen", None, ["gastroenterology", "gastrointestinal-surgery"]),
                _organ("large-intestine", "大肠和阑尾", "吸收水分并形成粪便，包括结肠和阑尾。", "便血、停止排气排便或进行性右下腹痛需要及时评估。", ["colon", "taenia", "appendix"], "abdomen", None, ["gastroenterology", "gastrointestinal-surgery", "colorectal-surgery"]),
                _organ("anorectal", "直肠、肛管与肛门", "消化道末端，包含直肠、肛管、肛门及肛门括约肌。", "痔并不是便血的唯一原因；大量便血、黑便、晕厥或肛周剧痛伴发热需要立即评估。", ["anal sphincter", "rectum", "anus"], "anorectal", None, ["colorectal-surgery", "general-surgery", "tcm-anorectal"]),
            ],
        ),
        AtlasSystem(
            id="urinary",
            name="泌尿系统",
            english_name="URINARY SYSTEM",
            color="#a78bfa",
            summary="调节体液、电解质与代谢废物排出。",
            organs=[
                _organ("kidney", "肾脏和肾盂", "位于左右腰背深部，过滤血液并调节水盐平衡。", "尿量骤减、肉眼血尿或腰痛伴发热需要及时评估。", ["kidney", "renal pelvis"], "urinary", None, ["nephrology", "urology"]),
                _organ("ureter", "输尿管", "连接肾脏与膀胱，输送尿液。", "腰腹绞痛、肉眼血尿或伴发热需要及时评估。", ["ureter"], "urinary"),
                _organ("bladder", "膀胱", "位于下腹和骨盆内，储存尿液。", "尿频尿急等表现需结合疼痛、发热和持续时间。", ["urinary bladder"], "urinary"),
                _organ("urethra", "尿道", "将膀胱内尿液排出体外。", "完全无法排尿、明显血尿或剧烈疼痛需要及时评估。", ["urethra"], "urinary"),
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
                    "breast",
                    ["female"],
                    ["breast-surgery", "gynecology"],
                ),
                _organ(
                    "breast-right",
                    "右侧乳房",
                    "位于右侧前胸壁，包含乳腺、乳头乳晕及周围软组织。",
                    "新发包块、皮肤凹陷、血性溢液或明显红肿发热需要线下评估。",
                    ["fat_R", "mammary_lobes_R", "nipple_R", "areola_R", "lactiferous_ducts_R", "lactiferous_sinuses_R", "suspensory_ligaments_R"],
                    "breast",
                    ["female"],
                    ["breast-surgery", "gynecology"],
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
                _organ("uterus", "子宫", "位于盆腔中央，孕育胚胎并参与月经周期。", "异常阴道出血、妊娠相关腹痛或大量出血需要及时评估。", ["uterus", "uterine", "endometrium", "myometrium"], "gynecologic", ["female"], ["gynecology", "obstetrics", "reproductive-medicine"]),
                _organ("cervix", "宫颈", "位于子宫下端并连接阴道。", "接触性出血、异常分泌物或筛查异常需要妇科评估。", ["cervix", "cervical canal"], "gynecologic", ["female"]),
                _organ("ovaries", "卵巢", "位于子宫两侧，产生卵细胞并分泌激素。", "突发单侧下腹剧痛、晕厥或妊娠可能时需尽快评估。", ["left_ovary", "right_ovary", "ovarian"], "gynecologic", ["female"]),
                _organ("uterine-tubes", "输卵管", "连接卵巢附近与子宫腔，是受精过程相关结构。", "停经后腹痛、出血或晕厥需要排除异位妊娠等急症。", ["uterine tube", "fallopian", "oviduct"], "gynecologic", ["female"]),
                _organ("vagina", "阴道", "连接宫颈与外阴，是女性生殖道的一部分。", "大量出血、剧痛、恶臭分泌物或伴发热需要及时评估。", ["vagina", "vaginal"], "gynecologic", ["female"]),
            ],
            available_models=["female"],
        ),
    ]
    departments = _build_departments()
    _validate_atlas_routes(systems, body_regions, departments)
    return BodyAtlasResponse(
        title="人体系统交互图谱",
        description=(
            "先在三维人体上指出哪里不舒服，再选择疼痛、肿胀、麻木等具体表现；"
            "支持多部位一起带入智能问诊。"
        ),
        systems=systems,
        departments=departments,
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
