# CPOS Engine-Zero (DevOps x AI Agent Hackathon 2026 Edition)

## Overview
CPOS Engine-Zero は、DevOps サイクルにおける「Run (まわす)」を自動化する、自律型安定性確保エージェントです。
Google Cloud (Gemini) と CPOS (Context Pointer OS) の設計思想を融合し、脆弱性やバグの検出から、AI による修正案の生成、そして Sandbox での検証までを完全自動で行います。

## Key Features
- **Autonomous Self-Healing**: Gemini CLI を活用し、検出された問題に対して最適な修正コードを自律的に生成・適用します。
- **Interactive Command Center (Dashboard 2.0)**: HTTPS 化されたダッシュボードで、リアルタイムの実行状況や「Memory Graph」による思考プロセスの可視化、修正の承認・却下、ロールバックが可能です。
- **Defensive Backend**:
    - **Encrypted Context Memory**: AES-128 (Fernet) によるポインタと監査ログの暗号化。
    - **Tamper-evident Hash Chain**: 全ての操作ログをハッシュチェーンで連結し、改ざんを即座に検知。
    - **HSTS / CSP Enforcement**: 強固なセキュリティヘッダーによる要塞化された運用環境。
- **Context Pointers (#ctx)**: ファイル間の依存関係や過去の失敗パターンをポインタとして管理し、LLM に最適な文脈を提供します。
- **Audit & Sandbox**: すべての修正は Docker Sandbox 内で検証され、安定性が確認されたコードのみが最終的なアウトプットとなります。

## Deployment & Security
### Running the Secure Server
1. 依存関係のインストール:
   ```bash
   cd cpos_defensive_agent
   .venv/bin/pip install -r requirements.txt
   ```

2. サーバーの起動 (HTTPS 必須):
   ```bash
   export CPOS_ENFORCE_HTTPS=true
   export CPOS_REQUIRE_FIX_APPROVAL=true
   .venv/bin/python server.py
   ```
   ダッシュボードには `https://<IP>:8080/dashboard` でアクセスできます（自己署名証明書のため警告が出ますが、通信は暗号化されています）。

3. デモのトリガー:
   ```bash
   .venv/bin/python trigger_demo.py
   ```

## Detailed Pitch & Strategy
詳細はプロジェクトルートの [PITCH.md](../PITCH.md) を参照してください。

---
** Kagioneko (2026) | DevOps x AI Agent Hackathon **
