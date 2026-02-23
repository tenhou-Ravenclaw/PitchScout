/**
 * 【App.test.tsx】
 * 役割：アプリが正しく動いているかを確認するための「自動テスト」ファイルです。
 * 開発者が手動で画面を確認しなくても、プログラムが自動で「文字が表示されているか」などをチェックします。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づく移動案：
 * 1. 移動先: src/app/App.test.tsx または src/__tests__/
 * 2. 理由：アプリ全体の動作確認（スモークテスト）を担当するため、appフォルダ等にまとめると管理しやすくなります。
 */

import React from "react";
// テスト用の便利な道具（レンダリング機能や画面検索機能）を読み込みます
import { render, screen } from "@testing-library/react";
import App from "./App";

/**
 * ── 前準備 (Lifecycle) ──
 * 各テストが始まる前に毎回実行される処理です。
 */
beforeEach(() => {
  // ブラウザに保存されている一時データを消去して、常に「真っさらな状態」でテストを開始します
  localStorage.clear();
});

/**
 * ── テストケース本体 ──
 * test("テストの名前", async () => { ... }) という形式で書きます。
 */
test("ランディング画面が初期表示される", async () => {
  // 1. 仮想的なブラウザ上でアプリを起動（表示）させます
  render(<App />);

  // 2. 画面内に特定の文字があるか探します。
  // ここではトップ画面（Landing）の「NEW RECORD」と「HISTORY」という文字を探しています。
  
  // expect(...).toBeInTheDocument() は「～が画面上にあるはずだ」という期待を表します
  expect(await screen.findByText("NEW")).toBeInTheDocument();
  expect(await screen.findByText("HISTORY")).toBeInTheDocument();
});