import argparse
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
    '''スプレッドシートからシートを DataFrame として読み込む'''
    url = get_sheet_csv_url(name)
    r = requests.get(url)
    r.encoding = 'utf-8'
    df = pd.read_csv(io.StringIO(r.text))
    return df


def get_sheet_csv_url(name: str) -> str:
    url_base = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSWkD1CJvETQFWYfImMvpdGxJPmruNqh7HrCqc2d1FcE2m_hyBMjyOoFkbJFzxXBssgDapfng1IPUBB/pub?gid={sheet_id}&single=true&output=csv'
    return url_base.format(sheet_id=get_sheet_id(name))


def get_sheet_url(name: str) -> str:
    url_base = 'https://docs.google.com/spreadsheets/d/1of3ywHK2tUp2Q12x8Dh6CWHvh6RmNiigOvvYrZWayC4/edit#gid={sheet_id}'
    return url_base.format(sheet_id=get_sheet_id(name))


def get_sheet_id(name: str) -> int:
    '''シート名の一部からスプレッドシート上のシート id を取得する'''
    for sheet_name, sheet_id in sheet_ids.items():
        if name in sheet_name:
            return sheet_id
    return None


def update_wiki(sheet_name, page_name, page_data_factory):
    '''Wiki の各ページを更新するための高階関数'''
    data = page_data_factory(sheet_name)
    page_template = load_template(page_name)
    page_text = render_template(page_template, data)
    save_page(page_name, page_text, sheet_name)


def info_important_data_factory(sheet_name):
    '''「お知らせ/重要なお知らせ」ページの wiki を生成する'''
    df = get_sheet(sheet_name).fillna('-') # バージョンがないセルは '-' で埋める
    block_template = load_template('お知らせ/重要なお知らせ/ブロック')
    block_text = ''
    for i, row in reversed(list(df.iterrows())):
        block_text += render_template(block_template, row) + '\n\n'
    return {'ブロック': block_text}


def info_normal_data_factory(sheet_name):
    '''「お知らせ/一般情報」ページの wiki を生成する'''
    df = get_sheet(sheet_name)
    block_template = load_template('お知らせ/一般情報/ブロック')
    block_text = ''
    for i, row in reversed(list(df.iterrows())):
        block_text += render_template(block_template, row) + '\n\n'
    return {'ブロック': block_text}


def profile_data_factory(sheet_name):
    '''「プリズムスタァのプロフィール」ページの wiki を生成する'''
    df = get_sheet(sheet_name)
    block_template = load_template('プリズムスタァのプロフィール/ブロック')
    block_text = ''
    for i, row in df.iterrows():
        block_text += render_template(block_template, row) + '\n\n'
    return {'ブロック': block_text}


def cheering_goods_data_factory(sheet_name):
    '''「応援グッズ」ページの wiki を生成する'''
    df = get_sheet(sheet_name)
    # アイコン画像用列を追加
    df['アイコン'] = '[[File:アイテム ' + df['レア'] + ' ' + df['ブロマイド名'] + \
                     '.png|48x48px|' + df['ブロマイド名'] + ']]'
    template = load_template('応援グッズ')
    goods_list_cols = ['アイコン', 'ブロマイド名', 'レア', 'タイプ']
    way_to_get_cols = ['アイコン', 'ブロマイド名', '楽曲ドロップ', '難易度', 'その他の入手方法']
    goods_list = tabulate(df[goods_list_cols],
                          tablefmt='wikia', headers='keys', showindex=False)
    way_to_get = tabulate(df[way_to_get_cols],
                          tablefmt='wikia', headers='keys', showindex=False)
    return {'応援グッズ一覧': goods_list, '入手方法': way_to_get}


def load_template(name: str) -> str:
    '''`name` という名前の bot 用テンプレートを wiki から読み込む'''
    return Page(site, 'Template:bot/' + name).text


def render_template(template: str, data: any) -> str:
    '''wiki から取得したテンプレートにスプレッドシートのデータを流し込む'''
    if type(data) is not dict:
        data = dict(data)
    return Template(template).render(data)


def save_page(pagename: str, text: str, sheet_name: str) -> None:
    '''実際に wiki のページを書き込む'''

    # Bot 編集ページであることを知らせるフッターを付加して更新する
    sheet_url = get_sheet_url(sheet_name)
    footer = '\n\n{{bot/編集の注意|url = %s}}' % sheet_url
    text += footer

    # ページに変更がない場合には何もしない
    page = Page(site, pagename)
    if page.text == text:
        return

    page.text = text
    if args.debug:
        print(page.text)
    else:
        page.save()


def main(args):
    update_wiki(
        sheet_name='お知らせ/重要',
        page_name='お知らせ/重要なお知らせ',
        page_data_factory=info_important_data_factory)
    update_wiki(
        sheet_name='お知らせ/一般',
        page_name='お知らせ/一般情報',
        page_data_factory=info_normal_data_factory)
    update_wiki(
        sheet_name='プロフィール',
        page_name='プリズムスタァのプロフィール',
        page_data_factory=profile_data_factory)
    update_wiki(
        sheet_name='応援グッズ',
        page_name='応援グッズ',
        page_data_factory=cheering_goods_data_factory)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true',
                        help='デバッグモードで実行する')
    args = parser.parse_args()
    main(args)
