import pypistats
import json 
import requests
import os

# Get the GitHub API token from environment variables
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# Set up the API request headers
headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

def handle_python_library(library):
    try:
        data = json.loads(pypistats.overall(library["name"], format="json"))['data']
        if isinstance(data, list):
            data = data[0]
            last_month = data["downloads"]
        else:
            last_month = data["last_month"]
        library["downloads"] = last_month
    except Exception as e:
        print(f"Failed to get data for {library['name']}: {e}")
        raise e

def handle_javascript_library(library):
    if "package_manager_name" in library:
        name = library["package_manager_name"].lower()
    else:
        name = library["name"].lower()
    response = requests.get(f"https://api.npmjs.org/downloads/point/last-month/{name}", headers=headers)

    response.raise_for_status()
    data = response.json()
    last_month = data["downloads"]
    library["downloads"] = last_month

def handle_other_library(library):
    library["downloads"] = "N/A"

libraries = json.load(open("libraries.json"))


for library in libraries:
    print(f"Getting data for {library['name']}")

    # Get the latest number of stars for each library
    github_name = library["URL"].replace("https://github.com/", "")

    response = requests.get(f"https://api.github.com/repos/{github_name}")
    response.raise_for_status()
    data = response.json()
    library["value"] = data["stargazers_count"]

    if "Python" in library["Language"]:
        handle_python_library(library)
    elif "JavaScript" in library["Language"]:
        handle_javascript_library(library)
    else:
        handle_other_library(library)

json.dump(libraries, open("library_downloads.json", "w"), indent=2)