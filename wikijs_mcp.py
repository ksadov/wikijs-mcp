import os
import httpx
import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get Wiki.js configuration from environment variables
WIKI_URL = os.getenv("WIKI_URL")
WIKI_API_KEY = os.getenv("WIKI_API_KEY")

# Validate required environment variables
if not WIKI_URL or not WIKI_API_KEY:
    logger.error("WIKI_URL and WIKI_API_KEY must be set in .env file")
    raise ValueError("WIKI_URL and WIKI_API_KEY must be set in .env file")

# Create an MCP server
logger.info(f"Creating MCP server for Wiki.js at {WIKI_URL}")
mcp = FastMCP("Wiki.js MCP Server")


class WikiJsClient:
    def __init__(self, url, api_key):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def search_pages(self, query):
        """Search for pages in Wiki.js"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/graphql",
                headers=self.headers,
                json={
                    "query": """
                    query ($query: String!) {
                        pages {
                            search(query: $query) {
                                results {
                                    id
                                    title
                                    description
                                    path
                                }
                            }
                        }
                    }
                    """,
                    "variables": {"query": query},
                },
            )

            if response.status_code != 200:
                return f"Error: {response.status_code} - {response.text}"

            data = response.json()
            if "errors" in data:
                return f"GraphQL Error: {data['errors']}"

            return data["data"]["pages"]["search"]["results"]

    async def get_page_by_id(self, page_id):
        """Get page content by ID"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/graphql",
                headers=self.headers,
                json={
                    "query": """
                    query ($id: Int!) {
                        pages {
                            single(id: $id) {
                                id
                                title
                                description
                                content
                                path
                                updatedAt
                            }
                        }
                    }
                    """,
                    "variables": {"id": int(page_id)},
                },
            )

            if response.status_code != 200:
                return f"Error: {response.status_code} - {response.text}"

            data = response.json()

            # Check for GraphQL errors
            if "errors" in data:
                # If the error is about a non-existent page, return None
                for error in data["errors"]:
                    if (
                        error.get("extensions", {}).get("exception", {}).get("code")
                        == 6003
                    ):
                        return None
                return f"GraphQL Error: {data['errors']}"

            # Check if the page exists in the response
            page_data = data.get("data", {}).get("pages", {}).get("single")
            if page_data is None:
                return None

            return page_data

    async def get_page_by_path(self, path):
        """Get page content by path"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/graphql",
                headers=self.headers,
                json={
                    "query": """
                    query ($path: String!, $locale: String!) {
                        pages {
                            singleByPath(path: $path, locale: $locale) {
                                id
                                title
                                description
                                content
                                path
                                updatedAt
                            }
                        }
                    }
                    """,
                    "variables": {"path": path, "locale": "en"},
                },
            )

            if response.status_code != 200:
                return f"Error: {response.status_code} - {response.text}"

            data = response.json()

            # Check for GraphQL errors
            if "errors" in data:
                # If the error is about a non-existent page, return None
                for error in data["errors"]:
                    if (
                        error.get("extensions", {}).get("exception", {}).get("code")
                        == 6003
                    ):
                        return None
                return f"GraphQL Error: {data['errors']}"

            # Check if the page exists in the response
            page_data = data.get("data", {}).get("pages", {}).get("singleByPath")
            if page_data is None:
                return None

            return page_data

    async def create_page(self, title, content, path, description=""):
        """Create a new page in Wiki.js"""
        variables = {
            "title": title,
            "content": content,
            "description": description,  # Now required, default to empty string
            "editor": "markdown",
            "locale": "en",
            "isPrivate": False,
            "isPublished": True,
            "path": path,
            "tags": [],
            "scriptCss": "",
            "scriptJs": "",
            "publishStartDate": None,
            "publishEndDate": None,
        }

        logger.info(f"Creating page with variables: {variables}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.url}/graphql",
                    headers=self.headers,
                    json={
                        "query": """
                        mutation (
                            $title: String!
                            $content: String!
                            $description: String!
                            $editor: String!
                            $locale: String!
                            $isPrivate: Boolean!
                            $isPublished: Boolean!
                            $path: String!
                            $tags: [String]!
                            $scriptCss: String
                            $scriptJs: String
                            $publishStartDate: Date
                            $publishEndDate: Date
                        ) {
                            pages {
                                create(
                                    title: $title
                                    content: $content
                                    description: $description
                                    editor: $editor
                                    locale: $locale
                                    isPrivate: $isPrivate
                                    isPublished: $isPublished
                                    path: $path
                                    tags: $tags
                                    scriptCss: $scriptCss
                                    scriptJs: $scriptJs
                                    publishStartDate: $publishStartDate
                                    publishEndDate: $publishEndDate
                                ) {
                                    responseResult {
                                        succeeded
                                        slug
                                        message
                                    }
                                    page {
                                        id
                                        title
                                        content
                                        description
                                        path
                                    }
                                }
                            }
                        }
                        """,
                        "variables": variables,
                    },
                )

                if response.status_code != 200:
                    error_msg = f"HTTP Error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return error_msg

                data = response.json()
                logger.info(f"API Response: {data}")

                if "errors" in data:
                    error_msg = f"GraphQL Error: {data['errors']}"
                    logger.error(error_msg)
                    return error_msg

                if (
                    "data" not in data
                    or "pages" not in data["data"]
                    or "create" not in data["data"]["pages"]
                ):
                    error_msg = f"Unexpected response structure: {data}"
                    logger.error(error_msg)
                    return error_msg

                result = data["data"]["pages"]["create"]["responseResult"]
                if result["succeeded"]:
                    page_data = data["data"]["pages"]["create"]["page"]
                    success_msg = (
                        f"Page created successfully with ID: {page_data['id']}"
                    )
                    logger.info(success_msg)
                    return success_msg
                else:
                    error_msg = f"Failed to create page: {result['message']}"
                    logger.error(error_msg)
                    return error_msg

            except Exception as e:
                error_msg = f"Exception during page creation: {str(e)}"
                logger.error(error_msg)
                return error_msg

    async def update_page(self, page_id, content):
        """Update page content"""
        # First get the current page to preserve other fields
        page = await self.get_page_by_id(page_id)
        if isinstance(page, str) and page.startswith("Error"):
            return page
        if page is None:
            return f"Error: No page found with ID: {page_id}"

        # Prepare the update mutation with all required fields
        variables = {
            "id": int(page_id),
            "title": page.get("title", ""),  # Preserve existing title
            "content": content,
            "description": page.get("description", ""),  # Preserve existing description
            "editor": "markdown",
            "locale": "en",
            "isPrivate": False,
            "isPublished": True,
            "path": page.get("path", ""),  # Preserve existing path
            "tags": [],  # Empty tags array
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/graphql",
                headers=self.headers,
                json={
                    "query": """
                    mutation (
                        $id: Int!
                        $title: String
                        $content: String
                        $description: String
                        $editor: String
                        $locale: String
                        $isPrivate: Boolean
                        $isPublished: Boolean
                        $path: String
                        $tags: [String]
                    ) {
                        pages {
                            update(
                                id: $id
                                title: $title
                                content: $content
                                description: $description
                                editor: $editor
                                locale: $locale
                                isPrivate: $isPrivate
                                isPublished: $isPublished
                                path: $path
                                tags: $tags
                            ) {
                                responseResult {
                                    succeeded
                                    slug
                                    message
                                }
                                page {
                                    id
                                    title
                                    content
                                    description
                                    path
                                    tags {
                                        id
                                        tag
                                        title
                                        createdAt
                                        updatedAt
                                    }
                                }
                            }
                        }
                    }
                    """,
                    "variables": variables,
                },
            )

            if response.status_code != 200:
                logger.error(f"HTTP Error: {response.status_code} - {response.text}")
                return f"Error: {response.status_code} - {response.text}"

            data = response.json()
            logger.info(f"API Response: {data}")  # Add logging of the full response

            if "errors" in data:
                logger.error(f"GraphQL Errors: {data['errors']}")
                return f"GraphQL Error: {data['errors']}"

            if (
                "data" not in data
                or "pages" not in data["data"]
                or "update" not in data["data"]["pages"]
            ):
                logger.error(f"Unexpected response structure: {data}")
                return f"Unexpected response structure from API"

            result = data["data"]["pages"]["update"]["responseResult"]
            if result["succeeded"]:
                return f"Page updated successfully: {result['slug']}"
            else:
                return f"Failed to update page: {result['message']}"


# Initialize the Wiki.js client
wiki_client = WikiJsClient(WIKI_URL, WIKI_API_KEY)


@mcp.tool()
async def search_wiki(query: str, ctx: Context) -> str:
    """
    Search for pages in Wiki.js

    Args:
        query: The search query string

    Returns:
        A list of pages that match the search query
    """
    await ctx.info(f"Searching Wiki.js for: {query}")
    results = await wiki_client.search_pages(query)

    if isinstance(results, str) and results.startswith("Error"):
        return results

    if not results:
        return "No results found"

    # Format the results
    formatted_results = ["Search results:"]
    for page in results:
        formatted_results.append(
            f"- ID: {page['id']}, Title: {page['title']}, Path: {page['path']}"
        )
        if page.get("description"):
            formatted_results.append(f"  Description: {page['description']}")

    return "\n".join(formatted_results)


@mcp.tool()
async def get_page(identifier: str, ctx: Context, by_path: bool = False) -> str:
    """
    Get page content and metadata from Wiki.js

    Args:
        identifier: Either the page ID (number) or the relative page path (string, i.e /people/Zef)
        by_path: If True, look up by path instead of page ID number. False by default.

    Returns:
        The page content and metadata or an error message if the page is not found
    """
    if by_path:
        await ctx.info(f"Getting page by path: {identifier}")
        page = await wiki_client.get_page_by_path(identifier)
    else:
        try:
            page_id = int(identifier)
            await ctx.info(f"Getting page by ID: {page_id}")
            page = await wiki_client.get_page_by_id(page_id)
        except ValueError:
            return "Error: When by_path is False, identifier must be a numeric ID"

    # Debug logging
    await ctx.info(f"Page data type: {type(page)}")
    await ctx.info(f"Page data: {page}")

    if isinstance(page, str) and page.startswith("Error"):
        return page

    if not page or page is None:
        return f"No page found with {'path' if by_path else 'ID'}: {identifier}"

    # Ensure page is a dictionary before accessing its keys
    if not isinstance(page, dict):
        return f"Unexpected response format: {page}"

    # Format the page data
    return f"""
