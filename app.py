#!/usr/bin/env python3
"""STUDYX Web App — serves course materials from the study.db SQLite database.

This is a lightweight Flask app that can run standalone or embedded in bot.py.
It provides:
  - API endpoints: /api/modules, /api/materials/<module>
  - A static HTML frontend at /
  - Download endpoint: /api/materials/<module>/<material_id>/download

Usage:
  python3 webapp/app.py            # standalone, port 5000
  Or import start_webapp() from bot.py to run as background task.
"""
import os
import sys
import json
import logging
import sqlite3

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_PATH

logger = logging.getLogger(__name__)

from flask import Flask, jsonify, send_file, send_from_directory, request, Response

app = Flask(__name__,
            static_folder='static',
            static_url_path='/static',
            template_folder='templates')

# Path for the synced JSON (used on GitHub Pages)
JSON_PATH = os.path.join(os.path.dirname(__file__), 'static', 'api', 'materials.json')


def _get_db():
    """Return a sqlite3 connection (read-only for web safety)."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/materials.json')
def api_materials_json():
    """Serve the synced JSON file (for GitHub Pages compatibility).
    If not found, fetch from DB directly."""
    if os.path.exists(JSON_PATH):
        return send_file(JSON_PATH, mimetype='application/json')

    conn = _get_db()
    try:
        cursor = conn.execute("""
            SELECT mo.name as module_name, m.id, m.title, m.file_path,
                   m.file_size, m.mime_type, m.content_text, m.uploaded_at
            FROM materials m
            JOIN modules mo ON m.module_id = mo.id
            ORDER BY m.uploaded_at DESC
        """)
        materials = []
        for row in cursor.fetchall():
            materials.append({
                "module": row["module_name"],
                "id": row["id"],
                "title": row["title"],
                "file_path": row["file_path"],
                "file_size": row["file_size"],
                "mime_type": row["mime_type"],
                "content_text": row["content_text"],
                "uploaded_at": row["uploaded_at"],
            })
        return jsonify({"modules": [], "materials": materials, "last_updated": None})
    finally:
        conn.close()


@app.route('/api/modules')
def api_modules():
    """Return all modules with material counts."""
    conn = _get_db()
    try:
        cursor = conn.execute("""
            SELECT mo.id, mo.name, mo.description,
                   COUNT(m.id) as material_count
            FROM modules mo
            LEFT JOIN materials m ON m.module_id = mo.id
            GROUP BY mo.id
            ORDER BY mo.name
        """)
        modules = []
        for row in cursor.fetchall():
            modules.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"] or "",
                "material_count": row["material_count"] or 0,
            })
        return jsonify({"modules": modules})
    finally:
        conn.close()


@app.route('/api/materials/<module_name>')
def api_materials(module_name):
    """Return all materials for a given module name."""
    conn = _get_db()
    try:
        cursor = conn.execute("""
            SELECT m.id, m.title, m.file_path, m.file_size,
                   m.mime_type, m.content_text, m.uploaded_at
            FROM materials m
            JOIN modules mo ON m.module_id = mo.id
            WHERE mo.name = ?
            ORDER BY m.uploaded_at DESC
        """, (module_name,))
        materials = []
        for row in cursor.fetchall():
            materials.append({
                "id": row["id"],
                "title": row["title"],
                "file_path": row["file_path"],
                "file_size": row["file_size"],
                "mime_type": row["mime_type"],
                "uploaded_at": row["uploaded_at"],
                "download_url": f"/api/materials/{module_name}/{row['id']}/download",
            })
        return jsonify({"module": module_name, "materials": materials})
    finally:
        conn.close()


@app.route('/api/materials/<module_name>/<int:material_id>/download')
def api_download(module_name, material_id):
    """Download a specific material file."""
    conn = _get_db()
    try:
        cursor = conn.execute("""
            SELECT m.file_path, m.title, m.mime_type
            FROM materials m
            JOIN modules mo ON m.module_id = mo.id
            WHERE mo.name = ? AND m.id = ?
        """, (module_name, material_id))
        row = cursor.fetchone()
        if not row or not row["file_path"]:
            return jsonify({"error": "Material not found"}), 404

        file_path = row["file_path"]
        if not os.path.exists(file_path):
            return jsonify({"error": f"File not found on disk: {file_path}"}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=row["title"],
            mimetype=row["mime_type"] or "application/octet-stream"
        )
    finally:
        conn.close()


@app.route('/api/search')
def api_search():
    """Search materials across all modules."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"results": []})

    conn = _get_db()
    try:
        cursor = conn.execute("""
            SELECT mo.name as module_name, m.id, m.title, m.file_size, m.mime_type
            FROM materials m
            JOIN modules mo ON m.module_id = mo.id
            WHERE m.title LIKE ? OR m.content_text LIKE ?
            ORDER BY m.uploaded_at DESC
            LIMIT 50
        """, (f'%{query}%', f'%{query}%'))
        results = []
        for row in cursor.fetchall():
            results.append({
                "module": row["module_name"],
                "id": row["id"],
                "title": row["title"],
                "file_size": row["file_size"],
                "mime_type": row["mime_type"],
            })
        return jsonify({"query": query, "results": results})
    finally:
        conn.close()


@app.route('/apks/<path:filename>')
def download_apk(filename):
    """Serve APK files from the public/apks directory."""
    apk_dir = os.path.join(app.static_folder, '..', 'public', 'apks')
    apk_dir = os.path.realpath(apk_dir)
    return send_from_directory(apk_dir, filename, as_attachment=True)


@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "db_path": DB_PATH})


def start_webapp(host='0.0.0.0', port=5000):
    """Start the Flask web app. Call this in a background thread or process."""
    import threading
    server_thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True
    )
    server_thread.start()
    logger.info("Web app started at http://%s:%d", host, port)
    return server_thread


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get('WEBAPP_PORT', 5000))
    print(f"🌐 STUDYX Web App starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
