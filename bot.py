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
    return re.sub(r"[ \t]+", " ", text).strip()

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
