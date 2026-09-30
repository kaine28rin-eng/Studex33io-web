#!/usr/bin/env python3
"""Sync study materials from the SQLite DB to a JSON file for GitHub Pages.

Push this JSON to the Studex33io-web repo's docs/ folder so the static
webapp can fetch it at /api/materials.json.

Usage:
  python3 -m webapp.sync_db_to_json
"""
import os
import sys
import json
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_PATH


async def sync():
    """Read all modules + materials from SQLite and write JSON."""
    import aiosqlite
    materials_data = {"modules": [], "last_updated": None}

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Get all modules with material counts
        cursor = await db.execute("""
            SELECT mo.id, mo.name, mo.description,
                   COUNT(m.id) as material_count
            FROM modules mo
            LEFT JOIN materials m ON m.module_id = mo.id
            GROUP BY mo.id
            ORDER BY mo.name
        """)
        rows = await cursor.fetchall()

        for row in rows:
            materials_data["modules"].append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"] or "",
                "material_count": row["material_count"] or 0,
            })

        # Get all materials with module names
        cursor = await db.execute("""
            SELECT mo.name as module_name, m.id, m.title, m.file_path,
                   m.file_size, m.mime_type, m.content_text, m.uploaded_at
            FROM materials m
            JOIN modules mo ON m.module_id = mo.id
            ORDER BY m.uploaded_at DESC
        """)
        rows = await cursor.fetchall()

        all_materials = []
        for row in rows:
            all_materials.append({
                "module": row["module_name"],
                "id": row["id"],
                "title": row["title"],
                "file_path": row["file_path"],
                "file_size": row["file_size"],
                "mime_type": row["mime_type"],
                "content_text": row["content_text"],
                "uploaded_at": row["uploaded_at"],
            })

        materials_data["materials"] = all_materials
        materials_data["last_updated"] = datetime.utcnow().isoformat()

    # Write JSON file
    output_path = os.path.join(os.path.dirname(__file__), 'api', 'materials.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(materials_data, f, indent=2, default=str)

    print(f"✅ Synced {len(materials_data['modules'])} modules, {len(materials_data['materials'])} materials")
    print(f"   Output: {output_path}")
    return output_path


if __name__ == '__main__':
    from datetime import datetime
    asyncio.run(sync())
