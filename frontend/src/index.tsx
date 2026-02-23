/**
 * 【index.tsx】
 * 役割：アプリの「エントリポイント（最初の実行地点）」です。
 * ブラウザのHTMLにある「root」という場所を探して、そこにReactアプリを流し込みます。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づくステータス：
 * 1. 配置場所: src/index.tsx（このファイルは src 直下にあるのが一般的です）
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
// グローバルスタイルを読み込み
import './index.css';
// アプリ本体（App.tsx）を読み込み
import App from './App';
// パフォーマンス計測用の道具を読み込み
import reportWebVitals from './reportWebVitals';

/**
 * ── アプリの起動（マウント） ──
 * public/index.html の中にある <div id="root"></div> を捕まえます。
 */
const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

/**
 * ── 描画の実行 ──
 * root.render によって、Appコンポーネントが実際に画面に表示されます。
 */
root.render(
  /**
   * React.StrictMode: 
   * 開発中に、プログラムのおかしな書き方や古い機能を自動で警告してくれるモードです。
   * 本番環境には影響しません。
   */
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

/**
 * ── パフォーマンス計測 ──
 * アプリの表示速度などをログに出したい場合に、関数を渡して実行します。
 * (例: reportWebVitals(console.log))
 */
reportWebVitals();