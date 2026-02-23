/**
 * 【index.tsx】
 * 役割：Reactアプリを開始（起動）させるためのメインファイルです。
 * ブラウザのHTMLファイルにある土台（root）を見つけて、そこにアプリを流し込みます。
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
// アプリ全体のデザイン（CSS）を読み込みます
import './index.css';
// アプリのメインプログラムである App.tsx を読み込みます
import App from './App';
// アプリの表示速度などを計測するためのツールを読み込みます
import reportWebVitals from './reportWebVitals';

/**
 * ── アプリの土台作り ──
 * public/index.html の中にある <div id="root"></div> を探し、
 * そこに React が描画するための「根っこ（root）」を作成します。
 */
const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

/**
 * ── アプリの描画 ──
 * root.render を実行することで、実際に画面にアプリが表示されます。
 */
root.render(
  /**
   * <React.StrictMode>:
   * 開発中に、コードの古い書き方や潜在的な問題を自動でチェックして
   * コンソールに警告を出してくれる機能です。
   */
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

/**
 * ── パフォーマンス計測 ──
 * 表示スピードなどをログに出力したい場合に利用します。
 * 例: reportWebVitals(console.log); と書くと詳細が見れます。
 */
reportWebVitals();