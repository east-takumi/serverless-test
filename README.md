# Step Functions Local Testing

GitHub ActionsでStep Functions Localを使用した自動テストを含むサーバレスアプリケーション。

## プロジェクト構造

```
├── src/                    # Lambda関数のソースコード
├── tests/                  # テストファイル
├── workflow/               # Step Functions定義
├── .github/workflows/      # GitHub Actionsワークフロー
├── template.yaml           # SAMテンプレート
├── requirements.txt        # Python依存関係
├── samconfig.toml         # SAM設定
└── .gitignore             # Git除外ファイル
```

## 概要

3つのLambda関数を順次実行するStep Functionsワークフローを実装し、Step Functions Localを使用してローカル環境でテストします。

### ワークフロー構成

1. **State1**: 初期入力データを処理
2. **State2**: 中間処理を実行
3. **State3**: 最終出力を生成

## 要件

- Python 3.9+
- AWS SAM CLI
- Step Functions Local
- Docker (Step Functions Local用)

## セットアップ

1. 依存関係のインストール:
```bash
pip install -r requirements.txt
```

2. SAMアプリケーションのビルド:
```bash
sam build
```

3. ローカルでのテスト実行:
```bash
# Step Functions LocalのJAR版を使用し、AWS公式ドキュメントに記載された
# Lambda連携手順に合わせてSAM Localと接続します。
# 参考: https://docs.aws.amazon.com/ja_jp/step-functions/latest/dg/sfn-local-lambda.html
sam local start-lambda --port 3001
java -jar stepfunctions-local/StepFunctionsLocal.jar \
  --lambda-endpoint http://localhost:3001 \
  --aws-account-id 123456789012 \
  --lambda-function-arn-prefix arn:aws:lambda:us-east-1:123456789012:function \
  --region us-east-1
```

GitHub Actionsのワークフローでも同じ構成を採用しており、Step Functions LocalをJAR版で起動することで、SAM Localのエンドポイントへ確実に到達できるようにしています。

## GitHub Actionsでの認証情報管理

このリポジトリのワークフローはStep Functions Local／SAM Localのみに接続する前提で構成しており、実際のAWSリソースへアクセスすることは想定していません。
そのため、GitHub Actions上ではダミー資格情報を自動設定してローカルエンドポイントに署名付きリクエストを送れるようにしています。

> **NOTE:** 将来的に本物のAWSリソースへアクセスするケースが出てきた場合のみ、GitHub Secretsにアクセスキーを登録し、ワークフローで利用するよう調整してください。
