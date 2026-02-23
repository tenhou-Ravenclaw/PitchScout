/**
 * 【reportWebVitals.ts】
 * 役割：アプリのパフォーマンス（表示スピードや反応の良さ）を計測するためのツールです。
 * Googleが提唱している「Web Vitals」という指標（読み込み時間やズレの少なさ）を測ります。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づくステータス：
 * このファイルは src 直下、あるいは src/utils/ に配置されるのが一般的です。
 */

import { ReportHandler } from 'web-vitals';

/**
 * 計測データを処理する関数
 * @param onPerfEntry 計測結果を受け取った時に実行したい関数（例：console.log）
 */
const reportWebVitals = (onPerfEntry?: ReportHandler) => {
  if (onPerfEntry && onPerfEntry instanceof Function) {
    // web-vitals ライブラリを動的に読み込み、各指標を取得します
    import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      getCLS(onPerfEntry);  // 画面のガタつき（ズレ）
      getFID(onPerfEntry);  // 最初の操作への反応速度
      getFCP(onPerfEntry);  // 最初の文字や画像が出るまでの時間
      getLCP(onPerfEntry);  // 最も大きなコンテンツが出るまでの時間
      getTTFB(onPerfEntry); // サーバーからの最初の1バイトが届くまでの時間
    });
  }
};

export default reportWebVitals;