Title: {page.get('title', 'No title')}
Path: {page.get('path', 'No path')}
ID: {page.get('id', 'No ID')}
Last Updated: {page.get('updatedAt', 'No update time')}
Description: {page.get('description', 'No description')}

Content:
{page.get('content', 'No content')}
"""


@mcp.tool()
async def update_page(page_id: str, content: str, ctx: Context) -> str:
    """
    Update a Wiki.js page's content

    Note that
        - page_id is the numeric ID of the page
        - content totally replaces the existing content of the page. You may want to
        get the existing content first to make sure that you're not overwriting anything
        important.

    Args:
        page_id: The ID of the page to update
        content: The new content for the page

    Returns:
        A status message indicating success or failure
    """
    try:
        page_id_int = int(page_id)
    except ValueError:
        return "Error: page_id must be a numeric ID"

    await ctx.info(f"Updating page with ID: {page_id_int}")
    await ctx.info("Updating content")

    result = await wiki_client.update_page(page_id_int, content)
    return result


@mcp.tool()
async def create_page(
    title: str, content: str, path: str, ctx: Context, description: str = ""
) -> str:
    """
    Create a new page in Wiki.js

    Args:
        title: The title of the new page
        content: The content of the new page
        path: The path where the page should be created (e.g., '/my-page')
        description: Description of the page contents (required, defaults to empty string)

    Returns:
        A status message indicating success or failure, including the new page ID if successful
    """
    await ctx.info(f"Creating new page with title: {title} at path: {path}")
    await ctx.info(f"Description: {description}")

    result = await wiki_client.create_page(title, content, path, description)
    return result


if __name__ == "__main__":
    logger.info("Starting Wiki.js MCP Server...")
    try:
        # Run the MCP server
        mcp.run(transport="stdio")
        # Note: The above line will not return until the server is shut down
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        raise
