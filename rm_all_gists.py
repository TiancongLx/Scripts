import os
import sys
import time
import requests
from typing import List, Dict
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# API Constants
GITHUB_API_BASE_URL = 'https://api.github.com'
GITHUB_API_VERSION = 'application/vnd.github.v3+json'
ITEMS_PER_PAGE = 100
API_SLEEP_TIME = 0.5

# Environment Variables
ENV_TOKEN_NAME = 'GITHUB_TOKEN'

# Messages
MSG_TOKEN_NOT_FOUND = "[red]錯誤: 未設置 GITHUB_TOKEN 環境變數[/red]"
MSG_TOKEN_SETUP_GUIDE = """請設置您的 GitHub Personal Access Token:
Linux/macOS: export GITHUB_TOKEN='your_token'
Windows PowerShell: $env:GITHUB_TOKEN='your_token'
Windows CMD: set GITHUB_TOKEN=your_token"""

class GistDeleter:
    def __init__(self):
        self.console = Console()
        self.token = self._get_github_token()
        self.headers = {
                'Authorization': f'token {self.token}',
                'Accept': GITHUB_API_VERSION
                }
        self.base_url = GITHUB_API_BASE_URL

    def _get_github_token(self) -> str:
        """從環境變數獲取 GitHub token"""
        token = os.getenv(ENV_TOKEN_NAME)
        if not token:
            self.console.print(MSG_TOKEN_NOT_FOUND)
            self.console.print(MSG_TOKEN_SETUP_GUIDE)
            sys.exit(1)
        return token

    def get_all_gists(self) -> List[Dict]:
        """獲取所有 Gists（支援分頁）"""
        all_gists = []
        page = 1
        per_page = 100

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("正在獲取 Gists...", total=None)

            while True:
                response = requests.get(
                    f'{self.base_url}/gists',
                    headers=self.headers,
                    params={'page': page, 'per_page': per_page}
                )

                if response.status_code != 200:
                    self.console.print(f"[red]獲取 Gists 失敗: {
                                       response.status_code}[/red]")
                    sys.exit(1)

                gists = response.json()
                if not gists:
                    break

                all_gists.extend(gists)
                progress.update(task, advance=len(gists))
                page += 1

        return all_gists

    def format_gist_info(self, gist: Dict) -> str:
        """格式化 Gist 資訊"""
        created_at = datetime.strptime(
            gist['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        files = ', '.join(f"{name}" for name in gist['files'].keys())
        description = gist['description'] or '無描述'
        return f"ID: {gist['id']}\n  建立時間: {created_at}\n  檔案: {files}\n  描述: {description}"

    def delete_gists(self, gists: List[Dict]) -> None:
        """刪除指定的 Gists"""
        total = len(gists)

        if not self._confirm_deletion(total):
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            # 在 add_task 的 f-string 中添加佔位符 {task.completed}
            task = progress.add_task(f"正在刪除 Gists，當前進度：0/{total}", total=total)

            for i, gist in enumerate(gists):
                try:
                    response = requests.delete(
                        f'{self.base_url}/gists/{gist["id"]}',
                        headers=self.headers
                    )

                    if response.status_code != 204:
                        self.console.print(f"[yellow]警告: 刪除 Gist {
                                       gist['id']} 失敗[/yellow]")

                    # 避免觸發 API 限制
                    time.sleep(API_SLEEP_TIME)

                except Exception as e:
                    self.console.print(f"[red]錯誤: 刪除 Gist {
                                       gist['id']} 時發生異常: {str(e)}[/red]")

                # 更新任務進度，並在 description 中顯示更詳細的資訊
                progress.update(task, advance=1, description=f"正在刪除 Gists, 當前 {i+1}/{total}...")

    def _confirm_deletion(self, count: int) -> bool:
        """確認刪除操作"""
        self.console.print(f"\n[yellow]警告: 您即將刪除 {count} 個 Gists[/yellow]")
        self.console.print("[red]此操作不可撤銷！[/red]")
        return input("\n輸入 'yes' 確認刪除: ").strip().lower() == 'yes'

    def run(self):
        """主運行函數"""
        self.console.print("[bold blue]開始獲取您的 Gists...[/bold blue]")
        gists = self.get_all_gists()

        if not gists:
            self.console.print("[yellow]未找到任何 Gists[/yellow]")
            return

        self.console.print(f"\n[green]找到 {len(gists)} 個 Gists:[/green]")
        for gist in gists:
            self.console.print(self.format_gist_info(gist))

        self.delete_gists(gists)
        self.console.print("[bold green]操作完成！[/bold green]")

if __name__ == "__main__":
    deleter = GistDeleter()
    deleter.run()

