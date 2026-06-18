import urllib.parse
import re
import httpx

def search_web(query: str) -> str:
    """
    Performs a web search using DuckDuckGo HTML search interface and returns a summary of the results.
    
    Args:
        query (str): The search query to look up on the web.
    """
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        with httpx.Client(headers=headers, follow_redirects=True, timeout=10.0) as client:
            response = client.get(url)
            if response.status_code != 200:
                return f"Failed to retrieve search results. Status code: {response.status_code}"
            
            html = response.text
            
            # Simple regex parser to extract results from DuckDuckGo HTML
            # Results are in divs with class "result__body"
            # Title & Link are inside a href with class "result__url"
            # Snippet is inside an a with class "result__snippet"
            
            bodies = re.findall(r'<div class="result__body">.*?</div>\s*</div>', html, re.DOTALL)
            
            if not bodies:
                # Fallback to general link/snippet matching if class names changed
                bodies = re.findall(r'<a class="result__url".*?</a>.*?<a class="result__snippet".*?</a>', html, re.DOTALL)
            
            results = []
            for body in bodies[:5]:  # Get top 5 results
                # Extract title
                title_match = re.search(r'<a class="result__url"[^>]*>(.*?)</a>', body, re.DOTALL)
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else "No Title"
                
                # Extract URL
                url_match = re.search(r'href="([^"]+)"', body)
                raw_url = url_match.group(1) if url_match else ""
                
                # Clean up DuckDuckGo redirect URLs if present
                if "/l/?" in raw_url or "uddg=" in raw_url:
                    parsed_url = urllib.parse.urlparse(raw_url)
                    query_params = urllib.parse.parse_qs(parsed_url.query)
                    actual_url = query_params.get("uddg", [raw_url])[0]
                    actual_url = urllib.parse.unquote(actual_url)
                else:
                    actual_url = raw_url
                
                # Extract snippet
                snippet_match = re.search(r'<a class="result__snippet"[^>]*>(.*?)</a>', body, re.DOTALL)
                snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip() if snippet_match else "No Description"
                
                results.append(f"Title: {title}\nURL: {actual_url}\nSnippet: {snippet}\n---")
                
            if not results:
                return "No results found for this search query."
                
            return "\n".join(results)
            
    except Exception as e:
        return f"An error occurred during search execution: {str(e)}"
