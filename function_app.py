import azure.functions as func
import logging
import feedparser   
import requests
import hashlib
import re
from urllib.parse import urlparse, parse_qs


app = func.FunctionApp()

@app.function_name(name="HttpTrigger1")
@app.route(route="hello", auth_level=func.AuthLevel.ANONYMOUS)
@app.queue_output(arg_name="msg", queue_name="outqueue", connection="AzureWebJobsStorage")
@app.cosmos_db_output(arg_name="outputDocument", database_name="my-database", container_name="my-container", connection="CosmosDbConnectionSetting")
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

def make_safe_id(guid: str) -> str:
    # Remove all non-alphanumeric characters
    return re.sub(r'[^A-Za-z0-9]', '', guid)


def make_safe_id(guid: str) -> str:
    # Remove all non-alphanumeric characters
    return re.sub(r'[^A-Za-z0-9]', '', guid)

@app.function_name(name="CollectRssFeedScheduleTrigger")
@app.schedule(schedule="0 */5 * * * *", arg_name="mytimer", connection="AzureWebJobsStorage")
def collect_rss_feed(mytimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function processed a request.')
    feed_urls = [
        "https://thefifthtrooper.com/feed/",
        "https://wintermoonwargaming.substack.com/feed",
        "https://yetanother-feed-url.com/rss", 
        "https://apointofinterestlegion.substack.com/feed"
        # Add more feed URLs as needed
    ]
    endpoint = "http://localhost:7071/api/processrssfeed"  # Update if deployed

    for rss_url in feed_urls:
        logging.info(f"Collecting RSS feed data from {rss_url}")
        d = feedparser.parse(rss_url)
        if d.entries:
            for entry in d.entries:
                logging.info(f"Title: {entry.title}, Link: {entry.link}")
                guid_url = entry.get("guid") or entry.get("link")
                doc_id = make_safe_id(guid_url) if guid_url else None
                entry_dict = dict(entry)
                entry_dict["id"] = doc_id
                try:
                    response = requests.post(endpoint, json=entry_dict)
                    response.raise_for_status()
                    logging.info(f"Posted entry {doc_id} successfully.")
                except Exception as e:
                    logging.exception(f"Failed to POST entry {doc_id}: {e}")
        else:
            logging.info(f"No entries found in RSS feed {rss_url}.")


@app.function_name(name="ProcessRssFeedQueueTrigger")
@app.route(route="processrssfeed", methods=["POST"])
@app.cosmos_db_output(arg_name="outputDocument", database_name="legion", container_name="podcasts", connection="CosmosDbConnectionStringLegion")
def process_rss_feed(req: func.HttpRequest, outputDocument: func.Out[func.Document]) -> func.HttpResponse:
    try:
        doc = req.get_json()
        outputDocument.set(func.Document.from_dict(doc))
        return func.HttpResponse("Document stored.", status_code=201)
    except Exception as e:
        logging.exception("Failed to process RSS feed entry.")
        return func.HttpResponse("Error processing entry.", status_code=500)


