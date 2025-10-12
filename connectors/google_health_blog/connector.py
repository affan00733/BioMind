import logging
import requests
from bs4 import BeautifulSoup
from google.cloud import bigquery
import connectors.google_health_blog.config as config

def run_google_health_blog_connector():
    try:
        res = requests.get(config.BASE_URL)
        res.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to retrieve Google Health blog: {e}")
        return
    soup = BeautifulSoup(res.text, 'html.parser')
    posts = soup.find_all('a', href=True)
    posts_urls = set()
    for a in posts:
        href = a['href']
        if href.startswith("/blog/") and "/technology/health" in href:
            full_url = "https://blog.google" + href
            posts_urls.add(full_url)

    rows_to_insert = []
    for url in posts_urls:
        try:
            page = requests.get(url)
            page.raise_for_status()
            page_soup = BeautifulSoup(page.text, 'html.parser')
            title_tag = page_soup.find('h1')
            title = title_tag.get_text().strip() if title_tag else ""
            paragraphs = page_soup.find_all('p')
            content = "\n".join([p.get_text() for p in paragraphs])
            post_id = title.replace(" ", "_")[:50]
            rows_to_insert.append({
                "post_id": post_id,
                "url": url,
                "title": title,
                "content": content
            })
        except Exception as e:
            logging.error(f"Failed to fetch blog post {url}: {e}")
            continue

    if rows_to_insert:
        bq_client = bigquery.Client(project=config.PROJECT_ID)
        dataset_ref = bq_client.dataset(config.BIGQUERY_DATASET)
        table_ref = dataset_ref.table(config.TABLE_NAME)
        schema = [
            bigquery.SchemaField("post_id", "STRING"),
            bigquery.SchemaField("url", "STRING"),
            bigquery.SchemaField("title", "STRING"),
            bigquery.SchemaField("content", "STRING")
        ]
        try:
            table = bigquery.Table(table_ref, schema=schema)
            bq_client.create_table(table, exists_ok=True)
        except Exception:
            pass
        errors = bq_client.insert_rows_json(table_ref, rows_to_insert)
        if errors:
            logging.error(f"Errors inserting Google Health blog rows: {errors}")
        else:
            logging.info(f"Inserted {len(rows_to_insert)} rows into {config.TABLE_NAME}.")
