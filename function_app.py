import azure.functions as func
import logging
import feedparser   
import requests
import hashlib
import re
from urllib.parse import urlparse, parse_qs
import os
import uuid
from datetime import datetime

from azure.eventgrid import EventGridPublisherClient, EventGridEvent
from azure.core.credentials import AzureKeyCredential

topic_endpoint = os.environ.get("EventGridTopicEndpoint")
access_key = "Bv6FFuPkRSErKm0OkWND2ftMwp6NOiH5ZJ4V2H37pqjF9P0egtwWJQQJ99BFACBsN54XJ3w3AAABAZEGhqfw"

credential = AzureKeyCredential(access_key)
event_client = EventGridPublisherClient(topic_endpoint, credential)

app = func.FunctionApp()

def make_safe_id(guid: str) -> str:
    # Remove all non-alphanumeric characters
    return re.sub(r'[^A-Za-z0-9]', '', guid)

@app.function_name(name="CollectRssFeedScheduleTrigger")
@app.schedule(schedule="0 */5 * * * *", arg_name="mytimer", connection="AzureWebJobsStorage")
def collect_rss_feed(mytimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function processed a request.')
    feed_urls = [
        {"site": "fifthtrooper", "url": "https://thefifthtrooper.com/feed/"},
        {"site": "wintermoonwargaming", "url": "https://wintermoonwargaming.substack.com/feed"},
        {"site": "yetanother", "url": "https://yetanother-feed-url.com/rss"},
        {"site": "apointofinterestlegion", "url": "https://apointofinterestlegion.substack.com/feed"}
    ]

    events = []
    for feed in feed_urls:
        rss_url = feed["url"]
        site = feed["site"]
        logging.info(f"Collecting RSS feed data from {rss_url}")
        d = feedparser.parse(rss_url)
        entries = []
        if d.entries:
            for entry in d.entries:
                guid_url = entry.get("guid") or entry.get("link")
                doc_id = make_safe_id(guid_url) if guid_url else None
                entry_dict = dict(entry)
                entry_dict["id"] = doc_id
                entries.append(entry_dict)
            event = EventGridEvent(
                subject=f"RssFeed/{site}",
                data={"site": site, "entries": entries},
                event_type="RssFeed.NewEntries",
                data_version="1.0"
            )
            events.append(event)
            logging.info(f"Added {len(entries)} entries for {site} as one event.")
        else:
            logging.info(f"No entries found in RSS feed {rss_url}.")

    if events:
        event_client.send(events)
        logging.info(f"Published {len(events)} events to Event Grid.")
    else:
        logging.info("No events to publish.")


@app.function_name(name="ProcessRssFeedQueueTrigger")
@app.route(route="processrssfeed", methods=["POST"])
@app.cosmos_db_output(arg_name="outputDocument", database_name="legion", container_name="podcasts", connection="CosmosDbConnectionStringLegion")
def process_rss_feed(req: func.HttpRequest, outputDocument: func.Out[func.Document]) -> func.HttpResponse:
    try:
        # Handle Event Grid validation handshake
        events = req.get_json()
        if isinstance(events, list) and events and "validationCode" in events[0]:
            return func.HttpResponse(events[0]["validationCode"], status_code=200)
        # Process Event Grid events
        if isinstance(events, list):
            for event in events:
                data = event.get("data")
                if data and "entries" in data:
                    for entry in data["entries"]:
                        outputDocument.set(func.Document.from_dict(entry))
            return func.HttpResponse("Documents stored.", status_code=201)
        else:
            return func.HttpResponse("No valid events received.", status_code=400)
    except Exception as e:
        logging.exception("Failed to process RSS feed entry.")
        return func.HttpResponse("Error processing entry.", status_code=500) 