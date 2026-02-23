/**
 * 【App.test.tsx】
 * 役割：アプリが正しく動作するかを自動的に確認するためのテストファイルです。
 * 開発者が手動で確認しなくても、このプログラムを実行することで「画面に特定の文字が出ているか」などを検証できます。
 */

import React from "react";
// テスト用のライブラリ（React Testing Library）から必要な機能を読み込みます
import { render, screen } from "@testing-library/react";
// テスト対象となるアプリ本体を読み込みます
import App from "./App";

/**
 * ── 前準備 (Lifecycle) ──
 * 各テストケースが実行される「直前」に毎回行われる処理です。
 */
beforeEach(() => {
  // ブラウザの保存領域（localStorage）をクリアして、
  // 過去のログイン情報などに左右されない「真っさらな状態」でテストを開始します。
  localStorage.clear();
});

/**
 * ── テストケース ──
 * test("テストの名前", async () => { ... }) の形式で記述します。
 */
test("ランディング画面が初期表示される", async () => {
  // 1. 仮想的なブラウザ環境でアプリを起動（表示）させます
  render(<App />);
  
  // 2. 画面内に特定のテキストが存在するかをチェックします。
  // ここではランディングページに「NEW」（NEW RECORDの一部）と「HISTORY」が表示されているかを確認しています。
  
  // expect(...).toBeInTheDocument() は「～が画面上に存在するはずだ」という期待（アサーション）を表します。
  expect(await screen.findByText("NEW")).toBeInTheDocument();
  expect(await screen.findByText("HISTORY")).toBeInTheDocument();
});