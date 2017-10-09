import argparse
from pywikibot import Site, Page
from bs4 import BeautifulSoup
import requests
from tabulate import tabulate
from jinja2 import Template
import pandas as pd
import numpy as np
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
    "ブロマイド(PPガチャ)": 951128679,
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

colors = ['紫', '藍', '青', '緑', '黄', '橙', '赤']


def get_sheet(name: str, **kargs) -> pd.DataFrame:
    '''スプレッドシートからシートを DataFrame として読み込む'''
    url = get_sheet_csv_url(name)
    r = requests.get(url)
    r.encoding = 'utf-8'
    df = pd.read_csv(io.StringIO(r.text), **kargs)
    df = df.rename(
        columns=lambda x: x.replace('\n', '').replace('.', '')) # 列名の改行を除去
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


def update_wiki(sheet_name, page_name,
                template_name=None, page_data_factory=None, data=None):
    '''Wiki の各ページを更新するための高階関数'''
    if data is None:
        data = page_data_factory(sheet_name)
    if template_name is None:
        template_name = page_name
    page_text = render_template(template_name, data)
    save_page(page_name, page_text, sheet_name, template_name)


def info_important_data_factory(sheet_name):
    '''「お知らせ/重要なお知らせ」ページの wiki を生成する'''
    df = get_sheet(sheet_name).fillna('-') # バージョンがないセルは '-' で埋める
    block_text = ''
    for i, row in reversed(list(df.iterrows())):
        block_text += render_template('お知らせ/重要なお知らせ/ブロック', row) + '\n\n'
    return {'ブロック': block_text}


def info_normal_data_factory(sheet_name):
    '''「お知らせ/一般情報」ページの wiki を生成する'''
    df = get_sheet(sheet_name)
    block_text = ''
    for i, row in reversed(list(df.iterrows())):
        block_text += render_template('お知らせ/一般情報/ブロック', row) + '\n\n'
    return {'ブロック': block_text}


def profile_data_factory(sheet_name):
    '''「プリズムスタァのプロフィール」ページの wiki を生成する'''
    df = get_sheet(sheet_name)
    block_text = ''
    for i, row in df.iterrows():
        block_text += render_template('プリズムスタァのプロフィール/ブロック', row) + '\n\n'
    return {'ブロック': block_text}


def cheering_goods_data_factory(sheet_name):
    '''「応援グッズ」ページの wiki を生成する'''
    df = get_sheet(sheet_name)
    # アイコン画像用列を追加
    df['アイコン'] = '[[File:アイテム ' + df['レア'] + ' ' + df['ブロマイド名'] + \
                     '.png|48x48px|' + df['ブロマイド名'] + ']]'
    goods_list_cols = ['アイコン', 'ブロマイド名', 'レア', 'タイプ']
    way_to_get_cols = ['アイコン', 'ブロマイド名', '楽曲ドロップ', '難易度', 'その他の入手方法']
    goods_list = tabulate(df[goods_list_cols],
                          tablefmt='wikia', headers='keys', showindex=False)
    way_to_get = tabulate(df[way_to_get_cols],
                          tablefmt='wikia', headers='keys', showindex=False)
    return {'応援グッズ一覧': goods_list, '入手方法': way_to_get}


def fan_level_data_factory(sheet_name):
    '''「ファンレベル」ページの wiki を生成する'''
    # まだデータが存在しないレベルの行を取り除く
    df = get_sheet(sheet_name, index_col='ファンレベル').dropna(axis=0, how='all').fillna('')
    parameter_cols = ['レベルアップに必要な経験値', 'Δ',
                      'キャパ', 'Δ1', 'スタミナ', 'Δ2', 'フレンド枠', 'Δ3']
    story_cols = ['解放ストーリー', '話数']
    parameter_table = tabulate(
        df[parameter_cols], tablefmt='wikia', headers='keys')
    story_table = tabulate(df[story_cols], tablefmt='wikia', headers='keys')
    return {'必要経験値と増加パラメータ': parameter_table, '解放ストーリー': story_table}


def tutorial_bromide_data_factory(sheet_name):
    '''「チュートリアルでもらえるブロマイド」ページの wiki を生成する'''
    df = get_sheet(sheet_name)
    block_text = ''
    for i, row in df.iterrows():
        block_text += render_template('チュートリアルでもらえるブロマイド/ブロック', row) + '\n\n'
    return {'ブロック': block_text}


