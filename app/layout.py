"""
Shared HTML layout and styling helpers.
"""
from fastapi.responses import HTMLResponse


def render_page(title: str, body: str, user: dict | None = None) -> HTMLResponse:
    """
    Shared layout: dark background, nav bar, and optional 'signed in as' line.
    """
    if user:
        auth_links = """
          <a href="/my-alerts">
            <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" style="vertical-align:-4px;margin-right:8px;color:#fbbf24;">
              <path d="M12 3a6 6 0 00-6 6v3.5l-1.5 2.5h15L18 12.5V9a6 6 0 00-6-6z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M10 19a2 2 0 004 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            My alerts
          </a>
          <a href="/logout">
            <svg aria-hidden="true" width="16" height="16" viewBox="0 0 20 20" fill="none" style="vertical-align:-3px;margin-right:8px;color:#38bdf8;">
              <path d="M8 5l5 5-5 5" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M4 10h9" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Logout
          </a>
        """
        signed_in_text = f'Signed in as <strong>{user.get("email")}</strong>'
    else:
        auth_links = """
          <a href="/login">
            <svg aria-hidden="true" width="12" height="12" viewBox="0 0 20 20" fill="none" style="vertical-align:-2px;margin-right:6px;">
              <path d="M8 5l5 5-5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M4 10h9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Login
          </a>
        """
        signed_in_text = "Not signed in"

    admin_links = ""
    if user and user.get("role") == "admin":
        admin_links = """
              <a href="/jobs">📄 Jobs</a>
              <a href="/subscriptions">📬 Subscriptions</a>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>{title}</title>
        <style>
          :root {{
            color-scheme: dark;
          }}
          * {{
            box-sizing: border-box;
          }}
          body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 0;
            padding: 0;
            background: #020617;
            color: #e5e7eb;
          }}
          .page {{
            max-width: 960px;
            margin: 0 auto;
            padding: 1.5rem 1rem 3rem;
          }}
          header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding: 0.75rem 1rem;
            background: linear-gradient(90deg, rgba(56,189,248,0.08), rgba(34,197,94,0.08));
            border: 1px solid #1f2937;
            border-radius: 0.75rem;
          }}
          header h1 {{
            font-size: 1.4rem;
            margin: 0;
          }}
          nav {{
            display: flex;
            gap: 0.6rem;
            align-items: center;
          }}
          nav a {{
            text-decoration: none;
            color: #e5e7eb;
            font-size: 0.95rem;
            cursor: pointer;
            display: inline-block;
            padding: 6px 10px;
            border-radius: 8px;
            background: rgba(255,255,255,0.04);
            border: 1px solid transparent;
          }}
          nav a:hover {{
            color: #38bdf8;
            border-color: #1f2937;
          }}
          .signed-in {{
            font-size: 0.8rem;
            color: #9ca3af;
            margin-top: 0.25rem;
          }}
          main {{
            margin-top: 1rem;
          }}
          a {{
            color: #38bdf8;
          }}
          .card {{
            background: #020617;
            border-radius: 0.75rem;
            border: 1px solid #1f2937;
            padding: 1rem 1.25rem;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.5);
          }}
          .form-card {{
            max-width: 760px;
            margin: 0 auto;
          }}
          .form-card form {{
            max-width: 720px;
          }}
          label {{
            display: block;
            margin-top: 1rem;
            font-size: 0.95rem;
          }}
          input:not([type="checkbox"]):not([type="radio"]), select {{
            width: 100%;
            padding: 0.5rem;
            margin-top: 0.25rem;
            border-radius: 0.375rem;
            border: 1px solid #4b5563;
            background: #020617;
            color: #e5e7eb;
          }}
          input[type="checkbox"], input[type="radio"] {{
            width: auto;
            margin-top: 0;
            accent-color: #22c55e;
          }}
          button {{
            margin-top: 1.5rem;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            border: none;
            background: #22c55e;
            color: #022c22;
            font-weight: 600;
            cursor: pointer;
          }}
          button:hover {{
            background: #16a34a;
          }}
          table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
            background: #020617;
            font-size: 0.9rem;
          }}
          th, td {{
            border: 1px solid #1f2937;
            padding: 0.4rem 0.6rem;
            vertical-align: top;
          }}
          th {{
            background: #111827;
            text-align: left;
          }}
          tr:nth-child(even) td {{
            background: #020617;
          }}
          .muted {{
            color: #9ca3af;
            font-size: 0.85rem;
          }}
          .stats {{
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
          }}
          .stat {{
            flex: 0 0 140px;
            padding: 0.6rem 0.8rem;
            border-radius: 0.75rem;
            border: 1px solid #1f2937;
            background: #020617;
          }}
          .stat .label {{
            font-size: 0.75rem;
            color: #9ca3af;
          }}
          .stat .value {{
            font-size: 1.2rem;
            font-weight: 600;
          }}
          footer {{
            margin-top: 2.5rem;
            padding: 1.5rem 0;
            border-top: 1px solid #1f2937;
            font-size: 0.95rem;
            color: #e5e7eb;
            background: linear-gradient(90deg, rgba(56,189,248,0.08), rgba(34,197,94,0.08));
            border-radius: 0.75rem;
            width: 100%;
            text-align: center;
          }}
          footer a {{
            color: #38bdf8;
            text-decoration: none;
            font-weight: 600;
          }}
          footer a:hover {{
            color: #22d3ee;
          }}
        </style>
      </head>
      <body>
        <div class="page">
          <header>
            <div>
              <h1>{title}</h1>
              <div class="signed-in">{signed_in_text}</div>
            </div>
            <nav>
              <a href="/">🏠 Home</a>
              {admin_links}
              {auth_links}
            </nav>
          </header>
          <main>
            {body}
          </main>
          <footer>
            <div><strong>(c) 2025 Zone Job Alerts.</strong> All rights reserved.</div>
            <div><a href="/privacy">Privacy</a></div>
          </footer>
        </div>
      </body>
    </html>
    """
    return HTMLResponse(content=html)
