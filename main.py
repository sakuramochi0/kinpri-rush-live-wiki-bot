from pywikibot import Site, Page
from bs4 import BeautifulSoup
import requests
from tabulate import tabulate
from jinja2 import Template
import pandas as pd
import io
from mypy.types import Dict


site = Site()
sheet_ids = {
    "📺 シナリオ一覧": 788224352,
    "🎉 イベント": 195852940,
    "ℹ️ このファイルについて": 569209742,
    "🌏 translation help": 1795795580,
    "ジャンプ(スタァ別)": 607126312,
    "🌈 ジャンプ": 397595116,
    "🎴 ブロマイド": 1442344221,
    "ジャンプコマンド": 1371879367,
    "合体ジャンプ": 1223304644,
    "🎶 楽曲リスト": 1572242050,
    "🎫 Prismチケット入手条件": 451938944,
    "ブロマイト(PPガチャ)": 951128679,
    "📕 応援グッズ": 1833623005,
    "🎁 日替わりプレゼント": 1247915676,
    "⛸️ 練習経験値": 2109961420,
    "⛸️ 練習コスト": 585549272,
    "ファンレベル": 1956343157,
    "コレクション": 1441848021,
    "🔢 ガチャ確率": 0,
    "スチル": 53502103,
    "❓ ゲーム内ヘルプ": 1132300940,
    "チュートリアル": 1753746412,
    "👥 プロフィール": 1890320497,
    "お知らせ/一般": 1393334757,
    "お知らせ/重要": 1834106149,
}


def get_sheet(name: str) -> pd.DataFrame:
    '''スプレッドシートからシートを読み込む'''
    url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSWkD1CJvETQFWYfImMvpdGxJPmruNqh7HrCqc2d1FcE2m_hyBMjyOoFkbJFzxXBssgDapfng1IPUBB/pub?gid={sheet_id}&single=true&output=csv'.format(
        sheet_id=get_sheet_id(name),
    )
    r = requests.get(url)
    r.encoding = 'utf-8'

    # バージョンがないセルは '-' で埋める
    df = pd.read_csv(io.StringIO(r.text)).fillna('-')
    return df


def get_sheet_id(name: str) -> int:
    for sheet_name, sheet_id in sheet_ids.items():
        if name in sheet_name:
            return sheet_id
    return None

def update_info_important() -> None:

    # ブロックのテンプレートをfill
    df = get_sheet('お知らせ/重要')
    block_template = load_template('お知らせ/重要なお知らせ/ブロック')
    block_text = ''
    for i, row in reversed(list(df.iterrows())):
        block_text += render_template(block_template, dict(row)) + '\n\n'

    # テンプレートをfill
    page_template = load_template('お知らせ/重要なお知らせ')
    page_text = render_template(page_template, {'ブロック': block_text})

    # wiki に書き込み
    save_page('お知らせ/重要なお知らせ', page_text)


def update_info_normal() -> None:

    # ブロックのテンプレートをfill
    df = get_sheet('お知らせ/一般')
    block_template = load_template('お知らせ/一般情報/ブロック')
    block_text = ''
    for i, row in reversed(list(df.iterrows())):
        block_text += render_template(block_template, dict(row)) + '\n\n'

    # テンプレートをfill
    page_template = load_template('お知らせ/一般情報')
    page_text = render_template(page_template, {'ブロック': block_text})

    # wiki に書き込み
    save_page('お知らせ/一般情報', page_text)


def load_template(name: str) -> str:
    '''`name` という名前の bot 用テンプレートを wiki から読み込む'''
    return Page(site, 'Template:bot/' + name).text


def render_template(template: str, data: Dict) -> str:
    return Template(template).render(data)


def save_page(pagename: str, text: str) -> None:
    page = Page(site, pagename)

    # ページに変更がない場合には何もしない
    if page.text == text:
        return

    page.text = text
    page.save()


def main():
    update_info_important()
    update_info_normal()


if __name__ == '__main__':
    main()
