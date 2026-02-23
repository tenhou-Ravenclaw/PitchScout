/**
 * 【setupTests.ts】
 * 役割：テストを実行するための「環境設定」を行うファイルです。
 * React Testing Library を使ってテストを書く際、
 * 「要素が画面にあるか」などを簡単にチェックするための拡張機能を追加します。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づくステータス：
 * 1. 配置場所: src/setupTests.ts（このファイルは通常 src 直下に置きます）
 */

// jest-dom は、Jest というテストツールに「DOM（画面の要素）」に関する便利な命令を追加します。
// これにより、例えば以下のような書き方ができるようになります。
// expect(element).toHaveTextContent(/react/i) // 「要素に 'react' という文字が含まれているか」
import '@testing-library/jest-dom';