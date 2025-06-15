# josh-cloud-app

## Getting Started

Follow these steps to download and run this project locally:

### 1. Prerequisites

- **Python 3.11**: [Download Python](https://www.python.org/downloads/)
- **Node.js (LTS recommended)**: [Download Node.js](https://nodejs.org/en/download)
- **Azure Functions Core Tools**: See below for install/update instructions

### 2. Clone the Repository

```
git clone https://github.com/your-username/josh-cloud-app.git
cd josh-cloud-app
```

### 3. Create a Python 3.11 Virtual Environment

```
python -m venv .venv --prompt josh-cloud-app
```

Activate the virtual environment:
- **Windows (PowerShell):**
  ```
  .venv\Scripts\Activate.ps1
  ```
- **Windows (cmd):**
  ```
  .venv\Scripts\activate.bat
  ```
- **macOS/Linux:**
  ```
  source .venv/bin/activate
  ```

### 4. Install Python Dependencies

```
pip install -r requirements.txt
```

### 5. Install or Update Azure Functions Core Tools

If you do not have Azure Functions Core Tools, or want to update to the latest version, run:

```
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```

> If you get errors, make sure you are using Node.js version 14, 16, or 18 (not 20+).

### 6. Run the Azure Functions Host

```
func start
```

The function app will be available at `http://localhost:7071/api/hello`.

---

## Usage

Send a GET or POST request to `/api/hello` with a `name` parameter:

```
GET http://localhost:7071/api/hello?name=YourName
```

or POST with JSON body:

```
{
  "name": "YourName"
}
```

---

## Notes
- Make sure you have [Azure Functions Core Tools](https://docs.microsoft.com/azure/azure-functions/functions-run-local), [Node.js](https://nodejs.org/en/download), and Python 3.11 installed.
- Configure your `local.settings.json` for local development as needed.
- For local storage emulation, install Azurite: `npm install -g azurite` and run with `azurite`.
