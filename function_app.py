import azure.functions as func
import logging

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