def prism_point_gacha_bromide_data_factory(sheet_name):
    '''「Pポイントガチャで入手できるブロマイド」ページの wiki を生成する'''
    df = get_sheet(sheet_name).fillna('不明')
    df = df.replace('1', '○').replace('0', '×')
    table = tabulate(df, tablefmt='wikia', showindex=False, headers='keys')
    return {'テーブル': table}


def update_bromide():
    def to_int(i):
        if type(i) is float:
            return int(i)
        else:
            return i

    df = get_sheet('🎴 ブロマイド', skiprows=1)

    # jinja2 の変数名のために調整
    df.loc[:, 'first'] = df['1st']
    df.loc[:, 'second'] = df['2nd']
    df.loc[:, 'third'] = df['3rd']
    df.loc[:, 'チェンジ後最大ランク'] = df['最大ランク1']

    for i, bromide in df.iterrows():
        page_name = '{}{}{}'.format(
            bromide['レア'], bromide['ブロマイド名'], bromide['キャラクター名'])
        bromide = {k: to_int(v) for k,v in bromide.fillna('').to_dict().items()}
        update_wiki(
            sheet_name='🎴 ブロマイド',
            page_name=page_name,
            template_name='ブロマイド',
            page_data_factory=None,
            data=bromide)


def update_item_prism():
    '''3種類のプリズムの各ページを更新する'''
    df = get_sheet('楽曲リスト', header=1)
    bromide_df = get_sheet('ブロマイド', header=1)
    for prism_name in ['瞬きプリズム', '煌めきプリズム', '輝きプリズム']:
        for color in colors:
            # 楽曲リストを求める
            prism = df[df[prism_name].str.contains(color, na=False)]
            prism = prism[['楽曲グループ', '楽曲名', '難易度', prism_name]]
            songs_table_text = tabulate(prism, tablefmt='wikia',
                                  headers=prism.keys(), showindex=False)
            # プリズムを必要としているスタァを求める
            stars = bromide_df[bromide_df[prism_name] == color]
            stars = stars['レア'] + stars['ブロマイド名'] + stars['キャラクター名']
            stars = ['* [[{}]]'.format(star) for _, star in stars.items()]
            stars_list_text = '\n'.join(stars)

            page_name = '{}({})'.format(prism_name, color)
            data = {
                'アイテム名': page_name,
                '楽曲一覧': songs_table_text,
                'スタァ一覧': stars_list_text,
            }
            update_wiki(
                sheet_name='楽曲リスト',
                page_name=page_name,
                template_name='プリズム',
                data=data)


def load_template(name: str) -> str:
    '''`name` という名前の bot 用テンプレートを wiki から読み込む'''
    return Page(site, 'Template:bot/' + name).text


def render_template(page_name: str, data: any) -> str:
    '''wiki から取得したテンプレートにスプレッドシートのデータを流し込む'''
    template = load_template(page_name)
    if type(data) is not dict:
        data = dict(data)
    return Template(template).render(data)


def save_page(page_name: str, text: str, sheet_name: str,
              template_name: str) -> None:
    '''実際に wiki のページを書き込む'''
    if template_name is None:
        template_name = page_name

    # Bot 編集ページであることを知らせるフッターを付加して更新する
    sheet_url = get_sheet_url(sheet_name)
    footer = '\n\n{{bot/編集の注意|template_name = %s | url = %s}}' \
                                              % (template_name, sheet_url)
    text += footer

    # ページに変更がない場合には何もしない
    page = Page(site, page_name)
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
    update_wiki(
        sheet_name='ファンレベル',
        page_name='ファンレベル',
        page_data_factory=fan_level_data_factory)
    update_wiki(
        sheet_name='チュートリアル',
        page_name='チュートリアルでもらえるブロマイド',
        page_data_factory=tutorial_bromide_data_factory)
    update_wiki(
        sheet_name='ブロマイド(PPガチャ)',
        page_name='Pポイントガチャで入手できるブロマイド',
        page_data_factory=prism_point_gacha_bromide_data_factory)
    update_bromide()
    update_item_prism()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true',
                        help='デバッグモードで実行する')
    args = parser.parse_args()
    main(args)
