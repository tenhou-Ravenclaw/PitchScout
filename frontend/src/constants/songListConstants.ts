/**
 * 【songListConstants.ts】
 * SongListPage で使用する定数とユーティリティ関数を集約したファイルです。
 */

/**
 * 五十音インデックスの見出し文字
 * アーティスト名の並び替えと検索ジャンプに使用します。
 */
export const INDEX_KANA = ['あ', 'か', 'さ', 'た', 'な', 'は', 'ま', 'や', 'ら', 'わ'];

/**
 * ページあたりの表示件数
 */
export const ARTISTS_PER_PAGE = 10;
export const SONGS_PER_PAGE = 10;

/**
 * ── 五十音の行判定 ──
 * 
 * ひらがなの読み（reading）の先頭文字から、あ・か・さ...の行番号を返します。
 * アーティスト名を五十音順に分類する際に使用します。
 * 
 * @param reading - ひらがなまたはカタカナの読み仮名
 * @returns 0-9: あ行～わ行 / 99: その他（英字・記号など）
 * 
 * @example
 * getConsonantRow("あいうえお") // => 0 (あ行)
 * getConsonantRow("かきくけこ") // => 1 (か行)
 * getConsonantRow("ABC") // => 99 (その他)
 */
export const getConsonantRow = (reading: string): number => {
  if (!reading) return 99;
  let code = reading.codePointAt(0) ?? 0;
  // カタカナをひらがな範囲にずらす
  if (code >= 0x30A1 && code <= 0x30F6) code -= 0x60;
  if (code >= 0x3041 && code <= 0x3093) {
    if (code <= 0x304A) return 0; // あ行
    if (code <= 0x3054) return 1; // か行
    if (code <= 0x305E) return 2; // さ行
    if (code <= 0x3069) return 3; // た行
    if (code <= 0x306E) return 4; // な行
    if (code <= 0x307D) return 5; // は行
    if (code <= 0x3082) return 6; // ま行
    if (code <= 0x3088) return 7; // や行
    if (code <= 0x308D) return 8; // ら行
    return 9; // わ行
  }
  return 99;
};

/**
 * ── 検索用の略称辞書（エイリアス） ──
 * 
 * ユーザーが入力した略称を、データベース上の正式名称に読み替えます。
 * 例: "ミセス" → "Mrs. GREEN APPLE"
 * 
 * @remarks
 * ユーザーが略称で検索しても、正式名称のアーティストを見つけられるようにします。
 * 大文字・小文字、ひらがな・カタカナの両方に対応しています。
 */
export const SEARCH_ALIASES: Record<string, string> = {
  // === 超定番・現代ポップス・ロック ===
  "ミセス": "Mrs. GREEN APPLE",
  "みせす": "Mrs. GREEN APPLE",
  "ヒゲダン": "Official髭男dism",
  "ひげだん": "Official髭男dism",
  "ワンオク": "ONE OK ROCK",
  "わんおく": "ONE OK ROCK",
  "バウンディ": "Vaundy",
  "ばうんでぃ": "Vaundy",
  "キングヌー": "King Gnu",
  "きんぐぬー": "King Gnu",
  "ヌー": "King Gnu",
  "ヨアソビ": "YOASOBI",
  "よあそび": "YOASOBI",
  "セカオワ": "SEKAI NO OWARI",
  "せかおわ": "SEKAI NO OWARI",
  "ラッド": "RADWIMPS",
  "らっど": "RADWIMPS",
  "ヨルシカ": "ヨルシカ",
  "ずとまよ": "ずっと真夜中でいいのに。",
  "ズトマヨ": "ずっと真夜中でいいのに。",
  "マカエン": "マカロニえんぴつ",
  "まかえん": "マカロニえんぴつ",
  "サウシー": "Saucy Dog",
  "さうしー": "Saucy Dog",
  "リョクシャカ": "緑黄色社会",
  "りょくしゃか": "緑黄色社会",
  "マイヘア": "My Hair is Bad",
  "まいへあ": "My Hair is Bad",
  "ノベブラ": "Novelbright",
  "ノーベル": "Novelbright",
  "ビーファ": "BE:FIRST",
  "びーふぁ": "BE:FIRST",

  // === 英語名のカタカナ読み ===
  "アド": "Ado",
  "あど": "Ado",
  "ユーリ": "優里",
  "ゆうり": "優里",
  "エメ": "Aimer",
  "えめ": "Aimer",
  "ユーアールユー": "Uru",
  "ウル": "Uru",
  "ミレイ": "milet",
  "みれい": "milet",
  "イヴ": "Eve",
  "いゔ": "Eve",
  "いぶ": "Eve",
  "オーサム": "Awesome City Club",
  "ディッシュ": "DISH//",
  "でぃっしゅ": "DISH//",
  "バックナンバー": "back number",
  "ばっくなんばー": "back number",

  // === レジェンド・定番バンド ===
  "ミスチル": "Mr.Children",
  "みすちる": "Mr.Children",
  "ポルノ": "ポルノグラフィティ",
  "ぽるの": "ポルノグラフィティ",
  "バンプ": "BUMP OF CHICKEN",
  "ばんぷ": "BUMP OF CHICKEN",
  "アジカン": "ASIAN KUNG-FU GENERATION",
  "あじかん": "ASIAN KUNG-FU GENERATION",
  "エルレ": "ELLEGARDEN",
  "えるれ": "ELLEGARDEN",
  "ウーバー": "UVERworld",
  "うーばー": "UVERworld",
  "ラルク": "L'Arc~en~Ciel",
  "らるく": "L'Arc~en~Ciel",
  "ブルハ": "THE BLUE HEARTS",
  "ぶるは": "THE BLUE HEARTS",
  "モンパチ": "MONGOL800",
  "もんぱち": "MONGOL800",
  "ドロス": "![Alexandros]",
  "アレキ": "![Alexandros]",
  "カナブーン": "KANA-BOON",
  "かなぶーん": "KANA-BOON",
  "ホルモン": "マキシマム ザ ホルモン",
  "マンウィズ": "MAN WITH A MISSION",
  "テンフィ": "10-FEET",
  "てんふぃ": "10-FEET",
  "スピッツ": "スピッツ",
  "spitz": "スピッツ",

  // === グループ・アイドル・その他 ===
  "ドリカム": "DREAMS COME TRUE",
  "どりかむ": "DREAMS COME TRUE",
  "いきもの": "いきものがかり",
  "エグザイル": "EXILE",
  "えぐざいる": "EXILE",
  "三代目": "三代目 J SOUL BROTHERS from EXILE TRIBE",
  "ジェネ": "GENERATIONS from EXILE TRIBE",
  "ストーンズ": "SixTONES",
  "すとーんず": "SixTONES",
  "スノ": "Snow Man",
  "すの": "Snow Man",
  "エイト": "関ジャニ∞",
  "キンキ": "KinKi Kids",
  "ももクロ": "ももいろクローバーZ",
  "モー娘。": "モーニング娘。",
  "ニジュー": "NiziU",
  "にじゅー": "NiziU",
  "パフューム": "Perfume",
  "ぱふゅーむ": "Perfume",
  "ビッシュ": "BiSH",
  "びっしゅ": "BiSH",

  // === よくある略称（ソロアーティスト等） ===
  "ユーミン": "松任谷由実",
  "ゆーみん": "松任谷由実",
  "林檎": "椎名林檎",
  "りんご": "椎名林檎",
  "事変": "東京事変",
  "じへん": "東京事変",
  "源さん": "星野源",
  "げんさん": "星野源"
};
