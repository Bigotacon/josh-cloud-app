import logging
import asyncio
import re
import feedparser
import httpx
import os
from azure.cosmos.aio import CosmosClient
import azure.functions as func
from azure.cosmos import exceptions
from azure.functions.decorators import app

app = func.FunctionApp()

@app.function_name(name="HttpTrigger1")
@app.route(route="hello", auth_level=func.AuthLevel.ANONYMOUS)
@app.queue_output(arg_name="msg", queue_name="outqueue", connection="AzureWebJobsStorage")
@app.cosmos_db_output(arg_name="outputDocument", database_name="my-database", container_name="my-container", connection="CosmosDbConnectionString")
def test_function(req: func.HttpRequest, msg: func.Out[func.QueueMessage],
    outputDocument: func.Out[func.Document]) -> func.HttpResponse:
    try:
        logging.info('Python HTTP trigger function processed a request.')
        logging.info('Python Cosmos DB trigger function processed a request.')
        name = req.params.get('name')
        if not name:
            try:
                req_body = req.get_json()
            except ValueError as ve:
                logging.warning(f"Failed to parse JSON body: {ve}")
                req_body = None
            else:
                name = req_body.get('name') if req_body else None

        if name:
            try:
                outputDocument.set(func.Document.from_dict({"id": name}))
            except Exception as e:
                logging.exception(f"Error writing to Cosmos DB: {e}")
                return func.HttpResponse("Error writing to Cosmos DB.", status_code=500)
            try:
                msg.set(name)
            except Exception as e:
                logging.exception(f"Error writing to Queue: {e}")
                return func.HttpResponse("Error writing to Queue.", status_code=500)
            return func.HttpResponse(f"Hello {name}!")
        else:
            return func.HttpResponse(
                        "Please pass a name on the query string or in the request body",
                        status_code=400
                    )
    except Exception as e:
        logging.exception(f"Unhandled exception in function: {e}")
        return func.HttpResponse("Internal server error.", status_code=500)
    

feed_urls = [
    {"site": "fifthtrooper", "url": "https://thefifthtrooper.com/feed/"},
    {"site": "wintermoonwargaming", "url": "https://wintermoonwargaming.substack.com/feed"},
    {"site": "yetanother", "url": "https://yetanother-feed-url.com/rss"},
    {"site": "apointofinterestlegion", "url": "https://apointofinterestlegion.substack.com/feed"}
]
COSMOS_CONNECTION_STRING = os.environ["CosmosDbConnectionStringLegion"]
COSMOS_DATABASE = "legion"
COSMOS_CONTAINER = "podcasts"

def make_safe_id(guid: str) -> str:
    # Remove all non-alphanumeric characters
    return re.sub(r'[^A-Za-z0-9]', '', guid)

async def process_rss_feed(feed, container):
    site = feed["site"]
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(feed["url"], timeout=10.0)
        parsed = feedparser.parse(response.text)
        if not parsed.entries:
            logging.info(f"No entries found in RSS feed {feed['url']}.")
            return 
        
        inserted = 0
        skipped = 0

        for entry in parsed.entries:
            guid_url = entry.get("guid") or entry.get("link")
            if not guid_url:
                logging.warning(f"Entry in RSS feed {feed['url']} has no GUID or link, skipping.")
                continue    
            doc_id = make_safe_id(guid_url) if guid_url else None
            entry_dict = dict(entry)
            entry_dict["id"] = doc_id
            entry_dict["site"] = site

            await container.read_item(item=doc_id, partition_key=doc_id)
            try:
                logging.info(f"Item with ID {doc_id} already exists, skipping.")
                skipped += 1
            except exceptions.CosmosResourceNotFoundError:
                await container.upsert_item(entry_dict)
                logging.info(f"Inserted item with ID {doc_id}.")
                inserted += 1

    except Exception as e:
        logging.exception(f"Error processing RSS feed {feed['url']}: {e}")

@app.schedule(schedule="0 */5 * * * *", arg_name="mytimer", connection="AzureWebJobsStorage")
async def main():
    async with CosmosClient.from_connection_string(COSMOS_CONNECTION_STRING) as cosmos_client:
        container = cosmos_client.get_database_client(COSMOS_DATABASE).get_container_client(COSMOS_CONTAINER)
        tasks = [process_rss_feed(feed=feed, container=container) for feed in feed_urls]
        await asyncio.gather(*tasks)

            