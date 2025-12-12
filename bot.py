import json, os, random, re
from datetime import datetime, timezone, timedelta
import requests
from requests_oauthlib import OAuth1

JST = timezone(timedelta(hours=9))

SYSTEM_STYLE = {"min_len": 70, "max_len": 140}

TEMPLATES = [
    "「{myth}」って思ってたけど、家で飲むなら一番効くのは{truth}だった。これを{action}だけで、毎朝の一杯がちゃんと美味しくなる。",
    "家コーヒーが急に美味しくなるポイント\n\n・{p1}\n・{p2}\n・{p3}\n\n全部やらなくていい。まずは{first}だけで変わる。",
    "昔の自分、コーヒーを「{bad}」だと思ってた。でも{stop}をやめて{do}にしたら、ちゃんと美味しい飲み物になった。",
    "コーヒーが美味しくならない原因、だいたい{cause}。"
]

TOPICS_MORNING = [
    # 家で美味しくなる（②）
    "お湯を少し待つだけで変わった話",
    "粉をほんの少し増やした時の変化",
    "注ぐスピードを変えただけの話",
    "最初の一口を急がない理由",
    "淹れたらすぐ飲むだけで違った話",
    "カップを温めたら印象が変わった",
    "忙しい日は完璧を目指さない方がいい話",
    "失敗したと思った時の立て直し方",
]

TOPICS_NOON = [
    # 選び方・考え方（④）
    "正解より自分の好みでいい話",
    "家で飲むなら十分な基準",
    "続けやすいコーヒーの考え方",
    "毎日飲むならこれくらいでいい話",
    "比べすぎない方が楽な理由",
    "他人の評価を気にしなくていい話",
    # 勘違い（①）も昼は刺さる
    "苦い＝美味しいと勘違いしてた頃",
    "お湯は熱いほどいいと思ってた",
]

TOPICS_NIGHT = [
    # 共感・放置向け（③＋⑦＋⑤）
    "ずっとえぐくて悩んでた頃",
    "薄すぎて水みたいだった話",
    "真面目にやりすぎて疲れた話",
    "情報を追いすぎた失敗",
    "コーヒーは生活の飲み物",
    "家コーヒーは頑張らない方が続く",
    "毎日飲むなら完璧はいらない",
    "まあいいかで飲む話",
]

TOPICS = [
    # ① 勘違い系
    "コーヒーは豆が一番大事だと思ってた話",
    "苦い＝美味しいと勘違いしてた頃",
    "高い器具が必要だと思い込んでた",
    "正解の淹れ方が一つだと思ってた",
    "毎回計量しないとダメだと思ってた",
    "お湯は熱いほどいいと思ってた",
    "最後まで落とすのが当たり前だと思ってた",
    "ブラックは我慢して飲むものだと思ってた",
    "酸っぱい＝失敗だと思ってた",
    "コーヒーは難しい飲み物だと思ってた",

    # ② 家で美味しくなる系
    "お湯を少し待つだけで変わった話",
    "粉をほんの少し増やした時の変化",
    "注ぐスピードを変えただけの話",
    "最初の一口を急がない理由",
    "淹れたらすぐ飲むだけで違った話",
    "カップを温めたら印象が変わった",
    "朝と夜で味の感じ方が違った話",
    "同じ豆でも日によって違う理由",
    "忙しい日は完璧を目指さない方がいい話",
    "失敗したと思った時の立て直し方",

    # ③ 失敗談・共感系
    "ずっとえぐくて悩んでた頃",
    "薄すぎて水みたいだった話",
    "毎回味がブレてた理由",
    "レシピ通りにしても美味しくならなかった話",
    "真面目にやりすぎて疲れた話",
    "一度コーヒー嫌いになりかけた話",
    "失敗を気にしなくなって楽になった話",
    "人に勧められて迷走した話",
    "情報を追いすぎた失敗",
    "自分の好みを無視してた頃",

    # ④ 選び方・考え方系
    "正解より自分の好みでいい話",
    "家で飲むなら十分な基準",
    "続けやすいコーヒーの考え方",
    "毎日飲むならこれくらいでいい話",
    "コスパより満足感の話",
    "比べすぎない方が楽な理由",
    "味の好みは日によって変わる話",
    "体調で味が変わる話",
    "他人の評価を気にしなくていい話",
    "今日はこれでいいと思える話",

    # ⑤ 一言刺し系
    "コーヒーが美味しくならない原因はだいたい一つ",
    "家コーヒーは頑張らない方が続く",
    "毎日飲むなら完璧はいらない",
    "苦いだけなら何かが合ってない",
    "高い器具より大事なこと",
    "正解探しをやめたら楽になった",
    "好きな味でいい",
    "情報を減らしたら美味しくなった",
    "コーヒーは生活の飲み物",
    "今日の一杯が全て",

    # ⑥ 生活×コーヒー
    "朝に飲む一杯の役割",
    "仕事前のコーヒーとの距離感",
    "休日のコーヒーは雑でいい話",
    "忙しい日のコーヒー",
    "雨の日の味の感じ方",
    "寒い日の一杯",
    "夏でもホットを飲む理由",
    "夜に飲まない選択",
    "一人で飲む時間",
    "誰かと飲むコーヒー",

    # ⑦ 劣化しない放置向け
    "コーヒーにハマりすぎない話",
    "飲み続けるコツ",
    "飽きた時の距離の取り方",
    "うまく淹れようとしない日",
    "失敗してもいい理由",
    "続く人と続かない人の違い",
    "生活に溶け込む瞬間",
    "習慣としてのコーヒー",
    "まあいいかで飲む話",
    "コーヒーは趣味じゃなくて日常",
]

