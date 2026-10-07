            - name: Telegram Cloud-Test
        if: github.event_name == 'workflow_dispatch'
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          python - <<'PY'
          import os, requests

          token = os.environ["TELEGRAM_BOT_TOKEN"]
          chat_id = os.environ["TELEGRAM_CHAT_ID"]

          r = requests.post(
              f"https://api.telegram.org/bot{token}/sendMessage",
              json={
                  "chat_id": chat_id,
                  "text": "✅ GOLD DEMO V3.8 – Cloud-Test erfolgreich\nGitHub Actions → Telegram → Handy funktioniert."
              },
              timeout=20
          )

          r.raise_for_status()
          print("Telegram Cloud-Test: OK")
          PY 
