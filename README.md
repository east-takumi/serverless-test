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
# Step Functions Localの起動とテスト実行は後続のタスクで実装
```

## GitHub Actionsでの認証情報管理

GitHub Actions上でAWSリソースへ安全にアクセスするには、リポジトリのシークレットに認証情報を登録します。

1. GitHubのリポジトリページで **Settings > Secrets and variables > Actions** を開きます。
2. 以下のシークレットを追加します。
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - （必要に応じて）`AWS_SESSION_TOKEN`
3. ワークフローではこれらのシークレットが自動的に読み込まれ、`aws-actions/configure-aws-credentials` によって安全に設定されます。シークレットが未登録の場合はローカルテスト向けのダミー資格情報が自動的に使用されます。