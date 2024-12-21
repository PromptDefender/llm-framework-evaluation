import datetime
import requests
import csv
from tenacity import retry, stop_after_attempt, wait_fixed
import os 

# Define your GitHub API token
GITHUB_TOKEN=os.getenv("GH_TOKEN")

# Set up the API request headers
headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

current_rage_limit = 0 

@retry(stop=stop_after_attempt(5), wait=wait_fixed(60))
def make_request(url, headers):
    global current_rage_limit

    # Get the current time in UTC
    current_time = datetime.datetime.utcnow()

    if datetime.datetime.fromtimestamp(current_rage_limit) > current_time:
        print("Rate limited. Sleeping for ", current_rage_limit - current_time)
        sleep_time = current_rage_limit - current_time
        datetime.time.sleep(sleep_time.total_seconds())

    response = requests.get(url, headers=headers)
    if response.status_code == 403:
        print("Rate limited. Retrying... for URL: ", url)
        current_rage_limit = int(response.headers['X-RateLimit-Remaining'])

    response.raise_for_status()
    return response

def search_frameworks(query, filename):
    # Construct the API URL
    import urllib.parse
    escaped_query = urllib.parse.quote(query)
    url = f"https://api.github.com/search/code?q={escaped_query}"

    unique_repos = set()
    page = 1

    while True:
        response = make_request(f"{url}&page={page}", headers)

        # Parse the JSON response
        if response.status_code == 200:
            data = response.json()
            for item in data.get("items", []):
                unique_repos.add(item['repository']['full_name'])
            if 'next' not in response.links:
                break
            page += 1
        else:
            print(f"Error: {response.status_code} - {response.json()} (for query) {query}")
            raise SystemExit

    # Fetch stars for each unique repository
    repo_stars = {}
    for repo_name in unique_repos:
        repo_url = f"https://api.github.com/repos/{repo_name}"
        repo_response = make_request(repo_url, headers)
        if repo_response.status_code == 200:
            repo_data = repo_response.json()
            repo_stars[repo_name] = repo_data.get('stargazers_count', 0)
        else:
            repo_stars[repo_name] = "Error fetching stars"

    # Write the repository information to a CSV file
    with open("{0}.csv".format(filename), "w", newline='') as csvfile:
        fieldnames = ['Repository', 'Stars']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for repo_name, stars in repo_stars.items():
            writer.writerow({'Repository': repo_name, 'Stars': stars})

queries = [
    ('"import prompty" OR "from prompty import" NOT owner:microsoft NOT owner:Azure NOT owner:Azure-Samples language:Python NOT is:fork', "prompty"),
    ('"@genkit-ai" NOT is:fork NOT owner:firebase language:JavaScript OR language:TypeScript NOT is:fork NOT repo:GoogleCloudPlatform/generative-ai NOT repo:TheFireCo/genkit-plugins NOT repo:project-idx/templates NOT repo:invertase/genkit-plugin-redis', "genkit-js"),
    ('github.com/firebase/genkit/go language:Go NOT repo:firebase/genkit NOT repo:golang/example NOT is:fork', "genkit-go"),
    ('promptflow path:requirements.txt NOT is:fork NOT owner:microsoft NOT owner:Azure', 'prompt-flow'),
    ('"from aiconfig import" or "import aiconfig" NOT owner:lastmile-ai language:Python NOT is:fork', "aiconfig-python"),
    ('from "aiconfig" NOT owner:lastmile-ai language:JavaScript OR language:TypeScript NOT is:fork', "aiconfig-js"),
]

for query, filename in queries:
    search_frameworks(query, filename)
