/**
 * 【reportWebVitals.ts】
 * 役割：アプリの読み込み速度などのパフォーマンスデータを計測するためのツールです。
 */

import { ReportHandler } from 'web-vitals';

const reportWebVitals = (onPerfEntry?: ReportHandler) => {
  if (onPerfEntry && onPerfEntry instanceof Function) {
    // 実際に計測を行うライブラリを必要な時だけ読み込みます
    import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      getCLS(onPerfEntry);  // 画面のズレ
      getFID(onPerfEntry);  // 操作への反応時間
      getFCP(onPerfEntry);  // 最初の表示時間
      getLCP(onPerfEntry);  // メインの表示時間
      getTTFB(onPerfEntry); // サーバーからの返答時間
    });
  }
};

export default reportWebVitals;