# 能登屋監控：安全試運行

* 每小時第 17 分鐘以 GitHub Actions 啟動一次唯讀日曆掃描（GitHub 排程可能延遲）。
* 目標：2026 年 12 月～2027 年 2 月、2 位成人、1 晚；優先河側 10 畳、7.5 畳、2 間客室。
* **安全模式：不會訂房、不會發送空房 Email、不會把 ○ 當作已確認可訂房。**
* 每次運行產出 Artifacts > notoya-safe-pilot-report > six-windows.json。
* 若頁面有可疑空房符號，必須另行確認「兩成人、1 晚、可進入有效方案」，正式警報程式尚未完成。
* 日曆中 7.5 畳房型若未顯示，視為未知，不等同客滿。
* 此 repository 若為 Public，請絕對不要提交 API key、私人信箱或其他憑證。

## 手動測試 Email（Brevo）

Outlook/Hotmail 只作收件信箱；寄件端選 Brevo API，不需提供 Outlook 密碼。
先自行在 Brevo 完成帳號及寄件地址／網域驗證，取得 API key。
在 GitHub Repository > Settings > Secrets and variables > Actions 設定以下 Repository secrets：
- BREVO_API_KEY：Brevo API key
- EMAIL_FROM：已在 Brevo 驗證的寄件地址
- EMAIL_TO：你的 Outlook/Hotmail 收件地址

在 Actions > Notoya safe monitoring pilot > Run workflow 將 email_test 勾選為 true，會寄一封清楚標示「測試」的信；排程絕不觸發寄信。若 Brevo API 拒絕請求，會在 job log 顯示錯誤，不會列出 API key。

## 注意
每小時掃描可能耗用 GitHub Actions 免費額度，私有庫請先檢查用量。GitHub 不保證精準按時啟動。公開庫若 60 天沒有活動，排程可能被停用。正式空房驗證和去重通知仍待開發。
