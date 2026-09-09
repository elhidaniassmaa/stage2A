"""Script de vérification du rattachement SQLite <-> JSON RAG."""
from sync_base_reglementaire import rattacher_articles_heritage, _charger_json, modifier_article_rag, supprimer_article_rag
from database import get_db_connection


def main():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM articles")
    total_sqlite = cur.fetchone()[0]
    conn.close()

    data = _charger_json()
    with_id = sum(1 for c in data if c.get("admin_article_id"))
    print(f"SQLite articles: {total_sqlite}")
    print(f"JSON tirets: {len(data)}, avec admin_article_id: {with_id}")

    result = rattacher_articles_heritage()
    print(f"Rattachement: {result}")

    data2 = _charger_json()
    with_id2 = sum(1 for c in data2 if c.get("admin_article_id"))
    print(f"Apres rattachement: {with_id2} tirets lies")


if __name__ == "__main__":
    main()
