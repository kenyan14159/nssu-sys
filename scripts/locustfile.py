"""
負荷テスト設定ファイル（Locust）

使用方法:
1. pip install locust
2. locust -f scripts/locustfile.py
3. ブラウザで http://localhost:8089 を開く
4. ユーザー数とスポーンレートを設定して開始

推奨設定:
- 小規模テスト: 50ユーザー, 5ユーザー/秒
- 中規模テスト: 200ユーザー, 10ユーザー/秒
- 大規模テスト: 500ユーザー, 20ユーザー/秒
"""

from locust import HttpUser, between, task


class WebsiteUser(HttpUser):
    """一般ユーザーの行動をシミュレート"""
    
    # リクエスト間の待機時間（1-5秒）
    wait_time = between(1, 5)
    
    def on_start(self):
        """テスト開始時にログイン"""
        # ログインページにアクセス
        self.client.get("/accounts/login/")
        
        # CSRFトークンを取得してログイン
        # 注: 本番テストではテストユーザーを事前に作成しておく
        # response = self.client.post("/accounts/login/", {
        #     "username": "testuser@example.com",
        #     "password": "testpassword123",
        # })
    
    @task(10)
    def view_homepage(self):
        """トップページ閲覧"""
        self.client.get("/")
    
    @task(8)
    def view_competitions_dashboard(self):
        """大会ダッシュボード閲覧"""
        self.client.get("/competitions/")
    
    @task(5)
    def view_competition_list(self):
        """大会一覧閲覧"""
        self.client.get("/competitions/list/")


class AdminUser(HttpUser):
    """管理者ユーザーの行動をシミュレート"""
    
    wait_time = between(2, 8)
    weight = 1  # 一般ユーザーより少ない割合
    
    def on_start(self):
        """管理者としてログイン"""
        self.client.get("/admin/")
    
    @task(5)
    def view_admin_dashboard(self):
        """管理画面ダッシュボード"""
        self.client.get("/admin/")
    
    @task(3)
    def view_entry_list(self):
        """エントリー一覧（管理画面）"""
        self.client.get("/admin/entries/entry/")
    
    @task(3)
    def view_athlete_list(self):
        """選手一覧（管理画面）"""
        self.client.get("/admin/accounts/athlete/")
    
    @task(2)
    def view_heat_list(self):
        """組一覧（管理画面）"""
        self.client.get("/admin/heats/heat/")


class EntryFlowUser(HttpUser):
    """エントリーフローをシミュレート"""
    
    wait_time = between(3, 10)
    weight = 2  # エントリー期間中は多め
    
    @task(5)
    def complete_entry_flow(self):
        """エントリーフロー全体"""
        # 大会一覧
        self.client.get("/competitions/")
        
        # 大会詳細（IDは動的に取得する必要あり）
        # self.client.get("/competitions/1/")
        
        # エントリーカート確認
        # self.client.get("/entries/competition/1/cart/")