MYTHS  = ["豆さえ良ければ勝ち","苦いほど本格派","高い器具が必要","毎回きっちり計らないとダメ"]
TRUTHS = ["お湯の温度","粉の量を少し増やすこと","注ぐスピード","淹れたてをすぐ飲むこと"]
ACTIONS = ["少し下げる","ほんの少し足す","ゆっくりにする","最初の一口を急がない"]

POINTS = ["沸騰したお湯を少し落ち着かせる","粉を入れたら表面を平らにする","最初は少量だけ注いで待つ",
          "濃いと感じたら粉を減らすよりお湯を少し増やす","薄いと感じたら注ぐ回数を減らす"]
BAD = ["ただ苦いだけ","薄くて物足りない","酸っぱく感じる","えぐい"]
STOP = ["勢いよくドバッと注ぐの","熱すぎるお湯のまま淹れるの","ずっとかき回すの","最後まで全部落とし切るの"]
DO = ["ゆっくり注ぐ","少し待ってから淹れる","途中で止める","最初の一口を丁寧にする"]
CAUSE = ["お湯が熱すぎる","注ぐのが速すぎる","粉が少なすぎる","最後まで落とし切ってる"]

BANNED = ["絶対","最強","バカ","死ね","政治","宗教","差別"]


def time_slot_jst():
    h = datetime.now(JST).hour
    if 5 <= h < 10:
        return "morning"
    if 10 <= h < 17:
        return "noon"
    return "night"

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def generate_post():
    slot = time_slot_jst()
    if slot == "morning":
        topic = random.choice(TOPICS_MORNING)
    elif slot == "noon":
        topic = random.choice(TOPICS_NOON)
    else:
        topic = random.choice(TOPICS_NIGHT)

    # topic を自然に混ぜる（テンプレはそのまま使う）
    t = random.choice(TEMPLATES)

    text = t.format(
        myth=random.choice(MYTHS),
        truth=random.choice(TRUTHS),
        action=random.choice(ACTIONS),
        p1=random.choice(POINTS),
        p2=random.choice(POINTS),
        p3=random.choice(POINTS),
        first=random.choice(["お湯の温度","注ぐスピード","粉の量"]),
        bad=random.choice(BAD),
        stop=random.choice(STOP),
        do=random.choice(DO),
        cause=random.choice(CAUSE),
    )

    # 最後に「話題」を添える（人間っぽくなる）
    # ※文字数が増えすぎたら quality_check が落とすので安全
    text = f"{text}\n\n{topic}"

    text = re.sub(r"[ \t]+", " ", text).strip()
    return text

def quality_check(text, recent):
    if any(b in text for b in BANNED):
        return False
    if not (SYSTEM_STYLE["min_len"] <= len(text) <= SYSTEM_STYLE["max_len"]):
        return False
    head = text[:30]
    if any(r.startswith(head) for r in recent):
        return False
    if text.count("\n") > 4:
        return False
    return True

def post_to_x(text):
    auth = OAuth1(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    url = "https://api.x.com/2/tweets"
    r = requests.post(url, auth=auth, json={"text": text}, timeout=30)
    if r.status_code >= 300:
        raise RuntimeError(f"X API error {r.status_code}: {r.text}")
    return r.json()

def main():
    state = load_json("state.json", {"paused": False})
    if state.get("paused"):
        print("paused=true; skip")
        return

    recent = load_json("recent.json", [])[-30:]

    for _ in range(5):
        text = generate_post()
        if quality_check(text, recent):
            break
    else:
        raise RuntimeError("Failed to generate acceptable post")

    print(f"[{datetime.now(JST).strftime('%Y-%m-%d %H:%M')}] {text} (len={len(text)})")
    res = post_to_x(text)

    recent.append(text)
    save_json("recent.json", recent[-60:])
    print("posted:", res)

if __name__ == "__main__":
    main()
